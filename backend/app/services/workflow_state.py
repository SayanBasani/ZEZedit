"""Authoritative Video-to-Shorts Workflow State Machine and Lifecycle Orchestration."""

import json
import sqlite3
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.db.connection import sqlite_session


class WorkflowStage(str, Enum):
    IMPORTED = "IMPORTED"
    READY_FOR_ANALYSIS = "READY_FOR_ANALYSIS"
    ANALYZING = "ANALYZING"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    READY_FOR_DISCOVERY = "READY_FOR_DISCOVERY"
    DISCOVERING = "DISCOVERING"
    CANDIDATES_AVAILABLE = "CANDIDATES_AVAILABLE"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    REVIEW_IN_PROGRESS = "REVIEW_IN_PROGRESS"
    SHORTS_APPROVED = "SHORTS_APPROVED"
    EDITING = "EDITING"
    READY_FOR_REFRAMING = "READY_FOR_REFRAMING"
    REFRAMING = "REFRAMING"
    READY_FOR_EXPORT = "READY_FOR_EXPORT"
    EXPORTING = "EXPORTING"
    EXPORT_COMPLETED = "EXPORT_COMPLETED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"



class VideoWorkflowStateResponse(BaseModel):
    video_id: str
    project_id: str
    video_name: str
    duration_seconds: float
    current_stage: str
    completed_stages: List[str]
    available_next_actions: List[str]
    active_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    failed_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    candidate_counts: Dict[str, int] = Field(default_factory=dict)
    approved_short_counts: int = 0
    export_counts: Dict[str, int] = Field(default_factory=dict)
    last_modified: str


