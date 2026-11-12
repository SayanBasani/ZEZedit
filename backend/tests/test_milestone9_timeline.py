"""Test suite for Milestone 9: AI Video Editor, Multi-Track Timeline & Non-Destructive Editing."""

import json
import sqlite3
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.main import create_app
from app.models.export import STANDARD_EXPORT_PRESETS
from app.models.timeline import (
    AddTextOverlayRequest,
    ClipType,
    CreateTimelineRequest,
    CreateTrackRequest,
    InsertClipRequest,
    MoveClipRequest,
    SendAIMessageRequest,
    SplitClipRequest,
    TimelineRenderRequest,
    TrackType,
    TrimClipRequest,
    UpdateClipPropsRequest,
    UpdateTimelineSettingsRequest,
    UpdateTrackRequest,
)
from app.services.ai_editor_service import AIEditorService
from app.services.timeline_command_service import TimelineCommandService
from app.services.timeline_renderer import TimelineRenderer
from app.services.timeline_service import TimelineService


@pytest.fixture
def timeline_env(tmp_path: Path):
    """Isolated environment with applied migrations 0001 through 0008 and a sample video."""
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()
    db_path = layout.db_file

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(db_path, migrations_dir)

    settings = Settings(
        app_env="test",
        storage_root=storage_root,
        sqlite_db_path=db_path,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        ffmpeg_threads=2,
    )

    # Insert test project
    proj_id = "p_m9_test"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, description, storage_subdir, created_at, updated_at)
            VALUES (?, 'Timeline Project', 'M9 Test Project', 'p_m9_sub', '2026-11-12T00:00:00Z', '2026-11-12T00:00:00Z')
            """,
            (proj_id,),
        )

        # Generate a small 10s video asset
        media_id = "m_source_1"
        media_file = storage_root / "test_source.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=10:size=640x360:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            str(media_file),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external, file_size_bytes, duration_seconds,
                width, height, fps, video_codec, audio_codec, created_at, updated_at
            ) VALUES (
                ?, ?, 'test_source.mp4', ?, 1, ?, 10.0,
                640, 360, 30.0, 'h264', 'aac', '2026-11-12T00:00:00Z', '2026-11-12T00:00:00Z'
            )
            """,
            (media_id, proj_id, str(media_file), media_file.stat().st_size),
        )
        conn.commit()

    return {
        "settings": settings,
        "db_path": db_path,
        "project_id": proj_id,
        "media_id": media_id,
        "media_file": media_file,
    }


def test_timeline_and_track_crud(timeline_env):
    """Verify sequence creation, default tracks, and track operations."""
    tl_svc = TimelineService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    proj_id = timeline_env["project_id"]

    # 1. Fetch default sequence
    timeline = tl_svc.get_or_create_default_timeline(proj_id)
    assert timeline.name == "Main Sequence"
    assert timeline.revision == 1
    assert len(timeline.tracks) == 4  # V2, V1, A1, A2

    # 2. Add custom B-roll track
    new_tr = tl_svc.add_track(
        timeline.id,
        CreateTrackRequest(name="V3 - B-Roll", track_type=TrackType.VIDEO),
    )
    assert new_tr.name == "V3 - B-Roll"

    # 3. Update track settings (mute & lock)
    updated_tr = tl_svc.update_track(new_tr.id, UpdateTrackRequest(is_muted=True, is_locked=True))
    assert updated_tr.is_muted is True
    assert updated_tr.is_locked is True

    # 4. Update timeline settings
    updated_tl = tl_svc.update_timeline_settings(
        timeline.id,
        UpdateTimelineSettingsRequest(name="Shorts Edit 9:16", fps=60),
    )
    assert updated_tl.name == "Shorts Edit 9:16"
    assert updated_tl.fps == 60


