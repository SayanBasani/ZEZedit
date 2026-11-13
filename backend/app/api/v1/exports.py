"""REST API endpoints for rendering engine, export presets, and automatic Shorts generation."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.core.config import Settings, get_settings
from app.core.errors import AppError, NotFoundError, ProcessingError, ValidationError
from app.core.storage import StorageLayout
from app.models.export import AudioConfig, CaptionConfig, ExportPreset, RenderExportRequest
from app.services.export_service import ExportService
from pydantic import BaseModel, Field

logger = logging.getLogger("zezedit.api.exports")

router = APIRouter(prefix="/projects/{project_id}/exports", tags=["exports-and-rendering"])


class BatchExportRequest(BaseModel):
    candidate_ids: List[str] = Field(..., min_length=1, description="List of candidate IDs to render into Shorts")
    preset_id: str = Field(default="shorts_reels_9_16", description="Export preset ID (e.g. 'shorts_reels_9_16')")
    caption_config: Optional[CaptionConfig] = None
    audio_config: Optional[AudioConfig] = None
    custom_tag: Optional[str] = None


class BatchExportItem(BaseModel):
    candidate_id: str
    export_id: str
    job_id: str
    status: str
    output_filename: str


class BatchExportResponse(BaseModel):
    batch_id: str
    project_id: str
    total_requested: int
    total_submitted: int
    items: List[BatchExportItem]
    skipped_candidates: List[Dict[str, str]] = Field(default_factory=list)


def get_export_service(request: Request) -> ExportService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return ExportService(settings=settings, db_path=layout.db_file)


# -----------------------------------------------------------------------------
# Presets
# -----------------------------------------------------------------------------

@router.get("/presets", response_model=List[ExportPreset])
def list_export_presets(service: ExportService = Depends(get_export_service)):
    """List standard export presets (Shorts/Reels 9:16, Landscape 16:9, Square 1:1)."""
    return service.get_presets()


# -----------------------------------------------------------------------------
# Render Initiation & Preview
# -----------------------------------------------------------------------------

@router.post("/render")
def create_export_render_job(
    project_id: str,
    payload: RenderExportRequest,
    background_tasks: BackgroundTasks,
    run_synchronously: bool = Query(False, description="Run render synchronously in request (useful for testing)"),
    service: ExportService = Depends(get_export_service),
):
    """Enqueue a candidate export render job."""
    try:
        res = service.submit_export_job(project_id=project_id, request=payload)
        job_id = res["job_id"]

        if run_synchronously:
            # Execute synchronously in this thread
            exec_res = service.execute_render_job(job_id)
            return {**res, "render_result": exec_res}
        else:
            # Dispatch to background task worker
            background_tasks.add_task(service.execute_render_job, job_id)
            return res
    except (NotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to enqueue export render: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/batch", response_model=BatchExportResponse)
def create_batch_export_jobs(
    project_id: str,
    payload: BatchExportRequest,
    background_tasks: BackgroundTasks,
    run_synchronously: bool = Query(False, description="Run batch renders synchronously"),
    service: ExportService = Depends(get_export_service),
) -> BatchExportResponse:
    """Enqueue parallel independent render jobs for multiple approved candidate shorts."""
    import uuid

    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    submitted_items: List[BatchExportItem] = []
    skipped_cands: List[Dict[str, str]] = []

    for cid in payload.candidate_ids:
        try:
            render_req = RenderExportRequest(
                candidate_id=cid,
                preset_id=payload.preset_id,
                caption_config=payload.caption_config or CaptionConfig(),
                audio_config=payload.audio_config or AudioConfig(),
            )
            res = service.submit_export_job(project_id=project_id, request=render_req)
            job_id = res["job_id"]
            export_id = res["export_id"]

            if run_synchronously:
                service.execute_render_job(job_id)

            submitted_items.append(
                BatchExportItem(
                    candidate_id=cid,
                    export_id=export_id,
                    job_id=job_id,
                    status="rendering" if run_synchronously else "queued",
                    output_filename=res.get("output_filename", f"{export_id}.mp4"),
                )
            )

            if not run_synchronously:
                background_tasks.add_task(service.execute_render_job, job_id)

        except Exception as exc:
            logger.warning("Skipping candidate '%s' in batch export: %s", cid, exc)
            skipped_cands.append({"candidate_id": cid, "reason": str(exc)})

    return BatchExportResponse(
        batch_id=batch_id,
        project_id=project_id,
        total_requested=len(payload.candidate_ids),
        total_submitted=len(submitted_items),
        items=submitted_items,
        skipped_candidates=skipped_cands,
    )


@router.post("/preview")
def create_export_preview(
    project_id: str,
    payload: RenderExportRequest,
    service: ExportService = Depends(get_export_service),
):
    """Generate a fast 480p preview clip for interactive inspection."""
    try:
        payload.is_preview = True
        res = service.submit_export_job(project_id=project_id, request=payload)
        exec_res = service.execute_render_job(res["job_id"])
        return {**res, "preview_result": exec_res}
    except (NotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to generate export preview: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# -----------------------------------------------------------------------------
# Export Record Management
# -----------------------------------------------------------------------------

@router.get("")
def list_exports(
    project_id: str,
    candidate_id: Optional[str] = Query(None),
    media_asset_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    service: ExportService = Depends(get_export_service),
):
    """List exports for a project, optionally filtered by candidate or media asset."""
    exports = service.list_exports(
        project_id=project_id,
        candidate_id=candidate_id,
        media_asset_id=media_asset_id,
        limit=limit,
    )
    return {"items": [e.__dict__ for e in exports], "count": len(exports)}


@router.get("/{export_id}")
def get_export_details(
    project_id: str,
    export_id: str,
    service: ExportService = Depends(get_export_service),
):
    """Fetch details of a single export record."""
    try:
        exp = service.get_export(project_id=project_id, export_id=export_id)
        return exp.__dict__
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{export_id}/cancel")
def cancel_export(
    project_id: str,
    export_id: str,
    service: ExportService = Depends(get_export_service),
):
    """Cancel an active export render job."""
    try:
        return service.cancel_export_render(project_id=project_id, export_id=export_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{export_id}")
def delete_export(
    project_id: str,
    export_id: str,
    service: ExportService = Depends(get_export_service),
):
    """Delete an export record and its output video file."""
    try:
        service.delete_export(project_id=project_id, export_id=export_id)
        return {"export_id": export_id, "deleted": True}
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# -----------------------------------------------------------------------------
# Video Streaming with HTTP 206 Partial Content
# -----------------------------------------------------------------------------

@router.get("/{export_id}/video")
def stream_export_video(
    project_id: str,
    export_id: str,
    request: Request,
    service: ExportService = Depends(get_export_service),
):
    """Stream rendered export MP4 video with HTTP 206 byte-range seeking support."""
    try:
        exp = service.get_export(project_id=project_id, export_id=export_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not exp.output_path:
        raise HTTPException(status_code=404, detail="Export video has not been rendered yet.")

    video_path = Path(exp.output_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Export video file missing from disk: {video_path.name}")

    file_size = video_path.stat().st_size
    range_header = request.headers.get("range")

    if not range_header:
        return FileResponse(
            str(video_path),
            media_type="video/mp4",
            filename=video_path.name,
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
        end = min(end, file_size - 1)
        content_length = end - start + 1
    except Exception:
        raise HTTPException(status_code=416, detail="Requested range not satisfiable")

    def iter_bytes():
        with open(video_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            chunk_size = 1024 * 64
            while remaining > 0:
                read_len = min(remaining, chunk_size)
                data = f.read(read_len)
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        iter_bytes(),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type="video/mp4",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        },
    )


# -----------------------------------------------------------------------------
# Direct Download Endpoint
# -----------------------------------------------------------------------------

@router.get("/{export_id}/download")
def download_export_video(
    project_id: str,
    export_id: str,
    service: ExportService = Depends(get_export_service),
):
    """Download the rendered export MP4 file as an attachment."""
    try:
        exp = service.get_export(project_id=project_id, export_id=export_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not exp.output_path:
        raise HTTPException(status_code=404, detail="Export video has not been rendered yet.")

    video_path = Path(exp.output_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Export video file missing from disk: {video_path.name}")

    filename = exp.output_filename or video_path.name
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=filename,
    )
