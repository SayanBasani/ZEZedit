"""Controlled, downscaled visual frame extraction for analysis."""

import concurrent.futures
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings
from app.core.errors import ProcessingError
from app.services.scene_detector import DetectedScene

logger = logging.getLogger("zezedit.frame_sampler")


@dataclass
class SampledFrame:
    timestamp: float
    frame_path: str
    scene_index: Optional[int]
    width: int
    height: int


def sample_analysis_frames(
    video_path: Path,
    output_dir: Path,
    scenes: List[DetectedScene],
    duration_seconds: float,
    max_dimension: int = 640,
    interval_seconds: float = 10.0,
    max_frames: int = 60,
) -> List[SampledFrame]:
    """Sample key visual frames across video scenes, downscaled for fast inference.
    
    Extracts frames at scene midpoints plus regular intervals for extended scenes.
    """
    settings = get_settings()
    ffmpeg_bin = settings.ffmpeg_path or "ffmpeg"

    if not video_path.exists():
        raise ProcessingError(f"Video file does not exist: {video_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine target sample timestamps
    timestamps_with_scene: List[tuple[float, Optional[int]]] = []

    for scene in scenes:
        # Scene midpoint is primary representative frame
        timestamps_with_scene.append((scene.representative_timestamp, scene.scene_index))

        # If scene is long, sample interior intervals
        scene_len = scene.end_time - scene.start_time
        if scene_len > interval_seconds * 1.5:
            step = interval_seconds
            t = scene.start_time + step
            while t < (scene.end_time - 1.0):
                timestamps_with_scene.append((round(t, 2), scene.scene_index))
                t += step

    # Sort and deduplicate timestamps that are closer than 1.5s
    timestamps_with_scene.sort(key=lambda x: x[0])
    deduped: List[tuple[float, Optional[int]]] = []
    last_t = -999.0
    for t, sc in timestamps_with_scene:
        if t - last_t >= 1.5 and 0.0 <= t <= duration_seconds:
            deduped.append((t, sc))
            last_t = t

    # Cap to max_frames to protect memory and runtime
    if len(deduped) > max_frames:
        stride = len(deduped) / max_frames
        deduped = [deduped[int(i * stride)] for i in range(max_frames)]

    # Downscale filter preserving aspect ratio: scale='if(gt(iw,ih),640,-2)':'if(gt(iw,ih),-2,640)'
    scale_filter = f"scale='if(gt(iw,ih),{max_dimension},-2)':'if(gt(iw,ih),-2,{max_dimension})'"

    def _sample_one(item: tuple[float, Optional[int]]) -> Optional[SampledFrame]:
        ts, sc_idx = item
        ts_ms = int(ts * 1000)
        frame_filename = f"frame_{ts_ms:08d}.jpg"
        target_path = output_dir / frame_filename

        # Re-use existing cached frame if valid and non-empty
        if target_path.exists() and target_path.stat().st_size > 0:
            return SampledFrame(
                timestamp=ts,
                frame_path=str(target_path),
                scene_index=sc_idx,
                width=max_dimension,
                height=int(max_dimension * 9 / 16),
            )

        cmd = [
            ffmpeg_bin,
            "-y",
            "-loglevel", "error",
            "-ss", f"{ts:.3f}",
            "-i", str(video_path),
            "-frames:v", "1",
            "-vf", scale_filter,
            "-q:v", "3",
            str(target_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=20.0)
            if target_path.exists() and target_path.stat().st_size > 0:
                return SampledFrame(
                    timestamp=ts,
                    frame_path=str(target_path),
                    scene_index=sc_idx,
                    width=max_dimension,
                    height=int(max_dimension * 9 / 16),
                )
        except subprocess.TimeoutExpired:
            logger.warning("Frame extraction timed out after 20s at %.2fs", ts)
        except Exception as exc:
            logger.warning("Failed to sample frame at %.2fs: %s", ts, exc)
        return None

    if not deduped:
        return []

    workers = min(6, len(deduped), 8)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_sample_one, deduped))

    sampled_results: List[SampledFrame] = [r for r in results if r is not None]
    sampled_results.sort(key=lambda f: f.timestamp)
    logger.info("Sampled %d frames from %s", len(sampled_results), video_path.name)
    return sampled_results
