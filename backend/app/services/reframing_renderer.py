"""Authoritative FFmpeg renderer for dynamic portrait reframing with exact keyframe parity."""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.models.reframing import CropKeyframe

logger = logging.getLogger("zezedit.reframing.renderer")


def _simplify_keyframes(keyframes: List[CropKeyframe], min_delta_x: float = 3.0) -> List[CropKeyframe]:
    """Reduce keyframe count by pruning redundant collinear frames while keeping boundaries and scene cuts."""
    if len(keyframes) <= 3:
        return keyframes

    simplified: List[CropKeyframe] = [keyframes[0]]

    for i in range(1, len(keyframes) - 1):
        prev_k = simplified[-1]
        cur_k = keyframes[i]
        next_k = keyframes[i + 1]

        # Always keep scene cut boundaries or manual overrides
        if cur_k.is_scene_boundary or cur_k.is_manual_override or next_k.is_scene_boundary:
            simplified.append(cur_k)
            continue

        # Keep if significant movement occurs
        if abs(cur_k.crop_x - prev_k.crop_x) >= min_delta_x or abs(cur_k.crop_y - prev_k.crop_y) >= min_delta_x:
            simplified.append(cur_k)

    simplified.append(keyframes[-1])
    return simplified


def build_crop_filter_expression(
    keyframes: List[CropKeyframe],
    start_time: float,
    end_time: float,
    source_w: int,
    source_h: int,
    output_w: int = 1080,
    output_h: int = 1920,
) -> Tuple[str, int, int]:
    """Generate dynamic FFmpeg filtergraph string using piecewise-linear interpolation.

    Uses `t` (relative timestamp in clip) to evaluate smooth camera pan.
    """
    if not keyframes:
        # Fallback centered portrait crop
        cw = int(source_h * (output_w / output_h) // 2) * 2
        ch = source_h
        cx = max(0, (source_w - cw) // 2)
        cy = 0
        return f"crop={cw}:{ch}:{cx}:{cy},scale={output_w}:{output_h}", cw, ch

    simplified = _simplify_keyframes(keyframes)

    # Use first keyframe's dimensions as reference crop window
    ref_cw = simplified[0].crop_w
    ref_ch = simplified[0].crop_h

    if len(simplified) == 1:
        # Stationary crop
        k = simplified[0]
        return f"crop={ref_cw}:{ref_ch}:{k.crop_x}:{k.crop_y},scale={output_w}:{output_h}", ref_cw, ref_ch

    # Build nested if expressions for time-dependent X and Y coordinates:
    # relative_t = t - start_time
    expr_x_parts = []
    expr_y_parts = []

    # Work in relative timestamps inside the trimmed clip
    rel_keyframes = [
        (round(k.timestamp - start_time, 3), k.crop_x, k.crop_y, k.is_scene_boundary)
        for k in simplified
    ]

    # Construct backwards nested if(lt(t, t_next), linear_interp, ...)
    # Base fallback is the last keyframe position
    last_t, last_x, last_y, _ = rel_keyframes[-1]
    curr_expr_x = f"{last_x}"
    curr_expr_y = f"{last_y}"

    for i in range(len(rel_keyframes) - 2, -1, -1):
        t0, x0, y0, _ = rel_keyframes[i]
        t1, x1, y1, is_cut = rel_keyframes[i + 1]

        dt = max(0.001, t1 - t0)

        if is_cut:
            # Step jump across scene cut
            interp_x = f"{x0}"
            interp_y = f"{y0}"
        else:
            # Smooth linear interpolation between keyframes
            interp_x = f"({x0}+({x1}-{x0})*(t-{t0:.3f})/{dt:.3f})"
            interp_y = f"({y0}+({y1}-{y0})*(t-{t0:.3f})/{dt:.3f})"

        curr_expr_x = f"if(lt(t,{t1:.3f}),{interp_x},{curr_expr_x})"
        curr_expr_y = f"if(lt(t,{t1:.3f}),{interp_y},{curr_expr_y})"

    filter_graph = f"crop=w={ref_cw}:h={ref_ch}:x='{curr_expr_x}':y='{curr_expr_y}',scale={output_w}:{output_h}"
    return filter_graph, ref_cw, ref_ch


class ReframingRenderer:
    """Renders authoritative reframed video files with audio synchronization via FFmpeg."""

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        threads: int = 4,
    ) -> None:
        self.ffmpeg_path = shutil.which(ffmpeg_path) or "ffmpeg"
        self.threads = max(1, min(8, threads))

    def render_reframed_clip(
        self,
        source_media_path: Path,
        start_time: float,
        end_time: float,
        keyframes: List[CropKeyframe],
        output_path: Path,
        source_w: int,
        source_h: int,
        output_w: int = 1080,
        output_h: int = 1920,
    ) -> Dict[str, Any]:
        """Render the reframed vertical 9:16 clip to a real video file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = max(0.5, end_time - start_time)

        filter_graph, cw, ch = build_crop_filter_expression(
            keyframes=keyframes,
            start_time=start_time,
            end_time=end_time,
            source_w=source_w,
            source_h=source_h,
            output_w=output_w,
            output_h=output_h,
        )

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", f"{start_time:.3f}",
            "-t", f"{duration:.3f}",
            "-i", str(source_media_path),
            "-vf", filter_graph,
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ac", "2",
            "-ar", "44100",
            "-movflags", "+faststart",
            "-threads", str(self.threads),
            str(output_path),
        ]

        logger.info("Executing reframing render: %s -> %s", source_media_path.name, output_path.name)
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            logger.error("FFmpeg reframing render failed (exit=%d): %s", result.returncode, result.stderr)
            raise RuntimeError(f"FFmpeg render failed: {result.stderr[-400:] if result.stderr else 'Unknown error'}")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Reframing renderer completed but output file is empty or missing")

        file_size = output_path.stat().st_size
        return {
            "output_path": str(output_path),
            "output_width": output_w,
            "output_height": output_h,
            "duration": duration,
            "file_size_bytes": file_size,
            "crop_w": cw,
            "crop_h": ch,
            "keyframes_count": len(keyframes),
        }
