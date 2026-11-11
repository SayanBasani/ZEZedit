"""Smart Reframing, Subject Tracking & Portrait Composition REST API endpoints."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.storage import StorageLayout
from app.services.reframing_service import ReframingService

logger = logging.getLogger("zezedit.api.reframing")

router = APIRouter(prefix="/projects/{project_id}", tags=["smart-reframing"])


# --- Dependencies ---

def get_reframing_service(request: Request) -> ReframingService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return ReframingService(settings=settings, db_path=layout.db_file)


# --- Request & Response Schemas ---

class CreateReframingPlanRequest(BaseModel):
    candidate_id: Optional[str] = None
    target_aspect_ratio: str = Field(default="9:16", description="'9:16', '1:1', or '16:9'")
    framing_strategy: str = Field(default="auto", description="'auto', 'single_subject', 'two_person', 'group'")
    base_zoom: float = Field(default=1.0, ge=0.8, le=2.5)
    headroom_factor: float = Field(default=0.15, ge=0.05, le=0.35)
    smoothing_window: float = Field(default=0.8, ge=0.2, le=3.0)


class ManualOverrideItem(BaseModel):
    timestamp: float
    crop_x: Optional[int] = None
    crop_y: Optional[int] = None
    zoom: Optional[float] = Field(default=1.0, ge=0.8, le=3.0)
    headroom: Optional[float] = Field(default=0.15, ge=0.05, le=0.35)
    target_center_x: Optional[float] = None
    target_center_y: Optional[float] = None
    action: str = Field(default="override")


class SaveOverridesRequest(BaseModel):
    manual_overrides: List[ManualOverrideItem]
    revision_label: Optional[str] = None


class RenderRevisionRequest(BaseModel):
    revision_id: Optional[str] = None


# --- Endpoints ---

@router.post(
    "/media/{media_asset_id}/reframing/analyze",
    status_code=status.HTTP_201_CREATED,
)
def create_reframing_plan(
    project_id: str,
    media_asset_id: str,
    payload: CreateReframingPlanRequest,
    service: ReframingService = Depends(get_reframing_service),
):
    """Analyze media clip, track subjects, and compute authoritative initial 9:16 reframing plan."""
    plan = service.analyze_and_create_plan(
        project_id=project_id,
        media_asset_id=media_asset_id,
        candidate_id=payload.candidate_id,
        target_aspect_ratio=payload.target_aspect_ratio,
        framing_strategy=payload.framing_strategy,
        base_zoom=payload.base_zoom,
        headroom_factor=payload.headroom_factor,
        smoothing_window=payload.smoothing_window,
    )
    return plan.to_dict()


@router.get("/reframing/{plan_id}")
def get_reframing_plan(
    project_id: str,
    plan_id: str,
    service: ReframingService = Depends(get_reframing_service),
):
    """Retrieve reframing plan with keyframes, subject tracks, and active revision."""
    return service.get_plan(project_id=project_id, plan_id=plan_id)


@router.get("/reframing/{plan_id}/preview")
def preview_crop_geometry(
    project_id: str,
    plan_id: str,
    timestamp: float = Query(..., ge=0.0, description="Timestamp in seconds"),
    service: ReframingService = Depends(get_reframing_service),
):
    """Calculate exact interpolated crop coordinates [crop_x, crop_y, crop_w, crop_h] at timestamp."""
    return service.preview_crop_at(
        project_id=project_id,
        plan_id=plan_id,
        timestamp=timestamp,
    )


@router.post("/reframing/{plan_id}/overrides")
def save_manual_overrides(
    project_id: str,
    plan_id: str,
    payload: SaveOverridesRequest,
    service: ReframingService = Depends(get_reframing_service),
):
    """Save manual crop keyframe overrides and persist as a new non-destructive revision."""
    overrides_dicts = [ov.model_dump() for ov in payload.manual_overrides]
    return service.save_manual_overrides(
        project_id=project_id,
        plan_id=plan_id,
        manual_overrides=overrides_dicts,
        revision_label=payload.revision_label,
    )


@router.get("/reframing/{plan_id}/revisions")
def list_reframing_revisions(
    project_id: str,
    plan_id: str,
    service: ReframingService = Depends(get_reframing_service),
):
    """List all saved revisions and render history for a reframing plan."""
    return service.list_revisions(project_id=project_id, plan_id=plan_id)


@router.post("/reframing/{plan_id}/revisions/{revision_id}/restore")
def restore_reframing_revision(
    project_id: str,
    plan_id: str,
    revision_id: str,
    service: ReframingService = Depends(get_reframing_service),
):
    """Activate a prior revision as the authoritative framing plan."""
    return service.restore_revision(
        project_id=project_id,
        plan_id=plan_id,
        revision_id=revision_id,
    )


@router.post("/reframing/{plan_id}/render")
def render_reframed_video(
    project_id: str,
    plan_id: str,
    payload: Optional[RenderRevisionRequest] = None,
    service: ReframingService = Depends(get_reframing_service),
):
    """Render real vertical 9:16 MP4 video via FFmpeg using the revision's authoritative keyframes."""
    rev_id = payload.revision_id if payload else None
    return service.render_revision(
        project_id=project_id,
        plan_id=plan_id,
        revision_id=rev_id,
    )


@router.get("/reframing/{plan_id}/video")
def get_rendered_video_file(
    project_id: str,
    plan_id: str,
    revision_id: Optional[str] = Query(None),
    service: ReframingService = Depends(get_reframing_service),
):
    """Serve or stream the rendered vertical MP4 video file."""
    revisions = service.list_revisions(project_id, plan_id)
    if not revisions:
        raise NotFoundError("No revisions found for this reframing plan.")

    target_rev = None
    if revision_id:
        matching = [r for r in revisions if r["id"] == revision_id]
        if matching:
            target_rev = matching[0]
    else:
        # Find latest rendered revision
        rendered = [r for r in revisions if r.get("rendered_video_path")]
        if rendered:
            target_rev = rendered[-1]

    if not target_rev or not target_rev.get("rendered_video_path"):
        raise NotFoundError("Video has not been rendered yet for this revision. Call POST /render first.")

    video_path = Path(target_rev["rendered_video_path"])
    if not video_path.exists():
        raise NotFoundError(f"Rendered video file '{video_path.name}' is missing on disk.")

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video_path.name,
    )
