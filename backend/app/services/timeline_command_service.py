"""Validated command processing service: Atomic, reversible timeline editing with persistent Undo/Redo."""

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
    AddTextOverlayRequest,
    AudioProps,
    ClipType,
    CommandType,
    ContentProps,
    InsertClipRequest,
    MoveClipRequest,
    SplitClipRequest,
    TimelineClip,
    TimelineCommandRecord,
    TimelineHistoryResponse,
    TimelineRecord,
    TrackType,
    TransformProps,
    TrimClipRequest,
    UpdateClipPropsRequest,
)
from app.services.timeline_service import TimelineService

logger = logging.getLogger("zezedit.timeline.commands")


class TimelineCommandService:
    """Processes validated editing commands with reversible state transitions and persistent undo/redo."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.layout = StorageLayout.from_root(self.settings.storage_root)
        self.db_path = db_path or self.layout.db_file
        self.timeline_service = TimelineService(self.settings, self.db_path)

    # -------------------------------------------------------------------------
    # Core Editing Commands
    # -------------------------------------------------------------------------

    def insert_clip(
        self,
        timeline_id: str,
        request: InsertClipRequest,
        executed_by: str = "user",
    ) -> TimelineClip:
        """Insert a clip onto a track, checking bounds and recording reversible history."""
        if request.duration <= 0.0:
            raise ValidationError(f"Clip duration must be positive, got {request.duration}s.")
        if request.timeline_start < 0.0:
            raise ValidationError(f"Timeline start must be non-negative, got {request.timeline_start}s.")
        if request.source_in < 0.0:
            raise ValidationError(f"Source in-point must be non-negative, got {request.source_in}s.")

        timeline_end = round(request.timeline_start + request.duration, 4)
        source_out = round(request.source_in + request.duration * request.speed, 4)
        clip_id = f"cl_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            tl = self._get_timeline_row(conn, timeline_id)
            tr = conn.execute(
                "SELECT * FROM timeline_tracks WHERE id = ? AND timeline_id = ?",
                (request.track_id, timeline_id),
            ).fetchone()
            if not tr:
                raise NotFoundError(f"Track '{request.track_id}' not found in timeline '{timeline_id}'.")
            if bool(tr["is_locked"]):
                raise ValidationError(f"Cannot insert clip into locked track '{tr['name']}'.")

            # Validate source media if present
            if request.source_media_id:
                media = conn.execute(
                    "SELECT duration_seconds FROM media_assets WHERE id = ?",
                    (request.source_media_id,),
                ).fetchone()
                if not media:
                    raise NotFoundError(f"Source media '{request.source_media_id}' not found.")
                media_dur = float(media["duration_seconds"] or 0.0)
                if media_dur > 0 and source_out > media_dur + 0.1:
                    logger.warning(
                        "Clip source_out (%.2fs) exceeds source duration (%.2fs); clamping",
                        source_out, media_dur
                    )

            t_props = request.transform_props.model_dump() if request.transform_props else {}
            c_props = request.content_props.model_dump() if request.content_props else {}
            a_props = request.audio_props.model_dump() if request.audio_props else {}

            conn.execute(
                """
                INSERT INTO timeline_clips (
                    id, timeline_id, track_id, source_media_id, clip_type, name,
                    timeline_start, timeline_end, source_in, source_out, speed,
                    volume, opacity, transform_props, content_props, audio_props,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0, ?, ?, ?, ?, ?)
                """,
                (
                    clip_id,
                    timeline_id,
                    request.track_id,
                    request.source_media_id,
                    request.clip_type.value,
                    request.name,
                    request.timeline_start,
                    timeline_end,
                    request.source_in,
                    source_out,
                    request.speed,
                    request.volume,
                    json.dumps(t_props),
                    json.dumps(c_props),
                    json.dumps(a_props),
                    now,
                    now,
                ),
            )

            # Record history
            payload = {
                "clip_id": clip_id,
                "track_id": request.track_id,
                "source_media_id": request.source_media_id,
                "clip_type": request.clip_type.value,
                "name": request.name,
                "timeline_start": request.timeline_start,
                "timeline_end": timeline_end,
                "source_in": request.source_in,
                "source_out": source_out,
                "speed": request.speed,
                "volume": request.volume,
                "transform_props": t_props,
                "content_props": c_props,
                "audio_props": a_props,
            }
            inverse_payload = {"clip_id": clip_id}

            self._record_command(
                conn=conn,
                timeline_id=timeline_id,
                command_type=CommandType.INSERT_CLIP.value,
                payload=payload,
                inverse_payload=inverse_payload,
                description=f"Insert clip '{request.name}' at {request.timeline_start:.2f}s",
                executed_by=executed_by,
            )

            self.timeline_service._recalculate_timeline_duration(conn, timeline_id)
            conn.commit()

            row = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (clip_id,)).fetchone()
            return self.timeline_service._row_to_clip(row)

    def move_clip(
        self,
        timeline_id: str,
        request: MoveClipRequest,
        executed_by: str = "user",
    ) -> TimelineClip:
        """Move a clip to a new start time or track."""
        if request.new_timeline_start < 0.0:
            raise ValidationError("New timeline start must be non-negative.")

        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            clip = conn.execute(
                "SELECT * FROM timeline_clips WHERE id = ? AND timeline_id = ?",
                (request.clip_id, timeline_id),
            ).fetchone()
            if not clip:
                raise NotFoundError(f"Clip '{request.clip_id}' not found in timeline '{timeline_id}'.")

            old_start = float(clip["timeline_start"])
            old_end = float(clip["timeline_end"])
            old_track_id = clip["track_id"]
            duration = round(old_end - old_start, 4)

            target_track_id = request.new_track_id or old_track_id
            target_track = conn.execute(
                "SELECT * FROM timeline_tracks WHERE id = ? AND timeline_id = ?",
                (target_track_id, timeline_id),
            ).fetchone()
            if not target_track:
                raise NotFoundError(f"Target track '{target_track_id}' not found.")
            if bool(target_track["is_locked"]):
                raise ValidationError("Cannot move clip to a locked track.")

            new_start = round(request.new_timeline_start, 4)
            new_end = round(new_start + duration, 4)
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            conn.execute(
                """
                UPDATE timeline_clips
                SET timeline_start = ?, timeline_end = ?, track_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_start, new_end, target_track_id, now, request.clip_id),
            )

            payload = {
                "clip_id": request.clip_id,
                "new_timeline_start": new_start,
                "new_track_id": target_track_id,
            }
            inverse_payload = {
                "clip_id": request.clip_id,
                "new_timeline_start": old_start,
                "new_track_id": old_track_id,
            }

            self._record_command(
                conn=conn,
                timeline_id=timeline_id,
                command_type=CommandType.MOVE_CLIP.value,
                payload=payload,
                inverse_payload=inverse_payload,
                description=f"Move clip '{clip['name']}' from {old_start:.2f}s to {new_start:.2f}s",
                executed_by=executed_by,
            )

            self.timeline_service._recalculate_timeline_duration(conn, timeline_id)
            conn.commit()

            row = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (request.clip_id,)).fetchone()
            return self.timeline_service._row_to_clip(row)

    def trim_clip(
        self,
        timeline_id: str,
        request: TrimClipRequest,
        executed_by: str = "user",
    ) -> TimelineClip:
        """Trim left or right boundary of a clip."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            clip = conn.execute(
                "SELECT * FROM timeline_clips WHERE id = ? AND timeline_id = ?",
                (request.clip_id, timeline_id),
            ).fetchone()
            if not clip:
                raise NotFoundError(f"Clip '{request.clip_id}' not found.")

            old_start = float(clip["timeline_start"])
            old_end = float(clip["timeline_end"])
            old_sin = float(clip["source_in"])
            old_sout = float(clip["source_out"])
            speed = float(clip["speed"])

            new_start = round(request.new_timeline_start if request.new_timeline_start is not None else old_start, 4)
            new_end = round(request.new_timeline_end if request.new_timeline_end is not None else old_end, 4)

            if new_start < 0.0:
                raise ValidationError("Timeline start cannot be negative.")
            if new_end <= new_start:
                raise ValidationError(f"Invalid trim: end time ({new_end:.2f}s) must be greater than start ({new_start:.2f}s).")

            # Calculate source in/out shifts based on delta
            delta_start = new_start - old_start
            delta_end = new_end - old_end

            new_sin = round(request.new_source_in if request.new_source_in is not None else old_sin + (delta_start * speed), 4)
            new_sout = round(request.new_source_out if request.new_source_out is not None else old_sout + (delta_end * speed), 4)

            if new_sin < 0.0:
                new_sin = 0.0
            if new_sout <= new_sin:
                new_sout = round(new_sin + (new_end - new_start) * speed, 4)

            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute(
                """
                UPDATE timeline_clips
                SET timeline_start = ?, timeline_end = ?, source_in = ?, source_out = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_start, new_end, new_sin, new_sout, now, request.clip_id),
            )

            payload = {
                "clip_id": request.clip_id,
                "timeline_start": new_start,
                "timeline_end": new_end,
                "source_in": new_sin,
                "source_out": new_sout,
            }
            inverse_payload = {
                "clip_id": request.clip_id,
                "timeline_start": old_start,
                "timeline_end": old_end,
                "source_in": old_sin,
                "source_out": old_sout,
            }

            self._record_command(
                conn=conn,
                timeline_id=timeline_id,
                command_type=CommandType.TRIM_CLIP.value,
                payload=payload,
                inverse_payload=inverse_payload,
                description=f"Trim clip '{clip['name']}' to [{new_start:.2f}s - {new_end:.2f}s]",
                executed_by=executed_by,
            )

            self.timeline_service._recalculate_timeline_duration(conn, timeline_id)
            conn.commit()

            row = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (request.clip_id,)).fetchone()
            return self.timeline_service._row_to_clip(row)

    def split_clip(
        self,
        timeline_id: str,
        request: SplitClipRequest,
        executed_by: str = "user",
    ) -> Tuple[TimelineClip, TimelineClip]:
        """Split a clip at an exact timeline timestamp into two adjacent clips."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            clip = conn.execute(
                "SELECT * FROM timeline_clips WHERE id = ? AND timeline_id = ?",
                (request.clip_id, timeline_id),
            ).fetchone()
            if not clip:
                raise NotFoundError(f"Clip '{request.clip_id}' not found.")

            c_start = float(clip["timeline_start"])
            c_end = float(clip["timeline_end"])
            split_t = round(request.split_time, 4)

            if split_t <= c_start + 0.05 or split_t >= c_end - 0.05:
                raise ValidationError(
                    f"Split time {split_t:.2f}s must be strictly inside clip bounds [{c_start:.2f}s - {c_end:.2f}s]."
                )

            speed = float(clip["speed"])
            orig_sin = float(clip["source_in"])
            orig_sout = float(clip["source_out"])

            # Left clip: [c_start, split_t]
            # Right clip: [split_t, c_end]
            left_end = split_t
            right_start = split_t

            left_sout = round(orig_sin + (split_t - c_start) * speed, 4)
            right_sin = left_sout
            right_sout = orig_sout

            new_clip_id = f"cl_{uuid.uuid4().hex[:12]}"
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # 1. Update left clip (original)
            conn.execute(
                """
                UPDATE timeline_clips
                SET timeline_end = ?, source_out = ?, updated_at = ?
                WHERE id = ?
                """,
                (left_end, left_sout, now, request.clip_id),
            )

            # 2. Insert right clip
            conn.execute(
                """
                INSERT INTO timeline_clips (
                    id, timeline_id, track_id, source_media_id, clip_type, name,
                    timeline_start, timeline_end, source_in, source_out, speed,
                    volume, opacity, transform_props, content_props, audio_props,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_clip_id,
                    timeline_id,
                    clip["track_id"],
                    clip["source_media_id"],
                    clip["clip_type"],
                    f"{clip['name']} (Part 2)",
                    right_start,
                    c_end,
                    right_sin,
                    right_sout,
                    speed,
                    float(clip["volume"]),
                    float(clip["opacity"]),
                    clip["transform_props"],
                    clip["content_props"],
                    clip["audio_props"],
                    now,
                    now,
                ),
            )

            payload = {
                "left_clip_id": request.clip_id,
                "right_clip_id": new_clip_id,
                "split_time": split_t,
            }
            inverse_payload = {
                "left_clip_id": request.clip_id,
                "right_clip_id": new_clip_id,
                "orig_end": c_end,
                "orig_sout": orig_sout,
            }

            self._record_command(
                conn=conn,
                timeline_id=timeline_id,
                command_type=CommandType.SPLIT_CLIP.value,
                payload=payload,
                inverse_payload=inverse_payload,
                description=f"Split clip '{clip['name']}' at {split_t:.2f}s",
                executed_by=executed_by,
            )

            self.timeline_service._recalculate_timeline_duration(conn, timeline_id)
            conn.commit()

            left_row = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (request.clip_id,)).fetchone()
            right_row = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (new_clip_id,)).fetchone()
            return (
                self.timeline_service._row_to_clip(left_row),
                self.timeline_service._row_to_clip(right_row),
            )

    def delete_clip(
        self,
        timeline_id: str,
        clip_id: str,
        executed_by: str = "user",
    ) -> None:
        """Delete a clip from a timeline with reversible undo recovery."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            clip = conn.execute(
                "SELECT * FROM timeline_clips WHERE id = ? AND timeline_id = ?",
                (clip_id, timeline_id),
            ).fetchone()
            if not clip:
                raise NotFoundError(f"Clip '{clip_id}' not found in timeline '{timeline_id}'.")

            # Stash entire clip attributes for inverse command
            inverse_payload = {
                "id": clip["id"],
                "track_id": clip["track_id"],
                "source_media_id": clip["source_media_id"],
                "clip_type": clip["clip_type"],
                "name": clip["name"],
                "timeline_start": float(clip["timeline_start"]),
                "timeline_end": float(clip["timeline_end"]),
                "source_in": float(clip["source_in"]),
                "source_out": float(clip["source_out"]),
                "speed": float(clip["speed"]),
                "volume": float(clip["volume"]),
                "opacity": float(clip["opacity"]),
                "transform_props": json.loads(clip["transform_props"] or "{}"),
                "content_props": json.loads(clip["content_props"] or "{}"),
                "audio_props": json.loads(clip["audio_props"] or "{}"),
            }
            payload = {"clip_id": clip_id}

            conn.execute("DELETE FROM timeline_clips WHERE id = ?", (clip_id,))

            self._record_command(
                conn=conn,
                timeline_id=timeline_id,
                command_type=CommandType.DELETE_CLIP.value,
                payload=payload,
                inverse_payload=inverse_payload,
                description=f"Delete clip '{clip['name']}'",
                executed_by=executed_by,
            )

            self.timeline_service._recalculate_timeline_duration(conn, timeline_id)
            conn.commit()

    def duplicate_clip(
        self,
        timeline_id: str,
        clip_id: str,
        executed_by: str = "user",
    ) -> TimelineClip:
        """Duplicate an existing clip and append it right after."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            clip = conn.execute(
                "SELECT * FROM timeline_clips WHERE id = ? AND timeline_id = ?",
                (clip_id, timeline_id),
            ).fetchone()
            if not clip:
                raise NotFoundError(f"Clip '{clip_id}' not found.")

            duration = round(float(clip["timeline_end"]) - float(clip["timeline_start"]), 4)
            new_start = round(float(clip["timeline_end"]), 4)
            new_end = round(new_start + duration, 4)
            new_id = f"cl_{uuid.uuid4().hex[:12]}"
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            conn.execute(
                """
                INSERT INTO timeline_clips (
                    id, timeline_id, track_id, source_media_id, clip_type, name,
                    timeline_start, timeline_end, source_in, source_out, speed,
                    volume, opacity, transform_props, content_props, audio_props,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id,
                    timeline_id,
                    clip["track_id"],
                    clip["source_media_id"],
                    clip["clip_type"],
                    f"{clip['name']} (Copy)",
                    new_start,
                    new_end,
                    float(clip["source_in"]),
                    float(clip["source_out"]),
                    float(clip["speed"]),
                    float(clip["volume"]),
                    float(clip["opacity"]),
                    clip["transform_props"],
                    clip["content_props"],
                    clip["audio_props"],
                    now,
                    now,
                ),
            )

            payload = {"clip_id": new_id}
            inverse_payload = {"clip_id": new_id}

            self._record_command(
                conn=conn,
                timeline_id=timeline_id,
                command_type=CommandType.DUPLICATE_CLIP.value,
                payload=payload,
                inverse_payload=inverse_payload,
                description=f"Duplicate clip '{clip['name']}'",
                executed_by=executed_by,
            )

            self.timeline_service._recalculate_timeline_duration(conn, timeline_id)
            conn.commit()

            row = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (new_id,)).fetchone()
            return self.timeline_service._row_to_clip(row)

    def update_clip_props(
        self,
        timeline_id: str,
        request: UpdateClipPropsRequest,
        executed_by: str = "user",
    ) -> TimelineClip:
        """Update volume, speed, transform, or content properties with undo tracking."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            clip = conn.execute(
                "SELECT * FROM timeline_clips WHERE id = ? AND timeline_id = ?",
                (request.clip_id, timeline_id),
            ).fetchone()
            if not clip:
                raise NotFoundError(f"Clip '{request.clip_id}' not found.")

            old_state = {
                "name": clip["name"],
                "speed": float(clip["speed"]),
                "volume": float(clip["volume"]),
                "opacity": float(clip["opacity"]),
                "transform_props": json.loads(clip["transform_props"] or "{}"),
                "content_props": json.loads(clip["content_props"] or "{}"),
                "audio_props": json.loads(clip["audio_props"] or "{}"),
            }

            updates = []
            params = []
            if request.name is not None:
                updates.append("name = ?")
                params.append(request.name)
            if request.speed is not None:
                if request.speed <= 0.1 or request.speed > 10.0:
                    raise ValidationError("Speed must be between 0.1 and 10.0.")
                updates.append("speed = ?")
                params.append(request.speed)
            if request.volume is not None:
                updates.append("volume = ?")
                params.append(max(0.0, request.volume))
            if request.opacity is not None:
                updates.append("opacity = ?")
                params.append(max(0.0, min(1.0, request.opacity)))
            if request.transform_props is not None:
                updates.append("transform_props = ?")
                params.append(json.dumps(request.transform_props.model_dump()))
            if request.content_props is not None:
                updates.append("content_props = ?")
                params.append(json.dumps(request.content_props.model_dump()))
            if request.audio_props is not None:
                updates.append("audio_props = ?")
                params.append(json.dumps(request.audio_props.model_dump()))

            if updates:
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                updates.append("updated_at = ?")
                params.append(now)
                params.append(request.clip_id)
                conn.execute(f"UPDATE timeline_clips SET {', '.join(updates)} WHERE id = ?", params)

                new_row = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (request.clip_id,)).fetchone()
                new_state = {
                    "name": new_row["name"],
                    "speed": float(new_row["speed"]),
                    "volume": float(new_row["volume"]),
                    "opacity": float(new_row["opacity"]),
                    "transform_props": json.loads(new_row["transform_props"] or "{}"),
                    "content_props": json.loads(new_row["content_props"] or "{}"),
                    "audio_props": json.loads(new_row["audio_props"] or "{}"),
                }

                self._record_command(
                    conn=conn,
                    timeline_id=timeline_id,
                    command_type=CommandType.UPDATE_CLIP_PROPS.value,
                    payload={"clip_id": request.clip_id, "state": new_state},
                    inverse_payload={"clip_id": request.clip_id, "state": old_state},
                    description=f"Update properties for clip '{clip['name']}'",
                    executed_by=executed_by,
                )
                conn.commit()

            row = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (request.clip_id,)).fetchone()
            return self.timeline_service._row_to_clip(row)

    def add_text_overlay(
        self,
        timeline_id: str,
        request: AddTextOverlayRequest,
        executed_by: str = "user",
    ) -> TimelineClip:
        """Add a text overlay clip, locating or creating an overlay track automatically."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            target_track_id = request.track_id
            if not target_track_id:
                # Find first overlay track
                track_row = conn.execute(
                    "SELECT id FROM timeline_tracks WHERE timeline_id = ? AND track_type = ? ORDER BY track_order ASC LIMIT 1",
                    (timeline_id, TrackType.OVERLAY.value),
                ).fetchone()
                if track_row:
                    target_track_id = track_row["id"]
                else:
                    # Create overlay track
                    tr_id = f"tr_{uuid.uuid4().hex[:12]}"
                    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    conn.execute(
                        """
                        INSERT INTO timeline_tracks (
                            id, timeline_id, name, track_type, track_subtype,
                            track_order, is_visible, is_muted, is_locked, height,
                            created_at, updated_at
                        ) VALUES (?, ?, 'Overlays', 'overlay', 'text', 0, 1, 0, 0, 56, ?, ?)
                        """,
                        (tr_id, timeline_id, now, now),
                    )
                    target_track_id = tr_id

        return self.insert_clip(
            timeline_id=timeline_id,
            request=InsertClipRequest(
                track_id=target_track_id,
                clip_type=ClipType.TEXT,
                name=f"Text: {request.text[:20]}",
                timeline_start=request.timeline_start,
                duration=request.duration,
                content_props=ContentProps(
                    text=request.text,
                    font_size=request.font_size,
                    color=request.color,
                    alignment=request.alignment,
                ),
                transform_props=TransformProps(x=request.x, y=request.y),
            ),
            executed_by=executed_by,
        )

    # -------------------------------------------------------------------------
    # Persistent Undo & Redo Engine
    # -------------------------------------------------------------------------

    def get_history(self, timeline_id: str) -> TimelineHistoryResponse:
        """Fetch command history and available undo/redo states."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            tl = self._get_timeline_row(conn, timeline_id)
            current_revision = int(tl["revision"])

            rows = conn.execute(
                "SELECT * FROM timeline_commands WHERE timeline_id = ? ORDER BY revision_after ASC",
                (timeline_id,),
            ).fetchall()

            history = []
            for r in rows:
                history.append(
                    TimelineCommandRecord(
                        id=r["id"],
                        timeline_id=r["timeline_id"],
                        command_type=r["command_type"],
                        payload=json.loads(r["payload"]),
                        inverse_payload=json.loads(r["inverse_payload"]),
                        revision_before=int(r["revision_before"]),
                        revision_after=int(r["revision_after"]),
                        description=r["description"],
                        executed_by=r["executed_by"],
                        is_undone=bool(r["is_undone"]),
                        created_at=r["created_at"],
                    )
                )

            # Check if undo is available (at least one non-undone command)
            can_undo = any(not h.is_undone for h in history)
            # Check if redo is available (at least one undone command)
            can_redo = any(h.is_undone for h in history)

            return TimelineHistoryResponse(
                timeline_id=timeline_id,
                current_revision=current_revision,
                can_undo=can_undo,
                can_redo=can_redo,
                history=history,
            )

    def undo(self, timeline_id: str) -> TimelineRecord:
        """Revert the most recent applied operation using its recorded inverse payload."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            tl = self._get_timeline_row(conn, timeline_id)

            # Find the latest command that is not undone
            cmd = conn.execute(
                """
                SELECT * FROM timeline_commands
                WHERE timeline_id = ? AND is_undone = 0
                ORDER BY revision_after DESC LIMIT 1
                """,
                (timeline_id,),
            ).fetchone()

            if not cmd:
                raise ValidationError("No actions available to undo.")

            cmd_type = cmd["command_type"]
            inverse_payload = json.loads(cmd["inverse_payload"])

            self._apply_inverse(conn, timeline_id, cmd_type, inverse_payload)

            # Mark command as undone and bump timeline revision
            new_rev = int(tl["revision"]) + 1
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute("UPDATE timeline_commands SET is_undone = 1 WHERE id = ?", (cmd["id"],))
            conn.execute(
                "UPDATE timelines SET revision = ?, updated_at = ? WHERE id = ?",
                (new_rev, now, timeline_id),
            )
            self.timeline_service._recalculate_timeline_duration(conn, timeline_id)
            conn.commit()

            return self.timeline_service.get_timeline(timeline_id)

    def redo(self, timeline_id: str) -> TimelineRecord:
        """Reapply the next undone operation."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            tl = self._get_timeline_row(conn, timeline_id)

            # Find the earliest undone command
            cmd = conn.execute(
                """
                SELECT * FROM timeline_commands
                WHERE timeline_id = ? AND is_undone = 1
                ORDER BY revision_after ASC LIMIT 1
                """,
                (timeline_id,),
            ).fetchone()

            if not cmd:
                raise ValidationError("No actions available to redo.")

            cmd_type = cmd["command_type"]
            payload = json.loads(cmd["payload"])

            self._apply_forward(conn, timeline_id, cmd_type, payload)

            new_rev = int(tl["revision"]) + 1
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute("UPDATE timeline_commands SET is_undone = 0 WHERE id = ?", (cmd["id"],))
            conn.execute(
                "UPDATE timelines SET revision = ?, updated_at = ? WHERE id = ?",
                (new_rev, now, timeline_id),
            )
            self.timeline_service._recalculate_timeline_duration(conn, timeline_id)
            conn.commit()

            return self.timeline_service.get_timeline(timeline_id)

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _get_timeline_row(self, conn: sqlite3.Connection, timeline_id: str) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM timelines WHERE id = ?", (timeline_id,)).fetchone()
        if not row:
            raise NotFoundError(f"Timeline '{timeline_id}' not found.")
        return row

    def _record_command(
        self,
        conn: sqlite3.Connection,
        timeline_id: str,
        command_type: str,
        payload: Dict[str, Any],
        inverse_payload: Dict[str, Any],
        description: str,
        executed_by: str,
    ) -> None:
        tl = self._get_timeline_row(conn, timeline_id)
        current_rev = int(tl["revision"])
        next_rev = current_rev + 1

        # Truncate any previous redo branch beyond this point
        conn.execute(
            "DELETE FROM timeline_commands WHERE timeline_id = ? AND is_undone = 1",
            (timeline_id,),
        )

        cmd_id = f"cmd_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        conn.execute(
            """
            INSERT INTO timeline_commands (
                id, timeline_id, command_type, payload, inverse_payload,
                revision_before, revision_after, description, executed_by,
                is_undone, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                cmd_id,
                timeline_id,
                command_type,
                json.dumps(payload),
                json.dumps(inverse_payload),
                current_rev,
                next_rev,
                description,
                executed_by,
                now,
            ),
        )

        conn.execute(
            "UPDATE timelines SET revision = ?, updated_at = ? WHERE id = ?",
            (next_rev, now, timeline_id),
        )

    def _apply_inverse(
        self,
        conn: sqlite3.Connection,
        timeline_id: str,
        cmd_type: str,
        inv: Dict[str, Any],
    ) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if cmd_type == CommandType.INSERT_CLIP.value:
            conn.execute("DELETE FROM timeline_clips WHERE id = ?", (inv["clip_id"],))

        elif cmd_type == CommandType.DELETE_CLIP.value:
            conn.execute(
                """
                INSERT INTO timeline_clips (
                    id, timeline_id, track_id, source_media_id, clip_type, name,
                    timeline_start, timeline_end, source_in, source_out, speed,
                    volume, opacity, transform_props, content_props, audio_props,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inv["id"],
                    timeline_id,
                    inv["track_id"],
                    inv["source_media_id"],
                    inv["clip_type"],
                    inv["name"],
                    inv["timeline_start"],
                    inv["timeline_end"],
                    inv["source_in"],
                    inv["source_out"],
                    inv["speed"],
                    inv["volume"],
                    inv["opacity"],
                    json.dumps(inv["transform_props"]),
                    json.dumps(inv["content_props"]),
                    json.dumps(inv["audio_props"]),
                    now,
                    now,
                ),
            )

        elif cmd_type == CommandType.MOVE_CLIP.value:
            conn.execute(
                """
                UPDATE timeline_clips
                SET timeline_start = ?, timeline_end = timeline_start + (timeline_end - timeline_start),
                    track_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (inv["new_timeline_start"], inv["new_track_id"], now, inv["clip_id"]),
            )

        elif cmd_type == CommandType.TRIM_CLIP.value:
            conn.execute(
                """
                UPDATE timeline_clips
                SET timeline_start = ?, timeline_end = ?, source_in = ?, source_out = ?, updated_at = ?
                WHERE id = ?
                """,
                (inv["timeline_start"], inv["timeline_end"], inv["source_in"], inv["source_out"], now, inv["clip_id"]),
            )

        elif cmd_type == CommandType.SPLIT_CLIP.value:
            # Delete right clip and restore left clip's original end and source_out
            conn.execute("DELETE FROM timeline_clips WHERE id = ?", (inv["right_clip_id"],))
            conn.execute(
                "UPDATE timeline_clips SET timeline_end = ?, source_out = ?, updated_at = ? WHERE id = ?",
                (inv["orig_end"], inv["orig_sout"], now, inv["left_clip_id"]),
            )

        elif cmd_type == CommandType.DUPLICATE_CLIP.value:
            conn.execute("DELETE FROM timeline_clips WHERE id = ?", (inv["clip_id"],))

        elif cmd_type == CommandType.UPDATE_CLIP_PROPS.value:
            state = inv["state"]
            conn.execute(
                """
                UPDATE timeline_clips
                SET name = ?, speed = ?, volume = ?, opacity = ?,
                    transform_props = ?, content_props = ?, audio_props = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    state["name"],
                    state["speed"],
                    state["volume"],
                    state["opacity"],
                    json.dumps(state["transform_props"]),
                    json.dumps(state["content_props"]),
                    json.dumps(state["audio_props"]),
                    now,
                    inv["clip_id"],
                ),
            )

    def _apply_forward(
        self,
        conn: sqlite3.Connection,
        timeline_id: str,
        cmd_type: str,
        payload: Dict[str, Any],
    ) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if cmd_type == CommandType.INSERT_CLIP.value:
            conn.execute(
                """
                INSERT INTO timeline_clips (
                    id, timeline_id, track_id, source_media_id, clip_type, name,
                    timeline_start, timeline_end, source_in, source_out, speed,
                    volume, opacity, transform_props, content_props, audio_props,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0, ?, ?, ?, ?, ?)
                """,
                (
                    payload["clip_id"],
                    timeline_id,
                    payload["track_id"],
                    payload["source_media_id"],
                    payload["clip_type"],
                    payload["name"],
                    payload["timeline_start"],
                    payload["timeline_end"],
                    payload["source_in"],
                    payload["source_out"],
                    payload["speed"],
                    payload["volume"],
                    json.dumps(payload["transform_props"]),
                    json.dumps(payload["content_props"]),
                    json.dumps(payload["audio_props"]),
                    now,
                    now,
                ),
            )

        elif cmd_type == CommandType.DELETE_CLIP.value:
            conn.execute("DELETE FROM timeline_clips WHERE id = ?", (payload["clip_id"],))

        elif cmd_type == CommandType.MOVE_CLIP.value:
            clip = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (payload["clip_id"],)).fetchone()
            dur = float(clip["timeline_end"]) - float(clip["timeline_start"])
            conn.execute(
                """
                UPDATE timeline_clips
                SET timeline_start = ?, timeline_end = ?, track_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload["new_timeline_start"],
                    round(payload["new_timeline_start"] + dur, 4),
                    payload["new_track_id"],
                    now,
                    payload["clip_id"],
                ),
            )

        elif cmd_type == CommandType.TRIM_CLIP.value:
            conn.execute(
                """
                UPDATE timeline_clips
                SET timeline_start = ?, timeline_end = ?, source_in = ?, source_out = ?, updated_at = ?
                WHERE id = ?
                """,
                (payload["timeline_start"], payload["timeline_end"], payload["source_in"], payload["source_out"], now, payload["clip_id"]),
            )

        elif cmd_type == CommandType.SPLIT_CLIP.value:
            # Reapply split
            split_t = payload["split_time"]
            left_clip = conn.execute("SELECT * FROM timeline_clips WHERE id = ?", (payload["left_clip_id"],)).fetchone()
            dur = float(left_clip["timeline_end"]) - float(left_clip["timeline_start"])
            speed = float(left_clip["speed"])
            orig_sin = float(left_clip["source_in"])
            orig_sout = float(left_clip["source_out"])
            orig_end = float(left_clip["timeline_end"])

            conn.execute(
                "UPDATE timeline_clips SET timeline_end = ?, source_out = ?, updated_at = ? WHERE id = ?",
                (split_t, orig_sin + (split_t - float(left_clip["timeline_start"])) * speed, now, payload["left_clip_id"]),
            )
            conn.execute(
                """
                INSERT INTO timeline_clips (
                    id, timeline_id, track_id, source_media_id, clip_type, name,
                    timeline_start, timeline_end, source_in, source_out, speed,
                    volume, opacity, transform_props, content_props, audio_props,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["right_clip_id"],
                    timeline_id,
                    left_clip["track_id"],
                    left_clip["source_media_id"],
                    left_clip["clip_type"],
                    f"{left_clip['name']} (Part 2)",
                    split_t,
                    orig_end,
                    orig_sin + (split_t - float(left_clip["timeline_start"])) * speed,
                    orig_sout,
                    speed,
                    float(left_clip["volume"]),
                    float(left_clip["opacity"]),
                    left_clip["transform_props"],
                    left_clip["content_props"],
                    left_clip["audio_props"],
                    now,
                    now,
                ),
            )

        elif cmd_type == CommandType.DUPLICATE_CLIP.value:
            pass  # Already saved or recreated

        elif cmd_type == CommandType.UPDATE_CLIP_PROPS.value:
            state = payload["state"]
            conn.execute(
                """
                UPDATE timeline_clips
                SET name = ?, speed = ?, volume = ?, opacity = ?,
                    transform_props = ?, content_props = ?, audio_props = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    state["name"],
                    state["speed"],
                    state["volume"],
                    state["opacity"],
                    json.dumps(state["transform_props"]),
                    json.dumps(state["content_props"]),
                    json.dumps(state["audio_props"]),
                    now,
                    payload["clip_id"],
                ),
            )
