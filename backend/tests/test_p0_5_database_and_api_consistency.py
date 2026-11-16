"""Tests for P0.5: Database & API consistency, foreign-key enforcement, safe reconciliation, and path safety."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import create_sqlite_connection, sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.backup_service import BackupService
from app.services.export_service import ExportService


@pytest.fixture
def p05_env(tmp_path: Path):
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    # Run migrations
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(
        app_name="ZezEditTest",
        storage_root=storage_root,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
    )

    app = create_app(settings)
    client = TestClient(app)

    # Seed baseline project and media asset
    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, storage_subdir, created_at, updated_at)
            VALUES ('default', 'Test Project', 'default', '2026-11-15T00:00:00Z', '2026-11-15T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, file_size_bytes, duration_seconds, availability_status, created_at, updated_at)
            VALUES ('med_test1', 'default', 'test_video.mp4', 'media/default/test_video.mp4', 1048576, 60.0, 'present', '2026-11-15T00:00:00Z', '2026-11-15T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, profile, created_at, updated_at)
            VALUES ('run_test1', 'default', 'med_test1', 'completed', 'balanced', '2026-11-15T00:00:00Z', '2026-11-15T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration, suggested_start_time, suggested_end_time, title, suggested_title, created_at, updated_at)
            VALUES ('cand_test1', 'default', 'med_test1', 'run_test1', 10.0, 25.0, 15.0, 10.0, 25.0, 'Candidate One', 'Candidate One', '2026-11-15T00:00:00Z', '2026-11-15T00:00:00Z')
            """
        )

    return {
        "storage_root": storage_root,
        "layout": layout,
        "db_path": layout.db_file,
        "settings": settings,
        "app": app,
        "client": client,
        "backup_service": BackupService(layout.db_file, layout.backups),
        "export_service": ExportService(settings, layout.db_file),
    }


def test_foreign_key_enforcement_on_connection(p05_env):
    """Verify that every connection created via connection factory enforces foreign keys."""
    conn = create_sqlite_connection(p05_env["db_path"])
    try:
        fk_val = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_val == 1, "Foreign keys must be enabled (1) by create_sqlite_connection."

        # Verify foreign key constraint blocks orphaned insert
        with pytest.raises(Exception):
            conn.execute(
                """
                INSERT INTO exports (id, project_id, media_asset_id, title, output_filename, created_at)
                VALUES ('exp_bad', 'nonexistent_project', 'med_test1', 'Bad Export', 'bad.mp4', '2026-11-15T00:00:00Z')
                """
            )
    finally:
        conn.close()


