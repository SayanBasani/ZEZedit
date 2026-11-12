"""Parity verification tests for Milestone 15: Video Analysis, AI Understanding & Temporal Context Engine."""

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
from app.services.audio_extractor import detect_audio_silence, extract_audio_16k_mono, inspect_audio_stream
from app.services.scene_detector import detect_scenes_ffmpeg
from app.services.temporal_aggregator import get_temporal_context_at


@pytest.fixture
def m15_env(tmp_path: Path):
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

    # 1. Standard audio-video (4s, 2 scenes, 440Hz tone)
    standard_video = sample_dir / "standard_video.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2",
            "-f", "lavfi", "-i", "color=c=white:s=320x240:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map", "[v]",
            "-map", "2:a",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(standard_video),
        ],
        capture_output=True,
        check=True,
    )

    # 2. Silent video (no audio stream)
    silent_video = sample_dir / "silent_video.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "color=c=red:s=320x240:d=3",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(silent_video),
        ],
        capture_output=True,
        check=True,
    )

    # Register project and media assets in DB
    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, status, storage_subdir, created_at, updated_at)
            VALUES ('p1', 'Analysis Parity Project', 'active', 'projects/p1', datetime('now'), datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, file_size_bytes,
                duration_seconds, media_type, width, height, fps, is_external,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                'm_std', 'p1', 'standard_video.mp4', ?, 1024, 4.0, 'video',
                320, 240, 30.0, 0, 'ready', 'complete', datetime('now'), datetime('now')
            )
            """,
            (str(standard_video),),
        )
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, file_size_bytes,
                duration_seconds, media_type, width, height, fps, is_external,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                'm_silent', 'p1', 'silent_video.mp4', ?, 1024, 3.0, 'video',
                320, 240, 30.0, 0, 'ready', 'complete', datetime('now'), datetime('now')
            )
            """,
            (str(silent_video),),
        )

    return {
        "settings": settings,
        "storage": layout,
        "standard_video": standard_video,
        "silent_video": silent_video,
        "tmp_path": tmp_path,
    }


def test_audio_stream_inspection_and_silence(m15_env):
    """Verify audio stream inspection and silence detection algorithms."""
    # 1. Standard video inspection
    std_meta = inspect_audio_stream(m15_env["standard_video"])
    assert std_meta.has_audio is True
    assert std_meta.channels is not None
    assert std_meta.sample_rate is not None

    # 2. Silent video inspection
    silent_meta = inspect_audio_stream(m15_env["silent_video"])
    assert silent_meta.has_audio is False

    # 3. Extract 16kHz mono audio from standard video
    out_wav = m15_env["tmp_path"] / "std_audio.wav"
    extracted_path, meta = extract_audio_16k_mono(m15_env["standard_video"], out_wav, return_metadata=True)
    assert extracted_path.exists()
    assert meta.has_audio is True
    assert meta.speech_density > 0.0

    # 4. Extract audio from silent video (should synthesize silent 16kHz WAV without error)
    silent_wav = m15_env["tmp_path"] / "silent_audio.wav"
    s_path, s_meta = extract_audio_16k_mono(m15_env["silent_video"], silent_wav, return_metadata=True)
    assert s_path.exists()
    assert s_meta.has_audio is False
    assert s_meta.speech_density == 0.0


def test_scene_detection_and_thumbnails(m15_env):
    """Verify scene detection produces real scene thumbnails on disk."""
    thumbs_dir = m15_env["tmp_path"] / "scenes_thumbs"
    scenes = detect_scenes_ffmpeg(
        m15_env["standard_video"],
        duration_seconds=4.0,
        threshold=0.3,
        thumbnails_dir=thumbs_dir,
    )
    assert len(scenes) >= 1
    for sc in scenes:
        assert sc.thumbnail_path is not None
        thumb_file = Path(sc.thumbnail_path)
        assert thumb_file.exists()
        assert thumb_file.stat().st_size > 0


def test_silent_video_analysis_pipeline(m15_env):
    """Verify video analysis completes successfully on video without audio (ZEZ-021, ZEZ-022)."""
    app = create_app(m15_env["settings"])
    with TestClient(app) as client:
        # Trigger analysis synchronously on silent video
        res = client.post(
            "/api/v1/projects/p1/media/m_silent/analysis",
            json={"profile": "fast", "run_synchronously": True},
        )
        assert res.status_code == 202
        run_data = res.json()
        run_id = run_data["id"]
        assert run_data["status"] == "completed"

        # Check transcript is empty but valid
        t_res = client.get(f"/api/v1/projects/p1/media/m_silent/analysis/{run_id}/transcript")
        assert t_res.status_code == 200
        t_data = t_res.json()
        assert t_data["segments_count"] == 0

        # Check audio analysis record
        a_res = client.get(f"/api/v1/projects/p1/media/m_silent/analysis/{run_id}/audio")
        assert a_res.status_code == 200
        a_data = a_res.json()
        assert a_data["has_audio"] is False


