"""Persistent job management endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.schemas.core import (
    JobCreateRequest,
    JobListResponse,
    JobResponse,
)
from app.services.jobs import JobOrchestrator

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_orchestrator(request: Request) -> JobOrchestrator:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return JobOrchestrator(settings=settings, db_path=layout.db_file)


@router.post("", response_model=JobResponse, status_code=201)
def create_job(
    req: JobCreateRequest,
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> JobResponse:
    rec = service.create_job(
        job_type=req.job_type,
        project_id=req.project_id,
        priority=req.priority,
        input_config=req.input_config,
        max_attempts=req.max_attempts,
    )
    return JobResponse(**rec.__dict__)


@router.get("", response_model=JobListResponse)
def list_jobs(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> JobListResponse:
    items = service.list_jobs(project_id=project_id, status=status, limit=limit)
    return JobListResponse(
        items=[JobResponse(**r.__dict__) for r in items],
        total=len(items),
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> JobResponse:
    rec = service.get_job(job_id)
    return JobResponse(**rec.__dict__)


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: str,
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> JobResponse:
    rec = service.request_cancellation(job_id)
    return JobResponse(**rec.__dict__)


@router.post("/{job_id}/retry", response_model=JobResponse)
def retry_job(
    job_id: str,
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> JobResponse:
    rec = service.retry_job(job_id)
    return JobResponse(**rec.__dict__)
