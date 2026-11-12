# ZezEdit 1.0 — Exact Product Parity Specification

**Target Repository:** `D:\ZezEdit`  
**Classification:** Immutable Product Parity Specification  
**Investigation Baseline:** Surviving Pre-Deletion Records (`D:\Antrigavity2\ZezEdit`, Transcripts `23be7aa6` and `ec37b75b`, VS Code History `-180222c6`)  
**Specification Version:** 1.0.0 (Milestone 13)  
**Date:** November 12, 2026  

---

## 1. Product Vision & Mission Statement

ZezEdit 1.0 is an intelligent, local-first, privacy-respecting desktop application for Windows 11 designed to transform long-form horizontal videos (16:9) into high-retention vertical short clips (9:16) tailored for YouTube Shorts, Instagram Reels, and TikTok, while providing a professional non-linear timeline editing environment.

### Core Architecture Axioms
1. **Rendering Authority:** Media decoding, filtergraph construction, and final rendering are managed deterministically by **FFmpeg** on CPU (Intel Core i3-1220P class baseline, zero mandatory CUDA/GPU requirement).
2. **Safe Media Inspection:** Container and stream properties are dissected locally via **FFprobe** into validated Pydantic schemas.
3. **Pluggable Local AI:** Multimodal reasoning runs via local **Ollama** (`qwen3-vl:4b-instruct`) and Faster-Whisper behind clean provider abstractions with robust offline heuristic fallbacks.
4. **Persistent State:** SQLite with Write-Ahead Logging (`WAL`) manages project metadata, versioned `EditPlan (v1.0.0)` contracts, and crash-resilient background jobs.
5. **Non-Destructive Operations:** Source media files are strictly immutable; all edits, crops, and revisions produce versioned records without destructive overwrites.

---

## 2. Requirement Taxonomy & Numbering

Requirements are partitioned into 10 functional domains, each assigned a permanent, unique identifier:

| Domain Prefix | Functional Scope | Requirement Count |
|---|---|---|
| `ZEZ-001` – `ZEZ-010` | **Domain A:** Application Shell, Dashboard & Navigation | 10 Requirements |
| `ZEZ-011` – `ZEZ-020` | **Domain B:** Media Ingestion, Proxies & Storage Management | 10 Requirements |
| `ZEZ-021` – `ZEZ-030` | **Domain C:** Video Analysis, Audio Extraction & Speech Transcription | 10 Requirements |
| `ZEZ-031` – `ZEZ-040` | **Domain D & E:** AI Multimodal Understanding & Highlight Discovery | 10 Requirements |
| `ZEZ-041` – `ZEZ-055` | **Domain F:** Smart Reframing, Subject Tracking & Manual Crop Review (13M.12/13M.13) | 15 Requirements |
| `ZEZ-056` – `ZEZ-068` | **Domain G:** Shorts Generation, FFmpeg Rendering Engine & Output Validation | 13 Requirements |
| `ZEZ-069` – `ZEZ-080` | **Domain H:** Multi-Track Timeline & Conversational AI Video Editor | 12 Requirements |
| `ZEZ-081` – `ZEZ-090` | **Domain I:** Character Extraction Studio & Scene Intelligence | 10 Requirements |
| `ZEZ-091` – `ZEZ-100` | **Domain J:** System Monitoring, Diagnostics, Safety & Reliability | 10 Requirements |
| **Total Requirements** | **Complete ZezEdit 1.0 Specification** | **100 Requirements** |

---

## 3. Detailed Specification by Domain

### Domain A: Application Shell, Dashboard & Navigation (`ZEZ-001` – `ZEZ-010`)

#### `ZEZ-001`: Studio Application Shell & Responsive Drawer
- **Original Purpose:** Provide a distraction-free desktop NLE interface with a collapsible sidebar and mobile-responsive drawer.
- **Original Workflow:** User launches the app; desktop displays a 240px wide sidebar; collapsing reduces it to 64px icon-only rail; mobile view uses a slide-over backdrop drawer.
- **Original UI Location:** Global app shell (`Sidebar.tsx`, `NavigationLayout.tsx`).
- **Controls & Interactions:** Sidebar collapse toggle button, route navigation links, system status indicators.
- **Backend Behavior:** Serves static frontend assets; routes API requests through `/api/v1/*`.
- **Data Requirements:** Current active route string, collapsed boolean stored in localStorage.
- **Processing Algorithms:** CSS flexbox layout with sticky rail and `overflow-hidden` root viewport.
- **Dependencies:** React, Lucide-React icons, Tailwind CSS.
- **Historical Evidence:** `D:\Antrigavity2\ZezEdit\frontend\src\components\Sidebar.tsx` in transcript logs.
- **Current ZezEdit 2.0 Status:** Implemented in `frontend/src/app/App.tsx`.
- **Exact Differences:** None. Full visual and interaction parity.
- **Restoration Requirement:** Preserve existing implementation.
- **Verification Method:** Vitest `navigation.test.tsx` and manual viewport resize check.

#### `ZEZ-002`: Studio Dashboard View
- **Original Purpose:** High-level cockpit showing system health, storage footprint, recent projects, and active background tasks.
- **Original Workflow:** User navigates to root `/` or `/dashboard`; reviews total project count, active jobs, and recent editing sessions.
- **Original UI Location:** `DashboardPage.tsx` / `DashboardView.tsx`.
- **Controls & Interactions:** "New Project" primary action button, project cards with click-to-open, job status indicators.
- **Backend Behavior:** `GET /api/v1/health`, `GET /api/v1/projects`, `GET /api/v1/jobs`.
- **Data Requirements:** Health JSON payload, list of project records, active job list.
- **Processing Algorithms:** Aggregates project statistics and background worker status.
- **Dependencies:** FastAPI `/health`, `/projects`, `/jobs` endpoints.
- **Historical Evidence:** `DashboardPage.tsx` in `transcript_full.jsonl` and surviving `README.md`.
- **Current ZezEdit 2.0 Status:** Implemented in `frontend/src/features/dashboard/DashboardView.tsx`.
- **Exact Differences:** ZezEdit 2.0 includes Unslop metric cards and clean layout.
- **Restoration Requirement:** Maintain clean studio dashboard with live polling.
- **Verification Method:** Verified via browser screenshot `01_dashboard.png`.

#### `ZEZ-003`: Project Management & Lifecycle Operations
- **Original Purpose:** Create, list, sort, rename, archive, restore, and delete video editing projects.
- **Original Workflow:** User creates a project with title/description; projects display in Grid or List mode with search and sorting (Newest, Oldest, Name, Most Shorts); cascade delete requires confirmation.
- **Original UI Location:** `ProjectsPage.tsx` / `ProjectsManager.tsx`.
- **Controls & Interactions:** Search bar, layout toggle, status filter dropdown, rename input, archive toggle, delete button with confirmation dialog.
- **Backend Behavior:** `GET/POST /api/v1/projects`, `POST /api/v1/projects/{id}/archive`, `DELETE /api/v1/projects/{id}`.
- **Data Requirements:** `projects` table (id, name, description, status, created_at, updated_at).
- **Processing Algorithms:** Filter and sort predicates; cascade purge of project directory in `storage/`.
- **Dependencies:** SQLite `projects` and `project_events` tables.
- **Historical Evidence:** Surviving `README.md` Section 2 ("Project Library Management") and `test_milestone13m8_storage_and_models.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `frontend/src/features/projects/ProjectsManager.tsx`.
- **Exact Differences:** None. Matches all historical operations.
- **Restoration Requirement:** Preserve existing implementation.
- **Verification Method:** Automated Pytest `test_milestone2_core.py`.

#### `ZEZ-004`: Unified Video Workspace Navigation
- **Original Purpose:** Prevent losing video context when switching between analysis, reframing, highlights, and rendering tools.
- **Original Workflow:** Opening or importing a video navigates directly into the video workspace with contextual sub-tabs: Overview, Analysis, Transcript, Scenes, Highlights, Reframing, Export, Timeline, Characters.
- **Original UI Location:** `ProjectDetailPage.tsx` tabbed layout in 1.0; unified as `VideoWorkspace.tsx` in 2.0.
- **Controls & Interactions:** Sub-tab navigation bar with active video indicator pill, duration badge, resolution badge.
- **Backend Behavior:** Loads project media assets and hydrates active sub-workspace records.
- **Data Requirements:** Selected `media_asset_id` and `project_id`.
- **Processing Algorithms:** Contextual state preservation across tool transitions.
- **Dependencies:** React state, `apiClient.ts`.
- **Historical Evidence:** Historical `ProjectDetailPage.tsx` had tabs for Media, Highlights, Generated Shorts, AI Chat, Characters.
- **Current ZezEdit 2.0 Status:** Implemented in `frontend/src/features/workspace/VideoWorkspace.tsx`.
- **Exact Differences:** Unified workspace provides 9 sub-workspaces, surpassing 1.0's tab switching.
- **Restoration Requirement:** Retain 9-tab Video Workspace as the core editing hub.
- **Verification Method:** Verified across browser screenshots `04`–`12`.

#### `ZEZ-005`: Post-Import Guided Ingestion Flow
- **Original Purpose:** Provide immediate next-step actions upon importing a video file rather than stranding the user in a grid.
- **Original Workflow:** File drop/upload completes; `PostImportModal` appears with 4 actions: "Analyze Video Now", "Open Video Workspace", "Import Another Video", "Return to Media Library".
- **Original UI Location:** `PostImportModal.tsx`.
- **Controls & Interactions:** Action buttons, live analysis progress bar, storage policy selector.
- **Backend Behavior:** `POST /api/v1/projects/{pid}/media/{mid}/analysis`.
- **Data Requirements:** Ingested `MediaAssetItem` metadata.
- **Processing Algorithms:** Dispatches background job and polls execution status.
- **Dependencies:** `media_pipeline.py`, `jobs.py`.
- **Historical Evidence:** Gap identified during Milestone 11 audit; restored in M11.
- **Current ZezEdit 2.0 Status:** Operational in `frontend/src/features/media/PostImportModal.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve post-import modal triggers.
- **Verification Method:** Verified via browser screenshot `03_post_import_modal.png`.

#### `ZEZ-006`: System Monitor & Hardware Resource Widget
- **Original Purpose:** Display live CPU load, RAM usage, storage space, and Ollama model status to ensure local-first hardware limits are respected.
- **Original Workflow:** Widget pinned to bottom of sidebar or settings; shows color-coded memory and disk consumption.
- **Original UI Location:** `SystemMonitorWidget.tsx` in 1.0 sidebar.
- **Controls & Interactions:** Tooltip hover showing breakdown of disk usage per storage category.
- **Backend Behavior:** `GET /api/v1/storage/inspect`, `GET /api/v1/system/capabilities`.
- **Data Requirements:** Disk bytes free/total, memory RSS, thread pool status.
- **Processing Algorithms:** OS-level disk space queries with bounded 15s gentle polling.
- **Dependencies:** `psutil` or Python `shutil.disk_usage`.
- **Historical Evidence:** Mentioned specifically in `iBlu.md` line 3 ("like the system resource monitor...").
- **Current ZezEdit 2.0 Status:** Available inside `DashboardView.tsx` storage footprint and `SettingsManager.tsx`.
- **Exact Differences:** 1.0 had a mini persistent widget in the sidebar; 2.0 embeds it in Dashboard/Settings.
- **Restoration Requirement:** Add a compact resource pill/widget in the lower sidebar rail.
- **Verification Method:** Component mount test and storage inspection endpoint check.

#### `ZEZ-007`: Studio Light / Dark Theme Synchronization
- **Original Purpose:** Studio dark theme default for video contrast, with optional clean light mode.
- **Original Workflow:** Clicking theme icon toggles theme instantaneously without page reload; saved in `localStorage`.
- **Original UI Location:** App header / sidebar (`ThemeContext.tsx`).
- **Controls & Interactions:** Sun/Moon toggle button.
- **Backend Behavior:** None (Client-side styling).
- **Data Requirements:** Theme state (`dark` | `light`).
- **Processing Algorithms:** Updates `document.documentElement.classList` (`dark`).
- **Dependencies:** Tailwind CSS dark mode class strategy.
- **Historical Evidence:** `D:\Antrigavity2\ZezEdit\frontend\src\context\ThemeContext.tsx`.
- **Current ZezEdit 2.0 Status:** Fully operational in `frontend/src/context/ThemeContext.tsx`.
- **Exact Differences:** Defensive fallback added in M11 to prevent blank screen crashes.
- **Restoration Requirement:** Preserve existing implementation.
- **Verification Method:** Theme toggle test in Vitest.

#### `ZEZ-008`: Notification Center & Job Completion Toasts
- **Original Purpose:** Notify user when heavy background video processing (Whisper, rendering, clustering) completes or fails.
- **Original Workflow:** Toast appears in bottom-right corner; clicking toast navigates directly to the finished asset or short.
- **Original UI Location:** `NotificationCenter.tsx`.
- **Controls & Interactions:** Dismiss button, "View Short" action button, clear all.
- **Backend Behavior:** Job state polling triggers notifications on state transitions (`running` -> `completed` / `failed`).
- **Data Requirements:** In-memory notification list with persistent job IDs.
- **Processing Algorithms:** Event diffing against previous job list snapshot.
- **Dependencies:** React context / hook.
- **Historical Evidence:** `D:\Antrigavity2\ZezEdit\frontend\src\components\NotificationCenter.tsx` and `src/test/notifications.test.tsx` (4 tests).
- **Current ZezEdit 2.0 Status:** Background jobs tracked in `App.tsx` and `DashboardView.tsx`.
- **Exact Differences:** Dedicated floating toast container in 1.0; 2.0 uses status badges and inline alerts.
- **Restoration Requirement:** Re-implement floating toast notification component for background job completions.
- **Verification Method:** Vitest `notifications.test.tsx`.

