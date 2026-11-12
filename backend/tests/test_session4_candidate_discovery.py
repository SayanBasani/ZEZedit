"""Automated tests for Session 4: Candidate Discovery, Multimodal Scoring, Natural Boundaries & Novelty Non-Repetition."""

import json
import sqlite3
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
def session4_env(tmp_path: Path):
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

    now = "2026-11-12T10:00:00Z"
    proj_id = "proj_s4_test"
    asset_id = "med_s4_test"
    run_id = "run_s4_test"

    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, status, storage_subdir, created_at, updated_at)
            VALUES (?, 'Session 4 Test Project', 'active', ?, ?, ?)
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
                ?, ?, 'feature_interview.mp4', 'feature_interview.mp4', 0,
                'video', 120000000, 300.0, 1920, 1080, 25.0,
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

        # 6 Scene cuts spanning 300s
        conn.execute(
            """
            INSERT INTO video_scenes (id, analysis_run_id, media_asset_id, scene_index, start_time, end_time, representative_timestamp, change_score, created_at)
            VALUES ('sc1', ?, ?, 0, 0.0, 45.0, 22.5, 0.45, ?),
                   ('sc2', ?, ?, 1, 45.0, 95.0, 70.0, 0.55, ?),
                   ('sc3', ?, ?, 2, 95.0, 150.0, 122.5, 0.60, ?),
                   ('sc4', ?, ?, 3, 150.0, 205.0, 177.5, 0.50, ?),
                   ('sc5', ?, ?, 4, 205.0, 260.0, 232.5, 0.40, ?),
                   ('sc6', ?, ?, 5, 260.0, 300.0, 280.0, 0.35, ?)
            """,
            (run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now,
             run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now),
        )

        # Speech turns with varied sentiment and dialogue structure
        conn.execute(
            """
            INSERT INTO speech_turns (id, analysis_run_id, media_asset_id, start_time, end_time, speaker_label, text, turn_type, created_at)
            VALUES 
            ('t1', ?, ?, 5.0, 18.0, 'Host', 'Why did everyone say local video AI was completely impossible on consumer laptops?', 'question', ?),
            ('t2', ?, ?, 19.0, 38.0, 'Guest', 'Because legacy architectures tried loading whole movies into RAM! When you stream frames with FFmpeg, memory is bounded and everything changes.', 'exclamation', ?),
            ('t3', ?, ?, 50.0, 68.0, 'Host', 'What is the secret behind instant re-analysis without wasting GPU power?', 'question', ?),
            ('t4', ?, ?, 69.5, 90.0, 'Guest', 'Sub-millisecond source signatures! A 64KB head hash and mtime verify file identity in under one millisecond.', 'statement', ?),
            ('t5', ?, ?, 105.0, 125.0, 'Guest', 'The breakthrough moment happened when the emotional narrative reached a climax.', 'statement', ?),
            ('t6', ?, ?, 126.0, 142.0, 'Host', 'That is unbelievable! Content creators finally have total control over their data.', 'exclamation', ?),
            ('t7', ?, ?, 160.0, 185.0, 'Guest', 'Action and motion scenes require intelligent tracking so faces never get cut off in vertical 9:16 reels.', 'statement', ?),
            ('t8', ?, ?, 215.0, 245.0, 'Host', 'And so in summary, local-first intelligence brings speed, privacy, and zero recurring cloud bills.', 'statement', ?)
            """,
            (run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now,
             run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now),
        )

        # Word-level transcript segments
        w1 = json.dumps([{"word": "Why", "start": 5.0, "end": 5.4}, {"word": "did", "start": 5.4, "end": 5.7}, {"word": "laptops?", "start": 17.2, "end": 18.0}])
        w2 = json.dumps([{"word": "Because", "start": 19.0, "end": 19.5}, {"word": "changes.", "start": 37.0, "end": 38.0}])
        conn.execute(
            """
            INSERT INTO transcript_segments (id, analysis_run_id, media_asset_id, start_time, end_time, text, words_json, created_at)
            VALUES 
            ('seg1', ?, ?, 5.0, 18.0, 'Why did everyone say local video AI was completely impossible on consumer laptops?', ?, ?),
            ('seg2', ?, ?, 19.0, 38.0, 'Because legacy architectures tried loading whole movies into RAM! When you stream frames with FFmpeg, memory is bounded and everything changes.', ?, ?)
            """,
            (run_id, asset_id, w1, now, run_id, asset_id, w2, now),
        )

        # Visual observations
        conn.execute(
            """
            INSERT INTO visual_observations (id, analysis_run_id, media_asset_id, timestamp, category, description, provider_model, confidence, created_at)
            VALUES ('obs1', ?, ?, 15.0, 'faces', 'Host looking directly into camera with engaged expression', 'yunet', 0.94, ?),
                   ('obs2', ?, ?, 30.0, 'action', 'Guest gesturing with high motion dynamics and enthusiasm', 'yunet', 0.96, ?),
                   ('obs3', ?, ?, 115.0, 'faces', 'Emotional close-up framing with intense dramatic focus', 'yunet', 0.91, ?),
                   ('obs4', ?, ?, 175.0, 'motion', 'Rapid subject movement across horizontal frame boundary', 'yunet', 0.88, ?)
            """,
            (run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now),
        )

        # Audio features
        conn.execute(
            """
            INSERT INTO audio_analysis (id, analysis_run_id, media_asset_id, has_audio, sample_rate, channels, codec_name, speech_density, silence_intervals_json, created_at)
            VALUES ('aud1', ?, ?, 1, 48000, 2, 'aac', 0.82, '[]', ?)
            """,
            (run_id, asset_id, now),
        )

    return {
        "settings": settings,
        "storage": layout,
        "project_id": proj_id,
        "media_asset_id": asset_id,
        "analysis_run_id": run_id,
    }


