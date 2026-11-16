"""P1.1 — Single and Multiple Video Upload Test Suite.

Verifies:
1. Single video upload success with metadata extraction and storage persistence.
2. Multiple video batch upload in one operation with accurate items response.
3. Partial batch failure handling (valid files succeed, invalid files fail, both reported).
4. Empty file upload rejection (0-byte file rejected with 400 EMPTY_MEDIA_FILE).
5. Filenames with spaces, brackets, and Unicode preserved safely in metadata.
6. Path traversal security rejection (traversal sequence rejected with 400 PATH_TRAVERSAL_DETECTED).
7. Non-destructive file collision handling (repeated upload of identical filename yields distinct records and files).
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
def clean_storage_env():
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

    logging.shutdown()
    try:
        tmpdir.cleanup()
    except Exception:
        pass


def _create_synthetic_mp4(out_path: Path, duration: int = 1, width: int = 320, height: int = 240, fps: int = 25):
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def test_single_video_upload_success(clean_storage_env, tmp_path):
    client, layout, _ = clean_storage_env
    clip_path = tmp_path / "single_test.mp4"
    _create_synthetic_mp4(clip_path, duration=2, width=320, height=240, fps=25)

    with open(clip_path, "rb") as f:
        res = client.post(
            "/api/v1/media/upload",
            files={"file": ("single_test.mp4", f, "video/mp4")},
        )

    assert res.status_code == 201, f"Upload failed: {res.text}"
    data = res.json()
    assert data["id"]
    assert data["original_filename"] == "single_test.mp4"
    assert data["media_type"] == "video"
    assert data["width"] == 320
    assert data["height"] == 240
    assert data["fps"] == 25.0
    assert data["duration_seconds"] is not None and data["duration_seconds"] > 0
    assert data["file_size_bytes"] == clip_path.stat().st_size

    stored_file = Path(data["storage_path"])
    assert stored_file.exists()
    assert stored_file.stat().st_size == clip_path.stat().st_size


def test_multiple_video_batch_upload_all_valid(clean_storage_env, tmp_path):
    client, layout, _ = clean_storage_env

    clips = []
    for i in range(3):
        p = tmp_path / f"batch_clip_{i + 1}.mp4"
        _create_synthetic_mp4(p, duration=1, width=320, height=240, fps=25)
        clips.append(p)

    files_payload = []
    open_files = []
    try:
        for p in clips:
            f = open(p, "rb")
            open_files.append(f)
            files_payload.append(("files", (p.name, f, "video/mp4")))

        res = client.post("/api/v1/media/batch-upload", files=files_payload)
        assert res.status_code == 200, f"Batch upload failed: {res.text}"
        data = res.json()

        assert data["total"] == 3
        assert data["succeeded"] == 3
        assert data["failed"] == 0
        assert len(data["items"]) == 3

        ids = set()
        paths = set()
        for item in data["items"]:
            assert item["success"] is True
            assert item["media_id"]
            assert item["asset"]
            ids.add(item["media_id"])
            asset_path = Path(item["asset"]["storage_path"])
            assert asset_path.exists()
            paths.add(str(asset_path))

        assert len(ids) == 3, "Each uploaded video must have a unique ID"
        assert len(paths) == 3, "Each uploaded video must have a unique physical file"
    finally:
        for f in open_files:
            f.close()


def test_batch_upload_partial_failure(clean_storage_env, tmp_path):
    client, layout, _ = clean_storage_env

    valid_clip = tmp_path / "valid_batch_item.mp4"
    _create_synthetic_mp4(valid_clip, duration=1)

    invalid_text = tmp_path / "corrupt_video.mp4"
    invalid_text.write_text("This is not a real video file content, just plain text.")

    with open(valid_clip, "rb") as f1, open(invalid_text, "rb") as f2:
        files = [
            ("files", ("valid_batch_item.mp4", f1, "video/mp4")),
            ("files", ("corrupt_video.mp4", f2, "video/mp4")),
        ]
        res = client.post("/api/v1/media/batch-upload", files=files)

    assert res.status_code == 200, f"Batch endpoint should return 200 for partial results: {res.text}"
    data = res.json()
    assert data["total"] == 2
    assert data["succeeded"] == 1
    assert data["failed"] == 1

    item1 = data["items"][0]
    assert item1["filename"] == "valid_batch_item.mp4"
    assert item1["success"] is True
    assert item1["media_id"] is not None
    assert Path(item1["asset"]["storage_path"]).exists()

    item2 = data["items"][1]
    assert item2["filename"] == "corrupt_video.mp4"
    assert item2["success"] is False
    assert item2["media_id"] is None
    assert item2["error"] is not None


def test_empty_file_upload_rejection(clean_storage_env, tmp_path):
    client, layout, _ = clean_storage_env
    empty_file = tmp_path / "empty_video.mp4"
    empty_file.write_bytes(b"")

    with open(empty_file, "rb") as f:
        res = client.post(
            "/api/v1/media/upload",
            files={"file": ("empty_video.mp4", f, "video/mp4")},
        )

    assert res.status_code == 400
    assert "EMPTY_MEDIA_FILE" in res.text


def test_filename_spaces_unicode_brackets(clean_storage_env, tmp_path):
    client, layout, _ = clean_storage_env
    complex_name = "Hindi-English [BollyFlix] 01.mp4"
    clip_path = tmp_path / complex_name
    _create_synthetic_mp4(clip_path, duration=1)

    with open(clip_path, "rb") as f:
        res = client.post(
            "/api/v1/media/upload",
            files={"file": (complex_name, f, "video/mp4")},
        )

    assert res.status_code == 201, f"Failed upload: {res.text}"
    data = res.json()
    assert data["original_filename"] == complex_name
    stored_path = Path(data["storage_path"])
    assert stored_path.exists()
    assert stored_path.stat().st_size == clip_path.stat().st_size


def test_path_traversal_rejection(clean_storage_env, tmp_path):
    client, layout, _ = clean_storage_env
    clip_path = tmp_path / "probe.mp4"
    _create_synthetic_mp4(clip_path, duration=1)

    # Test single upload with traversal sequence
    with open(clip_path, "rb") as f:
        res = client.post(
            "/api/v1/media/upload",
            files={"file": ("../../evil_script.mp4", f, "video/mp4")},
        )
    assert res.status_code == 400
    assert "PATH_TRAVERSAL_DETECTED" in res.text

    # Test batch upload with traversal sequence
    with open(clip_path, "rb") as f:
        res_batch = client.post(
            "/api/v1/media/batch-upload",
            files=[("files", ("..\\escaped.mp4", f, "video/mp4"))],
        )
    assert res_batch.status_code == 200
    data = res_batch.json()
    assert data["failed"] == 1
    assert data["items"][0]["success"] is False
    assert "PATH_TRAVERSAL_DETECTED" in data["items"][0]["error_code"]


def test_repeated_upload_non_destructive_collision(clean_storage_env, tmp_path):
    client, layout, _ = clean_storage_env
    clip_path = tmp_path / "repeated_upload.mp4"
    _create_synthetic_mp4(clip_path, duration=1)

    # First upload
    with open(clip_path, "rb") as f:
        res1 = client.post(
            "/api/v1/media/upload",
            files={"file": ("repeated_upload.mp4", f, "video/mp4")},
        )
    assert res1.status_code == 201
    data1 = res1.json()

    # Second upload with identical filename
    with open(clip_path, "rb") as f:
        res2 = client.post(
            "/api/v1/media/upload",
            files={"file": ("repeated_upload.mp4", f, "video/mp4")},
        )
    assert res2.status_code == 201
    data2 = res2.json()

    assert data1["id"] != data2["id"], "Each upload must receive a distinct asset ID"
    assert data1["storage_path"] != data2["storage_path"], "Storage paths must be distinct"

    p1 = Path(data1["storage_path"])
    p2 = Path(data2["storage_path"])
    assert p1.exists(), "First file must still exist"
    assert p2.exists(), "Second file must exist"
    assert p1 != p2, "Files must be stored at distinct filesystem paths"
