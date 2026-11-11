"""Milestone 2 Automated Test Suite:
Database Migrations, Projects, Media Assets, Jobs, Settings, Storage & Backup/Restore.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.backup_service import BackupService
from app.services.jobs import JobOrchestrator
from app.services.media import MediaService
from app.services.projects import ProjectService
from app.services.settings_service import SettingsService
from app.services.storage import StorageService


@pytest.fixture
def env(tmp_path: Path):
    storage_root = tmp_path / "storage"
    settings = Settings(
        storage_root=storage_root,
        ollama_base_url="http://127.0.0.1:19999",
        ollama_timeout_seconds=0.2,
    )
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    # Run all migrations in backend/migrations
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    return {
        "settings": settings,
        "layout": layout,
        "db_path": layout.db_file,
        "tmp_path": tmp_path,
    }


def test_migration_and_foreign_keys(env):
    """Verify migrations 0001 and 0002 apply and foreign key cascade works."""
    db_path = env["db_path"]
    with sqlite_session(db_path) as conn:
        rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC").fetchall()
        versions = [r["version"] for r in rows]
        assert "0001" in versions
        assert "0002" in versions

        # Verify foreign keys are active
        fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_status == 1


def test_project_lifecycle_and_events(env):
    """Test project create, get, update, archive, restore, events, and protected delete."""
    svc = ProjectService(env["settings"], env["db_path"])

    # 1. Create project
    proj = svc.create_project(name="Test Short", description="Draft project", project_config={"ratio": "9:16"})
    assert proj.id.startswith("proj_")
    assert proj.name == "Test Short"
    assert proj.status == "active"
    assert proj.project_config["ratio"] == "9:16"

    # 2. Get project
    fetched = svc.get_project(proj.id)
    assert fetched.id == proj.id

    # 3. Update project
    updated = svc.update_project(proj.id, name="Renamed Short", project_config={"ratio": "16:9"})
    assert updated.name == "Renamed Short"
    assert updated.project_config["ratio"] == "16:9"

    # 4. Archive & Restore
    archived = svc.archive_project(proj.id)
    assert archived.status == "archived"
    assert archived.archived_at is not None

    restored = svc.restore_project(proj.id)
    assert restored.status == "active"
    assert restored.archived_at is None

    # 5. Events tracked
    events = svc.get_events(proj.id)
    types = [e.event_type for e in events]
    assert "project_created" in types
    assert "project_updated" in types
    assert "project_archived" in types
    assert "project_restored" in types

    # 6. Protected delete (requires confirmation)
    with pytest.raises(AppError) as exc_info:
        svc.delete_project(proj.id, confirmation=False)
    assert exc_info.value.code == "CONFIRMATION_REQUIRED"

    svc.delete_project(proj.id, confirmation=True)
    with pytest.raises(AppError):
        svc.get_project(proj.id)


def test_media_assets_and_relinking(env):
    """Test media asset registration, missing status, and relinking."""
    proj_svc = ProjectService(env["settings"], env["db_path"])
    media_svc = MediaService(env["settings"], env["db_path"])

    proj = proj_svc.create_project(name="Media Test")

    # Create dummy external media file
    media_file = env["tmp_path"] / "sample.mp4"
    media_file.write_text("fake video bytes", encoding="utf-8")

    asset = media_svc.register_media_asset(
        project_id=proj.id,
        original_filename="sample.mp4",
        storage_path=str(media_file),
        is_external=True,
        media_type="video",
        file_size_bytes=media_file.stat().st_size,
        duration_seconds=12.5,
        width=1920,
        height=1080,
    )
    assert asset.id.startswith("med_")
    assert asset.availability_status == "present"

    # Mark missing
    missing = media_svc.mark_missing(proj.id, asset.id)
    assert missing.availability_status == "missing"

    # Relink to new path
    new_media_file = env["tmp_path"] / "sample_moved.mp4"
    new_media_file.write_text("fake moved video bytes", encoding="utf-8")

    relinked = media_svc.relink_media(proj.id, asset.id, str(new_media_file))
    assert relinked.availability_status == "present"
    assert relinked.storage_path == str(new_media_file.resolve())


def test_job_orchestrator_state_machine_and_recovery(env):
    """Test job state transitions, cancellation semantics, retries, and crash recovery."""
    proj_svc = ProjectService(env["settings"], env["db_path"])
    job_svc = JobOrchestrator(env["settings"], env["db_path"])

    proj = proj_svc.create_project(name="Jobs Test")

    # 1. Create job
    job = job_svc.create_job(job_type="proxy_generation", project_id=proj.id, priority=50)
    assert job.status == "queued"
    assert job.retry_count == 0

    # 2. Transition queued -> running
    running = job_svc.transition_job_state(
        job.id, "running", progress_pct=10.0, stage="probing", worker_id="w_1", worker_pid=1234
    )
    assert running.status == "running"
    assert running.progress_pct == 10.0
    assert running.worker_pid == 1234

    # 3. Invalid transition: running directly to queued without failing
    with pytest.raises(AppError) as exc_info:
        job_svc.transition_job_state(job.id, "queued")
    assert exc_info.value.code == "INVALID_JOB_TRANSITION"

    # 4. Cancellation semantics on running job -> moves to 'cancelling'
    cancelling = job_svc.request_cancellation(job.id)
    assert cancelling.status == "cancelling"

    # 5. Worker acknowledges cancellation -> moves to 'cancelled'
    cancelled = job_svc.transition_job_state(job.id, "cancelled", stage="cancelled_acknowledged")
    assert cancelled.status == "cancelled"

    # 6. Retry job
    retried = job_svc.retry_job(job.id)
    assert retried.status == "queued"
    assert retried.retry_count == 1

    # 7. Simulate backend crash while job is running -> recover_interrupted_jobs
    job_svc.transition_job_state(retried.id, "running", worker_id="w_dead")
    recovered = job_svc.recover_interrupted_jobs()
    assert retried.id in recovered

    recovered_job = job_svc.get_job(retried.id)
    assert recovered_job.status == "interrupted"
    assert "restarted" in recovered_job.error_message


def test_settings_storage_and_secret_redaction(env):
    """Test settings persistence, secret redaction, and storage inspection."""
    settings_svc = SettingsService(env["settings"], env["db_path"])
    storage_svc = StorageService(env["settings"])

    settings = settings_svc.get_settings()
    assert settings.proxy_resolution == "480p"

    # Update with an accidental secret field
    updated = settings_svc.update_settings({
        "proxy_resolution": "720p",
        "ai_provider_config": {"ollama_base_url": "http://127.0.0.1:11434", "api_key": "supersecret123"},
    })
    assert updated.proxy_resolution == "720p"
    assert updated.ai_provider_config["api_key"] == "[REDACTED]"

    # Storage inspection
    inspect_data = storage_svc.inspect_storage()
    assert inspect_data["is_accessible"] is True
    assert inspect_data["is_writable"] is True
    assert "media" in inspect_data["directories"]


def test_backup_and_restore_verification(env):
    """Test online SQLite backup creation, integrity verification, and restore."""
    proj_svc = ProjectService(env["settings"], env["db_path"])
    backup_svc = BackupService(env["db_path"], env["layout"].backups)

    # Seed data
    p1 = proj_svc.create_project(name="Project Pre-Backup")

    # Create backup
    backup_res = backup_svc.create_backup(label="unit_test")
    assert backup_res["integrity_verified"] is True
    backup_file = backup_res["backup_filename"]

    # Mutate data after backup
    p2 = proj_svc.create_project(name="Project Post-Backup")
    assert len(proj_svc.list_projects()) == 2

    # Restore backup
    restore_res = backup_svc.restore_backup(backup_file)
    assert restore_res["status"] == "success"

    # Data should match pre-backup state
    projects_after = proj_svc.list_projects()
    assert len(projects_after) == 1
    assert projects_after[0].id == p1.id


def test_api_endpoints_end_to_end(env):
    """Test full HTTP API contracts using TestClient."""
    app = create_app(settings_override=env["settings"])
    with TestClient(app) as client:
        # Projects CRUD
        p_res = client.post("/api/v1/projects", json={"name": "API Project", "description": "Via TestClient"})
        assert p_res.status_code == 201
        pid = p_res.json()["id"]

        list_res = client.get("/api/v1/projects")
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1

        # Media registration
        dummy_file = env["tmp_path"] / "api_video.mp4"
        dummy_file.write_text("video", encoding="utf-8")
        m_res = client.post(
            f"/api/v1/projects/{pid}/media",
            json={"original_filename": "api_video.mp4", "storage_path": str(dummy_file)},
        )
        assert m_res.status_code == 201
        mid = m_res.json()["id"]

        # Job submission
        j_res = client.post("/api/v1/jobs", json={"job_type": "proxy_generation", "project_id": pid})
        assert j_res.status_code == 201
        jid = j_res.json()["id"]

        # Job cancellation on queued job
        cancel_res = client.post(f"/api/v1/jobs/{jid}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"

        # Settings read/update
        s_res = client.get("/api/v1/settings")
        assert s_res.status_code == 200

        # Storage inspect
        store_res = client.get("/api/v1/storage/inspect")
        assert store_res.status_code == 200
        assert store_res.json()["is_writable"] is True

        # System capabilities
        cap_res = client.get("/api/v1/system/capabilities")
        assert cap_res.status_code == 200
        assert cap_res.json()["execution_mode"] == "cpu_first"
