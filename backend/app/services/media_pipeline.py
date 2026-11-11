"""End-to-end media ingestion, import, proxy, and thumbnail pipeline coordinator."""

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import is_path_confined
from app.core.storage import StorageLayout
from app.models.entities import MediaAssetRecord
from app.schemas.core import MediaStorageStatsResponse
from app.services.jobs import JobOrchestrator
from app.services.media import MediaService
from app.services.media_probe import probe_media_file
from app.services.media_proxy import generate_proxy
from app.services.media_thumbnail import generate_thumbnail
from app.services.projects import ProjectService

logger = logging.getLogger("zezedit.media_pipeline")

STREAM_CHUNK_SIZE = 1024 * 1024  # 1 MB chunk for streaming to prevent high RAM consumption
MIN_FREE_SPACE_BYTES = 100 * 1024 * 1024  # 100 MB safety headroom


class MediaPipelineService:
    """Coordinates media file import, metadata extraction, thumbnailing, and proxy creation."""

    def __init__(
        self,
        settings: Settings,
        storage: StorageLayout,
        media_service: MediaService,
        project_service: ProjectService,
        job_orchestrator: JobOrchestrator,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.media_service = media_service
        self.project_service = project_service
        self.job_orchestrator = job_orchestrator

    def import_local_media(
        self,
        project_id: str,
        file_path: str,
        copy_to_storage: bool = False,
        generate_proxy_now: bool = False,
        generate_thumbnail_now: bool = True,
        proxy_profile: str = "480p",
    ) -> MediaAssetRecord:
        """
        Import a local media file by reference or by copying into managed storage.
        Runs FFprobe metadata extraction, thumbnail generation, and optional proxy transcoding.
        """
        project = self.project_service.get_project(project_id)
        src = Path(file_path).expanduser().resolve(strict=False)

        if not src.is_file():
            raise AppError(
                code="FILE_NOT_FOUND",
                message=f"Local media file '{src}' does not exist or is not a regular file.",
                status_code=404,
            )

        file_size = src.stat().st_size
        if file_size == 0:
            raise AppError(
                code="EMPTY_MEDIA_FILE",
                message=f"Source file '{src.name}' is empty (0 bytes).",
                status_code=400,
            )

        # Create persistent job tracking the import
        job = self.job_orchestrator.create_job(
            job_type="media_import",
            project_id=project_id,
            input_config={
                "source_path": str(src),
                "copy_to_storage": copy_to_storage,
                "generate_proxy": generate_proxy_now,
            },
        )
        self.job_orchestrator.transition_job_state(
            job.id, "running", progress_pct=0.1, stage="preparing"
        )

        try:
            # Handle storage mode
            if copy_to_storage:
                self._check_disk_space(file_size)
                proj_media_dir = self.storage.media / project.storage_subdir
                proj_media_dir.mkdir(parents=True, exist_ok=True)
                clean_name = f"{uuid.uuid4().hex[:8]}_{src.name}"
                dest_path = proj_media_dir / clean_name

                logger.info("Copying local file to managed storage: %s -> %s", src, dest_path)
                with open(src, "rb") as fsrc, open(dest_path, "wb") as fdst:
                    shutil.copyfileobj(fsrc, fdst, length=STREAM_CHUNK_SIZE)

                effective_path = dest_path
                is_external = False
            else:
                effective_path = src
                is_external = True

            # Probe media metadata with FFprobe
            self.job_orchestrator.transition_job_state(
                job.id, "running", progress_pct=0.3, stage="extracting_metadata"
            )
            probe = probe_media_file(effective_path, ffprobe_path=self.settings.ffprobe_path)

            # Register media asset record in database
            asset = self.media_service.register_media_asset(
                project_id=project_id,
                original_filename=src.name,
                storage_path=str(effective_path),
                is_external=is_external,
                media_type=probe.media_type,
                file_size_bytes=probe.file_size_bytes,
                duration_seconds=probe.duration_seconds,
                width=probe.width,
                height=probe.height,
                fps=probe.fps,
                video_codec=probe.video_codec,
                audio_codec=probe.audio_codec,
                metadata=probe.raw_metadata,
                metadata_status="extracted",
            )

            # Generate Thumbnail
            thumb_rel_path: Optional[str] = None
            if generate_thumbnail_now and probe.media_type in {"video", "image", "audio"}:
                self.job_orchestrator.transition_job_state(
                    job.id, "running", progress_pct=0.6, stage="generating_thumbnail"
                )
                thumb_dest = self.storage.thumbnails / f"{asset.id}.jpg"
                thumb_res = generate_thumbnail(
                    source_path=effective_path,
                    output_path=thumb_dest,
                    media_type=probe.media_type,
                    duration=probe.duration_seconds,
                    ffmpeg_path=self.settings.ffmpeg_path,
                )
                if thumb_res:
                    thumb_rel_path = str(thumb_res)
                    self.media_service.update_media_metadata(
                        project_id=project_id,
                        asset_id=asset.id,
                        updates={"thumbnail_reference_path": thumb_rel_path},
                    )

            # Generate Proxy if requested and media is video
            if generate_proxy_now and probe.media_type == "video":
                self.job_orchestrator.transition_job_state(
                    job.id, "running", progress_pct=0.8, stage="generating_proxy"
                )
                proxy_dest = self.storage.proxies / f"{asset.id}_proxy_{proxy_profile}.mp4"
                self.media_service.update_media_metadata(
                    project_id=project_id,
                    asset_id=asset.id,
                    updates={"proxy_status": "generating"},
                )
                try:
                    proxy_res = generate_proxy(
                        source_path=effective_path,
                        output_path=proxy_dest,
                        profile=proxy_profile,
                        max_threads=self.settings.ffmpeg_threads,
                        ffmpeg_path=self.settings.ffmpeg_path,
                    )
                    self.media_service.update_media_metadata(
                        project_id=project_id,
                        asset_id=asset.id,
                        updates={
                            "proxy_reference_path": str(proxy_res),
                            "proxy_status": "ready",
                        },
                    )
                except Exception as proxy_err:
                    logger.warning("Optional proxy generation failed for %s: %s", asset.id, proxy_err)
                    self.media_service.update_media_metadata(
                        project_id=project_id,
                        asset_id=asset.id,
                        updates={"proxy_status": "failed"},
                    )

            # Mark job completed
            self.job_orchestrator.transition_job_state(
                job.id,
                "completed",
                progress_pct=1.0,
                stage="completed",
                result_metadata={"asset_id": asset.id, "media_type": probe.media_type},
            )
            return self.media_service.get_media_asset(project_id, asset.id)

        except Exception as exc:
            logger.error("Media import failed for %s: %s", src, exc, exc_info=True)
            self.job_orchestrator.transition_job_state(
                job.id, "failed", error_message=str(exc), stage="failed"
            )
            raise

    async def import_uploaded_media(
        self,
        project_id: str,
        upload_file: UploadFile,
        generate_proxy_now: bool = False,
        generate_thumbnail_now: bool = True,
        proxy_profile: str = "480p",
    ) -> MediaAssetRecord:
        """
        Stream an uploaded media file in bounded chunks to managed storage.
        Extracts metadata and optionally generates thumbnails/proxies.
        """
        project = self.project_service.get_project(project_id)
        original_filename = upload_file.filename or "uploaded_media"

        proj_media_dir = self.storage.media / project.storage_subdir
        proj_media_dir.mkdir(parents=True, exist_ok=True)
        clean_name = f"{uuid.uuid4().hex[:8]}_{original_filename}"
        dest_path = proj_media_dir / clean_name

        job = self.job_orchestrator.create_job(
            job_type="media_import",
            project_id=project_id,
            input_config={"uploaded_filename": original_filename, "destination": str(dest_path)},
        )
        self.job_orchestrator.transition_job_state(
            job.id, "running", progress_pct=0.1, stage="streaming_upload"
        )

        total_bytes = 0
        try:
            with open(dest_path, "wb") as fdst:
                while True:
                    chunk = await upload_file.read(STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    fdst.write(chunk)

            if total_bytes == 0:
                dest_path.unlink(missing_ok=True)
                raise AppError(
                    code="EMPTY_MEDIA_FILE",
                    message="Uploaded media file is empty (0 bytes).",
                    status_code=400,
                )

            # Metadata inspection
            self.job_orchestrator.transition_job_state(
                job.id, "running", progress_pct=0.4, stage="extracting_metadata"
            )
            probe = probe_media_file(dest_path, ffprobe_path=self.settings.ffprobe_path)

            asset = self.media_service.register_media_asset(
                project_id=project_id,
                original_filename=original_filename,
                storage_path=str(dest_path),
                is_external=False,
                media_type=probe.media_type,
                file_size_bytes=total_bytes,
                duration_seconds=probe.duration_seconds,
                width=probe.width,
                height=probe.height,
                fps=probe.fps,
                video_codec=probe.video_codec,
                audio_codec=probe.audio_codec,
                metadata=probe.raw_metadata,
                metadata_status="extracted",
            )

            # Thumbnail
            if generate_thumbnail_now and probe.media_type in {"video", "image", "audio"}:
                self.job_orchestrator.transition_job_state(
                    job.id, "running", progress_pct=0.7, stage="generating_thumbnail"
                )
                thumb_dest = self.storage.thumbnails / f"{asset.id}.jpg"
                thumb_res = generate_thumbnail(
                    source_path=dest_path,
                    output_path=thumb_dest,
                    media_type=probe.media_type,
                    duration=probe.duration_seconds,
                    ffmpeg_path=self.settings.ffmpeg_path,
                )
                if thumb_res:
                    self.media_service.update_media_metadata(
                        project_id=project_id,
                        asset_id=asset.id,
                        updates={"thumbnail_reference_path": str(thumb_res)},
                    )

            # Proxy
            if generate_proxy_now and probe.media_type == "video":
                self.job_orchestrator.transition_job_state(
                    job.id, "running", progress_pct=0.85, stage="generating_proxy"
                )
                proxy_dest = self.storage.proxies / f"{asset.id}_proxy_{proxy_profile}.mp4"
                self.media_service.update_media_metadata(
                    project_id=project_id,
                    asset_id=asset.id,
                    updates={"proxy_status": "generating"},
                )
                try:
                    proxy_res = generate_proxy(
                        source_path=dest_path,
                        output_path=proxy_dest,
                        profile=proxy_profile,
                        max_threads=self.settings.ffmpeg_threads,
                        ffmpeg_path=self.settings.ffmpeg_path,
                    )
                    self.media_service.update_media_metadata(
                        project_id=project_id,
                        asset_id=asset.id,
                        updates={
                            "proxy_reference_path": str(proxy_res),
                            "proxy_status": "ready",
                        },
                    )
                except Exception as proxy_err:
                    logger.warning("Optional proxy generation failed for uploaded %s: %s", asset.id, proxy_err)
                    self.media_service.update_media_metadata(
                        project_id=project_id,
                        asset_id=asset.id,
                        updates={"proxy_status": "failed"},
                    )

            self.job_orchestrator.transition_job_state(
                job.id,
                "completed",
                progress_pct=1.0,
                stage="completed",
                result_metadata={"asset_id": asset.id, "bytes": total_bytes},
            )
            return self.media_service.get_media_asset(project_id, asset.id)

        except Exception as exc:
            dest_path.unlink(missing_ok=True)
            self.job_orchestrator.transition_job_state(
                job.id, "failed", error_message=str(exc), stage="failed"
            )
            raise

    def generate_proxy_for_asset(
        self,
        project_id: str,
        asset_id: str,
        profile: str = "480p",
    ) -> MediaAssetRecord:
        """Trigger proxy generation for an existing video asset."""
        asset = self.media_service.get_media_asset(project_id, asset_id)
        if asset.media_type != "video":
            raise AppError(
                code="INVALID_MEDIA_TYPE",
                message=f"Proxy generation is only supported for video assets, but asset '{asset_id}' is '{asset.media_type}'.",
                status_code=400,
            )

        src = Path(asset.storage_path).expanduser().resolve(strict=False)
        if not src.is_file():
            self.media_service.mark_missing(project_id, asset_id)
            raise AppError(
                code="SOURCE_MEDIA_MISSING",
                message=f"Source media file '{src}' is missing. Relink the asset before creating a proxy.",
                status_code=400,
            )

        job = self.job_orchestrator.create_job(
            job_type="proxy_generation",
            project_id=project_id,
            input_config={"asset_id": asset_id, "profile": profile},
        )
        self.job_orchestrator.transition_job_state(
            job.id, "running", progress_pct=0.1, stage="transcoding_proxy"
        )
        self.media_service.update_media_metadata(
            project_id=project_id,
            asset_id=asset_id,
            updates={"proxy_status": "generating"},
        )

        try:
            proxy_dest = self.storage.proxies / f"{asset.id}_proxy_{profile}.mp4"
            proxy_res = generate_proxy(
                source_path=src,
                output_path=proxy_dest,
                profile=profile,
                max_threads=self.settings.ffmpeg_threads,
                ffmpeg_path=self.settings.ffmpeg_path,
            )
            self.media_service.update_media_metadata(
                project_id=project_id,
                asset_id=asset_id,
                updates={
                    "proxy_reference_path": str(proxy_res),
                    "proxy_status": "ready",
                },
            )
            self.job_orchestrator.transition_job_state(
                job.id,
                "completed",
                progress_pct=1.0,
                stage="completed",
                result_metadata={"proxy_path": str(proxy_res)},
            )
            return self.media_service.get_media_asset(project_id, asset_id)
        except Exception as exc:
            self.media_service.update_media_metadata(
                project_id=project_id,
                asset_id=asset_id,
                updates={"proxy_status": "failed"},
            )
            self.job_orchestrator.transition_job_state(
                job.id, "failed", error_message=str(exc), stage="failed"
            )
            raise

    def regenerate_thumbnail_for_asset(
        self,
        project_id: str,
        asset_id: str,
    ) -> MediaAssetRecord:
        """Regenerate thumbnail for an existing media asset."""
        asset = self.media_service.get_media_asset(project_id, asset_id)
        src = Path(asset.storage_path).expanduser().resolve(strict=False)
        if not src.is_file():
            self.media_service.mark_missing(project_id, asset_id)
            raise AppError(
                code="SOURCE_MEDIA_MISSING",
                message=f"Source media file '{src}' is missing. Relink the asset first.",
                status_code=400,
            )

        job = self.job_orchestrator.create_job(
            job_type="thumbnail_generation",
            project_id=project_id,
            input_config={"asset_id": asset_id},
        )
        self.job_orchestrator.transition_job_state(
            job.id, "running", progress_pct=0.2, stage="rendering_thumbnail"
        )

        try:
            thumb_dest = self.storage.thumbnails / f"{asset.id}.jpg"
            thumb_res = generate_thumbnail(
                source_path=src,
                output_path=thumb_dest,
                media_type=asset.media_type,
                duration=asset.duration_seconds,
                ffmpeg_path=self.settings.ffmpeg_path,
            )
            if thumb_res:
                self.media_service.update_media_metadata(
                    project_id=project_id,
                    asset_id=asset_id,
                    updates={"thumbnail_reference_path": str(thumb_res)},
                )
                self.job_orchestrator.transition_job_state(
                    job.id, "completed", progress_pct=1.0, stage="completed"
                )
            else:
                self.job_orchestrator.transition_job_state(
                    job.id, "completed", progress_pct=1.0, stage="no_artwork_available"
                )
            return self.media_service.get_media_asset(project_id, asset_id)
        except Exception as exc:
            self.job_orchestrator.transition_job_state(
                job.id, "failed", error_message=str(exc), stage="failed"
            )
            raise

    def delete_media_asset(
        self,
        project_id: str,
        asset_id: str,
        delete_source_file: bool = False,
    ) -> None:
        """
        Safely delete media asset record and generated derivative files (proxy, thumbnail).
        Only deletes source file on disk if managed (never deletes external referenced files).
        """
        asset = self.media_service.get_media_asset(project_id, asset_id)

        # Remove generated proxy file
        if asset.proxy_reference_path:
            p = Path(asset.proxy_reference_path)
            if p.exists() and is_path_confined(p, self.storage.proxies):
                p.unlink(missing_ok=True)

        # Remove generated thumbnail file
        if asset.thumbnail_reference_path:
            t = Path(asset.thumbnail_reference_path)
            if t.exists() and is_path_confined(t, self.storage.thumbnails):
                t.unlink(missing_ok=True)

        # Optionally delete managed source file
        if delete_source_file:
            if asset.is_external:
                raise AppError(
                    code="EXTERNAL_FILE_PROTECTED",
                    message="External referenced files cannot be deleted from disk by ZezEdit. Only the project reference was removed.",
                    status_code=400,
                )
            src = Path(asset.storage_path)
            if src.exists() and is_path_confined(src, self.storage.media):
                src.unlink(missing_ok=True)

        self.media_service.delete_media_asset(project_id, asset_id)

    def get_project_media_stats(self, project_id: str) -> MediaStorageStatsResponse:
        """Calculate media storage metrics for a project."""
        assets = self.media_service.list_media_assets(project_id)

        total_bytes = 0
        proxy_bytes = 0
        thumb_bytes = 0
        managed_count = 0
        external_count = 0

        for a in assets:
            total_bytes += a.file_size_bytes or 0
            if a.is_external:
                external_count += 1
            else:
                managed_count += 1

            if a.proxy_reference_path:
                p = Path(a.proxy_reference_path)
                if p.is_file():
                    proxy_bytes += p.stat().st_size

            if a.thumbnail_reference_path:
                t = Path(a.thumbnail_reference_path)
                if t.is_file():
                    thumb_bytes += t.stat().st_size

        return MediaStorageStatsResponse(
            project_id=project_id,
            total_media_count=len(assets),
            total_media_bytes=total_bytes,
            total_proxy_bytes=proxy_bytes,
            total_thumbnail_bytes=thumb_bytes,
            managed_files_count=managed_count,
            external_files_count=external_count,
        )

    def _check_disk_space(self, required_bytes: int) -> None:
        """Verify storage disk has sufficient space before copying or downloading."""
        try:
            usage = shutil.disk_usage(self.storage.root)
            if usage.free < (required_bytes + MIN_FREE_SPACE_BYTES):
                raise AppError(
                    code="INSUFFICIENT_STORAGE",
                    message=f"Insufficient disk space on {self.storage.root}. Required: {required_bytes // (1024*1024)} MB, Free: {usage.free // (1024*1024)} MB.",
                    status_code=507,
                )
        except OSError:
            pass  # Non-blocking if stat fails on certain virtual drives
