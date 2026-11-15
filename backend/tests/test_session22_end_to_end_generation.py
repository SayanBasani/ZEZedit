"""Session 22 Authoritative Acceptance Tests: End-to-End Generation Repair,
Real Video Export Verification, Tab Counts, Job Lifecycle & Recovery.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List
import pytest
from starlette.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.main import create_app
from app.services.export_service import ExportService
from app.services.highlight_discovery import HighlightDiscoveryEngine


@pytest.fixture
def client(tmp_path) -> TestClient:
    real_migrations = Path(__file__).resolve().parent.parent / "migrations"
    settings = Settings(
        app_name="ZezEditSession22Test",
        storage_root=tmp_path / "storage",
        migrations_dir=real_migrations,
        environment="test",
        max_concurrent_jobs=3,
    )
    app = create_app(settings_override=settings)
    with TestClient(app) as test_client:
        yield test_client


def create_synthetic_test_video(output_path: Path, duration: int = 12, width: int = 640, height: int = 360) -> Path:
    """Generate a clean synthetic video with video and audio streams for test exports."""
    import cv2
    import numpy as np

    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_video = output_path.with_suffix(".raw.mp4")
    fps = 10
    total_frames = duration * fps
    writer = cv2.VideoWriter(str(raw_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for f in range(total_frames):
        img = np.zeros((height, width, 3), dtype=np.uint8)
        x = int(40 + 440 * (f / max(1, total_frames - 1)))
        cv2.rectangle(img, (x, 100), (x + 80, 240), (255, 255, 255), -1)
        writer.write(img)
    writer.release()

    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        "-shortest", str(output_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if raw_video.exists():
        raw_video.unlink()
    return output_path


def test_five_candidates_generate_five_exports_and_mp4s(client: TestClient):
    """Test 1: Five candidates discovered during Generate Shorts create five export jobs,

    which all execute and create physical, FFprobe-valid MP4 short videos automatically.
    """
    proj_res = client.post("/api/v1/projects", json={"name": "End-to-End 5 Renders Project"})
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_5_renders_test"
    now_iso = "2026-11-15T12:00:00Z"

    synth_video = layout.media / "test_5_renders.mp4"
    create_synthetic_test_video(synth_video, duration=25, width=640, height=360)

    # Seed media asset and completed analysis with 5 speech turns
    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, '5_renders.mp4', ?, 'video', ?, 25.0, 640, 360, 0, 'ready', ?, ?)
            """,
            (asset_id, pid, str(synth_video), synth_video.stat().st_size, now_iso, now_iso),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, project_id, media_asset_id, status, profile,
                progress_pct, current_stage, created_at, updated_at
            ) VALUES ('run_5_01', ?, ?, 'completed', 'balanced', 100.0, 'completed', ?, ?)
            """,
            (pid, asset_id, now_iso, now_iso),
        )
        # 5 distinct speech turns
        conn.execute(
            """
            INSERT INTO speech_turns (id, analysis_run_id, media_asset_id, start_time, end_time, speaker_label, text, turn_type, created_at)
            VALUES 
            ('t1', 'run_5_01', ?, 0.5, 4.0, 'Host', 'Welcome to the ultimate video guide.', 'statement', ?),
            ('t2', 'run_5_01', ?, 5.0, 8.5, 'Guest', 'The secret lies in proper execution.', 'statement', ?),
            ('t3', 'run_5_01', ?, 9.5, 13.0, 'Host', 'Notice how smooth the transition feels.', 'statement', ?),
            ('t4', 'run_5_01', ?, 14.0, 18.0, 'Guest', 'That changes the entire outcome immediately.', 'exclamation', ?),
            ('t5', 'run_5_01', ?, 19.0, 23.5, 'Host', 'Subscribe and check out the next clip.', 'statement', ?)
            """,
            (asset_id, now_iso, asset_id, now_iso, asset_id, now_iso, asset_id, now_iso, asset_id, now_iso),
        )
        conn.execute(
            """
            INSERT INTO transcript_segments (id, analysis_run_id, media_asset_id, start_time, end_time, text, language, confidence, words_json, created_at)
            VALUES 
            ('s1', 'run_5_01', ?, 0.5, 4.0, 'Welcome to the ultimate video guide.', 'en', 0.95, '[]', ?),
            ('s2', 'run_5_01', ?, 5.0, 8.5, 'The secret lies in proper execution.', 'en', 0.95, '[]', ?),
            ('s3', 'run_5_01', ?, 9.5, 13.0, 'Notice how smooth the transition feels.', 'en', 0.95, '[]', ?),
            ('s4', 'run_5_01', ?, 14.0, 18.0, 'That changes the entire outcome immediately.', 'en', 0.95, '[]', ?),
            ('s5', 'run_5_01', ?, 19.0, 23.5, 'Subscribe and check out the next clip.', 'en', 0.95, '[]', ?)
            """,
            (asset_id, now_iso, asset_id, now_iso, asset_id, now_iso, asset_id, now_iso, asset_id, now_iso),
        )
        conn.execute(
            """
            INSERT INTO video_scenes (id, analysis_run_id, media_asset_id, scene_index, start_time, end_time, representative_timestamp, change_score, created_at)
            VALUES 
            ('sc1', 'run_5_01', ?, 0, 0.0, 5.0, 2.5, 0.8, ?),
            ('sc2', 'run_5_01', ?, 1, 5.0, 10.0, 7.5, 0.8, ?),
            ('sc3', 'run_5_01', ?, 2, 10.0, 15.0, 12.5, 0.8, ?),
            ('sc4', 'run_5_01', ?, 3, 15.0, 20.0, 17.5, 0.8, ?),
            ('sc5', 'run_5_01', ?, 4, 20.0, 25.0, 22.5, 0.8, ?)
            """,
            (asset_id, now_iso, asset_id, now_iso, asset_id, now_iso, asset_id, now_iso, asset_id, now_iso),
        )

    # Submit Generate Shorts with auto_render=True and run_synchronously=True
    res = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/highlights/discover",
        json={
            "analysis_run_id": "run_5_01",
            "target_clip_count": 5,
            "min_duration": 3.0,
            "max_duration": 5.0,
            "auto_render": True,
            "run_synchronously": True,
        },
    )
    assert res.status_code == 202
    candidates = res.json()
    assert len(candidates) == 5, f"Expected 5 candidates, got {len(candidates)}"

    # Verify that exactly 5 export records were created in SQLite
    exp_res = client.get(f"/api/v1/projects/{pid}/exports?media_asset_id={asset_id}")
    assert exp_res.status_code == 200
    exp_items = exp_res.json()["items"]
    assert len(exp_items) == 5, f"Expected 5 exports, got {len(exp_items)}"

    # Verify each export is completed and has a physical, valid MP4 file on disk
    for exp in exp_items:
        assert exp["status"] == "completed"
        output_path = Path(exp["output_path"])
        assert output_path.exists(), f"MP4 file does not exist at {output_path}"
        assert output_path.stat().st_size > 1000

        # Validate with FFprobe
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,codec_name",
            "-of", "default=noprint_wrappers=1",
            str(output_path),
        ]
        probe_run = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        assert "h264" in probe_run.stdout
        assert "width=1080" in probe_run.stdout
        assert "height=1920" in probe_run.stdout


def test_failed_render_preserves_script_and_retry_works(client: TestClient):
    """Test 2: A failed render preserves the candidate script record,

    marks the export as 'failed' with error_message, and can be retried successfully.
    """
    proj_res = client.post("/api/v1/projects", json={"name": "Retry Test Project"})
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_retry_test"
    synth_video = layout.media / "test_retry.mp4"
    create_synthetic_test_video(synth_video, duration=8, width=640, height=360)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, media_type, file_size_bytes, duration_seconds, width, height, is_external, proxy_status, created_at, updated_at)
            VALUES (?, ?, 'retry.mp4', ?, 'video', ?, 8.0, 640, 360, 0, 'ready', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (asset_id, pid, str(synth_video), synth_video.stat().st_size),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, profile, progress_pct, current_stage, created_at, updated_at)
            VALUES ('run_ret_01', ?, ?, 'completed', 'balanced', 100.0, 'completed', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (pid, asset_id),
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time,
                suggested_start_time, suggested_end_time, duration, title, suggested_title,
                quality_score, review_status, created_at, updated_at
            ) VALUES ('cand_ret_01', ?, ?, 'run_ret_01', 1.0, 5.0, 1.0, 5.0, 4.0, 'Retry Candidate', 'Retry Candidate', 88.0, 'approved', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (pid, asset_id),
        )

    # 1. Submit export render with valid candidate
    exp_res = client.post(
        f"/api/v1/projects/{pid}/exports/render?run_synchronously=true",
        json={"candidate_id": "cand_ret_01", "preset_id": "shorts_reels_9_16"},
    )
    assert exp_res.status_code == 200
    exp_id = exp_res.json()["export_id"]

    # 2. Simulate failure by updating status to failed with error message
    with sqlite_session(db_path) as conn:
        conn.execute(
            "UPDATE exports SET status = 'failed', error_message = 'Simulated GPU OOM render crash' WHERE id = ?",
            (exp_id,),
        )

    # Verify export endpoint returns failed export with reason
    item_res = client.get(f"/api/v1/projects/{pid}/exports/{exp_id}")
    assert item_res.status_code == 200
    failed_item = item_res.json()
    assert failed_item["status"] == "failed"
    assert "Simulated" in failed_item["error_message"]

    # Candidate script record is 100% PRESERVED
    cand_check = client.get(f"/api/v1/projects/{pid}/media/{asset_id}/highlights")
    assert cand_check.status_code == 200
    cands = cand_check.json()
    assert len(cands) == 1
    assert cands[0]["id"] == "cand_ret_01"

    # 3. Retry Render on the same candidate
    retry_res = client.post(
        f"/api/v1/projects/{pid}/exports/render?run_synchronously=true",
        json={"candidate_id": "cand_ret_01", "preset_id": "shorts_reels_9_16"},
    )
    assert retry_res.status_code == 200
    retry_exp_id = retry_res.json()["export_id"]
    retry_item = client.get(f"/api/v1/projects/{pid}/exports/{retry_exp_id}").json()
    assert retry_item["status"] == "completed"
    assert Path(retry_item["output_path"]).exists()


def test_batch_render_recovery_action(client: TestClient):
    """Test 3: Batch render missing videos endpoint recovers candidates without valid exports,

    and ignores candidates that already have completed or active exports.
    """
    proj_res = client.post("/api/v1/projects", json={"name": "Batch Recovery Project"})
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_batch_rec"
    synth_video = layout.media / "test_batch_rec.mp4"
    create_synthetic_test_video(synth_video, duration=10, width=640, height=360)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, media_type, file_size_bytes, duration_seconds, width, height, is_external, proxy_status, created_at, updated_at)
            VALUES (?, ?, 'rec.mp4', ?, 'video', ?, 10.0, 640, 360, 0, 'ready', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (asset_id, pid, str(synth_video), synth_video.stat().st_size),
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, profile, progress_pct, current_stage, created_at, updated_at)
            VALUES ('run_rec_01', ?, ?, 'completed', 'balanced', 100.0, 'completed', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (pid, asset_id),
        )
        # Create 3 candidates: C1 (already completed export), C2 (unrendered), C3 (unrendered)
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time,
                suggested_start_time, suggested_end_time, duration, title, suggested_title,
                quality_score, review_status, created_at, updated_at
            ) VALUES 
            ('c1', ?, ?, 'run_rec_01', 0.0, 3.0, 0.0, 3.0, 3.0, 'Clip 1', 'Clip 1', 80.0, 'approved', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z'),
            ('c2', ?, ?, 'run_rec_01', 3.0, 6.0, 3.0, 6.0, 3.0, 'Clip 2', 'Clip 2', 85.0, 'approved', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z'),
            ('c3', ?, ?, 'run_rec_01', 6.0, 9.0, 6.0, 9.0, 3.0, 'Clip 3', 'Clip 3', 82.0, 'approved', '2026-11-15T12:00:00Z', '2026-11-15T12:00:00Z')
            """,
            (pid, asset_id, pid, asset_id, pid, asset_id),
        )

    # Export C1 synchronously so it is already completed
    res_c1 = client.post(
        f"/api/v1/projects/{pid}/exports/render?run_synchronously=true",
        json={"candidate_id": "c1", "preset_id": "shorts_reels_9_16"},
    )
    assert res_c1.status_code == 200

    # Call batch export with all 3 candidate IDs
    batch_res = client.post(
        f"/api/v1/projects/{pid}/exports/batch?run_synchronously=true",
        json={"candidate_ids": ["c1", "c2", "c3"], "preset_id": "shorts_reels_9_16"},
    )
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert batch_data["total_requested"] == 3
    # c2 and c3 submitted, c1 either skipped or reused
    assert len(batch_data["items"]) >= 2

    # Query all exports for asset
    all_exps = client.get(f"/api/v1/projects/{pid}/exports?media_asset_id={asset_id}").json()["items"]
    cand_ids = {e["candidate_id"] for e in all_exps if e["status"] == "completed"}
    assert "c1" in cand_ids
    assert "c2" in cand_ids
    assert "c3" in cand_ids
