"""Milestone 24 Regression Test Expansion: Multi-Track Timeline & Non-Destructive Operations (ZEZ-099)."""

import json
import sqlite3
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationError
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.main import create_app
from app.models.timeline import (
    AddTextOverlayRequest,
    ClipType,
    CreateTimelineRequest,
    CreateTrackRequest,
    InsertClipRequest,
    MoveClipRequest,
    SplitClipRequest,
    TrackType,
    TrimClipRequest,
    UpdateClipPropsRequest,
    UpdateTimelineSettingsRequest,
    UpdateTrackRequest,
)
from app.services.timeline_command_service import TimelineCommandService
from app.services.timeline_service import TimelineService


@pytest.fixture
def timeline_env(tmp_path: Path):
    """Provides isolated storage, fully migrated DB, and sample timeline with video track."""
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(layout.db_file, migrations_dir, layout.backups)

    settings = Settings(
        app_name="ZezEditTestM24Timeline",
        environment="test",
        storage_root=storage_root,
        ffmpeg_threads=2,
    )

    proj_id = "proj_m24_tl"
    media_id = "med_m24_tl"

    with sqlite3.connect(layout.db_file) as conn:
        conn.execute(
            "INSERT INTO projects (id, name, storage_subdir, created_at, updated_at) VALUES (?, 'M24 Timeline Proj', 'm24_tl_p', datetime('now'), datetime('now'))",
            (proj_id,)
        )
        conn.execute(
            """INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external, file_size_bytes,
                duration_seconds, width, height, fps, video_codec, audio_codec, created_at, updated_at
            ) VALUES (?, ?, 'synth_tl.mp4', 'dummy_path.mp4', 1, 1024, 10.0, 1920, 1080, 30.0, 'h264', 'aac', datetime('now'), datetime('now'))""",
            (media_id, proj_id)
        )
        conn.commit()

    tl_service = TimelineService(settings, layout.db_file)
    cmd_service = TimelineCommandService(settings, layout.db_file)

    timeline = tl_service.get_or_create_default_timeline(proj_id)
    v1_track = next(t for t in timeline.tracks if t.track_type == TrackType.VIDEO)

    # Insert an 8-second clip into V1
    clip = cmd_service.insert_clip(
        timeline.id,
        InsertClipRequest(
            track_id=v1_track.id,
            source_media_id=media_id,
            name="Main Clip",
            timeline_start=0.0,
            duration=8.0,
        ),
        executed_by="test",
    )

    return {
        "layout": layout,
        "settings": settings,
        "db_path": layout.db_file,
        "project_id": proj_id,
        "media_id": media_id,
        "timeline_service": tl_service,
        "command_service": cmd_service,
        "timeline_id": timeline.id,
        "track_id": v1_track.id,
        "clip_id": clip.id,
    }


def test_timeline_split_clip_boundary_constraints(timeline_env):
    """Verify split_clip enforces that split time must be strictly inside clip bounds."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_id = timeline_env["timeline_id"]
    clip_id = timeline_env["clip_id"]

    # Split at start time 0.0 (must fail)
    with pytest.raises(ValidationError):
        cmd_svc.split_clip(tl_id, SplitClipRequest(clip_id=clip_id, split_time=0.0))

    # Split at end time 8.0 (must fail)
    with pytest.raises(ValidationError):
        cmd_svc.split_clip(tl_id, SplitClipRequest(clip_id=clip_id, split_time=8.0))

    # Split outside bounds 10.0 (must fail)
    with pytest.raises(ValidationError):
        cmd_svc.split_clip(tl_id, SplitClipRequest(clip_id=clip_id, split_time=10.0))

    # Valid split at 4.0 succeeds and creates two pieces
    left, right = cmd_svc.split_clip(tl_id, SplitClipRequest(clip_id=clip_id, split_time=4.0))
    assert left.timeline_start == 0.0 and left.timeline_end == 4.0
    assert right.timeline_start == 4.0 and right.timeline_end == 8.0


def test_timeline_trim_clip_bounds_and_duration(timeline_env):
    """Verify trim_clip validates start < end and bounds."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_id = timeline_env["timeline_id"]
    clip_id = timeline_env["clip_id"]

    # Invalid: new_start >= new_end
    with pytest.raises(ValidationError):
        cmd_svc.trim_clip(
            tl_id,
            TrimClipRequest(clip_id=clip_id, new_timeline_start=6.0, new_timeline_end=4.0),
        )

    # Valid trim: trim start to 1.0 and end to 7.0
    trimmed = cmd_svc.trim_clip(
        tl_id,
        TrimClipRequest(clip_id=clip_id, new_timeline_start=1.0, new_timeline_end=7.0),
    )
    assert trimmed.timeline_start == 1.0
    assert trimmed.timeline_end == 7.0


