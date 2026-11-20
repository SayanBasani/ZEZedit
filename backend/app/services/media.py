"""Media metadata domain service managing media asset records, availability states, and relinking."""

import hashlib
import json
import logging
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.models.entities import MediaAssetRecord, StoredMediaFileRecord
from app.services.media_probe import probe_media_file

logger = logging.getLogger("zezedit.media_service")

SUPPORTED_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v"}


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
        sha256: Optional[str] = None,
        integrity_status: Optional[str] = None,
        upload_attempt_id: Optional[str] = None,
        integrity_details: Optional[dict] = None,
        stored_file_id: Optional[str] = None,
    ) -> MediaAssetRecord:
        """Register a media asset record associated with a project."""
        asset_id = f"med_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata or {})
        integ_json = json.dumps(integrity_details or {}) if integrity_details else None

        # Verify project exists
        with sqlite_session(self.db_path) as conn:
            proj = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not proj:
                raise AppError(
                    code="PROJECT_NOT_FOUND",
                    message=f"Project with ID '{project_id}' does not exist.",
                    status_code=404,
                )

            # If sha256 is present and stored_file_id is not given, register or link stored file
            actual_stored_file_id = stored_file_id
            if sha256 and not actual_stored_file_id:
                smf = self.get_stored_media_file_by_sha256(sha256)
                if not smf:
                    smf = self.register_or_update_stored_file(
                        sha256=sha256,
                        storage_path=storage_path,
                        file_size_bytes=file_size_bytes,
                        mime_type=mime_type,
                        duration_seconds=duration_seconds,
                        width=width,
                        height=height,
                        fps=fps,
                        video_codec=video_codec,
                        audio_codec=audio_codec,
                        is_external=is_external,
                    )
                actual_stored_file_id = smf.id

            cols = [col[1] for col in conn.execute("PRAGMA table_info(media_assets)").fetchall()]
            has_stored_file_col = "stored_file_id" in cols
            if "sha256" in cols and "upload_attempt_id" in cols:
                if has_stored_file_col:
                    conn.execute(
                        """
                        INSERT INTO media_assets (
                            id, project_id, original_filename, storage_path, is_external,
                            media_type, file_size_bytes, mime_type, duration_seconds,
                            width, height, fps, video_codec, audio_codec, availability_status,
                            proxy_reference_path, thumbnail_reference_path, metadata_status,
                            metadata_json, created_at, updated_at, proxy_status,
                            sha256, integrity_status, upload_attempt_id, integrity_details_json, last_integrity_check,
                            stored_file_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'present', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            sha256,
                            integrity_status or "verified",
                            upload_attempt_id,
                            integ_json,
                            now if integrity_status else None,
                            actual_stored_file_id,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO media_assets (
                            id, project_id, original_filename, storage_path, is_external,
                            media_type, file_size_bytes, mime_type, duration_seconds,
                            width, height, fps, video_codec, audio_codec, availability_status,
                            proxy_reference_path, thumbnail_reference_path, metadata_status,
                            metadata_json, created_at, updated_at, proxy_status,
                            sha256, integrity_status, upload_attempt_id, integrity_details_json, last_integrity_check
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'present', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            sha256,
                            integrity_status or "verified",
                            upload_attempt_id,
                            integ_json,
                            now if integrity_status else None,
                        ),
                    )
            else:
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

        if actual_stored_file_id:
            try:
                self.recalculate_stored_file_reference_count(actual_stored_file_id)
            except Exception as ref_err:
                logger.warning("Could not recalculate reference count for stored file %s: %s", actual_stored_file_id, ref_err)

        return self.get_media_asset(project_id, asset_id)

    def _row_to_stored_file(self, row) -> StoredMediaFileRecord:
        keys = row.keys() if hasattr(row, "keys") else []
        return StoredMediaFileRecord(
            id=row["id"],
            sha256=row["sha256"],
            storage_path=row["storage_path"],
            file_size_bytes=row["file_size_bytes"],
            mime_type=row["mime_type"] if "mime_type" in keys else None,
            container_format=row["container_format"] if "container_format" in keys else None,
            duration_seconds=row["duration_seconds"] if "duration_seconds" in keys else None,
            width=row["width"] if "width" in keys else None,
            height=row["height"] if "height" in keys else None,
            fps=row["fps"] if "fps" in keys else None,
            video_codec=row["video_codec"] if "video_codec" in keys else None,
            audio_codec=row["audio_codec"] if "audio_codec" in keys else None,
            is_external=bool(row["is_external"]) if "is_external" in keys else False,
            reference_count=row["reference_count"] if "reference_count" in keys else 1,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_verified_at=row["last_verified_at"] if "last_verified_at" in keys else None,
        )

    def get_stored_media_file_by_sha256(self, sha256: str) -> Optional[StoredMediaFileRecord]:
        """Fetch canonical stored media file record by SHA-256."""
        if not sha256 or not sha256.strip():
            return None
        with sqlite_session(self.db_path) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "stored_media_files" not in tables:
                return None
            row = conn.execute("SELECT * FROM stored_media_files WHERE sha256 = ?", (sha256.strip().lower(),)).fetchone()
            if not row:
                return None
            return self._row_to_stored_file(row)

    def get_stored_media_file_by_id(self, stored_file_id: str) -> Optional[StoredMediaFileRecord]:
        """Fetch canonical stored media file record by ID."""
        if not stored_file_id or not stored_file_id.strip():
            return None
        with sqlite_session(self.db_path) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "stored_media_files" not in tables:
                return None
            row = conn.execute("SELECT * FROM stored_media_files WHERE id = ?", (stored_file_id.strip(),)).fetchone()
            if not row:
                return None
            return self._row_to_stored_file(row)

    def register_or_update_stored_file(
        self,
        sha256: str,
        storage_path: str,
        file_size_bytes: int,
        mime_type: Optional[str] = None,
        container_format: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        video_codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        is_external: bool = False,
    ) -> StoredMediaFileRecord:
        """Register or atomically return existing canonical stored media file record keyed by sha256."""
        now = datetime.now(timezone.utc).isoformat()
        clean_sha = sha256.strip().lower()
        file_id = f"smf_{clean_sha[:16]}"
        with sqlite_session(self.db_path) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "stored_media_files" not in tables:
                return StoredMediaFileRecord(
                    id=file_id,
                    sha256=clean_sha,
                    storage_path=storage_path,
                    file_size_bytes=file_size_bytes,
                    created_at=now,
                    updated_at=now,
                )

            existing = conn.execute(
                "SELECT * FROM stored_media_files WHERE sha256 = ?", (clean_sha,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE stored_media_files
                    SET last_verified_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, now, existing["id"]),
                )
                return self._row_to_stored_file(existing)

            try:
                conn.execute(
                    """
                    INSERT INTO stored_media_files (
                        id, sha256, storage_path, file_size_bytes, mime_type, container_format,
                        duration_seconds, width, height, fps, video_codec, audio_codec,
                        is_external, reference_count, created_at, updated_at, last_verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                    """,
                    (
                        file_id,
                        clean_sha,
                        storage_path,
                        file_size_bytes,
                        mime_type,
                        container_format,
                        duration_seconds,
                        width,
                        height,
                        fps,
                        video_codec,
                        audio_codec,
                        1 if is_external else 0,
                        now,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                existing = conn.execute(
                    "SELECT * FROM stored_media_files WHERE sha256 = ?", (clean_sha,)
                ).fetchone()
                if existing:
                    return self._row_to_stored_file(existing)

            created = conn.execute(
                "SELECT * FROM stored_media_files WHERE id = ?", (file_id,)
            ).fetchone()
            return self._row_to_stored_file(created)

    def recalculate_stored_file_reference_count(self, stored_file_id: str) -> int:
        """Atomically recount active media assets referencing this stored file and update reference_count."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "stored_media_files" not in tables:
                return 1
            sf = conn.execute("SELECT sha256 FROM stored_media_files WHERE id = ?", (stored_file_id,)).fetchone()
            sha = sf[0] if sf else ""
            row = conn.execute(
                """
                SELECT COUNT(*) FROM media_assets
                WHERE (stored_file_id = ? OR (sha256 IS NOT NULL AND sha256 != '' AND sha256 = ?))
                  AND availability_status != 'deleted'
                """,
                (stored_file_id, sha),
            ).fetchone()
            count = row[0] if row else 0
            conn.execute(
                "UPDATE stored_media_files SET reference_count = ?, updated_at = ? WHERE id = ?",
                (count, now, stored_file_id),
            )
            return count

    def reconcile_reference_counts(self) -> Dict[str, Any]:
        """
        Reconcile and synchronize reference counts across all stored media files
        against actual active media assets in the database.
        """
        now = datetime.now(timezone.utc).isoformat()
        total_reconciled = 0
        orphaned_files = 0
        with sqlite_session(self.db_path) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "stored_media_files" not in tables:
                return {"total_stored_files": 0, "updated_counts": 0, "orphaned_files": 0, "reconciled_at": now}
            stored_files = conn.execute("SELECT id, sha256, storage_path, reference_count FROM stored_media_files").fetchall()
            for sf in stored_files:
                sf_id = sf["id"]
                sf_sha = sf["sha256"]
                actual = conn.execute(
                    """
                    SELECT COUNT(*) FROM media_assets
                    WHERE (stored_file_id = ? OR (sha256 IS NOT NULL AND sha256 != '' AND sha256 = ?))
                      AND availability_status != 'deleted'
                    """,
                    (sf_id, sf_sha),
                ).fetchone()[0]

                if actual != sf["reference_count"]:
                    conn.execute(
                        "UPDATE stored_media_files SET reference_count = ?, updated_at = ? WHERE id = ?",
                        (actual, now, sf_id),
                    )
                    total_reconciled += 1
                if actual == 0:
                    orphaned_files += 1

        return {
            "total_stored_files": len(stored_files),
            "updated_counts": total_reconciled,
            "orphaned_files": orphaned_files,
            "reconciled_at": now,
        }

    def get_deduplication_stats(self) -> Dict[str, Any]:
        """
        Compute global deduplication statistics:
        - Total logical media assets
        - Unique stored physical files
        - Shared stored files (reference_count > 1)
        - Deduplicated assets count
        - Total logical bytes vs actual physical bytes
        - Total storage bytes saved and deduplication ratio
        """
        with sqlite_session(self.db_path) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "stored_media_files" not in tables:
                return {
                    "total_media_assets": 0,
                    "unique_stored_files": 0,
                    "shared_stored_files": 0,
                    "deduplicated_assets_count": 0,
                    "total_logical_bytes": 0,
                    "actual_physical_bytes": 0,
                    "saved_bytes": 0,
                    "deduplication_ratio": 1.0,
                }
            total_assets = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(file_size_bytes), 0) FROM media_assets WHERE availability_status != 'deleted'"
            ).fetchone()
            total_media_assets = total_assets[0] if total_assets else 0
            total_logical_bytes = total_assets[1] if total_assets else 0

            stored_stats = conn.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(SUM(file_size_bytes), 0),
                    COALESCE(SUM(CASE WHEN reference_count > 1 THEN 1 ELSE 0 END), 0)
                FROM stored_media_files
                """
            ).fetchone()
            unique_stored_files = stored_stats[0] if stored_stats else 0
            actual_physical_bytes = stored_stats[1] if stored_stats else 0
            shared_stored_files = stored_stats[2] if stored_stats else 0

            saved_instances = max(0, total_media_assets - unique_stored_files)
            saved_bytes = max(0, total_logical_bytes - actual_physical_bytes)
            ratio = round(total_logical_bytes / actual_physical_bytes, 2) if actual_physical_bytes > 0 else 1.0

        return {
            "total_media_assets": total_media_assets,
            "unique_stored_files": unique_stored_files,
            "shared_stored_files": shared_stored_files,
            "deduplicated_assets_count": saved_instances,
            "total_logical_bytes": total_logical_bytes,
            "actual_physical_bytes": actual_physical_bytes,
            "saved_bytes": saved_bytes,
            "deduplication_ratio": ratio,
        }

    def list_media_assets(
        self,
        project_id: Optional[str] = None,
        availability: Optional[str] = None,
        media_type: Optional[str] = None,
        proxy_status: Optional[str] = None,
        search: Optional[str] = None,
        resolution: Optional[str] = None,
        format: Optional[str] = None,
        video_codec: Optional[str] = None,
        duration_min: Optional[float] = None,
        duration_max: Optional[float] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        integrity_status: Optional[str] = None,
        analysis_status: Optional[str] = None,
        missing_thumbnail: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: Optional[int] = None,
        return_total: bool = False,
    ):
        """List media assets with server-side search, filtering, allowlisted sorting, and pagination."""
        where_clauses = ["1=1"]
        params: list = []

        if project_id and project_id != "all":
            where_clauses.append("project_id = ?")
            params.append(project_id)

        if availability:
            where_clauses.append("availability_status = ?")
            params.append(availability)

        if media_type:
            where_clauses.append("media_type = ?")
            params.append(media_type)

        if proxy_status:
            where_clauses.append("proxy_status = ?")
            params.append(proxy_status)

        if search and search.strip():
            s = f"%{search.strip()}%"
            where_clauses.append("(original_filename LIKE ? OR id LIKE ?)")
            params.extend([s, s])

        if resolution:
            r = resolution.lower().strip()
            if r == "4k":
                where_clauses.append("(height >= 2160 OR width >= 3840)")
            elif r == "1440p":
                where_clauses.append("((height >= 1440 OR width >= 2560) AND (height < 2160 AND width < 3840))")
            elif r == "1080p":
                where_clauses.append("((height >= 1080 OR width >= 1920) AND (height < 1440 AND width < 2560))")
            elif r == "720p":
                where_clauses.append("((height >= 720 OR width >= 1280) AND (height < 1080 AND width < 1920))")
            elif r == "480p":
                where_clauses.append("((height >= 480 OR width >= 854) AND (height < 720 AND width < 1280))")
            elif r in ("sd", "360p"):
                where_clauses.append("(height < 480 AND width < 854)")

        if format:
            fmt = format.lower().strip().lstrip(".")
            where_clauses.append("(original_filename LIKE ? OR mime_type LIKE ?)")
            params.extend([f"%.{fmt}", f"%{fmt}%"])

        if video_codec:
            vc = video_codec.lower().strip()
            where_clauses.append("video_codec LIKE ?")
            params.append(f"%{vc}%")

        if duration_min is not None:
            where_clauses.append("duration_seconds >= ?")
            params.append(duration_min)

        if duration_max is not None:
            where_clauses.append("duration_seconds <= ?")
            params.append(duration_max)

        if date_from:
            where_clauses.append("created_at >= ?")
            params.append(date_from)

        if date_to:
            where_clauses.append("created_at <= ?")
            params.append(date_to)

        if integrity_status:
            where_clauses.append("integrity_status = ?")
            params.append(integrity_status)

        if analysis_status:
            astat = analysis_status.lower().strip()
            if astat == "completed":
                where_clauses.append("id IN (SELECT media_asset_id FROM analysis_runs WHERE status = 'completed')")
            elif astat in ("running", "processing"):
                where_clauses.append("id IN (SELECT media_asset_id FROM analysis_runs WHERE status IN ('running', 'queued'))")
            elif astat in ("failed", "interrupted", "error"):
                where_clauses.append("id IN (SELECT media_asset_id FROM analysis_runs WHERE status IN ('failed', 'interrupted'))")
            elif astat in ("none", "unstarted", "pending"):
                where_clauses.append("id NOT IN (SELECT media_asset_id FROM analysis_runs)")

        if missing_thumbnail is not None:
            if missing_thumbnail:
                where_clauses.append("(thumbnail_reference_path IS NULL OR thumbnail_reference_path = '')")
            else:
                where_clauses.append("(thumbnail_reference_path IS NOT NULL AND thumbnail_reference_path != '')")

        # Sorting allowlist
        sort_col_map = {
            "created_at": "created_at",
            "newest": "created_at",
            "oldest": "created_at",
            "recent": "created_at",
            "original_filename": "original_filename COLLATE NOCASE",
            "name": "original_filename COLLATE NOCASE",
            "filename": "original_filename COLLATE NOCASE",
            "file_size_bytes": "file_size_bytes",
            "file_size": "file_size_bytes",
            "filesize": "file_size_bytes",
            "size": "file_size_bytes",
            "largest": "file_size_bytes",
            "smallest": "file_size_bytes",
            "duration_seconds": "duration_seconds",
            "duration": "duration_seconds",
            "longest": "duration_seconds",
            "shortest": "duration_seconds",
            "resolution": "(COALESCE(width, 0) * COALESCE(height, 0))",
            "highest_res": "(COALESCE(width, 0) * COALESCE(height, 0))",
        }
        col = sort_col_map.get(sort_by.lower(), "created_at")

        direction = sort_order.upper() if sort_order.upper() in ("ASC", "DESC") else "DESC"
        if sort_by.lower() in ("oldest", "smallest", "shortest"):
            direction = "ASC"
        elif sort_by.lower() in ("newest", "largest", "longest", "highest_res", "recent"):
            direction = "DESC"

        order_by = f"{col} {direction}"
        if col != "id":
            order_by += ", id DESC"

        where_sql = " AND ".join(where_clauses)
        count_sql = f"SELECT COUNT(*) FROM media_assets WHERE {where_sql}"

        with sqlite_session(self.db_path) as conn:
            total_count = conn.execute(count_sql, params).fetchone()[0]

            query = f"""
                SELECT media_assets.*,
                       COALESCE(
                           (SELECT reference_count FROM stored_media_files WHERE id = media_assets.stored_file_id),
                           1
                       ) AS reference_count
                FROM media_assets
                WHERE {where_sql}
                ORDER BY {order_by}
            """
            query_params = list(params)
            if page_size is not None and page_size > 0:
                p = max(1, page)
                offset = (p - 1) * page_size
                query += " LIMIT ? OFFSET ?"
                query_params.extend([page_size, offset])

            rows = conn.execute(query, query_params).fetchall()

            # Batch query analysis status for returned rows
            asset_ids = [r["id"] for r in rows]
            analysis_map = {}
            if asset_ids:
                placeholders = ",".join("?" for _ in asset_ids)
                ar_rows = conn.execute(
                    f"""
                    SELECT media_asset_id, status FROM analysis_runs
                    WHERE media_asset_id IN ({placeholders})
                    ORDER BY created_at DESC
                    """,
                    asset_ids,
                ).fetchall()
                for ar in ar_rows:
                    aid, st = ar[0], ar[1]
                    if aid not in analysis_map:
                        analysis_map[aid] = st

            records = [
                self._row_to_record(row, analysis_status_override=analysis_map.get(row["id"]))
                for row in rows
            ]

        if return_total:
            return records, total_count
        return records

    def get_media_asset(self, project_id: Optional[str], asset_id: str) -> MediaAssetRecord:
        """Fetch media asset details, either within a specific project or by asset ID alone."""
        with sqlite_session(self.db_path) as conn:
            if project_id and project_id != "all":
                row = conn.execute(
                    """
                    SELECT m.*,
                           COALESCE(
                               (SELECT reference_count FROM stored_media_files WHERE id = m.stored_file_id),
                               1
                           ) AS reference_count
                    FROM media_assets m
                    WHERE m.project_id = ? AND m.id = ?
                    """,
                    (project_id, asset_id),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT m.*,
                           COALESCE(
                               (SELECT reference_count FROM stored_media_files WHERE id = m.stored_file_id),
                               1
                           ) AS reference_count
                    FROM media_assets m
                    WHERE m.id = ?
                    """,
                    (asset_id,),
                ).fetchone()

            if not row:
                raise AppError(
                    code="MEDIA_ASSET_NOT_FOUND",
                    message=f"Media asset with ID '{asset_id}' not found.",
                    status_code=404,
                )

            ar = conn.execute(
                "SELECT status FROM analysis_runs WHERE media_asset_id = ? ORDER BY created_at DESC LIMIT 1",
                (asset_id,),
            ).fetchone()
            analysis_status = ar[0] if ar else "none"
            return self._row_to_record(row, analysis_status_override=analysis_status)

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
        project_id: Optional[str],
        asset_id: str,
        delete_source: bool = False,
        force_with_exports: bool = False,
    ) -> dict:
        """
        Safely unregister media asset record and reclaim its managed storage files.
        Checks active operations and dependent exports before deleting.
        """
        asset = self.get_media_asset(project_id, asset_id)
        now = datetime.now(timezone.utc).isoformat()
        layout = StorageLayout.from_root(self.settings.storage_root)

        # 1. Check for active jobs (upload, analysis, export)
        with sqlite_session(self.db_path) as conn:
            active_jobs = conn.execute(
                """
                SELECT id, job_type, status FROM jobs
                WHERE status IN ('running', 'queued') AND (media_asset_id = ? OR input_config_json LIKE ?)
                """,
                (asset_id, f"%{asset_id}%"),
            ).fetchall()
            if active_jobs:
                raise AppError(
                    code="ACTIVE_OPERATION_IN_PROGRESS",
                    message=f"Cannot delete asset '{asset_id}': active job '{active_jobs[0][0]}' ({active_jobs[0][1]}) is currently {active_jobs[0][2]}.",
                    status_code=409,
                )

            # 2. Check for dependent exports
            dependent_exports = conn.execute(
                "SELECT id, title, status FROM exports WHERE media_asset_id = ?",
                (asset_id,),
            ).fetchall()
            if dependent_exports and not force_with_exports:
                raise AppError(
                    code="DEPENDENCY_CONFLICT",
                    message=f"Cannot delete asset '{asset_id}': {len(dependent_exports)} export(s) depend on this video. Please delete exports first or specify force_with_exports=true.",
                    status_code=409,
                )

        # 3. Cancel any remaining or historical non-running jobs
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

        # 4. Check remaining references to the underlying physical file (P1.8 Reference Counting)
        stored_file = None
        if asset.stored_file_id:
            stored_file = self.get_stored_media_file_by_id(asset.stored_file_id)
        if not stored_file and asset.sha256:
            stored_file = self.get_stored_media_file_by_sha256(asset.sha256)

        remaining_references = 0
        with sqlite_session(self.db_path) as conn:
            if stored_file:
                rem_row = conn.execute(
                    """
                    SELECT COUNT(*) FROM media_assets
                    WHERE (stored_file_id = ? OR (sha256 IS NOT NULL AND sha256 != '' AND sha256 = ?))
                      AND id != ?
                      AND availability_status != 'deleted'
                    """,
                    (stored_file.id, stored_file.sha256, asset_id),
                ).fetchone()
                remaining_references = rem_row[0] if rem_row else 0
            elif asset.storage_path:
                rem_row = conn.execute(
                    """
                    SELECT COUNT(*) FROM media_assets
                    WHERE storage_path = ?
                      AND id != ?
                      AND availability_status != 'deleted'
                    """,
                    (asset.storage_path, asset_id),
                ).fetchone()
                remaining_references = rem_row[0] if rem_row else 0

        physical_file_retained = False
        if remaining_references > 0:
            physical_file_retained = True
            logger.info(
                "Preserving physical file for asset '%s': %d other reference(s) exist.",
                asset_id,
                remaining_references,
            )
        else:
            # Reclaim managed disk files (only if within storage_root!)
            try:
                # Managed source video (if not external original)
                if not asset.is_external and asset.storage_path:
                    src_file = layout.media / asset.storage_path
                    if not src_file.is_file():
                        src_file = Path(asset.storage_path)
                    if src_file.exists() and src_file.is_file():
                        # Check path traversal
                        try:
                            resolved_src = src_file.resolve()
                            resolved_root = layout.root.resolve()
                            if resolved_src.is_relative_to(resolved_root) or str(resolved_src).lower().startswith(str(resolved_root).lower()):
                                src_file.unlink(missing_ok=True)
                        except Exception as unlink_err:
                            logger.warning("Failed to unlink source file '%s': %s", src_file, unlink_err)

                if stored_file:
                    with sqlite_session(self.db_path) as conn:
                        conn.execute("DELETE FROM stored_media_files WHERE id = ?", (stored_file.id,))
            except Exception as file_err:
                logger.warning("Error deleting managed media files for %s: %s", asset_id, file_err)

        # Asset-specific proxies, thumbnails, and analysis files are always reclaimed
        try:
            for p in layout.proxies.glob(f"{asset_id}*"):
                p.unlink(missing_ok=True)
            for t in layout.thumbnails.glob(f"{asset_id}*"):
                t.unlink(missing_ok=True)
            analysis_dir = layout.analysis / asset_id
            if analysis_dir.exists():
                shutil.rmtree(analysis_dir, ignore_errors=True)
        except Exception as file_err:
            logger.warning("Error deleting managed proxy/thumb files for %s: %s", asset_id, file_err)

        # 5. Delete database records across related tables
        with sqlite_session(self.db_path) as conn:
            # If force_with_exports is True, delete dependent exports
            if force_with_exports:
                conn.execute("DELETE FROM exports WHERE media_asset_id = ?", (asset_id,))

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

            if project_id and project_id != "all":
                conn.execute("DELETE FROM media_assets WHERE project_id = ? AND id = ?", (project_id, asset_id))
            else:
                conn.execute("DELETE FROM media_assets WHERE id = ?", (asset_id,))

            event_id = f"evt_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO project_events (id, project_id, event_type, event_summary, payload_json, created_at)
                VALUES (?, ?, 'media_deleted', ?, ?, ?)
                """,
                (
                    event_id,
                    asset.project_id,
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

        if stored_file and remaining_references > 0:
            try:
                self.recalculate_stored_file_reference_count(stored_file.id)
            except Exception as ref_err:
                logger.warning("Could not recalculate reference count after deleting %s: %s", asset_id, ref_err)

        return {
            "deleted": True,
            "asset_id": asset_id,
            "remaining_references": remaining_references,
            "physical_file_retained": physical_file_retained,
        }

    def refresh_media_metadata(self, project_id: Optional[str], asset_id: str) -> MediaAssetRecord:
        """
        Explicitly re-probe a media file on disk with FFprobe and update its technical metadata atomically.
        Preserves pre-computed SHA-256 and integrity contract status.
        """
        asset = self.get_media_asset(project_id, asset_id)
        layout = StorageLayout.from_root(self.settings.storage_root)
        phys_path = Path(asset.storage_path)
        if not phys_path.is_file():
            phys_path = layout.media / asset.storage_path
            if not phys_path.is_file():
                self.mark_missing(asset.project_id, asset_id)
                raise AppError(
                    code="MEDIA_FILE_MISSING",
                    message=f"Physical media file for asset '{asset_id}' not found on disk at '{asset.storage_path}'.",
                    status_code=404,
                )

        from app.services.media_probe import probe_media_file
        probe = probe_media_file(phys_path, ffprobe_path=self.settings.ffprobe_path)
        if probe.media_type == "unknown":
            raise AppError(
                code="CORRUPT_MEDIA",
                message=f"FFprobe could not read media file for asset '{asset_id}'.",
                status_code=400,
            )

        now = datetime.now(timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                UPDATE media_assets
                SET width = ?, height = ?, fps = ?, duration_seconds = ?,
                    video_codec = ?, audio_codec = ?, metadata_status = 'extracted',
                    metadata_json = ?, updated_at = ?, availability_status = 'present'
                WHERE id = ?
                """,
                (
                    probe.width,
                    probe.height,
                    probe.fps,
                    probe.duration_seconds,
                    probe.video_codec,
                    probe.audio_codec,
                    json.dumps(probe.raw_metadata or {"streams": probe.streams}),
                    now,
                    asset_id,
                ),
            )
        return self.get_media_asset(project_id, asset_id)

    def regenerate_thumbnail(self, project_id: Optional[str], asset_id: str) -> MediaAssetRecord:
        """Explicitly regenerate JPEG thumbnail for an asset using FFmpeg."""
        asset = self.get_media_asset(project_id, asset_id)
        layout = StorageLayout.from_root(self.settings.storage_root)
        source_path = Path(asset.storage_path)
        if not source_path.is_file():
            source_path = layout.media / asset.storage_path
            if not source_path.is_file():
                self.mark_missing(asset.project_id, asset_id)
                raise AppError(
                    code="MEDIA_FILE_MISSING",
                    message=f"Physical media file for asset '{asset_id}' not found.",
                    status_code=404,
                )

        from app.services.media_thumbnail import generate_thumbnail
        thumb_name = f"{asset.id}.jpg"
        thumb_dest = layout.thumbnails / thumb_name
        res = generate_thumbnail(
            source_path=source_path,
            output_path=thumb_dest,
            media_type=asset.media_type,
            duration=asset.duration_seconds,
            ffmpeg_path=self.settings.ffmpeg_path,
        )
        now = datetime.now(timezone.utc).isoformat()
        rel_thumb_path = f"thumbnails/{thumb_name}" if res else None
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                "UPDATE media_assets SET thumbnail_reference_path = ?, updated_at = ? WHERE id = ?",
                (rel_thumb_path, now, asset_id),
            )
        return self.get_media_asset(project_id, asset_id)

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
            "integrity_status": "verified" if integrity == "online" else integrity,
            "file_exists": exists,
            "file_size_bytes": size_bytes,
            "size_matches": size_matches,
            "probe_ok": probe_ok,
            "duration_seconds": duration,
            "width": width,
            "height": height,
            "issues": issues,
            "checked_at": now,
            "sha256": getattr(asset, "sha256", None),
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
        """Probe replacement candidate and compare against original media attributes with SHA-256 validation."""
        asset = self.get_media_asset(project_id, asset_id)
        candidate_path = Path(new_storage_path).expanduser().resolve(strict=False)

        # 1. Existence and regular file checks
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

        # 2. Path security validation: forbid system-critical directories
        resolved_str = str(candidate_path.resolve()).lower()
        disallowed_prefixes = [
            "c:\\windows", "c:\\program files", "c:\\program files (x86)",
            "/etc", "/bin", "/sbin", "/usr", "/sys", "/dev", "/proc"
        ]
        if any(resolved_str.startswith(p) for p in disallowed_prefixes):
            raise AppError(
                code="SECURITY_VIOLATION",
                message="Access to restricted system paths is prohibited.",
                status_code=403,
            )

        # 3. Video format validation
        ext = candidate_path.suffix.lower()
        if ext not in SUPPORTED_VIDEO_EXTS:
            raise AppError(
                code="UNSUPPORTED_MEDIA_TYPE",
                message=f"Unsupported video file format '{ext}'. Supported formats: {sorted(SUPPORTED_VIDEO_EXTS)}.",
                status_code=400,
            )

        # 4. Readability and FFprobe stream inspection
        warnings: List[str] = []
        try:
            probe = probe_media_file(candidate_path, ffprobe_path=self.settings.ffprobe_path)
        except Exception as probe_err:
            raise AppError(
                code="INVALID_VIDEO_FILE",
                message=f"Replacement video file is corrupt or unreadable by FFprobe: {probe_err}",
                status_code=400,
            )

        if not probe.width or not probe.height or not probe.video_codec:
            raise AppError(
                code="NO_VIDEO_STREAM",
                message="Replacement media file does not contain a valid readable video stream.",
                status_code=400,
            )

        # 5. Incremental SHA-256 calculation (bounded memory chunks)
        candidate_sha = None
        try:
            hasher = hashlib.sha256()
            with open(candidate_path, "rb") as f:
                while chunk := f.read(64 * 1024):
                    hasher.update(chunk)
            candidate_sha = hasher.hexdigest()
        except Exception as hash_err:
            logger.warning("Could not compute candidate SHA-256: %s", hash_err)

        # 6. Metadata comparison & identity check
        dur_diff = 0.0
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

        sha256_match = None
        if asset.sha256 and candidate_sha:
            if asset.sha256.lower() == candidate_sha.lower():
                sha256_match = True
            else:
                sha256_match = False
                warnings.append(
                    f"SHA-256 checksum mismatch: Candidate hash '{candidate_sha[:8]}...' differs from original '{asset.sha256[:8]}...'."
                )

        if dur_diff > 1.0:
            match_status = "mismatch"
        elif sha256_match is False or len(warnings) > 0:
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
            "original_sha256": asset.sha256,
            "candidate_sha256": candidate_sha,
            "sha256_match": sha256_match,
            "candidate_video_codec": probe.video_codec if probe else None,
            "candidate_audio_codec": probe.audio_codec if probe else None,
            "candidate_fps": probe.fps if probe else None,
        }

        return {
            "match_status": match_status,
            "warnings": warnings,
            "comparison": comparison,
            "probe": probe,
            "candidate_path": candidate_path,
            "candidate_sha256": candidate_sha,
        }

    def relink_media(
        self, project_id: str, asset_id: str, new_storage_path: str, force: bool = False
    ) -> MediaAssetRecord:
        """Relink an asset to a new filesystem path with comparison, atomic update, and user audit."""
        inspection = self.inspect_relink_candidate(project_id, asset_id, new_storage_path)
        candidate_path = inspection["candidate_path"]
        probe = inspection["probe"]
        warnings = inspection["warnings"]
        match_status = inspection["match_status"]
        comparison = inspection["comparison"]
        candidate_sha = inspection.get("candidate_sha256")

        if match_status == "mismatch" and not force:
            raise AppError(
                code="RELINK_MISMATCH",
                message=f"Candidate replacement video has significant discrepancies ({'; '.join(warnings)}). Explicit confirmation (force=true) is required.",
                status_code=400,
                details=comparison,
            )

        asset = self.get_media_asset(project_id, asset_id)
        now = datetime.now(timezone.utc).isoformat()
        prev_path = asset.storage_path
        prev_sha = asset.sha256

        probe_size = probe.file_size_bytes if probe else candidate_path.stat().st_size
        probe_dur = probe.duration_seconds if probe else None
        probe_w = probe.width if probe else None
        probe_h = probe.height if probe else None
        probe_fps = probe.fps if probe else None
        probe_vc = probe.video_codec if probe else None
        probe_ac = probe.audio_codec if probe else None

        is_candidate_external = True
        try:
            is_candidate_external = not candidate_path.resolve().is_relative_to(self.settings.storage_root.resolve())
        except Exception:
            is_candidate_external = True

        old_stored_file_id = asset.stored_file_id
        new_stored_file_id = None
        if candidate_sha:
            smf = self.get_stored_media_file_by_sha256(candidate_sha)
            if not smf:
                smf = self.register_or_update_stored_file(
                    sha256=candidate_sha,
                    storage_path=str(candidate_path),
                    file_size_bytes=probe_size or 0,
                    mime_type=f"{probe.media_type}/{probe.container_format}" if probe else None,
                    container_format=probe.container_format if probe else None,
                    duration_seconds=probe_dur,
                    width=probe_w,
                    height=probe_h,
                    fps=probe_fps,
                    video_codec=probe_vc,
                    audio_codec=probe_ac,
                    is_external=is_candidate_external,
                )
            new_stored_file_id = smf.id

        with sqlite_session(self.db_path) as conn:
            cols = [col[1] for col in conn.execute("PRAGMA table_info(media_assets)").fetchall()]
            if "stored_file_id" in cols:
                conn.execute(
                    """
                    UPDATE media_assets
                    SET storage_path = ?,
                        is_external = ?,
                        availability_status = 'present',
                        integrity_status = ?,
                        file_size_bytes = COALESCE(?, file_size_bytes),
                        duration_seconds = COALESCE(?, duration_seconds),
                        width = COALESCE(?, width),
                        height = COALESCE(?, height),
                        fps = COALESCE(?, fps),
                        video_codec = COALESCE(?, video_codec),
                        audio_codec = COALESCE(?, audio_codec),
                        sha256 = COALESCE(?, sha256),
                        relinked_at = ?,
                        previous_storage_path = ?,
                        previous_sha256 = ?,
                        relink_match_status = ?,
                        last_integrity_check = ?,
                        updated_at = ?,
                        stored_file_id = COALESCE(?, stored_file_id)
                    WHERE id = ?
                    """,
                    (
                        str(candidate_path),
                        1 if is_candidate_external else 0,
                        "verified" if match_status in ("exact", "compatible") else "online",
                        probe_size,
                        probe_dur,
                        probe_w,
                        probe_h,
                        probe_fps,
                        probe_vc,
                        probe_ac,
                        candidate_sha,
                        now,
                        prev_path,
                        prev_sha,
                        match_status,
                        now,
                        now,
                        new_stored_file_id,
                        asset_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE media_assets
                    SET storage_path = ?,
                        is_external = ?,
                        availability_status = 'present',
                        integrity_status = ?,
                        file_size_bytes = COALESCE(?, file_size_bytes),
                        duration_seconds = COALESCE(?, duration_seconds),
                        width = COALESCE(?, width),
                        height = COALESCE(?, height),
                        fps = COALESCE(?, fps),
                        video_codec = COALESCE(?, video_codec),
                        audio_codec = COALESCE(?, audio_codec),
                        sha256 = COALESCE(?, sha256),
                        relinked_at = ?,
                        previous_storage_path = ?,
                        previous_sha256 = ?,
                        relink_match_status = ?,
                        last_integrity_check = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        str(candidate_path),
                        1 if is_candidate_external else 0,
                        "verified" if match_status in ("exact", "compatible") else "online",
                        probe_size,
                        probe_dur,
                        probe_w,
                        probe_h,
                        probe_fps,
                        probe_vc,
                        probe_ac,
                        candidate_sha,
                        now,
                        prev_path,
                        prev_sha,
                        match_status,
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
                    asset.project_id,
                    f"Media asset '{asset_id}' relinked to '{candidate_path}' (match: {match_status})",
                    json.dumps({
                        "asset_id": asset_id,
                        "new_path": str(candidate_path),
                        "previous_path": prev_path,
                        "previous_sha256": prev_sha,
                        "candidate_sha256": candidate_sha,
                        "match_status": match_status,
                        "warnings": warnings,
                        "comparison": comparison,
                        "force": force,
                        "relinked_at": now,
                    }),
                    now,
                ),
            )

        # Regenerate thumbnail
        try:
            from app.services.media_thumbnail import generate_thumbnail
            layout = StorageLayout.from_root(self.settings.storage_root)
            thumb_path = layout.thumbnails / f"{asset_id}.jpg"
            generate_thumbnail(
                candidate_path,
                thumb_path,
                media_type="video",
                duration=probe_dur or asset.duration_seconds,
            )
            with sqlite_session(self.db_path) as conn:
                conn.execute(
                    "UPDATE media_assets SET thumbnail_reference_path = ? WHERE id = ?",
                    (f"thumbnails/{thumb_path.name}", asset_id),
                )
        except Exception as thumb_err:
            logger.warning("Could not regenerate thumbnail during relink for asset %s: %s", asset_id, thumb_err)

        if old_stored_file_id:
            try:
                self.recalculate_stored_file_reference_count(old_stored_file_id)
            except Exception as ref_err:
                logger.warning("Could not recalculate reference count for old stored file %s: %s", old_stored_file_id, ref_err)

        if new_stored_file_id:
            try:
                self.recalculate_stored_file_reference_count(new_stored_file_id)
            except Exception as ref_err:
                logger.warning("Could not recalculate reference count for new stored file %s: %s", new_stored_file_id, ref_err)

        return self.get_media_asset(project_id, asset_id)

    def reconcile_missing_media(
        self, project_id: Optional[str] = "all"
    ) -> Dict[str, Any]:
        """
        Reconcile missing media files by checking disk availability.
        Restores assets where the file has returned (e.g. external drive reconnected).
        """
        now = datetime.now(timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            if project_id and project_id != "all":
                rows = conn.execute(
                    "SELECT * FROM media_assets WHERE project_id = ?",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM media_assets"
                ).fetchall()

        restored_assets: List[str] = []
        still_missing: List[str] = []
        layout = StorageLayout.from_root(self.settings.storage_root)

        for row in rows:
            asset_id = row["id"]
            storage_path = row["storage_path"]
            prev_avail = row["availability_status"]
            prev_integ = row["integrity_status"]
            if not storage_path:
                still_missing.append(asset_id)
                continue

            path = Path(storage_path)
            if not path.is_file():
                if (layout.media / storage_path).is_file():
                    path = layout.media / storage_path
                elif (layout.root / storage_path).is_file():
                    path = layout.root / storage_path

            if path.is_file():
                # If it was missing or unverified, verify and restore
                if prev_avail == "missing" or prev_integ == "missing":
                    try:
                        probe = probe_media_file(path, ffprobe_path=self.settings.ffprobe_path)
                        with sqlite_session(self.db_path) as conn:
                            conn.execute(
                                """
                                UPDATE media_assets
                                SET availability_status = 'present',
                                    integrity_status = 'verified',
                                    last_integrity_check = ?,
                                    updated_at = ?
                                WHERE id = ?
                                """,
                                (now, now, asset_id),
                            )
                        restored_assets.append(asset_id)
                        logger.info("Restored missing media asset '%s' at '%s'", asset_id, path)
                    except Exception as probe_err:
                        still_missing.append(asset_id)
                        logger.warning("File found for asset '%s' but unreadable: %s", asset_id, probe_err)
            else:
                # File not found on disk
                with sqlite_session(self.db_path) as conn:
                    conn.execute(
                        """
                        UPDATE media_assets
                        SET availability_status = 'missing',
                            integrity_status = 'missing',
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now, asset_id),
                    )
                still_missing.append(asset_id)

        return {
            "total_checked": len(rows),
            "restored_count": len(restored_assets),
            "still_missing_count": len(still_missing),
            "restored_assets": restored_assets,
            "still_missing_assets": still_missing,
        }

    def _row_to_record(self, row, analysis_status_override: Optional[str] = None) -> MediaAssetRecord:
        keys = row.keys() if hasattr(row, "keys") else []
        meta = json.loads(row["metadata_json"] or "{}")

        filename = row["original_filename"] or ""
        ext = Path(filename).suffix.lower()

        w = row["width"]
        h = row["height"]
        res_label = None
        aspect_ratio = None
        if w and h:
            if h >= 2160 or w >= 3840:
                res_label = "4K"
            elif h >= 1440 or w >= 2560:
                res_label = "1440p"
            elif h >= 1080 or w >= 1920:
                res_label = "1080p"
            elif h >= 720 or w >= 1280:
                res_label = "720p"
            elif h >= 480 or w >= 854:
                res_label = "480p"
            else:
                res_label = f"{w}x{h}"

            import math
            gcd = math.gcd(w, h)
            if gcd > 0:
                aspect_ratio = f"{w // gcd}:{h // gcd}"

        streams = meta.get("streams", []) if isinstance(meta, dict) else []
        audio_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
        subtitle_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "subtitle"]
        video_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"]

        audio_count = len(audio_streams) or (1 if row["audio_codec"] else 0)
        sub_count = len(subtitle_streams)

        audio_langs: List[str] = []
        for s in audio_streams:
            lang = s.get("tags", {}).get("language") if isinstance(s.get("tags"), dict) else None
            if lang and lang not in audio_langs:
                audio_langs.append(lang)

        sub_langs: List[str] = []
        for s in subtitle_streams:
            lang = s.get("tags", {}).get("language") if isinstance(s.get("tags"), dict) else None
            if lang and lang not in sub_langs:
                sub_langs.append(lang)

        pixel_format = None
        if video_streams:
            pixel_format = video_streams[0].get("pix_fmt")

        bitrate = None
        if isinstance(meta, dict):
            fmt = meta.get("format")
            if isinstance(fmt, dict):
                try:
                    bitrate = int(fmt.get("bit_rate") or 0) or None
                except (ValueError, TypeError):
                    bitrate = None
            if not bitrate and "bit_rate" in meta:
                try:
                    bitrate = int(meta.get("bit_rate") or 0) or None
                except (ValueError, TypeError):
                    bitrate = None

        container_format = meta.get("format_name") if isinstance(meta, dict) else None
        if not container_format and ext:
            container_format = ext.lstrip(".")

        thumb_path = row["thumbnail_reference_path"]
        thumb_avail = bool(thumb_path)
        thumb_url = f"/api/v1/media/{row['id']}/thumbnail"
        stream_url = f"/api/v1/media/{row['id']}/stream"
        dash_url = f"/projects/{row['project_id']}/dashboard"

        avail = row["availability_status"]
        file_missing = (avail in ("missing", "corrupted"))
        if not file_missing and row["storage_path"]:
            p = Path(row["storage_path"])
            if not p.is_file():
                layout = StorageLayout.from_root(self.settings.storage_root)
                if not (layout.root / row["storage_path"]).is_file() and not (layout.media / row["storage_path"]).is_file():
                    file_missing = True
        is_playable = not file_missing
        effective_avail = "missing" if file_missing else row["availability_status"]
        effective_integrity = "missing" if file_missing else (row["integrity_status"] if "integrity_status" in keys else None)
        analysis_stat = analysis_status_override or "none"

        relinked_at = row["relinked_at"] if "relinked_at" in keys else None
        previous_storage_path = row["previous_storage_path"] if "previous_storage_path" in keys else None
        previous_sha256 = row["previous_sha256"] if "previous_sha256" in keys else None
        relink_match_status = row["relink_match_status"] if "relink_match_status" in keys else None

        stored_file_id = row["stored_file_id"] if "stored_file_id" in keys else None
        ref_count = row["reference_count"] if "reference_count" in keys and row["reference_count"] is not None else 1
        is_shared = (ref_count > 1)
        is_dedup = False
        if "integrity_details_json" in keys and row["integrity_details_json"]:
            try:
                det = json.loads(row["integrity_details_json"])
                if isinstance(det, dict) and det.get("deduplicated"):
                    is_dedup = True
            except Exception:
                pass
        if not is_dedup and is_shared:
            is_dedup = True

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
            availability_status=effective_avail,
            proxy_reference_path=row["proxy_reference_path"],
            thumbnail_reference_path=row["thumbnail_reference_path"],
            proxy_status=row["proxy_status"] if "proxy_status" in keys else "none",
            metadata_status=row["metadata_status"],
            metadata=meta,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            sha256=row["sha256"] if "sha256" in keys else None,
            integrity_status=effective_integrity,
            upload_attempt_id=row["upload_attempt_id"] if "upload_attempt_id" in keys else None,
            integrity_details_json=row["integrity_details_json"] if "integrity_details_json" in keys else None,
            last_integrity_check=row["last_integrity_check"] if "last_integrity_check" in keys else None,
            display_filename=filename,
            file_extension=ext,
            container_format=container_format,
            resolution_label=res_label,
            aspect_ratio=aspect_ratio,
            audio_stream_count=audio_count,
            subtitle_stream_count=sub_count,
            audio_languages=audio_langs,
            subtitle_languages=sub_langs,
            pixel_format=pixel_format,
            bitrate=bitrate,
            analysis_status=analysis_stat,
            is_playable=is_playable,
            thumbnail_available=thumb_avail,
            thumbnail_url=thumb_url,
            streaming_url=stream_url,
            dashboard_url=dash_url,
            relinked_at=relinked_at,
            previous_storage_path=previous_storage_path,
            previous_sha256=previous_sha256,
            relink_match_status=relink_match_status,
            stored_file_id=stored_file_id,
            reference_count=ref_count,
            is_shared=is_shared,
            is_deduplicated=is_dedup,
        )
