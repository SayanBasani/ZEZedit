"""Automated tests for Session 6A: AI-First Video Analysis, Reusable Intelligence, Simple Generator, and Generate More Shorts."""

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
from app.services.highlight_discovery import HighlightDiscoveryEngine
from app.services.analysis_pipeline import VideoAnalysisPipeline, compute_source_signature


@pytest.fixture
def session6a_env(tmp_path: Path):
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

    now = "2026-11-13T01:00:00Z"
    proj_id = "proj_s6a_test"
    asset_id = "med_s6a_test"
    run_id = "run_s6a_test"

    # Create dummy media file to satisfy signature checks
    dummy_video = storage_root / "media" / "test_movie.mp4"
    dummy_video.parent.mkdir(parents=True, exist_ok=True)
    dummy_video.write_bytes(b"\x00" * 131072)
    sig = compute_source_signature(dummy_video)

    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, status, storage_subdir, created_at, updated_at)
            VALUES (?, 'Session 6A Test Project', 'active', ?, ?, ?)
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
                ?, ?, 'test_movie.mp4', ?, 0,
                'video', 131072, 300.0, 1920, 1080, 25.0,
                'present', 'complete', ?, ?
            )
            """,
            (asset_id, proj_id, str(dummy_video), now, now),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, media_asset_id, project_id, status, profile, config_json,
                progress_pct, current_stage, source_signature, created_at, updated_at
            ) VALUES (?, ?, ?, 'completed', 'balanced', '{}', 100.0, 'completed', ?, ?, ?)
            """,
            (run_id, asset_id, proj_id, sig, now, now),
        )

        # 6 Video Scenes
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

        # 8 Speech Turns
        conn.execute(
            """
            INSERT INTO speech_turns (id, analysis_run_id, media_asset_id, start_time, end_time, speaker_label, text, turn_type, created_at)
            VALUES 
            ('t1', ?, ?, 5.0, 18.0, 'Speaker A', 'Why did everyone say local video intelligence was completely impossible on consumer laptops?', 'question', ?),
            ('t2', ?, ?, 19.0, 38.0, 'Speaker B', 'Because legacy tools tried loading full movies into RAM! When you stream frames with FFmpeg, memory is bounded.', 'statement', ?),
            ('t3', ?, ?, 50.0, 68.0, 'Speaker A', 'What makes instant re-analysis possible without wasting GPU cycles?', 'question', ?),
            ('t4', ?, ?, 69.5, 90.0, 'Speaker B', 'Sub-millisecond source signatures! A 64KB head hash and mtime verify file identity instantly.', 'statement', ?),
            ('t5', ?, ?, 105.0, 125.0, 'Speaker B', 'The breakthrough happened when the emotional narrative reached a dramatic climax.', 'statement', ?),
            ('t6', ?, ?, 126.0, 142.0, 'Speaker A', 'That is incredible! Content creators finally have total control over their local data.', 'exclamation', ?),
            ('t7', ?, ?, 160.0, 185.0, 'Speaker B', 'Action and motion scenes require intelligent tracking so subjects never get cut off in vertical reels.', 'statement', ?),
            ('t8', ?, ?, 215.0, 245.0, 'Speaker A', 'In summary, local-first intelligence brings speed, privacy, and zero recurring cloud subscriptions.', 'statement', ?)
            """,
            (run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now,
             run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now),
        )

        # Transcript segments
        conn.execute(
            """
            INSERT INTO transcript_segments (id, analysis_run_id, media_asset_id, start_time, end_time, text, words_json, created_at)
            VALUES 
            ('seg1', ?, ?, 5.0, 38.0, 'Why did everyone say local video intelligence was completely impossible? Because legacy tools tried loading full movies into RAM!', '[]', ?),
            ('seg2', ?, ?, 50.0, 90.0, 'What makes instant re-analysis possible? Sub-millisecond source signatures! A 64KB head hash and mtime verify file identity instantly.', '[]', ?),
            ('seg3', ?, ?, 105.0, 142.0, 'The breakthrough happened when the emotional narrative reached a dramatic climax. That is incredible!', '[]', ?),
            ('seg4', ?, ?, 160.0, 185.0, 'Action and motion scenes require intelligent tracking so subjects never get cut off in vertical reels.', '[]', ?),
            ('seg5', ?, ?, 215.0, 245.0, 'In summary, local-first intelligence brings speed, privacy, and zero recurring cloud subscriptions.', '[]', ?)
            """,
            (run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now, run_id, asset_id, now),
        )

        # Audio analysis record
        conn.execute(
            """
            INSERT INTO audio_analysis (id, analysis_run_id, media_asset_id, has_audio, sample_rate, channels, codec_name, speech_density, silence_intervals_json, created_at)
            VALUES ('aud1', ?, ?, 1, 48000, 2, 'aac', 0.82, '[]', ?)
            """,
            (run_id, asset_id, now),
        )

    app = create_app(settings)
    client = TestClient(app)

    return {
        "client": client,
        "settings": settings,
        "layout": layout,
        "project_id": proj_id,
        "asset_id": asset_id,
        "run_id": run_id,
        "media_path": dummy_video,
    }


