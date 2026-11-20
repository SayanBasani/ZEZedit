"""
ZEZEdit 2.0 — P1.7 Media Relinking, Missing File Recovery & External Media Handling Demonstrations.
Executes and records all 5 independent demonstrations (Scenarios A through E)
matching the P1.7 specification against FastAPI and SQLite.
Outputs structured evidence to docs/reports/priority_1/p1_7_evidence/p1_7_evidence.json.
"""

import asyncio
import hashlib
import io
import json
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

PROJECT_ROOT = Path(r"D:\ZezEdit")
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "reports" / "priority_1" / "p1_7_evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_FILE = EVIDENCE_DIR / "p1_7_evidence.json"

sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.media import MediaService
from app.services.projects import ProjectService


def create_synthetic_mp4(out_path: Path, duration: float = 2.0, width: int = 640, height: int = 360, fps: int = 25):
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
        "-f", "lavfi",
        "-i", f"sine=frequency=1000:duration={duration}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        str(out_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out_path


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_all_demos():
    print("=" * 80)
    print("ZEZEDIT 2.0 — P1.7 MEDIA RELINKING & RECOVERY DEMONSTRATION RUNNER")
    print("=" * 80)

    evidence = {
        "task": "P1.7 Media Relinking, Missing File Recovery and External Media Handling",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenarios": {},
        "summary": {
            "total_scenarios": 5,
            "passed_scenarios": 0,
            "failed_scenarios": 0,
        }
    }

    temp_dir = tempfile.mkdtemp(prefix="zezedit_p1_7_demos_")
    demo_root = Path(temp_dir)
    storage_root = demo_root / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    settings = Settings(
        storage_root=storage_root,
        environment="testing",
        log_level="DEBUG",
        max_upload_size_bytes=100 * 1024 * 1024,
        max_concurrent_uploads=2,
    )

    run_migrations(
        db_path=layout.db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=layout.backups,
    )

    app = create_app(settings_override=settings)
    client = TestClient(app)
    proj_svc = ProjectService(settings=settings, db_path=layout.db_file)
    media_svc = MediaService(settings=settings, db_path=layout.db_file)
    project = proj_svc.create_project(name="P1.7 Demonstration Workspace")
    project_id = project.id

    try:
        # =========================================================================
        # SCENARIO A: File Moved & Relinked to New Local Path
        # =========================================================================
        print("\n--- Running SCENARIO A: File Moved & Relinked to New Local Path ---")
        orig_video_path = demo_root / "scenario_a_original.mp4"
        create_synthetic_mp4(orig_video_path, duration=2.0, width=640, height=360)
        orig_sha256 = compute_sha256(orig_video_path)
        orig_size = orig_video_path.stat().st_size

        # Register initial media asset
        reg_media = media_svc.register_media_asset(
            project_id=project_id,
            storage_path=str(orig_video_path),
            original_filename="vacation_vlog.mp4",
            duration_seconds=2.0,
            width=640,
            height=360,
            sha256=orig_sha256,
            mime_type="video/mp4",
            file_size_bytes=orig_size,
            is_external=True,
        )
        media_id_a = reg_media.id

        # Confirm initial state
        res_initial = client.get(f"/api/v1/media/{media_id_a}")
        assert res_initial.status_code == 200
        media_data_initial = res_initial.json()
        assert media_data_initial["availability_status"] == "present"
        assert media_data_initial["is_playable"] is True

        # Move the physical file to simulate user moving it on disk
        moved_video_path = demo_root / "relocated_media" / "vacation_vlog_renamed.mp4"
        moved_video_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(orig_video_path), str(moved_video_path))

        # Dynamic missing detection
        res_missing = client.get(f"/api/v1/media/{media_id_a}")
        assert res_missing.status_code == 200
        media_data_missing = res_missing.json()
        assert media_data_missing["availability_status"] == "missing"
        assert media_data_missing["is_playable"] is False
        assert media_data_missing["duration_seconds"] == 2.0  # Metadata preserved

        # Inspect candidate
        res_inspect = client.post(
            f"/api/v1/media/{media_id_a}/relink/inspect",
            json={"candidate_path": str(moved_video_path)},
        )
        assert res_inspect.status_code == 200, res_inspect.text
        inspect_data = res_inspect.json()
        assert inspect_data["match_status"] == "exact"
        assert inspect_data["comparison"]["sha256_match"] is True
        assert inspect_data["comparison"]["duration_diff_seconds"] == 0.0
        assert len(inspect_data["warnings"]) == 0

        # Execute relink
        res_relink = client.post(
            f"/api/v1/media/{media_id_a}/relink",
            json={"new_storage_path": str(moved_video_path), "force": False},
        )
        assert res_relink.status_code == 200, res_relink.text
        relink_data = res_relink.json()
        assert relink_data["asset"]["availability_status"] == "present"
        assert relink_data["match_status"] == "exact"
        assert relink_data["asset"]["previous_storage_path"] == str(orig_video_path)
        assert relink_data["asset"]["previous_sha256"] == orig_sha256
        assert relink_data["relinked_at"] is not None

        # Verify streaming HTTP 206
        stream_res = client.get(
            f"/api/v1/media/{media_id_a}/stream",
            headers={"Range": "bytes=0-1023"},
        )
        assert stream_res.status_code == 206
        assert len(stream_res.content) == 1024

        # Verify project_events table
        with sqlite_session(layout.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT event_type, payload_json FROM project_events WHERE project_id = ? AND event_type = 'media_relinked'",
                (project_id,)
            )
            event_row = cursor.fetchone()
            assert event_row is not None
            event_payload = json.loads(event_row[1])
            assert event_payload.get("asset_id") == media_id_a or event_payload.get("media_id") == media_id_a

        print("  ✓ SCENARIO A PASSED")
        evidence["scenarios"]["scenario_a_file_moved"] = {
            "status": "PASSED",
            "media_id": media_id_a,
            "original_path": str(orig_video_path),
            "moved_path": str(moved_video_path),
            "original_sha256": orig_sha256,
            "stream_status_code": stream_res.status_code,
            "previous_storage_path": relink_data["asset"]["previous_storage_path"],
            "previous_sha256": relink_data["asset"]["previous_sha256"],
            "relink_match_status": relink_data["match_status"],
            "relinked_at": relink_data["relinked_at"],
        }
        evidence["summary"]["passed_scenarios"] += 1

        # =========================================================================
        # SCENARIO B: External Drive Disconnected & Reconnected (Reconciliation)
        # =========================================================================
        print("\n--- Running SCENARIO B: External Drive Disconnected & Reconnected ---")
        ext_drive_dir = demo_root / "simulated_external_drive_E"
        ext_drive_dir.mkdir(parents=True, exist_ok=True)
        ext_video_path = ext_drive_dir / "field_interview.mp4"
        create_synthetic_mp4(ext_video_path, duration=3.0, width=640, height=360)
        ext_sha256 = compute_sha256(ext_video_path)

        reg_ext = media_svc.register_media_asset(
            project_id=project_id,
            storage_path=str(ext_video_path),
            original_filename="field_interview.mp4",
            duration_seconds=3.0,
            width=640,
            height=360,
            sha256=ext_sha256,
            mime_type="video/mp4",
            file_size_bytes=ext_video_path.stat().st_size,
            is_external=True,
        )
        media_id_b = reg_ext.id

        # Simulate unmounting / disconnecting the external drive
        disconnected_dir = demo_root / "simulated_external_drive_E_OFFLINE"
        shutil.move(str(ext_drive_dir), str(disconnected_dir))

        # Reconcile availability
        reconcile_off = client.post(f"/api/v1/media/reconcile-availability?project_id={project_id}")
        assert reconcile_off.status_code == 200
        rec_off_data = reconcile_off.json()
        assert rec_off_data["still_missing_count"] >= 1
        assert media_id_b in rec_off_data["still_missing_assets"]

        # Confirm media record is missing
        res_ext_missing = client.get(f"/api/v1/media/{media_id_b}")
        assert res_ext_missing.json()["availability_status"] == "missing"
        assert res_ext_missing.json()["integrity_status"] == "missing"

        # Simulate reconnecting external drive
        shutil.move(str(disconnected_dir), str(ext_drive_dir))

        # Reconcile availability again
        reconcile_on = client.post(f"/api/v1/media/reconcile-availability?project_id={project_id}")
        assert reconcile_on.status_code == 200
        rec_on_data = reconcile_on.json()
        assert rec_on_data["restored_count"] >= 1
        assert media_id_b in rec_on_data["restored_assets"]

        # Confirm media record restored to present and verified
        res_ext_restored = client.get(f"/api/v1/media/{media_id_b}")
        assert res_ext_restored.json()["availability_status"] == "present"
        assert res_ext_restored.json()["integrity_status"] == "verified"
        assert res_ext_restored.json()["is_playable"] is True

        print("  ✓ SCENARIO B PASSED")
        evidence["scenarios"]["scenario_b_external_drive_reconciliation"] = {
            "status": "PASSED",
            "media_id": media_id_b,
            "external_mount_path": str(ext_video_path),
            "reconcile_offline_result": rec_off_data,
            "reconcile_online_result": rec_on_data,
            "restored_availability": res_ext_restored.json()["availability_status"],
            "restored_integrity": res_ext_restored.json()["integrity_status"],
        }
        evidence["summary"]["passed_scenarios"] += 1

        # =========================================================================
        # SCENARIO C: Discrepancy Warnings & Forced Relink
        # =========================================================================
        print("\n--- Running SCENARIO C: Discrepancy Warnings & Forced Relink ---")
        orig_video_c = demo_root / "scenario_c_original.mp4"
        create_synthetic_mp4(orig_video_c, duration=2.0, width=640, height=360)
        c_sha256 = compute_sha256(orig_video_c)

        reg_c = media_svc.register_media_asset(
            project_id=project_id,
            storage_path=str(orig_video_c),
            original_filename="original_cut_c.mp4",
            duration_seconds=2.0,
            width=640,
            height=360,
            sha256=c_sha256,
            mime_type="video/mp4",
            file_size_bytes=orig_video_c.stat().st_size,
            is_external=True,
        )
        media_id_c = reg_c.id

        # Create altered replacement video (5.0s, 1280x720)
        altered_video_c = demo_root / "scenario_c_altered_5s_720p.mp4"
        create_synthetic_mp4(altered_video_c, duration=5.0, width=1280, height=720)
        altered_sha256 = compute_sha256(altered_video_c)

        # Inspect candidate
        res_inspect_c = client.post(
            f"/api/v1/media/{media_id_c}/relink/inspect",
            json={"candidate_path": str(altered_video_c)},
        )
        assert res_inspect_c.status_code == 200
        inspect_c_data = res_inspect_c.json()
        assert inspect_c_data["match_status"] == "mismatch"
        assert inspect_c_data["comparison"]["sha256_match"] is False
        assert abs(inspect_c_data["comparison"]["duration_diff_seconds"] - 3.0) < 0.2
        assert len(inspect_c_data["warnings"]) >= 1

        # Relink without force -> must be rejected
        res_relink_no_force = client.post(
            f"/api/v1/media/{media_id_c}/relink",
            json={"new_storage_path": str(altered_video_c), "force": False},
        )
        assert res_relink_no_force.status_code == 400
        err_body = res_relink_no_force.json()
        err_msg = err_body.get("detail") or err_body.get("error", {}).get("message")
        assert "DISCREPANCY_REQUIRES_CONFIRMATION" in err_msg or "mismatch" in err_msg.lower()

        # Relink with force=True -> must succeed
        res_relink_force = client.post(
            f"/api/v1/media/{media_id_c}/relink",
            json={"new_storage_path": str(altered_video_c), "force": True},
        )
        assert res_relink_force.status_code == 200
        forced_data = res_relink_force.json()
        assert forced_data["match_status"] == "mismatch"
        assert forced_data["asset"]["previous_storage_path"] == str(orig_video_c)
        assert forced_data["asset"]["previous_sha256"] == c_sha256
        assert forced_data["asset"]["duration_seconds"] == 5.0
        assert forced_data["asset"]["width"] == 1280
        assert forced_data["asset"]["height"] == 720

        print("  ✓ SCENARIO C PASSED")
        evidence["scenarios"]["scenario_c_forced_relink_discrepancy"] = {
            "status": "PASSED",
            "media_id": media_id_c,
            "original_duration": 2.0,
            "altered_duration": 5.0,
            "duration_difference": inspect_c_data["comparison"]["duration_diff_seconds"],
            "discrepancy_warnings": inspect_c_data["warnings"],
            "rejected_without_force_status": res_relink_no_force.status_code,
            "succeeded_with_force_status": res_relink_force.status_code,
            "relink_match_status": forced_data["match_status"],
            "updated_duration": forced_data["asset"]["duration_seconds"],
            "updated_resolution": f"{forced_data['asset']['width']}x{forced_data['asset']['height']}",
        }
        evidence["summary"]["passed_scenarios"] += 1

        # =========================================================================
        # SCENARIO D: Failed / Aborted Relink (Corrupt / Non-video / Traversal)
        # =========================================================================
        print("\n--- Running SCENARIO D: Failed / Aborted Relink ---")
        orig_video_d = demo_root / "scenario_d_original.mp4"
        create_synthetic_mp4(orig_video_d, duration=1.0, width=640, height=360)
        d_sha256 = compute_sha256(orig_video_d)

        reg_d = media_svc.register_media_asset(
            project_id=project_id,
            storage_path=str(orig_video_d),
            original_filename="source_d.mp4",
            duration_seconds=1.0,
            width=640,
            height=360,
            sha256=d_sha256,
            mime_type="video/mp4",
            file_size_bytes=orig_video_d.stat().st_size,
            is_external=True,
        )
        media_id_d = reg_d.id

        # Attempt 1: Non-video text file
        text_file = demo_root / "not_a_video.txt"
        text_file.write_text("This is plain text and not a video.", encoding="utf-8")
        res_fail_text = client.post(
            f"/api/v1/media/{media_id_d}/relink",
            json={"new_storage_path": str(text_file), "force": True},
        )
        assert res_fail_text.status_code in (400, 422)

        # Attempt 2: Non-existent path
        res_fail_missing = client.post(
            f"/api/v1/media/{media_id_d}/relink",
            json={"new_storage_path": str(demo_root / "non_existent_file.mp4"), "force": True},
        )
        assert res_fail_missing.status_code in (400, 404)

        # Attempt 2b: Non-existent media asset ID (404)
        res_fail_asset_404 = client.post(
            "/api/v1/media/med_nonexistent99/relink",
            json={"new_storage_path": str(orig_video_d), "force": True},
        )
        assert res_fail_asset_404.status_code == 404

        # Attempt 3: Path traversal / system path
        res_fail_traversal = client.post(
            f"/api/v1/media/{media_id_d}/relink",
            json={"new_storage_path": r"C:\Windows\System32\cmd.exe", "force": True},
        )
        assert res_fail_traversal.status_code in (400, 403, 422)

        # Verify database record remains completely unpolluted
        with sqlite_session(layout.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT storage_path, relinked_at, previous_storage_path, previous_sha256 FROM media_assets WHERE id = ?",
                (media_id_d,)
            )
            row_d = cursor.fetchone()
            assert row_d[0] == str(orig_video_d)
            assert row_d[1] is None  # relinked_at
            assert row_d[2] is None  # previous_storage_path
            assert row_d[3] is None  # previous_sha256

        print("  ✓ SCENARIO D PASSED")
        evidence["scenarios"]["scenario_d_aborted_relink_safety"] = {
            "status": "PASSED",
            "media_id": media_id_d,
            "text_file_rejection_code": res_fail_text.status_code,
            "missing_file_rejection_code": res_fail_missing.status_code,
            "system_path_rejection_code": res_fail_traversal.status_code,
            "database_unpolluted": True,
            "storage_path_unchanged": row_d[0] == str(orig_video_d),
            "relinked_at_is_null": row_d[1] is None,
        }
        evidence["summary"]["passed_scenarios"] += 1

        # =========================================================================
        # SCENARIO E: Replacement via Browser Upload Streaming Relink
        # =========================================================================
        print("\n--- Running SCENARIO E: Replacement via Browser Upload Streaming Relink ---")
        orig_video_e = demo_root / "scenario_e_original.mp4"
        create_synthetic_mp4(orig_video_e, duration=2.0, width=640, height=360)
        e_sha256 = compute_sha256(orig_video_e)

        reg_e = media_svc.register_media_asset(
            project_id=project_id,
            storage_path=str(orig_video_e),
            original_filename="source_e.mp4",
            duration_seconds=2.0,
            width=640,
            height=360,
            sha256=e_sha256,
            mime_type="video/mp4",
            file_size_bytes=orig_video_e.stat().st_size,
            is_external=True,
        )
        media_id_e = reg_e.id

        # Create replacement file for upload
        upload_video_e = demo_root / "replacement_e_upload.mp4"
        create_synthetic_mp4(upload_video_e, duration=2.0, width=640, height=360)
        upload_e_sha256 = compute_sha256(upload_video_e)
        upload_e_bytes = upload_video_e.read_bytes()

        # Delete original file to simulate missing
        orig_video_e.unlink()

        # Upload relink
        files = {
            "file": ("replacement_e_upload.mp4", io.BytesIO(upload_e_bytes), "video/mp4")
        }
        data = {"force": "true"}
        res_upload_relink = client.post(
            f"/api/v1/media/{media_id_e}/relink/upload",
            files=files,
            data=data,
        )
        assert res_upload_relink.status_code == 200, res_upload_relink.text
        upload_relink_data = res_upload_relink.json()
        assert upload_relink_data["asset"]["availability_status"] == "present"
        assert upload_relink_data["relinked_at"] is not None
        assert upload_relink_data["asset"]["previous_sha256"] == e_sha256
        assert Path(upload_relink_data["asset"]["storage_path"]).exists()

        # Verify streaming HTTP 206 on uploaded video
        stream_e = client.get(
            f"/api/v1/media/{media_id_e}/stream",
            headers={"Range": "bytes=0-511"},
        )
        assert stream_e.status_code == 206
        assert len(stream_e.content) == 512

        print("  ✓ SCENARIO E PASSED")
        evidence["scenarios"]["scenario_e_upload_relink"] = {
            "status": "PASSED",
            "media_id": media_id_e,
            "uploaded_sha256": upload_e_sha256,
            "previous_sha256": e_sha256,
            "new_storage_path": upload_relink_data["asset"]["storage_path"],
            "stream_206_length": len(stream_e.content),
            "relinked_at": upload_relink_data["relinked_at"],
        }
        evidence["summary"]["passed_scenarios"] += 1

    finally:
        # Cleanup demonstration files
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Save evidence file
    evidence["completed_at"] = datetime.now(timezone.utc).isoformat()
    with open(EVIDENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)

    print("\n" + "=" * 80)
    print(f"DEMONSTRATIONS COMPLETE: {evidence['summary']['passed_scenarios']}/{evidence['summary']['total_scenarios']} SCENARIOS PASSED")
    print(f"Evidence recorded at: {EVIDENCE_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    run_all_demos()
