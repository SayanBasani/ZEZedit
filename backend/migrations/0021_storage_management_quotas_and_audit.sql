-- Migration 0021: Storage Management, Quotas, Safe Cleanup and Audit Logging (P1.9)

-- Table: storage_quotas
-- Persistent configuration for overall, category, and temporary storage limits and auto-prune policies.
CREATE TABLE IF NOT EXISTS storage_quotas (
    id TEXT PRIMARY KEY,
    storage_limit_bytes INTEGER,               -- NULL indicates unlimited
    generated_video_limit_bytes INTEGER,       -- NULL indicates unlimited
    temp_storage_limit_bytes INTEGER,          -- NULL indicates unlimited
    warning_threshold_percent INTEGER NOT NULL DEFAULT 85,
    auto_prune_enabled INTEGER NOT NULL DEFAULT 0,  -- 0 = Disabled by default for user safety
    auto_prune_retention_hours INTEGER NOT NULL DEFAULT 24,
    auto_prune_categories_json TEXT NOT NULL DEFAULT '["orphaned_uploads", "abandoned_ffmpeg", "failed_renders", "expired_temp_files"]',
    max_temp_storage_bytes INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Seed default singleton quota policy if not present
INSERT OR IGNORE INTO storage_quotas (
    id,
    storage_limit_bytes,
    generated_video_limit_bytes,
    temp_storage_limit_bytes,
    warning_threshold_percent,
    auto_prune_enabled,
    auto_prune_retention_hours,
    auto_prune_categories_json,
    max_temp_storage_bytes,
    created_at,
    updated_at
) VALUES (
    'default',
    NULL,
    NULL,
    NULL,
    85,
    0,
    24,
    '["orphaned_uploads", "abandoned_ffmpeg", "failed_renders", "expired_temp_files"]',
    NULL,
    datetime('now'),
    datetime('now')
);

-- Table: storage_cleanup_audits
-- Persistent audit log recording every cleanup, manual wipe, and automatic pruning operation.
CREATE TABLE IF NOT EXISTS storage_cleanup_audits (
    id TEXT PRIMARY KEY,
    operation_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    cleanup_category TEXT NOT NULL,
    files_examined INTEGER NOT NULL DEFAULT 0,
    files_deleted INTEGER NOT NULL DEFAULT 0,
    files_skipped INTEGER NOT NULL DEFAULT 0,
    bytes_reclaimed INTEGER NOT NULL DEFAULT 0,
    is_automatic INTEGER NOT NULL DEFAULT 0,
    failure_reasons_json TEXT DEFAULT '[]',
    details_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_storage_cleanup_audits_op_id ON storage_cleanup_audits(operation_id);
CREATE INDEX IF NOT EXISTS idx_storage_cleanup_audits_timestamp ON storage_cleanup_audits(timestamp);
CREATE INDEX IF NOT EXISTS idx_storage_cleanup_audits_category ON storage_cleanup_audits(cleanup_category);
