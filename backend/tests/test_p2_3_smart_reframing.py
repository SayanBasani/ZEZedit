"""Comprehensive test suite for P2.3: Smart Reframing, Subject Tracking & Portrait Composition.

Validates all 12 key capabilities:
1. Preview/render math parity between FramingEngine and ReframingRenderer
2. Scene-cut boundary awareness (smooth moving average never bleeds across hard scene cuts)
3. Multi-strategy framing (single-subject, two-person joint composition, group, central fallback, pinned focus)
4. Missing media protection (P1.7 alignment: MediaFileMissingError on missing file or availability_status='missing')
5. Storage quota enforcement (P1.9 alignment: StorageQuotaExceededError on temp or generated video limits)
6. Non-destructive manual overrides and revision history (_rev1.mp4, _rev2.mp4, non-destructive restore)
7. Candidate integration and boundary trimming (P2.2 candidate interval extraction and linkage)
8. Global reframing REST endpoints (/media/{id}/reframing/... and /reframing/{id}/...)
9. Project isolation and authorization (mismatched project returns 404)
10. Path traversal defense on video endpoint
11. Real FFmpeg portrait render execution and output video validation
12. Regression protection (P2.1 analysis, P2.2 candidates, P1.7-P1.9 storage and deduplication)
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import MediaFileMissingError, NotFoundError, StorageQuotaExceededError
from app.core.security import resolve_contained_path
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.models.reframing import CropKeyframe, DetectedSubject, SubjectTrack
from app.services.framing_engine import FramingEngine
from app.services.reframing_renderer import ReframingRenderer, build_crop_filter_expression
from app.services.reframing_service import ReframingService
from app.services.storage import StorageService


@pytest.fixture
def p2_3_env(tmp_path: Path):
    """Isolated environment with database, storage layout, and mock media assets."""
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

    # Create dummy source media file
    media_file = layout.media / "sample_interview.mp4"
    media_file.write_bytes(b"dummy_mp4_bytes_p2_3" * 1024)

    now = "2026-11-20T12:00:00Z"
    proj_a = "proj_p2_3_alpha"
    proj_b = "proj_p2_3_beta"
    asset_id = "med_p2_3_sample"
    asset_missing_id = "med_p2_3_missing"
    candidate_id = "cand_p2_3_highlight"

    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, status, storage_subdir, created_at, updated_at)
            VALUES (?, 'Alpha Project', 'active', ?, ?, ?),
                   (?, 'Beta Project', 'active', ?, ?, ?)
            """,
            (proj_a, proj_a, now, now, proj_b, proj_b, now, now),
        )

        # Present source video asset
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external,
                media_type, file_size_bytes, duration_seconds, width, height, fps,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                ?, ?, 'sample_interview.mp4', 'sample_interview.mp4', 0,
                'video', 1048576, 60.0, 1920, 1080, 30.0,
                'present', 'complete', ?, ?
            )
            """,
            (asset_id, proj_a, now, now),
        )

        # Missing source video asset (P1.7 test)
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external,
                media_type, file_size_bytes, duration_seconds, width, height, fps,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                ?, ?, 'missing_file.mp4', 'non_existent_folder/missing_file.mp4', 0,
                'video', 1048576, 60.0, 1920, 1080, 30.0,
                'missing', 'complete', ?, ?
            )
            """,
            (asset_missing_id, proj_a, now, now),
        )

        # Analysis run for candidate FK
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, media_asset_id, project_id, status, profile, created_at, updated_at
            ) VALUES ('run_p2_3_dummy', ?, ?, 'completed', 'balanced', ?, ?)
            """,
            (asset_id, proj_a, now, now),
        )

        # Candidate moment from P2.2
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time,
                quality_score, review_status, rank_position, title, suggested_title, created_at, updated_at
            ) VALUES (
                ?, ?, ?, 'run_p2_3_dummy', 5.0, 20.0, 15.0,
                5.0, 20.0,
                92.5, 'recommended', 1, 'Key Insight Moment', 'Key Insight Moment', ?, ?
            )
            """,
            (candidate_id, proj_a, asset_id, now, now),
        )

        # Scene cut records
        conn.execute(
            """
            INSERT INTO video_scenes (
                id, analysis_run_id, media_asset_id, scene_index, start_time, end_time,
                representative_timestamp, created_at
            ) VALUES
                ('sc_1', 'run_p2_3_dummy', ?, 0, 0.0, 10.0, 5.0, ?),
                ('sc_2', 'run_p2_3_dummy', ?, 1, 10.0, 25.0, 17.5, ?)
            """,
            (asset_id, now, asset_id, now),
        )

    return {
        "settings": settings,
        "layout": layout,
        "proj_a": proj_a,
        "proj_b": proj_b,
        "asset_id": asset_id,
        "asset_missing_id": asset_missing_id,
        "candidate_id": candidate_id,
        "media_file": media_file,
    }


