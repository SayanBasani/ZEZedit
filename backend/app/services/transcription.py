"""Faster-Whisper CPU transcription provider with word and segment normalization."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

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
        self._model = None

    def _get_model(self):
        if self._model is None:
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
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        word_timestamps: bool = True,
        beam_size: int = 1,
    ) -> TranscriptionResult:
        """Transcribe an audio file (preferably 16kHz mono WAV) into normalized segments."""
        if not audio_path.exists():
            raise ProcessingError(f"Audio file does not exist: {audio_path}")

        model = self._get_model()

        logger.info("Transcribing audio %s with Faster-Whisper (%s)...", audio_path.name, self.model_size)
        try:
            raw_segments, info = model.transcribe(
                str(audio_path),
                language=language,
                beam_size=beam_size,
                word_timestamps=word_timestamps,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            raw_list = list(raw_segments)
            # If VAD filter classified everything as non-speech (common with dialogue over music/rhymes),
            # retry without VAD filter to preserve real speech
            if not raw_list:
                logger.info("VAD filter yielded 0 segments for %s; retrying without VAD filter", audio_path.name)
                raw_segments, info = model.transcribe(
                    str(audio_path),
                    language=language,
                    beam_size=beam_size,
                    word_timestamps=word_timestamps,
                    vad_filter=False,
                )
                raw_list = list(raw_segments)

            normalized_segments: List[NormalizedSegment] = []
            for seg in raw_list:
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
                    # e.g. exp(logprob) or normalized score
                    import math
                    confidence = round(max(0.0, min(1.0, math.exp(seg.avg_logprob))), 3)

                normalized_segments.append(
                    NormalizedSegment(
                        start_time=round(float(seg.start), 3),
                        end_time=round(float(seg.end), 3),
                        text=seg_text,
                        language=info.language,
                        confidence=confidence,
                        words=words_data,
                    )
                )

            logger.info(
                "Transcription complete: %d segments detected (language: %s, prob: %.2f)",
                len(normalized_segments),
                info.language,
                info.language_probability,
            )

            return TranscriptionResult(
                detected_language=info.language,
                language_probability=round(float(info.language_probability), 3),
                duration_seconds=round(float(info.duration), 3) if hasattr(info, "duration") else 0.0,
                segments=normalized_segments,
            )

        except Exception as exc:
            logger.error("Whisper transcription failed: %s", exc)
            raise ProcessingError(f"Transcription failed: {exc}") from exc
