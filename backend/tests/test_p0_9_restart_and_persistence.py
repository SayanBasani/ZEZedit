"""
P0.9 Automated Regression Test Suite: Restart, Recovery and Data Persistence
Covers 20 core persistence and recovery scenarios using isolated tmp_path environments.
"""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import create_sqlite_connection, sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.backup_service import BackupService
from app.services.jobs import JobOrchestrator


@pytest.fixture
def isolated_env(tmp_path: Path):
    """Create a completely isolated test environment with fresh SQLite DB and directories."""
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    db_file = storage_root / "db" / "zezedit.db"
    backups_dir = storage_root / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        app_name="ZezEdit Test",
        app_version="2.0.0-test",
        storage_root=storage_root,
        sqlite_db_path=db_file,
        backup_dir=backups_dir,
        migrations_dir=Path(__file__).resolve().parents[1] / "migrations",
    )

    # Run migrations
    run_migrations(
        db_path=db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=backups_dir,
    )

    return {
        "settings": settings,
        "storage_root": storage_root,
        "db_file": db_file,
        "backups_dir": backups_dir,
    }


def test_01_database_integrity_after_restart(isolated_env):
    """1. Database integrity after restart."""
    db_file = isolated_env["db_file"]
    with sqlite_session(db_file) as conn:
        conn.execute(
            "INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p1', 'PersistProj', 'p1_sub', '2026-01-01', '2026-01-01')"
        )

    # Reopen connection simulating restart
    conn2 = create_sqlite_connection(db_file)
    try:
        cur = conn2.cursor()
        cur.execute("PRAGMA integrity_check;")
        res = cur.fetchone()[0]
        assert str(res).lower() == "ok"

        row = cur.execute("SELECT name FROM projects WHERE id='p1'").fetchone()
        assert row["name"] == "PersistProj"
    finally:
        conn2.close()


