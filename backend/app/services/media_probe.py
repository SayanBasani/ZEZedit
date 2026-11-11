"""Media metadata inspection service using FFprobe."""

import json
import logging
import math
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.errors import AppError

logger = logging.getLogger("zezedit.media_probe")

# Standard image extensions to help classify single-frame media
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".svg"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".opus", ".wma"}


@dataclass
class MediaStreamInfo:
    index: int
    codec_type: str
    codec_name: str
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    channel_layout: Optional[str] = None
    bit_rate: Optional[int] = None
    pix_fmt: Optional[str] = None
    duration: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaProbeResult:
    media_type: str  # "video" | "audio" | "image" | "unknown"
    container_format: str
    duration_seconds: Optional[float]
    file_size_bytes: int
    bit_rate: Optional[int]
    width: Optional[int]
    height: Optional[int]
    fps: Optional[float]
    video_codec: Optional[str]
    audio_codec: Optional[str]
    sample_rate: Optional[int]
    channels: Optional[int]
    channel_layout: Optional[str]
    aspect_ratio: Optional[str]
    pix_fmt: Optional[str]
    rotation: Optional[int]
    creation_time: Optional[str]
    streams: List[Dict[str, Any]] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


def parse_fraction(val: Optional[str]) -> Optional[float]:
    """Parse FFmpeg fractions like '30000/1001' or '24/1' into a float."""
    if not val or val == "0/0" or "/" not in val:
        try:
            return float(val) if val else None
        except (ValueError, TypeError):
            return None
    try:
        num, den = val.split("/", 1)
        n, d = float(num), float(den)
        return round(n / d, 3) if d != 0 else None
    except (ValueError, ZeroDivisionError):
        return None


def calculate_aspect_ratio(width: Optional[int], height: Optional[int], dar: Optional[str] = None) -> Optional[str]:
    """Determine display aspect ratio string like '16:9', '9:16', '1:1', etc."""
    if dar and dar != "0:1" and ":" in dar:
        return dar
    if not width or not height or width <= 0 or height <= 0:
        return None

    gcd = math.gcd(width, height)
    w_ratio = width // gcd
    h_ratio = height // gcd

    # Match well-known video ratios
    known_ratios = [
        (16, 9), (9, 16), (1, 1), (4, 3), (3, 4), (21, 9), (9, 21), (4, 5)
    ]
    tolerance = 0.03
    actual_ratio = width / height
    for rw, rh in known_ratios:
        if abs(actual_ratio - (rw / rh)) < tolerance:
            return f"{rw}:{rh}"

    return f"{w_ratio}:{h_ratio}" if w_ratio <= 32 and h_ratio <= 32 else f"{width}:{height}"