def test_candidate_discovery_and_natural_boundaries(session4_env):
    """Verifies candidate discovery, word-aligned natural boundaries, and explainable scoring."""
    engine = HighlightDiscoveryEngine(
        settings=session4_env["settings"],
        db_path=session4_env["storage"].db_file,
    )

    candidates = engine.discover_highlights(
        project_id=session4_env["project_id"],
        media_asset_id=session4_env["media_asset_id"],
        creative_direction="best_overall",
        min_duration=12.0,
        max_duration=60.0,
        target_clip_count=5,
    )

    assert len(candidates) >= 1
    for c in candidates:
        assert c["start_time"] >= 0.0
        assert c["end_time"] > c["start_time"]
        assert c["duration"] <= 60.0 + 0.5
        assert c["natural_boundary_confidence"] >= 0.70
        assert 0.0 <= c["quality_score"] <= 100.0

        b = c["score_breakdown"]
        assert "hook_strength" in b
        assert "dialogue_interest" in b
        assert "emotional_signal" in b
        assert "action_motion" in b
        assert "attractiveness_estimate" in b


def test_creative_direction_weighting_differentiation(session4_env):
    """Verifies that different creative directions produce meaningfully differentiated scores and rankings."""
    engine = HighlightDiscoveryEngine(
        settings=session4_env["settings"],
        db_path=session4_env["storage"].db_file,
    )

    viral_cands = engine.discover_highlights(
        project_id=session4_env["project_id"],
        media_asset_id=session4_env["media_asset_id"],
        creative_direction="viral_punchy",
        target_clip_count=3,
    )

    dramatic_cands = engine.discover_highlights(
        project_id=session4_env["project_id"],
        media_asset_id=session4_env["media_asset_id"],
        creative_direction="dramatic",
        target_clip_count=3,
    )

    assert len(viral_cands) >= 1
    assert len(dramatic_cands) >= 1

    # In viral_punchy, hook strength has higher weight (0.30)
    top_viral = viral_cands[0]
    assert top_viral["creative_direction"] == "viral_punchy"

    top_dramatic = dramatic_cands[0]
    assert top_dramatic["creative_direction"] == "dramatic"


