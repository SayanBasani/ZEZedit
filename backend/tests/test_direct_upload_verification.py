"""Comprehensive Direct Video Upload verification test suite.

Verifies:
1. Upload valid MP4.
2. Upload valid MKV.
3. Attempt invalid text file (rejected with 400).
4. Attempt corrupt video file (rejected with 400).
5. Attempt misleading extension (e.g. text file renamed to .mp4, rejected with 400).
6. Verify default title is derived from original filename.
7. Rename the video using PATCH /media/{asset_id}.
8. Refresh / retrieve and verify persistence of updated metadata.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations


@pytest.fixture
def client_with_clean_storage():
    tmpdir = TemporaryDirectory()
    settings = Settings(storage_root=tmpdir.name)
    layout = StorageLayout.from_root(tmpdir.name)
    layout.ensure_directories()

    run_migrations(
        db_path=layout.db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=layout.backups,
    )

    test_app = create_app(settings)
    with TestClient(test_app) as client:
        yield client, layout, settings

    # Clean up logging file handlers so Windows doesn't lock zezedit.log
    logging.shutdown()
    try:
        tmpdir.cleanup()
    except Exception:
        pass


@pytest.fixture
def sample_videos(tmp_path: Path):
    """Generate minimal valid MP4 and MKV videos using FFmpeg."""
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    mp4_path = tmp_path / "valid_clip.mp4"
    mkv_path = tmp_path / "valid_clip.mkv"

    # 1s video, 320x240, 25fps
    subprocess.run(
        [
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(mp4_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    subprocess.run(
        [
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(mkv_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return mp4_path, mkv_path


def test_upload_valid_mp4(client_with_clean_storage, sample_videos):
    client, _, _ = client_with_clean_storage
    mp4_path, _ = sample_videos

    with open(mp4_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/v1/media/upload?project_id=default",
        files={"file": ("cinematic_feature_trailer.mp4", file_bytes, "video/mp4")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "cinematic_feature_trailer.mp4"
    assert data["media_type"] == "video"
    assert data["width"] == 320
    assert data["height"] == 240
    assert data["duration_seconds"] is not None and data["duration_seconds"] > 0


def test_upload_valid_mkv(client_with_clean_storage, sample_videos):
    client, _, _ = client_with_clean_storage
    _, mkv_path = sample_videos

    with open(mkv_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/v1/media/upload?project_id=default",
        files={"file": ("raw_recording_stream.mkv", file_bytes, "video/x-matroska")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "raw_recording_stream.mkv"
    assert data["media_type"] == "video"
    assert data["width"] == 320
    assert data["height"] == 240


def test_upload_invalid_text_file(client_with_clean_storage):
    client, _, _ = client_with_clean_storage
    invalid_content = b"This is a plain text file, not a video."
    response = client.post(
        "/api/v1/media/upload?project_id=default",
        files={"file": ("notes.txt", invalid_content, "text/plain")},
    )
    assert response.status_code == 400


def test_upload_corrupt_video(client_with_clean_storage):
    client, _, _ = client_with_clean_storage
    garbage = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00" + b"\xff" * 128
    response = client.post(
        "/api/v1/media/upload?project_id=default",
        files={"file": ("corrupt_sample.mp4", garbage, "video/mp4")},
    )
    assert response.status_code == 400


def test_upload_misleading_extension(client_with_clean_storage):
    client, _, _ = client_with_clean_storage
    fake_mp4 = b"Hello world! I am actually text masquerading as an MP4 container."
    response = client.post(
        "/api/v1/media/upload?project_id=default",
        files={"file": ("fake_video.mp4", fake_mp4, "video/mp4")},
    )
    assert response.status_code == 400


def test_rename_video_and_verify_persistence(client_with_clean_storage, sample_videos):
    client, _, _ = client_with_clean_storage
    mp4_path, _ = sample_videos

    with open(mp4_path, "rb") as f:
        file_bytes = f.read()

    # 1. Upload
    up_res = client.post(
        "/api/v1/media/upload?project_id=default",
        files={"file": ("raw_interview_tape.mp4", file_bytes, "video/mp4")},
    )
    assert up_res.status_code == 201
    asset_id = up_res.json()["id"]

    # 2. Rename video via PATCH /media/{asset_id}
    patch_res = client.patch(
        f"/api/v1/media/{asset_id}",
        json={"original_filename": "Director Cut Final Interview.mp4"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["original_filename"] == "Director Cut Final Interview.mp4"

    # 3. Retrieve / refresh via GET /media/{asset_id}
    get_res = client.get(f"/api/v1/media/{asset_id}")
    assert get_res.status_code == 200
    assert get_res.json()["original_filename"] == "Director Cut Final Interview.mp4"
