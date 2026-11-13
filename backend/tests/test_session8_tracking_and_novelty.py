"""Session 8 verification tests: Temporal Novelty Correction, Real Object Tracking, and Multi-Subject Framing."""

import math
import tempfile
from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.models.reframing import CropKeyframe, DetectedSubject, SubjectTrack
from app.services.framing_engine import FramingEngine
from app.services.highlight_discovery import (
    GeneratedCandidate,
    HighlightDiscoveryEngine,
    QualityGateResult,
    ScoreBreakdown,
)
from app.services.reframing_renderer import build_crop_filter_expression
from app.services.subject_tracker import SubjectTracker


# =============================================================================
# 1. Temporal Novelty Tests
# =============================================================================

def test_compute_temporal_overlap_containment():
    """Verify that shorter containment ratio R_min correctly identifies full and high containment."""
    engine = HighlightDiscoveryEngine()
    # Case A: Candidate A [63.07, 87.31] (dur 24.24), Candidate B [63.07, 114.01] (dur 50.94)
    # Candidate B fully contains Candidate A!
    tiou, ratio_a, ratio_shorter = engine._compute_temporal_overlap(63.07, 87.31, 63.07, 114.01)

    assert math.isclose(ratio_a, 1.0, rel_tol=1e-3)  # Candidate A is 100% covered
    assert math.isclose(ratio_shorter, 1.0, rel_tol=1e-3)  # Shorter interval is 100% contained
    # tIoU is 24.24 / 50.94 ~= 0.4758 (less than 0.50, but shorter containment is 1.0!)
    assert tiou < 0.50
    assert ratio_shorter >= 0.60


def test_compute_temporal_overlap_disjoint():
    """Verify that disjoint intervals yield 0.0 overlap."""
    engine = HighlightDiscoveryEngine()
    tiou, ratio_a, ratio_shorter = engine._compute_temporal_overlap(10.0, 30.0, 35.0, 55.0)
    assert tiou == 0.0
    assert ratio_a == 0.0
    assert ratio_shorter == 0.0


def test_compute_temporal_overlap_partial():
    """Verify partial overlap calculations."""
    engine = HighlightDiscoveryEngine()
    # [10, 30] and [20, 40]: intersection = 10, union = 30, durations = 20 each
    tiou, ratio_a, ratio_shorter = engine._compute_temporal_overlap(10.0, 30.0, 20.0, 40.0)
    assert math.isclose(tiou, 10.0 / 30.0, rel_tol=1e-3)
    assert math.isclose(ratio_a, 0.5, rel_tol=1e-3)
    assert math.isclose(ratio_shorter, 0.5, rel_tol=1e-3)


def test_intra_batch_containment_deduplication():
    """Verify that Candidate B is rejected as an alternative when Candidate A is already selected."""
    engine = HighlightDiscoveryEngine()

    dummy_scores = ScoreBreakdown(
        semantic_interest=85, narrative_completeness=85, conversation_structure=85,
        visual_interest=85, audio_evidence=85, opening_clarity=85, ending_completeness=85,
        duration_suitability=85, context_dependency_penalty=0, total_score=85,
    )
    dummy_gate = QualityGateResult(passed=True, status="recommended", rejection_reasons=[], warnings=[])

    cand_a = GeneratedCandidate(
        id="cand_a",
        start_time=63.07,
        end_time=87.31,
        duration=24.24,
        suggested_title="Candidate A",
        description="First candidate",
        category="highlight",
        secondary_categories=[],
        score_breakdown=dummy_scores,
        gate_result=dummy_gate,
        transcript_refs=[],
        scene_refs=[],
        visual_refs=[],
        audio_refs=[],
        ai_explanation={},
    )

    cand_b = GeneratedCandidate(
        id="cand_b",
        start_time=63.07,
        end_time=114.01,
        duration=50.94,
        suggested_title="Candidate B (Longer Containing Cut)",
        description="Contains candidate A",
        category="highlight",
        secondary_categories=[],
        score_breakdown=dummy_scores,
        gate_result=dummy_gate,
        transcript_refs=[],
        scene_refs=[],
        visual_refs=[],
        audio_refs=[],
        ai_explanation={},
    )

    cand_c = GeneratedCandidate(
        id="cand_c",
        start_time=130.0,
        end_time=155.0,
        duration=25.0,
        suggested_title="Candidate C (Distinct)",
        description="Non-overlapping segment",
        category="highlight",
        secondary_categories=[],
        score_breakdown=dummy_scores,
        gate_result=dummy_gate,
        transcript_refs=[],
        scene_refs=[],
        visual_refs=[],
        audio_refs=[],
        ai_explanation={},
    )

    # Run deduplication and grouping
    grouped = engine._deduplicate_and_group([cand_a, cand_b, cand_c])

    # cand_b must be identified as an alternative of cand_a
    cand_b_result = next(c for c in grouped if c.id == "cand_b")
    assert cand_b_result.alternative_of_id == "cand_a"
    assert cand_b_result.overlap_group_id is not None

    # cand_c must remain independent
    cand_c_result = next(c for c in grouped if c.id == "cand_c")
    assert cand_c_result.alternative_of_id is None


