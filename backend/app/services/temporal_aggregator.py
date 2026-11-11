"""Temporal context aggregator unifying scenes, speech turns, transcripts, and visual observations."""

import logging
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

        return TemporalContext(
            timestamp=timestamp,
            current_scene=current_scene,
            active_segment=active_segment,
            nearby_segments=nearby_segments,
            active_speech_turn=active_speech_turn,
            nearby_visual_observations=nearby_visual_observations,
            nearest_frame=nearest_frame,
        )
