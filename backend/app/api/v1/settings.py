"""Application settings and storage inspection endpoints."""

import os
from fastapi import APIRouter, Depends, Request

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
from app.services.settings_service import SettingsService
from app.services.storage import StorageService

router = APIRouter(tags=["settings"])


def get_settings_service(request: Request) -> SettingsService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return SettingsService(settings=settings, db_path=layout.db_file)


def get_storage_service(request: Request) -> StorageService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    return StorageService(settings=settings)


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
