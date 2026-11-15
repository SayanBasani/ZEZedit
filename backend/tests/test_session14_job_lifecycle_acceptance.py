"""Comprehensive acceptance tests for Session 14 Job Lifecycle and State Machine Invariants.

Verifies all 10 mandatory cases:
1. A healthy worker performing a long operation without frequent database checkpoints.
2. A worker that is genuinely blocked.
3. A worker that has crashed.
4. A worker that raises an exception.
5. A worker that completes successfully.
6. A worker that attempts to update a terminal job.
7. A job whose process identifier is 'local' rather than a numeric PID.
8. A worker that exits without persisting its final outputs.
9. A worker that reports completion after the job has already been canceled.
10. A worker that reports progress after being marked failed.
"""

import os
import time
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.core.config import get_settings
from app.db.connection import sqlite_session
from app.core.errors import AppError
from app.db.migrator import run_migrations
from app.services.jobs import JobOrchestrator


def _setup_orchestrator(tmp_path: Path) -> JobOrchestrator:
    db_file = tmp_path / "test_jobs_s14.db"
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(db_path=db_file, migrations_dir=migrations_dir)
    settings = get_settings()
    return JobOrchestrator(settings=settings, db_path=db_file)


# Case 1: Healthy worker performing a long operation with periodic heartbeats
def test_case_01_healthy_worker_long_operation_with_heartbeats(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="media_analysis", project_id=None)
    orch.start_job(job.id, stage="transcribing_speech", worker_pid="local")

    # Worker reports heartbeats periodically without advancing progress
    for _ in range(3):
        orch.record_heartbeat(job.id, stage="transcribing_speech", stage_details={"chunk": "evaluating"})

    # Watchdog check with standard timeout
    stalled = orch.check_stalled_jobs(timeout_seconds=600.0)
    assert job.id not in stalled

    rec = orch.get_job(job.id)
    assert rec.status == "running"
    assert rec.current_stage == "transcribing_speech"


# Case 2: Worker that is genuinely blocked (stopped heartbeats)
def test_case_02_worker_genuinely_blocked(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="media_analysis", project_id=None)
    orch.start_job(job.id, stage="sampling_frames", worker_pid="local")

    # Simulate silence exceeding timeout by backdating updated_at
    past = (datetime.now(timezone.utc) - timedelta(seconds=700)).isoformat()
    with sqlite_session(orch.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (past, job.id))

    stalled = orch.check_stalled_jobs(timeout_seconds=600.0)
    assert job.id in stalled

    rec = orch.get_job(job.id)
    assert rec.status == "failed"
    assert "Job stalled" in rec.error_message


# Case 3: Worker that has crashed (external process PID exited)
def test_case_03_worker_crashed_external_process(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="export_render", project_id=None)
    # 999999 is a dead PID
    orch.start_job(job.id, stage="rendering_mp4", worker_pid=999999)

    # Backdate past grace period (>30s)
    past = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()
    with sqlite_session(orch.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (past, job.id))

    stalled = orch.check_stalled_jobs(timeout_seconds=600.0)
    assert job.id in stalled

    rec = orch.get_job(job.id)
    assert rec.status == "failed"


# Case 4: Worker that raises an exception
def test_case_04_worker_raises_exception(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="media_analysis", project_id=None)
    orch.start_job(job.id, stage="extracting_audio")

    # Simulated worker unhandled exception
    try:
        raise RuntimeError("FFmpeg demux failure: invalid audio stream")
    except Exception as exc:
        orch.fail_job(job.id, error_message=str(exc))

    rec = orch.get_job(job.id)
    assert rec.status == "failed"
    assert "FFmpeg demux failure" in rec.error_message
    assert rec.current_stage == "failed"


# Case 5: Worker that completes successfully with verified completion evidence
def test_case_05_worker_completes_successfully(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="media_analysis", project_id=None)
    orch.start_job(job.id, stage="analyzing_scenes")

    # Intermediate progress
    orch.save_checkpoint(job.id, stage="analyzing_scenes", completed_units=50, total_units=100)
    rec1 = orch.get_job(job.id)
    assert rec1.progress_pct == 50.0

    # Final completion with evidence
    evidence = {"scenes_count": 42, "transcript_segments": 115, "duration_seconds": 120.5}
    orch.complete_job(job.id, result_summary=evidence)

    rec2 = orch.get_job(job.id)
    assert rec2.status == "completed"
    assert rec2.progress_pct == 100.0
    assert rec2.error_message is None
    assert rec2.result_metadata == evidence


