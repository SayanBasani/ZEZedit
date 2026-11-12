"""Milestone 20: Production Hardening, Long-Video Performance, Storage Management & Recovery tests."""

import json
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.main import create_app
from app.services.audio_extractor import extract_audio_chunk
from app.services.backup_service import BackupService
from app.services.frame_sampler import sample_analysis_frames
from app.services.jobs import JobOrchestrator
from app.services.media import MediaService
from app.services.scene_detector import DetectedScene
from app.services.storage import StorageService


def create_test_video(path: Path, duration: int = 2):
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc=duration={duration}:size=320x240:rate=25",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            str(path),
        ],
        check=True,
    )


def create_test_wav(path: Path, duration: int = 2):
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", str(duration),
            "-c:a", "pcm_s16le",
            str(path),
        ],
        check=True,
    )


@pytest.fixture
def app_and_client(tmp_path: Path):
    storage_root = tmp_path / "storage"
    real_migrations = Path(__file__).resolve().parent.parent / "migrations"
    settings = Settings(
        app_name="ZezEditTestM20",
        storage_root=storage_root,
        migrations_dir=real_migrations,
        environment="test",
        max_concurrent_jobs=1,
    )
    app = create_app(settings_override=settings)
    layout = StorageLayout.from_root(storage_root)
    with TestClient(app) as client:
        yield client, settings, layout


def test_media_integrity_and_relinking(app_and_client, tmp_path):
    client, settings, layout = app_and_client

    # 1. Create project
    p_res = client.post("/api/v1/projects", json={"name": "M20 Media Integrity"})
    assert p_res.status_code == 201
    pid = p_res.json()["id"]

    # 2. Register media asset pointing to a real test video
    original_vid = tmp_path / "original_vid.mp4"
    create_test_video(original_vid, duration=2)

    reg_res = client.post(
        f"/api/v1/projects/{pid}/media",
        json={
            "original_filename": "original_vid.mp4",
            "storage_path": str(original_vid),
            "media_type": "video",
            "file_size_bytes": original_vid.stat().st_size,
            "duration_seconds": 2.0,
            "width": 320,
            "height": 240,
        },
    )
    assert reg_res.status_code == 201
    asset_id = reg_res.json()["id"]

    # Delete source file to simulate moved/missing asset
    original_vid.unlink()

    # 3. Test integrity check detects missing file
    chk_res = client.get(f"/api/v1/projects/{pid}/media/{asset_id}/integrity")
    assert chk_res.status_code == 200
    chk_data = chk_res.json()
    assert chk_data["integrity_status"] == "missing"
    assert chk_data["file_exists"] is False
    assert len(chk_data["issues"]) > 0

    # 4. Batch integrity check for project
    batch_res = client.post(f"/api/v1/projects/{pid}/media/check-integrity")
    assert batch_res.status_code == 200
    b_data = batch_res.json()
    assert b_data["total_assets"] == 1
    assert b_data["missing_count"] == 1
    assert b_data["all_healthy"] is False

    # 5. Create replacement video for relinking
    replacement = tmp_path / "replacement_vid.mp4"
    create_test_video(replacement, duration=3)

    # 6. Test relink inspection
    inspect_res = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/relink/inspect",
        json={"new_storage_path": str(replacement)},
    )
    assert inspect_res.status_code == 200
    i_data = inspect_res.json()
    assert "match_status" in i_data
    assert "comparison" in i_data
    assert i_data["comparison"]["candidate_duration"] is not None

    # 7. Test relink execution
    relink_res = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/relink",
        json={"new_storage_path": str(replacement), "force": True},
    )
    assert relink_res.status_code == 200
    r_data = relink_res.json()
    assert r_data["asset"]["storage_path"] == str(replacement.resolve())
    assert r_data["asset"]["availability_status"] == "present"


def test_frame_sampler_caching(tmp_path):
    video_path = tmp_path / "dummy.mp4"
    video_path.write_bytes(b"\x00" * 100)
    out_dir = tmp_path / "frames"
    out_dir.mkdir(parents=True)

    # Pre-create a cached frame
    cached_frame = out_dir / "frame_00005000.jpg"
    cached_frame.write_bytes(b"JPEG_FAKE_DATA")

    scenes = [
        DetectedScene(
            scene_index=0,
            start_time=0.0,
            end_time=10.0,
            representative_timestamp=5.0,
        )
    ]

    # sample_analysis_frames should reuse the existing frame without calling ffmpeg
    results = sample_analysis_frames(
        video_path=video_path,
        output_dir=out_dir,
        scenes=scenes,
        duration_seconds=10.0,
    )
    assert len(results) == 1
    assert results[0].frame_path == str(cached_frame)


