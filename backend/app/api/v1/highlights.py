"""Highlight discovery and Shorts candidate review REST API endpoints."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.errors import AppError, NotFoundError, ProcessingError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.services.highlight_discovery import HighlightDiscoveryEngine

logger = logging.getLogger("zezedit.api.highlights")

router = APIRouter(prefix="/projects/{project_id}", tags=["highlight-discovery"])


# --- Dependencies ---

def get_db_path(request: Request) -> Path:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return layout.db_file


def get_discovery_engine(request: Request) -> HighlightDiscoveryEngine:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return HighlightDiscoveryEngine(settings=settings, db_path=layout.db_file)


# --- Request & Response Schemas ---

class DiscoverHighlightsRequest(BaseModel):
    analysis_run_id: Optional[str] = None
    min_duration: float = Field(default=12.0, ge=5.0, le=120.0)
    max_duration: float = Field(default=60.0, ge=10.0, le=300.0)
    target_clip_count: int = Field(default=10, ge=1, le=50)
    use_ai_explanations: bool = Field(default=True)
    run_synchronously: bool = Field(default=False)


class UpdateCandidateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class BulkReviewRequest(BaseModel):
    candidate_ids: List[str]
    action: str = Field(description="'approve', 'reject', or 'restore'")
    rejection_reason: Optional[str] = None


class CandidateResponse(BaseModel):
    id: str
    project_id: str
    media_asset_id: str
    analysis_run_id: str
    job_id: Optional[str] = None
    start_time: float
    end_time: float
    duration: float
    suggested_start_time: float
    suggested_end_time: float
    is_user_modified: bool
    title: str
    suggested_title: str
    description: str
    category: str
    secondary_categories: List[str] = Field(default_factory=list)
    quality_score: float
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    gate_results: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    review_status: str
    rejection_reason: Optional[str] = None
    transcript_references: List[str] = Field(default_factory=list)
    scene_references: List[str] = Field(default_factory=list)
    visual_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    audio_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    ai_explanation: Dict[str, Any] = Field(default_factory=dict)
    alternative_of_candidate_id: Optional[str] = None
    overlap_group_id: Optional[str] = None
    scoring_version: str
    queued_for_render: bool
    created_at: str
    updated_at: str


class HighlightsOverviewResponse(BaseModel):
    project_id: str
    total_candidates: int
    recommended_count: int
    needs_review_count: int
    approved_count: int
    rejected_count: int
    candidates: List[CandidateResponse]


# --- Helper Function ---

def _row_to_candidate_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d["is_user_modified"] = bool(d.get("is_user_modified", 0))
    d["queued_for_render"] = bool(d.get("queued_for_render", 0))

    json_fields = [
        ("secondary_categories", "secondary_categories_json", []),
        ("score_breakdown", "score_breakdown_json", {}),
        ("gate_results", "gate_results_json", {}),
        ("warnings", "warnings_json", []),
        ("missing_evidence", "missing_evidence_json", []),
        ("transcript_references", "transcript_references_json", []),
        ("scene_references", "scene_references_json", []),
        ("visual_evidence", "visual_evidence_json", []),
        ("audio_evidence", "audio_evidence_json", []),
        ("ai_explanation", "ai_explanation_json", {}),
    ]

    for dest, src, default in json_fields:
        raw = d.get(src)
        try:
            d[dest] = json.loads(raw) if raw else default
        except Exception:
            d[dest] = default

    return d


# --- Endpoints ---

@router.post(
    "/media/{media_asset_id}/highlights/discover",
    response_model=List[CandidateResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
def start_highlight_discovery(
    project_id: str,
    media_asset_id: str,
    payload: DiscoverHighlightsRequest,
    background_tasks: BackgroundTasks,
    engine: HighlightDiscoveryEngine = Depends(get_discovery_engine),
    db_path: Path = Depends(get_db_path),
):
    """Trigger AI Highlight Discovery for an analyzed media asset."""
    if payload.run_synchronously:
        results = engine.discover_highlights(
            project_id=project_id,
            media_asset_id=media_asset_id,
            analysis_run_id=payload.analysis_run_id,
            min_duration=payload.min_duration,
            max_duration=payload.max_duration,
            target_clip_count=payload.target_clip_count,
            use_ai_explanations=payload.use_ai_explanations,
        )
        # Fetch fresh rows
        with sqlite_session(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM shorts_candidates
                WHERE project_id = ? AND media_asset_id = ?
                ORDER BY quality_score DESC
                """,
                (project_id, media_asset_id),
            ).fetchall()
            return [_row_to_candidate_dict(r) for r in rows]
    else:
        # Background execution
        background_tasks.add_task(
            engine.discover_highlights,
            project_id=project_id,
            media_asset_id=media_asset_id,
            analysis_run_id=payload.analysis_run_id,
            min_duration=payload.min_duration,
            max_duration=payload.max_duration,
            target_clip_count=payload.target_clip_count,
            use_ai_explanations=payload.use_ai_explanations,
        )
        return []


