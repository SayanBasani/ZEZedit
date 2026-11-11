"""Tests for Milestone 5: Video Analysis Engine, Transcription & Visual Understanding."""

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
from app.services.audio_extractor import extract_audio_16k_mono
from app.services.frame_sampler import sample_analysis_frames
from app.services.scene_detector import DetectedScene, detect_scenes_ffmpeg
from app.services.speech_segmentation import (
    NormalizedSegment,
    segment_dialogue_turns,
)
from app.services.temporal_aggregator import get_temporal_context_at
from app.services.visual_understanding import OllamaVisionAnalyzer


@pytest.fixture
def analysis_env(tmp_path: Path):
    """Set up isolated storage, database, and synthetic test media files."""
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
    assert ffmpeg is not None, "FFmpeg must be installed and on PATH for tests."

    sample_dir = tmp_path / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    video_path = sample_dir / "test_synth_video.mp4"

    # Generate 4s video with red/blue scene change and 440Hz tone
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map", "[v]",
            "-map", "2:a",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )

    return {
        "settings": settings,
        "storage": layout,
        "video": video_path,
        "tmp_path": tmp_path,
    }


def test_audio_extractor(analysis_env):
    video_path = analysis_env["video"]
    audio_out = analysis_env["tmp_path"] / "extracted_16k.wav"
    res = extract_audio_16k_mono(video_path, audio_out)
    assert res.exists()
    assert res.stat().st_size > 0


def test_scene_detection(analysis_env):
    video_path = analysis_env["video"]
    scenes = detect_scenes_ffmpeg(video_path, duration_seconds=4.0, threshold=0.3)
    assert len(scenes) >= 1
    assert scenes[0].start_time == 0.0
    assert scenes[-1].end_time <= 4.1


def test_speech_segmentation():
    segments = [
        NormalizedSegment(start_time=0.0, end_time=1.5, text="Hello world.", language="en", confidence=0.9, words=[]),
        NormalizedSegment(start_time=1.8, end_time=3.0, text="How are you doing today?", language="en", confidence=0.88, words=[]),
        NormalizedSegment(start_time=5.0, end_time=7.0, text="I am doing fantastic!", language="en", confidence=0.95, words=[]),
    ]

    turns = segment_dialogue_turns(segments, pause_threshold_seconds=1.0)
    assert len(turns) == 2
    # First turn: "Hello world. How are you doing today?"
    assert "Hello world." in turns[0].text
    assert turns[0].turn_type == "question"
    # Second turn after 2.0s pause: "I am doing fantastic!"
    assert turns[1].turn_type == "exclamation"
    assert turns[1].speaker_label == "Speaker 2"


def test_frame_sampler(analysis_env):
    video_path = analysis_env["video"]
    scenes = [DetectedScene(0, 0.0, 4.0, 2.0, 0.0)]
    out_dir = analysis_env["tmp_path"] / "frames"
    frames = sample_analysis_frames(video_path, out_dir, scenes, duration_seconds=4.0, max_frames=2)
    assert len(frames) > 0
    assert Path(frames[0].frame_path).exists()


def test_visual_understanding_fallback(tmp_path):
    analyzer = OllamaVisionAnalyzer(base_url="http://127.0.0.1:99999")
    dummy_img = tmp_path / "dummy.jpg"
    dummy_img.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 200)

    obs = analyzer._heuristic_fallback(dummy_img, timestamp=1.5, frame_id="frame_1")
    assert len(obs) == 1
    assert obs[0].provider_model == "heuristic_fallback"
    assert obs[0].confidence == 0.5


