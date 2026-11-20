-- Migration 0022: Video Analysis Foundation, Canonical Media Linkage & Indexes
ALTER TABLE analysis_runs ADD COLUMN stored_file_id TEXT REFERENCES stored_media_files(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_analysis_runs_stored_file_id ON analysis_runs(stored_file_id);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_status_sig ON analysis_runs(media_asset_id, status, source_signature);
