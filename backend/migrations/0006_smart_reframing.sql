-- ZezEdit 2.0 Milestone 7 Schema Migration: Smart Reframing & Subject Tracking

CREATE TABLE IF NOT EXISTS reframing_plans (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    candidate_id TEXT REFERENCES shorts_candidates(id) ON DELETE SET NULL,
    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    target_aspect_ratio TEXT NOT NULL DEFAULT '9:16', -- '9:16', '1:1', '16:9'
    framing_strategy TEXT NOT NULL DEFAULT 'single_subject', -- 'single_subject', 'two_person', 'group', 'action_object', 'fallback'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'tracking', 'completed', 'failed'
    source_width INTEGER NOT NULL,
    source_height INTEGER NOT NULL,
    output_width INTEGER NOT NULL DEFAULT 1080,
    output_height INTEGER NOT NULL DEFAULT 1920,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    base_zoom REAL NOT NULL DEFAULT 1.0,
    headroom_factor REAL NOT NULL DEFAULT 0.15,
    smoothing_window_seconds REAL NOT NULL DEFAULT 0.8,
    keyframes_json TEXT NOT NULL DEFAULT '[]',
    detected_tracks_json TEXT NOT NULL DEFAULT '[]',
    scene_cuts_json TEXT NOT NULL DEFAULT '[]',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    active_revision_id TEXT,
    calculation_version TEXT NOT NULL DEFAULT '2.0.0-m7',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reframing_revisions (
    id TEXT PRIMARY KEY,
    reframing_plan_id TEXT NOT NULL REFERENCES reframing_plans(id) ON DELETE CASCADE,
    revision_number INTEGER NOT NULL DEFAULT 1,
    label TEXT NOT NULL,
    is_ai_generated INTEGER NOT NULL DEFAULT 1,
    manual_overrides_json TEXT NOT NULL DEFAULT '[]',
    effective_keyframes_json TEXT NOT NULL DEFAULT '[]',
    render_job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    rendered_video_path TEXT,
    rendered_duration REAL,
    rendered_file_size_bytes INTEGER,
    rendered_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reframing_project
    ON reframing_plans (project_id, candidate_id);

CREATE INDEX IF NOT EXISTS idx_reframing_media
    ON reframing_plans (media_asset_id, start_time, end_time);

CREATE INDEX IF NOT EXISTS idx_reframing_revisions
    ON reframing_revisions (reframing_plan_id, revision_number DESC);
