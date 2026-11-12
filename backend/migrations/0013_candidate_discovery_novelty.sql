-- Migration 0013: Candidate Generation Runs, Persistent Novelty Ledger & Natural Boundaries

CREATE TABLE IF NOT EXISTS candidate_generation_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    creative_direction TEXT NOT NULL DEFAULT 'best_overall',
    aspect_ratio TEXT NOT NULL DEFAULT '9:16',
    requested_count INTEGER NOT NULL DEFAULT 10,
    min_duration REAL NOT NULL DEFAULT 12.0,
    max_duration REAL NOT NULL DEFAULT 60.0,
    status TEXT NOT NULL DEFAULT 'completed',
    candidates_discovered INTEGER NOT NULL DEFAULT 0,
    candidates_selected INTEGER NOT NULL DEFAULT 0,
    candidates_rejected INTEGER NOT NULL DEFAULT 0,
    novelty_exclusions INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cand_gen_runs_asset ON candidate_generation_runs(media_asset_id, created_at);
CREATE INDEX IF NOT EXISTS idx_cand_gen_runs_proj ON candidate_generation_runs(project_id, created_at);

CREATE TABLE IF NOT EXISTS media_generated_clips_history (
    id TEXT PRIMARY KEY,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    generation_run_id TEXT NOT NULL REFERENCES candidate_generation_runs(id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    creative_direction TEXT NOT NULL,
    aspect_ratio TEXT NOT NULL,
    score REAL NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clip_history_asset ON media_generated_clips_history(media_asset_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_clip_history_run ON media_generated_clips_history(generation_run_id);

ALTER TABLE shorts_candidates ADD COLUMN generation_run_id TEXT;
ALTER TABLE shorts_candidates ADD COLUMN creative_direction TEXT DEFAULT 'best_overall';
ALTER TABLE shorts_candidates ADD COLUMN natural_boundary_confidence REAL DEFAULT 1.0;

CREATE INDEX IF NOT EXISTS idx_shorts_candidates_gen_run ON shorts_candidates(generation_run_id);
