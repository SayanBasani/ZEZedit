"""Comprehensive tests for Session 15: Long-video endurance, job recovery, watchdog transitions, and request idempotency."""

import os
import json
import time
import asyncio
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.migrator import run_migrations
from app.db.connection import sqlite_session
from app.services.jobs import JobOrchestrator
from app.services.analysis_pipeline import VideoAnalysisPipeline, _heartbeat_ticker
from app.services.export_service import ExportService, RenderExportRequest


@pytest.fixture
def temp_db(tmp_path: Path):
    """Create a temporary sqlite database initialized with all standard migrations."""
    db_file = tmp_path / "test_session15_endurance.db"
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(db_path=db_file, migrations_dir=migrations_dir)
    return db_file


@pytest.fixture
def mock_settings(tmp_path: Path):
    s = get_settings()
    s.storage_root = tmp_path / "storage"
    s.storage_root.mkdir(parents=True, exist_ok=True)
    return s


# Scenario 1: Long-running work with active progress callbacks keeps ticker alive
def test_heartbeat_ticker_keeps_ticking_with_active_callbacks(temp_db, mock_settings):
    orchestrator = JobOrchestrator(mock_settings, temp_db)
    job = orchestrator.create_job(job_type="media_analysis", priority=150)
    orchestrator.start_job(job.id, stage="transcribing_speech")

    async def _run_test():
        progress_ts = [time.monotonic()]

        async with _heartbeat_ticker(
            job_id=job.id,
            stage_name="transcribing_speech",
            orchestrator=orchestrator,
            last_progress_check=lambda: progress_ts[0],
            max_inactive_seconds=2.0,
            max_stage_seconds=10.0,
        ):
            # Simulate active progress updates every 0.1s
            for _ in range(5):
                await asyncio.sleep(0.15)
                progress_ts[0] = time.monotonic()

    asyncio.run(_run_test())

    rec = orchestrator.get_job(job.id)
    assert rec.status == "running"
    assert rec.current_stage == "transcribing_speech"


# Scenario 2: Inactive/blocked native work triggers ticker halt and watchdog stall
def test_watchdog_detects_stalled_job_when_heartbeats_stop(temp_db, mock_settings):
    orchestrator = JobOrchestrator(mock_settings, temp_db)
    job = orchestrator.create_job(job_type="media_analysis", priority=150)
    orchestrator.start_job(job.id, stage="transcribing_speech")

    # Artificially age the job's updated_at by 700 seconds
    with sqlite_session(temp_db) as conn:
        old_time = "2026-11-15T00:00:00+00:00"
        conn.execute(
            "UPDATE jobs SET updated_at = ?, progress_pct = 40.0, current_stage = 'transcribing' WHERE id = ?",
            (old_time, job.id),
        )

    stalled = orchestrator.check_stalled_jobs(timeout_seconds=60.0)
    assert job.id in stalled

    rec = orchestrator.get_job(job.id)
    assert rec.status == "failed"
    assert rec.current_stage == "stalled_timeout"
    assert "Job stalled: no worker heartbeat" in (rec.error_message or "")


# Scenario 3: Watchdog stall synchronizes cross-table analysis_runs and exports
def test_watchdog_stall_cross_table_synchronization(temp_db, mock_settings):
    orchestrator = JobOrchestrator(mock_settings, temp_db)
    job = orchestrator.create_job(job_type="media_analysis", priority=150)
    orchestrator.start_job(job.id, stage="transcribing_speech")

    with sqlite_session(temp_db) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, storage_subdir, created_at, updated_at)
            VALUES ('proj1', 'Test Project', 'proj1', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, file_size_bytes, duration_seconds, media_type, created_at, updated_at)
            VALUES ('med1', 'proj1', 'sample.mp4', '/path/to/sample.mp4', 1000, 60.0, 'video', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, job_id, profile, status, current_stage, created_at, updated_at)
            VALUES ('run_test1', 'proj1', 'med1', ?, 'balanced', 'running', 'transcribing', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """,
            (job.id,),
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (id, project_id, media_asset_id, analysis_run_id, generation_run_id, start_time, end_time, duration, suggested_start_time, suggested_end_time, suggested_title, title, created_at, updated_at)
            VALUES ('cand1', 'proj1', 'med1', 'run_test1', 'gen1', 10.0, 30.0, 20.0, 10.0, 30.0, 'Clip', 'Clip', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, render_job_id, title, export_preset, target_aspect_ratio, output_filename, status, created_at)
            VALUES ('exp_test1', 'proj1', 'cand1', 'med1', ?, 'Test Export', 'shorts_reels_9_16', '9:16', 'out.mp4', 'rendering', '2026-11-15T00:00:00+00:00')
            """,
            (job.id,),
        )
        # Age updated_at
        conn.execute("UPDATE jobs SET updated_at = '2026-11-15T00:00:00+00:00' WHERE id = ?", (job.id,))

    orchestrator.check_stalled_jobs(timeout_seconds=60.0)

    with sqlite_session(temp_db) as conn:
        run_status = conn.execute("SELECT status, current_stage FROM analysis_runs WHERE id = 'run_test1'").fetchone()
        exp_status = conn.execute("SELECT status FROM exports WHERE id = 'exp_test1'").fetchone()

    assert run_status["status"] == "failed"
    assert run_status["current_stage"] == "stalled_timeout"
    assert exp_status["status"] == "failed"


