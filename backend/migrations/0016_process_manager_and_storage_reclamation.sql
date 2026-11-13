-- Forward-only migration 0016: Process Manager & Storage Reclamation
-- Adds media_asset_id and parent_job_id to jobs table for central process tracking and retry lineage

ALTER TABLE jobs ADD COLUMN media_asset_id TEXT;
ALTER TABLE jobs ADD COLUMN parent_job_id TEXT;

CREATE INDEX IF NOT EXISTS idx_jobs_media_asset ON jobs(media_asset_id);
CREATE INDEX IF NOT EXISTS idx_jobs_parent_job ON jobs(parent_job_id);