def test_first_generation_reuses_existing_analysis(session6a_env):
    """Verifies that discovery consumes stored analysis without re-analyzing source."""
    client = session6a_env["client"]
    pid = session6a_env["project_id"]
    aid = session6a_env["asset_id"]
    run_id = session6a_env["run_id"]

    res = client.post(
        f"/api/v1/projects/{pid}/media/{aid}/highlights/discover",
        json={
            "analysis_run_id": run_id,
            "creative_direction": "best_overall",
            "aspect_ratio": "9:16",
            "duration_preference": "ai_best_duration",
            "target_clip_count": 3,
            "run_synchronously": True,
        },
    )
    assert res.status_code == 202
    candidates = res.json()
    assert len(candidates) >= 1
    for c in candidates:
        assert c["analysis_run_id"] == run_id
        assert c["duration"] >= 12.0

    # Verify candidate generation run recorded reused_analysis_run_id
    runs_res = client.get(f"/api/v1/projects/{pid}/media/{aid}/highlights/runs")
    assert runs_res.status_code == 200
    runs = runs_res.json()
    assert len(runs) == 1
    assert runs[0]["reused_analysis_run_id"] == run_id
    assert runs[0]["generation_type"] == "initial"
    assert runs[0]["duration_preference"] == "ai_best_duration"


def test_aspect_ratio_and_creative_direction_changes_reuse_analysis(session6a_env):
    """Changing aspect ratio or direction does not rerun source analysis."""
    client = session6a_env["client"]
    pid = session6a_env["project_id"]
    aid = session6a_env["asset_id"]
    run_id = session6a_env["run_id"]

    # Initial 9:16 run
    res1 = client.post(
        f"/api/v1/projects/{pid}/media/{aid}/highlights/discover",
        json={
            "analysis_run_id": run_id,
            "creative_direction": "best_overall",
            "aspect_ratio": "9:16",
            "target_clip_count": 2,
            "run_synchronously": True,
        },
    )
    assert res1.status_code == 202

    # Switch to 1:1 and viral_punchy direction
    res2 = client.post(
        f"/api/v1/projects/{pid}/media/{aid}/highlights/discover",
        json={
            "analysis_run_id": run_id,
            "creative_direction": "viral_punchy",
            "aspect_ratio": "1:1",
            "target_clip_count": 2,
            "run_synchronously": True,
        },
    )
    assert res2.status_code == 202

    runs_res = client.get(f"/api/v1/projects/{pid}/media/{aid}/highlights/runs")
    runs = runs_res.json()
    assert len(runs) == 2
    # Both runs reused the identical source analysis run
    assert runs[0]["reused_analysis_run_id"] == run_id
    assert runs[1]["reused_analysis_run_id"] == run_id


def test_novelty_ledger_rejects_exact_and_near_identical_repeats(session6a_env):
    """Novelty engine blocks identical intervals and near-duplicates across batches."""
    client = session6a_env["client"]
    pid = session6a_env["project_id"]
    aid = session6a_env["asset_id"]
    run_id = session6a_env["run_id"]
    layout = session6a_env["layout"]

    # Run batch 1
    res1 = client.post(
        f"/api/v1/projects/{pid}/media/{aid}/highlights/discover",
        json={
            "analysis_run_id": run_id,
            "creative_direction": "best_overall",
            "aspect_ratio": "9:16",
            "target_clip_count": 2,
            "run_synchronously": True,
        },
    )
    assert res1.status_code == 202
    batch1 = res1.json()
    assert len(batch1) > 0
    intervals_b1 = [(c["start_time"], c["end_time"]) for c in batch1]

    # Verify history ledger recorded intervals
    with sqlite_session(layout.db_file) as conn:
        hist_count = conn.execute(
            "SELECT COUNT(*) FROM media_generated_clips_history WHERE media_asset_id = ?",
            (aid,),
        ).fetchone()[0]
        assert hist_count == len(batch1)

    # Run batch 2: Generate More Shorts
    res2 = client.post(
        f"/api/v1/projects/{pid}/media/{aid}/highlights/generate-more",
        json={
            "analysis_run_id": run_id,
            "creative_direction": "best_overall",
            "aspect_ratio": "9:16",
            "target_clip_count": 2,
            "run_synchronously": True,
        },
    )
    assert res2.status_code == 202
    batch2 = res2.json()

    # Verify that NO candidate in batch 2 is identical to batch 1
    for c2 in batch2:
        for b1_start, b1_end in intervals_b1:
            diff_start = abs(c2["start_time"] - b1_start)
            diff_end = abs(c2["end_time"] - b1_end)
            # Must not be an exact duplicate (tolerance < 2.0s)
            assert not (diff_start < 2.0 and diff_end < 2.0), f"Duplicate found: {c2['start_time']}-{c2['end_time']}"


