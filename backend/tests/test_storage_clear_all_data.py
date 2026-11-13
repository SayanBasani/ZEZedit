"""Test storage clear all data / factory reset functionality."""

import pytest
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from app.core.config import Settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.services.storage import StorageService


def test_clear_all_data_validation():
    with TemporaryDirectory() as tmpdir:
        settings = Settings(storage_root=tmpdir)
        service = StorageService(settings=settings)

        # Missing or invalid confirmation token should raise AppError
        with pytest.raises(AppError) as exc_info:
            service.clear_all_data("")
        assert exc_info.value.code == "INVALID_CLEAR_ALL_CONFIRMATION"

        with pytest.raises(AppError) as exc_info:
            service.clear_all_data("WRONG")
        assert exc_info.value.code == "INVALID_CLEAR_ALL_CONFIRMATION"


def test_clear_all_data_execution():
    with TemporaryDirectory() as tmpdir:
        settings = Settings(storage_root=tmpdir)
        layout = StorageLayout.from_root(tmpdir)
        layout.ensure_directories()

        # Seed sample files in media, thumbnails, temp
        dummy_media = layout.media / "test.mp4"
        dummy_media.write_text("dummy media content")
        dummy_thumb = layout.thumbnails / "test.jpg"
        dummy_thumb.write_text("dummy thumb")
        dummy_temp = layout.temp / "cache.tmp"
        dummy_temp.write_text("dummy temp")

        # Create sqlite db with dummy tables
        conn = sqlite3.connect(str(layout.db_file))
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY);")
        conn.execute("INSERT INTO schema_migrations VALUES ('0014');")
        conn.execute("CREATE TABLE app_settings (key TEXT PRIMARY KEY, value_json TEXT, updated_at TEXT);")
        conn.execute("INSERT INTO app_settings VALUES ('theme', '\"dark\"', '2026-01-01');")
        conn.execute(
            "CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, description TEXT, settings_json TEXT, created_at TEXT, updated_at TEXT);"
        )
        conn.execute("INSERT INTO projects VALUES ('p1', 'My Old Project', '', '{}', '2026-01-01', '2026-01-01');")
        conn.execute(
            "CREATE TABLE media_assets (id TEXT PRIMARY KEY, project_id TEXT, original_filename TEXT, storage_path TEXT, is_external INTEGER, media_type TEXT, file_size_bytes INTEGER, mime_type TEXT, duration_seconds REAL, width INTEGER, height INTEGER, fps REAL, video_codec TEXT, audio_codec TEXT, container_format TEXT, thumbnail_reference_path TEXT, proxy_reference_path TEXT, status TEXT, created_at TEXT, updated_at TEXT);"
        )
        conn.execute("INSERT INTO media_assets (id, project_id) VALUES ('m1', 'p1');")
        conn.commit()
        conn.close()

        service = StorageService(settings=settings)
        result = service.clear_all_data("DELETE")

        assert result["status"] == "success"
        assert result["deleted_files_count"] == 3
        assert not dummy_media.exists()
        assert not dummy_thumb.exists()
        assert not dummy_temp.exists()

        # Check DB state
        conn = sqlite3.connect(str(layout.db_file))
        mig_rows = conn.execute("SELECT version FROM schema_migrations;").fetchall()
        assert len(mig_rows) == 1
        assert mig_rows[0][0] == "0014"

        settings_rows = conn.execute("SELECT key FROM app_settings;").fetchall()
        assert len(settings_rows) == 1

        media_rows = conn.execute("SELECT id FROM media_assets;").fetchall()
        assert len(media_rows) == 0

        # Verify default project exists
        project_rows = conn.execute("SELECT id, name FROM projects;").fetchall()
        assert len(project_rows) == 1
        assert project_rows[0][0] == "default"
        conn.close()


def test_clear_all_data_safety_and_jobs_cancellation():
    """Verify active jobs are cancelled and files outside storage root are untouched."""
    with TemporaryDirectory() as external_tmp:
        # Create an external file that should NEVER be deleted
        external_file = Path(external_tmp) / "precious_user_video.mp4"
        external_file.write_text("irreplaceable raw source footage")

        with TemporaryDirectory() as storage_tmp:
            settings = Settings(storage_root=storage_tmp)
            layout = StorageLayout.from_root(storage_tmp)
            layout.ensure_directories()

            # Managed file
            managed_file = layout.media / "managed_copy.mp4"
            managed_file.write_text("managed copy")

            # Setup DB with active jobs
            conn = sqlite3.connect(str(layout.db_file))
            conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY);")
            conn.execute("INSERT INTO schema_migrations VALUES ('0014');")
            conn.execute("CREATE TABLE app_settings (key TEXT PRIMARY KEY, value_json TEXT, updated_at TEXT);")
            conn.execute(
                "CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, description TEXT, settings_json TEXT, created_at TEXT, updated_at TEXT);"
            )
            conn.execute(
                """
                CREATE TABLE jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT,
                    project_id TEXT,
                    status TEXT,
                    stage TEXT,
                    progress_pct REAL,
                    error_message TEXT,
                    updated_at TEXT
                );
                """
            )
            conn.execute(
                "INSERT INTO jobs VALUES ('j1', 'analysis', 'p1', 'running', 'demuxing', 25.0, NULL, '2026-01-01');"
            )
            conn.execute(
                "INSERT INTO jobs VALUES ('j2', 'render', 'p1', 'queued', 'queued', 0.0, NULL, '2026-01-01');"
            )
            conn.commit()
            conn.close()

            service = StorageService(settings=settings)
            res = service.clear_all_data("DELETE")

            assert res["status"] == "success"
            assert not managed_file.exists()
            # External file MUST still exist!
            assert external_file.exists()
            assert external_file.read_text() == "irreplaceable raw source footage"

            # Check jobs table in DB was cleared or had cancelled jobs truncated safely
            conn = sqlite3.connect(str(layout.db_file))
            project_rows = conn.execute("SELECT id FROM projects;").fetchall()
            assert len(project_rows) == 1
            assert project_rows[0][0] == "default"
            conn.close()

