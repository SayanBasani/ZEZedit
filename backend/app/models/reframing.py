"""Data models and entities for Milestone 7 Smart Reframing & Subject Tracking."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DetectedSubject:
    """Individual subject bounding box detection at a specific timestamp."""

    timestamp: float
    box_x: float  # Absolute pixels in source coordinate system
    box_y: float
    box_w: float
    box_h: float
    confidence: float
    category: str = "face"  # 'face', 'person', 'upper_body', 'saliency'
    subject_id: Optional[str] = None

    @property
    def center_x(self) -> float:
        return self.box_x + (self.box_w / 2.0)

    @property
    def center_y(self) -> float:
        return self.box_y + (self.box_h / 2.0)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubjectTrack:
    """Temporal trajectory of a detected subject across sampled frames."""

    track_id: str
    category: str
    detections: List[DetectedSubject] = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0
    confidence_avg: float = 0.0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "category": self.category,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "confidence_avg": self.confidence_avg,
            "detections": [d.to_dict() for d in self.detections],
        }


@dataclass
class CropKeyframe:
    """Authoritative time-varying crop window representation.

    All preview rendering and FFmpeg export filtergraphs consume this exact representation.
    """

    timestamp: float
    crop_x: int  # Top-left X in source pixel coordinates
    crop_y: int  # Top-left Y in source pixel coordinates
    crop_w: int  # Width of crop window
    crop_h: int  # Height of crop window
    zoom: float = 1.0
    headroom: float = 0.15
    subject_count: int = 1
    framing_strategy: str = "single_subject"
    is_scene_boundary: bool = False
    is_manual_override: bool = False
    target_center_x: Optional[float] = None
    target_center_y: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReframingPlanRecord:
    """Database entity representing an analyzed reframing plan."""

    id: str
    project_id: str
    media_asset_id: str
    candidate_id: Optional[str]
    job_id: Optional[str]
    target_aspect_ratio: str  # '9:16', '1:1', '16:9'
    framing_strategy: str  # 'single_subject', 'two_person', 'group', 'action_object', 'fallback'
    status: str  # 'pending', 'tracking', 'completed', 'failed'
    source_width: int
    source_height: int
    output_width: int
    output_height: int
    start_time: float
    end_time: float
    duration: float
    base_zoom: float
    headroom_factor: float
    smoothing_window_seconds: float
    keyframes: List[CropKeyframe] = field(default_factory=list)
    detected_tracks: List[SubjectTrack] = field(default_factory=list)
    scene_cuts: List[float] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    active_revision_id: Optional[str] = None
    calculation_version: str = "2.0.0-m7"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["keyframes"] = [k.to_dict() for k in self.keyframes]
        d["detected_tracks"] = [t.to_dict() for t in self.detected_tracks]
        return d


@dataclass
class ReframingRevisionRecord:
    """Database entity representing an immutable or editable reframing revision."""

    id: str
    reframing_plan_id: str
    revision_number: int
    label: str
    is_ai_generated: bool
    manual_overrides: List[Dict[str, Any]] = field(default_factory=list)
    effective_keyframes: List[CropKeyframe] = field(default_factory=list)
    render_job_id: Optional[str] = None
    rendered_video_path: Optional[str] = None
    rendered_duration: Optional[float] = None
    rendered_file_size_bytes: Optional[int] = None
    rendered_at: Optional[str] = None
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["effective_keyframes"] = [k.to_dict() for k in self.effective_keyframes]
        return d
