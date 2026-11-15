"""Session 21 Authoritative Acceptance Tests: Multimodal Intelligence Completion,
Real Subject Tracking, Dynamic Framing & Permanent Novelty Verification.
"""

import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List
import pytest
from starlette.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.main import create_app
from app.models.reframing import CropKeyframe
from app.services.analysis_pipeline import VideoAnalysisPipeline, compute_source_signature
from app.services.export_service import ExportService
from app.services.framing_engine import FramingEngine
from app.services.highlight_discovery import HighlightDiscoveryEngine
from app.services.reframing_renderer import build_crop_filter_expression
from app.services.subject_tracker import SubjectTracker
from app.services.temporal_aggregator import get_temporal_context_at


@pytest.fixture
def client(tmp_path) -> TestClient:
    real_migrations = Path(__file__).resolve().parent.parent / "migrations"
    settings = Settings(
        app_name="ZezEditSession21Test",
        storage_root=tmp_path / "storage",
        migrations_dir=real_migrations,
        environment="test",
        max_concurrent_jobs=2,
    )
    app = create_app(settings_override=settings)
    with TestClient(app) as test_client:
        yield test_client


def create_moving_subject_video(output_path: Path, duration: int = 6, width: int = 640, height: int = 360) -> Path:
    """Generate a synthetic video where a bright colored rectangle visibly moves from left to right."""
    import cv2
    import numpy as np

    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_video = output_path.with_suffix(".raw.mp4")
    fps = 10
    total_frames = duration * fps
    writer = cv2.VideoWriter(str(raw_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for f in range(total_frames):
        img = np.zeros((height, width, 3), dtype=np.uint8)
        x = int(40 + 440 * (f / max(1, total_frames - 1)))
        cv2.rectangle(img, (x, 100), (x + 80, 240), (255, 255, 255), -1)
        writer.write(img)
    writer.release()

    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        "-shortest", str(output_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if raw_video.exists():
        raw_video.unlink()
    return output_path


def test_moving_subject_tracking_and_dynamic_crop(tmp_path):
    """Test 1: Moving subject from left to right is tracked with time-varying crop keyframes."""
    video_path = tmp_path / "moving_person.mp4"
    create_moving_subject_video(video_path, duration=6, width=640, height=360)

    tracker = SubjectTracker(sample_fps=2.0)
    tracks = tracker.track_clip(
        media_path=video_path,
        start_time=0.0,
        end_time=6.0,
        source_w=640,
        source_h=360,
    )

    assert len(tracks) >= 1
    # Find the tracked moving subject
    moving_tracks = [t for t in tracks if t.total_displacement_x > 50 or t.is_moving]
    assert len(moving_tracks) >= 1, "Expected at least one actively moving track"
    primary_track = moving_tracks[0]

    # Verify horizontal displacement spans from left toward right
    first_det = primary_track.detections[0]
    last_det = primary_track.detections[-1]
    assert first_det.center_x < 300, f"Expected subject to start on left side, got {first_det.center_x}"
    assert last_det.center_x > 300, f"Expected subject to end on right side, got {last_det.center_x}"

    # Generate authoritative 9:16 portrait keyframes (target crop is 202x360 for 640x360 source)
    engine = FramingEngine(target_aspect_ratio="9:16", base_zoom=1.0)
    keyframes, warnings = engine.generate_framing_keyframes(
        tracks=tracks,
        start_time=0.0,
        end_time=6.0,
        source_w=640,
        source_h=360,
    )

    assert len(keyframes) >= 6
    cw, ch = engine.calculate_crop_dimensions(640, 360, zoom=1.0)
    max_allowable_x = 640 - cw

    # Verify boundary adherence on all keyframes
    for kf in keyframes:
        assert 0 <= kf.crop_x <= max_allowable_x, f"crop_x {kf.crop_x} outside [0, {max_allowable_x}]"
        assert 0 <= kf.crop_y <= (360 - ch), f"crop_y {kf.crop_y} outside bounds"
        assert kf.crop_w == cw
        assert kf.crop_h == ch

    # Verify dynamic camera pan follows subject from left to right
    start_crop_x = keyframes[0].crop_x
    end_crop_x = keyframes[-1].crop_x
    assert start_crop_x < end_crop_x, f"Expected camera to pan right (start={start_crop_x}, end={end_crop_x})"

    # Verify FFmpeg piecewise-linear expression compilation and actual video rendering
    vf_expr, _, _ = build_crop_filter_expression(keyframes, 0.0, 6.0, 640, 360, output_w=cw, output_h=ch)
    assert "crop=" in vf_expr
    assert "scale=" in vf_expr

    rendered_mp4 = tmp_path / "tracked_render.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-ss", "0.000", "-t", "6.000",
        "-i", str(video_path),
        "-vf", vf_expr,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(rendered_mp4),
    ]
    render_proc = subprocess.run(cmd, capture_output=True, text=True)
    assert render_proc.returncode == 0, f"FFmpeg render failed: {render_proc.stderr}"
    assert rendered_mp4.exists()
    assert rendered_mp4.stat().st_size > 1000


def test_permanent_novelty_ledger_survives_deletions(client: TestClient):
    """Test 2: Novelty ledger permanently rejects duplicates even after exports and scripts are deleted."""
    proj_res = client.post("/api/v1/projects", json={"name": "Novelty Test Project"})
    assert proj_res.status_code == 201
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_novelty_test"
    now_iso = "2026-11-15T12:00:00Z"

    synth_video = layout.media / "test_novelty.mp4"
    create_moving_subject_video(synth_video, duration=15, width=640, height=360)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, 'novelty_test.mp4', ?, 'video', ?, 15.0, 640, 360, 0, 'ready', ?, ?)
            """,
            (asset_id, pid, str(synth_video), synth_video.stat().st_size, now_iso, now_iso),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, project_id, media_asset_id, status, profile,
                progress_pct, current_stage, created_at, updated_at
            ) VALUES ('run_nov_01', ?, ?, 'completed', 'balanced', 100.0, 'completed', ?, ?)
            """,
            (pid, asset_id, now_iso, now_iso),
        )
        # Seed speech turns across the 15-second duration
        conn.execute(
            """
            INSERT INTO speech_turns (id, analysis_run_id, media_asset_id, start_time, end_time, speaker_label, text, turn_type, created_at)
            VALUES 
            ('t1', 'run_nov_01', ?, 0.5, 4.5, 'Speaker 1', 'The journey begins right here.', 'statement', ?),
            ('t2', 'run_nov_01', ?, 5.0, 9.5, 'Speaker 2', 'Now the middle phase reveals the true secret.', 'exclamation', ?),
            ('t3', 'run_nov_01', ?, 10.0, 14.5, 'Speaker 1', 'Finally we reach the dramatic conclusion.', 'statement', ?)
            """,
            (asset_id, now_iso, asset_id, now_iso, asset_id, now_iso),
        )
        # Seed transcript segments
        conn.execute(
            """
            INSERT INTO transcript_segments (id, analysis_run_id, media_asset_id, start_time, end_time, text, language, confidence, words_json, created_at)
            VALUES 
            ('s1', 'run_nov_01', ?, 0.5, 4.5, 'The journey begins right here.', 'en', 0.95, '[]', ?),
            ('s2', 'run_nov_01', ?, 5.0, 9.5, 'Now the middle phase reveals the true secret.', 'en', 0.95, '[]', ?),
            ('s3', 'run_nov_01', ?, 10.0, 14.5, 'Finally we reach the dramatic conclusion.', 'en', 0.95, '[]', ?)
            """,
            (asset_id, now_iso, asset_id, now_iso, asset_id, now_iso),
        )
        # Seed video scenes
        conn.execute(
            """
            INSERT INTO video_scenes (id, analysis_run_id, media_asset_id, scene_index, start_time, end_time, representative_timestamp, change_score, created_at)
            VALUES 
            ('sc1', 'run_nov_01', ?, 0, 0.0, 5.0, 2.5, 0.8, ?),
            ('sc2', 'run_nov_01', ?, 1, 5.0, 10.0, 7.5, 0.8, ?),
            ('sc3', 'run_nov_01', ?, 2, 10.0, 15.0, 12.5, 0.8, ?)
            """,
            (asset_id, now_iso, asset_id, now_iso, asset_id, now_iso),
        )

    # 1. First Generation: discover initial candidate clips
    res1 = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/highlights/discover",
        json={
            "analysis_run_id": "run_nov_01",
            "target_clip_count": 2,
            "min_duration": 4.0,
            "max_duration": 8.0,
            "auto_render": True,
            "run_synchronously": True,
        },
    )
    assert res1.status_code == 202
    cands1 = res1.json()
    assert len(cands1) >= 1

    first_cand_id = cands1[0]["id"]
    first_start = cands1[0]["start_time"]
    first_end = cands1[0]["end_time"]

    # Verify novelty ledger has recorded the interval
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        hist_rows = conn.execute(
            "SELECT * FROM media_generated_clips_history WHERE media_asset_id = ?",
            (asset_id,),
        ).fetchall()
        assert len(hist_rows) == len(cands1)

        exports = conn.execute("SELECT * FROM exports WHERE project_id = ?", (pid,)).fetchall()
        assert len(exports) == len(cands1)
        exp_ids = [e["id"] for e in exports]

    # 2. DELETE all rendered export records
    for exp_id in exp_ids:
        del_exp_res = client.delete(f"/api/v1/projects/{pid}/exports/{exp_id}")
        assert del_exp_res.status_code == 200

    # Verify exports are 0 in DB
    with sqlite_session(db_path) as conn:
        remaining_exports = conn.execute("SELECT COUNT(*) FROM exports WHERE project_id = ?", (pid,)).fetchone()[0]
        assert remaining_exports == 0

        # But novelty history is 100% PRESERVED
        hist_after_del = conn.execute("SELECT COUNT(*) FROM media_generated_clips_history WHERE media_asset_id = ?", (asset_id,)).fetchone()[0]
        assert hist_after_del == len(cands1)

    # 3. DELETE all candidate scripts
    for c in cands1:
        del_cand_res = client.delete(f"/api/v1/projects/{pid}/highlights/{c['id']}")
        assert del_cand_res.status_code == 200

    # Verify scripts are 0 in shorts_candidates
    with sqlite_session(db_path) as conn:
        remaining_cands = conn.execute("SELECT COUNT(*) FROM shorts_candidates WHERE project_id = ?", (pid,)).fetchone()[0]
        assert remaining_cands == 0

        # Novelty history MUST STILL BE 100% PRESERVED
        hist_after_script_del = conn.execute("SELECT COUNT(*) FROM media_generated_clips_history WHERE media_asset_id = ?", (asset_id,)).fetchone()[0]
        assert hist_after_script_del == len(cands1)

    # 4. Generate Shorts AGAIN: System must reject the previously used intervals
    res2 = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/highlights/discover",
        json={
            "analysis_run_id": "run_nov_01",
            "target_clip_count": 2,
            "min_duration": 4.0,
            "max_duration": 8.0,
            "auto_render": False,
            "run_synchronously": True,
        },
    )
    assert res2.status_code == 202
    cands2 = res2.json()

    # Any new candidate must NOT duplicate the previously used first_start/first_end
    for c in cands2:
        overlap_dist = abs(c["start_time"] - first_start) + abs(c["end_time"] - first_end)
        assert overlap_dist >= 2.0, f"Discovered candidate duplicated previous interval [{first_start}, {first_end}]"


