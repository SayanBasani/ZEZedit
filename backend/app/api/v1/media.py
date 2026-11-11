"""Media metadata management, ingestion, proxying, and thumbnail endpoints."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.schemas.core import (
    MediaAssetCreateRequest,
    MediaAssetListResponse,
    MediaAssetResponse,
    MediaAssetUpdateRequest,
    MediaImportLocalRequest,
    MediaProxyGenerateRequest,
    MediaRelinkRequest,
    MediaStorageStatsResponse,
)
from app.services.jobs import JobOrchestrator
from app.services.media import MediaService
from app.services.media_pipeline import MediaPipelineService
from app.services.projects import ProjectService

router = APIRouter(prefix="/projects/{project_id}/media", tags=["media"])


def get_pipeline_service(request: Request) -> MediaPipelineService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    media_service = MediaService(settings=settings, db_path=layout.db_file)
    project_service = ProjectService(settings=settings, db_path=layout.db_file)
    job_orchestrator = JobOrchestrator(settings=settings, db_path=layout.db_file)
    return MediaPipelineService(
        settings=settings,
        storage=layout,
        media_service=media_service,
        project_service=project_service,
        job_orchestrator=job_orchestrator,
    )


def get_media_service(request: Request) -> MediaService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return MediaService(settings=settings, db_path=layout.db_file)


# -------------------- IMPORT & REGISTRATION ENDPOINTS --------------------

@router.post("", response_model=MediaAssetResponse, status_code=201)
def register_media(
    project_id: str,
    req: MediaAssetCreateRequest,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    """Register a media asset directly with provided technical metadata."""
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


@router.post("/import-local", response_model=MediaAssetResponse, status_code=201)
def import_local_file(
    project_id: str,
    req: MediaImportLocalRequest,
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaAssetResponse:
    """Import media from local filesystem path (either as external reference or copied into managed storage)."""
    rec = pipeline.import_local_media(
        project_id=project_id,
        file_path=req.file_path,
        copy_to_storage=req.copy_to_storage,
        generate_proxy_now=req.generate_proxy,
        generate_thumbnail_now=req.generate_thumbnail,
    )
    return MediaAssetResponse(**rec.__dict__)


@router.post("/upload", response_model=MediaAssetResponse, status_code=201)
async def upload_media_file(
    project_id: str,
    file: UploadFile = File(...),
    generate_proxy: bool = Query(False),
    generate_thumbnail: bool = Query(True),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaAssetResponse:
    """Stream-upload a media file in chunks into managed storage."""
    rec = await pipeline.import_uploaded_media(
        project_id=project_id,
        upload_file=file,
        generate_proxy_now=generate_proxy,
        generate_thumbnail_now=generate_thumbnail,
    )
    return MediaAssetResponse(**rec.__dict__)


# -------------------- ASSET LISTING & RETRIEVAL --------------------

@router.get("", response_model=MediaAssetListResponse)
def list_media(
    project_id: str,
    availability: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    proxy_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    service: MediaService = Depends(get_media_service),
) -> MediaAssetListResponse:
    """List assets for a project with optional filters for type, availability, proxy status, and search query."""
    items = service.list_media_assets(
        project_id=project_id,
        availability=availability,
        media_type=media_type,
        proxy_status=proxy_status,
        search=search,
    )
    return MediaAssetListResponse(
        items=[MediaAssetResponse(**r.__dict__) for r in items],
        total=len(items),
    )


@router.get("/storage-stats", response_model=MediaStorageStatsResponse)
def get_media_stats(
    project_id: str,
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaStorageStatsResponse:
    """Get project storage statistics for media, proxies, and thumbnails."""
    return pipeline.get_project_media_stats(project_id)


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


@router.delete("/{asset_id}", status_code=204)
def delete_media(
    project_id: str,
    asset_id: str,
    delete_source: bool = Query(False),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> None:
    """Safely remove media asset from project, removing derivative proxies and thumbnails."""
    pipeline.delete_media_asset(project_id, asset_id, delete_source_file=delete_source)


# -------------------- THUMBNAILS & PROXIES --------------------

@router.get("/{asset_id}/thumbnail")
def get_thumbnail_file(
    project_id: str,
    asset_id: str,
    service: MediaService = Depends(get_media_service),
):
    """Serve the thumbnail image for a media asset."""
    asset = service.get_media_asset(project_id, asset_id)
    if not asset.thumbnail_reference_path:
        raise AppError(
            code="THUMBNAIL_NOT_AVAILABLE",
            message=f"No thumbnail available for asset '{asset_id}'.",
            status_code=404,
        )
    p = Path(asset.thumbnail_reference_path)
    if not p.is_file():
        raise AppError(
            code="THUMBNAIL_FILE_MISSING",
            message="Thumbnail file does not exist on disk.",
            status_code=404,
        )
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.post("/{asset_id}/thumbnail/regenerate", response_model=MediaAssetResponse)
def regenerate_thumbnail(
    project_id: str,
    asset_id: str,
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaAssetResponse:
    """Force regeneration of thumbnail image."""
    rec = pipeline.regenerate_thumbnail_for_asset(project_id, asset_id)
    return MediaAssetResponse(**rec.__dict__)


@router.post("/{asset_id}/proxy", response_model=MediaAssetResponse)
def generate_proxy_endpoint(
    project_id: str,
    asset_id: str,
    req: MediaProxyGenerateRequest = MediaProxyGenerateRequest(),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaAssetResponse:
    """Trigger proxy video transcode for a video asset."""
    rec = pipeline.generate_proxy_for_asset(project_id, asset_id, profile=req.profile)
    return MediaAssetResponse(**rec.__dict__)


@router.get("/{asset_id}/proxy")
def get_proxy_file(
    project_id: str,
    asset_id: str,
    service: MediaService = Depends(get_media_service),
):
    """Serve the proxy video file with byte-range streaming support."""
    asset = service.get_media_asset(project_id, asset_id)
    if not asset.proxy_reference_path:
        raise AppError(
            code="PROXY_NOT_READY",
            message=f"No proxy video generated for asset '{asset_id}'.",
            status_code=404,
        )
    p = Path(asset.proxy_reference_path)
    if not p.is_file():
        raise AppError(
            code="PROXY_FILE_MISSING",
            message="Proxy video file not found on disk.",
            status_code=404,
        )
    return FileResponse(p, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})


# -------------------- RELINK & MAINTENANCE --------------------

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
