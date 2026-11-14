"""Faster-Whisper CPU transcription provider with word and segment normalization."""

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Compatibility patch for PyAV 14+ with faster-whisper
try:
    import av
    if hasattr(av, "open"):
        _orig_av_open = av.open
        def _compat_av_open(*args, **kwargs):
            kwargs.pop("metadata_errors", None)
            return _orig_av_open(*args, **kwargs)
        av.open = _compat_av_open
except ImportError:
    pass

from app.core.errors import ProcessingError
from app.services.speech_segmentation import NormalizedSegment

logger = logging.getLogger("zezedit.transcription")

# Singleton process-level model cache to prevent repeated HuggingFace downloads and reloads
_WHISPER_CACHE: Dict[Tuple[str, str, str, int], Any] = {}
_CACHE_LOCK = threading.Lock()


@dataclass
class TranscriptionResult:
    detected_language: str
    language_probability: float
    duration_seconds: float
    segments: List[NormalizedSegment]


class WhisperTranscriber:
    """Wrapper around faster-whisper WhisperModel running on CPU with int8 quantization."""

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads

    def _get_model(self):
        cache_key = (self.model_size, self.device, self.compute_type, self.cpu_threads)
        with _CACHE_LOCK:
            if cache_key in _WHISPER_CACHE:
                return _WHISPER_CACHE[cache_key]

            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise ProcessingError(
                    "faster-whisper is not installed. Please install faster-whisper to enable transcription."
                ) from exc

            logger.info(
                "Loading Faster-Whisper model '%s' on %s (%s, %d threads)",
                self.model_size,
                self.device,
                self.compute_type,
                self.cpu_threads,
            )
            model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )
            _WHISPER_CACHE[cache_key] = model
            return model

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        word_timestamps: bool = True,
        beam_size: int = 1,
        vad_filter: bool = False,
        progress_callback: Optional[Callable[[float, float, str], None]] = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file (preferably 16kHz mono WAV) into normalized segments with streaming progress."""
        if not audio_path.exists():
            raise ProcessingError(f"Audio file does not exist: {audio_path}")

        model = self._get_model()

        logger.info("Transcribing audio %s with Faster-Whisper (%s, vad=%s)...", audio_path.name, self.model_size, vad_filter)
        try:
            raw_segments, info = model.transcribe(
                str(audio_path),
                language=language,
                beam_size=beam_size,
                word_timestamps=word_timestamps,
                vad_filter=vad_filter,
                vad_parameters=dict(min_silence_duration_ms=500) if vad_filter else None,
            )

            total_duration = float(info.duration) if hasattr(info, "duration") and info.duration else 0.0

            normalized_segments: List[NormalizedSegment] = []
            for seg in raw_segments:
                seg_text = seg.text.strip()
                if not seg_text:
                    continue

                words_data: List[Dict[str, Any]] = []
                if hasattr(seg, "words") and seg.words:
                    for w in seg.words:
                        words_data.append(
                            {
                                "word": w.word,
                                "start": round(float(w.start), 3),
                                "end": round(float(w.end), 3),
                                "probability": round(float(w.probability), 3) if hasattr(w, "probability") else 1.0,
                            }
                        )

                # Estimate confidence from avg_logprob if available
                confidence = 1.0
                if hasattr(seg, "avg_logprob") and seg.avg_logprob is not None:
                    import math
                    confidence = round(max(0.0, min(1.0, math.exp(seg.avg_logprob))), 3)

                norm_seg = NormalizedSegment(
                    start_time=round(float(seg.start), 3),
                    end_time=round(float(seg.end), 3),
                    text=seg_text,
                    language=info.language,
                    confidence=confidence,
                    words=words_data,
                )
                normalized_segments.append(norm_seg)

                # Dispatch streaming progress callback
                if progress_callback and total_duration > 0.0:
                    try:
                        progress_callback(float(seg.end), total_duration, seg_text)
                    except Exception as p_err:
                        logger.debug("Transcription progress callback error: %s", p_err)

            # If VAD filter was requested and yielded 0 segments, fall back cleanly without VAD
            if not normalized_segments and vad_filter:
                logger.info("VAD filter yielded 0 segments for %s; retrying without VAD filter", audio_path.name)
                raw_segments, info = model.transcribe(
                    str(audio_path),
                    language=language,
                    beam_size=beam_size,
                    word_timestamps=word_timestamps,
                    vad_filter=False,
                )
                total_duration = float(info.duration) if hasattr(info, "duration") and info.duration else total_duration
                for seg in raw_segments:
                    seg_text = seg.text.strip()
                    if not seg_text:
                        continue
                    words_data = []
                    if hasattr(seg, "words") and seg.words:
                        for w in seg.words:
                            words_data.append(
                                {
                                    "word": w.word,
                                    "start": round(float(w.start), 3),
                                    "end": round(float(w.end), 3),
                                    "probability": round(float(w.probability), 3) if hasattr(w, "probability") else 1.0,
                                }
                            )
                    confidence = 1.0
                    if hasattr(seg, "avg_logprob") and seg.avg_logprob is not None:
                        import math
                        confidence = round(max(0.0, min(1.0, math.exp(seg.avg_logprob))), 3)
                    norm_seg = NormalizedSegment(
                        start_time=round(float(seg.start), 3),
                        end_time=round(float(seg.end), 3),
                        text=seg_text,
                        language=info.language,
                        confidence=confidence,
                        words=words_data,
                    )
                    normalized_segments.append(norm_seg)
                    if progress_callback and total_duration > 0.0:
                        try:
                            progress_callback(float(seg.end), total_duration, seg_text)
                        except Exception:
                            pass

            logger.info(
                "Transcription complete: %d segments detected (language: %s, prob: %.2f)",
                len(normalized_segments),
                info.language,
                info.language_probability,
            )

            return TranscriptionResult(
                detected_language=info.language,
                language_probability=round(float(info.language_probability), 3),
                duration_seconds=round(total_duration, 3),
                segments=normalized_segments,
            )

        except Exception as exc:
            logger.error("Whisper transcription failed: %s", exc)
            raise ProcessingError(f"Transcription failed: {exc}") from exc
