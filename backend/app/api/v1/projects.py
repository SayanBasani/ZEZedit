"""Project management endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.schemas.core import (
    ProjectCreateRequest,
    ProjectEventResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(request: Request) -> ProjectService:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return ProjectService(settings=settings, db_path=layout.db_file)


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    req: ProjectCreateRequest,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    rec = service.create_project(
        name=req.name,
        description=req.description,
        project_config=req.project_config,
    )
    return ProjectResponse(**rec.__dict__)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    include_archived: bool = Query(False),
    service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    items = service.list_projects(include_archived=include_archived)
    return ProjectListResponse(
        items=[ProjectResponse(**r.__dict__) for r in items],
        total=len(items),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    rec = service.get_project(project_id)
    return ProjectResponse(**rec.__dict__)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    rec = service.update_project(
        project_id=project_id,
        name=req.name,
        description=req.description,
        project_config=req.project_config,
    )
    return ProjectResponse(**rec.__dict__)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    rec = service.archive_project(project_id)
    return ProjectResponse(**rec.__dict__)


@router.post("/{project_id}/restore", response_model=ProjectResponse)
def restore_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    rec = service.restore_project(project_id)
    return ProjectResponse(**rec.__dict__)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    confirmation: bool = Query(False),
    service: ProjectService = Depends(get_project_service),
) -> None:
    service.delete_project(project_id, confirmation=confirmation)


@router.get("/{project_id}/events", response_model=list[ProjectEventResponse])
def get_project_events(
    project_id: str,
    limit: int = Query(50, ge=1, le=200),
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectEventResponse]:
    events = service.get_events(project_id, limit=limit)
    return [ProjectEventResponse(**e.__dict__) for e in events]
