"""Maintenance, storage breakdown, cleanup preview/execution, quotas, and automatic pruning endpoints."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.config import Settings, get_settings
from app.schemas.core import (
    CleanupExecuteRequest,
    CleanupExecuteResponse,
    CleanupPreviewResponse,
    StorageBreakdownResponse,
    StorageQuotaSettingsDTO,
    StorageQuotaStatusResponse,
    StorageQuotaUpdateRequest,
)
from app.services.storage import StorageService

logger = logging.getLogger("zezedit.maintenance")
router = APIRouter(prefix="/maintenance", tags=["maintenance"])


def get_storage_service(request: Request) -> StorageService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    return StorageService(settings=settings)


@router.get("/breakdown", response_model=StorageBreakdownResponse)
@router.get("/storage-breakdown", response_model=StorageBreakdownResponse)
def get_maintenance_storage_breakdown(
    service: StorageService = Depends(get_storage_service),
) -> StorageBreakdownResponse:
    """Return categorized storage consumption across media, caches, exports, DB, and quotas."""
    data = service.get_storage_breakdown()
    return StorageBreakdownResponse(**data)


@router.get("/cleanup-preview", response_model=CleanupPreviewResponse)
@router.post("/cleanup-preview", response_model=CleanupPreviewResponse)
def preview_maintenance_cleanup(
    categories: Optional[List[str]] = Query(None),
    service: StorageService = Depends(get_storage_service),
) -> CleanupPreviewResponse:
    """Non-destructive preview of removable temporary files, abandoned renders, and orphaned uploads."""
    data = service.preview_maintenance_cleanup(category_filter=categories)
    return CleanupPreviewResponse(**data)


@router.post("/cleanup-execute", response_model=CleanupExecuteResponse)
def execute_maintenance_cleanup(
    req: CleanupExecuteRequest = CleanupExecuteRequest(),
    service: StorageService = Depends(get_storage_service),
) -> CleanupExecuteResponse:
    """Execute safe deletion strictly bounded to eligible temporary files with audit logging."""
    data = service.execute_maintenance_cleanup(
        candidate_ids=req.candidate_ids,
        selected_categories=req.selected_categories,
        is_automatic=False,
    )
    return CleanupExecuteResponse(**data)


@router.get("/quotas", response_model=StorageQuotaStatusResponse)
def get_storage_quotas_status(
    service: StorageService = Depends(get_storage_service),
) -> StorageQuotaStatusResponse:
    """Return current storage quota settings, utilization percentages, and threshold warnings."""
    return service.get_storage_quota_status()


@router.patch("/quotas", response_model=StorageQuotaSettingsDTO)
@router.put("/quotas", response_model=StorageQuotaSettingsDTO)
def update_storage_quotas(
    req: StorageQuotaUpdateRequest,
    service: StorageService = Depends(get_storage_service),
) -> StorageQuotaSettingsDTO:
    """Update persistent storage quota limits and auto-pruning policies."""
    return service.update_storage_quotas(req)


@router.post("/auto-prune")
def execute_auto_prune(
    force: bool = Query(False, description="Force run even if auto_prune_enabled is false"),
    service: StorageService = Depends(get_storage_service),
) -> Dict[str, Any]:
    """Execute automatic pruning of eligible temporary files respecting configured retention period."""
    return service.execute_auto_prune(force=force)


@router.post("/recover-stale-artifacts")
def recover_stale_artifacts(
    service: StorageService = Depends(get_storage_service),
) -> Dict[str, Any]:
    """Recover from interrupted uploads, abandoned render staging, and app crashes."""
    return service.recover_stale_artifacts()


@router.get("/cleanup-history")
def get_cleanup_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: StorageService = Depends(get_storage_service),
) -> List[Dict[str, Any]]:
    """Return recent storage cleanup audit records from database."""
    return service.get_cleanup_history(limit=limit, offset=offset)