def test_clip_operations_and_validation(timeline_env):
    """Verify insert, move, trim, split, duplicate, and validation safeguards."""
    cmd_svc = TimelineCommandService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    tl_svc = TimelineService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    proj_id = timeline_env["project_id"]
    media_id = timeline_env["media_id"]

    timeline = tl_svc.get_or_create_default_timeline(proj_id)
    v1_track = next(t for t in timeline.tracks if t.name == "V1 - Main Video")

    # 1. Insert clip
    clip = cmd_svc.insert_clip(
        timeline.id,
        InsertClipRequest(
            track_id=v1_track.id,
            source_media_id=media_id,
            name="Main Clip",
            timeline_start=1.0,
            duration=5.0,
            source_in=0.0,
        ),
    )
    assert clip.name == "Main Clip"
    assert clip.timeline_start == 1.0
    assert clip.timeline_end == 6.0
    assert clip.duration == 5.0

    # Verify timeline duration updated
    tl_reloaded = tl_svc.get_timeline(timeline.id)
    assert tl_reloaded.duration == 6.0
    assert tl_reloaded.revision == 2

    # 2. Validation: negative start or negative duration must raise ValidationError
    with pytest.raises(Exception):
        cmd_svc.insert_clip(
            timeline.id,
            InsertClipRequest(
                track_id=v1_track.id,
                name="Bad Clip",
                timeline_start=-1.0,
                duration=3.0,
            ),
        )

    # 3. Move clip
    moved = cmd_svc.move_clip(timeline.id, MoveClipRequest(clip_id=clip.id, new_timeline_start=2.0))
    assert moved.timeline_start == 2.0
    assert moved.timeline_end == 7.0

    # 4. Trim clip
    trimmed = cmd_svc.trim_clip(timeline.id, TrimClipRequest(clip_id=clip.id, new_timeline_end=6.0))
    assert trimmed.timeline_end == 6.0
    assert trimmed.duration == 4.0

    # 5. Split clip at 4.0s
    left, right = cmd_svc.split_clip(timeline.id, SplitClipRequest(clip_id=clip.id, split_time=4.0))
    assert left.timeline_start == 2.0
    assert left.timeline_end == 4.0
    assert right.timeline_start == 4.0
    assert right.timeline_end == 6.0

    # 6. Duplicate right clip
    dup = cmd_svc.duplicate_clip(timeline.id, right.id)
    assert dup.timeline_start == 6.0
    assert dup.timeline_end == 8.0

    # 7. Text overlay
    txt = cmd_svc.add_text_overlay(
        timeline.id,
        AddTextOverlayRequest(text="Subscribe Now!", timeline_start=1.5, duration=3.0),
    )
    assert txt.clip_type == ClipType.TEXT
    assert txt.content_props.text == "Subscribe Now!"


def test_persistent_undo_and_redo(timeline_env):
    """Verify undo and redo survive simulated application/connection restarts."""
    cmd_svc = TimelineCommandService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    tl_svc = TimelineService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    proj_id = timeline_env["project_id"]
    media_id = timeline_env["media_id"]

    timeline = tl_svc.get_or_create_default_timeline(proj_id)
    v1_track = next(t for t in timeline.tracks if t.name == "V1 - Main Video")

    # Insert clip
    c1 = cmd_svc.insert_clip(
        timeline.id,
        InsertClipRequest(
            track_id=v1_track.id,
            source_media_id=media_id,
            name="Undo Test Clip",
            timeline_start=0.0,
            duration=4.0,
        ),
    )

    # Split at 2.0s
    left, right = cmd_svc.split_clip(timeline.id, SplitClipRequest(clip_id=c1.id, split_time=2.0))

    history = cmd_svc.get_history(timeline.id)
    assert history.can_undo is True
    assert len(history.history) == 2

    # Simulate crash/restart: instantiate brand new command service
    new_cmd_svc = TimelineCommandService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])

    # Undo split
    undone_tl = new_cmd_svc.undo(timeline.id)
    assert undone_tl.duration == 4.0
    v1_clips = next(t for t in undone_tl.tracks if t.id == v1_track.id).clips
    assert len(v1_clips) == 1
    assert v1_clips[0].timeline_end == 4.0

    # Redo split
    redone_tl = new_cmd_svc.redo(timeline.id)
    v1_clips_redone = next(t for t in redone_tl.tracks if t.id == v1_track.id).clips
    assert len(v1_clips_redone) == 2
    assert v1_clips_redone[0].timeline_end == 2.0
    assert v1_clips_redone[1].timeline_start == 2.0


