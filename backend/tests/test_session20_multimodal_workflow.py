"""Session 20 Authoritative Acceptance Tests: Multimodal Video Intelligence, Automatic Short Generation & Permanent Novelty Management."""

import json
import re
import sqlite3
import subprocess
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.core.config import Settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.main import create_app
from app.services.export_service import ExportService
from app.services.highlight_discovery import HighlightDiscoveryEngine
from app.services.jobs import JobOrchestrator


@pytest.fixture
def client(tmp_path) -> TestClient:
    real_migrations = Path(__file__).resolve().parent.parent / "migrations"
    settings = Settings(
        app_name="ZezEditSession20Test",
        storage_root=tmp_path / "storage",
        migrations_dir=real_migrations,
        environment="test",
        max_concurrent_jobs=2,
    )
    app = create_app(settings_override=settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_setup(client: TestClient):
    """Setup project, storage layout, media asset and synthetic video."""
    proj_res = client.post("/api/v1/projects", json={"name": "Session 20 Multimodal Project"})
    assert proj_res.status_code == 201
    pid = proj_res.json()["id"]

    layout = StorageLayout.from_root(client.app.state.settings.storage_root)
    db_path = layout.db_file
    asset_id = "med_session20_01"
    now_iso = "2026-11-15T10:00:00Z"

    # Generate 20-second synthetic test video
    synth_video = layout.media / "test_synth_video.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=20:size=320x240:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=20",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "64k",
            str(synth_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with sqlite_session(db_path) as conn:
        conn.execute(
            """
            INSERT INTO media_assets (
                id, project_id, original_filename, storage_path, media_type,
                file_size_bytes, duration_seconds, width, height, is_external,
                proxy_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id, pid, "Elephant Dance Highlight.mp4", str(synth_video), "video",
                synth_video.stat().st_size, 20.0, 320, 240, 0, "ready", now_iso, now_iso
            ),
        )

        # Seed completed analysis run with transcript segments, speech turns and scene cuts
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, project_id, media_asset_id, status, profile,
                progress_pct, current_stage, created_at, updated_at
            ) VALUES (?, ?, ?, 'completed', 'balanced', 100.0, 'completed', ?, ?)
            """,
            ("run_session20_01", pid, asset_id, now_iso, now_iso),
        )

        # Seed speech turns
        conn.execute(
            """
            INSERT INTO speech_turns (id, analysis_run_id, media_asset_id, start_time, end_time, speaker_label, text, turn_type, created_at)
            VALUES 
            ('t1', 'run_session20_01', ?, 0.5, 6.0, 'Host', 'Look at the funny elephant dance in the wild!', 'question', ?),
            ('t2', 'run_session20_01', ?, 6.5, 14.0, 'Guest', 'Everyone is laughing because the elephant makes incredible rhythmic movements!', 'exclamation', ?),
            ('t3', 'run_session20_01', ?, 14.5, 19.5, 'Host', 'This is truly the highlight moment of the year!', 'statement', ?)
            """,
            (asset_id, now_iso, asset_id, now_iso, asset_id, now_iso),
        )

        # Seed transcript segments
        conn.execute(
            """
            INSERT INTO transcript_segments (
                id, analysis_run_id, media_asset_id, start_time, end_time,
                text, language, confidence, words_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'en', ?, ?, ?)
            """,
            (
                "seg_01", "run_session20_01", asset_id, 0.5, 6.0,
                "Look at the funny elephant dance in the wild!", 0.95, "[]", now_iso
            ),
        )
        conn.execute(
            """
            INSERT INTO transcript_segments (
                id, analysis_run_id, media_asset_id, start_time, end_time,
                text, language, confidence, words_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'en', ?, ?, ?)
            """,
            (
                "seg_02", "run_session20_01", asset_id, 6.5, 14.0,
                "Everyone is laughing because the elephant makes incredible rhythmic movements!", 0.95, "[]", now_iso
            ),
        )
        conn.execute(
            """
            INSERT INTO transcript_segments (
                id, analysis_run_id, media_asset_id, start_time, end_time,
                text, language, confidence, words_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'en', ?, ?, ?)
            """,
            (
                "seg_03", "run_session20_01", asset_id, 14.5, 19.5,
                "This is truly the highlight moment of the year!", 0.95, "[]", now_iso
            ),
        )

        # Seed scene cuts
        conn.execute(
            """
            INSERT INTO video_scenes (
                id, analysis_run_id, media_asset_id, scene_index, start_time, end_time,
                representative_timestamp, change_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0.8, ?)
            """,
            ("scene_01", "run_session20_01", asset_id, 0, 0.0, 7.0, 3.5, now_iso),
        )
        conn.execute(
            """
            INSERT INTO video_scenes (
                id, analysis_run_id, media_asset_id, scene_index, start_time, end_time,
                representative_timestamp, change_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0.8, ?)
            """,
            ("scene_02", "run_session20_01", asset_id, 1, 7.0, 20.0, 13.0, now_iso),
        )

    return {
        "pid": pid,
        "asset_id": asset_id,
        "synth_video": synth_video,
        "layout": layout,
        "db_path": db_path,
    }


def test_automatic_shorts_generation_enqueues_export_render(client: TestClient, test_setup):
    """Verify that highlight discovery automatically enqueues export render jobs when auto_render=True."""
    pid = test_setup["pid"]
    asset_id = test_setup["asset_id"]
    db_path = test_setup["db_path"]

    payload = {
        "analysis_run_id": "run_session20_01",
        "creative_direction": "best_overall",
        "aspect_ratio": "9:16",
        "target_clip_count": 2,
        "min_duration": 5.0,
        "max_duration": 18.0,
        "auto_render": True,
        "run_synchronously": True,
    }

    res = client.post(f"/api/v1/projects/{pid}/media/{asset_id}/highlights/discover", json=payload)
    assert res.status_code == 202
    candidates = res.json()
    assert len(candidates) > 0

    # Verify that exports and export_render jobs were automatically enqueued in SQLite
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        exports = conn.execute(
            "SELECT * FROM exports WHERE project_id = ? AND media_asset_id = ?",
            (pid, asset_id),
        ).fetchall()
        assert len(exports) == len(candidates)

        for exp in exports:
            assert exp["status"] in ("queued", "rendering", "completed")
            assert exp["target_aspect_ratio"] == "9:16"
            assert exp["export_preset"] == "shorts_reels_9_16"

        jobs = conn.execute(
            "SELECT * FROM jobs WHERE project_id = ? AND job_type = 'export_render'",
            (pid,),
        ).fetchall()
        assert len(jobs) == len(candidates)


def test_export_deletion_preserves_candidate_script_and_novelty_ledger(client: TestClient, test_setup):
    """Verify that deleting a rendered MP4 export preserves the source video, the script, and the novelty ledger."""
    pid = test_setup["pid"]
    asset_id = test_setup["asset_id"]
    db_path = test_setup["db_path"]
    layout = test_setup["layout"]

    # 1. Discover candidates and auto-render
    res = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/highlights/discover",
        json={
            "analysis_run_id": "run_session20_01",
            "target_clip_count": 1,
            "min_duration": 5.0,
            "max_duration": 18.0,
            "auto_render": True,
            "run_synchronously": True,
        },
    )
    assert res.status_code == 202
    cands = res.json()
    assert len(cands) >= 1
    cand_id = cands[0]["id"]

    # 2. Get enqueued export
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        exp = conn.execute(
            "SELECT * FROM exports WHERE candidate_id = ? AND project_id = ?",
            (cand_id, pid),
        ).fetchone()
        assert exp is not None
        exp_id = exp["id"]

    # Execute render synchronously to produce the actual MP4 file
    export_svc = ExportService(settings=client.app.state.settings, db_path=db_path)
    render_res = export_svc.execute_render_job(exp["render_job_id"])
    assert render_res["status"] == "completed"
    out_file = Path(render_res["output_path"])
    assert out_file.exists()

    # 3. Delete the export via API
    del_res = client.delete(f"/api/v1/projects/{pid}/exports/{exp_id}")
    assert del_res.status_code == 200

    # 4. Verify physical export file is unlinked
    assert not out_file.exists()

    # 5. Verify source video is strictly preserved
    assert test_setup["synth_video"].exists()

    # 6. Verify candidate script is strictly preserved in shorts_candidates
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cand_row = conn.execute(
            "SELECT * FROM shorts_candidates WHERE id = ? AND project_id = ?",
            (cand_id, pid),
        ).fetchone()
        assert cand_row is not None
        assert cand_row["id"] == cand_id

        # 7. Verify novelty ledger interval is preserved in media_generated_clips_history
        hist_rows = conn.execute(
            "SELECT * FROM media_generated_clips_history WHERE candidate_id = ?",
            (cand_id,),
        ).fetchall()
        assert len(hist_rows) == 1
        assert hist_rows[0]["start_time"] == cand_row["start_time"]


def test_candidate_script_deletion_and_re_rendering(client: TestClient, test_setup):
    """Verify that deleting a script removes the candidate record, and re-rendering from script works."""
    pid = test_setup["pid"]
    asset_id = test_setup["asset_id"]
    db_path = test_setup["db_path"]

    # 1. Discover a candidate
    res = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/highlights/discover",
        json={
            "analysis_run_id": "run_session20_01",
            "target_clip_count": 1,
            "min_duration": 5.0,
            "max_duration": 18.0,
            "auto_render": False,
            "run_synchronously": True,
        },
    )
    assert res.status_code == 202
    cands = res.json()
    assert len(cands) >= 1
    cand_id = cands[0]["id"]

    # 2. Re-render from script via single render endpoint
    render_sub = client.post(
        f"/api/v1/projects/{pid}/exports/render?run_synchronously=true",
        json={
            "candidate_id": cand_id,
            "preset_id": "shorts_reels_9_16",
        },
    )
    assert render_sub.status_code == 200
    rdata = render_sub.json()
    assert rdata["status"] == "completed" or "export_id" in rdata

    # 3. Delete candidate script via DELETE /highlights/{id}
    del_script_res = client.delete(f"/api/v1/projects/{pid}/highlights/{cand_id}")
    assert del_script_res.status_code == 200
    assert del_script_res.json()["status"] == "deleted"

    # Verify script is removed from shorts_candidates
    with sqlite_session(db_path) as conn:
        cand_check = conn.execute(
            "SELECT id FROM shorts_candidates WHERE id = ?",
            (cand_id,),
        ).fetchone()
        assert cand_check is None

        # Verify novelty ledger still holds the historical interval
        hist_check = conn.execute(
            "SELECT id FROM media_generated_clips_history WHERE candidate_id = ?",
            (cand_id,),
        ).fetchone()
        assert hist_check is not None


