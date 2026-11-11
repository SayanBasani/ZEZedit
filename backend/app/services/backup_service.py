"""Database backup and restore verification service."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from app.core.errors import AppError


class BackupService:
    """Safely snapshots and restores SQLite databases while WAL mode is active."""

    def __init__(self, db_path: Path, backups_dir: Path) -> None:
        self.db_path = db_path
        self.backups_dir = backups_dir

    def create_backup(self, label: str = "manual") -> Dict[str, any]:
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
            if not row or row[0].lower() != "ok":
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
        }

    def restore_backup(self, backup_filename: str) -> Dict[str, any]:
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
            if not row or row[0].lower() != "ok":
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
