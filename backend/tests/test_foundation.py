"""Milestone 1 Foundation Tests: Security Boundaries, Migrations, Error Envelopes & Health API."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import (
    AppError,
    BoundaryViolationError,
    MigrationError,
    RootDeletionForbiddenError,
    UnsafeStorageRootError,
)
from app.core.security import (
    resolve_contained_path,
    safe_delete_directory,
    validate_storage_root_path,
)
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app


def test_storage_root_rejects_drive_root_and_os_dirs(tmp_path: Path):
    """Drive roots, home directory, and OS protected directories must be rejected."""
    with pytest.raises(UnsafeStorageRootError):
        validate_storage_root_path(Path("D:\\"))

    with pytest.raises(UnsafeStorageRootError):
        validate_storage_root_path(Path("C:\\Windows\\System32"))

    with pytest.raises(UnsafeStorageRootError):
        validate_storage_root_path(Path.home())

    valid = validate_storage_root_path(tmp_path / "zezedit_storage")
    assert valid == (tmp_path / "zezedit_storage").resolve()


def test_path_confinement_blocks_traversal(tmp_path: Path):
    """resolve_contained_path prevents escaping the permitted container directory."""
    container = tmp_path / "media"
    container.mkdir()

    safe_child = resolve_contained_path(container, "clips/sample.mp4")
    assert safe_child == (container / "clips" / "sample.mp4").resolve()

    with pytest.raises(BoundaryViolationError):
        resolve_contained_path(container, "../secrets.txt")

    with pytest.raises(BoundaryViolationError):
        resolve_contained_path(container, str(tmp_path / "outside.mp4"))

    with pytest.raises(BoundaryViolationError):
        resolve_contained_path(container, ".")


def test_safe_delete_forbids_storage_root_and_buckets(tmp_path: Path):
    """Recursive deletion of storage root or top-level buckets must be blocked."""
    layout = StorageLayout.from_root(tmp_path / "storage")
    layout.ensure_directories()

    with pytest.raises(BoundaryViolationError):
        safe_delete_directory(layout.root, layout.root, layout.root)

    with pytest.raises(RootDeletionForbiddenError):
        safe_delete_directory(layout.media, layout.root, layout.root)

    with pytest.raises(RootDeletionForbiddenError):
        safe_delete_directory(layout.temp, layout.root, layout.root)

    # Scoped job temp cleanup inside storage/temp IS permitted
    job_temp = layout.temp / "jobs" / "job_123"
    job_temp.mkdir(parents=True)
    (job_temp / "scratch.tmp").write_text("temp", encoding="utf-8")

    safe_delete_directory(job_temp, layout.temp, layout.root)
    assert not job_temp.exists()
    assert layout.temp.exists()


def test_sqlite_migrations_idempotency_backup_and_checksum(tmp_path: Path):
    """Forward-only migrations create schema, remain idempotent, snapshot upgrades, and catch edits."""
    layout = StorageLayout.from_root(tmp_path / "storage")
    layout.ensure_directories()

    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    mig_1 = migrations_dir / "0001_initial_schema.sql"
    mig_1.write_text(
        """
        CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE jobs (id TEXT PRIMARY KEY, status TEXT NOT NULL);
        """,
        encoding="utf-8",
    )

    first = run_migrations(layout.db_file, migrations_dir, layout.backups)
    assert first.newly_applied == ["0001"]
    assert first.current_version == "0001"

    # Re-running is idempotent
    second = run_migrations(layout.db_file, migrations_dir, layout.backups)
    assert second.newly_applied == []
    assert second.applied_versions == ["0001"]

    # Adding a second migration creates a backup before applying
    mig_2 = migrations_dir / "0002_add_notes.sql"
    mig_2.write_text("ALTER TABLE projects ADD COLUMN notes TEXT;", encoding="utf-8")
    third = run_migrations(layout.db_file, migrations_dir, layout.backups)
    assert third.newly_applied == ["0002"]
    assert list(layout.backups.glob("pre_migration_0002_*.db"))

    # Tampering with an already-applied migration raises MigrationError
    mig_1.write_text("CREATE TABLE tampered (id TEXT);", encoding="utf-8")
    with pytest.raises(MigrationError):
        run_migrations(layout.db_file, migrations_dir, layout.backups)

    # Verify WAL pragma active
    with sqlite_session(layout.db_file) as conn:
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert str(mode).lower() == "wal"


def test_health_and_system_info_endpoints(tmp_path: Path):
    """FastAPI lifespan initializes storage & DB cleanly and responds on /api/v1/health."""
    settings = Settings(
        storage_root=tmp_path / "storage",
        ollama_base_url="http://127.0.0.1:19999",  # intentionally closed port for fast deterministic test
        ollama_timeout_seconds=0.3,
    )
    app = create_app(settings_override=settings)

    # Add temporary route inside test app to verify centralized AppError envelope
    @app.get("/api/v1/_test_error")
    def _raise_err():
        raise AppError(code="SAMPLE_ERROR", message="Simulated domain failure", status_code=409)

    with TestClient(app) as client:
        health_res = client.get("/api/v1/health")
        assert health_res.status_code == 200
        assert "X-Request-ID" in health_res.headers

        data = health_res.json()
        assert data["database"]["connected"] is True
        assert data["database"]["journal_mode"].lower() == "wal"
        assert "0001" in data["database"]["applied_migrations"]
        assert data["storage"]["writable"] is True
        assert data["storage"]["buckets_ready"] is True
        assert data["ollama"]["reachable"] is False

        info_res = client.get("/api/v1/system/info")
        assert info_res.status_code == 200
        info = info_res.json()
        assert info["execution_mode"] == "cpu_first"
        assert info["cpu_count"] >= 1

        err_res = client.get("/api/v1/_test_error")
        assert err_res.status_code == 409
        err_json = err_res.json()
        assert err_json["error"]["code"] == "SAMPLE_ERROR"
        assert err_json["error"]["request_id"].startswith("req_")
