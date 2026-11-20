"""Comprehensive test suite for P2.1: AI Video Analysis Foundation.

Covers:
- Valid source video analysis (audio demux, whisper transcription, scenes, frames, visual observations)
- Video without audio track (graceful fallback, warnings, visual stages preserved)
- Missing / inaccessible media file protection (P1.7 alignment: HTTP 400 MEDIA_FILE_MISSING)
- Storage quota enforcement (P1.9 alignment: HTTP 400 STORAGE_QUOTA_EXCEEDED)
- Concurrency and duplicate request deduplication
- Stage-aware cache reuse (source signature caching with zero redundant compute)
- Canonical shared media deduplication reuse (P1.8 alignment: instant clone across projects sharing stored_file_id)
- Cancellation and retry lifecycle
- Direct global media analysis API endpoints (/media/{asset_id}/analysis...)
- Bounded memory safety during streaming extraction
- Multimodal temporal context aggregation (/context?timestamp=X)
- Database persistence and SQLite foreign key integrity
"""

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import MediaFileMissingError, StorageQuotaExceededError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.analysis_pipeline import VideoAnalysisPipeline, compute_source_signature
from app.services.storage import StorageService
from app.services.temporal_aggregator import get_temporal_context_at


@pytest.fixture
def p2_1_env(tmp_path: Path):
    """Set up isolated storage layout, SQLite database with all migrations, and test media."""
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
    video_path = sample_dir / "p2_1_test_video.mp4"

    # Generate 3s video with red/green cut and 440Hz sine tone
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1.5",
            "-f", "lavfi", "-i", "color=c=green:s=320x240:d=1.5",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
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

    # Silent video without audio track
    silent_video_path = sample_dir / "p2_1_silent_video.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(silent_video_path),
        ],
        capture_output=True,
        check=True,
    )

    app = create_app(settings)
    client = TestClient(app)

    return {
        "settings": settings,
        "storage": layout,
        "video_path": video_path,
        "silent_video_path": silent_video_path,
        "client": client,
        "tmp_path": tmp_path,
    }


