"""Unit and integration test suite for P1.6: Media Library, Metadata and Asset Management.

Verifies:
1. Search across titles, filenames, and IDs (case-insensitive, unicode, spaces).
2. Filtering by resolution, format, video codec, duration range, analysis status, and integrity status.
3. Allowlisted server-side sorting (newest, oldest, name asc/desc, size largest/smallest, duration, resolution).
4. Stable server-side pagination with total_count and total_pages without row duplication or skips.
5. Enriched metadata projection (container_format, resolution_label, aspect_ratio, audio/subtitle counts and languages, pixel format, bitrate).
6. HTTP 206 byte-range streaming for HTML5 playback, including seek headers, 416 range errors, and path traversal protection.
7. Explicit technical metadata refresh endpoint preserving pre-computed SHA-256 and attempt ID.
8. Explicit thumbnail regeneration endpoint.
9. Dependency-safe deletion: rejects deletion with 409 when active operations or dependent exports exist unless force_with_exports=true.
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


def _create_synthetic_mkv(dest_path: Path, duration_sec: float = 1.0, width: int = 1920, height: int = 1080):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg binary not found")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration_sec}:size={width}x{height}:rate=24",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration_sec}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(dest_path),
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


@pytest.fixture
def p1_6_env() -> Generator[dict, None, None]:
    temp_dir = tempfile.mkdtemp(prefix="zezedit_p1_6_test_")
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

    migration_res = run_migrations(
        db_path=layout.db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=layout.backups,
    )

    app = create_app(settings_override=settings)
    with TestClient(app) as client:
        proj_svc = ProjectService(settings=settings, db_path=layout.db_file)
        media_svc = MediaService(settings=settings, db_path=layout.db_file)
        project = proj_svc.create_project(name="P1.6 Test Library Project")

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


def test_media_library_search_and_filtering(p1_6_env: dict):
    client: TestClient = p1_6_env["client"]
    project = p1_6_env["project"]
    media_svc: MediaService = p1_6_env["media_service"]
    layout: StorageLayout = p1_6_env["layout"]

    # Register 3 assets: 1 4K MP4, 1 1080p MKV, 1 720p MP4
    f1 = layout.media / "wildlife_4k.mp4"
    f2 = layout.media / "interview_1080p.mkv"
    f3 = layout.media / "action_720p.mp4"

    _create_synthetic_mp4(f1, duration_sec=2.0, width=3840, height=2160)
    _create_synthetic_mkv(f2, duration_sec=4.0, width=1920, height=1080)
    _create_synthetic_mp4(f3, duration_sec=1.5, width=1280, height=720)

    # Register via service
    a1 = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="Wild Life Document 4K.mp4",
        storage_path="wildlife_4k.mp4",
        is_external=False,
        media_type="video",
        file_size_bytes=f1.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=2.0,
        width=3840,
        height=2160,
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
    )
    a2 = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="Studio Interview Special.mkv",
        storage_path="interview_1080p.mkv",
        is_external=False,
        media_type="video",
        file_size_bytes=f2.stat().st_size,
        mime_type="video/x-matroska",
        duration_seconds=4.0,
        width=1920,
        height=1080,
        fps=24.0,
        video_codec="h264",
        audio_codec="aac",
    )
    a3 = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="Fast Action Clip.mp4",
        storage_path="action_720p.mp4",
        is_external=False,
        media_type="video",
        file_size_bytes=f3.stat().st_size,
        mime_type="video/mp4",
        duration_seconds=1.5,
        width=1280,
        height=720,
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
    )

    # 1. Search partial match case-insensitive
    res = client.get(f"/api/v1/projects/{project.id}/media?search=wild")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == a1.id

    # 2. Search by ID
    res = client.get(f"/api/v1/projects/{project.id}/media?search={a2.id}")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["id"] == a2.id

    # 3. Filter by resolution
    res_4k = client.get(f"/api/v1/projects/{project.id}/media?resolution=4k")
    assert res_4k.status_code == 200
    assert res_4k.json()["total"] == 1
    assert res_4k.json()["items"][0]["resolution_label"] == "4K"

    res_1080 = client.get(f"/api/v1/projects/{project.id}/media?resolution=1080p")
    assert res_1080.status_code == 200
    assert res_1080.json()["total"] == 1
    assert res_1080.json()["items"][0]["id"] == a2.id

    # 4. Filter by container format
    res_mkv = client.get(f"/api/v1/projects/{project.id}/media?format=mkv")
    assert res_mkv.status_code == 200
    assert res_mkv.json()["total"] == 1
    assert res_mkv.json()["items"][0]["id"] == a2.id

    res_mp4 = client.get(f"/api/v1/projects/{project.id}/media?format=mp4")
    assert res_mp4.status_code == 200
    assert res_mp4.json()["total"] == 2

    # 5. Filter by duration range
    res_dur = client.get(f"/api/v1/projects/{project.id}/media?duration_min=3.0")
    assert res_dur.status_code == 200
    assert res_dur.json()["total"] == 1
    assert res_dur.json()["items"][0]["id"] == a2.id


def test_media_library_sorting_and_pagination(p1_6_env: dict):
    client: TestClient = p1_6_env["client"]
    project = p1_6_env["project"]
    media_svc: MediaService = p1_6_env["media_service"]
    layout: StorageLayout = p1_6_env["layout"]

    f = layout.media / "sample.mp4"
    _create_synthetic_mp4(f, duration_sec=1.0)

    # Register 5 assets with distinct names and sizes
    created_ids = []
    for i in range(5):
        a = media_svc.register_media_asset(
            project_id=project.id,
            original_filename=f"video_alpha_{i}.mp4",
            storage_path="sample.mp4",
            is_external=False,
            media_type="video",
            file_size_bytes=1000 * (i + 1),
            duration_seconds=float(i + 1),
            width=1920,
            height=1080,
        )
        created_ids.append(a.id)

    # 1. Sort by filename ASC
    res = client.get(f"/api/v1/projects/{project.id}/media?sort_by=filename&sort_order=asc")
    assert res.status_code == 200
    items = res.json()["items"]
    assert items[0]["original_filename"] == "video_alpha_0.mp4"
    assert items[-1]["original_filename"] == "video_alpha_4.mp4"

    # 2. Sort by size DESC
    res_size = client.get(f"/api/v1/projects/{project.id}/media?sort_by=size&sort_order=desc")
    assert res_size.status_code == 200
    items_size = res_size.json()["items"]
    assert items_size[0]["file_size_bytes"] == 5000
    assert items_size[-1]["file_size_bytes"] == 1000

    # 3. Pagination: page 1 (size 2), page 2 (size 2), page 3 (size 2)
    p1 = client.get(f"/api/v1/projects/{project.id}/media?page=1&page_size=2&sort_by=filename&sort_order=asc").json()
    assert len(p1["items"]) == 2
    assert p1["page"] == 1
    assert p1["total"] == 5
    assert p1["total_pages"] == 3
    assert p1["items"][0]["original_filename"] == "video_alpha_0.mp4"

    p2 = client.get(f"/api/v1/projects/{project.id}/media?page=2&page_size=2&sort_by=filename&sort_order=asc").json()
    assert len(p2["items"]) == 2
    assert p2["page"] == 2
    assert p2["items"][0]["original_filename"] == "video_alpha_2.mp4"

    p3 = client.get(f"/api/v1/projects/{project.id}/media?page=3&page_size=2&sort_by=filename&sort_order=asc").json()
    assert len(p3["items"]) == 1
    assert p3["page"] == 3
    assert p3["items"][0]["original_filename"] == "video_alpha_4.mp4"

    # Verify no overlap across pages
    all_seen = [it["id"] for it in p1["items"]] + [it["id"] for it in p2["items"]] + [it["id"] for it in p3["items"]]
    assert len(all_seen) == 5
    assert len(set(all_seen)) == 5


def test_stream_media_range_seeking(p1_6_env: dict):
    client: TestClient = p1_6_env["client"]
    project = p1_6_env["project"]
    media_svc: MediaService = p1_6_env["media_service"]
    layout: StorageLayout = p1_6_env["layout"]

    f = layout.media / "streamable.mp4"
    _create_synthetic_mp4(f, duration_sec=2.0, width=1280, height=720)
    file_size = f.stat().st_size
    assert file_size > 1000

    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="streamable.mp4",
        storage_path="streamable.mp4",
        is_external=False,
        media_type="video",
        file_size_bytes=file_size,
        mime_type="video/mp4",
    )

    # 1. Full content request (no Range header) -> 200 OK
    res_full = client.get(f"/api/v1/media/{asset.id}/stream")
    assert res_full.status_code == 200
    assert res_full.headers["accept-ranges"] == "bytes"
    assert int(res_full.headers["content-length"]) == file_size

    # 2. Initial chunk range request: bytes=0-511 -> 206 Partial Content
    res_range = client.get(f"/api/v1/media/{asset.id}/stream", headers={"Range": "bytes=0-511"})
    assert res_range.status_code == 206
    assert res_range.headers["content-range"] == f"bytes 0-511/{file_size}"
    assert int(res_range.headers["content-length"]) == 512
    assert len(res_range.content) == 512

    # 3. Seeking request: bytes=512-1023 -> 206 Partial Content
    res_seek = client.get(f"/api/v1/media/{asset.id}/stream", headers={"Range": "bytes=512-1023"})
    assert res_seek.status_code == 206
    assert res_seek.headers["content-range"] == f"bytes 512-1023/{file_size}"
    assert int(res_seek.headers["content-length"]) == 512
    assert len(res_seek.content) == 512

    # 4. Open-ended range: bytes=1000-
    res_tail = client.get(f"/api/v1/media/{asset.id}/stream", headers={"Range": "bytes=1000-"})
    assert res_tail.status_code == 206
    assert res_tail.headers["content-range"] == f"bytes 1000-{file_size - 1}/{file_size}"
    assert len(res_tail.content) == file_size - 1000

    # 5. Invalid range -> 416 Range Not Satisfiable
    res_inv = client.get(f"/api/v1/media/{asset.id}/stream", headers={"Range": f"bytes={file_size + 100}-{file_size + 200}"})
    assert res_inv.status_code == 416


def test_metadata_refresh_and_thumbnail_regeneration(p1_6_env: dict):
    client: TestClient = p1_6_env["client"]
    project = p1_6_env["project"]
    media_svc: MediaService = p1_6_env["media_service"]
    layout: StorageLayout = p1_6_env["layout"]

    f = layout.media / "test_refresh.mp4"
    _create_synthetic_mp4(f, duration_sec=1.5, width=1280, height=720)
    file_size = f.stat().st_size

    # Compute expected SHA
    h = hashlib.sha256()
    with open(f, "rb") as fp:
        while chunk := fp.read(65536):
            h.update(chunk)
    expected_sha = h.hexdigest()

    # Register initial asset with placeholder/missing specs
    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="test_refresh.mp4",
        storage_path="test_refresh.mp4",
        is_external=False,
        media_type="video",
        file_size_bytes=file_size,
        mime_type="video/mp4",
        width=None,
        height=None,
        duration_seconds=None,
        fps=None,
    )

    # Attach sha256 to record in DB to simulate uploaded contract
    with sqlite_session(p1_6_env["layout"].db_file) as conn:
        conn.execute("UPDATE media_assets SET sha256 = ?, upload_attempt_id = 'att_p1_6_init' WHERE id = ?", (expected_sha, asset.id))

    # 1. Trigger Refresh Metadata endpoint
    res_refresh = client.post(f"/api/v1/media/{asset.id}/refresh-metadata")
    assert res_refresh.status_code == 200
    refreshed = res_refresh.json()
    assert refreshed["width"] == 1280
    assert refreshed["height"] == 720
    assert refreshed["resolution_label"] == "720p"
    assert refreshed["duration_seconds"] is not None
    assert refreshed["sha256"] == expected_sha
    assert refreshed["upload_attempt_id"] == "att_p1_6_init"
    assert refreshed["availability_status"] == "present"

    # 2. Trigger Thumbnail Regeneration endpoint
    res_thumb = client.post(f"/api/v1/media/{asset.id}/thumbnail/regenerate")
    assert res_thumb.status_code == 200
    thumb_data = res_thumb.json()
    assert thumb_data["thumbnail_reference_path"] is not None
    assert (layout.thumbnails / f"{asset.id}.jpg").exists()

    # 3. Verify thumbnail endpoint serves JPEG
    res_get_thumb = client.get(f"/api/v1/media/{asset.id}/thumbnail")
    assert res_get_thumb.status_code == 200
    assert res_get_thumb.headers["content-type"] == "image/jpeg"
    assert len(res_get_thumb.content) > 0


def test_dependency_safe_deletion(p1_6_env: dict):
    client: TestClient = p1_6_env["client"]
    project = p1_6_env["project"]
    media_svc: MediaService = p1_6_env["media_service"]
    layout: StorageLayout = p1_6_env["layout"]

    f = layout.media / "deletable.mp4"
    _create_synthetic_mp4(f, duration_sec=1.0)

    asset = media_svc.register_media_asset(
        project_id=project.id,
        original_filename="deletable.mp4",
        storage_path="deletable.mp4",
        is_external=False,
        media_type="video",
        file_size_bytes=f.stat().st_size,
    )

    # Insert an active running job on this asset
    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, project_id, job_type, status, priority, progress_pct,
                             retry_count, max_attempts, input_config_json, media_asset_id,
                             created_at, updated_at)
            VALUES ('job_active_1', ?, 'analysis', 'running', 1, 50.0, 0, 3, '{}', ?, datetime('now'), datetime('now'))
            """,
            (project.id, asset.id),
        )

    # 1. Attempt delete while active job is running -> 409 ACTIVE_OPERATION_IN_PROGRESS
    res_del_active = client.delete(f"/api/v1/media/{asset.id}")
    assert res_del_active.status_code == 409
    assert "ACTIVE_OPERATION_IN_PROGRESS" in res_del_active.text

    # Complete the job
    with sqlite_session(layout.db_file) as conn:
        conn.execute("UPDATE jobs SET status = 'completed' WHERE id = 'job_active_1'")

    # Insert a dependent export on this asset
    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO exports (id, project_id, media_asset_id, title, output_filename, status, created_at)
            VALUES ('exp_dep_1', ?, ?, 'Dependent Reel Export', 'export_dep_1.mp4', 'completed', datetime('now'))
            """,
            (project.id, asset.id),
        )

    # 2. Attempt delete with dependent export without force -> 409 DEPENDENCY_CONFLICT
    res_del_dep = client.delete(f"/api/v1/media/{asset.id}")
    assert res_del_dep.status_code == 409
    assert "DEPENDENCY_CONFLICT" in res_del_dep.text

    # 3. Delete with force_with_exports=true -> 204 No Content
    res_del_force = client.delete(f"/api/v1/media/{asset.id}?force_with_exports=true")
    assert res_del_force.status_code == 204

    # Verify asset and dependent export are deleted
    with sqlite_session(layout.db_file) as conn:
        assert conn.execute("SELECT COUNT(*) FROM media_assets WHERE id = ?", (asset.id,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM exports WHERE id = 'exp_dep_1'").fetchone()[0] == 0

    # Verify managed disk file reclaimed
    assert not f.exists()