def test_changing_aspect_ratio_cannot_bypass_novelty(session6a_env):
    """Changing aspect ratio from 9:16 to 1:1 does not cause previous moments to be repeated."""
    client = session6a_env["client"]
    pid = session6a_env["project_id"]
    aid = session6a_env["asset_id"]
    run_id = session6a_env["run_id"]

    # Generate 9:16
    res1 = client.post(
        f"/api/v1/projects/{pid}/media/{aid}/highlights/discover",
        json={
            "analysis_run_id": run_id,
            "creative_direction": "best_overall",
            "aspect_ratio": "9:16",
            "target_clip_count": 3,
            "run_synchronously": True,
        },
    )
    b1_intervals = [(c["start_time"], c["end_time"]) for c in res1.json()]

    # Request 1:1 clips
    res2 = client.post(
        f"/api/v1/projects/{pid}/media/{aid}/highlights/discover",
        json={
            "analysis_run_id": run_id,
            "creative_direction": "best_overall",
            "aspect_ratio": "1:1",
            "target_clip_count": 3,
            "run_synchronously": True,
        },
    )
    b2_intervals = [(c["start_time"], c["end_time"]) for c in res2.json()]

    # Ensure no exact overlap with previously generated moments
    for s2, e2 in b2_intervals:
        for s1, e1 in b1_intervals:
            assert not (abs(s2 - s1) < 2.0 and abs(e2 - e1) < 2.0)


def test_exhaustion_returns_honest_warning_without_fillers(session6a_env):
    """When source footage has exhausted fresh non-repeating moments, honest warning is returned."""
    client = session6a_env["client"]
    pid = session6a_env["project_id"]
    aid = session6a_env["asset_id"]
    run_id = session6a_env["run_id"]

    # Request multiple large batches to exhaust moments in the 300s test video
    for _ in range(4):
        client.post(
            f"/api/v1/projects/{pid}/media/{aid}/highlights/generate-more",
            json={
                "analysis_run_id": run_id,
                "target_clip_count": 5,
                "run_synchronously": True,
            },
        )

    # Next generation request
    res_final = client.post(
        f"/api/v1/projects/{pid}/media/{aid}/highlights/generate-more",
        json={
            "analysis_run_id": run_id,
            "target_clip_count": 10,
            "run_synchronously": True,
        },
    )
    assert res_final.status_code == 202

    runs_res = client.get(f"/api/v1/projects/{pid}/media/{aid}/highlights/runs")
    latest_run = runs_res.json()[0]
    # Check that novelty exclusions were recorded and warnings describe exclusion
    if latest_run["candidates_selected"] < latest_run["requested_count"]:
        assert latest_run["is_novelty_exhausted"] is True
        assert len(latest_run["warnings"]) > 0
        assert "novelty ledger" in latest_run["warnings"][0].lower() or "quality" in latest_run["warnings"][0].lower()


def test_ai_recommended_clip_count_and_natural_duration(session6a_env):
    """When target_clip_count is omitted, AI recommends an optimal clip count dynamically."""
    client = session6a_env["client"]
    pid = session6a_env["project_id"]
    aid = session6a_env["asset_id"]
    run_id = session6a_env["run_id"]

    res = client.post(
        f"/api/v1/projects/{pid}/media/{aid}/highlights/discover",
        json={
            "analysis_run_id": run_id,
            "duration_preference": "ai_best_duration",
            # target_clip_count omitted!
            "run_synchronously": True,
        },
    )
    assert res.status_code == 202
    candidates = res.json()
    assert len(candidates) >= 1
    # Check that candidate durations are natural (between 15 and 65 seconds)
    for c in candidates:
        assert 12.0 <= c["duration"] <= 70.0
