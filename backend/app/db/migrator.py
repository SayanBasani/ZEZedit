"""Forward-only numbered SQL migration runner tracked in `schema_migrations`."""

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.errors import MigrationError
from app.db.connection import sqlite_session

logger = logging.getLogger("zezedit.migrator")

SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class MigrationResult:
    """Summary of applied and existing database migrations."""

    db_path: str
    applied_versions: List[str]
    newly_applied: List[str]
    current_version: Optional[str]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_version_and_name(filename: str) -> tuple[str, str]:
    stem = Path(filename).stem
    parts = stem.split("_", 1)
    if len(parts) < 2 or not parts[0].isdigit():
        raise MigrationError(
            f"Migration filename '{filename}' must follow 'NNNN_description.sql' format."
        )
    return parts[0], parts[1]


def _backup_before_upgrade(conn: sqlite3.Connection, backup_dir: Path, target_version: str) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"pre_migration_{target_version}_{stamp}.db"
    dst = sqlite3.connect(str(backup_path))
    try:
        conn.backup(dst)
    finally:
        dst.close()
    return backup_path


def run_migrations(
    db_path: Path,
    migrations_dir: Path,
    backup_dir: Optional[Path] = None,
) -> MigrationResult:
    """
    Apply any pending `NNNN_*.sql` migrations cleanly in lexical order.
    Verifies checksums of previously applied migrations before applying new ones.
    """
    if not migrations_dir.exists():
        raise MigrationError(f"Migrations directory '{migrations_dir}' does not exist.")

    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        raise MigrationError(f"No SQL migration files found in '{migrations_dir}'.")

    newly_applied: List[str] = []

    with sqlite_session(db_path) as conn:
        conn.execute(SCHEMA_MIGRATIONS_DDL)

        existing_rows = conn.execute(
            "SELECT version, name, checksum_sha256 FROM schema_migrations ORDER BY version ASC"
        ).fetchall()
        applied_map = {row["version"]: row for row in existing_rows}

        pending_files: List[tuple[str, str, str, Path]] = []
        for sql_file in migration_files:
            version, name = _parse_version_and_name(sql_file.name)
            checksum = _file_sha256(sql_file)

            if version in applied_map:
                recorded_checksum = applied_map[version]["checksum_sha256"]
                if recorded_checksum != checksum:
                    raise MigrationError(
                        f"Checksum mismatch for already-applied migration {version}_{name}.sql.",
                        details={
                            "version": version,
                            "expected_checksum": recorded_checksum,
                            "actual_checksum": checksum,
                        },
                    )
                continue

            pending_files.append((version, name, checksum, sql_file))

        # Snapshot existing database before upgrading schema
        if pending_files and applied_map and backup_dir is not None:
            first_pending_ver = pending_files[0][0]
            backup_path = _backup_before_upgrade(conn, backup_dir, first_pending_ver)
            logger.info("Created pre-migration SQLite snapshot: %s", backup_path)

        for version, name, checksum, sql_file in pending_files:
            sql_body = sql_file.read_text(encoding="utf-8").strip()
            if not sql_body:
                raise MigrationError(f"Migration file '{sql_file.name}' is empty.")

            applied_at = datetime.now(timezone.utc).isoformat()
            try:
                conn.executescript(f"BEGIN IMMEDIATE;\n{sql_body}\nCOMMIT;")
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, checksum_sha256, applied_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (version, name, checksum, applied_at),
                )
                newly_applied.append(version)
                logger.info("Applied SQLite migration %s (%s)", version, name)
            except sqlite3.Error as exc:
                try:
                    conn.execute("ROLLBACK;")
                except sqlite3.Error:
                    pass
                raise MigrationError(
                    f"Failed applying migration {sql_file.name}: {exc}",
                    details={"version": version, "file": sql_file.name},
                ) from exc

        final_rows = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version ASC"
        ).fetchall()
        applied_versions = [row["version"] for row in final_rows]

    return MigrationResult(
        db_path=str(db_path),
        applied_versions=applied_versions,
        newly_applied=newly_applied,
        current_version=applied_versions[-1] if applied_versions else None,
    )
