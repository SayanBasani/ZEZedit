"""Persistent background job lifecycle and worker orchestration foundation."""

import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None

from app.core.config import Settings
from app.core.errors import AppError
from app.db.connection import sqlite_session
from app.models.entities import JobRecord

logger = logging.getLogger("zezedit.jobs")

# Valid state transition matrix
VALID_TRANSITIONS: Dict[str, set[str]] = {
    "queued": {"running", "cancelling", "cancelled"},
    "running": {"running", "cancelling", "completed", "failed", "interrupted"},
    "cancelling": {"cancelling", "cancelled", "failed"},
    "cancelled": {"queued"},  # Re-enqueue
    "completed": set(),       # Terminal
    "failed": {"queued"},     # Retry
    "interrupted": {"queued"},# Retry / recovery
}


class JobOrchestrator:
    """Manages persistent job records, state machines, retries, and startup recovery."""

    def __init__(self, settings: Settings, db_path: Path) -> None:
        self.settings = settings
        self.db_path = db_path

    def create_job(
        self,
        job_type: str,
        project_id: Optional[str] = None,
        priority: int = 100,
        input_config: Optional[dict] = None,
        max_attempts: int = 2,
        media_asset_id: Optional[str] = None,
        parent_job_id: Optional[str] = None,
    ) -> JobRecord:
        """Create a new queued job record."""
        # Backward compatibility for positional input_config: create_job(job_type, input_config_dict)
        if isinstance(project_id, dict) and input_config is None:
            input_config = project_id
            project_id = None

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        cfg = input_config or {}
        cfg_json = json.dumps(cfg)
        raw_asset_id = media_asset_id or cfg.get("media_asset_id") or cfg.get("asset_id")
        asset_id = str(raw_asset_id) if raw_asset_id is not None else None
        parent_id = str(parent_job_id) if parent_job_id is not None else None

        with sqlite_session(self.db_path) as conn:
            # If project_id provided, verify exists
            if project_id:
                p = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
                if not p:
                    raise AppError(
                        code="PROJECT_NOT_FOUND",
                        message=f"Project with ID '{project_id}' does not exist.",
                        status_code=404,
                    )

            conn.execute(
                """
                INSERT INTO jobs (
                    id, project_id, media_asset_id, parent_job_id, job_type, status, priority, progress_pct,
                    current_stage, worker_id, worker_pid, input_config_json,
                    result_metadata_json, error_message, retry_count, max_attempts,
                    created_at, started_at, completed_at, cancellation_requested_at,
                    cancelled_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'queued', ?, 0.0, 'queued', NULL, NULL, ?, NULL, NULL, 0, ?, ?, NULL, NULL, NULL, NULL, ?)
                """,
                (job_id, project_id, asset_id, parent_id, job_type, priority, cfg_json, max_attempts, now, now),
            )
            if project_id:
                event_id = f"evt_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO project_events (id, project_id, event_type, event_summary, payload_json, created_at)
                    VALUES (?, ?, 'job_submitted', ?, ?, ?)
                    """,
                    (
                        event_id,
                        project_id,
                        f"Job '{job_type}' submitted",
                        json.dumps({"job_id": job_id, "job_type": job_type, "media_asset_id": asset_id}),
                        now,
                    ),
                )

        return self.get_job(job_id)

    def list_jobs(
        self,
        project_id: Optional[str] = None,
        media_asset_id: Optional[str] = None,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[JobRecord]:
        """List jobs matching filters with video metadata joined."""
        query = """
        SELECT j.*, m.original_filename as video_title
        FROM jobs j
        LEFT JOIN media_assets m ON j.media_asset_id = m.id
        WHERE 1=1
        """
        params: list = []
        if project_id and project_id != "all":
            query += " AND j.project_id = ?"
            params.append(project_id)
        if media_asset_id:
            query += " AND j.media_asset_id = ?"
            params.append(media_asset_id)
        if status:
            if status == "running":
                query += " AND j.status = 'running'"
            elif status == "queued":
                query += " AND j.status IN ('queued', 'pending')"
            elif status == "completed":
                query += " AND j.status = 'completed'"
            elif status == "failed":
                query += " AND j.status IN ('failed', 'interrupted')"
            elif status == "cancelled":
                query += " AND j.status IN ('cancelled', 'cancelling')"
            elif status != "all":
                query += " AND j.status = ?"
                params.append(status)
        if job_type:
            query += " AND j.job_type = ?"
            params.append(job_type)
        if search and search.strip():
            s = f"%{search.strip().lower()}%"
            query += " AND (LOWER(j.id) LIKE ? OR LOWER(j.job_type) LIKE ? OR LOWER(COALESCE(j.current_stage, '')) LIKE ? OR LOWER(COALESCE(m.original_filename, '')) LIKE ?)"
            params.extend([s, s, s, s])

        query += " ORDER BY j.created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_record(row) for row in rows]

    def get_job(self, job_id: str) -> JobRecord:
        """Fetch job details with joined video metadata."""
        with sqlite_session(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT j.*, m.original_filename as video_title
                FROM jobs j
                LEFT JOIN media_assets m ON j.media_asset_id = m.id
                WHERE j.id = ?
                """,
                (job_id,),
            ).fetchone()
            if not row:
                raise AppError(
                    code="JOB_NOT_FOUND",
                    message=f"Job with ID '{job_id}' does not exist.",
                    status_code=404,
                )
            return self._row_to_record(row)
            if not row:
                raise AppError(
                    code="JOB_NOT_FOUND",
                    message=f"Job with ID '{job_id}' does not exist.",
                    status_code=404,
                )
            return self._row_to_record(row)

    def transition_job_state(
        self,
        job_id: str,
        new_status: str,
        progress_pct: Optional[float] = None,
        stage: Optional[str] = None,
        error_message: Optional[str] = None,
        result_metadata: Optional[dict] = None,
        worker_id: Optional[str] = None,
        worker_pid: Optional[int] = None,
    ) -> JobRecord:
        """Enforce strict state machine transitions and update progress."""
        job = self.get_job(job_id)
        current_status = job.status

        # Validate transition
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise AppError(
                code="INVALID_JOB_TRANSITION",
                message=f"Cannot transition job from '{current_status}' to '{new_status}'.",
                status_code=400,
            )

        now = datetime.now(timezone.utc).isoformat()
        started_at = now if new_status == "running" and not job.started_at else job.started_at
        completed_at = now if new_status in {"completed", "failed"} else job.completed_at
        cancelled_at = now if new_status == "cancelled" else job.cancelled_at
        cancelling_at = now if new_status == "cancelling" else job.cancellation_requested_at

        res_json = (
            json.dumps(result_metadata)
            if result_metadata is not None
            else json.dumps(job.result_metadata)
        )

        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?,
                    progress_pct = COALESCE(?, progress_pct),
                    current_stage = COALESCE(?, current_stage),
                    error_message = COALESCE(?, error_message),
                    result_metadata_json = ?,
                    worker_id = COALESCE(?, worker_id),
                    worker_pid = COALESCE(?, worker_pid),
                    started_at = ?,
                    completed_at = ?,
                    cancellation_requested_at = ?,
                    cancelled_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    new_status,
                    progress_pct,
                    stage,
                    error_message,
                    res_json,
                    worker_id,
                    worker_pid,
                    started_at,
                    completed_at,
                    cancelling_at,
                    cancelled_at,
                    now,
                    job_id,
                ),
            )

        return self.get_job(job_id)

    def request_cancellation(self, job_id: str) -> JobRecord:
        """
        Request cancellation of a job.
        If queued: transitions to 'cancelled' immediately.
        If running: transitions to 'cancelling', terminates worker subprocesses safely, and transitions to 'cancelled'.
        """
        job = self.get_job(job_id)
        if job.status in {"completed", "cancelled", "failed"}:
            raise AppError(
                code="JOB_TERMINAL",
                message=f"Job is already in terminal state '{job.status}'.",
                status_code=400,
            )

        if job.status == "queued":
            return self.transition_job_state(job_id, "cancelled", stage="cancelled_before_run")
        elif job.status == "running":
            # Cooperative cancellation transition
            cancelling_job = self.transition_job_state(job_id, "cancelling", stage="cancellation_requested")
            # If worker PID is known, terminate child process tree safely
            if job.worker_pid:
                self._terminate_pid_tree(job.worker_pid)
                # When PID was actively terminated, also mark cancelled immediately
                return self.transition_job_state(job_id, "cancelled", stage="cancelled_by_user")
            return cancelling_job
        elif job.status == "cancelling":
            if job.worker_pid:
                self._terminate_pid_tree(job.worker_pid)
            return self.transition_job_state(job_id, "cancelled", stage="cancelled_by_user")
        return job

    def _terminate_pid_tree(self, pid: int) -> bool:
        """Safely terminate a worker process tree (e.g. Python worker and child FFmpeg)."""
        try:
            if psutil is not None:
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    children = proc.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    proc.terminate()
                    _, alive = psutil.wait_procs(children + [proc], timeout=1.5)
                    for p in alive:
                        try:
                            p.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    return True
            else:
                os.kill(pid, 15)
                return True
        except Exception as exc:
            logger.warning("Could not terminate PID %s: %s", pid, exc)
        return False

    def retry_job(self, job_id: str, create_new_attempt: bool = False) -> JobRecord:
        """Retry a failed, interrupted, or cancelled job."""
        job = self.get_job(job_id)
        if job.status not in {"failed", "interrupted", "cancelled"}:
            raise AppError(
                code="JOB_NOT_RETRYABLE",
                message=f"Cannot retry job in '{job.status}' status.",
                status_code=400,
            )
        if job.retry_count >= job.max_attempts:
            raise AppError(
                code="MAX_RETRIES_EXCEEDED",
                message=f"Job has reached its maximum attempts ({job.max_attempts}).",
                status_code=400,
            )

        # Validate that associated media asset still exists if linked
        if job.media_asset_id:
            with sqlite_session(self.db_path) as conn:
                asset_row = conn.execute(
                    "SELECT id FROM media_assets WHERE id = ?",
                    (job.media_asset_id,),
                ).fetchone()
                if not asset_row:
                    raise AppError(
                        code="MEDIA_ASSET_MISSING",
                        message=f"Cannot retry job: source media '{job.media_asset_id}' is missing or was deleted.",
                        status_code=404,
                    )

        now = datetime.now(timezone.utc).isoformat()
        if create_new_attempt:
            # Create a new execution attempt preserving previous attempt history
            new_job = self.create_job(
                job_type=job.job_type,
                project_id=job.project_id,
                media_asset_id=job.media_asset_id,
                parent_job_id=job.id,
                priority=job.priority,
                input_config=job.input_config,
                max_attempts=job.max_attempts,
            )
            with sqlite_session(self.db_path) as conn:
                conn.execute(
                    "UPDATE jobs SET retry_count = ? WHERE id = ?",
                    (job.retry_count + 1, new_job.id),
                )
            return self.get_job(new_job.id)

        # Default in-place retry (compatible with existing lifecycle tests)
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'queued',
                    retry_count = retry_count + 1,
                    progress_pct = 0.0,
                    current_stage = 'queued_retry',
                    error_message = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, job_id),
            )
            if job.project_id:
                event_id = f"evt_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO project_events (id, project_id, event_type, event_summary, payload_json, created_at)
                    VALUES (?, ?, 'job_retried', ?, ?, ?)
                    """,
                    (
                        event_id,
                        job.project_id,
                        f"Job '{job.job_type}' retried (attempt {job.retry_count + 1})",
                        json.dumps({"job_id": job_id, "job_type": job.job_type, "retry_count": job.retry_count + 1}),
                        now,
                    ),
                )
        return self.get_job(job_id)

    def delete_job(self, job_id: str) -> bool:
        """Delete a single process record without deleting user media or outputs."""
        job = self.get_job(job_id)
        if job.status == "running":
            raise AppError(
                code="JOB_RUNNING",
                message="Cannot delete a process while it is actively running. Stop or cancel it first.",
                status_code=400,
            )
        # Clean temporary directory for this job if present
        temp_dir = self.settings.storage_root / "temp" / f"job_{job_id}"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

        with sqlite_session(self.db_path) as conn:
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.execute(
                "DELETE FROM project_events WHERE payload_json LIKE ?",
                (f"%{job_id}%",),
            )
        return True

    def delete_job_history(self, status: Optional[str] = None) -> int:
        """Delete terminal job records without deleting media or active jobs."""
        query = "DELETE FROM jobs WHERE status IN ('completed', 'cancelled', 'failed', 'interrupted')"
        params: list = []
        if status and status in ("completed", "cancelled", "failed", "interrupted"):
            query = "DELETE FROM jobs WHERE status = ?"
            params = [status]

        with sqlite_session(self.db_path) as conn:
            cur = conn.execute(query, params)
            return cur.rowcount

    def save_checkpoint(
        self,
        job_id: str,
        stage: str,
        completed_units: int,
        total_units: int,
        intermediate_artifacts: Optional[Dict[str, Any]] = None,
        checkpoint_payload: Optional[Dict[str, Any]] = None,
    ) -> JobRecord:
        """Persist granular execution checkpoint with completed units and intermediate files."""
        job = self.get_job(job_id)
        now = datetime.now(timezone.utc).isoformat()
        total = max(total_units, 1)
        max_pct = 100.0 if stage == "completed" or job.status == "completed" else 99.0
        pct = round(min(max_pct, max(0.0, (completed_units / total) * 100.0)), 1)

        checkpoint = {
            "job_id": job_id,
            "stage": stage,
            "completed_units": completed_units,
            "total_units": total_units,
            "progress_pct": pct,
            "intermediate_artifacts": intermediate_artifacts or {},
            "checkpoint_payload": checkpoint_payload or {},
            "checkpointed_at": now,
        }
        cp_json = json.dumps(checkpoint)

        with sqlite_session(self.db_path) as conn:
            if stage == "completed" or pct >= 100.0:
                conn.execute(
                    """
                    UPDATE jobs
                    SET current_stage = ?,
                        progress_pct = ?,
                        status = CASE WHEN status = 'running' OR (status = 'failed' AND error_message LIKE 'Job stalled%') THEN 'completed' ELSE status END,
                        error_message = CASE WHEN status = 'failed' AND error_message LIKE 'Job stalled%' THEN NULL ELSE error_message END,
                        completed_at = COALESCE(completed_at, ?),
                        checkpoint_data_json = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (stage, pct, now, cp_json, now, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE jobs
                    SET current_stage = ?,
                        progress_pct = ?,
                        checkpoint_data_json = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (stage, pct, cp_json, now, job_id),
                )
            if job.project_id:
                event_id = f"evt_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO project_events (id, project_id, event_type, event_summary, payload_json, created_at)
                    VALUES (?, ?, 'job_checkpoint', ?, ?, ?)
                    """,
                    (
                        event_id,
                        job.project_id,
                        f"Job '{job.job_type}' checkpoint: {stage} ({completed_units}/{total_units})",
                        cp_json,
                        now,
                    ),
                )

        return self.get_job(job_id)

    def get_checkpoint(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve latest execution checkpoint for a job."""
        job = self.get_job(job_id)
        return job.checkpoint_data

    def can_dispatch_job(
        self,
        job_type: str,
        max_concurrent: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """Verify concurrency limits and host hardware resource thresholds before dispatching heavy task."""
        # Check active running jobs of this type
        with sqlite_session(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM jobs WHERE status = 'running' AND job_type = ?",
                (job_type,),
            ).fetchone()
            active_count = row["cnt"] if row else 0

        limit = max_concurrent if max_concurrent is not None else 1
        if active_count >= limit:
            return False, f"Concurrency limit reached for '{job_type}' ({active_count}/{limit} active)."

        # Check host CPU & RAM pressure via psutil if available
        if psutil is not None:
            try:
                vm = psutil.virtual_memory()
                if vm.percent > 92.0:
                    return False, f"Host memory pressure ({vm.percent:.1f}% used > 92%), holding new jobs."
                cpu = psutil.cpu_percent(interval=None)
                if cpu > 96.0:
                    return False, f"Host CPU saturated ({cpu:.1f}% used > 96%), holding new jobs."
            except Exception as e:
                logger.warning("Resource check failed: %s", e)

        return True, "Dispatch capacity available."

    def get_next_queued_job(self) -> Optional[JobRecord]:
        """Retrieve highest priority queued job according to priority and FIFO scheduling."""
        with sqlite_session(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 1"
            ).fetchone()
            return self._row_to_record(row) if row else None

    def recover_interrupted_jobs(self) -> List[str]:
        """Detect and mark any jobs left 'running' or 'cancelling' from an unclean backend crash.
        
        Checks checkpoint data and preserves intermediate artifacts for idempotent resume.
        """
        now = datetime.now(timezone.utc).isoformat()
        recovered_ids: List[str] = []
        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, status, checkpoint_data_json, job_type FROM jobs WHERE status IN ('running', 'cancelling')"
            ).fetchall()
            for r in rows:
                jid = r["id"]
                has_cp = bool(r["checkpoint_data_json"])
                err_msg = (
                    "Backend restarted while job was active. Checkpoint preserved for resume."
                    if has_cp
                    else "Backend process restarted while job was active."
                )
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'interrupted',
                        error_message = ?,
                        current_stage = 'interrupted',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (err_msg, now, jid),
                )
                recovered_ids.append(jid)
        return recovered_ids

    def get_queue_stats(self) -> dict:
        """Calculate aggregate job counts across all execution statuses and job types."""
        with sqlite_session(self.db_path) as conn:
            rows = conn.execute("SELECT status, job_type, id FROM jobs").fetchall()
            stats = {
                "total_jobs": len(rows),
                "queued": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "by_type": {},
                "active_job_ids": [],
            }
            for r in rows:
                status = r["status"]
                jtype = r["job_type"]
                jid = r["id"]

                # Group statuses
                if status == "running":
                    stats["running"] += 1
                    stats["active_job_ids"].append(jid)
                elif status in ("queued", "pending"):
                    stats["queued"] += 1
                elif status == "completed":
                    stats["completed"] += 1
                elif status in ("failed", "interrupted"):
                    stats["failed"] += 1
                elif status in ("cancelled", "cancelling"):
                    stats["cancelled"] += 1

                stats["by_type"][jtype] = stats["by_type"].get(jtype, 0) + 1

            return stats

    def get_job_logs(self, job_id: str) -> dict:
        """Retrieve detailed timeline logs and execution messages for a job."""
        job = self.get_job(job_id)
        logs: List[str] = [
            f"[{job.created_at}] Job '{job.id}' created (type: {job.job_type}, priority: {job.priority})."
        ]

        if job.started_at:
            logs.append(f"[{job.started_at}] Worker started execution. PID: {job.worker_pid or 'local'}.")
        if job.current_stage:
            logs.append(f"[{job.updated_at}] Current stage: '{job.current_stage}' (Progress: {job.progress_pct:.1f}%).")

        # Pull any related project events
        with sqlite_session(self.db_path) as conn:
            events = conn.execute(
                "SELECT event_type, event_summary, created_at FROM project_events WHERE payload_json LIKE ? ORDER BY created_at ASC",
                (f"%{job_id}%",),
            ).fetchall()
            for ev in events:
                logs.append(f"[{ev['created_at']}] {ev['event_type'].upper()}: {ev['event_summary']}")

        if job.completed_at:
            logs.append(f"[{job.completed_at}] Job completed successfully.")
        if job.cancelled_at:
            logs.append(f"[{job.cancelled_at}] Job cancelled by user.")
        if job.error_message:
            logs.append(f"[{job.updated_at}] ERROR: {job.error_message}")

        return {
            "job_id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "current_stage": job.current_stage,
            "progress_percent": job.progress_pct,
            "error_message": job.error_message,
            "logs": logs,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }

    def record_heartbeat(
        self,
        job_id: str,
        progress_pct: Optional[float] = None,
        stage: Optional[str] = None,
        stage_details: Optional[Dict[str, Any]] = None,
    ) -> JobRecord:
        """Record periodic worker heartbeat, updating updated_at and optional checkpoint data."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            if stage_details is not None:
                cp_row = conn.execute("SELECT checkpoint_data_json FROM jobs WHERE id = ?", (job_id,)).fetchone()
                existing_cp = {}
                if cp_row and cp_row["checkpoint_data_json"]:
                    try:
                        existing_cp = json.loads(cp_row["checkpoint_data_json"])
                    except Exception:
                        existing_cp = {}
                existing_cp["last_heartbeat"] = now
                existing_cp["stage_details"] = stage_details
                if stage:
                    existing_cp["stage"] = stage
                if progress_pct is not None:
                    existing_cp["progress_pct"] = progress_pct
                conn.execute(
                    """
                    UPDATE jobs
                    SET updated_at = ?,
                        progress_pct = COALESCE(?, progress_pct),
                        current_stage = COALESCE(?, current_stage),
                        checkpoint_data_json = ?
                    WHERE id = ?
                    """,
                    (now, progress_pct, stage, json.dumps(existing_cp), job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE jobs
                    SET updated_at = ?,
                        progress_pct = COALESCE(?, progress_pct),
                        current_stage = COALESCE(?, current_stage)
                    WHERE id = ?
                    """,
                    (now, progress_pct, stage, job_id),
                )
        return self.get_job(job_id)

    def start_job(self, job_id: str, stage: str = "running", worker_pid: Optional[int] = None) -> JobRecord:
        """Convenience method to transition a queued job to running."""
        return self.transition_job_state(job_id, "running", stage=stage, worker_pid=worker_pid)

    def complete_job(self, job_id: str, result_summary: Optional[dict] = None) -> JobRecord:
        """Convenience method to transition an active job to completed."""
        job = self.get_job(job_id)
        # If job was prematurely marked failed by stall detector, allow completing it cleanly
        if job.status == "failed" and job.error_message and "Job stalled" in job.error_message:
            with sqlite_session(self.db_path) as conn:
                conn.execute(
                    "UPDATE jobs SET status = 'running', error_message = NULL WHERE id = ?",
                    (job_id,),
                )
        return self.transition_job_state(
            job_id, "completed", progress_pct=100.0, stage="completed", result_metadata=result_summary
        )

    def fail_job(self, job_id: str, error_message: str) -> JobRecord:
        """Convenience method to transition a job to failed with an error message."""
        return self.transition_job_state(job_id, "failed", error_message=error_message, stage="failed")

    def check_stalled_jobs(self, timeout_seconds: float = 600.0) -> List[str]:
        """Detect and mark jobs that stopped sending heartbeats while in running status."""
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        stalled_ids: List[str] = []
        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, status, updated_at, worker_pid, current_stage, progress_pct 
                FROM jobs 
                WHERE status = 'running'
                """
            ).fetchall()
            for r in rows:
                jid = r["id"]
                upd = r["updated_at"]
                pid = r["worker_pid"]
                stage = r["current_stage"]
                pct = r["progress_pct"] if r["progress_pct"] is not None else 0.0

                # 1. Never mark completed or 100% jobs as stalled
                if stage == "completed" or pct >= 100.0:
                    continue

                is_stalled = False
                age = 0.0
                if upd:
                    try:
                        upd_dt = datetime.fromisoformat(upd.replace("Z", "+00:00"))
                        age = (now_dt - upd_dt).total_seconds()
                    except Exception:
                        pass

                # 2. Check worker process liveness if worker_pid is known
                if pid and psutil is not None:
                    try:
                        if psutil.pid_exists(pid):
                            # Worker process is still actively running in OS
                            # Only stall if completely silent for over 30 minutes
                            if age > 1800.0:
                                is_stalled = True
                        else:
                            # Process PID is truly terminated from OS
                            # Allow 30s buffer for orchestrator thread to finalize
                            if age > 30.0:
                                is_stalled = True
                    except Exception:
                        pass
                else:
                    # In-process async background task or unknown PID
                    # Stall if silent for more than timeout_seconds (default 600s / 10 min)
                    if age > timeout_seconds:
                        is_stalled = True

                if is_stalled:
                    conn.execute(
                        """
                        UPDATE jobs
                        SET status = 'failed',
                            error_message = ?,
                            current_stage = 'stalled_timeout',
                            updated_at = ?,
                            completed_at = ?
                        WHERE id = ? AND status = 'running' AND (current_stage != 'completed' AND progress_pct < 100.0)
                        """,
                        (f"Job stalled: no worker heartbeat or progress update for {int(age)}s.", now, now, jid),
                    )
                    stalled_ids.append(jid)
        return stalled_ids

    def _row_to_record(self, row) -> JobRecord:
        keys = row.keys() if hasattr(row, "keys") else []
        cp_data = None
        if "checkpoint_data_json" in keys and row["checkpoint_data_json"]:
            try:
                cp_data = json.loads(row["checkpoint_data_json"])
            except Exception:
                cp_data = None

        media_asset_id = row["media_asset_id"] if "media_asset_id" in keys else None
        parent_job_id = row["parent_job_id"] if "parent_job_id" in keys else None
        video_title = row["video_title"] if "video_title" in keys else None

        input_cfg = json.loads(row["input_config_json"] or "{}")
        if not media_asset_id:
            media_asset_id = input_cfg.get("media_asset_id") or input_cfg.get("asset_id")
        if not video_title:
            video_title = input_cfg.get("video_title") or input_cfg.get("filename") or input_cfg.get("title")

        return JobRecord(
            id=row["id"],
            project_id=row["project_id"],
            job_type=row["job_type"],
            status=row["status"],
            priority=row["priority"],
            progress_pct=row["progress_pct"],
            current_stage=row["current_stage"],
            worker_id=row["worker_id"],
            worker_pid=row["worker_pid"],
            input_config=input_cfg,
            result_metadata=json.loads(row["result_metadata_json"])
            if row["result_metadata_json"]
            else None,
            error_message=row["error_message"],
            retry_count=row["retry_count"],
            max_attempts=row["max_attempts"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            cancellation_requested_at=row["cancellation_requested_at"],
            cancelled_at=row["cancelled_at"],
            updated_at=row["updated_at"],
            checkpoint_data=cp_data,
            media_asset_id=media_asset_id,
            parent_job_id=parent_job_id,
            video_title=video_title,
        )