def test_ai_video_editor_assistant(timeline_env):
    """Verify context retrieval, natural language reasoning, structured plan generation, and approval."""
    ai_svc = AIEditorService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    tl_svc = TimelineService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    cmd_svc = TimelineCommandService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    proj_id = timeline_env["project_id"]
    media_id = timeline_env["media_id"]

    timeline = tl_svc.get_or_create_default_timeline(proj_id)
    v1_track = next(t for t in timeline.tracks if t.name == "V1 - Main Video")

    # Insert a clip
    c = cmd_svc.insert_clip(
        timeline.id,
        InsertClipRequest(
            track_id=v1_track.id,
            source_media_id=media_id,
            name="Interview Scene",
            timeline_start=0.0,
            duration=6.0,
        ),
    )

    # 1. Ask a question
    conv = ai_svc.get_or_create_conversation(proj_id, timeline.id)
    reply = ai_svc.send_message(
        conv.id,
        SendAIMessageRequest(message="What is the project status and duration?", playhead_time=2.0),
    )
    assert reply.role == "assistant"
    assert "duration" in reply.content.lower() or "project" in reply.content.lower()
    assert reply.plan is None

    # 2. Request an edit: "Split clip at playhead"
    split_reply = ai_svc.send_message(
        conv.id,
        SendAIMessageRequest(
            message="Split clip at playhead",
            playhead_time=3.0,
            selected_clip_id=c.id,
        ),
    )
    assert split_reply.plan is not None
    plan = split_reply.plan
    assert plan.status == "proposed"
    assert len(plan.operations) == 1
    assert plan.operations[0].parameters["split_time"] == 3.0

    # 3. Approve and execute plan
    updated_tl = ai_svc.approve_and_execute_plan(plan.id)
    assert updated_tl.revision > timeline.revision

    v1_clips = next(t for t in updated_tl.tracks if t.id == v1_track.id).clips
    assert len(v1_clips) == 2
    assert v1_clips[0].timeline_end == 3.0
    assert v1_clips[1].timeline_start == 3.0

    # Plan status must now be 'executed'
    final_plan = ai_svc.get_plan(plan.id)
    assert final_plan.status == "executed"


