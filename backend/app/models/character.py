"""Pydantic data models for Character Extraction Studio and Character Library."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DetectionType(str, Enum):
    FACE = "face"
    PERSON = "person"


class ReviewStatus(str, Enum):
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    MERGED = "merged"
    SPLIT = "split"


class BoundingBox(BaseModel):
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


class CharacterObservation(BaseModel):
    id: str
    candidate_id: str
    job_id: str
    project_id: str
    media_asset_id: str
    timestamp: float
    frame_path: Optional[str] = None
    thumbnail_path: str
    bounding_box: BoundingBox
    detection_type: str = "face"
    confidence: float = 0.8
    detection_method: str = "opencv_haar"
    unverified_dialogue: Optional[str] = None
    is_detached: bool = False
    created_at: str


class CharacterCandidate(BaseModel):
    id: str
    job_id: str
    project_id: str
    label: str
    review_status: str = "provisional"
    confirmed_character_id: Optional[str] = None
    observation_count: int = 0
    sampled_screen_time_seconds: float = 0.0
    estimated_screen_time_seconds: float = 0.0
    representative_thumbnail_path: Optional[str] = None
    detection_methodology: str = "opencv_haar_spatial_temporal"
    clustering_confidence: float = 0.0
    notes: str = ""
    observations: List[CharacterObservation] = []
    created_at: str
    updated_at: str


class CharacterProfile(BaseModel):
    id: str
    project_id: str
    name: str
    avatar_path: Optional[str] = None
    biography: str = ""
    appearance_tags: List[str] = []
    total_appearances: int = 0
    total_screen_time_seconds: float = 0.0
    metadata_json: Dict[str, Any] = {}
    created_at: str
    updated_at: str


class ExtractionJobConfig(BaseModel):
    media_asset_id: str
    sample_interval_sec: float = Field(default=1.0, ge=0.2, le=10.0)
    detector_model: str = "opencv_haar_cpu"
    min_face_size: int = Field(default=30, ge=20, le=300)
    detect_persons: bool = True


class ExtractionJobStatus(BaseModel):
    id: str
    job_id: Optional[str] = None
    project_id: str
    media_asset_id: str
    status: str
    sample_interval_sec: float
    detector_model: str
    frames_sampled: int
    detections_count: int
    candidates_count: int
    duration_seconds: float
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class RenameCandidateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)


class ConfirmCandidateRequest(BaseModel):
    name: Optional[str] = None
    biography: Optional[str] = ""
    appearance_tags: Optional[List[str]] = None
    existing_character_id: Optional[str] = None


class MergeCandidatesRequest(BaseModel):
    source_candidate_ids: List[str] = Field(..., min_length=1)
    target_candidate_id: str
    new_label: Optional[str] = None


class SplitCandidateRequest(BaseModel):
    candidate_id: Optional[str] = None
    observation_ids_to_split: List[str] = Field(..., min_length=1)
    new_candidate_label: str = Field(..., min_length=1, max_length=100)


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    biography: Optional[str] = None
    appearance_tags: Optional[List[str]] = None


class CharacterExportPayload(BaseModel):
    export_version: str = "2.0.0"
    exported_at: str
    profile: CharacterProfile
    associated_candidates: List[Dict[str, Any]] = []
    screen_time_summary: Dict[str, Any] = {}
    disclaimer: str = (
        "ZezEdit 2.0 Character Studio metadata. Identity grouping is provisional, "
        "user-verified, and does not constitute biometric facial recognition. "
        "Associated dialogue represents temporal transcript overlap, not confirmed speaker diarization."
    )
