"""Advanced Substation Alpha (.ass) subtitle and dynamic caption generation engine."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.export import CaptionConfig

logger = logging.getLogger("zezedit.captions")


def hex_to_ass_color(hex_str: str, alpha: int = 0) -> str:
    """Convert #RRGGBB or #RGB to ASS &HAABBGGRR color format."""
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6:
        # Fallback to white if invalid
        return f"&H{alpha:02X}FFFFFF"

    rr = clean[0:2].upper()
    gg = clean[2:4].upper()
    bb = clean[4:6].upper()
    return f"&H{alpha:02X}{bb}{gg}{rr}"


def format_ass_timestamp(seconds: float) -> str:
    """Convert seconds to ASS timestamp format: H:MM:SS.cs (centiseconds)."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


class CaptionEngine:
    """Compiles transcript segments and word timestamps into styled .ass subtitle files."""

    def __init__(self, config: Optional[CaptionConfig] = None) -> None:
        self.config = config or CaptionConfig()

    def generate_ass_file(
        self,
        transcript_segments: List[Dict[str, Any]],
        clip_start_time: float,
        clip_end_time: float,
        output_file_path: Path,
        canvas_width: int = 1080,
        canvas_height: int = 1920,
    ) -> Optional[Path]:
        """Generate a valid ASS subtitle file for the specified clip window.

        Returns output_file_path if captions are enabled and generated, or None if mode is 'none'.
        """
        if self.config.mode == "none":
            return None

        # Filter segments that intersect the clip interval
        active_segments = [
            s for s in transcript_segments
            if s.get("end_time", 0.0) > clip_start_time and s.get("start_time", 0.0) < clip_end_time
        ]

        if not active_segments:
            logger.info("No transcript segments found within interval [%.2f, %.2f]", clip_start_time, clip_end_time)
            return None

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Build styles
        primary_ass = hex_to_ass_color(self.config.text_color, alpha=0)
        highlight_ass = hex_to_ass_color(self.config.highlight_color, alpha=0)
        outline_ass = hex_to_ass_color(self.config.outline_color, alpha=0)
        back_ass = hex_to_ass_color("#000000", alpha=120)  # Subtle shadow/box

        bold_val = -1 if self.config.bold else 0

        # Scale font size appropriately if canvas is not 1080x1920
        scale_factor = canvas_height / 1920.0
        effective_font_size = max(14, int(round(self.config.font_size * scale_factor)))
        effective_outline = round(self.config.outline_width * scale_factor, 1)
        effective_shadow = round(self.config.shadow_depth * scale_factor, 1)
        effective_margin_v = max(20, int(round(self.config.margin_v * scale_factor)))

        header = f"""[Script Info]