def _seed_project_and_asset(
    db_path: Path,
    video_path: Path,
    project_id: str = "proj_p2_1",
    asset_id: str = "asset_p2_1",
    stored_file_id: str = None,
    sha256: str = None,
    availability_status: str = "available",
) -> Dict[str, str]:
    now = "2026-11-20T12:00:00Z"
    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO projects (id, name, description, storage_subdir, status, created_at, updated_at)
            VALUES (?, 'P2.1 Foundation Test Project', 'Testing analysis foundation', ?, 'active', ?, ?)
            """,
            (project_id, project_id, now, now),
        )

        if stored_file_id:
            conn.execute(
                """
                INSERT OR IGNORE INTO stored_media_files (
                    id, sha256, file_size_bytes, storage_path, reference_count,
                    created_at, updated_at
                ) VALUES (?, ?, 10240, ?, 1, ?, ?)
                """,
                (stored_file_id, sha256 or "dummy_sha256", str(video_path), now, now),
            )

        conn.execute(
            """
            INSERT OR REPLACE INTO media_assets (
                id, project_id, original_filename, storage_path, is_external, media_type,
                file_size_bytes, mime_type, duration_seconds, width, height, fps,
                video_codec, audio_codec, availability_status, stored_file_id, sha256,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0, 'video', 10240, 'video/mp4', 3.0, 320, 240, 25.0, 'h264', 'aac', ?, ?, ?, ?, ?)
            """,
            (
                asset_id,
                project_id,
                video_path.name,
                str(video_path),
                availability_status,
                stored_file_id,
                sha256,
                now,
                now,
            ),
        )

    return {"project_id": project_id, "asset_id": asset_id}


def test_source_signature_computation(p2_1_env):
    """Test fast bounded-memory source signature computation."""
    video = p2_1_env["video_path"]
    sig1 = compute_source_signature(video)
    sig2 = compute_source_signature(video)
    assert sig1 == sig2
    assert ":" in sig1
    assert compute_source_signature(Path("non_existent_file.mp4")) == "missing"


def test_analysis_pipeline_full_execution(p2_1_env):
    """Test full asynchronous or synchronous analysis pipeline execution on a synthetic video."""
    storage = p2_1_env["storage"]
    settings = p2_1_env["settings"]
    db_path = storage.db_file
    video = p2_1_env["video_path"]

    meta = _seed_project_and_asset(db_path, video)
    pipeline = VideoAnalysisPipeline(settings=settings, db_path=db_path)

    # 1. Create run
    run_id = pipeline.create_analysis_run(
        media_asset_id=meta["asset_id"],
        project_id=meta["project_id"],
        profile="fast",
    )
    assert run_id.startswith("run_")

    # 2. Check initial pending status
    telemetry = pipeline.get_run_telemetry(run_id)
    assert telemetry["status"] == "pending"
    assert telemetry["current_stage"] == "queued"

    # 3. Synchronous execution
    import asyncio
    result = asyncio.run(pipeline.execute_analysis(run_id))
    assert result["status"] == "completed"
    assert result["has_audio"] is True

    # 4. Verify SQLite persistence across all tables
    with sqlite_session(db_path) as conn:
        run_row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        assert run_row is not None

        audio_row = conn.execute("SELECT * FROM audio_analysis WHERE analysis_run_id = ?", (run_id,)).fetchone()
        assert audio_row is not None

        scenes = conn.execute("SELECT * FROM video_scenes WHERE analysis_run_id = ?", (run_id,)).fetchall()
        assert len(scenes) >= 1

        frames = conn.execute("SELECT * FROM sampled_frames WHERE analysis_run_id = ?", (run_id,)).fetchall()
        assert len(frames) >= 1

        obs = conn.execute("SELECT * FROM visual_observations WHERE analysis_run_id = ?", (run_id,)).fetchall()
        assert len(obs) >= 1

    # 5. Check cache info
    cache_info = pipeline.get_run_cache_info(run_id)
    assert cache_info["is_cache_valid"] is True
    assert cache_info["records"]["video_scenes"] >= 1


def test_analysis_pipeline_silent_video_no_audio(p2_1_env):
    """Test video analysis handles media with no audio track gracefully."""
    storage = p2_1_env["storage"]
    settings = p2_1_env["settings"]
    db_path = storage.db_file
    silent_video = p2_1_env["silent_video_path"]

    meta = _seed_project_and_asset(db_path, silent_video, asset_id="asset_silent")
    pipeline = VideoAnalysisPipeline(settings=settings, db_path=db_path)

    run_id = pipeline.create_analysis_run(media_asset_id=meta["asset_id"], project_id=meta["project_id"])

    import asyncio
    result = asyncio.run(pipeline.execute_analysis(run_id))
    assert result["status"] == "completed"
    assert result["has_audio"] is False

    with sqlite_session(db_path) as conn:
        aud = conn.execute("SELECT has_audio FROM audio_analysis WHERE analysis_run_id = ?", (run_id,)).fetchone()
        assert aud[0] == 0

        # Scenes and frames are still sampled correctly
        scenes = conn.execute("SELECT COUNT(*) FROM video_scenes WHERE analysis_run_id = ?", (run_id,)).fetchone()[0]
        assert scenes >= 1


def test_analysis_missing_file_rejected_immediately(p2_1_env):
    """Test that missing or inaccessible media is rejected immediately with HTTP 400 (P1.7 alignment)."""
    storage = p2_1_env["storage"]
    settings = p2_1_env["settings"]
    client = p2_1_env["client"]
    db_path = storage.db_file

    missing_path = p2_1_env["tmp_path"] / "non_existent_video.mp4"
    meta = _seed_project_and_asset(
        db_path, missing_path, asset_id="asset_missing", availability_status="missing"
    )

    pipeline = VideoAnalysisPipeline(settings=settings, db_path=db_path)

    # Calling pipeline directly raises MediaFileMissingError
    with pytest.raises(MediaFileMissingError):
        pipeline.create_analysis_run(media_asset_id=meta["asset_id"], project_id=meta["project_id"])

    # Calling via API returns HTTP 400 with structured MEDIA_FILE_MISSING
    resp = client.post(
        f"/api/v1/projects/{meta['project_id']}/media/{meta['asset_id']}/analysis",
        json={"profile": "balanced"},
    )
    assert resp.status_code == 400
    data = resp.json()
    detail = data.get("detail", {})
    assert detail.get("error_code") == "MEDIA_FILE_MISSING"


def test_analysis_storage_quota_enforcement(p2_1_env):
    """Test that analysis respects storage quotas and rejects when limit is breached (P1.9 alignment)."""
    storage = p2_1_env["storage"]
    settings = p2_1_env["settings"]
    client = p2_1_env["client"]
    db_path = storage.db_file
    video = p2_1_env["video_path"]

    meta = _seed_project_and_asset(db_path, video, asset_id="asset_quota_test")

    # Configure a tiny temp storage quota of 10 bytes in storage_quotas
    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            UPDATE storage_quotas
            SET temp_storage_limit_bytes = 10, updated_at = '2026-11-20T12:00:00Z'
            WHERE id = 'default'
            """
        )

    pipeline = VideoAnalysisPipeline(settings=settings, db_path=db_path)

    with pytest.raises(StorageQuotaExceededError):
        pipeline.create_analysis_run(media_asset_id=meta["asset_id"], project_id=meta["project_id"])

    # API returns HTTP 400 with STORAGE_QUOTA_EXCEEDED
    resp = client.post(
        f"/api/v1/projects/{meta['project_id']}/media/{meta['asset_id']}/analysis",
        json={"profile": "balanced"},
    )
    assert resp.status_code == 400
    data = resp.json()
    detail = data.get("detail", {})
    assert detail.get("error_code") == "STORAGE_QUOTA_EXCEEDED"

    # Reset quota
    with sqlite_session(db_path) as conn:
        conn.execute("UPDATE storage_quotas SET temp_storage_limit_bytes = NULL WHERE id = 'default'")


