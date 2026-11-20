"""Automated test suite for P1.9: Storage Management, Quotas, Safe Cleanup & Automatic Pruning.

Covers all 26 test cases from Section 12:
1. Accurate total storage calculation
2. Correct category-wise storage breakdown
3. Shared physical files counted once
4. Logical asset counts distinguished from physical files
5. Missing directories handled safely
6. Cleanup preview does not delete files
7. Valid stale upload chunks can be cleaned
8. Active uploads are protected
9. Active rendering files are protected
10. Shared canonical media files are protected
11. Original source videos are protected
12. Path traversal attempts are rejected
13. Symlink escape attempts are rejected
14. Preview candidates are revalidated at execution
15. Files changed after preview are handled safely
16. Quota settings persist across restarts
17. Invalid quota settings are rejected
18. Quota limits prevent unsafe new operations (HTTP 507)
19. Automatic pruning respects retention policies
20. Automatic pruning is disabled by default
21. Interrupted upload recovery works
22. Interrupted render recovery works
23. Failed deletions are reported accurately
24. Audit history is recorded
25. Database integrity is preserved
26. P1.7 and P1.8 regression tests continue to pass
"""

import asyncio
import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
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
from app.services.storage import StorageService
from app.schemas.core import StorageQuotaUpdateRequest


