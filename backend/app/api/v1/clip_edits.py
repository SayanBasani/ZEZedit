"""Candidate clip editing, trimming, and reframing API endpoints."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.storage import StorageLayout
from app.services.clip_editing_service import ClipEditingService

logger = logging.getLogger("zezedit.api.clip_edits")

router = APIRouter(prefix="/projects/{project_id}", tags=["clip-edits"])


# --- Pydantic Schemas ---

class CandidateEditSaveRequest(BaseModel):
    edited_start_time: float = Field(..., ge=0.0, description="Start timestamp of edited clip in seconds")
    edited_end_time: float = Field(..., gt=0.0, description="End timestamp of edited clip in seconds")
    aspect_ratio: str = Field(default="9:16", description="Target aspect ratio: 9:16, 1:1, 16:9, 4:5")
    framing_mode: str = Field(default="center", description="Framing mode: center, manual, smart_tracking")
    manual_crop_x_pct: float = Field(default=50.0, ge=0.0, le=100.0, description="Horizontal crop center percentage")
    manual_crop_y_pct: float = Field(default=50.0, ge=0.0, le=100.0, description="Vertical crop center percentage")
    manual_crop_zoom: float = Field(default=1.0, ge=1.0, le=2.5, description="Digital zoom factor")
    tracked_subject_id: Optional[str] = Field(default=None, description="Optional tracked subject identifier")


class TrackCandidateRequest(BaseModel):
    target_aspect_ratio: str = Field(default="9:16", description="Target aspect ratio for tracking")


# --- Dependencies ---

def get_clip_editing_service(request: Request) -> ClipEditingService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return ClipEditingService(settings=settings, db_path=layout.db_file)


# --- Routes ---

@router.get(
    "/media/{media_asset_id}/candidates/{candidate_id}/edit",
    response_model=Dict[str, Any],
    summary="Get or initialize candidate clip edit state",
)
def get_candidate_edit(
    project_id: str,
    media_asset_id: str,
    candidate_id: str,
    service: ClipEditingService = Depends(get_clip_editing_service),
) -> Dict[str, Any]:
    """Retrieve existing edit state or initialize default draft from candidate discovery bounds."""
    try:
        return service.get_or_create_edit(candidate_id, project_id, media_asset_id)
    except NotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        logger.exception("Failed to get candidate edit: %s", err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


@router.put(
    "/media/{media_asset_id}/candidates/{candidate_id}/edit",
    response_model=Dict[str, Any],
    summary="Save candidate clip edit parameters",
)
def save_candidate_edit(
    project_id: str,
    media_asset_id: str,
    candidate_id: str,
    payload: CandidateEditSaveRequest,
    service: ClipEditingService = Depends(get_clip_editing_service),
) -> Dict[str, Any]:
    """Validate and persist edited timestamps, aspect ratio, framing mode, and manual crop offsets."""
    try:
        return service.save_edit(
            candidate_id=candidate_id,
            project_id=project_id,
            media_asset_id=media_asset_id,
            edited_start_time=payload.edited_start_time,
            edited_end_time=payload.edited_end_time,
            aspect_ratio=payload.aspect_ratio,
            framing_mode=payload.framing_mode,
            manual_crop_x_pct=payload.manual_crop_x_pct,
            manual_crop_y_pct=payload.manual_crop_y_pct,
            manual_crop_zoom=payload.manual_crop_zoom,
            tracked_subject_id=payload.tracked_subject_id,
        )
    except (ValidationError, ValueError) as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err))
    except NotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        logger.exception("Failed to save candidate edit: %s", err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


@router.post(
    "/media/{media_asset_id}/candidates/{candidate_id}/edit/reset",
    response_model=Dict[str, Any],
    summary="Reset candidate clip edit to original boundaries",
)
def reset_candidate_edit(
    project_id: str,
    media_asset_id: str,
    candidate_id: str,
    service: ClipEditingService = Depends(get_clip_editing_service),
) -> Dict[str, Any]:
    """Reset clip boundaries and framing back to initial discovery state."""
    try:
        return service.reset_to_original(candidate_id, project_id, media_asset_id)
    except NotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        logger.exception("Failed to reset candidate edit: %s", err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


@router.post(
    "/media/{media_asset_id}/candidates/{candidate_id}/edit/track",
    response_model=Dict[str, Any],
    summary="Run smart subject tracking on candidate interval",
)
def track_candidate_subjects(
    project_id: str,
    media_asset_id: str,
    candidate_id: str,
    payload: TrackCandidateRequest = TrackCandidateRequest(),
    service: ClipEditingService = Depends(get_clip_editing_service),
) -> Dict[str, Any]:
    """Execute smart subject tracking and generate portrait reframing keyframes for this clip."""
    try:
        return service.run_clip_tracking(
            candidate_id=candidate_id,
            project_id=project_id,
            media_asset_id=media_asset_id,
            target_aspect_ratio=payload.target_aspect_ratio,
        )
    except NotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        logger.exception("Failed to run clip tracking: %s", err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))
