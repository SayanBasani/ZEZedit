"""Audio filtergraph compiler and processing pipeline for video export."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.models.export import AudioConfig

logger = logging.getLogger("zezedit.audio.pipeline")


class AudioPipeline:
    """Builds FFmpeg audio filter strings and stream mappings for export."""

    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config or AudioConfig()

    def build_audio_filters(
        self,
        duration: float,
        has_source_audio: bool,
    ) -> Tuple[Optional[str], List[str]]:
        """Construct the audio filter string (-af) and any extra FFmpeg CLI arguments.

        Returns (af_filter_string, extra_ffmpeg_args).
        """
        if not has_source_audio:
            # Generate a silent stereo track synchronized with the duration
            logger.info("Source media has no audio track; synthesizing silent stereo audio track.")
            silent_args = [
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout=stereo:sample_rate={self.config.sample_rate}",
            ]
            af_filter = f"atrim=0:{duration:.3f},asetpts=PTS-STARTPTS"
            return af_filter, silent_args

        filters: List[str] = []

        # 1. Volume adjustment (if not default 1.0)
        if abs(self.config.volume - 1.0) > 0.01:
            filters.append(f"volume={self.config.volume:.2f}")

        # 2. Fade in
        if self.config.fade_in_seconds > 0.05:
            d = min(self.config.fade_in_seconds, duration / 2.0)
            filters.append(f"afade=t=in:ss=0:d={d:.2f}")

        # 3. Fade out
        if self.config.fade_out_seconds > 0.05:
            d = min(self.config.fade_out_seconds, duration / 2.0)
            st = max(0.0, duration - d)
            filters.append(f"afade=t=out:st={st:.2f}:d={d:.2f}")

        # 4. Loudness normalization (EBU R128)
        if self.config.normalize_loudness:
            filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

        # 5. Resample to standard rate
        filters.append(f"aresample={self.config.sample_rate}")

        af_str = ",".join(filters) if filters else None
        return af_str, []
