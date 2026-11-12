-- Migration 0014: Candidate Clip Edits, Trimming, and Aspect Ratio Framing State

CREATE TABLE IF NOT EXISTS candidate_clip_edits (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL UNIQUE,
    project_id TEXT NOT NULL,
    media_asset_id TEXT NOT NULL,
    original_start_time REAL NOT NULL,
    original_end_time REAL NOT NULL,
    edited_start_time REAL NOT NULL,
    edited_end_time REAL NOT NULL,
    edited_duration REAL NOT NULL,
    aspect_ratio TEXT NOT NULL DEFAULT '9:16',
    framing_mode TEXT NOT NULL DEFAULT 'center',
    manual_crop_x_pct REAL DEFAULT 50.0,
    manual_crop_y_pct REAL DEFAULT 50.0,
    manual_crop_zoom REAL DEFAULT 1.0,
    tracked_subject_id TEXT,
    tracking_status TEXT DEFAULT 'none',
    reframing_plan_id TEXT,
    version INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES shorts_candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (media_asset_id) REFERENCES media_assets(id) ON DELETE CASCADE,
    FOREIGN KEY (reframing_plan_id) REFERENCES reframing_plans(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_candidate_clip_edits_candidate ON candidate_clip_edits(candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidate_clip_edits_lookup ON candidate_clip_edits(project_id, media_asset_id);
