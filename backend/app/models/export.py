"""Domain models and Pydantic schemas for rendering engine, export presets, and captions."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CaptionConfig(BaseModel):
    """Configuration for subtitle and on-screen caption rendering."""

    mode: str = Field(
        default="word_highlight",
        description="Caption style: 'none', 'standard', 'word_highlight', 'phrase', 'sentence'",
    )
    font_family: str = Field(default="Arial", description="Font face family name")
    font_size: int = Field(default=24, ge=12, le=72, description="Font point size for target canvas")
    bold: bool = Field(default=True, description="Bold typeface")
    text_color: str = Field(default="#FFFFFF", description="Base font hex color (e.g. #FFFFFF)")
    highlight_color: str = Field(default="#FACC15", description="Spoken word highlight hex color (e.g. #FACC15 amber/yellow)")
    outline_color: str = Field(default="#000000", description="Text outline border color")
    outline_width: float = Field(default=2.5, ge=0.0, le=10.0, description="Outline stroke width in px")
    shadow_depth: float = Field(default=1.5, ge=0.0, le=10.0, description="Drop shadow depth in px")
    alignment: int = Field(default=2, ge=1, le=9, description="ASS alignment code (2 = bottom-center)")
    margin_v: int = Field(default=90, ge=10, le=500, description="Vertical safe margin from canvas edge in px")
    max_words_per_line: int = Field(default=5, ge=2, le=12, description="Maximum words displayed per phrase/burst")
    max_lines: int = Field(default=2, ge=1, le=4, description="Maximum concurrent lines")
    burn_in: bool = Field(default=True, description="Hardcode/burn captions into exported video")


class AudioConfig(BaseModel):
    """Configuration for audio filters, normalization, and volume adjustments."""

    volume: float = Field(default=1.0, ge=0.0, le=3.0, description="Linear volume multiplier (1.0 = 100%)")
    fade_in_seconds: float = Field(default=0.0, ge=0.0, le=5.0, description="Audio fade-in duration")
    fade_out_seconds: float = Field(default=0.0, ge=0.0, le=5.0, description="Audio fade-out duration")
    normalize_loudness: bool = Field(default=False, description="Apply EBU R128 loudness normalization")
    sample_rate: int = Field(default=48000, description="Output audio sample rate (Hz)")
    channels: int = Field(default=2, ge=1, le=2, description="Output audio channels (1=mono, 2=stereo)")


class ExportPreset(BaseModel):
    """Standardized output export preset specification."""

    preset_id: str
    name: str
    description: str
    target_aspect_ratio: str  # '9:16', '16:9', '1:1'
    target_width: int
    target_height: int
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    pixel_fmt: str = "yuv420p"
    fps: float = 30.0
    crf: int = 22
    video_bitrate: Optional[str] = None
    audio_bitrate: str = "128k"


STANDARD_EXPORT_PRESETS: Dict[str, ExportPreset] = {
    "shorts_reels_9_16": ExportPreset(
        preset_id="shorts_reels_9_16",
        name="YouTube Shorts / Reels (9:16)",
        description="Vertical portrait 1080x1920 high-quality H.264 video for YouTube Shorts, Instagram Reels, and TikTok.",
        target_aspect_ratio="9:16",
        target_width=1080,
        target_height=1920,
        crf=22,
        audio_bitrate="128k",
        fps=30.0,
    ),
    "landscape_16_9": ExportPreset(
        preset_id="landscape_16_9",
        name="Widescreen Landscape (16:9)",
        description="Standard widescreen 1920x1080 landscape video for YouTube, desktop monitors, and TV displays.",
        target_aspect_ratio="16:9",
        target_width=1920,
        target_height=1080,
        crf=22,
        audio_bitrate="128k",
        fps=30.0,
    ),
    "square_1_1": ExportPreset(
        preset_id="square_1_1",
        name="Square Social (1:1)",
        description="Square 1080x1080 video for Instagram posts, LinkedIn feeds, and Facebook video carousels.",
        target_aspect_ratio="1:1",
        target_width=1080,
        target_height=1080,
        crf=22,
        audio_bitrate="128k",
        fps=30.0,
    ),
    "portrait_4_5": ExportPreset(
        preset_id="portrait_4_5",
        name="Portrait Social (4:5)",
        description="Portrait 1080x1350 video for Instagram portrait feed and social posts.",
        target_aspect_ratio="4:5",
        target_width=1080,
        target_height=1350,
        crf=22,
        audio_bitrate="128k",
        fps=30.0,
    ),
    "standard_4_3": ExportPreset(
        preset_id="standard_4_3",
        name="Standard TV / Tablet (4:3)",
        description="Classic 1440x1080 video for standard monitors, presentations, and tablets.",
        target_aspect_ratio="4:3",
        target_width=1440,
        target_height=1080,
        crf=22,
        audio_bitrate="128k",
        fps=30.0,
    ),
    "tall_3_4": ExportPreset(
        preset_id="tall_3_4",
        name="Vertical Tablet (3:4)",
        description="Vertical 1080x1440 video for portrait tablets and reading feeds.",
        target_aspect_ratio="3:4",
        target_width=1080,
        target_height=1440,
        crf=22,
        audio_bitrate="128k",
        fps=30.0,
    ),
}


class RenderExportRequest(BaseModel):
    """Request payload to initiate a candidate export render job."""

    candidate_id: str = Field(..., description="ID of the approved candidate clip to render")
    preset_id: str = Field(default="shorts_reels_9_16", description="Export preset ID")
    reframing_plan_id: Optional[str] = Field(default=None, description="Optional reframing plan ID")
    framing_revision_id: Optional[str] = Field(default=None, description="Optional specific framing revision ID")
    title: Optional[str] = Field(default=None, description="Custom title for the export output")
    caption_config: Optional[CaptionConfig] = Field(default=None, description="Caption styling and mode settings")
    audio_config: Optional[AudioConfig] = Field(default=None, description="Audio levels and normalization")
    crf: Optional[int] = Field(default=None, ge=14, le=35, description="Optional custom CRF quality override")
    is_preview: bool = Field(default=False, description="Generate fast 480p preview rather than full 1080p")


class ValidationDetails(BaseModel):
    """Detailed post-render probe and decode verification data."""

    is_valid: bool = False
    duration: float = 0.0
    width: int = 0
    height: int = 0
    video_codec: str = ""
    audio_codec: Optional[str] = None
    pixel_fmt: str = ""
    file_size_bytes: int = 0
    playable: bool = False
    errors: List[str] = Field(default_factory=list)


@dataclass
class ExportRecord:
    """Dataclass mapping database record for an export."""

    id: str
    project_id: str
    candidate_id: Optional[str]
    media_asset_id: str
    reframing_plan_id: Optional[str]
    framing_revision_id: Optional[str]
    render_job_id: Optional[str]
    title: str
    export_preset: str
    target_aspect_ratio: str
    target_width: int
    target_height: int
    video_codec: str
    audio_codec: str
    pixel_fmt: str
    fps: float
    crf: int
    video_bitrate: Optional[str]
    audio_bitrate: str
    caption_config: Dict[str, Any]
    audio_config: Dict[str, Any]
    output_path: Optional[str]
    output_filename: str
    file_size_bytes: int
    duration_seconds: float
    status: str
    validation_status: str
    validation_details: Dict[str, Any]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]
