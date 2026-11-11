"""Thumbnail generation service using FFmpeg."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.core.errors import AppError

logger = logging.getLogger("zezedit.thumbnail")


def generate_thumbnail(
    source_path: Path,
    output_path: Path,
    media_type: str,
    duration: Optional[float] = None,
    ffmpeg_path: str = "",
) -> Optional[Path]:
    """
    Generate a representative JPEG thumbnail using FFmpeg.
    Returns the resolved output path if generated, or None if unavailable (e.g. audio with no art).
    """
    source = Path(source_path).expanduser().resolve(strict=False)
    if not source.is_file():
        raise AppError(
            code="FILE_NOT_FOUND",
            message=f"Source file '{source}' does not exist for thumbnail generation.",
            status_code=404,
        )

    ffmpeg = ffmpeg_path.strip() or shutil.which("ffmpeg")
    if not ffmpeg:
        raise AppError(
            code="DEPENDENCY_MISSING",
            message="ffmpeg binary not found on PATH or configuration.",
            status_code=500,
        )

    output = Path(output_path).expanduser().resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)

    if media_type == "video":
        # Pick 10% into the video or 1.0s, bounded by duration
        seek_sec = 0.0
        if duration and duration > 1.0:
            seek_sec = min(1.0, duration * 0.1)

        # First attempt: fast input seek
        cmd = [
            ffmpeg,
            "-ss", str(seek_sec),
            "-i", str(source),
            "-vframes", "1",
            "-vf", "scale='min(640,iw)':-2",
            "-q:v", "3",
            str(output),
            "-y",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)

        # Fallback to output seek if input seek failed (some formats / bad keyframes fail on input seek)
        if proc.returncode != 0 or not output.exists() or output.stat().st_size == 0:
            logger.debug("Fast input seek failed for %s, trying output seek", source.name)
            cmd_fallback = [
                ffmpeg,
                "-i", str(source),
                "-ss", str(seek_sec),
                "-vframes", "1",
                "-vf", "scale='min(640,iw)':-2",
                "-q:v", "3",
                str(output),
                "-y",
            ]
            proc = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=20, check=False)

        if proc.returncode != 0 or not output.exists() or output.stat().st_size == 0:
            logger.warning("Failed to generate video thumbnail for %s: %s", source.name, proc.stderr)
            return None

        return output

    elif media_type == "image":
        cmd = [
            ffmpeg,
            "-i", str(source),
            "-vf", "scale='min(640,iw)':-2",
            "-q:v", "3",
            str(output),
            "-y",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode == 0 and output.exists() and output.stat().st_size > 0:
            return output
        logger.warning("Failed to generate image thumbnail for %s: %s", source.name, proc.stderr)
        return None

    elif media_type == "audio":
        # Extract embedded album art if present
        cmd = [
            ffmpeg,
            "-i", str(source),
            "-an",
            "-vcodec", "mjpeg",
            str(output),
            "-y",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        if proc.returncode == 0 and output.exists() and output.stat().st_size > 0:
            return output
        # Audio without art is common and normal, return None
        return None

    return None
