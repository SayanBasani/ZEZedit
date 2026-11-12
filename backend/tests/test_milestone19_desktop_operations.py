"""Milestone 19: Desktop Operations Center, Working Queue, Resource Inspector, and AI Provider Manager tests."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.main import create_app
from app.services.jobs import JobOrchestrator


@pytest.fixture
def app_and_client(tmp_path: Path):
    storage_root = tmp_path / "storage"
    real_migrations = Path(__file__).resolve().parent.parent / "migrations"
    settings = Settings(
        app_name="ZezEditTest",
        storage_root=storage_root,
        migrations_dir=real_migrations,
        environment="test",
        max_concurrent_jobs=2,
    )
    app = create_app(settings_override=settings)
    layout = StorageLayout.from_root(storage_root)
    with TestClient(app) as client:
        yield client, settings, layout


def test_system_diagnostics_comprehensive(app_and_client):
    client, settings, layout = app_and_client
    res = client.get("/api/v1/system/diagnostics")
    assert res.status_code == 200
    data = res.json()

    assert "overall_status" in data
    assert data["overall_status"] in {"healthy", "degraded", "action_required"}
    assert "checks" in data
    assert len(data["checks"]) >= 5

    check_names = {c["name"] for c in data["checks"]}
    assert "SQLite Database Engine" in check_names
    assert "Storage Directory Boundary" in check_names
    assert "FFmpeg Media Encoder" in check_names
    assert "FFprobe Stream Inspector" in check_names
    assert "Ollama Local Inference Provider" in check_names

    # Verify SQLite check details
    sqlite_check = next(c for c in data["checks"] if c["name"] == "SQLite Database Engine")
    assert sqlite_check["status"] in {"ok", "warning"}
    assert sqlite_check["details"]["journal_mode"].lower() == "wal"


def test_job_cancellation_and_terminal_constraints(app_and_client):
    client, settings, layout = app_and_client

    # 1. Create a project
    proj_res = client.post("/api/v1/projects", json={"name": "Queue Ops Test"})
    assert proj_res.status_code == 201
    pid = proj_res.json()["id"]

    # 2. Create a queued job
    job_res = client.post(
        "/api/v1/jobs",
        json={
            "job_type": "test_operation",
            "project_id": pid,
            "priority": 100,
            "max_attempts": 2,
        },
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]
    assert job_res.json()["status"] == "queued"

    # 3. Cancel while queued
    cancel_res = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # 4. Attempting to cancel an already-cancelled job fails
    cancel_again = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_again.status_code == 400
    err_body = cancel_again.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "already in terminal state" in err_msg.lower()


def test_job_retry_lifecycle_and_event_timeline(app_and_client):
    client, settings, layout = app_and_client
    orchestrator = JobOrchestrator(settings=settings, db_path=layout.db_file)

    proj_res = client.post("/api/v1/projects", json={"name": "Retry Test"})
    pid = proj_res.json()["id"]

    # Create job with max_attempts = 2
    job = orchestrator.create_job(job_type="analysis_step", project_id=pid, max_attempts=2)
    assert job.status == "queued"
    assert job.retry_count == 0

    # Start job and fail it
    orchestrator.transition_job_state(job.id, "running")
    orchestrator.transition_job_state(job.id, "failed", error_message="Sample test error")

    failed_job = orchestrator.get_job(job.id)
    assert failed_job.status == "failed"

    # 1. Retry attempt 1
    retry_res = client.post(f"/api/v1/jobs/{job.id}/retry")
    assert retry_res.status_code == 200
    retried_data = retry_res.json()
    assert retried_data["status"] == "queued"
    assert retried_data["retry_count"] == 1
    assert retried_data["error_message"] is None

    # Fail attempt 1
    orchestrator.transition_job_state(job.id, "running")
    orchestrator.transition_job_state(job.id, "failed", error_message="Second failure")

    # 2. Retry attempt 2
    retry_res2 = client.post(f"/api/v1/jobs/{job.id}/retry")
    assert retry_res2.status_code == 200
    assert retry_res2.json()["retry_count"] == 2

    # Fail attempt 2 (max reached)
    orchestrator.transition_job_state(job.id, "running")
    orchestrator.transition_job_state(job.id, "failed", error_message="Third failure")

    # 3. Third retry must be rejected (max attempts exceeded)
    retry_res3 = client.post(f"/api/v1/jobs/{job.id}/retry")
    assert retry_res3.status_code == 400
    err_body3 = retry_res3.json()
    err_msg3 = err_body3.get("detail") or err_body3.get("error", {}).get("message", "")
    assert "maximum attempts" in err_msg3.lower()

    # 4. Inspect job logs to ensure retry events appear in timeline
    logs_res = client.get(f"/api/v1/jobs/{job.id}/logs")
    assert logs_res.status_code == 200
    logs_data = logs_res.json()
    assert len(logs_data["logs"]) >= 4
    has_retry_event = any("retried" in msg.lower() for msg in logs_data["logs"])
    assert has_retry_event


def test_queue_stats_aggregation(app_and_client):
    client, settings, layout = app_and_client
    orchestrator = JobOrchestrator(settings=settings, db_path=layout.db_file)

    orchestrator.create_job(job_type="proxy_transcode")
    j2 = orchestrator.create_job(job_type="export_encode")
    orchestrator.transition_job_state(j2.id, "running")
    orchestrator.transition_job_state(j2.id, "completed")

    stats_res = client.get("/api/v1/jobs/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_jobs"] >= 2
    assert stats["queued"] >= 1
    assert stats["completed"] >= 1
    assert "proxy_transcode" in stats["by_type"]
    assert "export_encode" in stats["by_type"]


def test_ai_providers_and_heuristics_offline_resilience(app_and_client):
    client, settings, layout = app_and_client

    # 1. List providers
    list_res = client.get("/api/v1/ai-providers")
    assert list_res.status_code == 200
    providers = list_res.json()
    assert len(providers) >= 3

    p_ids = {p["id"] for p in providers}
    assert "ollama" in p_ids
    assert "faster-whisper" in p_ids
    assert "heuristic-engine" in p_ids

    # Heuristic engine is guaranteed ready
    heuristic = next(p for p in providers if p["id"] == "heuristic-engine")
    assert heuristic["status"] == "ready"
    assert heuristic["is_local"] is True

    # 2. Test heuristic probe
    test_res = client.post("/api/v1/ai-providers/test", json={"provider_id": "heuristic-engine"})
    assert test_res.status_code == 200
    assert test_res.json()["reachable"] is True


def test_documentation_center_categories_and_search(app_and_client):
    client, settings, layout = app_and_client

    # 1. Categories
    cat_res = client.get("/api/v1/docs/categories")
    assert cat_res.status_code == 200
    cats = cat_res.json()
    assert len(cats) >= 5

    # 2. Articles search by keyword
    search_res = client.get("/api/v1/docs/articles?query=troubleshooting")
    assert search_res.status_code == 200
    articles = search_res.json()
    assert len(articles) >= 1
    assert articles[0]["id"] == "troubleshooting-guide"

    # 3. Article detail retrieval
    detail_res = client.get("/api/v1/docs/articles/troubleshooting-guide")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "FFmpeg" in detail["markdown_content"]
    assert len(detail["tags"]) >= 3