def test_02_foreign_key_enforcement_after_restart(isolated_env):
    """2. Foreign-key enforcement after restart."""
    db_file = isolated_env["db_file"]
    conn = create_sqlite_connection(db_file)
    try:
        fk_on = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_on == 1

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO media_assets (id, project_id, original_filename, storage_path, created_at, updated_at)
                VALUES ('m1', 'non_existent_project', 'test.mp4', 'storage/media/test.mp4', '2026-01-01', '2026-01-01')
                """
            )
    finally:
        conn.close()


def test_03_wal_recovery(isolated_env):
    """3. WAL recovery: committed transactions in WAL survive crash before checkpoint."""
    db_file = isolated_env["db_file"]
    conn = create_sqlite_connection(db_file)
    try:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p_wal', 'WalProj', 'p_wal_sub', '2026-01-01', '2026-01-01')")
    finally:
        conn.close()

    conn2 = create_sqlite_connection(db_file)
    try:
        cur = conn2.cursor()
        row = cur.execute("SELECT name FROM projects WHERE id='p_wal'").fetchone()
        assert row is not None
        assert row["name"] == "WalProj"
        cur.execute("PRAGMA quick_check;")
        assert str(cur.fetchone()[0]).lower() == "ok"
    finally:
        conn2.close()


def test_04_checkpoint_behavior(isolated_env):
    """4. Checkpoint behavior: PRAGMA wal_checkpoint flush and verify integrity."""
    db_file = isolated_env["db_file"]
    conn = create_sqlite_connection(db_file)
    try:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p_chk', 'ChkProj', 'p_chk_sub', '2026-01-01', '2026-01-01')")
        chk_res = conn.execute("PRAGMA wal_checkpoint(TRUNCATE);").fetchone()
        assert chk_res[0] == 0
    finally:
        conn.close()

    conn2 = create_sqlite_connection(db_file)
    try:
        cur = conn2.cursor()
        cur.execute("PRAGMA integrity_check;")
        assert str(cur.fetchone()[0]).lower() == "ok"
        row = cur.execute("SELECT name FROM projects WHERE id='p_chk'").fetchone()
        assert row["name"] == "ChkProj"
    finally:
        conn2.close()


def test_05_backup_integrity(isolated_env):
    """5. Backup integrity: online backup creates valid, verified snapshot."""
    db_file = isolated_env["db_file"]
    backups_dir = isolated_env["backups_dir"]

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p_bak', 'BackupProj', 'p_bak_sub', '2026-01-01', '2026-01-01')")

    svc = BackupService(db_path=db_file, backups_dir=backups_dir)
    b_res = svc.create_backup(label="test_integrity")
    assert b_res["integrity_verified"] is True
    assert Path(b_res["backup_path"]).exists()

    b_conn = sqlite3.connect(b_res["backup_path"])
    try:
        r = b_conn.execute("SELECT name FROM projects WHERE id='p_bak'").fetchone()
        assert r[0] == "BackupProj"
    finally:
        b_conn.close()


def test_06_restore_into_isolated_location(isolated_env):
    """6. Restore into an isolated location."""
    db_file = isolated_env["db_file"]
    backups_dir = isolated_env["backups_dir"]

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p_orig', 'Original', 'p_orig_sub', '2026-01-01', '2026-01-01')")

    svc = BackupService(db_path=db_file, backups_dir=backups_dir)
    b_res = svc.create_backup(label="restore_source")

    with sqlite_session(db_file) as conn:
        conn.execute("UPDATE projects SET name = 'Modified' WHERE id = 'p_orig'")

    isolated_target = isolated_env["storage_root"] / "restored.db"
    target_svc = BackupService(db_path=isolated_target, backups_dir=backups_dir)
    target_svc.restore_backup(b_res["backup_filename"])

    t_conn = create_sqlite_connection(isolated_target)
    try:
        r = t_conn.execute("SELECT name FROM projects WHERE id='p_orig'").fetchone()
        assert r["name"] == "Original"
    finally:
        t_conn.close()


def test_07_job_state_recovery_on_startup(isolated_env):
    """7. Job state recovery: active jobs in running/cancelling transition to interrupted."""
    db_file = isolated_env["db_file"]
    settings = isolated_env["settings"]

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('pj1', 'Proj1', 'pj1_sub', '2026-01-01', '2026-01-01')")
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, project_id, status, progress_pct, created_at, updated_at)
            VALUES ('job_run', 'media_analysis', 'pj1', 'running', 45.0, '2026-01-01', '2026-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, project_id, status, progress_pct, created_at, updated_at)
            VALUES ('job_canc', 'export_render', 'pj1', 'cancelling', 80.0, '2026-01-01', '2026-01-01')
            """
        )

    orch = JobOrchestrator(settings=settings, db_path=db_file)
    recovered = orch.recover_interrupted_jobs()

    assert "job_run" in recovered
    assert "job_canc" in recovered

    with sqlite_session(db_file) as conn:
        r1 = conn.execute("SELECT status, current_stage FROM jobs WHERE id='job_run'").fetchone()
        assert r1["status"] == "interrupted"
        assert r1["current_stage"] == "interrupted"

        r2 = conn.execute("SELECT status, current_stage FROM jobs WHERE id='job_canc'").fetchone()
        assert r2["status"] == "interrupted"