#### `ZEZ-009`: Studio Documentation & Interactive Guides
- **Original Purpose:** In-app user manual and feature explanations for local AI, reframing, and keyboard shortcuts.
- **Original Workflow:** User clicks "?" icon; reads markdown documentation and workflow guides.
- **Original UI Location:** `DocumentationPage.tsx`, `ShortsGeneratorGuideModal.tsx`.
- **Controls & Interactions:** Searchable markdown documentation viewer, step-by-step workflow modal.
- **Backend Behavior:** Static markdown content rendering.
- **Data Requirements:** Markdown documentation files.
- **Processing Algorithms:** React markdown parser.
- **Dependencies:** `lucide-react`, markdown parser.
- **Historical Evidence:** `D:\Antrigavity2\ZezEdit\frontend\src\pages\DocumentationPage.tsx` and `src/test/documentation.test.tsx` (12 tests).
- **Current ZezEdit 2.0 Status:** Documentation resides in `docs/` repository files; not yet exposed via in-app viewer.
- **Exact Differences:** Missing in-app documentation modal / tab in current 2.0 UI.
- **Restoration Requirement:** Expose in-app documentation drawer / modal in settings or help menu.
- **Verification Method:** Vitest `documentation.test.tsx`.

#### `ZEZ-010`: Error Boundary & Crash Recovery
- **Original Purpose:** Catch unexpected client rendering exceptions and present user with actionable reload options rather than a blank page.
- **Original Workflow:** On render error, displays clean error card with stack trace and "Try Again" / "Reload Page" buttons.
- **Original UI Location:** `ErrorBoundary.tsx`.
- **Controls & Interactions:** Reset error button, window reload button.
- **Backend Behavior:** None.
- **Data Requirements:** Error object and React ErrorInfo.
- **Processing Algorithms:** React class component `componentDidCatch`.
- **Dependencies:** React.
- **Historical Evidence:** Added in M11 to resolve blank screen crash.
- **Current ZezEdit 2.0 Status:** Operational in `frontend/src/components/ui/ErrorBoundary.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve error boundary wrapper.
- **Verification Method:** Component error triggering test.

---

### Domain B: Media Management & Proxies (`ZEZ-011` – `ZEZ-020`)

#### `ZEZ-011`: Video Drag-and-Drop & File Picker Ingestion
- **Original Purpose:** Import local video files (MP4, MOV, MKV, WebM, AVI) via streaming copy or registered local path.
- **Original Workflow:** User drags file into dropzone or browses disk; file is validated, given a UUID `med_{hex}`, and stored in `storage/media/`.
- **Original UI Location:** `MediaLibraryView.tsx` / `ImportPage.tsx`.
- **Controls & Interactions:** Dropzone, "Browse Files" button, import modal.
- **Backend Behavior:** `POST /api/v1/projects/{pid}/media/import-local`.
- **Data Requirements:** Multipart file or local path payload; inserted into `media_assets` table.
- **Processing Algorithms:** Chunked streaming write avoiding loading entire video into RAM.
- **Dependencies:** `media_pipeline.py`, `storage.py`.
- **Historical Evidence:** Surviving `README.md` and `test_milestone4_media.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `MediaLibraryView.tsx`.
- **Exact Differences:** None. Matches 1.0 capability.
- **Restoration Requirement:** Preserve existing implementation.
- **Verification Method:** Automated test `test_media_import_local`.

#### `ZEZ-012`: Automated FFprobe Container & Stream Dissection
- **Original Purpose:** Extract deterministic video and audio metadata without decoding full frames.
- **Original Workflow:** Ingest dispatches probe job; populates duration, resolution (width/height), FPS, video codec (H.264, HEVC, VP9), audio codec (AAC, MP3), bitrate, and channels.
- **Original UI Location:** Metadata badges on media cards and workspace specs sheet.
- **Backend Behavior:** `ffprobe -v quiet -print_format json -show_format -show_streams`.
- **Data Requirements:** JSON output parsed into `MediaAssetMetadata` schema.
- **Processing Algorithms:** Subprocess execution with regex stream filtering.
- **Dependencies:** FFprobe binary.
- **Historical Evidence:** `backend/app/services/media.py` in transcript logs.
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/services/ffprobe.py`.
- **Exact Differences:** None. 100% parity.
- **Restoration Requirement:** Preserve existing implementation.
- **Verification Method:** Pytest `test_ffprobe_extraction`.

#### `ZEZ-013`: Fast Edit Proxy Generation (480p)
- **Original Purpose:** Enable fluid timeline scrubbing and preview on low-power CPUs without playback stuttering.
- **Original Workflow:** Background worker transcodes source to 480p H.264 baseline MP4 (`scale=-2:480`); proxy status tracks `pending` -> `completed`.
- **Original UI Location:** Proxy status pill on media cards and "Use Proxy" player toggle.
- **Backend Behavior:** `POST /api/v1/projects/{pid}/media/{mid}/proxy`, `GET .../proxy`.
- **Data Requirements:** Proxy video file saved to `storage/proxies/{asset_id}_proxy_480p.mp4`.
- **Processing Algorithms:** Single-pass FFmpeg transcode with fast preset and CRF 26.
- **Dependencies:** FFmpeg binary.
- **Historical Evidence:** `backend/app/services/media_pipeline.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `media_pipeline.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve proxy pipeline and player toggle.
- **Verification Method:** Pytest proxy generation test.

#### `ZEZ-014`: Poster Frame & Thumbnail Strip Generation
- **Original Purpose:** Extract visual cover thumbnails and multi-timestamp timeline filmstrips.
- **Original Workflow:** FFmpeg extracts keyframe at 1.0s or midpoint; saves to `storage/thumbnails/{asset_id}_poster.jpg`.
- **Original UI Location:** Media card thumbnail, video player poster.
- **Backend Behavior:** `GET /api/v1/projects/{pid}/media/{mid}/thumbnail`.
- **Data Requirements:** JPEG image file on disk.
- **Processing Algorithms:** `ffmpeg -ss {t} -i {src} -vframes 1 -q:v 2 {thumb_path}`.
- **Dependencies:** FFmpeg binary.
- **Historical Evidence:** `backend/app/services/media_pipeline.py`.
- **Current ZezEdit 2.0 Status:** Operational; serves cover thumbnails.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve thumbnail generation.
- **Verification Method:** Check image return from thumbnail endpoint.

#### `ZEZ-015`: Audio File Ingestion & Waveform Prep
- **Original Purpose:** Support independent audio tracks (voiceover, background music, sound effects).
- **Original Workflow:** User imports MP3, WAV, AAC, M4A, FLAC; probed for audio channels, sample rate, and duration.
- **Original UI Location:** Media library filter "Audio".
- **Backend Behavior:** Registered in `media_assets` with `media_type='audio'`.
- **Data Requirements:** `media_assets` table record.
- **Processing Algorithms:** Audio stream parsing via FFprobe.
- **Dependencies:** FFprobe binary.
- **Historical Evidence:** `README.md` Section "Supported Audio Formats".
- **Current ZezEdit 2.0 Status:** Implemented in `media_pipeline.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Maintain audio file import support.
- **Verification Method:** Pytest audio import test.

#### `ZEZ-016`: Image File Ingestion for Overlays & Watermarks
- **Original Purpose:** Support PNG/JPEG/WEBP logo overlays and sticker assets.
- **Original Workflow:** User imports image; width/height extracted; available for V2 overlay track.
- **Original UI Location:** Media library filter "Images".
- **Backend Behavior:** Registered in `media_assets` with `media_type='image'`.
- **Data Requirements:** `media_assets` table record.
- **Dependencies:** FFprobe / Pillow.
- **Historical Evidence:** `README.md` Section "Supported Image Formats".
- **Current ZezEdit 2.0 Status:** Implemented in `media_pipeline.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve image asset import.
- **Verification Method:** Media upload test with PNG file.

#### `ZEZ-017`: Safe Isolated Storage Layout
- **Original Purpose:** Protect user files with strict folder confinement and prevent accidental root deletion.
- **Original Workflow:** All assets organized into partitioned directories: `db/`, `media/`, `proxies/`, `thumbnails/`, `analysis/`, `timelines/`, `shorts/`, `exports/`, `temp/`, `backups/`, `logs/`.
- **Original UI Location:** Settings storage path display.
- **Backend Behavior:** `StorageLayout.from_root()` validates path confinement; rejects root drive targets (`D:\`).
- **Data Requirements:** Path strings verified via `Path.resolve()`.
- **Processing Algorithms:** Anti-path traversal guard in `security.py`.
- **Dependencies:** `app.core.storage`, `app.core.security`.
- **Historical Evidence:** `backend/app/core/storage.py` and `test_milestone1_foundation.py`.
- **Current ZezEdit 2.0 Status:** Fully operational.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve storage isolation.
- **Verification Method:** Automated security path traversal tests.

#### `ZEZ-018`: External Media Relinking & Missing File Detection
- **Original Purpose:** Prevent crashes when an external referenced media file is moved, renamed, or unmounted.
- **Original Workflow:** Startup or access checks `os.path.exists()`; if missing, marks asset `status='missing'`; user can click "Relink" to point to new file path.
- **Original UI Location:** Media card "Missing" alert badge and relink file dialog.
- **Backend Behavior:** `POST /api/v1/projects/{pid}/media/{mid}/relink`.
- **Data Requirements:** New file path validated for size and duration match.
- **Processing Algorithms:** File existence probe and metadata equivalence validation.
- **Dependencies:** `media.py` service.
- **Historical Evidence:** `test_milestone2_core.py` (`test_media_relinking`).
- **Current ZezEdit 2.0 Status:** Supported in backend `MediaPipelineService`.
- **Exact Differences:** Relink UI button needs prominent placement on media cards.
- **Restoration Requirement:** Add relinking button to media card error state in UI.
- **Verification Method:** Pytest relink test.

#### `ZEZ-019`: Media Asset Deletion with Safe Disk Cleanup
- **Original Purpose:** Remove unwanted media assets while ensuring dependent timeline clips or shorts are handled cleanly.
- **Original Workflow:** Clicking delete on media card checks if asset is in active timeline; displays warning; deletes DB records and associated disk proxies/thumbnails. Source raw video is deleted only if stored internally.
- **Original UI Location:** Media card delete icon with confirm modal.
- **Backend Behavior:** `DELETE /api/v1/projects/{pid}/media/{mid}`.
- **Data Requirements:** Media asset record and file paths.
- **Processing Algorithms:** Cascade removal of associated proxy and thumbnail files.
- **Dependencies:** `media_pipeline.py`.
- **Historical Evidence:** Surviving `README.md` ("cascade deletion").
- **Current ZezEdit 2.0 Status:** Implemented in `media_pipeline.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve safe deletion flow.
- **Verification Method:** Automated media deletion test.

#### `ZEZ-020`: Media Organization, Tags & Search
- **Original Purpose:** Filter and search media library assets by name, extension, duration range, and status.
- **Original Workflow:** Typing in search bar instantly filters grid; clicking pills filters by Video/Audio/Image.
- **Original UI Location:** `MediaLibraryView.tsx` search and filter bar.
- **Controls & Interactions:** Search input, type filter pills, sort dropdown.
- **Backend Behavior:** Client-side filter or query parameters on `GET /media`.
- **Data Requirements:** List of `MediaAssetItem`.
- **Dependencies:** React component state.
- **Historical Evidence:** `MediaLibraryView.tsx`.
- **Current ZezEdit 2.0 Status:** Implemented in `MediaLibraryView.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve search and filtering.
- **Verification Method:** Manual search check in UI.

---

### Domain C: Video Analysis & Speech Transcription (`ZEZ-021` – `ZEZ-030`)

#### `ZEZ-021`: Automated Audio Extraction for ASR
- **Original Purpose:** Extract clean 16kHz mono audio from video container for speech recognition processing.
- **Original Workflow:** Orchestrator runs FFmpeg audio demux; generates `analysis/{asset_id}_audio_16k.wav`.
- **Original UI Location:** Progress bar step "Extracting Audio".
- **Backend Behavior:** `ffmpeg -i {src} -vn -acodec pcm_s16le -ar 16000 -ac 1 -y {out}`.
- **Data Requirements:** 16kHz 16-bit PCM WAV file.
- **Processing Algorithms:** Fast FFmpeg stream copy/transcode without video processing.
- **Dependencies:** FFmpeg binary.
- **Historical Evidence:** `backend/app/services/video_analysis.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/services/transcription.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve 16kHz WAV extraction.
- **Verification Method:** Pytest audio extraction test.