# =============================================================================
# 2. Object Detection & Subject Tracking Tests
# =============================================================================

def test_subject_tracker_detection_person_and_object():
    """Verify CPU-friendly detection of person (skin tone) and object (gradient saliency)."""
    tracker = SubjectTracker()

    # Create synthetic frame: 720p with a vertical person shape and a horizontal object shape
    frame = np.full((720, 1280, 3), 40, dtype=np.uint8)

    # Person shape with skin tone chroma in YCrCb: (B=140, G=160, R=210)
    # Height > 1.3 * Width -> classified as 'person'
    frame[150:450, 200:320] = [140, 160, 210]

    # Foreground object: horizontal bright yellow/white rectangle
    # Width >= 1.4 * Height -> classified as 'vehicle' or 'object'
    frame[300:460, 700:980] = [240, 220, 50]

    dets = tracker.detect_subjects_in_frame(frame, timestamp=1.5, source_w=1280, source_h=720)

    categories = [d.category for d in dets]
    assert len(dets) >= 2
    assert "person" in categories or "face" in categories
    assert "object" in categories or "vehicle" in categories

    for d in dets:
        assert d.confidence >= 0.70
        assert 0 <= d.box_x <= 1280
        assert 0 <= d.box_y <= 720
        assert d.box_w > 0
        assert d.box_h > 0


def test_subject_tracker_multi_subject_tracking_separate_tracks():
    """Verify that two distinct moving subjects maintain independent SubjectTrack identities."""
    import cv2
    tracker = SubjectTracker(sample_fps=2.0)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        samples = []

        # Generate 4 synthetic frames with 2 subjects moving in opposite directions
        # Subject A moves right, Subject B moves left
        for i in range(4):
            t = round(i * 0.5, 2)
            f = np.full((720, 1280, 3), 40, dtype=np.uint8)

            # Subject A (Person, skin-like): starts at x=200, moves +30px each frame
            ax = 200 + (i * 30)
            f[150:450, ax:ax + 120] = [140, 160, 210]

            # Subject B (Object): starts at x=900, moves -30px each frame
            bx = 900 - (i * 30)
            f[300:460, bx:bx + 200] = [240, 220, 50]

            img_p = tmp_path / f"frame_{i:03d}.jpg"
            cv2.imwrite(str(img_p), f)
            samples.append((t, img_p))

        tracks = tracker.track_subjects_across_samples(
            samples=samples,
            source_w=1280,
            source_h=720,
        )

        # Must maintain at least 2 distinct tracks
        assert len(tracks) >= 2
        track_ids = {t.track_id for t in tracks}
        assert len(track_ids) >= 2
        assert "subject_1" in track_ids
        assert "subject_2" in track_ids

        # Ensure tracks contain sequential observations
        t1 = next(t for t in tracks if t.track_id == "subject_1")
        assert len(t1.detections) >= 3
        assert t1.confidence_avg > 0.60


def test_subject_tracker_scene_cut_termination():
    """Verify that active tracks terminate cleanly when crossing a scene cut boundary."""
    import cv2
    tracker = SubjectTracker(sample_fps=2.0)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        samples = []

        # Frame 0 (t=0.0): Subject A
        f0 = np.full((720, 1280, 3), 40, dtype=np.uint8)
        f0[150:450, 200:320] = [140, 160, 210]
        p0 = tmp_path / "f0.jpg"
        cv2.imwrite(str(p0), f0)
        samples.append((0.0, p0))

        # Scene cut occurs at t=0.4s

        # Frame 1 (t=0.5): Completely different scene
        f1 = np.full((720, 1280, 3), 40, dtype=np.uint8)
        f1[200:350, 800:950] = [140, 160, 210]
        p1 = tmp_path / "f1.jpg"
        cv2.imwrite(str(p1), f1)
        samples.append((0.5, p1))

        tracks = tracker.track_subjects_across_samples(
            samples=samples,
            source_w=1280,
            source_h=720,
            scene_cut_timestamps=[0.4],
        )

        # Subject track before cut must be terminated; a new track must spawn for post-cut
        assert len(tracks) >= 2
        assert tracks[0].track_id != tracks[1].track_id


# =============================================================================
# 3. Multi-Subject Framing Strategies Tests
# =============================================================================

def test_framing_engine_single_subject():
    """Verify single / primary subject framing targets the prominent subject."""
    engine = FramingEngine(target_aspect_ratio="9:16")

    det1 = DetectedSubject(timestamp=1.0, box_x=300, box_y=200, box_w=150, box_h=300, confidence=0.90, category="person", subject_id="sub_1")
    det2 = DetectedSubject(timestamp=1.0, box_x=800, box_y=250, box_w=100, box_h=200, confidence=0.75, category="person", subject_id="sub_2")

    track1 = SubjectTrack(track_id="sub_1", category="person", detections=[det1], first_seen=0.0, last_seen=2.0)
    track2 = SubjectTrack(track_id="sub_2", category="person", detections=[det2], first_seen=0.0, last_seen=2.0)

    target_x, target_y, strategy, count, warns = engine.select_framing_target(
        tracks=[track1, track2],
        timestamp=1.0,
        source_w=1920,
        source_h=1080,
        preferred_strategy="primary_subject",
    )

    # Must frame sub_1 (prominent subject with higher confidence and area)
    assert strategy == "single_subject"
    assert count == 1
    assert math.isclose(target_x, det1.center_x, abs_tol=10.0)


