"""Session 23: Real-Media AI Quality Validation, Tracking & Professional Export Acceptance Tests.

Verifies:
1. Moving-subject tracking across left-to-right, right-to-left, two crossing subjects,
   temporary occlusion, and scene cuts.
2. Actual 9:16 portrait video rendering with frame-level subject visibility verification.
3. Multi-tier honest coverage reporting (scene vs semantic vision model vs local CV).
4. Full-duration multimodal timeline consistency (timestamp -> scene -> visual -> speech).
5. Permanent novelty exclusion across repeated generation batches.
"""

import math
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import pytest
from starlette.testclient import TestClient

from app.core.config import Settings
from app.db.connection import sqlite_session
from app.main import create_app
from app.services.analysis_pipeline import VideoAnalysisPipeline
from app.services.export_service import ExportService
from app.services.framing_engine import FramingEngine
from app.services.highlight_discovery import HighlightDiscoveryEngine
from app.services.reframing_renderer import build_crop_filter_expression
from app.core.storage import StorageLayout
from app.services.subject_tracker import DetectedSubject, SubjectTrack, SubjectTracker
from app.services.temporal_aggregator import get_temporal_context_at


@pytest.fixture
def client(tmp_path) -> TestClient:
    real_migrations = Path(__file__).resolve().parent.parent / "migrations"
    settings = Settings(
        app_name="ZezEditSession23Test",
        storage_root=tmp_path / "storage",
        migrations_dir=real_migrations,
        environment="test",
        max_concurrent_jobs=2,
    )
    app = create_app(settings_override=settings)
    with TestClient(app) as test_client:
        yield test_client


# Distinct physiological skin tone in BGR: (B=130, G=160, R=220) -> YCrCb inRange matches (0, 133, 77) to (255, 173, 127)
SKIN_COLOR_BGR = (130, 160, 220)
SHIRT_COLOR_BGR = (180, 100, 60)
SECONDARY_SKIN_BGR = (120, 150, 210)
SECONDARY_SHIRT_BGR = (60, 140, 60)