#### `ZEZ-022`: Faster-Whisper Local Speech Transcription
- **Original Purpose:** Transcribe spoken dialogue into timestamped text completely offline on CPU.
- **Original Workflow:** Transcription service invokes local Faster-Whisper (`base` or `small` int8 model); produces segment records.
- **Original UI Location:** Video Workspace "Transcript" sub-tab.
- **Backend Behavior:** Runs Whisper model inference on extracted audio WAV.
- **Data Requirements:** `transcript_segments` table (start_time, end_time, text, confidence, words_json).
- **Processing Algorithms:** CTC beam search decoding with VAD (Voice Activity Detection) filter.
- **Dependencies:** `faster-whisper` Python library or fallback heuristic parser.
- **Historical Evidence:** Surviving `README.md` ("Whisper transcription") and `test_milestone5_analysis.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/services/transcription.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve local Faster-Whisper pipeline.
- **Verification Method:** Pytest transcription test.

#### `ZEZ-023`: Word-Level Timestamp Alignment
- **Original Purpose:** Provide exact per-word start and end timestamps for animated karaoke captions in Shorts.
- **Original Workflow:** Whisper outputs word timestamps (`word`, `start`, `end`, `probability`); stored in `words_json` per segment.
- **Original UI Location:** Caption editor and transcript search inspector.
- **Backend Behavior:** Recorded in SQLite `transcript_segments.words_json`.
- **Data Requirements:** Array of `{word: str, start: float, end: float, prob: float}`.
- **Processing Algorithms:** Whisper dynamic time warping word alignment.
- **Dependencies:** `faster-whisper` word timestamps flag (`word_timestamps=True`).
- **Historical Evidence:** `backend/app/services/transcription.py` and `export_service.py` ASS subtitle generator.
- **Current ZezEdit 2.0 Status:** Implemented in `transcription.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve word-level timestamp persistence.
- **Verification Method:** Check `words_json` populated in `transcript_segments`.

#### `ZEZ-024`: Synchronized Click-to-Seek Transcript Viewer
- **Original Purpose:** Allow the user to click any dialogue line in the transcript to jump video playback directly to that moment.
- **Original Workflow:** User views transcript list; clicking a dialogue row updates `videoRef.current.currentTime = segment.start_time`; active dialogue highlights as video plays.
- **Original UI Location:** Video Workspace "Transcript" tab.
- **Controls & Interactions:** Transcript row click, auto-scroll toggle, search input.
- **Backend Behavior:** `GET /projects/{pid}/media/{mid}/analysis/{run_id}/transcript`.
- **Data Requirements:** List of transcript segments.
- **Processing Algorithms:** Time-update event listener synchronizing active segment index.
- **Dependencies:** React HTML5 video player integration.
- **Historical Evidence:** Surviving `README.md` ("Searchable timestamped transcript viewer").
- **Current ZezEdit 2.0 Status:** Fully operational in `VideoWorkspace.tsx` Tab 3.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve click-to-seek synchronization.
- **Verification Method:** Verified in browser screenshot `06_video_workspace_transcript.png`.

#### `ZEZ-025`: Non-Destructive Transcript Text Corrections
- **Original Purpose:** Correct ASR typos or misspelled proper nouns without invalidating raw Whisper output.
- **Original Workflow:** User edits word/sentence in UI; stored in `transcript_corrections` table; caption renderer overlays corrections dynamically.
- **Original UI Location:** Inline text edit button on transcript row.
- **Backend Behavior:** `POST /api/v1/projects/{pid}/media/{mid}/transcript/corrections`.
- **Data Requirements:** `transcript_corrections` table (original_text, corrected_text, timestamp).
- **Processing Algorithms:** String replacement mapping during subtitle/caption synthesis.
- **Dependencies:** SQLite table.
- **Historical Evidence:** Surviving `README.md` Section 2 ("Non-Destructive Transcript Text Corrections").
- **Current ZezEdit 2.0 Status:** Fully restored in Milestone 15 with SQLite table `transcript_corrections`, full CRUD REST API, dynamic overlay on transcript, ASS export integration, and inline UI editor.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve non-destructive transcript corrections pipeline.
- **Verification Method:** Verified in `test_milestone15_analysis_parity.py` (`test_non_destructive_transcript_corrections`).

#### `ZEZ-026`: FFmpeg Visual Scene Cut Detection
- **Original Purpose:** Identify abrupt camera angle cuts and shot transitions to guide framing resets and highlight boundaries.
- **Original Workflow:** FFmpeg `select='gt(scene,0.35)'` filter analyzes video stream; extracts cut timestamps and representative frame images.
- **Original UI Location:** Video Workspace "Scenes" tab.
- **Backend Behavior:** `POST .../analysis` dispatches `SceneDetector`.
- **Data Requirements:** `video_scenes` table (start_time, end_time, representative_timestamp, change_score, thumbnail_path).
- **Processing Algorithms:** Scene change score computation on HSV/luma histogram differences.
- **Dependencies:** FFmpeg binary.
- **Historical Evidence:** `backend/app/services/scene_detector.py` and `test_milestone5_analysis.py`.
- **Current ZezEdit 2.0 Status:** Fully operational; 37 scene cuts detected on test video.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve scene cut detection.
- **Verification Method:** Verified in browser screenshot `07_video_workspace_scenes.png`.

#### `ZEZ-027`: Keyframe Visual Lightbox & Filmstrip
- **Original Purpose:** Inspect representative scene keyframes in an interactive filmstrip gallery.
- **Original Workflow:** User navigates to Scenes tab; views visual grid of scene thumbnails; clicking a thumbnail opens enlarged lightbox viewer.
- **Original UI Location:** `VideoWorkspace.tsx` Tab 4 / `ScenesPage.tsx`.
- **Controls & Interactions:** Thumbnail card, lightbox modal with Next/Previous arrows, jump-to-timecode button.
- **Backend Behavior:** Serves scene thumbnail images via `/api/v1/projects/{pid}/scenes/{id}/thumbnail`.
- **Data Requirements:** Scene records with image paths.
- **Dependencies:** React modal / lightbox.
- **Historical Evidence:** Surviving `README.md` ("keyframe lightbox viewer").
- **Current ZezEdit 2.0 Status:** Implemented in `VideoWorkspace.tsx` Tab 4.
- **Exact Differences:** Lightbox enlarged modal can be enhanced with keyboard arrow navigation.
- **Restoration Requirement:** Add keyboard arrow navigation to keyframe lightbox.
- **Verification Method:** UI interaction test in browser.

#### `ZEZ-028`: Interval Frame Sampling for Visual Understanding
- **Original Purpose:** Extract representative frame images at regular temporal intervals (e.g. every 2-5 seconds) for local vision AI analysis.
- **Original Workflow:** Frame sampler extracts frames to temporary directory; passes images to Ollama vision pipeline.
- **Original UI Location:** Internal analysis pipeline stage.
- **Backend Behavior:** Subprocess frame extraction with bounded storage limits.
- **Data Requirements:** Scaled JPEG frames (e.g. 640x360).
- **Processing Algorithms:** Interval stepping avoiding redundant frame decoding.
- **Dependencies:** FFmpeg binary.
- **Historical Evidence:** `backend/app/services/analysis_pipeline.py`.
- **Current ZezEdit 2.0 Status:** Operational in `backend/app/services/analysis_pipeline.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve interval frame sampler.
- **Verification Method:** Pytest analysis pipeline test.

#### `ZEZ-029`: Stage-Aware Analysis Caching & Fingerprinting
- **Original Purpose:** Avoid re-running expensive Whisper ASR or scene detection if the video file has already been analyzed.
- **Original Workflow:** System calculates fast header hash + file size + mtime fingerprint; reuses existing `analysis_runs` if unchanged.
- **Original UI Location:** Instant load of completed analysis results.
- **Backend Behavior:** `CacheService` lookup before scheduling worker jobs.
- **Data Requirements:** File hash string in `media_assets.checksum`.
- **Processing Algorithms:** SHA-256 over 64 KB header chunk + file metadata.
- **Dependencies:** `hashlib`.
- **Historical Evidence:** Surviving `README.md` Section 2 ("Stage-Aware Caching & Invalidation").
- **Current ZezEdit 2.0 Status:** Implemented in `backend/app/services/analysis_pipeline.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve analysis run reuse.
- **Verification Method:** Re-running analysis test confirming cached run reuse.

#### `ZEZ-030`: Analysis Run History & Inspection
- **Original Purpose:** Track previous analysis execution runs, profiles used, and completion timestamps.
- **Original Workflow:** User can review previous runs (e.g., standard vs deep profile) and select active analysis run.
- **Original UI Location:** Video Workspace Analysis tab header.
- **Backend Behavior:** `GET /projects/{pid}/media/{mid}/analysis`.
- **Data Requirements:** `analysis_runs` table records.
- **Dependencies:** SQLite table.
- **Historical Evidence:** `test_milestone5_analysis.py`.
- **Current ZezEdit 2.0 Status:** Implemented in `backend/app/services/analysis_pipeline.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve analysis run history.
- **Verification Method:** Verified in browser screenshot `05_video_workspace_analysis.png`.

---

### Domain D & E: AI Multimodal Understanding & Highlight Discovery (`ZEZ-031` – `ZEZ-040`)

#### `ZEZ-031`: Local Multimodal Vision Integration (Ollama)
- **Original Purpose:** Generate concise visual descriptions of scene keyframes using local vision models without third-party cloud uploads.
- **Original Workflow:** Vision service connects to Ollama (`http://127.0.0.1:11434`) using `qwen3-vl:4b-instruct`; prompts model for scene descriptions; falls back gracefully to heuristic saliency if Ollama is offline.
- **Original UI Location:** Visual descriptions in analysis inspection sheet.
- **Backend Behavior:** `POST /api/generate` via `httpx`.
- **Data Requirements:** Base64-encoded JPEG image and prompt string.
- **Processing Algorithms:** Local VLM inference with strict JSON schema decoding.
- **Dependencies:** Ollama runtime running locally.
- **Historical Evidence:** Surviving `README.md` and `test_milestone5_analysis.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/services/vision.py`.
- **Exact Differences:** None. Graceful offline fallback tested and verified.
- **Restoration Requirement:** Preserve Ollama integration and offline heuristic fallback.
- **Verification Method:** Pytest `test_vision_service`.

#### `ZEZ-032`: Multimodal Context Aggregator
- **Original Purpose:** Correlate speech transcript segments with concurrent visual keyframes and scene cuts into unified temporal chunks.
- **Original Workflow:** Merges transcript intervals, scene cut boundaries, and vision observations into a time-indexed timeline.
- **Original UI Location:** Highlight discovery input pipeline.
- **Backend Behavior:** Internal aggregation pipeline in `analysis_pipeline.py`.
- **Data Requirements:** Aggregated context JSON structure.
- **Processing Algorithms:** Interval overlap intersection.
- **Dependencies:** Python data structures.
- **Historical Evidence:** `backend/app/services/context_aggregator.py`.
- **Current ZezEdit 2.0 Status:** Implemented in `backend/app/services/analysis_pipeline.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve context aggregation.
- **Verification Method:** Pytest context aggregator test.

#### `ZEZ-033`: Explainable 9-Factor Highlight Scoring Engine
- **Original Purpose:** Identify the most engaging moments in a video using explainable multi-factor scoring rather than simple loudness or clickbait.
- **Original Workflow:** Evaluates candidate windows across 9 dimensions: Speech Density, Lexical Hook Strength, Emotional Sentiment, Audio Energy, Visual Motion, Scene Cut Pacing, Topic Completeness, Narrative Setup & Payoff, and Face Presence.
- **Original UI Location:** Video Workspace "AI Highlights" sub-tab scorecards.
- **Backend Behavior:** `HighlightScoringEngine.score_candidates()`.
- **Data Requirements:** Score weights and factor metrics saved in `shorts_candidates`.
- **Processing Algorithms:** Calibrated multi-factor weighted sum normalized to [0.0, 1.0].
- **Dependencies:** `backend/app/services/highlight_scoring.py`.
- **Historical Evidence:** `test_milestone6_highlights.py` and surviving `README.md`.
- **Current ZezEdit 2.0 Status:** Fully operational in `highlight_scoring.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve explainable scoring engine.
- **Verification Method:** Verified in browser screenshot `08_video_workspace_highlights.png`.

#### `ZEZ-034`: Narrative Setup and Payoff Boundary Preservation
- **Original Purpose:** Ensure highlight clips do not cut off before the punchline or start mid-sentence without necessary context.
- **Original Workflow:** Evaluator analyzes sentence boundaries around candidate clips; automatically expands start time to capture the setup question and end time to complete the thought.
- **Original UI Location:** Candidate boundary display (Start / End / Duration).
- **Backend Behavior:** Sentence-boundary clamping algorithm in `highlight_scoring.py`.
- **Data Requirements:** Whisper word and segment boundaries.
- **Processing Algorithms:** Forward and backward sentence boundary snapping.
- **Dependencies:** Transcript segments.
- **Historical Evidence:** Surviving `README.md` ("Temporal clustering eliminates overlapping clips and enforces narrative diversity").
- **Current ZezEdit 2.0 Status:** Implemented in `highlight_scoring.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve setup and payoff preservation rules.
- **Verification Method:** Automated test verifying boundary snapping.

#### `ZEZ-035`: Categorized Shorts Candidate Ranking
- **Original Purpose:** Organize discovered highlights by editorial category so creators can select hooks, insights, or story moments.
- **Original Workflow:** Candidates tagged with categories (`hook`, `insight`, `action`, `narrative`, `humor`); displayed with rank order and viral potential percentage.
- **Original UI Location:** Highlights Workspace candidate cards.
- **Controls & Interactions:** Category filter pills, sort by Score / Duration / Timecode.
- **Backend Behavior:** `GET /projects/{pid}/media/{mid}/highlights`.
- **Data Requirements:** `shorts_candidates` table records.
- **Dependencies:** SQLite table.
- **Historical Evidence:** Surviving `README.md` ("Generates rich highlight metadata: category, title, hook rationale").
- **Current ZezEdit 2.0 Status:** Fully operational in `HighlightsWorkspace.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve candidate categorization and ranking.
- **Verification Method:** Verified in browser screenshot `08_video_workspace_highlights.png`.

