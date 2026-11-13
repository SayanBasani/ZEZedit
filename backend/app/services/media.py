"""Media metadata domain service managing media asset records, availability states, and relinking."""

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.models.entities import MediaAssetRecord
from app.services.media_probe import probe_media_file

logger = logging.getLogger("zezedit.media_service")


class MediaService:
    """Manages media metadata records, missing media detection, and relinking."""

    def __init__(self, settings: Settings, db_path: Path) -> None:
        self.settings = settings
        self.db_path = db_path

    def register_media_asset(
        self,
        project_id: str,
        original_filename: str,
        storage_path: str,
        is_external: bool = False,
        media_type: str = "video",
        file_size_bytes: int = 0,
        mime_type: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        video_codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        metadata: Optional[dict] = None,
        thumbnail_reference_path: Optional[str] = None,
        proxy_reference_path: Optional[str] = None,
        proxy_status: str = "none",
        metadata_status: str = "unextracted",
    ) -> MediaAssetRecord:
        """Register a media asset record associated with a project."""
        asset_id = f"med_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata or {})

        # Verify project exists
        with sqlite_session(self.db_path) as conn:
            proj = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not proj:
                raise AppError(
                    code="PROJECT_NOT_FOUND",
                    message=f"Project with ID '{project_id}' does not exist.",
                    status_code=404,
                )

            conn.execute(
                """
                INSERT INTO media_assets (
                    id, project_id, original_filename, storage_path, is_external,
                    media_type, file_size_bytes, mime_type, duration_seconds,
                    width, height, fps, video_codec, audio_codec, availability_status,
                    proxy_reference_path, thumbnail_reference_path, metadata_status,
                    metadata_json, created_at, updated_at, proxy_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'present', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    project_id,
                    original_filename,
                    storage_path,
                    1 if is_external else 0,
                    media_type,
                    file_size_bytes,
                    mime_type,
                    duration_seconds,
                    width,
                    height,
                    fps,
                    video_codec,
                    audio_codec,
                    proxy_reference_path,
                    thumbnail_reference_path,
                    metadata_status,
                    meta_json,
                    now,
                    now,
                    proxy_status,
                ),
            )
            # Record project activity event
            event_id = f"evt_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO project_events (id, project_id, event_type, event_summary, payload_json, created_at)
                VALUES (?, ?, 'media_registered', ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    f"Media asset '{original_filename}' registered",
                    json.dumps({"asset_id": asset_id, "path": storage_path}),
                    now,
                ),
            )

        return self.get_media_asset(project_id, asset_id)

    def list_media_assets(
        self,
        project_id: Optional[str] = None,
        availability: Optional[str] = None,
        media_type: Optional[str] = None,
        proxy_status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[MediaAssetRecord]:
        """List all media assets for a project (or across all projects if project_id is None or 'all')."""
        if project_id and project_id != "all":
            query = "SELECT * FROM media_assets WHERE project_id = ?"
            params: list = [project_id]
        else:
            query = "SELECT * FROM media_assets WHERE 1=1"
            params = []

        if availability:
            query += " AND availability_status = ?"
            params.append(availability)
        if media_type:
            query += " AND media_type = ?"
            params.append(media_type)
        if proxy_status:
            query += " AND proxy_status = ?"
            params.append(proxy_status)
        if search and search.strip():
            query += " AND original_filename LIKE ?"
            params.append(f"%{search.strip()}%")

        query += " ORDER BY created_at DESC"

        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_record(row) for row in rows]

    def get_media_asset(self, project_id: Optional[str], asset_id: str) -> MediaAssetRecord:
        """Fetch media asset details, either within a specific project or by asset ID alone."""
        with sqlite_session(self.db_path) as conn:
            if project_id and project_id != "all":
                row = conn.execute(
                    "SELECT * FROM media_assets WHERE project_id = ? AND id = ?",
                    (project_id, asset_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM media_assets WHERE id = ?",
                    (asset_id,),
                ).fetchone()

            if not row:
                raise AppError(
                    code="MEDIA_ASSET_NOT_FOUND",
                    message=f"Media asset with ID '{asset_id}' not found.",
                    status_code=404,
                )
            return self._row_to_record(row)

    def update_media_metadata(
        self,
        project_id: str,
        asset_id: str,
        updates: dict,
    ) -> MediaAssetRecord:
        """Update extracted technical metadata on an asset."""
        existing = self.get_media_asset(project_id, asset_id)
        now = datetime.now(timezone.utc).isoformat()

        # Merge fields
        meta_dict = existing.metadata.copy()
        if "metadata" in updates and updates["metadata"] is not None:
            meta_dict.update(updates["metadata"])

        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                UPDATE media_assets
                SET original_filename = COALESCE(?, original_filename),
                    media_type = COALESCE(?, media_type),
                    duration_seconds = COALESCE(?, duration_seconds),
                    width = COALESCE(?, width),
                    height = COALESCE(?, height),
                    fps = COALESCE(?, fps),
                    video_codec = COALESCE(?, video_codec),
                    audio_codec = COALESCE(?, audio_codec),
                    metadata_status = COALESCE(?, metadata_status),
                    proxy_status = COALESCE(?, proxy_status),
                    proxy_reference_path = COALESCE(?, proxy_reference_path),
                    thumbnail_reference_path = COALESCE(?, thumbnail_reference_path),
                    metadata_json = ?,
                    updated_at = ?
                WHERE project_id = ? AND id = ?
                """,
                (
                    updates.get("original_filename"),
                    updates.get("media_type"),
                    updates.get("duration_seconds"),
                    updates.get("width"),
                    updates.get("height"),
                    updates.get("fps"),
                    updates.get("video_codec"),
                    updates.get("audio_codec"),
                    updates.get("metadata_status"),
                    updates.get("proxy_status"),
                    updates.get("proxy_reference_path"),
                    updates.get("thumbnail_reference_path"),
                    json.dumps(meta_dict),
                    now,
                    project_id,
                    asset_id,
                ),
            )

        return self.get_media_asset(project_id, asset_id)

    def delete_media_asset(
        self,
        project_id: str,
        asset_id: str,
        delete_source: bool = False,
    ) -> None:
        """Unregister media asset record and reclaim its managed storage files."""
        asset = self.get_media_asset(project_id, asset_id)
        now = datetime.now(timezone.utc).isoformat()
        layout = StorageLayout.from_root(self.settings.storage_root)

        # 1. Cancel active jobs associated with this asset
        try:
            with sqlite_session(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'cancelled', current_stage = 'cancelled_by_media_deletion', updated_at = ?
                    WHERE status IN ('running', 'queued') AND (media_asset_id = ? OR input_config_json LIKE ?)
                    """,
                    (now, asset_id, f"%{asset_id}%"),
                )
        except Exception as e:
            logger.warning("Could not cancel jobs for asset %s: %s", asset_id, e)

        # 2. Reclaim managed disk files (only if within storage_root!)
        try:
            # Managed source video (if not external original)
            if not asset.is_external and asset.storage_path:
                src_file = layout.media / asset.storage_path
                if src_file.exists() and src_file.is_file():
                    src_file.unlink(missing_ok=True)

            # Proxies matching asset_id
            for p in layout.proxies.glob(f"{asset_id}*"):
                p.unlink(missing_ok=True)
            # Thumbnails matching asset_id
            for t in layout.thumbnails.glob(f"{asset_id}*"):
                t.unlink(missing_ok=True)
            # Analysis directory for asset
            analysis_dir = layout.analysis / asset_id
            if analysis_dir.exists():
                shutil.rmtree(analysis_dir, ignore_errors=True)
        except Exception as file_err:
            logger.warning("Error deleting managed media files for %s: %s", asset_id, file_err)

        # 3. Delete database records across related tables
        with sqlite_session(self.db_path) as conn:
            for tbl in (
                "candidate_clip_edits",
                "media_generated_clips_history",
                "media_highlight_candidates",
                "candidate_generation_runs",
                "audio_analysis",
                "visual_observations",
                "sampled_frames",
                "video_scenes",
                "speech_turns",
                "transcript_segments",
                "analysis_runs",
                "shorts_candidates",
            ):
                try:
                    conn.execute(f"DELETE FROM {tbl} WHERE media_asset_id = ?", (asset_id,))
                except Exception:
                    pass

            conn.execute("DELETE FROM media_assets WHERE project_id = ? AND id = ?", (project_id, asset_id))
            event_id = f"evt_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO project_events (id, project_id, event_type, event_summary, payload_json, created_at)
                VALUES (?, ?, 'media_deleted', ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    f"Media asset '{asset_id}' removed and storage reclaimed",
                    json.dumps({"asset_id": asset_id}),
                    now,
                ),
            )
            # Run checkpoint to reclaim wal pages
            try:
                conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            except Exception:
                pass

    def mark_missing(self, project_id: str, asset_id: str) -> MediaAssetRecord:
        """Mark an external media file as missing without deleting project state."""
        self.get_media_asset(project_id, asset_id)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                "UPDATE media_assets SET availability_status = 'missing', updated_at = ? WHERE id = ?",
                (now, asset_id),
            )
        return self.get_media_asset(project_id, asset_id)

    def check_asset_integrity(self, project_id: str, asset_id: str) -> Dict[str, Any]:
        """Check source media existence, size integrity, and probe readability."""
        asset = self.get_media_asset(project_id, asset_id)
        path = Path(asset.storage_path)
        now = datetime.now(timezone.utc).isoformat()

        exists = path.exists() and path.is_file()
        size_bytes = 0
        size_matches = False
        probe_ok = False
        duration = asset.duration_seconds
        width = asset.width
        height = asset.height
        issues: List[str] = []

        if not exists:
            availability = "missing"
            integrity = "missing"
            issues.append(f"Media file does not exist at '{asset.storage_path}'.")
        else:
            try:
                size_bytes = path.stat().st_size
                if size_bytes == 0:
                    availability = "corrupted"
                    integrity = "corrupted"
                    issues.append("Media file is 0 bytes (empty).")
                else:
                    size_matches = (asset.file_size_bytes == 0) or (abs(size_bytes - asset.file_size_bytes) == 0)
                    if not size_matches:
                        issues.append(
                            f"File size on disk ({size_bytes}B) differs from registered ({asset.file_size_bytes}B)."
                        )

                    # Probe readability with ffprobe
                    try:
                        probe = probe_media_file(path, ffprobe_path=self.settings.ffprobe_path)
                        probe_ok = True
                        duration = probe.duration_seconds
                        width = probe.width
                        height = probe.height
                        availability = "present"
                        integrity = "online"
                    except Exception as probe_err:
                        probe_ok = False
                        availability = "corrupted"
                        integrity = "corrupted"
                        issues.append(f"FFprobe failed to read container or stream headers: {probe_err}")
            except Exception as stat_err:
                availability = "corrupted"
                integrity = "corrupted"
                issues.append(f"Failed to stat media file: {stat_err}")

        # Update database with integrity status
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                UPDATE media_assets
                SET availability_status = ?,
                    integrity_details_json = ?,
                    last_integrity_check = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (availability, json.dumps({"issues": issues, "size_bytes": size_bytes, "probe_ok": probe_ok}), now, now, asset_id),
            )

        return {
            "asset_id": asset.id,
            "project_id": asset.project_id,
            "original_filename": asset.original_filename,
            "storage_path": asset.storage_path,
            "availability_status": availability,
            "integrity_status": integrity,
            "file_exists": exists,
            "file_size_bytes": size_bytes,
            "size_matches": size_matches,
            "probe_ok": probe_ok,
            "duration_seconds": duration,
            "width": width,
            "height": height,
            "issues": issues,
            "checked_at": now,
        }

    def check_project_media_integrity(self, project_id: str) -> Dict[str, Any]:
        """Run batch media integrity verification for all assets in a project."""
        assets = self.list_media_assets(project_id=project_id)
        results = [self.check_asset_integrity(project_id, a.id) for a in assets]
        online = sum(1 for r in results if r["integrity_status"] == "online")
        missing = sum(1 for r in results if r["integrity_status"] == "missing")
        corrupted = sum(1 for r in results if r["integrity_status"] == "corrupted")
        now = datetime.now(timezone.utc).isoformat()

        return {
            "project_id": project_id,
            "total_assets": len(results),
            "online_count": online,
            "missing_count": missing,
            "corrupted_count": corrupted,
            "all_healthy": (missing == 0 and corrupted == 0),
            "assets": results,
            "checked_at": now,
        }

    def inspect_relink_candidate(
        self, project_id: str, asset_id: str, new_storage_path: str
    ) -> Dict[str, Any]:
        """Probe replacement candidate and compare against original media attributes."""
        asset = self.get_media_asset(project_id, asset_id)
        candidate_path = Path(new_storage_path).expanduser().resolve(strict=False)

        if not candidate_path.exists():
            raise AppError(
                code="FILE_NOT_FOUND",
                message=f"Candidate media file '{candidate_path}' does not exist on disk.",
                status_code=400,
            )
        if not candidate_path.is_file():
            raise AppError(
                code="INVALID_FILE",
                message=f"Candidate path '{candidate_path}' is not a regular file.",
                status_code=400,
            )

        probe = None
        warnings: List[str] = []
        try:
            probe = probe_media_file(candidate_path, ffprobe_path=self.settings.ffprobe_path)
        except Exception as probe_err:
            warnings.append(f"Media stream probing notice: {probe_err}")

        dur_diff = 0.0
        if probe:
            if asset.duration_seconds is not None and probe.duration_seconds is not None:
                dur_diff = round(abs(probe.duration_seconds - asset.duration_seconds), 3)
                if dur_diff > 1.0:
                    warnings.append(
                        f"Duration mismatch: Candidate has {probe.duration_seconds:.2f}s, original had {asset.duration_seconds:.2f}s (difference: {dur_diff:.2f}s)."
                    )

            if asset.width and asset.height and probe.width and probe.height:
                if (probe.width, probe.height) != (asset.width, asset.height):
                    warnings.append(
                        f"Resolution mismatch: Candidate is {probe.width}x{probe.height}, original was {asset.width}x{asset.height}."
                    )

        if dur_diff > 1.0:
            match_status = "mismatch"
        elif len(warnings) > 0:
            match_status = "compatible"
        else:
            match_status = "exact"

        comparison = {
            "original_filename": asset.original_filename,
            "original_path": asset.storage_path,
            "candidate_path": str(candidate_path),
            "original_duration": asset.duration_seconds,
            "candidate_duration": probe.duration_seconds if probe else None,
            "duration_diff_seconds": dur_diff,
            "original_resolution": f"{asset.width}x{asset.height}" if asset.width else None,
            "candidate_resolution": f"{probe.width}x{probe.height}" if probe and probe.width else None,
            "original_size_bytes": asset.file_size_bytes,
            "candidate_size_bytes": probe.file_size_bytes if probe else candidate_path.stat().st_size,
            "candidate_video_codec": probe.video_codec if probe else None,
            "candidate_audio_codec": probe.audio_codec if probe else None,
        }

        return {
            "match_status": match_status,
            "warnings": warnings,
            "comparison": comparison,
            "probe": probe,
            "candidate_path": candidate_path,
        }

    def relink_media(
        self, project_id: str, asset_id: str, new_storage_path: str, force: bool = False
    ) -> MediaAssetRecord:
        """Relink an asset to a new filesystem path with comparison and user audit."""
        inspection = self.inspect_relink_candidate(project_id, asset_id, new_storage_path)
        candidate_path = inspection["candidate_path"]
        probe = inspection["probe"]
        warnings = inspection["warnings"]
        match_status = inspection["match_status"]
        comparison = inspection["comparison"]

        now = datetime.now(timezone.utc).isoformat()
        probe_size = probe.file_size_bytes if probe else candidate_path.stat().st_size
        probe_dur = probe.duration_seconds if probe else None
        probe_w = probe.width if probe else None
        probe_h = probe.height if probe else None
        probe_fps = probe.fps if probe else None
        probe_vc = probe.video_codec if probe else None
        probe_ac = probe.audio_codec if probe else None

        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                UPDATE media_assets
                SET storage_path = ?,
                    availability_status = 'present',
                    file_size_bytes = COALESCE(?, file_size_bytes),
                    duration_seconds = COALESCE(?, duration_seconds),
                    width = COALESCE(?, width),
                    height = COALESCE(?, height),
                    fps = COALESCE(?, fps),
                    video_codec = COALESCE(?, video_codec),
                    audio_codec = COALESCE(?, audio_codec),
                    last_integrity_check = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    str(candidate_path),
                    probe_size,
                    probe_dur,
                    probe_w,
                    probe_h,
                    probe_fps,
                    probe_vc,
                    probe_ac,
                    now,
                    now,
                    asset_id,
                ),
            )
            event_id = f"evt_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO project_events (id, project_id, event_type, event_summary, payload_json, created_at)
                VALUES (?, ?, 'media_relinked', ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    f"Media asset '{asset_id}' relinked to '{candidate_path}' (match: {match_status})",
                    json.dumps({
                        "asset_id": asset_id,
                        "new_path": str(candidate_path),
                        "match_status": match_status,
                        "warnings": warnings,
                        "comparison": comparison,
                    }),
                    now,
                ),
            )

        return self.get_media_asset(project_id, asset_id)

    def _row_to_record(self, row) -> MediaAssetRecord:
        keys = row.keys() if hasattr(row, "keys") else []
        return MediaAssetRecord(
            id=row["id"],
            project_id=row["project_id"],
            original_filename=row["original_filename"],
            storage_path=row["storage_path"],
            is_external=bool(row["is_external"]),
            media_type=row["media_type"],
            file_size_bytes=row["file_size_bytes"],
            mime_type=row["mime_type"],
            duration_seconds=row["duration_seconds"],
            width=row["width"],
            height=row["height"],
            fps=row["fps"],
            video_codec=row["video_codec"],
            audio_codec=row["audio_codec"],
            availability_status=row["availability_status"],
            proxy_reference_path=row["proxy_reference_path"],
            thumbnail_reference_path=row["thumbnail_reference_path"],
            proxy_status=row["proxy_status"] if "proxy_status" in keys else "none",
            metadata_status=row["metadata_status"],
            metadata=json.loads(row["metadata_json"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
