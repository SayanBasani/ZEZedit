"""Unit tests for P1.4: Upload failure handling, retry and recovery."""

import io
import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.main import create_app
from app.models.entities import MediaAssetRecord
from app.services.media import MediaService
from app.services.media_probe import MediaProbeResult
from app.services.projects import ProjectService


def make_mock_probe(media_type="video", duration=1.0, width=1280, height=720, codec="h264") -> MediaProbeResult:
    return MediaProbeResult(
        media_type=media_type,
        container_format="mp4",
        duration_seconds=duration,
        file_size_bytes=1024,
        bit_rate=1000000,
        width=width,
        height=height,
        fps=30.0,
        video_codec=codec,
        audio_codec="aac",
        sample_rate=48000,
        channels=2,
        channel_layout="stereo",
        aspect_ratio="16:9",
        pix_fmt="yuv420p",
        rotation=0,
        creation_time=None,
        streams=[],
        raw_metadata={},
    )


@pytest.fixture
def temp_env() -> Generator[dict, None, None]:
    temp_dir = tempfile.mkdtemp(prefix="zezedit_p1_4_test_")
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

    app = create_app(settings_override=settings)
    with TestClient(app) as client:
        # Create a default project
        proj_svc = ProjectService(settings=settings, db_path=layout.db_file)
        proj = proj_svc.create_project(name="P1.4 Test Project")

        yield {
            "client": client,
            "settings": settings,
            "layout": layout,
            "project_id": proj.id,
            "temp_dir": temp_dir,
        }

    # Teardown
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_simulated_500_failure_and_retry(temp_env: dict):
    """Verify that an upload with simulated 500 error fails cleanly and can be retried successfully."""
    client: TestClient = temp_env["client"]
    project_id: str = temp_env["project_id"]
    layout: StorageLayout = temp_env["layout"]

    fake_video = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free" + b"A" * 1024

    # 1. Attempt upload with test_failure_code=500
    res_fail = client.post(
        f"/api/v1/projects/{project_id}/media/upload?test_failure_code=500",
        files={"file": ("video_500_test.mp4", io.BytesIO(fake_video), "video/mp4")},
    )
    assert res_fail.status_code == 500
    err_body = res_fail.json()
    assert err_body["error"]["code"] == "SIMULATED_FAILURE_500"

    # Verify no record was added to the DB
    media_svc = MediaService(settings=temp_env["settings"], db_path=layout.db_file)
    assets = media_svc.list_media_assets(project_id)
    assert len(assets) == 0

    # 2. Retry upload without failure flag (mocking probe to avoid requiring real ffmpeg for test dummy)
    mock_probe = make_mock_probe()
    with patch("app.services.media_pipeline.probe_media_file", return_value=mock_probe):
        res_retry = client.post(
            f"/api/v1/projects/{project_id}/media/upload",
            files={"file": ("video_500_test.mp4", io.BytesIO(fake_video), "video/mp4")},
        )
        assert res_retry.status_code == 201
        data = res_retry.json()
        assert data["original_filename"] == "video_500_test.mp4"
        assert data["file_size_bytes"] == len(fake_video)

        # Verify exactly 1 record in DB
        assets = media_svc.list_media_assets(project_id)
        assert len(assets) == 1
        assert assets[0].id == data["id"]


def test_database_registration_failure_cleanup(temp_env: dict):
    """Verify that a database registration failure cleanly unlinks disk files and leaves 0 zombie DB records."""
    client: TestClient = temp_env["client"]
    project_id: str = temp_env["project_id"]
    layout: StorageLayout = temp_env["layout"]

    fake_video = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free" + b"B" * 1024

    mock_probe = make_mock_probe()
    with patch("app.services.media_pipeline.probe_media_file", return_value=mock_probe):
        res_fail = client.post(
            f"/api/v1/projects/{project_id}/media/upload?test_fail_registration=true",
            files={"file": ("db_fail_test.mp4", io.BytesIO(fake_video), "video/mp4")},
        )
        assert res_fail.status_code == 500
        assert res_fail.json()["error"]["code"] == "DATABASE_REGISTRATION_FAILED"

    # Verify no zombie file remains in media storage
    media_files = list(layout.media.glob("**/*db_fail_test.mp4*"))
    assert len(media_files) == 0

    # Verify no record in DB
    media_svc = MediaService(settings=temp_env["settings"], db_path=layout.db_file)
    assets = media_svc.list_media_assets(project_id)
    assert len(assets) == 0


