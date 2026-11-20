"""Media metadata management, ingestion, proxying, and thumbnail endpoints."""

import logging
import math
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.schemas.core import (
    MediaAssetCreateRequest,
    MediaAssetListResponse,
    MediaAssetResponse,
    MediaAssetUpdateRequest,
    MediaBatchUploadItemResult,
    MediaBatchUploadResponse,
    MediaDeduplicationStatsResponse,
    MediaImportLocalRequest,
    MediaIntegrityCheckResult,
    MediaProxyGenerateRequest,
    MediaReconcileResponse,
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

logger = logging.getLogger("zezedit.media_api")

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


def _stream_video_asset(asset_id: str, service: MediaService, request: Request):
    """Serve source video or proxy with HTTP 206 byte-range streaming for HTML5 playback."""
    asset = service.get_media_asset("all", asset_id)
    layout = StorageLayout.from_root(service.settings.storage_root)
    source_path = Path(asset.storage_path) if asset.storage_path else None
    if not source_path or not source_path.is_file():
        source_path = layout.media / (asset.storage_path or "")
    if not source_path.is_file() and asset.proxy_reference_path:
        source_path = Path(asset.proxy_reference_path)
        if not source_path.is_file():
            source_path = layout.proxies / Path(asset.proxy_reference_path).name

    if not source_path.is_file():
        raise AppError(
            code="MEDIA_STREAM_NOT_FOUND",
            message=f"Video stream file for asset '{asset_id}' is not accessible on disk.",
            status_code=404,
        )

    # Path traversal defense: verify file is within storage_root if not external
    if not asset.is_external:
        try:
            if not source_path.resolve().is_relative_to(service.settings.storage_root.resolve()):
                raise AppError(
                    code="ACCESS_DENIED",
                    message="Access denied: media path is outside allowed storage root.",
                    status_code=403,
                )
        except Exception as p_err:
            if isinstance(p_err, AppError):
                raise
            pass

    file_size = source_path.stat().st_size
    media_type = asset.mime_type or "video/mp4"
    range_header = request.headers.get("range")

    if not range_header:
        return FileResponse(
            str(source_path),
            media_type=media_type,
            filename=source_path.name,
            headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
        )

    # Parse byte range: "bytes=start-end"
    try:
        units, range_val = range_header.split("=")
        if units.strip() != "bytes":
            raise ValueError()
        start_str, end_str = range_val.split("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        if start < 0 or start >= file_size or end < start:
            raise ValueError()
        end = min(end, file_size - 1)
        content_length = end - start + 1
    except Exception:
        raise AppError(
            code="RANGE_NOT_SATISFIABLE",
            message=f"Requested range '{range_header}' not satisfiable for file of size {file_size} bytes.",
            status_code=416,
        )

    def iter_bytes():
        with open(source_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            chunk_size = 64 * 1024
            while remaining > 0:
                read_len = min(remaining, chunk_size)
                data = f.read(read_len)
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        iter_bytes(),
        status_code=206,
        media_type=media_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        },
    )


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
    request: Request,
    project_id: str,
    file: UploadFile = File(...),
    generate_proxy: bool = Query(False),
    generate_thumbnail: bool = Query(True),
    expected_size: Optional[int] = Query(None),
    expected_sha256: Optional[str] = Query(None),
    attempt_id: Optional[str] = Query(None),
    test_delay_seconds: float = Query(0.0),
    test_failure_code: Optional[int] = Query(None),
    test_fail_registration: bool = Query(False),
    test_fail_publication: bool = Query(False),
    require_video: bool = Query(False),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaAssetResponse:
    """Stream-upload a media file in chunks into managed storage."""
    if test_failure_code and test_failure_code > 0:
        raise AppError(
            code=f"SIMULATED_FAILURE_{test_failure_code}",
            message=f"Simulated test failure with HTTP status {test_failure_code}.",
            status_code=test_failure_code,
        )

    exp_size = expected_size
    if exp_size is None and "x-expected-file-size" in request.headers:
        try:
            exp_size = int(request.headers["x-expected-file-size"])
        except ValueError:
            pass
    exp_sha = expected_sha256 or request.headers.get("x-expected-sha256")
    att_id = attempt_id or request.headers.get("x-upload-attempt-id")
    req_vid = require_video or request.headers.get("x-require-video", "").lower() == "true"

    rec = await pipeline.import_uploaded_media(
        project_id=project_id,
        upload_file=file,
        generate_proxy_now=generate_proxy,
        generate_thumbnail_now=generate_thumbnail,
        expected_size=exp_size,
        expected_sha256=exp_sha,
        attempt_id=att_id,
        test_fail_registration=test_fail_registration,
        test_fail_publication=test_fail_publication,
        require_video=req_vid,
    )
    if test_delay_seconds > 0:
        import asyncio
        await asyncio.sleep(test_delay_seconds)
    return MediaAssetResponse(**rec.__dict__)


@router.post("/batch-upload", response_model=MediaBatchUploadResponse, status_code=200)
async def upload_media_batch(
    request: Request,
    project_id: str,
    files: List[UploadFile] = File(...),
    generate_proxy: bool = Query(False),
    generate_thumbnail: bool = Query(True),
    test_delay_seconds: float = Query(0.0),
    test_failure_code: Optional[int] = Query(None),
    test_fail_registration: bool = Query(False),
    test_fail_publication: bool = Query(False),
    test_failure_filename: Optional[str] = Query(None),
    require_video: bool = Query(False),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaBatchUploadResponse:
    """Upload multiple media files in one operation with per-file status reporting."""
    if not files:
        raise AppError(
            code="NO_FILES_PROVIDED",
            message="No files provided for batch upload.",
            status_code=400,
        )

    items: List[MediaBatchUploadItemResult] = []
    succeeded_count = 0
    failed_count = 0
    batch_attempt_id = request.headers.get("x-upload-attempt-id")
    req_vid = require_video or request.headers.get("x-require-video", "").lower() == "true"

    for upload_file in files:
        fname = upload_file.filename or "uploaded_media"
        try:
            if test_failure_code and test_failure_code > 0:
                if not test_failure_filename or test_failure_filename in fname:
                    raise AppError(
                        code=f"SIMULATED_FAILURE_{test_failure_code}",
                        message=f"Simulated test failure for item '{fname}' with HTTP status {test_failure_code}.",
                        status_code=test_failure_code,
                    )
            rec = await pipeline.import_uploaded_media(
                project_id=project_id,
                upload_file=upload_file,
                generate_proxy_now=generate_proxy,
                generate_thumbnail_now=generate_thumbnail,
                attempt_id=batch_attempt_id,
                test_fail_registration=test_fail_registration,
                test_fail_publication=test_fail_publication,
                require_video=req_vid,
            )
            asset_resp = MediaAssetResponse(**rec.__dict__)
            items.append(
                MediaBatchUploadItemResult(
                    filename=fname,
                    success=True,
                    media_id=rec.id,
                    asset=asset_resp,
                    is_deduplicated=rec.is_deduplicated,
                    reference_count=rec.reference_count,
                )
            )
            succeeded_count += 1
        except Exception as exc:
            err_msg = str(exc)
            err_code = getattr(exc, "code", "UPLOAD_FAILED")
            logger.warning("Batch upload failed for item '%s': %s", fname, err_msg)
            items.append(
                MediaBatchUploadItemResult(
                    filename=fname,
                    success=False,
                    media_id=None,
                    asset=None,
                    error=err_msg,
                    error_code=err_code,
                )
            )
            failed_count += 1

    if test_delay_seconds > 0:
        import asyncio
        await asyncio.sleep(test_delay_seconds)

    return MediaBatchUploadResponse(
        total=len(files),
        succeeded=succeeded_count,
        failed=failed_count,
        items=items,
    )


# -------------------- ASSET LISTING & RETRIEVAL --------------------

@router.get("", response_model=MediaAssetListResponse)
def list_media(
    project_id: str,
    availability: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    proxy_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    resolution: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    video_codec: Optional[str] = Query(None),
    duration_min: Optional[float] = Query(None),
    duration_max: Optional[float] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    integrity_status: Optional[str] = Query(None),
    analysis_status: Optional[str] = Query(None),
    missing_thumbnail: Optional[bool] = Query(None),
    sort: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: MediaService = Depends(get_media_service),
) -> MediaAssetListResponse:
    """List assets for a project with server-side search, filtering, allowlisted sorting, and pagination."""
    if sort:
        if ":" in sort:
            s_by, s_ord = sort.split(":", 1)
            sort_by = s_by.strip()
            sort_order = s_ord.strip()
        else:
            sort_by = sort.strip()

    items, total_count = service.list_media_assets(
        project_id=project_id,
        availability=availability,
        media_type=media_type,
        proxy_status=proxy_status,
        search=search,
        resolution=resolution,
        format=format,
        video_codec=video_codec,
        duration_min=duration_min,
        duration_max=duration_max,
        date_from=date_from,
        date_to=date_to,
        integrity_status=integrity_status,
        analysis_status=analysis_status,
        missing_thumbnail=missing_thumbnail,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        return_total=True,
    )
    total_pages = max(1, math.ceil(total_count / page_size))
    return MediaAssetListResponse(
        items=[MediaAssetResponse(**r.__dict__) for r in items],
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/storage-stats", response_model=MediaStorageStatsResponse)
def get_media_stats(
    project_id: str,
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaStorageStatsResponse:
    """Get project storage statistics for media, proxies, and thumbnails."""
    return pipeline.get_project_media_stats(project_id)


@router.get("/deduplication/stats", response_model=MediaDeduplicationStatsResponse)
@router.get("/deduplication-stats", response_model=MediaDeduplicationStatsResponse)
def get_deduplication_stats_project(
    project_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaDeduplicationStatsResponse:
    """Get global media deduplication and reference statistics."""
    stats = service.get_deduplication_stats()
    return MediaDeduplicationStatsResponse(**stats)


@router.post("/deduplication/reconcile")
@router.post("/reconcile-references")
def reconcile_references_project(
    project_id: str,
    service: MediaService = Depends(get_media_service),
):
    """Reconcile and synchronize stored media reference counts."""
    return service.reconcile_reference_counts()


@router.get("/{asset_id}", response_model=MediaAssetResponse)
def get_media(
    project_id: str,
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    rec = service.get_media_asset(project_id, asset_id)
    return MediaAssetResponse(**rec.__dict__)


@router.get("/{asset_id}/stream")
def stream_media(
    project_id: str,
    asset_id: str,
    request: Request,
    service: MediaService = Depends(get_media_service),
):
    """Serve source video or proxy with byte-range streaming for HTML5 playback."""
    return _stream_video_asset(asset_id, service, request)


@router.post("/{asset_id}/refresh-metadata", response_model=MediaAssetResponse)
def refresh_metadata_endpoint(
    project_id: str,
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    """Explicitly re-probe media file on disk and update metadata atomically."""
    rec = service.refresh_media_metadata(project_id, asset_id)
    return MediaAssetResponse(**rec.__dict__)


@router.post("/{asset_id}/thumbnail/regenerate", response_model=MediaAssetResponse)
def regenerate_thumbnail_endpoint(
    project_id: str,
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    """Explicitly regenerate JPEG thumbnail for an asset."""
    rec = service.regenerate_thumbnail(project_id, asset_id)
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
    force_with_exports: bool = Query(False),
    service: MediaService = Depends(get_media_service),
) -> None:
    """Safely remove media asset from project, checking active operations and dependent exports."""
    service.delete_media_asset(
        project_id=project_id,
        asset_id=asset_id,
        delete_source=delete_source,
        force_with_exports=force_with_exports,
    )


# -------------------- THUMBNAILS & PROXIES --------------------

@router.get("/{asset_id}/thumbnail")
def get_thumbnail_file(
    project_id: str,
    asset_id: str,
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
    service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """Serve the thumbnail image for a media asset with on-demand fallback generation."""
    from app.services.media_thumbnail import generate_thumbnail
    asset = service.get_media_asset(project_id, asset_id)
    thumb_path = None
    if asset.thumbnail_reference_path:
        p = Path(asset.thumbnail_reference_path)
        if p.is_file():
            thumb_path = p
        elif (pipeline.storage.root / asset.thumbnail_reference_path).is_file():
            thumb_path = pipeline.storage.root / asset.thumbnail_reference_path
        elif (pipeline.storage.thumbnails / p.name).is_file():
            thumb_path = pipeline.storage.thumbnails / p.name
    if not thumb_path or not thumb_path.is_file():
        thumb_path = pipeline.storage.thumbnails / f"{asset_id}.jpg"

    if not thumb_path.exists() or thumb_path.stat().st_size == 0:
        source_path = Path(asset.storage_path) if asset.storage_path else None
        if not source_path or not source_path.is_file():
            source_path = pipeline.storage.media / (asset.storage_path or "")
        if source_path and source_path.is_file():
            try:
                generate_thumbnail(source_path, thumb_path, media_type=asset.media_type or "video", duration=asset.duration_seconds)
                service.update_media_metadata(asset.project_id, asset_id, {"thumbnail_reference_path": f"thumbnails/{thumb_path.name}"})
            except Exception as exc:
                raise AppError(
                    code="THUMBNAIL_NOT_FOUND",
                    message=f"Thumbnail for asset '{asset_id}' could not be generated: {exc}",
                    status_code=404,
                )
        else:
            raise AppError(
                code="THUMBNAIL_FILE_MISSING",
                message=f"Thumbnail file for asset '{asset_id}' does not exist on disk and source is missing.",
                status_code=404,
            )
    return FileResponse(thumb_path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


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
        relinked_at=asset_rec.relinked_at,
    )


@router.post("/{asset_id}/relink/upload", response_model=MediaRelinkResponse)
async def relink_media_upload(
    project_id: str,
    asset_id: str,
    file: UploadFile = File(...),
    force: bool = Form(False),
    expected_sha256: Optional[str] = Form(None),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaRelinkResponse:
    """Relink an asset using streamed file upload with atomic staging and verification."""
    res = await pipeline.relink_uploaded_media(
        project_id=project_id,
        asset_id=asset_id,
        upload_file=file,
        force=force,
        expected_sha256=expected_sha256,
    )
    return MediaRelinkResponse(
        asset=MediaAssetResponse(**res["asset"].__dict__),
        match_status=res["match_status"],
        warnings=res["warnings"],
        comparison=res["comparison"],
        relinked_at=res["relinked_at"],
    )


@router.post("/reconcile-availability", response_model=MediaReconcileResponse)
def reconcile_project_availability(
    project_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaReconcileResponse:
    """Reconcile missing files for project (e.g. after external drive is reconnected)."""
    res = service.reconcile_missing_media(project_id=project_id)
    return MediaReconcileResponse(**res)


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
    resolution: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    video_codec: Optional[str] = Query(None),
    duration_min: Optional[float] = Query(None),
    duration_max: Optional[float] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    integrity_status: Optional[str] = Query(None),
    analysis_status: Optional[str] = Query(None),
    missing_thumbnail: Optional[bool] = Query(None),
    sort: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: MediaService = Depends(get_media_service),
) -> MediaAssetListResponse:
    """List all assets across all projects with server-side search, filtering, allowlisted sorting, and pagination."""
    if sort:
        if ":" in sort:
            s_by, s_ord = sort.split(":", 1)
            sort_by = s_by.strip()
            sort_order = s_ord.strip()
        else:
            sort_by = sort.strip()

    items, total_count = service.list_media_assets(
        project_id="all",
        availability=availability,
        media_type=media_type,
        proxy_status=proxy_status,
        search=search,
        resolution=resolution,
        format=format,
        video_codec=video_codec,
        duration_min=duration_min,
        duration_max=duration_max,
        date_from=date_from,
        date_to=date_to,
        integrity_status=integrity_status,
        analysis_status=analysis_status,
        missing_thumbnail=missing_thumbnail,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        return_total=True,
    )
    total_pages = max(1, math.ceil(total_count / page_size))
    return MediaAssetListResponse(
        items=[MediaAssetResponse(**r.__dict__) for r in items],
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@global_media_router.post("/upload", response_model=MediaAssetResponse, status_code=201)
async def upload_media_file_global(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[str] = Query(None),
    generate_proxy: bool = Query(False),
    generate_thumbnail: bool = Query(True),
    expected_size: Optional[int] = Query(None),
    expected_sha256: Optional[str] = Query(None),
    attempt_id: Optional[str] = Query(None),
    test_delay_seconds: float = Query(0.0),
    test_failure_code: Optional[int] = Query(None),
    test_fail_registration: bool = Query(False),
    test_fail_publication: bool = Query(False),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaAssetResponse:
    """Upload media directly; if project_id is omitted, auto-creates or selects the default project."""
    if test_failure_code and test_failure_code > 0:
        raise AppError(
            code=f"SIMULATED_FAILURE_{test_failure_code}",
            message=f"Simulated test failure with HTTP status {test_failure_code}.",
            status_code=test_failure_code,
        )

    exp_size = expected_size
    if exp_size is None and "x-expected-file-size" in request.headers:
        try:
            exp_size = int(request.headers["x-expected-file-size"])
        except ValueError:
            pass
    exp_sha = expected_sha256 or request.headers.get("x-expected-sha256")
    att_id = attempt_id or request.headers.get("x-upload-attempt-id")

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
        expected_size=exp_size,
        expected_sha256=exp_sha,
        attempt_id=att_id,
        test_fail_registration=test_fail_registration,
        test_fail_publication=test_fail_publication,
        require_video=True,
    )
    if test_delay_seconds > 0:
        import asyncio
        await asyncio.sleep(test_delay_seconds)
    return MediaAssetResponse(**rec.__dict__)


@global_media_router.post("/batch-upload", response_model=MediaBatchUploadResponse, status_code=200)
async def upload_media_batch_global(
    request: Request,
    files: List[UploadFile] = File(...),
    project_id: Optional[str] = Query(None),
    generate_proxy: bool = Query(False),
    generate_thumbnail: bool = Query(True),
    test_delay_seconds: float = Query(0.0),
    test_failure_code: Optional[int] = Query(None),
    test_fail_registration: bool = Query(False),
    test_fail_publication: bool = Query(False),
    test_failure_filename: Optional[str] = Query(None),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaBatchUploadResponse:
    """Upload multiple media files globally; auto-selects or creates default project if omitted."""
    if not files:
        raise AppError(
            code="NO_FILES_PROVIDED",
            message="No files provided for batch upload.",
            status_code=400,
        )

    if not project_id or project_id in ("auto", "default", "all"):
        settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
        layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
            settings.storage_root
        )
        proj_svc = ProjectService(settings=settings, db_path=layout.db_file)
        proj = proj_svc.get_or_create_default_project(name="Default Project")
        target_pid = proj.id
    else:
        target_pid = project_id

    items: List[MediaBatchUploadItemResult] = []
    succeeded_count = 0
    failed_count = 0
    batch_attempt_id = request.headers.get("x-upload-attempt-id")

    for upload_file in files:
        fname = upload_file.filename or "uploaded_media"
        try:
            if test_failure_code and test_failure_code > 0:
                if not test_failure_filename or test_failure_filename in fname:
                    raise AppError(
                        code=f"SIMULATED_FAILURE_{test_failure_code}",
                        message=f"Simulated test failure for item '{fname}' with HTTP status {test_failure_code}.",
                        status_code=test_failure_code,
                    )
            rec = await pipeline.import_uploaded_media(
                project_id=target_pid,
                upload_file=upload_file,
                generate_proxy_now=generate_proxy,
                generate_thumbnail_now=generate_thumbnail,
                attempt_id=batch_attempt_id,
                test_fail_registration=test_fail_registration,
                test_fail_publication=test_fail_publication,
                require_video=True,
            )
            asset_resp = MediaAssetResponse(**rec.__dict__)
            items.append(
                MediaBatchUploadItemResult(
                    filename=fname,
                    success=True,
                    media_id=rec.id,
                    asset=asset_resp,
                    is_deduplicated=rec.is_deduplicated,
                    reference_count=rec.reference_count,
                )
            )
            succeeded_count += 1
        except Exception as exc:
            err_msg = str(exc)
            err_code = getattr(exc, "code", "UPLOAD_FAILED")
            logger.warning("Global batch upload failed for item '%s': %s", fname, err_msg)
            items.append(
                MediaBatchUploadItemResult(
                    filename=fname,
                    success=False,
                    media_id=None,
                    asset=None,
                    error=err_msg,
                    error_code=err_code,
                )
            )
            failed_count += 1

    if test_delay_seconds > 0:
        import asyncio
        await asyncio.sleep(test_delay_seconds)

    return MediaBatchUploadResponse(
        total=len(files),
        succeeded=succeeded_count,
        failed=failed_count,
        items=items,
    )


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
    from app.services.media_thumbnail import generate_thumbnail
    asset = service.get_media_asset("all", asset_id)
    thumb_path = None
    if asset.thumbnail_reference_path:
        p = Path(asset.thumbnail_reference_path)
        if p.is_file():
            thumb_path = p
        elif (pipeline.storage.root / asset.thumbnail_reference_path).is_file():
            thumb_path = pipeline.storage.root / asset.thumbnail_reference_path
        elif (pipeline.storage.thumbnails / p.name).is_file():
            thumb_path = pipeline.storage.thumbnails / p.name
    if not thumb_path or not thumb_path.is_file():
        thumb_path = pipeline.storage.thumbnails / f"{asset_id}.jpg"

    if not thumb_path.exists() or thumb_path.stat().st_size == 0:
        source_path = Path(asset.storage_path) if asset.storage_path else None
        if not source_path or not source_path.is_file():
            source_path = pipeline.storage.media / (asset.storage_path or "")
        if source_path and source_path.is_file():
            try:
                generate_thumbnail(source_path, thumb_path, media_type=asset.media_type or "video", duration=asset.duration_seconds)
                service.update_media_metadata(asset.project_id, asset_id, {"thumbnail_reference_path": f"thumbnails/{thumb_path.name}"})
            except Exception as exc:
                raise AppError(
                    code="THUMBNAIL_NOT_FOUND",
                    message=f"Thumbnail for asset '{asset_id}' could not be generated: {exc}",
                    status_code=404,
                )
        else:
            raise AppError(
                code="THUMBNAIL_NOT_FOUND",
                message=f"Thumbnail for asset '{asset_id}' not found.",
                status_code=404,
            )
    return FileResponse(thumb_path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@global_media_router.get("/{asset_id}/proxy")
def get_media_proxy_global(
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """Serve 480p proxy video directly by asset ID."""
    asset = service.get_media_asset("all", asset_id)
    if not asset.proxy_reference_path:
        raise AppError(
            code="PROXY_NOT_FOUND",
            message=f"Proxy video for asset '{asset_id}' not found.",
            status_code=404,
        )
    proxy_path = Path(asset.proxy_reference_path)
    if not proxy_path.is_file():
        raise AppError(
            code="PROXY_NOT_FOUND",
            message=f"Proxy video file for asset '{asset_id}' does not exist on disk.",
            status_code=404,
        )
    return FileResponse(proxy_path, media_type="video/mp4")


@global_media_router.get("/{asset_id}/stream")
def stream_media_global(
    asset_id: str,
    request: Request,
    service: MediaService = Depends(get_media_service),
):
    """Serve source video or proxy with byte-range streaming for HTML5 playback."""
    return _stream_video_asset(asset_id, service, request)


@global_media_router.post("/{asset_id}/refresh-metadata", response_model=MediaAssetResponse)
def refresh_media_metadata_global(
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    """Explicitly re-probe media file on disk and update metadata atomically."""
    rec = service.refresh_media_metadata("all", asset_id)
    return MediaAssetResponse(**rec.__dict__)


@global_media_router.post("/{asset_id}/thumbnail/regenerate", response_model=MediaAssetResponse)
def regenerate_thumbnail_global(
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    """Explicitly regenerate JPEG thumbnail for an asset."""
    rec = service.regenerate_thumbnail("all", asset_id)
    return MediaAssetResponse(**rec.__dict__)


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
    force_with_exports: bool = Query(False),
    service: MediaService = Depends(get_media_service),
) -> None:
    """Safely remove media asset across all projects, checking active operations and dependent exports."""
    service.delete_media_asset("all", asset_id, delete_source=delete_source, force_with_exports=force_with_exports)


@global_media_router.post("/{asset_id}/mark-missing", response_model=MediaAssetResponse)
def mark_media_missing_global(
    asset_id: str,
    service: MediaService = Depends(get_media_service),
) -> MediaAssetResponse:
    """Explicitly mark asset as missing across all projects."""
    rec = service.mark_missing("all", asset_id)
    return MediaAssetResponse(**rec.__dict__)


@global_media_router.post("/{asset_id}/relink/inspect")
def inspect_relink_global(
    asset_id: str,
    req: MediaRelinkRequest,
    service: MediaService = Depends(get_media_service),
):
    """Inspect and compare candidate replacement path globally without modifying database."""
    res = service.inspect_relink_candidate(
        project_id="all",
        asset_id=asset_id,
        new_storage_path=req.new_storage_path,
    )
    return {
        "match_status": res["match_status"],
        "warnings": res["warnings"],
        "comparison": res["comparison"],
    }


@global_media_router.post("/{asset_id}/relink", response_model=MediaRelinkResponse)
def relink_media_global(
    asset_id: str,
    req: MediaRelinkRequest,
    service: MediaService = Depends(get_media_service),
) -> MediaRelinkResponse:
    """Relink an asset to a new filesystem path globally with comparison verification."""
    inspection = service.inspect_relink_candidate(
        project_id="all",
        asset_id=asset_id,
        new_storage_path=req.new_storage_path,
    )
    asset_rec = service.relink_media(
        project_id="all",
        asset_id=asset_id,
        new_storage_path=req.new_storage_path,
        force=req.force,
    )
    return MediaRelinkResponse(
        asset=MediaAssetResponse(**asset_rec.__dict__),
        match_status=inspection["match_status"],
        warnings=inspection["warnings"],
        comparison=inspection["comparison"],
        relinked_at=asset_rec.relinked_at,
    )


@global_media_router.post("/{asset_id}/relink/upload", response_model=MediaRelinkResponse)
async def relink_media_upload_global(
    asset_id: str,
    file: UploadFile = File(...),
    force: bool = Form(False),
    expected_sha256: Optional[str] = Form(None),
    pipeline: MediaPipelineService = Depends(get_pipeline_service),
) -> MediaRelinkResponse:
    """Relink an asset globally using streamed file upload with atomic staging and verification."""
    res = await pipeline.relink_uploaded_media(
        project_id="all",
        asset_id=asset_id,
        upload_file=file,
        force=force,
        expected_sha256=expected_sha256,
    )
    return MediaRelinkResponse(
        asset=MediaAssetResponse(**res["asset"].__dict__),
        match_status=res["match_status"],
        warnings=res["warnings"],
        comparison=res["comparison"],
        relinked_at=res["relinked_at"],
    )


@global_media_router.post("/reconcile-availability", response_model=MediaReconcileResponse)
def reconcile_availability_global(
    service: MediaService = Depends(get_media_service),
) -> MediaReconcileResponse:
    """Reconcile missing files across all media assets (e.g. after external drive reconnection)."""
    res = service.reconcile_missing_media(project_id="all")
    return MediaReconcileResponse(**res)


@global_media_router.get("/deduplication/stats", response_model=MediaDeduplicationStatsResponse)
@global_media_router.get("/deduplication-stats", response_model=MediaDeduplicationStatsResponse)
def get_deduplication_stats_global(
    service: MediaService = Depends(get_media_service),
) -> MediaDeduplicationStatsResponse:
    """Get global media deduplication and reference statistics."""
    stats = service.get_deduplication_stats()
    return MediaDeduplicationStatsResponse(**stats)


@global_media_router.post("/deduplication/reconcile")
@global_media_router.post("/reconcile-references")
def reconcile_references_global(
    service: MediaService = Depends(get_media_service),
):
    """Reconcile and synchronize stored media reference counts."""
    return service.reconcile_reference_counts()


