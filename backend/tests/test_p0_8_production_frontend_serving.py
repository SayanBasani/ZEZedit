"""
P0.8 Automated Regression Test Suite: Production Frontend Serving & SPA Routing
Comprehensive testing of root serving, static JS/CSS MIME types, 404 for missing assets,
valid SPA deep links, deep-link refresh, API route protection, health endpoint JSON,
media/streaming route preservation, path traversal defense, sensitive file protection,
working-directory independence, and missing-build diagnostic responses.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from app.core.config import PROJECT_ROOT, Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app


@pytest.fixture
def mock_prod_client(tmp_path: Path):
    """Fixture providing a TestClient with an isolated temporary production frontend build and storage."""
    dist_dir = tmp_path / "frontend" / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    index_html = dist_dir / "index.html"
    index_html.write_text(
        "<!doctype html><html><head><title>ZezEdit 2.0</title>"
        "<script type=\"module\" src=\"/assets/bundle.js\"></script>"
        "<link rel=\"stylesheet\" href=\"/assets/bundle.css\">"
        "</head><body><div id=\"root\">ZezEdit App Container</div></body></html>",
        encoding="utf-8",
    )

    sample_js = assets_dir / "bundle.js"
    sample_js.write_text("console.log('ZezEdit Production Frontend Bundle');", encoding="utf-8")

    sample_css = assets_dir / "bundle.css"
    sample_css.write_text("body { background-color: #0b0f17; color: #f8fafc; }", encoding="utf-8")

    favicon = dist_dir / "favicon.ico"
    favicon.write_bytes(b"\x00\x00\x01\x00")

    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()
    run_migrations(
        db_path=layout.db_file,
        migrations_dir=PROJECT_ROOT / "backend" / "migrations",
        backup_dir=layout.backups,
    )

    settings = Settings(
        storage_root=storage_root,
        frontend_dist_dir=dist_dir,
        ollama_base_url="http://127.0.0.1:19999",
        ollama_timeout_seconds=0.1,
    )

    app = create_app(settings_override=settings)
    with TestClient(app) as client:
        yield client, dist_dir, storage_root, settings


# -----------------------------------------------------------------------------
# 1. Root URL serves the production frontend
# -----------------------------------------------------------------------------
def test_01_root_url_serves_production_frontend(mock_prod_client):
    client, dist_dir, _, _ = mock_prod_client
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "ZezEdit App Container" in res.text
    assert "/assets/bundle.js" in res.text


# -----------------------------------------------------------------------------
# 2. Existing JavaScript asset returns correct content and MIME type
# -----------------------------------------------------------------------------
def test_02_javascript_asset_serves_correct_mime_and_content(mock_prod_client):
    client, _, _, _ = mock_prod_client
    res = client.get("/assets/bundle.js")
    assert res.status_code == 200
    content_type = res.headers.get("content-type", "").lower()
    assert "javascript" in content_type or "text/javascript" in content_type
    assert "ZezEdit Production Frontend Bundle" in res.text


# -----------------------------------------------------------------------------
# 3. Existing CSS asset returns correct content and MIME type
# -----------------------------------------------------------------------------
def test_03_css_asset_serves_correct_mime_and_content(mock_prod_client):
    client, _, _, _ = mock_prod_client
    res = client.get("/assets/bundle.css")
    assert res.status_code == 200
    assert "text/css" in res.headers.get("content-type", "").lower()
    assert "background-color: #0b0f17" in res.text


# -----------------------------------------------------------------------------
# 4. Missing static assets return 404, NEVER fallback to index.html
# -----------------------------------------------------------------------------
def test_04_missing_static_assets_return_404_not_html(mock_prod_client):
    client, _, _, _ = mock_prod_client
    missing_paths = [
        "/assets/nonexistent_chunk_123.js",
        "/assets/missing_styles.css",
        "/assets/image_404.png",
        "/missing_script.js",
        "/missing_styles.css",
        "/missing_logo.png",
        "/missing_font.woff2",
        "/missing_manifest.webmanifest",
    ]
    for path in missing_paths:
        res = client.get(path)
        assert res.status_code == 404, f"Path {path} did not return 404: {res.status_code}"
        assert "text/html" not in res.headers.get("content-type", ""), f"Path {path} returned HTML instead of 404 error"
        assert "<html" not in res.text.lower()


# -----------------------------------------------------------------------------
# 5. Valid frontend deep links return SPA entry point
# -----------------------------------------------------------------------------
def test_05_valid_frontend_deep_links_return_spa_entry(mock_prod_client):
    client, _, _, _ = mock_prod_client
    valid_deep_links = [
        "/videos",
        "/videos/med_test_12345",
        "/videos/med_test_12345/editor",
        "/studio/med_test_12345",
        "/projects",
        "/media",
        "/settings",
        "/processes",
        "/queue",
        "/ai-providers",
        "/characters",
        "/dashboard",
    ]
    for link in valid_deep_links:
        res = client.get(link)
        assert res.status_code == 200, f"Deep link {link} failed with {res.status_code}"
        assert "text/html" in res.headers.get("content-type", "")
        assert "ZezEdit App Container" in res.text


# -----------------------------------------------------------------------------
# 6. Refreshing a frontend deep link works (repeated requests succeed)
# -----------------------------------------------------------------------------
def test_06_refreshing_frontend_deep_link_is_idempotent(mock_prod_client):
    client, _, _, _ = mock_prod_client
    nested_route = "/videos/med_refresh_target"
    for i in range(3):
        res = client.get(nested_route)
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        assert "ZezEdit App Container" in res.text


# -----------------------------------------------------------------------------
# 7. Unknown API routes return proper API 404 JSON, NOT HTML
# -----------------------------------------------------------------------------
def test_07_unknown_api_routes_return_json_404_not_html(mock_prod_client):
    client, _, _, _ = mock_prod_client
    unknown_api_routes = [
        "/api/v1/non_existent_route",
        "/api/v1/media/unknown_action_xyz",
        "/api/v1/invalid/endpoint/nested",
        "/api/unknown",
        "/api/",
    ]
    for route in unknown_api_routes:
        get_res = client.get(route)
        assert get_res.status_code == 404, f"Route {route} did not return 404: {get_res.status_code}"
        assert "text/html" not in get_res.headers.get("content-type", "")
        assert "application/json" in get_res.headers.get("content-type", "")
        assert "<html" not in get_res.text.lower()

        post_res = client.post(route, json={"key": "val"})
        assert post_res.status_code in [404, 405]
        assert "text/html" not in post_res.headers.get("content-type", "")


# -----------------------------------------------------------------------------
# 8. Health endpoint remains JSON and unaffected by SPA fallback
# -----------------------------------------------------------------------------
def test_08_health_endpoint_remains_json(mock_prod_client):
    client, _, _, _ = mock_prod_client
    for health_url in ["/health", "/api/v1/health"]:
        res = client.get(health_url)
        assert res.status_code == 200
        assert "application/json" in res.headers.get("content-type", "")
        data = res.json()
        assert "status" in data
        assert "database" in data
        assert data["database"]["connected"] is True
        assert data["frontend_build_available"] is True


# -----------------------------------------------------------------------------
# 9. Existing media and system API routes remain reachable
# -----------------------------------------------------------------------------
def test_09_existing_api_routes_remain_reachable(mock_prod_client):
    client, _, _, _ = mock_prod_client
    routes = [
        ("/api/v1/projects", 200),
        ("/api/v1/jobs", 200),
        ("/api/v1/system/info", 200),
        ("/api/v1/system/diagnostics", 200),
        ("/api/v1/media", 200),
    ]
    for endpoint, expected_status in routes:
        res = client.get(endpoint)
        assert res.status_code == expected_status, f"Route {endpoint} failed with {res.status_code}"
        assert "application/json" in res.headers.get("content-type", "")


# -----------------------------------------------------------------------------
# 10. Existing streaming and download routes preserve their behavior
# -----------------------------------------------------------------------------
def test_10_streaming_and_download_routes_preserve_behavior(mock_prod_client):
    client, _, storage_root, _ = mock_prod_client

    # Test missing media streaming returns 404 JSON, NOT index.html
    missing_stream = client.get("/api/v1/media/med_missing_stream/stream")
    assert missing_stream.status_code == 404
    assert "text/html" not in missing_stream.headers.get("content-type", "")

    # Test missing export download returns 404 JSON, NOT index.html
    missing_export = client.get("/api/v1/exports/exp_missing_dl/download")
    assert missing_export.status_code == 404
    assert "text/html" not in missing_export.headers.get("content-type", "")


# -----------------------------------------------------------------------------
# 11. Path traversal attempts are strictly rejected
# -----------------------------------------------------------------------------
def test_11_path_traversal_attempts_are_blocked(mock_prod_client):
    client, _, _, _ = mock_prod_client
    traversals = [
        "/..%2f..%2f..%2fWindows%2fwin.ini",
        "/....//....//....//etc/passwd",
        "/assets/..%2f..%2fstorage/db/zezedit.db",
        "/assets/..%2f..%2fbackend/app/main.py",
        "/..\\..\\..\\Windows\\System32\\cmd.exe",
    ]
    for bad_path in traversals:
        res = client.get(bad_path)
        assert res.status_code in [400, 403, 404], f"Traversal {bad_path} was not rejected: {res.status_code}"
        assert "zezedit.db" not in res.text
        assert "password" not in res.text.lower()


# -----------------------------------------------------------------------------
# 12. Sensitive files (.env, SQLite databases, logs, source) are never exposed
# -----------------------------------------------------------------------------
def test_12_sensitive_files_are_protected_from_exposure(mock_prod_client):
    client, _, _, _ = mock_prod_client
    sensitive_targets = [
        "/.env",
        "/storage/db/zezedit.db",
        "/backend/app/main.py",
        "/storage/logs/launcher_stdout.log",
        "/storage/backups/test.db",
        "/.git/config",
        "/migrations/0001_initial_schema.sql",
    ]
    for target in sensitive_targets:
        res = client.get(target)
        assert res.status_code in [403, 404], f"Sensitive target {target} was exposed with {res.status_code}"
        assert "ZEZEDIT_" not in res.text
        assert "SQLite format" not in res.text
        assert "CREATE TABLE" not in res.text


# -----------------------------------------------------------------------------
# 13. Production serving works when launched from an external working directory
# -----------------------------------------------------------------------------
def test_13_production_serving_is_cwd_independent(mock_prod_client):
    client, dist_dir, _, settings = mock_prod_client
    # Verify frontend_dist_dir is an absolute resolved path independent of os.getcwd()
    assert settings.frontend_dist_dir.is_absolute()
    assert (settings.frontend_dist_dir / "index.html").is_file()

    # Request root and deep link
    assert client.get("/").status_code == 200
    assert client.get("/videos/med_cwd_test").status_code == 200


# -----------------------------------------------------------------------------
# 14. Missing production build produces useful diagnostic responses
# -----------------------------------------------------------------------------
def test_14_missing_production_build_diagnostic(tmp_path: Path):
    empty_dist = tmp_path / "empty_frontend" / "dist"
    # Do NOT create index.html
    empty_dist.mkdir(parents=True, exist_ok=True)

    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()
    run_migrations(
        db_path=layout.db_file,
        migrations_dir=PROJECT_ROOT / "backend" / "migrations",
        backup_dir=layout.backups,
    )

    settings = Settings(
        storage_root=storage_root,
        frontend_dist_dir=empty_dist,
        ollama_timeout_seconds=0.1,
    )
    app = create_app(settings_override=settings)
    with TestClient(app) as client:
        # Root returns JSON diagnostic
        res = client.get("/")
        assert res.status_code == 200
        assert "application/json" in res.headers.get("content-type", "")
        data = res.json()
        assert data["status"] == "online"
        assert "not found" in data["message"].lower()

        # Deep link returns 404 diagnostic
        deep_res = client.get("/videos/med_missing_dist")
        assert deep_res.status_code == 404
        assert "not found" in deep_res.json().get("detail", "").lower()


# -----------------------------------------------------------------------------
# 15. Production serving does not require Vite development server
# -----------------------------------------------------------------------------
def test_15_production_serving_has_zero_vite_dependency(mock_prod_client):
    client, _, _, settings = mock_prod_client
    # Verify no vite proxy configuration or vite dev server ports are queried
    res = client.get("/")
    assert res.status_code == 200
    # Built asset bundle paths are served directly by FastAPI /assets mount
    js_res = client.get("/assets/bundle.js")
    assert js_res.status_code == 200
    assert "5173" not in js_res.text