def test_temporal_aggregator_query(analysis_env):
    proj_id = "test_proj_1"
    run_id = "test_run_1"
    asset_id = "test_asset_1"
    now = "2026-11-11T00:00:00Z"
    db_file = analysis_env["storage"].db_file

    with sqlite_session(db_file) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, status, storage_subdir, created_at, updated_at)
            VALUES (?, 'Test Project', 'active', ?, ?, ?)
            """,
            (proj_id, proj_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, is_external, media_type, file_size_bytes, availability_status, metadata_status, created_at, updated_at)
            VALUES (?, ?, 'test.mp4', 'test.mp4', 0, 'video', 1000, 'ready', 'complete', ?, ?)
            """,
            (asset_id, proj_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, media_asset_id, project_id, status, profile, config_json, created_at, updated_at)
            VALUES (?, ?, ?, 'completed', 'fast', '{}', ?, ?)
            """,
            (run_id, asset_id, proj_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO video_scenes (id, analysis_run_id, media_asset_id, scene_index, start_time, end_time, representative_timestamp, change_score, created_at)
            VALUES ('s1', ?, ?, 0, 0.0, 5.0, 2.5, 0.35, ?)
            """,
            (run_id, asset_id, now),
        )
        conn.execute(
            """
            INSERT INTO transcript_segments (id, analysis_run_id, media_asset_id, start_time, end_time, text, language, confidence, words_json, created_at)
            VALUES ('seg1', ?, ?, 1.0, 3.5, 'Welcome to ZezEdit video analysis', 'en', 0.95, '[]', ?)
            """,
            (run_id, asset_id, now),
        )
        conn.execute(
            """
            INSERT INTO speech_turns (id, analysis_run_id, media_asset_id, start_time, end_time, speaker_label, text, segment_ids_json, turn_type, created_at)
            VALUES ('t1', ?, ?, 1.0, 3.5, 'Speaker 1', 'Welcome to ZezEdit video analysis', '["seg1"]', 'statement', ?)
            """,
            (run_id, asset_id, now),
        )
        conn.execute(
            """
            INSERT INTO visual_observations (id, analysis_run_id, media_asset_id, timestamp, category, description, provider_model, confidence, created_at)
            VALUES ('obs1', ?, ?, 2.5, 'scene_setting', 'Indoor studio environment with bright lighting', 'qwen3-vl:4b-instruct', 0.9, ?)
            """,
            (run_id, asset_id, now),
        )

    ctx = get_temporal_context_at(run_id, timestamp=2.0, db_path=db_file)
    assert ctx.current_scene is not None
    assert ctx.current_scene["id"] == "s1"
    assert ctx.active_segment is not None
    assert "Welcome to ZezEdit" in ctx.active_segment["text"]
    assert ctx.active_speech_turn is not None
    assert len(ctx.nearby_visual_observations) == 1


def test_analysis_api_flow(analysis_env):
    app = create_app(settings_override=analysis_env["settings"])
    with TestClient(app) as client:
        # 1. Create project
        proj_resp = client.post("/api/v1/projects", json={"name": "Analysis Test Project"})
        assert proj_resp.status_code == 201
        project_id = proj_resp.json()["id"]

        # 2. Import media asset
        imp_resp = client.post(
            f"/api/v1/projects/{project_id}/media/import-local",
            json={
                "file_path": str(analysis_env["video"]),
                "copy_to_storage": False,
                "generate_proxy": False,
                "generate_thumbnail": True,
            },
        )
        assert imp_resp.status_code == 201
        asset_id = imp_resp.json()["id"]

        # 3. Trigger analysis synchronously
        start_resp = client.post(
            f"/api/v1/projects/{project_id}/media/{asset_id}/analysis",
            json={"profile": "fast", "run_synchronously": True},
        )
        assert start_resp.status_code == 202
        run_data = start_resp.json()
        run_id = run_data["id"]
        assert run_data["status"] == "completed"

        # 4. Inspect transcript
        trans_resp = client.get(f"/api/v1/projects/{project_id}/media/{asset_id}/analysis/{run_id}/transcript")
        assert trans_resp.status_code == 200
        assert "segments" in trans_resp.json()

        # 5. Inspect scenes
        scenes_resp = client.get(f"/api/v1/projects/{project_id}/media/{asset_id}/analysis/{run_id}/scenes")
        assert scenes_resp.status_code == 200
        assert len(scenes_resp.json()) >= 1

        # 6. Query temporal context
        ctx_resp = client.get(f"/api/v1/projects/{project_id}/media/{asset_id}/analysis/{run_id}/context?timestamp=1.5")
        assert ctx_resp.status_code == 200
        ctx_data = ctx_resp.json()
        assert ctx_data["current_scene"] is not None

        # 7. Test cancellation logic on pending run
        with sqlite_session(analysis_env["storage"].db_file) as conn:
            conn.execute(
                """
                INSERT INTO analysis_runs (id, media_asset_id, project_id, status, profile, config_json, created_at, updated_at)
                VALUES ('pending_run', ?, ?, 'pending', 'fast', '{}', datetime('now'), datetime('now'))
                """,
                (asset_id, project_id),
            )

        cancel_resp = client.post(f"/api/v1/projects/{project_id}/media/{asset_id}/analysis/pending_run/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"
