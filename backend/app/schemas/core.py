"""Request and response schemas for Projects, Media Assets, Jobs, Settings, and Storage."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


# ==================== PROJECTS ====================

class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    project_config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    project_config: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
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


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int


class ProjectEventResponse(BaseModel):
    id: str
    project_id: str
    event_type: str
    event_summary: str
    payload: Dict[str, Any]
    created_at: str


# ==================== MEDIA ASSETS ====================

class MediaAssetCreateRequest(BaseModel):
    original_filename: str = Field(..., min_length=1)
    storage_path: str = Field(..., min_length=1)
    is_external: bool = False
    media_type: str = "video"
    file_size_bytes: int = 0
    mime_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MediaAssetUpdateRequest(BaseModel):
    original_filename: Optional[str] = None
    media_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    metadata_status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MediaRelinkRequest(BaseModel):
    new_storage_path: Optional[str] = None
    candidate_path: Optional[str] = None
    force: bool = False
    expected_sha256: Optional[str] = None

    @model_validator(mode="before")
    def resolve_path(cls, values):
        if isinstance(values, dict):
            path = values.get("new_storage_path") or values.get("candidate_path")
            if not path or not str(path).strip():
                raise ValueError("new_storage_path or candidate_path must be provided")
            values["new_storage_path"] = str(path).strip()
        return values


class MediaRelinkResponse(BaseModel):
    asset: 'MediaAssetResponse'
    match_status: str  # "exact", "compatible", "mismatch"
    warnings: List[str] = Field(default_factory=list)
    comparison: Dict[str, Any] = Field(default_factory=dict)
    relinked_at: Optional[str] = None


class MediaReconcileResponse(BaseModel):
    total_checked: int
    restored_count: int
    still_missing_count: int
    restored_assets: List[str] = Field(default_factory=list)
    still_missing_assets: List[str] = Field(default_factory=list)


class MediaIntegrityCheckResult(BaseModel):
    asset_id: str
    project_id: str
    original_filename: str
    storage_path: str
    availability_status: str
    integrity_status: str
    file_exists: bool
    file_size_bytes: int
    size_matches: bool
    probe_ok: bool
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    issues: List[str] = Field(default_factory=list)
    checked_at: str


class ProjectMediaIntegrityResponse(BaseModel):
    project_id: str
    total_assets: int
    online_count: int
    missing_count: int
    corrupted_count: int
    all_healthy: bool
    assets: List[MediaIntegrityCheckResult]
    checked_at: str


class MediaImportLocalRequest(BaseModel):
    file_path: str = Field(..., min_length=1)
    copy_to_storage: bool = False
    generate_proxy: bool = False
    generate_thumbnail: bool = True


class MediaProxyGenerateRequest(BaseModel):
    profile: str = Field("480p", pattern="^(360p|480p|720p)$")


class MediaStorageStatsResponse(BaseModel):
    project_id: str
    total_media_count: int
    total_media_bytes: int
    total_proxy_bytes: int
    total_thumbnail_bytes: int
    managed_files_count: int
    external_files_count: int


class MediaAssetResponse(BaseModel):
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
    proxy_status: str = "none"
    metadata_status: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
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
    audio_languages: List[str] = Field(default_factory=list)
    subtitle_languages: List[str] = Field(default_factory=list)
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


class MediaDeduplicationStatsResponse(BaseModel):
    total_media_assets: int
    unique_stored_files: int
    shared_stored_files: int
    deduplicated_assets_count: int
    total_logical_bytes: int
    actual_physical_bytes: int
    saved_bytes: int
    deduplication_ratio: float


class MediaAssetListResponse(BaseModel):
    items: List[MediaAssetResponse]
    total: int
    total_count: Optional[int] = None
    page: int = 1
    page_size: int = 20
    total_pages: int = 1

    def __init__(self, **data):
        if "total" in data and "total_count" not in data:
            data["total_count"] = data["total"]
        elif "total_count" in data and "total" not in data:
            data["total"] = data["total_count"]
        super().__init__(**data)


class MediaBatchUploadItemResult(BaseModel):
    filename: str
    success: bool
    media_id: Optional[str] = None
    asset: Optional[MediaAssetResponse] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    is_deduplicated: bool = False
    reference_count: int = 1


class MediaBatchUploadResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    items: List[MediaBatchUploadItemResult]


MediaRelinkResponse.model_rebuild()


# ==================== JOBS ====================

class JobCreateRequest(BaseModel):
    project_id: Optional[str] = None
    media_asset_id: Optional[str] = None
    job_type: str = Field(..., min_length=1)
    priority: int = 100
    input_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    max_attempts: int = 2


class JobResponse(BaseModel):
    id: str
    project_id: Optional[str]
    media_asset_id: Optional[str] = None
    parent_job_id: Optional[str] = None
    video_title: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    estimated_remaining_seconds: Optional[float] = None
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


class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int


# ==================== SETTINGS & STORAGE ====================

class AppSettingsDTO(BaseModel):
    storage_root: str
    temporary_storage_location: str
    proxy_resolution: str = "480p"
    proxy_generate_on_import: bool = True
    cpu_processing_limits: Dict[str, Any] = Field(default_factory=lambda: {"max_threads": 4, "max_concurrent_jobs": 1})
    memory_limits_mb: int = 8192
    ai_provider_config: Dict[str, Any] = Field(default_factory=lambda: {"ollama_base_url": "http://127.0.0.1:11434"})
    model_preferences: Dict[str, Any] = Field(default_factory=lambda: {"default_vision_model": "qwen3-vl:4b-instruct"})
    default_export_preferences: Dict[str, Any] = Field(default_factory=lambda: {"resolution": "1080x1920", "codec": "libx264"})
    application_appearance: Dict[str, Any] = Field(default_factory=lambda: {"theme": "dark"})


class AppSettingsUpdateRequest(BaseModel):
    proxy_resolution: Optional[str] = None
    proxy_generate_on_import: Optional[bool] = None
    cpu_processing_limits: Optional[Dict[str, Any]] = None
    memory_limits_mb: Optional[int] = None
    ai_provider_config: Optional[Dict[str, Any]] = None
    model_preferences: Optional[Dict[str, Any]] = None
    default_export_preferences: Optional[Dict[str, Any]] = None
    application_appearance: Optional[Dict[str, Any]] = None


class StorageInspectResponse(BaseModel):
    storage_root: str
    is_accessible: bool
    is_writable: bool
    total_space_bytes: int
    free_space_bytes: int
    used_space_bytes: int
    directories: Dict[str, str]
    category_sizes_bytes: Dict[str, int]


# ==================== P1.9 STORAGE MANAGEMENT & QUOTAS ====================

class StorageBreakdownCategories(BaseModel):
    source_media_bytes: int = 0
    canonical_shared_media_bytes: int = 0
    logical_media_assets_bytes: int = 0
    generated_video_bytes: int = 0
    rendered_exports_bytes: int = 0
    extracted_audio_bytes: int = 0
    keyframes_and_thumbnails_bytes: int = 0
    transcripts_and_analysis_bytes: int = 0
    temporary_uploads_bytes: int = 0
    temporary_rendering_bytes: int = 0
    database_and_backups_bytes: int = 0
    proxies_bytes: int = 0
    logs_bytes: int = 0
    characters_bytes: int = 0
    timelines_bytes: int = 0
    temp_cache_bytes: int = 0


class StorageBreakdownResponse(BaseModel):
    storage_root: str
    total_disk_space_bytes: int
    free_disk_space_bytes: int
    used_disk_space_bytes: int
    total_application_storage_bytes: int
    recoverable_storage_bytes: int
    protected_storage_bytes: int
    is_low_storage: bool
    low_storage_threshold_bytes: int
    categories: StorageBreakdownCategories
    directories: Dict[str, str]
    quota_status: Optional[Dict[str, Any]] = None


class CleanupCandidateItem(BaseModel):
    candidate_id: str
    relative_path: str
    category: str
    size_bytes: int
    reason: str
    last_modified_at: str
    associated_project_id: Optional[str] = None
    associated_job_id: Optional[str] = None
    is_blocked: bool = False
    protection_reason: Optional[str] = None


class CleanupPreviewResponse(BaseModel):
    preview_id: str
    total_candidates: int
    eligible_candidates_count: int
    total_eligible_bytes: int
    blocked_candidates_count: int
    total_blocked_bytes: int
    categories_summary: Dict[str, Dict[str, int]]
    candidates: List[CleanupCandidateItem]
    protected_categories: List[str]
    generated_at: str


class CleanupExecuteRequest(BaseModel):
    preview_id: Optional[str] = None
    selected_categories: Optional[List[str]] = None
    candidate_ids: Optional[List[str]] = None
    confirmation: Optional[str] = None


class CleanupExecuteResponse(BaseModel):
    status: str
    operation_id: str
    deleted_count: int
    bytes_reclaimed: int
    skipped_count: int
    failed_count: int
    deleted_items: List[Dict[str, Any]] = Field(default_factory=list)
    skipped_items: List[Dict[str, Any]] = Field(default_factory=list)
    failed_items: List[Dict[str, Any]] = Field(default_factory=list)
    executed_at: str


class StorageQuotaSettingsDTO(BaseModel):
    id: str = "default"
    storage_limit_bytes: Optional[int] = None
    generated_video_limit_bytes: Optional[int] = None
    temp_storage_limit_bytes: Optional[int] = None
    warning_threshold_percent: int = 85
    auto_prune_enabled: bool = False
    auto_prune_retention_hours: int = 24
    auto_prune_categories: List[str] = Field(default_factory=lambda: ["orphaned_uploads", "abandoned_ffmpeg", "failed_renders", "expired_temp_files"])
    max_temp_storage_bytes: Optional[int] = None
    updated_at: str = ""


class StorageQuotaUpdateRequest(BaseModel):
    storage_limit_bytes: Optional[int] = None
    generated_video_limit_bytes: Optional[int] = None
    temp_storage_limit_bytes: Optional[int] = None
    warning_threshold_percent: Optional[int] = None
    auto_prune_enabled: Optional[bool] = None
    auto_prune_retention_hours: Optional[int] = None
    auto_prune_categories: Optional[List[str]] = None
    max_temp_storage_bytes: Optional[int] = None


class StorageQuotaStatusResponse(BaseModel):
    quota_settings: StorageQuotaSettingsDTO
    total_usage_bytes: int
    total_utilization_pct: Optional[float] = None
    generated_video_usage_bytes: int
    generated_video_utilization_pct: Optional[float] = None
    temp_storage_usage_bytes: int
    temp_storage_utilization_pct: Optional[float] = None
    is_warning: bool = False
    is_exceeded: bool = False
    warning_reasons: List[str] = Field(default_factory=list)


class CleanupAuditRecordDTO(BaseModel):
    id: str
    operation_id: str
    timestamp: str
    cleanup_category: str
    files_examined: int
    files_deleted: int
    files_skipped: int
    bytes_reclaimed: int
    is_automatic: bool
    failure_reasons: List[Dict[str, Any]] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)



class CapabilitiesResponse(BaseModel):
    app_version: str
    execution_mode: str
    cpu_cores: int
    ffmpeg_available: bool
    ffprobe_available: bool
    ollama_reachable: bool
    supported_aspect_ratios: List[str]
    supported_codecs: List[str]


# ==================== SYSTEM RESOURCE MONITORING ====================

class SystemResourceMetricsResponse(BaseModel):
    cpu_percent: float
    process_cpu_percent: float
    cpu_count_logical: int
    cpu_count_physical: int
    memory_total_mb: float
    memory_available_mb: float
    memory_used_mb: float
    memory_percent: float
    process_memory_rss_mb: float
    process_memory_vms_mb: float
    active_workers: int
    pending_jobs: int
    max_concurrent_jobs: int
    execution_mode: str = "cpu_first"
    timestamp: str


# ==================== WORKING QUEUE & STATS ====================

class QueueStatsResponse(BaseModel):
    total_jobs: int
    queued: int
    running: int
    completed: int
    failed: int
    cancelled: int
    by_type: Dict[str, int] = Field(default_factory=dict)
    active_job_ids: List[str] = Field(default_factory=list)


class JobLogsResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    current_stage: Optional[str] = None
    progress_percent: float = 0.0
    error_message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ==================== AI PROVIDERS ====================

class AIProviderCapability(BaseModel):
    task: str
    supported: bool
    description: str


class AIProviderDTO(BaseModel):
    id: str
    name: str
    provider_type: str  # local_llm, local_asr, heuristic
    status: str  # ready, offline, degraded
    is_local: bool = True
    base_url: Optional[str] = None
    active_model: str
    available_models: List[str] = Field(default_factory=list)
    capabilities: List[AIProviderCapability] = Field(default_factory=list)
    latency_ms: Optional[float] = None
    last_health_check: Optional[str] = None
    details: Optional[str] = None


class AIProviderTestRequest(BaseModel):
    provider_id: str
    base_url: Optional[str] = None


class AIProviderTestResponse(BaseModel):
    provider_id: str
    reachable: bool
    latency_ms: Optional[float] = None
    available_models: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class AIProviderUpdateRequest(BaseModel):
    base_url: Optional[str] = None
    active_model: Optional[str] = None


# ==================== DOCUMENTATION CENTER ====================

class DocArticleDTO(BaseModel):
    id: str
    title: str
    category: str
    summary: str
    tags: List[str] = Field(default_factory=list)
    reading_time_minutes: int = 2


class DocCategoryDTO(BaseModel):
    id: str
    name: str
    description: str
    article_count: int


class DocArticleDetailResponse(BaseModel):
    id: str
    title: str
    category: str
    summary: str
    markdown_content: str
    tags: List[str] = Field(default_factory=list)
    related_article_ids: List[str] = Field(default_factory=list)
    updated_at: str