# Scenario 4: Backend restart recovery marks running jobs interrupted and synchronizes cross tables
def test_recover_interrupted_jobs_synchronizes_cross_tables(temp_db, mock_settings):
    orchestrator = JobOrchestrator(mock_settings, temp_db)
    job = orchestrator.create_job(job_type="media_analysis", priority=150)
    orchestrator.start_job(job.id, stage="transcribing_speech")

    with sqlite_session(temp_db) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, storage_subdir, created_at, updated_at)
            VALUES ('proj1', 'Test Project', 'proj1', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, file_size_bytes, duration_seconds, media_type, created_at, updated_at)
            VALUES ('med1', 'proj1', 'sample.mp4', '/path/to/sample.mp4', 1000, 60.0, 'video', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, job_id, profile, status, current_stage, created_at, updated_at)
            VALUES ('run_rec1', 'proj1', 'med1', ?, 'balanced', 'running', 'transcribing', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """,
            (job.id,),
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (id, project_id, media_asset_id, analysis_run_id, generation_run_id, start_time, end_time, duration, suggested_start_time, suggested_end_time, suggested_title, title, created_at, updated_at)
            VALUES ('cand1', 'proj1', 'med1', 'run_rec1', 'gen1', 10.0, 30.0, 20.0, 10.0, 30.0, 'Clip', 'Clip', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, render_job_id, title, export_preset, target_aspect_ratio, output_filename, status, created_at)
            VALUES ('exp_rec1', 'proj1', 'cand1', 'med1', ?, 'Test Export', 'shorts_reels_9_16', '9:16', 'out.mp4', 'rendering', '2026-11-15T00:00:00+00:00')
            """,
            (job.id,),
        )

    recovered = orchestrator.recover_interrupted_jobs()
    assert job.id in recovered

    rec = orchestrator.get_job(job.id)
    assert rec.status == "interrupted"

    with sqlite_session(temp_db) as conn:
        run_row = conn.execute("SELECT status, current_stage FROM analysis_runs WHERE id = 'run_rec1'").fetchone()
        exp_row = conn.execute("SELECT status FROM exports WHERE id = 'exp_rec1'").fetchone()

    assert run_row["status"] == "interrupted"
    assert run_row["current_stage"] == "interrupted"
    assert exp_row["status"] == "failed"


# Scenario 5: Late worker completion after cancellation or failure is strictly rejected
def test_late_worker_completion_rejected_after_cancellation_or_failure(temp_db, mock_settings):
    orchestrator = JobOrchestrator(mock_settings, temp_db)
    job = orchestrator.create_job(job_type="media_analysis", priority=150)
    orchestrator.start_job(job.id, stage="transcribing_speech")

    # Cancel the job
    rec_cancelled = orchestrator.request_cancellation(job.id)
    assert rec_cancelled.status in ("cancelling", "cancelled")

    # Worker attempts late completion
    with pytest.raises(AppError) as exc_info:
        orchestrator.complete_job(job.id)
    assert exc_info.value.code == "INVALID_JOB_TRANSITION"

    # Worker attempts late checkpoint
    orchestrator.save_checkpoint(job.id, stage="completed", completed_units=100, total_units=100)
    final_rec = orchestrator.get_job(job.id)
    assert final_rec.status in ("cancelling", "cancelled")
    assert final_rec.current_stage != "completed"


# Scenario 6: Enforce completion evidence (COMPLETION_EVIDENCE_MISSING)
def test_enforce_completion_evidence_missing(temp_db, mock_settings, tmp_path):
    orchestrator = JobOrchestrator(mock_settings, temp_db)
    job = orchestrator.create_job(job_type="export_render", priority=100)
    orchestrator.start_job(job.id)

    missing_file = tmp_path / "nonexistent_rendered.mp4"

    # Specifying missing output file raises COMPLETION_EVIDENCE_MISSING
    with pytest.raises(AppError) as exc_info:
        orchestrator.transition_job_state(
            job.id,
            "completed",
            result_metadata={"output_path": str(missing_file)},
        )
    assert exc_info.value.code == "COMPLETION_EVIDENCE_MISSING"

    # Creating a 0-byte file also raises COMPLETION_EVIDENCE_MISSING
    empty_file = tmp_path / "empty_rendered.mp4"
    empty_file.touch()
    with pytest.raises(AppError) as exc_info2:
        orchestrator.transition_job_state(
            job.id,
            "completed",
            result_metadata={"output_path": str(empty_file)},
        )
    assert exc_info2.value.code == "COMPLETION_EVIDENCE_MISSING"

    # Creating a valid non-empty file succeeds
    valid_file = tmp_path / "valid_rendered.mp4"
    valid_file.write_bytes(b"VALID_MP4_CONTENT")
    completed = orchestrator.transition_job_state(
        job.id,
        "completed",
        result_metadata={"output_path": str(valid_file)},
    )
    assert completed.status == "completed"


