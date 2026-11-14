"""Video analysis API endpoints for transcription, scene cuts, frames & visual understanding."""

import asyncio
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
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

router = APIRouter(prefix="/projects/{project_id}/media/{media_asset_id}", tags=["video-analysis"])


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    force_reanalysis: bool = Field(default=False, description="Bypass cache and force fresh analysis run")


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
    job_id: Optional[str] = None
    source_signature: Optional[str] = None
    stage_details: Optional[Dict[str, Any]] = None
    checkpoint_data: Optional[Dict[str, Any]] = None


def _format_run_response(row: sqlite3.Row) -> dict:
    """Format an analysis_runs SQL row for the API response."""
    d = dict(row)
    if "stage_details_json" in d:
        raw = d.pop("stage_details_json")
        try:
            d["stage_details"] = json.loads(raw) if raw else {}
        except Exception:
            d["stage_details"] = {}
    elif "stage_details" not in d:
        d["stage_details"] = {}

    if "checkpoint_data_json" in d:
        raw_cp = d.pop("checkpoint_data_json")
        try:
            d["checkpoint_data"] = json.loads(raw_cp) if raw_cp else None
        except Exception:
            d["checkpoint_data"] = None
    elif "checkpoint_data" not in d:
        d["checkpoint_data"] = None

    return d


class TranscriptSegmentItem(BaseModel):
    id: str
    start_time: float
    end_time: float
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    words: List[Dict[str, Any]] = Field(default_factory=list)
    corrected_text: Optional[str] = None
    is_corrected: bool = False
    correction_id: Optional[str] = None


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


class AudioAnalysisItem(BaseModel):
    id: str
    analysis_run_id: str
    media_asset_id: str
    has_audio: bool
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    codec_name: Optional[str] = None
    bit_rate: Optional[int] = None
    duration_seconds: Optional[float] = None
    speech_density: float = 1.0
    silence_intervals: List[Dict[str, float]] = Field(default_factory=list)


class TranscriptCorrectionCreate(BaseModel):
    segment_id: Optional[str] = None
    start_time: float = Field(..., ge=0.0)
    end_time: float = Field(..., ge=0.0)
    original_text: str
    corrected_text: str


class TranscriptCorrectionItem(BaseModel):
    id: str
    media_asset_id: str
    segment_id: Optional[str] = None
    start_time: float
    end_time: float
    original_text: str
    corrected_text: str
    created_at: str
    updated_at: str


# --- Background worker helper ---

def _run_analysis_worker(pipeline: VideoAnalysisPipeline, run_id: str) -> None:
    """Run analysis pipeline in dedicated threadpool worker, keeping FastAPI main loop unblocked."""
    try:
        asyncio.run(pipeline.execute_analysis(run_id))
    except Exception as exc:
        logger.error("Background analysis worker failed for run %s: %s", run_id, exc, exc_info=True)


# --- Endpoints ---

