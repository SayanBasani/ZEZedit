"""REST API routes for Timeline Editing, Commands, Undo/Redo, AI Video Editor, and Rendering."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request

from app.core.config import Settings
from app.models.timeline import (
    AddTextOverlayRequest,
    AIConversation,
    AIEditingPlan,
    AIMessage,
    CreateTimelineRequest,
    CreateTrackRequest,
    InsertClipRequest,
    MoveClipRequest,
    SendAIMessageRequest,
    SplitClipRequest,
    TimelineClip,
    TimelineHistoryResponse,
    TimelineRecord,
    TimelineRenderRequest,
    TimelineTrack,
    TrimClipRequest,
    UpdateClipPropsRequest,
    UpdateTimelineSettingsRequest,
    UpdateTrackRequest,
)
from app.services.ai_editor_service import AIEditorService
from app.services.timeline_command_service import TimelineCommandService
from app.services.timeline_renderer import TimelineRenderer
from app.services.timeline_service import TimelineService

logger = logging.getLogger("zezedit.api.timeline")

router = APIRouter(prefix="/projects/{project_id}", tags=["timeline"])


def get_timeline_service(request: Request) -> TimelineService:
    settings: Settings = getattr(request.app.state, "settings", None)
    return TimelineService(settings=settings)


def get_command_service(request: Request) -> TimelineCommandService:
    settings: Settings = getattr(request.app.state, "settings", None)
    return TimelineCommandService(settings=settings)


def get_ai_editor_service(request: Request) -> AIEditorService:
    settings: Settings = getattr(request.app.state, "settings", None)
    return AIEditorService(settings=settings)


def get_timeline_renderer(request: Request) -> TimelineRenderer:
    settings: Settings = getattr(request.app.state, "settings", None)
    return TimelineRenderer(settings=settings)


# ---------------------------------------------------------------------------
# Timeline CRUD & Settings
# ---------------------------------------------------------------------------

@router.get("/timeline", response_model=TimelineRecord)
def get_active_timeline(
    project_id: str,
    svc: TimelineService = Depends(get_timeline_service),
) -> TimelineRecord:
    """Retrieve the active project timeline or initialize default tracks."""
    return svc.get_or_create_default_timeline(project_id)


@router.post("/timelines", response_model=TimelineRecord)
def create_timeline(
    project_id: str,
    body: CreateTimelineRequest,
    svc: TimelineService = Depends(get_timeline_service),
) -> TimelineRecord:
    """Create a new sequence for a project."""
    return svc.create_timeline(project_id, body)


@router.get("/timelines/{timeline_id}", response_model=TimelineRecord)
def get_timeline(
    project_id: str,
    timeline_id: str,
    svc: TimelineService = Depends(get_timeline_service),
) -> TimelineRecord:
    """Retrieve timeline by ID."""
    return svc.get_timeline(timeline_id)


@router.patch("/timelines/{timeline_id}/settings", response_model=TimelineRecord)
def update_timeline_settings(
    project_id: str,
    timeline_id: str,
    body: UpdateTimelineSettingsRequest,
    svc: TimelineService = Depends(get_timeline_service),
) -> TimelineRecord:
    """Update timeline canvas dimensions, fps, or sequence name."""
    return svc.update_timeline_settings(timeline_id, body)


# ---------------------------------------------------------------------------
# Track Management
# ---------------------------------------------------------------------------

@router.post("/timelines/{timeline_id}/tracks", response_model=TimelineTrack)
def add_track(
    project_id: str,
    timeline_id: str,
    body: CreateTrackRequest,
    svc: TimelineService = Depends(get_timeline_service),
) -> TimelineTrack:
    """Add a video, audio, or overlay track to the timeline."""
    return svc.add_track(timeline_id, body)


@router.patch("/timelines/{timeline_id}/tracks/{track_id}", response_model=TimelineTrack)
def update_track(
    project_id: str,
    timeline_id: str,
    track_id: str,
    body: UpdateTrackRequest,
    svc: TimelineService = Depends(get_timeline_service),
) -> TimelineTrack:
    """Update track mute, lock, visibility, or name."""
    return svc.update_track(track_id, body)


@router.delete("/timelines/{timeline_id}/tracks/{track_id}")
def delete_track(
    project_id: str,
    timeline_id: str,
    track_id: str,
    svc: TimelineService = Depends(get_timeline_service),
) -> Dict[str, str]:
    """Delete a track and all its clips."""
    svc.delete_track(track_id)
    return {"message": f"Track '{track_id}' deleted."}


# ---------------------------------------------------------------------------
# Clip Operations (Validated Reversible Commands)
# ---------------------------------------------------------------------------

@router.post("/timelines/{timeline_id}/clips", response_model=TimelineClip)
def insert_clip(
    project_id: str,
    timeline_id: str,
    body: InsertClipRequest,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> TimelineClip:
    """Insert a media or overlay clip onto a track."""
    return cmd_svc.insert_clip(timeline_id, body, executed_by="user")


@router.post("/timelines/{timeline_id}/clips/move", response_model=TimelineClip)
def move_clip(
    project_id: str,
    timeline_id: str,
    body: MoveClipRequest,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> TimelineClip:
    """Move clip to a new timeline start time or target track."""
    return cmd_svc.move_clip(timeline_id, body, executed_by="user")


@router.post("/timelines/{timeline_id}/clips/trim", response_model=TimelineClip)
def trim_clip(
    project_id: str,
    timeline_id: str,
    body: TrimClipRequest,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> TimelineClip:
    """Trim clip in-point or out-point."""
    return cmd_svc.trim_clip(timeline_id, body, executed_by="user")


@router.post("/timelines/{timeline_id}/clips/split", response_model=List[TimelineClip])
def split_clip(
    project_id: str,
    timeline_id: str,
    body: SplitClipRequest,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> List[TimelineClip]:
    """Split a clip into two pieces at playhead/timestamp."""
    left, right = cmd_svc.split_clip(timeline_id, body, executed_by="user")
    return [left, right]


@router.delete("/timelines/{timeline_id}/clips/{clip_id}")
def delete_clip(
    project_id: str,
    timeline_id: str,
    clip_id: str,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> Dict[str, str]:
    """Delete a clip (reversible via Undo)."""
    cmd_svc.delete_clip(timeline_id, clip_id, executed_by="user")
    return {"message": f"Clip '{clip_id}' deleted."}


@router.post("/timelines/{timeline_id}/clips/{clip_id}/duplicate", response_model=TimelineClip)
def duplicate_clip(
    project_id: str,
    timeline_id: str,
    clip_id: str,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> TimelineClip:
    """Duplicate a clip."""
    return cmd_svc.duplicate_clip(timeline_id, clip_id, executed_by="user")


@router.patch("/timelines/{timeline_id}/clips/{clip_id}", response_model=TimelineClip)
def update_clip_props(
    project_id: str,
    timeline_id: str,
    clip_id: str,
    body: UpdateClipPropsRequest,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> TimelineClip:
    """Update volume, speed, transform, or content properties."""
    body.clip_id = clip_id
    return cmd_svc.update_clip_props(timeline_id, body, executed_by="user")


@router.post("/timelines/{timeline_id}/overlays/text", response_model=TimelineClip)
def add_text_overlay(
    project_id: str,
    timeline_id: str,
    body: AddTextOverlayRequest,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> TimelineClip:
    """Add a text overlay clip."""
    return cmd_svc.add_text_overlay(timeline_id, body, executed_by="user")


# ---------------------------------------------------------------------------
# Persistent History: Undo & Redo
# ---------------------------------------------------------------------------

@router.get("/timelines/{timeline_id}/history", response_model=TimelineHistoryResponse)
def get_history(
    project_id: str,
    timeline_id: str,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> TimelineHistoryResponse:
    """Inspect history log and undo/redo availability."""
    return cmd_svc.get_history(timeline_id)


@router.post("/timelines/{timeline_id}/history/undo", response_model=TimelineRecord)
def undo(
    project_id: str,
    timeline_id: str,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> TimelineRecord:
    """Revert the most recent operation."""
    return cmd_svc.undo(timeline_id)


@router.post("/timelines/{timeline_id}/history/redo", response_model=TimelineRecord)
def redo(
    project_id: str,
    timeline_id: str,
    cmd_svc: TimelineCommandService = Depends(get_command_service),
) -> TimelineRecord:
    """Reapply the next undone operation."""
    return cmd_svc.redo(timeline_id)


# ---------------------------------------------------------------------------
# AI Video Editor Assistant
# ---------------------------------------------------------------------------

@router.get("/timelines/{timeline_id}/ai/conversation", response_model=AIConversation)
def get_ai_conversation(
    project_id: str,
    timeline_id: str,
    ai_svc: AIEditorService = Depends(get_ai_editor_service),
) -> AIConversation:
    """Retrieve active AI editing conversation and message history."""
    return ai_svc.get_or_create_conversation(project_id, timeline_id)


@router.post("/timelines/{timeline_id}/ai/messages", response_model=AIMessage)
def send_ai_message(
    project_id: str,
    timeline_id: str,
    body: SendAIMessageRequest,
    ai_svc: AIEditorService = Depends(get_ai_editor_service),
) -> AIMessage:
    """Send natural language instruction to AI editor; returns answer or proposed plan."""
    conv = ai_svc.get_or_create_conversation(project_id, timeline_id)
    return ai_svc.send_message(conv.id, body)


@router.get("/timelines/{timeline_id}/ai/plans/{plan_id}", response_model=AIEditingPlan)
def get_plan(
    project_id: str,
    timeline_id: str,
    plan_id: str,
    ai_svc: AIEditorService = Depends(get_ai_editor_service),
) -> AIEditingPlan:
    """Get AI editing plan details."""
    return ai_svc.get_plan(plan_id)


@router.post("/timelines/{timeline_id}/ai/plans/{plan_id}/approve", response_model=TimelineRecord)
def approve_plan(
    project_id: str,
    timeline_id: str,
    plan_id: str,
    ai_svc: AIEditorService = Depends(get_ai_editor_service),
) -> TimelineRecord:
    """Approve and safely execute all operations in an AI editing plan."""
    return ai_svc.approve_and_execute_plan(plan_id)


@router.post("/timelines/{timeline_id}/ai/plans/{plan_id}/reject", response_model=AIEditingPlan)
def reject_plan(
    project_id: str,
    timeline_id: str,
    plan_id: str,
    ai_svc: AIEditorService = Depends(get_ai_editor_service),
) -> AIEditingPlan:
    """Reject an AI editing plan."""
    return ai_svc.reject_plan(plan_id)


# ---------------------------------------------------------------------------
# Timeline Rendering Integration
# ---------------------------------------------------------------------------

@router.post("/timelines/{timeline_id}/render")
def render_timeline(
    project_id: str,
    timeline_id: str,
    body: TimelineRenderRequest,
    renderer: TimelineRenderer = Depends(get_timeline_renderer),
) -> Dict[str, Any]:
    """Render the timeline using the Milestone 8 FFmpeg export engine."""
    return renderer.submit_timeline_render(project_id, timeline_id, body)
