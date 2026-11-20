"""Storage manager service for path validation, storage inspection, and safe operations."""

import gc
import hashlib
import json
import logging
import os
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import resolve_contained_path, validate_storage_root_path
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.schemas.core import (
    StorageQuotaSettingsDTO,
    StorageQuotaUpdateRequest,
    StorageQuotaStatusResponse,
)
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

    def resolve_contained_path(self, candidate_path: Union[str, Path]) -> Optional[Path]:
        """Safely resolve candidate path within storage root, returning None on traversal/escape."""
        try:
            return resolve_contained_path(self.layout.root, candidate_path)
        except Exception:
            return None

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
        """Return structured breakdown separating source media, canonical shared media, intermediate caches, DB, and exports."""
        stats = self.inspect_storage()
        cat = stats["category_sizes_bytes"]
        free_bytes = stats["free_space_bytes"]

        # Calculate database physical and logical asset metrics
        canonical_shared_bytes = 0
        logical_assets_bytes = 0
        unique_canonical_files: Set[str] = set()

        if self.layout.db_file.exists():
            try:
                with sqlite_session(self.layout.db_file) as conn:
                    cursor = conn.cursor()
                    tables = {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                    if "stored_media_files" in tables:
                        stored_rows = cursor.execute("SELECT id, storage_path, file_size_bytes, reference_count FROM stored_media_files").fetchall()
                        for sr in stored_rows:
                            sp = Path(sr["storage_path"])
                            if sp.exists() and not sp.is_symlink():
                                try:
                                    resolved = str(sp.resolve())
                                    if resolved not in unique_canonical_files:
                                        unique_canonical_files.add(resolved)
                                        canonical_shared_bytes += sp.stat().st_size
                                except OSError:
                                    pass
                    if "media_assets" in tables:
                        row = cursor.execute("SELECT SUM(file_size_bytes) FROM media_assets WHERE availability_status != 'deleted'").fetchone()
                        if row and row[0]:
                            logical_assets_bytes = int(row[0])
            except Exception as exc:
                logger.warning("Could not gather database media metrics for breakdown: %s", exc)

        # Temporary uploads: files in temp/uploads or *.uploading / *.part files across storage
        temporary_uploads_bytes = 0
        uploads_dir = self.layout.temp / "uploads"
        if uploads_dir.exists():
            for f in uploads_dir.rglob("*"):
                if f.is_file() and not f.is_symlink():
                    try:
                        temporary_uploads_bytes += f.stat().st_size
                    except OSError:
                        pass
        for pattern in ("**/*.uploading", "**/*.part"):
            if self.layout.media.exists():
                for f in self.layout.media.glob(pattern):
                    if f.is_file() and not f.is_symlink():
                        try:
                            temporary_uploads_bytes += f.stat().st_size
                        except OSError:
                            pass
            if self.layout.temp.exists():
                for f in self.layout.temp.glob(pattern):
                    if f.is_file() and not f.is_symlink():
                        try:
                            if not uploads_dir.exists() or not f.is_relative_to(uploads_dir):
                                temporary_uploads_bytes += f.stat().st_size
                        except OSError:
                            pass

        # Temporary rendering: temp/job_* folders, temp/render_scratch.mp4, temp/*.tmp, temp/*.ass
        temporary_rendering_bytes = 0
        if self.layout.temp.exists():
            for item in self.layout.temp.iterdir():
                if item.name == "uploads":
                    continue
                if item.is_dir() and item.name.startswith("job_"):
                    for f in item.rglob("*"):
                        if f.is_file() and not f.is_symlink():
                            try:
                                temporary_rendering_bytes += f.stat().st_size
                            except OSError:
                                pass
                elif item.is_file() and not item.is_symlink():
                    if item.name.endswith((".tmp", ".ass", ".uploading", ".part")) or item.name in ("render_scratch.mp4", "captions.ass"):
                        try:
                            temporary_rendering_bytes += item.stat().st_size
                        except OSError:
                            pass

        # Extracted audio: temp audio files or analysis audio
        extracted_audio_bytes = 0
        audio_exts = {".wav", ".aac", ".flac", ".mp3", ".m4a"}
        if self.layout.temp.exists():
            for f in self.layout.temp.rglob("*"):
                if f.is_file() and not f.is_symlink() and f.suffix.lower() in audio_exts:
                    try:
                        extracted_audio_bytes += f.stat().st_size
                    except OSError:
                        pass
        analysis_audio_dir = self.layout.analysis / "audio"
        if analysis_audio_dir.exists():
            for f in analysis_audio_dir.rglob("*"):
                if f.is_file() and not f.is_symlink() and f.suffix.lower() in audio_exts:
                    try:
                        extracted_audio_bytes += f.stat().st_size
                    except OSError:
                        pass

        # Keyframes and thumbnails
        keyframes_and_thumbnails_bytes = cat.get("thumbnails", 0)
        frames_dir = self.layout.analysis / "frames"
        if frames_dir.exists():
            for f in frames_dir.rglob("*"):
                if f.is_file() and not f.is_symlink():
                    try:
                        keyframes_and_thumbnails_bytes += f.stat().st_size
                    except OSError:
                        pass

        # Database and backups
        database_and_backups_bytes = cat.get("db", 0) + cat.get("backups", 0)

        # Total application physical storage (measured uniquely across all physical files, no double counting)
        seen_unique_files: Set[str] = set()
        total_application_bytes = 0
        if self.layout.root.exists():
            for f in self.layout.root.rglob("*"):
                if f.is_file() and not f.is_symlink():
                    try:
                        res_str = str(f.resolve())
                        if res_str not in seen_unique_files:
                            seen_unique_files.add(res_str)
                            total_application_bytes += f.stat().st_size
                    except OSError:
                        pass

        # Recoverable storage: temp uploads + temp renders + extracted audio in temp + proxies
        recoverable_bytes = temporary_uploads_bytes + temporary_rendering_bytes + extracted_audio_bytes + cat.get("proxies", 0)
        protected_bytes = max(0, total_application_bytes - recoverable_bytes)

        quota_status_res = self.get_storage_quota_status()

        return {
            "storage_root": stats["storage_root"],
            "total_disk_space_bytes": stats["total_space_bytes"],
            "free_disk_space_bytes": free_bytes,
            "used_disk_space_bytes": stats["used_space_bytes"],
            "total_application_storage_bytes": total_application_bytes,
            "recoverable_storage_bytes": recoverable_bytes,
            "protected_storage_bytes": protected_bytes,
            "is_low_storage": free_bytes < LOW_STORAGE_THRESHOLD_BYTES,
            "low_storage_threshold_bytes": LOW_STORAGE_THRESHOLD_BYTES,
            "categories": {
                "source_media_bytes": cat.get("media", 0),
                "canonical_shared_media_bytes": canonical_shared_bytes,
                "logical_media_assets_bytes": logical_assets_bytes,
                "generated_video_bytes": cat.get("shorts", 0),
                "rendered_exports_bytes": cat.get("exports", 0),
                "extracted_audio_bytes": extracted_audio_bytes,
                "keyframes_and_thumbnails_bytes": keyframes_and_thumbnails_bytes,
                "transcripts_and_analysis_bytes": cat.get("analysis", 0),
                "temporary_uploads_bytes": temporary_uploads_bytes,
                "temporary_rendering_bytes": temporary_rendering_bytes,
                "database_and_backups_bytes": database_and_backups_bytes,
                "proxies_bytes": cat.get("proxies", 0),
                "logs_bytes": cat.get("logs", 0),
                "characters_bytes": cat.get("characters", 0),
                "timelines_bytes": cat.get("timelines", 0),
                "temp_cache_bytes": cat.get("temp", 0),
                # Legacy aliases for backward compatibility
                "extracted_frames_bytes": cat.get("analysis", 0),
                "exports_bytes": cat.get("exports", 0),
                "database_bytes": cat.get("db", 0),
                "backups_bytes": cat.get("backups", 0),
                "thumbnails_bytes": cat.get("thumbnails", 0),
            },
            "directories": stats["directories"],
            "quota_status": quota_status_res.model_dump() if quota_status_res else None,
        }

    def get_storage_quotas(self) -> StorageQuotaSettingsDTO:
        """Fetch current quota settings from storage_quotas table."""
        if self.layout.db_file.exists():
            try:
                with sqlite_session(self.layout.db_file) as conn:
                    row = conn.execute("SELECT * FROM storage_quotas WHERE id = 'default'").fetchone()
                    if row:
                        cats = json.loads(row["auto_prune_categories_json"]) if row["auto_prune_categories_json"] else []
                        return StorageQuotaSettingsDTO(
                            id=row["id"],
                            storage_limit_bytes=row["storage_limit_bytes"],
                            generated_video_limit_bytes=row["generated_video_limit_bytes"],
                            temp_storage_limit_bytes=row["temp_storage_limit_bytes"],
                            warning_threshold_percent=row["warning_threshold_percent"],
                            auto_prune_enabled=bool(row["auto_prune_enabled"]),
                            auto_prune_retention_hours=row["auto_prune_retention_hours"],
                            auto_prune_categories=cats,
                            max_temp_storage_bytes=row["max_temp_storage_bytes"],
                            updated_at=row["updated_at"],
                        )
            except Exception as exc:
                logger.warning("Could not fetch storage quotas: %s", exc)

        return StorageQuotaSettingsDTO()

    def update_storage_quotas(self, updates: StorageQuotaUpdateRequest) -> StorageQuotaSettingsDTO:
        """Update persistent quota settings with strict validation."""
        if updates.storage_limit_bytes is not None and updates.storage_limit_bytes <= 0:
            raise AppError(code="INVALID_QUOTA_LIMIT", message="Storage limit must be greater than 0 bytes.", status_code=400)
        if updates.generated_video_limit_bytes is not None and updates.generated_video_limit_bytes <= 0:
            raise AppError(code="INVALID_QUOTA_LIMIT", message="Generated video storage limit must be greater than 0 bytes.", status_code=400)
        if updates.temp_storage_limit_bytes is not None and updates.temp_storage_limit_bytes <= 0:
            raise AppError(code="INVALID_QUOTA_LIMIT", message="Temporary storage limit must be greater than 0 bytes.", status_code=400)
        if updates.warning_threshold_percent is not None and not (50 <= updates.warning_threshold_percent <= 100):
            raise AppError(code="INVALID_WARNING_THRESHOLD", message="Warning threshold percent must be between 50 and 100.", status_code=400)
        if updates.auto_prune_retention_hours is not None and updates.auto_prune_retention_hours < 1:
            raise AppError(code="INVALID_RETENTION_PERIOD", message="Auto-prune retention period must be at least 1 hour.", status_code=400)

        current = self.get_storage_quotas()
        new_storage_limit = updates.storage_limit_bytes if updates.storage_limit_bytes is not None else current.storage_limit_bytes
        new_gen_limit = updates.generated_video_limit_bytes if updates.generated_video_limit_bytes is not None else current.generated_video_limit_bytes
        new_temp_limit = updates.temp_storage_limit_bytes if updates.temp_storage_limit_bytes is not None else current.temp_storage_limit_bytes
        new_thresh = updates.warning_threshold_percent if updates.warning_threshold_percent is not None else current.warning_threshold_percent
        new_auto_prune = updates.auto_prune_enabled if updates.auto_prune_enabled is not None else current.auto_prune_enabled
        new_retention = updates.auto_prune_retention_hours if updates.auto_prune_retention_hours is not None else current.auto_prune_retention_hours
        new_cats = updates.auto_prune_categories if updates.auto_prune_categories is not None else current.auto_prune_categories
        new_max_temp = updates.max_temp_storage_bytes if updates.max_temp_storage_bytes is not None else current.max_temp_storage_bytes
        now_iso = datetime.now(timezone.utc).isoformat()

        if self.layout.db_file.exists():
            with sqlite_session(self.layout.db_file) as conn:
                conn.execute(
                    """
                    INSERT INTO storage_quotas (
                        id, storage_limit_bytes, generated_video_limit_bytes, temp_storage_limit_bytes,
                        warning_threshold_percent, auto_prune_enabled, auto_prune_retention_hours,
                        auto_prune_categories_json, max_temp_storage_bytes, created_at, updated_at
                    ) VALUES ('default', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        storage_limit_bytes = excluded.storage_limit_bytes,
                        generated_video_limit_bytes = excluded.generated_video_limit_bytes,
                        temp_storage_limit_bytes = excluded.temp_storage_limit_bytes,
                        warning_threshold_percent = excluded.warning_threshold_percent,
                        auto_prune_enabled = excluded.auto_prune_enabled,
                        auto_prune_retention_hours = excluded.auto_prune_retention_hours,
                        auto_prune_categories_json = excluded.auto_prune_categories_json,
                        max_temp_storage_bytes = excluded.max_temp_storage_bytes,
                        updated_at = excluded.updated_at
                    """,
                    (
                        new_storage_limit,
                        new_gen_limit,
                        new_temp_limit,
                        new_thresh,
                        1 if new_auto_prune else 0,
                        new_retention,
                        json.dumps(new_cats),
                        new_max_temp,
                        now_iso,
                        now_iso,
                    ),
                )

        return self.get_storage_quotas()

    def get_storage_quota_status(self) -> StorageQuotaStatusResponse:
        """Evaluate current storage quota utilization and warning thresholds."""
        quotas = self.get_storage_quotas()
        stats = self.inspect_storage()
        cat = stats["category_sizes_bytes"]
        total_usage = stats.get("total_managed_bytes", sum(cat.values()))

        gen_usage = cat.get("shorts", 0) + cat.get("exports", 0)
        temp_usage = cat.get("temp", 0)

        total_pct = round((total_usage / quotas.storage_limit_bytes) * 100.0, 1) if quotas.storage_limit_bytes else None
        gen_pct = round((gen_usage / quotas.generated_video_limit_bytes) * 100.0, 1) if quotas.generated_video_limit_bytes else None
        temp_pct = round((temp_usage / quotas.temp_storage_limit_bytes) * 100.0, 1) if quotas.temp_storage_limit_bytes else None

        warning_reasons = []
        is_warning = False
        is_exceeded = False

        thresh = quotas.warning_threshold_percent
        if total_pct is not None:
            if total_pct >= 100.0:
                is_exceeded = True
                warning_reasons.append(f"Overall storage quota exceeded ({total_pct}% used of {self.format_bytes(quotas.storage_limit_bytes)})")
            elif total_pct >= thresh:
                is_warning = True
                warning_reasons.append(f"Overall storage nearing quota limit ({total_pct}% used)")

        if gen_pct is not None:
            if gen_pct >= 100.0:
                is_exceeded = True
                warning_reasons.append(f"Generated video storage quota exceeded ({gen_pct}% used of {self.format_bytes(quotas.generated_video_limit_bytes)})")
            elif gen_pct >= thresh:
                is_warning = True
                warning_reasons.append(f"Generated video storage nearing quota limit ({gen_pct}% used)")

        if temp_pct is not None:
            if temp_pct >= 100.0:
                is_exceeded = True
                warning_reasons.append(f"Temporary storage quota exceeded ({temp_pct}% used of {self.format_bytes(quotas.temp_storage_limit_bytes)})")
            elif temp_pct >= thresh:
                is_warning = True
                warning_reasons.append(f"Temporary storage nearing quota limit ({temp_pct}% used)")

        return StorageQuotaStatusResponse(
            quota_settings=quotas,
            total_usage_bytes=total_usage,
            total_utilization_pct=total_pct,
            generated_video_usage_bytes=gen_usage,
            generated_video_utilization_pct=gen_pct,
            temp_storage_usage_bytes=temp_usage,
            temp_storage_utilization_pct=temp_pct,
            is_warning=is_warning or is_exceeded,
            is_exceeded=is_exceeded,
            warning_reasons=warning_reasons,
        )

    def check_quota_for_operation(self, category: str, incoming_bytes: int = 0) -> Tuple[bool, Optional[str]]:
        """Check if an incoming operation would breach configured hard quotas."""
        quotas = self.get_storage_quotas()
        if (
            not quotas.storage_limit_bytes
            and not (category == "generated_video" and quotas.generated_video_limit_bytes)
            and not (category in ("temp", "upload") and quotas.temp_storage_limit_bytes)
        ):
            return True, None

        status = self.get_storage_quota_status()

        if quotas.storage_limit_bytes:
            if status.total_usage_bytes + incoming_bytes > quotas.storage_limit_bytes:
                return False, f"OVERALL_QUOTA_EXCEEDED: Operation requiring {self.format_bytes(incoming_bytes)} would exceed overall storage quota of {self.format_bytes(quotas.storage_limit_bytes)} (current usage: {self.format_bytes(status.total_usage_bytes)})."

        if category == "generated_video" and quotas.generated_video_limit_bytes:
            if status.generated_video_usage_bytes + incoming_bytes > quotas.generated_video_limit_bytes:
                return False, f"GENERATED_VIDEO_QUOTA_EXCEEDED: Operation requiring {self.format_bytes(incoming_bytes)} would exceed generated video quota of {self.format_bytes(quotas.generated_video_limit_bytes)} (current usage: {self.format_bytes(status.generated_video_usage_bytes)})."

        if category in ("temp", "upload") and quotas.temp_storage_limit_bytes:
            if status.temp_storage_usage_bytes + incoming_bytes > quotas.temp_storage_limit_bytes:
                return False, f"TEMP_STORAGE_QUOTA_EXCEEDED: Operation requiring {self.format_bytes(incoming_bytes)} would exceed temporary storage quota of {self.format_bytes(quotas.temp_storage_limit_bytes)} (current usage: {self.format_bytes(status.temp_storage_usage_bytes)})."

        return True, None

    def preview_maintenance_cleanup(self, category_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """Scan disposable temporary files, abandoned renders, and orphaned uploads without deleting anything."""
        candidates: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        root_resolved = self.layout.root.resolve()

        # Discover active background jobs from SQLite to protect in-flight job files
        active_job_ids = set()
        if self.layout.db_file.exists():
            try:
                with sqlite_session(self.layout.db_file) as conn:
                    cursor = conn.cursor()
                    tables = {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                    if "jobs" in tables:
                        rows = cursor.execute("SELECT id FROM jobs WHERE status IN ('running', 'queued', 'cancelling')").fetchall()
                        active_job_ids = {r[0] for r in rows}
            except Exception as exc:
                logger.warning("Could not gather active jobs for preview: %s", exc)

        def make_candidate(f: Path, cat: str, reason: str, job_id: Optional[str] = None, is_blocked: bool = False, protection_reason: Optional[str] = None):
            try:
                res_path = f.resolve()
                if not res_path.is_relative_to(root_resolved):
                    return None
                rel = f.relative_to(self.layout.root)
                sz = f.stat().st_size if f.is_file() else 0
                mtime_iso = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()
                cand_id = f"cand_{hashlib.sha256(str(rel.as_posix()).encode()).hexdigest()[:12]}"
                return {
                    "candidate_id": cand_id,
                    "relative_path": str(rel.as_posix()),
                    "category": cat,
                    "size_bytes": sz,
                    "reason": reason,
                    "last_modified_at": mtime_iso,
                    "associated_project_id": None,
                    "associated_job_id": job_id,
                    "is_blocked": is_blocked,
                    "protection_reason": protection_reason,
                }
            except Exception:
                return None

        # 1. Orphaned uploads (.uploading and .part files)
        for pattern in ("**/*.uploading", "**/*.part"):
            if self.layout.media.exists():
                for f in self.layout.media.glob(pattern):
                    if f.is_file():
                        age_sec = (now.timestamp() - f.stat().st_mtime) if f.exists() else 0
                        is_locked = age_sec < 60.0
                        cand = make_candidate(
                            f,
                            "orphaned_uploads",
                            "Abandoned in-flight upload part file from interrupted/cancelled session",
                            is_blocked=is_locked,
                            protection_reason="File recently updated; may be an in-flight upload" if is_locked else None,
                        )
                        if cand:
                            candidates.append(cand)
            if self.layout.temp.exists():
                for f in self.layout.temp.glob(pattern):
                    if f.is_file():
                        age_sec = (now.timestamp() - f.stat().st_mtime) if f.exists() else 0
                        is_locked = age_sec < 60.0
                        cand = make_candidate(
                            f,
                            "orphaned_uploads",
                            "Staged upload chunk file in temporary upload storage",
                            is_blocked=is_locked,
                            protection_reason="File recently modified (< 60s); protecting active upload" if is_locked else None,
                        )
                        if cand:
                            candidates.append(cand)

        # 2. Abandoned FFmpeg temp renders (temp/job_* directories and scratch files)
        if self.layout.temp.exists():
            for item in self.layout.temp.iterdir():
                if item.is_dir() and item.name.startswith("job_"):
                    job_id = item.name.removeprefix("job_")
                    is_active = job_id in active_job_ids
                    for sub_f in item.rglob("*"):
                        if sub_f.is_file() and not sub_f.is_symlink():
                            cand = make_candidate(
                                sub_f,
                                "abandoned_ffmpeg",
                                f"Temporary render scratch file from job '{job_id}'",
                                job_id=job_id,
                                is_blocked=is_active,
                                protection_reason=f"File is in active use by running background job '{job_id}'" if is_active else None,
                            )
                            if cand:
                                candidates.append(cand)
                elif item.is_file() and not item.is_symlink() and not item.name.endswith((".uploading", ".part")):
                    if item.name in ("render_scratch.mp4", "captions.ass") or item.name.startswith("ffmpeg_"):
                        cand = make_candidate(
                            item,
                            "abandoned_ffmpeg",
                            "Orphaned FFmpeg render scratch output",
                        )
                        if cand:
                            candidates.append(cand)

        # 3. Failed render outputs (*.part in exports)
        if self.layout.exports.exists():
            for f in self.layout.exports.glob("*.part"):
                if f.is_file():
                    cand = make_candidate(
                        f,
                        "failed_renders",
                        "Incomplete render output from interrupted export job",
                    )
                    if cand:
                        candidates.append(cand)

        # 4. Expired temporary files in temp/
        if self.layout.temp.exists():
            for f in self.layout.temp.glob("*"):
                if f.is_file() and not f.is_symlink() and not f.name.endswith((".uploading", ".part", ".pid", ".json")):
                    if f.name not in ("render_scratch.mp4", "captions.ass", "zezedit.pid", "zezedit_process.json"):
                        age_hours = (now.timestamp() - f.stat().st_mtime) / 3600.0
                        if age_hours > 0.5:
                            cand = make_candidate(
                                f,
                                "expired_temp_files",
                                f"Expired temporary workspace file ({age_hours:.1f} hours old)",
                            )
                            if cand:
                                candidates.append(cand)

        # Filter by categories if requested
        if category_filter:
            cat_set = set(category_filter)
            candidates = [c for c in candidates if c["category"] in cat_set]

        # Deduplicate candidates by candidate_id
        seen_cands = set()
        unique_candidates = []
        for c in candidates:
            if c["candidate_id"] not in seen_cands:
                seen_cands.add(c["candidate_id"])
                unique_candidates.append(c)

        eligible_count = sum(1 for c in unique_candidates if not c["is_blocked"])
        total_eligible_bytes = sum(c["size_bytes"] for c in unique_candidates if not c["is_blocked"])
        blocked_count = sum(1 for c in unique_candidates if c["is_blocked"])
        total_blocked_bytes = sum(c["size_bytes"] for c in unique_candidates if c["is_blocked"])

        cat_summary: Dict[str, Dict[str, int]] = {}
        for c in unique_candidates:
            cat_name = c["category"]
            if cat_name not in cat_summary:
                cat_summary[cat_name] = {"count": 0, "bytes": 0}
            cat_summary[cat_name]["count"] += 1
            cat_summary[cat_name]["bytes"] += c["size_bytes"]

        preview_id = f"prev_{hashlib.sha256(f'{len(unique_candidates)}_{total_eligible_bytes}_{now_iso}'.encode()).hexdigest()[:12]}"

        return {
            "preview_id": preview_id,
            "total_candidates": len(unique_candidates),
            "eligible_candidates_count": eligible_count,
            "total_eligible_bytes": total_eligible_bytes,
            "blocked_candidates_count": blocked_count,
            "total_blocked_bytes": total_blocked_bytes,
            "categories_summary": cat_summary,
            "candidates": unique_candidates,
            "protected_categories": [
                "Original source videos (media/)",
                "Shared canonical media files with active references (stored_media_files)",
                "Active background rendering jobs and in-flight uploads",
                "Completed user exports (exports/*.mp4)",
                "Database files and recovery snapshots (db/, backups/)",
            ],
            "generated_at": now_iso,
        }

    def execute_maintenance_cleanup(
        self,
        candidate_ids: Optional[List[str]] = None,
        selected_categories: Optional[List[str]] = None,
        is_automatic: bool = False,
    ) -> Dict[str, Any]:
        """Execute safe deletion of verified candidate files with audit logging."""
        with _CLEANUP_LOCK:
            now_iso = datetime.now(timezone.utc).isoformat()
            operation_id = f"op_{uuid.uuid4().hex[:8]}"
            deleted_items: List[Dict[str, Any]] = []
            skipped_items: List[Dict[str, Any]] = []
            failed_items: List[Dict[str, Any]] = []
            total_reclaimed = 0

            # Always re-generate candidates at execution time to ensure revalidation
            preview = self.preview_maintenance_cleanup(category_filter=selected_categories)
            candidates = preview["candidates"]

            if candidate_ids:
                cand_id_set = set(candidate_ids)
                matched_candidates = []
                found_cand_ids = set()
                for c in candidates:
                    if c["candidate_id"] in cand_id_set:
                        matched_candidates.append(c)
                        found_cand_ids.add(c["candidate_id"])
                for missing_id in cand_id_set - found_cand_ids:
                    skipped_items.append({
                        "candidate_id": missing_id,
                        "path": "unknown / vanished",
                        "reason": "File no longer exists or became ineligible prior to execution",
                    })
                candidates = matched_candidates

            # Gather set of protected paths from database to double-check
            protected_db_paths: Set[str] = set()
            active_db_jobs: Set[str] = set()
            if self.layout.db_file.exists():
                try:
                    with sqlite_session(self.layout.db_file) as conn:
                        cursor = conn.cursor()
                        tables = {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                        if "stored_media_files" in tables:
                            rows = cursor.execute("SELECT storage_path FROM stored_media_files WHERE reference_count > 0").fetchall()
                            for r in rows:
                                if r[0]:
                                    try:
                                        protected_db_paths.add(str(Path(r[0]).resolve()))
                                    except Exception:
                                        pass
                        if "media_assets" in tables:
                            rows = cursor.execute("SELECT storage_path FROM media_assets WHERE availability_status != 'deleted'").fetchall()
                            for r in rows:
                                if r[0]:
                                    try:
                                        protected_db_paths.add(str(Path(r[0]).resolve()))
                                    except Exception:
                                        pass
                        if "jobs" in tables:
                            rows = cursor.execute("SELECT id FROM jobs WHERE status IN ('running', 'queued', 'cancelling')").fetchall()
                            active_db_jobs = {r[0] for r in rows}
                except Exception as exc:
                    logger.warning("Could not query database protection tables during cleanup: %s", exc)

            root_resolved = self.layout.root.resolve()

            for c in candidates:
                rel_p = c["relative_path"]

                # 1. Check if candidate was marked blocked during preview
                if c.get("is_blocked"):
                    skipped_items.append({
                        "candidate_id": c["candidate_id"],
                        "path": rel_p,
                        "reason": c.get("protection_reason") or "File is blocked by active process/job",
                    })
                    continue

                # 2. Check if associated job became active
                if c.get("associated_job_id") in active_db_jobs:
                    skipped_items.append({
                        "candidate_id": c["candidate_id"],
                        "path": rel_p,
                        "reason": f"Associated job '{c['associated_job_id']}' is active",
                    })
                    continue

                # 3. Resolve path safely within storage root
                try:
                    target_path = resolve_contained_path(self.layout.root, rel_p)
                except Exception as path_err:
                    skipped_items.append({
                        "candidate_id": c["candidate_id"],
                        "path": rel_p,
                        "reason": f"Path traversal / security rejection: {path_err}",
                    })
                    continue

                # 4. Check existence and symlinks
                if not target_path.exists():
                    skipped_items.append({
                        "candidate_id": c["candidate_id"],
                        "path": rel_p,
                        "reason": "File no longer exists on disk",
                    })
                    continue

                if target_path.is_symlink() or os.path.islink(str(target_path)):
                    skipped_items.append({
                        "candidate_id": c["candidate_id"],
                        "path": rel_p,
                        "reason": "Security rejection: symlink detected",
                    })
                    continue

                # 5. Check if target_path matches any protected database asset
                try:
                    target_resolved = str(target_path.resolve())
                    if target_resolved in protected_db_paths:
                        skipped_items.append({
                            "candidate_id": c["candidate_id"],
                            "path": rel_p,
                            "reason": "Protection guard: path is an active database media asset or shared canonical file",
                        })
                        continue
                except Exception:
                    pass

                # 6. Safe deletion
                try:
                    if target_path.is_file():
                        sz = target_path.stat().st_size
                        try:
                            target_path.unlink(missing_ok=True)
                            deleted_items.append({
                                "candidate_id": c["candidate_id"],
                                "path": rel_p,
                                "category": c["category"],
                                "size_bytes": sz,
                            })
                            total_reclaimed += sz
                        except PermissionError:
                            gc.collect()
                            time.sleep(0.05)
                            target_path.unlink(missing_ok=True)
                            deleted_items.append({
                                "candidate_id": c["candidate_id"],
                                "path": rel_p,
                                "category": c["category"],
                                "size_bytes": sz,
                            })
                            total_reclaimed += sz
                    elif target_path.is_dir():
                        sz = sum(sub.stat().st_size for sub in target_path.rglob("*") if sub.is_file() and not sub.is_symlink())
                        shutil.rmtree(target_path, ignore_errors=True)
                        deleted_items.append({
                            "candidate_id": c["candidate_id"],
                            "path": rel_p,
                            "category": c["category"],
                            "size_bytes": sz,
                        })
                        total_reclaimed += sz
                except Exception as del_err:
                    logger.warning("Failed to delete candidate %s: %s", target_path, del_err)
                    failed_items.append({
                        "candidate_id": c["candidate_id"],
                        "path": rel_p,
                        "error": str(del_err),
                    })

            # Remove any newly empty directories in layout.temp
            if self.layout.temp.exists():
                for d in list(self.layout.temp.iterdir()):
                    if d.is_dir() and d.name.startswith("job_"):
                        try:
                            if not any(d.iterdir()):
                                d.rmdir()
                        except Exception:
                            pass

            # 7. Record cleanup audit record in SQLite
            audit_id = f"cln_audit_{uuid.uuid4().hex[:12]}"
            cleanup_cat = ", ".join(selected_categories) if selected_categories else (", ".join(sorted({item["category"] for item in deleted_items})) if deleted_items else "all_eligible")
            if self.layout.db_file.exists():
                try:
                    with sqlite_session(self.layout.db_file) as conn:
                        conn.execute(
                            """
                            INSERT INTO storage_cleanup_audits (
                                id, operation_id, timestamp, cleanup_category,
                                files_examined, files_deleted, files_skipped,
                                bytes_reclaimed, is_automatic, failure_reasons_json,
                                details_json, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                audit_id,
                                operation_id,
                                now_iso,
                                cleanup_cat,
                                len(candidates),
                                len(deleted_items),
                                len(skipped_items) + len(failed_items),
                                total_reclaimed,
                                1 if is_automatic else 0,
                                json.dumps(failed_items),
                                json.dumps({
                                    "deleted_count": len(deleted_items),
                                    "skipped_count": len(skipped_items),
                                    "failed_count": len(failed_items),
                                }),
                                now_iso,
                            ),
                        )
                except Exception as audit_err:
                    logger.warning("Could not persist cleanup audit log: %s", audit_err)

            logger.info(
                "Executed maintenance cleanup: %d deleted (%d bytes), %d skipped, %d failed",
                len(deleted_items),
                total_reclaimed,
                len(skipped_items),
                len(failed_items),
            )

            return {
                "status": "success",
                "operation_id": operation_id,
                "deleted_count": len(deleted_items),
                "bytes_reclaimed": total_reclaimed,
                "skipped_count": len(skipped_items),
                "failed_count": len(failed_items),
                "deleted_items": deleted_items,
                "skipped_items": skipped_items,
                "failed_items": failed_items,
                "executed_at": now_iso,
            }

    def execute_auto_prune(self, force: bool = False) -> Dict[str, Any]:
        """Run automated cleanup of eligible temporary/staging files respecting retention policies."""
        quotas = self.get_storage_quotas()
        if not quotas.auto_prune_enabled and not force:
            return {
                "executed": False,
                "reason": "Automatic pruning is disabled by default for user data safety. Enable it in Quota Settings.",
            }

        preview = self.preview_maintenance_cleanup(category_filter=quotas.auto_prune_categories)
        now = datetime.now(timezone.utc)
        retention_seconds = quotas.auto_prune_retention_hours * 3600

        eligible_cand_ids = []
        for c in preview["candidates"]:
            if c.get("is_blocked"):
                continue
            try:
                mtime = datetime.fromisoformat(c["last_modified_at"])
                age = now.timestamp() - mtime.timestamp()
                if age >= retention_seconds:
                    eligible_cand_ids.append(c["candidate_id"])
            except Exception:
                eligible_cand_ids.append(c["candidate_id"])

        if not eligible_cand_ids:
            return {
                "executed": True,
                "message": f"No temporary files exceeded the retention threshold of {quotas.auto_prune_retention_hours} hours.",
                "deleted_count": 0,
                "bytes_reclaimed": 0,
            }

        res = self.execute_maintenance_cleanup(
            candidate_ids=eligible_cand_ids,
            selected_categories=quotas.auto_prune_categories,
            is_automatic=True,
        )
        res["executed"] = True
        return res

    def recover_stale_artifacts(self) -> Dict[str, Any]:
        """Identify and safely recover from interrupted uploads, abandoned render staging, and app crashes."""
        recovered_files_count = 0
        bytes_reclaimed = 0
        now = datetime.now(timezone.utc)

        # 1. Recover incomplete upload parts (.uploading, .part) older than 2 minutes
        for pattern in ("**/*.uploading", "**/*.part"):
            for root_dir in (self.layout.temp, self.layout.media):
                if root_dir.exists():
                    for f in root_dir.glob(pattern):
                        if f.is_file():
                            try:
                                age = now.timestamp() - f.stat().st_mtime
                                if age > 120.0:
                                    sz = f.stat().st_size
                                    f.unlink(missing_ok=True)
                                    recovered_files_count += 1
                                    bytes_reclaimed += sz
                            except Exception as exc:
                                logger.warning("Could not recover stale part %s: %s", f, exc)

        # 2. Recover abandoned job render directories for finished/interrupted jobs
        if self.layout.temp.exists():
            for item in self.layout.temp.iterdir():
                if item.is_dir() and item.name.startswith("job_"):
                    job_id = item.name.removeprefix("job_")
                    is_active = False
                    if self.layout.db_file.exists():
                        try:
                            with sqlite_session(self.layout.db_file) as conn:
                                row = conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
                                if row and row["status"] in ("running", "queued", "cancelling"):
                                    is_active = True
                        except Exception:
                            pass
                    if not is_active:
                        try:
                            sz = sum(sub.stat().st_size for sub in item.rglob("*") if sub.is_file() and not sub.is_symlink())
                            shutil.rmtree(item, ignore_errors=True)
                            recovered_files_count += 1
                            bytes_reclaimed += sz
                        except Exception as exc:
                            logger.warning("Could not recover abandoned job dir %s: %s", item, exc)

        # 3. Check database consistency: inspect missing media
        missing_media_count = 0
        if self.layout.db_file.exists():
            try:
                with sqlite_session(self.layout.db_file) as conn:
                    rows = conn.execute("SELECT id, storage_path FROM media_assets WHERE availability_status != 'deleted'").fetchall()
                    for r in rows:
                        if r["storage_path"] and not Path(r["storage_path"]).exists():
                            missing_media_count += 1
            except Exception:
                pass

        return {
            "status": "success",
            "recovered_files_count": recovered_files_count,
            "bytes_reclaimed": bytes_reclaimed,
            "formatted_bytes_reclaimed": self.format_bytes(bytes_reclaimed),
            "missing_media_detected": missing_media_count,
            "timestamp": now.isoformat(),
        }

    def get_cleanup_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Return recent cleanup audit logs from SQLite."""
        if not self.layout.db_file.exists():
            return []
        try:
            with sqlite_session(self.layout.db_file) as conn:
                rows = conn.execute(
                    """
                    SELECT id, operation_id, timestamp, cleanup_category,
                           files_examined, files_deleted, files_skipped,
                           bytes_reclaimed, is_automatic, failure_reasons_json, details_json
                    FROM storage_cleanup_audits
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
                results = []
                for r in rows:
                    results.append({
                        "id": r["id"],
                        "operation_id": r["operation_id"],
                        "timestamp": r["timestamp"],
                        "cleanup_category": r["cleanup_category"],
                        "files_examined": r["files_examined"],
                        "files_deleted": r["files_deleted"],
                        "files_skipped": r["files_skipped"],
                        "bytes_reclaimed": r["bytes_reclaimed"],
                        "is_automatic": bool(r["is_automatic"]),
                        "failure_reasons": json.loads(r["failure_reasons_json"]) if r["failure_reasons_json"] else [],
                        "details": json.loads(r["details_json"]) if r["details_json"] else {},
                    })
                return results
        except Exception as exc:
            logger.warning("Could not read cleanup history: %s", exc)
            return []


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
