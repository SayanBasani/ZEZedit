"""Persistent background job lifecycle and worker orchestration foundation."""

import json
import logging
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
    ) -> JobRecord:
        """Create a new queued job record."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        cfg_json = json.dumps(input_config or {})

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
                    id, project_id, job_type, status, priority, progress_pct,
                    current_stage, worker_id, worker_pid, input_config_json,
                    result_metadata_json, error_message, retry_count, max_attempts,
                    created_at, started_at, completed_at, cancellation_requested_at,
                    cancelled_at, updated_at
                ) VALUES (?, ?, ?, 'queued', ?, 0.0, 'queued', NULL, NULL, ?, NULL, NULL, 0, ?, ?, NULL, NULL, NULL, NULL, ?)
                """,
                (job_id, project_id, job_type, priority, cfg_json, max_attempts, now, now),
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
                        json.dumps({"job_id": job_id, "job_type": job_type}),
                        now,
                    ),
                )

        return self.get_job(job_id)

    def list_jobs(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[JobRecord]:
        """List jobs matching filters."""
        query = "SELECT * FROM jobs WHERE 1=1"
        params: list = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_record(row) for row in rows]

    def get_job(self, job_id: str) -> JobRecord:
        """Fetch job details."""
        with sqlite_session(self.db_path) as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
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
        If running: transitions to 'cancelling' until worker acknowledges.
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
            return self.transition_job_state(job_id, "cancelling", stage="cancellation_requested")
        return job

    def retry_job(self, job_id: str) -> JobRecord:
        """Retry a failed or interrupted job if retry count permits."""
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

        now = datetime.now(timezone.utc).isoformat()
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

    def _row_to_record(self, row) -> JobRecord:
        keys = row.keys() if hasattr(row, "keys") else []
        cp_data = None
        if "checkpoint_data_json" in keys and row["checkpoint_data_json"]:
            try:
                cp_data = json.loads(row["checkpoint_data_json"])
            except Exception:
                cp_data = None

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
            input_config=json.loads(row["input_config_json"] or "{}"),
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
        )