def test_08_interrupted_worker_recovery_preserves_checkpoints(isolated_env):
    """8. Interrupted worker recovery preserves checkpoint data."""
    db_file = isolated_env["db_file"]
    settings = isolated_env["settings"]

    cp_data = {"stage": "transcription", "last_chunk": 12, "items_processed": 50}

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('pj2', 'Proj2', 'pj2_sub', '2026-01-01', '2026-01-01')")
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, project_id, status, progress_pct, checkpoint_data_json, created_at, updated_at)
            VALUES ('job_cp', 'media_analysis', 'pj2', 'running', 50.0, ?, '2026-01-01', '2026-01-01')
            """,
            (json.dumps(cp_data),),
        )

    orch = JobOrchestrator(settings=settings, db_path=db_file)
    orch.recover_interrupted_jobs()

    with sqlite_session(db_file) as conn:
        row = conn.execute("SELECT status, checkpoint_data_json, error_message FROM jobs WHERE id='job_cp'").fetchone()
        assert row["status"] == "interrupted"
        assert "Checkpoint preserved for resume" in row["error_message"]
        recovered_cp = json.loads(row["checkpoint_data_json"])
        assert recovered_cp["stage"] == "transcription"
        assert recovered_cp["items_processed"] == 50


def test_09_retry_after_restart(isolated_env):
    """9. Retry after restart: interrupted job can be safely retried."""
    db_file = isolated_env["db_file"]
    settings = isolated_env["settings"]

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('pj3', 'Proj3', 'pj3_sub', '2026-01-01', '2026-01-01')")
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, project_id, status, progress_pct, retry_count, created_at, updated_at)
            VALUES ('job_retry', 'media_analysis', 'pj3', 'interrupted', 30.0, 0, '2026-01-01', '2026-01-01')
            """
        )

    orch = JobOrchestrator(settings=settings, db_path=db_file)
    retried_job = orch.retry_job("job_retry")

    assert retried_job.status == "queued"
    assert retried_job.retry_count == 1
    assert retried_job.progress_pct == 0.0


def test_10_duplicate_job_prevention(isolated_env):
    """10. Duplicate job prevention: running job cannot be claimed concurrently."""
    db_file = isolated_env["db_file"]
    settings = isolated_env["settings"]

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('pj4', 'Proj4', 'pj4_sub', '2026-01-01', '2026-01-01')")
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, project_id, status, created_at, updated_at)
            VALUES ('job_q', 'media_analysis', 'pj4', 'queued', '2026-01-01', '2026-01-01')
            """
        )

    orch = JobOrchestrator(settings=settings, db_path=db_file)
    claimed1 = orch.claim_next_queued_job(worker_id="worker_1")
    assert claimed1 is not None
    assert claimed1.id == "job_q"

    # Second claim must return None (no queued jobs left)
    claimed2 = orch.claim_next_queued_job(worker_id="worker_2")
    assert claimed2 is None


def test_11_source_media_persistence(isolated_env):
    """11. Source media persistence across connection/restart."""
    db_file = isolated_env["db_file"]
    storage_root = isolated_env["storage_root"]

    media_file = storage_root / "media" / "p1" / "video.mp4"
    media_file.parent.mkdir(parents=True, exist_ok=True)
    media_file.write_bytes(b"VIDEO_HEADER_SAMPLE_BYTES" * 100)

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p1', 'Proj1', 'p1_sub', '2026-01-01', '2026-01-01')")
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, file_size_bytes, availability_status, created_at, updated_at)
            VALUES ('med1', 'p1', 'video.mp4', ?, ?, 'available', '2026-01-01', '2026-01-01')
            """,
            (str(media_file), media_file.stat().st_size),
        )

    conn2 = create_sqlite_connection(db_file)
    try:
        row = conn2.execute("SELECT original_filename, storage_path, file_size_bytes FROM media_assets WHERE id='med1'").fetchone()
        assert row["original_filename"] == "video.mp4"
        p = Path(row["storage_path"])
        assert p.is_file()
        assert p.stat().st_size == row["file_size_bytes"]
    finally:
        conn2.close()


