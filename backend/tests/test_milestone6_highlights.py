"""Automated tests for Milestone 6: AI Highlight Discovery & Candidate Ranking."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.highlight_discovery import HighlightDiscoveryEngine, SCORING_VERSION


@pytest.fixture
def highlights_env(tmp_path: Path):
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    settings = Settings(
        storage_root=storage_root,
        environment="testing",
        log_level="DEBUG",
    )

    run_migrations(
        db_path=layout.db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=layout.backups,
    )

    # Seed an analyzed media project into DB
    now = "2026-11-11T12:00:00Z"
    proj_id = "proj_test_hl"
    asset_id = "med_test_hl"
    run_id = "run_test_hl"

    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, status, storage_subdir, created_at, updated_at)
            VALUES (?, 'Highlight Test Project', 'active', ?, ?, ?)
            """,
            (proj_id, proj_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external,
                media_type, file_size_bytes, duration_seconds, width, height, fps,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                ?, ?, 'podcast_interview.mp4', 'podcast_interview.mp4', 0,
                'video', 50000000, 120.0, 1920, 1080, 30.0,
                'ready', 'complete', ?, ?
            )
            """,
            (asset_id, proj_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, media_asset_id, project_id, status, profile, config_json,
                progress_pct, current_stage, created_at, updated_at
            ) VALUES (?, ?, ?, 'completed', 'balanced', '{}', 100.0, 'completed', ?, ?)
            """,
            (run_id, asset_id, proj_id, now, now),
        )

        # Seed Scenes
        conn.execute(
            """
            INSERT INTO video_scenes (id, analysis_run_id, media_asset_id, scene_index, start_time, end_time, representative_timestamp, change_score, created_at)
            VALUES ('sc1', ?, ?, 0, 0.0, 30.0, 15.0, 0.4, ?),
                   ('sc2', ?, ?, 1, 30.0, 75.0, 52.5, 0.5, ?),
                   ('sc3', ?, ?, 2, 75.0, 120.0, 97.5, 0.35, ?)
            """,
            (run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now),
        )

        # Seed Speech Turns forming dialogue setup & punchlines
        conn.execute(
            """
            INSERT INTO speech_turns (id, analysis_run_id, media_asset_id, start_time, end_time, speaker_label, text, turn_type, created_at)
            VALUES 
            ('t1', ?, ?, 5.0, 15.0, 'Speaker 1', 'Why did you decide to build an AI video editor completely local first?', 'question', ?),
            ('t2', ?, ?, 16.0, 32.0, 'Speaker 2', 'Because privacy and reliability matter! Cloud uploads take hours and cost a fortune.', 'exclamation', ?),
            ('t3', ?, ?, 35.0, 50.0, 'Speaker 1', 'That is an incredible breakthrough for content creators.', 'statement', ?),
            ('t4', ?, ?, 80.0, 95.0, 'Speaker 2', 'And so we realized simplicity is the ultimate sophistication.', 'statement', ?)
            """,
            (run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now),
        )

        # Seed Visual observations
        conn.execute(
            """
            INSERT INTO visual_observations (id, analysis_run_id, media_asset_id, timestamp, category, description, provider_model, confidence, created_at)
            VALUES ('obs1', ?, ?, 12.0, 'subjects', 'Speaker 1 gesturing enthusiastically in modern podcast studio', 'qwen3-vl:4b-instruct', 0.92, ?),
                   ('obs2', ?, ?, 25.0, 'subjects', 'Speaker 2 smiling and speaking directly into microphone', 'qwen3-vl:4b-instruct', 0.95, ?)
            """,
            (run_id, asset_id, now, run_id, asset_id, now),
        )

    return {
        "settings": settings,
        "storage": layout,
        "project_id": proj_id,
        "media_asset_id": asset_id,
        "analysis_run_id": run_id,
    }


def test_highlight_discovery_engine(highlights_env):
    engine = HighlightDiscoveryEngine(
        settings=highlights_env["settings"],
        db_path=highlights_env["storage"].db_file,
    )

    candidates = engine.discover_highlights(
        project_id=highlights_env["project_id"],
        media_asset_id=highlights_env["media_asset_id"],
        min_duration=10.0,
        max_duration=60.0,
        target_clip_count=5,
        use_ai_explanations=False,
    )

    assert len(candidates) >= 1
    top = candidates[0]

    # Verify score breakdown exists and matches schema
    assert "score_breakdown" in top
    b = top["score_breakdown"]
    assert b["total_score"] > 0
    assert "semantic_interest" in b
    assert "narrative_completeness" in b
    assert "conversation_structure" in b
    assert "visual_interest" in b
    assert "audio_evidence" in b
    assert "opening_clarity" in b
    assert "ending_completeness" in b

    # Verify duration bounds
    assert 10.0 <= top["duration"] <= 60.0