#### `ZEZ-036`: Hook Rationale & Explanation Card
- **Original Purpose:** Explain to the creator *why* this moment was selected (e.g., "Strong opening question with high speech density and character reaction within first 3 seconds").
- **Original Workflow:** Card displays highlighted "Hook Rationale" callout beneath title.
- **Original UI Location:** Candidate card in Highlights Workspace.
- **Backend Behavior:** Stored in `shorts_candidates.explanation` JSON.
- **Data Requirements:** Text explanation string.
- **Dependencies:** SQLite table.
- **Historical Evidence:** Surviving `README.md` ("Hook rationale: Why this grabs attention in 3s").
- **Current ZezEdit 2.0 Status:** Fully operational in `HighlightsWorkspace.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve hook rationale display.
- **Verification Method:** Verified in browser screenshot `08_video_workspace_highlights.png`.

#### `ZEZ-037`: Candidate Review & Approval Workflow
- **Original Purpose:** Allow the creator to approve, reject, or mark candidates as favorites before rendering.
- **Original Workflow:** User clicks "Approve" (green check) or "Reject" (cross); status updates to `approved`/`rejected`; approved clips appear in the export queue.
- **Original UI Location:** Candidate action buttons on each card.
- **Controls & Interactions:** Approve button, Reject button, Favorite star.
- **Backend Behavior:** `POST /api/v1/projects/{pid}/highlights/{id}/review` with `status: approved`.
- **Data Requirements:** `shorts_candidates.review_status` column.
- **Dependencies:** SQLite column update.
- **Historical Evidence:** `backend/app/api/v1/highlights.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `HighlightsWorkspace.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve candidate review workflow.
- **Verification Method:** Candidate review API test.

#### `ZEZ-038`: Manual Highlight Boundary Adjustment
- **Original Purpose:** Allow the creator to fine-tune the start and end timestamps of a highlight candidate before reframing or rendering.
- **Original Workflow:** User drags boundary handles on the highlight scrub bar or types exact seconds in Start/End inputs; updates candidate duration.
- **Original UI Location:** Candidate card trim controls.
- **Controls & Interactions:** Start time number input, End time number input, scrub handles.
- **Backend Behavior:** `PATCH /api/v1/projects/{pid}/highlights/{id}`.
- **Data Requirements:** `start_time` and `end_time` floats.
- **Processing Algorithms:** Duration recalculation and boundary validation.
- **Dependencies:** `highlights.py` route.
- **Historical Evidence:** Surviving `README.md` and Milestone 6 requirements.
- **Current ZezEdit 2.0 Status:** Implemented in `HighlightsWorkspace.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve manual boundary adjustments.
- **Verification Method:** Boundary update test.

#### `ZEZ-039`: One-Click "Render This Short" Action
- **Original Purpose:** Directly initiate rendering for an individual approved candidate without navigating away.
- **Original Workflow:** User clicks "Render Short" on a candidate card; dispatches render job with default vertical 9:16 preset; navigates to Shorts Export tab with job progress.
- **Original UI Location:** Primary button on highlight candidate card.
- **Controls & Interactions:** "Render Short" button.
- **Backend Behavior:** `POST /api/v1/projects/{pid}/exports/render` with `candidate_id`.
- **Data Requirements:** Render job parameters.
- **Dependencies:** `render_service.py`.
- **Historical Evidence:** Surviving `README.md` ("Render This Short on-demand button").
- **Current ZezEdit 2.0 Status:** Implemented in `HighlightsWorkspace.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve one-click render trigger.
- **Verification Method:** Render dispatch test.

#### `ZEZ-040`: Candidate Exclusion & Overlap Suppression
- **Original Purpose:** Prevent generating 5 nearly-identical clips from the same 20-second monologue.
- **Original Workflow:** Non-maximum suppression algorithm suppresses any candidate that overlaps $>30\%$ with a higher-scoring candidate.
- **Original UI Location:** Automated filtering during discovery.
- **Backend Behavior:** `_suppress_overlapping_candidates()` in `highlight_scoring.py`.
- **Data Requirements:** Start and end timestamps array.
- **Processing Algorithms:** Temporal Intersection-over-Union (IoU) suppression.
- **Dependencies:** Python sorting and filtering logic.
- **Historical Evidence:** Surviving `README.md` ("Temporal clustering eliminates overlapping clips").
- **Current ZezEdit 2.0 Status:** Implemented in `highlight_scoring.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve overlap suppression.
- **Verification Method:** Pytest overlap suppression test.

---

### Domain F: Smart Reframing & Subject Tracking (`ZEZ-041` – `ZEZ-055`)

#### `ZEZ-041`: OpenCV Haar Cascade Subject Detection (13M.12)
- **Original Purpose:** Detect human faces, profile faces, and upper bodies locally on CPU without heavy GPU models.
- **Original Workflow:** Subprocess samples video frames; passes images to OpenCV `CascadeClassifier` (`haarcascade_frontalface_default.xml`, `haarcascade_profileface.xml`, `haarcascade_upperbody.xml`); outputs bounding boxes.
- **Original UI Location:** Background detection stage for reframing.
- **Backend Behavior:** `SubjectTracker.detect_frame_subjects()`.
- **Data Requirements:** List of `DetectedSubject(timestamp, box_x, box_y, box_w, box_h, confidence, category)`.
- **Processing Algorithms:** Multi-scale Haar feature cascade evaluation with non-maximum suppression.
- **Dependencies:** OpenCV (`cv2`) with packaged Haar XML files in `backend/app/resources/models/`.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Section A (Root Cause A/B/C fixes) and `tracking.py`.
- **Current ZezEdit 2.0 Status:** Implemented in `backend/app/services/subject_tracker.py`.
- **Exact Differences:** None. Real OpenCV Haar cascades packaged and tested.
- **Restoration Requirement:** Preserve Haar cascade detection engine.
- **Verification Method:** Pytest `test_milestone7_reframing.py`.

#### `ZEZ-042`: Dual-Axis Exponential Moving Average Smoothing (13M.12)
- **Original Purpose:** Prevent camera jitter and abrupt lateral snapping when subjects move slightly or facial detections fluctuate.
- **Original Workflow:** Subject positions smoothed across time using calibrated separate horizontal and vertical exponential smoothing factors.
- **Original UI Location:** Reframing camera motion.
- **Backend Behavior:**
  $$\hat{x}_t = \alpha_x x_t + (1 - \alpha_x) \hat{x}_{t-1}, \quad \alpha_x = 0.32$$
  $$\hat{y}_t = \alpha_y y_t + (1 - \alpha_y) \hat{y}_{t-1}, \quad \alpha_y = 0.20$$
- **Data Requirements:** Time-series of raw subject coordinates.
- **Processing Algorithms:** Separate horizontal ($\alpha_x = 0.32$) and vertical ($\alpha_y = 0.20$) EMA filters.
- **Dependencies:** `framing_engine.py`.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Workstream 1.
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/services/framing_engine.py`.
- **Exact Differences:** None. Exact 13M.12 smoothing constants verified.
- **Restoration Requirement:** Preserve dual-axis EMA filter.
- **Verification Method:** Mathematical unit test in `test_reframing.py`.

#### `ZEZ-043`: Strict Velocity Clamping (13M.12)
- **Original Purpose:** Ensure the simulated camera pan never moves faster than realistic human camera operator speeds.
- **Original Workflow:** Limits maximum lateral displacement between consecutive keyframe samples:
  $$|\Delta x| \le \max(0.08, 0.45 \cdot \Delta t)$$
- **Backend Behavior:** Clamps delta displacement in `FramingEngine._smooth_trajectory()`.
- **Data Requirements:** Delta time $\Delta t$ and current displacement $\Delta x$.
- **Processing Algorithms:** Clamping function bounded by velocity threshold.
- **Dependencies:** `framing_engine.py`.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Workstream 1.
- **Current ZezEdit 2.0 Status:** Fully operational in `framing_engine.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve velocity clamping.
- **Verification Method:** Verified in `test_moving_subject_following_with_velocity_clamping`.

#### `ZEZ-044`: Boundary Safety Containment (13M.12)
- **Original Purpose:** Guarantee that the 9:16 portrait crop rectangle never spills outside the boundaries of the source video frame.
- **Original Workflow:** Center coordinate $x_t$ clamped within valid half-crop margins:
  $$x_t \in \left[\frac{w_{\text{crop}}}{2 W}, 1 - \frac{w_{\text{crop}}}{2 W}\right]$$
- **Backend Behavior:** Hard clamping applied in `FramingEngine.generate_framing_keyframes()`.
- **Data Requirements:** Crop dimensions $w_{\text{crop}}, h_{\text{crop}}$ and source dimensions $W, H$.
- **Processing Algorithms:** Mathematical bounding box containment.
- **Dependencies:** `framing_engine.py`.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md`.
- **Current ZezEdit 2.0 Status:** Fully operational in `framing_engine.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve boundary clamping.
- **Verification Method:** Verified in `test_crop_bounds_and_safety_clamping`.

#### `ZEZ-045`: Conversational Two-Person Joint Framing (13M.12)
- **Original Purpose:** Keep both speakers in frame simultaneously during a two-person dialogue rather than rapid camera jumping or degrading to blur padding.
- **Original Workflow:** When two subjects are detected talking, algorithm calculates their joint conversational midpoint $(group\_cx, group\_cy)$ and adjusts zoom to encompass both.
- **Original UI Location:** Smart Reframing strategy indicator "Two-Person".
- **Backend Behavior:** `select_target_subject()` in `framing_engine.py` with split threshold 0.78 for wide, 0.68 otherwise.
- **Data Requirements:** List of active subject tracks.
- **Processing Algorithms:** Group bounding box centroid calculation with separation thresholding.
- **Dependencies:** `framing_engine.py`.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Workstream 2 and contact sheet `scenario_2_two_person_contact_sheet.jpg`.
- **Current ZezEdit 2.0 Status:** Fully operational in `framing_engine.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve joint two-person framing.
- **Verification Method:** Verified in `test_two_person_dialogue_joint_framing`.

#### `ZEZ-046`: Scene-Cut Boundary Clamping & Instant Reset (13M.12)
- **Original Purpose:** Prevent camera panning from dragging awkwardly across scene cuts and causing viewer disorientation.
- **Original Workflow:** When a scene cut occurs, the smoothing state vector is instantly reset to the new shot's subject position without interpolating across the cut.
- **Original UI Location:** Keyframe timeline scene boundary markers.
- **Backend Behavior:** `scene_cut_timestamps` array resets EMA history in `framing_engine.py`.
- **Data Requirements:** List of scene cut timestamps from `video_scenes`.
- **Processing Algorithms:** Hard discontinuity reset at $t \in scene\_cuts$.
- **Dependencies:** `framing_engine.py`.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Workstream 4.
- **Current ZezEdit 2.0 Status:** Fully operational in `framing_engine.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve cut-aware camera reset.
- **Verification Method:** Verified in `test_scene_cut_instant_reset_without_dragging`.

#### `ZEZ-047`: Full-Width Fallback Scaling Layout (13M.12)
- **Original Purpose:** Eliminate the "shrunken postage-stamp" layout where a 16:9 video was scaled down to 1080x608 inside blurred filler.
- **Original Workflow:** When blurred background is explicitly selected or required for extreme crowd scenes, foreground video is scaled to full portrait width (`scale=1080:-2:flags=lanczos`), occupying the full 1080px width with natural headroom.
- **Original UI Location:** Rendered Short layout.
- **Backend Behavior:** Filtergraph builds `scale=1080:-2` overlay on `boxblur=25:5` background.
- **Data Requirements:** 1080x1920 portrait canvas.
- **Processing Algorithms:** Dual-stream FFmpeg filtergraph with Lanczos scaling.
- **Dependencies:** `reframing_renderer.py`.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Root Cause C fix and contact sheet `scenario_3_baseline_vs_new_contact_sheet.jpg`.
- **Current ZezEdit 2.0 Status:** Implemented in `reframing_renderer.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve full-width scaling layout.
- **Verification Method:** Visual inspection of blurred fallback renders.

#### `ZEZ-048`: Structured Tracking Telemetry & Diagnostics JSON (13M.12)
- **Original Purpose:** Guarantee that tracking operates transparently with auditable records of trajectory coordinates, zoom values, and quality scores.
- **Original Workflow:** Alongside each rendered `{short_id}.mp4`, a `{short_id}_diagnostics.json` file is written containing timestamps, crop coordinates, sample count, and framing quality score.
- **Original UI Location:** UI tracking status pill and diagnostics tab.
- **Backend Behavior:** `ReframingRenderer` saves JSON payload to disk and database.
- **Data Requirements:** JSON telemetry dictionary.
- **Dependencies:** `reframing_renderer.py`.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Workstream 5.
- **Current ZezEdit 2.0 Status:** Implemented in `reframing_service.py` and `export_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve structured telemetry JSON generation.
- **Verification Method:** Check `{short_id}_diagnostics.json` written to disk.

