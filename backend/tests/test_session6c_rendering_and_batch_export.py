"""Comprehensive tests for Session 6C: Real short video rendering, clip editing, batch export, and output verification."""

import gc
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError, NotFoundError, ProcessingError, ValidationError
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.main import create_app
from app.models.export import CaptionConfig, AudioConfig, RenderExportRequest, STANDARD_EXPORT_PRESETS
from app.services.export_service import ExportService
from app.services.clip_editing_service import ClipEditingService
from app.services.jobs import JobOrchestrator


def _create_test_mp4(output_path: Path, duration: float = 3.0, width: int = 640, height: int = 360, with_audio: bool = True) -> Path:
    """Generate a valid synthetic test MP4 video using FFmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration}:size={width}x{height}:rate=30",
    ]
    if with_audio:
        cmd.extend(["-f", "lavfi", "-i", f"sine=frequency=1000:duration={duration}"])
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
    else:
        cmd.extend(["-an"])

    cmd.extend([
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ])
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    assert res.returncode == 0, f"FFmpeg failed to create test MP4: {res.stderr}"
    assert output_path.exists() and output_path.stat().st_size > 0
    return output_path


def _setup_test_env(tmp_path: Path) -> tuple[Settings, StorageLayout, ExportService, ClipEditingService, JobOrchestrator]:
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(
        app_name="ZezEditTestRendering",
        environment="test",
        storage_root=storage_root,
        max_concurrent_jobs=2,
    )
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute("INSERT OR IGNORE INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('default', 'Default Project', 'default_p', datetime('now'), datetime('now'));")

    export_svc = ExportService(settings=settings, db_path=layout.db_file)
    clip_edit_svc = ClipEditingService(settings=settings, db_path=layout.db_file)
    job_svc = JobOrchestrator(settings=settings, db_path=layout.db_file)
    return settings, layout, export_svc, clip_edit_svc, job_svc


def test_standard_presets_catalog_all_aspect_ratios():
    """Verify that all target aspect ratios (9:16, 16:9, 1:1, 4:5, 4:3, 3:4) exist in preset catalog."""
    presets = STANDARD_EXPORT_PRESETS
    assert "shorts_reels_9_16" in presets
    assert "landscape_16_9" in presets
    assert "square_1_1" in presets
    assert "portrait_4_5" in presets
    assert "standard_4_3" in presets
    assert "tall_3_4" in presets

    assert presets["shorts_reels_9_16"].target_aspect_ratio == "9:16"
    assert presets["portrait_4_5"].target_aspect_ratio == "4:5"
    assert presets["standard_4_3"].target_aspect_ratio == "4:3"
    assert presets["tall_3_4"].target_aspect_ratio == "3:4"


def test_render_candidate_with_clip_editing_integration(tmp_path: Path):
    """Verify that a candidate trimmed via ClipEditingService renders the edited interval and aspect ratio."""
    settings, layout, export_svc, clip_edit_svc, job_svc = _setup_test_env(tmp_path)

    # 1. Create a 6-second source video
    source_file = layout.media / "source_interview.mp4"
    _create_test_mp4(source_file, duration=6.0, width=1280, height=720, with_audio=True)

    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, created_at, updated_at)
            VALUES ('run_test1', 'default', 'asset_vid1', 'completed', datetime('now'), datetime('now'));
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, duration_seconds, width, height, created_at, updated_at)
            VALUES ('asset_vid1', 'default', 'source_interview.mp4', 'source_interview.mp4', 6.0, 1280, 720, datetime('now'), datetime('now'));
            """
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time, title, suggested_title, quality_score,
                review_status, created_at, updated_at
            ) VALUES (
                'cand_001', 'default', 'asset_vid1', 'run_test1', 0.5, 5.5, 5.0,
                0.5, 5.5, 'Discovered Hook', 'Discovered Hook', 0.92,
                'approved', datetime('now'), datetime('now')
            );
            """
        )

    # 2. User trims the clip: start=1.5s, end=4.0s (duration=2.5s), aspect ratio="1:1"
    clip_edit = clip_edit_svc.save_edit(
        candidate_id="cand_001",
        project_id="default",
        media_asset_id="asset_vid1",
        edited_start_time=1.5,
        edited_end_time=4.0,
        aspect_ratio="1:1",
        framing_mode="center",
    )
    assert clip_edit["edited_duration"] == 2.5
    assert clip_edit["aspect_ratio"] == "1:1"

    # 3. Submit render without specifying explicit preset -> ExportService automatically inherits clip_edit's 1:1 preset and 2.5s duration
    render_req = RenderExportRequest(
        candidate_id="cand_001",
        title="Trimmed Clip Render",
    )
    submit_res = export_svc.submit_export_job("default", render_req)
    job_id = submit_res["job_id"]
    export_id = submit_res["export_id"]

    # Verify job received media_asset_id for Process Manager linkage
    job_record = job_svc.get_job(job_id)
    assert job_record.media_asset_id == "asset_vid1"
    assert job_record.input_config["clip_start_time"] == 1.5
    assert job_record.input_config["clip_end_time"] == 4.0

    # 4. Execute render
    render_result = export_svc.execute_render_job(job_id)
    assert render_result["status"] == "completed"
    assert render_result["width"] == 1080
    assert render_result["height"] == 1080
    assert 2.0 <= render_result["duration"] <= 3.0

    # 5. Verify published MP4 file exists on disk
    mp4_path = Path(render_result["output_path"])
    assert mp4_path.exists()
    assert mp4_path.stat().st_size > 10_000

    # 6. Verify export record status in database
    exp_record = export_svc.get_export("default", export_id)
    assert exp_record.status == "completed"
    assert exp_record.validation_status == "valid"
    assert exp_record.target_aspect_ratio == "1:1"
    assert exp_record.duration_seconds >= 2.0
    gc.collect()


def test_batch_export_rendering_pipeline(tmp_path: Path):
    """Verify batch rendering multiple candidate clips sequentially without resource contention."""
    settings, layout, export_svc, clip_edit_svc, job_svc = _setup_test_env(tmp_path)

    # Create source video
    source_file = layout.media / "source_lecture.mp4"
    _create_test_mp4(source_file, duration=8.0, width=1280, height=720, with_audio=True)

    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, created_at, updated_at)
            VALUES ('run_test2', 'default', 'asset_lec', 'completed', datetime('now'), datetime('now'));
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, duration_seconds, width, height, created_at, updated_at)
            VALUES ('asset_lec', 'default', 'source_lecture.mp4', 'source_lecture.mp4', 8.0, 1280, 720, datetime('now'), datetime('now'));
            """
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time, title, suggested_title, quality_score,
                review_status, created_at, updated_at
            ) VALUES
            ('cand_b1', 'default', 'asset_lec', 'run_test2', 0.5, 3.0, 2.5, 0.5, 3.0, 'Key Concept 1', 'Key Concept 1', 0.88, 'approved', datetime('now'), datetime('now')),
            ('cand_b2', 'default', 'asset_lec', 'run_test2', 3.5, 6.0, 2.5, 3.5, 6.0, 'Key Concept 2', 'Key Concept 2', 0.94, 'approved', datetime('now'), datetime('now'));
            """
        )

    # Submit batch render for both candidates
    app = create_app(settings)
    client = TestClient(app)

    batch_res = client.post(
        "/api/v1/projects/default/exports/batch?run_synchronously=true",
        json={
            "candidate_ids": ["cand_b1", "cand_b2"],
            "preset_id": "shorts_reels_9_16",
        },
    )
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert batch_data["total_requested"] == 2
    assert batch_data["total_submitted"] == 2
    assert len(batch_data["items"]) == 2

    # Verify both output files were rendered and validated
    for item in batch_data["items"]:
        exp = export_svc.get_export("default", item["export_id"])
        assert exp.status == "completed"
        assert exp.validation_status == "valid"
        assert exp.target_aspect_ratio == "9:16"
        assert exp.target_width == 1080
        assert exp.target_height == 1920
        assert Path(exp.output_path).exists()
    gc.collect()


def test_audio_preservation_and_silent_video_support(tmp_path: Path):
    """Verify that video without audio stream renders without crashing and validates correctly."""
    settings, layout, export_svc, clip_edit_svc, job_svc = _setup_test_env(tmp_path)

    # Create silent video
    silent_file = layout.media / "silent_timelapse.mp4"
    _create_test_mp4(silent_file, duration=4.0, width=640, height=360, with_audio=False)

    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, created_at, updated_at)
            VALUES ('run_test3', 'default', 'asset_silent', 'completed', datetime('now'), datetime('now'));
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, duration_seconds, width, height, created_at, updated_at)
            VALUES ('asset_silent', 'default', 'silent_timelapse.mp4', 'silent_timelapse.mp4', 4.0, 640, 360, datetime('now'), datetime('now'));
            """
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time, title, suggested_title, quality_score,
                review_status, created_at, updated_at
            ) VALUES (
                'cand_sil1', 'default', 'asset_silent', 'run_test3', 0.5, 3.0, 2.5,
                0.5, 3.0, 'Silent Motion', 'Silent Motion', 0.85,
                'approved', datetime('now'), datetime('now')
            );
            """
        )

    render_req = RenderExportRequest(
        candidate_id="cand_sil1",
        preset_id="square_1_1",
    )
    submit_res = export_svc.submit_export_job("default", render_req)
    render_result = export_svc.execute_render_job(submit_res["job_id"])

    assert render_result["status"] == "completed"
    assert render_result["width"] == 1080
    assert render_result["height"] == 1080
    assert Path(render_result["output_path"]).exists()
    gc.collect()


def test_output_verification_rejects_corrupted_renders(tmp_path: Path):
    """Verify that OutputValidator fails and does not publish zero-byte or corrupt files."""
    settings, layout, export_svc, clip_edit_svc, job_svc = _setup_test_env(tmp_path)

    fake_file = tmp_path / "corrupt_fake.mp4"
    fake_file.write_text("corrupted content not an mp4")

    val_result = export_svc.validator.validate_export(
        file_path=fake_file,
        expected_duration=5.0,
        expected_width=1080,
        expected_height=1920,
    )
    assert not val_result.is_valid
    assert len(val_result.errors) > 0
    gc.collect()
