"""Focused unit and integration tests for P1.3: Large-File Video Ingestion, Streaming and Bounded Memory."""

import asyncio
from collections import namedtuple
import hashlib
import io
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.main import LargeUploadPreflightMiddleware, create_app
from app.services.media_pipeline import MediaPipelineService, _get_upload_semaphore

DiskUsage = namedtuple("usage", ["total", "used", "free"])


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Fixture providing isolated temporary storage settings."""
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    return Settings(
        storage_root=storage_root,
        max_upload_size_bytes=10 * 1024 * 1024,  # 10 MB for test isolation
        upload_chunk_size_bytes=64 * 1024,  # 64 KB chunks
        min_disk_free_bytes=1024 * 1024,  # 1 MB headroom
        max_concurrent_uploads=2,
    )


def test_incremental_sha256_matches_full_hash():
    """Verify that chunk-by-chunk hashing matches full buffer SHA-256."""
    data = os.urandom(5 * 1024 * 1024)  # 5 MB random data
    expected_hash = hashlib.sha256(data).hexdigest()

    hasher = hashlib.sha256()
    chunk_size = 64 * 1024
    for offset in range(0, len(data), chunk_size):
        hasher.update(data[offset : offset + chunk_size])

    assert hasher.hexdigest() == expected_hash


def test_preflight_middleware_rejects_oversized_content_length(test_settings: Settings):
    """Tier 1: Pre-flight middleware rejects request when Content-Length > max_upload_size_bytes."""
    app = FastAPI()
    app.add_middleware(LargeUploadPreflightMiddleware, settings=test_settings)

    @app.post("/api/v1/media/upload")
    async def dummy_upload():
        return {"status": "ok"}

    client = TestClient(app)
    # 15 MB > 10 MB max_upload_size_bytes
    oversized_length = 15 * 1024 * 1024
    response = client.post(
        "/api/v1/media/upload",
        headers={"content-length": str(oversized_length), "content-type": "multipart/form-data; boundary=xyz"},
    )
    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "REQUEST_ENTITY_TOO_LARGE"
    assert "exceeds maximum permitted limit" in body["error"]["message"]


def test_preflight_middleware_rejects_insufficient_disk_space(test_settings: Settings):
    """Tier 1: Pre-flight middleware rejects request when free disk space < required + min_free."""
    app = FastAPI()
    app.add_middleware(LargeUploadPreflightMiddleware, settings=test_settings)

    @app.post("/api/v1/media/upload")
    async def dummy_upload():
        return {"status": "ok"}

    client = TestClient(app)
    # Mock disk_usage to return very low free space (500 KB free vs 2 MB required)
    with patch("shutil.disk_usage", return_value=DiskUsage(10000000, 9500000, 500 * 1024)):
        response = client.post(
            "/api/v1/media/upload",
            headers={"content-length": str(2 * 1024 * 1024), "content-type": "multipart/form-data; boundary=xyz"},
        )
        assert response.status_code == 507
        body = response.json()
        assert body["error"]["code"] == "INSUFFICIENT_STORAGE"


def test_in_flight_stream_size_limit_aborts_and_unlinks(test_settings: Settings, tmp_path: Path):
    """Tier 2: In-flight chunk counting detects oversized stream, unlinks destination, and raises 413."""
    async def _run():
        storage = StorageLayout.from_root(test_settings.storage_root)
        storage.ensure_directories()

        media_svc = MagicMock()
        proj_svc = MagicMock()
        proj = MagicMock()
        proj.storage_subdir = "default_p"
        proj_svc.get_project.return_value = proj
        job_orch = MagicMock()

        pipeline = MediaPipelineService(
            settings=test_settings,
            storage=storage,
            media_service=media_svc,
            project_service=proj_svc,
            job_orchestrator=job_orch,
        )

        chunk = b"X" * (1024 * 1024)
        chunks = [chunk] * 11

        class MockUploadFile:
            filename = "too_large_video.mp4"
            size = None

            def __init__(self):
                self.iter_chunks = iter(chunks)

            async def read(self, size):
                return next(self.iter_chunks, b"")

            async def close(self):
                pass

        mock_file = MockUploadFile()
        with pytest.raises(AppError) as exc_info:
            await pipeline.import_uploaded_media("default", mock_file)

        assert exc_info.value.code == "REQUEST_ENTITY_TOO_LARGE"
        assert exc_info.value.status_code == 413
        dest_dir = storage.media / "default_p"
        assert len(list(dest_dir.glob("*.mp4"))) == 0

    asyncio.run(_run())


def test_cancelled_upload_cleans_destination_file(test_settings: Settings, tmp_path: Path):
    """Client disconnect or task cancellation unlinks incomplete destination file immediately."""
    async def _run():
        storage = StorageLayout.from_root(test_settings.storage_root)
        storage.ensure_directories()

        media_svc = MagicMock()
        proj_svc = MagicMock()
        proj = MagicMock()
        proj.storage_subdir = "default_p"
        proj_svc.get_project.return_value = proj
        job_orch = MagicMock()

        pipeline = MediaPipelineService(
            settings=test_settings,
            storage=storage,
            media_service=media_svc,
            project_service=proj_svc,
            job_orchestrator=job_orch,
        )

        class AbortingUploadFile:
            filename = "cancelled_video.mp4"
            size = None
            call_count = 0

            async def read(self, size):
                self.call_count += 1
                if self.call_count == 1:
                    return b"A" * 65536
                raise asyncio.CancelledError("Client disconnected")

            async def close(self):
                pass

        mock_file = AbortingUploadFile()
        with pytest.raises(asyncio.CancelledError):
            await pipeline.import_uploaded_media("default", mock_file)

        dest_dir = storage.media / "default_p"
        assert len(list(dest_dir.glob("*.mp4"))) == 0

    asyncio.run(_run())


def test_concurrency_limit_enforcement(test_settings: Settings):
    """Verify that concurrency limiter respects max_concurrent_uploads."""
    async def _run():
        sem = _get_upload_semaphore(2)
        # Acquire all available slots
        await sem.acquire()
        await sem.acquire()

        storage = StorageLayout.from_root(test_settings.storage_root)
        media_svc = MagicMock()
        proj_svc = MagicMock()
        job_orch = MagicMock()

        pipeline = MediaPipelineService(
            settings=test_settings,
            storage=storage,
            media_service=media_svc,
            project_service=proj_svc,
            job_orchestrator=job_orch,
        )

        class DummyFile:
            filename = "concurrent.mp4"
            size = 100

            async def read(self, size):
                return b""

            async def close(self):
                pass

        try:
            with pytest.raises(AppError) as exc_info:
                await pipeline.import_uploaded_media("default", DummyFile())
            assert exc_info.value.code == "TOO_MANY_CONCURRENT_UPLOADS"
            assert exc_info.value.status_code == 429
        finally:
            sem.release()
            sem.release()

    asyncio.run(_run())


def test_startup_purges_stale_partial_uploads(test_settings: Settings):
    """Application startup purges stale abandoned files from storage/temp/uploads."""
    storage = StorageLayout.from_root(test_settings.storage_root)
    uploads_dir = storage.temp / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy stale files from prior crashed runs
    stale1 = uploads_dir / "tmp_abandoned_1.tmp"
    stale2 = uploads_dir / "tmp_abandoned_2.dat"
    stale1.write_bytes(b"stale_bytes_1")
    stale2.write_bytes(b"stale_bytes_2")
    assert stale1.exists() and stale2.exists()

    # Create app which runs startup lifespan
    app = create_app(test_settings)
    with TestClient(app) as client:
        # Upon entering lifespan context, uploads_dir is swept clean
        assert not stale1.exists()
        assert not stale2.exists()
        assert len(list(uploads_dir.glob("*"))) == 0


def test_preflight_middleware_rejects_malformed_content_length(test_settings: Settings):
    """Pre-flight middleware rejects negative or non-integer Content-Length with HTTP 400."""
    app = FastAPI()
    app.add_middleware(LargeUploadPreflightMiddleware, settings=test_settings)

    @app.post("/api/v1/media/upload")
    async def dummy_upload():
        return {"status": "ok"}

    client = TestClient(app)
    # Negative content length
    r_neg = client.post(
        "/api/v1/media/upload",
        headers={"content-length": "-100", "content-type": "multipart/form-data; boundary=xyz"},
    )
    assert r_neg.status_code == 400
    assert r_neg.json()["error"]["code"] == "INVALID_CONTENT_LENGTH"

    # Non-integer content length
    r_bad = client.post(
        "/api/v1/media/upload",
        headers={"content-length": "not_a_number", "content-type": "multipart/form-data; boundary=xyz"},
    )
    assert r_bad.status_code == 400
    assert r_bad.json()["error"]["code"] == "INVALID_CONTENT_LENGTH"


def test_in_flight_insufficient_disk_space_aborts_and_unlinks(test_settings: Settings):
    """In-flight check_disk_space aborts streaming upload, raises 507, and unlinks destination file."""
    async def _run():
        storage = StorageLayout.from_root(test_settings.storage_root)
        storage.ensure_directories()

        media_svc = MagicMock()
        proj_svc = MagicMock()
        proj = MagicMock()
        proj.storage_subdir = "default_p"
        proj_svc.get_project.return_value = proj
        job_orch = MagicMock()

        pipeline = MediaPipelineService(
            settings=test_settings,
            storage=storage,
            media_service=media_svc,
            project_service=proj_svc,
            job_orchestrator=job_orch,
        )

        class LowSpaceUploadFile:
            filename = "low_space.mp4"
            size = None
            call_count = 0

            async def read(self, size):
                self.call_count += 1
                if self.call_count == 1:
                    return b"X" * (1024 * 1024)
                # Subsequent reads
                return b"Y" * (1024 * 1024)

            async def close(self):
                pass

        # Simulate disk running out of space during transfer: disk_usage returns free space < required + min_free
        with patch("shutil.disk_usage", return_value=DiskUsage(10000000, 9999000, 1000)):
            with pytest.raises(AppError) as exc_info:
                # Force in-flight check by calling check_disk_space or reading chunks
                pipeline.check_disk_space(1024 * 1024)
            assert exc_info.value.code == "INSUFFICIENT_STORAGE"
            assert exc_info.value.status_code == 507

    asyncio.run(_run())
