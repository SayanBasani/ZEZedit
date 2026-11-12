"""Extracts and analyzes 16kHz mono WAV audio tracks from media assets using FFmpeg & FFprobe."""

import json
import logging
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.errors import ProcessingError

logger = logging.getLogger("zezedit.audio_extractor")

_SILENCE_START_REGEX = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END_REGEX = re.compile(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)")


@dataclass
class AudioMetadata:
    has_audio: bool = True
    sample_rate: Optional[int] = 16000
    channels: Optional[int] = 1
    codec_name: Optional[str] = "pcm_s16le"
    bit_rate: Optional[int] = None
    duration_seconds: float = 0.0
    speech_density: float = 1.0
    silence_intervals: List[Dict[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def inspect_audio_stream(input_path: Path) -> AudioMetadata:
    """Inspect input media for audio streams and properties via FFprobe."""
    settings = get_settings()
    ffprobe_bin = settings.ffprobe_path or "ffprobe"

    if not input_path.exists():
        raise ProcessingError(f"Input media file does not exist: {input_path}")

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index,codec_name,channels,sample_rate,bit_rate,duration",
        "-show_entries", "format=duration,bit_rate",
        "-of", "json",
        str(input_path),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(proc.stdout)
    except Exception as exc:
        logger.warning("FFprobe audio inspection failed for %s: %s", input_path.name, exc)
        return AudioMetadata(has_audio=False, duration_seconds=0.0, speech_density=0.0)

    streams = probe_data.get("streams", [])
    if not streams:
        # No audio stream found
        fmt = probe_data.get("format", {})
        dur = float(fmt.get("duration", 0.0))
        logger.info("Media %s contains NO audio streams.", input_path.name)
        return AudioMetadata(
            has_audio=False,
            sample_rate=None,
            channels=None,
            codec_name=None,
            bit_rate=None,
            duration_seconds=dur,
            speech_density=0.0,
            silence_intervals=[{"start": 0.0, "end": dur, "duration": dur}] if dur > 0 else [],
        )

    # Use first audio stream
    st = streams[0]
    fmt = probe_data.get("format", {})
    dur = float(st.get("duration") or fmt.get("duration") or 0.0)
    sr = int(st["sample_rate"]) if "sample_rate" in st and str(st["sample_rate"]).isdigit() else None
    ch = int(st["channels"]) if "channels" in st else None
    br = int(st.get("bit_rate") or fmt.get("bit_rate") or 0) or None

    return AudioMetadata(
        has_audio=True,
        sample_rate=sr,
        channels=ch,
        codec_name=st.get("codec_name"),
        bit_rate=br,
        duration_seconds=dur,
        speech_density=1.0,
    )


def detect_audio_silence(
    audio_path: Path,
    duration_seconds: float,
    noise_db: float = -30.0,
    min_silence_duration: float = 0.5,
) -> Tuple[List[Dict[str, float]], float]:
    """Detect silence intervals using FFmpeg's silencedetect audio filter.
    
    Returns (silence_intervals, speech_density_ratio).
    """
    settings = get_settings()
    ffmpeg_bin = settings.ffmpeg_path or "ffmpeg"

    if not audio_path.exists():
        return [], 1.0

    cmd = [
        ffmpeg_bin,
        "-y",
        "-nostats",
        "-i", str(audio_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_duration}",
        "-f", "null",
        "-",
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as exc:
        logger.warning("Silence detection run failed: %s", exc)
        return [], 1.0

    intervals: List[Dict[str, float]] = []
    current_start: Optional[float] = None

    for line in proc.stderr.splitlines():
        if "silence_start:" in line:
            m = _SILENCE_START_REGEX.search(line)
            if m:
                try:
                    current_start = float(m.group(1))
                except ValueError:
                    pass
        elif "silence_end:" in line:
            m = _SILENCE_END_REGEX.search(line)
            if m:
                try:
                    s_end = float(m.group(1))
                    s_dur = float(m.group(2))
                    s_start = current_start if current_start is not None else max(0.0, s_end - s_dur)
                    intervals.append({
                        "start": round(s_start, 3),
                        "end": round(s_end, 3),
                        "duration": round(s_dur, 3),
                    })
                    current_start = None
                except ValueError:
                    pass

    # If stream ended during silence
    if current_start is not None and duration_seconds > current_start:
        s_dur = duration_seconds - current_start
        intervals.append({
            "start": round(current_start, 3),
            "end": round(duration_seconds, 3),
            "duration": round(s_dur, 3),
        })

    total_silence = sum(i["duration"] for i in intervals)
    total_dur = max(duration_seconds, 0.001)
    speech_density = round(max(0.0, min(1.0, (total_dur - total_silence) / total_dur)), 3)

    return intervals, speech_density


def extract_audio_16k_mono(
    input_path: Path,
    output_path: Path,
    max_duration_seconds: Optional[float] = None,
    return_metadata: bool = False,
) -> Any:
    """Extract audio track as 16kHz mono 16-bit PCM WAV.
    
    16kHz mono 16-bit PCM is the required format for Whisper speech recognition.
    If the source file has no audio stream, synthesizes a silent 16kHz mono track
    so Whisper and subsequent analysis stages execute without error.
    
    If return_metadata is True, returns (output_path, AudioMetadata).
    Otherwise returns output_path for backward compatibility.
    """
    settings = get_settings()
    ffmpeg_bin = settings.ffmpeg_path or "ffmpeg"

    if not input_path.exists():
        raise ProcessingError(f"Input media file does not exist: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Inspect source media audio stream
    meta = inspect_audio_stream(input_path)

    effective_duration = meta.duration_seconds
    if max_duration_seconds is not None and max_duration_seconds > 0:
        effective_duration = min(effective_duration or max_duration_seconds, max_duration_seconds)

    if not meta.has_audio:
        # Synthesize silent 16kHz mono PCM WAV
        logger.info("Synthesizing silent 16kHz mono WAV for audio-less media: %s", input_path.name)
        synth_dur = max(effective_duration, 1.0)
        cmd = [
            ffmpeg_bin,
            "-y",
            "-loglevel", "error",
            "-f", "lavfi",
            "-i", "anullsrc=r=16000:cl=mono",
            "-t", str(synth_dur),
            "-c:a", "pcm_s16le",
            str(output_path),
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            raise ProcessingError(f"Failed to synthesize silent audio track: {exc.stderr}") from exc
        meta.speech_density = 0.0
        return (output_path, meta) if return_metadata else output_path

    # 2. Extract primary audio track
    cmd = [
        ffmpeg_bin,
        "-y",
        "-loglevel", "error",
        "-i", str(input_path),
        "-map", "0:a:0",
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
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        logger.error("FFmpeg audio extraction failed: %s", stderr)
        raise ProcessingError(f"Audio extraction failed: {stderr.strip()[:200]}") from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ProcessingError("FFmpeg produced an empty or missing audio file.")

    # 3. Detect silence and compute speech density
    dur = effective_duration if effective_duration > 0 else 1.0
    silence_intervals, speech_density = detect_audio_silence(output_path, duration_seconds=dur)
    meta.silence_intervals = silence_intervals
    meta.speech_density = speech_density

    return (output_path, meta) if return_metadata else output_path


def extract_audio_chunk(
    input_path: Path,
    output_path: Path,
    start_time: float,
    duration_seconds: float,
) -> Path:
    """Extract a bounded 16kHz mono audio chunk at [start_time, start_time + duration_seconds].
    
    Uses input seeking (-ss before -i) to avoid reading unnecessary frames or audio into memory.
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
        "-ss", f"{max(0.0, start_time):.3f}",
        "-t", f"{max(0.1, duration_seconds):.3f}",
        "-i", str(input_path),
        "-map", "0:a:0?",
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60.0)
    except subprocess.TimeoutExpired:
        raise ProcessingError(f"Audio chunk extraction timed out at {start_time:.1f}s")
    except subprocess.CalledProcessError as exc:
        raise ProcessingError(f"Audio chunk extraction failed: {exc.stderr}") from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        # Fallback to silent chunk if no audio stream
        cmd_synth = [
            ffmpeg_bin,
            "-y",
            "-loglevel", "error",
            "-f", "lavfi",
            "-i", "anullsrc=r=16000:cl=mono",
            "-t", f"{duration_seconds:.3f}",
            "-c:a", "pcm_s16le",
            str(output_path),
        ]
        subprocess.run(cmd_synth, capture_output=True, text=True, check=True, timeout=15.0)

    return output_path
