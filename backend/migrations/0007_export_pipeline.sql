-- ZezEdit 2.0 Milestone 8 Schema Migration: Rendering Engine, Export Pipeline & Automatic Shorts Generation

CREATE TABLE IF NOT EXISTS exports (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    candidate_id TEXT REFERENCES shorts_candidates(id) ON DELETE SET NULL,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    reframing_plan_id TEXT REFERENCES reframing_plans(id) ON DELETE SET NULL,
    framing_revision_id TEXT REFERENCES reframing_revisions(id) ON DELETE SET NULL,
    render_job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    export_preset TEXT NOT NULL DEFAULT 'shorts_reels_9_16', -- 'shorts_reels_9_16', 'landscape_16_9', 'square_1_1', 'custom'
    target_aspect_ratio TEXT NOT NULL DEFAULT '9:16',
    target_width INTEGER NOT NULL DEFAULT 1080,
    target_height INTEGER NOT NULL DEFAULT 1920,
    video_codec TEXT NOT NULL DEFAULT 'libx264',
    audio_codec TEXT NOT NULL DEFAULT 'aac',
    pixel_fmt TEXT NOT NULL DEFAULT 'yuv420p',
    fps REAL NOT NULL DEFAULT 30.0,
    crf INTEGER NOT NULL DEFAULT 22,
    video_bitrate TEXT,
    audio_bitrate TEXT NOT NULL DEFAULT '128k',
    caption_config_json TEXT NOT NULL DEFAULT '{}',
    audio_config_json TEXT NOT NULL DEFAULT '{}',
    output_path TEXT,
    output_filename TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'queued', -- 'queued', 'rendering', 'completed', 'failed', 'cancelled'
    validation_status TEXT NOT NULL DEFAULT 'unvalidated', -- 'unvalidated', 'valid', 'invalid'
    validation_details_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_exports_project
    ON exports (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_exports_candidate
    ON exports (candidate_id);

CREATE INDEX IF NOT EXISTS idx_exports_job
    ON exports (render_job_id);

CREATE INDEX IF NOT EXISTS idx_exports_status
    ON exports (project_id, status);
