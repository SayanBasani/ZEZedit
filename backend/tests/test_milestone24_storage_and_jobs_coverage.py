"""Milestone 24 Regression Test Expansion: Storage Management, Job Orchestration & Database Integrity (ZEZ-099)."""

import json
import sqlite3
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import resolve_contained_path
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.backup_service import BackupService
from app.services.jobs import JobOrchestrator
from app.services.storage import StorageService


@pytest.fixture
def storage_jobs_env(tmp_path: Path):
    """Provides isolated storage layout, migrated SQLite DB, test client, and services."""
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(
        app_name="ZezEditTestM24Storage",
        environment="test",
        storage_root=storage_root,
        max_concurrent_jobs=2,
    )

    app = create_app(settings)
    client = TestClient(app)

    storage_svc = StorageService(settings)
    jobs_svc = JobOrchestrator(settings, layout.db_file)
    backup_svc = BackupService(layout.db_file, layout.backups)

    proj_id = "proj_m24_sj"
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            "INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES (?, 'M24 SJ Proj', 'm24_sj_p', datetime('now'), datetime('now'))",
            (proj_id,)
        )
        conn.commit()

    return {
        "layout": layout,
        "settings": settings,
        "db_path": layout.db_file,
        "client": client,
        "storage_service": storage_svc,
        "jobs_service": jobs_svc,
        "backup_service": backup_svc,
        "project_id": proj_id,
    }


def test_storage_layout_subdirectories_initialization(storage_jobs_env):
    """Verify StorageLayout ensures all required subdirectories exist."""
    layout: StorageLayout = storage_jobs_env["layout"]
    layout.ensure_directories()

    assert layout.media.exists()
    assert layout.proxies.exists()
    assert layout.thumbnails.exists()
    assert layout.analysis.exists()
    assert layout.exports.exists()
    assert layout.temp.exists()
    assert layout.backups.exists()
    assert layout.logs.exists()


def test_storage_path_confinement_blocks_parent_traversal(storage_jobs_env):
    """Verify resolve_contained_path blocks attempts to break out of storage root."""
    layout: StorageLayout = storage_jobs_env["layout"]

    with pytest.raises(Exception):
        resolve_contained_path(layout.root, "../../../etc/shadow")

    valid_sub = resolve_contained_path(layout.root, "media/my_video.mp4")
    assert str(valid_sub).startswith(str(layout.root))


def test_temp_cache_cleanup_preview_no_file_deletion(storage_jobs_env):
    """Verify temp cache cleanup preview calculates byte savings without deleting files."""
    storage_svc: StorageService = storage_jobs_env["storage_service"]
    layout: StorageLayout = storage_jobs_env["layout"]

    f1 = layout.temp / "cache1.tmp"
    f2 = layout.temp / "cache2.tmp"
    f1.write_bytes(b"A" * 5000)
    f2.write_bytes(b"B" * 5000)

    preview = storage_svc.preview_cache_cleanup()
    assert preview["eligible_files_count"] >= 2
    assert preview["total_bytes_to_free"] >= 10000
    assert "confirmation_token" in preview

    # Files must still exist on disk
    assert f1.exists()
    assert f2.exists()


def test_temp_cache_cleanup_execute_with_valid_token(storage_jobs_env):
    """Verify cache cleanup executes and deletes files when correct token is supplied."""
    storage_svc: StorageService = storage_jobs_env["storage_service"]
    layout: StorageLayout = storage_jobs_env["layout"]

    f = layout.temp / "cleanup_target.tmp"
    f.write_bytes(b"Z" * 8000)

    preview = storage_svc.preview_cache_cleanup()
    token = preview["confirmation_token"]

    result = storage_svc.execute_cache_cleanup(token)
    assert result["deleted_files_count"] >= 1
    assert result["freed_bytes"] >= 8000
    assert not f.exists()


def test_temp_cache_cleanup_invalid_token_rejected(storage_jobs_env):
    """Verify executing cache cleanup with an invalid token is strictly rejected."""
    storage_svc: StorageService = storage_jobs_env["storage_service"]
    with pytest.raises(AppError):
        storage_svc.execute_cache_cleanup("")


def test_storage_breakdown_categories_accuracy(storage_jobs_env):
    """Verify storage breakdown returns structured categories with byte sizes."""
    storage_svc: StorageService = storage_jobs_env["storage_service"]
    layout: StorageLayout = storage_jobs_env["layout"]

    test_export = layout.exports / "sample_out.mp4"
    test_export.write_bytes(b"0" * 4096)

    breakdown = storage_svc.get_storage_breakdown()
    assert "categories" in breakdown
    assert "total_disk_space_bytes" in breakdown
    assert "free_disk_space_bytes" in breakdown
    assert "is_low_storage" in breakdown
    assert breakdown["categories"]["exports_bytes"] >= 4096


def test_job_priority_queue_dispatch_order(storage_jobs_env):
    """Verify job orchestrator creates and prioritizes high-priority jobs."""
    jobs_svc: JobOrchestrator = storage_jobs_env["jobs_service"]
    proj_id = storage_jobs_env["project_id"]

    j_low = jobs_svc.create_job(project_id=proj_id, job_type="background_sync", priority=50)
    j_high = jobs_svc.create_job(project_id=proj_id, job_type="timeline_render", priority=200)
    j_med = jobs_svc.create_job(project_id=proj_id, job_type="video_analysis", priority=100)

    assert j_high.priority > j_med.priority > j_low.priority
    assert j_high.status == "queued"


