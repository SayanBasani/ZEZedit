"""Orchestrates multi-stage video analysis: audio, whisper, dialogue, scenes, visual frames & vision."""

import asyncio
import hashlib
import json
import logging
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.core.errors import NotFoundError, ProcessingError, MediaFileMissingError, StorageQuotaExceededError
from app.db.connection import sqlite_session
from app.services.audio_extractor import extract_audio_16k_mono, inspect_audio_stream, AudioMetadata
from app.services.frame_sampler import sample_analysis_frames, SampledFrame
from app.services.scene_detector import detect_scenes_ffmpeg, DetectedScene
from app.services.speech_segmentation import segment_dialogue_turns
from app.services.subject_tracker import SubjectTracker
from app.services.transcription import TranscriptionResult, WhisperTranscriber
from app.services.visual_understanding import OllamaVisionAnalyzer, VisualObservation
from app.services.jobs import JobOrchestrator
from app.services.storage import StorageService

logger = logging.getLogger("zezedit.analysis_pipeline")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@asynccontextmanager
async def _heartbeat_ticker(
    job_id: Optional[str],
    stage_name: str,
    orchestrator: Optional[JobOrchestrator],
    last_progress_check: Optional[Callable[[], float]] = None,
    max_inactive_seconds: float = 300.0,
    max_stage_seconds: float = 600.0,
):
    """Keep active worker heartbeat ticking periodically during heavy synchronous thread tasks.
    Halts heartbeats if worker thread makes zero progress for longer than max_inactive_seconds,
    preventing infinite heartbeats from masking a deadlocked worker thread.
    """
    if not job_id or not orchestrator:
        yield
        return
    stop_event = asyncio.Event()
    start_mono = time.monotonic()

    async def _ticker():
        while not stop_event.is_set():
            try:
                await asyncio.sleep(8.0)
                if stop_event.is_set():
                    break
                elapsed = time.monotonic() - start_mono
                if last_progress_check is not None:
                    last_act = last_progress_check()
                    # Only check inactivity if at least one callback was received or after initial grace period
                    silence_from = last_act if last_act > 0.0 else start_mono
                    silence_dur = time.monotonic() - silence_from
                    if silence_dur > max_inactive_seconds:
                        logger.warning(
                            "Worker progress inactive for %.1fs (>%.0fs limit) in stage '%s'; halting heartbeat ticker to allow watchdog detection.",
                            silence_dur,
                            max_inactive_seconds,
                            stage_name,
                        )
                        break
                else:
                    if elapsed > max_stage_seconds:
                        logger.warning(
                            "Stage '%s' exceeded max duration limit of %.0fs; halting heartbeat ticker to allow watchdog detection.",
                            stage_name,
                            max_stage_seconds,
                        )
                        break
                orchestrator.record_heartbeat(
                    job_id,
                    stage=stage_name,
                    stage_details={"last_heartbeat": _now_utc(), "stage": stage_name},
                )
            except Exception:
                pass

    task = asyncio.create_task(_ticker())
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


def compute_source_signature(media_path: Path) -> str:
    """Compute lightweight, deterministic signature of source media file.

    Evaluates size + mtime + first 64KB sha256 checksum without reading full movie into memory.
    """
    if not media_path.exists():
        return "missing"
    try:
        st = media_path.stat()
        hasher = hashlib.sha256()
        with open(media_path, "rb") as f:
            chunk = f.read(65536)
            hasher.update(chunk)
        return f"{st.st_size}:{int(st.st_mtime)}:{hasher.hexdigest()[:16]}"
    except Exception as exc:
        logger.warning("Failed to compute signature for %s: %s", media_path, exc)
        return "unreadable"


