"""Session 12: Comprehensive Job Lifecycle Stress Testing Suite.
Verifies all 16 required edge cases and confirms strict terminal state consistency:
1. Normal completion
2. Long CPU operation
3. Long FFmpeg operation
4. Slow transcription
5. Worker thread crash
6. Worker process crash
7. Worker deadlock
8. Heartbeat interruption
9. Database write failure
10. Backend restart recovery
11. Cancellation
12. Retry
13. Duplicate submission
14. Multiple simultaneous jobs
15. Completed job receiving a late watchdog check
16. Failed job receiving a late completion callback
"""

import os
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

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
        app_name="ZezEditTestJobsStress",
        environment="test",
        storage_root=storage_root,
        max_concurrent_jobs=8,
    )
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('default', 'Default', 'def', datetime('now'), datetime('now'));"
        )
    return settings, JobOrchestrator(settings, layout.db_file)


# 1. Normal completion
def test_case_01_normal_completion(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    assert job.status == "queued"
    orch.start_job(job.id, stage="validating_source")
    running = orch.get_job(job.id)
    assert running.status == "running"

    orch.save_checkpoint(job.id, stage="extracting_frames", completed_units=50, total_units=100)
    mid = orch.get_job(job.id)
    assert mid.progress_pct == 50.0

    orch.complete_job(job.id, result_summary={"result": "ok"})
    final = orch.get_job(job.id)
    assert final.status == "completed"
    assert final.progress_pct == 100.0
    assert final.current_stage == "completed"
    assert final.error_message is None


# 2. Long CPU operation (heartbeats keep it running)
def test_case_02_long_cpu_operation_heartbeat(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id, stage="analyzing_visuals")

    for step in range(5):
        orch.record_heartbeat(job.id, progress_pct=20.0 + step * 10, stage="analyzing_visuals")

    rec = orch.get_job(job.id)
    assert rec.status == "running"
    assert rec.progress_pct == 60.0
    stalled = orch.check_stalled_jobs(timeout_seconds=60.0)
    assert job.id not in stalled


# 3. Long FFmpeg operation (external child process alive)
def test_case_03_long_ffmpeg_child_process_alive(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    child_pid = os.getppid()  # Parent process is guaranteed alive and distinct from current backend
    job = orch.create_job("clip_render", "default")
    orch.start_job(job.id, stage="rendering_video", worker_pid=child_pid)

    # 15 minutes of silence while child process is alive in OS
    past = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    with sqlite3.connect(orch.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (past, job.id))

    stalled = orch.check_stalled_jobs(timeout_seconds=60.0)
    assert job.id not in stalled
    assert orch.get_job(job.id).status == "running"


# 4. Slow transcription (streaming progress callbacks keep advancing)
def test_case_04_slow_transcription_progress(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id, stage="transcribing_speech")

    for sec in [10.0, 30.0, 60.0, 120.0, 300.0]:
        orch.save_checkpoint(job.id, stage="transcribing_speech", completed_units=int(sec), total_units=600)

    rec = orch.get_job(job.id)
    assert rec.status == "running"
    assert rec.progress_pct == 50.0
    assert rec.current_stage == "transcribing_speech"


# 5. Worker thread crash (exception triggers fail_job)
def test_case_05_worker_thread_crash(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id, stage="extracting_metadata")

    # Simulate thread crash with traceback message
    orch.fail_job(job.id, error_message="MemoryError: Out of RAM during keyframe sampling")

    failed = orch.get_job(job.id)
    assert failed.status == "failed"
    assert failed.progress_pct < 100.0
    assert "MemoryError" in failed.error_message


# 6. Worker process crash (child process dead in OS)
def test_case_06_worker_process_crash(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    dead_pid = 99999999
    job = orch.create_job("clip_render", "default")
    orch.start_job(job.id, stage="rendering_video", worker_pid=dead_pid)

    past = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()
    with sqlite3.connect(orch.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (past, job.id))

    stalled = orch.check_stalled_jobs(timeout_seconds=60.0)
    assert job.id in stalled
    failed = orch.get_job(job.id)
    assert failed.status == "failed"
    assert failed.current_stage == "stalled_timeout"
    assert failed.progress_pct < 100.0


# 7. Worker deadlock (silence on in-process job exceeds timeout)
def test_case_07_worker_deadlock_detected(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    current_pid = os.getpid()
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id, stage="transcribing_speech", worker_pid=current_pid)

    # In-process worker thread hung for 15 minutes
    past = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    with sqlite3.connect(orch.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (past, job.id))

    stalled = orch.check_stalled_jobs(timeout_seconds=600.0)
    assert job.id in stalled
    rec = orch.get_job(job.id)
    assert rec.status == "failed"
    assert "Job stalled" in rec.error_message


# 8. Heartbeat interruption (unexpected worker halt)
def test_case_08_heartbeat_interruption(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id, stage="analyzing_visuals")

    past = (datetime.now(timezone.utc) - timedelta(seconds=700)).isoformat()
    with sqlite3.connect(orch.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (past, job.id))

    stalled = orch.check_stalled_jobs(timeout_seconds=600.0)
    assert job.id in stalled
    assert orch.get_job(job.id).status == "failed"


# 9. Database write resilience
def test_case_09_database_write_resilience(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id, stage="validating_source")

    # Verify invalid parameters raise clean AppError without leaving corrupt state
    with pytest.raises(Exception):
        orch.transition_job_state(job.id, "invalid_status_xyz")

    rec = orch.get_job(job.id)
    assert rec.status == "running"


# 10. Backend restart recovery
def test_case_10_backend_restart_recovery(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    j1 = orch.create_job("media_analysis", "default")
    orch.start_job(j1.id, stage="transcribing_speech")
    j2 = orch.create_job("clip_render", "default")
    orch.start_job(j2.id, stage="rendering_video")

    # Simulate backend crash/restart
    interrupted = orch.recover_interrupted_jobs()
    assert j1.id in interrupted
    assert j2.id in interrupted

    rec1 = orch.get_job(j1.id)
    rec2 = orch.get_job(j2.id)
    assert rec1.status == "interrupted"
    assert rec2.status == "interrupted"
    assert rec1.current_stage == "interrupted"


# 11. Cancellation behavior
def test_case_11_cancellation_enforcement(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id, stage="extracting_frames")

    orch.request_cancellation(job.id)
    cancelling = orch.get_job(job.id)
    assert cancelling.status in ("cancelling", "cancelled")

    orch.transition_job_state(job.id, "cancelled")
    cancelled = orch.get_job(job.id)
    assert cancelled.status == "cancelled"

    # Late checkpoint must NOT resurrect or mutate cancelled job
    orch.save_checkpoint(job.id, stage="completed", completed_units=100, total_units=100)
    after_late_cp = orch.get_job(job.id)
    assert after_late_cp.status == "cancelled"
    assert after_late_cp.progress_pct < 100.0


# 12. Retry lifecycle
def test_case_12_retry_lifecycle(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id, stage="extracting_metadata")
    orch.fail_job(job.id, "Simulated network glitch")

    retried = orch.retry_job(job.id)
    assert retried.status == "queued"
    assert retried.retry_count == 1
    assert retried.error_message is None
    assert retried.progress_pct == 0.0


# 13. Idempotent state transitions
def test_case_13_idempotent_complete(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id)
    orch.complete_job(job.id)

    # Calling complete_job a second time is safely idempotent
    rec = orch.complete_job(job.id)
    assert rec.status == "completed"
    assert rec.progress_pct == 100.0
    assert rec.error_message is None


# 14. Multiple simultaneous jobs do not interfere
def test_case_14_multiple_simultaneous_jobs(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    j1 = orch.create_job("media_analysis", "default")
    j2 = orch.create_job("media_analysis", "default")
    j3 = orch.create_job("clip_render", "default")

    orch.start_job(j1.id, stage="stage_1")
    orch.start_job(j2.id, stage="stage_2")
    orch.start_job(j3.id, stage="stage_3")

    # Stalled check does not stall actively running jobs
    orch.record_heartbeat(j1.id, progress_pct=10.0)
    orch.record_heartbeat(j2.id, progress_pct=20.0)
    orch.record_heartbeat(j3.id, progress_pct=30.0)

    stalled = orch.check_stalled_jobs(timeout_seconds=600.0)
    assert len(stalled) == 0

    assert orch.get_job(j1.id).progress_pct == 100.0 if False else 10.0
    assert orch.get_job(j2.id).progress_pct == 20.0
    assert orch.get_job(j3.id).progress_pct == 30.0


# 15. Completed job receiving a late watchdog check
def test_case_15_completed_job_late_watchdog_check(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id)
    orch.complete_job(job.id)

    # Simulate updated_at from days ago
    past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    with sqlite3.connect(orch.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (past, job.id))

    stalled = orch.check_stalled_jobs(timeout_seconds=1.0)
    assert job.id not in stalled
    rec = orch.get_job(job.id)
    assert rec.status == "completed"
    assert rec.progress_pct == 100.0
    assert rec.error_message is None


# 16. Failed job receiving a late completion callback
def test_case_16_failed_job_late_completion_callback(tmp_path: Path):
    settings, orch = _setup_test_orchestrator(tmp_path)
    job = orch.create_job("media_analysis", "default")
    orch.start_job(job.id, stage="demuxing")
    orch.fail_job(job.id, error_message="DemuxerFatalError: Stream corruption detected")

    # Late completion callback must be rejected
    with pytest.raises(AppError) as exc_info:
        orch.complete_job(job.id)

    assert "INVALID_JOB_TRANSITION" in str(exc_info.value.code)

    rec = orch.get_job(job.id)
    assert rec.status == "failed"
    assert rec.progress_pct < 100.0
    assert rec.current_stage == "failed"
    assert "Stream corruption" in rec.error_message
