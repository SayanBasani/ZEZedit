"""Timeline Rendering Integration: Compiles multi-track timelines to FFmpeg filtergraphs using Milestone 8 Export Engine."""

from __future__ import annotations

import datetime
import json
import logging
import os
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
from app.models.export import STANDARD_EXPORT_PRESETS, ExportPreset
from app.models.timeline import ClipType, TimelineClip, TimelineRecord, TimelineRenderRequest, TrackType
from app.services.jobs import JobOrchestrator
from app.services.output_validator import OutputValidator
from app.services.timeline_service import TimelineService

logger = logging.getLogger("zezedit.timeline.renderer")

# Register active render subprocesses for timeline renders
_ACTIVE_TIMELINE_RENDERS: Dict[str, subprocess.Popen] = {}
_TL_LOCK = threading.Lock()


def _format_ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


class TimelineRenderer:
    """Translates a multi-track timeline into an FFmpeg execution graph and renders finished video."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.layout = StorageLayout.from_root(self.settings.storage_root)
        self.db_path = db_path or self.layout.db_file
        self.jobs = JobOrchestrator(self.settings, self.db_path)
        self.timeline_service = TimelineService(self.settings, self.db_path)
        self.validator = OutputValidator(
            ffprobe_path=self.settings.ffprobe_path,
            ffmpeg_path=self.settings.ffmpeg_path,
        )

    def submit_timeline_render(
        self,
        project_id: str,
        timeline_id: str,
        request: TimelineRenderRequest,
    ) -> Dict[str, Any]:
        """Validate timeline and enqueue an asynchronous rendering job."""
        timeline = self.timeline_service.get_timeline(timeline_id)
        if timeline.duration <= 0.1:
            raise ValidationError("Timeline is empty or has zero duration.")

        preset = STANDARD_EXPORT_PRESETS.get(request.preset_id)
        if not preset:
            preset = STANDARD_EXPORT_PRESETS["shorts_reels_9_16"]

        job_rec = self.jobs.create_job(
            job_type="timeline_render",
            project_id=project_id,
            input_config={
                "timeline_id": timeline_id,
                "preset_id": preset.preset_id,
                "title": request.title or f"{timeline.name} Render",
                "crf": request.crf or preset.crf,
                "include_audio": request.include_audio,
            },
        )
        job_id = job_rec.id

        worker = threading.Thread(
            target=self._execute_timeline_render,
            args=(job_id, project_id, timeline_id, preset, request),
            daemon=True,
            name=f"timeline_render_{job_id}",
        )
        worker.start()

        return {
            "job_id": job_id,
            "timeline_id": timeline_id,
            "status": "queued",
            "message": f"Timeline render enqueued using preset '{preset.name}'.",
        }

    def _execute_timeline_render(
        self,
        job_id: str,
        project_id: str,
        timeline_id: str,
        preset: ExportPreset,
        request: TimelineRenderRequest,
    ) -> None:
        """Background thread executing filtergraph compilation and FFmpeg render."""
        logger.info("Starting timeline render job %s for timeline %s", job_id, timeline_id)
        job_temp_dir = self.layout.temp / f"tl_render_{job_id}"
        job_temp_dir.mkdir(parents=True, exist_ok=True)
        temp_out = job_temp_dir / "timeline_scratch.mp4"

        try:
            self.jobs.transition_job_state(job_id, "running", progress_pct=5.0, stage="inspecting_timeline")
            timeline = self.timeline_service.get_timeline(timeline_id)

            # Identify all media assets referenced in clips
            referenced_media_ids = set()
            for tr in timeline.tracks:
                for cl in tr.clips:
                    if cl.source_media_id:
                        referenced_media_ids.add(cl.source_media_id)

            media_paths: Dict[str, Path] = {}
            with sqlite_session(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                for m_id in referenced_media_ids:
                    row = conn.execute("SELECT storage_path FROM media_assets WHERE id = ?", (m_id,)).fetchone()
                    if row and Path(row["storage_path"]).exists():
                        media_paths[m_id] = Path(row["storage_path"])

            # Build multi-input FFmpeg command
            self.jobs.transition_job_state(job_id, "running", progress_pct=15.0, stage="compiling_filtergraph")

            cmd, total_duration = self._compile_ffmpeg_command(
                timeline=timeline,
                media_paths=media_paths,
                preset=preset,
                output_path=temp_out,
                job_temp_dir=job_temp_dir,
                include_audio=request.include_audio,
            )

            # Execute FFmpeg with real-time stdout progress parsing
            self.jobs.transition_job_state(job_id, "running", progress_pct=30.0, stage="rendering_timeline")
            logger.info("Executing timeline render: %s", " ".join(cmd[:15]))

            proc = subprocess.Popen(
                cmd,
                cwd=str(job_temp_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            with _TL_LOCK:
                _ACTIVE_TIMELINE_RENDERS[job_id] = proc

            err_lines: List[str] = []
            total_us = max(1.0, total_duration) * 1_000_000.0
            for line in iter(proc.stdout.readline, ""):
                line_str = line.strip()
                err_lines.append(line_str)
                if len(err_lines) > 50:
                    err_lines.pop(0)

                if "out_time_us=" in line_str:
                    try:
                        us_val = float(line_str.split("out_time_us=")[1])
                        pct = min(92.0, max(30.0, 30.0 + (us_val / total_us) * 62.0))
                        self.jobs.update_job_progress(job_id, round(pct, 1), stage="rendering_timeline")
                    except Exception:
                        pass

            proc.wait()
            with _TL_LOCK:
                _ACTIVE_TIMELINE_RENDERS.pop(job_id, None)

            if proc.returncode != 0:
                tail = "\n".join(err_lines[-15:])
                raise ProcessingError(f"FFmpeg timeline render exited with code {proc.returncode}:\n{tail}")

            if not temp_out.exists() or temp_out.stat().st_size < 100:
                raise ProcessingError("Timeline output video was not generated or is empty.")

            # Validate output video
            self.jobs.transition_job_state(job_id, "running", progress_pct=95.0, stage="validating_output")
            val_result = self.validator.validate_export(
                file_path=temp_out,
                expected_duration=total_duration,
                expected_width=preset.target_width,
                expected_height=preset.target_height,
                expected_video_codec=preset.video_codec,
                expected_audio_codec=preset.audio_codec,
            )

            # Publish to storage/exports/{project_id}/
            export_id = f"exp_{uuid.uuid4().hex[:12]}"
            export_dir = self.layout.exports / project_id
            export_dir.mkdir(parents=True, exist_ok=True)
            final_filename = f"{timeline.name.lower().replace(' ', '_')}_{export_id}.mp4"
            final_path = export_dir / final_filename

            import shutil
            shutil.move(str(temp_out), str(final_path))

            # Record in exports table
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            with sqlite_session(self.db_path) as conn:
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
                    ) VALUES (
                        ?, ?, NULL, ?, NULL, NULL, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        '{}', '{}', ?, ?, ?, ?, 'completed', ?, ?, NULL, ?, ?
                    )
                    """,
                    (
                        export_id,
                        project_id,
                        list(referenced_media_ids)[0] if referenced_media_ids else "timeline",
                        job_id,
                        f"{timeline.name} Export",
                        preset.preset_id,
                        f"{preset.target_width}:{preset.target_height}",
                        preset.target_width,
                        preset.target_height,
                        preset.video_codec,
                        preset.audio_codec,
                        preset.pixel_fmt,
                        preset.fps,
                        request.crf or preset.crf,
                        preset.video_bitrate,
                        preset.audio_bitrate,
                        str(final_path.resolve()),
                        final_filename,
                        final_path.stat().st_size,
                        total_duration,
                        "valid" if val_result.is_valid else "invalid",
                        json.dumps(val_result.model_dump()),
                        now,
                        now,
                    ),
                )
                conn.commit()

            self.jobs.transition_job_state(
                job_id,
                "completed",
                progress_pct=100.0,
                stage="completed",
                result_metadata={
                    "export_id": export_id,
                    "output_path": str(final_path.resolve()),
                    "duration": total_duration,
                    "validation": val_result.model_dump(),
                },
            )
            logger.info("Timeline render job %s finished successfully: %s", job_id, final_path)

        except Exception as exc:
            logger.error("Timeline render job %s failed: %s", job_id, exc)
            self.jobs.transition_job_state(job_id, "failed", error_message=str(exc))
        finally:
            import shutil
            if job_temp_dir.exists():
                shutil.rmtree(str(job_temp_dir), ignore_errors=True)

    def _compile_ffmpeg_command(
        self,
        timeline: TimelineRecord,
        media_paths: Dict[str, Path],
        preset: ExportPreset,
        output_path: Path,
        job_temp_dir: Path,
        include_audio: bool,
    ) -> Tuple[List[str], float]:
        """Assemble an FFmpeg command that layers video, text overlays, and audio tracks."""
        total_duration = max(1.0, timeline.duration)
        canvas_w = preset.target_width
        canvas_h = preset.target_height
        fps = preset.fps

        # Build list of active clips
        video_clips: List[TimelineClip] = []
        text_clips: List[TimelineClip] = []
        audio_clips: List[TimelineClip] = []

        for tr in sorted(timeline.tracks, key=lambda t: t.track_order):
            if not tr.is_visible:
                continue
            for cl in tr.clips:
                if cl.clip_type == ClipType.TEXT:
                    text_clips.append(cl)
                elif cl.clip_type == ClipType.AUDIO:
                    if not tr.is_muted:
                        audio_clips.append(cl)
                elif cl.clip_type == ClipType.VIDEO:
                    video_clips.append(cl)
                    if not tr.is_muted:
                        audio_clips.append(cl)

        # Base background generator: color black canvas of duration
        cmd = [
            self.settings.ffmpeg_path or "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={canvas_w}x{canvas_h}:r={fps}:d={total_duration:.3f}",
        ]

        # Add inputs for referenced video/audio media files
        input_index_map: Dict[str, int] = {}
        for m_id, path in media_paths.items():
            input_index_map[m_id] = len(input_index_map) + 1
            cmd.extend(["-i", str(path.resolve())])

        # Filtergraph construction
        filter_chains: List[str] = []
        current_v = "[0:v]"

        # Layer video clips
        for idx, cl in enumerate(video_clips):
            if cl.source_media_id and cl.source_media_id in input_index_map:
                in_idx = input_index_map[cl.source_media_id]
                c_dur = cl.duration
                cl_tag = f"[vclip_{idx}]"
                # Scale clip to fit canvas while preserving aspect ratio, center it
                filter_chains.append(
                    f"[{in_idx}:v]trim=start={cl.source_in:.3f}:duration={c_dur:.3f},setpts=PTS-STARTPTS,"
                    f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,setsar=1{cl_tag}"
                )
                next_v = f"[v_mix_{idx}]"
                # Overlay onto timeline base at clip start
                filter_chains.append(
                    f"{current_v}{cl_tag}overlay=x=(W-w)/2:y=(H-h)/2:enable='between(t,{cl.timeline_start:.3f},{cl.timeline_end:.3f})'{next_v}"
                )
                current_v = next_v

        # Layer text overlays via ASS subtitle file (libass is rock solid on Windows)
        if text_clips:
            events = []
            for txt in text_clips:
                start_str = _format_ass_time(txt.timeline_start)
                end_str = _format_ass_time(txt.timeline_end)
                events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{txt.content_props.text}")

            ass_content = (
                f"[Script Info]\n"
                f"ScriptType: v4.00+\n"
                f"PlayResX: {canvas_w}\n"
                f"PlayResY: {canvas_h}\n\n"
                f"[V4+ Styles]\n"
                f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                f"Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,50,50,150,1\n\n"
                f"[Events]\n"
                f"Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                + "\n".join(events) + "\n"
            )
            ass_path = job_temp_dir / "overlay.ass"
            ass_path.write_text(ass_content, encoding="utf-8")
            filter_chains.append(f"{current_v}ass=filename=overlay.ass[v_ass]")
            current_v = "[v_ass]"

        # Final video output tag
        filter_chains.append(f"{current_v}format=yuv420p[v_final]")

        # Audio handling: mix or synthesize silent stereo
        has_audio = include_audio and any(cl.source_media_id in input_index_map for cl in audio_clips)
        if has_audio:
            audio_tags = []
            for idx, cl in enumerate(audio_clips):
                if cl.source_media_id and cl.source_media_id in input_index_map:
                    in_idx = input_index_map[cl.source_media_id]
                    c_dur = cl.duration
                    a_tag = f"[aclip_{idx}]"
                    vol = cl.volume
                    delay_ms = int(cl.timeline_start * 1000)
                    filter_chains.append(
                        f"[{in_idx}:a]atrim=start={cl.source_in:.3f}:duration={c_dur:.3f},asetpts=PTS-STARTPTS,"
                        f"volume={vol:.2f},adelay={delay_ms}|{delay_ms}{a_tag}"
                    )
                    audio_tags.append(a_tag)

            if audio_tags:
                filter_chains.append(
                    f"{''.join(audio_tags)}amix=inputs={len(audio_tags)}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a_final]"
                )
            else:
                has_audio = False

        if not has_audio:
            # Generate silent stereo stream
            cmd.extend(["-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000:d={total_duration:.3f}"])
            filter_chains.append(f"[{len(input_index_map) + 1}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a_final]")

        filtergraph = ";".join(filter_chains)

        cmd.extend([
            "-filter_complex", filtergraph,
            "-map", "[v_final]",
            "-map", "[a_final]",
            "-c:v", preset.video_codec,
            "-preset", "faster",
            "-crf", str(preset.crf),
            "-pix_fmt", preset.pixel_fmt,
            "-c:a", preset.audio_codec,
            "-b:a", preset.audio_bitrate,
            "-ar", "48000",
            "-ac", "2",
            "-t", f"{total_duration:.3f}",
            "-movflags", "+faststart",
            "-threads", str(self.settings.ffmpeg_threads),
            "-progress", "pipe:1",
            "-nostats",
            str(output_path.resolve()),
        ])

        return cmd, total_duration
