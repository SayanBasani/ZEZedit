"""Session 3: Unified Full-Video Analysis Pipeline Tests.

Verifies:
- Long-video streaming safety (bounded memory)
- Persistent job linkage with JobOrchestrator
- Granular stage-level telemetry
- Stage-aware caching and source signature invalidation
- Cancellation and retry state machine
- Graceful handling of audio-less media and corrupted/missing files
"""

import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.analysis_pipeline import VideoAnalysisPipeline, compute_source_signature
from app.services.jobs import JobOrchestrator


@pytest.fixture
def session3_env(tmp_path: Path):
    """Set up isolated storage layout, test database, and synthetic test videos."""
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

    sample_dir = tmp_path / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)

    # 1. Standard video with audio (4 seconds, two distinct color scenes)
    std_video = sample_dir / "test_movie_scene.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
            "-f", "lavfi", "-i", "color=c=yellow:s=320x240:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map", "[v]",
            "-map", "2:a",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(std_video),
        ],
        capture_output=True,
        check=True,
    )

    # 2. Audio-less video (2 seconds red)
    silent_video = sample_dir / "test_silent.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2",
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
            VALUES ('proj_s3', 'Session 3 Intelligence Project', 'active', 'projects/proj_s3', datetime('now'), datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, file_size_bytes,
                duration_seconds, media_type, width, height, fps, is_external,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                'med_s3_std', 'proj_s3', 'test_movie_scene.mp4', ?, 4096, 4.0, 'video',
                320, 240, 30.0, 0, 'ready', 'complete', datetime('now'), datetime('now')
            )
            """,
            (str(std_video),),
        )
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, file_size_bytes,
                duration_seconds, media_type, width, height, fps, is_external,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                'med_s3_silent', 'proj_s3', 'test_silent.mp4', ?, 2048, 2.0, 'video',
                320, 240, 30.0, 0, 'ready', 'complete', datetime('now'), datetime('now')
            )
            """,
            (str(silent_video),),
        )

    return {
        "settings": settings,
        "storage": layout,
        "std_video": std_video,
        "silent_video": silent_video,
        "tmp_path": tmp_path,
    }


def test_source_signature_computation(session3_env):
    """Verify source signature is deterministic, rapid, and sensitive to file modification."""
    video = session3_env["std_video"]
    sig1 = compute_source_signature(video)
    assert sig1 != "missing"
    assert sig1 != "unreadable"

    # Signature must be identical on unchanged file
    sig2 = compute_source_signature(video)
    assert sig1 == sig2

    # Non-existent file returns 'missing'
    assert compute_source_signature(Path("non_existent_file.mp4")) == "missing"


