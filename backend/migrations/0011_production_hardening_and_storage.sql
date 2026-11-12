-- Migration 0011: Production Hardening, Checkpointing & Storage
ALTER TABLE jobs ADD COLUMN checkpoint_data_json TEXT DEFAULT NULL;
ALTER TABLE media_assets ADD COLUMN integrity_details_json TEXT DEFAULT NULL;
ALTER TABLE media_assets ADD COLUMN last_integrity_check TEXT DEFAULT NULL;

-- Index for job priority and status scheduling
CREATE INDEX IF NOT EXISTS idx_jobs_status_priority ON jobs(status, priority DESC, created_at ASC);
-- Index for media asset availability checks
CREATE INDEX IF NOT EXISTS idx_media_assets_availability ON media_assets(project_id, availability_status);
