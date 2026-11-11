"""Test suite for Milestone 10: Character Extraction Studio, Character Library & Review System."""

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
from app.models.character import (
    ConfirmCandidateRequest,
    ExtractionJobConfig,
    MergeCandidatesRequest,
    RenameCandidateRequest,
    SplitCandidateRequest,
    UpdateProfileRequest,
)
from app.services.character_service import CharacterService


@pytest.fixture
def character_env(tmp_path: Path):
    """Isolated environment with migrations 0001-0009 and a synthetic video file."""
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()
    db_path = layout.db_file

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    run_migrations(db_path, migrations_dir)

    settings = Settings(
        storage_root=storage_root,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        ffmpeg_threads=2,
    )

    # Generate synthetic 3-second test video
    raw_dir = storage_root / "projects" / "proj_char_test" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    video_path = raw_dir / "interview_sample.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=3:size=640x360:rate=25",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(video_path),
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    proj_id = "proj_char_test"
    asset_id = "med_char_test"
    now = "2026-11-12T01:00:00Z"

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO projects (id, name, description, storage_subdir, status, created_at, updated_at)
            VALUES (?, 'Character Test Project', 'M10 Test', 'proj_char_test', 'active', ?, ?)
            """,
            (proj_id, now, now),
        )
        cur.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, is_external, file_size_bytes, duration_seconds,
                width, height, fps, video_codec, audio_codec, created_at, updated_at
            ) VALUES (
                ?, ?, 'interview_sample.mp4', ?, 1, 1024, 3.0,
                640, 360, 25.0, 'h264', 'aac', ?, ?
            )
            """,
            (asset_id, proj_id, str(video_path), now, now),
        )
        # Insert a transcript segment for dialogue correlation test
        cur.execute(
            """
            INSERT INTO analysis_runs (id, project_id, media_asset_id, status, created_at, updated_at)
            VALUES ('run_char_1', ?, ?, 'completed', ?, ?)
            """,
            (proj_id, asset_id, now, now),
        )
        cur.execute(
            """
            INSERT INTO transcript_segments (
                id, analysis_run_id, media_asset_id, start_time, end_time, text, language, confidence, words_json, created_at
            ) VALUES ('seg_1', 'run_char_1', ?, 0.5, 2.5, 'Welcome to the interview show today.', 'en', 0.95, '[]', ?)
            """,
            (asset_id, now),
        )
        conn.commit()

    return {
        "settings": settings,
        "storage": layout,
        "project_id": proj_id,
        "media_asset_id": asset_id,
        "video_path": video_path,
        "db_path": db_path,
    }


def test_character_extraction_and_observations(character_env):
    """Test frame sampling, face/person region detection, thumbnails, and dialogue association."""
    service = CharacterService(
        settings=character_env["settings"],
        db_path=character_env["db_path"],
    )

    cfg = ExtractionJobConfig(
        media_asset_id=character_env["media_asset_id"],
        sample_interval_sec=1.0,
        min_face_size=20,
    )

    job_status = service.run_extraction_job(character_env["project_id"], cfg)
    assert job_status.status == "completed"
    assert job_status.frames_sampled >= 3
    assert job_status.detections_count >= 1
    assert job_status.candidates_count >= 1

    candidates = service.get_candidates(character_env["project_id"], job_id=job_status.id)
    assert len(candidates) >= 1
    c1 = candidates[0]
    assert c1.review_status == "provisional"
    assert c1.observation_count >= 1
    assert c1.sampled_screen_time_seconds > 0.0

    # Verify observations
    assert len(c1.observations) >= 1
    obs = c1.observations[0]
    assert Path(obs.thumbnail_path).exists()
    assert Path(obs.thumbnail_path).stat().st_size > 0
    assert obs.bounding_box.width > 0
    assert obs.bounding_box.height > 0

    # Verify dialogue association at t >= 0.5s
    overlapping_obs = [o for o in c1.observations if 0.5 <= o.timestamp <= 2.5]
    if overlapping_obs:
        assert overlapping_obs[0].unverified_dialogue is not None
        assert "Welcome to the interview show" in overlapping_obs[0].unverified_dialogue
        assert "Unverified" in overlapping_obs[0].unverified_dialogue


