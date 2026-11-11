"""Scene cut and boundary detection using FFmpeg scene filter."""

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings
from app.core.errors import ProcessingError

logger = logging.getLogger("zezedit.scene_detector")


@dataclass
class DetectedScene:
    scene_index: int
    start_time: float
    end_time: float
    representative_timestamp: float
    change_score: float = 0.0
    thumbnail_path: Optional[str] = None


_PTS_TIME_REGEX = re.compile(r"pts_time:\s*([0-9.]+)")


def detect_scenes_ffmpeg(
    video_path: Path,
    duration_seconds: float,
    threshold: float = 0.35,
    min_scene_duration: float = 1.0,
    max_duration_seconds: Optional[float] = None,
) -> List[DetectedScene]:
    """Detect visual scene cuts using FFmpeg's scene change detection filter.
    
    threshold: sensitivity between 0.0 and 1.0 (default 0.35).
    min_scene_duration: minimum seconds between cuts to avoid micro-fragmentation.
    """
    settings = get_settings()
    ffmpeg_bin = settings.ffmpeg_path or "ffmpeg"

    if not video_path.exists():
        raise ProcessingError(f"Video file does not exist: {video_path}")

    effective_duration = duration_seconds
    if max_duration_seconds is not None and 0 < max_duration_seconds < duration_seconds:
        effective_duration = max_duration_seconds

    # FFmpeg select filter with scene score threshold and showinfo
    filter_expr = f"select='gt(scene,{threshold})',showinfo"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-nostats",
        "-i", str(video_path),
    ]

    if max_duration_seconds is not None and max_duration_seconds > 0:
        cmd.extend(["-t", str(max_duration_seconds)])

    cmd.extend([
        "-vf", filter_expr,
        "-f", "null",
        "-",
    ])

    logger.info("Detecting scenes with threshold %.2f on %s", threshold, video_path.name)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as exc:
        logger.error("FFmpeg scene detection execution failed: %s", exc)
        raise ProcessingError(f"Scene detection failed: {exc}") from exc

    # Parse stderr for showinfo pts_time
    cut_timestamps: List[float] = []
    for line in proc.stderr.splitlines():
        if "Parsed_showinfo" in line:
            match = _PTS_TIME_REGEX.search(line)
            if match:
                try:
                    ts = float(match.group(1))
                    cut_timestamps.append(ts)
                except ValueError:
                    continue

    # Filter out cuts too close to each other
    filtered_cuts: List[float] = []
    last_cut = 0.0
    for ts in cut_timestamps:
        if ts > last_cut + min_scene_duration and ts < (effective_duration - 0.5):
            filtered_cuts.append(round(ts, 3))
            last_cut = ts

    # Build scene segments from boundaries: [0.0, cut1, cut2, ..., effective_duration]
    boundaries = [0.0] + filtered_cuts
    if not boundaries or boundaries[-1] < effective_duration:
        boundaries.append(round(effective_duration, 3))

    scenes: List[DetectedScene] = []
    for idx in range(len(boundaries) - 1):
        start = boundaries[idx]
        end = boundaries[idx + 1]
        if end <= start:
            continue
        midpoint = round((start + end) / 2.0, 3)
        scenes.append(
            DetectedScene(
                scene_index=idx,
                start_time=start,
                end_time=end,
                representative_timestamp=midpoint,
                change_score=threshold,
            )
        )

    # Fallback if no scenes detected: one single full-length scene
    if not scenes:
        scenes.append(
            DetectedScene(
                scene_index=0,
                start_time=0.0,
                end_time=round(effective_duration, 3),
                representative_timestamp=round(effective_duration / 2.0, 3),
                change_score=0.0,
            )
        )

    logger.info("Detected %d scene(s) across %.2fs video", len(scenes), effective_duration)
    return scenes
