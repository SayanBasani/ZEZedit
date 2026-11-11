"""REST API endpoints for Character Extraction Studio and Character Library."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.config import Settings
from app.models.character import (
    CharacterCandidate,
    CharacterExportPayload,
    CharacterProfile,
    ConfirmCandidateRequest,
    ExtractionJobConfig,
    ExtractionJobStatus,
    MergeCandidatesRequest,
    RenameCandidateRequest,
    SplitCandidateRequest,
    UpdateProfileRequest,
)
from app.services.character_service import CharacterService

logger = logging.getLogger("zezedit.api.characters")

router = APIRouter(prefix="/projects/{project_id}/characters", tags=["characters"])


def get_character_service(request: Request) -> CharacterService:
    settings: Settings = getattr(request.app.state, "settings", None)
    return CharacterService(settings=settings)


# -----------------------------------------------------------------------------
# Extraction Jobs
# -----------------------------------------------------------------------------

@router.post("/extract", response_model=ExtractionJobStatus)
def run_character_extraction(
    project_id: str,
    payload: ExtractionJobConfig,
    service: CharacterService = Depends(get_character_service),
) -> ExtractionJobStatus:
    """Run character and face extraction job on selected media asset."""
    return service.run_extraction_job(project_id, payload)


@router.get("/jobs/{job_id}", response_model=ExtractionJobStatus)
def get_extraction_job(
    project_id: str,
    job_id: str,
    service: CharacterService = Depends(get_character_service),
) -> ExtractionJobStatus:
    """Get status of an extraction job."""
    return service.get_job_status(job_id)


# -----------------------------------------------------------------------------
# Candidate Review
# -----------------------------------------------------------------------------

@router.get("/candidates", response_model=List[CharacterCandidate])
def list_candidates(
    project_id: str,
    job_id: Optional[str] = Query(None, description="Filter by extraction job"),
    include_detached: bool = Query(False, description="Include detached observations"),
    service: CharacterService = Depends(get_character_service),
) -> List[CharacterCandidate]:
    """List provisional and reviewed character candidates for project."""
    return service.get_candidates(project_id, job_id=job_id, include_detached=include_detached)


@router.patch("/candidates/{candidate_id}", response_model=CharacterCandidate)
def rename_candidate(
    project_id: str,
    candidate_id: str,
    payload: RenameCandidateRequest,
    service: CharacterService = Depends(get_character_service),
) -> CharacterCandidate:
    """Rename candidate label."""
    return service.rename_candidate(project_id, candidate_id, payload.label)


@router.post("/candidates/{candidate_id}/confirm", response_model=CharacterProfile)
def confirm_candidate(
    project_id: str,
    candidate_id: str,
    payload: ConfirmCandidateRequest,
    service: CharacterService = Depends(get_character_service),
) -> CharacterProfile:
    """Confirm provisional candidate into persistent Character Library."""
    return service.confirm_candidate(project_id, candidate_id, payload)


@router.post("/candidates/merge", response_model=CharacterCandidate)
def merge_candidates(
    project_id: str,
    payload: MergeCandidatesRequest,
    service: CharacterService = Depends(get_character_service),
) -> CharacterCandidate:
    """Merge multiple candidate groups into a single target candidate."""
    return service.merge_candidates(project_id, payload)


@router.post("/candidates/split", response_model=List[CharacterCandidate])
def split_candidate(
    project_id: str,
    payload: SplitCandidateRequest,
    service: CharacterService = Depends(get_character_service),
) -> List[CharacterCandidate]:
    """Split observation subset into a new candidate group."""
    c1, c2 = service.split_candidate(project_id, payload)
    return [c1, c2]


@router.delete("/candidates/{candidate_id}/observations/{observation_id}", response_model=CharacterCandidate)
def detach_observation(
    project_id: str,
    candidate_id: str,
    observation_id: str,
    service: CharacterService = Depends(get_character_service),
) -> CharacterCandidate:
    """Detach an observation from candidate without deleting raw disk evidence."""
    return service.detach_observation(project_id, candidate_id, observation_id)


@router.post("/candidates/{candidate_id}/reject", response_model=CharacterCandidate)
def reject_candidate(
    project_id: str,
    candidate_id: str,
    service: CharacterService = Depends(get_character_service),
) -> CharacterCandidate:
    """Reject candidate as false positive or unwanted."""
    return service.reject_candidate(project_id, candidate_id)


# -----------------------------------------------------------------------------
# Character Library & JSON Export
# -----------------------------------------------------------------------------

@router.get("/library", response_model=List[CharacterProfile])
def list_library_characters(
    project_id: str,
    query: Optional[str] = Query(None, description="Search by name or biography"),
    service: CharacterService = Depends(get_character_service),
) -> List[CharacterProfile]:
    """List persistent confirmed characters in the Character Library."""
    return service.get_library_profiles(project_id, query)


@router.get("/library/{character_id}", response_model=CharacterProfile)
def get_library_character(
    project_id: str,
    character_id: str,
    service: CharacterService = Depends(get_character_service),
) -> CharacterProfile:
    """Get profile of a confirmed character."""
    return service.get_character_profile(project_id, character_id)


@router.patch("/library/{character_id}", response_model=CharacterProfile)
def update_library_character(
    project_id: str,
    character_id: str,
    payload: UpdateProfileRequest,
    service: CharacterService = Depends(get_character_service),
) -> CharacterProfile:
    """Update confirmed character profile."""
    return service.update_character_profile(project_id, character_id, payload)


@router.get("/library/{character_id}/export", response_model=CharacterExportPayload)
def export_character(
    project_id: str,
    character_id: str,
    service: CharacterService = Depends(get_character_service),
) -> CharacterExportPayload:
    """Export character profile and structured appearance evidence as documented JSON."""
    return service.export_character_json(project_id, character_id)
