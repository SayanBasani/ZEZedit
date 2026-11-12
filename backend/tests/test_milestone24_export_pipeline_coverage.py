"""Milestone 24 Regression Test Expansion: Export Pipeline, Captions & Video Rendering Edge Cases (ZEZ-099)."""

import json
import sqlite3
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.main import create_app
from app.models.export import (
    STANDARD_EXPORT_PRESETS,
    AudioConfig,
    CaptionConfig,
    RenderExportRequest,
)
from app.services.audio_pipeline import AudioPipeline
from app.services.caption_engine import CaptionEngine, hex_to_ass_color, format_ass_timestamp
from app.services.output_validator import OutputValidator


@pytest.fixture
def export_env(tmp_path: Path):
    """Provides isolated storage, fully migrated SQLite DB, test client, and sample video asset."""
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(
        app_name="ZezEditTestM24",
        environment="test",
        storage_root=storage_root,
        ffmpeg_threads=2,
    )

    app = create_app(settings)
    client = TestClient(app)

    # 4-second synthetic video with audio
    synth_video = layout.temp / "synth_m24.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=4:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        str(synth_video),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    proj_id = "proj_m24_exp"
    media_id = "med_m24_exp"
    cand_id = "cand_m24_exp"

    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            "INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES (?, 'M24 Proj', 'm24_p', datetime('now'), datetime('now'))",
            (proj_id,)
        )
        conn.execute(
            """INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external, file_size_bytes,
                duration_seconds, width, height, fps, video_codec, audio_codec, created_at, updated_at
            ) VALUES (?, ?, 'synth_m24.mp4', ?, 0, ?, 4.0, 640, 360, 25.0, 'h264', 'aac', datetime('now'), datetime('now'))""",
            (media_id, proj_id, str(synth_video), synth_video.stat().st_size)
        )
        conn.execute(
            """INSERT INTO analysis_runs (
                id, media_asset_id, project_id, status, created_at, updated_at
            ) VALUES ('ar_m24', ?, ?, 'completed', datetime('now'), datetime('now'))""",
            (media_id, proj_id)
        )
        conn.execute(
            """INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time, title, suggested_title, review_status, created_at, updated_at
            ) VALUES (?, ?, ?, 'ar_m24', 0.5, 3.5, 3.0, 0.5, 3.5, 'M24 Clip', 'M24 Clip', 'approved', datetime('now'), datetime('now'))""",
            (cand_id, proj_id, media_id)
        )
        conn.commit()

    return {
        "layout": layout,
        "settings": settings,
        "client": client,
        "project_id": proj_id,
        "media_id": media_id,
        "candidate_id": cand_id,
        "video_path": synth_video,
    }


def test_standard_presets_catalog_aspect_ratios():
    """Verify all STANDARD_EXPORT_PRESETS define valid resolutions, aspect ratios and FPS."""
    assert len(STANDARD_EXPORT_PRESETS) >= 3
    assert "shorts_reels_9_16" in STANDARD_EXPORT_PRESETS
    assert "landscape_16_9" in STANDARD_EXPORT_PRESETS
    assert "square_1_1" in STANDARD_EXPORT_PRESETS

    for pid, preset in STANDARD_EXPORT_PRESETS.items():
        assert preset.target_width > 0 and preset.target_height > 0
        assert preset.fps in (24.0, 25.0, 30.0, 60.0)
        assert preset.crf >= 15 and preset.crf <= 30
        assert preset.video_codec in ("libx264", "h264")


def test_hex_to_ass_color_conversion_variations():
    """Verify hex color parsing to ASS format (&HAABBGGRR) with alpha channels."""
    # Standard white: #FFFFFF -> &H00FFFFFF
    assert hex_to_ass_color("#FFFFFF") == "&H00FFFFFF"
    # Black: #000000 -> &H00000000
    assert hex_to_ass_color("#000000") == "&H00000000"
    # Red: #FF0000 -> Blue=00, Green=00, Red=FF -> &H000000FF
    assert hex_to_ass_color("#FF0000") == "&H000000FF"
    # Custom alpha integer 128 (0x80)
    assert hex_to_ass_color("#FFFFFF", alpha=128) == "&H80FFFFFF"
    # Fallback on malformed hex
    assert hex_to_ass_color("invalid") == "&H00FFFFFF"


