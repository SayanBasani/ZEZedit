# ZezEdit 2.0 — Shared Timeline Data Model & API Boundaries

> **Milestone 1 Status Note:** Per Milestone 1 scope boundaries, the Timeline Editor runtime and UI are **NOT implemented yet** (scheduled for Milestone 7). This document establishes the authoritative data contract and API boundaries so both the manual Timeline UI and the AI Video Editor (`Module G`) operate on one unified sequence model.

---

## 1. Core Architectural Rule: One Shared Document Model

ZezEdit separates timeline editing from destructive video encoding. A Timeline Sequence is a declarative, versioned JSON document stored alongside SQLite revision history. Manual NLE actions (`move`, `trim`, `split`) and AI-generated edit plans mutate this exact same document schema via validated atomic operations.

---

## 2. Canonical Data Model (`TimelineDocument`)

```json
{
  "schema_version": 1,
  "sequence_id": "seq_01J...",
  "project_id": "proj_01J...",
  "source_kind": "project_master | rendered_short",
  "source_ref_id": "asset_or_short_id",
  "title": "Main Edit v1",
  "fps": 30.0,
  "width": 1080,
  "height": 1920,
  "aspect_ratio": "9:16",
  "duration_sec": 42.5,
  "playhead_sec": 0.0,
  "snap_enabled": true,
  "zoom_px_per_sec": 60.0,
  "tracks": [
    {
      "id": "trk_v1",
      "kind": "video",
      "name": "Video 1",
      "order": 0,
      "visible": true,
      "locked": false,
      "muted": false,
      "solo": false,
      "clips": []
    }
  ]
}
```

### Track Kinds Supported
1. `video` — Primary & B-roll video segments, frame transforms (`scale`, `pos_x`, `pos_y`), crop/reframing reference, playback speed (`rate`), fade in/out.
2. `audio` — Linked clip audio or standalone music/SFX tracks (`volume_db`, `mute`, `ducking_enabled`, `fade_in_sec`, `fade_out_sec`).
3. `overlay` — Picture-in-picture, stickers, logos (`opacity`, `blend_mode`, `x`, `y`, `width`, `height`, `z_index`).
4. `text` — Titles & animated captions (`text`, `style_preset`, `font_family`, `font_size`, `color`, `position_y_pct`, `highlight_active_word`).

### Canonical Clip Schema (`TimelineClip`)
Every clip on any track shares core timing fields:
- `id`: Unique clip ID (`clip_...`)
- `track_id`: Parent track ID
- `media_asset_id`: Reference to `media_assets.id` (or `null` for generated `text` clips)
- `timeline_start_sec`: Position on sequence timeline (`>= 0.0`)
- `timeline_end_sec`: End position on sequence timeline (`> timeline_start_sec`)
- `source_in_sec`: Offset into underlying source media (`>= 0.0`)
- `source_out_sec`: End offset in underlying source media
- `speed`: Playback rate (`0.25` to `4.0`, default `1.0`)
- `properties`: Track-kind-specific transforms, filters, audio gains, transitions, or caption styling.

**Timing Invariant:**
$$\text{timeline\_end} - \text{timeline\_start} \approx \frac{\text{source\_out} - \text{source\_in}}{\text{speed}}$$
The backend validator rejects negative timings, zero-duration clips, or overlapping clips on the same non-blendable track.

---

## 3. Undo / Redo & Autosave Architecture

- **Command / Operation Pattern:** Edits submit atomic `TimelineOperation` payloads (`move_clip`, `trim_clip`, `split_clip`, `delete_clip`, `add_track`, `toggle_track_flag`, `apply_caption_style`, `ai_batch_plan`).
- **Persistent Revision Ledger (`timeline_revisions`):**
  - Stores monotonically increasing `revision_number` (`1, 2, 3...`), `parent_revision`, `operation_summary`, `author` (`user` | `ai_editor`), and compressed/delta document snapshot.
  - Client maintains responsive local undo stack synchronized with backend `/undo` and `/redo` endpoints.
- **Debounced Autosave:** Active workspace changes autosave after `1500ms` of inactivity (`POST /timeline/autosave`), distinguishing draft autosaves from named user checkpoints so crashes never lose work.

---

## 4. Layout & Interaction Boundaries (Historical Fixes Preserved)

Drawing directly from historical `BUG-08A-3`, `BUG-08A-4`, and `BUG-08A-10`:
1. **Bounded Single-Viewport NLE Layout:** The Timeline Editor page uses `h-full flex flex-col overflow-hidden`. Preview monitor & Clip Inspector share a bounded flex-1 row; the multi-track timeline occupies a fixed-proportion bottom dock with internal horizontal & vertical scrolling—zooming the timeline MUST NEVER stretch the browser window.
2. **Explicit Sequence Selection:** Opening the editor via `?shortId=...` loads that specific Short's sequence rather than defaulting to a generic clip, with a header dropdown to switch sequences cleanly.
3. **Snapping & Scrubbing:** Snaps against clip edges, playhead, and scene-cut markers when `snap_enabled = true`; preview `<video>` synchronizes seamlessly with the scrub playhead.

---

## 5. API Boundary Contract (Planned Milestone 7)

| Method & Path | Responsibility |
|---|---|
| `GET /api/v1/projects/{pid}/timeline` | Load active sequence (or create default from `?shortId=`) |
| `POST /api/v1/projects/{pid}/timeline/operations` | Validate & apply atomic operation(s), returning updated `revision` |
| `POST /api/v1/projects/{pid}/timeline/undo` | Step back one revision cleanly |
| `POST /api/v1/projects/{pid}/timeline/redo` | Step forward one revision cleanly |
| `PUT /api/v1/projects/{pid}/timeline/autosave` | Persist non-destructive UI state & sequence draft |
| `GET /api/v1/projects/{pid}/timeline/revisions` | Inspect revision history & rollback |