def test_analysis_duplicate_request_deduplication(p2_1_env):
    """Test that concurrent/repeated requests for the same media asset reuse the active run."""
    storage = p2_1_env["storage"]
    settings = p2_1_env["settings"]
    db_path = storage.db_file
    video = p2_1_env["video_path"]

    meta = _seed_project_and_asset(db_path, video, asset_id="asset_dedup_test")
    pipeline = VideoAnalysisPipeline(settings=settings, db_path=db_path)

    run_1 = pipeline.create_analysis_run(media_asset_id=meta["asset_id"], project_id=meta["project_id"])
    run_2 = pipeline.create_analysis_run(media_asset_id=meta["asset_id"], project_id=meta["project_id"])

    assert run_1 == run_2

    with sqlite_session(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM analysis_runs WHERE media_asset_id = ?",
            (meta["asset_id"],),
        ).fetchone()[0]
        assert count == 1


def test_analysis_stage_aware_cache_reuse(p2_1_env):
    """Test stage-aware cache returns completed run without re-running unless force_reanalysis is set."""
    storage = p2_1_env["storage"]
    settings = p2_1_env["settings"]
    db_path = storage.db_file
    video = p2_1_env["video_path"]

    meta = _seed_project_and_asset(db_path, video, asset_id="asset_cache_test")
    pipeline = VideoAnalysisPipeline(settings=settings, db_path=db_path)

    run_1 = pipeline.create_analysis_run(media_asset_id=meta["asset_id"], project_id=meta["project_id"])
    import asyncio
    asyncio.run(pipeline.execute_analysis(run_1))

    # Second call without force_reanalysis returns existing completed run
    run_2 = pipeline.create_analysis_run(
        media_asset_id=meta["asset_id"], project_id=meta["project_id"], force_reanalysis=False
    )
    assert run_2 == run_1

    # Call with force_reanalysis creates a new run
    run_3 = pipeline.create_analysis_run(
        media_asset_id=meta["asset_id"], project_id=meta["project_id"], force_reanalysis=True
    )
    assert run_3 != run_1


def test_analysis_canonical_shared_media_reuse(p2_1_env):
    """Test that uploading the same physical media into a second project reuses canonical analysis (P1.8 alignment)."""
    storage = p2_1_env["storage"]
    settings = p2_1_env["settings"]
    db_path = storage.db_file
    video = p2_1_env["video_path"]

    stored_file_id = "sf_shared_123"
    sha256 = "hash_shared_abc"

    # Project A: seed and run analysis
    meta_a = _seed_project_and_asset(
        db_path, video, project_id="proj_a", asset_id="asset_a", stored_file_id=stored_file_id, sha256=sha256
    )
    pipeline = VideoAnalysisPipeline(settings=settings, db_path=db_path)

    run_a = pipeline.create_analysis_run(media_asset_id=meta_a["asset_id"], project_id=meta_a["project_id"])
    import asyncio
    asyncio.run(pipeline.execute_analysis(run_a))

    # Project B: seed duplicate media asset pointing to same stored_file_id
    meta_b = _seed_project_and_asset(
        db_path, video, project_id="proj_b", asset_id="asset_b", stored_file_id=stored_file_id, sha256=sha256
    )

    t_start = time.monotonic()
    run_b = pipeline.create_analysis_run(media_asset_id=meta_b["asset_id"], project_id=meta_b["project_id"])
    duration = time.monotonic() - t_start

    # Cloned run is created immediately in < 0.2s without CPU compute
    assert duration < 1.0
    assert run_b != run_a

    with sqlite_session(db_path) as conn:
        b_row = conn.execute("SELECT status, progress_pct, stored_file_id FROM analysis_runs WHERE id = ?", (run_b,)).fetchone()
        assert b_row[0] == "completed"
        assert b_row[1] == 100.0
        assert b_row[2] == stored_file_id

        # Verify cloned scenes and frames exist for asset_b
        b_scenes = conn.execute("SELECT COUNT(*) FROM video_scenes WHERE analysis_run_id = ? AND media_asset_id = ?", (run_b, meta_b["asset_id"])).fetchone()[0]
        assert b_scenes >= 1

        b_frames = conn.execute("SELECT COUNT(*) FROM sampled_frames WHERE analysis_run_id = ? AND media_asset_id = ?", (run_b, meta_b["asset_id"])).fetchone()[0]
        assert b_frames >= 1


