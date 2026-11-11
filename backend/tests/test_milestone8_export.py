"""Automated test suite for Milestone 8: Rendering Engine, Export Pipeline & Automatic Shorts Generation."""

import json
import os
import shutil
import sqlite3
import subprocess
import time
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
from app.services.export_service import ExportService
from app.services.output_validator import OutputValidator


@pytest.fixture
def m8_env(tmp_path: Path):
    """Fixture providing isolated storage, migrated database, test client, and synthetic video."""
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    # Run all migrations up to 0007
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(
        app_name="ZezEditTest",
        environment="test",
        storage_root=storage_root,
        ffmpeg_threads=2,
    )

    app = create_app(settings)
    client = TestClient(app)

    # Generate a lightweight 640x360 4-second synthetic test video with audio
    synth_video = layout.temp / "test_synth.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=4:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        str(synth_video),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {
        "settings": settings,
        "layout": layout,
        "client": client,
        "synth_video": synth_video,
    }


def test_export_presets_catalog():
    """Verify standard export profiles for YouTube Shorts (9:16), Landscape (16:9), and Square (1:1)."""
    assert "shorts_reels_9_16" in STANDARD_EXPORT_PRESETS
    assert "landscape_16_9" in STANDARD_EXPORT_PRESETS
    assert "square_1_1" in STANDARD_EXPORT_PRESETS

    shorts = STANDARD_EXPORT_PRESETS["shorts_reels_9_16"]
    assert shorts.target_width == 1080
    assert shorts.target_height == 1920
    assert shorts.target_aspect_ratio == "9:16"

    landscape = STANDARD_EXPORT_PRESETS["landscape_16_9"]
    assert landscape.target_width == 1920
    assert landscape.target_height == 1080
    assert landscape.target_aspect_ratio == "16:9"

    square = STANDARD_EXPORT_PRESETS["square_1_1"]
    assert square.target_width == 1080
    assert square.target_height == 1080
    assert square.target_aspect_ratio == "1:1"


def test_caption_engine_ass_generation(tmp_path: Path):
    """Verify ASS subtitle generation with word highlights, phrases, and sentence layouts."""
    # Test color conversion
    assert hex_to_ass_color("#FFFFFF") == "&H00FFFFFF"
    assert hex_to_ass_color("#FACC15") == "&H0015CCFA"
    assert format_ass_timestamp(75.42) == "0:01:15.42"

    segments = [
        {
            "id": "seg_1",
            "start_time": 1.0,
            "end_time": 3.5,
            "text": "Welcome to ZezEdit smart reframing.",
            "words": [
                {"word": "Welcome", "start": 1.0, "end": 1.4},
                {"word": "to", "start": 1.5, "end": 1.7},
                {"word": "ZezEdit", "start": 1.8, "end": 2.3},
                {"word": "smart", "start": 2.4, "end": 2.8},
                {"word": "reframing.", "start": 2.9, "end": 3.5},
            ],
        }
    ]

    out_ass = tmp_path / "test_captions.ass"

    # 1. Mode: word_highlight
    cfg = CaptionConfig(mode="word_highlight", font_size=28, max_words_per_line=3)
    engine = CaptionEngine(cfg)
    res_path = engine.generate_ass_file(
        transcript_segments=segments,
        clip_start_time=0.5,
        clip_end_time=4.0,
        output_file_path=out_ass,
        canvas_width=1080,
        canvas_height=1920,
    )
    assert res_path is not None
    assert res_path.exists()
    content = res_path.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "Dialogue:" in content
    assert "\\c&H" in content  # Contains color highlight override tags

    # 2. Mode: none
    cfg_none = CaptionConfig(mode="none")
    engine_none = CaptionEngine(cfg_none)
    assert engine_none.generate_ass_file(segments, 0.5, 4.0, out_ass) is None


def test_audio_pipeline_filters():
    """Verify audio filter configuration (volume, fades, normalization, and silent synthesis)."""
    # Audio with volume + fade in/out + normalization
    cfg = AudioConfig(
        volume=1.5,
        fade_in_seconds=0.5,
        fade_out_seconds=0.5,
        normalize_loudness=True,
    )
    pipeline = AudioPipeline(cfg)
    af_str, extra_args = pipeline.build_audio_filters(duration=5.0, has_source_audio=True)
    assert extra_args == []
    assert "volume=1.50" in af_str
    assert "afade=t=in:ss=0:d=0.50" in af_str
    assert "afade=t=out:st=4.50:d=0.50" in af_str
    assert "loudnorm=" in af_str
    assert "aresample=48000" in af_str

    # Silent audio fallback when source has no audio
    af_silent, silent_args = pipeline.build_audio_filters(duration=5.0, has_source_audio=False)
    assert len(silent_args) > 0
    assert "anullsrc=" in silent_args[3]
    assert "atrim=0:5.000" in af_silent


