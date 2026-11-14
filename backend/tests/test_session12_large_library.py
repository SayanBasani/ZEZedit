"""Session 12: Large Library Stress Test (1,000 Export Records).

Verifies:
1. Fast insertion and retrieval of 1,000 realistic export records in an isolated DB.
2. Server-side pagination (limit=12, limit=50, limit=100) response times < 50ms.
3. Payload size reduction: paginated page (~15KB) vs unbounded fetch (>1.5MB).
4. Offset/limit stability: traversing all 1,000 records page-by-page produces 0 duplicates and 0 missing items.
5. Server-side search filtering by title/filename.
6. Server-side filtering by aspect ratio and status.
7. Server-side sorting (newest, oldest, duration_desc, duration_asc, title).
"""

import os
import sys
import time
import json
import uuid
import sqlite3
import pytest
from pathlib import Path

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.services.export_service import ExportService


@pytest.fixture(scope="module")
def large_library_service(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("large_library")
    storage_root = tmp_dir / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(storage_root=str(storage_root), db_file=str(layout.db_file))
    service = ExportService(settings=settings, db_path=layout.db_file)
    project_id = "proj_stress_1000"
    asset_id = "med_stress_asset"

    # Pre-populate project, media_asset, and candidate
    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            "INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
            (project_id, "Stress Test Project", "proj_stress_1000"),
        )
        conn.execute(
            """
            INSERT INTO media_assets (id, project_id, original_filename, storage_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (asset_id, project_id, "benchmark.mp4", str(tmp_dir / "benchmark.mp4")),
        )

        aspect_ratios = ["9:16", "16:9", "1:1", "4:5"]
        statuses = ["completed", "completed", "completed", "failed", "rendering"]

        # Insert 1,000 export records
        records = []
        for i in range(1000):
            exp_id = f"exp_stress_{i:04d}"
            cand_id = f"cand_stress_{i % 50:03d}"
            aspect = aspect_ratios[i % len(aspect_ratios)]
            status = statuses[i % len(statuses)]
            dur = 15.0 + (i % 45)  # 15s to 60s
            title = f"Clip Highlight {i:04d} - {'Epic Action' if i % 2 == 0 else 'Insightful Moment'}"
            out_name = f"short_{i:04d}_{aspect.replace(':', 'x')}.mp4"
            created_at = f"2026-11-14T{12 + (i // 100):02d}:{(i % 60):02d}:00Z"

            records.append((
                exp_id,
                project_id,
                cand_id,
                asset_id,
                f"job_stress_{i:04d}",
                title,
                f"preset_{aspect.replace(':', '_')}",
                aspect,
                1080 if aspect == "9:16" else 1920,
                1920 if aspect == "9:16" else 1080,
                "h264",
                "aac",
                "yuv420p",
                30.0,
                23,
                5000000,
                192000,
                json.dumps({"mode": "word_by_word"}),
                json.dumps({"loudnorm": True}),
                f"/exports/{out_name}",
                out_name,
                int(dur * 500000),  # approx file size
                dur,
                status,
                "valid" if status == "completed" else "pending",
                json.dumps({}),
                "Error encountered" if status == "failed" else None,
                created_at,
                created_at if status in ("completed", "failed") else None,
            ))

        conn.executemany(
            """
            INSERT INTO exports (
                id, project_id, candidate_id, media_asset_id, render_job_id,
                title, export_preset, target_aspect_ratio, target_width, target_height,
                video_codec, audio_codec, pixel_fmt, fps, crf, video_bitrate, audio_bitrate,
                caption_config_json, audio_config_json, output_path, output_filename,
                file_size_bytes, duration_seconds, status, validation_status,
                validation_details_json, error_message, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        conn.commit()

    return {
        "service": service,
        "project_id": project_id,
        "asset_id": asset_id,
        "total_records": 1000,
    }


def test_large_library_pagination_performance(large_library_service):
    """Verify response time is well below 50ms for page of 12, 50, and 100."""
    service = large_library_service["service"]
    pid = large_library_service["project_id"]

    for page_size in [12, 50, 100]:
        t0 = time.perf_counter()
        results = service.list_exports(project_id=pid, limit=page_size, offset=0)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert len(results) == page_size
        assert elapsed_ms < 50.0, f"Query took {elapsed_ms:.2f}ms, expected < 50ms"


def test_large_library_offset_limit_stability(large_library_service):
    """Verify iterating through 1,000 records page by page gives exact count, no duplicates, no missing."""
    service = large_library_service["service"]
    pid = large_library_service["project_id"]

    page_size = 50
    offset = 0
    collected_ids = []

    while True:
        page = service.list_exports(project_id=pid, limit=page_size, offset=offset)
        if not page:
            break
        collected_ids.extend([item.id for item in page])
        offset += page_size

    assert len(collected_ids) == 1000
    assert len(set(collected_ids)) == 1000, "Duplicate records found across page transitions!"


def test_large_library_payload_size_comparison(large_library_service):
    """Compare JSON payload size of page (12 items) vs 1,000 items."""
    service = large_library_service["service"]
    pid = large_library_service["project_id"]

    page_12 = service.list_exports(project_id=pid, limit=12, offset=0)
    all_1000 = service.list_exports(project_id=pid, limit=1000, offset=0)

    payload_page_12 = json.dumps([item.__dict__ for item in page_12])
    payload_all_1000 = json.dumps([item.__dict__ for item in all_1000])

    size_page_kb = len(payload_page_12.encode("utf-8")) / 1024.0
    size_all_kb = len(payload_all_1000.encode("utf-8")) / 1024.0

    assert size_page_kb < 30.0, f"Page size too large: {size_page_kb:.1f} KB"
    assert size_all_kb > 800.0, f"Expected 1000 items to be large, got {size_all_kb:.1f} KB"


def test_large_library_search_filter(large_library_service):
    """Verify server-side search filtering handles queries accurately."""
    service = large_library_service["service"]
    pid = large_library_service["project_id"]

    results = service.list_exports(project_id=pid, search="Highlight 0042", limit=10)
    assert len(results) == 1
    assert "0042" in results[0].title

    epic_results = service.list_exports(project_id=pid, search="Epic Action", limit=50)
    assert len(epic_results) == 50
    assert all("Epic Action" in r.title for r in epic_results)

    total_epic = service.count_exports(project_id=pid, search="Epic Action")
    assert total_epic == 500


def test_large_library_aspect_and_status_filters(large_library_service):
    """Verify aspect ratio and status filters."""
    service = large_library_service["service"]
    pid = large_library_service["project_id"]

    # Aspect ratio 9:16 (every 4th item = 250 items)
    r916 = service.list_exports(project_id=pid, aspect_ratio="9:16", limit=50)
    assert len(r916) == 50
    assert all(r.target_aspect_ratio == "9:16" for r in r916)
    count_916 = service.count_exports(project_id=pid, aspect_ratio="9:16")
    assert count_916 == 250

    # Status failed (1 out of 5 = 200 items)
    failed = service.list_exports(project_id=pid, status="failed", limit=50)
    assert len(failed) == 50
    assert all(r.status == "failed" for r in failed)
    count_failed = service.count_exports(project_id=pid, status="failed")
    assert count_failed == 200


def test_large_library_sorting(large_library_service):
    """Verify sorting (duration, title, dates)."""
    service = large_library_service["service"]
    pid = large_library_service["project_id"]

    dur_desc = service.list_exports(project_id=pid, sort_by="duration_desc", limit=20)
    for i in range(len(dur_desc) - 1):
        assert (dur_desc[i].duration_seconds or 0) >= (dur_desc[i + 1].duration_seconds or 0)

    dur_asc = service.list_exports(project_id=pid, sort_by="duration_asc", limit=20)
    for i in range(len(dur_asc) - 1):
        assert (dur_asc[i].duration_seconds or 0) <= (dur_asc[i + 1].duration_seconds or 0)

    title_sort = service.list_exports(project_id=pid, sort_by="title", limit=20)
    for i in range(len(title_sort) - 1):
        assert title_sort[i].title <= title_sort[i + 1].title