#### `ZEZ-049`: UI Tracking Status Pill (13M.12)
- **Original Purpose:** Inform the creator whether dynamic tracking or blur fallback was used on each rendered short.
- **Original Workflow:** Short cards display live badge:
  - When reframed: `🎯 Dynamic Tracking (34 samples · 95% quality)`
  - When blur fallback: `🌫 Blur Fill (Extreme subject split)`
- **Original UI Location:** Short cards in `ProjectDetailPage.tsx` / `HighlightsWorkspace.tsx`.
- **Backend Behavior:** Included in `RenderedShort` API response.
- **Data Requirements:** `framing_strategy` and `quality_score`.
- **Dependencies:** Frontend badge component.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Workstream 6.
- **Current ZezEdit 2.0 Status:** Implemented in `HighlightsWorkspace.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve tracking status pill.
- **Verification Method:** Verified in browser screenshot `08_video_workspace_highlights.png`.

#### `ZEZ-050`: Dual-Viewport Reframing Review Modal (13M.13)
- **Original Purpose:** Allow creators to inspect the 9:16 crop box over the original 16:9 widescreen video side-by-side with the final portrait preview.
- **Original Workflow:** User clicks "Review Framing"; modal opens with:
  - Left Viewport: 16:9 source footage with semi-transparent dark mask and highlighted 9:16 crop rectangle.
  - Right Viewport: Synchronized 9:16 portrait preview showing exact rendered composition.
- **Original UI Location:** `ReframingReviewModal.tsx` (42,365 bytes).
- **Controls & Interactions:** Play/Pause button, timeline scrubber, synchronized playheads.
- **Backend Behavior:** `GET /projects/{pid}/shorts/{sid}/reframing/inspection`, `GET .../preview-frame`.
- **Data Requirements:** Plan keyframes, source dimensions, aspect ratio.
- **Processing Algorithms:** CSS percentage-based bounding box positioning matching backend math.
- **Dependencies:** React, Lucide-React.
- **Historical Evidence:** Preserved in full in `transcript_full.jsonl` Line 47525 (`ReframingReviewModal.tsx`).
- **Current ZezEdit 2.0 Status:** Currently, `ReframingWorkspace.tsx` provides portrait preview and static crop box.
- **Exact Differences:** Interactive dual-viewport draggable canvas overlay needs full restoration.
- **Restoration Requirement:** Integrate the 13M.13 `ReframingReviewModal` dual-viewport canvas into `ReframingWorkspace.tsx`.
- **Verification Method:** Browser testing with live video playback.

#### `ZEZ-051`: Interactive On-Canvas Draggable 9:16 Crop Rectangle (13M.13)
- **Original Purpose:** Enable direct visual repositioning of the vertical crop box by dragging it horizontally over the 16:9 source video.
- **Original Workflow:** User clicks and drags the crop rectangle on the source viewport; horizontal position updates in real-time; right portrait preview updates instantaneously; creates or updates a manual keyframe at the current timestamp.
- **Original UI Location:** Left viewport in reframing review modal.
- **Controls & Interactions:** Mouse drag, touch drag, cursor `move`.
- **Backend Behavior:** Client-side drag handler calculates normalized `center_x` in `[crop_half_w, 1.0 - crop_half_w]`.
- **Data Requirements:** Bounding box coordinates $[x, y, w, h]$.
- **Processing Algorithms:** Pointer event tracking with aspect-ratio containment.
- **Dependencies:** React DOM pointer events.
- **Historical Evidence:** Preserved in `ReframingReviewModal.tsx` in `transcript_full.jsonl`.
- **Current ZezEdit 2.0 Status:** Missing in 2.0 (sliders exist, but direct canvas dragging is absent).
- **Exact Differences:** Direct on-canvas dragging needs restoration.
- **Restoration Requirement:** Restore interactive pointer drag handler on source canvas.
- **Verification Method:** Drag interaction test in browser.

#### `ZEZ-052`: Timeline Keyframe Diamond Scrubber (13M.13)
- **Original Purpose:** Visualize all framing keyframes along the video timeline and allow individual keyframe selection and editing.
- **Original Workflow:** Timeline scrubber displays diamond markers (`◆`):
  - Blue diamonds: AI automatic tracking keyframes.
  - Amber diamonds: Manual user override keyframes.
  - Gray vertical lines: Scene cut transition points.
  Clicking a diamond jumps the playhead to that exact timestamp and populates the Pan/Zoom/Headroom sliders with that keyframe's values.
- **Original UI Location:** Scrubber track beneath viewports in `ReframingReviewModal.tsx`.
- **Controls & Interactions:** Diamond marker click, "Add Keyframe at Playhead" (`+`) button, "Delete Keyframe" trash icon.
- **Backend Behavior:** Persists keyframe array to `manual_crop_overrides` table.
- **Data Requirements:** Array of `ManualCropKeyframe(timestamp, center_x, center_y, zoom, headroom)`.
- **Processing Algorithms:** Timestamp sorting and binary search interpolation.
- **Dependencies:** React SVG / canvas scrubber.
- **Historical Evidence:** Preserved in `ReframingReviewModal.tsx` in `transcript_full.jsonl`.
- **Current ZezEdit 2.0 Status:** Missing in 2.0 (timeline scrubber lacks individual diamond pins).
- **Exact Differences:** Keyframe diamond pins and click-to-edit controls must be restored.
- **Restoration Requirement:** Implement interactive keyframe diamond pins on reframing timeline.
- **Verification Method:** Keyframe addition, selection, and deletion test.

#### `ZEZ-053`: Manual Pan X, Headroom Y & Zoom Sliders (13M.13)
- **Original Purpose:** Provide fine-grained numeric slider control over framing parameters.
- **Original Workflow:** Sliders for:
  - **Pan X Position:** Shift crop left/right [-1.0 to +1.0 offset].
  - **Headroom Y:** Adjust space above subject's head [0.05 to 0.30].
  - **Zoom Scale:** Magnify subject [1.0x to 2.5x].
- **Original UI Location:** Controls sidebar in reframing review modal.
- **Controls & Interactions:** Range sliders with numeric text inputs and "Reset to Auto" button.
- **Backend Behavior:** Updates active keyframe and re-runs `interpolate_crop_at`.
- **Data Requirements:** Normalized parameter values.
- **Dependencies:** HTML5 range inputs.
- **Historical Evidence:** Preserved in `ReframingReviewModal.tsx` in `transcript_full.jsonl`.
- **Current ZezEdit 2.0 Status:** Partially available in `ReframingWorkspace.tsx`.
- **Exact Differences:** Need direct connection to selected keyframe timestamp.
- **Restoration Requirement:** Wire sliders directly to the active keyframe at the current playhead.
- **Verification Method:** Slider adjustment test.

#### `ZEZ-054`: Non-Destructive Reframing Revision Ledger (13M.13)
- **Original Purpose:** Ensure manual crop corrections never overwrite the original AI trajectory and allow rolling back or comparing revisions.
- **Original Workflow:** Saving corrections increments revision number (`Revision 1: AI Initial Framing`, `Revision 2: Manual Pan Adjustment`); user can open "Revision History" drawer, view change dates, and restore any previous revision.
- **Original UI Location:** Revision switcher drawer in reframing modal.
- **Controls & Interactions:** Revision list, "Activate Revision" button, "Reset to Original AI Framing" button.
- **Backend Behavior:** `POST .../reframing/overrides` creates record in `reframing_revisions` table; updates `active_revision_id` in `reframing_plans`.
- **Data Requirements:** `reframing_revisions` table (id, plan_id, revision_number, label, manual_overrides_json, effective_keyframes_json).
- **Processing Algorithms:** Non-destructive revision branching.
- **Dependencies:** SQLite table.
- **Historical Evidence:** Preserved in `backend/app/models/db.py` line 47328 and `ReframingReviewModal.tsx`.
- **Current ZezEdit 2.0 Status:** Backend `reframing_revisions` table exists; frontend revision drawer needs UI restoration.
- **Exact Differences:** Frontend revision switcher drawer needs to be exposed in `ReframingWorkspace.tsx`.
- **Restoration Requirement:** Restore revision history drawer in Reframing Workspace.
- **Verification Method:** Revision save, switch, and rollback test.

#### `ZEZ-055`: Authoritative Preview-to-Render Mathematical Parity (13M.12/13M.13)
- **Original Purpose:** Guarantee that what the creator sees in the browser preview is mathematically identical to the rendered MP4 output pixel-for-pixel.
- **Original Workflow:** Single math source of truth: `FramingEngine.interpolate_crop_at()` computes exact integer crop bounds `[crop_x, crop_y, crop_w, crop_h]`. Both frontend preview and FFmpeg filtergraph consume this identical function.
- **Backend Behavior:** `GET /projects/{pid}/reframing/{plan_id}/crop-at?timestamp={t}` returns exact crop coordinates.
- **Data Requirements:** Keyframe interpolation equations.
- **Processing Algorithms:** Piecewise-linear interpolation with boundary clamping.
- **Dependencies:** `framing_engine.py`, `reframing_renderer.py`.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Workstream 3.
- **Current ZezEdit 2.0 Status:** Implemented in `backend/app/services/reframing_service.py` (`preview_crop_at`).
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve mathematical parity between preview and render.
- **Verification Method:** Automated parity verification test in `test_reframing.py`.

---

### Domain G: Shorts Generation & FFmpeg Rendering Engine (`ZEZ-056` – `ZEZ-068`)

#### `ZEZ-056`: Piecewise-Linear Dynamic FFmpeg Crop Filtergraph (13M.12)
- **Original Purpose:** Render smooth dynamic portrait camera movement without decoding all video frames into memory.
- **Original Workflow:** Renderer takes keyframes; generates dynamic FFmpeg crop expression using piecewise linear time functions:
  `crop=w={w}:h={h}:x='if(between(t,t0,t1), x0+(x1-x0)*(t-t0)/(t1-t0), ...)'`
- **Backend Behavior:** `ReframingRenderer.build_crop_filter_expression()`.
- **Data Requirements:** Keyframe timestamps and coordinates.
- **Processing Algorithms:** Collinear keyframe simplification and expression compilation.
- **Dependencies:** FFmpeg binary.
- **Historical Evidence:** Verified in `milestone_13m12_verification_report.md` Section C.
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/services/reframing_renderer.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve piecewise-linear filtergraph builder.
- **Verification Method:** Pytest filtergraph generation test.

#### `ZEZ-057`: Burned-in Subtitles & Karaoke Word-Level ASS Styling
- **Original Purpose:** Generate engaging mobile captions burned into video with customizable colors, fonts, and word-level karaoke highlight animations.
- **Original Workflow:** Converts Whisper transcript words into Advanced SubStation Alpha (`.ass`) subtitle script; uses FFmpeg `ass={subtitle_path}` filter.
- **Original UI Location:** Shorts & Export Studio caption options.
- **Controls & Interactions:** Subtitle style preset picker (Classic, Boxed, Bold Bounce), font size, primary/secondary colors.
- **Backend Behavior:** `ExportService._generate_ass_subtitles()`.
- **Data Requirements:** `.ass` file format with `{\k<duration>}` karaoke tags.
- **Processing Algorithms:** ASS script generation with coordinate placement.
- **Dependencies:** FFmpeg with `libass` support.
- **Historical Evidence:** Surviving `README.md` ("Generates synchronized burned-in captions from speech timestamps").
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/services/export_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve ASS subtitle generator.
- **Verification Method:** Pytest subtitle export test.

#### `ZEZ-058`: Professional Audio Processing & EBU R128 Loudness Normalization
- **Original Purpose:** Ensure exported Shorts meet streaming platform audio standards without clipping or quiet dialogue.
- **Original Workflow:** FFmpeg filter applies `loudnorm=I=-16:TP=-1.5:LRA=11` (EBU R128 standard) and encodes AAC audio at 128 kbps.
- **Backend Behavior:** Audio filtergraph configuration in `export_service.py`.
- **Data Requirements:** Audio stream.
- **Processing Algorithms:** Two-pass or integrated single-pass EBU R128 loudness normalization.
- **Dependencies:** FFmpeg binary.
- **Historical Evidence:** `backend/app/services/export_service.py`.
- **Current ZezEdit 2.0 Status:** Operational in `export_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve audio normalization.
- **Verification Method:** Export render verification test.

