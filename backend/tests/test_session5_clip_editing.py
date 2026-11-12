"""Tests for Session 5: Candidate Clip Editing, Trimming, and Aspect Ratio Framing."""

import sqlite3
import uuid
import pytest
from pathlib import Path

from app.core.config import Settings
from app.core.errors import ValidationError, NotFoundError
from app.services.clip_editing_service import ClipEditingService


@pytest.fixture
def test_db_setup(tmp_path: Path):
    """Set up a test sqlite database with migrations up to 0014."""
    from app.db.migrator import run_migrations

    db_path = tmp_path / "test_session5.db"
    migrations_dir = Path("D:/ZezEdit/backend/migrations")
    run_migrations(db_path, migrations_dir)

    # Seed sample project, media_asset, and shorts_candidate
    proj_id = f"proj_{uuid.uuid4().hex[:8]}"
    media_id = f"med_{uuid.uuid4().hex[:8]}"
    cand_id = f"cand_{uuid.uuid4().hex[:8]}"
    run_id = f"cgr_{uuid.uuid4().hex[:8]}"
    an_id = f"an_{uuid.uuid4().hex[:8]}"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES (?, 'Test Proj', 'proj_dir', datetime('now'), datetime('now'))",
            (proj_id,),
        )
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path,
                file_size_bytes, duration_seconds, width, height, is_external,
                availability_status, created_at, updated_at
            ) VALUES (?, ?, 'sample.mp4', 'dummy/path.mp4', 1000000, 120.0, 1920, 1080, 0, 'available', datetime('now'), datetime('now'))
            """,
            (media_id, proj_id),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, project_id, media_asset_id, status, profile, created_at, updated_at
            ) VALUES (?, ?, ?, 'completed', 'full_pipeline', datetime('now'), datetime('now'))
            """,
            (an_id, proj_id, media_id),
        )
        conn.execute(
            """
            INSERT INTO candidate_generation_runs (
                id, project_id, media_asset_id, analysis_run_id, creative_direction, requested_count,
                min_duration, max_duration, status, candidates_discovered,
                candidates_selected, candidates_rejected, novelty_exclusions,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'auto_viral', 5, 10.0, 60.0, 'completed', 5, 5, 0, 0, datetime('now'), datetime('now'))
            """,
            (run_id, proj_id, media_id, an_id),
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, generation_run_id,
                start_time, end_time, duration, suggested_start_time, suggested_end_time,
                title, suggested_title, quality_score, review_status, creative_direction,
                natural_boundary_confidence, scoring_version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 10.5, 35.0, 24.5, 10.5, 35.0, 'Test Candidate', 'Test Candidate', 88.0, 'pending', 'auto_viral', 0.95, '2.0.0-m4', datetime('now'), datetime('now'))
            """,
            (cand_id, proj_id, media_id, an_id, run_id),
        )
        # Also seed a novelty record to verify it is NEVER modified by editing
        conn.execute(
            """
            INSERT INTO media_generated_clips_history (
                id, media_asset_id, project_id, generation_run_id, candidate_id,
                start_time, end_time, duration, creative_direction, aspect_ratio,
                score, title, created_at
            ) VALUES (?, ?, ?, ?, ?, 10.5, 35.0, 24.5, 'auto_viral', '9:16', 88.0, 'Test Candidate', datetime('now'))
            """,
            (f"hist_{uuid.uuid4().hex[:8]}", media_id, proj_id, run_id, cand_id),
        )

    settings = Settings(storage_root=tmp_path / "storage")
    service = ClipEditingService(settings=settings, db_path=db_path)
    return {
        "db_path": db_path,
        "service": service,
        "project_id": proj_id,
        "media_asset_id": media_id,
        "candidate_id": cand_id,
    }


def test_get_or_create_edit_creates_default(test_db_setup):
    """Test initial edit state matches original candidate bounds."""
    s = test_db_setup["service"]
    res = s.get_or_create_edit(
        test_db_setup["candidate_id"],
        test_db_setup["project_id"],
        test_db_setup["media_asset_id"],
    )

    assert res["candidate_id"] == test_db_setup["candidate_id"]
    assert res["original_start_time"] == 10.5
    assert res["original_end_time"] == 35.0
    assert res["edited_start_time"] == 10.5
    assert res["edited_end_time"] == 35.0
    assert res["edited_duration"] == 24.5
    assert res["aspect_ratio"] == "9:16"
    assert res["framing_mode"] == "center"
    assert res["manual_crop_x_pct"] == 50.0
    assert res["manual_crop_y_pct"] == 50.0
    assert res["manual_crop_zoom"] == 1.0
    assert res["media_duration"] == 120.0


def test_save_edit_and_validation(test_db_setup):
    """Test saving updated timestamps, aspect ratio, and manual positioning."""
    s = test_db_setup["service"]
    cid = test_db_setup["candidate_id"]
    pid = test_db_setup["project_id"]
    mid = test_db_setup["media_asset_id"]

    # 1. Successful save
    res = s.save_edit(
        candidate_id=cid,
        project_id=pid,
        media_asset_id=mid,
        edited_start_time=12.0,
        edited_end_time=30.0,
        aspect_ratio="1:1",
        framing_mode="manual",
        manual_crop_x_pct=65.0,
        manual_crop_y_pct=45.0,
        manual_crop_zoom=1.2,
    )

    assert res["edited_start_time"] == 12.0
    assert res["edited_end_time"] == 30.0
    assert res["edited_duration"] == 18.0
    assert res["aspect_ratio"] == "1:1"
    assert res["framing_mode"] == "manual"
    assert res["manual_crop_x_pct"] == 65.0
    assert res["manual_crop_y_pct"] == 45.0
    assert res["manual_crop_zoom"] == 1.2

    # 2. Validation: negative start
    with pytest.raises(ValidationError):
        s.save_edit(cid, pid, mid, -1.0, 20.0)

    # 3. Validation: end exceeds duration (120.0s)
    with pytest.raises(ValidationError):
        s.save_edit(cid, pid, mid, 10.0, 150.0)

    # 4. Validation: start >= end
    with pytest.raises(ValidationError):
        s.save_edit(cid, pid, mid, 30.0, 20.0)

    # 5. Validation: duration < 1.0s
    with pytest.raises(ValidationError):
        s.save_edit(cid, pid, mid, 10.0, 10.5)

    # 6. Validation: invalid aspect ratio
    with pytest.raises(ValidationError):
        s.save_edit(cid, pid, mid, 10.0, 20.0, aspect_ratio="21:9")


def test_reset_to_original_preserves_pristine_candidate(test_db_setup):
    """Test resetting to original restores boundaries without affecting candidate table."""
    s = test_db_setup["service"]
    cid = test_db_setup["candidate_id"]
    pid = test_db_setup["project_id"]
    mid = test_db_setup["media_asset_id"]
    db_path = test_db_setup["db_path"]

    # Modify the edit
    s.save_edit(cid, pid, mid, 15.0, 25.0, aspect_ratio="16:9", framing_mode="manual")

    # Reset
    reset_res = s.reset_to_original(cid, pid, mid)
    assert reset_res["edited_start_time"] == 10.5
    assert reset_res["edited_end_time"] == 35.0
    assert reset_res["edited_duration"] == 24.5
    assert reset_res["aspect_ratio"] == "9:16"
    assert reset_res["framing_mode"] == "center"

    # Verify immutable candidate table in SQLite
    with sqlite3.connect(db_path) as conn:
        cand_row = conn.execute(
            "SELECT start_time, end_time, duration FROM shorts_candidates WHERE id = ?",
            (cid,),
        ).fetchone()
        assert cand_row[0] == 10.5
        assert cand_row[1] == 35.0
        assert cand_row[2] == 24.5

        # Verify novelty ledger was untouched
        hist_row = conn.execute(
            "SELECT start_time, end_time FROM media_generated_clips_history WHERE candidate_id = ?",
            (cid,),
        ).fetchone()
        assert hist_row[0] == 10.5
        assert hist_row[1] == 35.0


def test_api_clip_edit_routes(test_db_setup):
    """Test REST API endpoints for candidate clip editing."""
    from fastapi.testclient import TestClient
    from app.main import app

    cid = test_db_setup["candidate_id"]
    pid = test_db_setup["project_id"]
    mid = test_db_setup["media_asset_id"]

    # Point app to the test db
    app.state.settings = Settings(storage_root=test_db_setup["db_path"].parent / "storage")
    app.state.storage = type("MockLayout", (), {"db_file": test_db_setup["db_path"]})()

    client = TestClient(app)

    # 1. GET edit
    get_res = client.get(f"/api/v1/projects/{pid}/media/{mid}/candidates/{cid}/edit")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["candidate_id"] == cid
    assert data["edited_start_time"] == 10.5
    assert data["edited_end_time"] == 35.0
    assert data["aspect_ratio"] == "9:16"

    # 2. PUT edit
    put_res = client.put(
        f"/api/v1/projects/{pid}/media/{mid}/candidates/{cid}/edit",
        json={
            "edited_start_time": 14.0,
            "edited_end_time": 28.0,
            "aspect_ratio": "4:5",
            "framing_mode": "manual",
            "manual_crop_x_pct": 60.0,
            "manual_crop_y_pct": 50.0,
            "manual_crop_zoom": 1.1,
        },
    )
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["edited_start_time"] == 14.0
    assert updated_data["edited_end_time"] == 28.0
    assert updated_data["edited_duration"] == 14.0
    assert updated_data["aspect_ratio"] == "4:5"
    assert updated_data["framing_mode"] == "manual"

    # 3. POST reset
    reset_res = client.post(f"/api/v1/projects/{pid}/media/{mid}/candidates/{cid}/edit/reset")
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["edited_start_time"] == 10.5
    assert reset_data["edited_end_time"] == 35.0
    assert reset_data["aspect_ratio"] == "9:16"
    assert reset_data["framing_mode"] == "center"

