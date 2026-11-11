"""Proxy media generation service using FFmpeg."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.core.errors import AppError

logger = logging.getLogger("zezedit.proxy")

PROXY_PROFILES = {
    "360p": "scale='min(640,iw)':-2",
    "480p": "scale='min(854,iw)':-2",
    "720p": "scale='min(1280,iw)':-2",
}


def generate_proxy(
    source_path: Path,
    output_path: Path,
    profile: str = "480p",
    max_threads: int = 4,
    ffmpeg_path: str = "",
) -> Path:
    """
    Transcode source video to an optimized, lightweight H.264 proxy file.
    Ensures CPU thread confinement and fast-start MP4 atom placement for scrubbing.
    """
    source = Path(source_path).expanduser().resolve(strict=False)
    if not source.is_file():
        raise AppError(
            code="FILE_NOT_FOUND",
            message=f"Source file '{source}' does not exist for proxy generation.",
            status_code=404,
        )

    ffmpeg = ffmpeg_path.strip() or shutil.which("ffmpeg")
    if not ffmpeg:
        raise AppError(
            code="DEPENDENCY_MISSING",
            message="ffmpeg binary not found on PATH or configuration.",
            status_code=500,
        )

    scale_filter = PROXY_PROFILES.get(profile, PROXY_PROFILES["480p"])

    output = Path(output_path).expanduser().resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-i", str(source),
        "-vf", f"{scale_filter},format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "26",
        "-c:a", "aac",
        "-b:a", "128k",
        "-threads", str(max(1, min(max_threads, 16))),
        "-movflags", "+faststart",
        str(output),
        "-y",
    ]

    logger.info("Starting proxy transcode: %s -> %s (profile=%s, threads=%d)", source.name, output.name, profile, max_threads)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    except subprocess.TimeoutExpired as exc:
        if output.exists():
            output.unlink(missing_ok=True)
        raise AppError(
            code="PROXY_TIMEOUT",
            message=f"Proxy generation timed out after 10 minutes for '{source.name}'.",
            status_code=500,
        ) from exc
    except OSError as exc:
        raise AppError(
            code="PROXY_FAILED",
            message=f"Failed to launch ffmpeg for proxy generation: {exc}",
            status_code=500,
        ) from exc

    if proc.returncode != 0 or not output.exists() or output.stat().st_size == 0:
        err = proc.stderr.strip() if proc.stderr else f"Exit code {proc.returncode}"
        if output.exists():
            output.unlink(missing_ok=True)
        raise AppError(
            code="PROXY_GENERATION_FAILED",
            message=f"FFmpeg proxy transcode failed for '{source.name}': {err}",
            status_code=500,
        )

    logger.info("Proxy generated successfully: %s (%d bytes)", output.name, output.stat().st_size)
    return output
