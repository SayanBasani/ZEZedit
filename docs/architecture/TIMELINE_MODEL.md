# ZezEdit 2.0 — Shared Timeline Data Model & API Architecture

> **Milestone 9 Implementation Status:** Fully implemented and verified. Both manual editing and the AI Video Editor assistant operate on this exact unified model with transactional persistence, persistent undo/redo history, and direct integration with the Milestone 8 rendering engine.

---

## 1. Core Architectural Rule: One Shared Document Model

ZezEdit enforces complete architectural unification between manual editing and AI assistance:
- Both manual UI interactions (split, trim, move, delete, duplicate, add text) and AI-generated editing instructions compile into the exact same command layer (`TimelineCommandService`).
- All changes are recorded in the SQLite database with forward `payload` and reversible `inverse_payload` data.
- The timeline can be rendered at any revision into finished playable videos using `TimelineRenderer` backed by the existing Milestone 8 FFmpeg engine.

---

## 2. Canonical Data Models

### 1. `timelines` Table
```sql
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
```

### 2. `timeline_tracks` Table
```sql
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
```

### 3. `timeline_clips` Table
```sql
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
```

---

## 3. Persistent Reversible Command System (Undo / Redo)

Every timeline modification executes through `TimelineCommandService`:
- `InsertClip`: Adds clip, records inverse `DeleteClip`.
- `MoveClip`: Updates timeline bounds, records inverse `MoveClip` to previous position.
- `TrimClip`: Adjusts in/out points, records previous boundaries.
- `SplitClip`: Splits clip at playhead time into two adjacent clips, records inverse merge.
- `DeleteClip`: Removes clip, stashes all attributes in `inverse_payload` for perfect restoration.
- `DuplicateClip`: Clones clip immediately adjacent, records inverse removal.
- `UpdateClipProps`: Modifies volume, speed, transform, or content properties with prior state snapshot.
- `AddTextOverlay`: Creates high-visibility text overlay on overlay track.

### Undo & Redo Lifecycle:
1. `undo()`: Queries `SELECT * FROM timeline_commands WHERE timeline_id = ? AND is_undone = 0 ORDER BY revision_after DESC LIMIT 1`, applies `inverse_payload`, sets `is_undone = 1`, and updates revision.
2. `redo()`: Queries `SELECT * FROM timeline_commands WHERE timeline_id = ? AND is_undone = 1 ORDER BY revision_after ASC LIMIT 1`, reapplies `payload`, sets `is_undone = 0`, and updates revision.
3. Because history is recorded in `timeline_commands`, **Undo/Redo survives application crashes and restarts**.

---

## 4. AI Video Editor Assistant Architecture

The AI Editor assistant operates under strict safety boundaries:
1. **Context Aggregator**: Gathers project media, transcripts (Whisper tokens), scenes, highlight candidates, timeline tracks, clips, playhead time, and selected clip ID.
2. **Deterministic & Semantic Reasoner**: Answers informational queries (e.g. "What is happening at 2 minutes?", "Find highlight candidates") or creates an `AIEditingPlan`.
3. **Structured Plan Structure**:
   - `plan_id`: Unique identifier.
   - `user_instruction`: Raw prompt.
   - `target_revision`: Sequence revision when plan was generated.
   - `explanation`: Plain English explanation of proposed edits.
   - `operations`: Array of validated editing commands.
   - `warnings`: Explanations of destructive actions or timing changes.
   - `status`: `'proposed' | 'approved' | 'rejected' | 'executed' | 'failed'`.
4. **Approval Gate**: The user reviews the plan and clicks **Approve & Execute** or **Reject**. The assistant *never* executes edits silently.
5. **Safe Execution**: All approved operations are piped directly through `TimelineCommandService`.

---

## 5. Timeline Rendering Integration (FFmpeg Filtergraph)

The timeline renders into finished video via `TimelineRenderer`:
- Layers visual tracks from lowest `track_order` (base video) to highest (B-roll, overlays, text).
- Trims source clips with `trim=start=...:duration=...` and delays/overlays at `timeline_start`.
- Compiles text overlays into libass subtitle tracks (`ass=filename=overlay.ass`), guaranteeing 100% stability across Windows environments without freetype font crashes.
- Mixes audio streams with `amix=inputs=N:normalize=0` and applies EBU R128 loudness normalization (`loudnorm=I=-14:TP=-1.5:LRA=11`).
- Validates the resulting MP4 container using Milestone 8's `OutputValidator` before publishing to `storage/exports/{project_id}/`.
