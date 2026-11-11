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
    metadata_status: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class MediaAssetListResponse(BaseModel):
    items: List[MediaAssetResponse]
    total: int


# ==================== JOBS ====================

class JobCreateRequest(BaseModel):
    project_id: Optional[str] = None
    job_type: str = Field(..., min_length=1)
    priority: int = 100
    input_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    max_attempts: int = 2


class JobResponse(BaseModel):
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