@router.get("/highlights", response_model=HighlightsOverviewResponse)
def get_project_highlights_overview(
    project_id: str,
    review_status: Optional[str] = Query(None, description="Filter by status: recommended, needs_review, approved, rejected"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search candidate title or text"),
    db_path: Path = Depends(get_db_path),
):
    """List all candidate clips across the project with aggregated count metrics."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # Calculate counts
        counts_rows = conn.execute(
            """
            SELECT review_status, COUNT(*) as cnt
            FROM shorts_candidates
            WHERE project_id = ?
            GROUP BY review_status
            """,
            (project_id,),
        ).fetchall()

        counts = {r["review_status"]: r["cnt"] for r in counts_rows}
        total = sum(counts.values())

        query = "SELECT * FROM shorts_candidates WHERE project_id = ?"
        params: List[Any] = [project_id]

        if review_status:
            query += " AND review_status = ?"
            params.append(review_status)

        if category:
            query += " AND category = ?"
            params.append(category)

        if search and search.strip():
            query += " AND (title LIKE ? OR description LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        query += " ORDER BY quality_score DESC"
        rows = conn.execute(query, tuple(params)).fetchall()

        candidates = [_row_to_candidate_dict(r) for r in rows]

        return HighlightsOverviewResponse(
            project_id=project_id,
            total_candidates=total,
            recommended_count=counts.get("recommended", 0),
            needs_review_count=counts.get("needs_review", 0),
            approved_count=counts.get("approved", 0),
            rejected_count=counts.get("rejected", 0),
            candidates=candidates,
        )


@router.get("/media/{media_asset_id}/highlights", response_model=List[CandidateResponse])
def list_media_candidates(
    project_id: str,
    media_asset_id: str,
    review_status: Optional[str] = Query(None),
    db_path: Path = Depends(get_db_path),
):
    """List highlight candidates for a specific media asset."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM shorts_candidates WHERE project_id = ? AND media_asset_id = ?"
        params: List[Any] = [project_id, media_asset_id]

        if review_status:
            query += " AND review_status = ?"
            params.append(review_status)

        query += " ORDER BY quality_score DESC"
        rows = conn.execute(query, tuple(params)).fetchall()
        return [_row_to_candidate_dict(r) for r in rows]


@router.get("/highlights/{candidate_id}", response_model=CandidateResponse)
def get_candidate_details(
    project_id: str,
    candidate_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Retrieve full details, score breakdown, and evidence for a candidate."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM shorts_candidates WHERE id = ? AND project_id = ?",
            (candidate_id, project_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Shorts candidate not found.")
        return _row_to_candidate_dict(row)


@router.patch("/highlights/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    project_id: str,
    candidate_id: str,
    payload: UpdateCandidateRequest,
    db_path: Path = Depends(get_db_path),
):
    """Update candidate title, description, category, or manual boundary adjustments."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT c.*, m.duration_seconds as media_duration
            FROM shorts_candidates c
            JOIN media_assets m ON c.media_asset_id = m.id
            WHERE c.id = ? AND c.project_id = ?
            """,
            (candidate_id, project_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Shorts candidate not found.")

        media_duration = float(row["media_duration"] or 999999.0)
        start_t = payload.start_time if payload.start_time is not None else float(row["start_time"])
        end_t = payload.end_time if payload.end_time is not None else float(row["end_time"])

        # Boundary validation
        if start_t < 0.0 or start_t >= end_t:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid boundaries: start_time ({start_t}s) must be non-negative and less than end_time ({end_t}s).",
            )
        if end_t > media_duration + 0.1:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid boundary: end_time ({end_t}s) exceeds source media duration ({media_duration:.1f}s).",
            )

        duration = round(end_t - start_t, 3)
        title = payload.title.strip() if payload.title is not None else row["title"]
        description = payload.description.strip() if payload.description is not None else row["description"]
        category = payload.category.strip() if payload.category is not None else row["category"]
        is_user_modified = 1 if (payload.start_time is not None or payload.end_time is not None) else row["is_user_modified"]

        conn.execute(
            """
            UPDATE shorts_candidates
            SET title = ?, description = ?, category = ?, start_time = ?, end_time = ?,
                duration = ?, is_user_modified = ?, updated_at = datetime('now')
            WHERE id = ? AND project_id = ?
            """,
            (title, description, category, start_t, end_t, duration, is_user_modified, candidate_id, project_id),
        )

        updated_row = conn.execute(
            "SELECT * FROM shorts_candidates WHERE id = ?",
            (candidate_id,),
        ).fetchone()
        return _row_to_candidate_dict(updated_row)


@router.post("/highlights/{candidate_id}/approve", response_model=CandidateResponse)
def approve_candidate(
    project_id: str,
    candidate_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Approve a candidate for short video creation."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        res = conn.execute(
            """
            UPDATE shorts_candidates
            SET review_status = 'approved', rejection_reason = NULL, updated_at = datetime('now')
            WHERE id = ? AND project_id = ?
            """,
            (candidate_id, project_id),
        )
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Candidate not found.")

        row = conn.execute("SELECT * FROM shorts_candidates WHERE id = ?", (candidate_id,)).fetchone()
        return _row_to_candidate_dict(row)


@router.post("/highlights/{candidate_id}/reject", response_model=CandidateResponse)
def reject_candidate(
    project_id: str,
    candidate_id: str,
    reason: Optional[str] = Query(None),
    db_path: Path = Depends(get_db_path),
):
    """Reject a candidate with documented reason."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        res = conn.execute(
            """
            UPDATE shorts_candidates
            SET review_status = 'rejected', rejection_reason = ?, updated_at = datetime('now')
            WHERE id = ? AND project_id = ?
            """,
            (reason or "User marked as rejected during review", candidate_id, project_id),
        )
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Candidate not found.")

        row = conn.execute("SELECT * FROM shorts_candidates WHERE id = ?", (candidate_id,)).fetchone()
        return _row_to_candidate_dict(row)


@router.post("/highlights/{candidate_id}/restore", response_model=CandidateResponse)
def restore_candidate(
    project_id: str,
    candidate_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Restore a rejected candidate back to recommended or needs_review."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT quality_score FROM shorts_candidates WHERE id = ? AND project_id = ?", (candidate_id, project_id)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Candidate not found.")

        new_status = "recommended" if row["quality_score"] >= 60.0 else "needs_review"
        conn.execute(
            """
            UPDATE shorts_candidates
            SET review_status = ?, rejection_reason = NULL, updated_at = datetime('now')
            WHERE id = ? AND project_id = ?
            """,
            (new_status, candidate_id, project_id),
        )

        updated_row = conn.execute("SELECT * FROM shorts_candidates WHERE id = ?", (candidate_id,)).fetchone()
        return _row_to_candidate_dict(updated_row)


@router.post("/highlights/{candidate_id}/queue-render")
def toggle_queue_render(
    project_id: str,
    candidate_id: str,
    queued: bool = Query(True),
    db_path: Path = Depends(get_db_path),
):
    """Toggle candidate queued status for Milestone 8 rendering."""
    with sqlite_session(db_path) as conn:
        res = conn.execute(
            """
            UPDATE shorts_candidates
            SET queued_for_render = ?, updated_at = datetime('now')
            WHERE id = ? AND project_id = ?
            """,
            (1 if queued else 0, candidate_id, project_id),
        )
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Candidate not found.")
    return {"candidate_id": candidate_id, "queued_for_render": queued}


@router.get("/highlights/{candidate_id}/alternatives", response_model=List[CandidateResponse])
def get_candidate_alternatives(
    project_id: str,
    candidate_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get overlapping alternative cuts of the same moment."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT overlap_group_id FROM shorts_candidates WHERE id = ? AND project_id = ?", (candidate_id, project_id)).fetchone()
        if not row or not row["overlap_group_id"]:
            return []

        group_id = row["overlap_group_id"]
        rows = conn.execute(
            """
            SELECT * FROM shorts_candidates
            WHERE project_id = ? AND overlap_group_id = ? AND id != ?
            ORDER BY quality_score DESC
            """,
            (project_id, group_id, candidate_id),
        ).fetchall()
        return [_row_to_candidate_dict(r) for r in rows]


@router.post("/highlights/bulk-review")
def bulk_review_candidates(
    project_id: str,
    payload: BulkReviewRequest,
    db_path: Path = Depends(get_db_path),
):
    """Bulk approve, reject, or restore multiple candidates."""
    if not payload.candidate_ids:
        return {"updated_count": 0, "action": payload.action}

    with sqlite_session(db_path) as conn:
        placeholders = ",".join("?" for _ in payload.candidate_ids)
        params: List[Any] = []

        if payload.action == "approve":
            sql = f"""
                UPDATE shorts_candidates
                SET review_status = 'approved', rejection_reason = NULL, updated_at = datetime('now')
                WHERE project_id = ? AND id IN ({placeholders})
            """
            params = [project_id] + payload.candidate_ids
        elif payload.action == "reject":
            reason = payload.rejection_reason or "Bulk rejected by user"
            sql = f"""
                UPDATE shorts_candidates
                SET review_status = 'rejected', rejection_reason = ?, updated_at = datetime('now')
                WHERE project_id = ? AND id IN ({placeholders})
            """
            params = [reason, project_id] + payload.candidate_ids
        elif payload.action == "restore":
            sql = f"""
                UPDATE shorts_candidates
                SET review_status = CASE WHEN quality_score >= 60.0 THEN 'recommended' ELSE 'needs_review' END,
                    rejection_reason = NULL, updated_at = datetime('now')
                WHERE project_id = ? AND id IN ({placeholders})
            """
            params = [project_id] + payload.candidate_ids
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action '{payload.action}'.")

        res = conn.execute(sql, tuple(params))
        return {"updated_count": res.rowcount, "action": payload.action}
