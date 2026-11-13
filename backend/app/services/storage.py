"""Storage manager service for path validation, storage inspection, and safe operations."""

import hashlib
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import resolve_contained_path, validate_storage_root_path
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session

logger = logging.getLogger("zezedit.storage")

# Low disk space threshold: 5 Gigabytes
LOW_STORAGE_THRESHOLD_BYTES = 5 * 1024 * 1024 * 1024


class StorageService:
    """Manages files, disk space, directory validation, and boundary safety."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.layout = StorageLayout.from_root(settings.storage_root)

    def inspect_storage(self) -> Dict[str, Any]:
        """Inspect directory accessibility, total/free disk space, and category sizes."""
        root = self.layout.root
        accessible = root.exists() and os.access(root, os.R_OK)
        writable = accessible and os.access(root, os.W_OK)

        total, used, free = 0, 0, 0
        if accessible:
            try:
                usage = shutil.disk_usage(root)
                total, used, free = usage.total, usage.used, usage.free
            except OSError:
                pass

        # Calculate category folder sizes
        category_sizes: Dict[str, int] = {}
        for folder_name in [
            "media",
            "proxies",
            "thumbnails",
            "analysis",
            "timelines",
            "shorts",
            "exports",
            "temp",
            "backups",
            "logs",
            "db",
        ]:
            folder_path: Path = getattr(self.layout, folder_name)
            size = 0
            if folder_path.exists():
                try:
                    for f in folder_path.rglob("*"):
                        if f.is_file() and not f.is_symlink():
                            size += f.stat().st_size
                except OSError:
                    pass
            category_sizes[folder_name] = size

        return {
            "storage_root": str(root),
            "is_accessible": accessible,
            "is_writable": writable,
            "total_space_bytes": total,
            "free_space_bytes": free,
            "used_space_bytes": used,
            "directories": {
                "media": str(self.layout.media),
                "proxies": str(self.layout.proxies),
                "thumbnails": str(self.layout.thumbnails),
                "analysis": str(self.layout.analysis),
                "timelines": str(self.layout.timelines),
                "shorts": str(self.layout.shorts),
                "exports": str(self.layout.exports),
                "temp": str(self.layout.temp),
                "backups": str(self.layout.backups),
                "logs": str(self.layout.logs),
                "db": str(self.layout.db),
            },
            "category_sizes_bytes": category_sizes,
        }

    def get_storage_breakdown(self) -> Dict[str, Any]:
        """Return structured breakdown separating source media, intermediate caches, DB, and exports."""
        stats = self.inspect_storage()
        cat = stats["category_sizes_bytes"]
        free_bytes = stats["free_space_bytes"]

        return {
            "storage_root": stats["storage_root"],
            "total_disk_space_bytes": stats["total_space_bytes"],
            "free_disk_space_bytes": free_bytes,
            "used_disk_space_bytes": stats["used_space_bytes"],
            "is_low_storage": free_bytes < LOW_STORAGE_THRESHOLD_BYTES,
            "low_storage_threshold_bytes": LOW_STORAGE_THRESHOLD_BYTES,
            "categories": {
                "source_media_bytes": cat.get("media", 0),
                "proxies_bytes": cat.get("proxies", 0),
                "thumbnails_bytes": cat.get("thumbnails", 0),
                "extracted_frames_bytes": cat.get("analysis", 0),
                "temp_cache_bytes": cat.get("temp", 0),
                "exports_bytes": cat.get("exports", 0),
                "database_bytes": cat.get("db", 0),
                "backups_bytes": cat.get("backups", 0),
                "logs_bytes": cat.get("logs", 0),
            },
            "directories": stats["directories"],
        }

    def preview_cache_cleanup(self) -> Dict[str, Any]:
        """Scan strictly disposable cache directories and generate preview with verification token."""
        eligible_files: List[Dict[str, Any]] = []
        total_bytes = 0

        # Scan layout.temp
        temp_dir = self.layout.temp
        if temp_dir.exists():
            for f in temp_dir.rglob("*"):
                if f.is_file() and not f.is_symlink():
                    try:
                        sz = f.stat().st_size
                        eligible_files.append({
                            "path": str(f),
                            "filename": f.name,
                            "category": "temp_buffer",
                            "size_bytes": sz,
                        })
                        total_bytes += sz
                    except OSError:
                        pass

        # Token binds the previewed count and bytes
        token_seed = f"CLEANUP_{len(eligible_files)}_{total_bytes}_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
        confirmation_token = hashlib.sha256(token_seed.encode("utf-8")).hexdigest()[:16].upper()

        return {
            "eligible_files_count": len(eligible_files),
            "total_bytes_to_free": total_bytes,
            "confirmation_token": confirmation_token,
            "eligible_files_preview": eligible_files[:30],
            "protected_categories": [
                "source_media (media/)",
                "database (db/zezedit.db)",
                "rendered_exports (exports/)",
                "backups (backups/)",
                "timeline_projects (timelines/)",
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def execute_cache_cleanup(self, confirmation_token: str) -> Dict[str, Any]:
        """Execute deletion strictly restricted to disposable cache files."""
        if not confirmation_token or len(confirmation_token.strip()) < 4:
            raise AppError(
                code="INVALID_CLEANUP_TOKEN",
                message="A valid confirmation token is required to execute cache cleanup.",
                status_code=400,
            )

        deleted_count = 0
        freed_bytes = 0
        temp_dir = self.layout.temp

        # Delete files inside temp_dir only
        if temp_dir.exists():
            for item in list(temp_dir.iterdir()):
                try:
                    if item.is_file() and not item.is_symlink():
                        sz = item.stat().st_size
                        item.unlink(missing_ok=True)
                        deleted_count += 1
                        freed_bytes += sz
                    elif item.is_dir():
                        for sub_f in item.rglob("*"):
                            if sub_f.is_file() and not sub_f.is_symlink():
                                sz = sub_f.stat().st_size
                                sub_f.unlink(missing_ok=True)
                                deleted_count += 1
                                freed_bytes += sz
                        shutil.rmtree(item, ignore_errors=True)
                except OSError as err:
                    logger.warning("Failed to remove cache file '%s': %s", item, err)

        logger.info("Executed cache cleanup: deleted %d files, freed %d bytes", deleted_count, freed_bytes)
        return {
            "status": "success",
            "deleted_files_count": deleted_count,
            "freed_bytes": freed_bytes,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    def clear_all_data(self, confirmation: str) -> Dict[str, Any]:
        """Wipe all managed media, thumbnails, proxies, frames, cache, temp, clips, scripts, and DB tables.
        
        Requires explicit confirmation == 'DELETE'.
        Never deletes external media original files outside managed storage or application code.
        Re-initializes the default project and keeps schema migrations intact.
        """
        if not confirmation or confirmation.strip().upper() != "DELETE":
            raise AppError(
                code="INVALID_CLEAR_ALL_CONFIRMATION",
                message="To clear all data, you must provide confirmation with exact value 'DELETE'.",
                status_code=400,
            )

        deleted_files_count = 0
        freed_bytes = 0
        cleared_categories: List[str] = []
        failed_deletions: List[Dict[str, str]] = []

        root_resolved = self.layout.root.resolve()

        # 0. Cancel any active or queued jobs first so background threads cannot write to disk or DB
        if self.layout.db_file.exists():
            try:
                with sqlite_session(self.layout.db_file) as conn:
                    cursor = conn.cursor()
                    has_jobs_tbl = cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
                    ).fetchone()
                    if has_jobs_tbl:
                        cursor.execute(
                            """
                            UPDATE jobs
                            SET status = 'cancelled',
                                stage = 'cancelled_by_system_reset',
                                error_message = 'Operation cancelled due to Clear All Data system reset',
                                updated_at = ?
                            WHERE status IN ('running', 'queued')
                            """,
                            (datetime.now(timezone.utc).isoformat(),),
                        )
            except Exception as job_err:
                logger.warning("Could not pre-cancel active jobs prior to cleanup: %s", job_err)

        # 1. Sweep all managed storage subdirectories strictly bounded within root
        managed_dirs = [
            ("media", self.layout.media),
            ("proxies", self.layout.proxies),
            ("thumbnails", self.layout.thumbnails),
            ("analysis", self.layout.analysis),
            ("timelines", self.layout.timelines),
            ("shorts", self.layout.shorts),
            ("exports", self.layout.exports),
            ("temp", self.layout.temp),
        ]

        for cat_name, folder_path in managed_dirs:
            # Verify folder_path is strictly within storage root
            try:
                resolved_folder = folder_path.resolve()
                if not resolved_folder.is_relative_to(root_resolved):
                    logger.error("Security violation: folder '%s' resolves outside storage root: %s", cat_name, resolved_folder)
                    continue
            except Exception as path_err:
                logger.error("Could not resolve folder path for %s: %s", cat_name, path_err)
                continue

            if folder_path.exists():
                cat_count = 0
                cat_bytes = 0
                for item in list(folder_path.iterdir()):
                    try:
                        # Symlink or junction protection: unlink link without traversing
                        if item.is_symlink() or os.path.islink(str(item)):
                            item.unlink(missing_ok=True)
                            cat_count += 1
                            continue

                        # Ensure target item resolves inside storage root
                        item_resolved = item.resolve()
                        if not item_resolved.is_relative_to(root_resolved):
                            logger.error("Security boundary skipped: item '%s' resolves outside storage root: %s", item, item_resolved)
                            continue

                        if item.is_file():
                            sz = item.stat().st_size
                            item.unlink(missing_ok=True)
                            cat_count += 1
                            cat_bytes += sz
                        elif item.is_dir():
                            for sub_f in list(item.rglob("*")):
                                if sub_f.is_symlink() or os.path.islink(str(sub_f)):
                                    sub_f.unlink(missing_ok=True)
                                    cat_count += 1
                                elif sub_f.is_file():
                                    if sub_f.resolve().is_relative_to(root_resolved):
                                        sz = sub_f.stat().st_size
                                        sub_f.unlink(missing_ok=True)
                                        cat_count += 1
                                        cat_bytes += sz
                            shutil.rmtree(item, ignore_errors=True)
                    except OSError as err:
                        logger.warning("Error clearing '%s' in %s: %s", item, cat_name, err)
                        failed_deletions.append({"path": str(item), "category": cat_name, "error": str(err)})

                # Re-ensure folder exists
                folder_path.mkdir(parents=True, exist_ok=True)
                cleared_categories.append(cat_name)
                deleted_files_count += cat_count
                freed_bytes += cat_bytes

        # 2. Reset database tables while preserving migrations & app_settings
        truncated_tables: List[str] = []
        if self.layout.db_file.exists():
            with sqlite_session(self.layout.db_file) as conn:
                conn.execute("PRAGMA foreign_keys = OFF;")
                cursor = conn.cursor()
                tables_rows = cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('schema_migrations', 'app_settings')"
                ).fetchall()
                table_names = [r[0] for r in tables_rows]

                for tbl in table_names:
                    cursor.execute(f"DELETE FROM {tbl};")
                    truncated_tables.append(tbl)

                # Ensure default project exists
                now_iso = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    """
                    INSERT INTO projects (id, name, description, settings_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "default",
                        "Default Workspace",
                        "Auto-created workspace for video intelligence",
                        "{}",
                        now_iso,
                        now_iso,
                    ),
                )
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("VACUUM;")

        logger.info(
            "Clear all data executed: %d files deleted (%d bytes), %d tables truncated, %d failures",
            deleted_files_count,
            freed_bytes,
            len(truncated_tables),
            len(failed_deletions),
        )

        return {
            "status": "success",
            "message": "All managed media, proxies, frames, cache, temp, clips, and database tables have been cleared.",
            "deleted_files_count": deleted_files_count,
            "freed_bytes": freed_bytes,
            "cleared_categories": cleared_categories,
            "truncated_tables": truncated_tables,
            "failed_deletions": failed_deletions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def validate_external_path(self, path_str: str) -> Path:
        """Validate an external media reference exists and is readable."""
        resolved = Path(path_str).expanduser().resolve(strict=False)
        if not resolved.exists():
            raise FileNotFoundError(f"Media file not found at '{resolved}'.")
        if not os.access(resolved, os.R_OK):
            raise PermissionError(f"Media file at '{resolved}' is not readable.")
        return resolved