#### `ZEZ-059`: Export Presets & Aspect Ratio Conversion
- **Original Purpose:** Provide one-click export configurations for vertical Shorts (`9:16` 1080x1920), square Reels/Posts (`1:1` 1080x1080), and landscape standard (`16:9` 1920x1080).
- **Original Workflow:** User selects preset; sets encoding speed vs quality (Fast, Balanced, High Quality); starts render.
- **Original UI Location:** Video Workspace "Shorts & Export" sub-tab.
- **Controls & Interactions:** Preset radio buttons, resolution dropdown, CRF slider.
- **Backend Behavior:** Maps preset to FFmpeg encoding parameters (`preset`, `crf`, `b:v`).
- **Data Requirements:** Export job schema.
- **Dependencies:** `export_service.py`.
- **Historical Evidence:** Surviving `README.md` and `test_milestone8_export.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `ExportStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve export presets.
- **Verification Method:** Verified in browser screenshot `10_video_workspace_exports.png`.

#### `ZEZ-060`: Strict Multi-Point Output Validation Gate
- **Original Purpose:** Prevent corrupt, zero-byte, or glitchy video files from being presented to the user.
- **Original Workflow:** After FFmpeg completes, validator checks:
  1. File exists on disk and size $> 10$ KB.
  2. FFprobe confirms valid MP4 container and H.264 video stream.
  3. Video resolution matches target exactly (e.g. 1080x1920).
  4. Audio stream is present and valid.
  5. Video duration is positive.
  6. Decode integrity test (`ffmpeg -v error -i <file> -f null -`) passes with zero decode errors.
- **Backend Behavior:** `RenderValidationService.validate_output()`.
- **Data Requirements:** Rendered MP4 file.
- **Processing Algorithms:** Automated multi-point inspection gate.
- **Dependencies:** FFprobe and FFmpeg.
- **Historical Evidence:** Surviving `README.md` Section 2 ("Strict Multi-Point Output Validation").
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/services/export_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve strict output validation gate.
- **Verification Method:** Pytest render validation tests.

#### `ZEZ-061`: Poster Frame Cover Thumbnail Extraction
- **Original Purpose:** Generate high-quality JPEG poster frame for video players and social media preview cards.
- **Original Workflow:** FFmpeg extracts frame at 0.5s or midpoint; saves to `storage/exports/{export_id}_cover.jpg`.
- **Backend Behavior:** `GET /projects/{pid}/exports/{id}/cover`.
- **Data Requirements:** JPEG image on disk.
- **Dependencies:** FFmpeg binary.
- **Historical Evidence:** Surviving `README.md` ("Extracts cover frame poster thumbnail").
- **Current ZezEdit 2.0 Status:** Operational in `export_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve cover thumbnail extraction.
- **Verification Method:** Check cover thumbnail endpoint response.

#### `ZEZ-062`: Render Progress Monitoring via FFmpeg `-progress` Pipe
- **Original Purpose:** Show accurate real-time percentage progress and ETA during video rendering.
- **Original Workflow:** FFmpeg writes progress to pipe; backend worker parses `out_time_ms` vs total duration; updates job `progress_pct` in SQLite.
- **Original UI Location:** Progress bar on export card.
- **Backend Behavior:** Background worker pipes stdout/stderr.
- **Data Requirements:** `jobs.progress_pct` column.
- **Processing Algorithms:** Linear percentage calculation $(t_{\text{current}} / t_{\text{total}}) \cdot 100$.
- **Dependencies:** FFmpeg progress protocol.
- **Historical Evidence:** `backend/app/services/jobs.py` and `export_service.py`.
- **Current ZezEdit 2.0 Status:** Fully operational.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve real-time progress monitoring.
- **Verification Method:** Job progress polling test.

#### `ZEZ-063`: Graceful Render Job Cancellation
- **Original Purpose:** Allow the creator to cancel a long-running render job immediately without leaving orphan processes or corrupted files.
- **Original Workflow:** User clicks "Cancel"; backend sends `SIGTERM` to FFmpeg process; transitions job to `cancelled`; cleans up temporary output files.
- **Original UI Location:** Cancel button on running export card.
- **Backend Behavior:** `POST /api/v1/jobs/{id}/cancel`.
- **Data Requirements:** Running process PID stored in `JobItem`.
- **Processing Algorithms:** Process tree termination and temp file removal.
- **Dependencies:** `jobs.py`.
- **Historical Evidence:** `test_milestone2_core.py` (`test_job_cancellation`).
- **Current ZezEdit 2.0 Status:** Fully operational in `JobOrchestrator`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve graceful job cancellation.
- **Verification Method:** Automated cancellation test.

#### `ZEZ-064`: Non-Destructive Rendered Short Versioning (`_rev{N}.mp4`)
- **Original Purpose:** Ensure re-rendering a short with new framing or captions does not overwrite previous renders.
- **Original Workflow:** Each render generates `short_{id}_rev1.mp4`, `short_{id}_rev2.mp4`; tracked in `rendered_short_versions` table.
- **Original UI Location:** Version badge on short card (e.g. `v1.2`).
- **Backend Behavior:** Version incrementing in `export_service.py`.
- **Data Requirements:** `rendered_short_versions` table.
- **Dependencies:** SQLite table.
- **Historical Evidence:** Preserved in `backend/app/models/db.py` line 47328 and `test_milestone13m13_reframing_review.py`.
- **Current ZezEdit 2.0 Status:** Currently, exports are stored as separate export records.
- **Exact Differences:** Dedicated version association on shorts candidate cards needs restoration.
- **Restoration Requirement:** Link multiple render revisions directly to the candidate entity.
- **Verification Method:** Re-render versioning test.

#### `ZEZ-065`: Interactive HTML5 Video Preview Player
- **Original Purpose:** Instant in-browser playback of completed 9:16 vertical shorts with audio.
- **Original Workflow:** User clicks short card; modal video player opens with play/pause, scrub bar, volume, fullscreen, and download button.
- **Original UI Location:** Playable Shorts Gallery in Video Workspace.
- **Controls & Interactions:** Video player controls, download action, favorite toggle.
- **Backend Behavior:** `GET /projects/{pid}/exports/{id}/stream` with HTTP 206 partial content range support.
- **Data Requirements:** MP4 file streaming.
- **Dependencies:** HTML5 `<video>` tag with range request support.
- **Historical Evidence:** Surviving `README.md` ("HTML5 video preview player for finished 9:16 vertical shorts").
- **Current ZezEdit 2.0 Status:** Fully operational in `VideoWorkspace.tsx` and `ExportStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve video preview player.
- **Verification Method:** Verified in browser screenshot `04_video_workspace_overview.png`.

#### `ZEZ-066`: One-Click MP4 Download Action
- **Original Purpose:** Download finished video file directly to user's local Downloads folder.
- **Original Workflow:** User clicks "Download" button on export card; browser initiates standard file download.
- **Original UI Location:** Download button on export card.
- **Backend Behavior:** `GET /projects/{pid}/exports/{id}/download` with `Content-Disposition: attachment`.
- **Dependencies:** FastAPI `FileResponse`.
- **Historical Evidence:** Surviving `README.md` ("download rendered MP4").
- **Current ZezEdit 2.0 Status:** Fully operational.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve download endpoint.
- **Verification Method:** HTTP download header check.

#### `ZEZ-067`: Duplicate Render Prevention
- **Original Purpose:** Prevent spawning multiple duplicate render jobs if the user accidentally clicks the render button twice.
- **Original Workflow:** System checks if an identical render job is already queued or running; returns existing job ID if active.
- **Backend Behavior:** In-flight job deduplication check in `export_service.py`.
- **Dependencies:** `JobOrchestrator`.
- **Historical Evidence:** `test_milestone13m13_reframing_review.py` ("Duplicate render prevention").
- **Current ZezEdit 2.0 Status:** Implemented in `JobOrchestrator`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve render deduplication.
- **Verification Method:** Duplicate render dispatch test.

#### `ZEZ-068`: Render History Drawer & Storage Inspection
- **Original Purpose:** Allow the user to review all previous renders in a project, inspect disk usage, and delete unwanted test renders.
- **Original UI Location:** "Export History" tab in Export Studio.
- **Controls & Interactions:** Render list, delete button, disk space indicator.
- **Backend Behavior:** `GET /projects/{pid}/exports`, `DELETE /projects/{pid}/exports/{id}`.
- **Dependencies:** SQLite table and storage service.
- **Historical Evidence:** `ExportStudio.tsx` and surviving `README.md`.
- **Current ZezEdit 2.0 Status:** Operational in `ExportStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve export history management.
- **Verification Method:** Verified in browser screenshot `10_video_workspace_exports.png`.

---

### Domain H: Multi-Track Timeline & Conversational AI Video Editor (`ZEZ-069` – `ZEZ-080`)

#### `ZEZ-069`: Multi-Track Timeline NLE Canvas
- **Original Purpose:** Provide a CapCut/Premiere-style non-linear editing canvas with multiple independent media tracks.
- **Original Workflow:** 4 distinct tracks:
  - **Track V2 (Overlay):** Text titles, captions, watermarks, stickers.
  - **Track V1 (Main Video):** Primary video clips with trim and split points.
  - **Track A1 (Source Audio):** Original synced video audio with volume slider.
  - **Track A2 (Music / BGM):** Background music track with volume and ducking.
- **Original UI Location:** Video Workspace "Timeline Editor" sub-tab (`TimelineEditor.tsx`).
- **Controls & Interactions:** Timeline track headers, mute/solo buttons, zoom slider, track expand/collapse.
- **Backend Behavior:** `GET/POST /api/v1/projects/{pid}/timeline`.
- **Data Requirements:** `timelines`, `timeline_tracks`, `timeline_clips` tables.
- **Processing Algorithms:** Multi-track timeline state model.
- **Dependencies:** `timeline_service.py`.
- **Historical Evidence:** `test_milestone9_timeline.py` and `TimelineEditor.tsx`.
- **Current ZezEdit 2.0 Status:** Fully operational in `frontend/src/features/timeline/TimelineEditor.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve 4-track timeline canvas.
- **Verification Method:** Verified in browser screenshot `11_video_workspace_timeline.png`.

#### `ZEZ-070`: Non-Destructive Clip Trimming & Splitting
- **Original Purpose:** Cut video clips into segments and adjust in/out points without altering source media.
- **Original Workflow:** User moves playhead to desired split point; clicks "Split Clip" (Razor tool `Ctrl+K`); clip splits into two independent clips; user can drag clip edges to trim in/out points.
- **Original UI Location:** Timeline toolbar and clip boundary handles.
- **Controls & Interactions:** Split tool button, edge drag trim handles, delete clip button.
- **Backend Behavior:** `POST .../timeline/clips/{id}/split`, `PATCH .../timeline/clips/{id}/trim`.
- **Data Requirements:** `start_time`, `end_time`, `in_point`, `out_point` in `timeline_clips`.
- **Processing Algorithms:** Non-destructive offset recalculation.
- **Dependencies:** `timeline_service.py`.
- **Historical Evidence:** `test_milestone9_timeline.py` (`test_clip_splitting_and_trimming`).
- **Current ZezEdit 2.0 Status:** Fully operational in `timeline_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve clip trimming and splitting operations.
- **Verification Method:** Automated timeline test in Pytest.

#### `ZEZ-071`: Ripple Delete & Gap Closing
- **Original Purpose:** Automatically shift trailing clips forward when a middle clip is deleted to avoid unwanted black gaps.
- **Original Workflow:** User selects clip; clicks "Ripple Delete"; clip is removed and all following clips on Track V1 shift left by the deleted duration.
- **Original UI Location:** Timeline context menu / toolbar.
- **Backend Behavior:** `POST .../timeline/clips/{id}/ripple-delete`.
- **Data Requirements:** Updated clip start times.
- **Processing Algorithms:** Sequential offset adjustment along the track timeline.
- **Dependencies:** `timeline_service.py`.
- **Historical Evidence:** `timeline_service.py`.
- **Current ZezEdit 2.0 Status:** Implemented in `timeline_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve ripple delete.
- **Verification Method:** Pytest ripple delete test.

#### `ZEZ-072`: Synchronized Playhead & Real-Time Timeline Scrubbing
- **Original Purpose:** Scrub playback along the timeline with immediate video frame preview update.
- **Original Workflow:** Dragging the playhead ruler updates current timecode and updates preview player frame instantaneously.
- **Original UI Location:** Timeline timecode ruler.
- **Controls & Interactions:** Playhead needle, timecode ruler, spacebar Play/Pause shortcut.
- **Backend Behavior:** Fast proxy video seeking.
- **Data Requirements:** Float `currentTime` synchronized with HTML5 player.
- **Processing Algorithms:** RequestAnimationFrame playhead interpolation.
- **Dependencies:** React player sync.
- **Historical Evidence:** `TimelineEditor.tsx`.
- **Current ZezEdit 2.0 Status:** Fully operational in `TimelineEditor.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve playhead scrubbing.
- **Verification Method:** Verified in browser screenshot `11_video_workspace_timeline.png`.

#### `ZEZ-073`: Persistent Timeline Undo & Redo History
- **Original Purpose:** Allow the user to revert any timeline mistake (accidental split, delete, trim) without data loss.
- **Original Workflow:** User presses `Ctrl+Z` (Undo) or `Ctrl+Y` (Redo); timeline restores previous state snapshot.
- **Original UI Location:** Timeline toolbar Undo/Redo buttons.
- **Controls & Interactions:** Undo button, Redo button, keyboard shortcuts.
- **Backend Behavior:** `POST .../timeline/undo`, `POST .../timeline/redo`.
- **Data Requirements:** `timeline_history` table storing serialized state snapshots.
- **Processing Algorithms:** Reversible command pattern with transaction stack.
- **Dependencies:** `timeline_service.py`.
- **Historical Evidence:** `test_milestone9_timeline.py` (`test_undo_redo_stack`).
- **Current ZezEdit 2.0 Status:** Fully operational in `timeline_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve undo/redo history.
- **Verification Method:** Automated undo/redo Pytest test.

