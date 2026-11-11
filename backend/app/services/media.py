"""Media metadata domain service managing media asset records, availability states, and relinking."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.config import Settings
from app.core.errors import AppError
from app.db.connection import sqlite_session
from app.models.entities import MediaAssetRecord


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
        project_id: str,
        availability: Optional[str] = None,
        media_type: Optional[str] = None,
        proxy_status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[MediaAssetRecord]:
        """List all media assets for a project with optional filtering."""
        query = "SELECT * FROM media_assets WHERE project_id = ?"
        params: list = [project_id]
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

    def get_media_asset(self, project_id: str, asset_id: str) -> MediaAssetRecord:
        """Fetch media asset details."""
        with sqlite_session(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM media_assets WHERE project_id = ? AND id = ?",
                (project_id, asset_id),
            ).fetchone()
            if not row:
                raise AppError(
                    code="MEDIA_ASSET_NOT_FOUND",
                    message=f"Media asset with ID '{asset_id}' not found in project '{project_id}'.",
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

    def delete_media_asset(self, project_id: str, asset_id: str) -> None:
        """Unregister media asset record from project."""
        self.get_media_asset(project_id, asset_id)
        now = datetime.now(timezone.utc).isoformat()

        with sqlite_session(self.db_path) as conn:
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
                    f"Media asset '{asset_id}' removed from project",
                    json.dumps({"asset_id": asset_id}),
                    now,
                ),
            )

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

    def relink_media(
        self, project_id: str, asset_id: str, new_storage_path: str
    ) -> MediaAssetRecord:
        """Relink an asset to a new filesystem path and mark present."""
        self.get_media_asset(project_id, asset_id)
        new_path = Path(new_storage_path).expanduser().resolve(strict=False)
        if not new_path.exists():
            raise AppError(
                code="FILE_NOT_FOUND",
                message=f"Relink target '{new_path}' does not exist on disk.",
                status_code=400,
            )

        now = datetime.now(timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                UPDATE media_assets
                SET storage_path = ?, availability_status = 'present', updated_at = ?
                WHERE id = ?
                """,
                (str(new_path), now, asset_id),
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
                    f"Media asset '{asset_id}' relinked to '{new_path}'",
                    json.dumps({"asset_id": asset_id, "new_path": str(new_path)}),
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