def test_standard_video_analysis_and_caching(m15_env):
    """Verify standard video analysis, persistence, and stage-aware caching (ZEZ-029, ZEZ-030)."""
    app = create_app(m15_env["settings"])
    with TestClient(app) as client:
        # 1. First run: executes full analysis
        res1 = client.post(
            "/api/v1/projects/p1/media/m_std/analysis",
            json={"profile": "fast", "run_synchronously": True},
        )
        assert res1.status_code == 202
        run1 = res1.json()
        assert run1["status"] == "completed"

        # 2. Second run without force_reanalysis: returns cached run (ZEZ-029)
        res2 = client.post(
            "/api/v1/projects/p1/media/m_std/analysis",
            json={"profile": "fast", "force_reanalysis": False},
        )
        assert res2.status_code == 202
        run2 = res2.json()
        assert run2["id"] == run1["id"]

        # 3. Third run with force_reanalysis=True: generates new run (ZEZ-030)
        res3 = client.post(
            "/api/v1/projects/p1/media/m_std/analysis",
            json={"profile": "fast", "force_reanalysis": True, "run_synchronously": True},
        )
        assert res3.status_code == 202
        run3 = res3.json()
        assert run3["id"] != run1["id"]
        assert run3["status"] == "completed"

        # 4. Check list of runs contains both runs in history
        runs_res = client.get("/api/v1/projects/p1/media/m_std/analysis")
        assert runs_res.status_code == 200
        runs_list = runs_res.json()
        assert len(runs_list) >= 2


def test_non_destructive_transcript_corrections(m15_env):
    """Verify non-destructive transcript corrections CRUD and overlay (ZEZ-025)."""
    app = create_app(m15_env["settings"])
    with TestClient(app) as client:
        # Setup run and segment in DB
        with sqlite_session(m15_env["storage"].db_file) as conn:
            conn.execute(
                """
                INSERT INTO analysis_runs (
                    id, media_asset_id, project_id, status, profile, config_json,
                    progress_pct, current_stage, created_at, updated_at
                ) VALUES ('r_test', 'm_std', 'p1', 'completed', 'balanced', '{}', 100.0, 'completed', datetime('now'), datetime('now'))
                """
            )
            conn.execute(
                """
                INSERT INTO transcript_segments (
                    id, analysis_run_id, media_asset_id, start_time, end_time,
                    text, language, confidence, words_json, created_at
                ) VALUES ('seg_1', 'r_test', 'm_std', 1.0, 3.0, 'Raw speech with typo', 'en', 0.95, '[]', datetime('now'))
                """
            )

        # 1. Fetch transcript: initially uncorrected
        t_res1 = client.get("/api/v1/projects/p1/media/m_std/analysis/r_test/transcript")
        assert t_res1.status_code == 200
        seg1 = t_res1.json()["segments"][0]
        assert seg1["is_corrected"] is False
        assert seg1["corrected_text"] is None

        # 2. Create non-destructive correction
        corr_payload = {
            "segment_id": "seg_1",
            "start_time": 1.0,
            "end_time": 3.0,
            "original_text": "Raw speech with typo",
            "corrected_text": "Corrected proper transcript text",
        }
        c_res = client.post("/api/v1/projects/p1/media/m_std/transcript/corrections", json=corr_payload)
        assert c_res.status_code == 200
        corr_data = c_res.json()
        corr_id = corr_data["id"]
        assert corr_data["corrected_text"] == "Corrected proper transcript text"

        # 3. Fetch transcript again: should have corrected_text overlaid
        t_res2 = client.get("/api/v1/projects/p1/media/m_std/analysis/r_test/transcript")
        seg2 = t_res2.json()["segments"][0]
        assert seg2["is_corrected"] is True
        assert seg2["corrected_text"] == "Corrected proper transcript text"
        assert seg2["text"] == "Raw speech with typo"  # Raw text preserved!

        # 4. List corrections
        list_res = client.get("/api/v1/projects/p1/media/m_std/transcript/corrections")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # 5. Delete/revert correction
        del_res = client.delete(f"/api/v1/projects/p1/media/m_std/transcript/corrections/{corr_id}")
        assert del_res.status_code == 200

        # 6. Fetch transcript again: reverted to raw Whisper text
        t_res3 = client.get("/api/v1/projects/p1/media/m_std/analysis/r_test/transcript")
        seg3 = t_res3.json()["segments"][0]
        assert seg3["is_corrected"] is False
        assert seg3["corrected_text"] is None


def test_temporal_context_and_thumbnails_serving(m15_env):
    """Verify temporal context aggregator queries and scene thumbnail streaming endpoint."""
    app = create_app(m15_env["settings"])
    with TestClient(app) as client:
        # Run analysis to populate scenes and frames
        res = client.post(
            "/api/v1/projects/p1/media/m_std/analysis",
            json={"profile": "fast", "run_synchronously": True},
        )
        run_id = res.json()["id"]

        # Fetch scenes
        scenes_res = client.get(f"/api/v1/projects/p1/media/m_std/analysis/{run_id}/scenes")
        scenes = scenes_res.json()
        assert len(scenes) >= 1
        scene_id = scenes[0]["id"]

        # Stream scene thumbnail image
        thumb_res = client.get(f"/api/v1/projects/p1/media/m_std/analysis/scene-thumbnail/{scene_id}")
        assert thumb_res.status_code == 200
        assert thumb_res.headers["content-type"] == "image/jpeg"
        assert len(thumb_res.content) > 0

        # Query temporal context at 1.5 seconds (ZEZ-032)
        ctx_res = client.get(f"/api/v1/projects/p1/media/m_std/analysis/{run_id}/context?timestamp=1.5&window=5.0")
        assert ctx_res.status_code == 200
        ctx_data = ctx_res.json()
        assert ctx_data["query_timestamp"] == 1.5
        assert "current_scene" in ctx_data