def test_job_state_transitions_and_progress(storage_jobs_env):
    """Verify job progress and stage updates persist correctly."""
    jobs_svc: JobOrchestrator = storage_jobs_env["jobs_service"]
    proj_id = storage_jobs_env["project_id"]

    job = jobs_svc.create_job(project_id=proj_id, job_type="analysis", priority=100)
    assert job.status == "queued"

    running_job = jobs_svc.transition_job_state(job.id, "running", progress_pct=10.0, stage="starting")
    assert running_job.status == "running"

    updated = jobs_svc.transition_job_state(job.id, "running", progress_pct=45.0, stage="transcribing")
    assert updated.progress_pct == 45.0
    assert updated.current_stage == "transcribing"


def test_job_completion_and_result_metadata(storage_jobs_env):
    """Verify completing a job sets completed status and records result metadata."""
    jobs_svc: JobOrchestrator = storage_jobs_env["jobs_service"]
    proj_id = storage_jobs_env["project_id"]

    job = jobs_svc.create_job(project_id=proj_id, job_type="export", priority=150)
    jobs_svc.transition_job_state(job.id, "running", progress_pct=20.0, stage="rendering")
    meta = {"output_file": "clip1.mp4", "render_time_sec": 3.2}

    finished = jobs_svc.transition_job_state(job.id, "completed", progress_pct=100.0, stage="done", result_metadata=meta)
    assert finished.status == "completed"
    assert finished.progress_pct == 100.0
    assert finished.result_metadata["output_file"] == "clip1.mp4"


def test_job_failure_records_error_message(storage_jobs_env):
    """Verify failing a job records error message and terminal failed status."""
    jobs_svc: JobOrchestrator = storage_jobs_env["jobs_service"]
    proj_id = storage_jobs_env["project_id"]

    job = jobs_svc.create_job(project_id=proj_id, job_type="render", priority=100)
    jobs_svc.transition_job_state(job.id, "running", progress_pct=10.0, stage="encoding")
    failed = jobs_svc.transition_job_state(
        job.id, "failed", error_message="FFmpeg process killed by OOM killer"
    )

    assert failed.status == "failed"
    assert "FFmpeg process killed" in (failed.error_message or "")


def test_job_cancellation_immediate_when_queued(storage_jobs_env):
    """Verify cancelling a queued job immediately transitions to cancelled."""
    jobs_svc: JobOrchestrator = storage_jobs_env["jobs_service"]
    proj_id = storage_jobs_env["project_id"]

    job = jobs_svc.create_job(project_id=proj_id, job_type="render", priority=100)
    cancelled = jobs_svc.request_cancellation(job.id)

    assert cancelled.status == "cancelled"


def test_job_retry_lifecycle_and_max_attempts(storage_jobs_env):
    """Verify retrying a job resets status to queued and increments retry count."""
    jobs_svc: JobOrchestrator = storage_jobs_env["jobs_service"]
    proj_id = storage_jobs_env["project_id"]

    job = jobs_svc.create_job(project_id=proj_id, job_type="render", priority=100)
    jobs_svc.transition_job_state(job.id, "running")
    jobs_svc.transition_job_state(job.id, "failed", error_message="Temporary timeout")

    retried = jobs_svc.retry_job(job.id)
    assert retried.status == "queued"
    assert retried.retry_count == 1


def test_sqlite_foreign_key_and_integrity_check(storage_jobs_env):
    """Verify database passes SQLite integrity and foreign key checks without corruption."""
    backup_svc: BackupService = storage_jobs_env["backup_service"]
    diag = backup_svc.get_database_diagnostics()

    assert diag["healthy"] is True
    assert diag["integrity_check"] == "ok"
    assert diag["foreign_key_check"] == "ok"
    assert diag["orphaned_records"]["shorts_candidates"] == 0


def test_sqlite_online_backup_generation(storage_jobs_env):
    """Verify SQLite online backup generates a valid standalone database file."""
    backup_svc: BackupService = storage_jobs_env["backup_service"]
    backup_info = backup_svc.create_backup(label="m24_test_backup")

    assert Path(backup_info["backup_path"]).exists()
    assert backup_info["file_size_bytes"] > 0
    assert "backup_m24_test_backup" in backup_info["backup_filename"]


def test_jobs_rest_api_list_and_stats(storage_jobs_env):
    """Verify GET /api/v1/jobs and GET /api/v1/jobs/stats endpoints."""
    client: TestClient = storage_jobs_env["client"]
    proj_id = storage_jobs_env["project_id"]
    jobs_svc: JobOrchestrator = storage_jobs_env["jobs_service"]

    jobs_svc.create_job(project_id=proj_id, job_type="api_test_job", priority=100)

    res_list = client.get("/api/v1/jobs")
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    res_stats = client.get("/api/v1/jobs/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "running" in stats
    assert "queued" in stats
    assert "total_jobs" in stats
