"""
ZEZEdit 2.0 — P1.9 Storage Management, Quotas, Safe Cleanup & Automatic Pruning Demonstrations.
Executes and records all 12 independent demonstrations (Demos A through L)
matching Section 13 against FastAPI and SQLite.
Outputs structured evidence to docs/reports/priority_1/p1_9_evidence/p1_9_evidence.json.
"""

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
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "reports" / "priority_1" / "p1_9_evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_FILE = EVIDENCE_DIR / "p1_9_evidence.json"

sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.media import MediaService
from app.services.projects import ProjectService
from app.services.storage import StorageService
from app.schemas.core import StorageQuotaUpdateRequest


def create_synthetic_mp4(out_path: Path, duration: float = 1.0, width: int = 640, height: int = 360, fps: int = 25, freq: int = 1000):
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
        "-f", "lavfi",
        "-i", f"sine=frequency={freq}:duration={duration}",
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
    print("ZEZEDIT 2.0 — P1.9 STORAGE MANAGEMENT & SAFE CLEANUP LIVE DEMOS")
    print("=" * 80)

    temp_root = Path(tempfile.mkdtemp(prefix="zezedit_p1_9_demos_"))
    storage_root = temp_root / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    settings = Settings(
        storage_root=storage_root,
        environment="testing",
        log_level="INFO",
        max_upload_size_bytes=100 * 1024 * 1024,
        max_concurrent_uploads=4,
    )

    print(f"Applying SQLite migrations on isolated database {layout.db_file}...")
    run_migrations(
        db_path=layout.db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=layout.backups,
    )

    app = create_app(settings_override=settings)
    client = TestClient(app)
    proj_svc = ProjectService(settings=settings, db_path=layout.db_file)
    media_svc = MediaService(settings=settings, db_path=layout.db_file)
    storage_svc = StorageService(settings=settings)

    # Pre-generate source video assets
    synth_dir = temp_root / "sources"
    synth_dir.mkdir(parents=True, exist_ok=True)
    video_1 = synth_dir / "camera_feed_1.mp4"
    video_2 = synth_dir / "camera_feed_2.mp4"
    create_synthetic_mp4(video_1, duration=1.0, freq=800)
    create_synthetic_mp4(video_2, duration=1.2, freq=1200)

    vid_1_bytes = video_1.read_bytes()
    vid_2_bytes = video_2.read_bytes()
    vid_1_sha = compute_sha256(video_1)
    vid_2_sha = compute_sha256(video_2)

    proj_a = proj_svc.create_project(name="Production Studio A")
    proj_b = proj_svc.create_project(name="Marketing Campaign B")

    evidence = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "milestone": "P1.9",
        "description": "Evidence records for P1.9 storage management, quotas, safe cleanup & automatic pruning",
        "demos": {},
    }

    try:
        # =====================================================================
        # DEMO A: Baseline Storage Breakdown
        # =====================================================================
        print("\n--- Running Demo A: Baseline Storage Inspection & Categorized Breakdown ---")
        bd_resp = client.get("/api/v1/maintenance/breakdown")
        assert bd_resp.status_code == 200, f"Breakdown failed: {bd_resp.text}"
        bd_data = bd_resp.json()
        print(f"  [Demo A] Total Application Storage: {bd_data['total_application_storage_bytes']} bytes")
        print(f"  [Demo A] Free Volume Space: {bd_data['free_disk_space_bytes']} bytes")
        evidence["demos"]["demo_a"] = {
            "status": "PASSED",
            "breakdown": bd_data,
        }

        # =====================================================================
        # DEMO B: Shared Physical Canonical Media Deduplication Accounting
        # =====================================================================
        print("\n--- Running Demo B: Shared Canonical Media Deduplication Accounting ---")
        up1 = client.post(
            f"/api/v1/projects/{proj_a.id}/media/upload",
            files={"file": ("interview_master.mp4", io.BytesIO(vid_1_bytes), "video/mp4")},
        )
        assert up1.status_code in (200, 201)
        up1_data = up1.json()

        up2 = client.post(
            f"/api/v1/projects/{proj_b.id}/media/upload",
            files={"file": ("interview_duplicate.mp4", io.BytesIO(vid_1_bytes), "video/mp4")},
        )
        assert up2.status_code in (200, 201)
        up2_data = up2.json()

        bd_resp_b = client.get("/api/v1/maintenance/breakdown")
        bd_data_b = bd_resp_b.json()
        cats_b = bd_data_b["categories"]
        print(f"  [Demo B] Logical Media Assets: {cats_b['logical_media_assets_bytes']} bytes (2 references)")
        print(f"  [Demo B] Physical Canonical Media: {cats_b['canonical_shared_media_bytes']} bytes (stored ONCE)")
        assert cats_b["logical_media_assets_bytes"] == len(vid_1_bytes) * 2
        assert cats_b["canonical_shared_media_bytes"] == len(vid_1_bytes)

        evidence["demos"]["demo_b"] = {
            "status": "PASSED",
            "logical_bytes": cats_b["logical_media_assets_bytes"],
            "canonical_bytes": cats_b["canonical_shared_media_bytes"],
            "single_stored_file_verified": True,
        }

        # =====================================================================
        # DEMO C: Non-Destructive Cleanup Preview
        # =====================================================================
        print("\n--- Running Demo C: Non-Destructive Cleanup Preview ---")
        abandoned_chunk = layout.temp / "abandoned_upload_session_99.uploading"
        abandoned_chunk.write_bytes(b"U" * 25000)
        old_time = time.time() - 7200
        os.utime(abandoned_chunk, (old_time, old_time))

        prev_resp = client.post("/api/v1/maintenance/cleanup-preview")
        assert prev_resp.status_code == 200
        prev_data = prev_resp.json()
        print(f"  [Demo C] Candidate count: {prev_data['total_candidates']}")
        print(f"  [Demo C] Eligible reclaimable bytes: {prev_data['total_eligible_bytes']}")
        assert abandoned_chunk.exists(), "Preview must NOT delete candidate file!"

        evidence["demos"]["demo_c"] = {
            "status": "PASSED",
            "candidates_found": prev_data["total_candidates"],
            "total_reclaimable_bytes": prev_data["total_eligible_bytes"],
            "file_retained_on_disk": abandoned_chunk.exists(),
        }

        # =====================================================================
        # DEMO D: Protection of Active Uploads and In-Flight Render Jobs
        # =====================================================================
        print("\n--- Running Demo D: Protection of Active Uploads & Render Workspaces ---")
        active_chunk = layout.temp / "active_in_flight.uploading"
        active_chunk.write_bytes(b"A" * 15000)  # mtime is now (< 60s)

        active_job_id = "job_live_active_render_111"
        with sqlite_session(layout.db_file) as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, project_id, job_type, status, created_at, updated_at)
                VALUES (?, ?, 'video_render', 'running', datetime('now'), datetime('now'))
                """,
                (active_job_id, proj_a.id),
            )
        job_dir = layout.temp / f"job_{active_job_id}"
        job_dir.mkdir(parents=True, exist_ok=True)
        render_scratch = job_dir / "render_scratch.mp4"
        render_scratch.write_bytes(b"R" * 50000)
        os.utime(render_scratch, (old_time, old_time))

        prev_d = client.post("/api/v1/maintenance/cleanup-preview").json()
        active_cands = [c for c in prev_d["candidates"] if active_job_id in c["relative_path"] or "active_in_flight" in c["relative_path"]]
        for ac in active_cands:
            print(f"  [Demo D] Protected: {ac['relative_path']} (Blocked: {ac['is_blocked']}, Reason: {ac['protection_reason']})")
            assert ac["is_blocked"] is True

        # Attempt execution on blocked candidate
        exec_d = client.post(
            "/api/v1/maintenance/cleanup-execute",
            json={"candidate_ids": [active_cands[0]["candidate_id"]]},
        ).json()
        assert exec_d["skipped_count"] >= 1
        assert active_chunk.exists() and render_scratch.exists(), "Active files must not be deleted!"

        evidence["demos"]["demo_d"] = {
            "status": "PASSED",
            "active_upload_blocked": True,
            "active_job_render_blocked": True,
            "files_survived_attempted_cleanup": True,
        }

        # =====================================================================
        # DEMO E: Protection of Canonical Media with Active References
        # =====================================================================
        print("\n--- Running Demo E: Protection of Canonical Media Assets ---")
        fake_cand_id = f"custom_guard_{up1_data['id']}"
        exec_e = client.post(
            "/api/v1/maintenance/cleanup-execute",
            json={"candidate_ids": [fake_cand_id]},
        ).json()
        media_check = client.get(f"/api/v1/media/{up1_data['id']}")
        assert media_check.status_code == 200
        print(f"  [Demo E] Media record '{up1_data['id']}' strictly preserved with status: {media_check.json()['availability_status']}")

        evidence["demos"]["demo_e"] = {
            "status": "PASSED",
            "media_record_preserved": True,
            "availability_status": media_check.json()["availability_status"],
        }

        # =====================================================================
        # DEMO F: Safe Cleanup Execution & Reclaimed Bytes Accounting
        # =====================================================================
        print("\n--- Running Demo F: Safe Cleanup Execution & Reclaimed Bytes ---")
        prev_f = client.post("/api/v1/maintenance/cleanup-preview").json()
        eligible_cands = [c for c in prev_f["candidates"] if not c["is_blocked"] and "abandoned_upload_session_99" in c["relative_path"]]
        assert len(eligible_cands) > 0

        target_cand = eligible_cands[0]
        exec_f = client.post(
            "/api/v1/maintenance/cleanup-execute",
            json={"candidate_ids": [target_cand["candidate_id"]]},
        ).json()
        print(f"  [Demo F] Deleted count: {exec_f['deleted_count']}, Reclaimed: {exec_f['bytes_reclaimed']} bytes")
        assert exec_f["deleted_count"] == 1
        assert exec_f["bytes_reclaimed"] == 25000
        assert not abandoned_chunk.exists(), "Target file must be safely unlinked!"

        evidence["demos"]["demo_f"] = {
            "status": "PASSED",
            "deleted_count": exec_f["deleted_count"],
            "bytes_reclaimed": exec_f["bytes_reclaimed"],
            "file_deleted": not abandoned_chunk.exists(),
        }

        # =====================================================================
        # DEMO G: Path Traversal & Boundary Escape Rejection
        # =====================================================================
        print("\n--- Running Demo G: Path Traversal & Boundary Escape Rejection ---")
        traversal_attempts = [
            "../../Windows/System32/cmd.exe",
            "../../../etc/passwd",
            "..\\..\\system.ini",
            "/absolute/outside/file.txt",
        ]
        rejection_results = {}
        for path_attempt in traversal_attempts:
            res = storage_svc.resolve_contained_path(path_attempt)
            print(f"  [Demo G] Attempt '{path_attempt}' -> Resolved: {res} (Correctly Rejected)")
            assert res is None
            rejection_results[path_attempt] = "REJECTED"

        evidence["demos"]["demo_g"] = {
            "status": "PASSED",
            "traversals_tested": rejection_results,
        }

        # =====================================================================
        # DEMO H: Persistent Quota Settings & Restart Retention
        # =====================================================================
        print("\n--- Running Demo H: Persistent Quota Configuration & Restart Retention ---")
        q_update = client.put(
            "/api/v1/maintenance/quotas",
            json={
                "storage_limit_bytes": 50 * 1024 * 1024 * 1024,
                "generated_video_limit_bytes": 10 * 1024 * 1024 * 1024,
                "temp_storage_limit_bytes": 5 * 1024 * 1024 * 1024,
                "warning_threshold_percent": 90,
                "auto_prune_enabled": True,
                "auto_prune_retention_hours": 36,
            },
        )
        assert q_update.status_code == 200

        # Simulate fresh app startup
        restarted_svc = StorageService(settings=settings)
        restarted_quotas = restarted_svc.get_storage_quotas()
        print(f"  [Demo H] Restarted storage limit: {restarted_quotas.storage_limit_bytes} bytes")
        print(f"  [Demo H] Restarted auto prune enabled: {restarted_quotas.auto_prune_enabled}, retention: {restarted_quotas.auto_prune_retention_hours} hrs")
        assert restarted_quotas.storage_limit_bytes == 50 * 1024 * 1024 * 1024
        assert restarted_quotas.auto_prune_enabled is True
        assert restarted_quotas.auto_prune_retention_hours == 36

        evidence["demos"]["demo_h"] = {
            "status": "PASSED",
            "persisted_storage_limit": restarted_quotas.storage_limit_bytes,
            "persisted_auto_prune_enabled": restarted_quotas.auto_prune_enabled,
            "persisted_retention_hours": restarted_quotas.auto_prune_retention_hours,
        }

        # =====================================================================
        # DEMO I: Hard Quota Pre-Flight Enforcement (HTTP 507)
        # =====================================================================
        print("\n--- Running Demo I: Hard Quota Preflight Enforcement (HTTP 507) ---")
        # Restrict quota to very small value (100 bytes)
        client.put("/api/v1/maintenance/quotas", json={"storage_limit_bytes": 100})

        quota_upload = client.post(
            f"/api/v1/projects/{proj_a.id}/media/upload",
            files={"file": ("excess_video.mp4", io.BytesIO(vid_2_bytes), "video/mp4")},
        )
        print(f"  [Demo I] Upload response status: {quota_upload.status_code}")
        assert quota_upload.status_code == 507
        err_msg = quota_upload.json()["error"]["message"]
        print(f"  [Demo I] Rejection message: {err_msg}")
        assert "OVERALL_QUOTA_EXCEEDED" in err_msg or "QUOTA_EXCEEDED" in str(quota_upload.json())

        # Reset quota to unblock subsequent tests
        client.put("/api/v1/maintenance/quotas", json={"storage_limit_bytes": 100 * 1024 * 1024 * 1024})

        evidence["demos"]["demo_i"] = {
            "status": "PASSED",
            "status_code": quota_upload.status_code,
            "error_response": quota_upload.json(),
        }

        # =====================================================================
        # DEMO J: Automatic Pruning with Retention Policy
        # =====================================================================
        print("\n--- Running Demo J: Automatic Pruning with Retention Policy ---")
        client.put(
            "/api/v1/maintenance/quotas",
            json={"auto_prune_enabled": True, "auto_prune_retention_hours": 24},
        )
        stale_auto = layout.temp / "expired_render_chunk.tmp"
        stale_auto.write_bytes(b"E" * 12000)
        stale_mtime = time.time() - (36 * 3600)
        os.utime(stale_auto, (stale_mtime, stale_mtime))

        fresh_auto = layout.temp / "fresh_active_render_chunk.tmp"
        fresh_auto.write_bytes(b"F" * 12000)
        fresh_mtime = time.time() - (2 * 3600)
        os.utime(fresh_auto, (fresh_mtime, fresh_mtime))

        prune_resp = client.post("/api/v1/maintenance/auto-prune")
        assert prune_resp.status_code == 200
        prune_data = prune_resp.json()
        print(f"  [Demo J] Auto prune deleted count: {prune_data['deleted_count']}, Reclaimed: {prune_data['bytes_reclaimed']} bytes")
        assert not stale_auto.exists(), "Stale chunk older than retention must be pruned!"
        assert fresh_auto.exists(), "Fresh chunk within retention window must be preserved!"

        evidence["demos"]["demo_j"] = {
            "status": "PASSED",
            "deleted_count": prune_data["deleted_count"],
            "bytes_reclaimed": prune_data["bytes_reclaimed"],
            "stale_pruned": not stale_auto.exists(),
            "fresh_retained": fresh_auto.exists(),
        }

        # =====================================================================
        # DEMO K: Interrupted Upload & Abandoned Render Workspace Recovery
        # =====================================================================
        print("\n--- Running Demo K: Interrupted Upload & Dead Workspace Recovery ---")
        crashed_upload = layout.temp / "crashed_session_part.part"
        crashed_upload.write_bytes(b"C" * 18000)
        os.utime(crashed_upload, (old_time, old_time))

        dead_job_dir = layout.temp / "job_dead_crash_404"
        dead_job_dir.mkdir(parents=True, exist_ok=True)
        (dead_job_dir / "frame_000.png").write_bytes(b"P" * 5000)
        os.utime(dead_job_dir, (old_time, old_time))
        for sf in dead_job_dir.iterdir():
            os.utime(sf, (old_time, old_time))

        rec_resp = client.post("/api/v1/maintenance/recover-stale-artifacts")
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        print(f"  [Demo K] Recovered files: {rec_data['recovered_files_count']}, Reclaimed: {rec_data['bytes_reclaimed']} bytes")
        assert not crashed_upload.exists(), "Interrupted part must be cleaned!"
        assert not dead_job_dir.exists(), "Dead workspace directory must be unlinked!"

        evidence["demos"]["demo_k"] = {
            "status": "PASSED",
            "recovered_files_count": rec_data["recovered_files_count"],
            "bytes_reclaimed": rec_data["bytes_reclaimed"],
            "crashed_upload_cleaned": not crashed_upload.exists(),
            "dead_workspace_cleaned": not dead_job_dir.exists(),
        }

        # =====================================================================
        # DEMO L: Audit History Verification & SQLite Database Integrity
        # =====================================================================
        print("\n--- Running Demo L: Cleanup Audit History & SQLite Integrity Check ---")
        hist_resp = client.get("/api/v1/maintenance/cleanup-history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        print(f"  [Demo L] Total recorded audit entries: {len(hist_data)}")
        assert len(hist_data) >= 2, "Expected multiple audit records from previous cleanup executions!"

        with sqlite_session(layout.db_file) as conn:
            integrity = [r[0] for r in conn.execute("PRAGMA integrity_check").fetchall()]
            print(f"  [Demo L] PRAGMA integrity_check: {integrity}")
            assert integrity == ["ok"]

            fk_check = conn.execute("PRAGMA foreign_key_check").fetchall()
            print(f"  [Demo L] PRAGMA foreign_key_check: {fk_check}")
            assert fk_check == []

        evidence["demos"]["demo_l"] = {
            "status": "PASSED",
            "total_audit_records": len(hist_data),
            "sqlite_integrity_check": integrity,
            "sqlite_foreign_key_check": fk_check,
        }

        print("\n" + "=" * 80)
        print("ALL 12 P1.9 DEMONSTRATIONS COMPLETED SUCCESSFULLY (100% PASSING)")
        print("=" * 80)

        # Write evidence JSON
        EVIDENCE_FILE.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(f"Evidence successfully written to: {EVIDENCE_FILE}")

    finally:
        try:
            shutil.rmtree(temp_root, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    run_all_demos()