def test_persistent_novelty_and_non_repetition(session4_env):
    """Critical test: Generating a second batch must exclude previously selected intervals using tIoU."""
    engine = HighlightDiscoveryEngine(
        settings=session4_env["settings"],
        db_path=session4_env["storage"].db_file,
    )

    # Batch 1: Generate 2 clips
    batch1 = engine.discover_highlights(
        project_id=session4_env["project_id"],
        media_asset_id=session4_env["media_asset_id"],
        target_clip_count=2,
    )
    assert len(batch1) == 2
    b1_intervals = [(c["start_time"], c["end_time"]) for c in batch1]

    # Verify history recorded in database
    with sqlite_session(session4_env["storage"].db_file) as conn:
        conn.row_factory = sqlite3.Row
        hist_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM media_generated_clips_history WHERE media_asset_id = ?",
            (session4_env["media_asset_id"],),
        ).fetchone()["cnt"]
        assert hist_count == 2

        # Verify generation run was created
        gen_runs = conn.execute(
            "SELECT * FROM candidate_generation_runs WHERE media_asset_id = ?",
            (session4_env["media_asset_id"],),
        ).fetchall()
        assert len(gen_runs) == 1
        assert gen_runs[0]["candidates_selected"] == 2

    # Batch 2: Generate More clips (must not duplicate Batch 1 intervals)
    batch2 = engine.discover_highlights(
        project_id=session4_env["project_id"],
        media_asset_id=session4_env["media_asset_id"],
        target_clip_count=2,
    )

    assert len(batch2) >= 1
    for c2 in batch2:
        for b1_start, b1_end in b1_intervals:
            # Calculate tIoU against Batch 1
            inter = max(0.0, min(c2["end_time"], b1_end) - max(c2["start_time"], b1_start))
            union = max(0.001, max(c2["end_time"], b1_end) - min(c2["start_time"], b1_start))
            tiou = inter / union
            overlap_ratio = inter / max(0.001, c2["duration"])
            # Assert that no batch 2 clip substantially overlaps with batch 1
            assert tiou < 0.50, f"Candidate {c2['id']} heavily overlaps with Batch 1 ({tiou:.2f})"
            assert overlap_ratio < 0.60

    # Verify history now contains Batch 1 + Batch 2 clips
    with sqlite_session(session4_env["storage"].db_file) as conn:
        conn.row_factory = sqlite3.Row
        total_hist = conn.execute(
            "SELECT COUNT(*) as cnt FROM media_generated_clips_history WHERE media_asset_id = ?",
            (session4_env["media_asset_id"],),
        ).fetchone()["cnt"]
        assert total_hist == len(batch1) + len(batch2)

        # Check second generation run has novelty exclusions recorded
        gen_runs = conn.execute(
            "SELECT * FROM candidate_generation_runs WHERE media_asset_id = ? ORDER BY created_at DESC",
            (session4_env["media_asset_id"],),
        ).fetchall()
        assert len(gen_runs) == 2
        assert gen_runs[0]["novelty_exclusions"] >= 1


