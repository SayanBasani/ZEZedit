"""
P0.8-R1 Database Audit Script
Read-only inspection of SQLite database integrity, foreign keys, table counts,
and physical disk file existence for exports and media assets.
"""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path("D:/ZezEdit/storage/db/zezedit.db")
PROJECT_ROOT = Path("D:/ZezEdit")

def audit():
    print("=" * 80)
    print("ZEZEDIT 2.0 — P0.8-R1 READ-ONLY DATABASE & FILE INTEGRITY AUDIT")
    print("=" * 80)
    print(f"Database Path: {DB_PATH.resolve()}")
    assert DB_PATH.exists(), f"Database file does not exist at {DB_PATH}"

    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # 1. Integrity Check
    cur.execute("PRAGMA integrity_check;")
    integrity_rows = cur.fetchall()
    integrity_status = [row[0] for row in integrity_rows]
    print(f"PRAGMA integrity_check: {integrity_status}")

    # 2. Foreign Key Check
    cur.execute("PRAGMA foreign_key_check;")
    fk_violations = cur.fetchall()
    print(f"PRAGMA foreign_key_check violations count: {len(fk_violations)}")
    if fk_violations:
        for v in fk_violations:
            print("  Violation:", dict(v))

    # 3. Table Counts
    cur.execute("SELECT count(id) FROM jobs;")
    jobs_count = cur.fetchone()[0]

    cur.execute("SELECT count(id) FROM exports;")
    exports_count = cur.fetchone()[0]

    cur.execute("SELECT count(id) FROM projects;")
    projects_count = cur.fetchone()[0]

    cur.execute("SELECT count(id) FROM media_assets;")
    media_count = cur.fetchone()[0]

    print("\n--- Table Record Counts ---")
    print(f"Jobs:         {jobs_count} (Expected: 93)")
    print(f"Exports:      {exports_count} (Expected: 44)")
    print(f"Projects:     {projects_count} (Expected: 1)")
    print(f"Media Assets: {media_count} (Expected: 5)")

    # 4. Physical existence of all registered source media files
    print("\n--- Registered Source Media Assets Inspection ---")
    cur.execute("SELECT id, original_filename, storage_path, availability_status FROM media_assets;")
    media_rows = cur.fetchall()
    missing_media = []
    found_media = []
    for row in media_rows:
        storage_path = Path(row["storage_path"])
        # Support relative or absolute
        if not storage_path.is_absolute():
            storage_path = PROJECT_ROOT / storage_path
        exists = storage_path.is_file()
        size = storage_path.stat().st_size if exists else 0
        print(f"Media ID: {row['id']} | File: {row['original_filename']} | Exists: {exists} ({size} bytes)")
        if exists:
            found_media.append(row["id"])
        else:
            missing_media.append((row["id"], str(storage_path)))

    print(f"Media physical existence: {len(found_media)} found, {len(missing_media)} missing")

    # 5. Physical existence of all completed exports
    print("\n--- Completed Exports Inspection ---")
    cur.execute("SELECT id, status, validation_status, output_path FROM exports;")
    export_rows = cur.fetchall()
    status_summary = {}
    valid_physical_mp4_count = 0
    missing_completed_exports = []
    for row in export_rows:
        st = row["status"]
        val = row["validation_status"]
        status_summary[f"{st}/{val}"] = status_summary.get(f"{st}/{val}", 0) + 1

        out_path_str = row["output_path"]
        if out_path_str:
            p = Path(out_path_str)
            if not p.is_absolute():
                p = PROJECT_ROOT / p
            if p.is_file() and p.suffix.lower() == ".mp4" and p.stat().st_size > 0:
                valid_physical_mp4_count += 1
            elif st == "completed":
                missing_completed_exports.append((row["id"], out_path_str, st, val))

    print(f"Export Status / Validation Breakdown: {status_summary}")
    print(f"Valid physical MP4 exports on disk: {valid_physical_mp4_count} (Expected: 33)")
    print(f"Missing completed exports: {len(missing_completed_exports)}")
    if missing_completed_exports:
        for item in missing_completed_exports:
            print("  Missing completed export:", item)

    con.close()

    result = {
        "integrity_ok": integrity_status == ["ok"],
        "foreign_key_violations": len(fk_violations),
        "jobs_count": jobs_count,
        "exports_count": exports_count,
        "projects_count": projects_count,
        "media_count": media_count,
        "media_found": len(found_media),
        "media_missing": len(missing_media),
        "valid_physical_mp4_count": valid_physical_mp4_count,
        "missing_completed_exports_count": len(missing_completed_exports),
    }

    print("\n--- Summary Audit Object ---")
    print(json.dumps(result, indent=2))
    print("=" * 80)
    return result

if __name__ == "__main__":
    audit()
