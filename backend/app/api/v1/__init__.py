"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.analysis import router as analysis_router
from app.api.v1.backups import router as backups_router
from app.api.v1.health import router as health_router
from app.api.v1.highlights import router as highlights_router
from app.api.v1.reframing import router as reframing_router
from app.api.v1.exports import router as exports_router
from app.api.v1.timeline import router as timeline_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.media import router as media_router
from app.api.v1.projects import router as projects_router
from app.api.v1.settings import router as settings_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(projects_router)
api_v1_router.include_router(media_router)
api_v1_router.include_router(analysis_router)
api_v1_router.include_router(highlights_router)
api_v1_router.include_router(reframing_router)
api_v1_router.include_router(exports_router)
api_v1_router.include_router(timeline_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(backups_router)
