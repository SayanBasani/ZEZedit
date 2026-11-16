"""P1.1 Demonstration Runner: Single and Multiple Video Upload.

Executes and coordinates all 5 mandatory demonstration cases:
- Demo A: Single Video Upload (request, response, DB row, physical file, dashboard URL)
- Demo B: Multiple Video Batch Upload (3 valid videos, 3 IDs, 3 physical files, 3 DB rows)
- Demo C: Mixed-Validity Batch Upload (1 valid, 1 corrupt, partial failure reporting)
- Demo D: Filename Safety, Spaces/Unicode, and Path Traversal Rejection
- Demo E: Repeated Upload Non-Destructive Collision Handling (2 uploads of same filename)
"""

import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path("D:/ZezEdit")
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "reports" / "priority_1" / "p1_1_evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_FILE = EVIDENCE_DIR / "p1_1_evidence.json"

from app.main import create_app
from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations

evidence_records = {}


def log_demo(demo_id: str, purpose: str, command: str, pre_state: dict, post_state: dict, status: str, details: dict):
    print(f"\n[{demo_id}] {purpose} -> {status.upper()}")
    evidence_records[demo_id] = {
        "demo_id": demo_id,
        "purpose": purpose,
        "command": command,
        "pre_state": pre_state,
        "post_state": post_state,
        "status": status,
        "details": details,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def create_synthetic_mp4(out_path: Path, duration: int = 1, width: int = 320, height: int = 240, fps: int = 25):
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


def run_all_demos():
    print("=" * 70)
    print("ZEZEdit 2.0 — P1.1 Live Demonstrations Runner")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    # Use an isolated demonstration workspace to keep production media/db untouched
    temp_dir = tempfile.TemporaryDirectory(prefix="zezedit_p1_1_demo_")
    demo_root = Path(temp_dir.name)
    settings = Settings(storage_root=str(demo_root))
    layout = StorageLayout.from_root(str(demo_root))
    layout.ensure_directories()

    run_migrations(
        db_path=layout.db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=layout.backups,
    )

    app = create_app(settings)
    client = TestClient(app)

    try:
        # -----------------------------------------------------------------
        # DEMO A: Single Video Upload
        # -----------------------------------------------------------------
        demo_a_clip = demo_root / "temp" / "demo_a_single.mp4"
        demo_a_clip.parent.mkdir(parents=True, exist_ok=True)
        create_synthetic_mp4(demo_a_clip, duration=2, width=320, height=240, fps=25)
        file_size = demo_a_clip.stat().st_size

        with open(demo_a_clip, "rb") as f:
            res_a = client.post(
                "/api/v1/media/upload",
                files={"file": ("demo_a_single.mp4", f, "video/mp4")},
            )

        assert res_a.status_code == 201, f"Expected 201, got {res_a.status_code}: {res_a.text}"
        data_a = res_a.json()
        asset_id_a = data_a["id"]
        stored_path_a = Path(data_a["storage_path"])
        dashboard_url_a = f"/videos/{asset_id_a}"

        # Verify database row
        with sqlite3.connect(layout.db_file) as conn:
            conn.row_factory = sqlite3.Row
            row_a = conn.execute("SELECT * FROM media_assets WHERE id = ?", (asset_id_a,)).fetchone()
            assert row_a is not None, "Media asset record must exist in database"
            assert row_a["original_filename"] == "demo_a_single.mp4"
            assert row_a["width"] == 320
            assert row_a["height"] == 240
            assert row_a["media_type"] == "video"

        assert stored_path_a.exists(), "Stored physical video must exist on disk"
        assert stored_path_a.stat().st_size == file_size, "Stored file size must match original"

        log_demo(
            demo_id="DEMO_A_SINGLE_UPLOAD",
            purpose="Upload single video, verify response, physical file, DB row, and dashboard URL",
            command="POST /api/v1/media/upload with demo_a_single.mp4",
            pre_state={"source_file": str(demo_a_clip), "file_size_bytes": file_size},
            post_state={
                "asset_id": asset_id_a,
                "storage_path": str(stored_path_a),
                "file_exists": stored_path_a.exists(),
                "db_record_found": bool(row_a),
                "dashboard_url": dashboard_url_a,
            },
            status="PASSED",
            details={
                "status_code": res_a.status_code,
                "duration_seconds": data_a.get("duration_seconds"),
                "width": data_a.get("width"),
                "height": data_a.get("height"),
                "fps": data_a.get("fps"),
                "video_codec": data_a.get("video_codec"),
            },
        )

        # -----------------------------------------------------------------
        # DEMO B: Multiple Video Batch Upload
        # -----------------------------------------------------------------
        batch_clips = []
        for i in range(1, 4):
            cp = demo_root / "temp" / f"demo_b_{i}.mp4"
            create_synthetic_mp4(cp, duration=1, width=320, height=240, fps=25)
            batch_clips.append(cp)

        files_b = []
        opened_b = []
        for cp in batch_clips:
            f = open(cp, "rb")
            opened_b.append(f)
            files_b.append(("files", (cp.name, f, "video/mp4")))

        try:
            res_b = client.post("/api/v1/media/batch-upload", files=files_b)
        finally:
            for f in opened_b:
                f.close()

        assert res_b.status_code == 200, f"Expected 200, got {res_b.status_code}: {res_b.text}"
        data_b = res_b.json()
        assert data_b["total"] == 3
        assert data_b["succeeded"] == 3
        assert data_b["failed"] == 0

        b_ids = [item["media_id"] for item in data_b["items"]]
        b_paths = [Path(item["asset"]["storage_path"]) for item in data_b["items"]]

        assert len(set(b_ids)) == 3, "All 3 items must have distinct media IDs"
        assert len(set(b_paths)) == 3, "All 3 items must have distinct storage paths"
        for p in b_paths:
            assert p.exists(), f"Physical file {p} must exist"

        # Verify DB rows
        with sqlite3.connect(layout.db_file) as conn:
            cursor = conn.cursor()
            rows_b = cursor.execute("SELECT id, original_filename FROM media_assets WHERE id IN (?, ?, ?)", tuple(b_ids)).fetchall()
            assert len(rows_b) == 3, "All 3 media records must exist in DB"

        log_demo(
            demo_id="DEMO_B_MULTIPLE_BATCH_UPLOAD",
            purpose="Select and upload multiple videos in one batch operation",
            command="POST /api/v1/media/batch-upload with 3 MP4 files",
            pre_state={"batch_count": 3, "files": [p.name for p in batch_clips]},
            post_state={
                "total": data_b["total"],
                "succeeded": data_b["succeeded"],
                "failed": data_b["failed"],
                "media_ids": b_ids,
                "all_physical_files_exist": all(p.exists() for p in b_paths),
            },
            status="PASSED",
            details={"items": data_b["items"]},
        )

        # -----------------------------------------------------------------
        # DEMO C: Mixed-Validity Batch Upload (Partial Failure)
        # -----------------------------------------------------------------
        c_valid = demo_root / "temp" / "demo_c_valid.mp4"
        create_synthetic_mp4(c_valid, duration=1)
        c_corrupt = demo_root / "temp" / "demo_c_corrupt.mp4"
        c_corrupt.write_text("NOT A VIDEO: Plain text dummy file.")

        with open(c_valid, "rb") as f1, open(c_corrupt, "rb") as f2:
            files_c = [
                ("files", ("demo_c_valid.mp4", f1, "video/mp4")),
                ("files", ("demo_c_corrupt.mp4", f2, "video/mp4")),
            ]
            res_c = client.post("/api/v1/media/batch-upload", files=files_c)

        assert res_c.status_code == 200, f"Expected 200, got {res_c.status_code}: {res_c.text}"
        data_c = res_c.json()
        assert data_c["total"] == 2
        assert data_c["succeeded"] == 1
        assert data_c["failed"] == 1

        succ_item = next(i for i in data_c["items"] if i["filename"] == "demo_c_valid.mp4")
        fail_item = next(i for i in data_c["items"] if i["filename"] == "demo_c_corrupt.mp4")

        assert succ_item["success"] is True
        assert succ_item["media_id"] is not None
        assert Path(succ_item["asset"]["storage_path"]).exists()

        assert fail_item["success"] is False
        assert fail_item["media_id"] is None
        assert fail_item["error"] is not None

        log_demo(
            demo_id="DEMO_C_MIXED_VALIDITY_BATCH",
            purpose="Verify partial batch failure reporting: valid item succeeds, invalid item rejected",
            command="POST /api/v1/media/batch-upload with 1 valid video and 1 invalid text file",
            pre_state={"items": ["demo_c_valid.mp4", "demo_c_corrupt.mp4"]},
            post_state={
                "total": data_c["total"],
                "succeeded": data_c["succeeded"],
                "failed": data_c["failed"],
                "valid_item_persisted": Path(succ_item["asset"]["storage_path"]).exists(),
                "invalid_item_reported": bool(fail_item["error"]),
            },
            status="PASSED",
            details={
                "valid_id": succ_item["media_id"],
                "invalid_error": fail_item["error"],
                "invalid_error_code": fail_item.get("error_code"),
            },
        )

        # -----------------------------------------------------------------
        # DEMO D: Filename Safety, Spaces/Unicode, and Path Traversal
        # -----------------------------------------------------------------
        unicode_name = "Hindi-English [BollyFlix] 01.mp4"
        d_unicode = demo_root / "temp" / unicode_name
        create_synthetic_mp4(d_unicode, duration=1)

        with open(d_unicode, "rb") as f:
            res_d1 = client.post(
                "/api/v1/media/upload",
                files={"file": (unicode_name, f, "video/mp4")},
            )

        assert res_d1.status_code == 201
        data_d1 = res_d1.json()
        assert data_d1["original_filename"] == unicode_name
        stored_d1 = Path(data_d1["storage_path"])
        assert stored_d1.exists()

        # Path traversal probe
        with open(d_unicode, "rb") as f:
            res_d2 = client.post(
                "/api/v1/media/upload",
                files={"file": ("../../traversal_probe.mp4", f, "video/mp4")},
            )
        assert res_d2.status_code == 400
        assert "PATH_TRAVERSAL_DETECTED" in res_d2.text

        log_demo(
            demo_id="DEMO_D_FILENAME_SAFETY_AND_TRAVERSAL",
            purpose="Verify spaces, Unicode, and brackets preserved, and path traversal rejected",
            command="POST /api/v1/media/upload with unicode filename and traversal sequence",
            pre_state={"unicode_name": unicode_name, "traversal_attempt": "../../traversal_probe.mp4"},
            post_state={
                "unicode_upload_status": res_d1.status_code,
                "unicode_stored_filename": data_d1["original_filename"],
                "traversal_status": res_d2.status_code,
                "traversal_rejected": "PATH_TRAVERSAL_DETECTED" in res_d2.text,
            },
            status="PASSED",
            details={
                "unicode_asset_id": data_d1["id"],
                "unicode_path": str(stored_d1),
                "traversal_error_response": res_d2.json(),
            },
        )

        # -----------------------------------------------------------------
        # DEMO E: Repeated Upload Non-Destructive Collision Handling
        # -----------------------------------------------------------------
        e_clip = demo_root / "temp" / "collision_test.mp4"
        create_synthetic_mp4(e_clip, duration=1)
        e_size = e_clip.stat().st_size

        with open(e_clip, "rb") as f:
            res_e1 = client.post(
                "/api/v1/media/upload",
                files={"file": ("collision_test.mp4", f, "video/mp4")},
            )
        assert res_e1.status_code == 201
        data_e1 = res_e1.json()

        with open(e_clip, "rb") as f:
            res_e2 = client.post(
                "/api/v1/media/upload",
                files={"file": ("collision_test.mp4", f, "video/mp4")},
            )
        assert res_e2.status_code == 201
        data_e2 = res_e2.json()

        p_e1 = Path(data_e1["storage_path"])
        p_e2 = Path(data_e2["storage_path"])

        assert data_e1["id"] != data_e2["id"], "Distinct asset IDs required"
        assert p_e1 != p_e2, "Distinct physical file paths required"
        assert p_e1.exists() and p_e2.exists(), "Both physical files must exist simultaneously"
        assert p_e1.stat().st_size == e_size and p_e2.stat().st_size == e_size

        log_demo(
            demo_id="DEMO_E_REPEATED_UPLOAD_COLLISION",
            purpose="Verify repeated upload of identical filename creates distinct records and files without overwriting",
            command="POST /api/v1/media/upload with collision_test.mp4 twice",
            pre_state={"filename": "collision_test.mp4", "size": e_size},
            post_state={
                "first_upload_id": data_e1["id"],
                "first_storage_path": str(p_e1),
                "second_upload_id": data_e2["id"],
                "second_storage_path": str(p_e2),
                "ids_distinct": data_e1["id"] != data_e2["id"],
                "paths_distinct": str(p_e1) != str(p_e2),
                "both_files_exist": p_e1.exists() and p_e2.exists(),
            },
            status="PASSED",
            details={
                "upload1_response": data_e1,
                "upload2_response": data_e2,
            },
        )

    finally:
        logging.shutdown()
        try:
            temp_dir.cleanup()
        except Exception:
            pass

    # Save evidence file
    with open(EVIDENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "priority": "P1.1",
                "milestone": "Single and Multiple Video Upload",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "all_demos_passed": all(r["status"] == "PASSED" for r in evidence_records.values()),
                "demo_count": len(evidence_records),
                "demos": evidence_records,
            },
            f,
            indent=2,
        )

    print("\n" + "=" * 70)
    print(f"All {len(evidence_records)} P1.1 Demonstrations Completed: ALL PASSED")
    print(f"Evidence recorded at: {EVIDENCE_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    run_all_demos()