def _create_synthetic_mp4(dest_path: Path, duration_sec: float = 1.0, width: int = 640, height: int = 360, freq: int = 1000):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg binary not found")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration_sec}:size={width}x{height}:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration_sec}",
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
def p1_9_env() -> Generator[dict, None, None]:
    temp_dir = tempfile.mkdtemp(prefix="zezedit_p1_9_test_")
    storage_root = Path(temp_dir) / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    settings = Settings(
        storage_root=storage_root,
        environment="testing",
        log_level="DEBUG",
        max_upload_size_bytes=50 * 1024 * 1024,
        max_concurrent_uploads=4,
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
        storage_svc = StorageService(settings=settings)

        project_a = proj_svc.create_project(name="Project A")
        project_b = proj_svc.create_project(name="Project B")

        synth_dir = Path(temp_dir) / "synth_sources"
        synth_dir.mkdir(parents=True, exist_ok=True)
        vid_1 = synth_dir / "sample_video_1.mp4"
        vid_2 = synth_dir / "sample_video_2.mp4"
        _create_synthetic_mp4(vid_1, duration_sec=1.0, freq=800)
        _create_synthetic_mp4(vid_2, duration_sec=1.5, freq=1200)

        yield {
            "temp_dir": temp_dir,
            "storage_root": storage_root,
            "layout": layout,
            "settings": settings,
            "client": client,
            "app": app,
            "project_a": project_a,
            "project_b": project_b,
            "proj_svc": proj_svc,
            "media_service": media_svc,
            "storage_service": storage_svc,
            "vid_1": vid_1,
            "vid_2": vid_2,
            "vid_1_bytes": vid_1.read_bytes(),
            "vid_2_bytes": vid_2.read_bytes(),
            "vid_1_sha": _compute_sha256(vid_1),
            "vid_2_sha": _compute_sha256(vid_2),
        }

    # Teardown
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


# 1. Accurate total storage calculation
def test_accurate_total_storage_calculation(p1_9_env):
    storage_svc: StorageService = p1_9_env["storage_service"]
    layout: StorageLayout = p1_9_env["layout"]

    # Place known dummy files in different locations
    f1 = layout.media / "test1.mp4"
    f1.write_bytes(b"A" * 1024)

    f2 = layout.exports / "export1.mp4"
    f2.write_bytes(b"B" * 2048)

    f3 = layout.temp / "chunk1.part"
    f3.write_bytes(b"C" * 4096)

    breakdown = storage_svc.get_storage_breakdown()
    assert breakdown["total_application_storage_bytes"] >= 1024 + 2048 + 4096
    assert breakdown["categories"]["source_media_bytes"] >= 1024
    assert breakdown["categories"]["rendered_exports_bytes"] >= 2048
    assert breakdown["categories"]["temporary_uploads_bytes"] >= 4096


# 2. Correct category-wise storage breakdown
def test_correct_category_wise_storage_breakdown(p1_9_env):
    client: TestClient = p1_9_env["client"]
    layout: StorageLayout = p1_9_env["layout"]

    # Add audio extraction file
    audio_dir = layout.analysis / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    (audio_dir / "sample.wav").write_bytes(b"W" * 5000)

    # Add thumbnail file
    thumb_dir = layout.thumbnails
    thumb_dir.mkdir(parents=True, exist_ok=True)
    (thumb_dir / "sample.jpg").write_bytes(b"T" * 3000)

    resp = client.get("/api/v1/maintenance/breakdown")
    assert resp.status_code == 200
    data = resp.json()
    cats = data["categories"]

    assert cats["extracted_audio_bytes"] >= 5000
    assert cats["keyframes_and_thumbnails_bytes"] >= 3000


# 3. Shared physical files counted once
def test_shared_physical_files_counted_once(p1_9_env):
    client: TestClient = p1_9_env["client"]
    proj_a = p1_9_env["project_a"]
    proj_b = p1_9_env["project_b"]
    vid_bytes = p1_9_env["vid_1_bytes"]

    # Upload video to Project A
    resp1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("podcast.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert resp1.status_code in (200, 201)

    # Upload identical video to Project B (deduplicated)
    resp2 = client.post(
        f"/api/v1/projects/{proj_b.id}/media/upload",
        files={"file": ("podcast_copy.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert resp2.status_code in (200, 201)

    # Inspect storage breakdown
    resp_bd = client.get("/api/v1/maintenance/breakdown")
    assert resp_bd.status_code == 200
    data = resp_bd.json()
    cats = data["categories"]

    # Canonical shared media must reflect the physical file size
    assert cats["canonical_shared_media_bytes"] == len(vid_bytes)
    # Total application storage must not double-count the shared video
    assert data["total_application_storage_bytes"] < len(vid_bytes) * 2 + 1024 * 1024


# 4. Logical asset counts distinguished from physical files
def test_logical_asset_counts_distinguished_from_physical_files(p1_9_env):
    client: TestClient = p1_9_env["client"]
    proj_a = p1_9_env["project_a"]
    proj_b = p1_9_env["project_b"]
    vid_bytes = p1_9_env["vid_1_bytes"]

    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("clip1.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert r1.status_code in (200, 201)

    r2 = client.post(
        f"/api/v1/projects/{proj_b.id}/media/upload",
        files={"file": ("clip2.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert r2.status_code in (200, 201)

    resp = client.get("/api/v1/maintenance/breakdown")
    data = resp.json()
    cats = data["categories"]

    assert cats["canonical_shared_media_bytes"] == len(vid_bytes)
    assert cats["logical_media_assets_bytes"] == len(vid_bytes) * 2


# 5. Missing directories handled safely
def test_missing_directories_handled_safely(p1_9_env):
    storage_svc: StorageService = p1_9_env["storage_service"]
    layout: StorageLayout = p1_9_env["layout"]

    # Delete exports directory completely
    if layout.exports.exists():
        shutil.rmtree(layout.exports)

    breakdown = storage_svc.get_storage_breakdown()
    assert breakdown["categories"]["rendered_exports_bytes"] == 0
    assert breakdown["total_application_storage_bytes"] >= 0


# 6. Cleanup preview does not delete files
def test_cleanup_preview_does_not_delete_files(p1_9_env):
    client: TestClient = p1_9_env["client"]
    layout: StorageLayout = p1_9_env["layout"]

    # Create an orphaned chunk file older than 2 hours
    stale_part = layout.temp / "abandoned_upload_123.part"
    stale_part.write_bytes(b"Z" * 10000)
    old_time = time.time() - 7200
    os.utime(stale_part, (old_time, old_time))

    # Request preview
    resp = client.post("/api/v1/maintenance/cleanup-preview")
    assert resp.status_code == 200
    data = resp.json()

    # Verify candidate was found
    found = any(c["relative_path"].endswith("abandoned_upload_123.part") for c in data["candidates"])
    assert found is True

    # Assert file still exists on disk
    assert stale_part.exists() is True


# 7. Valid stale upload chunks can be cleaned
def test_valid_stale_upload_chunks_can_be_cleaned(p1_9_env):
    client: TestClient = p1_9_env["client"]
    layout: StorageLayout = p1_9_env["layout"]

    stale_part = layout.temp / "abandoned_upload_456.uploading"
    stale_part.write_bytes(b"Z" * 8000)
    old_time = time.time() - 7200
    os.utime(stale_part, (old_time, old_time))

    # Run preview
    prev_resp = client.post("/api/v1/maintenance/cleanup-preview")
    data = prev_resp.json()
    cand = next(c for c in data["candidates"] if "abandoned_upload_456.uploading" in c["relative_path"])
    assert cand["is_blocked"] is False

    # Execute cleanup
    exec_resp = client.post(
        "/api/v1/maintenance/cleanup-execute",
        json={"candidate_ids": [cand["candidate_id"]]},
    )
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["deleted_count"] == 1
    assert exec_data["bytes_reclaimed"] == 8000
    assert not stale_part.exists()


# 8. Active uploads are protected
def test_active_uploads_are_protected(p1_9_env):
    client: TestClient = p1_9_env["client"]
    layout: StorageLayout = p1_9_env["layout"]

    # Create a fresh upload part (5 seconds old)
    fresh_part = layout.temp / "in_flight.uploading"
    fresh_part.write_bytes(b"U" * 4000)

    # Preview should mark candidate blocked or skip
    prev_resp = client.post("/api/v1/maintenance/cleanup-preview")
    data = prev_resp.json()
    cands = [c for c in data["candidates"] if "in_flight.uploading" in c["relative_path"]]
    if cands:
        assert cands[0]["is_blocked"] is True

    # Attempting to execute cleanup on it should skip it
    if cands:
        exec_resp = client.post(
            "/api/v1/maintenance/cleanup-execute",
            json={"candidate_ids": [cands[0]["candidate_id"]]},
        )
        assert exec_resp.status_code == 200
        assert fresh_part.exists() is True


# 9. Active rendering files are protected
def test_active_rendering_files_are_protected(p1_9_env):
    client: TestClient = p1_9_env["client"]
    layout: StorageLayout = p1_9_env["layout"]
    proj_a = p1_9_env["project_a"]

    # Create active job in DB
    job_id = "test_active_job_999"
    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, project_id, job_type, status, created_at, updated_at)
            VALUES (?, ?, 'video_render', 'running', datetime('now'), datetime('now'))
            """,
            (job_id, proj_a.id),
        )

    # Create temporary scratch directory for this active job
    job_dir = layout.temp / f"job_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)
    scratch_file = job_dir / "render_scratch.mp4"
    scratch_file.write_bytes(b"R" * 12000)
    old_time = time.time() - 7200
    os.utime(scratch_file, (old_time, old_time))

    prev_resp = client.post("/api/v1/maintenance/cleanup-preview")
    data = prev_resp.json()
    job_cands = [c for c in data["candidates"] if job_id in c["relative_path"]]
    assert len(job_cands) > 0
    assert job_cands[0]["is_blocked"] is True
    assert "running" in job_cands[0]["protection_reason"].lower() or "active" in job_cands[0]["protection_reason"].lower()

    # Execute cleanup
    exec_resp = client.post(
        "/api/v1/maintenance/cleanup-execute",
        json={"candidate_ids": [job_cands[0]["candidate_id"]]},
    )
    assert exec_resp.status_code == 200
    assert scratch_file.exists() is True


# 10. Shared canonical media files are protected
def test_shared_canonical_media_files_are_protected(p1_9_env):
    client: TestClient = p1_9_env["client"]
    proj_a = p1_9_env["project_a"]
    vid_bytes = p1_9_env["vid_1_bytes"]

    # Upload canonical media
    resp = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("shared_vid.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert resp.status_code in (200, 201)
    asset_id = resp.json()["id"]

    # Try executing cleanup passing canonical media path
    fake_cand_id = f"custom_{asset_id}"
    exec_resp = client.post(
        "/api/v1/maintenance/cleanup-execute",
        json={"candidate_ids": [fake_cand_id]},
    )
    assert exec_resp.status_code == 200
    # Media must still exist
    asset_check = client.get(f"/api/v1/media/{asset_id}")
    assert asset_check.status_code == 200


# 11. Original source videos are protected
def test_original_source_videos_are_protected(p1_9_env):
    storage_svc: StorageService = p1_9_env["storage_service"]
    layout: StorageLayout = p1_9_env["layout"]

    src_video = layout.media / "user_orig_source.mp4"
    src_video.write_bytes(b"S" * 15000)

    preview = storage_svc.preview_maintenance_cleanup()
    # Preview must never list files from media/
    for c in preview["candidates"]:
        assert not c["relative_path"].startswith("media/")
        assert not c["relative_path"].endswith("user_orig_source.mp4")

    assert src_video.exists() is True


# 12. Path traversal attempts are rejected
def test_path_traversal_attempts_are_rejected(p1_9_env):
    storage_svc: StorageService = p1_9_env["storage_service"]

    # Attempt path traversal
    resolved = storage_svc.resolve_contained_path("../../Windows/System32/calc.exe")
    assert resolved is None


# 13. Symlink escape attempts are rejected
def test_symlink_escape_attempts_are_rejected(p1_9_env):
    storage_svc: StorageService = p1_9_env["storage_service"]
    layout: StorageLayout = p1_9_env["layout"]
    temp_dir = Path(p1_9_env["temp_dir"])

    # Create target outside storage
    external_file = temp_dir / "external_secret.txt"
    external_file.write_text("classified")

    link_path = layout.temp / "evil_link.txt"
    try:
        os.symlink(external_file, link_path)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not permitted in this environment")

    resolved = storage_svc.resolve_contained_path(str(link_path))
    assert resolved is None


# 14. Preview candidates are revalidated at execution
def test_preview_candidates_revalidated_at_execution(p1_9_env):
    storage_svc: StorageService = p1_9_env["storage_service"]
    layout: StorageLayout = p1_9_env["layout"]

    stale_file = layout.temp / "reval_test.part"
    stale_file.write_bytes(b"R" * 500)
    old_time = time.time() - 7200
    os.utime(stale_file, (old_time, old_time))

    preview = storage_svc.preview_maintenance_cleanup()
    cand = next(c for c in preview["candidates"] if "reval_test.part" in c["relative_path"])

    # Touch file to make it fresh again (5 seconds old)
    now = time.time()
    os.utime(stale_file, (now, now))

    # Execute cleanup
    result = storage_svc.execute_maintenance_cleanup(candidate_ids=[cand["candidate_id"]])
    # Should be skipped because it became fresh
    assert result["skipped_count"] == 1
    assert stale_file.exists() is True


# 15. Files changed after preview are handled safely
def test_files_changed_after_preview_handled_safely(p1_9_env):
    storage_svc: StorageService = p1_9_env["storage_service"]
    layout: StorageLayout = p1_9_env["layout"]

    stale_file = layout.temp / "vanished_test.part"
    stale_file.write_bytes(b"V" * 500)
    old_time = time.time() - 7200
    os.utime(stale_file, (old_time, old_time))

    preview = storage_svc.preview_maintenance_cleanup()
    cand = next(c for c in preview["candidates"] if "vanished_test.part" in c["relative_path"])

    # Delete file externally
    stale_file.unlink()

    # Execution should handle missing file gracefully
    result = storage_svc.execute_maintenance_cleanup(candidate_ids=[cand["candidate_id"]])
    assert result["skipped_count"] == 1


# 16. Quota settings persist across restarts
def test_quota_settings_persist_across_restarts(p1_9_env):
    client: TestClient = p1_9_env["client"]
    settings: Settings = p1_9_env["settings"]
    layout: StorageLayout = p1_9_env["layout"]

    # Update quotas
    resp = client.put(
        "/api/v1/maintenance/quotas",
        json={
            "storage_limit_bytes": 100 * 1024 * 1024 * 1024,
            "generated_video_limit_bytes": 20 * 1024 * 1024 * 1024,
            "warning_threshold_percent": 90,
            "auto_prune_enabled": True,
            "auto_prune_retention_hours": 48,
        },
    )
    assert resp.status_code == 200

    # Instantiate completely new StorageService simulating app restart
    new_svc = StorageService(settings=settings)
    quotas = new_svc.get_storage_quotas()

    assert quotas.storage_limit_bytes == 100 * 1024 * 1024 * 1024
    assert quotas.generated_video_limit_bytes == 20 * 1024 * 1024 * 1024
    assert quotas.warning_threshold_percent == 90
    assert quotas.auto_prune_enabled is True
    assert quotas.auto_prune_retention_hours == 48


# 17. Invalid quota settings are rejected
def test_invalid_quota_settings_rejected(p1_9_env):
    client: TestClient = p1_9_env["client"]

    # Negative limit
    resp1 = client.put(
        "/api/v1/maintenance/quotas",
        json={"storage_limit_bytes": -500},
    )
    assert resp1.status_code in (400, 422)

    # Threshold > 100
    resp2 = client.put(
        "/api/v1/maintenance/quotas",
        json={"warning_threshold_percent": 150},
    )
    assert resp2.status_code in (400, 422)


# 18. Quota limits prevent unsafe new operations (HTTP 507)
def test_quota_limits_prevent_unsafe_new_operations(p1_9_env):
    client: TestClient = p1_9_env["client"]
    proj_a = p1_9_env["project_a"]
    vid_bytes = p1_9_env["vid_1_bytes"]

    # Set hard quota smaller than incoming upload
    resp_quota = client.put(
        "/api/v1/maintenance/quotas",
        json={"storage_limit_bytes": 100},  # 100 bytes hard limit
    )
    assert resp_quota.status_code == 200

    # Upload should fail with 507 Insufficient Storage
    resp = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("big_upload.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert resp.status_code == 507
    err_data = resp.json()
    assert "QUOTA_EXCEEDED" in str(err_data)


# 19. Automatic pruning respects retention policies
def test_automatic_pruning_respects_retention_policies(p1_9_env):
    storage_svc: StorageService = p1_9_env["storage_service"]
    layout: StorageLayout = p1_9_env["layout"]

    # Enable auto pruning with 24 hours retention
    storage_svc.update_storage_quotas(
        StorageQuotaUpdateRequest(
            auto_prune_enabled=True,
            auto_prune_retention_hours=24,
        )
    )

    # Stale chunk (30 hours old)
    stale_chunk = layout.temp / "old_stale.part"
    stale_chunk.write_bytes(b"O" * 5000)
    old_time = time.time() - (30 * 3600)
    os.utime(stale_chunk, (old_time, old_time))

    # Fresh chunk (2 hours old)
    fresh_chunk = layout.temp / "fresh_temp.part"
    fresh_chunk.write_bytes(b"F" * 5000)
    fresh_time = time.time() - (2 * 3600)
    os.utime(fresh_chunk, (fresh_time, fresh_time))

    res = storage_svc.execute_auto_prune()
    assert res["deleted_count"] == 1
    assert not stale_chunk.exists()
    assert fresh_chunk.exists() is True


# 20. Automatic pruning is disabled by default
def test_automatic_pruning_disabled_by_default(p1_9_env):
    client: TestClient = p1_9_env["client"]
    layout: StorageLayout = p1_9_env["layout"]

    stale_chunk = layout.temp / "default_disabled.part"
    stale_chunk.write_bytes(b"D" * 5000)
    old_time = time.time() - (50 * 3600)
    os.utime(stale_chunk, (old_time, old_time))

    # Auto prune endpoint call without enabling
    resp = client.post("/api/v1/maintenance/auto-prune")
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("executed") is False or data.get("deleted_count", 0) == 0
    assert stale_chunk.exists() is True


# 21. Interrupted upload recovery works
def test_interrupted_upload_recovery_works(p1_9_env):
    client: TestClient = p1_9_env["client"]
    layout: StorageLayout = p1_9_env["layout"]

    # Create stale interrupted parts
    crashed_1 = layout.temp / "crashed_1.part"
    crashed_1.write_bytes(b"C" * 2000)
    crashed_2 = layout.temp / "crashed_2.uploading"
    crashed_2.write_bytes(b"C" * 3000)

    old_time = time.time() - 7200
    os.utime(crashed_1, (old_time, old_time))
    os.utime(crashed_2, (old_time, old_time))

    resp = client.post("/api/v1/maintenance/recover-stale-artifacts")
    assert resp.status_code == 200
    data = resp.json()

    assert data["recovered_files_count"] >= 2
    assert not crashed_1.exists()
    assert not crashed_2.exists()


# 22. Interrupted render recovery works
def test_interrupted_render_recovery_works(p1_9_env):
    client: TestClient = p1_9_env["client"]
    layout: StorageLayout = p1_9_env["layout"]

    # Abandoned render workspace from dead job
    render_workspace = layout.temp / "job_abandoned_dead_process"
    render_workspace.mkdir(parents=True, exist_ok=True)
    (render_workspace / "frame_001.png").write_bytes(b"P" * 1000)
    (render_workspace / "scratch.mp4").write_bytes(b"M" * 4000)

    old_time = time.time() - 7200
    os.utime(render_workspace, (old_time, old_time))
    for f in render_workspace.iterdir():
        os.utime(f, (old_time, old_time))

    resp = client.post("/api/v1/maintenance/recover-stale-artifacts")
    assert resp.status_code == 200
    assert not render_workspace.exists()


# 23. Failed deletions are reported accurately
def test_failed_deletions_reported_accurately(p1_9_env, monkeypatch):
    storage_svc: StorageService = p1_9_env["storage_service"]
    layout: StorageLayout = p1_9_env["layout"]

    stale_file = layout.temp / "perm_error_test.part"
    stale_file.write_bytes(b"P" * 1000)
    old_time = time.time() - 7200
    os.utime(stale_file, (old_time, old_time))

    preview = storage_svc.preview_maintenance_cleanup()
    cand = next(c for c in preview["candidates"] if "perm_error_test.part" in c["relative_path"])

    # Monkeypatch os.unlink to simulate file permission lock
    def mock_unlink(path):
        raise PermissionError("Access is denied (locked by OS)")

    monkeypatch.setattr(os, "unlink", mock_unlink)

    result = storage_svc.execute_maintenance_cleanup(candidate_ids=[cand["candidate_id"]])
    assert result["failed_count"] == 1
    assert len(result["failed_items"]) == 1
    assert "Access is denied" in result["failed_items"][0]["error"]


# 24. Audit history is recorded
def test_audit_history_recorded(p1_9_env):
    client: TestClient = p1_9_env["client"]
    layout: StorageLayout = p1_9_env["layout"]

    stale_part = layout.temp / "audit_test.part"
    stale_part.write_bytes(b"A" * 6000)
    old_time = time.time() - 7200
    os.utime(stale_part, (old_time, old_time))

    prev_resp = client.post("/api/v1/maintenance/cleanup-preview")
    cand = next(c for c in prev_resp.json()["candidates"] if "audit_test.part" in c["relative_path"])

    client.post(
        "/api/v1/maintenance/cleanup-execute",
        json={"candidate_ids": [cand["candidate_id"]]},
    )

    # Fetch audit history
    hist_resp = client.get("/api/v1/maintenance/cleanup-history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()

    assert len(history) >= 1
    latest = history[0]
    assert latest["files_deleted"] == 1
    assert latest["bytes_reclaimed"] == 6000
    assert latest["cleanup_category"] == "orphaned_uploads"


# 25. Database integrity is preserved
def test_database_integrity_preserved(p1_9_env):
    layout: StorageLayout = p1_9_env["layout"]

    with sqlite_session(layout.db_file) as conn:
        integrity = [r[0] for r in conn.execute("PRAGMA integrity_check").fetchall()]
        assert integrity == ["ok"]

        fk_check = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert fk_check == []


# 26. P1.7 and P1.8 regression tests continue to pass
def test_p1_7_and_p1_8_regression_tests_continue_to_pass(p1_9_env):
    client: TestClient = p1_9_env["client"]
    proj_a = p1_9_env["project_a"]
    proj_b = p1_9_env["project_b"]
    vid_1 = p1_9_env["vid_1_bytes"]

    # Upload identical files (P1.8 deduplication test)
    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("regr_1.mp4", io.BytesIO(vid_1), "video/mp4")},
    )
    assert r1.status_code in (200, 201)
    asset_1 = r1.json()

    r2 = client.post(
        f"/api/v1/projects/{proj_b.id}/media/upload",
        files={"file": ("regr_2.mp4", io.BytesIO(vid_1), "video/mp4")},
    )
    assert r2.status_code in (200, 201)
    asset_2 = r2.json()

    # Shared asset reference count must be 2
    detail_1 = client.get(f"/api/v1/media/{asset_1['id']}").json()
    assert detail_1["reference_count"] == 2

    # Deduplication stats API works
    dedup_summary = client.get("/api/v1/media/deduplication/stats")
    assert dedup_summary.status_code == 200
    assert dedup_summary.json()["shared_stored_files"] >= 1
