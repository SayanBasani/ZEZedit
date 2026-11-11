"""Conversational speech turn segmentation and dialogue grouping."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger("zezedit.speech_segmentation")


@dataclass
class SegmentWord:
    word: str
    start: float
    end: float
    probability: float


@dataclass
class NormalizedSegment:
    start_time: float
    end_time: float
    text: str
    language: str
    confidence: float
    words: List[Dict[str, Any]]


@dataclass
class SpeechTurn:
    start_time: float
    end_time: float
    speaker_label: str
    text: str
    segment_indices: List[int]
    turn_type: str  # 'question', 'statement', 'exclamation'


def segment_dialogue_turns(
    segments: List[NormalizedSegment],
    pause_threshold_seconds: float = 0.8,
    max_turn_duration_seconds: float = 30.0,
) -> List[SpeechTurn]:
    """Group consecutive transcript segments into coherent speech turns.
    
    A new turn is created when:
    1. A pause > pause_threshold_seconds occurs between segments.
    2. A segment ends with strong sentence-ending punctuation followed by a pause.
    3. The turn exceeds max_turn_duration_seconds.
    """
    if not segments:
        return []

    turns: List[SpeechTurn] = []
    current_segment_indices: List[int] = []
    current_texts: List[str] = []
    turn_start = segments[0].start_time
    turn_end = segments[0].end_time
    speaker_counter = 1

    for idx, seg in enumerate(segments):
        text = seg.text.strip()
        if not text:
            continue

        if not current_segment_indices:
            current_segment_indices = [idx]
            current_texts = [text]
            turn_start = seg.start_time
            turn_end = seg.end_time
            continue

        pause = seg.start_time - turn_end
        turn_duration = seg.end_time - turn_start

        # Check turn break conditions
        should_break = False
        if pause >= pause_threshold_seconds:
            should_break = True
        elif turn_duration >= max_turn_duration_seconds:
            should_break = True
        elif current_texts[-1].endswith(("?", "!", ".")) and pause >= (pause_threshold_seconds * 0.6):
            should_break = True

        if should_break:
            # Finalize previous turn
            combined_text = " ".join(current_texts).strip()
            turn_type = "statement"
            if combined_text.endswith("?"):
                turn_type = "question"
            elif combined_text.endswith("!"):
                turn_type = "exclamation"

            turns.append(
                SpeechTurn(
                    start_time=round(turn_start, 3),
                    end_time=round(turn_end, 3),
                    speaker_label=f"Speaker {speaker_counter}",
                    text=combined_text,
                    segment_indices=list(current_segment_indices),
                    turn_type=turn_type,
                )
            )

            # Alternate speaker label if pause suggests dialogue shift
            if pause >= (pause_threshold_seconds * 1.2):
                speaker_counter = 2 if speaker_counter == 1 else 1

            # Start new turn
            current_segment_indices = [idx]
            current_texts = [text]
            turn_start = seg.start_time
            turn_end = seg.end_time
        else:
            current_segment_indices.append(idx)
            current_texts.append(text)
            turn_end = seg.end_time

    # Finalize any remaining turn
    if current_segment_indices:
        combined_text = " ".join(current_texts).strip()
        turn_type = "statement"
        if combined_text.endswith("?"):
            turn_type = "question"
        elif combined_text.endswith("!"):
            turn_type = "exclamation"

        turns.append(
            SpeechTurn(
                start_time=round(turn_start, 3),
                end_time=round(turn_end, 3),
                speaker_label=f"Speaker {speaker_counter}",
                text=combined_text,
                segment_indices=list(current_segment_indices),
                turn_type=turn_type,
            )
        )

    logger.info("Grouped %d segments into %d speech turn(s)", len(segments), len(turns))
    return turns
