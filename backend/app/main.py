"""FastAPI application entrypoint and Windows lifecycle manager."""

import json
import logging
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from app.api.v1 import api_v1_router
from app.api.v1.health import get_health
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.schemas.health import HealthResponse

logger = logging.getLogger("zezedit.main")


class LargeUploadPreflightMiddleware:
    """Pre-flight size and disk-space enforcement middleware for large video uploads (P1.3)."""

    def __init__(self, app, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if "/media/upload" in path or "/media/batch-upload" in path:
                headers = dict(scope.get("headers", []))
                content_length_raw = headers.get(b"content-length")
                if content_length_raw is not None:
                    try:
                        content_length = int(content_length_raw.decode("latin-1").strip())
                        if content_length < 0:
                            res = JSONResponse(
                                status_code=400,
                                content={
                                    "error": {
                                        "code": "INVALID_CONTENT_LENGTH",
                                        "message": "Malformed Content-Length header: must be a non-negative integer.",
                                    }
                                },
                            )
                            await res(scope, receive, send)
                            return

                        max_limit = getattr(self.settings, "max_upload_size_bytes", 2500 * 1024 * 1024)
                        if content_length > max_limit:
                            res = JSONResponse(
                                status_code=413,
                                content={
                                    "error": {
                                        "code": "REQUEST_ENTITY_TOO_LARGE",
                                        "message": f"Upload size ({content_length / (1024 * 1024):.1f} MB) exceeds maximum permitted limit of {max_limit / (1024 * 1024):.1f} MB.",
                                    }
                                },
                            )
                            await res(scope, receive, send)
                            return

                        # Pre-flight check on available storage volume free space
                        try:
                            usage = shutil.disk_usage(self.settings.storage_root)
                            min_free = getattr(self.settings, "min_disk_free_bytes", 500 * 1024 * 1024)
                            if usage.free < (content_length + min_free):
                                res = JSONResponse(
                                    status_code=507,
                                    content={
                                        "error": {
                                            "code": "INSUFFICIENT_STORAGE",
                                            "message": f"Insufficient disk space for upload. Available: {usage.free / (1024 * 1024):.1f} MB, required: {(content_length + min_free) / (1024 * 1024):.1f} MB.",
                                        }
                                    },
                                )
                                await res(scope, receive, send)
                                return

                            # Pre-flight check on configured storage quotas (P1.9)
                            try:
                                from app.services.storage import StorageService
                                storage_svc = StorageService(self.settings)
                                allowed, quota_err = storage_svc.check_quota_for_operation("upload", incoming_bytes=content_length)
                                if not allowed and quota_err:
                                    res = JSONResponse(
                                        status_code=507,
                                        content={
                                            "error": {
                                                "code": "QUOTA_EXCEEDED",
                                                "message": quota_err,
                                            }
                                        },
                                    )
                                    await res(scope, receive, send)
                                    return
                            except Exception:
                                pass
                        except OSError:
                            pass
                    except (ValueError, UnicodeDecodeError):
                        res = JSONResponse(
                            status_code=400,
                            content={
                                "error": {
                                    "code": "INVALID_CONTENT_LENGTH",
                                    "message": "Malformed Content-Length header: must be a valid integer.",
                                }
                            },
                        )
                        await res(scope, receive, send)
                        return

        await self.app(scope, receive, send)


def create_app(settings_override: Optional[Settings] = None) -> FastAPI:
    """Create and configure the ZezEdit FastAPI application."""
    settings = settings_override or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        layout = StorageLayout.from_root(settings.storage_root)
        layout.ensure_directories()

        # Setup managed upload temp directory inside storage_root (P1.3)
        uploads_temp_dir = layout.temp / "uploads"
        uploads_temp_dir.mkdir(parents=True, exist_ok=True)
        # Purge any stale abandoned partial uploads from prior crashed runs
        for stale in uploads_temp_dir.glob("*"):
            try:
                if stale.is_file():
                    stale.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("Could not clean stale upload file %s: %s", stale, exc)

        # Purge any stale in-flight .uploading or .part files across media and temp (P1.4 / P1.5)
        # Safely cleans abandoned partial uploads from crashed runs; skips any locked files
        for pattern in ("**/*.uploading", "**/*.part"):
            for stale in layout.media.glob(pattern):
                try:
                    if stale.is_file():
                        stale.unlink(missing_ok=True)
                        logger.info("Purged stale partial upload: %s", stale)
                except PermissionError:
                    logger.debug("Skipping active/locked partial upload file: %s", stale)
                except Exception as exc:
                    logger.warning("Could not sweep stale partial upload %s: %s", stale, exc)
            for stale in layout.temp.glob(pattern):
                try:
                    if stale.is_file():
                        stale.unlink(missing_ok=True)
                except PermissionError:
                    pass
                except Exception:
                    pass

        configure_logging(log_level=settings.log_level, log_dir=layout.logs)
        logger.info("Starting %s %s (%s)", settings.app_name, settings.app_version, settings.environment)
        logger.info("Validated storage root: %s", layout.root)

        migration_result = run_migrations(
            db_path=layout.db_file,
            migrations_dir=settings.migrations_dir,
            backup_dir=layout.backups,
        )
        logger.info(
            "SQLite ready at %s (migration version=%s)",
            layout.db_file,
            migration_result.current_version,
        )

        # Detect and recover any jobs left in-flight from an unclean shutdown
        from app.services.jobs import JobOrchestrator
        orch_startup = JobOrchestrator(settings=settings, db_path=layout.db_file)
        recovered = orch_startup.recover_interrupted_jobs()
        if recovered:
            logger.warning("Recovered %d interrupted job(s) on startup: %s", len(recovered), recovered)
        try:
            orch_startup.dispatch_queued_jobs()
        except Exception as exc:
            logger.warning("Startup queue dispatch failed: %s", exc)

        app.state.settings = settings
        app.state.storage = layout
        app.state.migration_result = migration_result
        app.state.dispatcher_initialized = True
        app.state.starting = False
        app.state.ready = True

        pid_file = layout.temp / "zezedit.pid"
        meta_file = layout.temp / "zezedit_process.json"
        try:
            pid_file.write_text(str(os.getpid()), encoding="utf-8")
            meta = {
                "pid": os.getpid(),
                "project_root": str(settings.storage_root.parent if settings.storage_root.name == "storage" else settings.storage_root),
                "storage_root": str(settings.storage_root),
                "port": 8000,
                "host": "127.0.0.1",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "role": "production_server",
                "version": settings.app_version,
            }
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception:
            pass

        # Ensure catch-all SPA routes are evaluated after all API routes
        app.router.routes.sort(key=lambda r: 1 if getattr(r, "path", "") == "/{full_path:path}" else 0)

        import asyncio

        async def _queue_poller():
            orch = JobOrchestrator(settings=settings, db_path=layout.db_file)
            while True:
                try:
                    await asyncio.sleep(2.0)
                    orch.dispatch_queued_jobs()
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug("Queue poller tick exception: %s", exc)

        poller_task = asyncio.create_task(_queue_poller())

        yield

        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass

        try:
            if pid_file.exists():
                pid_file.unlink(missing_ok=True)
            if meta_file.exists():
                meta_file.unlink(missing_ok=True)
        except Exception:
            pass

        app.state.ready = False
        logger.info("Shutting down %s gracefully.", settings.app_name)

    app = FastAPI(
        title="ZezEdit 2.0 API",
        version=settings.app_version,
        description="Local-first AI video editor backend foundation",
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.storage = StorageLayout.from_root(settings.storage_root)
    app.state.starting = True
    app.state.ready = False
    app.state.dispatcher_initialized = True

    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LargeUploadPreflightMiddleware, settings=settings)

    app.include_router(api_v1_router, prefix="/api/v1")

    # Authoritative root-level health endpoint
    app.add_api_route(
        "/health",
        get_health,
        methods=["GET"],
        response_model=HealthResponse,
        tags=["health"],
        summary="Startup & Runtime Readiness Health Check",
    )

    # Production frontend static & SPA fallback serving
    STATIC_EXTENSIONS = {
        ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
        ".css", ".scss", ".sass", ".less",
        ".map", ".json",
        ".ico", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".bmp", ".tiff",
        ".woff", ".woff2", ".ttf", ".eot", ".otf",
        ".mp4", ".webm", ".ogg", ".mp3", ".wav", ".flac", ".aac",
        ".wasm", ".webmanifest", ".xml", ".txt", ".pdf", ".zip", ".gz"
    }

    frontend_dist = getattr(settings, "frontend_dist_dir", None)
    if frontend_dist and frontend_dist.is_dir():
        assets_dir = frontend_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
        async def serve_spa_frontend(full_path: str):
            # Guard against directory traversal
            if ".." in full_path or "%2e%2e" in full_path.lower() or "\\" in full_path or "%5c" in full_path.lower():
                raise HTTPException(status_code=400, detail="Invalid path traversal sequence")

            clean_path = full_path.lstrip("/").lower()

            # Guard against sensitive file exposure
            if (
                clean_path.startswith(".")
                or "/." in clean_path
                or clean_path.endswith((".env", ".db", ".sqlite", ".py", ".log", ".bak", ".sh", ".bat", ".ps1"))
                or clean_path.startswith(("storage", "backend", "migrations"))
            ):
                raise HTTPException(status_code=403, detail="Access forbidden")

            # Never fallback for API or health routes
            if (
                clean_path == "api"
                or clean_path.startswith("api/")
                or clean_path == "health"
                or clean_path.startswith("health/")
                or clean_path == "docs"
                or clean_path.startswith("docs/")
                or clean_path == "openapi.json"
                or clean_path == "redoc"
            ):
                raise HTTPException(status_code=404, detail="Not Found")

            # Try direct file inside dist root (e.g. favicon.ico, robots.txt, vite.svg)
            if full_path:
                try:
                    resolved_dist = frontend_dist.resolve()
                    target_file = (frontend_dist / full_path).resolve()
                    if target_file.is_relative_to(resolved_dist) and target_file.is_file():
                        return FileResponse(target_file)
                except Exception:
                    pass

            # Missing assets (under assets/ or having a known static extension) return 404 rather than HTML
            ext = Path(full_path).suffix.lower()
            if clean_path.startswith("assets/") or ext in STATIC_EXTENSIONS:
                raise HTTPException(status_code=404, detail="Static asset not found")

            # SPA client-side routing fallback: serve index.html
            index_file = frontend_dist / "index.html"
            if index_file.is_file():
                return FileResponse(index_file, media_type="text/html")

            raise HTTPException(status_code=404, detail="Frontend production build not found")

        @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
        async def serve_spa_root():
            index_file = frontend_dist / "index.html"
            if index_file.is_file():
                return FileResponse(index_file, media_type="text/html")
            return {
                "app": settings.app_name,
                "version": settings.app_version,
                "status": "online",
                "message": "ZezEdit 2.0 backend API is running. Production frontend build not found at frontend/dist.",
                "health_url": "/health",
                "api_docs_url": "/docs",
            }
    else:
        @app.get("/", include_in_schema=False)
        async def serve_api_welcome():
            return {
                "app": settings.app_name,
                "version": settings.app_version,
                "status": "online",
                "message": "ZezEdit 2.0 backend API is running. Production frontend build not found at frontend/dist.",
                "health_url": "/health",
                "api_docs_url": "/docs",
            }

    # Ensure catch-all SPA routes are always evaluated after all API and static routes
    app.router.routes.sort(key=lambda r: 1 if getattr(r, "path", "") == "/{full_path:path}" else 0)

    return app


app = create_app()
