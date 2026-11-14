"""Modular 15-stage video rendering engine, export pipeline, and automatic Shorts generation service."""

import datetime
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import Settings, get_settings
from app.core.errors import AppError, NotFoundError, ProcessingError, ValidationError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.models.entities import JobRecord
from app.models.export import (
    STANDARD_EXPORT_PRESETS,
    AudioConfig,
    CaptionConfig,
    ExportPreset,
    ExportRecord,
    RenderExportRequest,
    ValidationDetails,
)
from app.models.reframing import CropKeyframe
from app.services.audio_pipeline import AudioPipeline
from app.services.caption_engine import CaptionEngine
from app.services.jobs import JobOrchestrator
from app.services.output_validator import OutputValidator
from app.services.reframing_renderer import build_crop_filter_expression
from app.services.reframing_service import ReframingService

logger = logging.getLogger("zezedit.export.service")

# Global thread-safe map of active render subprocesses for clean cancellation
_ACTIVE_RENDER_PROCESSES: Dict[str, subprocess.Popen] = {}
_PROCESS_LOCK = threading.Lock()


class ExportService:
    """Coordinates validation, reframing, captioning, audio filtering, FFmpeg execution, and output validation."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.layout = StorageLayout.from_root(self.settings.storage_root)
        self.db_path = db_path or self.layout.db_file
        self.jobs = JobOrchestrator(self.settings, self.db_path)
        self.reframing_service = ReframingService(self.settings, self.db_path)
        self.validator = OutputValidator(
            ffprobe_path=self.settings.ffprobe_path,
            ffmpeg_path=self.settings.ffmpeg_path,
        )

    # -------------------------------------------------------------------------
    # Public API: Submission & Querying
    # -------------------------------------------------------------------------

    def get_presets(self) -> List[ExportPreset]:
        """Return available standard export presets."""
        return list(STANDARD_EXPORT_PRESETS.values())

    def submit_export_job(
        self,
        project_id: str,
        request: RenderExportRequest,
    ) -> Dict[str, Any]:
        """Validate request and enqueue a background render job."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 1. Validate project
            proj = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not proj:
                raise NotFoundError(f"Project '{project_id}' does not exist.")

            # 2. Validate candidate
            cand = conn.execute(
                "SELECT * FROM shorts_candidates WHERE id = ? AND project_id = ?",
                (request.candidate_id, project_id),
            ).fetchone()
            if not cand:
                raise NotFoundError(f"Shorts candidate '{request.candidate_id}' not found in project '{project_id}'.")

            # Check for candidate clip edits (trims, aspect ratio override, framing adjustments)
            clip_edit_row = conn.execute(
                """
                SELECT * FROM candidate_clip_edits
                WHERE candidate_id = ?
                """,
                (request.candidate_id,),
            ).fetchone()

            # Resolve effective interval
            if clip_edit_row and clip_edit_row["edited_start_time"] is not None and clip_edit_row["edited_end_time"] is not None:
                start_t = float(clip_edit_row["edited_start_time"])
                end_t = float(clip_edit_row["edited_end_time"])
            else:
                start_t = float(cand["start_time"])
                end_t = float(cand["end_time"])

            duration = round(end_t - start_t, 3)
            if duration < 1.0:
                raise ValidationError(f"Invalid candidate duration: {duration}s. Minimum export duration is 1.0s.")

            # Resolve preset (from request or clip_edit aspect_ratio)
            effective_preset_id = request.preset_id
            if clip_edit_row and clip_edit_row["aspect_ratio"]:
                aspect = clip_edit_row["aspect_ratio"]
                ratio_map = {
                    "9:16": "shorts_reels_9_16",
                    "16:9": "landscape_16_9",
                    "1:1": "square_1_1",
                    "4:5": "portrait_4_5",
                    "4:3": "standard_4_3",
                    "3:4": "tall_3_4",
                }
                if aspect in ratio_map and (not request.preset_id or request.preset_id == "shorts_reels_9_16"):
                    effective_preset_id = ratio_map[aspect]

            preset = STANDARD_EXPORT_PRESETS.get(effective_preset_id)
            if not preset:
                preset = STANDARD_EXPORT_PRESETS["shorts_reels_9_16"]

            export_id = f"exp_{uuid.uuid4().hex[:12]}"
            title = request.title or cand["title"] or cand["suggested_title"] or f"Short_{cand['id'][:8]}"
            clean_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title)[:40]
            output_filename = f"{clean_title}_{preset.target_aspect_ratio.replace(':', 'x')}_{export_id[-6:]}.mp4"

            # Create persistent job
            input_cfg = {
                "export_id": export_id,
                "project_id": project_id,
                "candidate_id": request.candidate_id,
                "media_asset_id": cand["media_asset_id"],
                "preset_id": preset.preset_id,
                "reframing_plan_id": request.reframing_plan_id or (clip_edit_row["reframing_plan_id"] if clip_edit_row else None),
                "framing_revision_id": request.framing_revision_id,
                "title": title,
                "output_filename": output_filename,
                "caption_config": request.caption_config.model_dump() if request.caption_config else CaptionConfig().model_dump(),
                "audio_config": request.audio_config.model_dump() if request.audio_config else AudioConfig().model_dump(),
                "crf": request.crf or preset.crf,
                "is_preview": request.is_preview,
                "clip_start_time": start_t,
                "clip_end_time": end_t,
            }

            job = self.jobs.create_job(
                job_type="export_render",
                project_id=project_id,
                priority=120 if request.is_preview else 100,
                input_config=input_cfg,
                media_asset_id=cand["media_asset_id"],
            )

            # Insert initial export record
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO exports (
                    id, project_id, candidate_id, media_asset_id, reframing_plan_id,
                    framing_revision_id, render_job_id, title, export_preset,
                    target_aspect_ratio, target_width, target_height, video_codec,
                    audio_codec, pixel_fmt, fps, crf, video_bitrate, audio_bitrate,
                    caption_config_json, audio_config_json, output_path, output_filename,
                    file_size_bytes, duration_seconds, status, validation_status,
                    validation_details_json, error_message, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 0, ?, 'queued', 'unvalidated', '{}', NULL, ?, NULL)
                """,
                (
                    export_id,
                    project_id,
                    request.candidate_id,
                    cand["media_asset_id"],
                    request.reframing_plan_id,
                    request.framing_revision_id,
                    job.id,
                    title,
                    preset.preset_id,
                    preset.target_aspect_ratio,
                    preset.target_width if not request.is_preview else int(preset.target_width * 480 / preset.target_height),
                    preset.target_height if not request.is_preview else 480,
                    preset.video_codec,
                    preset.audio_codec,
                    preset.pixel_fmt,
                    preset.fps,
                    input_cfg["crf"],
                    preset.video_bitrate,
                    preset.audio_bitrate,
                    json.dumps(input_cfg["caption_config"]),
                    json.dumps(input_cfg["audio_config"]),
                    output_filename,
                    duration,
                    now,
                ),
            )

        logger.info("Enqueued export render job: export_id=%s, job_id=%s, candidate=%s", export_id, job.id, request.candidate_id)
        return {
            "export_id": export_id,
            "job_id": job.id,
            "status": "queued",
            "output_filename": output_filename,
        }

    def list_exports(
        self,
        project_id: str,
        candidate_id: Optional[str] = None,
        media_asset_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ExportRecord]:
        """List exports for a project with optional candidate or media asset filtering."""
        query = "SELECT * FROM exports WHERE project_id = ?"
        params: list = [project_id]
        if candidate_id:
            query += " AND candidate_id = ?"
            params.append(candidate_id)
        if media_asset_id:
            query += " AND media_asset_id = ?"
            params.append(media_asset_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_export_record(r) for r in rows]

    def get_export(self, project_id: str, export_id: str) -> ExportRecord:
        """Fetch a specific export record."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM exports WHERE id = ? AND project_id = ?",
                (export_id, project_id),
            ).fetchone()
            if not row:
                raise NotFoundError(f"Export '{export_id}' not found in project '{project_id}'.")
            return self._row_to_export_record(row)

    def delete_export(self, project_id: str, export_id: str) -> bool:
        """Delete an export record and its generated output video file."""
        export = self.get_export(project_id, export_id)
        if export.output_path:
            p = Path(export.output_path)
            if p.exists():
                try:
                    p.unlink(missing_ok=True)
                except Exception as exc:
                    logger.warning("Could not delete export file %s: %s", p, exc)

        with sqlite_session(self.db_path) as conn:
            conn.execute("DELETE FROM exports WHERE id = ? AND project_id = ?", (export_id, project_id))
        return True

    def cancel_export_render(self, project_id: str, export_id: str) -> Dict[str, Any]:
        """Cancel an ongoing render job and terminate the FFmpeg process."""
        export = self.get_export(project_id, export_id)
        if not export.render_job_id:
            return {"status": export.status, "cancelled": False}

        job_id = export.render_job_id

        # Terminate active process
        with _PROCESS_LOCK:
            proc = _ACTIVE_RENDER_PROCESSES.get(job_id)
            if proc:
                logger.info("Terminating FFmpeg render process (PID %d) for job %s", proc.pid, job_id)
                try:
                    proc.kill()
                except Exception as exc:
                    logger.warning("Failed to kill FFmpeg process: %s", exc)

        self.jobs.request_cancellation(job_id)

        with sqlite_session(self.db_path) as conn:
            conn.execute(
                "UPDATE exports SET status = 'cancelled', error_message = 'Cancelled by user', completed_at = datetime('now') WHERE id = ?",
                (export_id,),
            )

        return {"export_id": export_id, "job_id": job_id, "status": "cancelled"}

    # -------------------------------------------------------------------------
    # Core 15-Stage Execution Pipeline
    # -------------------------------------------------------------------------

    def execute_render_job(self, job_id: str) -> Dict[str, Any]:
        """Execute the 15-stage export render synchronously, reporting progress to JobOrchestrator."""
        job = self.jobs.get_job(job_id)
        cfg = job.input_config
        export_id = cfg["export_id"]
        project_id = cfg["project_id"]
        candidate_id = cfg["candidate_id"]
        media_asset_id = cfg["media_asset_id"]
        preset_id = cfg.get("preset_id", "shorts_reels_9_16")
        is_preview = cfg.get("is_preview", False)

        caption_cfg = CaptionConfig(**cfg.get("caption_config", {}))
        audio_cfg = AudioConfig(**cfg.get("audio_config", {}))
        preset = STANDARD_EXPORT_PRESETS.get(preset_id, STANDARD_EXPORT_PRESETS["shorts_reels_9_16"])

        target_w = preset.target_width if not is_preview else int(preset.target_width * 480 / preset.target_height)
        target_h = preset.target_height if not is_preview else 480
        # Ensure even dimensions
        target_w = (target_w // 2) * 2
        target_h = (target_h // 2) * 2

        crf = cfg.get("crf", preset.crf)

        # Stage 1: Validate export request
        self.jobs.transition_job_state(job_id, "running", progress_pct=5.0, stage="validating_request")

        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("UPDATE exports SET status = 'rendering' WHERE id = ?", (export_id,))

            # Stage 2: Load candidate
            cand = conn.execute(
                "SELECT * FROM shorts_candidates WHERE id = ? AND project_id = ?",
                (candidate_id, project_id),
            ).fetchone()
            if not cand:
                raise NotFoundError(f"Candidate '{candidate_id}' not found.")

            # Check if explicit interval configured in job, or check clip edits
            clip_edit_row = conn.execute(
                "SELECT * FROM candidate_clip_edits WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()

            if cfg.get("clip_start_time") is not None and cfg.get("clip_end_time") is not None:
                clip_start = float(cfg["clip_start_time"])
                clip_end = float(cfg["clip_end_time"])
            elif clip_edit_row and clip_edit_row["edited_start_time"] is not None and clip_edit_row["edited_end_time"] is not None:
                clip_start = float(clip_edit_row["edited_start_time"])
                clip_end = float(clip_edit_row["edited_end_time"])
            else:
                clip_start = float(cand["start_time"])
                clip_end = float(cand["end_time"])

            duration = max(0.5, round(clip_end - clip_start, 3))

            # Stage 3: Resolve original media
            asset = conn.execute(
                "SELECT * FROM media_assets WHERE id = ? AND project_id = ?",
                (media_asset_id, project_id),
            ).fetchone()
            if not asset:
                raise NotFoundError(f"Media asset '{media_asset_id}' not found.")

            if asset["is_external"]:
                media_path = Path(asset["storage_path"])
            else:
                media_path = self.layout.media / asset["storage_path"]

            if not media_path.exists():
                raise NotFoundError(f"Source media file not found on disk: {media_path}")

            source_w = int(asset["width"] or 1920)
            source_h = int(asset["height"] or 1080)
            has_audio = self._check_media_has_audio(media_path)

            # Stage 4 & 5: Load or resolve reframing instructions
            self.jobs.transition_job_state(job_id, "running", progress_pct=15.0, stage="resolving_framing")

            keyframes = self._resolve_keyframes(
                conn=conn,
                project_id=project_id,
                media_asset_id=media_asset_id,
                candidate_id=candidate_id,
                plan_id=cfg.get("reframing_plan_id"),
                revision_id=cfg.get("framing_revision_id"),
                target_aspect=preset.target_aspect_ratio,
                start_time=clip_start,
                end_time=clip_end,
                source_w=source_w,
                source_h=source_h,
                clip_edit=dict(clip_edit_row) if clip_edit_row else None,
                job_id=job_id,
            )

            # Stage 6: Validate source interval
            if clip_start < 0 or clip_end <= clip_start:
                raise ValidationError(f"Invalid clip bounds: [{clip_start}, {clip_end}]")

            # Load transcript segments for captions
            transcript_rows = conn.execute(
                """
                SELECT * FROM transcript_segments
                WHERE media_asset_id = ? AND start_time < ? AND end_time > ?
                ORDER BY start_time ASC
                """,
                (media_asset_id, clip_end, clip_start),
            ).fetchall()
            segments = [dict(r) for r in transcript_rows]

            # Overlay any non-destructive transcript corrections (ZEZ-025)
            corr_rows = conn.execute(
                """
                SELECT segment_id, corrected_text FROM transcript_corrections
                WHERE media_asset_id = ?
                """,
                (media_asset_id,),
            ).fetchall()
            corr_map = {c["segment_id"]: c["corrected_text"] for c in corr_rows if c["segment_id"]}
            for s in segments:
                if s["id"] in corr_map:
                    s["text"] = corr_map[s["id"]]

        # Stage 7: Prepare temporary workspace
        job_temp_dir = self.layout.temp / f"job_{job_id}"
        job_temp_dir.mkdir(parents=True, exist_ok=True)
        temp_rendered_mp4 = job_temp_dir / "render_scratch.mp4"

        try:
            # Stage 8 & 9: Build video filtergraph (Dynamic Crop + Scaling)
            self.jobs.transition_job_state(job_id, "running", progress_pct=25.0, stage="compiling_filtergraph")

            crop_filter, cw, ch = build_crop_filter_expression(
                keyframes=keyframes,
                start_time=clip_start,
                end_time=clip_end,
                source_w=source_w,
                source_h=source_h,
                output_w=target_w,
                output_h=target_h,
            )

            vf_filters = [crop_filter]

            # Stage 10: Generate and attach captions if requested
            self.jobs.transition_job_state(job_id, "running", progress_pct=35.0, stage="generating_captions")
            if caption_cfg.mode != "none":
                caption_engine = CaptionEngine(caption_cfg)
                ass_path = job_temp_dir / "captions.ass"
                generated_ass = caption_engine.generate_ass_file(
                    transcript_segments=segments,
                    clip_start_time=clip_start,
                    clip_end_time=clip_end,
                    output_file_path=ass_path,
                    canvas_width=target_w,
                    canvas_height=target_h,
                )
                if generated_ass and generated_ass.exists():
                    # Use relative filename inside job_temp_dir to completely avoid Windows path escaping issues
                    vf_filters.append("ass=filename=captions.ass")

            vf_str = ",".join(vf_filters)

            # Stage 11: Apply audio processing filters
            self.jobs.transition_job_state(job_id, "running", progress_pct=45.0, stage="processing_audio")
            audio_pipe = AudioPipeline(audio_cfg)
            af_str, extra_audio_args = audio_pipe.build_audio_filters(
                duration=duration,
                has_source_audio=has_audio,
            )

            # Stage 12: Encode video and audio with real-time FFmpeg progress
            self.jobs.transition_job_state(job_id, "running", progress_pct=50.0, stage="rendering_video")

            cmd = [
                self.settings.ffmpeg_path or "ffmpeg",
                "-y",
                "-ss", f"{clip_start:.3f}",
                "-t", f"{duration:.3f}",
                "-i", str(media_path.resolve()),
            ]
            if extra_audio_args:
                cmd.extend(extra_audio_args)
                cmd.extend(["-map", "0:v:0", "-map", "1:a:0", "-shortest"])

            cmd.extend([
                "-vf", vf_str,
                "-c:v", preset.video_codec,
                "-preset", "faster" if not is_preview else "ultrafast",
                "-crf", str(crf),
                "-pix_fmt", preset.pixel_fmt,
            ])

            if af_str:
                cmd.extend(["-af", af_str])

            cmd.extend([
                "-c:a", preset.audio_codec,
                "-b:a", preset.audio_bitrate,
                "-ar", str(audio_cfg.sample_rate),
                "-ac", str(audio_cfg.channels),
                "-movflags", "+faststart",
                "-threads", str(self.settings.ffmpeg_threads),
                "-progress", "pipe:1",
                "-nostats",
                str(temp_rendered_mp4.resolve()),
            ])

            logger.info("Executing export render cmd in %s: %s", job_temp_dir, " ".join(cmd[:12]))

            proc = subprocess.Popen(
                cmd,
                cwd=str(job_temp_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            with _PROCESS_LOCK:
                _ACTIVE_RENDER_PROCESSES[job_id] = proc

            self.jobs.transition_job_state(job_id, "running", worker_pid=proc.pid, stage="rendering_video")

            # Parse real-time progress and error logs from stdout
            output_lines: List[str] = []
            if proc.stdout:
                for line in proc.stdout:
                    line_str = line.strip()
                    output_lines.append(line_str)
                    if line_str.startswith("out_time_us="):
                        try:
                            us = int(line_str.split("=")[1])
                            curr_sec = us / 1_000_000.0
                            pct = min(92.0, 50.0 + (curr_sec / max(0.1, duration)) * 42.0)
                            self.jobs.transition_job_state(
                                job_id, "running", progress_pct=round(pct, 1), stage="rendering_video"
                            )
                        except Exception:
                            pass

            proc.wait()

            with _PROCESS_LOCK:
                _ACTIVE_RENDER_PROCESSES.pop(job_id, None)

            if proc.returncode != 0:
                # Check if cancellation was requested or already cancelled
                job_check = self.jobs.get_job(job_id)
                if job_check.status in {"cancelling", "cancelled"}:
                    if job_check.status == "cancelling":
                        try:
                            self.jobs.transition_job_state(job_id, "cancelled", stage="cancelled")
                        except Exception:
                            pass
                    return {"status": "cancelled"}
                err_msg = "\n".join(output_lines[-20:]) if output_lines else "FFmpeg process failed"
                raise ProcessingError(f"Render failed (code {proc.returncode}): {err_msg}")

            if not temp_rendered_mp4.exists() or temp_rendered_mp4.stat().st_size == 0:
                raise ProcessingError("FFmpeg reported success but output file was not created or is empty.")

            # Stage 13: Validate output
            self.jobs.transition_job_state(job_id, "running", progress_pct=94.0, stage="validating_output")
            val_details = self.validator.validate_export(
                file_path=temp_rendered_mp4,
                expected_duration=duration,
                expected_width=target_w,
                expected_height=target_h,
                expected_video_codec=preset.video_codec,
                expected_audio_codec=preset.audio_codec if has_audio else None,
            )

            if not val_details.is_valid:
                err_summary = "; ".join(val_details.errors)
                logger.error("Output validation failed for %s: %s", temp_rendered_mp4.name, err_summary)
                raise ProcessingError(f"Export validation failed: {err_summary}")

            # Stage 14 & 15: Publish completed export and persist metadata
            self.jobs.transition_job_state(job_id, "running", progress_pct=98.0, stage="publishing_export")

            final_dir = self.layout.exports / project_id
            final_dir.mkdir(parents=True, exist_ok=True)
            final_output_path = final_dir / cfg["output_filename"]

            # Overwrite protection: if file exists, add timestamp suffix
            if final_output_path.exists():
                stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S")
                final_output_path = final_dir / f"{final_output_path.stem}_{stamp}.mp4"

            shutil.move(str(temp_rendered_mp4), str(final_output_path))
            final_size = final_output_path.stat().st_size

            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            with sqlite_session(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE exports
                    SET status = 'completed',
                        output_path = ?,
                        output_filename = ?,
                        file_size_bytes = ?,
                        duration_seconds = ?,
                        target_width = ?,
                        target_height = ?,
                        validation_status = 'valid',
                        validation_details_json = ?,
                        error_message = NULL,
                        completed_at = ?
                    WHERE id = ?
                    """,
                    (
                        str(final_output_path),
                        final_output_path.name,
                        final_size,
                        val_details.duration,
                        val_details.width,
                        val_details.height,
                        json.dumps(val_details.model_dump()),
                        now_iso,
                        export_id,
                    ),
                )

            self.jobs.transition_job_state(
                job_id,
                "completed",
                progress_pct=100.0,
                stage="completed",
                result_metadata={
                    "export_id": export_id,
                    "output_path": str(final_output_path),
                    "file_size_bytes": final_size,
                    "duration": val_details.duration,
                    "width": val_details.width,
                    "height": val_details.height,
                },
            )

            logger.info("Export completed successfully: %s (%dx%d, %d bytes)", final_output_path.name, val_details.width, val_details.height, final_size)
            return {
                "export_id": export_id,
                "job_id": job_id,
                "output_path": str(final_output_path),
                "duration": val_details.duration,
                "width": val_details.width,
                "height": val_details.height,
                "file_size_bytes": final_size,
                "status": "completed",
            }

        except Exception as exc:
            logger.error("Export render job %s failed: %s", job_id, exc)
            job_cur = None
            try:
                job_cur = self.jobs.get_job(job_id)
            except Exception:
                pass
            is_cancel = (job_cur and job_cur.status in {"cancelling", "cancelled"}) or "cancelling" in str(exc).lower()
            status_to_set = "cancelled" if is_cancel else "failed"
            err_msg = "Cancelled by user" if is_cancel else str(exc)
            with sqlite_session(self.db_path) as conn:
                conn.execute(
                    "UPDATE exports SET status = ?, error_message = ?, completed_at = datetime('now') WHERE id = ?",
                    (status_to_set, err_msg, export_id),
                )
            if is_cancel:
                try:
                    self.jobs.transition_job_state(job_id, "cancelled", stage="cancelled")
                except Exception:
                    pass
                return {"status": "cancelled"}
            else:
                try:
                    if job_cur and job_cur.status not in {"completed", "failed", "cancelled"}:
                        self.jobs.transition_job_state(
                            job_id, "failed", error_message=str(exc), stage="failed"
                        )
                except Exception as j_exc:
                    logger.warning("Could not transition job %s to failed: %s", job_id, j_exc)
                raise
        finally:
            # Clean up scratch files
            if job_temp_dir.exists():
                shutil.rmtree(job_temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Helper: Resolve Keyframes
    # -------------------------------------------------------------------------

    def _check_media_has_audio(self, media_path: Path) -> bool:
        """Check if source media container actually contains an audio stream."""
        cmd = [
            self.settings.ffprobe_path or "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "csv=p=0",
            str(media_path),
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            return bool(res.stdout.strip())
        except Exception:
            return False

    def _resolve_keyframes(
        self,
        conn: sqlite3.Connection,
        project_id: str,
        media_asset_id: str,
        candidate_id: str,
        plan_id: Optional[str],
        revision_id: Optional[str],
        target_aspect: str,
        start_time: float,
        end_time: float,
        source_w: int,
        source_h: int,
        clip_edit: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
    ) -> List[CropKeyframe]:
        """Load keyframes from specified revision or plan, or compute fallback centered/manual keyframes."""
        keyframes: List[CropKeyframe] = []

        if job_id:
            self.jobs.record_heartbeat(job_id)

        # If specific revision ID requested
        if revision_id:
            rev_row = conn.execute(
                "SELECT effective_keyframes_json FROM reframing_revisions WHERE id = ?",
                (revision_id,),
            ).fetchone()
            if rev_row and rev_row["effective_keyframes_json"]:
                raw = json.loads(rev_row["effective_keyframes_json"])
                for item in raw:
                    keyframes.append(CropKeyframe(**item))
                if keyframes:
                    return keyframes

        # If plan ID or candidate plan exists
        plan_query = (
            "SELECT * FROM reframing_plans WHERE id = ?"
            if plan_id
            else "SELECT * FROM reframing_plans WHERE candidate_id = ? AND target_aspect_ratio = ? ORDER BY created_at DESC LIMIT 1"
        )
        plan_params = (plan_id,) if plan_id else (candidate_id, target_aspect)
        plan_row = conn.execute(plan_query, plan_params).fetchone()

        if plan_row and plan_row["keyframes_json"]:
            raw = json.loads(plan_row["keyframes_json"])
            for item in raw:
                keyframes.append(CropKeyframe(**item))
            if keyframes:
                return keyframes

        # If manual framing mode was configured in clip_edit
        from app.services.framing_engine import FramingEngine
        engine = FramingEngine(target_aspect_ratio=target_aspect)
        cw, ch = engine.calculate_crop_dimensions(source_w, source_h)

        # If framing mode is manual in clip_edit, compute manual crop keyframes
        if clip_edit and clip_edit.get("framing_mode") == "manual":
            zoom = max(0.5, min(3.0, float(clip_edit.get("manual_crop_zoom") or 1.0)))
            if zoom != 1.0:
                cw = int(cw / zoom)
                ch = int(ch / zoom)
                cw = min(source_w, max(64, (cw // 2) * 2))
                ch = min(source_h, max(64, (ch // 2) * 2))

            crop_x_pct = float(clip_edit.get("manual_crop_x_pct", 50.0)) / 100.0
            crop_y_pct = float(clip_edit.get("manual_crop_y_pct", 50.0)) / 100.0
            cx = int(round(crop_x_pct * max(0, source_w - cw)))
            cy = int(round(crop_y_pct * max(0, source_h - ch)))
            cx = (max(0, min(source_w - cw, cx)) // 2) * 2
            cy = (max(0, min(source_h - ch, cy)) // 2) * 2
        else:
            # Dynamic subject tracking via ReframingService
            try:
                desired_strategy = "auto"
                pinned_sub = None
                if clip_edit:
                    desired_strategy = clip_edit.get("framing_mode") or "auto"
                    pinned_sub = clip_edit.get("tracked_subject_id")

                if job_id:
                    self.jobs.record_heartbeat(job_id)
                new_plan = self.reframing_service.analyze_and_create_plan(
                    project_id=project_id,
                    media_asset_id=media_asset_id,
                    candidate_id=candidate_id,
                    target_aspect_ratio=target_aspect,
                    framing_strategy=desired_strategy,
                    start_time=start_time,
                    end_time=end_time,
                    pinned_subject_id=pinned_sub,
                )
                if job_id:
                    self.jobs.record_heartbeat(job_id)
                if new_plan and new_plan.keyframes:
                    return new_plan.keyframes
            except Exception as plan_exc:
                logger.info("Dynamic reframing plan generation bypassed (%s); applying centered keyframes", plan_exc)

            cx = (max(0, (source_w - cw) // 2) // 2) * 2
            cy = (max(0, (source_h - ch) // 2) // 2) * 2

        steps = max(3, int((end_time - start_time) * 4))
        dt = (end_time - start_time) / steps
        for i in range(steps + 1):
            t = start_time + (i * dt)
            keyframes.append(
                CropKeyframe(
                    timestamp=round(t, 3),
                    crop_x=cx,
                    crop_y=cy,
                    crop_w=cw,
                    crop_h=ch,
                )
            )

        return keyframes

    def _row_to_export_record(self, row: sqlite3.Row) -> ExportRecord:
        return ExportRecord(
            id=row["id"],
            project_id=row["project_id"],
            candidate_id=row["candidate_id"],
            media_asset_id=row["media_asset_id"],
            reframing_plan_id=row["reframing_plan_id"],
            framing_revision_id=row["framing_revision_id"],
            render_job_id=row["render_job_id"],
            title=row["title"],
            export_preset=row["export_preset"],
            target_aspect_ratio=row["target_aspect_ratio"],
            target_width=row["target_width"],
            target_height=row["target_height"],
            video_codec=row["video_codec"],
            audio_codec=row["audio_codec"],
            pixel_fmt=row["pixel_fmt"],
            fps=row["fps"],
            crf=row["crf"],
            video_bitrate=row["video_bitrate"],
            audio_bitrate=row["audio_bitrate"],
            caption_config=json.loads(row["caption_config_json"] or "{}"),
            audio_config=json.loads(row["audio_config_json"] or "{}"),
            output_path=row["output_path"],
            output_filename=row["output_filename"],
            file_size_bytes=row["file_size_bytes"],
            duration_seconds=row["duration_seconds"],
            status=row["status"],
            validation_status=row["validation_status"],
            validation_details=json.loads(row["validation_details_json"] or "{}"),
            error_message=row["error_message"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )
