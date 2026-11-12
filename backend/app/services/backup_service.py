"""Database backup, recovery status, and diagnostic integrity verification service."""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.core.errors import AppError

logger = logging.getLogger("zezedit.backups")


class BackupService:
    """Safely snapshots, restores, and verifies SQLite databases while WAL mode is active."""

    def __init__(self, db_path: Path, backups_dir: Path) -> None:
        self.db_path = db_path
        self.backups_dir = backups_dir

    def create_backup(self, label: str = "manual") -> Dict[str, Any]:
        """Create a consistent SQLite backup using the online backup API."""
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_filename = f"backup_{label}_{stamp}.db"
        backup_path = self.backups_dir / backup_filename

        src = sqlite3.connect(str(self.db_path))
        dst = sqlite3.connect(str(backup_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        # Validate backup file integrity
        check = sqlite3.connect(str(backup_path))
        try:
            row = check.execute("PRAGMA integrity_check;").fetchone()
            if not row or str(row[0]).lower() != "ok":
                backup_path.unlink(missing_ok=True)
                raise AppError(
                    code="BACKUP_CORRUPTED",
                    message="Backup integrity verification check failed.",
                    status_code=500,
                )
        finally:
            check.close()

        return {
            "backup_filename": backup_filename,
            "backup_path": str(backup_path),
            "file_size_bytes": backup_path.stat().st_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "integrity_verified": True,
            "label": label,
        }

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all verified database backups sorted by creation time descending."""
        if not self.backups_dir.exists():
            return []

        backups: List[Dict[str, Any]] = []
        for f in self.backups_dir.glob("*.db"):
            if f.is_file():
                try:
                    stat = f.stat()
                    # Quick integrity check check
                    verified = False
                    try:
                        c = sqlite3.connect(str(f))
                        r = c.execute("PRAGMA quick_check;").fetchone()
                        verified = bool(r and str(r[0]).lower() == "ok")
                        c.close()
                    except Exception:
                        verified = False

                    backups.append({
                        "backup_filename": f.name,
                        "backup_path": str(f),
                        "file_size_bytes": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "is_safety_snapshot": "pre_restore" in f.name,
                        "integrity_verified": verified,
                    })
                except OSError:
                    pass

        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups

    def restore_backup(self, backup_filename: str) -> Dict[str, Any]:
        """Validate and restore a backup file to active SQLite database."""
        backup_path = self.backups_dir / backup_filename
        if not backup_path.exists():
            raise AppError(
                code="BACKUP_NOT_FOUND",
                message=f"Backup file '{backup_filename}' does not exist.",
                status_code=404,
            )

        # Integrity check backup before applying
        check = sqlite3.connect(str(backup_path))
        try:
            row = check.execute("PRAGMA integrity_check;").fetchone()
            if not row or str(row[0]).lower() != "ok":
                raise AppError(
                    code="BACKUP_CORRUPTED",
                    message="Target backup failed integrity verification.",
                    status_code=400,
                )
        finally:
            check.close()

        # Snapshot current database before restoring
        safety_snapshot = self.create_backup(label="pre_restore")

        # Perform online restore
        src = sqlite3.connect(str(backup_path))
        dst = sqlite3.connect(str(self.db_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        return {
            "restored_from": backup_filename,
            "safety_snapshot": safety_snapshot["backup_filename"],
            "restored_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        }

    def get_database_diagnostics(self) -> Dict[str, Any]:
        """Run deep diagnostic check on active database including integrity, FKs, and orphans."""
        issues: List[str] = []
        healthy = True

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            # 1. PRAGMA integrity_check
            row = conn.execute("PRAGMA integrity_check;").fetchone()
            integrity_ok = bool(row and str(row[0]).lower() == "ok")
            if not integrity_ok:
                healthy = False
                issues.append(f"PRAGMA integrity_check reported issues: {row[0] if row else 'empty'}")

            # 2. PRAGMA foreign_key_check
            fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
            fk_ok = len(fk_violations) == 0
            if not fk_ok:
                healthy = False
                issues.append(f"Foreign key violations detected ({len(fk_violations)} rows).")

            # 3. Journal mode verification
            jm_row = conn.execute("PRAGMA journal_mode;").fetchone()
            journal_mode = str(jm_row[0]).upper() if jm_row else "UNKNOWN"
            if journal_mode != "WAL":
                issues.append(f"Database journal mode is '{journal_mode}', recommended is 'WAL'.")

            # 4. Table counts
            counts: Dict[str, int] = {}
            for tbl in [
                "projects",
                "media_assets",
                "analysis_runs",
                "shorts_candidates",
                "timeline_sequences",
                "render_exports",
                "jobs",
                "project_events",
            ]:
                try:
                    c_row = conn.execute(f"SELECT COUNT(*) as cnt FROM {tbl}").fetchone()
                    counts[tbl] = c_row["cnt"] if c_row else 0
                except sqlite3.OperationalError:
                    counts[tbl] = 0

            # 5. Orphan scan: shorts_candidates missing project
            try:
                orphans = conn.execute(
                    """
                    SELECT COUNT(*) as cnt FROM shorts_candidates
                    WHERE project_id NOT IN (SELECT id FROM projects)
                    """
                ).fetchone()
                orphan_candidates = orphans["cnt"] if orphans else 0
                if orphan_candidates > 0:
                    healthy = False
                    issues.append(f"Found {orphan_candidates} orphaned shorts candidates referencing deleted projects.")
            except Exception:
                orphan_candidates = 0

        finally:
            conn.close()

        return {
            "healthy": healthy,
            "integrity_check": "ok" if integrity_ok else "failed",
            "foreign_key_check": "ok" if fk_ok else "violations",
            "journal_mode": journal_mode,
            "table_counts": counts,
            "orphaned_records": {
                "shorts_candidates": orphan_candidates,
            },
            "issues": issues,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_recovery_status(self) -> Dict[str, Any]:
        """Aggregate recovery metrics: last backup, interrupted jobs, missing assets, autosave."""
        backups = self.list_backups()
        last_backup = backups[0] if backups else None

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            # Check interrupted jobs
            interrupted = conn.execute(
                "SELECT id, job_type, updated_at FROM jobs WHERE status = 'interrupted' ORDER BY updated_at DESC"
            ).fetchall()
            interrupted_jobs = [dict(r) for r in interrupted]

            # Check missing media assets
            missing = conn.execute(
                "SELECT id, project_id, original_filename, storage_path FROM media_assets WHERE availability_status = 'missing'"
            ).fetchall()
            missing_assets = [dict(r) for r in missing]

            # Latest project event / autosave
            latest_ev = conn.execute(
                "SELECT project_id, event_type, created_at FROM project_events ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            last_activity = dict(latest_ev) if latest_ev else None
        finally:
            conn.close()

        return {
            "last_backup": last_backup,
            "total_backups_available": len(backups),
            "interrupted_jobs_count": len(interrupted_jobs),
            "interrupted_jobs": interrupted_jobs[:10],
            "missing_media_count": len(missing_assets),
            "missing_media_assets": missing_assets[:10],
            "last_project_activity": last_activity,
            "recovery_ready": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