def test_audio_extractor_bounded_chunk(tmp_path):
    audio_src = tmp_path / "source.wav"
    create_test_wav(audio_src, duration=4)
    chunk_out = tmp_path / "chunk_out.wav"

    # Call extract_audio_chunk
    out_path = extract_audio_chunk(
        input_path=audio_src,
        output_path=chunk_out,
        start_time=1.0,
        duration_seconds=2.0,
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_job_checkpointing_and_recovery(app_and_client):
    client, settings, layout = app_and_client
    orch = JobOrchestrator(settings=settings, db_path=layout.db_file)

    p_res = client.post("/api/v1/projects", json={"name": "M20 Job Checkpoints"})
    pid = p_res.json()["id"]

    job = orch.create_job(job_type="video_analysis", project_id=pid, priority=100)
    orch.transition_job_state(job.id, "running", stage="audio_extraction")

    # Save checkpoint
    orch.save_checkpoint(
        job_id=job.id,
        stage="transcription",
        completed_units=5,
        total_units=10,
        intermediate_artifacts={"audio_wav": "audio_16k.wav"},
        checkpoint_payload={"last_transcribed_timestamp": 45.2},
    )

    # Retrieve checkpoint
    cp = orch.get_checkpoint(job.id)
    assert cp is not None
    assert cp["stage"] == "transcription"
    assert cp["completed_units"] == 5
    assert cp["total_units"] == 10
    assert cp["progress_pct"] == 50.0
    assert cp["intermediate_artifacts"]["audio_wav"] == "audio_16k.wav"

    # Checkpoint retrieval via HTTP endpoint
    cp_res = client.get(f"/api/v1/jobs/{job.id}/checkpoint")
    assert cp_res.status_code == 200
    assert cp_res.json()["has_checkpoint"] is True
    assert cp_res.json()["checkpoint"]["stage"] == "transcription"

    # Test startup recovery preserves checkpoint
    orch.recover_interrupted_jobs()
    job_recovered = orch.get_job(job.id)
    assert job_recovered.status == "interrupted"
    assert "Checkpoint preserved" in job_recovered.error_message
    assert job_recovered.checkpoint_data is not None


def test_resource_aware_scheduler_and_priority(app_and_client):
    client, settings, layout = app_and_client
    orch = JobOrchestrator(settings=settings, db_path=layout.db_file)

    p_res = client.post("/api/v1/projects", json={"name": "M20 Priority Queue"})
    pid = p_res.json()["id"]

    # Queue multiple jobs with different priorities
    j_low = orch.create_job(job_type="background_sync", project_id=pid, priority=50)
    j_high = orch.create_job(job_type="timeline_render", project_id=pid, priority=200)
    j_mid = orch.create_job(job_type="shorts_export", project_id=pid, priority=150)

    # Test get_next_queued_job selects highest priority first
    next_job = orch.get_next_queued_job()
    assert next_job is not None
    assert next_job.id == j_high.id
    assert next_job.priority == 200

    # Test concurrency limits
    orch.transition_job_state(j_high.id, "running")
    can_dispatch, msg = orch.can_dispatch_job(job_type="timeline_render", max_concurrent=1)
    assert can_dispatch is False
    assert "Concurrency limit reached" in msg


def test_storage_breakdown_and_safe_cleanup(app_and_client):
    client, settings, layout = app_and_client

    # Place a dummy file in protected media directory
    media_file = layout.media / "test_source_video.mp4"
    media_file.parent.mkdir(parents=True, exist_ok=True)
    media_file.write_bytes(b"\x00" * 5000)

    # Place a disposable cache file in temp directory
    temp_file = layout.temp / "intermediate_chunk.tmp"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_bytes(b"\x00" * 2500)

    # 1. Fetch storage breakdown
    res = client.get("/api/v1/storage/breakdown")
    assert res.status_code == 200
    data = res.json()
    assert "total_disk_space_bytes" in data
    assert "free_disk_space_bytes" in data
    assert data["categories"]["source_media_bytes"] >= 5000
    assert data["categories"]["temp_cache_bytes"] >= 2500

    # 2. Preview cleanup
    prev_res = client.post("/api/v1/storage/cleanup/preview")
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["eligible_files_count"] >= 1
    assert prev_data["total_bytes_to_free"] >= 2500
    token = prev_data["confirmation_token"]
    assert token

    # 3. Execute cleanup with token
    exec_res = client.post(
        "/api/v1/storage/cleanup/execute",
        json={"confirmation_token": token},
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "success"
    assert exec_data["freed_bytes"] >= 2500

    # 4. Verify temp file was deleted but protected media file is intact
    assert not temp_file.exists()
    assert media_file.exists()


def test_database_integrity_and_backups(app_and_client):
    client, settings, layout = app_and_client

    # 1. Database diagnostics
    diag_res = client.get("/api/v1/system/db-integrity")
    assert diag_res.status_code == 200
    diag = diag_res.json()
    assert diag["healthy"] is True
    assert diag["integrity_check"] == "ok"
    assert diag["foreign_key_check"] == "ok"
    assert diag["journal_mode"].lower() == "wal"

    # 2. Create backup snapshot
    bk_res = client.post("/api/v1/backups", json={"label": "test_snap"})
    assert bk_res.status_code == 200
    bk = bk_res.json()
    assert bk["integrity_verified"] is True
    filename = bk["backup_filename"]

    # 3. List backups
    list_res = client.get("/api/v1/backups")
    assert list_res.status_code == 200
    bks = list_res.json()
    assert len(bks) >= 1
    assert any(b["backup_filename"] == filename for b in bks)

    # 4. Restore backup with automatic safety snapshot
    restore_res = client.post("/api/v1/backups/restore", json={"backup_filename": filename})
    assert restore_res.status_code == 200
    r_data = restore_res.json()
    assert r_data["status"] == "success"
    assert "pre_restore" in r_data["safety_snapshot"]

    # 5. Recovery status endpoint
    rec_res = client.get("/api/v1/system/recovery-status")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["recovery_ready"] is True
    assert rec_data["total_backups_available"] >= 2  # Original backup + pre_restore safety snapshot