class WorkflowStateMachine:
    """Computes authoritative workflow lifecycle states for a source video asset."""

    def __init__(self, settings: Any = None, db_path: Optional[Path] = None, **kwargs: Any) -> None:
        if settings is not None and db_path is not None:
            self.settings = settings
            self.db_path = db_path
        elif hasattr(settings, "db_path"):
            self.settings = getattr(settings, "settings", None)
            self.db_path = settings.db_path
        elif isinstance(settings, Path):
            self.settings = None
            self.db_path = settings
        else:
            self.settings = settings
            self.db_path = db_path or getattr(settings, "sqlite_db_path", None)

    def evaluate(self, project_id: str, media_asset_id: str) -> VideoWorkflowStateResponse:
        return self.get_workflow_state(project_id, media_asset_id)

    def get_workflow_state(self, project_id: str, media_asset_id: str) -> VideoWorkflowStateResponse:
        """Derive authoritative workflow state across DB tables and in-flight jobs."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 1. Inspect source media asset
            media_row = conn.execute(
                "SELECT * FROM media_assets WHERE id = ? AND project_id = ?",
                (media_asset_id, project_id),
            ).fetchone()

            if not media_row:
                raise NotFoundError(
                    message=f"Media asset '{media_asset_id}' not found in project '{project_id}'.",
                    resource="media_asset",
                )

            video_name = media_row["original_filename"]
            duration = float(media_row["duration_seconds"] or 0.0)
            now = datetime.now(timezone.utc).isoformat()
            updated_at = media_row["updated_at"] or now

            # 2. Inspect active & failed background jobs for this project / media
            jobs = conn.execute(
                """
                SELECT id, job_type, status, progress_pct, current_stage, error_message, created_at, started_at
                FROM jobs
                WHERE project_id = ?
                ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()

            active_jobs = [
                {
                    "job_id": j["id"],
                    "job_type": j["job_type"],
                    "status": j["status"],
                    "progress_pct": j["progress_pct"],
                    "stage": j["current_stage"],
                    "started_at": j["started_at"],
                }
                for j in jobs
                if j["status"] in ("queued", "running")
            ]

            failed_jobs = [
                {
                    "job_id": j["id"],
                    "job_type": j["job_type"],
                    "status": j["status"],
                    "error": j["error_message"],
                    "created_at": j["created_at"],
                }
                for j in jobs
                if j["status"] in ("failed", "interrupted")
            ]

            # 3. Inspect completed analysis runs
            analysis_rows = conn.execute(
                "SELECT id, status, completed_at FROM analysis_runs WHERE project_id = ? AND media_asset_id = ? ORDER BY created_at DESC",
                (project_id, media_asset_id),
            ).fetchall()
            completed_analyses = [a for a in analysis_rows if a["status"] == "completed"]

            # 4. Inspect highlight candidates
            candidate_rows = conn.execute(
                "SELECT id, review_status, is_user_modified FROM shorts_candidates WHERE project_id = ? AND media_asset_id = ?",
                (project_id, media_asset_id),
            ).fetchall()

            cand_total = len(candidate_rows)
            cand_approved = sum(1 for c in candidate_rows if c["review_status"] == "approved")
            cand_rejected = sum(1 for c in candidate_rows if c["review_status"] == "rejected")
            cand_recommended = sum(1 for c in candidate_rows if c["review_status"] in ("recommended", "pending"))
            cand_modified = sum(1 for c in candidate_rows if c["is_user_modified"] == 1)

            candidate_counts = {
                "total": cand_total,
                "recommended": cand_recommended,
                "approved": cand_approved,
                "rejected": cand_rejected,
                "modified": cand_modified,
            }

            # 5. Inspect exports
            export_rows = conn.execute(
                "SELECT id, status, output_path, created_at FROM exports WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()

            export_completed = sum(1 for e in export_rows if e["status"] == "completed")
            export_failed = sum(1 for e in export_rows if e["status"] == "failed")
            export_rendering = sum(1 for e in export_rows if e["status"] in ("rendering", "queued"))

            export_counts = {
                "total": len(export_rows),
                "completed": export_completed,
                "failed": export_failed,
                "rendering": export_rendering,
            }

            # 6. Evaluate State Machine Transitions
            completed_stages = ["IMPORTED"]
            current_stage = "READY_FOR_ANALYSIS"
            next_actions = ["start_analysis", "next_video"]

            # Analysis active?
            has_running_analysis = any(j["job_type"] == "video_analysis" for j in active_jobs)
            has_running_discovery = any(j["job_type"] == "highlight_discovery" for j in active_jobs)
            has_running_export = any(j["job_type"] == "export_render" for j in active_jobs)

            if has_running_analysis:
                current_stage = "ANALYZING"
                next_actions = ["cancel_job", "next_video"]
            elif completed_analyses:
                completed_stages.extend(["READY_FOR_ANALYSIS", "ANALYSIS_COMPLETED"])
                current_stage = "READY_FOR_DISCOVERY"
                next_actions = ["discover_highlights", "inspect_transcript", "inspect_scenes", "next_video"]

                if has_running_discovery:
                    current_stage = "DISCOVERING"
                    next_actions = ["cancel_job", "next_video"]
                elif cand_total > 0:
                    completed_stages.extend(["READY_FOR_DISCOVERY", "CANDIDATES_AVAILABLE"])

                    if cand_approved == 0 and cand_rejected == 0:
                        current_stage = "READY_FOR_REVIEW"
                        next_actions = ["review_shorts", "re_discover", "next_video"]
                    elif cand_approved > 0:
                        completed_stages.extend(["READY_FOR_REVIEW", "SHORTS_APPROVED"])
                        current_stage = "SHORTS_APPROVED"
                        next_actions = [
                            "batch_export",
                            "send_to_reframing",
                            "open_timeline",
                            "review_shorts",
                            "next_video",
                        ]

                        if has_running_export:
                            current_stage = "EXPORTING"
                            next_actions = ["cancel_job", "open_queue", "next_video"]
                        elif export_completed > 0:
                            completed_stages.extend(["READY_FOR_EXPORT", "EXPORT_COMPLETED"])
                            current_stage = "EXPORT_COMPLETED"
                            next_actions = [
                                "open_exports",
                                "batch_export",
                                "next_video",
                                "review_shorts",
                            ]
                    else:
                        current_stage = "REVIEW_IN_PROGRESS"
                        next_actions = ["review_shorts", "re_discover", "next_video"]

            return VideoWorkflowStateResponse(
                video_id=media_asset_id,
                project_id=project_id,
                video_name=video_name,
                duration_seconds=duration,
                current_stage=current_stage,
                completed_stages=completed_stages,
                available_next_actions=next_actions,
                active_jobs=active_jobs,
                failed_jobs=failed_jobs,
                candidate_counts=candidate_counts,
                approved_short_counts=cand_approved,
                export_counts=export_counts,
                last_modified=updated_at,
            )
