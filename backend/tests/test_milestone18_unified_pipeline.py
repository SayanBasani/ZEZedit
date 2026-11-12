"""Milestone 18: Unified Video-to-Shorts Production Pipeline Test Suite.

Verifies:
1. Authoritative workflow lifecycle state machine transitions across 18 explicit stages.
2. Workflow API endpoint GET /api/v1/projects/{project_id}/media/{asset_id}/workflow.
3. Batch export endpoint POST /api/v1/projects/{project_id}/exports/batch enqueuing parallel jobs.
4. Multi-video data isolation ensuring zero cross-project or cross-media state leakage.
5. Error handling and validation for skipped candidates.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.main import create_app
from app.services.workflow_state import WorkflowStage, WorkflowStateMachine


@pytest.fixture
def client(tmp_path) -> TestClient:
    real_migrations = Path(__file__).resolve().parent.parent / "migrations"
    settings = Settings(
        app_name="ZezEditM18Test",
        storage_root=tmp_path / "storage",
        migrations_dir=real_migrations,
        environment="test",
        max_concurrent_jobs=2,
    )
    app = create_app(settings_override=settings)
    with TestClient(app) as test_client:
        yield test_client


def seed_analysis_run(conn, run_id: str, project_id: str, media_asset_id: str, status: str = "completed"):
    now_iso = "2026-11-12T08:00:00Z"
    conn.execute(
        """
        INSERT INTO analysis_runs (
            id, project_id, media_asset_id, status, profile,
            progress_pct, current_stage, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'full', 100.0, 'completed', ?, ?)
        """,
        (run_id, project_id, media_asset_id, status, now_iso, now_iso),
    )


def seed_candidate(
    conn,
    cand_id: str,
    project_id: str,
    media_asset_id: str,
    analysis_run_id: str,
    title: str = "Test Highlight",
    start_time: float = 0.0,
    end_time: float = 15.0,
    quality_score: float = 0.85,
    review_status: str = "recommended",
):
    now_iso = "2026-11-12T08:00:00Z"
    duration = end_time - start_time
    conn.execute(
        """
        INSERT INTO shorts_candidates (
            id, project_id, media_asset_id, analysis_run_id, start_time, end_time,
            duration, suggested_start_time, suggested_end_time, is_user_modified,
            title, suggested_title, description, category, secondary_categories_json,
            quality_score, score_breakdown_json, gate_results_json, warnings_json,
            missing_evidence_json, review_status, transcript_references_json,
            scene_references_json, visual_evidence_json, audio_evidence_json,
            ai_explanation_json, scoring_version, queued_for_render, created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?
        )
        """,
        (
            cand_id, project_id, media_asset_id, analysis_run_id, start_time, end_time,
            duration, start_time, end_time, 0,
            title, title, "Test description", "hook", "[]",
            quality_score, "{}", "{}", "[]",
            "[]", review_status, "[]",
            "[]", "[]", "[]",
            "{}", "2.0.0", 0, now_iso, now_iso
        ),
    )


def seed_export(conn, exp_id: str, project_id: str, media_asset_id: str, cand_id: str, status: str = "completed"):
    now_iso = "2026-11-12T08:00:00Z"
    conn.execute(
        """
        INSERT INTO exports (
            id, project_id, candidate_id, media_asset_id, title, export_preset,
            target_aspect_ratio, target_width, target_height, video_codec, audio_codec,
            pixel_fmt, fps, crf, audio_bitrate, caption_config_json, audio_config_json,
            output_path, output_filename, file_size_bytes, duration_seconds, status,
            validation_status, validation_details_json, created_at
        ) VALUES (
            ?, ?, ?, ?, 'Test Short', 'shorts_reels_9_16',
            '9:16', 1080, 1920, 'libx264', 'aac',
            'yuv420p', 30.0, 22, '128k', '{}', '{}',
            '/storage/test.mp4', 'test.mp4', 50000, 25.0, ?,
            'valid', '{}', ?
        )
        """,
        (exp_id, project_id, cand_id, media_asset_id, status, now_iso),
    )


def test_workflow_state_evaluation_lifecycle(client: TestClient):
    """Verify authoritative lifecycle stage transitions for a media asset."""
    # 1. Create project
    proj_res = client.post("/api/v1/projects", json={"name": "Lifecycle Pipeline Project"})
    assert proj_res.status_code == 201
    pid = proj_res.json()["id"]

    db_path = StorageLayout.from_root(client.app.state.settings.storage_root).db_file
    asset_id = "med_test_pipeline_01"
    now_iso = "2026-11-12T08:00:00Z"

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id, pid, "source_interview.mp4", "/storage/test.mp4", "video",
                1048576, 120.0, 1920, 1080, 0, "ready", now_iso, now_iso
            ),
        )

    # State should initially be READY_FOR_ANALYSIS
    wf_service = WorkflowStateMachine(client.app.state.settings, db_path)
    wf_state = wf_service.evaluate(pid, asset_id)
    assert wf_state.current_stage == WorkflowStage.READY_FOR_ANALYSIS.value
    assert "start_analysis" in wf_state.available_next_actions
    assert wf_state.candidate_counts["total"] == 0
    assert wf_state.approved_short_counts == 0

    # 2. Simulate Analysis Completed
    with sqlite_session(db_path) as conn:
        seed_analysis_run(conn, "run_test_01", pid, asset_id, "completed")

    wf_state = wf_service.evaluate(pid, asset_id)
    assert wf_state.current_stage == WorkflowStage.READY_FOR_DISCOVERY.value
    assert "discover_highlights" in wf_state.available_next_actions
    assert WorkflowStage.ANALYSIS_COMPLETED.value in wf_state.completed_stages

    # 3. Simulate Candidates Generated
    cand_id_1 = "cand_test_01"
    cand_id_2 = "cand_test_02"
    with sqlite_session(db_path) as conn:
        seed_candidate(conn, cand_id_1, pid, asset_id, "run_test_01", title="Great Point", start_time=10.0, end_time=35.0, quality_score=0.88, review_status="recommended")
        seed_candidate(conn, cand_id_2, pid, asset_id, "run_test_01", title="Funny Moment", start_time=45.0, end_time=75.0, quality_score=0.92, review_status="recommended")

    wf_state = wf_service.evaluate(pid, asset_id)
    assert wf_state.current_stage == WorkflowStage.READY_FOR_REVIEW.value
    assert wf_state.candidate_counts["total"] == 2
    assert "review_shorts" in wf_state.available_next_actions

    # 4. Simulate Review: Approve cand_test_01
    with sqlite_session(db_path) as conn:
        conn.execute(
            "UPDATE shorts_candidates SET review_status = 'approved' WHERE id = ?",
            (cand_id_1,),
        )

    wf_state = wf_service.evaluate(pid, asset_id)
    assert wf_state.current_stage == WorkflowStage.SHORTS_APPROVED.value
    assert wf_state.approved_short_counts == 1
    assert "batch_export" in wf_state.available_next_actions

    # 5. Simulate Export Completed
    with sqlite_session(db_path) as conn:
        seed_export(conn, "exp_test_01", pid, asset_id, cand_id_1, "completed")

    wf_state = wf_service.evaluate(pid, asset_id)
    assert wf_state.current_stage == WorkflowStage.EXPORT_COMPLETED.value
    assert wf_state.export_counts["completed"] == 1
    assert "next_video" in wf_state.available_next_actions


def test_media_workflow_api_endpoint(client: TestClient):
    """Verify GET /api/v1/projects/{pid}/media/{asset_id}/workflow HTTP response structure."""
    proj_res = client.post("/api/v1/projects", json={"name": "API Workflow Project"})
    pid = proj_res.json()["id"]

    db_path = StorageLayout.from_root(client.app.state.settings.storage_root).db_file
    asset_id = "med_api_01"
    now_iso = "2026-11-12T08:00:00Z"
    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (asset_id, pid, "podcast.mp4", "/storage/pod.mp4", "video", 2048, 60.0, 1920, 1080, 0, "ready", now_iso, now_iso),
        )

    res = client.get(f"/api/v1/projects/{pid}/media/{asset_id}/workflow")
    assert res.status_code == 200
    data = res.json()
    assert data["video_id"] == asset_id
    assert data["project_id"] == pid
    assert data["video_name"] == "podcast.mp4"
    assert data["current_stage"] in [WorkflowStage.IMPORTED.value, WorkflowStage.READY_FOR_ANALYSIS.value]
    assert "available_next_actions" in data
    assert "candidate_counts" in data
    assert "export_counts" in data


def test_batch_export_endpoint_success(client: TestClient):
    """Verify POST /api/v1/projects/{pid}/exports/batch enqueues parallel render jobs."""
    import subprocess
    proj_res = client.post("/api/v1/projects", json={"name": "Batch Export Project"})
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_batch_01"
    now_iso = "2026-11-12T08:00:00Z"

    # Generate a lightweight 3-second synthetic video file for the render job
    synth_video = layout.temp / "synth_batch_source.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "64k",
            str(synth_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (asset_id, pid, "clip_source.mp4", str(synth_video), "video", 1024, 3.0, 320, 240, 0, "ready", now_iso, now_iso),
        )

        seed_analysis_run(conn, "run_dummy", pid, asset_id, "completed")
        seed_candidate(conn, "cand_batch_01", pid, asset_id, "run_dummy", title="Highlight 1", start_time=0.0, end_time=1.2, review_status="approved")
        seed_candidate(conn, "cand_batch_02", pid, asset_id, "run_dummy", title="Highlight 2", start_time=1.2, end_time=2.4, review_status="approved")

    # Call batch export
    payload = {
        "candidate_ids": ["cand_batch_01", "cand_batch_02"],
        "preset": "vertical_9_16",
        "caption_mode": "word_highlight",
        "normalize_audio": True,
    }
    batch_res = client.post(f"/api/v1/projects/{pid}/exports/batch", json=payload)
    assert batch_res.status_code == 200
    bdata = batch_res.json()

    assert bdata["total_requested"] == 2
    assert bdata["total_submitted"] == 2
    assert len(bdata["items"]) == 2
    assert len(bdata["skipped_candidates"]) == 0
    assert bdata["batch_id"].startswith("batch_")

    for item in bdata["items"]:
        assert item["status"] == "queued"
        assert item["export_id"].startswith("exp_")
        assert item["job_id"].startswith("job_")
        assert item["output_filename"].endswith(".mp4")

    # Verify jobs were created in database
    with sqlite_session(db_path) as conn:
        conn.row_factory = None
        jobs = conn.execute(
            "SELECT id, job_type, status FROM jobs WHERE project_id = ? ORDER BY created_at ASC",
            (pid,),
        ).fetchall()
        assert len(jobs) == 2
        assert all(j[1] == "export_render" for j in jobs)


def test_batch_export_validation_and_skipped(client: TestClient):
    """Verify batch export properly reports non-existent candidates in skipped_candidates."""
    proj_res = client.post("/api/v1/projects", json={"name": "Validation Project"})
    pid = proj_res.json()["id"]

    payload = {
        "candidate_ids": ["cand_non_existent_123", "cand_ghost_456"],
        "preset": "vertical_9_16",
    }
    res = client.post(f"/api/v1/projects/{pid}/exports/batch", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["total_requested"] == 2
    assert data["total_submitted"] == 0
    assert len(data["skipped_candidates"]) == 2
    assert data["skipped_candidates"][0]["candidate_id"] == "cand_non_existent_123"
    assert "not found" in data["skipped_candidates"][0]["reason"]


def test_multi_video_data_isolation(client: TestClient):
    """Verify strict multi-video isolation: candidate counts, approvals, and exports don't bleed across projects."""
    p1 = client.post("/api/v1/projects", json={"name": "Project Alpha"}).json()["id"]
    p2 = client.post("/api/v1/projects", json={"name": "Project Beta"}).json()["id"]

    db_path = StorageLayout.from_root(client.app.state.settings.storage_root).db_file
    now_iso = "2026-11-12T08:00:00Z"

    with sqlite_session(db_path) as conn:
        # Asset A in Project Alpha
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, media_type, duration_seconds, is_external, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("med_alpha", p1, "alpha.mp4", "/storage/alpha.mp4", "video", 100.0, 0, now_iso, now_iso),
        )
        # Asset B in Project Beta
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, media_type, duration_seconds, is_external, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("med_beta", p2, "beta.mp4", "/storage/beta.mp4", "video", 80.0, 0, now_iso, now_iso),
        )

        seed_analysis_run(conn, "run_a", p1, "med_alpha", "completed")
        seed_analysis_run(conn, "run_b", p2, "med_beta", "completed")

        # 2 candidates in Alpha, 1 approved
        seed_candidate(conn, "cand_alpha_1", p1, "med_alpha", "run_a", title="A1", review_status="approved")
        seed_candidate(conn, "cand_alpha_2", p1, "med_alpha", "run_a", title="A2", review_status="recommended")

        # 1 candidate in Beta, rejected
        seed_candidate(conn, "cand_beta_1", p2, "med_beta", "run_b", title="B1", review_status="rejected")

    wf_service = WorkflowStateMachine(client.app.state.settings, db_path)
    state_alpha = wf_service.evaluate(p1, "med_alpha")
    state_beta = wf_service.evaluate(p2, "med_beta")

    assert state_alpha.candidate_counts["total"] == 2
    assert state_alpha.approved_short_counts == 1
    assert state_alpha.current_stage == WorkflowStage.SHORTS_APPROVED.value

    assert state_beta.candidate_counts["total"] == 1
    assert state_beta.approved_short_counts == 0
    assert state_beta.candidate_counts["rejected"] == 1
    assert state_beta.current_stage == WorkflowStage.REVIEW_IN_PROGRESS.value