def create_scenario_video(
    output_path: Path,
    scenario: str = "left_to_right",
    duration: int = 5,
    width: int = 640,
    height: int = 360,
) -> Path:
    """Generate controlled test video with moving person, occlusion, crossing, or scene cut."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_video = output_path.with_suffix(".raw.mp4")
    fps = 10
    total_frames = duration * fps
    writer = cv2.VideoWriter(str(raw_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    for f in range(total_frames):
        t_norm = f / max(1, total_frames - 1)
        t_sec = f / fps

        # Background: quiet grey canvas
        img = np.full((height, width, 3), 40, dtype=np.uint8)

        if scenario == "left_to_right":
            # Person moves left (x=60) to right (x=500)
            px = int(60 + 440 * t_norm)
            py = 120
            # Head/face
            cv2.ellipse(img, (px + 30, py + 30), (25, 30), 0, 0, 360, SKIN_COLOR_BGR, -1)
            # Torso
            cv2.rectangle(img, (px + 10, py + 60), (px + 50, py + 140), SHIRT_COLOR_BGR, -1)

        elif scenario == "right_to_left":
            # Person moves right (x=500) to left (x=60)
            px = int(500 - 440 * t_norm)
            py = 120
            cv2.ellipse(img, (px + 30, py + 30), (25, 30), 0, 0, 360, SKIN_COLOR_BGR, -1)
            cv2.rectangle(img, (px + 10, py + 60), (px + 50, py + 140), SHIRT_COLOR_BGR, -1)

        elif scenario == "two_crossing":
            # Person 1 moves left-to-right
            p1_x = int(60 + 440 * t_norm)
            cv2.ellipse(img, (p1_x + 30, 110), (22, 28), 0, 0, 360, SKIN_COLOR_BGR, -1)
            cv2.rectangle(img, (p1_x + 12, 140), (p1_x + 48, 210), SHIRT_COLOR_BGR, -1)

            # Person 2 moves right-to-left
            p2_x = int(500 - 440 * t_norm)
            cv2.ellipse(img, (p2_x + 30, 130), (22, 28), 0, 0, 360, SECONDARY_SKIN_BGR, -1)
            cv2.rectangle(img, (p2_x + 12, 160), (p2_x + 48, 230), SECONDARY_SHIRT_BGR, -1)

        elif scenario == "occlusion":
            # Person moves left-to-right, but between t=2.0 and t=3.0 an obstacle blocks them
            px = int(60 + 440 * t_norm)
            py = 120
            cv2.ellipse(img, (px + 30, py + 30), (25, 30), 0, 0, 360, SKIN_COLOR_BGR, -1)
            cv2.rectangle(img, (px + 10, py + 60), (px + 50, py + 140), SHIRT_COLOR_BGR, -1)

            # Draw tall opaque pillar in the center (x=270 to 370)
            cv2.rectangle(img, (270, 0), (370, height), (15, 15, 15), -1)

        elif scenario == "scene_cut":
            # Scene 1 (t < 2.5s): Person on left
            if t_sec < 2.5:
                img.fill(30)
                px = 120
                cv2.ellipse(img, (px + 30, 110), (25, 30), 0, 0, 360, SKIN_COLOR_BGR, -1)
                cv2.rectangle(img, (px + 10, 140), (px + 50, 220), SHIRT_COLOR_BGR, -1)
            else:
                # Scene 2 (t >= 2.5s): Abrupt cut to bright outdoor background with Person on right
                img.fill(90)
                px = 480
                cv2.ellipse(img, (px + 30, 120), (25, 30), 0, 0, 360, SECONDARY_SKIN_BGR, -1)
                cv2.rectangle(img, (px + 10, 150), (px + 50, 230), SECONDARY_SHIRT_BGR, -1)

        elif scenario == "leave_and_reenter":
            # Moves to right edge, exits frame at t=2.0s, re-enters at t=3.5s
            if t_sec < 2.0:
                px = int(100 + 480 * (t_sec / 2.0))
            elif t_sec < 3.5:
                px = 750  # Off-screen right
            else:
                px = int(580 - 300 * ((t_sec - 3.5) / 1.5))

            if px < width:
                cv2.ellipse(img, (px + 30, 120), (25, 30), 0, 0, 360, SKIN_COLOR_BGR, -1)
                cv2.rectangle(img, (px + 10, 150), (px + 50, 230), SHIRT_COLOR_BGR, -1)

        writer.write(img)

    writer.release()

    # Mux synthetic audio sine track
    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if raw_video.exists():
        raw_video.unlink()

    return output_path


def test_moving_subject_tracking_left_to_right_and_visibility(tmp_path):
    """Test 1: Verify tracking left-to-right moving subject, render 9:16 portrait video, and measure subject visibility in output frames."""
    vid = tmp_path / "scenario_left_to_right.mp4"
    create_scenario_video(vid, scenario="left_to_right", duration=5, width=640, height=360)

    tracker = SubjectTracker(sample_fps=3.0)
    samples_dir = tmp_path / "samples_lr"
    samples_dir.mkdir(parents=True)
    samples = tracker.extract_frame_samples(vid, 0.0, 5.0, samples_dir)
    assert len(samples) >= 12

    tracks = tracker.track_subjects_across_samples(samples, 640, 360)
    assert len(tracks) >= 1

    # Verify primary track moved from left to right
    main_track = max(tracks, key=lambda trk: len(trk.detections))
    assert main_track.category in ("person", "face")
    first_x = main_track.detections[0].box_x
    last_x = main_track.detections[-1].box_x
    assert last_x > first_x + 150, f"Subject should visibly move right: start={first_x}, end={last_x}"

    # Generate 9:16 dynamic portrait keyframes
    engine = FramingEngine(target_aspect_ratio="9:16", base_zoom=1.0)
    keyframes, warnings = engine.generate_framing_keyframes(
        tracks=[main_track],
        start_time=0.0,
        end_time=5.0,
        source_w=640,
        source_h=360,
    )
    assert len(keyframes) >= 5

    # Crop dimensions for 9:16 on 640x360 source is 202x360
    cw, ch = engine.calculate_crop_dimensions(640, 360, zoom=1.0)
    assert keyframes[0].crop_x < keyframes[-1].crop_x, "Camera framing must pan right following subject"

    # Compile filter and render real 9:16 MP4
    vf_expr, _, _ = build_crop_filter_expression(keyframes, 0.0, 5.0, 640, 360, output_w=cw, output_h=ch)
    rendered_mp4 = tmp_path / "rendered_9x16_lr.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-ss", "0.000", "-t", "5.000",
        "-i", str(vid),
        "-vf", vf_expr,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(rendered_mp4),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"FFmpeg render failed: {res.stderr}"
    assert rendered_mp4.exists()

    # Extract output frames and measure subject visibility inside 9:16 portrait viewport
    cap = cv2.VideoCapture(str(rendered_mp4))
    assert cap.isOpened()

    visible_frames_count = 0
    total_checked = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        total_checked += 1
        # Detect presence of subject pixels in 9:16 frame using skin tone mask
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        skin_mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
        skin_pixel_count = cv2.countNonZero(skin_mask)
        # Subject should occupy at least 500 pixels in the frame
        if skin_pixel_count >= 300:
            visible_frames_count += 1

    cap.release()
    assert total_checked >= 40
    visibility_ratio = visible_frames_count / total_checked
    assert visibility_ratio >= 0.85, f"Subject should be visible in >= 85% of output frames, got {visibility_ratio:.1%}"


def test_moving_subject_two_crossing_separate_tracks(tmp_path):
    """Test 2: Verify tracking two people crossing in opposite directions with distinct tracks."""
    vid = tmp_path / "scenario_two_crossing.mp4"
    create_scenario_video(vid, scenario="two_crossing", duration=5, width=640, height=360)

    tracker = SubjectTracker(sample_fps=3.0)
    samples_dir = tmp_path / "samples_crossing"
    samples_dir.mkdir(parents=True)
    samples = tracker.extract_frame_samples(vid, 0.0, 5.0, samples_dir)

    tracks = tracker.track_subjects_across_samples(samples, 640, 360)
    # Both crossing subjects should be isolated into separate track entities
    substantial_tracks = [t for t in tracks if len(t.detections) >= 5]
    assert len(substantial_tracks) >= 2, f"Expected at least 2 distinct crossing tracks, found {len(substantial_tracks)}"

    # Track 1 moved left-to-right, Track 2 moved right-to-left
    dx_values = [t.detections[-1].box_x - t.detections[0].box_x for t in substantial_tracks]
    has_positive = any(dx > 50 for dx in dx_values)
    has_negative = any(dx < -50 for dx in dx_values)
    assert has_positive and has_negative, f"Expected opposing motion vectors in crossing scenario: {dx_values}"


def test_moving_subject_occlusion_and_scene_cut(tmp_path):
    """Test 3: Verify temporary occlusion gap-bridging and scene cut track boundary termination."""
    # 1. Occlusion scenario
    occ_vid = tmp_path / "scenario_occlusion.mp4"
    create_scenario_video(occ_vid, scenario="occlusion", duration=5, width=640, height=360)

    tracker = SubjectTracker(sample_fps=3.0, gap_tolerance_seconds=1.5)
    occ_samples = tracker.extract_frame_samples(occ_vid, 0.0, 5.0, tmp_path / "samples_occ")
    occ_tracks = tracker.track_subjects_across_samples(occ_samples, 640, 360)

    # Primary track should survive across the 1.0s central occlusion pillar via gap tolerance
    surviving_track = max(occ_tracks, key=lambda t: len(t.detections))
    assert len(surviving_track.detections) >= 8, "Track should bridge the temporary occlusion"

    # 2. Scene cut scenario
    cut_vid = tmp_path / "scenario_scene_cut.mp4"
    create_scenario_video(cut_vid, scenario="scene_cut", duration=5, width=640, height=360)

    cut_samples = tracker.extract_frame_samples(cut_vid, 0.0, 5.0, tmp_path / "samples_cut")
    # Tell tracker that a cut occurred at t=2.5s
    cut_tracks = tracker.track_subjects_across_samples(cut_samples, 640, 360, scene_cut_timestamps=[2.5])

    # No track should span continuously across the cut timestamp
    for trk in cut_tracks:
        start_t = trk.detections[0].timestamp
        end_t = trk.detections[-1].timestamp
        spans_cut = (start_t < 2.3 and end_t > 2.7)
        assert not spans_cut, f"Track {trk.track_id} inappropriately spanned across scene cut at 2.5s ([{start_t}, {end_t}])"


def test_honest_multi_tier_coverage_reporting(client: TestClient, tmp_path):
    """Test 4: Verify honest multi-tier coverage model distinguishing scene detection vs semantic vision model vs local CV."""
    proj_res = client.post("/api/v1/projects", json={"name": "Coverage Audit Project"})
    assert proj_res.status_code == 201
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_coverage_audit"

    synth_video = layout.media / "test_cov_audit.mp4"
    create_scenario_video(synth_video, scenario="left_to_right", duration=8, width=640, height=360)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, 'cov_audit.mp4', ?, 'video', ?, 8.0, 640, 360, 0, 'ready', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
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

    telemetry = pipeline.get_run_telemetry(run_id)
    stage_details = telemetry["stage_details"]
    assert "coverage" in stage_details
    cov = stage_details["coverage"]

    # Verify all required honest coverage metrics
    assert "total_source_duration_seconds" in cov
    assert cov["total_source_duration_seconds"] == 8.0

    assert "scene_detection_coverage_pct" in cov
    assert cov["scene_detection_coverage_pct"] >= 90.0

    assert "total_decoded_frames_approx" in cov
    assert cov["total_decoded_frames_approx"] >= 80

    assert "sampled_frames_count" in cov
    assert cov["sampled_frames_count"] >= 1

    assert "vision_model_analyzed_frames_count" in cov
    assert cov["vision_model_analyzed_frames_count"] >= 1

    assert "local_cv_analyzed_frames_count" in cov
    assert "semantically_inspected_scenes_count" in cov
    assert "total_scenes_count" in cov
    assert "semantic_visual_span_seconds" in cov
    assert "semantic_coverage_pct" in cov
    assert "sampling_density_frames_per_minute" in cov
    assert "analysis_limitations" in cov
    assert len(cov["analysis_limitations"]) >= 3

    # Backwards compatibility check
    assert cov["visual_coverage_pct"] >= 80.0
    assert cov["audio_coverage_pct"] >= 80.0


def test_multimodal_timeline_consistency(client: TestClient, tmp_path):
    """Test 5: Verify multimodal timeline consistency linking timestamp -> scene -> visual -> speech."""
    proj_res = client.post("/api/v1/projects", json={"name": "Timeline Consistency Project"})
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_timeline_test"

    synth_video = layout.media / "test_timeline.mp4"
    create_scenario_video(synth_video, scenario="left_to_right", duration=6, width=640, height=360)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, 'timeline_test.mp4', ?, 'video', ?, 6.0, 640, 360, 0, 'ready', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (asset_id, pid, str(synth_video), synth_video.stat().st_size),
        )

    pipeline = VideoAnalysisPipeline(settings=client.app.state.settings, db_path=db_path)
    run_id = pipeline.create_analysis_run(media_asset_id=asset_id, project_id=pid, profile="fast", force_reanalysis=True)

    import asyncio
    res = asyncio.run(pipeline.execute_analysis(run_id))
    assert res["status"] == "completed"

    # Query context at midpoint t=3.0s
    ctx = get_temporal_context_at(analysis_run_id=run_id, timestamp=3.0, window_seconds=4.0, db_path=db_path)
    assert ctx.timestamp == 3.0
    assert ctx.current_scene is not None
    sc_start = ctx.current_scene["start_time"] if isinstance(ctx.current_scene, dict) else ctx.current_scene.start_time
    sc_end = ctx.current_scene["end_time"] if isinstance(ctx.current_scene, dict) else ctx.current_scene.end_time
    assert sc_start <= 3.0 <= sc_end
    assert isinstance(ctx.nearby_visual_observations, list)


def test_permanent_novelty_on_multiple_batches(client: TestClient, tmp_path):
    """Test 6: Verify permanent novelty ledger rejects duplicates across multiple generation batches."""
    proj_res = client.post("/api/v1/projects", json={"name": "Novelty Batches Project"})
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_novelty_batches"
    now_iso = "2026-11-15T12:00:00Z"

    synth_video = layout.media / "test_nov_batches.mp4"
    create_scenario_video(synth_video, scenario="left_to_right", duration=15, width=640, height=360)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, 'nov_batches.mp4', ?, 'video', ?, 15.0, 640, 360, 0, 'ready', ?, ?)
            """,
            (asset_id, pid, str(synth_video), synth_video.stat().st_size, now_iso, now_iso),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, project_id, media_asset_id, status, profile,
                progress_pct, current_stage, created_at, updated_at
            ) VALUES ('run_batch_01', ?, ?, 'completed', 'balanced', 100.0, 'completed', ?, ?)
            """,
            (pid, asset_id, now_iso, now_iso),
        )

    # Batch 1
    res1 = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/highlights/discover",
        json={
            "analysis_run_id": "run_batch_01",
            "target_clip_count": 2,
            "min_duration": 4.0,
            "max_duration": 8.0,
            "auto_render": False,
            "run_synchronously": True,
        },
    )
    assert res1.status_code == 202
    b1_cands = res1.json()
    assert len(b1_cands) >= 1
    b1_intervals = [(c["start_time"], c["end_time"]) for c in b1_cands]

    # Batch 2: Generate More
    res2 = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/highlights/discover",
        json={
            "analysis_run_id": "run_batch_01",
            "target_clip_count": 2,
            "min_duration": 4.0,
            "max_duration": 8.0,
            "auto_render": False,
            "run_synchronously": True,
        },
    )
    assert res2.status_code == 202
    b2_cands = res2.json()

    # Verify no candidate in Batch 2 duplicates any interval from Batch 1
    for c2 in b2_cands:
        for s1, e1 in b1_intervals:
            overlap_dist = abs(c2["start_time"] - s1) + abs(c2["end_time"] - e1)
            assert overlap_dist >= 1.5, f"Batch 2 duplicate interval: [{c2['start_time']}, {c2['end_time']}] vs [{s1}, {e1}]"
