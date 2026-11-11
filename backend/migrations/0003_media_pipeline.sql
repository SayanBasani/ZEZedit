-- ZezEdit 2.0 Milestone 4 Schema Migration: Media Pipeline & Proxy Enhancements

ALTER TABLE media_assets ADD COLUMN proxy_status TEXT NOT NULL DEFAULT 'none';

CREATE INDEX IF NOT EXISTS idx_media_assets_proxy_status
    ON media_assets (project_id, proxy_status);
