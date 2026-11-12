# ZezEdit 2.0 — Unified Video Studio & UX Architecture Design
**Date:** November 12, 2026  
**Document:** `docs/architecture/UNIFIED_VIDEO_STUDIO_DESIGN.md`  
**Status:** Target Architectural Design (Session 0)

---

## 1. Primary Navigation & Mental Model

### 1.1 Simplified Primary Navigation
The left sidebar navigation is streamlined from 10+ confusing tools down to 5 essential destinations:

1. **Dashboard:** Overview of recent videos, quick metrics, active background renders, and system readiness.
2. **Media Library:** Central catalog of all imported source media files (MP4, MOV, MKV, WAV).
3. **Working Queue:** Real-time job monitor displaying background transcribing, tracking, and rendering tasks.
4. **AI Providers:** Configuration for local Ollama, Faster-Whisper, and optional external LLM endpoints.
5. **Settings:** Performance tuning, storage paths, hardware resource guard, and safe maintenance cleanup.

> **Consolidation Note:** Standalone sidebar entries for *Video Analysis*, *AI Highlights*, *Smart Reframing*, and *Shorts Export* are removed from global navigation. These are capabilities of an individual source video and live entirely within that video's dedicated studio.

---

## 2. Media Library Design

The Media Library is the entry point for all creative work.
- **Card Metrics:** Filename, thumbnail preview, duration, file size, resolution, frame rate, proxy status.
- **Primary Action:** Every video card features a single prominent button: **"Open Video Studio"** (with `Sliders` line icon).
- **Secondary Actions:** A quiet row underneath provides:
  - `Timeline`: Jump to advanced non-linear multi-track timeline editor if custom multi-clip editing is needed.
  - `Details`: Inspect technical metadata (bitrate, codecs, storage paths, relinking).
  - `Delete`: Remove media reference from project (with safety confirmation).
- **Import Drawer:** Drag-and-drop or select local filesystem path with instant indexing.