def test_candidate_human_review_workflow(character_env):
    """Test rename, detach observation (evidence retained), split, merge, reject, and confirm."""
    service = CharacterService(
        settings=character_env["settings"],
        db_path=character_env["db_path"],
    )

    cfg = ExtractionJobConfig(
        media_asset_id=character_env["media_asset_id"],
        sample_interval_sec=0.5,
    )
    job_status = service.run_extraction_job(character_env["project_id"], cfg)
    candidates = service.get_candidates(character_env["project_id"], job_id=job_status.id)
    assert len(candidates) >= 1
    target_cand = candidates[0]

    # 1. Rename candidate
    renamed = service.rename_candidate(character_env["project_id"], target_cand.id, "Host Alex")
    assert renamed.label == "Host Alex"

    # 2. Detach an observation (evidence file should NOT be deleted)
    assert len(renamed.observations) >= 2
    obs_to_detach = renamed.observations[0]
    thumb_file = Path(obs_to_detach.thumbnail_path)
    assert thumb_file.exists()

    after_detach = service.detach_observation(character_env["project_id"], target_cand.id, obs_to_detach.id)
    assert after_detach.observation_count == len(renamed.observations) - 1
    # Evidence must be intact
    assert thumb_file.exists()

    # 3. Split candidate
    active_obs = after_detach.observations
    obs_to_split = [active_obs[0].id]
    orig_c, new_c = service.split_candidate(
        character_env["project_id"],
        target_cand.id,
        SplitCandidateRequest(
            observation_ids_to_split=obs_to_split,
            new_candidate_label="Guest Bob",
        ),
    )
    assert new_c.label == "Guest Bob"
    assert new_c.observation_count == 1
    assert orig_c.observation_count == len(active_obs) - 1

    # 4. Merge candidates
    merged = service.merge_candidates(
        character_env["project_id"],
        MergeCandidatesRequest(
            source_candidate_ids=[new_c.id],
            target_candidate_id=orig_c.id,
            new_label="Host & Co-host Combined",
        ),
    )
    assert merged.label == "Host & Co-host Combined"
    assert merged.observation_count == len(active_obs)

    # 5. Confirm candidate into Character Library
    profile = service.confirm_candidate(
        character_env["project_id"],
        merged.id,
        ConfirmCandidateRequest(
            name="Alex Rivera",
            biography="Main host of tech discussions.",
            appearance_tags=["glasses", "dark shirt"],
        ),
    )
    assert profile.name == "Alex Rivera"
    assert profile.biography == "Main host of tech discussions."
    assert "glasses" in profile.appearance_tags
    assert profile.total_appearances == 1

    # Verify candidate marked as confirmed
    cands_after = service.get_candidates(character_env["project_id"])
    cand_dict = {c.id: c for c in cands_after}
    assert cand_dict[merged.id].review_status == "confirmed"
    assert cand_dict[merged.id].confirmed_character_id == profile.id


def test_character_library_and_export(character_env):
    """Test searching library, profile updates, and documented JSON export."""
    service = CharacterService(
        settings=character_env["settings"],
        db_path=character_env["db_path"],
    )

    # Extract & confirm
    cfg = ExtractionJobConfig(media_asset_id=character_env["media_asset_id"], sample_interval_sec=1.0)
    job = service.run_extraction_job(character_env["project_id"], cfg)
    cands = service.get_candidates(character_env["project_id"], job_id=job.id)

    prof = service.confirm_candidate(
        character_env["project_id"],
        cands[0].id,
        ConfirmCandidateRequest(name="Elena Rostova", biography="Guest speaker and engineer."),
    )

    # Search library
    results = service.get_library_profiles(character_env["project_id"], query="Elena")
    assert len(results) == 1
    assert results[0].name == "Elena Rostova"

    # Update profile
    updated = service.update_character_profile(
        character_env["project_id"],
        prof.id,
        UpdateProfileRequest(biography="Senior AI Researcher"),
    )
    assert updated.biography == "Senior AI Researcher"

    # Export JSON
    export_payload = service.export_character_json(character_env["project_id"], prof.id)
    assert export_payload.export_version == "2.0.0"
    assert export_payload.profile.name == "Elena Rostova"
    assert "disclaimer" in export_payload.model_dump()
    assert "biometric" in export_payload.disclaimer.lower()
    assert export_payload.screen_time_summary["total_appearances"] >= 1


def test_character_api_routes(character_env):
    """Test full HTTP REST API endpoints."""
    app = create_app(settings_override=character_env["settings"])

    with TestClient(app) as client:
        pid = character_env["project_id"]
        mid = character_env["media_asset_id"]

        # Run extraction
        resp = client.post(
            f"/api/v1/projects/{pid}/characters/extract",
            json={"media_asset_id": mid, "sample_interval_sec": 1.0},
        )
        assert resp.status_code == 200, resp.text
        job_data = resp.json()
        assert job_data["status"] == "completed"

        # List candidates
        resp = client.get(f"/api/v1/projects/{pid}/characters/candidates")
        assert resp.status_code == 200
        cands = resp.json()
        assert len(cands) >= 1
        cand_id = cands[0]["id"]

        # Rename
        resp = client.patch(
            f"/api/v1/projects/{pid}/characters/candidates/{cand_id}",
            json={"label": "Renamed Candidate"},
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "Renamed Candidate"

        # Confirm to library
        resp = client.post(
            f"/api/v1/projects/{pid}/characters/candidates/{cand_id}/confirm",
            json={"name": "Confirmed Star", "biography": "Hero of the show"},
        )
        assert resp.status_code == 200
        char_data = resp.json()
        char_id = char_data["id"]
        assert char_data["name"] == "Confirmed Star"

        # Query library
        resp = client.get(f"/api/v1/projects/{pid}/characters/library?query=Confirmed")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Export JSON
        resp = client.get(f"/api/v1/projects/{pid}/characters/library/{char_id}/export")
        assert resp.status_code == 200
        export_data = resp.json()
        assert export_data["export_version"] == "2.0.0"
        assert export_data["profile"]["name"] == "Confirmed Star"
