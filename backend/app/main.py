"""FastAPI application entrypoint and Windows lifecycle manager."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_v1_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations

logger = logging.getLogger("zezedit.main")


def create_app(settings_override: Optional[Settings] = None) -> FastAPI:
    """Create and configure the ZezEdit FastAPI application."""
    settings = settings_override or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        layout = StorageLayout.from_root(settings.storage_root)
        layout.ensure_directories()

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
        recovered = JobOrchestrator(settings=settings, db_path=layout.db_file).recover_interrupted_jobs()
        if recovered:
            logger.warning("Recovered %d interrupted job(s) on startup: %s", len(recovered), recovered)

        app.state.settings = settings
        app.state.storage = layout
        app.state.migration_result = migration_result

        yield

        logger.info("Shutting down %s gracefully.", settings.app_name)

    app = FastAPI(
        title="ZezEdit 2.0 API",
        version=settings.app_version,
        description="Local-first AI video editor backend foundation",
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.storage = StorageLayout.from_root(settings.storage_root)

    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix="/api/v1")
    return app


app = create_app()
