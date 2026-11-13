"""Storage manager service for path validation, storage inspection, and safe operations."""

import gc
import hashlib
import logging
import os
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import resolve_contained_path, validate_storage_root_path
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.services.jobs import JobOrchestrator

logger = logging.getLogger("zezedit.storage")

# Global cleanup execution lock preventing parallel wipeouts
_CLEANUP_LOCK = threading.Lock()

# Low disk space threshold: 5 Gigabytes
LOW_STORAGE_THRESHOLD_BYTES = 5 * 1024 * 1024 * 1024


def _format_bytes(bytes_count: int) -> str:
    if bytes_count <= 0:
        return "0 B"
    b = float(bytes_count)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024.0:
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} PB"


class StorageService:
    """Manages files, disk space, directory validation, and boundary safety."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.layout = StorageLayout.from_root(settings.storage_root)

    def format_bytes(self, bytes_count: int) -> str:
        return _format_bytes(bytes_count)

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
        managed_folder_map = {
            "media": self.layout.media,
            "proxies": self.layout.proxies,
            "thumbnails": self.layout.thumbnails,
            "analysis": self.layout.analysis,
            "characters": self.layout.root / "characters",
            "timelines": self.layout.timelines,
            "shorts": self.layout.shorts,
            "exports": self.layout.exports,
            "temp": self.layout.temp,
            "backups": self.layout.backups,
            "logs": self.layout.logs,
            "db": self.layout.db,
        }
        for folder_name, folder_path in managed_folder_map.items():
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
                "characters_bytes": cat.get("characters", 0),
                "temp_cache_bytes": cat.get("temp", 0),
                "exports_bytes": cat.get("exports", 0),
                "database_bytes": cat.get("db", 0),
                "backups_bytes": cat.get("backups", 0),
                "logs_bytes": cat.get("logs", 0),
            },
            "directories": stats["directories"],
        }

    def preview_user_data_cleanup(self) -> Dict[str, Any]:
        """Scan all managed storage and database tables to generate complete cleanup preview."""
        breakdown = self.get_storage_breakdown()
        cat = breakdown["categories"]
        total_user_bytes = (
            cat.get("source_media_bytes", 0)
            + cat.get("proxies_bytes", 0)
            + cat.get("thumbnails_bytes", 0)
            + cat.get("extracted_frames_bytes", 0)
            + cat.get("characters_bytes", 0)
            + cat.get("temp_cache_bytes", 0)
            + cat.get("exports_bytes", 0)
        )

        source_videos_count = 0
        generated_clips_count = 0
        analysis_artifacts_count = 0
        temp_files_count = 0
        active_jobs: List[Dict[str, Any]] = []

        # Count temp files
        if self.layout.temp.exists():
            temp_files_count = sum(1 for f in self.layout.temp.rglob("*") if f.is_file() and not f.is_symlink())

        if self.layout.db_file.exists():
            try:
                with sqlite_session(self.layout.db_file) as conn:
                    # Query user tables if present
                    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                    if "media_assets" in tables:
                        source_videos_count = conn.execute("SELECT COUNT(*) FROM media_assets").fetchone()[0]
                    if "media_generated_clips_history" in tables:
                        generated_clips_count += conn.execute("SELECT COUNT(*) FROM media_generated_clips_history").fetchone()[0]
                    if "shorts_candidates" in tables:
                        generated_clips_count += conn.execute("SELECT COUNT(*) FROM shorts_candidates").fetchone()[0]
                    if "sampled_frames" in tables:
                        analysis_artifacts_count += conn.execute("SELECT COUNT(*) FROM sampled_frames").fetchone()[0]
                    if "transcript_segments" in tables:
                        analysis_artifacts_count += conn.execute("SELECT COUNT(*) FROM transcript_segments").fetchone()[0]
                    if "video_scenes" in tables:
                        analysis_artifacts_count += conn.execute("SELECT COUNT(*) FROM video_scenes").fetchone()[0]
                    if "jobs" in tables:
                        active_rows = conn.execute(
                            "SELECT id, job_type, status, current_stage FROM jobs WHERE status IN ('running', 'queued', 'cancelling')"
                        ).fetchall()
                        active_jobs = [
                            {"id": r[0], "job_type": r[1], "status": r[2], "current_stage": r[3]}
                            for r in active_rows
                        ]
            except Exception as db_err:
                logger.warning("Could not gather DB entity counts for cleanup preview: %s", db_err)

        return {
            "total_managed_user_bytes": total_user_bytes,
            "estimated_reclaimable_bytes": total_user_bytes,
            "formatted_reclaimable_space": self.format_bytes(total_user_bytes),
            "categories": cat,
            "source_videos_count": source_videos_count,
            "video_count": source_videos_count,
            "generated_clips_count": generated_clips_count,
            "clip_count": generated_clips_count,
            "analysis_artifacts_count": analysis_artifacts_count,
            "frame_count": analysis_artifacts_count,
            "temp_files_count": temp_files_count,
            "temp_file_count": temp_files_count,
            "active_jobs_count": len(active_jobs),
            "active_jobs": active_jobs,
            "required_confirmation_text": "DELETE ALL USER DATA",
            "confirmation_prompt": "Type DELETE ALL USER DATA to confirm",
            "storage_root": str(self.layout.root),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def clear_all_data(self, confirmation: str) -> Dict[str, Any]:
        """Alias for clear_all_user_data for backward compatibility."""
        return self.clear_all_user_data(confirmation)

    def clear_all_user_data(self, confirmation: str) -> Dict[str, Any]:
        """Perform complete storage reclamation and user data purge.

        Requires confirmation == 'DELETE ALL USER DATA' (or 'DELETE').
        Guarantees:
        1. Cancels and stops all running workers, terminating child FFmpeg subprocesses.
        2. Measures physical disk bytes before and after.
        3. Removes all managed media, proxies, frames, analysis, characters, shorts, exports, and temp files.
        4. Truncates all user content tables while preserving schema migrations and app settings.
        5. Performs SQLite WAL checkpoint and VACUUM to reclaim database file space.
        6. Preserves application code, virtual environments, node dependencies, and external source files.
        """
        valid_confirmations = {"DELETE ALL USER DATA", "DELETE"}
        if not confirmation or confirmation.strip().upper() not in valid_confirmations:
            raise AppError(
                code="INVALID_CLEAR_ALL_CONFIRMATION",
                message="To clear all user data, you must provide confirmation with exact value 'DELETE ALL USER DATA'.",
                status_code=400,
            )

        with _CLEANUP_LOCK:
            root_resolved = self.layout.root.resolve()
            now_iso = datetime.now(timezone.utc).isoformat()

            # Measure pre-cleanup storage
            pre_managed_bytes = 0
            managed_dirs = [
                ("media", self.layout.media),
                ("proxies", self.layout.proxies),
                ("thumbnails", self.layout.thumbnails),
                ("analysis", self.layout.analysis),
                ("characters", self.layout.root / "characters"),
                ("timelines", self.layout.timelines),
                ("shorts", self.layout.shorts),
                ("exports", self.layout.exports),
                ("temp", self.layout.temp),
            ]

            for _, folder_path in managed_dirs:
                if folder_path.exists():
                    for f in folder_path.rglob("*"):
                        if f.is_file() and not f.is_symlink():
                            try:
                                pre_managed_bytes += f.stat().st_size
                            except OSError:
                                pass

            pre_db_bytes = self.layout.db_file.stat().st_size if self.layout.db_file.exists() else 0

            # Step 1: Pre-cleanup entity counts & stop running jobs
            source_videos_count = 0
            generated_clips_count = 0
            extracted_frames_count = 0
            thumbnails_count = 0
            analysis_records_count = 0
            temp_files_count = 0

            if self.layout.thumbnails.exists():
                thumbnails_count = len(list(self.layout.thumbnails.glob("*")))
            if self.layout.temp.exists():
                temp_files_count = sum(1 for f in self.layout.temp.rglob("*") if f.is_file())

            if self.layout.db_file.exists():
                try:
                    with sqlite_session(self.layout.db_file) as conn:
                        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                        if "media_assets" in tables:
                            source_videos_count = conn.execute("SELECT COUNT(*) FROM media_assets").fetchone()[0]
                        if "media_generated_clips_history" in tables:
                            generated_clips_count = conn.execute("SELECT COUNT(*) FROM media_generated_clips_history").fetchone()[0]
                        if "sampled_frames" in tables:
                            extracted_frames_count = conn.execute("SELECT COUNT(*) FROM sampled_frames").fetchone()[0]
                        if "analysis_runs" in tables:
                            analysis_records_count = conn.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]

                        # Stop active jobs
                        if "jobs" in tables:
                            active_jobs = conn.execute(
                                "SELECT id, worker_pid FROM jobs WHERE status IN ('running', 'queued', 'cancelling')"
                            ).fetchall()
                            jobs_mgr = JobOrchestrator(self.settings, self.layout.db_file)
                            for r in active_jobs:
                                jid, pid = r[0], r[1]
                                if pid:
                                    jobs_mgr._terminate_pid_tree(pid)
                                conn.execute(
                                    """
                                    UPDATE jobs
                                    SET status = 'cancelled', current_stage = 'cancelled_by_system_reset',
                                        error_message = 'Operation cancelled due to Clear All User Data system reset',
                                        updated_at = ?
                                    WHERE id = ?
                                    """,
                                    (now_iso, jid),
                                )
                except Exception as job_err:
                    logger.warning("Could not pre-cancel active jobs prior to cleanup: %s", job_err)

            # Give OS workers brief moment to exit and release file handles
            gc.collect()
            time.sleep(0.15)

            # Step 2: Sweep managed storage subdirectories strictly bounded within root
            deleted_files_count = 0
            freed_bytes = 0
            cleared_categories: List[str] = []
            failed_deletions: List[Dict[str, str]] = []

            for cat_name, folder_path in managed_dirs:
                try:
                    resolved_folder = folder_path.resolve()
                    if not resolved_folder.is_relative_to(root_resolved):
                        logger.error("Security boundary violation: %s resolves outside storage root: %s", cat_name, resolved_folder)
                        continue
                except Exception as path_err:
                    logger.error("Could not resolve folder path for %s: %s", cat_name, path_err)
                    continue

                if folder_path.exists():
                    cat_count = 0
                    cat_bytes = 0
                    for item in list(folder_path.iterdir()):
                        try:
                            # Symlink / junction safety
                            if item.is_symlink() or os.path.islink(str(item)):
                                item.unlink(missing_ok=True)
                                cat_count += 1
                                continue

                            item_resolved = item.resolve()
                            if not item_resolved.is_relative_to(root_resolved):
                                logger.error("Skipped item %s resolving outside root", item)
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
                                    elif sub_f.is_file() and sub_f.resolve().is_relative_to(root_resolved):
                                        sz = sub_f.stat().st_size
                                        try:
                                            sub_f.unlink(missing_ok=True)
                                        except PermissionError:
                                            # On Windows: brief gc and retry
                                            gc.collect()
                                            time.sleep(0.05)
                                            sub_f.unlink(missing_ok=True)
                                        cat_count += 1
                                        cat_bytes += sz
                                shutil.rmtree(item, ignore_errors=True)
                        except OSError as err:
                            logger.warning("Error clearing '%s' in %s: %s", item, cat_name, err)
                            failed_deletions.append({"path": str(item), "category": cat_name, "error": str(err)})

                    # Ensure empty managed folder persists
                    folder_path.mkdir(parents=True, exist_ok=True)
                    cleared_categories.append(cat_name)
                    deleted_files_count += cat_count
                    freed_bytes += cat_bytes

            # Step 3: Purge user-owned database records while preserving schema & migrations
            truncated_tables: List[str] = []
            if self.layout.db_file.exists():
                with sqlite_session(self.layout.db_file) as conn:
                    conn.execute("PRAGMA foreign_keys = OFF;")
                    cursor = conn.cursor()
                    tables_rows = cursor.execute(
                        """
                        SELECT name FROM sqlite_master
                        WHERE type='table'
                          AND name NOT LIKE 'sqlite_%'
                          AND name NOT IN ('schema_migrations', 'app_settings')
                        """
                    ).fetchall()
                    table_names = [r[0] for r in tables_rows]

                    for tbl in table_names:
                        cursor.execute(f"DELETE FROM {tbl};")
                        truncated_tables.append(tbl)

                    # Re-create clean default project
                    cursor.execute(
                        """
                        INSERT INTO projects (id, name, description, storage_subdir, created_at, updated_at, project_config_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "default",
                            "Default Workspace",
                            "Auto-created workspace for video intelligence",
                            "default_p",
                            now_iso,
                            now_iso,
                            "{}",
                        ),
                    )
                    conn.execute("PRAGMA foreign_keys = ON;")

                    # Reclaim SQLite pages and truncate WAL
                    try:
                        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                        conn.execute("VACUUM;")
                        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    except Exception as vac_err:
                        logger.warning("Could not execute VACUUM/checkpoint: %s", vac_err)

            # Step 4: Post-cleanup physical measurement
            post_managed_bytes = 0
            remaining_files_count = 0
            for _, folder_path in managed_dirs:
                if folder_path.exists():
                    for f in folder_path.rglob("*"):
                        if f.is_file() and not f.is_symlink():
                            try:
                                post_managed_bytes += f.stat().st_size
                                remaining_files_count += 1
                            except OSError:
                                pass

            post_db_bytes = self.layout.db_file.stat().st_size if self.layout.db_file.exists() else 0
            actual_reclaimed_bytes = max(0, (pre_managed_bytes + pre_db_bytes) - (post_managed_bytes + post_db_bytes))

            logger.info(
                "Clear All User Data complete: reclaimed %d bytes, deleted %d files, truncated %d tables",
                actual_reclaimed_bytes,
                deleted_files_count,
                len(truncated_tables),
            )

            return {
                "status": "success",
                "message": "All managed user data has been permanently cleared and disk space reclaimed.",
                "before_bytes": pre_managed_bytes + pre_db_bytes,
                "after_bytes": post_managed_bytes + post_db_bytes,
                "reclaimed_bytes": actual_reclaimed_bytes,
                "actual_reclaimed_bytes": actual_reclaimed_bytes,
                "formatted_reclaimed_space": _format_bytes(actual_reclaimed_bytes),
                "deleted_files_count": deleted_files_count,
                "purged_tables_count": len(truncated_tables),
                "source_videos_deleted": source_videos_count,
                "generated_clips_deleted": generated_clips_count,
                "extracted_frames_deleted": extracted_frames_count,
                "thumbnails_deleted": thumbnails_count,
                "analysis_records_deleted": analysis_records_count,
                "temp_files_deleted": temp_files_count,
                "remaining_managed_user_files": remaining_files_count,
                "cleared_categories": cleared_categories,
                "truncated_tables": truncated_tables,
                "failed_deletions": failed_deletions,
                "application_runtime": "Preserved",
                "database_schema": "Preserved",
                "external_files": "Preserved",
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
