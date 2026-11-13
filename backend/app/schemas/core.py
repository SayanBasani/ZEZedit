"""Request and response schemas for Projects, Media Assets, Jobs, Settings, and Storage."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
    new_storage_path: str = Field(..., min_length=1)
    force: bool = False


class MediaRelinkResponse(BaseModel):
    asset: 'MediaAssetResponse'
    match_status: str  # "exact", "compatible", "mismatch"
    warnings: List[str] = Field(default_factory=list)
    comparison: Dict[str, Any] = Field(default_factory=dict)


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


class MediaAssetListResponse(BaseModel):
    items: List[MediaAssetResponse]
    total: int


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

