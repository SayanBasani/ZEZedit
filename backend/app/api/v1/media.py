"""Media metadata management endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.schemas.core import (
    MediaAssetCreateRequest,
    MediaAssetListResponse,
    MediaAssetResponse,
    MediaAssetUpdateRequest,
    MediaRelinkRequest,
)
from app.services.media import MediaService

router = APIRouter(prefix="/projects/{project_id}/media", tags=["media"])


def get_media_service(request: Request) -> MediaService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return MediaService(settings=settings, db_path=layout.db_file)


@router.post("", response_model=MediaAssetResponse, status_code=201)
def register_media(
    project_id: str,
    req: MediaAssetCreateRequest,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    rec = service.register_media_asset(
        project_id=project_id,
        original_filename=req.original_filename,
        storage_path=req.storage_path,
        is_external=req.is_external,
        media_type=req.media_type,
        file_size_bytes=req.file_size_bytes,
        mime_type=req.mime_type,
        duration_seconds=req.duration_seconds,
        width=req.width,
        height=req.height,
        fps=req.fps,
        video_codec=req.video_codec,
        audio_codec=req.audio_codec,
        metadata=req.metadata,
    )
    return MediaAssetResponse(**rec.__dict__)


@router.get("", response_model=MediaAssetListResponse)
def list_media(
    project_id: str,
    availability: Optional[str] = Query(None),
    service: MediaService = Depends(get_media_service),
) -> MediaAssetListResponse:
    items = service.list_media_assets(project_id, availability=availability)
    return MediaAssetListResponse(
        items=[MediaAssetResponse(**r.__dict__) for r in items],
        total=len(items),
    )


@router.get("/{asset_id}", response_model=MediaAssetResponse)
def get_media(
    project_id: str,
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    rec = service.get_media_asset(project_id, asset_id)
    return MediaAssetResponse(**rec.__dict__)


@router.patch("/{asset_id}", response_model=MediaAssetResponse)
def update_media(
    project_id: str,
    asset_id: str,
    req: MediaAssetUpdateRequest,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    rec = service.update_media_metadata(
        project_id=project_id,
        asset_id=asset_id,
        updates=req.model_dump(exclude_unset=True),
    )
    return MediaAssetResponse(**rec.__dict__)


@router.post("/{asset_id}/mark-missing", response_model=MediaAssetResponse)
def mark_media_missing(
    project_id: str,
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    rec = service.mark_missing(project_id, asset_id)
    return MediaAssetResponse(**rec.__dict__)


@router.post("/{asset_id}/relink", response_model=MediaAssetResponse)
def relink_media(
    project_id: str,
    asset_id: str,
    req: MediaRelinkRequest,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    rec = service.relink_media(
        project_id=project_id,
        asset_id=asset_id,
        new_storage_path=req.new_storage_path,
    )
    return MediaAssetResponse(**rec.__dict__)
