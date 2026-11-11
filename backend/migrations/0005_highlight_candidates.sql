-- ZezEdit 2.0 Milestone 6 Schema Migration: AI Highlight Discovery & Shorts Candidates

CREATE TABLE IF NOT EXISTS shorts_candidates (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    analysis_run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    suggested_start_time REAL NOT NULL,
    suggested_end_time REAL NOT NULL,
    is_user_modified INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    suggested_title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'Conversation',
    secondary_categories_json TEXT NOT NULL DEFAULT '[]',
    quality_score REAL NOT NULL DEFAULT 0.0,
    score_breakdown_json TEXT NOT NULL DEFAULT '{}',
    gate_results_json TEXT NOT NULL DEFAULT '{}',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    missing_evidence_json TEXT NOT NULL DEFAULT '[]',
    review_status TEXT NOT NULL DEFAULT 'recommended', -- recommended, needs_review, approved, rejected
    rejection_reason TEXT,
    transcript_references_json TEXT NOT NULL DEFAULT '[]',
    scene_references_json TEXT NOT NULL DEFAULT '[]',
    visual_evidence_json TEXT NOT NULL DEFAULT '[]',
    audio_evidence_json TEXT NOT NULL DEFAULT '[]',
    ai_explanation_json TEXT NOT NULL DEFAULT '{}',
    alternative_of_candidate_id TEXT REFERENCES shorts_candidates(id) ON DELETE SET NULL,
    overlap_group_id TEXT,
    scoring_version TEXT NOT NULL DEFAULT '2.0.0-m6',
    queued_for_render INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_candidates_project_review
    ON shorts_candidates (project_id, review_status, quality_score DESC);

CREATE INDEX IF NOT EXISTS idx_candidates_media
    ON shorts_candidates (media_asset_id, quality_score DESC);

CREATE INDEX IF NOT EXISTS idx_candidates_time
    ON shorts_candidates (media_asset_id, start_time, end_time);