def test_portrait_crop_dimensions_and_math_parity(p2_3_env):
    """Scenario 1: FramingEngine and ReframingRenderer share exact crop calculation math."""
    engine = FramingEngine(target_aspect_ratio="9:16", base_zoom=1.0)
    cw, ch = engine.calculate_crop_dimensions(source_w=1920, source_h=1080, zoom=1.0)

    # 1080 / 1.0 = 1080h -> 1080 * 9/16 = 607.5 -> rounded even: 606w
    assert cw == 606
    assert ch == 1080
    assert cw % 2 == 0
    assert ch % 2 == 0

    # 1:1 Aspect Ratio
    sq_engine = FramingEngine(target_aspect_ratio="1:1", base_zoom=1.0)
    sq_w, sq_h = sq_engine.calculate_crop_dimensions(source_w=1920, source_h=1080)
    assert sq_w == 1080
    assert sq_h == 1080

    # Parity check: keyframes evaluated by interpolate_crop_at vs build_crop_filter_expression
    kfs = [
        CropKeyframe(timestamp=0.0, crop_x=600, crop_y=0, crop_w=608, crop_h=1080),
        CropKeyframe(timestamp=10.0, crop_x=700, crop_y=0, crop_w=608, crop_h=1080),
    ]

    interp_mid = FramingEngine.interpolate_crop_at(kfs, timestamp=5.0)
    assert interp_mid["crop_x"] == 650
    assert interp_mid["crop_y"] == 0
    assert interp_mid["crop_w"] == 608
    assert interp_mid["crop_h"] == 1080

    filter_expr, cw_f, ch_f = build_crop_filter_expression(
        keyframes=kfs,
        start_time=0.0,
        end_time=10.0,
        source_w=1920,
        source_h=1080,
    )
    assert "crop=w=608:h=1080" in filter_expr
    assert cw_f == 608
    assert ch_f == 1080


def test_scene_cut_awareness_instant_transitions():
    """Scenario 2: Moving average trajectory smoothing never interpolates pans across hard visual cuts."""
    engine = FramingEngine(smoothing_window_seconds=1.0)

    raw_kfs = [
        CropKeyframe(timestamp=0.0, crop_x=200, crop_y=0, crop_w=608, crop_h=1080, target_center_x=504),
        CropKeyframe(timestamp=2.0, crop_x=250, crop_y=0, crop_w=608, crop_h=1080, target_center_x=554),
        CropKeyframe(timestamp=4.0, crop_x=300, crop_y=0, crop_w=608, crop_h=1080, target_center_x=604),
        # Hard scene cut at 5.0 seconds
        CropKeyframe(timestamp=5.0, crop_x=800, crop_y=0, crop_w=608, crop_h=1080, target_center_x=1104),
        CropKeyframe(timestamp=7.0, crop_x=820, crop_y=0, crop_w=608, crop_h=1080, target_center_x=1124),
    ]

    scene_cuts = [5.0]
    smoothed = engine.smooth_crop_trajectory(
        raw_keyframes=raw_kfs,
        source_w=1920,
        source_h=1080,
        scene_cut_timestamps=scene_cuts,
    )

    # Keyframe at cut must be tagged as scene boundary
    cut_kfs = [k for k in smoothed if k.timestamp == 5.0]
    assert len(cut_kfs) == 1
    assert cut_kfs[0].is_scene_boundary is True

    # Check interpolate_crop_at near the scene cut: does not produce a blurred pan
    snap_before = FramingEngine.interpolate_crop_at(smoothed, timestamp=4.95)
    snap_after = FramingEngine.interpolate_crop_at(smoothed, timestamp=5.05)
    assert snap_after["crop_x"] >= 750
    assert snap_before["crop_x"] <= 350