def test_download_filename_derived_from_content_title(client: TestClient, test_setup):
    """Verify GET /exports/{id}/download attaches Content-Disposition with sanitized content-derived title."""
    pid = test_setup["pid"]
    asset_id = test_setup["asset_id"]
    db_path = test_setup["db_path"]

    # Discover candidate
    res = client.post(
        f"/api/v1/projects/{pid}/media/{asset_id}/highlights/discover",
        json={
            "analysis_run_id": "run_session20_01",
            "target_clip_count": 1,
            "min_duration": 5.0,
            "max_duration": 18.0,
            "auto_render": True,
            "run_synchronously": True,
        },
    )
    cands = res.json()
    assert len(cands) >= 1
    cand = cands[0]

    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        exp = conn.execute(
            "SELECT * FROM exports WHERE candidate_id = ?",
            (cand["id"],),
        ).fetchone()
        assert exp is not None

    export_svc = ExportService(settings=client.app.state.settings, db_path=db_path)
    export_svc.execute_render_job(exp["render_job_id"])

    # Download endpoint
    dl_res = client.get(f"/api/v1/projects/{pid}/exports/{exp['id']}/download")
    assert dl_res.status_code == 200
    cd_header = dl_res.headers.get("content-disposition", "")
    assert "attachment" in cd_header
    assert 'filename="' in cd_header
    assert cd_header.endswith('.mp4"')
    # Filename should not contain raw illegal chars or path characters
    assert "/" not in cd_header.split('filename="')[1]
    assert "\\" not in cd_header.split('filename="')[1]
