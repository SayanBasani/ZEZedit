-- Migration 0012: Unified Full-Video Analysis Pipeline, Job Linkage & Caching Telemetry
ALTER TABLE analysis_runs ADD COLUMN job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL;
ALTER TABLE analysis_runs ADD COLUMN source_signature TEXT DEFAULT NULL;
ALTER TABLE analysis_runs ADD COLUMN stage_details_json TEXT DEFAULT '{}';
ALTER TABLE analysis_runs ADD COLUMN checkpoint_data_json TEXT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_analysis_runs_job_id ON analysis_runs(job_id);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_signature ON analysis_runs(media_asset_id, source_signature);
