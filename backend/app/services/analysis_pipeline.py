"""Orchestrates multi-stage video analysis: audio, whisper, dialogue, scenes, visual frames & vision."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import Settings, get_settings
from app.core.storage import StorageLayout
from app.core.errors import NotFoundError, ProcessingError
from app.db.connection import sqlite_session
from app.services.audio_extractor import extract_audio_16k_mono
from app.services.frame_sampler import sample_analysis_frames
from app.services.scene_detector import detect_scenes_ffmpeg
from app.services.speech_segmentation import segment_dialogue_turns
from app.services.transcription import WhisperTranscriber
from app.services.visual_understanding import OllamaVisionAnalyzer

logger = logging.getLogger("zezedit.analysis_pipeline")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class VideoAnalysisPipeline:
    """Coordinates modular video analysis stages."""

    def __init__(self, settings: Optional[Settings] = None, db_path: Optional[Path] = None) -> None:
        self.settings = settings or get_settings()
        layout = StorageLayout.from_root(self.settings.storage_root)
        self.storage_root = layout.root
        self.db_path = db_path or layout.db_file
        self.transcriber = WhisperTranscriber(model_size="tiny", device="cpu", compute_type="int8")
        self.vision_analyzer = OllamaVisionAnalyzer()

    def create_analysis_run(
        self,
        media_asset_id: str,
        project_id: str,
        profile: str = "balanced",
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a pending analysis run record."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = _now_utc()
        config_json = json.dumps(config or {})

        with sqlite_session(self.db_path) as conn:
            # Verify asset exists
            asset = conn.execute(
                "SELECT id, duration_seconds FROM media_assets WHERE id = ? AND project_id = ?",
                (media_asset_id, project_id),
            ).fetchone()
            if not asset:
                raise NotFoundError(f"Media asset '{media_asset_id}' not found in project '{project_id}'.")

            conn.execute(
                """
                INSERT INTO analysis_runs (
                    id, media_asset_id, project_id, status, profile, config_json,
                    progress_pct, current_stage, created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', ?, ?, 0.0, 'queued', ?, ?)
                """,
                (run_id, media_asset_id, project_id, profile, config_json, now, now),
            )

        logger.info("Created analysis run %s for asset %s (profile: %s)", run_id, media_asset_id, profile)
        return run_id

    def update_run_progress(
        self,
        run_id: str,
        status: str,
        progress_pct: float,
        current_stage: str,
        error_message: Optional[str] = None,
    ) -> None:
        now = _now_utc()
        with sqlite_session(self.db_path) as conn:
            started_at = now if status == "running" and progress_pct <= 5.0 else None
            completed_at = now if status in ("completed", "failed", "cancelled") else None

            if started_at:
                conn.execute(
                    """
                    UPDATE analysis_runs
                    SET status = ?, progress_pct = ?, current_stage = ?, updated_at = ?, started_at = coalesce(started_at, ?)
                    WHERE id = ?
                    """,
                    (status, progress_pct, current_stage, now, started_at, run_id),
                )
            elif completed_at:
                conn.execute(
                    """
                    UPDATE analysis_runs
                    SET status = ?, progress_pct = ?, current_stage = ?, error_message = ?, updated_at = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (status, progress_pct, current_stage, error_message, now, completed_at, run_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE analysis_runs
                    SET status = ?, progress_pct = ?, current_stage = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, progress_pct, current_stage, now, run_id),
                )

    def is_cancelled(self, run_id: str) -> bool:
        with sqlite_session(self.db_path) as conn:
            row = conn.execute("SELECT status FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
            return bool(row and row[0] == "cancelled")

    async def execute_analysis(self, run_id: str) -> Dict[str, Any]:
        """Execute all analysis stages asynchronously."""
        with sqlite_session(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT a.id, a.media_asset_id, a.project_id, a.profile, a.config_json,
                       m.storage_path, m.duration_seconds, m.media_type
                FROM analysis_runs a
                JOIN media_assets m ON a.media_asset_id = m.id
                WHERE a.id = ?
                """,
                (run_id,),
            ).fetchone()

        if not row:
            raise NotFoundError(f"Analysis run {run_id} not found.")

        run_id, asset_id, project_id, profile, config_json_str, storage_path_str, duration, media_type = row
        media_path = Path(storage_path_str)
        duration = float(duration or 0.0)

        if not media_path.exists():
            self.update_run_progress(run_id, "failed", 0.0, "failed", f"Media file not found at {media_path}")
            raise ProcessingError(f"Media file not found at {media_path}")

        try:
            self.update_run_progress(run_id, "running", 5.0, "extracting_audio")
            if self.is_cancelled(run_id):
                return {"status": "cancelled"}

            # Prepare directories
            job_temp_dir = self.storage_root / "temp" / "analysis" / run_id
            job_temp_dir.mkdir(parents=True, exist_ok=True)
            frames_dir = self.storage_root / "analysis" / asset_id / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)

            # Stage 1: Audio Extraction
            audio_path = job_temp_dir / "audio_16k.wav"
            extract_audio_16k_mono(media_path, audio_path)

            self.update_run_progress(run_id, "running", 20.0, "transcribing_speech")
            if self.is_cancelled(run_id):
                return {"status": "cancelled"}

            # Stage 2: Faster-Whisper Speech Recognition
            transcription = self.transcriber.transcribe(audio_path)

            self.update_run_progress(run_id, "running", 45.0, "segmenting_dialogue")
            if self.is_cancelled(run_id):
                return {"status": "cancelled"}

            # Stage 3: Speech Turn & Dialogue Segmentation
            turns = segment_dialogue_turns(transcription.segments)

            self.update_run_progress(run_id, "running", 55.0, "detecting_scenes")
            if self.is_cancelled(run_id):
                return {"status": "cancelled"}

            # Stage 4: Scene Detection (for video assets)
            scenes = []
            if media_type == "video" and duration > 0.5:
                scenes = detect_scenes_ffmpeg(media_path, duration_seconds=duration)
            else:
                from app.services.scene_detector import DetectedScene
                scenes = [DetectedScene(0, 0.0, max(duration, 1.0), max(duration / 2.0, 0.5), 0.0)]

            self.update_run_progress(run_id, "running", 70.0, "sampling_frames")
            if self.is_cancelled(run_id):
                return {"status": "cancelled"}

            # Stage 5: Frame Sampling
            sampled_frames = []
            if media_type == "video" and duration > 0.5:
                max_frames = 20 if profile == "fast" else (50 if profile == "balanced" else 100)
                sampled_frames = sample_analysis_frames(
                    media_path,
                    frames_dir,
                    scenes,
                    duration_seconds=duration,
                    max_frames=max_frames,
                )

            self.update_run_progress(run_id, "running", 80.0, "analyzing_visuals")
            if self.is_cancelled(run_id):
                return {"status": "cancelled"}

            # Stage 6: Visual Understanding via Ollama
            observations = []
            # Check if ollama is available; if not, graceful fallback is automatic in analyzer
            for frame in sampled_frames[:10]: # cap Ollama queries per run for latency
                frame_obs = await self.vision_analyzer.analyze_frame(
                    Path(frame.frame_path),
                    timestamp=frame.timestamp,
                )
                observations.extend(frame_obs)

            self.update_run_progress(run_id, "running", 90.0, "persisting_results")
            if self.is_cancelled(run_id):
                return {"status": "cancelled"}

            # Stage 7: Persist everything to SQLite
            now = _now_utc()
            with sqlite_session(self.db_path) as conn:
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
                            seg_id, run_id, asset_id, seg.start_time, seg.end_time,
                            seg.text, seg.language, seg.confidence, json.dumps(seg.words), now
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
                            turn_id, run_id, asset_id, turn.start_time, turn.end_time,
                            turn.speaker_label, turn.text, json.dumps(turn.segment_indices), turn.turn_type, now
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
                            sc_id, run_id, asset_id, sc.scene_index, sc.start_time,
                            sc.end_time, sc.representative_timestamp, sc.thumbnail_path, sc.change_score, now
                        ),
                    )

                # 4. Sampled frames
                frame_id_list = []
                for fr in sampled_frames:
                    fr_id = f"frame_{uuid.uuid4().hex[:12]}"
                    frame_id_list.append(fr_id)
                    parent_sc_id = scene_id_map.get(fr.scene_index) if fr.scene_index is not None else None
                    conn.execute(
                        """
                        INSERT INTO sampled_frames (
                            id, analysis_run_id, media_asset_id, timestamp, frame_path,
                            scene_id, width, height, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            fr_id, run_id, asset_id, fr.timestamp, fr.frame_path,
                            parent_sc_id, fr.width, fr.height, now
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
                            obs_id, run_id, asset_id, obs.timestamp, obs.frame_id,
                            obs.category, obs.description, obs.provider_model, obs.confidence, now
                        ),
                    )

            # Stage 8: Mark completed
            self.update_run_progress(run_id, "completed", 100.0, "completed")
            logger.info("Analysis run %s completed successfully", run_id)

            return {
                "run_id": run_id,
                "status": "completed",
                "segment_count": len(transcription.segments),
                "turn_count": len(turns),
                "scene_count": len(scenes),
                "frame_count": len(sampled_frames),
                "observation_count": len(observations),
            }

        except Exception as exc:
            logger.error("Analysis execution failed on run %s: %s", run_id, exc, exc_info=True)
            self.update_run_progress(run_id, "failed", 0.0, "failed", str(exc))
            raise ProcessingError(f"Analysis run {run_id} failed: {exc}") from exc
        finally:
            # Clean up temporary audio file
            try:
                if job_temp_dir.exists():
                    import shutil
                    shutil.rmtree(job_temp_dir, ignore_errors=True)
            except Exception:
                pass
