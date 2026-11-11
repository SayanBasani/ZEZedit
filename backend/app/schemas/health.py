"""Health and runtime information Pydantic schemas."""

from typing import List, Optional

from pydantic import BaseModel


class DependencyCheck(BaseModel):
    """Availability status of an external CLI or local service."""

    available: bool
    path_or_url: Optional[str] = None
    version: Optional[str] = None
    details: Optional[str] = None


class DatabaseHealth(BaseModel):
    """SQLite database health and migration state."""

    connected: bool
    path: str
    journal_mode: str
    current_migration: Optional[str] = None
    applied_migrations: List[str]


class StorageHealth(BaseModel):
    """Storage root boundary verification status."""

    root: str
    writable: bool
    buckets_ready: bool


class OllamaHealth(BaseModel):
    """Local Ollama daemon and model inventory status."""

    reachable: bool
    base_url: str
    installed_models: List[str]
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """Authoritative response from `GET /api/v1/health`."""

    status: str  # "ready" | "degraded"
    app_name: str
    app_version: str
    environment: str
    timestamp: str
    database: DatabaseHealth
    storage: StorageHealth
    ffmpeg: DependencyCheck
    ffprobe: DependencyCheck
    ollama: OllamaHealth


class SystemInfoResponse(BaseModel):
    """Host and hardware execution constraints summary."""

    app_version: str
    os_platform: str
    python_version: str
    cpu_count: int
    execution_mode: str
    max_concurrent_jobs: int
    ffmpeg_threads: int
    storage_root: str
