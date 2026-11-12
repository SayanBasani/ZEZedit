"""Orchestrates multi-stage video analysis: audio, whisper, dialogue, scenes, visual frames & vision."""

import asyncio
import hashlib
import json
import logging
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.core.errors import NotFoundError, ProcessingError
from app.db.connection import sqlite_session
from app.services.audio_extractor import extract_audio_16k_mono, inspect_audio_stream, AudioMetadata
from app.services.frame_sampler import sample_analysis_frames, SampledFrame
from app.services.scene_detector import detect_scenes_ffmpeg, DetectedScene
from app.services.speech_segmentation import segment_dialogue_turns
from app.services.subject_tracker import SubjectTracker
from app.services.transcription import TranscriptionResult, WhisperTranscriber
from app.services.visual_understanding import OllamaVisionAnalyzer
from app.services.jobs import JobOrchestrator

logger = logging.getLogger("zezedit.analysis_pipeline")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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

    def create_analysis_run(
        self,
        media_asset_id: str,
        project_id: str,
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
            asset_row = conn.execute(
                "SELECT id, storage_path, duration_seconds FROM media_assets WHERE id = ? AND project_id = ?",
                (media_asset_id, project_id),
            ).fetchone()
            if not asset_row:
                raise NotFoundError(f"Media asset '{media_asset_id}' not found in project '{project_id}'.")

            media_path = Path(asset_row[1])
            source_sig = compute_source_signature(media_path)

            # Check for existing completed run if force_reanalysis is False (ZEZ-029 Stage-Aware Caching)
            if not force_reanalysis and source_sig != "missing":
                existing_run = conn.execute(
                    """
                    SELECT id, job_id FROM analysis_runs
                    WHERE media_asset_id = ? AND project_id = ? AND status = 'completed' AND source_signature = ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (media_asset_id, project_id, source_sig),
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

            # Create persistent job in JobOrchestrator
            job_record = self.jobs.create_job(
                job_type="media_analysis",
                project_id=project_id,
                priority=150,
                input_config={
                    "media_asset_id": media_asset_id,
                    "profile": profile,
                    "force_reanalysis": force_reanalysis,
                    "source_signature": source_sig,
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
                    created_at, updated_at, job_id, source_signature, stage_details_json, checkpoint_data_json
                ) VALUES (?, ?, ?, 'pending', ?, ?, 0.0, 'queued', NULL, NULL, NULL, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    run_id,
                    media_asset_id,
                    project_id,
                    profile,
                    json.dumps(config_dict),
                    now,
                    now,
                    job_record.id,
                    source_sig,
                    json.dumps(stage_details),
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
            "stage_pct": 100.0,
            "overall_pct": 5.0,
            "elapsed_seconds": round(time.monotonic() - start_mono, 2),
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
            raise ProcessingError(err_msg)

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
            stage_details["overall_pct"] = 10.0
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            self.update_run_progress(
                run_id, "running", 10.0, "extracting_metadata", stage_details=stage_details, job_id=effective_job_id
            )

            audio_meta = inspect_audio_stream(media_path)
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
            stage_details["overall_pct"] = 25.0
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            self.update_run_progress(
                run_id, "running", 25.0, "extracting_audio", stage_details=stage_details, job_id=effective_job_id
            )

            audio_path = job_temp_dir / "audio_16k.wav"
            t_audio_start = time.monotonic()
            _, audio_meta = extract_audio_16k_mono(
                media_path,
                audio_path,
                max_duration_seconds=duration,
                return_metadata=True,
            )
            audio_demux_time = round(time.monotonic() - t_audio_start, 2)
            logger.info("Audio demux for %s took %.2fs (speech_density: %.2f)", media_path.name, audio_demux_time, audio_meta.speech_density)

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 25.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 4: Speech Transcription (Faster-Whisper CPU int8)
            stage_details["stage"] = "transcribing_speech"
            stage_details["overall_pct"] = 45.0
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            self.update_run_progress(
                run_id, "running", 45.0, "transcribing_speech", stage_details=stage_details, job_id=effective_job_id
            )

            t_trans_start = time.monotonic()
            if audio_meta.has_audio and audio_meta.duration_seconds > 0.1:
                transcription = self.transcriber.transcribe(audio_path)
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
                self.update_run_progress(run_id, "cancelled", 45.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 5: Speech Turn & Dialogue Segmentation
            stage_details["stage"] = "segmenting_dialogue"
            stage_details["overall_pct"] = 55.0
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            self.update_run_progress(
                run_id, "running", 55.0, "segmenting_dialogue", stage_details=stage_details, job_id=effective_job_id
            )

            turns = segment_dialogue_turns(transcription.segments)

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 55.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 6: Scene Boundary Cut Detection (FFmpeg / PySceneDetect)
            stage_details["stage"] = "detecting_scenes"
            stage_details["overall_pct"] = 70.0
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            self.update_run_progress(
                run_id, "running", 70.0, "detecting_scenes", stage_details=stage_details, job_id=effective_job_id
            )

            t_scene_start = time.monotonic()
            scenes: List[DetectedScene] = []
            if media_type == "video" and duration > 0.5:
                scenes = detect_scenes_ffmpeg(
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
            stage_details["overall_pct"] = 80.0
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            self.update_run_progress(
                run_id, "running", 80.0, "sampling_frames", stage_details=stage_details, job_id=effective_job_id
            )

            t_sample_start = time.monotonic()
            sampled_frames: List[SampledFrame] = []
            if media_type == "video" and duration > 0.5:
                max_frames = 20 if profile == "fast" else (50 if profile == "balanced" else 100)
                sampled_frames = sample_analysis_frames(
                    media_path,
                    frames_dir,
                    scenes,
                    duration_seconds=duration,
                    max_frames=max_frames,
                )
            sample_time = round(time.monotonic() - t_sample_start, 2)
            logger.info("Sampled %d frames for %s in %.2fs", len(sampled_frames), media_path.name, sample_time)

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 80.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 8: Visual Understanding and Subject Tracking
            stage_details["stage"] = "analyzing_visuals"
            stage_details["overall_pct"] = 90.0
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
            self.update_run_progress(
                run_id, "running", 90.0, "analyzing_visuals", stage_details=stage_details, job_id=effective_job_id
            )

            observations = []
            if hasattr(self.vision_analyzer, "reset"):
                self.vision_analyzer.reset()
            sample_count = 5 if profile == "fast" else (12 if profile == "balanced" else 25)
            for frame in sampled_frames[:sample_count]:
                frame_path = Path(frame.frame_path)
                frame_obs = await self.vision_analyzer.analyze_frame(
                    frame_path,
                    timestamp=frame.timestamp,
                )
                observations.extend(frame_obs)

            if self.is_cancelled(run_id, effective_job_id):
                self.update_run_progress(run_id, "cancelled", 90.0, "cancelled", job_id=effective_job_id)
                return {"status": "cancelled"}

            # Stage 9: Persist to SQLite
            stage_details["stage"] = "persisting_results"
            stage_details["overall_pct"] = 95.0
            stage_details["elapsed_seconds"] = round(time.monotonic() - start_mono, 2)
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
                "stage_pct": 100.0,
                "overall_pct": 100.0,
                "elapsed_seconds": total_elapsed,
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
