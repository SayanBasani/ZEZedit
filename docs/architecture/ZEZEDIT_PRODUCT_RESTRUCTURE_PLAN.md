# ZezEdit 2.0 — Product Restructure & Video-Centric Architecture Plan

## 1. Executive Summary & Problem Diagnosis

### 1.1 The Problem in Previous Iterations
Previous development iterations incrementally added features (Projects, Media Library, Video Analysis, AI Highlights, Smart Reframing, Shorts Export, Timeline Editor) as isolated, disconnected tools. This forced users into an unnatural hierarchy:
1. Creating manual "Projects" before doing anything.
2. Grouping assets within projects.
3. Jumping across disjointed sidebar tools (`/analysis`, `/highlights`, `/reframing`, `/export`) with separate parameters and lost context.

### 1.2 The User's Desired Workflow
The true product workflow for ZezEdit is simple, unified, and centered exclusively on the **Video**:
```
Direct Video Upload / Drag-and-Drop
          │
          ▼
Short Video Generator (Central Video Library)
          │
          ▼
Open Specific Video Dashboard (/videos/:assetId)
   ├── Persistent Top Header: Title + Real-time Multi-stage Progress Bar
   └── 8 Dedicated Horizontal Tabs:
         1. Home (Clean Video Player + Pure Technical Metadata)
         2. Generated Shorts (Card Showcase, Live Preview, Scoring, Edit Modal, Export)
         3. Short Video Generator (Presets/Custom Quantity, 18 Creative Directions, Aspect Ratios, Subject Tracking, Scene Selection, Execution)
         4. Generated Scripts (Script Archive, Hook/Dialogue Flow, 1-Click "Regenerate Video from Script")
         5. Analyzed Frames (Keyframes & Scene Cuts Gallery with Visual Observation Tags)
         6. Voice & Transcript Analysis (Searchable Interactive Transcript & Speech Turns)
         7. Scene Analysis (Scene Cards with Timestamps & Selective Generation Toggles)
         8. Video Analysis Details (Deep Pipeline Telemetry & Cache Metrics)
```

In addition, users require a unified **"Clear All Data"** emergency / maintenance capability in Settings (`Storage & Data` section) to cleanly wipe all managed media, thumbnails, proxies, frames, cache, temp, clips, scripts, and database tables in a single action with a safe confirmation modal, without affecting external source files outside managed storage or deleting application source code.

---

## 2. Architecture Comparison: Current vs Video-Centric

| Architectural Domain | Current Multi-Tool Architecture | New Video-Centric Architecture |
|---|---|---|
| **Primary Sidebar** | 12 items: Dashboard, Projects, Media Library, Video Analysis, AI Highlights, Smart Reframing, Shorts Export, Timeline, Working Queue, AI Providers, Docs, Settings, Diagnostics | **Streamlined to 5 essentials:** Dashboard, Short Video Generator (Video Library), Working Queue, AI Providers, Settings |
| **Ingestion Model** | Requires Project creation, Project grouping, separate upload modals | **Direct Video Ingestion:** Drag-and-drop or file picker on Short Video Generator page. Validates video MIME type, extracts filename as default title, automatically assigns to internal `default` project |
| **Video Inspection & Execution** | Disjointed routes (`/media`, `/studio/:id`, `/analysis`, `/highlights`, `/reframing`) | **Single Unified Dashboard (`/videos/:assetId`):** Central command center containing all 8 inspection, generation, and editing tabs |
| **Progress & Telemetry** | Scattered progress widgets or isolated studio progress | **Persistent Top Banner:** Prominent stage name, progress percentage, animated bar, and estimated time remaining, polling `GET /api/v1/jobs` or active pipeline status |
| **Data Management** | Fragmented cache cleanup preview/apply in settings | **Unified "Clear All Data":** Dedicated service method `clear_all_data(confirmation_token='DELETE')` wiping managed directories and database tables cleanly |
| **Backward Compatibility** | Relies on SQLite `project_id` foreign keys | Internal `default` project exists implicitly; all queries default or query across assets seamlessly without breaking existing DB migrations |

---

## 3. Storage Layout & Clear All Data Safety Architecture

