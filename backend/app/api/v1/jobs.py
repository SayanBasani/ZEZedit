"""Persistent job management endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.schemas.core import (
    JobCreateRequest,
    JobListResponse,
    JobLogsResponse,
    JobResponse,
    QueueStatsResponse,
)
from app.services.jobs import JobOrchestrator

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_orchestrator(request: Request) -> JobOrchestrator:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return JobOrchestrator(settings=settings, db_path=layout.db_file)


@router.get("/stats", response_model=QueueStatsResponse)
def get_queue_stats(
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> QueueStatsResponse:
    """Return aggregated queue metrics for all background jobs."""
    stats = service.get_queue_stats()
    return QueueStatsResponse(**stats)


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


@router.get("/{job_id}/logs", response_model=JobLogsResponse)
def get_job_logs(
    job_id: str,
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> JobLogsResponse:
    """Return structured logs and execution timeline for a specific job."""
    logs_data = service.get_job_logs(job_id)
    return JobLogsResponse(**logs_data)


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


@router.get("/{job_id}/checkpoint")
def get_job_checkpoint(
    job_id: str,
    service: JobOrchestrator = Depends(get_job_orchestrator),
):
    """Return persistent execution checkpoint data if available for this job."""
    cp = service.get_checkpoint(job_id)
    return {"job_id": job_id, "has_checkpoint": cp is not None, "checkpoint": cp}