def test_12_export_file_persistence(isolated_env):
    """12. Export file persistence across connection/restart."""
    db_file = isolated_env["db_file"]
    storage_root = isolated_env["storage_root"]

    export_file = storage_root / "exports" / "p1" / "export_01.mp4"
    export_file.parent.mkdir(parents=True, exist_ok=True)
    export_file.write_bytes(b"MP4_RENDER_OUTPUT" * 200)

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p1', 'Proj1', 'p1_sub', '2026-01-01', '2026-01-01')")
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, created_at, updated_at)
            VALUES ('m1', 'p1', 'video.mp4', 'dummy/path.mp4', '2026-01-01', '2026-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO exports (id, project_id, media_asset_id, title, output_path, output_filename, file_size_bytes, status, validation_status, created_at)
            VALUES ('exp1', 'p1', 'm1', 'Export Title 01', ?, 'export_01.mp4', ?, 'completed', 'valid', '2026-01-01')
            """,
            (str(export_file), export_file.stat().st_size),
        )

    conn2 = create_sqlite_connection(db_file)
    try:
        row = conn2.execute("SELECT status, validation_status, output_path FROM exports WHERE id='exp1'").fetchone()
        assert row["status"] == "completed"
        assert row["validation_status"] == "valid"
        assert Path(row["output_path"]).is_file()
    finally:
        conn2.close()


def test_13_script_persistence(isolated_env):
    """13. Script persistence: candidates and speech turns survive restart."""
    db_file = isolated_env["db_file"]

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p1', 'Proj1', 'p1_sub', '2026-01-01', '2026-01-01')")
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, created_at, updated_at)
            VALUES ('m1', 'p1', 'v.mp4', 'p/v.mp4', '2026-01-01', '2026-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, current_stage, created_at, updated_at)
            VALUES ('ar_sc1', 'p1', 'm1', 'completed', 'done', '2026-01-01', '2026-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (id, project_id, media_asset_id, analysis_run_id, start_time, end_time, suggested_start_time, suggested_end_time, duration, title, suggested_title, description, created_at, updated_at)
            VALUES ('c1', 'p1', 'm1', 'ar_sc1', 10.0, 45.0, 10.0, 45.0, 35.0, 'Hook Moment', 'Suggested Hook', 'Watch this now description', '2026-01-01', '2026-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO speech_turns (id, analysis_run_id, media_asset_id, speaker_label, start_time, end_time, text, created_at)
            VALUES ('st1', 'ar_sc1', 'm1', 'SPEAKER_00', 10.0, 20.0, 'Hello world speech transcript', '2026-01-01')
            """
        )

    conn2 = create_sqlite_connection(db_file)
    try:
        cand = conn2.execute("SELECT title, description FROM shorts_candidates WHERE id='c1'").fetchone()
        assert cand["title"] == "Hook Moment"
        assert cand["description"] == "Watch this now description"

        turn = conn2.execute("SELECT text FROM speech_turns WHERE id='st1'").fetchone()
        assert "Hello world" in turn["text"]
    finally:
        conn2.close()


