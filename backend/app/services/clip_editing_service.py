"""Candidate clip editing service: trimming, aspect ratio framing, manual positioning, and smart tracking."""

import datetime
import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.models.entities import CandidateClipEditRecord
from app.services.reframing_service import ReframingService

logger = logging.getLogger("zezedit.clip_editing.service")

VALID_ASPECT_RATIOS = {"9:16", "1:1", "16:9", "4:5"}
VALID_FRAMING_MODES = {"center", "manual", "smart_tracking"}


class ClipEditingService:
    """Manages isolated candidate clip edits, preserving pristine discovery data."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.layout = StorageLayout.from_root(self.settings.storage_root)
        self.db_path = db_path or self.layout.db_file
        self.reframing_service = ReframingService(
            settings=self.settings,
            db_path=self.db_path,
        )

    def get_or_create_edit(
        self,
        candidate_id: str,
        project_id: str,
        media_asset_id: str,
    ) -> Dict[str, Any]:
        """Retrieve existing candidate edit or create initial draft from candidate bounds."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Verify candidate exists and retrieve original bounds
            cand = conn.execute(
                """
                SELECT id, project_id, media_asset_id, start_time, end_time, duration, title
                FROM shorts_candidates
                WHERE id = ? AND project_id = ? AND media_asset_id = ?
                """,
                (candidate_id, project_id, media_asset_id),
            ).fetchone()
            if not cand:
                raise NotFoundError(
                    f"Candidate '{candidate_id}' not found for media '{media_asset_id}' in project '{project_id}'."
                )

            # Retrieve media metadata
            asset = conn.execute(
                """
                SELECT duration_seconds, width, height FROM media_assets
                WHERE id = ? AND project_id = ?
                """,
                (media_asset_id, project_id),
            ).fetchone()
            media_duration = float(asset["duration_seconds"] or 0.0) if asset else 0.0
            media_width = int(asset["width"] or 1920) if asset else 1920
            media_height = int(asset["height"] or 1080) if asset else 1080

            # Check if edit already exists
            row = conn.execute(
                """
                SELECT * FROM candidate_clip_edits
                WHERE candidate_id = ?
                """,
                (candidate_id,),
            ).fetchone()

            if row:
                edit_dict = dict(row)
                edit_dict["media_duration"] = media_duration
                edit_dict["media_width"] = media_width
                edit_dict["media_height"] = media_height
                edit_dict["candidate_title"] = cand["title"] or f"Candidate {candidate_id[:8]}"
                return edit_dict

            # Create default edit record
            edit_id = f"cce_{uuid.uuid4().hex[:12]}"
            orig_start = round(float(cand["start_time"]), 3)
            orig_end = round(float(cand["end_time"]), 3)
            orig_duration = max(0.5, round(orig_end - orig_start, 3))
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            conn.execute(
                """
                INSERT INTO candidate_clip_edits (
                    id, candidate_id, project_id, media_asset_id,
                    original_start_time, original_end_time,
                    edited_start_time, edited_end_time, edited_duration,
                    aspect_ratio, framing_mode,
                    manual_crop_x_pct, manual_crop_y_pct, manual_crop_zoom,
                    tracked_subject_id, tracking_status, reframing_plan_id,
                    version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '9:16', 'center', 50.0, 50.0, 1.0, NULL, 'none', NULL, 1, ?, ?)
                """,
                (
                    edit_id, candidate_id, project_id, media_asset_id,
                    orig_start, orig_end,
                    orig_start, orig_end, orig_duration,
                    now, now,
                ),
            )

            created_row = conn.execute(
                "SELECT * FROM candidate_clip_edits WHERE id = ?",
                (edit_id,),
            ).fetchone()

            edit_dict = dict(created_row)
            edit_dict["media_duration"] = media_duration
            edit_dict["media_width"] = media_width
            edit_dict["media_height"] = media_height
            edit_dict["candidate_title"] = cand["title"] or f"Candidate {candidate_id[:8]}"
            return edit_dict

    def save_edit(
        self,
        candidate_id: str,
        project_id: str,
        media_asset_id: str,
        edited_start_time: float,
        edited_end_time: float,
        aspect_ratio: str = "9:16",
        framing_mode: str = "center",
        manual_crop_x_pct: float = 50.0,
        manual_crop_y_pct: float = 50.0,
        manual_crop_zoom: float = 1.0,
        tracked_subject_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate and persist edited clip boundaries and framing parameters."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 1. Fetch asset duration for boundary checking
            asset = conn.execute(
                "SELECT duration_seconds, width, height FROM media_assets WHERE id = ? AND project_id = ?",
                (media_asset_id, project_id),
            ).fetchone()
            if not asset:
                raise NotFoundError(f"Media asset '{media_asset_id}' not found.")
            media_dur = float(asset["duration_seconds"] or 36000.0)

            # 2. Validate timestamps
            if edited_start_time < 0.0:
                raise ValidationError("Start time cannot be negative.")
            if edited_end_time > media_dur + 0.1:
                raise ValidationError(f"End time ({edited_end_time:.2f}s) exceeds media duration ({media_dur:.2f}s).")
            if edited_start_time >= edited_end_time:
                raise ValidationError("Start time must be strictly before end time.")
            new_duration = round(edited_end_time - edited_start_time, 3)
            if new_duration < 1.0:
                raise ValidationError("Clip duration must be at least 1.0 second.")

            # 3. Validate aspect ratio and framing mode
            if aspect_ratio not in VALID_ASPECT_RATIOS:
                raise ValidationError(f"Invalid aspect ratio '{aspect_ratio}'. Must be one of {sorted(VALID_ASPECT_RATIOS)}")
            if framing_mode not in VALID_FRAMING_MODES:
                raise ValidationError(f"Invalid framing mode '{framing_mode}'. Must be one of {sorted(VALID_FRAMING_MODES)}")

            # 4. Validate manual crop ranges
            x_pct = max(0.0, min(100.0, float(manual_crop_x_pct)))
            y_pct = max(0.0, min(100.0, float(manual_crop_y_pct)))
            zoom = max(1.0, min(2.5, float(manual_crop_zoom)))

            # 5. Ensure edit record exists
            existing = conn.execute(
                "SELECT * FROM candidate_clip_edits WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            if not existing:
                cand = conn.execute(
                    "SELECT start_time, end_time FROM shorts_candidates WHERE id = ?",
                    (candidate_id,),
                ).fetchone()
                if not cand:
                    raise NotFoundError(f"Candidate '{candidate_id}' not found.")
                orig_start = float(cand["start_time"])
                orig_end = float(cand["end_time"])
                edit_id = f"cce_{uuid.uuid4().hex[:12]}"

                conn.execute(
                    """
                    INSERT INTO candidate_clip_edits (
                        id, candidate_id, project_id, media_asset_id,
                        original_start_time, original_end_time,
                        edited_start_time, edited_end_time, edited_duration,
                        aspect_ratio, framing_mode,
                        manual_crop_x_pct, manual_crop_y_pct, manual_crop_zoom,
                        tracked_subject_id, tracking_status, reframing_plan_id,
                        version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'none', NULL, 1, ?, ?)
                    """,
                    (
                        edit_id, candidate_id, project_id, media_asset_id,
                        orig_start, orig_end,
                        round(edited_start_time, 3), round(edited_end_time, 3), new_duration,
                        aspect_ratio, framing_mode,
                        x_pct, y_pct, zoom,
                        tracked_subject_id,
                        now, now,
                    ),
                )
            else:
                edit_id = existing["id"]
                conn.execute(
                    """
                    UPDATE candidate_clip_edits
                    SET edited_start_time = ?,
                        edited_end_time = ?,
                        edited_duration = ?,
                        aspect_ratio = ?,
                        framing_mode = ?,
                        manual_crop_x_pct = ?,
                        manual_crop_y_pct = ?,
                        manual_crop_zoom = ?,
                        tracked_subject_id = ?,
                        version = version + 1,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        round(edited_start_time, 3),
                        round(edited_end_time, 3),
                        new_duration,
                        aspect_ratio,
                        framing_mode,
                        x_pct,
                        y_pct,
                        zoom,
                        tracked_subject_id,
                        now,
                        edit_id,
                    ),
                )

            updated = conn.execute(
                "SELECT * FROM candidate_clip_edits WHERE id = ?",
                (edit_id,),
            ).fetchone()
            d = dict(updated)
            d["media_duration"] = media_dur
            d["media_width"] = int(asset["width"] or 1920)
            d["media_height"] = int(asset["height"] or 1080)
            return d

    def reset_to_original(
        self,
        candidate_id: str,
        project_id: str,
        media_asset_id: str,
    ) -> Dict[str, Any]:
        """Reset edited timestamps and framing back to initial discovery state."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            existing = conn.execute(
                "SELECT * FROM candidate_clip_edits WHERE candidate_id = ? AND project_id = ?",
                (candidate_id, project_id),
            ).fetchone()

            if not existing:
                # Initialize it first
                return self.get_or_create_edit(candidate_id, project_id, media_asset_id)

            orig_start = float(existing["original_start_time"])
            orig_end = float(existing["original_end_time"])
            orig_duration = max(0.5, round(orig_end - orig_start, 3))
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            conn.execute(
                """
                UPDATE candidate_clip_edits
                SET edited_start_time = ?,
                    edited_end_time = ?,
                    edited_duration = ?,
                    aspect_ratio = '9:16',
                    framing_mode = 'center',
                    manual_crop_x_pct = 50.0,
                    manual_crop_y_pct = 50.0,
                    manual_crop_zoom = 1.0,
                    tracked_subject_id = NULL,
                    tracking_status = 'none',
                    version = version + 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (orig_start, orig_end, orig_duration, now, existing["id"]),
            )

            updated = conn.execute(
                "SELECT * FROM candidate_clip_edits WHERE id = ?",
                (existing["id"],),
            ).fetchone()

            asset = conn.execute(
                "SELECT duration_seconds, width, height FROM media_assets WHERE id = ?",
                (media_asset_id,),
            ).fetchone()

            d = dict(updated)
            d["media_duration"] = float(asset["duration_seconds"] or 0.0) if asset else 0.0
            d["media_width"] = int(asset["width"] or 1920) if asset else 1920
            d["media_height"] = int(asset["height"] or 1080) if asset else 1080
            return d

    def run_clip_tracking(
        self,
        candidate_id: str,
        project_id: str,
        media_asset_id: str,
        target_aspect_ratio: str = "9:16",
    ) -> Dict[str, Any]:
        """Trigger smart subject tracking over the edited interval without decoding full video."""
        # 1. Fetch current edit boundaries
        current_edit = self.get_or_create_edit(candidate_id, project_id, media_asset_id)
        start_t = float(current_edit["edited_start_time"])
        end_t = float(current_edit["edited_end_time"])

        # 2. Run ReframingService on candidate interval
        logger.info(
            "Executing smart tracking on clip interval: candidate=%s [%.2f, %.2f] aspect=%s",
            candidate_id, start_t, end_t, target_aspect_ratio,
        )

        plan = self.reframing_service.analyze_and_create_plan(
            project_id=project_id,
            media_asset_id=media_asset_id,
            candidate_id=candidate_id,
            target_aspect_ratio=target_aspect_ratio,
            framing_strategy="auto",
            start_time=start_t,
            end_time=end_t,
        )

        tracking_status = "tracked" if plan.detected_tracks else "fallback"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 3. Update candidate_clip_edits with reframing_plan_id
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute(
                """
                UPDATE candidate_clip_edits
                SET reframing_plan_id = ?,
                    tracking_status = ?,
                    framing_mode = 'smart_tracking',
                    aspect_ratio = ?,
                    version = version + 1,
                    updated_at = ?
                WHERE candidate_id = ?
                """,
                (plan.id, tracking_status, target_aspect_ratio, now, candidate_id),
            )
            updated = conn.execute(
                "SELECT * FROM candidate_clip_edits WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()

            d = dict(updated)
            d["plan_id"] = plan.id
            d["detected_tracks"] = [t.to_dict() for t in plan.detected_tracks]
            d["keyframes_count"] = len(plan.keyframes)
            d["dominant_strategy"] = plan.framing_strategy
            return d