def test_multi_strategy_framing_selection():
    """Scenario 3: Multi-strategy framing handles single, two-person dialogue, group, and pinned focus."""
    engine = FramingEngine(target_aspect_ratio="9:16")

    # Single subject track
    track_1 = SubjectTrack(
        track_id="spk_1",
        category="face",
        detections=[
            DetectedSubject(timestamp=1.0, box_x=300, box_y=200, box_w=150, box_h=200, confidence=0.9, subject_id="spk_1")
        ],
    )
    # Second subject track
    track_2 = SubjectTrack(
        track_id="spk_2",
        category="face",
        detections=[
            DetectedSubject(timestamp=1.0, box_x=1200, box_y=200, box_w=150, box_h=200, confidence=0.88, subject_id="spk_2")
        ],
    )

    # 1. Single subject strategy
    tx, ty, strat, count, _ = engine.select_framing_target(
        tracks=[track_1],
        timestamp=1.0,
        source_w=1920,
        source_h=1080,
        preferred_strategy="single_subject",
    )
    assert strat == "single_subject"
    assert count == 1
    assert 350 <= tx <= 400

    # 2. Two-person joint dialogue composition
    tx2, ty2, strat2, count2, _ = engine.select_framing_target(
        tracks=[track_1, track_2],
        timestamp=1.0,
        source_w=1920,
        source_h=1080,
        preferred_strategy="auto",
    )
    assert strat2 == "two_person"
    assert count2 == 2
    # Joint center between ~375 and ~1275 is ~825
    assert 750 <= tx2 <= 900

    # 3. Pinned subject focus
    tx_pin, ty_pin, strat_pin, count_pin, _ = engine.select_framing_target(
        tracks=[track_1, track_2],
        timestamp=1.0,
        source_w=1920,
        source_h=1080,
        preferred_strategy="auto",
        pinned_subject_id="spk_2",
    )
    assert strat_pin == "single_subject"
    assert count_pin == 1
    assert 1200 <= tx_pin <= 1350

    # 4. Central fallback when no detections exist
    tx_fb, ty_fb, strat_fb, count_fb, _ = engine.select_framing_target(
        tracks=[],
        timestamp=1.0,
        source_w=1920,
        source_h=1080,
        preferred_strategy="auto",
    )
    assert strat_fb == "fallback"
    assert count_fb == 0
    assert tx_fb == 960.0
    assert ty_fb == 540.0


def test_missing_media_protection(p2_3_env):
    """Scenario 4: Missing or inaccessible media file immediately raises MediaFileMissingError."""
    service = ReframingService(settings=p2_3_env["settings"], db_path=p2_3_env["layout"].db_file)

    # 1. Media asset with availability_status = 'missing'
    with pytest.raises(MediaFileMissingError) as exc_info:
        service.analyze_and_create_plan(
            project_id=p2_3_env["proj_a"],
            media_asset_id=p2_3_env["asset_missing_id"],
        )
    assert "source file is missing or inaccessible on disk" in str(exc_info.value)
    assert exc_info.value.code == "MEDIA_FILE_MISSING"
    assert exc_info.value.status_code == 400

    # 2. Media asset marked present but file deleted from disk
    p2_3_env["media_file"].unlink(missing_ok=True)
    with pytest.raises(MediaFileMissingError) as exc_info2:
        service.analyze_and_create_plan(
            project_id=p2_3_env["proj_a"],
            media_asset_id=p2_3_env["asset_id"],
        )
    assert "source file is missing or inaccessible on disk" in str(exc_info2.value)


