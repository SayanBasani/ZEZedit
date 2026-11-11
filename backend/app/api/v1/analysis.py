"""Video analysis API endpoints for transcription, scene cuts, frames & visual understanding."""

import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError, ProcessingError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.services.analysis_pipeline import VideoAnalysisPipeline
from app.services.temporal_aggregator import get_temporal_context_at

logger = logging.getLogger("zezedit.api.analysis")

router = APIRouter(prefix="/projects/{project_id}/media/{media_asset_id}/analysis", tags=["video-analysis"])


# --- Dependencies ---

def get_db_path(request: Request) -> Path:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return layout.db_file


def get_analysis_pipeline(request: Request) -> VideoAnalysisPipeline:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    layout: StorageLayout = getattr(request.app.state, "storage", None) or StorageLayout.from_root(
        settings.storage_root
    )
    return VideoAnalysisPipeline(settings=settings, db_path=layout.db_file)


# --- Schemas ---

class StartAnalysisRequest(BaseModel):
    profile: str = Field(default="balanced", description="fast, balanced, or detailed")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    run_synchronously: bool = Field(default=False, description="For testing: wait for completion before returning")


class AnalysisRunResponse(BaseModel):
    id: str
    media_asset_id: str
    project_id: str
    status: str
    profile: str
    progress_pct: float
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str


class TranscriptSegmentItem(BaseModel):
    id: str
    start_time: float
    end_time: float
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    words: List[Dict[str, Any]] = Field(default_factory=list)


class SpeechTurnItem(BaseModel):
    id: str
    start_time: float
    end_time: float
    speaker_label: str
    text: str
    turn_type: str


class VideoSceneItem(BaseModel):
    id: str
    scene_index: int
    start_time: float
    end_time: float
    representative_timestamp: float
    thumbnail_path: Optional[str] = None
    change_score: float


class SampledFrameItem(BaseModel):
    id: str
    timestamp: float
    frame_path: str
    scene_id: Optional[str] = None
    width: int
    height: int


class VisualObservationItem(BaseModel):
    id: str
    timestamp: float
    frame_id: Optional[str] = None
    category: str
    description: str
    provider_model: str
    confidence: float


# --- Background worker helper ---

async def _run_analysis_task(pipeline: VideoAnalysisPipeline, run_id: str) -> None:
    try:
        await pipeline.execute_analysis(run_id)
    except Exception as exc:
        logger.error("Background analysis task %s failed: %s", run_id, exc)


# --- Endpoints ---