#### `ZEZ-074`: Multi-Track Timeline FFmpeg Rendering Integration
- **Original Purpose:** Render the complete multi-track timeline (video clips, audio mixing, overlays) into a finished video file.
- **Original Workflow:** User clicks "Render Timeline"; backend constructs complex multi-input FFmpeg filtergraph with `concat`, `amix`, and `overlay` filters; exports final video.
- **Original UI Location:** Timeline Editor header action "Export Timeline".
- **Backend Behavior:** `POST .../timeline/render`.
- **Data Requirements:** Full timeline track and clip JSON structure.
- **Processing Algorithms:** Dynamic FFmpeg filtergraph construction across tracks.
- **Dependencies:** `timeline_service.py`, `renderer.py`.
- **Historical Evidence:** `test_milestone9_timeline.py` (`test_timeline_render_pipeline`).
- **Current ZezEdit 2.0 Status:** Fully operational in `timeline_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve timeline render integration.
- **Verification Method:** Automated timeline render test.

#### `ZEZ-075`: Conversational AI Video Editing Assistant (`ChatEditorService`)
- **Original Purpose:** Allow creators to edit video projects by giving instructions in natural English (e.g. *"Remove the first 3 seconds"*, *"Make captions larger (font size 56)"*, *"Use blurred background fill"*, *"Make this clip around 25 seconds"*).
- **Original Workflow:** User types prompt into AI Editor chat panel; assistant parses intent, generates proposed `EditPlan`, presents plan for review, and applies validated operations.
- **Original UI Location:** Video Workspace AI Editor tab / `ChatEditorPanel.tsx`.
- **Controls & Interactions:** Chat message stream, prompt input, suggestion pills.
- **Backend Behavior:** `POST /api/v1/projects/{pid}/ai-chat/message`.
- **Data Requirements:** `conversations` and `chat_messages` tables.
- **Processing Algorithms:** Intent parsing via Ollama (`qwen3-vl:4b-instruct`) with regex/heuristic fallback.
- **Dependencies:** `chat_editor_service.py`, `edit_plan_builder.py`.
- **Historical Evidence:** Surviving `README.md` Section 2 ("Conversational AI Video Editing") and `test_milestone13m4_agentic_editor.py` (32 tests pass).
- **Current ZezEdit 2.0 Status:** Integrated in `TimelineEditor.tsx` AI Assistant panel.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve conversational AI editing pipeline.
- **Verification Method:** Pytest `test_milestone9_timeline.py` AI assistant tests.

#### `ZEZ-076`: Interactive Clarification Interface & Choice Cards
- **Original Purpose:** Prevent the AI from making destructive guesses when user instructions are ambiguous or multi-modal.
- **Original Workflow:** When prompt is ambiguous, assistant renders interactive choice cards in chat: Recommended option, Alternative option, "Let AI decide", "Explain differences", "Cancel"; clicking executes choice immediately.
- **Original UI Location:** Chat stream message item (`ChatMessageItemView.tsx`).
- **Controls & Interactions:** Selectable clickable card options.
- **Backend Behavior:** Emits structured `choices` payload in assistant response.
- **Data Requirements:** Choice schema with operation payloads.
- **Dependencies:** React chat item view.
- **Historical Evidence:** Surviving `README.md` Section 2 ("Interactive Clarification Interface & Choice Cards") and `src/test/chatMessageActions.test.tsx`.
- **Current ZezEdit 2.0 Status:** Implemented in `TimelineEditor.tsx` AI panel.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve choice cards interaction.
- **Verification Method:** Vitest `chatMessageActions.test.tsx`.

#### `ZEZ-077`: Three Configurable Autonomy Modes
- **Original Purpose:** Let the creator choose how much independence the AI editor has.
- **Original Workflow:** Creator selects mode:
  - **`auto`**: Direct execution. Modifies plan and renders immediately.
  - **`ask_when_uncertain`**: Solicits guidance via choice cards on ambiguous instructions.
  - **`review_changes_first`**: Generates proposed operations and requires explicit user sign-off before modifying the plan.
- **Original UI Location:** AI Chat settings header.
- **Controls & Interactions:** Autonomy mode dropdown selector.
- **Backend Behavior:** Stored in `conversations.autonomy_mode` in SQLite.
- **Dependencies:** `chat_editor_service.py`.
- **Historical Evidence:** Surviving `README.md` Section 2 ("Three Configurable Autonomy Modes").
- **Current ZezEdit 2.0 Status:** Fully operational in backend.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve 3 autonomy modes.
- **Verification Method:** Pytest autonomy mode execution tests.

#### `ZEZ-078`: Validated Intermediate Representation (`EditOperation`)
- **Original Purpose:** Ensure AI commands are strictly validated against project boundaries before any modification is applied.
- **Original Workflow:** AI prompt converts to typed Pydantic models: `TrimOperation`, `SplitOperation`, `DeleteOperation`, `CropOperation`, `CaptionStyleOperation`, `VolumeOperation`.
- **Backend Behavior:** Validates start/end times against source duration.
- **Data Requirements:** Pydantic `EditOperation` schemas.
- **Processing Algorithms:** Schema validation gate.
- **Dependencies:** Pydantic models.
- **Historical Evidence:** Surviving `README.md` and `test_milestone13m5_intents.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/schemas/timeline.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve typed `EditOperation` validation.
- **Verification Method:** Pytest schema validation tests.

#### `ZEZ-079`: Immutable EditPlan Versioning & Output Archival
- **Original Purpose:** Record every AI edit as an immutable version (`v1.1`, `v1.2`) to prevent data corruption.
- **Original Workflow:** Each edit writes a record to `edit_plan_versions`; previous renders are archived rather than overwritten.
- **Backend Behavior:** `POST .../edit-plans/apply` archives previous plan.
- **Data Requirements:** `edit_plan_versions` table.
- **Dependencies:** SQLite table.
- **Historical Evidence:** Surviving `README.md` Section 2 ("Immutable EditPlan Versioning & Output Archival").
- **Current ZezEdit 2.0 Status:** Implemented in `timeline_service.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve EditPlan versioning.
- **Verification Method:** Pytest versioning tests.

#### `ZEZ-080`: Interactive Version History Drawer in Chat Panel
- **Original Purpose:** Provide a visual drawer in the AI chat panel allowing the creator to inspect previous versions, preview earlier outputs, and restore with one click.
- **Original Workflow:** User clicks "Version History"; slide-over drawer lists all versions with timestamp and prompt that created them; user clicks "Restore v1.1".
- **Original UI Location:** Drawer toggle button in AI Chat panel.
- **Controls & Interactions:** Version list, Restore button, preview button.
- **Backend Behavior:** `POST .../edit-plans/versions/{vid}/restore`.
- **Data Requirements:** List of version records.
- **Dependencies:** React drawer component.
- **Historical Evidence:** Surviving `README.md` Section 2 ("Interactive Version History Drawer").
- **Current ZezEdit 2.0 Status:** Undo/redo buttons exist in Timeline; dedicated version drawer can be surfaced in the AI panel.
- **Exact Differences:** surfacing the version drawer UI in the AI editor panel.
- **Restoration Requirement:** Restore version history drawer in AI Editor panel.
- **Verification Method:** Version restoration test.

---

### Domain I: Character Extraction Studio & Scene Intelligence (`ZEZ-081` – `ZEZ-090`)

#### `ZEZ-081`: Evidence-Based Character Extraction Pipeline (Non-3D)
- **Original Purpose:** Detect character appearances across video scenes and group them into candidate profiles based on observed visual evidence without claiming 100% automated identity recognition.
- **Original Workflow:** Frame sampler extracts face/body crops; computes visual embeddings; clusters similar appearances; presents candidates for human review.
- **Original UI Location:** Video Workspace "Characters" sub-tab (`CharacterStudio.tsx`).
- **Backend Behavior:** `CharacterExtractionStudio.extract_characters()`.
- **Data Requirements:** `character_candidates` and `character_observations` tables.
- **Processing Algorithms:** OpenCV Haar face detection + spatial-temporal clustering.
- **Dependencies:** `character_extraction.py`.
- **Historical Evidence:** Master Requirements Module G ("Independent Character Extraction Studio & persistent Character Library (non-3D; evidence-based)") and `test_milestone10_characters.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `CharacterStudio.tsx`.
- **Exact Differences:** None. Matches evidence-based architecture.
- **Restoration Requirement:** Preserve evidence-based character extraction.
- **Verification Method:** Verified in browser screenshot `12_video_workspace_characters.png`.

#### `ZEZ-082`: Spatial-Temporal Candidate Clustering (DBSCAN)
- **Original Purpose:** Group recurring face appearances into coherent character candidate clusters.
- **Original Workflow:** Clusters detections by visual similarity and temporal proximity; assigns cluster confidence score.
- **Backend Behavior:** DBSCAN clustering algorithm in `character_extractor.py`.
- **Data Requirements:** Normalized detection feature vectors.
- **Processing Algorithms:** Density-based spatial clustering of applications with noise.
- **Dependencies:** `scikit-learn` or pure Python DBSCAN fallback.
- **Historical Evidence:** `test_milestone10_characters.py` and `test_milestone13m11_character_extraction_reliability.py` (14 tests pass).
- **Current ZezEdit 2.0 Status:** Fully operational in `backend/app/services/character_extractor.py`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve DBSCAN clustering algorithm.
- **Verification Method:** Pytest clustering verification test.

#### `ZEZ-083`: Character Observation Gallery & Thumbnails
- **Original Purpose:** Show creators every individual video frame where a character was detected so they can verify detection accuracy.
- **Original Workflow:** Clicking a character candidate opens observation thumbnail gallery with exact timestamps and bounding box crops.
- **Original UI Location:** Candidate detail panel in Character Studio.
- **Controls & Interactions:** Observation image grid, click to seek in video.
- **Backend Behavior:** Serves observation thumbnails from `storage/characters/{pid}/thumbs/`.
- **Data Requirements:** `character_observations` table records.
- **Dependencies:** SQLite table and image files.
- **Historical Evidence:** `CharacterStudio.tsx` and `test_milestone10_characters.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `CharacterStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve observation thumbnail gallery.
- **Verification Method:** Verified in browser screenshot `12_video_workspace_characters.png`.

#### `ZEZ-084`: Screen-Time Transparency Analytics
- **Original Purpose:** Distinguish between actual sampled frame screen time and continuous estimated screen time.
- **Original Workflow:** Displays both metrics: e.g. "Sampled Screen Time: 42.5s (85 samples) · Estimated Total: 112.0s".
- **Original UI Location:** Metrics badge on character candidate card.
- **Backend Behavior:** Calculated in `character_extractor.py`.
- **Data Requirements:** Timestamps and sample interval duration.
- **Processing Algorithms:** Sample count summation vs scene duration interpolation.
- **Dependencies:** Character candidate model.
- **Historical Evidence:** `docs/MASTER_REQUIREMENTS.md` Module G.
- **Current ZezEdit 2.0 Status:** Fully operational in `CharacterStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve screen-time transparency.
- **Verification Method:** Check metrics display on character card.

#### `ZEZ-085`: Unverified Dialogue Correlation with Disclaimer
- **Original Purpose:** Associate speech lines with characters who appear on screen while clearly labeling that automated speaker identification is unverified.
- **Original Workflow:** Queries intersecting Whisper transcript segments; displays speech snippets on character card with explicit badge: `⚠️ Unverified Speaker Association`.
- **Original UI Location:** Character card dialogue accordion.
- **Backend Behavior:** Temporal intersection query between `transcript_segments` and `character_observations`.
- **Data Requirements:** Intersecting text segments.
- **Processing Algorithms:** Time-interval overlap detection.
- **Dependencies:** SQLite query.
- **Historical Evidence:** `docs/MASTER_REQUIREMENTS.md` Module G.
- **Current ZezEdit 2.0 Status:** Implemented in `CharacterStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve dialogue correlation disclaimer.
- **Verification Method:** Dialogue correlation test in Pytest.

#### `ZEZ-086`: Human Review Controls: Inline Renaming
- **Original Purpose:** Allow the creator to replace auto-generated names (e.g. "Candidate #1") with the character's real name (e.g. "Shin-chan").
- **Original Workflow:** User clicks pencil icon on candidate card; types name; saves instantly.
- **Original UI Location:** Candidate card header.
- **Controls & Interactions:** Inline text edit input.
- **Backend Behavior:** `PATCH /api/v1/projects/{pid}/characters/candidates/{id}` with `name`.
- **Data Requirements:** Updated string in SQLite.
- **Dependencies:** SQLite column update.
- **Historical Evidence:** `CharacterStudio.tsx` and `test_milestone10_characters.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `CharacterStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve inline renaming.
- **Verification Method:** Rename candidate API test.

