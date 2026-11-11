"""Timeline management service: Projects, Timelines, Tracks, and Clips CRUD."""

from __future__ import annotations

import datetime
import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import Settings, get_settings
from app.core.errors import AppError, NotFoundError, ProcessingError, ValidationError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.models.timeline import (
    AudioProps,
    ClipType,
    ContentProps,
    CreateTimelineRequest,
    CreateTrackRequest,
    TimelineClip,
    TimelineRecord,
    TimelineTrack,
    TrackSubtype,
    TrackType,
    TransformProps,
    UpdateTimelineSettingsRequest,
    UpdateTrackRequest,
)

logger = logging.getLogger("zezedit.timeline.service")


class TimelineService:
    """Manages multi-track timelines, track hierarchies, and clip models."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.layout = StorageLayout.from_root(self.settings.storage_root)
        self.db_path = db_path or self.layout.db_file

    # -------------------------------------------------------------------------
    # Timeline Management
    # -------------------------------------------------------------------------

    def get_or_create_default_timeline(self, project_id: str) -> TimelineRecord:
        """Fetch the active project timeline or create a default sequence."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Verify project
            proj = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not proj:
                raise NotFoundError(f"Project '{project_id}' not found.")

            tl_row = conn.execute(
                "SELECT * FROM timelines WHERE project_id = ? AND is_active = 1 ORDER BY created_at ASC LIMIT 1",
                (project_id,),
            ).fetchone()

            if tl_row:
                return self._hydrate_timeline(conn, tl_row["id"])

        # No timeline exists, create one with default tracks
        return self.create_timeline(project_id, CreateTimelineRequest(name="Main Sequence", create_default_tracks=True))

    def create_timeline(self, project_id: str, request: CreateTimelineRequest) -> TimelineRecord:
        """Create a new timeline sequence for a project."""
        timeline_id = f"tl_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            proj = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not proj:
                raise NotFoundError(f"Project '{project_id}' not found.")

            conn.execute(
                """
                INSERT INTO timelines (
                    id, project_id, name, duration, fps, canvas_width, canvas_height,
                    time_base, revision, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, 0.0, ?, ?, ?, ?, 1, 1, ?, ?)
                """,
                (
                    timeline_id,
                    project_id,
                    request.name,
                    request.fps,
                    request.canvas_width,
                    request.canvas_height,
                    f"1/{request.fps}",
                    now,
                    now,
                ),
            )

            # Create standard default tracks if requested
            if request.create_default_tracks:
                default_tracks = [
                    ("V2 - Overlays", TrackType.OVERLAY, TrackSubtype.TEXT, 0, 56),
                    ("V1 - Main Video", TrackType.VIDEO, TrackSubtype.MAIN_VIDEO, 1, 72),
                    ("A1 - Source Audio", TrackType.AUDIO, TrackSubtype.SOURCE_AUDIO, 2, 56),
                    ("A2 - Background Music", TrackType.AUDIO, TrackSubtype.BGM, 3, 56),
                ]
                for name, t_type, t_subtype, order, height in default_tracks:
                    tr_id = f"tr_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """
                        INSERT INTO timeline_tracks (
                            id, timeline_id, name, track_type, track_subtype,
                            track_order, is_visible, is_muted, is_locked, height,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, 1, 0, 0, ?, ?, ?)
                        """,
                        (tr_id, timeline_id, name, t_type.value, t_subtype.value, order, height, now, now),
                    )

            conn.commit()
            return self._hydrate_timeline(conn, timeline_id)

    def get_timeline(self, timeline_id: str) -> TimelineRecord:
        """Retrieve full timeline with tracks and clips."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return self._hydrate_timeline(conn, timeline_id)

    def list_project_timelines(self, project_id: str) -> List[TimelineRecord]:
        """List all timelines in a project."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id FROM timelines WHERE project_id = ? ORDER BY created_at ASC",
                (project_id,),
            ).fetchall()
            return [self._hydrate_timeline(conn, r["id"]) for r in rows]

    def update_timeline_settings(
        self,
        timeline_id: str,
        request: UpdateTimelineSettingsRequest,
    ) -> TimelineRecord:
        """Update timeline canvas dimensions, fps, or name."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            tl = conn.execute("SELECT * FROM timelines WHERE id = ?", (timeline_id,)).fetchone()
            if not tl:
                raise NotFoundError(f"Timeline '{timeline_id}' not found.")

            updates = []
            params = []
            if request.name is not None:
                updates.append("name = ?")
                params.append(request.name)
            if request.fps is not None:
                if request.fps <= 0 or request.fps > 120:
                    raise ValidationError("FPS must be between 1 and 120.")
                updates.append("fps = ?")
                params.append(request.fps)
                updates.append("time_base = ?")
                params.append(f"1/{request.fps}")
            if request.canvas_width is not None:
                if request.canvas_width <= 0:
                    raise ValidationError("Canvas width must be positive.")
                updates.append("canvas_width = ?")
                params.append(request.canvas_width)
            if request.canvas_height is not None:
                if request.canvas_height <= 0:
                    raise ValidationError("Canvas height must be positive.")
                updates.append("canvas_height = ?")
                params.append(request.canvas_height)

            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.datetime.now(datetime.timezone.utc).isoformat())
                params.append(timeline_id)
                conn.execute(f"UPDATE timelines SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()

            return self._hydrate_timeline(conn, timeline_id)

    # -------------------------------------------------------------------------
    # Track Management
    # -------------------------------------------------------------------------

    def add_track(self, timeline_id: str, request: CreateTrackRequest) -> TimelineTrack:
        """Add a new track to a timeline."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            tl = conn.execute("SELECT id FROM timelines WHERE id = ?", (timeline_id,)).fetchone()
            if not tl:
                raise NotFoundError(f"Timeline '{timeline_id}' not found.")

            # Calculate next track order if not provided
            if request.track_order is None:
                max_order = conn.execute(
                    "SELECT COALESCE(MAX(track_order), -1) as mo FROM timeline_tracks WHERE timeline_id = ?",
                    (timeline_id,),
                ).fetchone()["mo"]
                order = max_order + 1
            else:
                order = request.track_order

            track_id = f"tr_{uuid.uuid4().hex[:12]}"
            subtype = request.track_subtype or (
                TrackSubtype.MAIN_VIDEO if request.track_type == TrackType.VIDEO else
                TrackSubtype.SOURCE_AUDIO if request.track_type == TrackType.AUDIO else
                TrackSubtype.TEXT
            )
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            conn.execute(
                """
                INSERT INTO timeline_tracks (
                    id, timeline_id, name, track_type, track_subtype,
                    track_order, is_visible, is_muted, is_locked, height,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, 0, 0, 64, ?, ?)
                """,
                (track_id, timeline_id, request.name, request.track_type.value, subtype.value, order, now, now),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM timeline_tracks WHERE id = ?", (track_id,)).fetchone()
            return self._row_to_track(row, [])

    def update_track(self, track_id: str, request: UpdateTrackRequest) -> TimelineTrack:
        """Update track visibility, mute, lock, or name."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            track = conn.execute("SELECT * FROM timeline_tracks WHERE id = ?", (track_id,)).fetchone()
            if not track:
                raise NotFoundError(f"Track '{track_id}' not found.")

            updates = []
            params = []
            if request.name is not None:
                updates.append("name = ?")
                params.append(request.name)
            if request.is_visible is not None:
                updates.append("is_visible = ?")
                params.append(1 if request.is_visible else 0)
            if request.is_muted is not None:
                updates.append("is_muted = ?")
                params.append(1 if request.is_muted else 0)
            if request.is_locked is not None:
                updates.append("is_locked = ?")
                params.append(1 if request.is_locked else 0)
            if request.track_order is not None:
                updates.append("track_order = ?")
                params.append(request.track_order)
            if request.height is not None:
                updates.append("height = ?")
                params.append(max(32, request.height))

            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.datetime.now(datetime.timezone.utc).isoformat())
                params.append(track_id)
                conn.execute(f"UPDATE timeline_tracks SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()

            updated_row = conn.execute("SELECT * FROM timeline_tracks WHERE id = ?", (track_id,)).fetchone()
            clip_rows = conn.execute(
                "SELECT * FROM timeline_clips WHERE track_id = ? ORDER BY timeline_start ASC",
                (track_id,),
            ).fetchall()
            return self._row_to_track(updated_row, [self._row_to_clip(c) for c in clip_rows])

    def delete_track(self, track_id: str) -> None:
        """Delete a track and all its associated clips."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            track = conn.execute("SELECT timeline_id FROM timeline_tracks WHERE id = ?", (track_id,)).fetchone()
            if not track:
                raise NotFoundError(f"Track '{track_id}' not found.")
            timeline_id = track["timeline_id"]

            conn.execute("DELETE FROM timeline_tracks WHERE id = ?", (track_id,))
            self._recalculate_timeline_duration(conn, timeline_id)
            conn.commit()

    # -------------------------------------------------------------------------
    # Internal Hydration Helpers
    # -------------------------------------------------------------------------

    def _hydrate_timeline(self, conn: sqlite3.Connection, timeline_id: str) -> TimelineRecord:
        tl_row = conn.execute("SELECT * FROM timelines WHERE id = ?", (timeline_id,)).fetchone()
        if not tl_row:
            raise NotFoundError(f"Timeline '{timeline_id}' not found.")

        track_rows = conn.execute(
            "SELECT * FROM timeline_tracks WHERE timeline_id = ? ORDER BY track_order ASC",
            (timeline_id,),
        ).fetchall()

        clip_rows = conn.execute(
            "SELECT * FROM timeline_clips WHERE timeline_id = ? ORDER BY timeline_start ASC",
            (timeline_id,),
        ).fetchall()

        clips_by_track: Dict[str, List[TimelineClip]] = {}
        max_end = 0.0
        for cr in clip_rows:
            clip = self._row_to_clip(cr)
            clips_by_track.setdefault(clip.track_id, []).append(clip)
            if clip.timeline_end > max_end:
                max_end = clip.timeline_end

        tracks = [
            self._row_to_track(tr, clips_by_track.get(tr["id"], []))
            for tr in track_rows
        ]

        # Auto-update duration if changed
        recorded_duration = float(tl_row["duration"])
        if abs(recorded_duration - max_end) > 0.001:
            conn.execute(
                "UPDATE timelines SET duration = ?, updated_at = ? WHERE id = ?",
                (max_end, datetime.datetime.now(datetime.timezone.utc).isoformat(), timeline_id),
            )
            conn.commit()
            recorded_duration = max_end

        return TimelineRecord(
            id=tl_row["id"],
            project_id=tl_row["project_id"],
            name=tl_row["name"],
            duration=recorded_duration,
            fps=int(tl_row["fps"]),
            canvas_width=int(tl_row["canvas_width"]),
            canvas_height=int(tl_row["canvas_height"]),
            time_base=tl_row["time_base"],
            revision=int(tl_row["revision"]),
            is_active=bool(tl_row["is_active"]),
            created_at=tl_row["created_at"],
            updated_at=tl_row["updated_at"],
            tracks=tracks,
        )

    def _row_to_track(self, row: sqlite3.Row, clips: List[TimelineClip]) -> TimelineTrack:
        return TimelineTrack(
            id=row["id"],
            timeline_id=row["timeline_id"],
            name=row["name"],
            track_type=TrackType(row["track_type"]),
            track_subtype=TrackSubtype(row["track_subtype"]),
            track_order=int(row["track_order"]),
            is_visible=bool(row["is_visible"]),
            is_muted=bool(row["is_muted"]),
            is_locked=bool(row["is_locked"]),
            height=int(row["height"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            clips=clips,
        )

    def _row_to_clip(self, row: sqlite3.Row) -> TimelineClip:
        transform_dict = json.loads(row["transform_props"] or "{}")
        content_dict = json.loads(row["content_props"] or "{}")
        audio_dict = json.loads(row["audio_props"] or "{}")

        return TimelineClip(
            id=row["id"],
            timeline_id=row["timeline_id"],
            track_id=row["track_id"],
            source_media_id=row["source_media_id"],
            clip_type=ClipType(row["clip_type"]),
            name=row["name"],
            timeline_start=round(float(row["timeline_start"]), 4),
            timeline_end=round(float(row["timeline_end"]), 4),
            source_in=round(float(row["source_in"]), 4),
            source_out=round(float(row["source_out"]), 4),
            speed=float(row["speed"]),
            volume=float(row["volume"]),
            opacity=float(row["opacity"]),
            transform_props=TransformProps(**transform_dict),
            content_props=ContentProps(**content_dict),
            audio_props=AudioProps(**audio_dict),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _recalculate_timeline_duration(self, conn: sqlite3.Connection, timeline_id: str) -> float:
        row = conn.execute(
            "SELECT COALESCE(MAX(timeline_end), 0.0) as max_end FROM timeline_clips WHERE timeline_id = ?",
            (timeline_id,),
        ).fetchone()
        max_end = round(float(row["max_end"]), 4)
        conn.execute(
            "UPDATE timelines SET duration = ?, updated_at = ? WHERE id = ?",
            (max_end, datetime.datetime.now(datetime.timezone.utc).isoformat(), timeline_id),
        )
        return max_end
