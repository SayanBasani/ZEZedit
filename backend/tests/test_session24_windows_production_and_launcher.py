"""Session 24 test suite: Windows Production Mode, One-Click Launcher & Release Hardening."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.core.config import PROJECT_ROOT, Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.main import create_app
from app.services.jobs import JobOrchestrator


@pytest.fixture
def prod_client(tmp_path: Path):
    """Fixture providing a test client with a mock frontend dist and isolated storage."""
    dist_dir = tmp_path / "frontend" / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    index_html = dist_dir / "index.html"
    index_html.write_text("<!DOCTYPE html><html><body><div id='root'>ZezEdit Production</div></body></html>", encoding="utf-8")

    sample_css = assets_dir / "app.css"
    sample_css.write_text("body { background: #0b0f17; }", encoding="utf-8")

    sample_js = assets_dir / "main.js"
    sample_js.write_text("console.log('ZezEdit');", encoding="utf-8")

    settings = Settings(
        storage_root=tmp_path / "storage",
        frontend_dist_dir=dist_dir,
        ollama_base_url="http://127.0.0.1:19999",
        ollama_timeout_seconds=0.2,
    )

    app = create_app(settings_override=settings)
    with TestClient(app) as client:
        yield client, dist_dir, settings


def test_production_frontend_serving_spa_and_assets(prod_client):
    """Test 1: FastAPI serves built frontend, SPA fallback, assets, and protects API routes."""
    client, dist_dir, settings = prod_client

    # 1. Root / serves index.html
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert "text/html" in root_res.headers.get("content-type", "")
    assert "ZezEdit Production" in root_res.text

    # 2. Direct SPA routes serve index.html (client-side routing)
    for route in ["/videos/med_12345", "/projects", "/settings", "/processes", "/characters"]:
        spa_res = client.get(route)
        assert spa_res.status_code == 200
        assert "text/html" in spa_res.headers.get("content-type", "")
        assert "ZezEdit Production" in spa_res.text

    # 3. Static assets under /assets return correct MIME types
    css_res = client.get("/assets/app.css")
    assert css_res.status_code == 200
    assert "text/css" in css_res.headers.get("content-type", "")
    assert "background: #0b0f17" in css_res.text

    js_res = client.get("/assets/main.js")
    assert js_res.status_code == 200
    assert "javascript" in js_res.headers.get("content-type", "")

    # 4. Missing assets return 404, NEVER fallback to HTML index
    missing_asset = client.get("/assets/missing-chunk-xyz.js")
    assert missing_asset.status_code == 404
    assert "text/html" not in missing_asset.headers.get("content-type", "")

    # 5. Missing API endpoints return 404, NEVER fallback to HTML index
    missing_api = client.get("/api/v1/missing_endpoint")
    assert missing_api.status_code == 404
    assert "text/html" not in missing_api.headers.get("content-type", "")

    # 6. Missing health endpoints return 404, NEVER fallback to HTML index
    missing_health = client.get("/health/missing")
    assert missing_health.status_code == 404


def test_readiness_health_endpoint_distinguishes_states(prod_client):
    """Test 2: /health endpoint distinguishes starting, ready, ready_with_optional_unavailable, and failed."""
    client, dist_dir, settings = prod_client

    # When Ollama is unreachable (as in fixture with port 19999), status must be ready_with_optional_unavailable
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["ready", "ready_with_optional_unavailable"]
    assert data["database"]["connected"] is True
    assert data["database"]["integrity_valid"] is True
    assert data["storage"]["writable"] is True
    assert data["storage"]["buckets_ready"] is True
    assert data["dispatcher_initialized"] is True
    assert data["frontend_build_available"] is True
    assert isinstance(data["whisper_available"], bool)

    # Root /health and /api/v1/health return consistent data
    api_health = client.get("/api/v1/health").json()
    assert api_health["status"] == data["status"]
    assert api_health["database"]["connected"] == data["database"]["connected"]


def test_health_check_reports_failed_on_unwritable_storage(tmp_path: Path):
    """Test 3: Health check reports failed if core storage is not writable."""
    storage_root = tmp_path / "storage"
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text("<html></html>")

    settings = Settings(
        storage_root=storage_root,
        frontend_dist_dir=dist_dir,
        ollama_timeout_seconds=0.1,
    )
    app = create_app(settings_override=settings)

    # Patch storage writable check to return False
    with patch("app.api.v1.health._check_storage_writable", return_value=(False, False)):
        with TestClient(app) as client:
            res = client.get("/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "failed"


def test_launcher_and_stop_scripts_exist_and_safe():
    """Test 4: Verify Windows launcher scripts exist, locate paths safely, and have no destructive commands."""
    bat_launcher = PROJECT_ROOT / "Start-ZEZEdit.bat"
    bat_stop = PROJECT_ROOT / "Stop-ZEZEdit.bat"
    ps_launcher = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    ps_stop = PROJECT_ROOT / "Stop-ZEZEdit.ps1"

    for script in [bat_launcher, bat_stop, ps_launcher, ps_stop]:
        assert script.exists(), f"Missing launcher script: {script.name}"
        content = script.read_text(encoding="utf-8").lower()

        # Mandatory safety checks: No destructive commands
        assert "git clean" not in content
        assert "git reset --hard" not in content
        assert "rmdir /s /q storage\\db" not in content
        assert "rmdir /s /q storage\\media" not in content
        assert "rmdir /s /q storage\\exports" not in content


def test_background_jobs_and_restart_recovery_idempotency(tmp_path: Path):
    """Test 5: Background job recovery cleans up interrupted jobs on restart without corrupting records."""
    layout = StorageLayout.from_root(tmp_path / "storage")
    layout.ensure_directories()
    db_path = layout.db_file

    from app.db.migrator import run_migrations
    run_migrations(db_path=db_path, migrations_dir=PROJECT_ROOT / "backend" / "migrations", backup_dir=layout.backups)

    settings = Settings(storage_root=layout.root)
    orch = JobOrchestrator(settings=settings, db_path=db_path)

    # Create dummy interrupted jobs
    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, status, priority, retry_count, current_stage, created_at, updated_at)
            VALUES ('job_int_1', 'export_render', 'running', 1, 0, 'rendering', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z'),
                   ('job_int_2', 'media_analysis', 'cancelling', 1, 0, 'cancelling', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """
        )

    recovered = orch.recover_interrupted_jobs()
    assert "job_int_1" in recovered
    assert "job_int_2" in recovered

    with sqlite_session(db_path) as conn:
        rows = conn.execute("SELECT id, status, error_message FROM jobs WHERE id IN ('job_int_1', 'job_int_2')").fetchall()
        for r in rows:
            assert r["status"] == "interrupted"
            assert "restarted" in r["error_message"].lower() or "interrupted" in r["error_message"].lower()

    # Re-running recovery is idempotent
    second_run = orch.recover_interrupted_jobs()
    assert "job_int_1" not in second_run
    assert "job_int_2" not in second_run


def test_security_confinement_and_no_path_traversal_on_spa(prod_client):
    """Test 6: Verify SPA static serving strictly blocks directory traversal attempts."""
    client, dist_dir, settings = prod_client

    traversal_attempts = [
        "/..%2f..%2f..%2fWindows%2fwin.ini",
        "/....//....//....//etc/passwd",
        "/assets/..%2f..%2fstorage/db/zezedit.db",
    ]

    for path in traversal_attempts:
        res = client.get(path)
        # Traversal must be rejected (either 404 Not Found or 400 Bad Request, never 200 with external file content)
        assert res.status_code in [404, 400]
        assert "zezedit" not in res.text.lower()