Title: ZezEdit Generated Subtitles
ScriptType: v4.00+
PlayResX: {canvas_width}
PlayResY: {canvas_height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.config.font_family},{effective_font_size},{primary_ass},{highlight_ass},{outline_ass},{back_ass},{bold_val},0,0,0,100,100,0,0,1,{effective_outline},{effective_shadow},{self.config.alignment},40,40,{effective_margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events: List[str] = []

        if self.config.mode == "word_highlight":
            events = self._build_word_highlight_events(
                active_segments, clip_start_time, clip_end_time, primary_ass, highlight_ass
            )
        elif self.config.mode == "phrase":
            events = self._build_phrase_events(active_segments, clip_start_time, clip_end_time)
        elif self.config.mode == "sentence":
            events = self._build_sentence_events(active_segments, clip_start_time, clip_end_time)
        else:  # 'standard'
            events = self._build_standard_events(active_segments, clip_start_time, clip_end_time)

        if not events:
            logger.info("No caption events generated for interval [%.2f, %.2f]", clip_start_time, clip_end_time)
            return None

        content = header + "\n".join(events) + "\n"
        output_file_path.write_text(content, encoding="utf-8")
        logger.info("Generated ASS captions (%d events) at %s", len(events), output_file_path.name)
        return output_file_path

    def _build_word_highlight_events(
        self,
        segments: List[Dict[str, Any]],
        clip_start: float,
        clip_end: float,
        text_color_ass: str,
        highlight_color_ass: str,
    ) -> List[str]:
        """Group words into short phrases and highlight each word as it is spoken."""
        events: List[str] = []

        # Collect all words in the clip interval
        all_words: List[Dict[str, Any]] = []
        for s in segments:
            words = s.get("words", [])
            if not words and s.get("words_json"):
                import json
                try:
                    words = json.loads(s["words_json"])
                except Exception:
                    words = []

            if words:
                for w in words:
                    w_start = float(w.get("start", 0.0))
                    w_end = float(w.get("end", 0.0))
                    if w_end > clip_start and w_start < clip_end:
                        all_words.append({
                            "word": w.get("word", "").strip(),
                            "start": w_start,
                            "end": w_end,
                        })
            else:
                # Fallback to segment-level timing if no word timestamps exist
                seg_text = s.get("text", "").strip()
                if seg_text:
                    s_words = seg_text.split()
                    seg_st = float(s.get("start_time", 0.0))
                    seg_et = float(s.get("end_time", seg_st + 1.0))
                    dt_per_word = max(0.1, (seg_et - seg_st) / max(1, len(s_words)))
                    for idx, sw in enumerate(s_words):
                        w_start = seg_st + (idx * dt_per_word)
                        w_end = min(seg_et, w_start + dt_per_word)
                        if w_end > clip_start and w_start < clip_end:
                            all_words.append({"word": sw, "start": w_start, "end": w_end})

        if not all_words:
            return self._build_sentence_events(segments, clip_start, clip_end)

        # Chunk words into small punchy phrases (up to max_words_per_line)
        chunk_size = self.config.max_words_per_line
        chunks = [all_words[i:i + chunk_size] for i in range(0, len(all_words), chunk_size)]

        for chunk in chunks:
            if not chunk:
                continue

            # Emit a sub-event for each active word in the chunk
            for active_idx, target_word in enumerate(chunk):
                w_rel_start = max(0.0, target_word["start"] - clip_start)
                w_rel_end = max(w_rel_start + 0.1, target_word["end"] - clip_start)

                start_str = format_ass_timestamp(w_rel_start)
                end_str = format_ass_timestamp(w_rel_end)

                # Build line with active word highlighted
                line_parts = []
                for idx, w in enumerate(chunk):
                    w_text = w["word"]
                    if idx == active_idx:
                        # Highlight active word
                        line_parts.append(f"{{\\c{highlight_color_ass}&}}{w_text}{{\\c{text_color_ass}&}}")
                    else:
                        line_parts.append(w_text)

                text = " ".join(line_parts)
                events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")

        return events

    def _build_phrase_events(
        self,
        segments: List[Dict[str, Any]],
        clip_start: float,
        clip_end: float,
    ) -> List[str]:
        """Group words into 3-5 word bursts without individual word color highlights."""
        events: List[str] = []
        all_words: List[Dict[str, Any]] = []

        for s in segments:
            words = s.get("words", [])
            if not words and s.get("words_json"):
                import json
                try:
                    words = json.loads(s["words_json"])
                except Exception:
                    words = []

            for w in words:
                w_start = float(w.get("start", 0.0))
                w_end = float(w.get("end", 0.0))
                if w_end > clip_start and w_start < clip_end:
                    all_words.append({
                        "word": w.get("word", "").strip(),
                        "start": w_start,
                        "end": w_end,
                    })

        if not all_words:
            return self._build_sentence_events(segments, clip_start, clip_end)

        chunk_size = self.config.max_words_per_line
        for i in range(0, len(all_words), chunk_size):
            chunk = all_words[i:i + chunk_size]
            rel_start = max(0.0, chunk[0]["start"] - clip_start)
            rel_end = max(rel_start + 0.2, chunk[-1]["end"] - clip_start)
            text = " ".join(w["word"] for w in chunk)
            events.append(
                f"Dialogue: 0,{format_ass_timestamp(rel_start)},{format_ass_timestamp(rel_end)},Default,,0,0,0,,{text}"
            )

        return events

    def _build_sentence_events(
        self,
        segments: List[Dict[str, Any]],
        clip_start: float,
        clip_end: float,
    ) -> List[str]:
        """Display full Whisper sentences or speech turns."""
        events: List[str] = []
        for s in segments:
            raw_text = s.get("text", "").strip()
            if not raw_text:
                continue

            st = max(0.0, float(s.get("start_time", 0.0)) - clip_start)
            et = max(st + 0.3, float(s.get("end_time", 0.0)) - clip_start)

            # Insert line break if sentence is very long
            words = raw_text.split()
            if len(words) > 8:
                mid = len(words) // 2
                text = " ".join(words[:mid]) + "\\N" + " ".join(words[mid:])
            else:
                text = raw_text

            events.append(
                f"Dialogue: 0,{format_ass_timestamp(st)},{format_ass_timestamp(et)},Default,,0,0,0,,{text}"
            )
        return events

    def _build_standard_events(
        self,
        segments: List[Dict[str, Any]],
        clip_start: float,
        clip_end: float,
    ) -> List[str]:
        """Traditional 1-2 line subtitle layout."""
        return self._build_sentence_events(segments, clip_start, clip_end)
