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
