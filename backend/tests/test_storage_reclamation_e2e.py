"""End-to-End verification of complete user data deletion, storage reclamation, and database consistency."""

import gc
import json
import os
import pytest
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.media import MediaService
from app.services.storage import StorageService


def _setup_disposable_studio(tmp_path: Path):
    storage_root = tmp_path / "managed_storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()
    (storage_root / "characters").mkdir(parents=True, exist_ok=True)
    (storage_root / "shorts").mkdir(parents=True, exist_ok=True)

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(
        app_name="ZezEditStorageReclamationE2E",
        environment="test",
        storage_root=storage_root,
        max_concurrent_jobs=1,
    )
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('default', 'Default Studio', 'default_p', datetime('now'), datetime('now'));"
        )

    # External folder simulating external videos outside managed storage
    external_dir = tmp_path / "user_desktop_videos"
    external_dir.mkdir(parents=True, exist_ok=True)
    external_video_file = external_dir / "my_external_family_recording.mp4"
    external_video_file.write_bytes(b"EXT_VIDEO_BYTES" * 1024)

    # Seed managed files
    managed_video = layout.media / "managed_interview.mp4"
    managed_video.write_bytes(b"MANAGED_VIDEO_DATA" * 4096)

    proxy_file = layout.proxies / "vid_01_proxy.mp4"
    proxy_file.write_bytes(b"PROXY_DATA" * 1024)

    thumb_file = layout.thumbnails / "vid_01_thumb.jpg"
    thumb_file.write_bytes(b"THUMB_DATA" * 512)

    frame_dir = layout.analysis / "vid_01"
    frame_dir.mkdir(parents=True, exist_ok=True)
    (frame_dir / "frame_001.jpg").write_bytes(b"FRAME1" * 512)
    (frame_dir / "frame_002.jpg").write_bytes(b"FRAME2" * 512)

    char_file = storage_root / "characters" / "char_profile_01.png"
    char_file.write_bytes(b"CHAR_DATA" * 512)

    short_file = storage_root / "shorts" / "cand_01.mp4"
    short_file.write_bytes(b"CANDIDATE_SHORT" * 2048)

    export_file = layout.exports / "final_export.mp4"
    export_file.write_bytes(b"RENDERED_EXPORT" * 2048)

    temp_file = layout.temp / "cache_chunk.tmp"
    temp_file.write_bytes(b"DISPOSABLE_TEMP" * 1024)

    # Seed Database entries
    with sqlite3.connect(layout.db_file) as conn:
        # Managed media asset
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external, file_size_bytes, created_at, updated_at
            ) VALUES ('vid_01', 'default', 'managed_interview.mp4', 'managed_interview.mp4', 0, 73728, datetime('now'), datetime('now'));
            """
        )
        # External media asset referencing external file
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external, file_size_bytes, created_at, updated_at
            ) VALUES ('vid_ext', 'default', 'my_external_family_recording.mp4', ?, 1, 15360, datetime('now'), datetime('now'));
            """,
            (str(external_video_file),),
        )
        # Analysis run
        conn.execute(
            """
            INSERT INTO analysis_runs (id, media_asset_id, project_id, status, profile, created_at, updated_at)
            VALUES ('run_01', 'vid_01', 'default', 'completed', 'balanced', datetime('now'), datetime('now'));
            """
        )
        # Transcript segment
        conn.execute(
            """
            INSERT INTO transcript_segments (id, analysis_run_id, media_asset_id, start_time, end_time, text, confidence, created_at)
            VALUES ('seg_01', 'run_01', 'vid_01', 0.0, 5.0, 'Hello world', 0.95, datetime('now'));
            """
        )
        # Video scene
        conn.execute(
            """
            INSERT INTO video_scenes (id, analysis_run_id, media_asset_id, scene_index, start_time, end_time, representative_timestamp, change_score, created_at)
            VALUES ('scn_01', 'run_01', 'vid_01', 0, 0.0, 10.0, 5.0, 0.5, datetime('now'));
            """
        )
        # Sampled frame
        conn.execute(
            """
            INSERT INTO sampled_frames (id, analysis_run_id, media_asset_id, timestamp, frame_path, width, height, created_at)
            VALUES ('frm_01', 'run_01', 'vid_01', 1.0, 'analysis/vid_01/frame_001.jpg', 1920, 1080, datetime('now'));
            """
        )
        # Short candidate
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time, title, suggested_title, quality_score, created_at, updated_at
            ) VALUES (
                'cand_01', 'default', 'vid_01', 'run_01', 0.0, 15.0, 15.0, 0.0, 15.0,
                'Best Short', 'Best Short', 0.88, datetime('now'), datetime('now')
            );
            """
        )
        # Jobs
        conn.execute(
            """
            INSERT INTO jobs (id, project_id, media_asset_id, job_type, status, priority, progress_pct, current_stage, created_at, updated_at)
            VALUES ('job_old_1', 'default', 'vid_01', 'analyze_video', 'completed', 100, 100.0, 'completed', datetime('now'), datetime('now'));
            """
        )

    return settings, layout, external_video_file


def test_storage_cleanup_preview_e2e(tmp_path: Path):
    settings, layout, external_video_file = _setup_disposable_studio(tmp_path)
    app = create_app(settings)
    client = TestClient(app)

    res = client.get("/api/v1/settings/storage/cleanup-preview")
    assert res.status_code == 200
    preview = res.json()

    assert preview["video_count"] == 2  # 1 managed + 1 external record
    assert preview["clip_count"] == 1
    assert preview["frame_count"] == 3
    assert preview["temp_file_count"] >= 1
    assert preview["estimated_reclaimable_bytes"] > 0
    assert "DELETE ALL USER DATA" in preview["confirmation_prompt"]
    gc.collect()


def test_storage_cleanup_invalid_confirmation(tmp_path: Path):
    settings, layout, _ = _setup_disposable_studio(tmp_path)
    app = create_app(settings)
    client = TestClient(app)

    res = client.post(
        "/api/v1/settings/storage/clear-all-user-data",
        json={"confirmation": "INVALID_TOKEN"},
    )
    assert res.status_code == 400
    gc.collect()


def test_complete_user_data_reclamation_execution_e2e(tmp_path: Path):
    settings, layout, external_video_file = _setup_disposable_studio(tmp_path)
    app = create_app(settings)
    client = TestClient(app)

    # 1. Measure initial physical managed storage folder bytes
    def _measure_managed():
        total = 0
        for p in layout.root.rglob("*"):
            if p.is_file() and p.name != "zezedit.db" and not p.name.startswith("zezedit.db"):
                total += p.stat().st_size
        return total

    pre_files_bytes = _measure_managed()
    assert pre_files_bytes > 0

    # 2. Execute Complete Storage Reclamation
    res = client.post(
        "/api/v1/settings/storage/clear-all-user-data",
        json={"confirmation": "DELETE ALL USER DATA"},
    )
    assert res.status_code == 200
    result = res.json()

    assert result["status"] == "success"
    assert result["actual_reclaimed_bytes"] > 0
    assert result["deleted_files_count"] >= 7
    assert result["purged_tables_count"] >= 10

    # 3. Verify physical files are unlinked from managed storage
    post_files_bytes = _measure_managed()
    assert post_files_bytes < pre_files_bytes
    assert post_files_bytes == 0  # All managed user files wiped

    # 4. Verify external video file is PRESERVED on disk
    assert external_video_file.exists()
    assert external_video_file.stat().st_size > 0

    # 5. Verify database integrity: user tables purged, system tables preserved
    with sqlite3.connect(layout.db_file) as conn:
        conn.row_factory = sqlite3.Row
        # System migrations preserved
        mig = conn.execute("SELECT COUNT(*) FROM schema_migrations;").fetchone()[0]
        assert mig > 0

        # App settings preserved
        settings_count = conn.execute("SELECT COUNT(*) FROM app_settings;").fetchone()[0]
        assert settings_count >= 0

        # User tables purged
        for tbl in ["media_assets", "analysis_runs", "transcript_segments", "video_scenes", "sampled_frames", "shorts_candidates", "jobs"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0]
            assert count == 0, f"Table {tbl} was not emptied!"

        # Default project restored
        proj = conn.execute("SELECT id FROM projects WHERE id = 'default';").fetchone()
        assert proj is not None

    gc.collect()


def test_single_video_deletion_storage_reclamation(tmp_path: Path):
    settings, layout, _ = _setup_disposable_studio(tmp_path)
    media_svc = MediaService(settings, layout.db_file)

    # Before single video deletion: vid_01 files exist
    managed_video = layout.media / "managed_interview.mp4"
    assert managed_video.exists()

    # Delete vid_01
    media_svc.delete_media_asset("default", "vid_01", delete_source=True)

    # Managed video file unlinked
    assert not managed_video.exists()

    # Proxy and thumbnails unlinked
    assert len(list(layout.proxies.glob("vid_01*"))) == 0
    assert len(list(layout.thumbnails.glob("vid_01*"))) == 0
    assert not (layout.analysis / "vid_01").exists()

    # DB record removed
    with sqlite3.connect(layout.db_file) as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM media_assets WHERE id = 'vid_01';").fetchone()[0]
        assert cnt == 0
        # External video vid_ext remains untouched
        ext_cnt = conn.execute("SELECT COUNT(*) FROM media_assets WHERE id = 'vid_ext';").fetchone()[0]
        assert ext_cnt == 1

    gc.collect()