def test_output_validator_gate(m8_env):
    """Verify OutputValidator detects correct MP4 properties and catches corrupt/invalid outputs."""
    validator = OutputValidator()
    synth_video = m8_env["synth_video"]

    # Valid check against synthetic video (640x360, 4.0s)
    res = validator.validate_export(
        file_path=synth_video,
        expected_duration=4.0,
        expected_width=640,
        expected_height=360,
        expected_video_codec="h264",
        expected_audio_codec="aac",
    )
    assert res.is_valid is True
    assert res.playable is True
    assert res.width == 640
    assert res.height == 360
    assert len(res.errors) == 0

    # Invalid resolution expectation
    res_bad_res = validator.validate_export(
        file_path=synth_video,
        expected_duration=4.0,
        expected_width=1080,
        expected_height=1920,
    )
    assert res_bad_res.is_valid is False
    assert any("Resolution mismatch" in e for e in res_bad_res.errors)

    # Non-existent file
    res_missing = validator.validate_export(
        file_path=Path("D:/nonexistent_file.mp4"),
        expected_duration=4.0,
        expected_width=640,
        expected_height=360,
    )
    assert res_missing.is_valid is False
    assert any("does not exist" in e for e in res_missing.errors)


def test_full_export_render_and_validation(m8_env):
    """End-to-end test of 15-stage export render producing real vertical 9:16 video with captions and audio."""
    layout = m8_env["layout"]
    settings = m8_env["settings"]
    service = ExportService(settings, layout.db_file)
    synth_video = m8_env["synth_video"]

    # Create project, media, and candidate in database
    with sqlite3.connect(str(layout.db_file)) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p1', 'Export Test Project', 'p1_sub', datetime('now'), datetime('now'))")
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, is_external, file_size_bytes, duration_seconds, width, height, video_codec, audio_codec, created_at, updated_at)
            VALUES ('m1', 'p1', 'test_synth.mp4', ?, 1, ?, 4.0, 640, 360, 'h264', 'aac', datetime('now'), datetime('now'))
            """,
            (str(synth_video), synth_video.stat().st_size),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, media_asset_id, project_id, status, created_at, updated_at)
            VALUES ('a1', 'm1', 'p1', 'completed', datetime('now'), datetime('now'))
            """
        )
        # Insert transcript segment with word timestamps
        words_json = json.dumps([
            {"word": "Smart", "start": 1.0, "end": 1.4},
            {"word": "Shorts", "start": 1.5, "end": 1.9},
            {"word": "Render", "start": 2.0, "end": 2.5},
        ])
        conn.execute(
            """
            INSERT INTO transcript_segments (id, analysis_run_id, media_asset_id, start_time, end_time, text, words_json, created_at)
            VALUES ('ts1', 'a1', 'm1', 1.0, 2.5, 'Smart Shorts Render', ?, datetime('now'))
            """,
            (words_json,),
        )
        # Insert approved candidate clip (interval 0.5s to 3.5s = 3.0s duration)
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time, title, suggested_title, review_status, created_at, updated_at
            ) VALUES (
                'cand1', 'p1', 'm1', 'a1', 0.5, 3.5, 3.0, 0.5, 3.5, 'Test Candidate Clip', 'Test Candidate', 'approved', datetime('now'), datetime('now')
            )
            """
        )
        conn.commit()

    # Submit export request (Vertical 9:16 with word_highlight captions)
    req = RenderExportRequest(
        candidate_id="cand1",
        preset_id="shorts_reels_9_16",
        caption_config=CaptionConfig(mode="word_highlight", font_size=24),
        audio_config=AudioConfig(volume=1.0, fade_in_seconds=0.2, fade_out_seconds=0.2),
        is_preview=True,  # 480p fast preview for unit test speed
    )

    submit_res = service.submit_export_job(project_id="p1", request=req)
    assert submit_res["status"] == "queued"
    job_id = submit_res["job_id"]
    export_id = submit_res["export_id"]

    # Execute the 15-stage pipeline
    exec_res = service.execute_render_job(job_id)
    assert exec_res["status"] == "completed"
    assert exec_res["duration"] > 2.5

    out_file = Path(exec_res["output_path"])
    assert out_file.exists()
    assert out_file.stat().st_size > 0

    # Verify export record in database
    exp_record = service.get_export(project_id="p1", export_id=export_id)
    assert exp_record.status == "completed"
    assert exp_record.validation_status == "valid"
    assert exp_record.duration_seconds > 2.5
    assert exp_record.target_height == 480  # Preview height


def test_export_rest_api_lifecycle(m8_env):
    """Verify full HTTP REST API endpoints for presets, export list, details, and video streaming."""
    client = m8_env["client"]
    layout = m8_env["layout"]
    synth_video = m8_env["synth_video"]

    # Setup project and candidate in database
    with sqlite3.connect(str(layout.db_file)) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p_api', 'API Project', 'p_api_sub', datetime('now'), datetime('now'))")
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, is_external, file_size_bytes, duration_seconds, width, height, video_codec, audio_codec, created_at, updated_at)
            VALUES ('m_api', 'p_api', 'test_synth.mp4', ?, 1, ?, 4.0, 640, 360, 'h264', 'aac', datetime('now'), datetime('now'))
            """,
            (str(synth_video), synth_video.stat().st_size),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, media_asset_id, project_id, status, created_at, updated_at)
            VALUES ('a1', 'm_api', 'p_api', 'completed', datetime('now'), datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time, title, suggested_title, review_status, created_at, updated_at
            ) VALUES (
                'cand_api', 'p_api', 'm_api', 'a1', 0.5, 3.0, 2.5, 0.5, 3.0, 'API Candidate', 'API Candidate', 'approved', datetime('now'), datetime('now')
            )
            """
        )
        conn.commit()

    # 1. GET /presets
    res_presets = client.get("/api/v1/projects/p_api/exports/presets")
    assert res_presets.status_code == 200
    presets = res_presets.json()
    assert len(presets) >= 3

    # 2. POST /render with run_synchronously=True
    render_payload = {
        "candidate_id": "cand_api",
        "preset_id": "shorts_reels_9_16",
        "caption_config": {"mode": "none"},
        "is_preview": True,
    }
    res_render = client.post("/api/v1/projects/p_api/exports/render?run_synchronously=true", json=render_payload)
    assert res_render.status_code == 200
    data = res_render.json()
    assert data["status"] == "queued"
    assert "export_id" in data
    export_id = data["export_id"]

    # 3. GET /exports
    res_list = client.get("/api/v1/projects/p_api/exports")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["count"] >= 1
    assert any(e["id"] == export_id for e in list_data["items"])

    # 4. GET /exports/{id}
    res_detail = client.get(f"/api/v1/projects/p_api/exports/{export_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["status"] == "completed"
    assert detail["validation_status"] == "valid"

    # 5. GET /exports/{id}/video (HTTP 206 Partial Content byte-range streaming)
    res_video = client.get(f"/api/v1/projects/p_api/exports/{export_id}/video", headers={"Range": "bytes=0-1023"})
    assert res_video.status_code == 206
    assert "Content-Range" in res_video.headers
    assert len(res_video.content) == 1024


def test_export_render_cancellation(m8_env):
    """Verify that canceling an active export render terminates the underlying FFmpeg subprocess."""
    layout = m8_env["layout"]
    settings = m8_env["settings"]
    service = ExportService(settings, layout.db_file)
    synth_video = m8_env["synth_video"]

    # Generate a longer 15-second synthetic video to test cancellation mid-render
    long_video = layout.temp / "long_synth.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=15:size=1280x720:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=15",
        "-c:v", "libx264", "-c:a", "aac",
        str(long_video),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    with sqlite3.connect(str(layout.db_file)) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p_cancel', 'Cancel Project', 'p_cancel_sub', datetime('now'), datetime('now'))")
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, is_external, file_size_bytes, duration_seconds, width, height, video_codec, audio_codec, created_at, updated_at)
            VALUES ('m_cancel', 'p_cancel', 'long_synth.mp4', ?, 1, ?, 15.0, 1280, 720, 'h264', 'aac', datetime('now'), datetime('now'))
            """,
            (str(long_video), long_video.stat().st_size),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, media_asset_id, project_id, status, created_at, updated_at)
            VALUES ('a_cancel', 'm_cancel', 'p_cancel', 'completed', datetime('now'), datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time, title, suggested_title, review_status, created_at, updated_at
            ) VALUES (
                'cand_cancel', 'p_cancel', 'm_cancel', 'a_cancel', 0.0, 14.0, 14.0, 0.0, 14.0, 'Cancel Clip', 'Cancel', 'approved', datetime('now'), datetime('now')
            )
            """
        )
        conn.commit()

    req = RenderExportRequest(
        candidate_id="cand_cancel",
        preset_id="shorts_reels_9_16",
        caption_config=CaptionConfig(mode="none"),
        is_preview=False,
    )
    submit_res = service.submit_export_job(project_id="p_cancel", request=req)
    job_id = submit_res["job_id"]
    export_id = submit_res["export_id"]

    # Start render in a background thread
    import threading
    render_thread = threading.Thread(target=service.execute_render_job, args=(job_id,))
    render_thread.start()

    # Wait until FFmpeg is running
    time.sleep(0.8)
    job = service.jobs.get_job(job_id)
    assert job.status in {"running", "queued"}

    # Cancel the render
    cancel_res = service.cancel_export_render(project_id="p_cancel", export_id=export_id)
    assert cancel_res["status"] == "cancelled"

    render_thread.join(timeout=5.0)

    # Verify export record marked cancelled
    exp = service.get_export(project_id="p_cancel", export_id=export_id)
    assert exp.status == "cancelled"
    assert "Cancelled" in (exp.error_message or "")
