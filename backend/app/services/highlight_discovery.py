"""AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking."""

import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError, ProcessingError
from app.db.connection import sqlite_session

logger = logging.getLogger("zezedit.highlight_discovery")

SCORING_VERSION = "2.0.0-m6"


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    overlap_group_id: Optional[str] = None
    alternative_of_id: Optional[str] = None


class HighlightDiscoveryEngine:
    """Discovers, bounds, scores, and deduplicates Shorts candidate moments from media analysis."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.db_path = db_path or (self.settings.storage_root / "db" / "zezedit.db")

    def discover_highlights(
        self,
        project_id: str,
        media_asset_id: str,
        analysis_run_id: Optional[str] = None,
        job_id: Optional[str] = None,
        min_duration: float = 12.0,
        max_duration: float = 65.0,
        target_clip_count: int = 10,
        use_ai_explanations: bool = True,
    ) -> List[Dict[str, Any]]:
        """Main highlight discovery workflow."""
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
            observations = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM visual_observations WHERE analysis_run_id = ? ORDER BY timestamp ASC",
                    (analysis_run_id,),
                ).fetchall()
            ]

        logger.info(
            "Loaded analysis for asset %s: %d segments, %d turns, %d scenes, %d observations",
            media_asset_id,
            len(segments),
            len(turns),
            len(scenes),
            len(observations),
        )

        # 4. Generate candidate intervals
        raw_candidates = self._generate_candidate_intervals(
            segments=segments,
            turns=turns,
            scenes=scenes,
            observations=observations,
            media_duration=media_duration,
            min_duration=min_duration,
            max_duration=max_duration,
        )

        # 5. Score and apply quality gates to each candidate
        scored_candidates: List[GeneratedCandidate] = []
        for cand in raw_candidates:
            scored = self._score_candidate(
                cand=cand,
                segments=segments,
                turns=turns,
                scenes=scenes,
                observations=observations,
                media_duration=media_duration,
                min_duration=min_duration,
                max_duration=max_duration,
            )
            scored_candidates.append(scored)

        # 6. Deduplicate & cluster overlapping alternatives
        processed_candidates = self._deduplicate_and_group(scored_candidates)

        # 7. Sort by score descending
        processed_candidates.sort(key=lambda c: c.score_breakdown.total_score, reverse=True)

        # 8. AI-Assisted explanations for top recommended candidates
        final_candidates = self._enrich_ai_explanations(
            candidates=processed_candidates[:target_clip_count],
            use_ai=use_ai_explanations,
        )

        # 9. Persist candidates to SQLite
        persisted = self._persist_candidates(
            candidates=final_candidates,
            project_id=project_id,
            media_asset_id=media_asset_id,
            analysis_run_id=analysis_run_id,
            job_id=job_id,
        )

        logger.info("Highlight discovery completed: %d candidates generated and persisted", len(persisted))
        return persisted

    def _generate_candidate_intervals(
        self,
        segments: List[Dict[str, Any]],
        turns: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
        observations: List[Dict[str, Any]],
        media_duration: float,
        min_duration: float,
        max_duration: float,
    ) -> List[Dict[str, Any]]:
        """Generate candidate boundaries from speech turns, conversational exchanges, and scene cuts."""
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

        # Strategy B: Multi-turn dialogue exchanges (2 to 5 consecutive turns)
        num_turns = len(turns)
        for i in range(num_turns):
            curr_text = [turns[i]["text"]]
            curr_turn_ids = [turns[i]["id"]]
            start_t = turns[i]["start_time"]

            for j in range(i + 1, min(i + 5, num_turns)):
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

        # Strategy C: Scene-aligned windows (for visual segments with or without speech)
        for sc in scenes:
            sc_dur = sc["end_time"] - sc["start_time"]
            if min_duration <= sc_dur <= max_duration:
                # Find overlapping turns
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

        # Fallback if video has no speech turns: generate uniform duration candidate windows
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

    def _score_candidate(
        self,
        cand: Dict[str, Any],
        segments: List[Dict[str, Any]],
        turns: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
        observations: List[Dict[str, Any]],
        media_duration: float,
        min_duration: float,
        max_duration: float,
    ) -> GeneratedCandidate:
        """Context-aware boundary snapping, explainable scoring, and quality gates."""
        start_t = cand["start_time"]
        end_t = cand["end_time"]

        # 1. Context-Aware Boundary Snapping
        # Add 0.3s lead-in and 0.5s lead-out for natural breathing room
        buffered_start = max(0.0, start_t - 0.3)
        buffered_end = min(media_duration, end_t + 0.5)

        # If a visual scene cut is within 0.6s of start or end, snap cleanly to avoid flash frames
        for sc in scenes:
            if abs(buffered_start - sc["start_time"]) <= 0.6:
                buffered_start = sc["start_time"]
            if abs(buffered_end - sc["end_time"]) <= 0.6:
                buffered_end = sc["end_time"]

        duration = round(buffered_end - buffered_start, 3)

        # Extract text and evidence inside the clip
        clip_turns = [
            t for t in turns
            if t["end_time"] >= buffered_start and t["start_time"] <= buffered_end
        ]
        clip_segments = [
            s for s in segments
            if s["end_time"] >= buffered_start and s["start_time"] <= buffered_end
        ]
        clip_scenes = [
            sc for sc in scenes
            if sc["end_time"] >= buffered_start and sc["start_time"] <= buffered_end
        ]
        clip_obs = [
            o for o in observations
            if buffered_start <= o["timestamp"] <= buffered_end
        ]

        text = " ".join(t["text"] for t in clip_turns).strip() or cand.get("text", "")

        # 2. Component Scoring Model (Documented, versioned 2.0.0-m6)
        # 2.1 Semantic interest (0-20)
        semantic_score = 5.0
        lower_text = text.lower()
        if any(w in lower_text for w in ("why", "how", "because", "secret", "never", "always", "best", "truth", "discover", "important")):
            semantic_score += 5.0
        if any(t.get("turn_type") == "question" for t in clip_turns):
            semantic_score += 5.0
        if any(t.get("turn_type") == "exclamation" for t in clip_turns) or "!" in text:
            semantic_score += 5.0
        semantic_score = min(20.0, semantic_score)

        # 2.2 Narrative completeness (0-20)
        narrative_score = 10.0
        if text.endswith((".", "!", "?")):
            narrative_score += 6.0
        if len(clip_turns) >= 2:
            narrative_score += 4.0
        narrative_score = min(20.0, narrative_score)

        # 2.3 Conversation structure (0-15)
        speakers = {t["speaker_label"] for t in clip_turns}
        conv_score = 5.0
        if len(speakers) >= 2:
            conv_score += 7.0
        if len(clip_turns) >= 3:
            conv_score += 3.0
        conv_score = min(15.0, conv_score)

        # 2.4 Visual interest (0-15)
        visual_score = 5.0
        if len(clip_scenes) >= 2:
            visual_score += 5.0
        if len(clip_obs) >= 1:
            visual_score += 5.0
        visual_score = min(15.0, visual_score)

        # 2.5 Audio evidence (0-10)
        audio_score = 6.0
        if clip_segments:
            avg_conf = sum(s.get("confidence", 0.9) for s in clip_segments) / len(clip_segments)
            audio_score = round(avg_conf * 10.0, 1)
        audio_score = min(10.0, audio_score)

        # 2.6 Opening clarity (0-10)
        opening_score = 8.0
        # Check if first turn starts cleanly without dangling prepositions
        first_words = lower_text.split()[:2]
        if any(w in ("and", "but", "so", "because", "or") for w in first_words):
            opening_score -= 4.0
        opening_score = max(0.0, min(10.0, opening_score))

        # 2.7 Ending completeness (0-10)
        ending_score = 7.0
        if text.endswith((".", "!", "?")):
            ending_score = 10.0
        ending_score = min(10.0, ending_score)

        # 2.8 Duration suitability (-5 to +10)
        # Optimal Shorts duration is 25s - 45s
        if 20.0 <= duration <= 45.0:
            duration_score = 10.0
        elif 15.0 <= duration < 20.0 or 45.0 < duration <= 55.0:
            duration_score = 6.0
        elif duration < 15.0:
            duration_score = 2.0
        else:
            duration_score = 0.0

        # 2.9 Context dependency penalty (0 to -15)
        context_penalty = 0.0
        if any(w in first_words for w in ("he", "she", "they", "that", "this")) and len(clip_turns) == 1:
            context_penalty = -5.0

        raw_total = (
            semantic_score
            + narrative_score
            + conv_score
            + visual_score
            + audio_score
            + opening_score
            + ending_score
            + duration_score
            + context_penalty
        )
        total_score = round(max(0.0, min(100.0, raw_total)), 1)

        breakdown = ScoreBreakdown(
            semantic_interest=semantic_score,
            narrative_completeness=narrative_score,
            conversation_structure=conv_score,
            visual_interest=visual_score,
            audio_evidence=audio_score,
            opening_clarity=opening_score,
            ending_completeness=ending_score,
            duration_suitability=duration_score,
            context_dependency_penalty=context_penalty,
            total_score=total_score,
        )

        # 3. Quality Gates
        rejection_reasons = []
        warnings = []

        if duration < min_duration:
            rejection_reasons.append(f"Duration ({duration:.1f}s) is shorter than minimum {min_duration}s")
        if duration > max_duration:
            rejection_reasons.append(f"Duration ({duration:.1f}s) exceeds maximum {max_duration}s")
        if buffered_start < 0.0 or buffered_end > media_duration + 0.1:
            rejection_reasons.append("Candidate boundary exceeds source media boundaries")
        if not text.strip() and not clip_scenes:
            rejection_reasons.append("Empty candidate: no speech or scene content detected")

        if opening_score < 5.0:
            warnings.append("Opening may require prior context (starts with conjunction/pronoun)")
        if ending_score < 7.0:
            warnings.append("Ending may sound slightly abrupt or incomplete")

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

        # 4. Category Classification
        category = "Conversation"
        secondary_categories: List[str] = []

        if len(speakers) >= 2:
            category = "Conversation"
        elif any(t.get("turn_type") == "question" for t in clip_turns):
            category = "Informative"
            secondary_categories.append("Reaction")
        elif "!" in text or any(t.get("turn_type") == "exclamation" for t in clip_turns):
            category = "Dramatic"
        elif any(w in lower_text for w in ("learn", "how", "tutorial", "step", "method")):
            category = "Educational"

        # 5. Suggested Title
        suggested_title = "Interesting Moment"
        if text:
            # Use first sentence up to 60 chars
            first_sentence = text.split(".")[0].split("?")[0].strip()
            if len(first_sentence) > 60:
                suggested_title = first_sentence[:57] + "..."
            elif len(first_sentence) > 5:
                suggested_title = first_sentence
            else:
                suggested_title = f"{category} Highlight ({format_timestamp(buffered_start)})"
        else:
            suggested_title = f"{category} Scene ({format_timestamp(buffered_start)})"

        return GeneratedCandidate(
            id=f"cand_{uuid.uuid4().hex[:12]}",
            start_time=round(buffered_start, 3),
            end_time=round(buffered_end, 3),
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
        )

    def _deduplicate_and_group(
        self,
        candidates: List[GeneratedCandidate],
        overlap_threshold: float = 0.65,
    ) -> List[GeneratedCandidate]:
        """Detect heavily overlapping candidate intervals and cluster alternative interpretations."""
        candidates.sort(key=lambda c: c.score_breakdown.total_score, reverse=True)
        clustered: List[GeneratedCandidate] = []

        for cand in candidates:
            matched_group_id = None
            primary_id = None

            for existing in clustered:
                # Compute temporal Intersection-over-Union (IoU)
                inter_start = max(cand.start_time, existing.start_time)
                inter_end = min(cand.end_time, existing.end_time)
                intersection = max(0.0, inter_end - inter_start)

                union_start = min(cand.start_time, existing.start_time)
                union_end = max(cand.end_time, existing.end_time)
                union = max(0.001, union_end - union_start)

                iou = intersection / union
                if iou >= overlap_threshold:
                    matched_group_id = existing.overlap_group_id or f"group_{existing.id}"
                    existing.overlap_group_id = matched_group_id
                    primary_id = existing.id
                    break

            if matched_group_id:
                cand.overlap_group_id = matched_group_id
                cand.alternative_of_id = primary_id
                # Demote review_status to needs_review so it doesn't pollute primary recommended list
                if cand.gate_result.status == "recommended":
                    cand.gate_result.status = "needs_review"
                    cand.gate_result.warnings.append(f"Alternative cut of candidate {primary_id}")

            clustered.append(cand)

        return clustered

    def _enrich_ai_explanations(
        self,
        candidates: List[GeneratedCandidate],
        use_ai: bool,
    ) -> List[GeneratedCandidate]:
        """Add structured AI explanations for top candidates using local Ollama or deterministic heuristics."""
        for cand in candidates:
            explanation = {
                "what_happens": cand.description or "A focused video moment highlighting key dialogue or activity.",
                "why_interesting": f"Rated with quality score {cand.score_breakdown.total_score:.1f}/100. Category: {cand.category}.",
                "context_required": "Minimal; moment contains self-contained speech or clear visual setup.",
                "opening_clarity": "Opening is clear and preserves complete sentence setup." if cand.score_breakdown.opening_clarity >= 6.0 else "May require brief surrounding context.",
                "ending_completeness": "Concludes on natural sentence closure." if cand.score_breakdown.ending_completeness >= 8.0 else "Concludes near natural boundary.",
                "uncertainties": cand.gate_result.warnings,
            }
            cand.ai_explanation = explanation

        return candidates

    def _persist_candidates(
        self,
        candidates: List[GeneratedCandidate],
        project_id: str,
        media_asset_id: str,
        analysis_run_id: str,
        job_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Persist candidate records to SQLite `shorts_candidates` table."""
        now = _now_utc()
        results: List[Dict[str, Any]] = []

        with sqlite_session(self.db_path) as conn:
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
                        queued_for_render, created_at, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        0, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        0, ?, ?
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
                        SCORING_VERSION, now, now
                    ),
                )

                results.append(
                    {
                        "id": cand.id,
                        "project_id": project_id,
                        "media_asset_id": media_asset_id,
                        "analysis_run_id": analysis_run_id,
                        "start_time": cand.start_time,
                        "end_time": cand.end_time,
                        "duration": cand.duration,
                        "title": cand.suggested_title,
                        "category": cand.category,
                        "quality_score": b.total_score,
                        "review_status": g.status,
                        "score_breakdown": asdict(b),
                        "gate_results": asdict(g),
                        "overlap_group_id": cand.overlap_group_id,
                        "alternative_of_id": cand.alternative_of_id,
                    }
                )

        return results


def format_timestamp(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"