def test_quality_gates_and_statuses(highlights_env):
    engine = HighlightDiscoveryEngine(
        settings=highlights_env["settings"],
        db_path=highlights_env["storage"].db_file,
    )

    candidates = engine.discover_highlights(
        project_id=highlights_env["project_id"],
        media_asset_id=highlights_env["media_asset_id"],
    )

    statuses = {c["review_status"] for c in candidates}
    # Should include recommended or needs_review
    assert any(s in ("recommended", "needs_review") for s in statuses)

    for c in candidates:
        assert c["quality_score"] >= 0.0
        assert c["quality_score"] <= 100.0
        assert "gate_results" in c
        assert isinstance(c["gate_results"]["passed"], bool)


def test_candidate_api_lifecycle(highlights_env):
    app = create_app(settings_override=highlights_env["settings"])
    with TestClient(app) as client:
        pid = highlights_env["project_id"]
        aid = highlights_env["media_asset_id"]

        # 1. Trigger highlight discovery synchronously
        disc_resp = client.post(
            f"/api/v1/projects/{pid}/media/{aid}/highlights/discover",
            json={"run_synchronously": True, "min_duration": 10.0, "max_duration": 50.0},
        )
        assert disc_resp.status_code == 202
        candidates = disc_resp.json()
        assert len(candidates) >= 1
        cid = candidates[0]["id"]

        # 2. Project overview endpoint
        over_resp = client.get(f"/api/v1/projects/{pid}/highlights")
        assert over_resp.status_code == 200
        overview = over_resp.json()
        assert overview["total_candidates"] >= 1
        assert "recommended_count" in overview

        # 3. Candidate detail
        detail_resp = client.get(f"/api/v1/projects/{pid}/highlights/{cid}")
        assert detail_resp.status_code == 200
        det = detail_resp.json()
        assert det["id"] == cid
        assert det["scoring_version"] == SCORING_VERSION

        # 4. Patch candidate (boundary adjustment & rename)
        orig_start = det["start_time"]
        orig_end = det["end_time"]
        new_start = round(orig_start + 1.0, 2)
        new_end = round(orig_end - 1.0, 2)

        patch_resp = client.patch(
            f"/api/v1/projects/{pid}/highlights/{cid}",
            json={"title": "Custom User Title", "start_time": new_start, "end_time": new_end},
        )
        assert patch_resp.status_code == 200
        patched = patch_resp.json()
        assert patched["title"] == "Custom User Title"
        assert patched["is_user_modified"] is True
        assert patched["start_time"] == new_start
        assert patched["end_time"] == new_end
        assert patched["duration"] == round(new_end - new_start, 3)

        # 5. Boundary validation rejects invalid intervals
        bad_resp1 = client.patch(
            f"/api/v1/projects/{pid}/highlights/{cid}",
            json={"start_time": 50.0, "end_time": 40.0},  # start > end
        )
        assert bad_resp1.status_code == 400

        bad_resp2 = client.patch(
            f"/api/v1/projects/{pid}/highlights/{cid}",
            json={"start_time": 0.0, "end_time": 500.0},  # exceeds 120s duration
        )
        assert bad_resp2.status_code == 400

        # 6. Approve candidate
        appr_resp = client.post(f"/api/v1/projects/{pid}/highlights/{cid}/approve")
        assert appr_resp.status_code == 200
        assert appr_resp.json()["review_status"] == "approved"

        # 7. Reject candidate
        rej_resp = client.post(f"/api/v1/projects/{pid}/highlights/{cid}/reject?reason=Pacing%20too%20slow")
        assert rej_resp.status_code == 200
        assert rej_resp.json()["review_status"] == "rejected"
        assert "Pacing too slow" in rej_resp.json()["rejection_reason"]

        # 8. Restore candidate
        rest_resp = client.post(f"/api/v1/projects/{pid}/highlights/{cid}/restore")
        assert rest_resp.status_code == 200
        assert rest_resp.json()["review_status"] in ("recommended", "needs_review")

        # 9. Queue for render
        q_resp = client.post(f"/api/v1/projects/{pid}/highlights/{cid}/queue-render?queued=true")
        assert q_resp.status_code == 200
        assert q_resp.json()["queued_for_render"] is True

        # 10. Bulk review operations
        bulk_resp = client.post(
            f"/api/v1/projects/{pid}/highlights/bulk-review",
            json={"candidate_ids": [cid], "action": "approve"},
        )
        assert bulk_resp.status_code == 200
        assert bulk_resp.json()["updated_count"] == 1