@router.post("/analysis", response_model=AnalysisRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(
    project_id: str,
    media_asset_id: str,
    payload: StartAnalysisRequest,
    background_tasks: BackgroundTasks,
    pipeline: VideoAnalysisPipeline = Depends(get_analysis_pipeline),
    db_path: Path = Depends(get_db_path),
):
    """Trigger a new video analysis run or return cached completed run."""
    try:
        run_id = pipeline.create_analysis_run(
            media_asset_id=media_asset_id,
            project_id=project_id,
            profile=payload.profile,
            config=payload.config,
            force_reanalysis=payload.force_reanalysis,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Check if run was already completed (from cache)
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to fetch analysis run.")
        run_data = _format_run_response(row)

    if run_data.get("status") == "completed":
        return run_data

    if payload.run_synchronously:
        await pipeline.execute_analysis(run_id)
    else:
        background_tasks.add_task(_run_analysis_worker, pipeline, run_id)

    # Return created run record
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        return _format_run_response(row)


@router.get("/analysis", response_model=List[AnalysisRunResponse])
def list_analysis_runs(
    project_id: str,
    media_asset_id: str,
    db_path: Path = Depends(get_db_path),
):
    """List all analysis runs for a media asset (ZEZ-030)."""
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
        return [_format_run_response(r) for r in rows]


@router.get("/analysis/{run_id}", response_model=AnalysisRunResponse)
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
        return _format_run_response(row)
        return dict(row)


@router.get("/analysis/{run_id}/transcript")
def get_transcript(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get all transcript segments with applied non-destructive corrections (ZEZ-024, ZEZ-025)."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # Fetch transcript corrections for this asset
        corrections = conn.execute(
            """
            SELECT * FROM transcript_corrections
            WHERE media_asset_id = ?
            ORDER BY start_time ASC
            """,
            (media_asset_id,),
        ).fetchall()

        corr_by_seg = {c["segment_id"]: dict(c) for c in corrections if c["segment_id"]}
        corr_list = [dict(c) for c in corrections]

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

            # Check for non-destructive correction
            matched_corr = corr_by_seg.get(d["id"])
            if not matched_corr:
                # Fallback to time overlap matching
                for c in corr_list:
                    if abs(c["start_time"] - d["start_time"]) < 0.2 and abs(c["end_time"] - d["end_time"]) < 0.2:
                        matched_corr = c
                        break

            if matched_corr:
                d["corrected_text"] = matched_corr["corrected_text"]
                d["is_corrected"] = True
                d["correction_id"] = matched_corr["id"]
            else:
                d["corrected_text"] = None
                d["is_corrected"] = False
                d["correction_id"] = None

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


@router.get("/analysis/{run_id}/scenes", response_model=List[VideoSceneItem])
def get_scenes(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get detected scene boundaries with thumbnail paths (ZEZ-026, ZEZ-027)."""
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


@router.get("/analysis/{run_id}/frames", response_model=List[SampledFrameItem])
def get_sampled_frames(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get sampled keyframes metadata (ZEZ-028)."""
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


@router.get("/analysis/{run_id}/visual-observations", response_model=List[VisualObservationItem])
def get_visual_observations(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get visual observations generated by Ollama / heuristic analyzer (ZEZ-031)."""
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


@router.get("/analysis/{run_id}/audio", response_model=Optional[AudioAnalysisItem])
def get_audio_analysis(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Get audio analysis metadata and silence intervals (ZEZ-021)."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM audio_analysis
            WHERE analysis_run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["silence_intervals"] = json.loads(d.get("silence_intervals_json") or "[]")
        except Exception:
            d["silence_intervals"] = []
        d["has_audio"] = bool(d["has_audio"])
        return d


@router.get("/analysis/{run_id}/context")
def get_context(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    timestamp: float = Query(..., ge=0.0, description="Timestamp in seconds to query"),
    window: float = Query(15.0, ge=1.0, le=60.0, description="Window size in seconds"),
    db_path: Path = Depends(get_db_path),
):
    """Get unified multimodal temporal context around a timestamp (ZEZ-032)."""
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


@router.get("/analysis/{run_id}/telemetry")
def get_analysis_telemetry(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    pipeline: VideoAnalysisPipeline = Depends(get_analysis_pipeline),
):
    """Retrieve granular stage progress, telemetry, and linked job state for a run."""
    try:
        return pipeline.get_run_telemetry(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/analysis/{run_id}/cancel")
def cancel_analysis(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    pipeline: VideoAnalysisPipeline = Depends(get_analysis_pipeline),
):
    """Cancel an active or pending analysis run and its linked background job."""
    try:
        return pipeline.cancel_run(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/analysis/{run_id}/retry")
async def retry_analysis(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    background_tasks: BackgroundTasks,
    pipeline: VideoAnalysisPipeline = Depends(get_analysis_pipeline),
):
    """Retry a failed, cancelled, or interrupted analysis run."""
    try:
        result = pipeline.retry_run(run_id)
        background_tasks.add_task(_run_analysis_worker, pipeline, run_id)
        return result
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analysis/{run_id}/cache")
def get_analysis_cache(
    project_id: str,
    media_asset_id: str,
    run_id: str,
    pipeline: VideoAnalysisPipeline = Depends(get_analysis_pipeline),
):
    """Retrieve cache validity and component count information for an analysis run."""
    try:
        return pipeline.get_run_cache_info(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/analysis/frame-image/{frame_id}")
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


@router.get("/analysis/scene-thumbnail/{scene_id}")
def get_scene_thumbnail(
    project_id: str,
    media_asset_id: str,
    scene_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Stream a scene representative thumbnail JPEG (ZEZ-027)."""
    with sqlite_session(db_path) as conn:
        row = conn.execute(
            "SELECT thumbnail_path FROM video_scenes WHERE id = ? AND media_asset_id = ?",
            (scene_id, media_asset_id),
        ).fetchone()
        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="Scene thumbnail not found.")
        thumb_path = Path(row[0])
        if not thumb_path.exists():
            raise HTTPException(status_code=404, detail="Scene thumbnail file missing from storage.")
        return FileResponse(path=str(thumb_path), media_type="image/jpeg")


# ==================== NON-DESTRUCTIVE TRANSCRIPT CORRECTIONS (ZEZ-025) ====================

@router.post("/transcript/corrections", response_model=TranscriptCorrectionItem)
def create_or_update_transcript_correction(
    project_id: str,
    media_asset_id: str,
    payload: TranscriptCorrectionCreate,
    db_path: Path = Depends(get_db_path),
):
    """Create or update a non-destructive transcript text correction."""
    now = _now_utc()
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # If segment_id is provided, check if correction already exists
        existing = None
        if payload.segment_id:
            existing = conn.execute(
                "SELECT * FROM transcript_corrections WHERE media_asset_id = ? AND segment_id = ?",
                (media_asset_id, payload.segment_id),
            ).fetchone()

        if existing:
            corr_id = existing["id"]
            conn.execute(
                """
                UPDATE transcript_corrections
                SET corrected_text = ?, updated_at = ?
                WHERE id = ?
                """,
                (payload.corrected_text, now, corr_id),
            )
        else:
            corr_id = f"corr_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO transcript_corrections (
                    id, media_asset_id, segment_id, start_time, end_time,
                    original_text, corrected_text, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    corr_id, media_asset_id, payload.segment_id, payload.start_time,
                    payload.end_time, payload.original_text, payload.corrected_text, now, now
                ),
            )

        row = conn.execute("SELECT * FROM transcript_corrections WHERE id = ?", (corr_id,)).fetchone()
        return dict(row)


@router.get("/transcript/corrections", response_model=List[TranscriptCorrectionItem])
def list_transcript_corrections(
    project_id: str,
    media_asset_id: str,
    db_path: Path = Depends(get_db_path),
):
    """List all non-destructive transcript text corrections for a media asset."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM transcript_corrections
            WHERE media_asset_id = ?
            ORDER BY start_time ASC
            """,
            (media_asset_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.delete("/transcript/corrections/{correction_id}")
def delete_transcript_correction(
    project_id: str,
    media_asset_id: str,
    correction_id: str,
    db_path: Path = Depends(get_db_path),
):
    """Revert a non-destructive transcript text correction to raw Whisper transcript."""
    with sqlite_session(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM transcript_corrections WHERE id = ? AND media_asset_id = ?",
            (correction_id, media_asset_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transcript correction not found.")

        conn.execute("DELETE FROM transcript_corrections WHERE id = ?", (correction_id,))
    return {"message": "Transcript correction reverted successfully.", "correction_id": correction_id}
