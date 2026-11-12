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
    MediaIntegrityCheckResult,
    MediaProxyGenerateRequest,
    MediaRelinkRequest,
    MediaRelinkResponse,
    MediaStorageStatsResponse,
    ProjectMediaIntegrityResponse,
)
from app.services.jobs import JobOrchestrator
from app.services.media import MediaService
from app.services.media_pipeline import MediaPipelineService
from app.services.projects import ProjectService
from app.services.workflow_state import VideoWorkflowStateResponse, WorkflowStateMachine

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


@router.post("/check-integrity", response_model=ProjectMediaIntegrityResponse)
def check_project_media_integrity(
    project_id: str,
    service: MediaService = Depends(get_media_service),
) -> ProjectMediaIntegrityResponse:
    """Run batch media integrity verification for all assets in a project."""
    res = service.check_project_media_integrity(project_id)
    return ProjectMediaIntegrityResponse(**res)


@router.get("/{asset_id}/integrity", response_model=MediaIntegrityCheckResult)
def get_asset_integrity(
    project_id: str,
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaIntegrityCheckResult:
    """Check single asset existence, size, and container readability."""
    res = service.check_asset_integrity(project_id, asset_id)
    return MediaIntegrityCheckResult(**res)


@router.post("/{asset_id}/relink/inspect")
def inspect_relink(
    project_id: str,
    asset_id: str,
    req: MediaRelinkRequest,
    service: MediaService = Depends(get_media_service),
):
    """Inspect and compare candidate replacement without modifying database."""
    res = service.inspect_relink_candidate(
        project_id=project_id,
        asset_id=asset_id,
        new_storage_path=req.new_storage_path,
    )
    return {
        "match_status": res["match_status"],
        "warnings": res["warnings"],
        "comparison": res["comparison"],
    }


@router.post("/{asset_id}/relink", response_model=MediaRelinkResponse)
def relink_media(
    project_id: str,
    asset_id: str,
    req: MediaRelinkRequest,
    service: MediaService = Depends(get_media_service),
) -> MediaRelinkResponse:
    """Relink an asset to a new filesystem path with comparison verification."""
    inspection = service.inspect_relink_candidate(
        project_id=project_id,
        asset_id=asset_id,
        new_storage_path=req.new_storage_path,
    )
    asset_rec = service.relink_media(
        project_id=project_id,
        asset_id=asset_id,
        new_storage_path=req.new_storage_path,
        force=req.force,
    )
    return MediaRelinkResponse(
        asset=MediaAssetResponse(**asset_rec.__dict__),
        match_status=inspection["match_status"],
        warnings=inspection["warnings"],
        comparison=inspection["comparison"],
    )


# -------------------- WORKFLOW LIFECYCLE --------------------

@router.get("/{asset_id}/workflow", response_model=VideoWorkflowStateResponse)
def get_media_workflow_state(
    project_id: str,
    asset_id: str,
    request: Request,
) -> VideoWorkflowStateResponse:
    """Return authoritative video-to-shorts lifecycle workflow state."""
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    machine = WorkflowStateMachine(settings=settings, db_path=layout.db_file)
    return machine.get_workflow_state(project_id, asset_id)


# -------------------- GLOBAL MEDIA ROUTER (NO PROJECT DROPDOWN REQUIRED) --------------------

global_media_router = APIRouter(prefix="/media", tags=["global-media"])


@global_media_router.get("", response_model=MediaAssetListResponse)
def list_all_media(
    availability: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    proxy_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    service: MediaService = Depends(get_media_service),
) -> MediaAssetListResponse:
    """List all assets across all projects in a unified library view."""
    items = service.list_media_assets(
        project_id="all",
        availability=availability,
        media_type=media_type,
        proxy_status=proxy_status,
        search=search,
    )
    return MediaAssetListResponse(
        items=[MediaAssetResponse(**r.__dict__) for r in items],
        total=len(items),
    )


@global_media_router.post("/upload", response_model=MediaAssetResponse, status_code=201)
async def upload_media_file_global(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[str] = Query(None),
    generate_proxy: bool = Query(False),
    generate_thumbnail: bool = Query(True),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaAssetResponse:
    """Upload media directly; if project_id is omitted, auto-creates or selects the default project."""
    if not project_id or project_id in ("auto", "default", "all"):
        settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
        layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
            settings.storage_root
        )
        proj_svc = ProjectService(settings=settings, db_path=layout.db_file)
        base_name = Path(file.filename or "uploaded_video").stem.replace("_", " ").title()
        proj = proj_svc.get_or_create_default_project(name=f"Project {base_name}")
        target_pid = proj.id
    else:
        target_pid = project_id

    rec = await pipeline.import_uploaded_media(
        project_id=target_pid,
        upload_file=file,
        generate_proxy_now=generate_proxy,
        generate_thumbnail_now=generate_thumbnail,
    )
    return MediaAssetResponse(**rec.__dict__)


@global_media_router.post("/import-local", response_model=MediaAssetResponse, status_code=201)
def import_local_file_global(
    request: Request,
    req: MediaImportLocalRequest,
    project_id: Optional[str] = Query(None),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaAssetResponse:
    """Import media from local path; auto-creates or selects default project if omitted."""
    if not project_id or project_id in ("auto", "default", "all"):
        settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
        layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
            settings.storage_root
        )
        proj_svc = ProjectService(settings=settings, db_path=layout.db_file)
        base_name = Path(req.file_path).stem.replace("_", " ").title()
        proj = proj_svc.get_or_create_default_project(name=f"Project {base_name}")
        target_pid = proj.id
    else:
        target_pid = project_id

    rec = pipeline.import_local_media(
        project_id=target_pid,
        file_path=req.file_path,
        copy_to_storage=req.copy_to_storage,
        generate_proxy_now=req.generate_proxy,
        generate_thumbnail_now=req.generate_thumbnail,
    )
    return MediaAssetResponse(**rec.__dict__)


@global_media_router.get("/{asset_id}", response_model=MediaAssetResponse)
def get_media_global(
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    """Retrieve media asset details by asset ID across all projects."""
    rec = service.get_media_asset("all", asset_id)
    return MediaAssetResponse(**rec.__dict__)


@global_media_router.get("/{asset_id}/thumbnail")
def get_media_thumbnail_global(
    asset_id: str,
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
    service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """Serve media thumbnail directly by asset ID."""
    asset = service.get_media_asset("all", asset_id)
    thumb_path = pipeline.get_media_thumbnail_path(asset.project_id, asset_id)
    if not thumb_path or not thumb_path.exists():
        raise AppError(
            code="THUMBNAIL_NOT_FOUND",
            message=f"Thumbnail for asset '{asset_id}' not found.",
            status_code=404,
        )
    return FileResponse(thumb_path, media_type="image/jpeg")


@global_media_router.get("/{asset_id}/proxy")
def get_media_proxy_global(
    asset_id: str,
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
    service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """Serve 480p proxy video directly by asset ID."""
    asset = service.get_media_asset("all", asset_id)
    proxy_path = pipeline.get_media_proxy_path(asset.project_id, asset_id)
    if not proxy_path or not proxy_path.exists():
        raise AppError(
            code="PROXY_NOT_FOUND",
            message=f"Proxy video for asset '{asset_id}' not found.",
            status_code=404,
        )
    return FileResponse(proxy_path, media_type="video/mp4")


@global_media_router.get("/{asset_id}/stream")
def stream_media_global(
    asset_id: str,
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
    service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """Serve source video or proxy with byte-range streaming for HTML5 playback."""
    asset = service.get_media_asset("all", asset_id)
    source_path = Path(asset.storage_path) if asset.storage_path else None
    if source_path and source_path.is_file():
        return FileResponse(source_path, media_type=asset.mime_type or "video/mp4", headers={"Accept-Ranges": "bytes"})
    
    proxy_path = pipeline.get_media_proxy_path(asset.project_id, asset_id)
    if proxy_path and proxy_path.is_file():
        return FileResponse(proxy_path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})

    raise AppError(
        code="MEDIA_STREAM_NOT_FOUND",
        message=f"Video stream file for asset '{asset_id}' is not accessible on disk.",
        status_code=404,
    )


@global_media_router.patch("/{asset_id}", response_model=MediaAssetResponse)
def update_media_global(
    asset_id: str,
    req: MediaAssetUpdateRequest,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    """Update media asset title or metadata globally."""
    asset = service.get_media_asset("all", asset_id)
    rec = service.update_media_metadata(
        project_id=asset.project_id,
        asset_id=asset_id,
        updates=req.model_dump(exclude_unset=True),
    )
    return MediaAssetResponse(**rec.__dict__)


@global_media_router.delete("/{asset_id}", status_code=204)
def delete_media_global(
    asset_id: str,
    delete_source: bool = Query(False),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
    service: MediaService = Depends(get_media_service),
) -> None:
    """Safely remove media asset across all projects."""
    asset = service.get_media_asset("all", asset_id)
    pipeline.delete_media_asset(asset.project_id, asset_id, delete_source_file=delete_source)