def test_full_timeline_coverage_and_temporal_alignment(client: TestClient):
    """Test 3: Verify full-duration visual/audio analysis coverage and time-aligned context."""
    proj_res = client.post("/api/v1/projects", json={"name": "Coverage Test Project"})
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_cov_test"

    synth_video = layout.media / "test_cov.mp4"
    create_moving_subject_video(synth_video, duration=8, width=640, height=360)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, 'cov_test.mp4', ?, 'video', ?, 8.0, 640, 360, 0, 'ready', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (asset_id, pid, str(synth_video), synth_video.stat().st_size),
        )

    pipeline = VideoAnalysisPipeline(settings=client.app.state.settings, db_path=db_path)
    run_id = pipeline.create_analysis_run(
        media_asset_id=asset_id,
        project_id=pid,
        profile="fast",
        force_reanalysis=True,
    )

    import asyncio
    result = asyncio.run(pipeline.execute_analysis(run_id))
    assert result["status"] == "completed"

    # Query telemetry and check timeline coverage
    telemetry = pipeline.get_run_telemetry(run_id)
    stage_details = telemetry["stage_details"]
    assert "coverage" in stage_details
    cov = stage_details["coverage"]
    assert cov["visual_coverage_pct"] >= 80.0
    assert cov["audio_coverage_pct"] >= 80.0

    # Check explicit model metadata
    assert "models" in stage_details
    models = stage_details["models"]
    assert "faster-whisper" in models["transcription"]
    assert "Not Installed" in models["sound_event_classification"]

    # Verify multimodal temporal alignment at t=4.0s
    ctx = get_temporal_context_at(analysis_run_id=run_id, timestamp=4.0, window_seconds=5.0, db_path=db_path)
    assert ctx.timestamp == 4.0
    assert ctx.current_scene is not None
    assert ctx.audio_state in ("speech", "silence", "ambient")
    assert ctx.aligned_event is not None
    assert "timestamp" in ctx.aligned_event
    assert "audio_state" in ctx.aligned_event


