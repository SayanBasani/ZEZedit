-- Migration 0023: Multimodal Highlight Discovery & Candidate Ranking Foundation
-- Adds ranking position, evidence coverage, signal scores, and generation reason to shorts_candidates
-- Adds configurable scoring weights, score threshold, and minimum separation to candidate_generation_runs

-- Add columns to shorts_candidates
ALTER TABLE shorts_candidates ADD COLUMN rank_position INTEGER DEFAULT NULL;
ALTER TABLE shorts_candidates ADD COLUMN evidence_coverage REAL NOT NULL DEFAULT 1.0;
ALTER TABLE shorts_candidates ADD COLUMN signal_scores_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE shorts_candidates ADD COLUMN generation_reason TEXT DEFAULT NULL;
ALTER TABLE shorts_candidates ADD COLUMN transcript_excerpt TEXT DEFAULT NULL;

-- Add columns to candidate_generation_runs
ALTER TABLE candidate_generation_runs ADD COLUMN score_weights_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE candidate_generation_runs ADD COLUMN min_score REAL DEFAULT 0.0;
ALTER TABLE candidate_generation_runs ADD COLUMN min_separation_seconds REAL DEFAULT 0.0;
ALTER TABLE candidate_generation_runs ADD COLUMN source_signature TEXT DEFAULT NULL;

-- Create performance indexes for candidate ranking and discovery lookups
CREATE INDEX IF NOT EXISTS idx_shorts_candidates_asset_rank ON shorts_candidates(media_asset_id, rank_position);
CREATE INDEX IF NOT EXISTS idx_shorts_candidates_gen_run_rank ON shorts_candidates(generation_run_id, rank_position);
CREATE INDEX IF NOT EXISTS idx_candidate_gen_runs_asset_status ON candidate_generation_runs(media_asset_id, status);

-- Backfill rank_position for existing candidates based on quality_score descending per generation_run_id
UPDATE shorts_candidates
SET rank_position = (
    SELECT COUNT(*)
    FROM shorts_candidates c2
    WHERE c2.generation_run_id = shorts_candidates.generation_run_id
      AND (c2.quality_score > shorts_candidates.quality_score
           OR (c2.quality_score = shorts_candidates.quality_score AND c2.id <= shorts_candidates.id))
)
WHERE rank_position IS NULL AND generation_run_id IS NOT NULL;