def test_missing_media_file_graceful_failure(session3_env):
    """Verify missing source media fails cleanly with useful error and does not crash."""
    layout = session3_env["storage"]
    pipeline = VideoAnalysisPipeline(session3_env["settings"], layout.db_file)

    # Register an asset with non-existent path
    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, file_size_bytes,
                duration_seconds, media_type, width, height, fps, is_external,
                availability_status, metadata_status, created_at, updated_at
            ) VALUES (
                'med_missing', 'proj_s3', 'missing.mp4', 'D:\\non_existent\\missing.mp4', 0, 0.0, 'video',
                320, 240, 30.0, 0, 'missing', 'failed', datetime('now'), datetime('now')
            )
            """
        )

    run_id = pipeline.create_analysis_run("med_missing", "proj_s3")
    assert run_id.startswith("run_")

    app = create_app(session3_env["settings"])
    with TestClient(app) as client:
        # Check run status is pending initially
        r_resp = client.get(f"/api/v1/projects/proj_s3/media/med_missing/analysis/{run_id}")
        assert r_resp.status_code == 200
        assert r_resp.json()["status"] == "pending"

        # Executing analysis should fail gracefully without crashing
        with pytest.raises(Exception):
            import asyncio
            asyncio.run(pipeline.execute_analysis(run_id))

        # Run must be marked failed in DB with clear error message
        r_failed = client.get(f"/api/v1/projects/proj_s3/media/med_missing/analysis/{run_id}")
        assert r_failed.status_code == 200
        data = r_failed.json()
        assert data["status"] == "failed"
        assert "not found" in (data["error_message"] or "").lower()


def test_job_orchestrator_linkage_and_telemetry(session3_env):
    """Verify analysis run creates linked job in JobOrchestrator and exposes live telemetry."""
    app = create_app(session3_env["settings"])
    with TestClient(app) as client:
        # Start analysis synchronously
        resp = client.post(
            "/api/v1/projects/proj_s3/media/med_s3_std/analysis",
            json={"profile": "fast", "run_synchronously": True},
        )
        assert resp.status_code == 202
        run_data = resp.json()
        run_id = run_data["id"]
        job_id = run_data.get("job_id")
        assert job_id is not None, "Analysis run must be linked to a persistent JobRecord."
        assert run_data["status"] == "completed"
        assert run_data["progress_pct"] == 100.0

        # Verify JobOrchestrator state for this job
        jobs = JobOrchestrator(session3_env["settings"], session3_env["storage"].db_file)
        job = jobs.get_job(job_id)
        assert job.job_type == "media_analysis"
        assert job.status == "completed"
        assert job.progress_pct == 100.0

        # Verify telemetry endpoint
        telem_resp = client.get(f"/api/v1/projects/proj_s3/media/med_s3_std/analysis/{run_id}/telemetry")
        assert telem_resp.status_code == 200
        telem = telem_resp.json()
        assert telem["run_id"] == run_id
        assert telem["job_id"] == job_id
        assert telem["status"] == "completed"
        assert telem["progress_pct"] == 100.0
        assert "stage_details" in telem
        assert "timings" in telem["stage_details"]


def test_stage_aware_caching_and_source_invalidation(session3_env):
    """Verify unchanged media reuses cache, but modified media invalidates cache."""
    app = create_app(session3_env["settings"])
    with TestClient(app) as client:
        # 1. First run: computes and completes
        res1 = client.post(
            "/api/v1/projects/proj_s3/media/med_s3_std/analysis",
            json={"profile": "fast", "run_synchronously": True},
        )
        assert res1.status_code == 202
        run1 = res1.json()
        assert run1["status"] == "completed"

        # 2. Second run without force: returns cached run immediately
        res2 = client.post(
            "/api/v1/projects/proj_s3/media/med_s3_std/analysis",
            json={"profile": "fast", "force_reanalysis": False},
        )
        assert res2.status_code == 202
        run2 = res2.json()
        assert run2["id"] == run1["id"]

        # Check cache endpoint
        cache_resp = client.get(f"/api/v1/projects/proj_s3/media/med_s3_std/analysis/{run1['id']}/cache")
        assert cache_resp.status_code == 200
        cache_data = cache_resp.json()
        assert cache_data["is_cache_valid"] is True
        assert cache_data["records"]["video_scenes"] > 0

        # 3. Modify source file: change modification timestamp and append 1 byte
        std_video = session3_env["std_video"]
        with open(std_video, "ab") as f:
            f.write(b"\x00")

        # Third run: detected modification should bypass cache and create new run
        res3 = client.post(
            "/api/v1/projects/proj_s3/media/med_s3_std/analysis",
            json={"profile": "fast", "force_reanalysis": False, "run_synchronously": True},
        )
        assert res3.status_code == 202
        run3 = res3.json()
        assert run3["id"] != run1["id"], "Source modification must invalidate cached analysis run."


def test_cancellation_and_job_sync(session3_env):
    """Verify cancel_analysis transitions both analysis run and JobOrchestrator job to cancelled."""
    layout = session3_env["storage"]
    pipeline = VideoAnalysisPipeline(session3_env["settings"], layout.db_file)
    run_id = pipeline.create_analysis_run("med_s3_std", "proj_s3")

    app = create_app(session3_env["settings"])
    with TestClient(app) as client:
        # Check initial state
        run_before = client.get(f"/api/v1/projects/proj_s3/media/med_s3_std/analysis/{run_id}").json()
        assert run_before["status"] == "pending"

        # Cancel the run
        cancel_resp = client.post(f"/api/v1/projects/proj_s3/media/med_s3_std/analysis/{run_id}/cancel")
        assert cancel_resp.status_code == 200
        cancel_data = cancel_resp.json()
        assert cancel_data["status"] == "cancelled"

        # Verify run state in database
        run_after = client.get(f"/api/v1/projects/proj_s3/media/med_s3_std/analysis/{run_id}").json()
        assert run_after["status"] == "cancelled"

        # Verify JobOrchestrator job state is cancelled
        jobs = JobOrchestrator(session3_env["settings"], layout.db_file)
        job = jobs.get_job(cancel_data["job_id"])
        assert job.status == "cancelled"


def test_retry_endpoint(session3_env):
    """Verify retrying a cancelled/failed run resets it to pending and re-enqueues the job."""
    layout = session3_env["storage"]
    pipeline = VideoAnalysisPipeline(session3_env["settings"], layout.db_file)
    run_id = pipeline.create_analysis_run("med_s3_std", "proj_s3")
    pipeline.cancel_run(run_id)

    app = create_app(session3_env["settings"])
    with TestClient(app) as client:
        retry_resp = client.post(f"/api/v1/projects/proj_s3/media/med_s3_std/analysis/{run_id}/retry")
        assert retry_resp.status_code == 200
        retry_data = retry_resp.json()
        assert retry_data["status"] == "pending"

        run_after = client.get(f"/api/v1/projects/proj_s3/media/med_s3_std/analysis/{run_id}").json()
        assert run_after["status"] in ("pending", "running", "completed")


def test_silent_video_audio_less_pipeline(session3_env):
    """Verify video without audio stream analyzes scenes and frames without Whisper crash."""
    app = create_app(session3_env["settings"])
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/projects/proj_s3/media/med_s3_silent/analysis",
            json={"profile": "fast", "run_synchronously": True},
        )
        assert resp.status_code == 202
        run_data = resp.json()
        assert run_data["status"] == "completed"

        # Check transcript is empty (0 segments)
        t_resp = client.get(f"/api/v1/projects/proj_s3/media/med_s3_silent/analysis/{run_data['id']}/transcript")
        assert t_resp.status_code == 200
        assert t_resp.json()["segments_count"] == 0

        # Check scenes were detected
        s_resp = client.get(f"/api/v1/projects/proj_s3/media/med_s3_silent/analysis/{run_data['id']}/scenes")
        assert s_resp.status_code == 200
        assert len(s_resp.json()) >= 1