def test_format_ass_timestamp_precision():
    """Verify ASS timestamp precision matches H:MM:SS.cs (centiseconds)."""
    assert format_ass_timestamp(0.0) == "0:00:00.00"
    assert format_ass_timestamp(1.25) == "0:00:01.25"
    assert format_ass_timestamp(65.5) == "0:01:05.50"
    assert format_ass_timestamp(3661.05) == "1:01:01.05"
    # Negative time clamped to zero
    assert format_ass_timestamp(-5.0) == "0:00:00.00"


def test_caption_engine_ass_file_generation_and_styling(export_env):
    """Verify CaptionEngine generates valid ASS headers, styles, and dialogue lines."""
    cfg = CaptionConfig(
        mode="standard",
        font_family="Arial",
        font_size=42,
        text_color="#FFD700",
        outline_color="#000000",
        outline_width=2.5,
        alignment=2,
        margin_v=50,
    )
    engine = CaptionEngine(cfg)
    output_ass = export_env["layout"].temp / "test_styled.ass"

    segments = [
        {"start_time": 0.5, "end_time": 1.5, "text": "Welcome to ZezEdit 2.0"},
        {"start_time": 1.6, "end_time": 3.0, "text": "High performance video production"},
    ]

    path = engine.generate_ass_file(
        transcript_segments=segments,
        clip_start_time=0.0,
        clip_end_time=3.5,
        output_file_path=output_ass,
        canvas_width=1080,
        canvas_height=1920,
    )
    assert path is not None
    assert Path(path).exists()
    content = Path(path).read_text(encoding="utf-8")

    assert "[Script Info]" in content
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "Style: Default" in content
    assert "Welcome to ZezEdit 2.0" in content


def test_caption_engine_empty_segments(export_env):
    """Verify CaptionEngine returns None when transcript segments are empty without crashing."""
    engine = CaptionEngine(CaptionConfig(mode="standard"))
    output_ass = export_env["layout"].temp / "test_empty.ass"
    path = engine.generate_ass_file(
        transcript_segments=[],
        clip_start_time=0.0,
        clip_end_time=3.0,
        output_file_path=output_ass,
    )
    assert path is None


def test_audio_pipeline_loudnorm_and_volume_filter_chains():
    """Verify AudioPipeline builds proper FFmpeg filter syntax for loudnorm and volume adjustment."""
    # Volume adjustment
    cfg_vol = AudioConfig(volume=1.5, normalize_loudness=False)
    p_vol = AudioPipeline(cfg_vol)
    f_vol, args_vol = p_vol.build_audio_filters(duration=3.0, has_source_audio=True)
    assert f_vol is not None
    assert "volume=1.50" in f_vol

    # Loudnorm filter
    cfg_norm = AudioConfig(volume=1.0, normalize_loudness=True)
    p_norm = AudioPipeline(cfg_norm)
    f_norm, args_norm = p_norm.build_audio_filters(duration=3.0, has_source_audio=True)
    assert f_norm is not None
    assert "loudnorm" in f_norm

    # Silent fallback when source audio is absent
    p_silent = AudioPipeline(AudioConfig())
    f_silent, args_silent = p_silent.build_audio_filters(duration=3.0, has_source_audio=False)
    assert any("anullsrc" in a for a in args_silent)


def test_output_validator_success_and_tampered_metadata(export_env):
    """Verify OutputValidator inspects real video file dimensions, duration, and codecs."""
    validator = OutputValidator()
    real_video = export_env["video_path"]

    details = validator.validate_export(
        file_path=real_video,
        expected_duration=4.0,
        expected_width=640,
        expected_height=360,
        expected_video_codec="h264",
        expected_audio_codec="aac",
    )
    assert details.is_valid is True
    assert details.width == 640
    assert details.height == 360
    assert details.duration >= 3.9

    # Non-existent file validation must fail
    fake_details = validator.validate_export(
        file_path=Path("C:/non_existent_video_path.mp4"),
        expected_duration=4.0,
        expected_width=1080,
        expected_height=1920,
    )
    assert fake_details.is_valid is False