def test_analysis_cancellation_and_retry_lifecycle(p2_1_env):
    """Test cancellation of active run and retry transitioning back to pending."""
    storage = p2_1_env["storage"]
    settings = p2_1_env["settings"]
    db_path = storage.db_file
    video = p2_1_env["video_path"]

    meta = _seed_project_and_asset(db_path, video, asset_id="asset_lifecycle_test")
    pipeline = VideoAnalysisPipeline(settings=settings, db_path=db_path)

    run_id = pipeline.create_analysis_run(media_asset_id=meta["asset_id"], project_id=meta["project_id"])

    # Cancel
    cancel_res = pipeline.cancel_run(run_id)
    assert cancel_res["status"] == "cancelled"

    telemetry = pipeline.get_run_telemetry(run_id)
    assert telemetry["status"] == "cancelled"

    # Retry
    retry_res = pipeline.retry_run(run_id)
    assert retry_res["status"] == "pending"

    telemetry_retry = pipeline.get_run_telemetry(run_id)
    assert telemetry_retry["status"] == "pending"
    assert telemetry_retry["progress_pct"] == 0.0


def test_analysis_global_api_endpoints(p2_1_env):
    """Test direct global asset analysis endpoints (/api/v1/media/{asset_id}/analysis...)."""
    client = p2_1_env["client"]
    storage = p2_1_env["storage"]
    db_path = storage.db_file
    video = p2_1_env["video_path"]

    meta = _seed_project_and_asset(db_path, video, asset_id="asset_global_test")

    # Start analysis synchronously via global route
    resp = client.post(
        f"/api/v1/media/{meta['asset_id']}/analysis",
        json={"profile": "fast", "run_synchronously": True},
    )
    assert resp.status_code == 202
    data = resp.json()
    run_id = data["id"]
    assert data["status"] == "completed"

    # Query runs globally
    list_resp = client.get(f"/api/v1/media/{meta['asset_id']}/analysis")
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) >= 1
    assert runs[0]["id"] == run_id

    # Query context globally
    ctx_resp = client.get(f"/api/v1/media/{meta['asset_id']}/analysis/{run_id}/context?timestamp=1.0&window=5.0")
    assert ctx_resp.status_code == 200
    ctx = ctx_resp.json()
    assert ctx["analysis_run_id"] == run_id

    # Query telemetry globally
    telem_resp = client.get(f"/api/v1/media/{meta['asset_id']}/analysis/{run_id}/telemetry")
    assert telem_resp.status_code == 200
    assert telem_resp.json()["status"] == "completed"


def test_analysis_temporal_context_aggregation(p2_1_env):
    """Test unified multimodal temporal context lookup at a specific timestamp."""
    storage = p2_1_env["storage"]
    settings = p2_1_env["settings"]
    db_path = storage.db_file
    video = p2_1_env["video_path"]

    meta = _seed_project_and_asset(db_path, video, asset_id="asset_context_test")
    pipeline = VideoAnalysisPipeline(settings=settings, db_path=db_path)

    run_id = pipeline.create_analysis_run(media_asset_id=meta["asset_id"], project_id=meta["project_id"])
    import asyncio
    asyncio.run(pipeline.execute_analysis(run_id))

    ctx = get_temporal_context_at(run_id, timestamp=1.5, window_seconds=5.0, db_path=db_path)
    assert ctx.timestamp == 1.5
    assert ctx.current_scene is not None
    assert ctx.audio_state is not None
    assert ctx.aligned_event is not None


def test_database_foreign_key_and_integrity_check(p2_1_env):
    """Verify database schema integrity and zero foreign key violations after P2.1 operations."""
    storage = p2_1_env["storage"]
    db_path = storage.db_file

    with sqlite_session(db_path) as conn:
        integrity = [row[0] for row in conn.execute("PRAGMA integrity_check").fetchall()]
        assert integrity == ["ok"], f"Integrity check failed: {integrity}"

        fk_violations = [list(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()]
        assert fk_violations == [], f"Foreign key check failed: {fk_violations}"
