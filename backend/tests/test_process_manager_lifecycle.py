"""Comprehensive tests for Central Process Manager lifecycle, API parity, and restart recovery."""

import gc
import pytest
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.jobs import JobOrchestrator


def _setup_test_env(tmp_path: Path) -> tuple[Settings, StorageLayout, JobOrchestrator]:
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(
        app_name="ZezEditTestProcessManager",
        environment="test",
        storage_root=storage_root,
        max_concurrent_jobs=2,
    )
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute("INSERT OR IGNORE INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('default', 'Default Project', 'default_p', datetime('now'), datetime('now'));")

    orchestrator = JobOrchestrator(settings, layout.db_file)
    return settings, layout, orchestrator


def test_job_creation_with_media_asset_and_parent(tmp_path: Path):
    settings, layout, orchestrator = _setup_test_env(tmp_path)

    job = orchestrator.create_job(
        job_type="analyze_video",
        project_id="default",
        input_config={"param": "value"},
        media_asset_id="asset_123",
        parent_job_id="job_parent_001",
    )

    assert job.id.startswith("job_")
    assert job.job_type == "analyze_video"
    assert job.media_asset_id == "asset_123"
    assert job.parent_job_id == "job_parent_001"
    assert job.status == "queued"

    fetched = orchestrator.get_job(job.id)
    assert fetched.id == job.id
    assert fetched.media_asset_id == "asset_123"
    assert fetched.parent_job_id == "job_parent_001"
    gc.collect()


def test_list_jobs_filtering_and_video_title(tmp_path: Path):
    settings, layout, orchestrator = _setup_test_env(tmp_path)

    # Seed media asset
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, created_at, updated_at)
            VALUES ('vid_alpha', 'default', 'Interview_Take1.mp4', 'Interview_Take1.mp4', '2026-01-01', '2026-01-01');
            """
        )

    job1 = orchestrator.create_job(
        job_type="whisper_transcription",
        project_id="default",
        input_config={},
        media_asset_id="vid_alpha",
    )
    job2 = orchestrator.create_job(
        job_type="storage_cleanup",
        project_id="default",
        input_config={},
    )

    # List all
    all_jobs = orchestrator.list_jobs()
    assert len(all_jobs) >= 2

    # Filter by media_asset_id
    filtered_vid = orchestrator.list_jobs(media_asset_id="vid_alpha")
    assert len(filtered_vid) == 1
    assert filtered_vid[0].id == job1.id
    assert filtered_vid[0].video_title == "Interview_Take1.mp4"

    # Filter by job_type
    filtered_type = orchestrator.list_jobs(job_type="storage_cleanup")
    assert len(filtered_type) == 1
    assert filtered_type[0].id == job2.id

    # Search filter
    searched = orchestrator.list_jobs(search="Interview")
    assert len(searched) == 1
    assert searched[0].id == job1.id
    gc.collect()


def test_job_cancellation_lifecycle(tmp_path: Path):
    settings, layout, orchestrator = _setup_test_env(tmp_path)

    job = orchestrator.create_job(
        job_type="frame_extraction",
        project_id="default",
        input_config={},
        media_asset_id="vid_sample",
    )

    # Simulate job running
    orchestrator.transition_job_state(job.id, "running", worker_id="worker_test", worker_pid=12345, stage="extracting_frames")
    running_job = orchestrator.get_job(job.id)
    assert running_job.status == "running"

    # Cancel
    cancelled = orchestrator.request_cancellation(job.id)
    assert cancelled.status == "cancelled"
    assert cancelled.current_stage == "cancelled_by_user"
    assert cancelled.cancelled_at is not None
    gc.collect()


def test_retry_job_creates_linked_new_attempt(tmp_path: Path):
    settings, layout, orchestrator = _setup_test_env(tmp_path)

    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, created_at, updated_at)
            VALUES ('vid_99', 'default', 'clip_99.mp4', 'clip_99.mp4', '2026-01-01', '2026-01-01');
            """
        )

    job = orchestrator.create_job(
        job_type="export_mp4",
        project_id="default",
        input_config={"clip_id": "clip_42"},
        media_asset_id="vid_99",
    )
    orchestrator.transition_job_state(job.id, "running")
    orchestrator.transition_job_state(job.id, "failed", error_message="FFmpeg exit 1 error")

    # Retry with new attempt
    new_job = orchestrator.retry_job(job.id, create_new_attempt=True)
    assert new_job.id != job.id
    assert new_job.parent_job_id == job.id
    assert new_job.media_asset_id == "vid_99"
    assert new_job.status == "queued"
    assert new_job.retry_count == 1
    assert new_job.input_config.get("clip_id") == "clip_42"

    # Verify previous job preserved
    original = orchestrator.get_job(job.id)
    assert original.status == "failed"
    gc.collect()


