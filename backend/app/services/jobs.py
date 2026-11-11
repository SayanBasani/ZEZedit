"""Persistent background job lifecycle and worker orchestration foundation."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import Settings
from app.core.errors import AppError
from app.db.connection import sqlite_session
from app.models.entities import JobRecord

# Valid state transition matrix
VALID_TRANSITIONS: Dict[str, set[str]] = {
    "queued": {"running", "cancelling", "cancelled"},
    "running": {"cancelling", "completed", "failed", "interrupted"},
    "cancelling": {"cancelled", "failed"},
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
        return self.get_job(job_id)

    def recover_interrupted_jobs(self) -> List[str]:
        """Detect and mark any jobs left 'running' or 'cancelling' from an unclean backend crash."""
        now = datetime.now(timezone.utc).isoformat()
        recovered_ids: List[str] = []
        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, status FROM jobs WHERE status IN ('running', 'cancelling')"
            ).fetchall()
            for r in rows:
                jid = r["id"]
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'interrupted',
                        error_message = 'Backend process restarted while job was active.',
                        current_stage = 'interrupted',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, jid),
                )
                recovered_ids.append(jid)
        return recovered_ids

    def _row_to_record(self, row) -> JobRecord:
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
        )