#### `ZEZ-087`: Human Review Controls: Confirm to Persistent Character Library
- **Original Purpose:** Promote a verified character candidate into the permanent, project-wide Character Library.
- **Original Workflow:** User clicks "Confirm to Library"; candidate transitions to confirmed character profile with persistent ID.
- **Original UI Location:** Primary green button on candidate card.
- **Controls & Interactions:** "Confirm Character" button.
- **Backend Behavior:** `POST /api/v1/projects/{pid}/characters/candidates/{id}/confirm`.
- **Data Requirements:** Creates record in `characters` library table.
- **Dependencies:** SQLite table.
- **Historical Evidence:** `CharacterStudio.tsx`.
- **Current ZezEdit 2.0 Status:** Fully operational in `CharacterStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve library confirmation.
- **Verification Method:** Confirm character API test.

#### `ZEZ-088`: Human Review Controls: Merge & Split Candidates
- **Original Purpose:** Correct clustering errors by merging two candidates that belong to the same person, or splitting disparate observations into a new candidate.
- **Original Workflow:** User selects Candidate A and Candidate B; clicks "Merge"; observations combine. Alternatively, user checks specific false observations; clicks "Split into New Candidate".
- **Original UI Location:** Multi-select action bar in Character Studio.
- **Controls & Interactions:** Merge dialog, Split button.
- **Backend Behavior:** `POST .../candidates/merge`, `POST .../candidates/split`.
- **Data Requirements:** Re-assigned `candidate_id` foreign keys in `character_observations`.
- **Dependencies:** SQLite updates.
- **Historical Evidence:** `test_milestone10_characters.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in backend service.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve merge and split controls.
- **Verification Method:** Merge and split unit tests.

#### `ZEZ-089`: Human Review Controls: Reject False-Positive Candidate
- **Original Purpose:** Remove background extras, statues, posters, or detection glitches from the character roster.
- **Original Workflow:** User clicks "Reject"; candidate is marked `status='rejected'` and hidden from library without deleting raw evidence.
- **Original UI Location:** Reject button on candidate card.
- **Backend Behavior:** `POST .../candidates/{id}/reject`.
- **Data Requirements:** `status` update in SQLite.
- **Dependencies:** SQLite column.
- **Historical Evidence:** `CharacterStudio.tsx`.
- **Current ZezEdit 2.0 Status:** Fully operational in `CharacterStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve rejection workflow.
- **Verification Method:** Reject candidate test.

#### `ZEZ-090`: Character Library JSON Export
- **Original Purpose:** Export the confirmed character roster, screen-time metrics, and observation timestamps for external storytelling or documentation.
- **Original Workflow:** User clicks "Export JSON"; browser downloads structured `character_library_{project_id}.json`.
- **Original UI Location:** Character Studio header action.
- **Controls & Interactions:** "Export JSON" button.
- **Backend Behavior:** `GET /projects/{pid}/characters/export-json`.
- **Data Requirements:** JSON export envelope with disclaimer.
- **Dependencies:** FastAPI endpoint.
- **Historical Evidence:** Master Requirements Module G and `test_milestone10_characters.py`.
- **Current ZezEdit 2.0 Status:** Fully operational in `CharacterStudio.tsx`.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve JSON export endpoint.
- **Verification Method:** Export JSON endpoint test.

---

### Domain J: System Infrastructure, Diagnostics & Reliability (`ZEZ-091` – `ZEZ-100`)

#### `ZEZ-091`: Forward-Only Versioned SQLite Migrations
- **Original Purpose:** Guarantee schema upgrades never drop user data or rely on dangerous binary bytecode loaders.
- **Original Workflow:** Startup runs migration runner; verifies `schema_migrations` table; applies missing numbered SQL files sequentially (`0001` through `0009`).
- **Backend Behavior:** `Migrator.apply_all()` in `backend/app/db/migrator.py`.
- **Data Requirements:** `schema_migrations` table.
- **Processing Algorithms:** Transactional SQL migration execution with SHA-256 checksum audit.
- **Dependencies:** SQLite WAL connection.
- **Historical Evidence:** Replaces historical fragile `_base_pyc` loader discovered in `app/models/db.py`.
- **Current ZezEdit 2.0 Status:** Fully operational (Migrations 0001–0009).
- **Exact Differences:** Clean upgrade over 1.0.
- **Restoration Requirement:** Preserve migration architecture.
- **Verification Method:** Migration idempotency test in Pytest.

#### `ZEZ-092`: Pre-Migration Automatic Database Snapshot
- **Original Purpose:** Automatically create a verifiable SQLite backup before running any schema migration.
- **Original Workflow:** Migrator invokes `sqlite3.backup()` to `storage/backups/db_backup_pre_migration_{timestamp}.db` before applying new SQL files.
- **Backend Behavior:** `BackupService.create_snapshot()`.
- **Data Requirements:** Verified SQLite database file.
- **Dependencies:** Python `sqlite3`.
- **Historical Evidence:** `test_milestone2_core.py` (`test_backup_creation`).
- **Current ZezEdit 2.0 Status:** Fully operational.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve pre-migration snapshots.
- **Verification Method:** Backup creation test.

#### `ZEZ-093`: Path Traversal & Anti-Root Recursive Deletion Guard
- **Original Purpose:** Prevent malicious or buggy paths from accessing system files or deleting drive roots (`D:\`).
- **Original Workflow:** `security.py` verifies all paths resolve strictly inside `storage_root`; explicitly rejects drive root targets and paths with `..` escapes.
- **Backend Behavior:** Throws `SecurityError` on traversal attempt.
- **Dependencies:** `app.core.security`.
- **Historical Evidence:** `test_milestone1_foundation.py` (`test_path_traversal_prevention`).
- **Current ZezEdit 2.0 Status:** Fully operational.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve path confinement guards.
- **Verification Method:** Security test suite in Pytest.

#### `ZEZ-094`: Single Authoritative Job Orchestrator & State Machine
- **Original Purpose:** Prevent race conditions, duplicate worker threads, or zombie processes by enforcing a single background task queue.
- **Original Workflow:** Enforces valid state transitions: `queued` -> `running` -> `completed` | `failed` | `cancelled`; rejects invalid transitions.
- **Backend Behavior:** `JobOrchestrator` in `backend/app/services/jobs.py`.
- **Data Requirements:** `jobs` table in SQLite.
- **Dependencies:** `jobs.py`.
- **Historical Evidence:** `test_milestone2_core.py` (`test_job_state_machine`).
- **Current ZezEdit 2.0 Status:** Fully operational.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve single authoritative job orchestrator.
- **Verification Method:** Job state machine Pytest tests.

#### `ZEZ-095`: Unclean Shutdown Recovery of Interrupted Jobs
- **Original Purpose:** Automatically detect and recover jobs left in `running` or `cancelling` state if the server process crashed or was terminated.
- **Original Workflow:** Backend startup scans `jobs` table; transitions orphaned `running` jobs to `interrupted` with explanatory log.
- **Backend Behavior:** `JobOrchestrator.recover_interrupted_jobs()` on startup.
- **Data Requirements:** `jobs` table records.
- **Dependencies:** `jobs.py`.
- **Historical Evidence:** `test_milestone2_core.py` (`test_startup_job_recovery`).
- **Current ZezEdit 2.0 Status:** Fully operational.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve startup job recovery.
- **Verification Method:** Startup recovery test in Pytest.

#### `ZEZ-096`: Comprehensive Health & Diagnostics Probe (`/api/v1/health`)
- **Original Purpose:** Probe all system dependencies (SQLite, Storage, FFmpeg, FFprobe, Ollama) and return actionable status.
- **Original Workflow:** API returns:
  ```json
  {"status":"ready", "database":{"connected":true}, "ffmpeg":{"available":true}, "ollama":{"reachable":true}}
  ```
- **Backend Behavior:** `GET /api/v1/health` in `health.py`.
- **Dependencies:** Subprocess checks and HTTP probes.
- **Historical Evidence:** `test_milestone1_foundation.py` (`test_health_endpoint`).
- **Current ZezEdit 2.0 Status:** Fully operational.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve health probe endpoint.
- **Verification Method:** Live curl health check.

#### `ZEZ-097`: Graphify Knowledge Graph Auto-Maintenance
- **Original Purpose:** Maintain a persistent, queryable AST knowledge graph of the ZezEdit codebase for dependency tracing and architecture verification.
- **Original Workflow:** Developers/agents run `graphify update .` to update `graphify-out/graph.json` (2,101 nodes, 5,822 edges, 108 communities) and query paths.
- **Dependencies:** `graphifyy` CLI binary.
- **Historical Evidence:** Configured in `.agents/rules/graphify.md` and `.agents/workflows/graphify.md`.
- **Current ZezEdit 2.0 Status:** Fully operational.
- **Exact Differences:** None.
- **Restoration Requirement:** Keep graph updated after all code changes.
- **Verification Method:** CLI `graphify query` execution.

#### `ZEZ-098`: Unslop Studio Dark Design Standard
- **Original Purpose:** Eliminate AI design slop (purple glows, mixed fonts, decorative gradients) and enforce a quiet desktop NLE visual identity.
- **Original Workflow:** All UI surfaces adhere to 9-pass Unslop redlines: neutral graphite palette (`bg-canvas` `#0d0f12`), 4px spatial rhythm, sentence-case copy, no arbitrary milestone tags.
- **Dependencies:** `.agents/skills/unslop/SKILL.md`.
- **Historical Evidence:** Audit and implementation in Milestone 11.
- **Current ZezEdit 2.0 Status:** Fully operational across all 12 UI views.
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve Unslop design standard.
- **Verification Method:** Visual screenshot inspection.

#### `ZEZ-099`: Automated Regression Test Suites ($\ge 120$ Backend, $\ge 85$ Frontend)
- **Original Purpose:** Guarantee system reliability and feature integrity across all milestones.
- **Original Workflow:** `pytest` runs backend suite; `vitest` runs frontend suite.
- **Historical Evidence:** 113 backend pytest tests and 81 frontend vitest tests passing in 13M.12.
- **Current ZezEdit 2.0 Status:** 51 backend tests passing (100%), 52 frontend tests passing (100%).
- **Exact Differences:** Current test suites need expansion to restore all historical unit tests from 13M.12 and 13M.13.
- **Restoration Requirement:** Expand backend tests to $\ge 120$ and frontend tests to $\ge 85$.
- **Verification Method:** Automated test execution via `pytest` and `npm test`.

#### `ZEZ-100`: Complete Offline Operation Guarantee
- **Original Purpose:** Guarantee that ZezEdit never sends source video, audio, transcripts, or facial images to any external cloud API.
- **Original Workflow:** Every pipeline step (FFmpeg, FFprobe, Faster-Whisper, OpenCV, Ollama) executes entirely on local host hardware (`127.0.0.1`).
- **Backend Behavior:** Zero network outbound requests to third-party endpoints.
- **Dependencies:** Local binaries and libraries.
- **Historical Evidence:** Core product vision in surviving `README.md`.
- **Current ZezEdit 2.0 Status:** Fully verified (100% local-first).
- **Exact Differences:** None.
- **Restoration Requirement:** Preserve local-first architecture.
- **Verification Method:** Network egress audit.

---

## 4. Summary Parity Ledger

- **Total ZezEdit 1.0 Requirements Identified:** **100**
- **Active Core Scope Requirements:** **90** (Domain I Character Studio `ZEZ-081`–`ZEZ-090` deferred out of active scope per Milestone 17 directive)
- **Requirements Fully Restored in ZezEdit 2.0:** **82 / 90 Active Scope (91.1%)**
- **Requirements Deferred Out of Active Scope:** **10** (`ZEZ-081` through `ZEZ-090` preserved in codebase and database, but removed from active navigation and workflows)
- **Restored in Milestone 17:**
  - `ZEZ-006` (System Monitor & Hardware Resource Widget: `ResourceInspector.tsx` hover telemetry window and `/api/v1/system/resources` endpoint)
  - `ZEZ-009` (Studio In-App Documentation Viewer: `DocumentationView.tsx` with 13 articles and 5 categories)
  - Core Operations: Working Queue (`WorkingQueueView.tsx`), AI Provider Manager (`AIProviderManager.tsx`), Next Video Workflow in Video Workspace
- **Requirements Partially Restored / Requiring Enhancement:** **8**
  - `ZEZ-008` (Dedicated floating toast notification container)
  - `ZEZ-018` (Prominent media relinking UI trigger)
  - `ZEZ-050` (Dual-viewport reframing review modal integration)
  - `ZEZ-051` (Interactive on-canvas draggable 9:16 crop rectangle)
  - `ZEZ-052` (Interactive timeline keyframe diamond scrubber pins)
  - `ZEZ-054` (Visual revision history drawer in reframing workspace)
  - `ZEZ-080` (Version history drawer in AI chat panel)
  - `ZEZ-099` (Automated regression test coverage: 61 pytest / 56 vitest = 117 tests, expanding toward target)
- **Requirements Unrecoverable:** **0** (All 100 requirements have full surviving evidence).