def test_timeline_move_clip_cross_track(timeline_env):
    """Verify move_clip shifts timeline position and re-parents to another track."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_svc: TimelineService = timeline_env["timeline_service"]
    tl_id = timeline_env["timeline_id"]
    clip_id = timeline_env["clip_id"]

    # Create a second video track V2
    v2_track = tl_svc.add_track(
        tl_id,
        CreateTrackRequest(name="V2 Secondary", track_type=TrackType.VIDEO),
    )

    moved = cmd_svc.move_clip(
        tl_id,
        MoveClipRequest(clip_id=clip_id, new_timeline_start=2.5, new_track_id=v2_track.id),
    )
    assert moved.timeline_start == 2.5
    assert moved.timeline_end == 10.5
    assert moved.track_id == v2_track.id


def test_timeline_duplicate_clip_naming_and_props(timeline_env):
    """Verify duplicate_clip creates a copy with '(Copy)' suffix placed adjacent to original."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_id = timeline_env["timeline_id"]
    clip_id = timeline_env["clip_id"]

    dup = cmd_svc.duplicate_clip(tl_id, clip_id)
    assert "(Copy)" in dup.name
    assert dup.id != clip_id
    assert dup.timeline_start == 8.0  # Placed right after original clip [0.0 - 8.0]
    assert dup.timeline_end == 16.0


def test_timeline_update_clip_props_volume_and_speed(timeline_env):
    """Verify update_clip_props updates volume, opacity, and speed parameters."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_id = timeline_env["timeline_id"]
    clip_id = timeline_env["clip_id"]

    updated = cmd_svc.update_clip_props(
        tl_id,
        UpdateClipPropsRequest(clip_id=clip_id, volume=0.8, opacity=0.9, speed=1.25),
    )
    assert updated.volume == 0.8
    assert updated.opacity == 0.9
    assert updated.speed == 1.25


def test_timeline_text_overlay_creation_and_auto_track(timeline_env):
    """Verify add_text_overlay auto-locates or creates an overlay track."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_svc: TimelineService = timeline_env["timeline_service"]
    tl_id = timeline_env["timeline_id"]

    ov = cmd_svc.add_text_overlay(
        tl_id,
        AddTextOverlayRequest(text="Important Caption", timeline_start=1.0, duration=3.0, font_size=36),
    )
    assert ov.clip_type == ClipType.TEXT
    assert "Important Caption" in ov.name
    assert ov.content_props.font_size == 36

    # Verify an overlay track now exists
    tl = tl_svc.get_timeline(tl_id)
    assert any(t.track_type == TrackType.OVERLAY for t in tl.tracks)


def test_timeline_consecutive_undo_redo_stack(timeline_env):
    """Verify multiple operations can be undone and redone sequentially in exact reverse order."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_svc: TimelineService = timeline_env["timeline_service"]
    tl_id = timeline_env["timeline_id"]
    clip_id = timeline_env["clip_id"]

    initial_rev = tl_svc.get_timeline(tl_id).revision

    # Operation 1: Trim clip to [1.0 - 7.0]
    cmd_svc.trim_clip(
        tl_id,
        TrimClipRequest(clip_id=clip_id, new_timeline_start=1.0, new_timeline_end=7.0),
    )
    # Operation 2: Update volume to 0.5
    cmd_svc.update_clip_props(tl_id, UpdateClipPropsRequest(clip_id=clip_id, volume=0.5))

    tl_after_ops = tl_svc.get_timeline(tl_id)
    assert tl_after_ops.revision == initial_rev + 2

    # Undo Op 2: Volume returns to 1.0
    tl_undo_1 = cmd_svc.undo(tl_id)
    clip_u1 = next(c for t in tl_undo_1.tracks for c in t.clips if c.id == clip_id)
    assert clip_u1.volume == 1.0

    # Undo Op 1: Clip bounds return to [0.0 - 8.0]
    tl_undo_2 = cmd_svc.undo(tl_id)
    clip_u2 = next(c for t in tl_undo_2.tracks for c in t.clips if c.id == clip_id)
    assert clip_u2.timeline_start == 0.0
    assert clip_u2.timeline_end == 8.0

    # Redo Op 1: Clip bounds back to [1.0 - 7.0]
    tl_redo_1 = cmd_svc.redo(tl_id)
    clip_r1 = next(c for t in tl_redo_1.tracks for c in t.clips if c.id == clip_id)
    assert clip_r1.timeline_start == 1.0
    assert clip_r1.timeline_end == 7.0


def test_timeline_undo_empty_stack_validation(timeline_env):
    """Verify calling undo when history stack is exhausted raises ValidationError."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_id = timeline_env["timeline_id"]

    # Undo the single insert command from fixture
    cmd_svc.undo(tl_id)

    # Calling undo again must fail
    with pytest.raises(ValidationError):
        cmd_svc.undo(tl_id)


