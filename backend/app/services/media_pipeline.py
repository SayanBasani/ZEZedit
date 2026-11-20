"""End-to-end media ingestion, import, proxy, and thumbnail pipeline coordinator."""

import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
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

import asyncio
import hashlib

logger = logging.getLogger("zezedit.media_pipeline")

STREAM_CHUNK_SIZE = 1024 * 1024  # 1 MB chunk for streaming to prevent high RAM consumption
MIN_FREE_SPACE_BYTES = 100 * 1024 * 1024  # 100 MB safety headroom

_UPLOAD_SEMAPHORE: Optional[asyncio.Semaphore] = None


def _get_upload_semaphore(max_concurrent: int) -> asyncio.Semaphore:
    """Return or initialize process-wide concurrency semaphore for heavy uploads."""
    global _UPLOAD_SEMAPHORE
    if _UPLOAD_SEMAPHORE is None:
        _UPLOAD_SEMAPHORE = asyncio.Semaphore(max_concurrent)
    return _UPLOAD_SEMAPHORE


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

    def check_disk_space(self, required_bytes: int = 0) -> None:
        """Verify storage root has sufficient free disk space including safety margin."""
        try:
            usage = shutil.disk_usage(self.storage.root)
            min_free = getattr(self.settings, "min_disk_free_bytes", MIN_FREE_SPACE_BYTES)
            if usage.free < (required_bytes + min_free):
                raise AppError(
                    code="INSUFFICIENT_STORAGE",
                    message=(
                        f"Insufficient disk space on {self.storage.root}. "
                        f"Available: {usage.free / (1024 * 1024):.1f} MB, "
                        f"required: {(required_bytes + min_free) / (1024 * 1024):.1f} MB."
                    ),
                    status_code=507,
                )
        except OSError as err:
            logger.warning("Unable to verify disk usage: %s", err)

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

            # Streaming SHA-256 calculation in bounded chunks
            hasher = hashlib.sha256()
            with open(effective_path, "rb") as f:
                while chunk := f.read(STREAM_CHUNK_SIZE):
                    hasher.update(chunk)
            local_sha256 = hasher.hexdigest()

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
                sha256=local_sha256,
                integrity_status="verified",
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
        expected_size: Optional[int] = None,
        expected_sha256: Optional[str] = None,
        attempt_id: Optional[str] = None,
        test_fail_registration: bool = False,
        test_fail_publication: bool = False,
        require_video: bool = False,
    ) -> MediaAssetRecord:
        """
        Stream an uploaded media file in bounded chunks to managed storage.
        Verifies checksum, byte counts, and media validity before atomic publication.
        """
        project = self.project_service.get_project(project_id)
        raw_filename = upload_file.filename or "uploaded_media"

        # Security validation: reject path traversal sequences
        if ".." in raw_filename or raw_filename.startswith(("/", "\\")):
            raise AppError(
                code="PATH_TRAVERSAL_DETECTED",
                message=f"Path traversal sequence detected in filename: '{raw_filename}'",
                status_code=400,
            )

        safe_filename = Path(raw_filename).name.strip()
        if not safe_filename:
            safe_filename = "uploaded_media"

        proj_media_dir = self.storage.media / project.storage_subdir
        proj_media_dir.mkdir(parents=True, exist_ok=True)
        # Collision handling: unique 8-character prefix guarantees distinct physical path per upload
        clean_name = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
        dest_path = (proj_media_dir / clean_name).resolve()
        if not dest_path.is_relative_to(proj_media_dir.resolve()):
            raise AppError(
                code="PATH_TRAVERSAL_DETECTED",
                message="Target destination escapes media directory.",
                status_code=400,
            )

        # Quota enforcement (P1.9): reject early if declared size breaches quota
        if expected_size and expected_size > 0:
            from app.services.storage import StorageService
            storage_svc = StorageService(self.settings)
            allowed, quota_err = storage_svc.check_quota_for_operation("upload", incoming_bytes=expected_size)
            if not allowed and quota_err:
                raise AppError(code="QUOTA_EXCEEDED", message=quota_err, status_code=507)

        # Enforce bounded concurrent heavy uploads
        max_conc = getattr(self.settings, "max_concurrent_uploads", 2)
        sem = _get_upload_semaphore(max_conc)
        try:
            await asyncio.wait_for(sem.acquire(), timeout=0.05)
        except (asyncio.TimeoutError, TimeoutError):
            raise AppError(
                code="TOO_MANY_CONCURRENT_UPLOADS",
                message=f"Server is currently handling the maximum of {max_conc} concurrent uploads. Please retry when existing uploads complete.",
                status_code=429,
            )

        acquired = True
        part_path = dest_path.with_suffix(dest_path.suffix + ".uploading")
        part_created = False
        dest_created = False
        total_bytes = 0
        job = None

        try:
            job = self.job_orchestrator.create_job(
                job_type="media_import",
                project_id=project_id,
                input_config={
                    "uploaded_filename": safe_filename,
                    "destination": str(dest_path),
                    "expected_size": expected_size,
                    "expected_sha256": expected_sha256,
                    "attempt_id": attempt_id,
                },
            )
            self.job_orchestrator.transition_job_state(
                job.id, "running", progress_pct=0.1, stage="streaming_upload"
            )
            # Pre-flight checks if size is already hinted
            file_size_hint = getattr(upload_file, "size", None) or expected_size
            max_size = getattr(self.settings, "max_upload_size_bytes", 2500 * 1024 * 1024)
            if file_size_hint and file_size_hint > 0:
                if file_size_hint > max_size:
                    raise AppError(
                        code="REQUEST_ENTITY_TOO_LARGE",
                        message=f"Upload size ({file_size_hint / (1024 * 1024):.1f} MB) exceeds maximum permitted limit of {max_size / (1024 * 1024):.1f} MB.",
                        status_code=413,
                    )
                self.check_disk_space(file_size_hint)

            chunk_size = getattr(self.settings, "upload_chunk_size_bytes", STREAM_CHUNK_SIZE)
            hasher = hashlib.sha256()
            last_space_check = 0

            with open(part_path, "wb") as fdst:
                part_created = True
                while True:
                    chunk = await upload_file.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_size:
                        raise AppError(
                            code="REQUEST_ENTITY_TOO_LARGE",
                            message=f"Upload size exceeds maximum permitted limit of {max_size / (1024 * 1024):.1f} MB.",
                            status_code=413,
                        )
                    if expected_size is not None and expected_size > 0 and total_bytes > expected_size:
                        raise AppError(
                            code="BYTE_COUNT_MISMATCH",
                            message=f"Received byte count ({total_bytes}) exceeds declared expected size ({expected_size}).",
                            status_code=400,
                        )
                    if total_bytes - last_space_check >= 50 * 1024 * 1024:
                        self.check_disk_space(chunk_size)
                        last_space_check = total_bytes
                    fdst.write(chunk)
                    hasher.update(chunk)

            if total_bytes == 0:
                part_path.unlink(missing_ok=True)
                part_created = False
                raise AppError(
                    code="EMPTY_MEDIA_FILE",
                    message="Uploaded media file is empty (0 bytes).",
                    status_code=400,
                )

            # Byte-count and file-size verification on temporary staging file
            part_stat = part_path.stat().st_size
            if part_stat != total_bytes:
                part_path.unlink(missing_ok=True)
                part_created = False
                raise AppError(
                    code="STORAGE_WRITE_MISMATCH",
                    message=f"Temporary staging file size ({part_stat} bytes) does not match received byte stream ({total_bytes} bytes).",
                    status_code=500,
                )

            if expected_size is not None and expected_size > 0:
                if total_bytes != expected_size:
                    part_path.unlink(missing_ok=True)
                    part_created = False
                    raise AppError(
                        code="BYTE_COUNT_MISMATCH",
                        message=f"Received byte count ({total_bytes}) does not match expected size ({expected_size}).",
                        status_code=400,
                    )

            computed_sha256 = hasher.hexdigest()

            # Client expected SHA-256 verification
            if expected_sha256 and expected_sha256.strip():
                if computed_sha256.lower() != expected_sha256.strip().lower():
                    part_path.unlink(missing_ok=True)
                    part_created = False
                    raise AppError(
                        code="CHECKSUM_MISMATCH",
                        message=f"Computed SHA-256 checksum '{computed_sha256}' does not match expected checksum '{expected_sha256.strip().lower()}'.",
                        status_code=400,
                    )

            # Validate media while still in temporary staging (.uploading) prior to publication
            self.job_orchestrator.transition_job_state(
                job.id, "running", progress_pct=0.4, stage="validating_media"
            )
            probe = probe_media_file(part_path, ffprobe_path=self.settings.ffprobe_path)

            if probe.media_type == "unknown":
                part_path.unlink(missing_ok=True)
                part_created = False
                raise AppError(
                    code="UNSUPPORTED_MEDIA_TYPE",
                    message=f"File '{safe_filename}' is not a recognized video, audio, or image media file.",
                    status_code=400,
                )

            # Minimum video criteria: must contain a usable video stream
            video_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".ts", ".mts"}
            has_video_ext = Path(safe_filename).suffix.lower() in video_exts
            has_video_stream = (
                probe.video_stream_count > 0
                or (probe.media_type == "video" and (probe.width or 0) > 0 and (probe.height or 0) > 0)
            )
            if (require_video or has_video_ext) and (probe.media_type == "audio" or not has_video_stream):
                part_path.unlink(missing_ok=True)
                part_created = False
                raise AppError(
                    code="NO_VIDEO_STREAM",
                    message=f"File '{safe_filename}' does not contain a valid video stream. Audio-only media cannot be accepted as video assets.",
                    status_code=400,
                )

            if probe.media_type == "video":
                if probe.width is None or probe.height is None or probe.width <= 0 or probe.height <= 0:
                    part_path.unlink(missing_ok=True)
                    part_created = False
                    raise AppError(
                        code="INVALID_VIDEO_DIMENSIONS",
                        message=f"File '{safe_filename}' has invalid video dimensions ({probe.width}x{probe.height}).",
                        status_code=400,
                    )

            # Controlled test injection for atomic publication failure
            if test_fail_publication:
                part_path.unlink(missing_ok=True)
                part_created = False
                raise AppError(
                    code="PUBLICATION_FAILED",
                    message="Simulated filesystem failure during atomic file publication.",
                    status_code=500,
                )

            # Check for existing stored media file with matching SHA-256 (P1.8 Content-based Deduplication)
            is_deduplicated = False
            existing_stored = self.media_service.get_stored_media_file_by_sha256(computed_sha256)
            reusable_path = None
            if existing_stored:
                cand_path = Path(existing_stored.storage_path)
                if not cand_path.is_file():
                    cand_path = self.storage.media / existing_stored.storage_path
                # Verify physical existence and size matches
                if cand_path.is_file() and cand_path.stat().st_size == total_bytes:
                    reusable_path = cand_path

            if reusable_path:
                # Deduplication hit: reuse existing physical asset, discard staged uploading file
                is_deduplicated = True
                part_path.unlink(missing_ok=True)
                part_created = False
                final_dest_path = reusable_path
                stored_file = existing_stored
                logger.info(
                    "Deduplication hit for '%s' (SHA-256: %s): reusing existing physical asset '%s'",
                    safe_filename,
                    computed_sha256[:12],
                    final_dest_path,
                )
            else:
                # Atomic publication: rename validated .uploading part file to final dest_path
                os.replace(part_path, dest_path)
                part_created = False
                dest_created = True

                # Verify physical finalized file size matches received byte count
                final_stat = dest_path.stat().st_size
                if final_stat != total_bytes:
                    dest_path.unlink(missing_ok=True)
                    dest_created = False
                    raise AppError(
                        code="STORAGE_WRITE_MISMATCH",
                        message=f"Published file size ({final_stat} bytes) does not match verified received bytes ({total_bytes} bytes).",
                        status_code=500,
                    )
                final_dest_path = dest_path
                stored_file = self.media_service.register_or_update_stored_file(
                    sha256=computed_sha256,
                    storage_path=str(dest_path),
                    file_size_bytes=total_bytes,
                    mime_type=getattr(upload_file, "content_type", None) or f"{probe.media_type}/{probe.container_format}",
                    container_format=probe.container_format,
                    duration_seconds=probe.duration_seconds,
                    width=probe.width,
                    height=probe.height,
                    fps=probe.fps,
                    video_codec=probe.video_codec,
                    audio_codec=probe.audio_codec,
                    is_external=False,
                )
                # Concurrency check: If another concurrent upload registered first and stored_file path differs
                if stored_file.storage_path != str(dest_path):
                    winner_path = Path(stored_file.storage_path)
                    if winner_path.is_file():
                        dest_path.unlink(missing_ok=True)
                        dest_created = False
                        final_dest_path = winner_path
                        is_deduplicated = True

            # Integrity contract assembly
            now_iso = datetime.now(timezone.utc).isoformat()
            integrity_details = {
                "original_filename": safe_filename,
                "expected_size_bytes": expected_size,
                "received_bytes": total_bytes,
                "final_size_bytes": total_bytes,
                "sha256": computed_sha256,
                "container_format": probe.container_format,
                "video_codec": probe.video_codec,
                "audio_codec": probe.audio_codec,
                "video_stream_count": probe.video_stream_count,
                "audio_stream_count": probe.audio_stream_count,
                "subtitle_stream_count": probe.subtitle_stream_count,
                "width": probe.width,
                "height": probe.height,
                "duration_seconds": probe.duration_seconds,
                "validation_result": "valid",
                "integrity_status": "verified",
                "upload_attempt_id": attempt_id,
                "verified_at": now_iso,
                "deduplicated": is_deduplicated,
                "stored_file_id": stored_file.id,
            }

            probe.raw_metadata["sha256"] = computed_sha256
            probe.raw_metadata["integrity_details"] = integrity_details

            # Controlled test injection for database registration failure
            if test_fail_registration:
                if dest_created:
                    dest_path.unlink(missing_ok=True)
                    dest_created = False
                raise AppError(
                    code="DATABASE_REGISTRATION_FAILED",
                    message="Simulated database failure during media registration.",
                    status_code=500,
                )

            asset = self.media_service.register_media_asset(
                project_id=project_id,
                original_filename=safe_filename,
                storage_path=str(final_dest_path),
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
                sha256=computed_sha256,
                integrity_status="verified",
                upload_attempt_id=attempt_id,
                integrity_details=integrity_details,
                stored_file_id=stored_file.id,
            )

            # Thumbnail
            if generate_thumbnail_now and probe.media_type in {"video", "image", "audio"}:
                self.job_orchestrator.transition_job_state(
                    job.id, "running", progress_pct=0.7, stage="generating_thumbnail"
                )
                thumb_dest = self.storage.thumbnails / f"{asset.id}.jpg"
                thumb_res = generate_thumbnail(
                    source_path=final_dest_path,
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
                        source_path=final_dest_path,
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
                result_metadata={"asset_id": asset.id, "bytes": total_bytes, "sha256": computed_sha256},
            )
            rec = self.media_service.get_media_asset(project_id, asset.id)
            rec.is_deduplicated = is_deduplicated
            return rec

        except (Exception, asyncio.CancelledError) as exc:
            if part_created:
                try:
                    part_path.unlink(missing_ok=True)
                except Exception:
                    pass
            if dest_created:
                try:
                    dest_path.unlink(missing_ok=True)
                except Exception:
                    pass
            if job is not None:
                self.job_orchestrator.transition_job_state(
                    job.id, "failed", error_message=str(exc), stage="failed"
                )
            raise
        finally:
            if acquired:
                sem.release()
            try:
                await upload_file.close()
            except Exception:
                pass

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
            src = (self.storage.media / asset.storage_path).resolve(strict=False)
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

    async def relink_uploaded_media(
        self,
        project_id: str,
        asset_id: str,
        upload_file: UploadFile,
        force: bool = False,
        expected_sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Safely stream uploaded replacement video into managed staging,
        validate candidate integrity/metadata against original, and atomically relink.
        """
        asset = self.media_service.get_media_asset(project_id, asset_id)
        raw_filename = upload_file.filename or "replacement_video"

        # Security validation: reject path traversal sequences
        if ".." in raw_filename or raw_filename.startswith(("/", "\\")):
            raise AppError(
                code="PATH_TRAVERSAL_DETECTED",
                message=f"Path traversal sequence detected in filename: '{raw_filename}'",
                status_code=400,
            )

        safe_filename = Path(raw_filename).name.strip()
        if not safe_filename:
            safe_filename = "replacement_video"

        # Staging path
        staging_dir = self.storage.temp
        staging_dir.mkdir(parents=True, exist_ok=True)
        unique_prefix = uuid.uuid4().hex[:8]
        part_path = staging_dir / f"relink_{asset_id}_{unique_prefix}.uploading"
        verified_path = staging_dir / f"relink_{asset_id}_{unique_prefix}{Path(safe_filename).suffix}"

        hasher = hashlib.sha256()
        total_bytes = 0
        part_created = False

        try:
            with open(part_path, "wb") as dst:
                part_created = True
                while chunk := await upload_file.read(STREAM_CHUNK_SIZE):
                    dst.write(chunk)
                    hasher.update(chunk)
                    total_bytes += len(chunk)

            if total_bytes == 0:
                raise AppError(
                    code="EMPTY_UPLOAD_STREAM",
                    message="Uploaded replacement file contains zero bytes.",
                    status_code=400,
                )

            candidate_sha = hasher.hexdigest()
            if expected_sha256 and expected_sha256.lower() != candidate_sha.lower():
                raise AppError(
                    code="CHECKSUM_MISMATCH",
                    message=f"Uploaded replacement checksum '{candidate_sha}' does not match expected '{expected_sha256}'.",
                    status_code=400,
                )

            # Atomic move from .uploading to staging file
            part_path.rename(verified_path)
            part_created = False

            # Inspect candidate staged file
            inspection = self.media_service.inspect_relink_candidate(
                project_id=asset.project_id,
                asset_id=asset_id,
                new_storage_path=str(verified_path),
            )

            if inspection["match_status"] == "mismatch" and not force:
                if verified_path.exists():
                    try:
                        verified_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                raise AppError(
                    code="RELINK_MISMATCH",
                    message=f"Replacement video has discrepancies ({'; '.join(inspection['warnings'])}). Explicit confirmation (force=true) is required.",
                    status_code=400,
                    details=inspection["comparison"],
                )

            # Move verified file to permanent managed storage path
            proj_media_dir = self.storage.media / (asset.project_id if asset.project_id != "all" else "default")
            proj_media_dir.mkdir(parents=True, exist_ok=True)
            final_media_path = (proj_media_dir / f"relinked_{unique_prefix}_{safe_filename}").resolve()
            shutil.move(str(verified_path), str(final_media_path))

            # Atomically relink asset
            relinked_record = self.media_service.relink_media(
                project_id=asset.project_id,
                asset_id=asset_id,
                new_storage_path=str(final_media_path),
                force=force,
            )

            return {
                "asset": relinked_record,
                "match_status": inspection["match_status"],
                "warnings": inspection["warnings"],
                "comparison": inspection["comparison"],
                "relinked_at": relinked_record.relinked_at,
            }

        finally:
            if part_created and part_path.exists():
                try:
                    part_path.unlink(missing_ok=True)
                except Exception:
                    pass
            if verified_path.exists():
                try:
                    verified_path.unlink(missing_ok=True)
                except Exception:
                    pass

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