def test_timeline_rendering_pipeline(timeline_env):
    """Verify that a multi-track timeline compiles into an FFmpeg filtergraph and renders successfully."""
    renderer = TimelineRenderer(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    tl_svc = TimelineService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    cmd_svc = TimelineCommandService(settings=timeline_env["settings"], db_path=timeline_env["db_path"])
    proj_id = timeline_env["project_id"]
    media_id = timeline_env["media_id"]

    timeline = tl_svc.get_or_create_default_timeline(proj_id)
    v1_track = next(t for t in timeline.tracks if t.name == "V1 - Main Video")

    # Add clip
    cmd_svc.insert_clip(
        timeline.id,
        InsertClipRequest(
            track_id=v1_track.id,
            source_media_id=media_id,
            name="Render Test Clip",
            timeline_start=0.0,
            duration=3.0,
        ),
    )

    # Add text overlay
    cmd_svc.add_text_overlay(
        timeline.id,
        AddTextOverlayRequest(text="Final Render", timeline_start=0.5, duration=2.0),
    )

    # Submit render
    res = renderer.submit_timeline_render(
        project_id=proj_id,
        timeline_id=timeline.id,
        request=TimelineRenderRequest(preset_id="shorts_reels_9_16", title="Timeline M9 Render"),
    )
    assert res["status"] == "queued"
    job_id = res["job_id"]

    # Wait synchronously for background render thread
    jobs_svc = renderer.jobs
    import time
    for _ in range(30):
        job = jobs_svc.get_job(job_id)
        if job.status in ("completed", "failed"):
            break
        time.sleep(0.5)

    assert job.status == "completed", f"Timeline render failed: {job.error_message}"
    result = job.result_metadata
    assert Path(result["output_path"]).exists()
    assert result["output_path"].endswith(".mp4")
    assert result["validation"]["is_valid"] is True


def test_timeline_rest_api_lifecycle(timeline_env):
    """Verify end-to-end FastAPI endpoints for timeline, tracks, clips, and history."""
    app = create_app(settings_override=timeline_env["settings"])
    app.state.storage = StorageLayout.from_root(timeline_env["settings"].storage_root)

    proj_id = timeline_env["project_id"]
    media_id = timeline_env["media_id"]

    with TestClient(app) as client:
        # 1. GET /projects/{id}/timeline
        res = client.get(f"/api/v1/projects/{proj_id}/timeline")
        assert res.status_code == 200
        tl_data = res.json()
        tl_id = tl_data["id"]
        v1_id = next(t["id"] for t in tl_data["tracks"] if t["track_type"] == "video")

        # 2. POST /clips
        res_clip = client.post(
            f"/api/v1/projects/{proj_id}/timelines/{tl_id}/clips",
            json={
                "track_id": v1_id,
                "source_media_id": media_id,
                "name": "API Clip",
                "timeline_start": 0.0,
                "duration": 4.0,
            },
        )
        assert res_clip.status_code == 200
        clip_id = res_clip.json()["id"]

        # 3. GET /history
        res_hist = client.get(f"/api/v1/projects/{proj_id}/timelines/{tl_id}/history")
        assert res_hist.status_code == 200
        assert res_hist.json()["can_undo"] is True

        # 4. POST /undo
        res_undo = client.post(f"/api/v1/projects/{proj_id}/timelines/{tl_id}/history/undo")
        assert res_undo.status_code == 200

        # 5. POST /redo
        res_redo = client.post(f"/api/v1/projects/{proj_id}/timelines/{tl_id}/history/redo")
        assert res_redo.status_code == 200


def test_ai_plan_version_history_and_restore(timeline_env):
    """Verify listing historical AI editing plans and restoring an earlier plan version (ZEZ-080)."""
    app = create_app(settings_override=timeline_env["settings"])
    app.state.storage = StorageLayout.from_root(timeline_env["settings"].storage_root)

    proj_id = timeline_env["project_id"]
    media_id = timeline_env["media_id"]

    with TestClient(app) as client:
        # 1. Fetch timeline and track
        res = client.get(f"/api/v1/projects/{proj_id}/timeline")
        assert res.status_code == 200
        tl_data = res.json()
        tl_id = tl_data["id"]
        v1_id = next(t["id"] for t in tl_data["tracks"] if t["track_type"] == "video")

        # 2. Add an initial clip
        res_clip = client.post(
            f"/api/v1/projects/{proj_id}/timelines/{tl_id}/clips",
            json={
                "track_id": v1_id,
                "source_media_id": media_id,
                "name": "Historical Clip",
                "timeline_start": 0.0,
                "duration": 8.0,
            },
        )
        assert res_clip.status_code == 200
        clip_id = res_clip.json()["id"]

        # 3. Send AI instruction that produces a plan
        res_ai = client.post(
            f"/api/v1/projects/{proj_id}/timelines/{tl_id}/ai/messages",
            json={
                "message": "split this clip at 4.0 seconds",
                "playhead_time": 4.0,
                "selected_clip_id": clip_id,
            },
        )
        assert res_ai.status_code == 200
        msg_data = res_ai.json()
        assert msg_data["plan"] is not None
        plan_id = msg_data["plan"]["id"]

        # 4. GET /timelines/{tl_id}/ai/plans
        res_plans = client.get(f"/api/v1/projects/{proj_id}/timelines/{tl_id}/ai/plans")
        assert res_plans.status_code == 200
        plans = res_plans.json()
        assert len(plans) >= 1
        assert any(p["id"] == plan_id for p in plans)

        # 5. Approve plan
        res_app = client.post(f"/api/v1/projects/{proj_id}/timelines/{tl_id}/ai/plans/{plan_id}/approve")
        assert res_app.status_code == 200

        # 6. Test restore endpoint
        res_restore = client.post(f"/api/v1/projects/{proj_id}/timelines/{tl_id}/ai/plans/{plan_id}/restore")
        assert res_restore.status_code == 200
        restored_tl = res_restore.json()
        assert restored_tl["id"] == tl_id