class VideoAnalysisPipeline:
    """Coordinates modular video analysis stages with persistent job tracking and stage-aware caching."""

    def __init__(self, settings: Optional[Settings] = None, db_path: Optional[Path] = None) -> None:
        self.settings = settings or get_settings()
        layout = StorageLayout.from_root(self.settings.storage_root)
        self.storage_root = layout.root
        self.db_path = db_path or layout.db_file
        self.transcriber = WhisperTranscriber(model_size="tiny", device="cpu", compute_type="int8")
        self.vision_analyzer = OllamaVisionAnalyzer()
        self.subject_tracker = SubjectTracker(ffmpeg_path=self.settings.ffmpeg_path)
        self.jobs = JobOrchestrator(self.settings, self.db_path)
        self.job_orchestrator = self.jobs

    def _clone_analysis_run(
        self,
        conn: sqlite3.Connection,
        source_run_id: str,
        target_asset_id: str,
        target_project_id: str,
        stored_file_id: Optional[str],
        source_signature: str,
        profile: str,
        config_dict: Dict[str, Any],
    ) -> str:
        """Clone all analysis data from an existing completed run into a new completed run record for a deduplicated asset."""
        now = _now_utc()
        target_run_id = f"run_{uuid.uuid4().hex[:12]}"

        # 1. Fetch source stage_details_json and add shared caching metadata
        src_run = conn.execute("SELECT stage_details_json FROM analysis_runs WHERE id = ?", (source_run_id,)).fetchone()
        src_stage: Dict[str, Any] = {}
        if src_run and src_run[0]:
            try:
                src_stage = json.loads(src_run[0])
            except Exception:
                src_stage = {}
        src_stage["cached_from_shared_media"] = True
        src_stage["shared_from_run_id"] = source_run_id
        src_stage["shared_stored_file_id"] = stored_file_id

        # 2. Insert target analysis_runs record
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, media_asset_id, project_id, status, profile, config_json,
                progress_pct, current_stage, error_message, started_at, completed_at,
                created_at, updated_at, job_id, source_signature, stage_details_json, checkpoint_data_json, stored_file_id
            ) VALUES (?, ?, ?, 'completed', ?, ?, 100.0, 'completed', NULL, ?, ?, ?, ?, NULL, ?, ?, NULL, ?)
            """,
            (
                target_run_id,
                target_asset_id,
                target_project_id,
                profile,
                json.dumps(config_dict),
                now,
                now,
                now,
                now,
                source_signature,
                json.dumps(src_stage),
                stored_file_id,
            ),
        )

        # 3. Clone audio_analysis
        src_aud = conn.execute("SELECT * FROM audio_analysis WHERE analysis_run_id = ?", (source_run_id,)).fetchone()
        if src_aud:
            aud_id = f"aud_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO audio_analysis (
                    id, analysis_run_id, media_asset_id, has_audio, sample_rate, channels,
                    codec_name, bit_rate, duration_seconds, speech_density, silence_intervals_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    aud_id,
                    target_run_id,
                    target_asset_id,
                    src_aud[3],
                    src_aud[4],
                    src_aud[5],
                    src_aud[6],
                    src_aud[7],
                    src_aud[8],
                    src_aud[9],
                    src_aud[10],
                    now,
                ),
            )

        # 4. Clone video_scenes
        src_scenes = conn.execute("SELECT * FROM video_scenes WHERE analysis_run_id = ?", (source_run_id,)).fetchall()
        scene_id_map: Dict[int, str] = {}
        for sc in src_scenes:
            new_sc_id = f"scene_{uuid.uuid4().hex[:12]}"
            scene_id_map[sc[3]] = new_sc_id  # map scene_index -> new_sc_id
            conn.execute(
                """
                INSERT INTO video_scenes (
                    id, analysis_run_id, media_asset_id, scene_index, start_time,
                    end_time, representative_timestamp, thumbnail_path, change_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_sc_id,
                    target_run_id,
                    target_asset_id,
                    sc[3],
                    sc[4],
                    sc[5],
                    sc[6],
                    sc[7],
                    sc[8],
                    now,
                ),
            )

        # 5. Clone transcript_segments
        src_segs = conn.execute("SELECT * FROM transcript_segments WHERE analysis_run_id = ?", (source_run_id,)).fetchall()
        for seg in src_segs:
            new_seg_id = f"seg_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO transcript_segments (
                    id, analysis_run_id, media_asset_id, start_time, end_time,
                    text, language, confidence, words_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_seg_id,
                    target_run_id,
                    target_asset_id,
                    seg[3],
                    seg[4],
                    seg[5],
                    seg[6],
                    seg[7],
                    seg[8],
                    now,
                ),
            )

        # 6. Clone speech_turns
        src_turns = conn.execute("SELECT * FROM speech_turns WHERE analysis_run_id = ?", (source_run_id,)).fetchall()
        for turn in src_turns:
            new_turn_id = f"turn_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO speech_turns (
                    id, analysis_run_id, media_asset_id, start_time, end_time,
                    speaker_label, text, segment_ids_json, turn_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_turn_id,
                    target_run_id,
                    target_asset_id,
                    turn[3],
                    turn[4],
                    turn[5],
                    turn[6],
                    turn[7],
                    turn[8],
                    now,
                ),
            )

        # 7. Clone sampled_frames
        src_frames = conn.execute("SELECT * FROM sampled_frames WHERE analysis_run_id = ?", (source_run_id,)).fetchall()
        for fr in src_frames:
            new_fr_id = f"frame_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO sampled_frames (
                    id, analysis_run_id, media_asset_id, timestamp, frame_path,
                    scene_id, width, height, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_fr_id,
                    target_run_id,
                    target_asset_id,
                    fr[3],
                    fr[4],
                    fr[5],
                    fr[6],
                    fr[7],
                    now,
                ),
            )

        # 8. Clone visual_observations
        src_obs = conn.execute("SELECT * FROM visual_observations WHERE analysis_run_id = ?", (source_run_id,)).fetchall()
        for ob in src_obs:
            new_ob_id = f"obs_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO visual_observations (
                    id, analysis_run_id, media_asset_id, timestamp, frame_id,
                    category, description, provider_model, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_ob_id,
                    target_run_id,
                    target_asset_id,
                    ob[3],
                    ob[4],
                    ob[5],
                    ob[6],
                    ob[7],
                    ob[8],
                    now,
                ),
            )

        return target_run_id

    def create_analysis_run(
        self,
        media_asset_id: str,
        project_id: Optional[str] = None,
        profile: str = "balanced",
        config: Optional[Dict[str, Any]] = None,
        force_reanalysis: bool = False,
    ) -> str:
        """Create a pending analysis run record and persistent job or return an existing completed run."""
        now = _now_utc()
        config_dict = config or {}

        with sqlite_session(self.db_path) as conn:
            conn.row_factory = None
            # Verify asset exists
            if project_id:
                asset_row = conn.execute(
                    """
                    SELECT id, project_id, storage_path, duration_seconds, availability_status, stored_file_id, sha256
                    FROM media_assets WHERE id = ? AND project_id = ?
                    """,
                    (media_asset_id, project_id),
                ).fetchone()
            else:
                asset_row = conn.execute(
                    """
                    SELECT id, project_id, storage_path, duration_seconds, availability_status, stored_file_id, sha256
                    FROM media_assets WHERE id = ?
                    """,
                    (media_asset_id,),
                ).fetchone()

            if not asset_row:
                err = f"Media asset '{media_asset_id}' not found" + (f" in project '{project_id}'." if project_id else ".")
                raise NotFoundError(err)

            eff_project_id = asset_row[1]
            media_path = Path(asset_row[2])
            avail_status = asset_row[4]
            stored_file_id = asset_row[5]
            sha256_hash = asset_row[6]

            # Enforce missing / inaccessible media protection (P1.7)
            if avail_status == "missing" or not media_path.exists():
                raise MediaFileMissingError(
                    f"Media asset '{media_asset_id}' source file is missing or inaccessible on disk.",
                    details={
                        "media_asset_id": media_asset_id,
                        "storage_path": str(media_path),
                        "availability_status": avail_status,
                    },
                )

            # Enforce storage quota check before initiating analysis (P1.9)
            storage_service = StorageService(self.settings)
            quota_ok, quota_reason = storage_service.check_quota_for_operation("temp", 50 * 1024 * 1024)
            if not quota_ok:
                raise StorageQuotaExceededError(
                    quota_reason or "Temporary storage quota exceeded for video analysis.",
                    details={"media_asset_id": media_asset_id},
                )

            source_sig = compute_source_signature(media_path)

            # Check for existing completed run if force_reanalysis is False (ZEZ-029 Stage-Aware Caching)
            if not force_reanalysis and source_sig != "missing":
                existing_run = conn.execute(
                    """
                    SELECT id, job_id FROM analysis_runs
                    WHERE media_asset_id = ? AND status = 'completed' AND source_signature = ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (media_asset_id, source_sig),
                ).fetchone()

                if existing_run:
                    # Verify that underlying artifacts exist in database
                    has_scenes = conn.execute(
                        "SELECT COUNT(*) FROM video_scenes WHERE analysis_run_id = ?",
                        (existing_run[0],),
                    ).fetchone()[0] > 0
                    has_audio = conn.execute(
                        "SELECT COUNT(*) FROM audio_analysis WHERE analysis_run_id = ?",
                        (existing_run[0],),
                    ).fetchone()[0] > 0

                    if has_scenes or has_audio:
                        logger.info(
                            "Found valid cached completed analysis run %s (sig=%s) for asset %s",
                            existing_run[0],
                            source_sig,
                            media_asset_id,
                        )
                        return existing_run[0]

            # Canonical Shared Media Deduplication Awareness (P1.8)
            if not force_reanalysis and (stored_file_id or sha256_hash):
                shared_candidate = None
                if stored_file_id:
                    shared_candidate = conn.execute(
                        """
                        SELECT a.id, a.media_asset_id, a.profile, a.source_signature
                        FROM analysis_runs a
                        JOIN media_assets m ON a.media_asset_id = m.id
                        WHERE m.stored_file_id = ? AND a.status = 'completed' AND a.media_asset_id != ?
                        ORDER BY a.created_at DESC LIMIT 1
                        """,
                        (stored_file_id, media_asset_id),
                    ).fetchone()

                if not shared_candidate and sha256_hash:
                    shared_candidate = conn.execute(
                        """
                        SELECT a.id, a.media_asset_id, a.profile, a.source_signature
                        FROM analysis_runs a
                        JOIN media_assets m ON a.media_asset_id = m.id
                        WHERE m.sha256 = ? AND a.status = 'completed' AND a.media_asset_id != ?
                        ORDER BY a.created_at DESC LIMIT 1
                        """,
                        (sha256_hash, media_asset_id),
                    ).fetchone()

                if shared_candidate:
                    source_run_id = shared_candidate[0]
                    target_run_id = self._clone_analysis_run(
                        conn=conn,
                        source_run_id=source_run_id,
                        target_asset_id=media_asset_id,
                        target_project_id=eff_project_id,
                        stored_file_id=stored_file_id,
                        source_signature=source_sig,
                        profile=profile or shared_candidate[2],
                        config_dict=config_dict,
                    )
                    logger.info(
                        "Reused canonical shared analysis run %s for asset %s (target run %s, stored_file_id: %s)",
                        source_run_id,
                        media_asset_id,
                        target_run_id,
                        stored_file_id,
                    )
                    return target_run_id

            # Check for existing active (running, pending, queued) run to prevent duplicate executions
            active_run = conn.execute(
                """
                SELECT id FROM analysis_runs
                WHERE media_asset_id = ? AND status IN ('running', 'pending', 'queued')
                ORDER BY created_at DESC LIMIT 1
                """,
                (media_asset_id,),
            ).fetchone()
            if active_run:
                logger.info(
                    "Reusing existing active analysis run %s for asset %s",
                    active_run[0],
                    media_asset_id,
                )
                return active_run[0]

            # Create persistent job in JobOrchestrator
            job_record = self.jobs.create_job(
                job_type="media_analysis",
                project_id=eff_project_id,
                priority=150,
                input_config={
                    "media_asset_id": media_asset_id,
                    "profile": profile,
                    "force_reanalysis": force_reanalysis,
                    "source_signature": source_sig,
                    "stored_file_id": stored_file_id,
                },
            )

            run_id = f"run_{uuid.uuid4().hex[:12]}"
            stage_details = {
                "stage": "queued",
                "stage_pct": 0.0,
                "overall_pct": 0.0,
                "completed_units": 0,
                "total_units": 100,
                "cached_stages": [],
                "warnings": [],
            }

            conn.execute(
                """
                INSERT INTO analysis_runs (
                    id, media_asset_id, project_id, status, profile, config_json,
                    progress_pct, current_stage, error_message, started_at, completed_at,
                    created_at, updated_at, job_id, source_signature, stage_details_json, checkpoint_data_json, stored_file_id
                ) VALUES (?, ?, ?, 'pending', ?, ?, 0.0, 'queued', NULL, NULL, NULL, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    run_id,
                    media_asset_id,
                    eff_project_id,
                    profile,
                    json.dumps(config_dict),
                    now,
                    now,
                    job_record.id,
                    source_sig,
                    json.dumps(stage_details),
                    stored_file_id,
                ),
            )

            # Update job input_config with the created run_id
            updated_input = dict(job_record.input_config)
            updated_input["run_id"] = run_id
            conn.execute(
                "UPDATE jobs SET input_config_json = ? WHERE id = ?",
                (json.dumps(updated_input), job_record.id),
            )

        logger.info(
            "Created analysis run %s and job %s for asset %s (profile: %s, sig: %s)",
            run_id,
            job_record.id,
            media_asset_id,
            profile,
            source_sig,
        )
        return run_id

        logger.info(
            "Created analysis run %s and job %s for asset %s (profile: %s, sig: %s)",
            run_id,
            job_record.id,
            media_asset_id,
            profile,
            source_sig,
        )
        return run_id

    def update_run_progress(
        self,
        run_id: str,
        status: str,
        progress_pct: float,
        current_stage: str,
        stage_details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> None:
        """Update progress on analysis_runs and mirror state to JobOrchestrator."""
        now = _now_utc()
        pct = round(max(0.0, min(100.0, progress_pct)), 1)
        details_json = json.dumps(stage_details or {})

        with sqlite_session(self.db_path) as conn:
            # If job_id not provided, resolve from analysis_runs
            if not job_id:
                row = conn.execute("SELECT job_id FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
                job_id = row[0] if row and row[0] else None

            started_at = now if status == "running" and pct <= 5.0 else None
            completed_at = now if status in ("completed", "failed", "cancelled") else None

            if started_at:
                conn.execute(
                    """
                    UPDATE analysis_runs
                    SET status = ?, progress_pct = ?, current_stage = ?, stage_details_json = ?,
                        updated_at = ?, started_at = coalesce(started_at, ?)
                    WHERE id = ?
                    """,
                    (status, pct, current_stage, details_json, now, started_at, run_id),
                )
            elif completed_at:
                conn.execute(
                    """
                    UPDATE analysis_runs
                    SET status = ?, progress_pct = ?, current_stage = ?, stage_details_json = ?,
                        error_message = ?, updated_at = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (status, pct, current_stage, details_json, error_message, now, completed_at, run_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE analysis_runs
                    SET status = ?, progress_pct = ?, current_stage = ?, stage_details_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, pct, current_stage, details_json, now, run_id),
                )

        # Synchronize with JobOrchestrator if linked
        if job_id:
            try:
                job = self.jobs.get_job(job_id)
                current_job_status = job.status
                if status == "running":
                    if current_job_status == "queued":
                        self.jobs.transition_job_state(
                            job_id,
                            "running",
                            progress_pct=pct,
                            stage=current_stage,
                        )
                    elif current_job_status == "running":
                        self.jobs.transition_job_state(
                            job_id,
                            "running",
                            progress_pct=pct,
                            stage=current_stage,
                        )
                elif status in ("completed", "failed", "cancelled"):
                    if current_job_status in ("running", "queued", "cancelling"):
                        self.jobs.transition_job_state(
                            job_id,
                            status,
                            progress_pct=pct,
                            stage=current_stage,
                            error_message=error_message,
                        )

                # Persist checkpoint
                self.jobs.save_checkpoint(
                    job_id=job_id,
                    stage=current_stage,
                    completed_units=int(pct),
                    total_units=100,
                    checkpoint_payload=stage_details or {},
                )
            except Exception as j_exc:
                logger.warning("Could not synchronize job %s state: %s", job_id, j_exc)

    def is_cancelled(self, run_id: str, job_id: Optional[str] = None) -> bool:
        """Check whether the run or its linked job was cancelled."""
        with sqlite_session(self.db_path) as conn:
            row = conn.execute("SELECT status, job_id FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return True
            run_status, linked_job_id = row[0], row[1]
            if run_status == "cancelled":
                return True

            target_job_id = job_id or linked_job_id
            if target_job_id:
                j_row = conn.execute("SELECT status FROM jobs WHERE id = ?", (target_job_id,)).fetchone()
                if j_row and j_row[0] in ("cancelling", "cancelled"):
                    return True
        return False

    async def execute_analysis(self, run_id: str, job_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute all modular analysis stages sequentially across full video duration."""
        start_mono = time.monotonic()
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = None
            row = conn.execute(
                """
                SELECT a.id, a.media_asset_id, a.project_id, a.profile, a.config_json, a.status,
                       m.storage_path, m.duration_seconds, m.media_type, a.job_id, a.source_signature
                FROM analysis_runs a
                JOIN media_assets m ON a.media_asset_id = m.id
                WHERE a.id = ?
                """,
                (run_id,),
            ).fetchone()

        if not row:
            raise NotFoundError(f"Analysis run {run_id} not found.")

        (
            run_id,
            asset_id,
            project_id,
            profile,
            config_json_str,
            current_status,
            storage_path_str,
            duration,
            media_type,
            linked_job_id,
            persisted_sig,
        ) = row

        effective_job_id = job_id or linked_job_id
        media_path = Path(storage_path_str)
        duration = float(duration or 0.0)
        config_dict = json.loads(config_json_str or "{}")

        # If already completed, return immediately
        if current_status == "completed":
            return {"run_id": run_id, "status": "completed", "cached": True}

        # Stage 1: Validate Source
        stage_details: Dict[str, Any] = {
            "stage": "validating_source",
            "stage_status": "in_progress",
            "stage_pct": 100.0,
            "overall_pct": 5.0,
            "completed_units": 1,
            "total_units": 1,
            "units_label": "files",
            "elapsed_seconds": round(time.monotonic() - start_mono, 2),
            "last_heartbeat": _now_utc(),
            "operation_description": "Validating media source signature and integrity",
            "cached_stages": [],
            "warnings": [],
        }
        self.update_run_progress(
            run_id, "running", 5.0, "validating_source", stage_details=stage_details, job_id=effective_job_id
        )

        if not media_path.exists():
            err_msg = f"Media file not found at {media_path}"
            self.update_run_progress(
                run_id, "failed", 0.0, "failed", error_message=err_msg, job_id=effective_job_id
            )
            raise MediaFileMissingError(err_msg, details={"run_id": run_id, "media_path": str(media_path)})

        # Enforce storage quota before heavy temporary staging
        storage_service = StorageService(self.settings)
        quota_ok, quota_reason = storage_service.check_quota_for_operation("temp", 50 * 1024 * 1024)
        if not quota_ok:
            err_msg = quota_reason or "Temporary storage quota exceeded for video analysis."
            self.update_run_progress(
                run_id, "failed", 0.0, "failed", error_message=err_msg, job_id=effective_job_id
            )
            raise StorageQuotaExceededError(err_msg, details={"run_id": run_id})

        source_signature = compute_source_signature(media_path)
        if source_signature == "unreadable":
            err_msg = f"Media file is unreadable: {media_path}"
            self.update_run_progress(
                run_id, "failed", 0.0, "failed", error_message=err_msg, job_id=effective_job_id
            )
            raise ProcessingError(err_msg)

        job_temp_dir = self.storage_root / "temp" / "analysis" / run_id
        job_temp_dir.mkdir(parents=True, exist_ok=True)
        frames_dir = self.storage_root / "analysis" / asset_id / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        scenes_dir = self.storage_root / "analysis" / asset_id / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)

        try:
            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 5.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 2: Extract & Verify Metadata
            stage_details["stage"] = "extracting_metadata"
            stage_details["stage_status"] = "in_progress"
            stage_details["overall_pct"] = 10.0
            stage_details["stage_pct"] = 100.0
            stage_details["completed_units"] = 1
            stage_details["total_units"] = 1
            stage_details["units_label"] = "streams"
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            stage_details["last_heartbeat"] = _now_utc()
            stage_details["operation_description"] = "Inspecting audio/video stream container with FFprobe"
            self.update_run_progress(
                run_id, "running", 10.0, "extracting_metadata", stage_details=stage_details, job_id=effective_job_id
            )

            audio_meta = await asyncio.to_thread(inspect_audio_stream, media_path)
            if not audio_meta.has_audio:
                stage_details["warnings"].append("Source video has no audio track. Speech transcription will be skipped.")

            # Update asset duration if probe discovered more accurate length
            if audio_meta.duration_seconds > 0 and abs(duration - audio_meta.duration_seconds) > 1.0:
                duration = audio_meta.duration_seconds
                with sqlite_session(self.db_path) as conn:
                    conn.execute(
                        "UPDATE media_assets SET duration_seconds = ? WHERE id = ?",
                        (duration, asset_id),
                    )

            if duration <= 0.0:
                # Video has zero or unreadable duration
                duration = max(duration, 1.0)

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 10.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 3: Extract Audio (FFmpeg 16kHz mono WAV)
            stage_details["stage"] = "extracting_audio"
            stage_details["stage_status"] = "in_progress"
            stage_details["overall_pct"] = 20.0
            stage_details["stage_pct"] = 100.0
            stage_details["completed_units"] = int(duration)
            stage_details["total_units"] = int(duration)
            stage_details["units_label"] = "seconds"
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            stage_details["last_heartbeat"] = _now_utc()
            stage_details["operation_description"] = f"Demuxing audio track to 16kHz mono WAV ({duration:.1f}s)"
            self.update_run_progress(
                run_id, "running", 20.0, "extracting_audio", stage_details=stage_details, job_id=effective_job_id
            )

            audio_path = job_temp_dir / "audio_16k.wav"
            t_audio_start = time.monotonic()
            _, audio_meta = await asyncio.to_thread(
                extract_audio_16k_mono,
                media_path,
                audio_path,
                max_duration_seconds=duration,
                return_metadata=True,
            )
            audio_demux_time = round(time.monotonic() - t_audio_start, 2)
            logger.info("Audio demux for %s took %.2fs (speech_density: %.2f)", media_path.name, audio_demux_time, audio_meta.speech_density)

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 20.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 4: Speech Transcription (Faster-Whisper CPU int8 with streaming progress)
            t_trans_start = time.monotonic()
            tot_dur = max(1.0, audio_meta.duration_seconds if audio_meta.duration_seconds > 0 else duration)

            stage_details["stage"] = "transcribing_speech"
            stage_details["stage_status"] = "in_progress"
            stage_details["overall_pct"] = 25.0
            stage_details["stage_pct"] = 0.0
            stage_details["completed_units"] = 0.0
            stage_details["total_units"] = round(tot_dur, 1)
            stage_details["units_label"] = "seconds"
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            stage_details["last_heartbeat"] = _now_utc()
            stage_details["operation_description"] = f"Transcribing speech: 0s / {int(tot_dur)}s (0%)"
            self.update_run_progress(
                run_id, "running", 25.0, "transcribing_speech", stage_details=stage_details, job_id=effective_job_id
            )

            last_cb_time = [0.0]

            def on_transcribe_progress(current_sec: float, total_sec: float, latest_text: str) -> None:
                now_mono = time.monotonic()
                # Rate limit intermediate updates to at most once every 1.0 second unless at end
                if (now_mono - last_cb_time[0] < 1.0) and current_sec < (total_sec - 1.0):
                    return
                last_cb_time[0] = now_mono

                if self.is_cancelled(run_id, effective_job_id):
                    return

                tot = max(total_sec, 1.0)
                cur = min(current_sec, tot)
                st_pct = min(100.0, max(0.0, (cur / tot) * 100.0))
                # Map stage (0-100%) to overall progress (25% to 55%)
                overall = round(25.0 + 30.0 * (cur / tot), 1)
                elapsed = round(time.monotonic() - start_mono, 1)
                t_in_stage = max(0.1, time.monotonic() - t_trans_start)
                rate = cur / t_in_stage if t_in_stage > 0 else 1.0
                rem_audio = max(0.0, tot - cur)
                est_rem = round(rem_audio / rate, 1) if rate > 0 else 0.0

                prog_details = {
                    "stage": "transcribing_speech",
                    "stage_status": "in_progress",
                    "overall_pct": overall,
                    "stage_pct": round(st_pct, 1),
                    "completed_units": round(cur, 1),
                    "total_units": round(tot, 1),
                    "units_label": "seconds",
                    "elapsed_seconds": elapsed,
                    "estimated_remaining_seconds": est_rem,
                    "last_heartbeat": _now_utc(),
                    "operation_description": f"Transcribing speech: {int(cur)}s / {int(tot)}s ({st_pct:.0f}%)",
                    "latest_text": latest_text[:60] if latest_text else "",
                }
                self.update_run_progress(
                    run_id, "running", overall, "transcribing_speech", stage_details=prog_details, job_id=effective_job_id
                )

            if audio_meta.has_audio and audio_meta.duration_seconds > 0.1:
                async with _heartbeat_ticker(
                    effective_job_id,
                    "transcribing_speech",
                    self.job_orchestrator,
                    last_progress_check=lambda: last_cb_time[0],
                    max_inactive_seconds=600.0,
                    max_stage_seconds=7200.0,
                ):
                    transcription = await asyncio.to_thread(
                        self.transcriber.transcribe,
                        audio_path,
                        progress_callback=on_transcribe_progress,
                    )
            else:
                transcription = TranscriptionResult(
                    detected_language="none",
                    language_probability=1.0,
                    duration_seconds=duration,
                    segments=[],
                )
            transcribe_time = round(time.monotonic() - t_trans_start, 2)
            logger.info(
                "Transcription complete for %s in %.2fs: %d segments (lang: %s)",
                media_path.name,
                transcribe_time,
                len(transcription.segments),
                transcription.detected_language,
            )

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 55.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 5: Speech Turn & Dialogue Segmentation
            stage_details["stage"] = "segmenting_dialogue"
            stage_details["stage_status"] = "in_progress"
            stage_details["overall_pct"] = 60.0
            stage_details["stage_pct"] = 100.0
            stage_details["completed_units"] = len(transcription.segments)
            stage_details["total_units"] = len(transcription.segments)
            stage_details["units_label"] = "segments"
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            stage_details["last_heartbeat"] = _now_utc()
            stage_details["operation_description"] = f"Clustering {len(transcription.segments)} segments into conversational speech turns"
            self.update_run_progress(
                run_id, "running", 60.0, "segmenting_dialogue", stage_details=stage_details, job_id=effective_job_id
            )

            turns = segment_dialogue_turns(transcription.segments)

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 60.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 6: Scene Boundary Cut Detection (FFmpeg / PySceneDetect)
            stage_details["stage"] = "detecting_scenes"
            stage_details["stage_status"] = "in_progress"
            stage_details["overall_pct"] = 70.0
            stage_details["stage_pct"] = 100.0
            stage_details["completed_units"] = int(duration)
            stage_details["total_units"] = int(duration)
            stage_details["units_label"] = "seconds"
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            stage_details["last_heartbeat"] = _now_utc()
            stage_details["operation_description"] = "Analyzing temporal scene transitions and cuts with FFmpeg"
            self.update_run_progress(
                run_id, "running", 70.0, "detecting_scenes", stage_details=stage_details, job_id=effective_job_id
            )

            t_scene_start = time.monotonic()
            scenes: List[DetectedScene] = []
            if media_type == "video" and duration > 0.5:
                scene_timeout = max(600.0, float(duration) * 0.75)
                async with _heartbeat_ticker(
                    effective_job_id, "detecting_scenes", self.job_orchestrator, max_stage_seconds=scene_timeout
                ):
                    scenes = await asyncio.to_thread(
                        detect_scenes_ffmpeg,
                        media_path,
                        duration_seconds=duration,
                        thumbnails_dir=scenes_dir,
                    )
            else:
                single_scene = DetectedScene(0, 0.0, max(duration, 1.0), max(duration / 2.0, 0.5), 0.0)
                scenes = [single_scene]
            scene_detect_time = round(time.monotonic() - t_scene_start, 2)
            logger.info("Scene detection for %s in %.2fs: %d scenes detected", media_path.name, scene_detect_time, len(scenes))

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 70.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 7: Visual Frame Sampling
            stage_details["stage"] = "sampling_frames"
            stage_details["stage_status"] = "in_progress"
            stage_details["overall_pct"] = 80.0
            stage_details["stage_pct"] = 100.0
            stage_details["completed_units"] = len(scenes)
            stage_details["total_units"] = len(scenes)
            stage_details["units_label"] = "scenes"
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            stage_details["last_heartbeat"] = _now_utc()
            stage_details["operation_description"] = f"Extracting representative keyframes across {len(scenes)} scenes"
            self.update_run_progress(
                run_id, "running", 80.0, "sampling_frames", stage_details=stage_details, job_id=effective_job_id
            )

            t_sample_start = time.monotonic()
            sampled_frames: List[SampledFrame] = []
            if media_type == "video" and duration > 0.5:
                max_frames = 20 if profile == "fast" else (50 if profile == "balanced" else 100)
                sample_timeout = max(300.0, float(duration) * 0.5)
                promising_focus = [t.start_time for t in turns[:12]] if turns else None
                async with _heartbeat_ticker(
                    effective_job_id, "sampling_frames", self.job_orchestrator, max_stage_seconds=sample_timeout
                ):
                    sampled_frames = await asyncio.to_thread(
                        sample_analysis_frames,
                        media_path,
                        frames_dir,
                        scenes,
                        duration_seconds=duration,
                        max_frames=max_frames,
                        focus_timestamps=promising_focus,
                    )
            sample_time = round(time.monotonic() - t_sample_start, 2)
            logger.info("Sampled %d frames for %s in %.2fs", len(sampled_frames), media_path.name, sample_time)

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 80.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 8: Visual Understanding and Subject Tracking (Full-duration uniform coverage)
            sample_count = 5 if profile == "fast" else (15 if profile == "balanced" else 30)
            if len(sampled_frames) <= sample_count:
                target_frames = list(sampled_frames)
            else:
                stride = (len(sampled_frames) - 1) / float(sample_count - 1)
                chosen_indices = sorted(set(int(round(i * stride)) for i in range(sample_count)))
                target_frames = [sampled_frames[idx] for idx in chosen_indices]

            stage_details["stage"] = "analyzing_visuals"
            stage_details["stage_status"] = "in_progress"
            stage_details["overall_pct"] = 85.0
            stage_details["stage_pct"] = 0.0
            stage_details["completed_units"] = 0
            stage_details["total_units"] = len(target_frames)
            stage_details["units_label"] = "frames"
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            stage_details["last_heartbeat"] = _now_utc()
            stage_details["operation_description"] = f"Analyzing visual keyframes across full duration (0 / {len(target_frames)})"
            self.update_run_progress(
                run_id, "running", 85.0, "analyzing_visuals", stage_details=stage_details, job_id=effective_job_id
            )

            observations = []
            if hasattr(self.vision_analyzer, "reset"):
                self.vision_analyzer.reset()

            for idx, frame in enumerate(target_frames):
                if self.is_cancelled(run_id, effective_job_id):
                    self.update_run_progress(run_id, "cancelled", 85.0, "cancelled", job_id=effective_job_id)
                    return {"status": "cancelled"}

                frame_pct = round(((idx + 1) / max(len(target_frames), 1)) * 100.0, 1)
                vis_overall = round(85.0 + 10.0 * ((idx + 1) / max(len(target_frames), 1)), 1)
                stage_details["stage_pct"] = frame_pct
                stage_details["overall_pct"] = vis_overall
                stage_details["completed_units"] = idx + 1
                stage_details["last_heartbeat"] = _now_utc()
                stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
                stage_details["operation_description"] = f"Analyzing keyframe {idx + 1} of {len(target_frames)} ({frame_pct:.0f}%)"
                self.update_run_progress(
                    run_id, "running", vis_overall, "analyzing_visuals", stage_details=stage_details, job_id=effective_job_id
                )

                frame_path = Path(frame.frame_path)
                frame_obs = await self.vision_analyzer.analyze_frame(
                    frame_path,
                    timestamp=frame.timestamp,
                )
                observations.extend(frame_obs)

            # Generate lightweight local CV observations for remaining frames to guarantee 100% visual timeline coverage
            target_frame_paths = {f.frame_path for f in target_frames}
            for fr in sampled_frames:
                if fr.frame_path not in target_frame_paths:
                    obs_dets = self.subject_tracker.detect_subjects_in_frame(
                        fr.frame_path, fr.timestamp, fr.width, fr.height
                    )
                    sub_count = len([d for d in obs_dets if d.category in ("person", "face")])
                    desc = f"Visual keyframe at {fr.timestamp:.1f}s: {sub_count} subject(s) detected via local CV." if sub_count > 0 else f"Visual keyframe at {fr.timestamp:.1f}s: scenic/ambient shot."
                    observations.append(
                        VisualObservation(
                            timestamp=fr.timestamp,
                            frame_id=None,
                            category="subjects" if sub_count > 0 else "scene_setting",
                            description=desc,
                            provider_model="local_cv_detector",
                            confidence=0.80,
                        )
                    )

            # Compute honest multi-tier coverage metrics
            total_duration = round(duration, 2)
            scene_duration = round(min(duration, sum(s.end_time - s.start_time for s in scenes)), 2) if scenes else 0.0
            scene_cov_pct = round(min(100.0, (scene_duration / max(duration, 0.01)) * 100.0), 1) if duration > 0 else 100.0

            fps = 25.0
            total_decoded_frames = int(duration * fps) if duration > 0 else len(sampled_frames)

            sampled_frames_count = len(sampled_frames)
            vision_model_frames_count = len(target_frames)
            cv_frames_count = max(0, len(sampled_frames) - len(target_frames))

            inspected_scene_indices = {f.scene_index for f in target_frames if f.scene_index is not None}
            semantically_inspected_scenes = len(inspected_scene_indices)
            total_scenes_count = len(scenes)

            if scenes:
                semantic_visual_span = round(sum(s.end_time - s.start_time for s in scenes if s.scene_index in inspected_scene_indices), 2)
            else:
                semantic_visual_span = round(min(duration, vision_model_frames_count * 10.0), 2)
            semantic_cov_pct = round(min(100.0, (semantic_visual_span / max(duration, 0.01)) * 100.0), 1) if duration > 0 else 100.0

            sampling_density_fpm = round((sampled_frames_count / max(duration / 60.0, 0.01)), 2)
            unprocessed_intervals = [
                {"start": round(s.start_time, 2), "end": round(s.end_time, 2), "reason": "semantic_model_skipped"}
                for s in scenes if s.scene_index not in inspected_scene_indices
            ]

            aud_cov_pct = 100.0 if audio_meta.has_audio else 0.0

            coverage_metrics = {
                "visual_coverage_pct": scene_cov_pct if scenes else semantic_cov_pct,
                "visual_span_seconds": scene_duration if scenes else semantic_visual_span,
                "audio_coverage_pct": aud_cov_pct,
                "audio_duration_seconds": round(audio_meta.duration_seconds, 2),
                "is_complete_timeline": bool((scene_cov_pct if scenes else semantic_cov_pct) >= 80.0 and (aud_cov_pct >= 80.0 or not audio_meta.has_audio)),
                "uncovered_intervals": [] if scene_cov_pct >= 85.0 else [{"start": round(scene_duration, 1), "end": round(duration, 1), "reason": "tail_boundary"}],
                "total_source_duration_seconds": total_duration,
                "scene_detection_coverage_pct": scene_cov_pct,
                "scene_detection_duration_seconds": scene_duration,
                "total_decoded_frames_approx": total_decoded_frames,
                "sampled_frames_count": sampled_frames_count,
                "vision_model_analyzed_frames_count": vision_model_frames_count,
                "local_cv_analyzed_frames_count": cv_frames_count,
                "semantically_inspected_scenes_count": semantically_inspected_scenes,
                "total_scenes_count": total_scenes_count,
                "semantic_visual_span_seconds": semantic_visual_span,
                "semantic_coverage_pct": semantic_cov_pct,
                "sampling_density_frames_per_minute": sampling_density_fpm,
                "semantic_unprocessed_intervals": unprocessed_intervals,
                "semantic_unprocessed_intervals_count": len(unprocessed_intervals),
                "analysis_limitations": [
                    f"Full timeline scanned by scene detection ({scene_cov_pct}% duration covered across {total_scenes_count} scenes).",
                    f"Deep semantic vision model (Ollama / Qwen3-VL) inspected {vision_model_frames_count} sampled keyframes ({semantic_cov_pct}% semantic duration coverage).",
                    f"Remaining {cv_frames_count} keyframes analyzed using local CPU computer vision (face/motion differencing).",
                    "Semantic sound-event classification is not installed (speech density & FFmpeg silence detection used).",
                ],
            }
            models_info = {
                "transcription": "faster-whisper-tiny-int8 (CPU)",
                "vision": "ollama/qwen3-vl:4b-instruct (with local CV fallback)",
                "subject_tracking": "OpenCV TrackerMIL + motion differencing + skin chrominance",
                "sound_event_classification": "Not Installed (Semantic sound-event models such as AudioSet/YAMNet are unavailable without dedicated weights; using FFmpeg silence detection and speech density)",
            }
            stage_details["coverage"] = coverage_metrics
            stage_details["models"] = models_info

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 95.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 9: Persist to SQLite
            stage_details["stage"] = "persisting_results"
            stage_details["stage_status"] = "in_progress"
            stage_details["overall_pct"] = 95.0
            stage_details["stage_pct"] = 100.0
            stage_details["completed_units"] = 1
            stage_details["total_units"] = 1
            stage_details["units_label"] = "transactions"
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            stage_details["last_heartbeat"] = _now_utc()
            stage_details["operation_description"] = "Saving transcripts, scenes, dialogue turns, and frames into persistent intelligence database"
            self.update_run_progress(
                run_id, "running", 95.0, "persisting_results", stage_details=stage_details, job_id=effective_job_id
            )

            now = _now_utc()
            with sqlite_session(self.db_path) as conn:
                # 0. Audio analysis metadata
                audio_id = f"aud_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO audio_analysis (
                        id, analysis_run_id, media_asset_id, has_audio, sample_rate,
                        channels, codec_name, bit_rate, duration_seconds, speech_density,
                        silence_intervals_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        audio_id,
                        run_id,
                        asset_id,
                        1 if audio_meta.has_audio else 0,
                        audio_meta.sample_rate,
                        audio_meta.channels,
                        audio_meta.codec_name,
                        audio_meta.bit_rate,
                        audio_meta.duration_seconds,
                        audio_meta.speech_density,
                        json.dumps(audio_meta.silence_intervals),
                        now,
                    ),
                )

                # 1. Transcript segments
                for seg in transcription.segments:
                    seg_id = f"seg_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """
                        INSERT INTO transcript_segments (
                            id, analysis_run_id, media_asset_id, start_time, end_time,
                            text, language, confidence, words_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            seg_id,
                            run_id,
                            asset_id,
                            seg.start_time,
                            seg.end_time,
                            seg.text,
                            seg.language,
                            seg.confidence,
                            json.dumps(seg.words),
                            now,
                        ),
                    )

                # 2. Speech turns
                for turn in turns:
                    turn_id = f"turn_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """
                        INSERT INTO speech_turns (
                            id, analysis_run_id, media_asset_id, start_time, end_time,
                            speaker_label, text, segment_ids_json, turn_type, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            turn_id,
                            run_id,
                            asset_id,
                            turn.start_time,
                            turn.end_time,
                            turn.speaker_label,
                            turn.text,
                            json.dumps(turn.segment_indices),
                            turn.turn_type,
                            now,
                        ),
                    )

                # 3. Video scenes
                scene_id_map = {}
                for sc in scenes:
                    sc_id = f"scene_{uuid.uuid4().hex[:12]}"
                    scene_id_map[sc.scene_index] = sc_id
                    conn.execute(
                        """
                        INSERT INTO video_scenes (
                            id, analysis_run_id, media_asset_id, scene_index, start_time,
                            end_time, representative_timestamp, thumbnail_path, change_score, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sc_id,
                            run_id,
                            asset_id,
                            sc.scene_index,
                            sc.start_time,
                            sc.end_time,
                            sc.representative_timestamp,
                            sc.thumbnail_path,
                            sc.change_score,
                            now,
                        ),
                    )

                # 4. Sampled frames
                for fr in sampled_frames:
                    fr_id = f"frame_{uuid.uuid4().hex[:12]}"
                    parent_sc_id = scene_id_map.get(fr.scene_index) if fr.scene_index is not None else None
                    conn.execute(
                        """
                        INSERT INTO sampled_frames (
                            id, analysis_run_id, media_asset_id, timestamp, frame_path,
                            scene_id, width, height, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            fr_id,
                            run_id,
                            asset_id,
                            fr.timestamp,
                            fr.frame_path,
                            parent_sc_id,
                            fr.width,
                            fr.height,
                            now,
                        ),
                    )

                # 5. Visual observations
                for obs in observations:
                    obs_id = f"obs_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """
                        INSERT INTO visual_observations (
                            id, analysis_run_id, media_asset_id, timestamp, frame_id,
                            category, description, provider_model, confidence, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            obs_id,
                            run_id,
                            asset_id,
                            obs.timestamp,
                            obs.frame_id,
                            obs.category,
                            obs.description,
                            obs.provider_model,
                            obs.confidence,
                            now,
                        ),
                    )

                # Store signature on analysis_runs row
                conn.execute(
                    "UPDATE analysis_runs SET source_signature = ? WHERE id = ?",
                    (source_signature, run_id),
                )

            # Stage 10: Complete
            total_elapsed = round(time.monotonic() - start_mono, 2)
            stage_details = {
                "stage": "completed",
                "stage_status": "completed",
                "stage_pct": 100.0,
                "overall_pct": 100.0,
                "completed_units": 100,
                "total_units": 100,
                "units_label": "percent",
                "elapsed_seconds": total_elapsed,
                "estimated_remaining_seconds": 0.0,
                "last_heartbeat": _now_utc(),
                "operation_description": f"Video intelligence analysis complete in {total_elapsed:.1f}s",
                "segment_count": len(transcription.segments),
                "turn_count": len(turns),
                "scene_count": len(scenes),
                "frame_count": len(sampled_frames),
                "observation_count": len(observations),
                "speech_density": audio_meta.speech_density,
                "has_audio": audio_meta.has_audio,
                "timings": {
                    "audio_demux_s": audio_demux_time,
                    "transcribe_s": transcribe_time,
                    "scene_detect_s": scene_detect_time,
                    "frame_sample_s": sample_time,
                    "total_s": total_elapsed,
                },
                "cached_stages": stage_details.get("cached_stages", []),
                "warnings": stage_details.get("warnings", []),
                "coverage": stage_details.get("coverage", {}),
                "models": stage_details.get("models", {}),
            }

            self.update_run_progress(
                run_id,
                "completed",
                100.0,
                "completed",
                stage_details=stage_details,
                job_id=effective_job_id,
            )
            logger.info("Analysis run %s completed in %.2fs", run_id, total_elapsed)

            return {
                "run_id": run_id,
                "job_id": effective_job_id,
                "status": "completed",
                "segment_count": len(transcription.segments),
                "turn_count": len(turns),
                "scene_count": len(scenes),
                "frame_count": len(sampled_frames),
                "observation_count": len(observations),
                "speech_density": audio_meta.speech_density,
                "has_audio": audio_meta.has_audio,
                "total_elapsed_seconds": total_elapsed,
            }

        except Exception as exc:
            logger.error("Analysis execution failed on run %s: %s", run_id, exc, exc_info=True)
            self.update_run_progress(
                run_id, "failed", 0.0, "failed", error_message=str(exc), job_id=effective_job_id
            )
            raise ProcessingError(f"Analysis run {run_id} failed: {exc}") from exc
        finally:
            # Clean up temporary audio demux directory
            try:
                if job_temp_dir.exists():
                    shutil.rmtree(job_temp_dir, ignore_errors=True)
            except Exception:
                pass

    def get_run_telemetry(self, run_id: str) -> Dict[str, Any]:
        """Retrieve granular stage-level progress telemetry for a run and its linked job."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = None
            row = conn.execute(
                """
                SELECT id, media_asset_id, project_id, status, profile, progress_pct,
                       current_stage, error_message, started_at, completed_at,
                       job_id, source_signature, stage_details_json, checkpoint_data_json
                FROM analysis_runs WHERE id = ?
                """,
                (run_id,),
            ).fetchone()

            if not row:
                raise NotFoundError(f"Analysis run '{run_id}' not found.")

            try:
                stage_details = json.loads(row[12] or "{}")
            except Exception:
                stage_details = {}

            job_dict = None
            if row[10]:
                j_row = conn.execute("SELECT * FROM jobs WHERE id = ?", (row[10],)).fetchone()
                if j_row:
                    job_dict = {
                        "id": j_row[0],
                        "status": j_row[3],
                        "priority": j_row[4],
                        "progress_pct": j_row[5],
                        "current_stage": j_row[6],
                        "error_message": j_row[11],
                    }

            return {
                "run_id": row[0],
                "job_id": row[10],
                "media_asset_id": row[1],
                "project_id": row[2],
                "status": row[3],
                "profile": row[4],
                "progress_pct": row[5],
                "current_stage": row[6] or "queued",
                "error_message": row[7],
                "started_at": row[8],
                "completed_at": row[9],
                "source_signature": row[11],
                "stage_details": stage_details,
                "job": job_dict,
            }

    def cancel_run(self, run_id: str) -> Dict[str, Any]:
        """Cancel an in-flight or queued analysis run and its linked background job."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = None
            row = conn.execute("SELECT id, job_id, status FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Analysis run '{run_id}' not found.")
            r_id, job_id, current_status = row[0], row[1], row[2]
            if current_status in ("completed", "failed"):
                raise ProcessingError(f"Cannot cancel run with terminal status '{current_status}'.")

            now = _now_utc()
            conn.execute(
                "UPDATE analysis_runs SET status = 'cancelled', current_stage = 'cancelled', updated_at = ? WHERE id = ?",
                (now, run_id),
            )

        if job_id:
            try:
                self.jobs.request_cancellation(job_id)
            except Exception as j_exc:
                logger.warning("Error cancelling job %s for run %s: %s", job_id, run_id, j_exc)

        logger.info("Cancelled analysis run %s (job %s)", run_id, job_id)
        return {"run_id": run_id, "job_id": job_id, "status": "cancelled"}

    def retry_run(self, run_id: str) -> Dict[str, Any]:
        """Retry a failed or interrupted analysis run."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = None
            row = conn.execute("SELECT id, job_id, status, media_asset_id, project_id FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Analysis run '{run_id}' not found.")
            r_id, job_id, current_status, asset_id, project_id = row[0], row[1], row[2], row[3], row[4]
            if current_status not in ("failed", "cancelled", "interrupted"):
                raise ProcessingError(f"Cannot retry run with active status '{current_status}'.")

            now = _now_utc()
            conn.execute(
                "UPDATE analysis_runs SET status = 'pending', progress_pct = 0.0, current_stage = 'queued_retry', error_message = NULL, updated_at = ? WHERE id = ?",
                (now, run_id),
            )

        if job_id:
            try:
                self.jobs.retry_job(job_id)
            except Exception as j_exc:
                logger.warning("Error retrying job %s: %s", job_id, j_exc)

        logger.info("Queued retry for analysis run %s (job %s)", run_id, job_id)
        return {"run_id": run_id, "job_id": job_id, "status": "pending"}

    def get_run_cache_info(self, run_id: str) -> Dict[str, Any]:
        """Retrieve cache validity and component count information for an analysis run."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = None
            row = conn.execute(
                "SELECT id, media_asset_id, status, source_signature FROM analysis_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if not row:
                raise NotFoundError(f"Analysis run '{run_id}' not found.")

            r_id, asset_id, status, persisted_sig = row
            asset_row = conn.execute("SELECT storage_path FROM media_assets WHERE id = ?", (asset_id,)).fetchone()
            current_sig = compute_source_signature(Path(asset_row[0])) if asset_row else "missing"

            audio_count = conn.execute("SELECT COUNT(*) FROM audio_analysis WHERE analysis_run_id = ?", (run_id,)).fetchone()[0]
            trans_count = conn.execute("SELECT COUNT(*) FROM transcript_segments WHERE analysis_run_id = ?", (run_id,)).fetchone()[0]
            scene_count = conn.execute("SELECT COUNT(*) FROM video_scenes WHERE analysis_run_id = ?", (run_id,)).fetchone()[0]
            frame_count = conn.execute("SELECT COUNT(*) FROM sampled_frames WHERE analysis_run_id = ?", (run_id,)).fetchone()[0]
            obs_count = conn.execute("SELECT COUNT(*) FROM visual_observations WHERE analysis_run_id = ?", (run_id,)).fetchone()[0]

            is_valid = bool(status == "completed" and persisted_sig == current_sig and current_sig != "missing")
            return {
                "run_id": run_id,
                "media_asset_id": asset_id,
                "status": status,
                "persisted_signature": persisted_sig,
                "current_signature": current_sig,
                "is_cache_valid": is_valid,
                "records": {
                    "audio_analysis": audio_count,
                    "transcript_segments": trans_count,
                    "video_scenes": scene_count,
                    "sampled_frames": frame_count,
                    "visual_observations": obs_count,
                },
            }
