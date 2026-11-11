"""Health check and system information endpoints (`/api/v1/health`, `/api/v1/system/info`)."""

import os
import platform
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.core.binaries import probe_media_binary
from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.integrations.ollama import OllamaProvider
from app.schemas.health import (
    DatabaseHealth,
    DependencyCheck,
    HealthResponse,
    OllamaHealth,
    StorageHealth,
    SystemInfoResponse,
)

router = APIRouter()


def _check_storage_writable(layout: StorageLayout) -> tuple[bool, bool]:
    buckets = (
        layout.root,
        layout.db,
        layout.media,
        layout.proxies,
        layout.thumbnails,
        layout.analysis,
        layout.timelines,
        layout.shorts,
        layout.exports,
        layout.temp,
        layout.backups,
        layout.logs,
    )
    buckets_ready = all(b.exists() and b.is_dir() for b in buckets)
    probe_file = layout.temp / ".health_write_probe"
    try:
        probe_file.write_text("ok", encoding="utf-8")
        probe_file.unlink(missing_ok=True)
        return True, buckets_ready
    except OSError:
        return False, buckets_ready


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> HealthResponse:
    """Report backend readiness, SQLite migration state, storage boundary, media binaries, and Ollama status."""
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )

    # Probe SQLite WAL + schema_migrations
    db_connected = False
    journal_mode = "unknown"
    applied_migrations: list[str] = []
    try:
        with sqlite_session(layout.db_file) as conn:
            journal_row = conn.execute("PRAGMA journal_mode;").fetchone()
            journal_mode = str(journal_row[0]) if journal_row else "unknown"
            rows = conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version ASC"
            ).fetchall()
            applied_migrations = [str(r["version"]) for r in rows]
            db_connected = True
    except Exception:
        db_connected = False

    writable, buckets_ready = _check_storage_writable(layout)

    ffmpeg_status = probe_media_binary("ffmpeg", settings.ffmpeg_path)
    ffprobe_status = probe_media_binary("ffprobe", settings.ffprobe_path)

    ollama_client = OllamaProvider(
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    ollama_probe = await ollama_client.probe_health()

    core_ok = db_connected and writable and buckets_ready
    media_ok = ffmpeg_status.available and ffprobe_status.available
    overall_status = "ready" if (core_ok and media_ok) else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=DatabaseHealth(
            connected=db_connected,
            path=str(layout.db_file),
            journal_mode=journal_mode,
            current_migration=applied_migrations[-1] if applied_migrations else None,
            applied_migrations=applied_migrations,
        ),
        storage=StorageHealth(
            root=str(layout.root),
            writable=writable,
            buckets_ready=buckets_ready,
        ),
        ffmpeg=DependencyCheck(
            available=ffmpeg_status.available,
            path_or_url=ffmpeg_status.path,
            version=ffmpeg_status.version,
            details=ffmpeg_status.details,
        ),
        ffprobe=DependencyCheck(
            available=ffprobe_status.available,
            path_or_url=ffprobe_status.path,
            version=ffprobe_status.version,
            details=ffprobe_status.details,
        ),
        ollama=OllamaHealth(
            reachable=ollama_probe.reachable,
            base_url=settings.ollama_base_url,
            installed_models=ollama_probe.models,
            details=ollama_probe.details,
        ),
    )


@router.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info(request: Request) -> SystemInfoResponse:
    """Return host platform and CPU-first worker constraint metadata."""
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return SystemInfoResponse(
        app_version=settings.app_version,
        os_platform=platform.platform(),
        python_version=platform.python_version(),
        cpu_count=os.cpu_count() or 1,
        execution_mode="cpu_first",
        max_concurrent_jobs=settings.max_concurrent_jobs,
        ffmpeg_threads=settings.ffmpeg_threads,
        storage_root=str(layout.root),
    )
