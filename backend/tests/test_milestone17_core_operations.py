"""Milestone 17: Core Operations, Working Queue, Resource Inspector, AI Providers, and Docs Test Suite."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> TestClient:
    from pathlib import Path
    real_migrations = Path(__file__).resolve().parent.parent / "migrations"
    settings = Settings(
        app_name="ZezEditTest",
        storage_root=tmp_path / "storage",
        migrations_dir=real_migrations,
        environment="test",
        max_concurrent_jobs=2,
    )
    app = create_app(settings_override=settings)
    with TestClient(app) as test_client:
        yield test_client


def test_system_resources_endpoint(client: TestClient):
    """Verify live hardware resource monitoring endpoint returns valid CPU and RAM metrics."""
    res = client.get("/api/v1/system/resources")
    assert res.status_code == 200
    data = res.json()

    assert "cpu_percent" in data
    assert "process_cpu_percent" in data
    assert data["cpu_count_logical"] >= 1
    assert data["cpu_count_physical"] >= 1
    assert data["memory_total_mb"] > 0
    assert data["memory_percent"] >= 0.0
    assert data["process_memory_rss_mb"] >= 0.0
    assert data["execution_mode"] == "cpu_first"
    assert data["max_concurrent_jobs"] == 2


def test_queue_stats_and_job_logs(client: TestClient):
    """Verify Working Queue stats and job timeline log endpoints."""
    # Create project
    proj_res = client.post("/api/v1/projects", json={"name": "Queue Test Project"})
    assert proj_res.status_code == 201
    pid = proj_res.json()["id"]

    # Create job
    job_res = client.post(
        "/api/v1/jobs",
        json={
            "project_id": pid,
            "job_type": "highlight_discovery",
            "priority": 100,
            "input_config": {"target_clips": 3},
        },
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Verify queue stats
    stats_res = client.get("/api/v1/jobs/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_jobs"] >= 1
    assert stats["queued"] >= 1
    assert "highlight_discovery" in stats["by_type"]

    # Verify job logs
    logs_res = client.get(f"/api/v1/jobs/{job_id}/logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert logs["job_id"] == job_id
    assert logs["job_type"] == "highlight_discovery"
    assert len(logs["logs"]) >= 1
    assert any(job_id in l for l in logs["logs"])


def test_ai_providers_list_and_test_probe(client: TestClient):
    """Verify AI provider inventory, capabilities, and live health test probe."""
    res = client.get("/api/v1/ai-providers")
    assert res.status_code == 200
    providers = res.json()
    assert len(providers) >= 3

    provider_ids = [p["id"] for p in providers]
    assert "ollama" in provider_ids
    assert "faster-whisper" in provider_ids
    assert "heuristic-engine" in provider_ids

    # Check Ollama capabilities
    ollama = next(p for p in providers if p["id"] == "ollama")
    assert ollama["is_local"] is True
    assert any(c["task"] == "visual_understanding" for c in ollama["capabilities"])

    # Test probe on heuristic engine
    test_res = client.post("/api/v1/ai-providers/test", json={"provider_id": "heuristic-engine"})
    assert test_res.status_code == 200
    tdata = test_res.json()
    assert tdata["reachable"] is True
    assert tdata["error"] is None


def test_documentation_center_endpoints(client: TestClient):
    """Verify in-app documentation categories, article listings, search, and details."""
    # List categories
    cats_res = client.get("/api/v1/docs/categories")
    assert cats_res.status_code == 200
    cats = cats_res.json()
    assert len(cats) >= 5
    cat_ids = [c["id"] for c in cats]
    assert "getting-started" in cat_ids
    assert "workflow" in cat_ids
    assert "system-operations" in cat_ids

    # List articles
    arts_res = client.get("/api/v1/docs/articles")
    assert arts_res.status_code == 200
    arts = arts_res.json()
    assert len(arts) >= 10

    # Search articles
    search_res = client.get("/api/v1/docs/articles?query=reframing")
    assert search_res.status_code == 200
    s_arts = search_res.json()
    assert any("reframing" in a["title"].lower() or "reframing" in a["summary"].lower() for a in s_arts)

    # Get article detail
    detail_res = client.get("/api/v1/docs/articles/architecture-overview")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == "architecture-overview"
    assert "CPU-First Execution" in detail["markdown_content"]
    assert len(detail["tags"]) >= 1