def probe_media_file(file_path: Path, ffprobe_path: str = "") -> MediaProbeResult:
    """
    Execute FFprobe on a media file to inspect container, streams, and codecs.
    Never uses shell=True. Rejects missing or inaccessible files.
    """
    resolved_path = Path(file_path).expanduser().resolve(strict=False)
    if not resolved_path.is_file():
        raise AppError(
            code="FILE_NOT_FOUND",
            message=f"Media file '{resolved_path}' does not exist or is not a regular file.",
            status_code=404,
        )

    file_size = resolved_path.stat().st_size
    if file_size == 0:
        raise AppError(
            code="CORRUPT_MEDIA",
            message=f"Media file '{resolved_path.name}' is empty (0 bytes).",
            status_code=400,
        )

    ffprobe = ffprobe_path.strip() or shutil.which("ffprobe")
    if not ffprobe:
        raise AppError(
            code="DEPENDENCY_MISSING",
            message="ffprobe binary not found on PATH or configuration.",
            status_code=500,
        )

    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-show_error",
        str(resolved_path),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except subprocess.TimeoutExpired as exc:
        raise AppError(
            code="PROBE_TIMEOUT",
            message=f"FFprobe timed out while analyzing '{resolved_path.name}'.",
            status_code=500,
        ) from exc
    except OSError as exc:
        raise AppError(
            code="PROBE_FAILED",
            message=f"Failed to execute ffprobe: {exc}",
            status_code=500,
        ) from exc

    if proc.returncode != 0:
        err_msg = proc.stderr.strip() if proc.stderr else f"Exit code {proc.returncode}"
        raise AppError(
            code="CORRUPT_MEDIA",
            message=f"Unable to read media file '{resolved_path.name}': {err_msg}",
            status_code=400,
        )

    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise AppError(
            code="PROBE_PARSE_ERROR",
            message=f"Invalid JSON returned from ffprobe for '{resolved_path.name}'.",
            status_code=500,
        ) from exc

    if "error" in data:
        err_desc = data["error"].get("string", "Unknown format error")
        raise AppError(
            code="CORRUPT_MEDIA",
            message=f"FFprobe reported error for '{resolved_path.name}': {err_desc}",
            status_code=400,
        )

    format_info = data.get("format", {})
    streams_raw = data.get("streams", [])

    container_format = format_info.get("format_name", "unknown")
    duration_str = format_info.get("duration")
    duration_seconds = float(duration_str) if duration_str is not None else None
    bit_rate_str = format_info.get("bit_rate")
    bit_rate = int(bit_rate_str) if bit_rate_str is not None else None

    creation_time = format_info.get("tags", {}).get("creation_time")

    # Inspect streams
    video_stream = next((s for s in streams_raw if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams_raw if s.get("codec_type") == "audio"), None)

    # Determine media type
    ext = resolved_path.suffix.lower()
    if video_stream:
        # Check if it's a static image or a video
        nb_frames = video_stream.get("nb_frames")
        codec = video_stream.get("codec_name", "").lower()
        is_image_container = container_format.startswith("image2") or container_format in {
            "jpeg_pipe", "png_pipe", "bmp_pipe", "webp_pipe"
        }
        if (ext in IMAGE_EXTENSIONS or is_image_container or codec in {"mjpeg", "png", "webp", "bmp", "tiff"}) and (
            duration_seconds is None or duration_seconds <= 0.1 or nb_frames == "1" or is_image_container
        ):
            media_type = "image"
        else:
            media_type = "video"
    elif audio_stream:
        media_type = "audio"
    elif ext in IMAGE_EXTENSIONS:
        media_type = "image"
    elif ext in AUDIO_EXTENSIONS:
        media_type = "audio"
    else:
        media_type = "unknown"

    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    pix_fmt: Optional[str] = None
    rotation: Optional[int] = None
    aspect_ratio: Optional[str] = None

    if video_stream:
        width = video_stream.get("width")
        height = video_stream.get("height")
        video_codec = video_stream.get("codec_name")
        pix_fmt = video_stream.get("pix_fmt")

        fps_val = parse_fraction(video_stream.get("avg_frame_rate")) or parse_fraction(
            video_stream.get("r_frame_rate")
        )
        if fps_val and fps_val > 0:
            fps = fps_val

        # Rotation check (tags or side data)
        tags = video_stream.get("tags", {})
        if "rotate" in tags:
            try:
                rotation = int(tags["rotate"])
            except ValueError:
                pass
        for side in video_stream.get("side_data_list", []):
            if "rotation" in side:
                try:
                    rotation = int(side["rotation"])
                except ValueError:
                    pass

        dar = video_stream.get("display_aspect_ratio")
        aspect_ratio = calculate_aspect_ratio(width, height, dar)

    audio_codec: Optional[str] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    channel_layout: Optional[str] = None

    if audio_stream:
        audio_codec = audio_stream.get("codec_name")
        sr_val = audio_stream.get("sample_rate")
        sample_rate = int(sr_val) if sr_val is not None else None
        channels = audio_stream.get("channels")
        channel_layout = audio_stream.get("channel_layout")
        if duration_seconds is None and "duration" in audio_stream:
            try:
                duration_seconds = float(audio_stream["duration"])
            except ValueError:
                pass

    return MediaProbeResult(
        media_type=media_type,
        container_format=container_format,
        duration_seconds=duration_seconds,
        file_size_bytes=file_size,
        bit_rate=bit_rate,
        width=width,
        height=height,
        fps=fps,
        video_codec=video_codec,
        audio_codec=audio_codec,
        sample_rate=sample_rate,
        channels=channels,
        channel_layout=channel_layout,
        aspect_ratio=aspect_ratio,
        pix_fmt=pix_fmt,
        rotation=rotation,
        creation_time=creation_time,
        streams=streams_raw,
        raw_metadata=data,
    )
