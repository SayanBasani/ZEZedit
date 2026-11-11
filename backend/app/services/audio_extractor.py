"""Extracts 16kHz mono WAV audio tracks from media assets using FFmpeg."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.errors import ProcessingError

logger = logging.getLogger("zezedit.audio_extractor")


def extract_audio_16k_mono(
    input_path: Path,
    output_path: Path,
    max_duration_seconds: Optional[float] = None,
) -> Path:
    """Extract audio track as 16kHz mono 16-bit PCM WAV.
    
    16kHz mono 16-bit PCM is the required format for Whisper speech recognition.
    """
    settings = get_settings()
    ffmpeg_bin = settings.ffmpeg_path or "ffmpeg"

    if not input_path.exists():
        raise ProcessingError(f"Input media file does not exist: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_bin,
        "-y",
        "-loglevel", "error",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
    ]

    if max_duration_seconds is not None and max_duration_seconds > 0:
        cmd.extend(["-t", str(max_duration_seconds)])

    cmd.append(str(output_path))

    logger.info("Extracting 16kHz mono WAV: %s -> %s", input_path.name, output_path.name)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        logger.error("FFmpeg audio extraction failed: %s", stderr)
        raise ProcessingError(f"Audio extraction failed: {stderr.strip()[:200]}") from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ProcessingError("FFmpeg produced an empty or missing audio file.")

    return output_path
