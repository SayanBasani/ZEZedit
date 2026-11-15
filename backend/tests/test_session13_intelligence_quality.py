"""Regression and acceptance tests for Session 13: Video Intelligence & Quality Audit."""

import pytest
from pathlib import Path
from app.core.config import get_settings
from app.db.migrator import run_migrations
from app.models.reframing import CropKeyframe, DetectedSubject, SubjectTrack
from app.services.framing_engine import FramingEngine
from app.services.highlight_discovery import (
    CREATIVE_DIRECTION_ALIASES,
    DIRECTION_WEIGHTS,
    SUPPORTED_CREATIVE_DIRECTIONS,
)
from app.services.reframing_renderer import (
    build_crop_filter_expression,
)
from app.services.jobs import JobOrchestrator


def test_creative_direction_aliases_and_educational():
    """Verify UI creative directions map properly and do not collapse to best_overall."""
    assert CREATIVE_DIRECTION_ALIASES["action"] == "action_motion"
    assert CREATIVE_DIRECTION_ALIASES["dialogue"] == "engaging_dialogue"
    assert CREATIVE_DIRECTION_ALIASES["emotional"] == "emotional_sad"
    assert CREATIVE_DIRECTION_ALIASES["humor"] == "humorous"
    assert CREATIVE_DIRECTION_ALIASES["educational"] == "educational"

    assert "educational" in SUPPORTED_CREATIVE_DIRECTIONS
    assert "educational" in DIRECTION_WEIGHTS
    assert DIRECTION_WEIGHTS["educational"]["dialogue"] == 0.35
    assert DIRECTION_WEIGHTS["educational"]["narrative"] == 0.30


def test_crop_filter_expression_constant_y_simplification():
    """Verify that constant crop_y produces scalar constant without nested if expressions."""
    keyframes = [
        CropKeyframe(
            timestamp=float(i),
            crop_x=200 + (i % 5) * 10,
            crop_y=0,
            crop_w=452,
            crop_h=804,
            zoom=1.0,
            headroom=0.15,
            subject_count=1,
            framing_strategy="single_subject",
        )
        for i in range(20)
    ]
    expr, cw, ch = build_crop_filter_expression(
        keyframes=keyframes,
        start_time=0.0,
        end_time=20.0,
        source_w=1920,
        source_h=804,
        output_w=1080,
        output_h=1920,
    )
    # y must be a simple constant '0', not nested if
    assert "y='0'" in expr
    assert "crop=w=452:h=804" in expr
    assert len(expr) < 1500


def test_crop_filter_expression_stationary_crop():
    """Verify stationary crop produces simple crop with no if statements."""
    keyframes = [
        CropKeyframe(
            timestamp=float(i * 2),
            crop_x=300,
            crop_y=50,
            crop_w=452,
            crop_h=804,
            zoom=1.0,
            headroom=0.15,
            subject_count=1,
            framing_strategy="center",
        )
        for i in range(5)
    ]
    expr, cw, ch = build_crop_filter_expression(
        keyframes=keyframes,
        start_time=0.0,
        end_time=10.0,
        source_w=1920,
        source_h=804,
        output_w=1080,
        output_h=1920,
    )
    # Both x and y should be scalar constants without any nested if()
    assert "x='300'" in expr
    assert "y='50'" in expr
    assert "if(" not in expr


def test_framing_engine_center_and_speaker_strategies():
    """Verify center and speaker strategies are handled truthfully."""
    engine = FramingEngine()
    source_w, source_h = 1920, 1080

    # Center strategy
    cx, cy, strat, sc, warns = engine.select_framing_target(
        tracks=[],
        timestamp=5.0,
        source_w=source_w,
        source_h=source_h,
        preferred_strategy="center",
    )
    assert strat == "center"
    assert cx == 960.0
    assert cy == 540.0
    assert sc == 0

    # Speaker strategy without detected subjects
    cx, cy, strat, sc, warns = engine.select_framing_target(
        tracks=[],
        timestamp=5.0,
        source_w=source_w,
        source_h=source_h,
        preferred_strategy="speaker",
    )
    assert strat == "speaker_fallback"
    assert any("experimental" in w.lower() for w in warns)

    # Speaker strategy with detected subject
    track = SubjectTrack(
        track_id="trk_speaker_1",
        category="person",
        detections=[
            DetectedSubject(
                timestamp=5.0,
                subject_id="subj_speaker_1",
                category="person",
                box_x=500.0,
                box_y=200.0,
                box_w=200.0,
                box_h=400.0,
                confidence=0.95,
            )
        ],
    )
    cx, cy, strat, sc, warns = engine.select_framing_target(
        tracks=[track],
        timestamp=5.0,
        source_w=source_w,
        source_h=source_h,
        preferred_strategy="speaker",
    )
    assert strat == "speaker_focused"
    assert cx == 600.0
    assert any("experimental" in w.lower() for w in warns)


def test_jobs_stalled_detector_with_non_numeric_pid(tmp_path):
    """Verify check_stalled_jobs handles string worker_pid ('local') without TypeError."""
    settings = get_settings()
    db_file = tmp_path / "test_jobs.db"
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    
    # Initialize database
    run_migrations(db_path=db_file, migrations_dir=migrations_dir)

    orchestrator = JobOrchestrator(settings=settings, db_path=db_file)

    job = orchestrator.create_job(job_type="media_analysis", project_id=None)
    orchestrator.start_job(job.id, worker_pid="local")

    stalled = orchestrator.check_stalled_jobs(timeout_seconds=600.0)
    assert isinstance(stalled, list)
    assert job.id not in stalled