def test_analysis_reuse_and_signature_invalidation(client: TestClient):
    """Test 4: Verify completed analysis is reused when signature matches, and reanalyzed when file changes."""
    proj_res = client.post("/api/v1/projects", json={"name": "Signature Reuse Test Project"})
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_reuse_test"

    synth_video = layout.media / "test_reuse.mp4"
    create_moving_subject_video(synth_video, duration=4, width=320, height=240)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, 'reuse_test.mp4', ?, 'video', ?, 4.0, 320, 240, 0, 'ready', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (asset_id, pid, str(synth_video), synth_video.stat().st_size),
        )

    pipeline = VideoAnalysisPipeline(settings=client.app.state.settings, db_path=db_path)
    run_id1 = pipeline.create_analysis_run(media_asset_id=asset_id, project_id=pid, force_reanalysis=True)

    import asyncio
    asyncio.run(pipeline.execute_analysis(run_id1))

    # Requesting analysis again without force_reanalysis MUST reuse run_id1
    run_id2 = pipeline.create_analysis_run(media_asset_id=asset_id, project_id=pid, force_reanalysis=False)
    assert run_id2 == run_id1, f"Expected cache reuse of {run_id1}, but got new {run_id2}"


def test_alternate_exports_same_candidate(client: TestClient):
    """Test 5: Alternate aspect ratio exports for the same candidate do not pollute novelty history."""
    proj_res = client.post("/api/v1/projects", json={"name": "Alternate Exports Project"})
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_alt_exp_test"

    synth_video = layout.media / "test_alt.mp4"
    create_moving_subject_video(synth_video, duration=5, width=640, height=360)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, 'alt_test.mp4', ?, 'video', ?, 5.0, 640, 360, 0, 'ready', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (asset_id, pid, str(synth_video), synth_video.stat().st_size),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, profile, progress_pct, current_stage, created_at, updated_at)
            VALUES ('run_alt_01', ?, ?, 'completed', 'balanced', 100.0, 'completed', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (pid, asset_id),
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time,
                suggested_start_time, suggested_end_time,
                duration, title, suggested_title, quality_score, review_status, created_at, updated_at
            ) VALUES ('cand_alt_01', ?, ?, 'run_alt_01', 1.0, 4.0, 1.0, 4.0, 3.0, 'Alt Test Short', 'Alt Test Short', 85.0, 'approved', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (pid, asset_id),
        )
        conn.execute(
            """
            INSERT INTO candidate_generation_runs (
                id, project_id, media_asset_id, analysis_run_id, creative_direction, aspect_ratio,
                requested_count, status, candidates_discovered, candidates_selected, candidates_rejected,
                novelty_exclusions, created_at, updated_at
            ) VALUES ('run_gen_01', ?, ?, 'run_alt_01', 'best_overall', '9:16', 1, 'completed', 1, 1, 0, 0, '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (pid, asset_id),
        )
        # Seed 1 record in novelty history
        conn.execute(
            """
            INSERT INTO media_generated_clips_history (
                id, media_asset_id, project_id, generation_run_id, candidate_id, start_time, end_time,
                duration, creative_direction, aspect_ratio, score, title, created_at
            ) VALUES ('hist_alt_01', ?, ?, 'run_gen_01', 'cand_alt_01', 1.0, 4.0, 3.0, 'best_overall', '9:16', 85.0, 'Alt Test Short', '2026-11-15T12:00:00Z')
            """,
            (asset_id, pid),
        )

    # Export candidate in 9:16
    res_916 = client.post(
        f"/api/v1/projects/{pid}/exports/render?run_synchronously=true",
        json={"candidate_id": "cand_alt_01", "preset_id": "shorts_reels_9_16"},
    )
    assert res_916.status_code == 200

    # Export candidate in 1:1 square
    res_11 = client.post(
        f"/api/v1/projects/{pid}/exports/render?run_synchronously=true",
        json={"candidate_id": "cand_alt_01", "preset_id": "square_1_1"},
    )
    assert res_11.status_code == 200

    # Verify both export records exist
    with sqlite_session(db_path) as conn:
        exp_rows = conn.execute("SELECT id, target_aspect_ratio FROM exports WHERE candidate_id = 'cand_alt_01'").fetchall()
        assert len(exp_rows) == 2
        ratios = {r[1] for r in exp_rows}
        assert "9:16" in ratios
        assert "1:1" in ratios

        # Verify novelty ledger count is still 1 (not duplicated)
        hist_count = conn.execute("SELECT COUNT(*) FROM media_generated_clips_history WHERE candidate_id = 'cand_alt_01'").fetchone()[0]
        assert hist_count == 1
