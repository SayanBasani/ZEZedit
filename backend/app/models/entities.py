"""Data models and entities for Projects, Media Assets, Jobs, Settings, and Events."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProjectRecord:
    id: str
    name: str
    description: Optional[str]
    status: str
    project_config: Dict[str, Any]
    storage_subdir: str
    created_at: str
    updated_at: str
    last_opened_at: Optional[str] = None
    archived_at: Optional[str] = None


@dataclass
class MediaAssetRecord:
    id: str
    project_id: str
    original_filename: str
    storage_path: str
    is_external: bool
    media_type: str
    file_size_bytes: int
    mime_type: Optional[str]
    duration_seconds: Optional[float]
    width: Optional[int]
    height: Optional[int]
    fps: Optional[float]
    video_codec: Optional[str]
    audio_codec: Optional[str]
    availability_status: str
    proxy_reference_path: Optional[str]
    thumbnail_reference_path: Optional[str]
    metadata_status: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    proxy_status: str = "none"


@dataclass
class JobRecord:
    id: str
    project_id: Optional[str]
    job_type: str
    status: str
    priority: int
    progress_pct: float
    current_stage: Optional[str]
    worker_id: Optional[str]
    worker_pid: Optional[int]
    input_config: Dict[str, Any]
    result_metadata: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int
    max_attempts: int
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    cancellation_requested_at: Optional[str]
    cancelled_at: Optional[str]
    updated_at: str


@dataclass
class ProjectEventRecord:
    id: str
    project_id: str
    event_type: str
    event_summary: str
    payload: Dict[str, Any]
    created_at: str


@dataclass
class AnalysisRunRecord:
    id: str
    media_asset_id: str
    project_id: str
    status: str
    profile: str
    config_json: Dict[str, Any]
    progress_pct: float
    current_stage: Optional[str]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class TranscriptSegmentRecord:
    id: str
    analysis_run_id: str
    media_asset_id: str
    start_time: float
    end_time: float
    text: str
    language: Optional[str]
    confidence: Optional[float]
    words: list[Dict[str, Any]]
    created_at: str


@dataclass
class SpeechTurnRecord:
    id: str
    analysis_run_id: str
    media_asset_id: str
    start_time: float
    end_time: float
    speaker_label: str
    text: str
    segment_ids: list[str]
    turn_type: str
    created_at: str


@dataclass
class VideoSceneRecord:
    id: str
    analysis_run_id: str
    media_asset_id: str
    scene_index: int
    start_time: float
    end_time: float
    representative_timestamp: float
    thumbnail_path: Optional[str]
    change_score: float
    created_at: str


@dataclass
class SampledFrameRecord:
    id: str
    analysis_run_id: str
    media_asset_id: str
    timestamp: float
    frame_path: str
    scene_id: Optional[str]
    width: int
    height: int
    created_at: str


@dataclass
class VisualObservationRecord:
    id: str
    analysis_run_id: str
    media_asset_id: str
    timestamp: float
    frame_id: Optional[str]
    category: str
    description: str
    provider_model: str
    confidence: float
    created_at: str


@dataclass
class ShortsCandidateRecord:
    id: str
    project_id: str
    media_asset_id: str
    analysis_run_id: str
    start_time: float
    end_time: float
    duration: float
    suggested_start_time: float
    suggested_end_time: float
    is_user_modified: bool
    title: str
    suggested_title: str
    description: str
    category: str
    secondary_categories: list[str]
    quality_score: float
    score_breakdown: Dict[str, Any]
    gate_results: Dict[str, Any]
    warnings: list[str]
    missing_evidence: list[str]
    review_status: str
    rejection_reason: Optional[str]
    transcript_references: list[str]
    scene_references: list[str]
    visual_evidence: list[Dict[str, Any]]
    audio_evidence: list[Dict[str, Any]]
    ai_explanation: Dict[str, Any]
    scoring_version: str
    created_at: str
    updated_at: str
    job_id: Optional[str] = None
    alternative_of_candidate_id: Optional[str] = None
    overlap_group_id: Optional[str] = None
    queued_for_render: bool = False