def test_valid_export_streaming_and_download(p05_env):
    """Verify streaming and download endpoints for a real, existing export file."""
    client = p05_env["client"]
    storage_root = p05_env["storage_root"]
    db_path = p05_env["db_path"]

    # Create dummy export file inside storage/exports/default/
    exports_dir = storage_root / "exports" / "default"
    exports_dir.mkdir(parents=True, exist_ok=True)
    video_file = exports_dir / "valid_test_video.mp4"
    dummy_bytes = b"\x00" * 4096
    video_file.write_bytes(dummy_bytes)

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, file_size_bytes, duration_seconds, status, validation_status, created_at)
            VALUES ('exp_valid1', 'default', 'cand_test1', 'med_test1', 'Valid Video', ?, 'valid_test_video.mp4', 4096, 15.0, 'completed', 'valid', '2026-11-15T00:00:00Z')
            """,
            (str(video_file),),
        )

    # 1. Stream full or range
    res_stream = client.get("/api/v1/projects/default/exports/exp_valid1/video", headers={"Range": "bytes=0-1023"})
    assert res_stream.status_code == 206
    assert res_stream.headers.get("content-type") == "video/mp4"
    assert "bytes 0-1023/4096" in res_stream.headers.get("content-range", "")
    assert len(res_stream.content) == 1024

    # 2. Download attachment
    res_down = client.get("/api/v1/projects/default/exports/exp_valid1/download")
    assert res_down.status_code == 200
    assert "attachment" in res_down.headers.get("content-disposition", "")
    assert "Valid-Video.mp4" in res_down.headers.get("content-disposition", "")
    assert len(res_down.content) == 4096


def test_missing_export_file_behavior(p05_env):
    """Verify streaming and download for an export whose file does not exist returns 404."""
    client = p05_env["client"]
    db_path = p05_env["db_path"]
    storage_root = p05_env["storage_root"]
    missing_path = storage_root / "exports" / "default" / "missing_video.mp4"

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, file_size_bytes, duration_seconds, status, validation_status, created_at)
            VALUES ('exp_missing1', 'default', 'cand_test1', 'med_test1', 'Missing Video', ?, 'missing_video.mp4', 1000, 10.0, 'completed', 'valid', '2026-11-15T00:00:00Z')
            """,
            (str(missing_path),),
        )

    # Streaming missing file -> 404
    res_stream = client.get("/api/v1/projects/default/exports/exp_missing1/video")
    assert res_stream.status_code == 404
    assert "missing" in res_stream.json()["detail"].lower()

    # Download missing file -> 404
    res_down = client.get("/api/v1/projects/default/exports/exp_missing1/download")
    assert res_down.status_code == 404
    assert "missing" in res_down.json()["detail"].lower()


def test_invalid_out_of_root_path_rejection(p05_env):
    """Verify that export paths attempting to escape storage root are rejected with 403."""
    client = p05_env["client"]
    db_path = p05_env["db_path"]

    # Outside storage root path
    outside_file = Path("C:/Windows/System32/drivers/etc/hosts")

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, file_size_bytes, duration_seconds, status, validation_status, created_at)
            VALUES ('exp_traversal', 'default', 'cand_test1', 'med_test1', 'Hacked', ?, 'hosts', 100, 1.0, 'completed', 'valid', '2026-11-15T00:00:00Z')
            """,
            (str(outside_file),),
        )

    res_stream = client.get("/api/v1/projects/default/exports/exp_traversal/video")
    assert res_stream.status_code == 403
    assert "outside allowed storage root" in res_stream.json()["detail"]

    res_down = client.get("/api/v1/projects/default/exports/exp_traversal/download")
    assert res_down.status_code == 403
    assert "outside allowed storage root" in res_down.json()["detail"]


def test_export_deletion_preserves_candidate_and_media(p05_env):
    """Verify that deleting an export deletes the file & row, but preserves candidate and media asset."""
    client = p05_env["client"]
    storage_root = p05_env["storage_root"]
    db_path = p05_env["db_path"]

    exports_dir = storage_root / "exports" / "default"
    exports_dir.mkdir(parents=True, exist_ok=True)
    video_file = exports_dir / "delete_target.mp4"
    video_file.write_bytes(b"dummy")

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, file_size_bytes, duration_seconds, status, validation_status, created_at)
            VALUES ('exp_del1', 'default', 'cand_test1', 'med_test1', 'Delete Target', ?, 'delete_target.mp4', 5, 2.0, 'completed', 'valid', '2026-11-15T00:00:00Z')
            """,
            (str(video_file),),
        )

    assert video_file.exists()

    # Delete export via API
    res_del = client.delete("/api/v1/projects/default/exports/exp_del1")
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] is True

    # File unlinked
    assert not video_file.exists()

    # Row gone from exports
    with sqlite_session(db_path) as conn:
        exp_row = conn.execute("SELECT id FROM exports WHERE id = 'exp_del1'").fetchone()
        assert exp_row is None

        # Candidate still exists!
        cand_row = conn.execute("SELECT id FROM shorts_candidates WHERE id = 'cand_test1'").fetchone()
        assert cand_row is not None

        # Media asset still exists!
        med_row = conn.execute("SELECT id FROM media_assets WHERE id = 'med_test1'").fetchone()
        assert med_row is not None

    # Repeated delete returns 404
    res_repeat = client.delete("/api/v1/projects/default/exports/exp_del1")
    assert res_repeat.status_code == 404


