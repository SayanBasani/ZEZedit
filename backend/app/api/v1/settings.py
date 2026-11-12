"""Application settings, storage management, backups, and recovery endpoints."""

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.binaries import probe_media_binary
from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.integrations.ollama import OllamaProvider
from app.schemas.core import (
    AppSettingsDTO,
    AppSettingsUpdateRequest,
    CapabilitiesResponse,
    StorageInspectResponse,
)
from app.services.backup_service import BackupService
from app.services.settings_service import SettingsService
from app.services.storage import StorageService

router = APIRouter(tags=["settings"])


class CleanupExecuteRequest(BaseModel):
    confirmation_token: str = Field(..., min_length=4)


class ClearAllDataRequest(BaseModel):
    confirmation: str = Field(..., description="Must be exactly 'DELETE'")


class BackupCreateRequest(BaseModel):
    label: str = Field("manual", max_length=50)


class BackupRestoreRequest(BaseModel):
    backup_filename: str = Field(..., min_length=5)


def get_settings_service(request: Request) -> SettingsService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return SettingsService(settings=settings, db_path=layout.db_file)


def get_storage_service(request: Request) -> StorageService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    return StorageService(settings=settings)


def get_backup_service(request: Request) -> BackupService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return BackupService(db_path=layout.db_file, backups_dir=layout.backups)


@router.get("/settings", response_model=AppSettingsDTO)
def get_settings_endpoint(
    service: SettingsService = Depends(get_settings_service),
) -> AppSettingsDTO:
    return service.get_settings()


@router.patch("/settings", response_model=AppSettingsDTO)
def update_settings_endpoint(
    req: AppSettingsUpdateRequest,
    service: SettingsService = Depends(get_settings_service),
) -> AppSettingsDTO:
    return service.update_settings(req.model_dump(exclude_unset=True))


@router.get("/storage/inspect", response_model=StorageInspectResponse)
def inspect_storage_endpoint(
    service: StorageService = Depends(get_storage_service),
) -> StorageInspectResponse:
    data = service.inspect_storage()
    return StorageInspectResponse(**data)


@router.get("/storage/breakdown")
def get_storage_breakdown_endpoint(
    service: StorageService = Depends(get_storage_service),
) -> Dict[str, Any]:
    """Return categorized storage consumption across media, caches, exports, and DB."""
    return service.get_storage_breakdown()


@router.post("/storage/cleanup/preview")
def preview_cleanup_endpoint(
    service: StorageService = Depends(get_storage_service),
) -> Dict[str, Any]:
    """Scan disposable cache files and return eligible items with confirmation token."""
    return service.preview_cache_cleanup()


@router.post("/storage/cleanup/execute")
def execute_cleanup_endpoint(
    req: CleanupExecuteRequest,
    service: StorageService = Depends(get_storage_service),
) -> Dict[str, Any]:
    """Execute safe deletion strictly bounded to disposable temporary cache files."""
    return service.execute_cache_cleanup(req.confirmation_token)


@router.post("/storage/clear-all-data")
def clear_all_data_endpoint(
    req: ClearAllDataRequest,
    service: StorageService = Depends(get_storage_service),
) -> Dict[str, Any]:
    """Execute complete cleanup of managed media, proxies, frames, cache, temp, clips, and DB data."""
    return service.clear_all_data(req.confirmation)


@router.get("/backups")
def list_backups_endpoint(
    service: BackupService = Depends(get_backup_service),
) -> List[Dict[str, Any]]:
    """List verified database backups with size and integrity status."""
    return service.list_backups()


@router.post("/backups")
def create_backup_endpoint(
    req: BackupCreateRequest = BackupCreateRequest(),
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Create a verified SQLite backup snapshot."""
    return service.create_backup(label=req.label)


@router.post("/backups/restore")
def restore_backup_endpoint(
    req: BackupRestoreRequest,
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Restore database from backup file after creating an automatic safety snapshot."""
    return service.restore_backup(req.backup_filename)


@router.get("/system/db-integrity")
def get_db_integrity_endpoint(
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Execute SQLite PRAGMA integrity_check, foreign_key_check, and orphan scan."""
    return service.get_database_diagnostics()


@router.get("/system/recovery-status")
def get_recovery_status_endpoint(
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Return recovery metrics: last backup, interrupted jobs, missing media, autosave."""
    return service.get_recovery_status()


@router.get("/system/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities_endpoint(request: Request) -> CapabilitiesResponse:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    ffmpeg = probe_media_binary("ffmpeg", settings.ffmpeg_path)
    ffprobe = probe_media_binary("ffprobe", settings.ffprobe_path)
    ollama = await OllamaProvider(
        base_url=settings.ollama_base_url, timeout_seconds=2.0
    ).probe_health()

    return CapabilitiesResponse(
        app_version=settings.app_version,
        execution_mode="cpu_first",
        cpu_cores=os.cpu_count() or 1,
        ffmpeg_available=ffmpeg.available,
        ffprobe_available=ffprobe.available,
        ollama_reachable=ollama.reachable,
        supported_aspect_ratios=["9:16", "16:9", "1:1", "4:5"],
        supported_codecs=["h264", "aac", "pcm_s16le"],
    )
