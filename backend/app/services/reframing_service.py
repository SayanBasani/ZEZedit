"""High-level coordinator service for smart reframing, tracking, manual overrides, and rendering."""

import datetime
import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.errors import AppError, NotFoundError, ProcessingError, ValidationError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.models.reframing import (
    CropKeyframe,
    DetectedSubject,
    ReframingPlanRecord,
    ReframingRevisionRecord,
    SubjectTrack,
)
from app.services.framing_engine import FramingEngine
from app.services.reframing_renderer import ReframingRenderer
from app.services.subject_tracker import SubjectTracker

logger = logging.getLogger("zezedit.reframing.service")


class ReframingService:
    """Orchestrates subject tracking, portrait framing calculations, revision history, and FFmpeg rendering."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.layout = StorageLayout.from_root(self.settings.storage_root)
        self.db_path = db_path or self.layout.db_file
        self.tracker = SubjectTracker(ffmpeg_path=self.settings.ffmpeg_path)
        self.renderer = ReframingRenderer(
            ffmpeg_path=self.settings.ffmpeg_path,
            threads=self.settings.ffmpeg_threads,
        )

    def analyze_and_create_plan(
        self,
        project_id: str,
        media_asset_id: str,
        candidate_id: Optional[str] = None,
        target_aspect_ratio: str = "9:16",
        framing_strategy: str = "auto",
        base_zoom: float = 1.0,
        headroom_factor: float = 0.15,
        smoothing_window: float = 0.8,
        pinned_subject_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> ReframingPlanRecord:
        """Analyze media clip, track subjects, compute authoritative portrait keyframes, and persist initial revision."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 1. Verify media asset
            asset = conn.execute(
                """
                SELECT id, project_id, storage_path, is_external, duration_seconds, width, height
                FROM media_assets WHERE id = ? AND project_id = ?
                """,
                (media_asset_id, project_id),
            ).fetchone()
            if not asset:
                raise NotFoundError(f"Media asset '{media_asset_id}' not found in project '{project_id}'.")

            # Resolve absolute media path
            if asset["is_external"]:
                media_path = Path(asset["storage_path"])
            else:
                media_path = self.layout.media / asset["storage_path"]

            source_w = int(asset["width"] or 1920)
            source_h = int(asset["height"] or 1080)
            asset_duration = float(asset["duration_seconds"] or 60.0)

            # 2. Determine start and end time (from candidate if available, or explicit overrides)
            clip_start = 0.0
            clip_end = min(asset_duration, 30.0)

            if candidate_id:
                cand = conn.execute(
                    "SELECT id, start_time, end_time FROM shorts_candidates WHERE id = ? AND project_id = ?",
                    (candidate_id, project_id),
                ).fetchone()
                if cand:
                    clip_start = float(cand["start_time"])
                    clip_end = float(cand["end_time"])

            if start_time is not None:
                clip_start = float(start_time)
            if end_time is not None:
                clip_end = float(end_time)

            start_time = clip_start
            end_time = clip_end
            duration = max(0.5, round(end_time - start_time, 3))

            # 3. Load relevant visual scene cuts if available
            scene_cuts: List[float] = []
            scene_rows = conn.execute(
                """
                SELECT representative_timestamp, start_time, end_time FROM video_scenes
                WHERE media_asset_id = ? AND start_time >= ? AND start_time <= ?
                ORDER BY start_time ASC
                """,
                (media_asset_id, clip_start - 0.5, clip_end + 0.5),
            ).fetchall()
            for r in scene_rows:
                if r["start_time"] > clip_start:
                    scene_cuts.append(round(float(r["start_time"]), 3))

            # 4. Run Subject Tracking
            logger.info(
                "Tracking subjects for reframing plan: asset=%s interval=[%.2f, %.2f]",
                media_asset_id, clip_start, clip_end
            )
            tracks = self.tracker.track_clip(
                media_path=media_path,
                start_time=clip_start,
                end_time=clip_end,
                source_w=source_w,
                source_h=source_h,
                scene_cut_timestamps=scene_cuts,
            )

            # 5. Compute Authoritative Framing Keyframes
            engine = FramingEngine(
                target_aspect_ratio=target_aspect_ratio,
                base_zoom=base_zoom,
                headroom_factor=headroom_factor,
                smoothing_window_seconds=smoothing_window,
            )

            keyframes, warnings = engine.generate_framing_keyframes(
                tracks=tracks,
                start_time=start_time,
                end_time=end_time,
                source_w=source_w,
                source_h=source_h,
                scene_cut_timestamps=scene_cuts,
                preferred_strategy=framing_strategy,
                pinned_subject_id=pinned_subject_id,
            )

            # Determine dominant strategy
            strategies = [k.framing_strategy for k in keyframes]
            dominant_strategy = max(set(strategies), key=strategies.count) if strategies else "single_subject"

            plan_id = f"ref_{uuid.uuid4().hex[:12]}"
            rev_id = f"rev_{uuid.uuid4().hex[:12]}"
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Output dimensions for target aspect ratio
            if target_aspect_ratio == "9:16":
                out_w, out_h = (1080, 1920)
            elif target_aspect_ratio == "1:1":
                out_w, out_h = (1080, 1080)
            elif target_aspect_ratio == "4:5":
                out_w, out_h = (1080, 1350)
            else:
                out_w, out_h = (1920, 1080)

            # 6. Insert reframing plan
            conn.execute(
                """
                INSERT INTO reframing_plans (
                    id, project_id, media_asset_id, candidate_id, target_aspect_ratio,
                    framing_strategy, status, source_width, source_height, output_width,
                    output_height, start_time, end_time, duration, base_zoom, headroom_factor,
                    smoothing_window_seconds, keyframes_json, detected_tracks_json, scene_cuts_json,
                    warnings_json, active_revision_id, calculation_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '2.0.0-m7', ?, ?)
                """,
                (
                    plan_id, project_id, media_asset_id, candidate_id, target_aspect_ratio,
                    dominant_strategy, source_w, source_h, out_w, out_h, start_time, end_time,
                    duration, base_zoom, headroom_factor, smoothing_window,
                    json.dumps([k.to_dict() for k in keyframes]),
                    json.dumps([t.to_dict() for t in tracks]),
                    json.dumps(scene_cuts),
                    json.dumps(warnings),
                    rev_id, now, now,
                ),
            )

            # 7. Insert Initial Revision 1 (AI Initial Framing)
            conn.execute(
                """
                INSERT INTO reframing_revisions (
                    id, reframing_plan_id, revision_number, label, is_ai_generated,
                    manual_overrides_json, effective_keyframes_json, created_at
                ) VALUES (?, ?, 1, 'AI Initial Framing', 1, '[]', ?, ?)
                """,
                (
                    rev_id, plan_id,
                    json.dumps([k.to_dict() for k in keyframes]),
                    now,
                ),
            )

            return ReframingPlanRecord(
                id=plan_id,
                project_id=project_id,
                media_asset_id=media_asset_id,
                candidate_id=candidate_id,
                job_id=None,
                target_aspect_ratio=target_aspect_ratio,
                framing_strategy=dominant_strategy,
                status="completed",
                source_width=source_w,
                source_height=source_h,
                output_width=out_w,
                output_height=out_h,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                base_zoom=base_zoom,
                headroom_factor=headroom_factor,
                smoothing_window_seconds=smoothing_window,
                keyframes=keyframes,
                detected_tracks=tracks,
                scene_cuts=scene_cuts,
                warnings=warnings,
                active_revision_id=rev_id,
                created_at=now,
                updated_at=now,
            )

    def get_plan(self, project_id: str, plan_id: str) -> Dict[str, Any]:
        """Fetch full reframing plan record including active revision details."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            row = conn.execute(
                "SELECT * FROM reframing_plans WHERE id = ? AND project_id = ?",
                (plan_id, project_id),
            ).fetchone()
            if not row:
                raise NotFoundError(f"Reframing plan '{plan_id}' not found.")

            d = dict(row)
            d["keyframes"] = json.loads(d.get("keyframes_json") or "[]")
            d["detected_tracks"] = json.loads(d.get("detected_tracks_json") or "[]")
            d["scene_cuts"] = json.loads(d.get("scene_cuts_json") or "[]")
            d["warnings"] = json.loads(d.get("warnings_json") or "[]")

            # Fetch active revision
            if d.get("active_revision_id"):
                rev = conn.execute(
                    "SELECT * FROM reframing_revisions WHERE id = ?",
                    (d["active_revision_id"],),
                ).fetchone()
                if rev:
                    rev_d = dict(rev)
                    rev_d["manual_overrides"] = json.loads(rev_d.get("manual_overrides_json") or "[]")
                    rev_d["effective_keyframes"] = json.loads(rev_d.get("effective_keyframes_json") or "[]")
                    d["active_revision"] = rev_d

            return d

    def preview_crop_at(
        self,
        project_id: str,
        plan_id: str,
        timestamp: float,
    ) -> Dict[str, Any]:
        """Calculate exact interpolated crop geometry [crop_x, crop_y, crop_w, crop_h] at timestamp."""
        plan_data = self.get_plan(project_id, plan_id)

        # Use effective keyframes from active revision if available, else plan keyframes
        active_rev = plan_data.get("active_revision")
        raw_kf_list = active_rev.get("effective_keyframes") if active_rev else plan_data.get("keyframes")

        kfs = [
            CropKeyframe(
                timestamp=k["timestamp"],
                crop_x=k["crop_x"],
                crop_y=k["crop_y"],
                crop_w=k["crop_w"],
                crop_h=k["crop_h"],
                zoom=k.get("zoom", 1.0),
                headroom=k.get("headroom", 0.15),
                framing_strategy=k.get("framing_strategy", "single_subject"),
                is_scene_boundary=k.get("is_scene_boundary", False),
                is_manual_override=k.get("is_manual_override", False),
            )
            for k in raw_kf_list
        ]

        crop_info = FramingEngine.interpolate_crop_at(kfs, timestamp)
        crop_info["plan_id"] = plan_id
        crop_info["timestamp"] = timestamp
        crop_info["source_width"] = plan_data["source_width"]
        crop_info["source_height"] = plan_data["source_height"]
        crop_info["target_aspect_ratio"] = plan_data["target_aspect_ratio"]

        return crop_info

    def save_manual_overrides(
        self,
        project_id: str,
        plan_id: str,
        manual_overrides: List[Dict[str, Any]],
        revision_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply user manual crop adjustments, recompute authoritative effective keyframes,

        and persist a new non-destructive revision.
        """
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            plan = conn.execute(
                "SELECT * FROM reframing_plans WHERE id = ? AND project_id = ?",
                (plan_id, project_id),
            ).fetchone()
            if not plan:
                raise NotFoundError(f"Reframing plan '{plan_id}' not found.")

            source_w = int(plan["source_width"])
            source_h = int(plan["source_height"])
            start_time = float(plan["start_time"])
            end_time = float(plan["end_time"])
            raw_tracks = json.loads(plan["detected_tracks_json"] or "[]")
            scene_cuts = json.loads(plan["scene_cuts_json"] or "[]")

            # Reconstruct tracks
            tracks: List[SubjectTrack] = []
            for t_dict in raw_tracks:
                dets = [
                    DetectedSubject(
                        timestamp=d["timestamp"],
                        box_x=d["box_x"],
                        box_y=d["box_y"],
                        box_w=d["box_w"],
                        box_h=d["box_h"],
                        confidence=d.get("confidence", 0.8),
                        category=d.get("category", "face"),
                        subject_id=t_dict["track_id"],
                    )
                    for d in t_dict.get("detections", [])
                ]
                tracks.append(
                    SubjectTrack(
                        track_id=t_dict["track_id"],
                        category=t_dict.get("category", "face"),
                        detections=dets,
                        first_seen=t_dict.get("first_seen", 0.0),
                        last_seen=t_dict.get("last_seen", 0.0),
                    )
                )

            # Recompute effective keyframes incorporating manual overrides
            engine = FramingEngine(
                target_aspect_ratio=plan["target_aspect_ratio"],
                base_zoom=float(plan["base_zoom"]),
                headroom_factor=float(plan["headroom_factor"]),
                smoothing_window_seconds=float(plan["smoothing_window_seconds"]),
            )

            effective_kfs, warnings = engine.generate_framing_keyframes(
                tracks=tracks,
                start_time=start_time,
                end_time=end_time,
                source_w=source_w,
                source_h=source_h,
                scene_cut_timestamps=scene_cuts,
                manual_overrides=manual_overrides,
            )

            # Determine next revision number
            last_rev = conn.execute(
                "SELECT MAX(revision_number) as max_num FROM reframing_revisions WHERE reframing_plan_id = ?",
                (plan_id,),
            ).fetchone()
            next_rev_num = (last_rev["max_num"] or 1) + 1

            new_rev_id = f"rev_{uuid.uuid4().hex[:12]}"
            label = revision_label or f"Manual Revision {next_rev_num}"
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Insert new revision
            conn.execute(
                """
                INSERT INTO reframing_revisions (
                    id, reframing_plan_id, revision_number, label, is_ai_generated,
                    manual_overrides_json, effective_keyframes_json, created_at
                ) VALUES (?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    new_rev_id, plan_id, next_rev_num, label,
                    json.dumps(manual_overrides),
                    json.dumps([k.to_dict() for k in effective_kfs]),
                    now,
                ),
            )

            # Update active revision in plan
            conn.execute(
                """
                UPDATE reframing_plans
                SET active_revision_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_rev_id, now, plan_id),
            )

        return self.get_plan(project_id, plan_id)

    def list_revisions(self, project_id: str, plan_id: str) -> List[Dict[str, Any]]:
        """List all saved revisions for a reframing plan."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT r.* FROM reframing_revisions r
                JOIN reframing_plans p ON r.reframing_plan_id = p.id
                WHERE p.id = ? AND p.project_id = ?
                ORDER BY r.revision_number ASC
                """,
                (plan_id, project_id),
            ).fetchall()

            result = []
            for r in rows:
                d = dict(r)
                d["manual_overrides"] = json.loads(d.get("manual_overrides_json") or "[]")
                d["effective_keyframes"] = json.loads(d.get("effective_keyframes_json") or "[]")
                result.append(d)
            return result

    def restore_revision(self, project_id: str, plan_id: str, revision_id: str) -> Dict[str, Any]:
        """Activate a previous revision as the current active framing."""
        with sqlite_session(self.db_path) as conn:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            res = conn.execute(
                """
                UPDATE reframing_plans
                SET active_revision_id = ?, updated_at = ?
                WHERE id = ? AND project_id = ?
                """,
                (revision_id, now, plan_id, project_id),
            )
            if res.rowcount == 0:
                raise NotFoundError(f"Reframing plan '{plan_id}' or revision '{revision_id}' not found.")

        return self.get_plan(project_id, plan_id)

    def render_revision(
        self,
        project_id: str,
        plan_id: str,
        revision_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Render a real vertical 9:16 MP4 video via FFmpeg using the revision's authoritative keyframes."""
        plan_data = self.get_plan(project_id, plan_id)

        target_rev_id = revision_id or plan_data.get("active_revision_id")
        if not target_rev_id:
            raise ValidationError("No active revision found to render.")

        revisions = self.list_revisions(project_id, plan_id)
        matching_revs = [r for r in revisions if r["id"] == target_rev_id]
        if not matching_revs:
            raise NotFoundError(f"Revision '{target_rev_id}' not found.")

        rev = matching_revs[0]
        raw_kfs = rev["effective_keyframes"]
        if not raw_kfs:
            raw_kfs = plan_data["keyframes"]

        kfs = [
            CropKeyframe(
                timestamp=k["timestamp"],
                crop_x=k["crop_x"],
                crop_y=k["crop_y"],
                crop_w=k["crop_w"],
                crop_h=k["crop_h"],
                zoom=k.get("zoom", 1.0),
                headroom=k.get("headroom", 0.15),
                framing_strategy=k.get("framing_strategy", "single_subject"),
                is_scene_boundary=k.get("is_scene_boundary", False),
                is_manual_override=k.get("is_manual_override", False),
            )
            for k in raw_kfs
        ]

        # Resolve media source path
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            asset = conn.execute(
                "SELECT storage_path, is_external FROM media_assets WHERE id = ?",
                (plan_data["media_asset_id"],),
            ).fetchone()

        if asset["is_external"]:
            source_media_path = Path(asset["storage_path"])
        else:
            source_media_path = self.layout.media / asset["storage_path"]

        # Output video file path inside shorts storage
        shorts_dir = self.layout.shorts / project_id
        shorts_dir.mkdir(parents=True, exist_ok=True)
        out_filename = f"{plan_id}_rev{rev['revision_number']}.mp4"
        out_path = shorts_dir / out_filename

        logger.info(
            "Rendering reframing revision: plan=%s rev=%d -> %s",
            plan_id, rev["revision_number"], out_path
        )

        render_info = self.renderer.render_reframed_clip(
            source_media_path=source_media_path,
            start_time=plan_data["start_time"],
            end_time=plan_data["end_time"],
            keyframes=kfs,
            output_path=out_path,
            source_w=plan_data["source_width"],
            source_h=plan_data["source_height"],
            output_w=plan_data["output_width"],
            output_h=plan_data["output_height"],
        )

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Update revision record with rendered metadata
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                UPDATE reframing_revisions
                SET rendered_video_path = ?, rendered_duration = ?, rendered_file_size_bytes = ?, rendered_at = ?
                WHERE id = ?
                """,
                (
                    str(out_path),
                    render_info["duration"],
                    render_info["file_size_bytes"],
                    now,
                    target_rev_id,
                ),
            )

        render_info["revision_id"] = target_rev_id
        render_info["revision_number"] = rev["revision_number"]
        return render_info