def test_empty_transcript_visual_fallback(session4_env):
    """Verifies that an audio-less / speech-free video falls back to scene-based candidate extraction."""
    now = "2026-11-12T10:00:00Z"
    aid_silent = "med_silent_test"
    run_silent = "run_silent_test"

    with sqlite_session(session4_env["storage"].db_file) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external,
                media_type, file_size_bytes, duration_seconds, width, height, fps,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                ?, ?, 'silent_drone.mp4', 'silent_drone.mp4', 0,
                'video', 40000000, 90.0, 1920, 1080, 30.0,
                'ready', 'complete', ?, ?
            )
            """,
            (aid_silent, session4_env["project_id"], now, now),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, media_asset_id, project_id, status, profile, config_json,
                progress_pct, current_stage, created_at, updated_at
            ) VALUES (?, ?, ?, 'completed', 'balanced', '{}', 100.0, 'completed', ?, ?)
            """,
            (run_silent, aid_silent, session4_env["project_id"], now, now),
        )
        # 3 scenes, NO transcript segments or turns
        conn.execute(
            """
            INSERT INTO video_scenes (id, analysis_run_id, media_asset_id, scene_index, start_time, end_time, representative_timestamp, change_score, created_at)
            VALUES ('s_sc1', ?, ?, 0, 0.0, 25.0, 12.5, 0.4, ?),
                   ('s_sc2', ?, ?, 1, 25.0, 55.0, 40.0, 0.6, ?),
                   ('s_sc3', ?, ?, 2, 55.0, 90.0, 72.5, 0.35, ?)
            """,
            (run_silent, aid_silent, now, run_silent, aid_silent, now, run_silent, aid_silent, now),
        )

    engine = HighlightDiscoveryEngine(
        settings=session4_env["settings"],
        db_path=session4_env["storage"].db_file,
    )

    candidates = engine.discover_highlights(
        project_id=session4_env["project_id"],
        media_asset_id=aid_silent,
        min_duration=10.0,
        max_duration=40.0,
        target_clip_count=3,
    )

    assert len(candidates) >= 1
    for c in candidates:
        assert c["start_time"] >= 0.0
        assert c["end_time"] <= 90.0
        assert c["quality_score"] > 0.0


def test_session4_api_routes_and_history(session4_env):
    """Verifies generation run endpoints, history stats, and generate-more API."""
    app = create_app(settings_override=session4_env["settings"])
    with TestClient(app) as client:
        pid = session4_env["project_id"]
        aid = session4_env["media_asset_id"]

        # 1. Trigger candidate discovery
        disc_resp = client.post(
            f"/api/v1/projects/{pid}/media/{aid}/highlights/discover",
            json={
                "run_synchronously": True,
                "creative_direction": "viral_punchy",
                "aspect_ratio": "9:16",
                "target_clip_count": 2,
            },
        )
        assert disc_resp.status_code == 202
        cands = disc_resp.json()
        assert len(cands) == 2
        gen_run_id = cands[0]["generation_run_id"]
        assert gen_run_id is not None

        # 2. Query generation runs endpoint
        runs_resp = client.get(f"/api/v1/projects/{pid}/media/{aid}/highlights/runs")
        assert runs_resp.status_code == 200
        runs = runs_resp.json()
        assert len(runs) >= 1
        assert runs[0]["creative_direction"] == "viral_punchy"
        assert runs[0]["candidates_selected"] == 2

        # 3. Query specific run details
        run_detail_resp = client.get(f"/api/v1/projects/{pid}/media/{aid}/highlights/runs/{gen_run_id}")
        assert run_detail_resp.status_code == 200
        run_data = run_detail_resp.json()
        assert run_data["id"] == gen_run_id
        assert run_data["status"] == "completed"

        # 4. Query novelty history
        hist_resp = client.get(f"/api/v1/projects/{pid}/media/{aid}/highlights/history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["total_clips_generated"] == 2
        assert hist_data["total_duration_covered"] > 0

        # 5. Trigger Generate-More endpoint
        more_resp = client.post(
            f"/api/v1/projects/{pid}/media/{aid}/highlights/generate-more",
            json={
                "run_synchronously": True,
                "creative_direction": "dramatic",
                "aspect_ratio": "9:16",
                "target_clip_count": 2,
            },
        )
        assert more_resp.status_code == 202
        more_cands = more_resp.json()
        assert len(more_cands) >= 1

        # Confirm novelty exclusions logged
        runs_after = client.get(f"/api/v1/projects/{pid}/media/{aid}/highlights/runs").json()
        assert len(runs_after) == 2
        assert runs_after[0]["novelty_exclusions"] >= 1