def test_export_request_validation_models():
    """Verify RenderExportRequest model validation and field defaults."""
    req = RenderExportRequest(
        candidate_id="cand_1",
        preset_id="shorts_reels_9_16",
        title="Valid Export",
        crf=23,
    )
    assert req.candidate_id == "cand_1"
    assert req.preset_id == "shorts_reels_9_16"
    assert req.title == "Valid Export"
    assert req.crf == 23
    assert req.is_preview is False


def test_export_rest_api_list_presets(export_env):
    """Verify GET /api/v1/projects/{id}/exports/presets returns full preset catalog."""
    client = export_env["client"]
    proj_id = export_env["project_id"]

    res = client.get(f"/api/v1/projects/{proj_id}/exports/presets")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert any(p["preset_id"] == "shorts_reels_9_16" for p in data)


def test_export_render_submission_and_query(export_env):
    """Verify submitting an export render request registers a valid export record."""
    client = export_env["client"]
    proj_id = export_env["project_id"]
    cand_id = export_env["candidate_id"]

    res = client.post(
        f"/api/v1/projects/{proj_id}/exports/render",
        json={
            "candidate_id": cand_id,
            "preset_id": "shorts_reels_9_16",
            "title": "M24 Render Test",
            "is_preview": True,
        },
    )
    assert res.status_code == 200
    export_info = res.json()
    assert "export_id" in export_info
    export_id = export_info["export_id"]

    # Query export item details
    res_get = client.get(f"/api/v1/projects/{proj_id}/exports/{export_id}")
    assert res_get.status_code == 200
    details = res_get.json()
    assert details["id"] == export_id
    assert details["title"] == "M24 Render Test"


def test_export_delete_endpoint(export_env):
    """Verify deleting an export removes the database row and returns deleted boolean."""
    client = export_env["client"]
    proj_id = export_env["project_id"]
    export_id = f"exp_del_{export_env['candidate_id']}"

    with sqlite3.connect(export_env["layout"].db_file) as conn:
        conn.execute(
            """INSERT INTO exports (
                id, project_id, candidate_id, media_asset_id, title, output_filename,
                export_preset, status, created_at
            ) VALUES (?, ?, ?, ?, 'To Delete', 'to_delete.mp4', 'shorts_reels_9_16', 'completed', datetime('now'))""",
            (export_id, proj_id, export_env["candidate_id"], export_env["media_id"])
        )
        conn.commit()

    res_del = client.delete(f"/api/v1/projects/{proj_id}/exports/{export_id}")
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] is True

    # Subsequent GET returns 404
    res_check = client.get(f"/api/v1/projects/{proj_id}/exports/{export_id}")
    assert res_check.status_code == 404


def test_export_video_streaming_404_on_missing_file(export_env):
    """Verify video streaming endpoint returns 404 when file is absent on disk."""
    client = export_env["client"]
    proj_id = export_env["project_id"]
    exp_id = "exp_missing_file"

    with sqlite3.connect(export_env["layout"].db_file) as conn:
        conn.execute(
            """INSERT INTO exports (
                id, project_id, candidate_id, media_asset_id, title, output_filename, output_path,
                export_preset, status, created_at
            ) VALUES (?, ?, ?, ?, 'Missing Output', 'missing.mp4', 'non_existent_file.mp4', 'shorts_reels_9_16', 'completed', datetime('now'))""",
            (exp_id, proj_id, export_env["candidate_id"], export_env["media_id"])
        )
        conn.commit()

    res = client.get(f"/api/v1/projects/{proj_id}/exports/{exp_id}/video")
    assert res.status_code == 404