def test_timeline_redo_empty_stack_validation(timeline_env):
    """Verify calling redo when no undone commands exist raises ValidationError."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_id = timeline_env["timeline_id"]

    # Nothing has been undone yet
    with pytest.raises(ValidationError):
        cmd_svc.redo(tl_id)


def test_timeline_new_command_clears_redo_history(timeline_env):
    """Verify executing a new command after an undo prunes the undone forward history."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_id = timeline_env["timeline_id"]
    clip_id = timeline_env["clip_id"]

    # 1. Update volume
    cmd_svc.update_clip_props(tl_id, UpdateClipPropsRequest(clip_id=clip_id, volume=0.5))

    # 2. Undo volume update
    cmd_svc.undo(tl_id)
    hist_before = cmd_svc.get_history(tl_id)
    assert hist_before.can_redo is True

    # 3. Apply new command (trim clip)
    cmd_svc.trim_clip(
        tl_id,
        TrimClipRequest(clip_id=clip_id, new_timeline_start=1.0, new_timeline_end=6.0),
    )

    # 4. Forward redo must now be invalidated
    hist_after = cmd_svc.get_history(tl_id)
    assert hist_after.can_redo is False


def test_timeline_settings_update_aspect_and_fps(timeline_env):
    """Verify update_timeline_settings validates and persists name, fps, canvas width/height."""
    tl_svc: TimelineService = timeline_env["timeline_service"]
    tl_id = timeline_env["timeline_id"]

    updated = tl_svc.update_timeline_settings(
        tl_id,
        UpdateTimelineSettingsRequest(name="New Sequence Name", fps=60, canvas_width=1080, canvas_height=1920),
    )
    assert updated.name == "New Sequence Name"
    assert updated.fps == 60
    assert updated.canvas_width == 1080
    assert updated.canvas_height == 1920


def test_timeline_track_visibility_and_mute_toggles(timeline_env):
    """Verify update_track persists track mute, lock, and visibility state."""
    tl_svc: TimelineService = timeline_env["timeline_service"]
    track_id = timeline_env["track_id"]

    updated_tr = tl_svc.update_track(
        track_id,
        UpdateTrackRequest(is_muted=True, is_visible=False, is_locked=True),
    )
    assert updated_tr.is_muted is True
    assert updated_tr.is_visible is False
    assert updated_tr.is_locked is True


def test_timeline_track_deletion_and_clip_cascade(timeline_env):
    """Verify deleting a track cascades deletion to its clips without dangling foreign keys."""
    tl_svc: TimelineService = timeline_env["timeline_service"]
    tl_id = timeline_env["timeline_id"]
    track_id = timeline_env["track_id"]
    clip_id = timeline_env["clip_id"]

    tl_svc.delete_track(track_id)

    # Track must no longer exist in timeline
    tl = tl_svc.get_timeline(tl_id)
    assert not any(t.id == track_id for t in tl.tracks)

    # Clip must also be gone
    assert not any(c.id == clip_id for t in tl.tracks for c in t.clips)


def test_timeline_duration_auto_calculation(timeline_env):
    """Verify timeline total duration reflects the furthest clip out-point."""
    cmd_svc: TimelineCommandService = timeline_env["command_service"]
    tl_svc: TimelineService = timeline_env["timeline_service"]
    tl_id = timeline_env["timeline_id"]
    track_id = timeline_env["track_id"]
    media_id = timeline_env["media_id"]

    # Initial clip is [0.0 - 8.0]
    tl1 = tl_svc.get_timeline(tl_id)
    assert tl1.duration == 8.0

    # Insert a second clip from 10.0 to 15.0
    cmd_svc.insert_clip(
        tl_id,
        InsertClipRequest(
            track_id=track_id,
            source_media_id=media_id,
            name="Far Clip",
            timeline_start=10.0,
            duration=5.0,
        ),
    )

    tl2 = tl_svc.get_timeline(tl_id)
    assert tl2.duration == 15.0