### Text Wireframe: Media Library
```
+----------------------------------------------------------------------------------------------------+
| ZezEdit 2.0   [Search media...]  [All | Videos | Audio]  [Viewing: All Videos v]   [+ Import Media] |
+----------------------------------------------------------------------------------------------------+
|  TOTAL ASSETS: 10      STORAGE FOOTPRINT: 1.8 GB      PROXY SCRUB CACHE: 240 MB                    |
+----------------------------------------------------------------------------------------------------+
| +-------------------------+ +-------------------------+ +-------------------------+                |
| | [Thumbnail 16:9] 02:14  | | [Thumbnail 16:9] 08:45  | | [Thumbnail 16:9] 45:12  |                |
| | movie_scene_01.mp4      | | interview_take2.mp4     | | podcast_episode_14.mp4  |                |
| | 1080p • 25fps • 420 MB  | | 4K • 30fps • 1.2 GB     | | 1080p • 30fps • 850 MB  |                |
| | Proxy: 480p Ready       | | Proxy: + Create Proxy   | | Proxy: 480p Ready       |                |
| |                         | |                         | |                         |                |
| | [  Open Video Studio  ] | | [  Open Video Studio  ] | | [  Open Video Studio  ] |                |
| | [Timeline] [Info] [Del] | | [Timeline] [Info] [Del] | | [Timeline] [Info] [Del] |                |
| +-------------------------+ +-------------------------+ +-------------------------+                |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Dedicated Single-Video Studio (`/studio/:assetId`)

Clicking **"Open Video Studio"** on any video navigates to its dedicated studio page: `/studio/:assetId`.
Everything related to this video lives on this single page, structured in four clear sections:

### Section A: Top Video Header & Live Global Progress
- **Video Header:** Back button, filename, duration, resolution, file size, codec, and overall export status.
- **Global Real-Time Progress Bar:**
  - Active percentage (`0%` to `100%`) derived from measurable backend milestones.
  - Current stage name (e.g., *"Transcribing audio with Whisper"*, *"Detecting scene cuts"*, *"Tracking faces & motion"*, *"Discovering viral moments"*).
  - Elapsed time and real Estimated Time Remaining (ETA) calculated only once steady-state frame processing begins.
  - Non-blocking: creator can browse the page or queue background jobs without UI lockup.

### Section B: Upfront Generation Configuration Bar
Before analysis begins, the creator sets the desired parameters:
1. **Target Aspect Ratio:**
   - `9:16 Vertical` (Shorts / Reels / TikTok) — Default.
   - `1:1 Square` (Instagram / Facebook feed).
   - `16:9 Landscape` (YouTube / Television).
   - `4:5 Portrait` (Social feed).
2. **Number of Shorts:**
   - Quick pills for `5`, `6`, `10`, `15`, `20`, plus custom numeric input.
3. **Creative Direction / Vibe:**
   - `Best Overall` (Balanced scoring across all factors).
   - `Emotional / Sad` (Prioritizes minor tonal speech, low tempo, monologue reflection).
   - `Dramatic` (Prioritizes conflict, vocal intensity, shot transitions).
   - `Action & Motion` (Prioritizes high subject velocity, dynamic camera cuts).
   - `Engaging Dialogue` (Prioritizes conversational turn density, punchy statements).
   - `Funny / Humorous` (Prioritizes punchline pauses, audience laugh tracks/inflections).
   - `Strong Opening Hooks` (Prioritizes intriguing opening sentences with immediate clarity).
4. **Action Button:**
   - **"Analyze & Generate Shorts"**: Dispatches the unified pipeline.
   - History Indicator: Displays count of previously generated clips excluded to guarantee novelty (e.g., *"10 prior clips excluded"*).

### Section C: Main Workspace Body (Framed Preview Player + Shorts Showcase)
- **Left Column: Framed Preview Player:**
  - Viewport displaying video framed in the chosen aspect ratio (`9:16`, `1:1`, etc.).
  - Bounding box indicators showing active face/subject tracking.
  - Live subtitle overlay rendering with styled captions.
  - Video transport: Play/Pause, scrubber, volume, loop.
  - Crop override toggle: Allows fine-tuning horizontal framing keyframes.
- **Right Column: Generated Shorts Showcase:**
  - Clean card stack of all discovered shorts candidates.
  - Candidate Card:
    - Title / descriptive label.
    - Start & End timestamps (`00:14:22 - 00:14:58`) and natural duration (`36s`).
    - Attractiveness score (`92/100`) with breakdown tooltip.
    - Creative category badge (`Dramatic`, `Action`, `Dialogue`).
    - Dialogue quote / hook transcript preview.
    - Actions: `[Play Preview]`, `[Export MP4]`, `[Send to Timeline]`.
  - Batch Action: Header button **"Export All Selected (MP4)"** opening the batch export queue.

### Section D: Collapsible Video Intelligence Drawers
To prevent overwhelming the primary editing workflow, deep technical data is organized into three collapsible drawers at the bottom:
1. **Full Searchable Transcript:** Complete timestamped transcript with keyword search, speaker tags, and non-destructive text corrections.
2. **Detected Scene Cuts:** Visual filmstrip of keyframes generated at PySceneDetect cut points with exact timestamps.
3. **Subject & Motion Tracking:** Diagnostic inspection showing detected face coordinates, character groupings, and crop smoothing telemetry.

---

## 4. Text Wireframe: Dedicated Single-Video Studio

```
+----------------------------------------------------------------------------------------------------+
| [< Media Library]  movie_trailer_1080p.mp4 (02:14:10 • 1.8 GB • H.264 • 1080p)       [Batch Export] |
+----------------------------------------------------------------------------------------------------+
| [ PROGRESS: ============================= 64% ========================= ]  ETA: 35s                |
| Stage: Discovering viral dialogue moments & calculating 9:16 crop trajectories                     |
+----------------------------------------------------------------------------------------------------+
| UPFRONT CONFIGURATION:                                                                             |
| Aspect Ratio: [ (•) 9:16 Vertical | ( ) 1:1 Square | ( ) 16:9 Landscape | ( ) 4:5 Portrait ]       |
| Target Count: [ ( ) 5 | ( ) 6 | (•) 10 | ( ) 20 | Custom: [  ] ]   Vibe: [ Dramatic Conflict v ]   |
| [  Analyze & Generate Shorts  ]  (Novelty active: 6 previous shorts excluded from generation)      |
+----------------------------------------------------+-----------------------------------------------+
| FRAMED PREVIEW PLAYER (9:16 Viewport)              | GENERATED SHORTS SHOWCASE (10 Discovered)     |
| +------------------------------------------------+ | +-------------------------------------------+ |
| |                                                | | | Short #1: "The Interrogation"      94/100 | |
| |                                                | | | 00:12:30 - 00:13:08 (38s) • Dramatic      | |
| |               [ 9:16 Aspect Box ]              | | | "You knew about the leak three days ago!" | |
| |                                                | | | [ Play Preview ]  [ Export MP4 ]  [ Edit ]| |
| |             [Subject Track Active]             | | +-------------------------------------------+ |
| |                                                | | +-------------------------------------------+ |
| |         "Subtitle Overlay Preview"             | | | Short #2: "Unexpected Discovery"   89/100 | |
| |                                                | | | 00:24:15 - 00:24:52 (37s) • Suspense      | |
| +------------------------------------------------+ | | "Look at these files... they lied to us." | |
| [ > Play ] [ 00:12:45 / 00:13:08 ] [Vol] [Reframe] | | [ Play Preview ]  [ Export MP4 ]  [ Edit ]| |
+----------------------------------------------------+-----------------------------------------------+
| COLLAPSIBLE VIDEO INTELLIGENCE:                                                                    |
| [v] Full Transcript (1,420 words)    [>] Detected Scenes (84 cuts)    [>] Face Tracking Diagnostics|
+----------------------------------------------------------------------------------------------------+
```

---

## 5. Safe One-Button Maintenance & Cleanup Interface

Located in **Settings $\rightarrow$ Maintenance & Storage**:
- **Objective:** Allow creators to reclaim disk space effortlessly without risking original media or creative projects.
- **Categorized Storage Ledger:**
  1. **Safe Regenerable Temporary Files:** Intermediate audio WAVs, raw visual frame JPEGs, temporary render segments.
  2. **Regenerable Proxies & Thumbnails:** 480p proxy files and thumbnail caches (can be re-generated on demand).
  3. **Analysis Feature Caches:** SQLite visual observation cache and temporal indexes.
  4. **Abandoned Job Artifacts:** Incomplete render fragments from cancelled jobs.
  5. **Completed MP4 Exports:** Saved user exports (explicit checkbox required; unchecked by default).
  6. **Original Media Files:** **NEVER DELETED.** Strictly excluded from maintenance operations.
- **Workflow:**
  1. Creator clicks **"Inspect Storage & Calculate Cleanup"**.
  2. Interface displays exact recoverable bytes per category (e.g., *"Safe to clean: 4.2 GB"*).
  3. Creator clicks single prominent button: **"Clean Safe Temporary Files"**.
  4. System executes bounded deletion, purges obsolete job records, runs SQLite `VACUUM`, and presents a verified cleanup report.

### Text Wireframe: Maintenance & Cleanup View
```
+----------------------------------------------------------------------------------------------------+
| SETTINGS — MAINTENANCE & STORAGE CLEANUP                                                           |
+----------------------------------------------------------------------------------------------------+
| STORAGE BREAKDOWN:                                                                                 |
| Total Managed Storage: 8.4 GB | Disk Free Space: 142 GB                                            |
|                                                                                                    |
| [x] Temporary Processing Files (WAV audio, sampled frames) .............. 3.1 GB [Safe to delete]  |
| [x] Regenerable 480p Proxies & Preview Caches ............................ 1.8 GB [Safe to delete]  |
| [x] Abandoned & Cancelled Render Fragments ............................... 450 MB [Safe to delete]  |
| [ ] Completed Video Exports (MP4) ........................................ 2.8 GB [Keep exports]   |
|                                                                                                    |
| Total Recoverable Space: 5.35 GB                                                                   |
|                                                                                                    |
| [  Clean Safe Temporary Data (5.35 GB)  ]                                                          |
| Note: Original imported source videos and project timelines are permanent and never deleted.       |
+----------------------------------------------------------------------------------------------------+
```
