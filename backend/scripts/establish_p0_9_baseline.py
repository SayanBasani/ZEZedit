"""
P0.9 Baseline Establishment Script
Records comprehensive pre-test baseline including:
- Git branch and commit
- Database path, size, WAL journal mode
- Integrity and foreign key checks
- Exact entity counts across all tables
- SHA-256 hashes of all registered source media files
- SHA-256 hashes of all valid physical export MP4 files
- Verification of all existing backups
- Creation of a new verified backup using BackupService
- Saves baseline manifest to docs/reports/priority_0/p0_9_evidence/baseline_manifest.json
"""
import hashlib
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path("D:/ZezEdit")
DB_PATH = PROJECT_ROOT / "storage" / "db" / "zezedit.db"
BACKUPS_DIR = PROJECT_ROOT / "storage" / "backups"
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "reports" / "priority_0" / "p0_9_evidence"

def compute_sha256(file_path: Path, max_bytes: int = None) -> str:
    """Compute SHA-256 hash of a file (chunked)."""
    h = hashlib.sha256()
    bytes_read = 0
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            bytes_read += len(chunk)
            if max_bytes and bytes_read >= max_bytes:
                break
    return h.hexdigest()

def get_git_info():
    branch = subprocess.check_output(["git", "-C", str(PROJECT_ROOT), "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    head = subprocess.check_output(["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"], text=True).strip()
    status_raw = subprocess.check_output(["git", "-C", str(PROJECT_ROOT), "status", "--short"], text=True).strip()
    modified = []
    untracked = []
    for line in status_raw.splitlines():
        st = line[:2]
        path = line[3:]
        if "??" in st:
            untracked.append(path)
        else:
            modified.append(path)
    return {
        "branch": branch,
        "head": head,
        "modified_count": len(modified),
        "untracked_count": len(untracked),
        "modified_files": modified,
        "untracked_files": untracked,
    }

def establish_baseline():
    print("=" * 80)
    print("ZEZEDIT 2.0 — ESTABLISHING P0.9 SAFE PERSISTENCE BASELINE")
    print("=" * 80)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Git Info
    git_info = get_git_info()
    print(f"Git: Branch={git_info['branch']}, HEAD={git_info['head'][:8]}")
    print(f"Tracked Modified Files: {git_info['modified_count']}, Untracked: {git_info['untracked_count']}")

    # 2. Database Properties
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"
    db_size = DB_PATH.stat().st_size
    wal_file = PROJECT_ROOT / "storage" / "db" / "zezedit.db-wal"
    wal_size = wal_file.stat().st_size if wal_file.exists() else 0
    shm_file = PROJECT_ROOT / "storage" / "db" / "zezedit.db-shm"
    shm_size = shm_file.stat().st_size if shm_file.exists() else 0

    print(f"Database Path: {DB_PATH} ({db_size} bytes)")
    print(f"WAL File: exists={wal_file.exists()} ({wal_size} bytes), SHM: exists={shm_file.exists()} ({shm_size} bytes)")

    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("PRAGMA journal_mode;")
    journal_mode = cur.fetchone()[0]
    print(f"SQLite Journal Mode: {journal_mode}")

    cur.execute("PRAGMA integrity_check;")
    integrity = [r[0] for r in cur.fetchall()]
    print(f"PRAGMA integrity_check: {integrity}")
    assert integrity == ["ok"], f"Integrity check failed: {integrity}"

    cur.execute("PRAGMA foreign_key_check;")
    fk_violations = [dict(r) for r in cur.fetchall()]
    print(f"PRAGMA foreign_key_check violations: {len(fk_violations)}")
    assert len(fk_violations) == 0, f"Foreign key violations found: {fk_violations}"

    # 3. Table Counts
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cur.fetchall()]
    table_counts = {}
    for tbl in sorted(tables):
        cur.execute(f"SELECT count(*) FROM {tbl};")
        table_counts[tbl] = cur.fetchone()[0]

    print("\n--- Database Table Entity Counts ---")
    for tbl, count in table_counts.items():
        print(f"  {tbl:<25}: {count}")

    # 4. Job States Breakdown
    cur.execute("SELECT status, count(*) FROM jobs GROUP BY status;")
    job_states = {r[0]: r[1] for r in cur.fetchall()}
    print(f"\nJob States: {job_states}")

    # 5. Source Media Hash Baseline
    print("\n--- Source Media Integrity & Hash Baseline ---")
    cur.execute("SELECT id, original_filename, storage_path, file_size_bytes, availability_status FROM media_assets;")
    media_records = []
    for r in cur.fetchall():
        sp = Path(r["storage_path"])
        if not sp.is_absolute():
            sp = PROJECT_ROOT / sp
        exists = sp.is_file()
        actual_size = sp.stat().st_size if exists else 0
        sha = compute_sha256(sp) if exists else None
        print(f"  Media [{r['id']}] {r['original_filename']}: size={actual_size} bytes, sha256={sha[:16] if sha else 'MISSING'}...")
        media_records.append({
            "id": r["id"],
            "filename": r["original_filename"],
            "path": str(sp),
            "exists": exists,
            "recorded_size": r["file_size_bytes"],
            "actual_size": actual_size,
            "sha256": sha,
        })

    # 6. Generated Export Hash Baseline
    print("\n--- Generated Exports Integrity & Hash Baseline ---")
    cur.execute("SELECT id, status, validation_status, output_path, file_size_bytes FROM exports;")
    export_records = []
    valid_physical_exports = 0
    for r in cur.fetchall():
        out_p = r["output_path"]
        exists = False
        actual_size = 0
        sha = None
        if out_p:
            p = Path(out_p)
            if not p.is_absolute():
                p = PROJECT_ROOT / p
            exists = p.is_file()
            if exists and p.suffix.lower() == ".mp4" and p.stat().st_size > 0:
                valid_physical_exports += 1
                actual_size = p.stat().st_size
                sha = compute_sha256(p)
        export_records.append({
            "id": r["id"],
            "status": r["status"],
            "validation_status": r["validation_status"],
            "output_path": out_p,
            "exists": exists,
            "actual_size": actual_size,
            "sha256": sha,
        })

    print(f"  Total Export Rows: {len(export_records)}, Valid Physical MP4s on Disk: {valid_physical_exports}")

    con.close()

    # 7. Existing Backup Verification
    print("\n--- Existing Backups Verification ---")
    existing_backups = []
    if BACKUPS_DIR.exists():
        for bf in sorted(BACKUPS_DIR.glob("*.db")):
            size = bf.stat().st_size
            # Check integrity
            b_con = sqlite3.connect(str(bf))
            try:
                b_check = b_con.execute("PRAGMA quick_check;").fetchone()
                b_ok = bool(b_check and str(b_check[0]).lower() == "ok")
            except Exception:
                b_ok = False
            finally:
                b_con.close()
            print(f"  Backup: {bf.name} ({size} bytes), Integrity={b_ok}")
            existing_backups.append({
                "filename": bf.name,
                "size_bytes": size,
                "integrity_ok": b_ok,
            })

    # 8. Create a Fresh Verified Backup via Application's BackupService
    print("\n--- Creating New Verified Backup via BackupService ---")
    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))
    from app.services.backup_service import BackupService
    backup_svc = BackupService(db_path=DB_PATH, backups_dir=BACKUPS_DIR)
    new_backup = backup_svc.create_backup(label="p0_9_pre_test")
    print(f"  Created Baseline Backup: {new_backup['backup_filename']} ({new_backup['file_size_bytes']} bytes)")
    print(f"  Integrity Verified: {new_backup['integrity_verified']}")
    assert new_backup["integrity_verified"] is True

    # 9. Assemble Baseline Manifest
    manifest = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git": git_info,
        "database": {
            "path": str(DB_PATH),
            "size_bytes": db_size,
            "wal_size_bytes": wal_size,
            "journal_mode": journal_mode,
            "integrity_ok": True,
            "fk_violations_count": 0,
            "table_counts": table_counts,
            "job_states": job_states,
        },
        "media_assets": {
            "count": len(media_records),
            "records": media_records,
        },
        "exports": {
            "count": len(export_records),
            "valid_physical_mp4_count": valid_physical_exports,
            "records": export_records,
        },
        "backups": {
            "prior_existing_count": len(existing_backups),
            "prior_existing": existing_backups,
            "fresh_baseline_backup": new_backup,
        },
    }

    manifest_file = EVIDENCE_DIR / "baseline_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nSaved safe baseline manifest to: {manifest_file.resolve()}")
    print("=" * 80)
    return manifest

if __name__ == "__main__":
    establish_baseline()