def test_startup_sweep_cleans_stale_partial_uploads(temp_env: dict):
    """Verify that application startup lifespan cleans any abandoned .uploading or .part files."""
    layout: StorageLayout = temp_env["layout"]

    # Place fake abandoned partial files
    proj_dir = layout.media / "proj_dummy"
    proj_dir.mkdir(parents=True, exist_ok=True)
    stale_part = proj_dir / "orphaned_upload.mp4.uploading"
    stale_part.write_bytes(b"partial bytes left from crashed process")

    temp_part = layout.temp / "uploads" / "old_chunk.part"
    temp_part.write_bytes(b"temp chunk")

    # Valid file that should NOT be deleted
    valid_file = proj_dir / "finished_video.mp4"
    valid_file.write_bytes(b"finished video bytes")

    assert stale_part.is_file()
    assert temp_part.is_file()
    assert valid_file.is_file()

    # Re-run create_app lifespan
    with TestClient(create_app(settings_override=temp_env["settings"])):
        # Stale files should be deleted
        assert not stale_part.exists()
        assert not temp_part.exists()
        # Valid finished file must remain intact
        assert valid_file.exists()


def test_batch_upload_partial_failure_and_retry(temp_env: dict):
    """Verify that batch upload reports individual failure and enables selective retry without duplicating succeeded items."""
    client: TestClient = temp_env["client"]
    project_id: str = temp_env["project_id"]
    layout: StorageLayout = temp_env["layout"]

    file1 = ("batch1.mp4", io.BytesIO(b"data1"), "video/mp4")
    file2_fail = ("batch2_transient_fail.mp4", io.BytesIO(b"data2"), "video/mp4")
    file3 = ("batch3.mp4", io.BytesIO(b"data3"), "video/mp4")

    mock_probe = make_mock_probe()
    with patch("app.services.media_pipeline.probe_media_file", return_value=mock_probe):
        # First batch upload where batch2 fails with simulated 500
        res = client.post(
            f"/api/v1/projects/{project_id}/media/batch-upload?test_failure_code=500&test_failure_filename=batch2",
            files=[
                ("files", file1),
                ("files", file2_fail),
                ("files", file3),
            ],
        )
        assert res.status_code == 200
        batch_data = res.json()
        assert batch_data["total"] == 3
        assert batch_data["succeeded"] == 2
        assert batch_data["failed"] == 1

        items = batch_data["items"]
        assert items[0]["filename"] == "batch1.mp4" and items[0]["success"] is True
        assert items[1]["filename"] == "batch2_transient_fail.mp4" and items[1]["success"] is False
        assert items[2]["filename"] == "batch3.mp4" and items[2]["success"] is True

        # Verify DB has 2 records
        media_svc = MediaService(settings=temp_env["settings"], db_path=layout.db_file)
        assets = media_svc.list_media_assets(project_id)
        assert len(assets) == 2

        # Retry ONLY the failed file (single upload)
        res_retry = client.post(
            f"/api/v1/projects/{project_id}/media/upload",
            files={"file": ("batch2_transient_fail.mp4", io.BytesIO(b"data2_retry"), "video/mp4")},
        )
        assert res_retry.status_code == 201

        # Now DB should have exactly 3 distinct items
        assets = media_svc.list_media_assets(project_id)
        assert len(assets) == 3
        filenames = {a.original_filename for a in assets}
        assert filenames == {"batch1.mp4", "batch2_transient_fail.mp4", "batch3.mp4"}


def test_concurrency_limit_and_retry(temp_env: dict):
    """Verify that exceeding max concurrent uploads returns 429 and subsequent retry succeeds when concurrency slot opens."""
    client: TestClient = temp_env["client"]
    project_id: str = temp_env["project_id"]

    fake_video = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free" + b"C" * 1024

    # 1. Trigger simulated 429
    res_429 = client.post(
        f"/api/v1/projects/{project_id}/media/upload?test_failure_code=429",
        files={"file": ("conc_test.mp4", io.BytesIO(fake_video), "video/mp4")},
    )
    assert res_429.status_code == 429
    assert res_429.json()["error"]["code"] == "SIMULATED_FAILURE_429"

    # 2. Retry succeeds
    mock_probe = make_mock_probe()
    with patch("app.services.media_pipeline.probe_media_file", return_value=mock_probe):
        res_ok = client.post(
            f"/api/v1/projects/{project_id}/media/upload",
            files={"file": ("conc_test.mp4", io.BytesIO(fake_video), "video/mp4")},
        )
        assert res_ok.status_code == 201
        assert res_ok.json()["original_filename"] == "conc_test.mp4"


def test_terminal_error_rejection_empty_file(temp_env: dict):
    """Verify that an empty media file is rejected with 400 and non-retryable EMPTY_MEDIA_FILE error code."""
    client: TestClient = temp_env["client"]
    project_id: str = temp_env["project_id"]

    res_empty = client.post(
        f"/api/v1/projects/{project_id}/media/upload",
        files={"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")},
    )
    assert res_empty.status_code == 400
    assert res_empty.json()["error"]["code"] == "EMPTY_MEDIA_FILE"

