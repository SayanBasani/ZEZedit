"""Post-render output validation gate using FFprobe and test frame decoding."""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.export import ValidationDetails

logger = logging.getLogger("zezedit.output.validator")


class OutputValidator:
    """Validates rendered video files against requested duration, resolution, codecs, and decodability."""

    def __init__(
        self,
        ffprobe_path: str = "ffprobe",
        ffmpeg_path: str = "ffmpeg",
    ) -> None:
        self.ffprobe_path = shutil.which(ffprobe_path) or "ffprobe"
        self.ffmpeg_path = shutil.which(ffmpeg_path) or "ffmpeg"

    def validate_export(
        self,
        file_path: Path,
        expected_duration: float,
        expected_width: int,
        expected_height: int,
        expected_video_codec: str = "h264",
        expected_audio_codec: Optional[str] = "aac",
        duration_tolerance_seconds: float = 0.5,
    ) -> ValidationDetails:
        """Thoroughly inspect rendered video and return detailed validation result."""
        details = ValidationDetails()

        # 1. Existence and size check
        if not file_path.exists():
            details.errors.append(f"Export output file does not exist: {file_path}")
            return details

        file_size = file_path.stat().st_size
        details.file_size_bytes = file_size
        if file_size < 1024:
            details.errors.append(f"Export file size ({file_size} bytes) is suspiciously small or empty")
            return details

        # 2. Run FFprobe to inspect streams and container
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-of", "json",
            str(file_path),
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if res.returncode != 0:
                details.errors.append(f"FFprobe inspection failed: {res.stderr.strip()[:200]}")
                return details

            probe_data = json.loads(res.stdout)
        except Exception as exc:
            details.errors.append(f"Failed to parse FFprobe probe data: {exc}")
            return details

        format_info = probe_data.get("format", {})
        streams = probe_data.get("streams", [])

        # Find video stream
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        if not video_stream:
            details.errors.append("No video stream found in rendered container")
            return details

        # Parse duration
        duration_val = float(format_info.get("duration") or video_stream.get("duration") or 0.0)
        details.duration = round(duration_val, 3)

        # Parse dimensions
        details.width = int(video_stream.get("width") or 0)
        details.height = int(video_stream.get("height") or 0)
        details.video_codec = video_stream.get("codec_name", "")
        details.pixel_fmt = video_stream.get("pix_fmt", "")

        # Find audio stream
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if audio_stream:
            details.audio_codec = audio_stream.get("codec_name", "")

        # Verify resolution
        if details.width != expected_width or details.height != expected_height:
            details.errors.append(
                f"Resolution mismatch: expected {expected_width}x{expected_height}, got {details.width}x{details.height}"
            )

        # Verify duration
        if abs(details.duration - expected_duration) > duration_tolerance_seconds:
            details.errors.append(
                f"Duration mismatch: expected {expected_duration:.2f}s, got {details.duration:.2f}s (tolerance +/-{duration_tolerance_seconds}s)"
            )

        # Verify video codec
        if expected_video_codec:
            h264_aliases = {"h264", "libx264", "x264", "avc", "avc1"}
            h265_aliases = {"h265", "libx265", "x265", "hevc", "hev1"}
            exp = expected_video_codec.lower().strip()
            act = details.video_codec.lower().strip()
            is_match = (
                exp == act
                or (exp in h264_aliases and act in h264_aliases)
                or (exp in h265_aliases and act in h265_aliases)
                or exp in act
                or act in exp
            )
            if not is_match:
                details.errors.append(
                    f"Video codec mismatch: expected '{expected_video_codec}', got '{details.video_codec}'"
                )

        # Verify audio codec if expected
        if expected_audio_codec and (not details.audio_codec or expected_audio_codec.lower() not in details.audio_codec.lower()):
            details.errors.append(
                f"Audio codec mismatch: expected '{expected_audio_codec}', got '{details.audio_codec or 'none'}'"
            )

        # 3. Decode test: attempt decoding 5 frames to confirm stream integrity and decodability
        decode_cmd = [
            self.ffmpeg_path,
            "-v", "error",
            "-i", str(file_path),
            "-vframes", "5",
            "-f", "null",
            "-",
        ]
        try:
            dec_res = subprocess.run(decode_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if dec_res.returncode == 0:
                details.playable = True
            else:
                details.playable = False
                details.errors.append(f"Decode probe failed: {dec_res.stderr.strip()[:200]}")
        except Exception as exc:
            details.playable = False
            details.errors.append(f"Decode execution failed: {exc}")

        details.is_valid = len(details.errors) == 0 and details.playable
        if details.is_valid:
            logger.info("Export validation PASSED for %s (%dx%d, %.2fs)", file_path.name, details.width, details.height, details.duration)
        else:
            logger.warning("Export validation FAILED for %s: %s", file_path.name, "; ".join(details.errors))

        return details