# Case 6: Worker that attempts to update a terminal job
def test_case_06_worker_attempts_update_terminal_job(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="media_analysis", project_id=None)
    orch.start_job(job.id, stage="starting")
    orch.complete_job(job.id, result_summary={"initial": True})

    orig = orch.get_job(job.id)
    assert orig.status == "completed"

    # Attempt late checkpoint update
    orch.save_checkpoint(job.id, stage="late_stage", completed_units=99, total_units=100)
    # Attempt late heartbeat
    orch.record_heartbeat(job.id, progress_pct=50.0, stage="late_heartbeat")

    rec = orch.get_job(job.id)
    assert rec.status == "completed"
    assert rec.progress_pct == 100.0
    assert rec.current_stage == "completed"
    assert rec.result_metadata == {"initial": True}


# Case 7: Job whose process identifier is 'local' rather than a numeric PID
def test_case_07_worker_pid_is_local_string(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="media_analysis", project_id=None)
    orch.start_job(job.id, stage="transcribing_speech", worker_pid="local")

    rec = orch.get_job(job.id)
    assert rec.worker_pid == "local"

    # Watchdog must handle non-numeric pid gracefully without throwing TypeError or premature fail
    stalled = orch.check_stalled_jobs(timeout_seconds=600.0)
    assert job.id not in stalled
    assert rec.status == "running"


# Case 8: Worker that exits without persisting its final outputs
def test_case_08_worker_exits_without_persisting_outputs(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="export_render", project_id=None)
    orch.start_job(job.id, stage="encoding_mp4", worker_pid="local")
    orch.save_checkpoint(job.id, stage="encoding_mp4", completed_units=85, total_units=100)

    # Worker crashes/exits silently; watchdog times out
    past = (datetime.now(timezone.utc) - timedelta(seconds=650)).isoformat()
    with sqlite_session(orch.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (past, job.id))

    stalled = orch.check_stalled_jobs(timeout_seconds=600.0)
    assert job.id in stalled

    rec = orch.get_job(job.id)
    # Must NOT be completed because no completion evidence exists
    assert rec.status == "failed"
    assert rec.progress_pct == 85.0


# Case 9: Worker that reports completion after job has already been canceled
def test_case_09_worker_reports_completion_after_cancellation(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="media_analysis", project_id=None)
    orch.start_job(job.id, stage="analyzing")

    # User cancels the job (running -> cancelling -> cancelled)
    orch.request_cancellation(job.id)
    rec_cancelling = orch.get_job(job.id)
    assert rec_cancelling.status == "cancelling"

    # Attempting to complete while cancelling must be rejected
    with pytest.raises(AppError) as exc_info:
        orch.complete_job(job.id, result_summary={"late": "result"})
    assert "INVALID_JOB_TRANSITION" in exc_info.value.code

    # Worker honors cancellation and reaches cancelled terminal state
    orch.transition_job_state(job.id, "cancelled")
    rec_cancelled = orch.get_job(job.id)
    assert rec_cancelled.status == "cancelled"

    # Late worker completion on cancelled terminal job must raise INVALID_JOB_TRANSITION
    with pytest.raises(AppError) as exc_info:
        orch.complete_job(job.id, result_summary={"late": "result"})
    assert "INVALID_JOB_TRANSITION" in exc_info.value.code

    # Late checkpoint must be silently dropped, leaving job cancelled
    orch.save_checkpoint(job.id, stage="completed", completed_units=100, total_units=100)

    final_rec = orch.get_job(job.id)
    assert final_rec.status == "cancelled"
    assert final_rec.current_stage != "completed"


# Case 10: Worker that reports progress after being marked failed
def test_case_10_worker_reports_progress_after_marked_failed(tmp_path: Path):
    orch = _setup_orchestrator(tmp_path)
    job = orch.create_job(job_type="media_analysis", project_id=None)
    orch.start_job(job.id, stage="transcribing")
    orch.fail_job(job.id, error_message="FatalTimeout: watchdog marked stalled")

    rec_failed = orch.get_job(job.id)
    assert rec_failed.status == "failed"

    # Late worker checkpoint reporting 100% completion must NOT resurrect the job
    orch.save_checkpoint(job.id, stage="completed", completed_units=100, total_units=100)
    orch.record_heartbeat(job.id, progress_pct=100.0, stage="completed")

    final_rec = orch.get_job(job.id)
    assert final_rec.status == "failed"
    assert final_rec.current_stage == "failed"
    assert "FatalTimeout" in final_rec.error_message
