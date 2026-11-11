-- ZezEdit 2.0 Milestone 9 Schema Migration: AI Video Editor, Multi-Track Timeline & Non-Destructive Editing

-- 1. Timelines
CREATE TABLE IF NOT EXISTS timelines (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT 'Main Sequence',
    duration REAL NOT NULL DEFAULT 0.0,
    fps INTEGER NOT NULL DEFAULT 30,
    canvas_width INTEGER NOT NULL DEFAULT 1080,
    canvas_height INTEGER NOT NULL DEFAULT 1920,
    time_base TEXT NOT NULL DEFAULT '1/30',
    revision INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_timelines_project
    ON timelines (project_id, is_active);

-- 2. Timeline Tracks
CREATE TABLE IF NOT EXISTS timeline_tracks (
    id TEXT PRIMARY KEY,
    timeline_id TEXT NOT NULL REFERENCES timelines(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    track_type TEXT NOT NULL, -- 'video', 'audio', 'overlay'
    track_subtype TEXT NOT NULL DEFAULT 'main_video', -- 'main_video', 'secondary_video', 'b_roll', 'source_audio', 'bgm', 'voiceover', 'sfx', 'text', 'caption', 'graphics'
    track_order INTEGER NOT NULL DEFAULT 0,
    is_visible BOOLEAN NOT NULL DEFAULT 1,
    is_muted BOOLEAN NOT NULL DEFAULT 0,
    is_locked BOOLEAN NOT NULL DEFAULT 0,
    height INTEGER NOT NULL DEFAULT 64,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tracks_timeline
    ON timeline_tracks (timeline_id, track_order ASC);

-- 3. Timeline Clips
CREATE TABLE IF NOT EXISTS timeline_clips (
    id TEXT PRIMARY KEY,
    timeline_id TEXT NOT NULL REFERENCES timelines(id) ON DELETE CASCADE,
    track_id TEXT NOT NULL REFERENCES timeline_tracks(id) ON DELETE CASCADE,
    source_media_id TEXT REFERENCES media_assets(id) ON DELETE SET NULL,
    clip_type TEXT NOT NULL DEFAULT 'video', -- 'video', 'audio', 'text', 'overlay', 'caption'
    name TEXT NOT NULL,
    timeline_start REAL NOT NULL,
    timeline_end REAL NOT NULL,
    source_in REAL NOT NULL DEFAULT 0.0,
    source_out REAL NOT NULL DEFAULT 0.0,
    speed REAL NOT NULL DEFAULT 1.0,
    volume REAL NOT NULL DEFAULT 1.0,
    opacity REAL NOT NULL DEFAULT 1.0,
    transform_props TEXT NOT NULL DEFAULT '{}',
    content_props TEXT NOT NULL DEFAULT '{}',
    audio_props TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clips_timeline
    ON timeline_clips (timeline_id, timeline_start ASC);

CREATE INDEX IF NOT EXISTS idx_clips_track
    ON timeline_clips (track_id, timeline_start ASC);

-- 4. Timeline Editing Commands (Persistent Reversible History)
CREATE TABLE IF NOT EXISTS timeline_commands (
    id TEXT PRIMARY KEY,
    timeline_id TEXT NOT NULL REFERENCES timelines(id) ON DELETE CASCADE,
    command_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    inverse_payload TEXT NOT NULL,
    revision_before INTEGER NOT NULL,
    revision_after INTEGER NOT NULL,
    description TEXT NOT NULL,
    executed_by TEXT NOT NULL DEFAULT 'user', -- 'user' or 'ai'
    is_undone BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_timeline_commands
    ON timeline_commands (timeline_id, revision_after ASC);

-- 5. AI Assistant Conversations
CREATE TABLE IF NOT EXISTS ai_conversations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    timeline_id TEXT NOT NULL REFERENCES timelines(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Editing Assistant',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_conversations
    ON ai_conversations (project_id, timeline_id);

-- 6. AI Editing Plans
CREATE TABLE IF NOT EXISTS ai_editing_plans (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    target_revision INTEGER NOT NULL,
    user_instruction TEXT NOT NULL,
    explanation TEXT NOT NULL,
    operations TEXT NOT NULL, -- JSON list of command instructions
    warnings TEXT NOT NULL DEFAULT '[]', -- JSON list of warnings
    status TEXT NOT NULL DEFAULT 'proposed', -- 'proposed', 'approved', 'rejected', 'executed', 'failed'
    created_at TEXT NOT NULL,
    executed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_plans
    ON ai_editing_plans (timeline_id, status);

-- 7. AI Messages
CREATE TABLE IF NOT EXISTS ai_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    context_snapshot TEXT NOT NULL DEFAULT '{}',
    plan_id TEXT REFERENCES ai_editing_plans(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_messages
    ON ai_messages (conversation_id, created_at ASC);