@router.post("", response_model=AnalysisRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(
    project_id: str,
    media_asset_id: str,
    payload: StartAnalysisRequest,
    background_tasks: BackgroundTasks,
    pipeline: VideoAnalysisPipeline = Depends(get_analysis_pipeline),
    db_path: Path = Depends(get_db_path),
):
    """Trigger a new video analysis run."""
    try:
        run_id = pipeline.create_analysis_run(
            media_asset_id=media_asset_id,
            project_id=project_id,
            profile=payload.profile,
            config=payload.config,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if payload.run_synchronously:
        await pipeline.execute_analysis(run_id)
    else:
        background_tasks.add_task(_run_analysis_task, pipeline, run_id)

    # Return created run record
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to fetch created analysis run.")
        return dict(row)


@router.get("", response_model=List[AnalysisRunResponse])
def list_analysis_runs(
    project_id: str,
    media_asset_id: str,
    db_path: Path = Depends(get_db_path),
):
    """List all analysis runs for a media asset."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM analysis_runs
            WHERE project_id = ? AND media_asset_id = ?
            ORDER BY created_at DESC
            """,
            (project_id, media_asset_id),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/{run_id}", response_model=AnalysisRunResponse)
def get_analysis_run(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get status and stage information for a specific analysis run."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM analysis_runs
            WHERE id = ? AND project_id = ? AND media_asset_id = ?
            """,
            (run_id, project_id, media_asset_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Analysis run '{run_id}' not found.")
        return dict(row)


@router.get("/{run_id}/transcript")
def get_transcript(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get all transcript segments and speech turns for an analysis run."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        seg_rows = conn.execute(
            """
            SELECT * FROM transcript_segments
            WHERE analysis_run_id = ?
            ORDER BY start_time ASC
            """,
            (run_id,),
        ).fetchall()

        segments = []
        for r in seg_rows:
            d = dict(r)
            try:
                d["words"] = json.loads(d.get("words_json") or "[]")
            except Exception:
                d["words"] = []
            segments.append(d)

        turn_rows = conn.execute(
            """
            SELECT * FROM speech_turns
            WHERE analysis_run_id = ?
            ORDER BY start_time ASC
            """,
            (run_id,),
        ).fetchall()

        turns = [dict(r) for r in turn_rows]

        return {
            "analysis_run_id": run_id,
            "segments_count": len(segments),
            "turns_count": len(turns),
            "segments": segments,
            "speech_turns": turns,
        }


@router.get("/{run_id}/scenes", response_model=List[VideoSceneItem])
def get_scenes(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get detected scene boundaries."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM video_scenes
            WHERE analysis_run_id = ?
            ORDER BY scene_index ASC
            """,
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/{run_id}/frames", response_model=List[SampledFrameItem])
def get_sampled_frames(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get sampled keyframes metadata."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM sampled_frames
            WHERE analysis_run_id = ?
            ORDER BY timestamp ASC
            """,
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/{run_id}/visual-observations", response_model=List[VisualObservationItem])
def get_visual_observations(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get visual observations generated by Ollama / heuristic analyzer."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM visual_observations
            WHERE analysis_run_id = ?
            ORDER BY timestamp ASC
            """,
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/{run_id}/context")
def get_context(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    timestamp: float = Query(..., ge=0.0, description="Timestamp in seconds to query"),
    window: float = Query(15.0, ge=1.0, le=60.0, description="Window size in seconds"),
    db_path: Path = Depends(get_db_path),
):
    """Get unified multimodal temporal context around a timestamp."""
    ctx = get_temporal_context_at(run_id, timestamp=timestamp, window_seconds=window, db_path=db_path)
    return {
        "analysis_run_id": run_id,
        "query_timestamp": ctx.timestamp,
        "current_scene": ctx.current_scene,
        "active_segment": ctx.active_segment,
        "active_speech_turn": ctx.active_speech_turn,
        "nearby_segments": ctx.nearby_segments,
        "nearby_visual_observations": ctx.nearby_visual_observations,
        "nearest_frame": ctx.nearest_frame,
    }


@router.post("/{run_id}/cancel")
def cancel_analysis(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Cancel an active or pending analysis run."""
    with sqlite_session(db_path) as conn:
        row = conn.execute("SELECT status FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Analysis run not found.")
        current_status = row[0]
        if current_status in ("completed", "failed"):
            raise HTTPException(status_code=400, detail=f"Cannot cancel run with status '{current_status}'.")

        conn.execute(
            "UPDATE analysis_runs SET status = 'cancelled', updated_at = datetime('now') WHERE id = ?",
            (run_id,),
        )
    return {"message": "Analysis run cancelled successfully.", "run_id": run_id, "status": "cancelled"}


@router.get("/frame-image/{frame_id}")
def get_frame_image(
    project_id: str,
    media_asset_id: str,
    frame_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Stream a sampled frame image as JPEG."""
    with sqlite_session(db_path) as conn:
        row = conn.execute(
            "SELECT frame_path FROM sampled_frames WHERE id = ? AND media_asset_id = ?",
            (frame_id, media_asset_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Sampled frame not found.")
        frame_path = Path(row[0])
        if not frame_path.exists():
            raise HTTPException(status_code=404, detail="Frame image file missing from storage.")
        return FileResponse(path=str(frame_path), media_type="image/jpeg")
