"""Database backup and restore endpoints."""

from fastapi import APIRouter, Depends, Query, Request

from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.services.backup_service import BackupService

router = APIRouter(prefix="/system/backups", tags=["backups"])


def get_backup_service(request: Request) -> BackupService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return BackupService(db_path=layout.db_file, backups_dir=layout.backups)


@router.post("", status_code=201)
def create_backup(
    label: str = Query("manual"),
    service: BackupService = Depends(get_backup_service),
) -> dict:
    return service.create_backup(label=label)


@router.post("/restore")
def restore_backup(
    filename: str = Query(...),
    service: BackupService = Depends(get_backup_service),
) -> dict:
    return service.restore_backup(backup_filename=filename)
