"""Pydantic data models and schemas for Timeline, Tracks, Clips, Commands, and AI Assistant."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrackType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    OVERLAY = "overlay"


class TrackSubtype(str, Enum):
    MAIN_VIDEO = "main_video"
    SECONDARY_VIDEO = "secondary_video"
    B_ROLL = "b_roll"
    SOURCE_AUDIO = "source_audio"
    BGM = "bgm"
    VOICEOVER = "voiceover"
    SFX = "sfx"
    TEXT = "text"
    CAPTION = "caption"
    GRAPHICS = "graphics"


class ClipType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    OVERLAY = "overlay"
    CAPTION = "caption"


class CommandType(str, Enum):
    INSERT_CLIP = "InsertClip"
    MOVE_CLIP = "MoveClip"
    TRIM_CLIP = "TrimClip"
    SPLIT_CLIP = "SplitClip"
    DELETE_CLIP = "DeleteClip"
    DUPLICATE_CLIP = "DuplicateClip"
    ADD_TRACK = "AddTrack"
    REMOVE_TRACK = "RemoveTrack"
    UPDATE_TRACK = "UpdateTrack"
    UPDATE_CLIP_PROPS = "UpdateClipProps"
    UPDATE_AUDIO_SETTINGS = "UpdateAudioSettings"
    ADD_TEXT_OVERLAY = "AddTextOverlay"
    BATCH = "Batch"


class TransformProps(BaseModel):
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    crop_reference: Optional[str] = None


class ContentProps(BaseModel):
    text: str = ""
    font_family: str = "Inter"
    font_size: int = 48
    color: str = "#FFFFFF"
    alignment: str = "center"  # "left", "center", "right"
    background_color: Optional[str] = None


class AudioProps(BaseModel):
    fade_in: float = 0.0
    fade_out: float = 0.0
    is_muted: bool = False


class TimelineClip(BaseModel):
    id: str
    timeline_id: str
    track_id: str
    source_media_id: Optional[str] = None
    clip_type: ClipType = ClipType.VIDEO
    name: str
    timeline_start: float
    timeline_end: float
    source_in: float = 0.0
    source_out: float = 0.0
    speed: float = 1.0
    volume: float = 1.0
    opacity: float = 1.0
    transform_props: TransformProps = Field(default_factory=TransformProps)
    content_props: ContentProps = Field(default_factory=ContentProps)
    audio_props: AudioProps = Field(default_factory=AudioProps)
    created_at: str
    updated_at: str

    @property
    def duration(self) -> float:
        return max(0.0, round(self.timeline_end - self.timeline_start, 4))


class TimelineTrack(BaseModel):
    id: str
    timeline_id: str
    name: str
    track_type: TrackType
    track_subtype: TrackSubtype = TrackSubtype.MAIN_VIDEO
    track_order: int = 0
    is_visible: bool = True
    is_muted: bool = False
    is_locked: bool = False
    height: int = 64
    created_at: str
    updated_at: str
    clips: List[TimelineClip] = Field(default_factory=list)


class TimelineRecord(BaseModel):
    id: str
    project_id: str
    name: str = "Main Sequence"
    duration: float = 0.0
    fps: int = 30
    canvas_width: int = 1080
    canvas_height: int = 1920
    time_base: str = "1/30"
    revision: int = 1
    is_active: bool = True
    created_at: str
    updated_at: str
    tracks: List[TimelineTrack] = Field(default_factory=list)


class CreateTimelineRequest(BaseModel):
    name: str = "Main Sequence"
    fps: int = 30
    canvas_width: int = 1080
    canvas_height: int = 1920
    create_default_tracks: bool = True


class UpdateTimelineSettingsRequest(BaseModel):
    name: Optional[str] = None
    fps: Optional[int] = None
    canvas_width: Optional[int] = None
    canvas_height: Optional[int] = None


class CreateTrackRequest(BaseModel):
    name: str
    track_type: TrackType
    track_subtype: Optional[TrackSubtype] = None
    track_order: Optional[int] = None


class UpdateTrackRequest(BaseModel):
    name: Optional[str] = None
    is_visible: Optional[bool] = None
    is_muted: Optional[bool] = None
    is_locked: Optional[bool] = None
    track_order: Optional[int] = None
    height: Optional[int] = None


class InsertClipRequest(BaseModel):
    track_id: str
    source_media_id: Optional[str] = None
    clip_type: ClipType = ClipType.VIDEO
    name: str
    timeline_start: float
    duration: float
    source_in: float = 0.0
    speed: float = 1.0
    volume: float = 1.0
    transform_props: Optional[TransformProps] = None
    content_props: Optional[ContentProps] = None
    audio_props: Optional[AudioProps] = None


class MoveClipRequest(BaseModel):
    clip_id: str
    new_timeline_start: float
    new_track_id: Optional[str] = None


class TrimClipRequest(BaseModel):
    clip_id: str
    new_timeline_start: Optional[float] = None
    new_timeline_end: Optional[float] = None
    new_source_in: Optional[float] = None
    new_source_out: Optional[float] = None


class SplitClipRequest(BaseModel):
    clip_id: str
    split_time: float  # Absolute timeline time


class UpdateClipPropsRequest(BaseModel):
    clip_id: str
    name: Optional[str] = None
    speed: Optional[float] = None
    volume: Optional[float] = None
    opacity: Optional[float] = None
    transform_props: Optional[TransformProps] = None
    content_props: Optional[ContentProps] = None
    audio_props: Optional[AudioProps] = None


class AddTextOverlayRequest(BaseModel):
    track_id: Optional[str] = None  # Will create or find overlay track if None
    text: str
    timeline_start: float
    duration: float = 5.0
    font_size: int = 48
    color: str = "#FFFFFF"
    alignment: str = "center"
    x: float = 0.0
    y: float = 0.0


class TimelineCommandRecord(BaseModel):
    id: str
    timeline_id: str
    command_type: str
    payload: Dict[str, Any]
    inverse_payload: Dict[str, Any]
    revision_before: int
    revision_after: int
    description: str
    executed_by: str = "user"
    is_undone: bool = False
    created_at: str


class TimelineHistoryResponse(BaseModel):
    timeline_id: str
    current_revision: int
    can_undo: bool
    can_redo: bool
    history: List[TimelineCommandRecord]


# ---------------------------------------------------------------------------
# AI Assistant Schemas
# ---------------------------------------------------------------------------

class AIPlanOperation(BaseModel):
    command_type: CommandType
    description: str
    parameters: Dict[str, Any]


class AIEditingPlan(BaseModel):
    id: str
    conversation_id: str
    project_id: str
    timeline_id: str
    target_revision: int
    user_instruction: str
    explanation: str
    operations: List[AIPlanOperation]
    warnings: List[str] = Field(default_factory=list)
    status: str = "proposed"  # "proposed", "approved", "rejected", "executed", "failed"
    created_at: str
    executed_at: Optional[str] = None


class AIMessage(BaseModel):
    id: str
    conversation_id: str
    role: str  # "user", "assistant", "system"
    content: str
    context_snapshot: Dict[str, Any] = Field(default_factory=dict)
    plan: Optional[AIEditingPlan] = None
    created_at: str


class AIConversation(BaseModel):
    id: str
    project_id: str
    timeline_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[AIMessage] = Field(default_factory=list)


class SendAIMessageRequest(BaseModel):
    message: str
    playhead_time: Optional[float] = None
    selected_clip_id: Optional[str] = None
    selected_track_id: Optional[str] = None


class TimelineRenderRequest(BaseModel):
    preset_id: str = "shorts_reels_9_16"
    title: Optional[str] = None
    crf: Optional[int] = None
    include_audio: bool = True