### 3.1 Managed Storage Structure
Managed storage resides in `D:\ZezEdit\storage\`:
- `media/` — Stored managed video assets.
- `proxies/` — Scrubbing and low-res proxy MP4s.
- `thumbnails/` — Generated preview thumbnails.
- `analysis/` — Extracted audio, cached feature embeddings, transcripts, frame caches.
- `shorts/` — Cut candidate clips and cropped clips.
- `exports/` — Final rendered video files.
- `temp/` — Transient processing files and FFmpeg scratch.
- `db/zezedit.db` — SQLite database file.

### 3.2 Clear All Data Protocol
When the user executes **Clear All Data**:
1. User must confirm by typing exact text `DELETE` in the confirmation dialog.
2. API endpoint: `POST /api/v1/storage/clear-all-data` with payload `{"confirmation": "DELETE"}`.
3. Service `StorageService.factory_reset()` executes:
   - Traverses and empties all files and subdirectories inside `media/`, `proxies/`, `thumbnails/`, `analysis/`, `shorts/`, `exports/`, `temp/`.
   - Leaves directory structures intact.
   - Clears database tables: `candidate_clips`, `clip_edits`, `video_scripts`, `analysis_runs`, `timeline_tracks`, `timeline_items`, `timelines`, `media_assets`, `jobs`, `export_jobs`, `projects`.
   - Re-creates baseline project `default` ("Default Workspace") so foreign key constraints remain valid.
   - Preserves `schema_migrations` table so migration state remains 0014.
   - Never deletes external original files referenced by path outside `D:\ZezEdit\storage\`.
   - Returns a structured deletion manifest (files removed, directories swept, bytes reclaimed, tables truncated).

---

## 4. Video Ingestion & Short Video Generator Library

### 4.1 Ingestion Flow
1. Target: `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx` (accessible via route `/videos` and sidebar `Short Video Generator`).
2. Direct Upload Area:
   - Drag & drop zone supporting `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`.
   - Direct file picker with client-side MIME type check.
   - Title input pre-populated with filename (extension stripped).
   - Instant upload triggering `POST /api/v1/media/upload` with `project_id='default'` (or auto-assigned).
3. Video Card Grid & List:
   - Shows all existing videos (`med_51dc0e4b43f8`, etc.) and newly uploaded videos.
   - Displays thumbnail, title, duration, resolution, fps, size, and status badge (`Ready`, `Analyzing`, `Error`).
   - Primary action: **"Open Video Dashboard"** button navigating to `/videos/:assetId`.
   - Secondary actions: Quick Delete, Re-analyze, Refresh.

---

## 5. Single Video Edit Dashboard (`/videos/:assetId`) Specification

### 5.1 Persistent Top Header
- Left: Back to Short Video Generator (`/videos`), Video Title (editable inline or modal), Duration, Resolution badge.
- Center/Right: Multi-stage progress indicator:
  - If a job is active: Stage Name (e.g., `Scene Detection`, `Audio Transcription`, `Face Tracking`), `% Complete` (e.g. `68%`), Animated Progress Bar, and `Estimated Time Remaining`.
  - If idle: Status badge (`Analyzed - 27 Candidates Discovered`, `Ready to Analyze`, etc.) and primary action button (e.g. "Run Analysis" or "Generate Shorts").

### 5.2 The 8 Horizontal Tabs

#### Tab 1: Home
- Clean, focused layout:
  - High-performance HTML5 video player with scrubber, timecode, and playback speed.
  - Pure technical metadata cards: Duration, Resolution, Framerate, Video Codec, Audio Codec, Container Format, File Size, Storage Location.
  - Zero clutter: No configuration panels or disconnected tools here.

#### Tab 2: Generated Shorts
- Gallery of discovered short candidates and generated clips.
- Each short card includes:
  - Thumbnail / playable preview modal.
  - Virality / Attractiveness Score (0–100) with breakdown indicators (Hook, Pacing, Speech, Visuals).
  - Duration (e.g., `00:24.5`).
  - Boundary type badge (e.g., `Natural Scene Cut`, `Speech Pause Aligned`).
  - Actions: **"Edit Clip"** (opens existing `CandidateClipEditorModal` for 9:16/1:1 cropping, framing, and trimming) and **"Export MP4"** (triggers direct rendering/export).

#### Tab 3: Short Video Generator
- Comprehensive generation control center:
  - **Quantity Selection:** Preset chips (`AI Recommended`, `3`, `5`, `10`, `15`, `20`) or `Custom Number` input.
  - **18 Creative Directions:** Card/chip selector covering Best Overall, Viral Punchy, Dramatic, Action Motion, Emotional Sad, Engaging Dialogue, Humorous, Educational, Suspense/Thriller, Narrative Arc, High Energy, Cinematic, Storytelling, Reaction Focus, Interview Highlight, Teaser/Trailer, Motivational, Aesthetic Montage.
  - **Aspect Ratios:** `9:16` (Vertical), `1:1` (Square), `16:9` (Landscape), `4:3` (Classic), `4:5` (Portrait), `3:4` (Tall).
  - **Subject Tracking:** Face Tracking, Upper Body / Person Tracking, Object Motion, Multi-Subject Framing.
  - **Content Selection:** Option to generate from all scenes or filter by specific scenes selected in Scene Analysis.
  - **Duration Range:** Min/Max slider (e.g., 15s – 60s).
  - **Action Button:** Prominent **"Generate Shorts"** button executing generation and switching to Generated Shorts tab upon start.

#### Tab 4: Generated Scripts
- Script cards generated from video analysis and dialogue highlights:
  - Title & Hook summary.
  - Full dialogue excerpt with speaker indicators and timecodes.
  - Narrative structure (Hook → Body → Climax / Punchline → Call to Action).
  - **"Regenerate Video from Script"** 1-click action: Directly converts script timecodes into a candidate short clip for editing and export.

#### Tab 5: Analyzed Frames
- Visual keyframe browser:
  - Responsive image grid of extracted keyframes and scene boundaries.
  - Timestamps on every frame.
  - Visual observation tags (e.g., `Face Detected: 0.94`, `High Motion`, `Wide Shot`, `Close-up`, `Dynamic Lighting`).
  - Click-to-seek: Clicking any frame jumps the main video player to that exact timecode.

#### Tab 6: Voice & Transcript Analysis
- Interactive full-transcript view:
  - Search filter for keywords across speech.
  - Chronological speech turns with speaker labels, start/end timestamps, and duration.
  - Silence & pause interval markers.
  - Click-to-seek: Clicking any phrase jumps playback to that time.

#### Tab 7: Scene Analysis
- Detected scene cards:
  - Scene thumbnail, start time, end time, duration, and transition type (e.g., `Hard Cut`, `Fade`).
  - Scene visual description / tags.
  - **Inclusion / Exclusion Toggles:** Checkboxes allowing the user to select or exclude specific scenes for Short Video Generation.

#### Tab 8: Video Analysis Details
- Deep technical analysis inspection:
  - Component status indicators (Transcription, Scene Cuts, Saliency, Audio Energy, Face Detection).
  - Cache telemetry (Analysis cache size, cache validity, execution timestamps).
  - Stage execution durations and hardware utilization stats.
  - Option to invalidate cache and re-run specific stages.

---

## 6. Implementation Sequence & Milestones

1. **Backend Storage & Reset:**
   - Add `clear_all_data()` to `StorageService`.
   - Implement `POST /api/v1/storage/clear-all-data` in `settings.py`.
   - Write comprehensive unit tests for deletion safety.
2. **Backend Video Management:**
   - Ensure media upload and list endpoints seamlessly operate with default project fallback.
   - Provide script generation endpoint or synthesis helper if missing.
3. **Frontend Sidebar & Routing:**
   - Update `Sidebar.tsx` to the 5 primary routes.
   - Update `App.tsx` routes: `/videos` (Short Video Generator Library) and `/videos/:assetId` (Video Edit Dashboard).
4. **Frontend Short Video Generator Library:**
   - Implement direct drag-and-drop video upload and instant video list.
5. **Frontend Video Edit Dashboard:**
   - Build `VideoEditDashboard.tsx` with top persistent progress bar and 8 tabs.
   - Connect existing candidate editor modal, player, and analysis telemetry.
6. **Frontend Settings Clear All Data Modal:**
   - Implement modal requiring `DELETE` confirmation and wire to backend API.
7. **End-to-End Verification:**
   - Execute test suites, TypeScript check, Vite build, and live browser testing.
