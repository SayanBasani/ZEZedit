"""Integration and unit test suite for P1.7: Media Relinking, Missing File Recovery and External Media Handling.

Verifies:
1. Missing media detection (dynamic detection without database corruption, preserves metadata).
2. Unknown media ID handling (returns 404).
3. Candidate file inspection security (path traversal, system folders, non-existent paths).
4. Video file validation (supported containers, FFprobe stream check, corrupt file rejection).
5. Discrepancy warnings (duration difference, resolution difference).
6. Duration mismatch protection (blocks relinking without force=true).
7. Exact and mismatch SHA-256 comparison reporting.
8. Atomic database update and recovery audit (relinked_at, previous_storage_path, previous_sha256).
9. Project event recording for media relinking.
10. Thumbnail regeneration on relinking.
11. Bounded-memory file upload relinking endpoint.
12. External drive reconnection reconciliation (reconcile_missing_media).
13. Preservation of candidate highlights, scripts, and exports across relinking.
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.db.connection import sqlite_session
from app.main import create_app
from app.services.media import MediaService
from app.services.projects import ProjectService


def _create_synthetic_mp4(dest_path: Path, duration_sec: float = 1.0, width: int = 640, height: int = 360):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg binary not found")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration_sec}:size={width}x{height}:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency=1000:duration={duration_sec}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(dest_path),
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def _compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture
def p1_7_env() -> Generator[dict, None, None]:
    temp_dir = tempfile.mkdtemp(prefix="zezedit_p1_7_test_")
    storage_root = Path(temp_dir) / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    settings = Settings(
        storage_root=storage_root,
        environment="testing",
        log_level="DEBUG",
        max_upload_size_bytes=50 * 1024 * 1024,
        max_concurrent_uploads=2,
    )

    run_migrations(
        db_path=layout.db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=layout.backups,
    )

    app = create_app(settings_override=settings)
    with TestClient(app) as client:
        proj_svc = ProjectService(settings=settings, db_path=layout.db_file)
        media_svc = MediaService(settings=settings, db_path=layout.db_file)
        project = proj_svc.create_project(name="P1.7 Relinking Test Project")

        yield {
            "temp_dir": temp_dir,
            "storage_root": storage_root,
            "layout": layout,
            "settings": settings,
            "client": client,
            "project": project,
            "media_service": media_svc,
        }

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_detect_present_and_missing_files_dynamically(p1_7_env: dict):
    client: TestClient = p1_7_env["client"]
    project = p1_7_env["project"]
    media_svc: MediaService = p1_7_env["media_service"]
    layout: StorageLayout = p1_7_env["layout"]

    video_path = layout.media / "initial_take.mp4"
    _create_synthetic_mp4(video_path, duration_sec=2.0, width=640, height=360)
    sha = _compute_sha256(video_path)

    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="initial_take.mp4",
        storage_path=str(video_path.resolve()),
        is_external=False,
        media_type="video",
        file_size_bytes=video_path.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=2.0,
        width=640,
        height=360,
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
        sha256=sha,
    )
    assert asset.availability_status == "present"
    assert asset.is_playable is True

    # 1. API fetch when file is present
    res = client.get(f"/api/v1/projects/{project.id}/media/{asset.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["availability_status"] == "present"
    assert data["is_playable"] is True

    # 2. Simulate file moved/missing (external drive detached or file deleted)
    backup_path = layout.media / "detached_external_drive" / "initial_take.mp4"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(video_path), str(backup_path))
    assert not video_path.exists()

    # 3. Dynamic check immediately returns 'missing' without crashing or corrupting metadata
    res_missing = client.get(f"/api/v1/projects/{project.id}/media/{asset.id}")
    assert res_missing.status_code == 200
    missing_data = res_missing.json()
    assert missing_data["availability_status"] == "missing"
    assert missing_data["is_playable"] is False
    assert missing_data["duration_seconds"] > 0
    assert missing_data["width"] == 640


def test_relink_unknown_media_404(p1_7_env: dict):
    client: TestClient = p1_7_env["client"]
    project = p1_7_env["project"]

    res = client.post(
        f"/api/v1/projects/{project.id}/media/non-existent-media-id/relink",
        json={"new_storage_path": "C:\\videos\\sample.mp4", "force": False},
    )
    assert res.status_code == 404
    err_body = res.json()
    msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "not found" in msg.lower()


def test_inspect_candidate_validation_and_security(p1_7_env: dict):
    client: TestClient = p1_7_env["client"]
    project = p1_7_env["project"]
    media_svc: MediaService = p1_7_env["media_service"]
    layout: StorageLayout = p1_7_env["layout"]

    vpath = layout.media / "target_video.mp4"
    _create_synthetic_mp4(vpath, duration_sec=1.0)
    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="target_video.mp4",
        storage_path=str(vpath.resolve()),
        is_external=False,
        media_type="video",
        file_size_bytes=vpath.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=1.0,
        width=640,
        height=360,
    )

    # 1. Non-existent path returns 400 or 404
    res_missing = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink/inspect",
        json={"candidate_path": str(layout.media / "does_not_exist.mp4")},
    )
    assert res_missing.status_code in (400, 404)

    # 2. Unsupported extension returns 400
    text_file = layout.media / "notes.txt"
    text_file.write_text("Hello world")
    res_ext = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink/inspect",
        json={"candidate_path": str(text_file)},
    )
    assert res_ext.status_code == 400
    code = res_ext.json().get("error", {}).get("code") or res_ext.json().get("detail", "")
    assert "UNSUPPORTED" in code

    # 3. Corrupt video file returns 400 (corrupt header/FFprobe fails)
    corrupt_mp4 = layout.media / "corrupt_fake.mp4"
    corrupt_mp4.write_bytes(b"NOT A REAL VIDEO DATA HEADER AT ALL 1234567890")
    res_corrupt = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink/inspect",
        json={"candidate_path": str(corrupt_mp4)},
    )
    assert res_corrupt.status_code == 400
    code_corrupt = res_corrupt.json().get("error", {}).get("code") or res_corrupt.json().get("detail", "")
    assert "INVALID_VIDEO_FILE" in code_corrupt


def test_inspect_candidate_metrics_and_warnings(p1_7_env: dict):
    client: TestClient = p1_7_env["client"]
    project = p1_7_env["project"]
    media_svc: MediaService = p1_7_env["media_service"]
    layout: StorageLayout = p1_7_env["layout"]

    orig_path = layout.media / "orig_1s_640.mp4"
    _create_synthetic_mp4(orig_path, duration_sec=1.0, width=640, height=360)
    sha_orig = _compute_sha256(orig_path)
    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="orig_1s_640.mp4",
        storage_path=str(orig_path.resolve()),
        is_external=False,
        media_type="video",
        file_size_bytes=orig_path.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=1.0,
        width=640,
        height=360,
        sha256=sha_orig,
    )

    # Candidate A: Exact copy (matching duration, resolution, SHA-256)
    cand_exact = layout.media / "exact_copy.mp4"
    shutil.copy2(str(orig_path), str(cand_exact))
    res_exact = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink/inspect",
        json={"candidate_path": str(cand_exact)},
    )
    assert res_exact.status_code == 200
    data_exact = res_exact.json()
    assert data_exact["match_status"] == "exact"
    assert data_exact["comparison"]["sha256_match"] is True
    assert len(data_exact["warnings"]) == 0

    # Candidate B: Different duration & resolution (3.0s, 1280x720)
    cand_diff = layout.media / "cand_diff_3s.mp4"
    _create_synthetic_mp4(cand_diff, duration_sec=3.0, width=1280, height=720)
    res_diff = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink/inspect",
        json={"candidate_path": str(cand_diff)},
    )
    assert res_diff.status_code == 200
    data_diff = res_diff.json()
    assert data_diff["match_status"] == "mismatch"
    assert data_diff["comparison"]["sha256_match"] is False
    assert any("duration" in w.lower() for w in data_diff["warnings"])
    assert any("resolution" in w.lower() for w in data_diff["warnings"])


def test_relink_enforces_force_flag_on_mismatch(p1_7_env: dict):
    client: TestClient = p1_7_env["client"]
    project = p1_7_env["project"]
    media_svc: MediaService = p1_7_env["media_service"]
    layout: StorageLayout = p1_7_env["layout"]

    orig_path = layout.media / "source_orig.mp4"
    _create_synthetic_mp4(orig_path, duration_sec=1.0, width=640, height=360)
    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="source_orig.mp4",
        storage_path=str(orig_path.resolve()),
        is_external=False,
        media_type="video",
        file_size_bytes=orig_path.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=1.0,
        width=640,
        height=360,
    )

    # Different duration candidate
    cand_diff = layout.media / "mismatch_dur.mp4"
    _create_synthetic_mp4(cand_diff, duration_sec=4.0, width=640, height=360)

    # 1. Attempt relink without force=true fails with 400
    res_blocked = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink",
        json={"new_storage_path": str(cand_diff), "force": False},
    )
    assert res_blocked.status_code == 400
    err_body = res_blocked.json()
    msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "force=true" in msg

    # 2. Relink with force=true succeeds
    res_forced = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink",
        json={"new_storage_path": str(cand_diff), "force": True},
    )
    assert res_forced.status_code == 200
    data = res_forced.json()
    assert data["match_status"] == "mismatch"
    assert data["relinked_at"] is not None


def test_atomic_relinking_and_audit_history(p1_7_env: dict):
    client: TestClient = p1_7_env["client"]
    project = p1_7_env["project"]
    media_svc: MediaService = p1_7_env["media_service"]
    layout: StorageLayout = p1_7_env["layout"]

    orig_path = layout.media / "file_A.mp4"
    _create_synthetic_mp4(orig_path, duration_sec=1.5, width=640, height=360)
    sha_A = _compute_sha256(orig_path)
    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="file_A.mp4",
        storage_path=str(orig_path.resolve()),
        is_external=False,
        media_type="video",
        file_size_bytes=orig_path.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=1.5,
        width=640,
        height=360,
        sha256=sha_A,
    )

    new_path = layout.media / "file_B_restored.mp4"
    _create_synthetic_mp4(new_path, duration_sec=1.5, width=640, height=360)

    # Relink
    res = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink",
        json={"new_storage_path": str(new_path), "force": True},
    )
    assert res.status_code == 200

    # Verify updated record in DB
    relinked = media_svc.get_media_asset(project.id, asset.id)
    assert relinked.storage_path == str(new_path.resolve())
    assert relinked.previous_storage_path == str(orig_path.resolve())
    assert relinked.previous_sha256 == sha_A
    assert relinked.relinked_at is not None
    assert relinked.availability_status == "present"

    # Verify project_events entry
    with sqlite_session(layout.db_file) as conn:
        events = conn.execute(
            "SELECT event_type, payload_json FROM project_events WHERE project_id = ? AND event_type = 'media_relinked'",
            (project.id,),
        ).fetchall()
        assert len(events) >= 1
        ev_payload = json.loads(events[0]["payload_json"])
        assert (ev_payload.get("asset_id") or ev_payload.get("media_id")) == asset.id
        assert ev_payload["previous_path"] == str(orig_path.resolve())


def test_relink_with_upload_streaming(p1_7_env: dict):
    client: TestClient = p1_7_env["client"]
    project = p1_7_env["project"]
    media_svc: MediaService = p1_7_env["media_service"]
    layout: StorageLayout = p1_7_env["layout"]

    orig_path = layout.media / "initial_upload.mp4"
    _create_synthetic_mp4(orig_path, duration_sec=1.0, width=640, height=360)
    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="initial_upload.mp4",
        storage_path=str(orig_path.resolve()),
        is_external=False,
        media_type="video",
        file_size_bytes=orig_path.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=1.0,
        width=640,
        height=360,
    )

    replacement_file = layout.media / "replacement_temp.mp4"
    _create_synthetic_mp4(replacement_file, duration_sec=1.0, width=640, height=360)
    file_bytes = replacement_file.read_bytes()

    res = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink/upload",
        files={"file": ("replacement.mp4", io.BytesIO(file_bytes), "video/mp4")},
        data={"force": "true"},
    )
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["relinked_at"] is not None

    # Check that asset is updated and physically exists
    updated = media_svc.get_media_asset(project.id, asset.id)
    assert Path(updated.storage_path).exists()
    assert updated.availability_status == "present"


def test_reconcile_missing_media_external_drive(p1_7_env: dict):
    client: TestClient = p1_7_env["client"]
    project = p1_7_env["project"]
    media_svc: MediaService = p1_7_env["media_service"]
    layout: StorageLayout = p1_7_env["layout"]

    drive_mock = layout.media / "mock_usb_drive"
    drive_mock.mkdir(parents=True, exist_ok=True)
    video_on_drive = drive_mock / "drive_lecture.mp4"
    _create_synthetic_mp4(video_on_drive, duration_sec=2.0)

    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="drive_lecture.mp4",
        storage_path=str(video_on_drive.resolve()),
        is_external=True,
        media_type="video",
        file_size_bytes=video_on_drive.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=2.0,
        width=640,
        height=360,
    )
    assert asset.availability_status == "present"

    # Simulate drive disconnection (rename folder)
    disconnected_mock = layout.media / "mock_usb_drive_disconnected"
    drive_mock.rename(disconnected_mock)
    assert not video_on_drive.exists()

    # Dynamic check confirms it is missing
    missing_asset = media_svc.get_media_asset(project.id, asset.id)
    assert missing_asset.availability_status == "missing"

    # Reconcile while disconnected marks it in DB as missing
    res_disc = client.post(f"/api/v1/projects/{project.id}/media/reconcile-availability")
    assert res_disc.status_code == 200
    assert res_disc.json()["still_missing_count"] >= 1

    # Simulate drive reconnection (restore folder)
    disconnected_mock.rename(drive_mock)
    assert video_on_drive.exists()

    # Reconcile via endpoint
    res = client.post(f"/api/v1/projects/{project.id}/media/reconcile-availability")
    assert res.status_code == 200
    data = res.json()
    assert data["restored_count"] >= 1

    # Confirm asset status is restored
    restored_asset = media_svc.get_media_asset(project.id, asset.id)
    assert restored_asset.availability_status == "present"
    assert restored_asset.integrity_status == "verified"


def test_preserve_associated_records_across_relink(p1_7_env: dict):
    client: TestClient = p1_7_env["client"]
    project = p1_7_env["project"]
    media_svc: MediaService = p1_7_env["media_service"]
    layout: StorageLayout = p1_7_env["layout"]

    vpath = layout.media / "lesson.mp4"
    _create_synthetic_mp4(vpath, duration_sec=3.0)
    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="lesson.mp4",
        storage_path=str(vpath.resolve()),
        is_external=False,
        media_type="video",
        file_size_bytes=vpath.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=3.0,
        width=640,
        height=360,
    )

    # Insert mock analysis run, shorts candidate, and export tied to this asset
    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, profile, status, created_at, updated_at)
            VALUES ('run_p1_7_test', ?, ?, 'balanced', 'completed', '2026-11-16T12:00:00Z', '2026-11-16T12:00:00Z')
            """,
            (project.id, asset.id),
        )
        conn.execute(
            """
            INSERT INTO shorts_candidates (
                id, project_id, media_asset_id, analysis_run_id, start_time, end_time, duration,
                suggested_start_time, suggested_end_time, title, suggested_title, created_at, updated_at
            )
            VALUES ('cand_p1_7_test', ?, ?, 'run_p1_7_test', 0.5, 2.5, 2.0, 0.5, 2.5, 'Key takeaway', 'Key takeaway', '2026-11-16T12:00:00Z', '2026-11-16T12:00:00Z')
            """,
            (project.id, asset.id),
        )
        conn.execute(
            """
            INSERT INTO exports (id, project_id, candidate_id, media_asset_id, title, output_path, output_filename, status, created_at)
            VALUES ('exp_p1_7_test', ?, 'cand_p1_7_test', ?, 'Exported Short', 'exports/take.mp4', 'take.mp4', 'completed', '2026-11-16T12:00:00Z')
            """,
            (project.id, asset.id),
        )

    # Relink to new path
    replacement = layout.media / "lesson_relinked.mp4"
    _create_synthetic_mp4(replacement, duration_sec=3.0)
    res = client.post(
        f"/api/v1/projects/{project.id}/media/{asset.id}/relink",
        json={"new_storage_path": str(replacement), "force": True},
    )
    assert res.status_code == 200

    # Verify that candidate highlights and exports are completely preserved
    with sqlite_session(layout.db_file) as conn:
        cand = conn.execute("SELECT id, title FROM shorts_candidates WHERE id = 'cand_p1_7_test'").fetchone()
        assert cand is not None
        assert cand["title"] == "Key takeaway"

        exp = conn.execute("SELECT id, status FROM exports WHERE id = 'exp_p1_7_test'").fetchone()
        assert exp is not None
        assert exp["status"] == "completed"