def test_reconciliation_repeatability_and_idempotency(p05_env):
    """Verify that reconcile_database_consistency resolves FK violations and missing files, and is idempotent."""
    db_path = p05_env["db_path"]
    backup_service = p05_env["backup_service"]

    # Insert orphaned FK rows and missing completed export rows
    with sqlite_session(db_path) as conn:
        # Temporarily disable foreign keys during test setup to simulate legacy inconsistency
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, status, validation_status, created_at)
            VALUES ('exp_orphan_fk', 'default', 'cand_nonexistent', 'med_test1', 'Orphan FK', 'D:/missing/vid.mp4', 'vid.mp4', 'completed', 'valid', '2026-11-15T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT INTO reframing_plans (id, project_id, media_asset_id, candidate_id, target_aspect_ratio, source_width, source_height, start_time, end_time, duration, created_at, updated_at)
            VALUES ('ref_orphan_fk', 'default', 'med_test1', 'cand_nonexistent', '9:16', 1920, 1080, 0.0, 10.0, 10.0, '2026-11-15T00:00:00Z', '2026-11-15T00:00:00Z')
            """
        )

    # First reconciliation pass
    run1 = backup_service.reconcile_database_consistency()
    assert run1["status"] == "success"
    assert run1["foreign_key_violations_fixed"] == 2  # 1 in exports, 1 in reframing_plans
    assert "exp_orphan_fk" in run1["missing_exports_reconciled"]
    assert run1["remaining_foreign_key_violations"] == 0
    assert run1["integrity_check"] == "ok"

    # Verify state in DB
    with sqlite_session(db_path) as conn:
        exp_row = conn.execute("SELECT candidate_id, status, validation_status, error_message FROM exports WHERE id = 'exp_orphan_fk'").fetchone()
        assert exp_row["candidate_id"] is None
        assert exp_row["status"] == "failed"
        assert exp_row["validation_status"] == "invalid"
        assert "missing from storage disk" in exp_row["error_message"]

        ref_row = conn.execute("SELECT candidate_id FROM reframing_plans WHERE id = 'ref_orphan_fk'").fetchone()
        assert ref_row["candidate_id"] is None

    # Second reconciliation pass (Idempotency)
    run2 = backup_service.reconcile_database_consistency()
    assert run2["status"] == "success"
    assert run2["foreign_key_violations_fixed"] == 0
    assert run2["missing_exports_reconciled"] == []
    assert run2["remaining_foreign_key_violations"] == 0
    assert run2["integrity_check"] == "ok"


def test_diagnostics_endpoint_reporting(p05_env):
    """Verify /system/db-integrity and /system/db-reconcile API endpoints."""
    client = p05_env["client"]

    # Integrity check endpoint
    res_diag = client.get("/api/v1/system/db-integrity")
    assert res_diag.status_code == 200
    diag_data = res_diag.json()
    assert diag_data["healthy"] is True
    assert diag_data["integrity_check"] == "ok"
    assert diag_data["foreign_key_check"] == "ok"
    assert diag_data["journal_mode"] == "WAL"

    # Reconcile endpoint
    res_rec = client.post("/api/v1/system/db-reconcile")
    assert res_rec.status_code == 200
    rec_data = res_rec.json()
    assert rec_data["status"] == "success"
    assert rec_data["remaining_foreign_key_violations"] == 0


def test_reconciliation_transaction_rollback_on_interruption(p05_env):
    """Verify that if an error interrupts reconciliation, the entire transaction rolls back cleanly."""
    db_path = p05_env["db_path"]
    backup_service = p05_env["backup_service"]

    # Seed an orphan foreign key and a missing export
    with sqlite_session(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, status, validation_status, created_at)
            VALUES ('exp_rollback_test', 'default', 'cand_nonexistent_rb', 'med_test1', 'Rollback Target', 'D:/missing/rb.mp4', 'rb.mp4', 'completed', 'valid', '2026-11-15T00:00:00Z')
            """
        )

    # Monkeypatch conn.execute to simulate a crash/failure during the reframing_plans step
    original_sqlite_session = sqlite_session

    class InterruptedConnection:
        def __init__(self, real_conn):
            self._real = real_conn
            self._ref_plans_called = False

        def execute(self, sql, *args, **kwargs):
            if "UPDATE reframing_plans" in sql:
                self._ref_plans_called = True
                raise RuntimeError("Simulated crash mid-reconciliation")
            return self._real.execute(sql, *args, **kwargs)

        def cursor(self):
            return self._real.cursor()

        def commit(self):
            return self._real.commit()

        def rollback(self):
            return self._real.rollback()

        def close(self):
            return self._real.close()

    from contextlib import contextmanager

    @contextmanager
    def mock_session(path):
        with original_sqlite_session(path) as real_conn:
            yield InterruptedConnection(real_conn)

    import app.services.backup_service as bs_module

    old_session = bs_module.sqlite_session
    bs_module.sqlite_session = mock_session
    try:
        with pytest.raises(RuntimeError, match="Simulated crash mid-reconciliation"):
            backup_service.reconcile_database_consistency()
    finally:
        bs_module.sqlite_session = old_session

    # Verify atomic rollback: candidate_id was NOT committed to NULL; status remained 'completed'
    with sqlite_session(db_path) as conn:
        row = conn.execute(
            "SELECT candidate_id, status FROM exports WHERE id = 'exp_rollback_test'"
        ).fetchone()
        assert row["candidate_id"] == "cand_nonexistent_rb", "Candidate ID must not be modified after rollback."
        assert row["status"] == "completed", "Status must remain completed after rollback."


