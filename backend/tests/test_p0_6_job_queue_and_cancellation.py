"""
P0.6 Regression Test Suite: Job Queue, Cancellation, Worker Reliability & Restart Recovery
Comprehensive verification of all 20 job lifecycle, state transition, cancellation,
monotonic progress, stall detection, retry, and crash-recovery invariants.
"""

import os
import sys
import time
import json
import sqlite3
import subprocess
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.services.jobs import JobOrchestrator


def _setup_test_orchestrator(tmp_path: Path) -> tuple[Settings, JobOrchestrator]:
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(
        app_name="ZezEditTestP06",
        environment="testing",
        storage_root=storage_root,
        max_concurrent_jobs=4,
    )
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO projects (id, name, storage_subdir, created_at, updated_at) "
            "VALUES ('proj_p06', 'P06 Test Project', 'proj_p06', datetime('now'), datetime('now'));"
        )
    return settings, JobOrchestrator(settings, layout.db_file)


# ---------------------------------------------------------------------------
# 1. Valid Job State Transitions
# ---------------------------------------------------------------------------
def test_01_valid_job_state_transitions(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    assert job.status == "queued"

    # queued -> running
    running_job = orch.transition_job_state(job.id, "running", stage="analyzing")
    assert running_job.status == "running"
    assert running_job.started_at is not None

    # running -> completed (with valid evidence dummy file)
    dummy_out = tmp_path / "test_out.mp4"
    dummy_out.write_bytes(b"dummy mp4 content")
    completed_job = orch.transition_job_state(
        job.id, "completed", stage="completed", result_metadata={"output_path": str(dummy_out)}
    )
    assert completed_job.status == "completed"
    assert completed_job.progress_pct == 100.0
    assert completed_job.completed_at is not None


# ---------------------------------------------------------------------------
# 2. Invalid Terminal-State Transitions
# ---------------------------------------------------------------------------
def test_02_invalid_terminal_state_transitions(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(job.id)
    orch.fail_job(job.id, "Simulated worker failure")

    failed_job = orch.get_job(job.id)
    assert failed_job.status == "failed"

    # Cannot transition failed -> completed directly
    with pytest.raises(AppError) as exc_info:
        orch.transition_job_state(job.id, "completed")
    assert exc_info.value.code == "INVALID_JOB_TRANSITION"

    # Cannot complete_job directly on failed
    with pytest.raises(AppError) as exc_info:
        orch.complete_job(job.id)
    assert exc_info.value.code == "INVALID_JOB_TRANSITION"


# ---------------------------------------------------------------------------
# 3. Cancellation Before Execution Starts (Queued -> Cancelled)
# ---------------------------------------------------------------------------
def test_03_cancellation_before_execution_starts(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    assert job.status == "queued"

    cancelled_job = orch.request_cancellation(job.id)
    assert cancelled_job.status == "cancelled"
    assert cancelled_job.cancelled_at is not None
    assert cancelled_job.current_stage == "cancelled_before_run"

    # Cannot cancel an already cancelled job
    with pytest.raises(AppError) as exc_info:
        orch.request_cancellation(job.id)
    assert exc_info.value.code == "JOB_TERMINAL"


# ---------------------------------------------------------------------------
# 4. Cancellation During a Running Python Task
# ---------------------------------------------------------------------------
def test_04_cancellation_during_running_python_task(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(job.id, stage="analyzing_frames")

    cancelling_job = orch.request_cancellation(job.id)
    assert cancelling_job.status in ("cancelling", "cancelled")

    # Finalize cooperative cancellation
    final_job = orch.transition_job_state(job.id, "cancelled", stage="cancelled_by_user")
    assert final_job.status == "cancelled"
    assert final_job.cancelled_at is not None


# ---------------------------------------------------------------------------
# 5. Cancellation During an FFmpeg Subprocess
# ---------------------------------------------------------------------------
def test_05_cancellation_during_ffmpeg_subprocess(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    # Spawn a sleeping background process to simulate an in-flight FFmpeg render
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        job = orch.create_job("export_render", "proj_p06", input_config={})
        orch.transition_job_state(job.id, "running", worker_pid=proc.pid, stage="rendering_video")

        # Request cancellation
        cancelling_job = orch.request_cancellation(job.id)
        assert cancelling_job.status == "cancelled"

        # Give process tree termination a moment
        time.sleep(0.5)
        # Proc should have been terminated
        assert proc.poll() is not None
    finally:
        if proc.poll() is None:
            proc.kill()


# ---------------------------------------------------------------------------
# 6. Confirmation That Canceled Child Processes Exit
# ---------------------------------------------------------------------------
def test_06_confirmation_canceled_child_processes_exit(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        job = orch.create_job("export_render", "proj_p06", input_config={})
        orch.start_job(job.id, worker_pid=child.pid)

        # Terminate pid tree
        orch._terminate_pid_tree(child.pid)
        time.sleep(0.3)
        assert child.poll() is not None
    finally:
        if child.poll() is None:
            child.kill()


# ---------------------------------------------------------------------------
# 7. No Orphan Subprocesses Remain After Cancellation
# ---------------------------------------------------------------------------
def test_07_no_orphan_subprocesses_after_cancellation(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    pid = p.pid
    try:
        orch._terminate_pid_tree(pid)
        time.sleep(0.2)
        assert p.poll() is not None
    finally:
        if p.poll() is None:
            p.kill()


# ---------------------------------------------------------------------------
# 8. Worker Crash During Execution (Detection and Recovery)
# ---------------------------------------------------------------------------
def test_08_worker_crash_recovery(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(job.id, stage="extracting_features")

    # Simulate sudden backend/worker crash leaving state as 'running'
    recovered = orch.recover_interrupted_jobs()
    assert job.id in recovered

    recovered_job = orch.get_job(job.id)
    assert recovered_job.status == "interrupted"
    assert "restarted" in recovered_job.error_message.lower()


# ---------------------------------------------------------------------------
# 9. Stale Job Detection in check_stalled_jobs
# ---------------------------------------------------------------------------
def test_09_stale_job_detection(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(job.id, stage="transcribing_audio")

    # Age updated_at by 15 minutes
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    with sqlite3.connect(orch.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (old_time, job.id))

    stalled = orch.check_stalled_jobs(timeout_seconds=300.0)
    assert job.id in stalled

    stalled_job = orch.get_job(job.id)
    assert stalled_job.status == "failed"
    assert stalled_job.current_stage == "stalled_timeout"
    assert "stalled" in stalled_job.error_message.lower()


# ---------------------------------------------------------------------------
# 10. Heartbeat Without Real Progress (Liveness vs Percentage)
# ---------------------------------------------------------------------------
def test_10_heartbeat_without_real_progress(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(job.id, stage="analyzing_frames")
    orch.save_checkpoint(job.id, stage="analyzing_frames", completed_units=25, total_units=100)

    # Initial progress should be 25.0%
    j_before = orch.get_job(job.id)
    assert j_before.progress_pct == 25.0
    initial_updated = j_before.updated_at

    time.sleep(0.05)
    # Heartbeat without changing progress (liveness update only)
    hb_job = orch.record_heartbeat(job.id, stage_details={"info": "still analyzing frame 250"})
    assert hb_job.progress_pct == 25.0
    assert hb_job.updated_at >= initial_updated


# ---------------------------------------------------------------------------
# 11. Genuine Monotonic Progress Updates
# ---------------------------------------------------------------------------
def test_11_monotonic_progress_updates(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(job.id)

    # Progress at 40%
    orch.transition_job_state(job.id, "running", progress_pct=40.0)
    assert orch.get_job(job.id).progress_pct == 40.0

    # Attempt backwards progress (e.g. 20%) -> must remain 40.0%
    orch.transition_job_state(job.id, "running", progress_pct=20.0)
    assert orch.get_job(job.id).progress_pct == 40.0

    # Checkpoint with lower progress -> must remain 40.0%
    orch.save_checkpoint(job.id, stage="analyzing", progress_pct=30.0)
    assert orch.get_job(job.id).progress_pct == 40.0

    # Running job progress must be strictly capped below 100% (99.0%)
    orch.transition_job_state(job.id, "running", progress_pct=100.0)
    assert orch.get_job(job.id).progress_pct == 99.0

    # Only completed status sets 100.0%
    dummy = tmp_path / "valid.mp4"
    dummy.write_bytes(b"content")
    completed = orch.transition_job_state(
        job.id, "completed", result_metadata={"output_path": str(dummy)}
    )
    assert completed.progress_pct == 100.0


# ---------------------------------------------------------------------------
# 12. Retry After Failure
# ---------------------------------------------------------------------------
def test_12_retry_after_failure(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(job.id)
    orch.fail_job(job.id, "Network timeout during analysis")

    retried = orch.retry_job(job.id)
    assert retried.status == "queued"
    assert retried.retry_count == 1
    assert retried.error_message is None


# ---------------------------------------------------------------------------
# 13. Retry After Cancellation
# ---------------------------------------------------------------------------
def test_13_retry_after_cancellation(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.request_cancellation(job.id)
    assert orch.get_job(job.id).status == "cancelled"

    retried = orch.retry_job(job.id)
    assert retried.status == "queued"
    assert retried.retry_count == 1
    assert retried.error_message is None


# ---------------------------------------------------------------------------
# 14. Duplicate Job Dispatch Prevention (Atomic Claiming)
# ---------------------------------------------------------------------------
def test_14_duplicate_job_dispatch_prevention(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={"run_id": "r1"})

    # First claim succeeds
    claimed1 = orch.claim_next_queued_job(worker_id="worker_A")
    assert claimed1 is not None
    assert claimed1.id == job.id
    assert claimed1.worker_id == "worker_A"

    # Second claim returns None (no more queued jobs)
    claimed2 = orch.claim_next_queued_job(worker_id="worker_B")
    assert claimed2 is None


# ---------------------------------------------------------------------------
# 15. Concurrent Worker Ownership
# ---------------------------------------------------------------------------
def test_15_concurrent_worker_ownership(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    j1 = orch.create_job("media_analysis", "proj_p06", priority=10, input_config={"run_id": "r1"})
    j2 = orch.create_job("export_render", "proj_p06", priority=5, input_config={"export_id": "e1"})

    claimed1 = orch.claim_next_queued_job(worker_id="worker_1")
    claimed2 = orch.claim_next_queued_job(worker_id="worker_2")

    assert claimed1 is not None
    assert claimed1.id == j1.id
    assert claimed1.worker_id == "worker_1"
    assert claimed2 is not None
    assert claimed2.id == j2.id
    assert claimed2.worker_id == "worker_2"


# ---------------------------------------------------------------------------
# 16. No Duplicate Exports After Retry (Idempotency)
# ---------------------------------------------------------------------------
def test_16_no_duplicate_exports_after_retry(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    export_id = "exp_test_retry"
    with sqlite3.connect(orch.db_path) as conn:
        conn.execute(
            """
            INSERT INTO exports (id, project_id, media_asset_id, title, output_filename, status, created_at)
            VALUES (?, 'proj_p06', 'asset_p06', 'Test Export', 'test.mp4', 'queued', datetime('now'))
            """,
            (export_id,),
        )

    job = orch.create_job("export_render", "proj_p06", input_config={"export_id": export_id})
    orch.start_job(job.id)
    orch.fail_job(job.id, "FFmpeg crashed")

    # Retry job in-place
    retried_job = orch.retry_job(job.id, create_new_attempt=False)
    assert retried_job.id == job.id

    with sqlite3.connect(orch.db_path) as conn:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM exports WHERE id = ?", (export_id,)
        ).fetchone()[0]
        assert row_count == 1


# ---------------------------------------------------------------------------
# 17. No Completion After Cancellation
# ---------------------------------------------------------------------------
def test_17_no_completion_after_cancellation(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.request_cancellation(job.id)
    assert orch.get_job(job.id).status == "cancelled"

    # Late checkpoint received after cancellation must be rejected
    orch.save_checkpoint(job.id, stage="completed", completed_units=100, total_units=100, progress_pct=100.0)
    job_after_cp = orch.get_job(job.id)
    assert job_after_cp.status == "cancelled"
    assert job_after_cp.progress_pct != 100.0

    # Late heartbeat received after cancellation must be rejected
    orch.record_heartbeat(job.id, progress_pct=100.0, stage="completed")
    job_after_hb = orch.get_job(job.id)
    assert job_after_hb.status == "cancelled"

    # Direct completion must raise AppError
    with pytest.raises(AppError) as exc_info:
        orch.complete_job(job.id)
    assert exc_info.value.code == "INVALID_JOB_TRANSITION"


# ---------------------------------------------------------------------------
# 18. Job Recovery After Application Restart
# ---------------------------------------------------------------------------
def test_18_job_recovery_after_application_restart(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    j_running = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(j_running.id)

    j_cancelling = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(j_cancelling.id)
    orch.transition_job_state(j_cancelling.id, "cancelling")

    # Application restarts
    new_orch = JobOrchestrator(settings, orch.db_path)
    recovered = new_orch.recover_interrupted_jobs()

    assert j_running.id in recovered
    assert j_cancelling.id in recovered
    assert new_orch.get_job(j_running.id).status == "interrupted"
    assert new_orch.get_job(j_cancelling.id).status == "interrupted"


# ---------------------------------------------------------------------------
# 19. Database Consistency After Interrupted Execution
# ---------------------------------------------------------------------------
def test_19_database_consistency_after_interrupted_execution(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "proj_p06", input_config={})
    orch.start_job(job.id)

    # Link an analysis_run to this job
    run_id = "run_test_consistency"
    with sqlite3.connect(orch.db_path) as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, job_id, status, current_stage, created_at, updated_at)
            VALUES (?, 'proj_p06', 'asset_dummy', ?, 'running', 'analyzing', datetime('now'), datetime('now'))
            """,
            (run_id, job.id),
        )

    # Recover interrupted jobs
    orch.recover_interrupted_jobs()

    with sqlite3.connect(orch.db_path) as conn:
        run_row = conn.execute("SELECT status FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        assert run_row[0] == "interrupted"


# ---------------------------------------------------------------------------
# 20. Frontend Queue Stats and Terminal State Querying
# ---------------------------------------------------------------------------
def test_20_frontend_queue_stats_and_terminal_querying(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    j1 = orch.create_job("custom_task", "proj_p06", input_config={})
    j2 = orch.create_job("custom_task", "proj_p06", input_config={})
    orch.start_job(j2.id)

    j3 = orch.create_job("custom_task", "proj_p06", input_config={})
    dummy = tmp_path / "valid2.mp4"
    dummy.write_bytes(b"content")
    orch.start_job(j3.id)
    orch.complete_job(j3.id, result_summary={"output_path": str(dummy)})

    j4 = orch.create_job("custom_task", "proj_p06", input_config={})
    orch.start_job(j4.id)
    orch.fail_job(j4.id, "error")

    j5 = orch.create_job("custom_task", "proj_p06", input_config={})
    orch.request_cancellation(j5.id)

    stats = orch.get_queue_stats()
    assert stats["total_jobs"] == 5
    assert stats["queued"] == 1
    assert stats["running"] == 1
    assert stats["completed"] == 1
    assert stats["failed"] == 1
    assert stats["cancelled"] == 1
    assert j2.id in stats["active_job_ids"]