# Scenario 7: Watchdog preserves completed / 100% jobs and does not falsely mark them stalled
def test_watchdog_preserves_completed_and_100_percent_jobs(temp_db, mock_settings):
    orchestrator = JobOrchestrator(mock_settings, temp_db)
    job1 = orchestrator.create_job(job_type="media_analysis", priority=150)
    orchestrator.start_job(job1.id)
    orchestrator.complete_job(job1.id)

    job2 = orchestrator.create_job(job_type="media_analysis", priority=150)
    orchestrator.start_job(job2.id)

    with sqlite_session(temp_db) as conn:
        conn.execute(
            "UPDATE jobs SET progress_pct = 100.0, current_stage = 'completed', updated_at = '2026-11-15T00:00:00+00:00' WHERE id = ?",
            (job2.id,),
        )

    stalled = orchestrator.check_stalled_jobs(timeout_seconds=30.0)
    assert job1.id not in stalled
    assert job2.id not in stalled


# Scenario 8: Duplicate analysis run idempotency
def test_create_analysis_run_idempotency(temp_db, mock_settings, tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"dummy_video_bytes")

    with sqlite_session(temp_db) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, storage_subdir, created_at, updated_at)
            VALUES ('proj1', 'Test Project', 'proj1', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, file_size_bytes, duration_seconds, media_type, created_at, updated_at)
            VALUES ('med1', 'proj1', 'sample.mp4', ?, 1000, 60.0, 'video', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """,
            (str(video_path),),
        )

    pipeline = VideoAnalysisPipeline(mock_settings, temp_db)
    run_id1 = pipeline.create_analysis_run("med1", "proj1")
    assert run_id1.startswith("run_")

    # Second request while run1 is pending/queued reuses the same run_id
    run_id2 = pipeline.create_analysis_run("med1", "proj1")
    assert run_id1 == run_id2


# Scenario 9: Duplicate export job idempotency
def test_submit_export_job_idempotency(temp_db, mock_settings):
    with sqlite_session(temp_db) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, storage_subdir, created_at, updated_at)
            VALUES ('proj1', 'Test Project', 'proj1', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, file_size_bytes, duration_seconds, media_type, created_at, updated_at)
            VALUES ('med1', 'proj1', 'sample.mp4', '/path/to/sample.mp4', 1000, 60.0, 'video', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, job_id, profile, status, current_stage, created_at, updated_at)
            VALUES ('run_exp1', 'proj1', 'med1', NULL, 'balanced', 'completed', 'completed', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (id, project_id, media_asset_id, analysis_run_id, generation_run_id, start_time, end_time, duration, suggested_start_time, suggested_end_time, suggested_title, title, created_at, updated_at)
            VALUES ('cand1', 'proj1', 'med1', 'run_exp1', 'gen1', 10.0, 30.0, 20.0, 10.0, 30.0, 'Great Clip', 'Great Clip', '2026-11-15T00:00:00+00:00', '2026-11-15T00:00:00+00:00')
            """
        )

    export_service = ExportService(mock_settings, temp_db)
    req = RenderExportRequest(candidate_id="cand1", preset_id="shorts_reels_9_16")

    res1 = export_service.submit_export_job("proj1", req)
    assert res1["export_id"].startswith("exp_")
    assert res1["status"] == "queued"

    # Second export submission reuses the existing active export
    res2 = export_service.submit_export_job("proj1", req)
    assert res1["export_id"] == res2["export_id"]
    assert res1["job_id"] == res2["job_id"]


# Scenario 10: Exception propagation and clean failure recording
def test_exception_propagation_and_failure_recording(temp_db, mock_settings):
    orchestrator = JobOrchestrator(mock_settings, temp_db)
    job = orchestrator.create_job(job_type="media_analysis", priority=150)
    orchestrator.start_job(job.id, stage="transcribing_speech")

    try:
        raise ValueError("Simulated unexpected decode failure in audio demuxer")
    except Exception as exc:
        orchestrator.fail_job(job.id, error_message=f"{type(exc).__name__}: {str(exc)}")

    rec = orchestrator.get_job(job.id)
    assert rec.status == "failed"
    assert "ValueError: Simulated unexpected decode failure" in (rec.error_message or "")
    assert rec.completed_at is not None