def test_concurrent_reconciliation_requests(p05_env):
    """Verify that multiple simultaneous reconciliation requests execute safely without deadlock or data corruption."""
    from concurrent.futures import ThreadPoolExecutor
    backup_service = p05_env["backup_service"]

    def run_reconcile():
        return backup_service.reconcile_database_consistency()

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_reconcile) for _ in range(4)]
        results = [f.result() for f in futures]

    for res in results:
        assert res["status"] == "success"
        assert res["remaining_foreign_key_violations"] == 0
        assert res["integrity_check"] == "ok"


def test_reconciliation_during_active_export_operation(p05_env):
    """Verify that reconciliation safely runs concurrently while an export operation writes to the database."""
    from concurrent.futures import ThreadPoolExecutor
    import time
    db_path = p05_env["db_path"]
    storage_root = p05_env["storage_root"]
    backup_service = p05_env["backup_service"]

    # Prepare physical video for export
    exports_dir = storage_root / "exports" / "default"
    exports_dir.mkdir(parents=True, exist_ok=True)
    active_video = exports_dir / "active_export.mp4"
    active_video.write_bytes(b"content")

    def insert_active_export():
        time.sleep(0.01)
        with sqlite_session(db_path) as conn:
            conn.execute(
                """
                INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, status, validation_status, created_at)
                VALUES ('exp_active_concurrent', 'default', 'cand_test1', 'med_test1', 'Active Concurrent', ?, 'active_export.mp4', 'completed', 'valid', '2026-11-15T00:00:00Z')
                """,
                (str(active_video),),
            )
        return "inserted"

    def reconcile():
        return backup_service.reconcile_database_consistency()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(insert_active_export)
        f2 = executor.submit(reconcile)
        res_insert = f1.result()
        res_reconcile = f2.result()

    assert res_insert == "inserted"
    assert res_reconcile["status"] == "success"
    assert res_reconcile["integrity_check"] == "ok"

    # Verify active export was not marked as failed because physical file existed
    with sqlite_session(db_path) as conn:
        row = conn.execute("SELECT status, validation_status FROM exports WHERE id = 'exp_active_concurrent'").fetchone()
        assert row["status"] == "completed"
        assert row["validation_status"] == "valid"


