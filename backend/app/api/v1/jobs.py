"""Persistent job and process management endpoints."""

from datetime import datetime, timezone
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
processes_router = APIRouter(prefix="/processes", tags=["processes"])


def get_job_orchestrator(request: Request) -> JobOrchestrator:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return JobOrchestrator(settings=settings, db_path=layout.db_file)


def _enrich_job_response(rec) -> JobResponse:
    d = dict(rec.__dict__)
    started = rec.started_at
    completed = rec.completed_at
    progress = rec.progress_pct or 0.0
    elapsed = None
    remaining = None
    if started:
        try:
            start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            if completed:
                end_dt = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            else:
                end_dt = datetime.now(timezone.utc)
            elapsed = round(max(0.0, (end_dt - start_dt).total_seconds()), 1)
            if rec.status == "running" and progress > 3.0 and progress < 99.0 and elapsed > 0:
                total_est = (elapsed / progress) * 100.0
                remaining = round(max(0.0, total_est - elapsed), 1)
        except Exception:
            pass
    d["elapsed_seconds"] = elapsed
    d["estimated_remaining_seconds"] = remaining
    return JobResponse(**d)


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
        media_asset_id=req.media_asset_id,
        priority=req.priority,
        input_config=req.input_config,
        max_attempts=req.max_attempts,
    )
    return _enrich_job_response(rec)


@router.get("", response_model=JobListResponse)
def list_jobs(
    project_id: Optional[str] = Query(None),
    media_asset_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> JobListResponse:
    items = service.list_jobs(
        project_id=project_id,
        media_asset_id=media_asset_id,
        status=status,
        job_type=job_type,
        search=search,
        limit=limit,
    )
    return JobListResponse(
        items=[_enrich_job_response(r) for r in items],
        total=len(items),
    )


@router.delete("/history")
def delete_jobs_history(
    status: Optional[str] = Query(None),
    service: JobOrchestrator = Depends(get_job_orchestrator),
):
    """Delete all completed/terminal process history without deleting media files."""
    deleted = service.delete_job_history(status=status)
    return {"status": "success", "deleted_count": deleted}


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> JobResponse:
    rec = service.get_job(job_id)
    return _enrich_job_response(rec)


@router.delete("/{job_id}")
def delete_job(
    job_id: str,
    service: JobOrchestrator = Depends(get_job_orchestrator),
):
    """Delete a single job/process record without deleting user media."""
    service.delete_job(job_id)
    return {"status": "success", "deleted_job_id": job_id}


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
    return _enrich_job_response(rec)


@router.post("/{job_id}/retry", response_model=JobResponse)
def retry_job(
    job_id: str,
    new_attempt: bool = Query(False),
    service: JobOrchestrator = Depends(get_job_orchestrator),
) -> JobResponse:
    rec = service.retry_job(job_id, create_new_attempt=new_attempt)
    return _enrich_job_response(rec)


@router.get("/{job_id}/checkpoint")
def get_job_checkpoint(
    job_id: str,
    service: JobOrchestrator = Depends(get_job_orchestrator),
):
    """Return persistent execution checkpoint data if available for this job."""
    cp = service.get_checkpoint(job_id)
    return {"job_id": job_id, "has_checkpoint": cp is not None, "checkpoint": cp}


# Duplicate route handlers onto processes_router for /api/v1/processes parity
processes_router.add_api_route("/stats", get_queue_stats, methods=["GET"], response_model=QueueStatsResponse)
processes_router.add_api_route("", create_job, methods=["POST"], response_model=JobResponse, status_code=201)
processes_router.add_api_route("", list_jobs, methods=["GET"], response_model=JobListResponse)
processes_router.add_api_route("/history", delete_jobs_history, methods=["DELETE"])
processes_router.add_api_route("/{job_id}", get_job, methods=["GET"], response_model=JobResponse)
processes_router.add_api_route("/{job_id}", delete_job, methods=["DELETE"])
processes_router.add_api_route("/{job_id}/logs", get_job_logs, methods=["GET"], response_model=JobLogsResponse)
processes_router.add_api_route("/{job_id}/cancel", cancel_job, methods=["POST"], response_model=JobResponse)
processes_router.add_api_route("/{job_id}/retry", retry_job, methods=["POST"], response_model=JobResponse)
processes_router.add_api_route("/{job_id}/checkpoint", get_job_checkpoint, methods=["GET"])
