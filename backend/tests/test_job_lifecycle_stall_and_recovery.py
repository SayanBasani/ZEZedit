"""Tests for Session 11: Job lifecycle, stall detection, heartbeat recording, and self-healing recovery."""

import os
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.core.config import Settings
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
        app_name="ZezEditTestJobsLifecycle",
        environment="test",
        storage_root=storage_root,
        max_concurrent_jobs=4,
    )
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('default', 'Default', 'def', datetime('now'), datetime('now'));"
        )
    return settings, JobOrchestrator(settings, layout.db_file)


def test_completed_or_100pct_job_never_marked_stalled(tmp_path: Path):
    """Jobs that have completed stage or reached 100% must never be flagged as stalled."""
    settings, orchestrator = _setup_test_orchestrator(tmp_path)
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

    # Job 1: stage='completed'
    j1 = orchestrator.create_job("media_analysis", "default", input_config={})
    orchestrator.start_job(j1.id, stage="completed")
    with sqlite3.connect(orchestrator.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ?, progress_pct = 100.0 WHERE id = ?", (old_time, j1.id))

    # Job 2: progress_pct = 100.0
    j2 = orchestrator.create_job("media_analysis", "default", input_config={})
    orchestrator.start_job(j2.id, stage="finalizing")
    with sqlite3.connect(orchestrator.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ?, progress_pct = 100.0 WHERE id = ?", (old_time, j2.id))

    stalled = orchestrator.check_stalled_jobs(timeout_seconds=60.0)
    assert j1.id not in stalled
    assert j2.id not in stalled

    rec1 = orchestrator.get_job(j1.id)
    rec2 = orchestrator.get_job(j2.id)
    assert rec1.status != "failed"
    assert rec2.status != "failed"


def test_active_external_child_pid_never_marked_stalled_within_grace(tmp_path: Path):
    """If a dedicated external child worker process (e.g. ffmpeg.exe) is alive in the OS, long execution without heartbeat does not cause premature failure."""
    settings, orchestrator = _setup_test_orchestrator(tmp_path)
    # Use parent process ID as an external active process that is distinct from current backend process
    external_pid = os.getppid()

    # Simulate 120s of silence while running
    past_time = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    job = orchestrator.create_job("clip_render", "default", input_config={})
    orchestrator.start_job(job.id, stage="rendering_video", worker_pid=external_pid)

    with sqlite3.connect(orchestrator.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ?, progress_pct = 25.0 WHERE id = ?", (past_time, job.id))

    stalled = orchestrator.check_stalled_jobs(timeout_seconds=60.0)
    assert job.id not in stalled
    updated_rec = orchestrator.get_job(job.id)
    assert updated_rec.status == "running"


def test_in_process_job_stalls_when_silent_beyond_timeout(tmp_path: Path):
    """If an in-process worker thread (same backend PID or None) is silent beyond timeout, it stalls even though backend PID is alive."""
    settings, orchestrator = _setup_test_orchestrator(tmp_path)
    current_pid = os.getpid()

    # Simulate 120s of silence while running
    past_time = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    job = orchestrator.create_job("media_analysis", "default", input_config={})
    orchestrator.start_job(job.id, stage="transcribing_speech", worker_pid=current_pid)

    with sqlite3.connect(orchestrator.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ?, progress_pct = 25.0 WHERE id = ?", (past_time, job.id))

    stalled = orchestrator.check_stalled_jobs(timeout_seconds=60.0)
    assert job.id in stalled
    updated_rec = orchestrator.get_job(job.id)
    assert updated_rec.status == "failed"
    assert "Job stalled" in (updated_rec.error_message or "")


def test_dead_os_pid_marked_stalled_after_grace(tmp_path: Path):
    """If the worker process PID is dead and exceeds the 30s grace period, it is marked stalled."""
    settings, orchestrator = _setup_test_orchestrator(tmp_path)
    dead_pid = 99999999  # Guaranteed non-existent PID

    past_time = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()
    job = orchestrator.create_job("clip_render", "default", input_config={})
    orchestrator.start_job(job.id, stage="rendering_video", worker_pid=dead_pid)

    with sqlite3.connect(orchestrator.db_path) as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (past_time, job.id))

    stalled = orchestrator.check_stalled_jobs(timeout_seconds=60.0)
    assert job.id in stalled

    updated_rec = orchestrator.get_job(job.id)
    assert updated_rec.status == "failed"
    assert "Job stalled" in (updated_rec.error_message or "")


def test_checkpoint_never_heals_failed_status(tmp_path: Path):
    """A failed job must never be healed by late save_checkpoint calls (Session 14 invariant)."""
    settings, orchestrator = _setup_test_orchestrator(tmp_path)
    job = orchestrator.create_job("media_analysis", "default", input_config={})
    orchestrator.start_job(job.id, stage="transcribing_speech")

    # Force failure with stalled message
    with sqlite3.connect(orchestrator.db_path) as conn:
        conn.execute(
            """
            UPDATE jobs 
            SET status = 'failed', error_message = 'Job stalled: no worker heartbeat or progress update for 61s.'
            WHERE id = ?
            """,
            (job.id,),
        )

    # Worker finishes and calls save_checkpoint for completed stage
    orchestrator.save_checkpoint(
        job_id=job.id,
        stage="completed",
        completed_units=100,
        total_units=100,
        intermediate_artifacts={"output": "ready.mp4"},
    )

    rec = orchestrator.get_job(job.id)
    assert rec.status == "failed"
    assert "Job stalled" in (rec.error_message or "")


def test_complete_job_rejects_failed_status(tmp_path: Path):
    """Calling complete_job on a job in failed status is rejected (Session 14 invariant)."""
    from app.core.errors import AppError
    settings, orchestrator = _setup_test_orchestrator(tmp_path)
    job = orchestrator.create_job("candidate_generation", "default", input_config={})
    orchestrator.start_job(job.id, stage="analyzing")

    with sqlite3.connect(orchestrator.db_path) as conn:
        conn.execute(
            """
            UPDATE jobs 
            SET status = 'failed', error_message = 'Job stalled: no worker heartbeat or progress update for 65s.'
            WHERE id = ?
            """,
            (job.id,),
        )

    # Call complete_job must be rejected with INVALID_JOB_TRANSITION
    with pytest.raises(AppError) as exc_info:
        orchestrator.complete_job(job.id, result_summary={"candidates_count": 5})
    assert exc_info.value.code == "INVALID_JOB_TRANSITION"
