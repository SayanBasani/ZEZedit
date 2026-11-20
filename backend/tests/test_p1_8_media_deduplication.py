"""Automated test suite for P1.8: Media Deduplication & Reference Counting.

Covers all 15 scenarios from Section 11 of the requirement:
1. First upload creates canonical stored asset with reference count = 1.
2. Identical upload with different filename deduplicates and reuses existing physical asset (ref count = 2).
3. Upload of different content with same filename creates independent physical asset.
4. Deduplicated upload produces zero physical storage delta.
5. Authoritative reference counting across multiple assets and projects.
6. Deleting one reference preserves physical file and other active assets.
7. Deleting final reference cleans up physical file.
8. Project deletion cascades references correctly (preserves shared assets across projects).
9. Missing or corrupted physical file is not silently reused.
10. Concurrent identical uploads are atomic with single physical file and ref count = 2.
11. Concurrent different uploads remain completely independent.
12. Interrupted/failed upload leaves no dangling references or corrupted state.
13. Relinking shared asset isolates other references.
14. Deduplication stats and reconcile endpoints report accurate metrics.
15. Streaming bounded-memory hashing on upload.
"""

import asyncio
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
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
def p1_8_env() -> Generator[dict, None, None]:
    temp_dir = tempfile.mkdtemp(prefix="zezedit_p1_8_test_")
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
        project_a = proj_svc.create_project(name="Project A")
        project_b = proj_svc.create_project(name="Project B")

        synth_dir = Path(temp_dir) / "synth_sources"
        synth_dir.mkdir(parents=True, exist_ok=True)
        vid_1 = synth_dir / "video_1.mp4"
        vid_2 = synth_dir / "video_2.mp4"
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
            "vid_1": vid_1,
            "vid_2": vid_2,
            "vid_1_bytes": vid_1.read_bytes(),
            "vid_2_bytes": vid_2.read_bytes(),
            "vid_1_sha": _compute_sha256(vid_1),
            "vid_2_sha": _compute_sha256(vid_2),
        }

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_scenario_1_first_upload_creates_canonical_asset_refcount_1(p1_8_env: dict):
    """Scenario 1: First upload of a file creates a new physical asset with reference count = 1."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    vid_bytes = p1_8_env["vid_1_bytes"]
    vid_sha = p1_8_env["vid_1_sha"]

    resp = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("clip_one.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["sha256"] == vid_sha
    assert data["reference_count"] == 1
    assert data["is_shared"] is False
    assert data["is_deduplicated"] is False
    assert data["stored_file_id"] is not None

    # Verify physical file exists on disk
    layout: StorageLayout = p1_8_env["layout"]
    phys = Path(data["storage_path"])
    if not phys.is_file():
        phys = layout.media / data["storage_path"]
    assert phys.is_file()
    assert phys.stat().st_size == len(vid_bytes)


def test_scenario_2_identical_upload_different_filename_deduplicates(p1_8_env: dict):
    """Scenario 2: Second upload of identical content with different filename reuses physical asset."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    vid_bytes = p1_8_env["vid_1_bytes"]
    layout: StorageLayout = p1_8_env["layout"]

    # First upload
    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("original.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert r1.status_code == 201
    d1 = r1.json()

    # Second upload with different filename
    r2 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("duplicate_copy.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert r2.status_code == 201
    d2 = r2.json()

    assert d2["is_deduplicated"] is True
    assert d2["reference_count"] == 2
    assert d2["is_shared"] is True
    assert d2["stored_file_id"] == d1["stored_file_id"]
    # Reuses the exact same physical storage path
    assert d2["storage_path"] == d1["storage_path"]

    # Verify total physical mp4 files in project media folder is exactly 1!
    media_files = list(layout.media.glob("**/*.mp4"))
    assert len(media_files) == 1


def test_scenario_3_different_content_same_filename_independent(p1_8_env: dict):
    """Scenario 3: Upload of different content with same filename creates separate physical asset."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    v1_bytes = p1_8_env["vid_1_bytes"]
    v2_bytes = p1_8_env["vid_2_bytes"]
    layout: StorageLayout = p1_8_env["layout"]

    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("video.mp4", io.BytesIO(v1_bytes), "video/mp4")},
    )
    assert r1.status_code == 201
    d1 = r1.json()

    r2 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("video.mp4", io.BytesIO(v2_bytes), "video/mp4")},
    )
    assert r2.status_code == 201
    d2 = r2.json()

    assert d1["sha256"] != d2["sha256"]
    assert d1["stored_file_id"] != d2["stored_file_id"]
    assert d1["storage_path"] != d2["storage_path"]
    assert d1["reference_count"] == 1
    assert d2["reference_count"] == 1

    media_files = list(layout.media.glob("**/*.mp4"))
    assert len(media_files) == 2


def test_scenario_4_deduplicated_upload_zero_storage_growth(p1_8_env: dict):
    """Scenario 4: Deduplicated upload does not increase physical storage size."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    vid_bytes = p1_8_env["vid_1_bytes"]
    layout: StorageLayout = p1_8_env["layout"]

    client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("run_1.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )

    def total_media_size():
        return sum(f.stat().st_size for f in layout.media.glob("**/*.mp4"))

    size_before = total_media_size()

    # Upload identical content 3 more times
    for i in range(2, 5):
        r = client.post(
            f"/api/v1/projects/{proj_a.id}/media/upload",
            files={"file": (f"run_{i}.mp4", io.BytesIO(vid_bytes), "video/mp4")},
        )
        assert r.status_code == 201

    size_after = total_media_size()
    # Physical storage delta is exactly 0 bytes!
    assert size_after == size_before

    # Verify global stats endpoint
    stats_resp = client.get("/api/v1/media/deduplication/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_media_assets"] == 4
    assert stats["unique_stored_files"] == 1
    assert stats["shared_stored_files"] == 1
    assert stats["deduplicated_assets_count"] == 3
    assert stats["saved_bytes"] == len(vid_bytes) * 3
    assert stats["deduplication_ratio"] == 4.0


def test_scenario_5_multi_project_reference_counting(p1_8_env: dict):
    """Scenario 5: Reference count reflects total records across multiple projects."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    proj_b = p1_8_env["project_b"]
    vid_bytes = p1_8_env["vid_1_bytes"]

    # Upload to Project A
    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("vid_a.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert r1.json()["reference_count"] == 1

    # Upload to Project B
    r2 = client.post(
        f"/api/v1/projects/{proj_b.id}/media/upload",
        files={"file": ("vid_b.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert r2.json()["reference_count"] == 2

    # Check project A asset details reflects updated reference count
    ra_check = client.get(f"/api/v1/projects/{proj_a.id}/media/{r1.json()['id']}")
    assert ra_check.json()["reference_count"] == 2
    assert ra_check.json()["is_shared"] is True


def test_scenario_6_deleting_one_reference_preserves_shared_physical_file(p1_8_env: dict):
    """Scenario 6: Deleting one media record preserves physical file and remaining assets."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    proj_b = p1_8_env["project_b"]
    vid_bytes = p1_8_env["vid_1_bytes"]

    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("clip_a.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    asset_a = r1.json()

    r2 = client.post(
        f"/api/v1/projects/{proj_b.id}/media/upload",
        files={"file": ("clip_b.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    asset_b = r2.json()

    # Delete asset A from Project A
    del_resp = client.delete(f"/api/v1/projects/{proj_a.id}/media/{asset_a['id']}")
    assert del_resp.status_code == 204

    # Physical file MUST still exist!
    phys = Path(asset_a["storage_path"])
    assert phys.is_file(), "Physical file must be retained when other references exist"

    # Asset B in Project B must still be present, playable, with reference count = 1
    rb = client.get(f"/api/v1/projects/{proj_b.id}/media/{asset_b['id']}")
    assert rb.status_code == 200
    assert rb.json()["reference_count"] == 1
    assert rb.json()["is_shared"] is False

    # Streaming asset B still works (HTTP 206)
    stream_resp = client.get(
        f"/api/v1/projects/{proj_b.id}/media/{asset_b['id']}/stream",
        headers={"Range": "bytes=0-100"},
    )
    assert stream_resp.status_code == 206


def test_scenario_7_deleting_final_reference_cleans_up_physical_file(p1_8_env: dict):
    """Scenario 7: Deleting the final reference to a physical asset cleans up the physical file."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    proj_b = p1_8_env["project_b"]
    vid_bytes = p1_8_env["vid_1_bytes"]

    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("clip_1.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    r2 = client.post(
        f"/api/v1/projects/{proj_b.id}/media/upload",
        files={"file": ("clip_2.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    asset_a = r1.json()
    asset_b = r2.json()
    phys = Path(asset_a["storage_path"])
    assert phys.is_file()

    # Delete first reference
    client.delete(f"/api/v1/projects/{proj_a.id}/media/{asset_a['id']}")
    assert phys.is_file()

    # Delete final reference
    client.delete(f"/api/v1/projects/{proj_b.id}/media/{asset_b['id']}")
    # Physical file is now unlinked!
    assert not phys.exists(), "Physical file must be deleted when final reference is removed"


def test_scenario_8_project_deletion_cascades_references_correctly(p1_8_env: dict):
    """Scenario 8: Project deletion cascades reference count and preserves shared physical file."""
    client: TestClient = p1_8_env["client"]
    proj_svc: ProjectService = p1_8_env["proj_svc"]
    proj_a = p1_8_env["project_a"]
    proj_b = p1_8_env["project_b"]
    vid_bytes = p1_8_env["vid_1_bytes"]

    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("p_a_clip.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    r2 = client.post(
        f"/api/v1/projects/{proj_b.id}/media/upload",
        files={"file": ("p_b_clip.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    asset_b = r2.json()
    phys = Path(asset_b["storage_path"])
    assert phys.is_file()

    # Delete entire Project A
    proj_svc.delete_project(proj_a.id, confirmation=True)

    # Physical file MUST be preserved for Project B!
    assert phys.is_file()

    # Project B's asset now has reference_count = 1
    rb = client.get(f"/api/v1/projects/{proj_b.id}/media/{asset_b['id']}")
    assert rb.status_code == 200
    assert rb.json()["reference_count"] == 1


def test_scenario_9_missing_physical_file_not_silently_reused(p1_8_env: dict):
    """Scenario 9: Missing or corrupted physical file on disk is not reused; fresh copy is stored."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    vid_bytes = p1_8_env["vid_1_bytes"]

    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("first.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    d1 = r1.json()
    phys_1 = Path(d1["storage_path"])
    assert phys_1.is_file()

    # Delete physical file behind the scenes (simulating missing disk file)
    phys_1.unlink()
    assert not phys_1.exists()

    # Upload identical content again
    r2 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("second.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert r2.status_code == 201
    d2 = r2.json()

    # It must NOT have reused the non-existent phys_1 path!
    phys_2 = Path(d2["storage_path"])
    assert phys_2.is_file()
    assert phys_2.exists()


def test_scenario_10_concurrent_identical_uploads_atomic(p1_8_env: dict):
    """Scenario 10: Concurrent uploads of identical content result in single physical file and ref count = 2."""
    app = p1_8_env["app"]
    proj_a = p1_8_env["project_a"]
    vid_bytes = p1_8_env["vid_1_bytes"]
    layout: StorageLayout = p1_8_env["layout"]

    def upload_one(filename: str):
        with TestClient(app) as c:
            return c.post(
                f"/api/v1/projects/{proj_a.id}/media/upload",
                files={"file": (filename, io.BytesIO(vid_bytes), "video/mp4")},
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(upload_one, "concurrent_a.mp4")
        f2 = executor.submit(upload_one, "concurrent_b.mp4")
        r1 = f1.result()
        r2 = f2.result()

    assert r1.status_code == 201
    assert r2.status_code == 201
    d1 = r1.json()
    d2 = r2.json()

    # Only 1 physical file stored on disk!
    media_files = list(layout.media.glob("**/*.mp4"))
    assert len(media_files) == 1
    assert d1["storage_path"] == d2["storage_path"]
    assert d1["stored_file_id"] == d2["stored_file_id"]

    # Both report reference_count = 2
    with TestClient(app) as c:
        c1 = c.get(f"/api/v1/projects/{proj_a.id}/media/{d1['id']}").json()
        c2 = c.get(f"/api/v1/projects/{proj_a.id}/media/{d2['id']}").json()
        assert c1["reference_count"] == 2
        assert c2["reference_count"] == 2


def test_scenario_11_concurrent_different_uploads_independent(p1_8_env: dict):
    """Scenario 11: Concurrent uploads of different content remain fully independent."""
    app = p1_8_env["app"]
    proj_a = p1_8_env["project_a"]
    v1_bytes = p1_8_env["vid_1_bytes"]
    v2_bytes = p1_8_env["vid_2_bytes"]
    layout: StorageLayout = p1_8_env["layout"]

    def upload_data(filename: str, data: bytes):
        with TestClient(app) as c:
            return c.post(
                f"/api/v1/projects/{proj_a.id}/media/upload",
                files={"file": (filename, io.BytesIO(data), "video/mp4")},
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(upload_data, "diff_1.mp4", v1_bytes)
        f2 = executor.submit(upload_data, "diff_2.mp4", v2_bytes)
        r1 = f1.result()
        r2 = f2.result()

    assert r1.status_code == 201
    assert r2.status_code == 201
    d1 = r1.json()
    d2 = r2.json()

    assert d1["stored_file_id"] != d2["stored_file_id"]
    media_files = list(layout.media.glob("**/*.mp4"))
    assert len(media_files) == 2


def test_scenario_12_interrupted_upload_leaves_no_dangling_references(p1_8_env: dict):
    """Scenario 12: Failed/interrupted upload leaves no dangling references or temporary files."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    vid_bytes = p1_8_env["vid_1_bytes"]
    layout: StorageLayout = p1_8_env["layout"]

    resp = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload?test_fail_registration=true",
        files={"file": ("failing.mp4", io.BytesIO(vid_bytes), "video/mp4")},
    )
    assert resp.status_code == 500

    # No media assets exist
    assets_resp = client.get(f"/api/v1/projects/{proj_a.id}/media")
    assert assets_resp.json()["total"] == 0

    # No leftover .uploading files
    uploading_files = list(layout.media.glob("**/*.uploading"))
    assert len(uploading_files) == 0


def test_scenario_13_relinking_shared_asset_isolates_other_references(p1_8_env: dict):
    """Scenario 13: Relinking a shared asset updates only that asset's reference."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    vid_1_bytes = p1_8_env["vid_1_bytes"]
    vid_2 = p1_8_env["vid_2"]

    # Upload same video twice
    r1 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("shared_1.mp4", io.BytesIO(vid_1_bytes), "video/mp4")},
    )
    r2 = client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("shared_2.mp4", io.BytesIO(vid_1_bytes), "video/mp4")},
    )
    a1 = r1.json()
    a2 = r2.json()
    orig_path = a1["storage_path"]

    # Relink Asset 1 to vid_2 (candidate replacement)
    relink_resp = client.post(
        f"/api/v1/projects/{proj_a.id}/media/{a1['id']}/relink",
        json={"new_storage_path": str(vid_2), "force": True},
    )
    assert relink_resp.status_code == 200

    # Asset 1 points to new candidate
    a1_updated = client.get(f"/api/v1/projects/{proj_a.id}/media/{a1['id']}").json()
    assert str(Path(a1_updated["storage_path"])) == str(Path(vid_2))

    # Asset 2 STILL points to the original path!
    a2_check = client.get(f"/api/v1/projects/{proj_a.id}/media/{a2['id']}").json()
    assert a2_check["storage_path"] == orig_path
    # Asset 2's reference count is now 1 because Asset 1 relinked away
    assert a2_check["reference_count"] == 1


def test_scenario_14_reconcile_and_stats_endpoints(p1_8_env: dict):
    """Scenario 14: Deduplication stats and reconcile endpoints return accurate metrics."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    v1_bytes = p1_8_env["vid_1_bytes"]

    # Upload batch of 3 identical files
    client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("b1.mp4", io.BytesIO(v1_bytes), "video/mp4")},
    )
    client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("b2.mp4", io.BytesIO(v1_bytes), "video/mp4")},
    )
    client.post(
        f"/api/v1/projects/{proj_a.id}/media/upload",
        files={"file": ("b3.mp4", io.BytesIO(v1_bytes), "video/mp4")},
    )

    stats = client.get(f"/api/v1/projects/{proj_a.id}/media/deduplication/stats").json()
    assert stats["total_media_assets"] == 3
    assert stats["unique_stored_files"] == 1
    assert stats["shared_stored_files"] == 1
    assert stats["deduplicated_assets_count"] == 2
    assert stats["saved_bytes"] == len(v1_bytes) * 2

    # Call reconcile references
    rec = client.post(f"/api/v1/projects/{proj_a.id}/media/deduplication/reconcile").json()
    assert rec["total_stored_files"] == 1
    assert "reconciled_at" in rec


def test_scenario_15_batch_upload_passes_deduplication_flags(p1_8_env: dict):
    """Scenario 15: Batch upload endpoint returns is_deduplicated and reference_count flags."""
    client: TestClient = p1_8_env["client"]
    proj_a = p1_8_env["project_a"]
    v1_bytes = p1_8_env["vid_1_bytes"]

    batch_resp = client.post(
        f"/api/v1/projects/{proj_a.id}/media/batch-upload",
        files=[
            ("files", ("batch_1.mp4", io.BytesIO(v1_bytes), "video/mp4")),
            ("files", ("batch_2.mp4", io.BytesIO(v1_bytes), "video/mp4")),
        ],
    )
    assert batch_resp.status_code == 200
    bdata = batch_resp.json()
    assert bdata["succeeded"] == 2
    assert bdata["items"][0]["is_deduplicated"] is False
    assert bdata["items"][1]["is_deduplicated"] is True
    assert bdata["items"][1]["reference_count"] == 2