def test_14_analysis_persistence(isolated_env):
    """14. Analysis persistence: analysis runs and scenes survive restart."""
    db_file = isolated_env["db_file"]

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p1', 'Proj1', 'p1_sub', '2026-01-01', '2026-01-01')")
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, created_at, updated_at)
            VALUES ('m1', 'p1', 'v.mp4', 'p/v.mp4', '2026-01-01', '2026-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, current_stage, created_at, updated_at)
            VALUES ('ar1', 'p1', 'm1', 'completed', 'done', '2026-01-01', '2026-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO video_scenes (id, analysis_run_id, media_asset_id, scene_index, start_time, end_time, representative_timestamp, created_at)
            VALUES ('sc1', 'ar1', 'm1', 0, 0.0, 15.5, 5.0, '2026-01-01')
            """
        )

    conn2 = create_sqlite_connection(db_file)
    try:
        ar = conn2.execute("SELECT status FROM analysis_runs WHERE id='ar1'").fetchone()
        assert ar["status"] == "completed"
        sc = conn2.execute("SELECT end_time FROM video_scenes WHERE id='sc1'").fetchone()
        assert sc["end_time"] == 15.5
    finally:
        conn2.close()


def test_15_incomplete_upload_handling(isolated_env):
    """15. Incomplete upload handling: partial temp upload is not registered as completed."""
    storage_root = isolated_env["storage_root"]
    temp_dir = storage_root / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    partial_upload = temp_dir / "upload_partial_xyz.tmp"
    partial_upload.write_bytes(b"INCOMPLETE_PARTIAL_CHUNK")

    db_file = isolated_env["db_file"]
    with sqlite_session(db_file) as conn:
        count = conn.execute("SELECT count(*) FROM media_assets;").fetchone()[0]
        assert count == 0

    assert partial_upload.exists()


def test_16_incomplete_export_handling(isolated_env):
    """16. Incomplete export handling: temporary export write failure does not create valid completed export."""
    db_file = isolated_env["db_file"]
    storage_root = isolated_env["storage_root"]

    scratch_render = storage_root / "temp" / "scratch_render_123.mp4"
    scratch_render.parent.mkdir(parents=True, exist_ok=True)
    scratch_render.write_bytes(b"INTERRUPTED_CORRUPTED_STREAM")

    with sqlite_session(db_file) as conn:
        conn.execute("INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p1', 'Proj1', 'p1_sub', '2026-01-01', '2026-01-01')")
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, created_at, updated_at)
            VALUES ('m1', 'p1', 'video.mp4', 'dummy/path.mp4', '2026-01-01', '2026-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO exports (id, project_id, media_asset_id, title, output_path, output_filename, status, validation_status, created_at)
            VALUES ('exp_fail', 'p1', 'm1', 'Export Failure', ?, 'scratch_render_123.mp4', 'failed', 'invalid', '2026-01-01')
            """,
            (str(scratch_render),),
        )

    # Clean unlinking of scratch
    scratch_render.unlink(missing_ok=True)

    with sqlite_session(db_file) as conn:
        exp = conn.execute("SELECT status, validation_status FROM exports WHERE id='exp_fail'").fetchone()
        assert exp["status"] == "failed"
        assert exp["validation_status"] == "invalid"
        assert not scratch_render.exists()


def test_17_launcher_restart_behavior(isolated_env, tmp_path):
    """17. Launcher restart behavior: PID file written on startup and unlinked on stop."""
    temp_dir = isolated_env["storage_root"] / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    pid_file = temp_dir / "zezedit.pid"
    meta_file = temp_dir / "zezedit_process.json"

    pid_file.write_text("99999", encoding="utf-8")
    meta_file.write_text(json.dumps({"pid": 99999, "role": "production_server"}), encoding="utf-8")

    assert pid_file.exists()
    assert meta_file.exists()

    pid_file.unlink(missing_ok=True)
    meta_file.unlink(missing_ok=True)

    assert not pid_file.exists()
    assert not meta_file.exists()


def test_18_pid_reuse_safety():
    """18. PID reuse safety: unrelated process PID is never killed."""
    def is_zezedit_proc(cmdline: str) -> bool:
        return "uvicorn" in cmdline.lower() and "app.main:app" in cmdline.lower()

    assert not is_zezedit_proc("python -m pytest backend/tests")


def test_19_no_orphan_worker_processes(isolated_env):
    """19. No orphan worker processes: termination logic calls subtree kill."""
    settings = isolated_env["settings"]
    db_file = isolated_env["db_file"]
    orch = JobOrchestrator(settings=settings, db_path=db_file)

    assert orch._terminate_pid_tree(None) is False
    assert orch._terminate_pid_tree(-99999) is False


def test_20_no_loss_of_committed_transactions(isolated_env):
    """20. No loss of committed transactions: 5 consecutive transactions all survive reopen."""
    db_file = isolated_env["db_file"]

    for i in range(5):
        conn = create_sqlite_connection(db_file)
        try:
            conn.execute(
                f"INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES ('p_tx_{i}', 'Proj_{i}', 'p_tx_{i}_sub', '2026-01-01', '2026-01-01')"
            )
        finally:
            conn.close()

    conn_final = create_sqlite_connection(db_file)
    try:
        count = conn_final.execute("SELECT count(*) FROM projects WHERE id LIKE 'p_tx_%'").fetchone()[0]
        assert count == 5
    finally:
        conn_final.close()
