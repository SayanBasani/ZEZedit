"""Temporal context aggregator unifying scenes, speech turns, transcripts, and visual observations."""

import json
import logging
from pathlib import Path
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.db.connection import sqlite_session

logger = logging.getLogger("zezedit.temporal_aggregator")


@dataclass
class TemporalContext:
    timestamp: float
    current_scene: Optional[Dict[str, Any]]
    active_segment: Optional[Dict[str, Any]]
    nearby_segments: List[Dict[str, Any]]
    active_speech_turn: Optional[Dict[str, Any]]
    nearby_visual_observations: List[Dict[str, Any]]
    nearest_frame: Optional[Dict[str, Any]]
    audio_state: str = "ambient"  # "speech", "silence", "ambient"
    aligned_event: Optional[Dict[str, Any]] = None


def get_temporal_context_at(
    analysis_run_id: str,
    timestamp: float,
    window_seconds: float = 15.0,
    db_path: Optional[Path] = None,
) -> TemporalContext:
    """Query unified temporal context around a specific timestamp."""
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # 1. Current or nearest scene
        scene_row = conn.execute(
            """
            SELECT * FROM video_scenes
            WHERE analysis_run_id = ? AND start_time <= ? AND end_time >= ?
            LIMIT 1
            """,
            (analysis_run_id, timestamp, timestamp),
        ).fetchone()

        if not scene_row:
            # Fallback to closest scene
            scene_row = conn.execute(
                """
                SELECT * FROM video_scenes
                WHERE analysis_run_id = ?
                ORDER BY ABS(representative_timestamp - ?) ASC
                LIMIT 1
                """,
                (analysis_run_id, timestamp),
            ).fetchone()

        current_scene = dict(scene_row) if scene_row else None

        # 2. Active segment
        seg_row = conn.execute(
            """
            SELECT * FROM transcript_segments
            WHERE analysis_run_id = ? AND start_time <= ? AND end_time >= ?
            LIMIT 1
            """,
            (analysis_run_id, timestamp, timestamp),
        ).fetchone()
        active_segment = dict(seg_row) if seg_row else None

        # 3. Nearby segments within window
        nearby_rows = conn.execute(
            """
            SELECT * FROM transcript_segments
            WHERE analysis_run_id = ? 
              AND end_time >= ? 
              AND start_time <= ?
            ORDER BY start_time ASC
            """,
            (analysis_run_id, timestamp - window_seconds, timestamp + window_seconds),
        ).fetchall()
        nearby_segments = [dict(r) for r in nearby_rows]

        # 4. Active speech turn
        turn_row = conn.execute(
            """
            SELECT * FROM speech_turns
            WHERE analysis_run_id = ? AND start_time <= ? AND end_time >= ?
            LIMIT 1
            """,
            (analysis_run_id, timestamp, timestamp),
        ).fetchone()
        active_speech_turn = dict(turn_row) if turn_row else None

        # 5. Nearby visual observations
        obs_rows = conn.execute(
            """
            SELECT * FROM visual_observations
            WHERE analysis_run_id = ? 
              AND timestamp >= ? 
              AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (analysis_run_id, timestamp - window_seconds, timestamp + window_seconds),
        ).fetchall()
        nearby_visual_observations = [dict(r) for r in obs_rows]

        # 6. Nearest sampled frame
        frame_row = conn.execute(
            """
            SELECT * FROM sampled_frames
            WHERE analysis_run_id = ?
            ORDER BY ABS(timestamp - ?) ASC
            LIMIT 1
            """,
            (analysis_run_id, timestamp),
        ).fetchone()
        nearest_frame = dict(frame_row) if frame_row else None

        # 7. Audio acoustic state (speech vs silence)
        aud_row = conn.execute(
            "SELECT silence_intervals_json FROM audio_analysis WHERE analysis_run_id = ?",
            (analysis_run_id,),
        ).fetchone()
        audio_state = "speech" if active_segment else "ambient"
        if aud_row and aud_row["silence_intervals_json"]:
            try:
                sil_intervals = json.loads(aud_row["silence_intervals_json"])
                for sil in sil_intervals:
                    if sil.get("start", 0.0) <= timestamp <= sil.get("end", 0.0):
                        audio_state = "silence"
                        break
            except Exception:
                pass

        # 8. Aligned Multimodal Event Linkage
        aligned_event = {
            "timestamp": timestamp,
            "scene_index": current_scene.get("scene_index") if current_scene else None,
            "audio_state": audio_state,
            "has_speech": active_speech_turn is not None,
            "speaker": active_speech_turn.get("speaker_label") if active_speech_turn else None,
            "speech_text": active_speech_turn.get("text") if active_speech_turn else (active_segment.get("text") if active_segment else None),
            "visual_setting": next((o.get("description") for o in nearby_visual_observations if o.get("category") == "scene_setting"), None),
            "visual_action": next((o.get("description") for o in nearby_visual_observations if o.get("category") in ("activity", "subjects")), None),
        }

        return TemporalContext(
            timestamp=timestamp,
            current_scene=current_scene,
            active_segment=active_segment,
            nearby_segments=nearby_segments,
            active_speech_turn=active_speech_turn,
            nearby_visual_observations=nearby_visual_observations,
            nearest_frame=nearest_frame,
            audio_state=audio_state,
            aligned_event=aligned_event,
        )
