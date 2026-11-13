"""AI Highlight Discovery, Contextual Clip Selection, Multimodal Scoring & Persistent Novelty Engine."""

import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError, ProcessingError
from app.db.connection import sqlite_session
from app.services.jobs import JobOrchestrator

logger = logging.getLogger("zezedit.highlight_discovery")

SCORING_VERSION = "2.0.0-m6"

# Supported creative directions
SUPPORTED_CREATIVE_DIRECTIONS = {
    "best_overall": "Balanced multimodal scoring across speech, visual dynamics, and context.",
    "viral_punchy": "Heavy hook weighting, rapid visual changes, high punchline density.",
    "dramatic": "Prioritizes emotional tension, vocal inflection, dramatic pauses, narrative peaks.",
    "action_motion": "Prioritizes visual motion, rapid scene dynamics, and physical activity.",
    "emotional_sad": "Prioritizes emotional speech, reflective pauses, and sustained shot continuity.",
    "engaging_dialogue": "Prioritizes multi-turn conversational exchanges, questions, and replies.",
    "humorous": "Prioritizes punchlines, snappy conversational exchanges, and expressive turns.",
}

# Creative direction component weight matrices (normalized to sum to 1.0)
DIRECTION_WEIGHTS: Dict[str, Dict[str, float]] = {
    "best_overall": {
        "hook": 0.15,
        "dialogue": 0.20,
        "emotional": 0.15,
        "action_motion": 0.15,
        "visual": 0.15,
        "narrative": 0.20,
    },
    "viral_punchy": {
        "hook": 0.30,
        "dialogue": 0.15,
        "emotional": 0.10,
        "action_motion": 0.20,
        "visual": 0.10,
        "narrative": 0.15,
    },
    "dramatic": {
        "hook": 0.10,
        "dialogue": 0.15,
        "emotional": 0.35,
        "action_motion": 0.10,
        "visual": 0.10,
        "narrative": 0.20,
    },
    "action_motion": {
        "hook": 0.15,
        "dialogue": 0.10,
        "emotional": 0.10,
        "action_motion": 0.35,
        "visual": 0.20,
        "narrative": 0.10,
    },
    "emotional_sad": {
        "hook": 0.10,
        "dialogue": 0.20,
        "emotional": 0.35,
        "action_motion": 0.05,
        "visual": 0.10,
        "narrative": 0.20,
    },
    "engaging_dialogue": {
        "hook": 0.10,
        "dialogue": 0.40,
        "emotional": 0.10,
        "action_motion": 0.05,
        "visual": 0.10,
        "narrative": 0.25,
    },
    "humorous": {
        "hook": 0.20,
        "dialogue": 0.30,
        "emotional": 0.20,
        "action_motion": 0.15,
        "visual": 0.05,
        "narrative": 0.10,
    },
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_timestamp(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


@dataclass
class QualityGateResult:
    passed: bool
    status: str  # 'recommended', 'needs_review', 'rejected'
    rejection_reasons: List[str]
    warnings: List[str]


@dataclass
class ScoreBreakdown:
    semantic_interest: float
    narrative_completeness: float
    conversation_structure: float
    visual_interest: float
    audio_evidence: float
    opening_clarity: float
    ending_completeness: float
    duration_suitability: float
    context_dependency_penalty: float
    total_score: float
    # Extended Multimodal Components (Session 4)
    hook_strength: float = 0.0
    dialogue_interest: float = 0.0
    emotional_signal: float = 0.0
    action_motion: float = 0.0
    attractiveness_estimate: float = 0.0


@dataclass
class GeneratedCandidate:
    id: str
    start_time: float
    end_time: float
    duration: float
    suggested_title: str
    description: str
    category: str
    secondary_categories: List[str]
    score_breakdown: ScoreBreakdown
    gate_result: QualityGateResult
    transcript_refs: List[str]
    scene_refs: List[str]
    visual_refs: List[Dict[str, Any]]
    audio_refs: List[Dict[str, Any]]
    ai_explanation: Dict[str, Any]
    creative_direction: str = "best_overall"
    natural_boundary_confidence: float = 1.0
    overlap_group_id: Optional[str] = None
    alternative_of_id: Optional[str] = None
    generation_run_id: Optional[str] = None


class HighlightDiscoveryEngine:
    """Discovers, bounds, scores, and deduplicates Shorts candidate moments from media analysis."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.db_path = db_path or (self.settings.storage_root / "db" / "zezedit.db")
        self.job_orchestrator = JobOrchestrator(settings=self.settings, db_path=self.db_path)

    def discover_highlights(
        self,
        project_id: str,
        media_asset_id: str,
        analysis_run_id: Optional[str] = None,
        job_id: Optional[str] = None,
        creative_direction: str = "best_overall",
        aspect_ratio: str = "9:16",
        min_duration: float = 12.0,
        max_duration: float = 60.0,
        target_clip_count: Optional[int] = None,
        use_ai_explanations: bool = True,
        is_generate_more: bool = False,
        selected_scene_ids: Optional[List[str]] = None,
        excluded_scene_ids: Optional[List[str]] = None,
        duration_preference: str = "ai_best_duration",
        novelty_mode: str = "strict",
        generation_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Main highlight discovery workflow with persistent novelty and natural boundaries."""
        if creative_direction not in SUPPORTED_CREATIVE_DIRECTIONS:
            creative_direction = "best_overall"

        # Apply duration bounds based on duration_preference
        if duration_preference == "short":
            min_duration = 15.0
            max_duration = 30.0
        elif duration_preference == "medium":
            min_duration = 30.0
            max_duration = 60.0
        elif duration_preference == "long":
            min_duration = 60.0
            max_duration = 90.0
        elif duration_preference in ("ai_best_duration", "ai_best"):
            min_duration = 15.0
            max_duration = 65.0

        generation_run_id = f"cgr_{uuid.uuid4().hex[:12]}"
        now = _now_utc()

        # Step 0: Progress telemetry - Loading analysis
        if job_id:
            try:
                self.job_orchestrator.save_checkpoint(job_id=job_id, stage="loading_analysis", progress_pct=10.0)
            except Exception as e:
                logger.warning("Failed to save job checkpoint: %s", e)

        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 1. Verify media asset
            asset = conn.execute(
                "SELECT id, project_id, duration_seconds FROM media_assets WHERE id = ? AND project_id = ?",
                (media_asset_id, project_id),
            ).fetchone()
            if not asset:
                raise NotFoundError(f"Media asset '{media_asset_id}' not found in project '{project_id}'.")
            media_duration = float(asset["duration_seconds"] or 0.0)

            # 2. Resolve analysis run
            if not analysis_run_id:
                run_row = conn.execute(
                    """
                    SELECT id FROM analysis_runs
                    WHERE media_asset_id = ? AND status = 'completed'
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (media_asset_id,),
                ).fetchone()
                if not run_row:
                    raise ProcessingError(
                        f"No completed video analysis run found for asset '{media_asset_id}'. Please analyze the video first."
                    )
                analysis_run_id = run_row["id"]
            else:
                run_row = conn.execute(
                    "SELECT id, status FROM analysis_runs WHERE id = ?",
                    (analysis_run_id,),
                ).fetchone()
                if not run_row or run_row["status"] != "completed":
                    raise ProcessingError(f"Analysis run '{analysis_run_id}' is not in completed state.")

            # 3. Load analysis data
            segments = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM transcript_segments WHERE analysis_run_id = ? ORDER BY start_time ASC",
                    (analysis_run_id,),
                ).fetchall()
            ]
            turns = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM speech_turns WHERE analysis_run_id = ? ORDER BY start_time ASC",
                    (analysis_run_id,),
                ).fetchall()
            ]
            scenes = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM video_scenes WHERE analysis_run_id = ? ORDER BY start_time ASC",
                    (analysis_run_id,),
                ).fetchall()
            ]

            # Filter scenes based on user selection / exclusion
            if selected_scene_ids:
                selected_set = set(selected_scene_ids)
                scenes = [s for s in scenes if s["id"] in selected_set]
            if excluded_scene_ids:
                excluded_set = set(excluded_scene_ids)
                scenes = [s for s in scenes if s["id"] not in excluded_set]
            observations = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM visual_observations WHERE analysis_run_id = ? ORDER BY timestamp ASC",
                    (analysis_run_id,),
                ).fetchall()
            ]
            audio_feat = conn.execute(
                "SELECT * FROM audio_analysis WHERE media_asset_id = ? ORDER BY created_at DESC LIMIT 1",
                (media_asset_id,),
            ).fetchone()
            audio_data = dict(audio_feat) if audio_feat else None

            # Load persistent novelty history for this asset
            history_rows = conn.execute(
                """
                SELECT id, start_time, end_time, duration, creative_direction, aspect_ratio, score, title
                FROM media_generated_clips_history
                WHERE media_asset_id = ?
                ORDER BY created_at ASC
                """,
                (media_asset_id,),
            ).fetchall()
            history_clips = [dict(r) for r in history_rows]

        # Resolve target clip count (AI Recommended if not explicitly passed)
        if target_clip_count is None or target_clip_count <= 0:
            base_clips = max(1, int(media_duration / 60.0))
            scene_factor = max(1, len(scenes) // 4)
            recommended = min(10, max(2, (base_clips + scene_factor) // 2))
            if len(history_clips) > 0:
                recommended = max(1, min(4, recommended - (len(history_clips) // 3)))
            target_clip_count = recommended
            logger.info("AI Recommended clip count for %s: %d", media_asset_id, target_clip_count)

        if not generation_type:
            generation_type = "generate_more" if (is_generate_more or len(history_clips) > 0) else "initial"

        logger.info(
            "Loaded analysis for asset %s: %d segments, %d turns, %d scenes, %d observations, %d history clips (mode=%s, gen_type=%s, target=%d)",
            media_asset_id,
            len(segments),
            len(turns),
            len(scenes),
            len(observations),
            len(history_clips),
            novelty_mode,
            generation_type,
            target_clip_count,
        )

        # Parse word-level timing from segments
        all_words: List[Dict[str, Any]] = []
        for s in segments:
            raw_w = s.get("words_json")
            if raw_w:
                try:
                    w_list = json.loads(raw_w)
                    if isinstance(w_list, list):
                        all_words.extend(w_list)
                except Exception:
                    pass

        # Step 1: Progress telemetry - Grouping dialogue & building moments
        if job_id:
            try:
                self.job_orchestrator.save_checkpoint(job_id=job_id, stage="grouping_dialogue", progress_pct=25.0)
            except Exception:
                pass

        # 4. Generate candidate intervals
        raw_candidates = self._generate_candidate_intervals(
            segments=segments,
            turns=turns,
            scenes=scenes,
            observations=observations,
            words=all_words,
            media_duration=media_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            creative_direction=creative_direction,
        )

        # If specific scenes were selected, prioritize candidates overlapping selected scenes
        if selected_scene_ids and scenes:
            filtered_cands = [
                c for c in raw_candidates
                if any(s["start_time"] < c["end_time"] and s["end_time"] > c["start_time"] for s in scenes)
            ]
            if filtered_cands:
                raw_candidates = filtered_cands

        total_discovered = len(raw_candidates)

        if job_id:
            try:
                self.job_orchestrator.save_checkpoint(job_id=job_id, stage="building_moment_windows", progress_pct=40.0)
            except Exception:
                pass

        # Step 2: Progress telemetry - Evaluating multimodal signals & boundary snapping
        if job_id:
            try:
                self.job_orchestrator.save_checkpoint(job_id=job_id, stage="evaluating_multimodal_signals", progress_pct=60.0)
            except Exception:
                pass

        # 5. Score and apply natural boundary snapping to each candidate
        scored_candidates: List[GeneratedCandidate] = []
        for cand in raw_candidates:
            scored = self._score_candidate(
                cand=cand,
                segments=segments,
                turns=turns,
                scenes=scenes,
                observations=observations,
                audio_data=audio_data,
                words=all_words,
                media_duration=media_duration,
                min_duration=min_duration,
                max_duration=max_duration,
                creative_direction=creative_direction,
                generation_run_id=generation_run_id,
            )
            scored_candidates.append(scored)

        if job_id:
            try:
                self.job_orchestrator.save_checkpoint(job_id=job_id, stage="refining_natural_boundaries", progress_pct=75.0)
            except Exception:
                pass

        # Filter out hard-rejected candidates (invalid boundaries)
        valid_candidates = [c for c in scored_candidates if c.gate_result.passed]
        hard_rejected_count = len(scored_candidates) - len(valid_candidates)

        if job_id:
            try:
                self.job_orchestrator.save_checkpoint(job_id=job_id, stage="scoring_candidates", progress_pct=85.0)
            except Exception:
                pass

        # 6. Multi-Layer Persistent Novelty & Non-Repetition Filter
        novelty_passed: List[GeneratedCandidate] = []
        novelty_exclusions_count = 0

        def _tokenize(text: str) -> set[str]:
            if not text:
                return set()
            return {w.lower().strip(".,!?;:\"'()[]") for w in text.split() if len(w) > 2}

        for cand in valid_candidates:
            is_novel = True
            cand_tokens = _tokenize(cand.description + " " + cand.suggested_title)

            for hist in history_clips:
                # 1. Exact or near-exact boundary match (< 2.5s tolerance at both ends)
                if abs(cand.start_time - hist["start_time"]) < 2.5 and abs(cand.end_time - hist["end_time"]) < 2.5:
                    is_novel = False
                    break

                # 2. Temporal overlap (tIoU and asymmetric overlap ratios)
                iou, cand_overlap_ratio = self._compute_temporal_overlap(
                    cand.start_time, cand.end_time, hist["start_time"], hist["end_time"]
                )
                intersection = max(0.0, min(cand.end_time, hist["end_time"]) - max(cand.start_time, hist["start_time"]))
                hist_dur = max(0.001, hist["end_time"] - hist["start_time"])
                hist_overlap_ratio = intersection / hist_dur

                iou_limit = 0.65 if novelty_mode == "relaxed" else 0.45
                ratio_limit = 0.70 if novelty_mode == "relaxed" else 0.55

                if iou >= iou_limit or cand_overlap_ratio >= ratio_limit or hist_overlap_ratio >= ratio_limit:
                    is_novel = False
                    break

                # 3. Content similarity (if words overlap substantially and temporal overlap > 30%)
                hist_tokens = _tokenize(hist.get("title", ""))
                if cand_tokens and hist_tokens and len(cand_tokens) > 3 and len(hist_tokens) > 3:
                    jaccard = len(cand_tokens & hist_tokens) / len(cand_tokens | hist_tokens)
                    if jaccard > 0.75 and cand_overlap_ratio > 0.30:
                        is_novel = False
                        break

            if is_novel:
                novelty_passed.append(cand)
            else:
                novelty_exclusions_count += 1

        if job_id:
            try:
                self.job_orchestrator.save_checkpoint(job_id=job_id, stage="filtering_novelty_and_overlaps", progress_pct=95.0)
            except Exception:
                pass

        # 7. Deduplicate & cluster overlapping alternatives among newly discovered candidates
        processed_candidates = self._deduplicate_and_group(novelty_passed)

        # 8. Sort by attractiveness score descending
        processed_candidates.sort(key=lambda c: c.score_breakdown.total_score, reverse=True)

        # Select distinct non-overlapping candidate moments up to target_clip_count
        # (Skip alternative cuts of an already selected moment so a batch never duplicates scenes)
        selected_candidates: List[GeneratedCandidate] = []
        for cand in processed_candidates:
            if cand.alternative_of_id is not None:
                continue
            selected_candidates.append(cand)
            if len(selected_candidates) >= target_clip_count:
                break

        total_selected = len(selected_candidates)
        total_rejected = hard_rejected_count + (len(novelty_passed) - total_selected)

        # 9. AI-Assisted explanations for top recommended candidates
        final_candidates = self._enrich_ai_explanations(
            candidates=selected_candidates,
            use_ai=use_ai_explanations,
            creative_direction=creative_direction,
        )

        warnings_list: List[str] = []
        is_novelty_exhausted = 0
        if total_selected < target_clip_count:
            if novelty_exclusions_count > 0:
                is_novelty_exhausted = 1
                warnings_list.append(
                    f"Returned {total_selected} candidates (requested {target_clip_count}). "
                    f"{novelty_exclusions_count} candidates were excluded by the persistent novelty ledger to avoid repeating previously generated moments. "
                    f"You can switch creative direction or relax the novelty threshold to extract more moments."
                )
            else:
                warnings_list.append(
                    f"Returned {total_selected} candidates (requested {target_clip_count}) because only {total_selected} distinct, "
                    f"naturally bounded segments met quality thresholds in this {format_timestamp(media_duration)} source video."
                )

        # 10. Persist candidates, generation run, and clip history transactionally to SQLite
        persisted = self._persist_candidates_and_history(
            candidates=final_candidates,
            project_id=project_id,
            media_asset_id=media_asset_id,
            analysis_run_id=analysis_run_id,
            job_id=job_id,
            generation_run_id=generation_run_id,
            creative_direction=creative_direction,
            aspect_ratio=aspect_ratio,
            requested_count=target_clip_count,
            min_duration=min_duration,
            max_duration=max_duration,
            candidates_discovered=total_discovered,
            candidates_selected=total_selected,
            candidates_rejected=total_rejected,
            novelty_exclusions=novelty_exclusions_count,
            warnings=warnings_list,
            generation_type=generation_type,
            reused_analysis_run_id=analysis_run_id,
            duration_preference=duration_preference,
            is_novelty_exhausted=is_novelty_exhausted,
        )

        if job_id:
            try:
                self.job_orchestrator.save_checkpoint(job_id=job_id, stage="completed", progress_pct=100.0)
            except Exception:
                pass

        logger.info(
            "Highlight discovery completed: %d selected, %d discovered, %d novelty exclusions (run %s)",
            total_selected,
            total_discovered,
            novelty_exclusions_count,
            generation_run_id,
        )
        return persisted

    def _generate_candidate_intervals(
        self,
        segments: List[Dict[str, Any]],
        turns: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
        observations: List[Dict[str, Any]],
        words: List[Dict[str, Any]],
        media_duration: float,
        min_duration: float,
        max_duration: float,
        creative_direction: str,
    ) -> List[Dict[str, Any]]:
        """Generate candidate boundaries from complete sentences, conversational exchanges, and scene cuts."""
        candidates: List[Dict[str, Any]] = []

        # Strategy A: Individual cohesive speech turns (e.g. self-contained statement or punchline)
        for turn in turns:
            dur = turn["end_time"] - turn["start_time"]
            if min_duration <= dur <= max_duration:
                candidates.append(
                    {
                        "start_time": turn["start_time"],
                        "end_time": turn["end_time"],
                        "source": "single_turn",
                        "turn_ids": [turn["id"]],
                        "text": turn["text"],
                        "primary_speaker": turn["speaker_label"],
                    }
                )

        # Strategy B: Multi-turn dialogue exchanges (2 to 6 consecutive turns)
        num_turns = len(turns)
        for i in range(num_turns):
            curr_text = [turns[i]["text"]]
            curr_turn_ids = [turns[i]["id"]]
            start_t = turns[i]["start_time"]

            for j in range(i + 1, min(i + 6, num_turns)):
                pause = turns[j]["start_time"] - turns[j - 1]["end_time"]
                if pause > 3.0:
                    # Break dialogue sequence on long pause
                    break

                curr_text.append(turns[j]["text"])
                curr_turn_ids.append(turns[j]["id"])
                end_t = turns[j]["end_time"]
                dur = end_t - start_t

                if min_duration <= dur <= max_duration:
                    candidates.append(
                        {
                            "start_time": start_t,
                            "end_time": end_t,
                            "source": "dialogue_exchange",
                            "turn_ids": list(curr_turn_ids),
                            "text": " ".join(curr_text),
                            "primary_speaker": f"Exchange ({len(curr_turn_ids)} turns)",
                        }
                    )
                elif dur > max_duration:
                    break

        # Strategy C: Sentence-level grouping from transcript segments
        if segments:
            current_sentence_words: List[Dict[str, Any]] = []
            sentence_windows: List[Tuple[float, float, str]] = []

            for seg in segments:
                text = seg.get("text", "").strip()
                s_start = seg.get("start_time", 0.0)
                s_end = seg.get("end_time", 0.0)
                sentence_windows.append((s_start, s_end, text))

            # Combine adjacent sentence windows into natural duration blocks
            n_sent = len(sentence_windows)
            for i in range(n_sent):
                accum_start = sentence_windows[i][0]
                accum_texts = [sentence_windows[i][2]]
                for j in range(i + 1, min(i + 12, n_sent)):
                    accum_end = sentence_windows[j][1]
                    dur = accum_end - accum_start
                    accum_texts.append(sentence_windows[j][2])
                    if min_duration <= dur <= max_duration:
                        candidates.append(
                            {
                                "start_time": accum_start,
                                "end_time": accum_end,
                                "source": "sentence_group",
                                "turn_ids": [],
                                "text": " ".join(accum_texts),
                                "primary_speaker": "Dialogue",
                            }
                        )
                    elif dur > max_duration:
                        break

        # Strategy D: Scene-aligned windows (for visual segments with or without speech)
        for sc in scenes:
            sc_dur = sc["end_time"] - sc["start_time"]
            if min_duration <= sc_dur <= max_duration:
                sc_turns = [
                    t for t in turns
                    if t["end_time"] >= sc["start_time"] and t["start_time"] <= sc["end_time"]
                ]
                text = " ".join(t["text"] for t in sc_turns) if sc_turns else "Visual scene segment"
                candidates.append(
                    {
                        "start_time": sc["start_time"],
                        "end_time": sc["end_time"],
                        "source": "scene_boundary",
                        "turn_ids": [t["id"] for t in sc_turns],
                        "text": text,
                        "primary_speaker": sc_turns[0]["speaker_label"] if sc_turns else "Visual",
                    }
                )

        # Strategy E: Fallback if video has no speech turns: generate uniform duration candidate windows
        if not candidates and media_duration > min_duration:
            step = min(max_duration / 2.0, 30.0)
            t = 0.0
            while t + min_duration <= media_duration:
                end_t = min(t + 30.0, media_duration)
                candidates.append(
                    {
                        "start_time": round(t, 2),
                        "end_time": round(end_t, 2),
                        "source": "time_window",
                        "turn_ids": [],
                        "text": "Media window without detected speech",
                        "primary_speaker": "Visual",
                    }
                )
                t += step

        return candidates

    def _snap_natural_boundaries(
        self,
        raw_start: float,
        raw_end: float,
        words: List[Dict[str, Any]],
        segments: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
        media_duration: float,
        min_duration: float,
        max_duration: float,
    ) -> Tuple[float, float, float, List[str]]:
        """Natural boundary algorithm: snaps to sentence start, word boundaries, and scene cuts."""
        warnings: List[str] = []
        confidence = 1.0

        snapped_start = raw_start
        snapped_end = raw_end

        # 1. Start boundary snapping: Ensure word boundary alignment & breathing lead-in
        words_in_window = [w for w in words if "start" in w and abs(w["start"] - raw_start) <= 2.0]
        if words_in_window:
            closest_word = min(words_in_window, key=lambda w: abs(w["start"] - raw_start))
            # Pad 0.15s before the word start so the consonant is not clipped
            snapped_start = max(0.0, closest_word["start"] - 0.15)
        else:
            snapped_start = max(0.0, raw_start - 0.25)

        # Check for preceding visual scene cut within 0.4s to prevent flash frames
        for sc in scenes:
            sc_start = sc["start_time"]
            if 0.0 <= (snapped_start - sc_start) <= 0.45:
                snapped_start = sc_start
                break

        # 2. End boundary snapping: Snap to sentence closure or trailing silence
        words_near_end = [w for w in words if "end" in w and abs(w["end"] - raw_end) <= 2.5]
        if words_near_end:
            punctuated_words = [
                w for w in words_near_end
                if any(w.get("word", "").endswith(p) for p in (".", "!", "?", ","))
            ]
            if punctuated_words:
                target_word = max(punctuated_words, key=lambda w: w["end"])
                snapped_end = target_word["end"] + 0.35
            else:
                target_word = max(words_near_end, key=lambda w: w["end"])
                snapped_end = target_word["end"] + 0.30
        else:
            snapped_end = min(media_duration, raw_end + 0.40)

        # Check for trailing visual scene cut within 0.5s after speech closure
        for sc in scenes:
            sc_end = sc["end_time"]
            if 0.0 <= (sc_end - snapped_end) <= 0.50:
                snapped_end = sc_end
                break

        # Check duration bounds and enforce limits safely
        dur = snapped_end - snapped_start
        if dur > max_duration:
            snapped_end = snapped_start + max_duration
            confidence = 0.75
            warnings.append(f"Trimmed candidate to maximum allowed duration ({max_duration:.1f}s)")
        elif dur < min_duration:
            # Expand slightly if boundary allows
            expansion_needed = min_duration - dur
            snapped_end = min(media_duration, snapped_end + expansion_needed)
            dur = snapped_end - snapped_start
            if dur < min_duration:
                confidence = 0.70

        snapped_start = round(max(0.0, snapped_start), 3)
        snapped_end = round(min(media_duration, snapped_end), 3)

        return snapped_start, snapped_end, confidence, warnings

    def _score_candidate(
        self,
        cand: Dict[str, Any],
        segments: List[Dict[str, Any]],
        turns: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
        observations: List[Dict[str, Any]],
        audio_data: Optional[Dict[str, Any]],
        words: List[Dict[str, Any]],
        media_duration: float,
        min_duration: float,
        max_duration: float,
        creative_direction: str,
        generation_run_id: str,
    ) -> GeneratedCandidate:
        """Context-aware boundary snapping, multimodal explainable scoring, and quality gates."""
        raw_start = cand["start_time"]
        raw_end = cand["end_time"]

        # 1. Natural Boundary Snapping
        snapped_start, snapped_end, boundary_confidence, boundary_warnings = self._snap_natural_boundaries(
            raw_start=raw_start,
            raw_end=raw_end,
            words=words,
            segments=segments,
            scenes=scenes,
            media_duration=media_duration,
            min_duration=min_duration,
            max_duration=max_duration,
        )

        duration = round(snapped_end - snapped_start, 3)

        # Extract text and evidence inside the clip
        clip_turns = [
            t for t in turns
            if t["end_time"] >= snapped_start and t["start_time"] <= snapped_end
        ]
        clip_segments = [
            s for s in segments
            if s["end_time"] >= snapped_start and s["start_time"] <= snapped_end
        ]
        clip_scenes = [
            sc for sc in scenes
            if sc["end_time"] >= snapped_start and sc["start_time"] <= snapped_end
        ]
        clip_obs = [
            o for o in observations
            if snapped_start <= o["timestamp"] <= snapped_end
        ]

        text = " ".join(t["text"] for t in clip_turns).strip()
        if not text and clip_segments:
            text = " ".join(s["text"] for s in clip_segments).strip()
        if not text:
            text = cand.get("text", "")

        lower_text = text.lower()
        words_in_text = lower_text.split()
        first_words = words_in_text[:3]

        # 2. Multimodal Component Scoring Model (Session 4)
        # Component A: Hook Strength (0 to 100 normalized)
        hook_raw = 30.0
        hook_keywords = ("why", "how", "what", "secret", "never", "always", "best", "truth", "discover", "important", "stop", "listen", "imagine", "watch", "breakthrough", "shocking")
        if any(w in " ".join(first_words) for w in hook_keywords):
            hook_raw += 35.0
        if any(t.get("turn_type") == "question" for t in clip_turns[:1]):
            hook_raw += 25.0
        if "?" in " ".join(words_in_text[:8]):
            hook_raw += 15.0
        if len(clip_scenes) >= 2:
            hook_raw += 10.0
        hook_score = max(0.0, min(100.0, hook_raw))

        # Component B: Dialogue Interest (0 to 100 normalized)
        dialogue_raw = 20.0
        speakers = {t.get("speaker_label", "speaker") for t in clip_turns}
        if len(speakers) >= 2:
            dialogue_raw += 35.0
        if len(clip_turns) >= 2:
            dialogue_raw += 20.0
        # Speech density check
        word_count = len(words_in_text)
        wps = word_count / max(1.0, duration)
        if 1.8 <= wps <= 3.8:
            dialogue_raw += 25.0
        elif wps > 0.5:
            dialogue_raw += 10.0
        dialogue_score = max(0.0, min(100.0, dialogue_raw))

        # Component C: Emotional & Dramatic Signal (0 to 100 normalized)
        emotional_raw = 25.0
        dramatic_keywords = ("incredible", "amazing", "worst", "fear", "love", "breakthrough", "danger", "secret", "never", "realized", "hate", "pain", "surprising", "crazy", "unbelievable")
        if any(w in lower_text for w in dramatic_keywords):
            emotional_raw += 35.0
        if any(t.get("turn_type") == "exclamation" for t in clip_turns) or "!" in text:
            emotional_raw += 25.0
        if any(t.get("turn_type") == "question" for t in clip_turns):
            emotional_raw += 15.0
        emotional_score = max(0.0, min(100.0, emotional_raw))

        # Component D: Action & Motion Interest (0 to 100 normalized)
        action_raw = 30.0
        if len(clip_scenes) >= 3:
            action_raw += 35.0
        elif len(clip_scenes) == 2:
            action_raw += 20.0
        if len(clip_obs) >= 2:
            action_raw += 25.0
        elif len(clip_obs) == 1:
            action_raw += 15.0
        action_score = max(0.0, min(100.0, action_raw))

        # Component E: Visual Presentation (0 to 100 normalized)
        visual_raw = 40.0
        if clip_obs:
            avg_obs_conf = sum(o.get("confidence", 0.7) for o in clip_obs) / len(clip_obs)
            visual_raw += avg_obs_conf * 40.0
        if clip_scenes:
            visual_raw += 20.0
        visual_score = max(0.0, min(100.0, visual_raw))

        # Component F: Narrative Completeness (0 to 100 normalized)
        narrative_raw = 40.0
        if text.endswith((".", "!", "?")):
            narrative_raw += 30.0
        if not any(w in first_words for w in ("and", "so", "but", "because", "or", "then")):
            narrative_raw += 20.0
        if len(clip_turns) >= 2:
            narrative_raw += 10.0
        narrative_score = max(0.0, min(100.0, narrative_raw))

        # 3. Apply Creative Direction Weight Matrix
        weights = DIRECTION_WEIGHTS.get(creative_direction, DIRECTION_WEIGHTS["best_overall"])
        weighted_total = (
            hook_score * weights["hook"]
            + dialogue_score * weights["dialogue"]
            + emotional_score * weights["emotional"]
            + action_score * weights["action_motion"]
            + visual_score * weights["visual"]
            + narrative_score * weights["narrative"]
        )

        # Context-dependency penalty
        context_penalty = 0.0
        if any(w in first_words for w in ("he", "she", "they", "this", "that")) and len(clip_turns) <= 1:
            context_penalty = 5.0
            weighted_total = max(0.0, weighted_total - context_penalty)

        total_score = round(max(0.0, min(100.0, weighted_total)), 1)

        # Backward-compatible ScoreBreakdown fields (maps to 0-20 or 0-10 scale as expected by tests)
        breakdown = ScoreBreakdown(
            semantic_interest=round(hook_score * 0.20, 1),
            narrative_completeness=round(narrative_score * 0.20, 1),
            conversation_structure=round(dialogue_score * 0.15, 1),
            visual_interest=round(visual_score * 0.15, 1),
            audio_evidence=round(dialogue_score * 0.10, 1),
            opening_clarity=round(min(10.0, narrative_score * 0.10), 1),
            ending_completeness=round(min(10.0, 10.0 if text.endswith((".", "!", "?")) else 6.0), 1),
            duration_suitability=10.0 if 15.0 <= duration <= 50.0 else 5.0,
            context_dependency_penalty=-context_penalty,
            total_score=total_score,
            hook_strength=round(hook_score, 1),
            dialogue_interest=round(dialogue_score, 1),
            emotional_signal=round(emotional_score, 1),
            action_motion=round(action_score, 1),
            attractiveness_estimate=total_score,
        )

        # 4. Quality Gates
        rejection_reasons = []
        warnings = list(boundary_warnings)

        if duration < min_duration:
            rejection_reasons.append(f"Duration ({duration:.1f}s) is shorter than minimum {min_duration}s")
        if duration > max_duration:
            rejection_reasons.append(f"Duration ({duration:.1f}s) exceeds maximum {max_duration}s")
        if snapped_start < 0.0 or snapped_end > media_duration + 0.1:
            rejection_reasons.append("Candidate boundary exceeds source media boundaries")
        if not text.strip() and not clip_scenes:
            rejection_reasons.append("Empty candidate: no speech or scene content detected")

        if any(w in first_words for w in ("and", "so", "but", "because")):
            warnings.append("Opening may require prior context (starts with conjunction)")
        if not text.endswith((".", "!", "?")):
            warnings.append("Ending may sound slightly abrupt (ends mid-sentence)")

        passed = len(rejection_reasons) == 0
        if not passed:
            gate_status = "rejected"
        elif total_score >= 60.0:
            gate_status = "recommended"
        else:
            gate_status = "needs_review"

        gate_result = QualityGateResult(
            passed=passed,
            status=gate_status,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
        )

        # 5. Category Classification
        category = "Conversation"
        secondary_categories: List[str] = []

        if creative_direction == "dramatic" or "!" in text or any(t.get("turn_type") == "exclamation" for t in clip_turns):
            category = "Dramatic"
        elif creative_direction == "action_motion" or len(clip_scenes) >= 3:
            category = "Action & Motion"
        elif any(t.get("turn_type") == "question" for t in clip_turns):
            category = "Informative"
            secondary_categories.append("Reaction")
        elif len(speakers) >= 2:
            category = "Conversation"
        else:
            category = "Highlight"

        # 6. Suggested Title
        suggested_title = "Interesting Moment"
        if text:
            first_sentence = text.split(".")[0].split("?")[0].split("!")[0].strip()
            if len(first_sentence) > 60:
                suggested_title = first_sentence[:57] + "..."
            elif len(first_sentence) > 5:
                suggested_title = first_sentence
            else:
                suggested_title = f"{category} Highlight ({format_timestamp(snapped_start)})"
        else:
            suggested_title = f"{category} Scene ({format_timestamp(snapped_start)})"

        return GeneratedCandidate(
            id=f"cand_{uuid.uuid4().hex[:12]}",
            start_time=snapped_start,
            end_time=snapped_end,
            duration=duration,
            suggested_title=suggested_title,
            description=text[:250],
            category=category,
            secondary_categories=secondary_categories,
            score_breakdown=breakdown,
            gate_result=gate_result,
            transcript_refs=[t["id"] for t in clip_turns],
            scene_refs=[sc["id"] for sc in clip_scenes],
            visual_refs=[{"timestamp": o["timestamp"], "description": o["description"]} for o in clip_obs],
            audio_refs=[{"segments_count": len(clip_segments), "turns_count": len(clip_turns)}],
            ai_explanation={},
            creative_direction=creative_direction,
            natural_boundary_confidence=boundary_confidence,
            generation_run_id=generation_run_id,
        )

    def _compute_temporal_overlap(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> Tuple[float, float]:
        """Calculates Temporal Intersection over Union (tIoU) and Overlap Ratio relative to candidate A."""
        intersection = max(0.0, min(end_a, end_b) - max(start_a, start_b))
        if intersection <= 0.0:
            return 0.0, 0.0

        union = max(0.001, max(end_a, end_b) - min(start_a, start_b))
        tiou = intersection / union
        overlap_ratio = intersection / max(0.001, end_a - start_a)
        return tiou, overlap_ratio

    def _deduplicate_and_group(
        self,
        candidates: List[GeneratedCandidate],
        overlap_threshold: float = 0.55,
    ) -> List[GeneratedCandidate]:
        """Detect heavily overlapping candidate intervals and cluster alternative cuts."""
        candidates.sort(key=lambda c: c.score_breakdown.total_score, reverse=True)
        clustered: List[GeneratedCandidate] = []

        for cand in candidates:
            matched_group_id = None
            primary_id = None

            for existing in clustered:
                tiou, _ = self._compute_temporal_overlap(
                    cand.start_time, cand.end_time, existing.start_time, existing.end_time
                )
                if tiou >= overlap_threshold:
                    matched_group_id = existing.overlap_group_id or f"group_{existing.id}"
                    existing.overlap_group_id = matched_group_id
                    primary_id = existing.id
                    break

            if matched_group_id:
                cand.overlap_group_id = matched_group_id
                cand.alternative_of_id = primary_id
                if cand.gate_result.status == "recommended":
                    cand.gate_result.status = "needs_review"
                    cand.gate_result.warnings.append(f"Alternative cut of candidate {primary_id}")

            clustered.append(cand)

        return clustered

    def _enrich_ai_explanations(
        self,
        candidates: List[GeneratedCandidate],
        use_ai: bool,
        creative_direction: str,
    ) -> List[GeneratedCandidate]:
        """Add structured explainable evaluation summaries for selected candidates."""
        for cand in candidates:
            explanation = {
                "what_happens": cand.description or "A focused video moment highlighting key dialogue or visual activity.",
                "why_interesting": f"Rated with attractiveness estimate {cand.score_breakdown.total_score:.1f}/100 in '{creative_direction}' direction. Category: {cand.category}.",
                "hook_evaluation": f"Hook strength: {cand.score_breakdown.hook_strength:.1f}/100. Opening words and setup establish clear attention.",
                "boundary_quality": f"Natural boundary confidence: {cand.natural_boundary_confidence * 100:.0f}%. Snapped to speech pauses and visual scene cuts.",
                "context_required": "Minimal; moment contains self-contained speech or visual action.",
                "opening_clarity": "Opening is clear and preserves complete sentence setup." if cand.score_breakdown.opening_clarity >= 6.0 else "May require brief surrounding context.",
                "ending_completeness": "Concludes on natural sentence closure." if cand.score_breakdown.ending_completeness >= 8.0 else "Concludes near natural boundary.",
                "uncertainties": cand.gate_result.warnings,
            }
            cand.ai_explanation = explanation

        return candidates

    def _persist_candidates_and_history(
        self,
        candidates: List[GeneratedCandidate],
        project_id: str,
        media_asset_id: str,
        analysis_run_id: str,
        job_id: Optional[str],
        generation_run_id: str,
        creative_direction: str,
        aspect_ratio: str,
        requested_count: int,
        min_duration: float,
        max_duration: float,
        candidates_discovered: int,
        candidates_selected: int,
        candidates_rejected: int,
        novelty_exclusions: int,
        warnings: List[str],
        generation_type: str = "initial",
        reused_analysis_run_id: Optional[str] = None,
        duration_preference: str = "ai_best_duration",
        is_novelty_exhausted: int = 0,
    ) -> List[Dict[str, Any]]:
        """Persists generation run, candidates, and novelty history in a single SQLite transaction."""
        now = _now_utc()
        results: List[Dict[str, Any]] = []

        with sqlite_session(self.db_path) as conn:
            # 1. Record candidate generation run
            conn.execute(
                """
                INSERT INTO candidate_generation_runs (
                    id, project_id, media_asset_id, analysis_run_id, job_id,
                    creative_direction, aspect_ratio, requested_count,
                    min_duration, max_duration, status,
                    candidates_discovered, candidates_selected, candidates_rejected,
                    novelty_exclusions, error_message, warnings_json,
                    started_at, completed_at, created_at, updated_at,
                    generation_type, reused_analysis_run_id, duration_preference, is_novelty_exhausted
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, 'completed',
                    ?, ?, ?,
                    ?, NULL, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
                """,
                (
                    generation_run_id, project_id, media_asset_id, analysis_run_id, job_id,
                    creative_direction, aspect_ratio, requested_count,
                    min_duration, max_duration,
                    candidates_discovered, candidates_selected, candidates_rejected,
                    novelty_exclusions, json.dumps(warnings),
                    now, now, now, now,
                    generation_type, reused_analysis_run_id, duration_preference, is_novelty_exhausted,
                ),
            )

            # 2. Record selected candidates and clip history
            for cand in candidates:
                b = cand.score_breakdown
                g = cand.gate_result

                conn.execute(
                    """
                    INSERT INTO shorts_candidates (
                        id, project_id, media_asset_id, analysis_run_id, job_id,
                        start_time, end_time, duration, suggested_start_time, suggested_end_time,
                        is_user_modified, title, suggested_title, description, category,
                        secondary_categories_json, quality_score, score_breakdown_json,
                        gate_results_json, warnings_json, missing_evidence_json, review_status,
                        rejection_reason, transcript_references_json, scene_references_json,
                        visual_evidence_json, audio_evidence_json, ai_explanation_json,
                        alternative_of_candidate_id, overlap_group_id, scoring_version,
                        queued_for_render, created_at, updated_at,
                        generation_run_id, creative_direction, natural_boundary_confidence
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        0, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        0, ?, ?,
                        ?, ?, ?
                    )
                    """,
                    (
                        cand.id, project_id, media_asset_id, analysis_run_id, job_id,
                        cand.start_time, cand.end_time, cand.duration, cand.start_time, cand.end_time,
                        cand.suggested_title, cand.suggested_title, cand.description, cand.category,
                        json.dumps(cand.secondary_categories), b.total_score, json.dumps(asdict(b)),
                        json.dumps(asdict(g)), json.dumps(g.warnings), json.dumps([]), g.status,
                        "; ".join(g.rejection_reasons) if g.rejection_reasons else None,
                        json.dumps(cand.transcript_refs), json.dumps(cand.scene_refs),
                        json.dumps(cand.visual_refs), json.dumps(cand.audio_refs),
                        json.dumps(cand.ai_explanation), cand.alternative_of_id, cand.overlap_group_id,
                        SCORING_VERSION, now, now,
                        generation_run_id, cand.creative_direction, cand.natural_boundary_confidence,
                    ),
                )

                # Persist to media_generated_clips_history for persistent novelty non-repetition
                clip_hist_id = f"clip_hist_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO media_generated_clips_history (
                        id, media_asset_id, project_id, generation_run_id,
                        candidate_id, start_time, end_time, duration,
                        creative_direction, aspect_ratio, score, title, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        clip_hist_id, media_asset_id, project_id, generation_run_id,
                        cand.id, cand.start_time, cand.end_time, cand.duration,
                        cand.creative_direction, aspect_ratio, b.total_score, cand.suggested_title, now,
                    ),
                )

                results.append(
                    {
                        "id": cand.id,
                        "project_id": project_id,
                        "media_asset_id": media_asset_id,
                        "analysis_run_id": analysis_run_id,
                        "generation_run_id": generation_run_id,
                        "creative_direction": cand.creative_direction,
                        "start_time": cand.start_time,
                        "end_time": cand.end_time,
                        "duration": cand.duration,
                        "title": cand.suggested_title,
                        "category": cand.category,
                        "quality_score": b.total_score,
                        "review_status": g.status,
                        "score_breakdown": asdict(b),
                        "gate_results": asdict(g),
                        "warnings": g.warnings,
                        "natural_boundary_confidence": cand.natural_boundary_confidence,
                        "overlap_group_id": cand.overlap_group_id,
                        "alternative_of_id": cand.alternative_of_id,
                    }
                )

        return results

    def get_generation_runs(self, media_asset_id: str) -> List[Dict[str, Any]]:
        """Retrieve all candidate generation runs for a media asset."""
        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM candidate_generation_runs
                WHERE media_asset_id = ?
                ORDER BY created_at DESC
                """,
                (media_asset_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_novelty_history(self, media_asset_id: str) -> Dict[str, Any]:
        """Retrieve persistent novelty history intervals for a media asset."""
        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, candidate_id, start_time, end_time, duration, creative_direction, aspect_ratio, score, title, created_at
                FROM media_generated_clips_history
                WHERE media_asset_id = ?
                ORDER BY created_at ASC
                """,
                (media_asset_id,),
            ).fetchall()
            history = [dict(r) for r in rows]
            total_duration = sum(r["duration"] for r in history)
            return {
                "media_asset_id": media_asset_id,
                "total_clips_generated": len(history),
                "total_duration_covered": round(total_duration, 2),
                "history": history,
            }
