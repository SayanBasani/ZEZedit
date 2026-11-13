-- Migration 0015: Reusable Intelligence and Generate More Shorts

ALTER TABLE candidate_generation_runs ADD COLUMN generation_type TEXT NOT NULL DEFAULT 'initial';
ALTER TABLE candidate_generation_runs ADD COLUMN reused_analysis_run_id TEXT;
ALTER TABLE candidate_generation_runs ADD COLUMN duration_preference TEXT NOT NULL DEFAULT 'ai_best';
ALTER TABLE candidate_generation_runs ADD COLUMN is_novelty_exhausted INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_cand_gen_runs_type ON candidate_generation_runs(media_asset_id, generation_type);
