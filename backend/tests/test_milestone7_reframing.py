"""Tests for Milestone 7: Smart Reframing, Subject Tracking & Portrait Composition."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.models.reframing import CropKeyframe, DetectedSubject, SubjectTrack
from app.services.framing_engine import FramingEngine
from app.services.reframing_renderer import ReframingRenderer, build_crop_filter_expression
from app.services.reframing_service import ReframingService
from app.services.subject_tracker import SubjectTracker


@pytest.fixture
def reframing_env(tmp_path: Path):
    """Set up isolated storage, database, and synthetic test videos for reframing."""
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    settings = Settings(
        storage_root=storage_root,
        environment="testing",
        log_level="DEBUG",
        ffmpeg_threads=2,
    )

    run_migrations(
        db_path=layout.db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=layout.backups,
    )

    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg is not None, "FFmpeg must be installed and on PATH."

    # Generate a real 16:9 test video (640x360, 5 seconds)
    video_path = tmp_path / "test_reframing_clip.mp4"
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        str(video_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    now = "2026-11-12T12:00:00Z"
    proj_id = "proj_test_ref"
    asset_id = "med_test_ref"

    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, status, storage_subdir, created_at, updated_at)
            VALUES (?, 'Reframing Test Project', 'active', ?, ?, ?)
            """,
            (proj_id, proj_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external,
                media_type, file_size_bytes, duration_seconds, width, height, fps,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (?, ?, 'test_clip.mp4', ?, 1, 'video', ?, 5.0, 640, 360, 25.0, 'present', 'complete', ?, ?)
            """,
            (asset_id, proj_id, str(video_path), video_path.stat().st_size, now, now),
        )

    return {
        "settings": settings,
        "storage": layout,
        "project_id": proj_id,
        "media_asset_id": asset_id,
        "video_path": video_path,
    }


def test_portrait_crop_geometry_and_bounds():
    """Verify crop geometry across 16:9, 2.4:1, 4:3, and 1:1 aspect ratios."""
    engine_916 = FramingEngine(target_aspect_ratio="9:16", base_zoom=1.0)

    # 1. Standard 16:9 landscape source (1920x1080)
    w, h = engine_916.calculate_crop_dimensions(1920, 1080, zoom=1.0)
    assert h == 1080
    assert w == 606 or w == 608  # 1080 * 9/16 = 607.5 -> rounded to even
    assert w % 2 == 0 and h % 2 == 0

    # 2. Cinematic 2.4:1 source (1920x800)
    w_cin, h_cin = engine_916.calculate_crop_dimensions(1920, 800, zoom=1.0)
    assert h_cin == 800
    assert w_cin == 450
    assert w_cin % 2 == 0

    # 3. 4:3 source (1440x1080)
    w_43, h_43 = engine_916.calculate_crop_dimensions(1440, 1080, zoom=1.0)
    assert h_43 == 1080
    assert w_43 <= 1440

    # 4. Square 1:1 target aspect ratio
    engine_11 = FramingEngine(target_aspect_ratio="1:1", base_zoom=1.0)
    w_sq, h_sq = engine_11.calculate_crop_dimensions(1920, 1080, zoom=1.0)
    assert w_sq == 1080
    assert h_sq == 1080

    # 5. Boundary clamping guarantees crop never exceeds source dimensions
    # Subject at extreme left boundary (center_x = 50)
    cx, cy = engine_916.clamp_crop_rect(50.0, 540.0, w, h, 1920, 1080)
    assert cx == 0  # Clamped to left edge
    assert cy == 0
    assert cx + w <= 1920
    assert cy + h <= 1080

    # Subject at extreme right boundary (center_x = 1900)
    cx_r, cy_r = engine_916.clamp_crop_rect(1900.0, 540.0, w, h, 1920, 1080)
    assert cx_r == 1920 - w  # Clamped to right edge
    assert cx_r + w == 1920


def test_framing_strategies_single_two_person_and_group():
    """Verify single-subject, two-person joint framing, group framing, and fallback."""
    engine = FramingEngine(target_aspect_ratio="9:16", base_zoom=1.0)
    source_w = 1920
    source_h = 1080

    # A. Single subject at x=1200
    s1 = DetectedSubject(timestamp=1.0, box_x=1150, box_y=300, box_w=100, box_h=120, confidence=0.9, category="face")
    t1 = SubjectTrack(track_id="sub_1", category="face", detections=[s1])

    tx, ty, strat, count, warns = engine.select_framing_target([t1], timestamp=1.0, source_w=source_w, source_h=source_h)
    assert strat == "single_subject"
    assert count == 1
    assert tx == s1.center_x

    # B. Two people close together (joint framing)
    s2 = DetectedSubject(timestamp=1.0, box_x=1300, box_y=320, box_w=100, box_h=120, confidence=0.88, category="face")
    t2 = SubjectTrack(track_id="sub_2", category="face", detections=[s2])

    tx_two, _, strat_two, count_two, _ = engine.select_framing_target([t1, t2], timestamp=1.0, source_w=source_w, source_h=source_h)
    assert strat_two == "two_person"
    assert count_two == 2
    # Target center should be midpoint between both subjects
    expected_mid = (1150 + 1400) / 2.0
    assert abs(tx_two - expected_mid) <= 1.0

    # C. Group framing (3 subjects)
    s3 = DetectedSubject(timestamp=1.0, box_x=1000, box_y=350, box_w=90, box_h=110, confidence=0.85, category="face")
    t3 = SubjectTrack(track_id="sub_3", category="face", detections=[s3])

    tx_grp, _, strat_grp, count_grp, _ = engine.select_framing_target([t1, t2, t3], timestamp=1.0, source_w=source_w, source_h=source_h)
    assert strat_grp == "group"
    assert count_grp == 3

    # D. Fallback when no detections present
    tx_fb, ty_fb, strat_fb, count_fb, warns_fb = engine.select_framing_target([], timestamp=1.0, source_w=source_w, source_h=source_h)
    assert strat_fb == "fallback"
    assert count_fb == 0
    assert tx_fb == source_w / 2.0
    assert len(warns_fb) >= 1


def test_trajectory_smoothing_and_scene_cut_isolation():
    """Verify camera movement smoothing without jitter and strict scene cut isolation."""
    engine = FramingEngine(target_aspect_ratio="9:16", smoothing_window_seconds=0.8)
    source_w = 1920
    source_h = 1080
    cw, ch = engine.calculate_crop_dimensions(source_w, source_h)

    # Keyframes spanning across a scene cut at t=2.0s
    raw_kfs = [
        CropKeyframe(timestamp=0.0, crop_x=200, crop_y=0, crop_w=cw, crop_h=ch, target_center_x=500.0, target_center_y=540.0),
        CropKeyframe(timestamp=0.5, crop_x=250, crop_y=0, crop_w=cw, crop_h=ch, target_center_x=550.0, target_center_y=540.0),
        CropKeyframe(timestamp=1.0, crop_x=300, crop_y=0, crop_w=cw, crop_h=ch, target_center_x=600.0, target_center_y=540.0),
        # Scene cut happens here: subject abruptly appears on the far right (x=1500)
        CropKeyframe(timestamp=2.0, crop_x=1200, crop_y=0, crop_w=cw, crop_h=ch, target_center_x=1500.0, target_center_y=540.0, is_scene_boundary=True),
        CropKeyframe(timestamp=2.5, crop_x=1220, crop_y=0, crop_w=cw, crop_h=ch, target_center_x=1520.0, target_center_y=540.0),
    ]

    smoothed = engine.smooth_crop_trajectory(raw_kfs, source_w, source_h, scene_cut_timestamps=[2.0])
    assert len(smoothed) == len(raw_kfs)

    # Before cut (t=1.0s), camera should remain in scene 1 region
    kf_before = [k for k in smoothed if k.timestamp == 1.0][0]
    assert kf_before.crop_x < 500

    # At cut (t=2.0s), camera jumps cleanly without sliding across cut
    kf_cut = [k for k in smoothed if k.timestamp == 2.0][0]
    assert kf_cut.crop_x >= 1100
    assert kf_cut.is_scene_boundary is True


def test_preview_and_renderer_expression_parity():
    """Verify that build_crop_filter_expression matches interpolate_crop_at math."""
    kfs = [
        CropKeyframe(timestamp=0.0, crop_x=100, crop_y=0, crop_w=600, crop_h=1080),
        CropKeyframe(timestamp=2.0, crop_x=300, crop_y=0, crop_w=600, crop_h=1080),
        CropKeyframe(timestamp=4.0, crop_x=500, crop_y=0, crop_w=600, crop_h=1080),
    ]

    filter_expr, cw, ch = build_crop_filter_expression(
        keyframes=kfs,
        start_time=0.0,
        end_time=4.0,
        source_w=1920,
        source_h=1080,
        output_w=1080,
        output_h=1920,
    )

    assert "crop=" in filter_expr
    assert "scale=1080:1920" in filter_expr
    assert cw == 600
    assert ch == 1080

    # Test interpolation at t=1.0s (midpoint between 100 and 300 should be 200)
    interp = FramingEngine.interpolate_crop_at(kfs, timestamp=1.0)
    assert interp["crop_x"] == 200
    assert interp["crop_y"] == 0


def test_real_ffmpeg_reframing_render(reframing_env):
    """Render real vertical 9:16 MP4 video via FFmpeg and verify output properties."""
    renderer = ReframingRenderer(
        ffmpeg_path=reframing_env["settings"].ffmpeg_path,
        threads=2,
    )

    cw, ch = 202, 360  # 9:16 crop from 640x360 source
    kfs = [
        CropKeyframe(timestamp=0.0, crop_x=100, crop_y=0, crop_w=cw, crop_h=ch),
        CropKeyframe(timestamp=2.5, crop_x=220, crop_y=0, crop_w=cw, crop_h=ch),
        CropKeyframe(timestamp=5.0, crop_x=300, crop_y=0, crop_w=cw, crop_h=ch),
    ]

    out_video = reframing_env["storage"].shorts / "test_rendered_short.mp4"

    render_result = renderer.render_reframed_clip(
        source_media_path=reframing_env["video_path"],
        start_time=0.0,
        end_time=5.0,
        keyframes=kfs,
        output_path=out_video,
        source_w=640,
        source_h=360,
        output_w=720,
        output_h=1280,
    )

    assert Path(render_result["output_path"]).exists()
    assert render_result["file_size_bytes"] > 5000
    assert render_result["output_width"] == 720
    assert render_result["output_height"] == 1280

    # Verify rendered video properties with ffprobe
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name,pix_fmt",
        "-of", "json",
        str(out_video),
    ]
    p_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, text=True, check=True)
    probe_data = json.loads(p_res.stdout)
    vstream = probe_data["streams"][0]

    assert vstream["width"] == 720
    assert vstream["height"] == 1280
    assert vstream["codec_name"] == "h264"
    assert vstream["pix_fmt"] == "yuv420p"


def test_reframing_api_lifecycle_and_revisions(reframing_env):
    """End-to-end API lifecycle test: analyze, preview, manual overrides, revisions, restore, and render."""
    app = create_app(settings_override=reframing_env["settings"])

    with TestClient(app) as client:
        pid = reframing_env["project_id"]
        aid = reframing_env["media_asset_id"]

        # 1. Trigger reframing analysis
        analyze_resp = client.post(
            f"/api/v1/projects/{pid}/media/{aid}/reframing/analyze",
            json={
                "target_aspect_ratio": "9:16",
                "base_zoom": 1.0,
                "headroom_factor": 0.15,
                "smoothing_window": 0.8,
            },
        )
        assert analyze_resp.status_code == 201
        plan = analyze_resp.json()
        plan_id = plan["id"]
        assert plan["target_aspect_ratio"] == "9:16"
        assert len(plan["keyframes"]) >= 1
        assert plan["active_revision_id"] is not None

        # 2. Get plan detail
        plan_resp = client.get(f"/api/v1/projects/{pid}/reframing/{plan_id}")
        assert plan_resp.status_code == 200
        assert plan_resp.json()["id"] == plan_id

        # 3. Query preview at specific timestamp
        prev_resp = client.get(f"/api/v1/projects/{pid}/reframing/{plan_id}/preview?timestamp=1.5")
        assert prev_resp.status_code == 200
        prev_data = prev_resp.json()
        assert "crop_x" in prev_data
        assert "crop_y" in prev_data
        assert "crop_w" in prev_data
        assert "crop_h" in prev_data

        # 4. Save manual crop overrides creating Revision 2
        ov_resp = client.post(
            f"/api/v1/projects/{pid}/reframing/{plan_id}/overrides",
            json={
                "revision_label": "User Adjusted Center",
                "manual_overrides": [
                    {"timestamp": 1.5, "crop_x": 150, "crop_y": 0, "zoom": 1.1, "action": "override"}
                ],
            },
        )
        assert ov_resp.status_code == 200
        updated_plan = ov_resp.json()
        rev2_id = updated_plan["active_revision_id"]
        assert rev2_id != plan["active_revision_id"]

        # 5. List revisions
        revs_resp = client.get(f"/api/v1/projects/{pid}/reframing/{plan_id}/revisions")
        assert revs_resp.status_code == 200
        revisions = revs_resp.json()
        assert len(revisions) == 2
        rev1_id = revisions[0]["id"]
        assert revisions[0]["revision_number"] == 1
        assert revisions[1]["revision_number"] == 2

        # 6. Restore original Revision 1
        rest_resp = client.post(f"/api/v1/projects/{pid}/reframing/{plan_id}/revisions/{rev1_id}/restore")
        assert rest_resp.status_code == 200
        assert rest_resp.json()["active_revision_id"] == rev1_id

        # 7. Render active revision to real video
        render_resp = client.post(f"/api/v1/projects/{pid}/reframing/{plan_id}/render")
        assert render_resp.status_code == 200
        render_data = render_resp.json()
        assert "output_path" in render_data
        assert render_data["file_size_bytes"] > 1000

        # 8. Stream/download rendered video
        vid_resp = client.get(f"/api/v1/projects/{pid}/reframing/{plan_id}/video")
        assert vid_resp.status_code == 200
        assert vid_resp.headers["content-type"] == "video/mp4"
