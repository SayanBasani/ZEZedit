import json
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.connection import create_sqlite_connection, sqlite_session
from app.db.migrator import run_migrations
from app.main import app
from app.services.jobs import JobOrchestrator


@pytest.fixture
def test_client():
    return TestClient(app)


def test_atomic_job_claiming_guarantee(tmp_path):
    """Verify that multiple concurrent workers cannot claim the same queued job."""
    db_file = tmp_path / "test_jobs.db"
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(db_path=db_file, migrations_dir=migrations_dir)

    now = datetime.now(timezone.utc).isoformat()
    with sqlite_session(db_file) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, status, priority, created_at, updated_at)
            VALUES ('job_test_atomic_1', 'export_render', 'queued', 100, ?, ?)
            """,
            (now, now),
        )

    settings = Settings(db_path=db_file)
    orchestrator = JobOrchestrator(settings=settings, db_path=db_file)

    results = []
    exceptions = []
    lock = threading.Lock()
    barrier = threading.Barrier(5)

    def worker_claim(worker_idx):
        try:
            barrier.wait()
            job = orchestrator.claim_next_queued_job(worker_id=f"worker_{worker_idx}")
            if job:
                with lock:
                    results.append((worker_idx, job.id))
        except Exception as e:
            with lock:
                exceptions.append((worker_idx, str(e)))

    threads = [threading.Thread(target=worker_claim, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not exceptions, f"Exceptions in worker threads: {exceptions}"
    # Exactly ONE worker must have claimed the job
    assert len(results) == 1
    assert results[0][1] == "job_test_atomic_1"

    # Further claims return None because the queue is empty
    assert orchestrator.claim_next_queued_job(worker_id="worker_subsequent") is None


def test_stale_queued_job_timeout_cleanup(tmp_path):
    """Verify that jobs queued longer than timeout threshold are cleaned up as failed."""
    db_file = tmp_path / "test_stale.db"
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(db_path=db_file, migrations_dir=migrations_dir)

    # 40 minutes old (2400s > 1800s threshold)
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=40)).isoformat()
    # 5 minutes old (300s < 1800s threshold)
    recent_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    with sqlite_session(db_file) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, status, priority, created_at, updated_at)
            VALUES ('job_stale_1', 'export_render', 'queued', 100, ?, ?)
            """,
            (stale_time, stale_time),
        )
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, status, priority, created_at, updated_at)
            VALUES ('job_recent_1', 'export_render', 'queued', 100, ?, ?)
            """,
            (recent_time, recent_time),
        )

    settings = Settings(db_path=db_file)
    orchestrator = JobOrchestrator(settings=settings, db_path=db_file)

    cleaned = orchestrator.cleanup_stale_queued_jobs(max_queued_age_seconds=1800.0)
    assert "job_stale_1" in cleaned
    assert "job_recent_1" not in cleaned

    stale_record = orchestrator.get_job("job_stale_1")
    assert stale_record.status == "failed"
    assert "timed out in queue" in (stale_record.error_message or "")

    recent_record = orchestrator.get_job("job_recent_1")
    assert recent_record.status == "queued"


def test_candidate_script_editing_persistence(test_client):
    """Verify that updating a candidate's script (title, hook, description) persists in SQLite."""
    res = test_client.get("/api/v1/projects/default/highlights")
    assert res.status_code == 200
    data = res.json()
    candidates = data.get("candidates", [])
    if not candidates:
        pytest.skip("No candidates available in project 'default' to test editing.")

    target_cand = candidates[0]
    cand_id = target_cand["id"]

    new_title = f"Acceptance Script Title {int(time.time())}"
    new_hook = "This is a tested high-impact opening hook for product acceptance!"
    new_desc = "Spoken dialogue detailing the climax and character reaction."

    patch_res = test_client.patch(
        f"/api/v1/projects/default/highlights/{cand_id}",
        json={
            "title": new_title,
            "hook": new_hook,
            "description": new_desc,
        },
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()

    assert patched_data["title"] == new_title
    assert patched_data["description"] == new_desc
    assert patched_data.get("is_user_modified") == 1
    ai_exp = patched_data.get("ai_explanation") or {}
    assert ai_exp.get("hook") == new_hook

    # Verify persistent retrieval on subsequent fresh GET
    get_res = test_client.get(f"/api/v1/projects/default/highlights/{cand_id}")
    assert get_res.status_code == 200
    fresh_data = get_res.json()
    assert fresh_data["title"] == new_title
    assert fresh_data["description"] == new_desc
    assert fresh_data.get("is_user_modified") == 1
    assert fresh_data.get("ai_explanation", {}).get("hook") == new_hook


def test_thumbnail_endpoint_returns_jpeg(test_client):
    """Verify that the global thumbnail endpoint successfully delivers JPEG thumbnails."""
    media_res = test_client.get("/api/v1/media")
    assert media_res.status_code == 200
    items = media_res.json().get("items", [])
    if not items:
        pytest.skip("No media assets present in test database.")

    asset_id = items[0]["id"]
    thumb_res = test_client.get(f"/api/v1/media/{asset_id}/thumbnail")
    assert thumb_res.status_code == 200
    assert thumb_res.headers["content-type"] == "image/jpeg"
    assert len(thumb_res.content) > 100