def test_foreign_key_enforcement_across_independent_connections(p05_env):
    """Verify that PRAGMA foreign_keys is strictly enabled across multiple independent connections."""
    db_path = p05_env["db_path"]

    conn1 = create_sqlite_connection(db_path)
    conn2 = create_sqlite_connection(db_path)
    try:
        assert conn1.execute("PRAGMA foreign_keys;").fetchone()[0] == 1
        assert conn2.execute("PRAGMA foreign_keys;").fetchone()[0] == 1

        # Inserting an invalid foreign key in conn1 fails
        with pytest.raises(Exception):
            conn1.execute(
                """
                INSERT INTO exports (id, project_id, media_asset_id, candidate_id, title, output_filename, created_at)
                VALUES ('exp_fk_fail', 'default', 'med_test1', 'cand_does_not_exist', 'Title', 'f.mp4', '2026-11-15T00:00:00Z')
                """
            )

        # Inserting an invalid foreign key in conn2 fails as well
        with pytest.raises(Exception):
            conn2.execute(
                """
                INSERT INTO exports (id, project_id, media_asset_id, candidate_id, title, output_filename, created_at)
                VALUES ('exp_fk_fail2', 'default', 'med_test1', 'cand_does_not_exist', 'Title', 'f.mp4', '2026-11-15T00:00:00Z')
                """
            )
    finally:
        conn1.close()
        conn2.close()


def test_missing_file_records_preserved_and_valid_exports_unchanged(p05_env):
    """Verify that missing files are marked failed but never deleted, while valid exports remain completed and unchanged."""
    db_path = p05_env["db_path"]
    storage_root = p05_env["storage_root"]
    backup_service = p05_env["backup_service"]

    # 1. Existing valid export
    exports_dir = storage_root / "exports" / "default"
    exports_dir.mkdir(parents=True, exist_ok=True)
    real_video = exports_dir / "preserved_valid.mp4"
    real_video.write_bytes(b"preserved_content")

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, status, validation_status, created_at)
            VALUES ('exp_valid_keep', 'default', 'cand_test1', 'med_test1', 'Keep Me', ?, 'preserved_valid.mp4', 'completed', 'valid', '2026-11-15T00:00:00Z')
            """,
            (str(real_video),),
        )
        # Missing export
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, status, validation_status, created_at)
            VALUES ('exp_missing_preserve', 'default', 'cand_test1', 'med_test1', 'Mark Failed', 'D:/missing/vid_none.mp4', 'vid_none.mp4', 'completed', 'valid', '2026-11-15T00:00:00Z')
            """
        )

    # Reconcile
    rec = backup_service.reconcile_database_consistency()
    assert rec["status"] == "success"
    assert "exp_missing_preserve" in rec["missing_exports_reconciled"]

    with sqlite_session(db_path) as conn:
        # Check valid export is completely unchanged
        valid_row = conn.execute("SELECT status, validation_status FROM exports WHERE id = 'exp_valid_keep'").fetchone()
        assert valid_row["status"] == "completed"
        assert valid_row["validation_status"] == "valid"

        # Check missing export record is preserved in the database (row not deleted)
        missing_row = conn.execute("SELECT status, validation_status, error_message FROM exports WHERE id = 'exp_missing_preserve'").fetchone()
        assert missing_row is not None, "Missing export record must be preserved in SQLite."
        assert missing_row["status"] == "failed"
        assert missing_row["validation_status"] == "invalid"
        assert "missing from storage disk" in missing_row["error_message"]
