"""Data models and entities for Projects, Media Assets, Jobs, Settings, and Events."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    sha256: Optional[str] = None
    integrity_status: Optional[str] = None
    upload_attempt_id: Optional[str] = None
    integrity_details_json: Optional[str] = None
    last_integrity_check: Optional[str] = None
    display_filename: Optional[str] = None
    file_extension: Optional[str] = None
    container_format: Optional[str] = None
    resolution_label: Optional[str] = None
    aspect_ratio: Optional[str] = None
    audio_stream_count: int = 0
    subtitle_stream_count: int = 0
    audio_languages: List[str] = field(default_factory=list)
    subtitle_languages: List[str] = field(default_factory=list)
    pixel_format: Optional[str] = None
    bitrate: Optional[int] = None
    analysis_status: str = "none"
    is_playable: bool = True
    thumbnail_available: bool = False
    thumbnail_url: Optional[str] = None
    streaming_url: Optional[str] = None
    dashboard_url: Optional[str] = None
    relinked_at: Optional[str] = None
    previous_storage_path: Optional[str] = None
    previous_sha256: Optional[str] = None
    relink_match_status: Optional[str] = None
    stored_file_id: Optional[str] = None
    reference_count: int = 1
    is_shared: bool = False
    is_deduplicated: bool = False


@dataclass
class StoredMediaFileRecord:
    id: str
    sha256: str
    storage_path: str
    file_size_bytes: int
    mime_type: Optional[str] = None
    container_format: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    is_external: bool = False
    reference_count: int = 1
    created_at: str = ""
    updated_at: str = ""
    last_verified_at: Optional[str] = None


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
    checkpoint_data: Optional[Dict[str, Any]] = None
    media_asset_id: Optional[str] = None
    parent_job_id: Optional[str] = None
    video_title: Optional[str] = None


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
    job_id: Optional[str] = None
    source_signature: Optional[str] = None
    stage_details: Optional[Dict[str, Any]] = None
    checkpoint_data: Optional[Dict[str, Any]] = None
    stored_file_id: Optional[str] = None


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
    rank_position: Optional[int] = None
    evidence_coverage: float = 1.0
    signal_scores: Dict[str, float] = field(default_factory=dict)
    generation_reason: Optional[str] = None
    transcript_excerpt: Optional[str] = None
    generation_run_id: Optional[str] = None
    creative_direction: str = "best_overall"
    natural_boundary_confidence: float = 1.0


@dataclass
class CandidateGenerationRunRecord:
    id: str
    project_id: str
    media_asset_id: str
    analysis_run_id: str
    creative_direction: str
    aspect_ratio: str
    requested_count: int
    min_duration: float
    max_duration: float
    status: str
    candidates_discovered: int
    candidates_selected: int
    candidates_rejected: int
    novelty_exclusions: int
    score_weights: Dict[str, float] = field(default_factory=dict)
    min_score: float = 0.0
    min_separation_seconds: float = 0.0
    source_signature: Optional[str] = None
    error_message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    generation_type: str = "initial"
    reused_analysis_run_id: Optional[str] = None
    duration_preference: str = "ai_best_duration"
    is_novelty_exhausted: bool = False
    job_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class CandidateClipEditRecord:
    id: str
    candidate_id: str
    project_id: str
    media_asset_id: str
    original_start_time: float
    original_end_time: float
    edited_start_time: float
    edited_end_time: float
    edited_duration: float
    aspect_ratio: str = "9:16"
    framing_mode: str = "center"  # 'center', 'manual', 'smart_tracking'
    manual_crop_x_pct: float = 50.0
    manual_crop_y_pct: float = 50.0
    manual_crop_zoom: float = 1.0
    tracked_subject_id: Optional[str] = None
    tracking_status: str = "none"  # 'none', 'tracking', 'tracked', 'fallback'
    reframing_plan_id: Optional[str] = None
    version: int = 1
    created_at: str = ""
    updated_at: str = ""


@dataclass
class StorageQuotaRecord:
    id: str = "default"
    storage_limit_bytes: Optional[int] = None
    generated_video_limit_bytes: Optional[int] = None
    temp_storage_limit_bytes: Optional[int] = None
    warning_threshold_percent: int = 85
    auto_prune_enabled: bool = False
    auto_prune_retention_hours: int = 24
    auto_prune_categories: List[str] = field(default_factory=lambda: ["orphaned_uploads", "abandoned_ffmpeg", "failed_renders", "expired_temp_files"])
    max_temp_storage_bytes: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class StorageCleanupAuditRecord:
    id: str
    operation_id: str
    timestamp: str
    cleanup_category: str
    files_examined: int = 0
    files_deleted: int = 0
    files_skipped: int = 0
    bytes_reclaimed: int = 0
    is_automatic: bool = False
    failure_reasons: List[Dict[str, Any]] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