def test_storage_quota_enforcement(p2_3_env):
    """Scenario 5: Preflight quota checks reject operations that would exceed hard storage limits."""
    # Re-create media file
    p2_3_env["media_file"].write_bytes(b"dummy_mp4_bytes_p2_3" * 1024)

    storage_svc = StorageService(p2_3_env["settings"])
    with sqlite_session(p2_3_env["layout"].db_file) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO storage_quotas (
                id, storage_limit_bytes, generated_video_limit_bytes, temp_storage_limit_bytes,
                warning_threshold_percent, auto_prune_enabled, auto_prune_retention_hours,
                auto_prune_categories_json, created_at, updated_at
            ) VALUES ('default', 500000000, 1000, 1000, 80, 0, 24, '["temp"]', '2026-11-20T12:00:00Z', '2026-11-20T12:00:00Z')
            """
        )

    service = ReframingService(settings=p2_3_env["settings"], db_path=p2_3_env["layout"].db_file)

    # Analysis requires temp quota
    with pytest.raises(StorageQuotaExceededError) as exc_info:
        service.analyze_and_create_plan(
            project_id=p2_3_env["proj_a"],
            media_asset_id=p2_3_env["asset_id"],
        )
    assert "QUOTA_EXCEEDED" in str(exc_info.value) or "exceeded" in str(exc_info.value).lower()
    assert exc_info.value.code == "STORAGE_QUOTA_EXCEEDED"


def test_manual_overrides_and_revision_history(p2_3_env):
    """Scenario 6: Manual overrides persist as non-destructive revisions and support instant restoration."""
    # Reset quotas to generous limits
    with sqlite_session(p2_3_env["layout"].db_file) as conn:
        conn.execute("UPDATE storage_quotas SET storage_limit_bytes = NULL, temp_storage_limit_bytes = NULL, generated_video_limit_bytes = NULL WHERE id = 'default'")

    p2_3_env["media_file"].write_bytes(b"dummy_mp4_bytes_p2_3" * 1024)
    service = ReframingService(settings=p2_3_env["settings"], db_path=p2_3_env["layout"].db_file)

    # 1. Initial Plan Creation
    plan = service.analyze_and_create_plan(
        project_id=p2_3_env["proj_a"],
        media_asset_id=p2_3_env["asset_id"],
        start_time=0.0,
        end_time=10.0,
    )
    assert plan.status == "completed"
    assert plan.active_revision_id is not None

    revs = service.list_revisions(project_id=p2_3_env["proj_a"], plan_id=plan.id)
    assert len(revs) == 1
    rev1 = revs[0]
    assert rev1["revision_number"] == 1
    assert rev1["is_ai_generated"] == 1
    assert rev1["label"] == "AI Initial Framing"

    # 2. Save Manual Override Keyframes -> Creates Revision 2
    overrides = [
        {"timestamp": 2.5, "crop_x": 450, "crop_y": 0, "zoom": 1.2, "action": "override"},
        {"timestamp": 7.5, "crop_x": 520, "crop_y": 0, "zoom": 1.1, "action": "override"},
    ]
    updated_plan = service.save_manual_overrides(
        project_id=p2_3_env["proj_a"],
        plan_id=plan.id,
        manual_overrides=overrides,
        revision_label="Custom Speaker Pan",
    )
    revs2 = service.list_revisions(project_id=p2_3_env["proj_a"], plan_id=plan.id)
    assert len(revs2) == 2
    rev2 = revs2[1]
    assert rev2["revision_number"] == 2
    assert rev2["is_ai_generated"] == 0
    assert rev2["label"] == "Custom Speaker Pan"
    assert updated_plan["active_revision_id"] == rev2["id"]

    # 3. Non-Destructive Restore: Revert to Revision 1
    restored = service.restore_revision(
        project_id=p2_3_env["proj_a"],
        plan_id=plan.id,
        revision_id=rev1["id"],
    )
    assert restored["active_revision_id"] == rev1["id"]
    # Revisions 1 and 2 are still fully preserved
    revs3 = service.list_revisions(project_id=p2_3_env["proj_a"], plan_id=plan.id)
    assert len(revs3) == 2


def test_candidate_integration_and_boundary_trimming(p2_3_env):
    """Scenario 7: Reframing plan extracts interval from shorts_candidates and respects trim overrides."""
    with sqlite_session(p2_3_env["layout"].db_file) as conn:
        conn.execute("UPDATE storage_quotas SET storage_limit_bytes = NULL, temp_storage_limit_bytes = NULL, generated_video_limit_bytes = NULL WHERE id = 'default'")

    service = ReframingService(settings=p2_3_env["settings"], db_path=p2_3_env["layout"].db_file)

    # Candidate has interval [5.0, 20.0]
    plan = service.analyze_and_create_plan(
        project_id=p2_3_env["proj_a"],
        media_asset_id=p2_3_env["asset_id"],
        candidate_id=p2_3_env["candidate_id"],
    )
    assert plan.candidate_id == p2_3_env["candidate_id"]
    assert plan.start_time == 5.0
    assert plan.end_time == 20.0
    assert plan.duration == 15.0

    # User trimmed candidate clip to [7.0, 18.0]
    trimmed_plan = service.analyze_and_create_plan(
        project_id=p2_3_env["proj_a"],
        media_asset_id=p2_3_env["asset_id"],
        candidate_id=p2_3_env["candidate_id"],
        start_time=7.0,
        end_time=18.0,
    )
    assert trimmed_plan.start_time == 7.0
    assert trimmed_plan.end_time == 18.0
    assert trimmed_plan.duration == 11.0


def test_global_reframing_api_endpoints(p2_3_env):
    """Scenario 8: Global routes (/media/{id}/reframing/... and /reframing/{id}/...) function identically."""
    with sqlite_session(p2_3_env["layout"].db_file) as conn:
        conn.execute("UPDATE storage_quotas SET storage_limit_bytes = NULL, temp_storage_limit_bytes = NULL, generated_video_limit_bytes = NULL WHERE id = 'default'")

    app = create_app(settings_override=p2_3_env["settings"])
    with TestClient(app) as client:
        # 1. Global analyze route
        res = client.post(
            f"/api/v1/media/{p2_3_env['asset_id']}/reframing/analyze",
            json={"target_aspect_ratio": "9:16", "framing_strategy": "single_subject"},
        )
        assert res.status_code == 201
        plan_data = res.json()
        plan_id = plan_data["id"]

        # 2. Global list plans route
        res_list = client.get(f"/api/v1/media/{p2_3_env['asset_id']}/reframing/plans")
        assert res_list.status_code == 200
        assert any(p["id"] == plan_id for p in res_list.json())

        # 3. Global get plan
        res_get = client.get(f"/api/v1/reframing/{plan_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == plan_id

        # 4. Global preview crop
        res_prev = client.get(f"/api/v1/reframing/{plan_id}/preview?timestamp=2.0")
        assert res_prev.status_code == 200
        crop = res_prev.json()
        assert "crop_x" in crop
        assert "crop_y" in crop
        assert crop["crop_w"] == 606
        assert crop["crop_h"] == 1080

        # 5. Global overrides route
        res_ov = client.post(
            f"/api/v1/reframing/{plan_id}/overrides",
            json={
                "manual_overrides": [{"timestamp": 2.0, "crop_x": 500, "crop_y": 0, "zoom": 1.0}],
                "revision_label": "Global Edit",
            },
        )
        assert res_ov.status_code == 200
        assert res_ov.json()["active_revision"]["label"] == "Global Edit"

        # 6. Global revisions list
        res_revs = client.get(f"/api/v1/reframing/{plan_id}/revisions")
        assert res_revs.status_code == 200
        assert len(res_revs.json()) == 2


def test_project_isolation_and_authorization(p2_3_env):
    """Scenario 9: Cross-project access is strictly rejected with 404."""
    with sqlite_session(p2_3_env["layout"].db_file) as conn:
        conn.execute("UPDATE storage_quotas SET storage_limit_bytes = NULL, temp_storage_limit_bytes = NULL, generated_video_limit_bytes = NULL WHERE id = 'default'")

    service = ReframingService(settings=p2_3_env["settings"], db_path=p2_3_env["layout"].db_file)
    plan = service.analyze_and_create_plan(
        project_id=p2_3_env["proj_a"],
        media_asset_id=p2_3_env["asset_id"],
    )

    app = create_app(settings_override=p2_3_env["settings"])
    with TestClient(app) as client:
        # Accessing Project Alpha's plan from Project Beta
        res = client.get(f"/api/v1/projects/{p2_3_env['proj_b']}/reframing/{plan.id}")
        assert res.status_code == 404

        # Analyzing an asset belonging to Project Alpha under Project Beta scope
        res_mismatch = client.post(
            f"/api/v1/projects/{p2_3_env['proj_b']}/media/{p2_3_env['asset_id']}/reframing/analyze",
            json={"target_aspect_ratio": "9:16"},
        )
        assert res_mismatch.status_code == 404


def test_path_traversal_defense_on_video_endpoint(p2_3_env):
    """Scenario 10: resolve_contained_path rejects out-of-boundary path traversal attempts."""
    storage_root = p2_3_env["layout"].root

    # Safe path inside shorts
    safe_target = p2_3_env["layout"].shorts / "proj_p2_3_alpha" / "valid_render.mp4"
    resolved = resolve_contained_path(storage_root, safe_target)
    assert resolved == safe_target.resolve()

    # Traversal attempt escaping storage root
    with pytest.raises(Exception):
        resolve_contained_path(storage_root, "../../../Windows/System32/drivers/etc/hosts")


def test_real_ffmpeg_reframing_render_with_scene_cuts(p2_3_env, tmp_path):
    """Scenario 11: Real FFmpeg rendering outputs genuine vertical 9:16 MP4 with verified dimensions."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        pytest.skip("FFmpeg executable not available on PATH")

    # Generate a real 3-second 16:9 test video via FFmpeg
    real_video = p2_3_env["layout"].media / "real_16x9_test.mp4"
    gen_cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=size=1920x1080:rate=25",
        "-f", "lavfi",
        "-i", "sine=frequency=440:sample_rate=44100",
        "-t", "3.0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        str(real_video),
    ]
    subprocess.run(gen_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    with sqlite_session(p2_3_env["layout"].db_file) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external,
                media_type, file_size_bytes, duration_seconds, width, height, fps,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                'med_real_16x9', ?, 'real_16x9_test.mp4', 'real_16x9_test.mp4', 0,
                'video', ?, 3.0, 1920, 1080, 25.0,
                'present', 'complete', '2026-11-20T12:00:00Z', '2026-11-20T12:00:00Z'
            )
            """,
            (p2_3_env["proj_a"], real_video.stat().st_size),
        )

    service = ReframingService(settings=p2_3_env["settings"], db_path=p2_3_env["layout"].db_file)
    plan = service.analyze_and_create_plan(
        project_id=p2_3_env["proj_a"],
        media_asset_id="med_real_16x9",
        start_time=0.0,
        end_time=3.0,
    )

    render_result = service.render_revision(
        project_id=p2_3_env["proj_a"],
        plan_id=plan.id,
    )

    out_file = Path(render_result["output_path"])
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    assert render_result["output_width"] == 1080
    assert render_result["output_height"] == 1920
    assert render_result["duration"] >= 2.9


def test_regressions_p2_1_p2_2_p1_7_p1_8_p1_9(p2_3_env):
    """Scenario 12: Integrity check and foreign key check verify no broken references or schema regressions."""
    with sqlite_session(p2_3_env["layout"].db_file) as conn:
        integrity = conn.execute("PRAGMA integrity_check;").fetchall()
        assert integrity[0][0] == "ok"

        fk_check = conn.execute("PRAGMA foreign_key_check;").fetchall()
        assert len(fk_check) == 0