def test_framing_engine_two_person_joint_framing():
    """Verify two-person framing centers between both subjects when spread fits."""
    engine = FramingEngine(target_aspect_ratio="9:16")

    det1 = DetectedSubject(timestamp=2.0, box_x=500, box_y=200, box_w=120, box_h=250, confidence=0.88, category="person", subject_id="sub_1")
    det2 = DetectedSubject(timestamp=2.0, box_x=800, box_y=220, box_w=120, box_h=240, confidence=0.85, category="person", subject_id="sub_2")

    track1 = SubjectTrack(track_id="sub_1", category="person", detections=[det1])
    track2 = SubjectTrack(track_id="sub_2", category="person", detections=[det2])

    target_x, target_y, strategy, count, warns = engine.select_framing_target(
        tracks=[track1, track2],
        timestamp=2.0,
        source_w=1920,
        source_h=1080,
        preferred_strategy="two_person",
    )

    assert strategy == "two_person"
    assert count == 2
    # Target center should be midpoint between both subjects
    expected_mid_x = (500 + 920) / 2.0  # 710.0
    assert math.isclose(target_x, expected_mid_x, abs_tol=5.0)


def test_framing_engine_group_framing():
    """Verify group framing encompasses bounding box union of 3+ subjects."""
    engine = FramingEngine(target_aspect_ratio="9:16")

    det1 = DetectedSubject(timestamp=3.0, box_x=400, box_y=200, box_w=100, box_h=200, confidence=0.85, category="person", subject_id="s1")
    det2 = DetectedSubject(timestamp=3.0, box_x=700, box_y=210, box_w=100, box_h=200, confidence=0.85, category="person", subject_id="s2")
    det3 = DetectedSubject(timestamp=3.0, box_x=1000, box_y=190, box_w=100, box_h=200, confidence=0.85, category="person", subject_id="s3")

    tracks = [
        SubjectTrack(track_id="s1", category="person", detections=[det1]),
        SubjectTrack(track_id="s2", category="person", detections=[det2]),
        SubjectTrack(track_id="s3", category="person", detections=[det3]),
    ]

    target_x, target_y, strategy, count, warns = engine.select_framing_target(
        tracks=tracks,
        timestamp=3.0,
        source_w=1920,
        source_h=1080,
        preferred_strategy="auto",
    )

    assert strategy == "group"
    assert count == 3
    # Union X spans from 400 to 1100 -> center is 750
    assert math.isclose(target_x, 750.0, abs_tol=5.0)


def test_framing_engine_action_object_framing():
    """Verify object tracking prioritizes vehicle/object categories over background."""
    engine = FramingEngine(target_aspect_ratio="9:16")

    det_person = DetectedSubject(timestamp=1.0, box_x=200, box_y=200, box_w=100, box_h=200, confidence=0.80, category="person", subject_id="p1")
    det_car = DetectedSubject(timestamp=1.0, box_x=900, box_y=300, box_w=300, box_h=180, confidence=0.85, category="vehicle", subject_id="v1")

    tracks = [
        SubjectTrack(track_id="p1", category="person", detections=[det_person]),
        SubjectTrack(track_id="v1", category="vehicle", detections=[det_car]),
    ]

    target_x, target_y, strategy, count, warns = engine.select_framing_target(
        tracks=tracks,
        timestamp=1.0,
        source_w=1920,
        source_h=1080,
        preferred_strategy="action_object",
    )

    assert strategy == "action_object"
    assert math.isclose(target_x, det_car.center_x, abs_tol=5.0)


# =============================================================================
# 4. Render Pipeline Keyframe & Filtergraph Compilation Tests
# =============================================================================

def test_dynamic_crop_filter_expression_generation():
    """Verify build_crop_filter_expression compiles moving keyframes into dynamic piecewise expressions."""
    keyframes = [
        CropKeyframe(timestamp=0.0, crop_x=200, crop_y=0, crop_w=608, crop_h=1080),
        CropKeyframe(timestamp=2.0, crop_x=400, crop_y=0, crop_w=608, crop_h=1080),
        CropKeyframe(timestamp=4.0, crop_x=600, crop_y=0, crop_w=608, crop_h=1080),
    ]

    expr, cw, ch = build_crop_filter_expression(
        keyframes=keyframes,
        start_time=0.0,
        end_time=4.0,
        source_w=1920,
        source_h=1080,
        output_w=1080,
        output_h=1920,
    )

    assert cw == 608
    assert ch == 1080
    assert "crop=w=608:h=1080" in expr
    assert "scale=1080:1920" in expr
    # Dynamic time-varying expression must be present
    assert "if(lt(t" in expr