def test_delete_single_job_record(tmp_path: Path):
    settings, layout, orchestrator = _setup_test_env(tmp_path)

    job = orchestrator.create_job(job_type="test_run", project_id="default", input_config={})
    orchestrator.transition_job_state(job.id, "running", worker_id="worker_1", worker_pid=9999)

    # Cannot delete running job
    with pytest.raises(AppError) as exc_info:
        orchestrator.delete_job(job.id)
    assert exc_info.value.code == "JOB_RUNNING"

    # Complete and then delete
    orchestrator.transition_job_state(job.id, "completed", result_metadata={"status": "ok"})
    deleted = orchestrator.delete_job(job.id)
    assert deleted is True

    with pytest.raises(AppError):
        orchestrator.get_job(job.id)
    gc.collect()


def test_delete_job_history(tmp_path: Path):
    settings, layout, orchestrator = _setup_test_env(tmp_path)

    j1 = orchestrator.create_job("type_a", "default", input_config={})
    j2 = orchestrator.create_job("type_b", "default", input_config={})
    j3 = orchestrator.create_job("type_c", "default", input_config={})

    orchestrator.transition_job_state(j1.id, "running")
    orchestrator.transition_job_state(j1.id, "completed")

    orchestrator.transition_job_state(j2.id, "running")
    orchestrator.transition_job_state(j2.id, "failed", error_message="err")

    orchestrator.transition_job_state(j3.id, "running")

    # Delete completed history
    count = orchestrator.delete_job_history(status="completed")
    assert count == 1

    remaining = orchestrator.list_jobs()
    rem_ids = {j.id for j in remaining}
    assert j1.id not in rem_ids
    assert j2.id in rem_ids
    assert j3.id in rem_ids
    gc.collect()


def test_restart_recovery_marks_running_jobs_interrupted(tmp_path: Path):
    settings, layout, orchestrator = _setup_test_env(tmp_path)

    # Create job and manually leave in running status
    job = orchestrator.create_job("scene_detection", "default", input_config={})
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            """
            UPDATE jobs SET status = 'running', worker_pid = 999999, updated_at = '2026-01-01T00:00:00Z'
            WHERE id = ?;
            """,
            (job.id,),
        )

    # Simulate restart recovery
    recovered = orchestrator.recover_interrupted_jobs()
    assert len(recovered) == 1
    assert job.id in recovered

    reloaded = orchestrator.get_job(job.id)
    assert reloaded.status == "interrupted"
    gc.collect()


def test_api_parity_processes_and_jobs_routes(tmp_path: Path):
    settings, layout, orchestrator = _setup_test_env(tmp_path)
    app = create_app(settings)
    client = TestClient(app)

    # Fetch from /api/v1/jobs
    res_jobs = client.get("/api/v1/jobs")
    assert res_jobs.status_code == 200

    # Fetch from /api/v1/processes
    res_proc = client.get("/api/v1/processes")
    assert res_proc.status_code == 200

    # Parity check
    data_jobs = res_jobs.json()
    data_proc = res_proc.json()
    assert "items" in data_jobs
    assert "items" in data_proc
    assert len(data_jobs["items"]) == len(data_proc["items"])
    gc.collect()
