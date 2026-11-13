# ZezEdit 2.0 — Local-First AI Video Editor

ZezEdit 2.0 is a modular, CPU-first, local-first AI-assisted video editor for Windows 11.

---

## Quick Start: Windows PowerShell Commands

### Backend Commands (FastAPI + Uvicorn)
Start FastAPI server at `http://127.0.0.1:8000`:
```powershell
cd D:\ZezEdit\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run backend automated test suite (Pytest):
```powershell
cd D:\ZezEdit\backend
.\.venv\Scripts\python -m pytest -v
```

### Frontend Commands (React + Vite + Tailwind)
Start frontend development server at `http://localhost:5173`:
```powershell
cd D:\ZezEdit\frontend
npm run dev
```

Run frontend unit tests (Vitest via npm, never pnpm):
```powershell
cd D:\ZezEdit\frontend
npm test -- --run
```

---

## 1. Prerequisites

- **Operating System:** Windows 11 (64-bit)
- **Hardware Baseline:** Multi-core CPU (tested on Intel Core i3-1220P), ~20 GB RAM recommended (no CUDA / dedicated GPU required)
- **Python:** Python 3.11+ (tested with Python 3.14.6)
- **Node.js & npm:** Node.js 20+ and npm 10+ (tested with Node v24.18.1 / npm 12.2.0; do not use pnpm)
- **Media Tools:** `ffmpeg` and `ffprobe` available on `PATH` (tested with FFmpeg 9.0.2) or configured explicitly in `.env`
- **Local AI Runtime (Optional for Milestone 1):** Ollama running at `http://127.0.0.1:11434` (verified with `qwen3-vl:4b-instruct`)

---

## 2. Installation commands

### Backend Python Environment

```powershell
cd D:\ZezEdit\backend
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -e ".[dev]"
```

### Frontend Node Dependencies (npm only)

```powershell
cd D:\ZezEdit\frontend
npm install
```

---

## 3. Environment and setup steps

1. Copy `.env.example` to `.env` in `D:\ZezEdit`:

```powershell
cd D:\ZezEdit
Copy-Item .env.example .env
```

2. Review `ZEZEDIT_STORAGE_ROOT` in `.env` (defaults to `D:\ZezEdit\storage`). Never point `ZEZEDIT_STORAGE_ROOT` to a drive root such as `D:\` or an OS system folder; startup validation explicitly rejects unsafe roots.
3. On backend startup, FastAPI automatically creates the isolated storage subdirectories (`db`, `media`, `proxies`, `thumbnails`, `analysis`, `timelines`, `shorts`, `exports`, `temp`, `backups`, `logs`) and initializes `storage\db\zezedit.db` via forward-only SQLite migrations in `backend\migrations\`.

---

## 4. Exact Windows PowerShell backend startup commands

Start FastAPI via Uvicorn (`http://127.0.0.1:8000`):

```powershell
cd D:\ZezEdit\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run backend automated test suite (Pytest):

```powershell
cd D:\ZezEdit\backend
.\.venv\Scripts\python -m pytest -v
```

---

## 5. Exact Windows PowerShell frontend startup commands

Development server (`http://localhost:5173`, proxying `/api` to `http://127.0.0.1:8000`):

```powershell
cd D:\ZezEdit\frontend
npm run dev
```

Run frontend unit tests (Vitest via npm, never pnpm):

```powershell
cd D:\ZezEdit\frontend
npm test -- --run
```

Production TypeScript check & Vite bundle build:

```powershell
cd D:\ZezEdit\frontend
npm run build
```

---

## 6. ZezEdit 1.0 Parity Specification & Restoration (Milestones 12–30)

- **Permanent Restoration Progress Tracker (Active Scope: 90/90 = 100.00% Verified):** [`docs/reconstruction/RESTORATION_PROGRESS_TRACKER.md`](file:///D:/ZezEdit/docs/reconstruction/RESTORATION_PROGRESS_TRACKER.md)
- **Authoritative Milestone 30 Restoration Report:** [`docs/reports/milestone_30_restoration_report.md`](file:///D:/ZezEdit/docs/reports/milestone_30_restoration_report.md)
- **Authoritative Milestone 29 Restoration Report:** [`docs/reports/milestone_29_restoration_report.md`](file:///D:/ZezEdit/docs/reports/milestone_29_restoration_report.md)
- **Authoritative Milestone 28 Restoration Report:** [`docs/reports/milestone_28_restoration_report.md`](file:///D:/ZezEdit/docs/reports/milestone_28_restoration_report.md)
- **Authoritative Milestone 27 Restoration Report:** [`docs/reports/milestone_27_restoration_report.md`](file:///D:/ZezEdit/docs/reports/milestone_27_restoration_report.md)
- **Authoritative Milestone 26 Restoration Report:** [`docs/reports/milestone_26_restoration_report.md`](file:///D:/ZezEdit/docs/reports/milestone_26_restoration_report.md)
- **Authoritative Milestone 25 Restoration Report:** [`docs/reports/milestone_25_restoration_report.md`](file:///D:/ZezEdit/docs/reports/milestone_25_restoration_report.md)
- **Authoritative Milestone 24 Restoration Report:** [`docs/reports/milestone_24_restoration_report.md`](file:///D:/ZezEdit/docs/reports/milestone_24_restoration_report.md)
- **Authoritative Milestone 23 Restoration Report:** [`docs/reports/milestone_23_restoration_report.md`](file:///D:/ZezEdit/docs/reports/milestone_23_restoration_report.md)
- **Remaining Restoration Work Plan:** [`docs/reconstruction/REMAINING_RESTORATION_WORK.md`](file:///D:/ZezEdit/docs/reconstruction/REMAINING_RESTORATION_WORK.md)
- **Authoritative Milestone 21 Restoration Audit:** [`docs/reports/milestone_21_authoritative_restoration_audit.md`](file:///D:/ZezEdit/docs/reports/milestone_21_authoritative_restoration_audit.md)
- **UI Quality & Unslop Design Audit:** [`docs/reconstruction/UI_QUALITY_AUDIT.md`](file:///D:/ZezEdit/docs/reconstruction/UI_QUALITY_AUDIT.md)
- **ZezEdit 1.0 Parity Specification (100 Requirements):** [`docs/reconstruction/ZEZEDIT_1_0_PARITY_SPECIFICATION.md`](file:///D:/ZezEdit/docs/reconstruction/ZEZEDIT_1_0_PARITY_SPECIFICATION.md)
- **Feature Parity Matrix & Scorecard (Active Scope: 90/90 = 100.00% Verified):** [`docs/reconstruction/FEATURE_PARITY_MATRIX.md`](file:///D:/ZezEdit/docs/reconstruction/FEATURE_PARITY_MATRIX.md)
- **Restoration Implementation Roadmap (Milestones 21–30 Active Parity Complete):** [`docs/reconstruction/RESTORATION_ROADMAP.md`](file:///D:/ZezEdit/docs/reconstruction/RESTORATION_ROADMAP.md)
- **Pre-Deletion Baseline Specification:** [`docs/reconstruction/PRE_DELETION_BASELINE.md`](file:///D:/ZezEdit/docs/reconstruction/PRE_DELETION_BASELINE.md)

---

## Media Ingestion, Formats & Proxy Pipeline (Milestone 4)

- **Supported Video Formats:** MP4, MOV, MKV, WebM, AVI, M4V, MPEG/MPG, TS, FLV, WMV
- **Supported Audio Formats:** MP3, WAV, AAC, M4A, FLAC, OGG, Opus, WMA
- **Supported Image Formats:** JPEG, PNG, WEBP, GIF, BMP, TIFF
- **Import Workflows:**
  - *External Reference:* References original files on disk with zero duplication, extracting metadata and generating cached thumbnails.
  - *Managed Copy:* Streams large files into `storage/media/{project_subdir}/` in 1 MB chunks without buffering entire files in memory.
  - *Streaming Upload:* `POST /api/v1/projects/{project_id}/media/upload` accepts chunked uploads directly to storage.
- **Scrub Proxies:** Downscaled H.264 MP4 proxies (`360p`, `480p`, `720p`) generated via FFmpeg bounded by CPU worker thread constraints (default 4 threads), with fast-start MP4 atoms for instantaneous seeking.
- **Thumbnails:** Deterministic JPEG frames saved to `storage/thumbnails/{asset_id}.jpg`.
- **Relinking:** Missing external files can be relinked to new filesystem paths without data loss.

---

## Video Analysis Engine, Transcription & Visual Understanding (Milestone 5)

- **Audio Extraction:** Automated extraction of 16kHz mono 16-bit PCM WAV tracks for CPU speech recognition.
- **Faster-Whisper Speech Recognition:** Speech-to-text with segment boundaries, language detection, and word-level timestamps (`tiny`, `base`, `small` on CPU with `int8` quantization).
- **Dialogue Segmentation:** Grouping of transcript segments into coherent conversational speech turns across pause thresholds with turn type classification (`statement`, `question`, `exclamation`).
- **Scene Boundary Detection:** FFmpeg scene filter (`select='gt(scene,0.35)'`) extracting cut timestamps and scene intervals.
- **Controlled Frame Sampling:** Controlled visual keyframe extraction downscaled to 640px, capped by analysis profiles (`fast`, `balanced`, `detailed`).
- **Visual Understanding:** Integration with local Ollama (`qwen3-vl:4b-instruct`) for factual observations (setting, subjects, activity, on-screen text) with graceful heuristic fallback when Ollama is offline.
- **Multimodal Temporal Context Aggregator:** Unified temporal index querying any timestamp for active scene, speech turn, nearby dialogue, and visible observations.
- **Interactive Analysis Workspace:** Full-featured frontend split-view workspace with synchronized video player, clickable transcript, scene strip, visual observations stream, and live temporal inspector.

---

## AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6)

- **Explainable Multi-Signal Scoring (`2.0.0-m6`):** Decomposes clip value into 9 inspectable factors: Semantic Interest (0-20), Narrative Completeness (0-20), Conversation Structure (0-15), Visual Interest (0-15), Audio Evidence (0-10), Opening Clarity (0-10), Ending Completeness (0-10), Duration Suitability (-5 to +10), and Context Dependency Penalty (0 to -15).
- **Context-Aware Boundary Snapping:** Snaps candidate boundaries to visual scene cuts within 0.6s and dialogue pause closures, applying 0.3s lead-in and 0.5s lead-out buffers to eliminate split-second flash frames and cut-off speech.
- **Three-Tier Quality Gates:** Automatically categorizes clips into `recommended`, `needs_review`, and `rejected` with explicit failure reasons (e.g., minimum score thresholds, missing context, abrupt opening).
- **Temporal Overlap Clustering & Deduplication:** Clips overlapping with $\text{IoU} \ge 0.65$ are clustered under `overlap_group_id`, surfacing the highest-scoring candidate as primary and grouping variations as alternative cuts.
- **Ollama AI Content Explanations:** Explains the viral hook, why the clip works, target audience, strengths, and risks via local `qwen3-vl:4b-instruct` (or deterministic heuristic fallback when offline).
- **Interactive Shorts Highlights Studio:** Dedicated frontend workspace featuring metric counters, search/filter toolbar, status tabs, candidate cards, boundary slider fine-tuning (±0.1s/0.5s), 9-component radar/score breakdown, and one-click render queue toggling.

---

## Smart Reframing, Subject Tracking & Portrait Composition (Milestone 7)

- **CPU-First Subject Tracking:** OpenCV Haar Cascades (`haarcascade_frontalface_default.xml`, `haarcascade_profileface.xml`, `haarcascade_upperbody.xml`) combined with saliency fallback, temporal IoU/centroid association across frames, and 1.2-second gap bridging.
- **Authoritative Crop Geometry:** Computes vertical `9:16`, square `1:1`, and landscape `16:9` crops with even integer dimensions, minimum subject framing, and strict boundary clamping ($0 \le x \le W-w$, $0 \le y \le H-h$).
- **Intelligent Framing Strategies:** Supports `single_subject`, `two_person` (joint conversational framing bounding both speakers), `group`, and centered `fallback` strategies with adjustable headroom factor ($0.0 \dots 0.4$) and base zoom.
- **Velocity-Constrained Smoothing & Scene-Cut Isolation:** Smooths camera trajectory with windowed moving averages while enforcing `max_pan_velocity` limits. Strictly terminates and resets tracking across visual scene cuts, preventing unnatural sliding pans across shots.
- **Preview / Renderer Mathematical Parity:** Both `FramingEngine.interpolate_crop_at(t)` (used in the interactive review UI) and `build_crop_filter_expression(keyframes)` (used in FFmpeg rendering) consume identical piecewise linear interpolation equations, guaranteeing that the preview canvas matches the rendered MP4 pixel-for-pixel.
- **Dynamic FFmpeg Filtergraph Rendering:** Renders full-resolution vertical videos using time-varying `crop=w:h:x:y` expressions and high-quality libx264 encoding with audio sync.
- **Non-Destructive Revision History:** Every manual crop override creates a new versioned revision in `reframing_revisions` while retaining prior revisions with 1-click restore.
- **Reframing Review Workspace UI:** Dual synchronized viewports (Source Landscape with animated crop box & detected subject overlays, alongside True 9:16 Portrait Canvas), pan offset buttons/sliders, zoom & headroom controls, keyframe toggles, revision history drawer, and one-click render trigger.

---

## Rendering Engine, Export Pipeline & Automatic Shorts Generation (Milestone 8)

- **Standard Export Presets:**
  - *YouTube Shorts / Instagram Reels (`shorts_reels_9_16`):* Vertical 1080x1920, H.264 (`yuv420p`), AAC stereo 48 kHz.
  - *Widescreen Landscape (`landscape_16_9`):* Standard 1920x1080, H.264, AAC stereo.
  - *Square Social (`square_1_1`):* Square 1080x1080, H.264, AAC stereo.
- **Dynamic Smart Reframing Integration:** Directly consumes piecewise-linear crop expressions from Milestone 7 with automatic target scaling and scene-cut isolation.
- **Configurable Caption & Subtitle Engine:**
  - Converts Whisper word timestamps into Advanced Substation Alpha (`.ass`) subtitle files.
  - Modes: `none`, `word_highlight` (TikTok-style karaoke spoken-word color highlights), `phrase` (3–5 word bursts), `sentence` (speech turns), and `standard`.
  - Full customization: font family, point size, bold, base text color, highlight color, outline width, drop shadow, and safe bottom margins.
- **Audio Processing Pipeline:**
  - Volume scaling ($0.0 \dots 2.0\times$), linear fade-in and fade-out buffers.
  - Optional broadcast-standard EBU R128 loudness normalization (`loudnorm=I=-16:TP=-1.5:LRA=11`).
  - Automatic silent stereo audio synthesis (`anullsrc`) for video-only source media.
- **15-Stage Modular Pipeline:** Request validation $\to$ Candidate resolution $\to$ Media verification $\to$ Framing keyframes $\to$ Filtergraph compilation $\to$ Subtitle generation $\to$ Audio filtering $\to$ FFmpeg execution $\to$ Output validation gate $\to$ Publishing to `storage/exports/`.
- **Subprocess Tracking & Clean Cancellation:** Active render jobs track `subprocess.Popen` PIDs and parse real-time progress percentages from `out_time_us`. Cancellation gracefully terminates the process tree and purges scratch files.
- **Output Validation Gate:** Post-render inspection via FFprobe verifying file existence, non-zero size, container readability, resolution, duration tolerances ($\pm 0.5$s), codec compliance, and test frame decoding.
- **Shorts Export Studio Workspace (`ExportStudio.tsx`):** Split layout with candidate selector, profile cards, caption/audio styling accordions, live animated progress monitor, HTML5 player with HTTP 206 byte-range seeking, and export history.

### Troubleshooting & Common Issues
- **Subtitles not appearing:** Ensure analysis transcript has completed (`status="completed"`) and candidate interval falls within speech segments.
- **Source video has no audio:** The engine automatically synthesizes an aligned silent stereo track so exports comply with YouTube Shorts / Reels audio requirements.
- **FFmpeg path override:** Set `ZEZEDIT_FFMPEG_PATH` and `ZEZEDIT_FFPROBE_PATH` in `.env` if using a custom build.

---

## AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9)

- **Unified Multi-Track Architecture:**
  - One authoritative timeline model representing sequences, tracks (video, audio, text overlays), and clips with frame-accurate timing.
  - Video tracks (Main Video, B-roll), Audio tracks (Source Audio, Background Music), Overlay tracks (Text, Graphics).
  - Time domains: Exact mapping between source time (`source_in`, `source_out`) and timeline time (`timeline_start`, `timeline_end`).
- **Validated Reversible Command System:**
  - Every timeline mutation operates through explicit commands: `InsertClip`, `MoveClip`, `TrimClip`, `SplitClip`, `DeleteClip`, `DuplicateClip`, `UpdateClipProps`, `AddTextOverlay`.
  - Commands validate interval boundaries ($timeline\_end > timeline\_start \ge 0$), track existence, and track lock states before execution.
  - Generates exact forward and inverse payloads recorded in `timeline_commands`.
- **Persistent Undo & Redo:**
  - Transactional history surviving application restarts and system crashes.
  - `undo()` applies inverse payload and increments sequence revision; `redo()` reapplies forward payload cleanly.
- **AI Video Editor Assistant:**
  - Dedicated assistant understanding project media, transcripts (Whisper tokens), shot boundaries, highlight candidates, timeline tracks, and selected clips.
  - Contextual reasoning: Answers user questions (e.g. "What happens at 2 minutes?", "Find highlight moments") or generates structured editing plans.
  - Strict Safety Boundaries: AI cannot run arbitrary shell commands, modify database files directly, delete source media, or execute unapproved edits.
  - Review & Approval Gate: Proposed plans present plain-English explanations, operation lists, and warnings. Edits are executed only after explicit user approval.
- **Multi-Track Timeline Rendering Pipeline:**
  - Directly translates timeline state into an FFmpeg execution graph without building a redundant second renderer.
  - Video layering with time-bounded overlays, libass text overlays (`ass=filename=overlay.ass`) for bulletproof Windows stability, multi-track audio mixing (`amix`), and loudness normalization (`loudnorm`).
  - Integrated with Milestone 8 `OutputValidator` gate to inspect dimensions, duration, codecs, and frame decodability.
- **Keyboard Shortcuts:**
  - `S`: Split clip at playhead position.
  - `Del`: Delete currently selected clip (reversible via Undo).
  - `D`: Duplicate selected clip.
  - `Ctrl+Z`: Undo last editing operation.
  - `Ctrl+Y`: Redo next operation.
  - `Space`: Toggle playback / pause.

---

## Character Extraction Studio, Character Library & System Integration (Milestone 10)

- **Independent, Non-Mandatory Workflow:** Character extraction operates completely decoupled from Shorts highlight discovery and rendering; users can use it optionally to track people and speech.
- **Configurable Frame Sampling:** Extracts representative frames across video duration at user-selected sampling rates (0.5s, 1.0s, 2.0s) without high memory overhead.
- **CPU-First Face & Person Detection:** Robust OpenCV skin-tone segmentation, contour geometry, and visual saliency running 100% on CPU without requiring CUDA or external network weights.
- **Spatial-Temporal Candidate Clustering:** Forms provisional candidate groupings based on temporal proximity and spatial bounding box distances with transparent confidence metrics.
- **Observations & Evidence Thumbnails:** Bounding box crops generated and saved to storage/characters/{project_id}/thumbs/, tracking detection method, confidence, and timestamps.
- **Unverified Dialogue Correlation:** Queries intersecting 	ranscript_segments and attaches speech snippets with explicit disclaimer (Unverified Speaker Association).
- **Screen Time Transparency:** Distinguishes sampled frames screen time from continuous estimated screen time.
- **Human Review Controls:**
  - Rename candidate labels
  - Confirm candidates to persistent Character Library
  - Merge multiple candidate groups into a target candidate
  - Split candidate observations into a new candidate group
  - Non-destructive observation detachment (evidence retained on disk)
  - Reject false-positive candidates
- **Persistent Character Library:** Project-wide library managing confirmed character profiles, biographies, appearance tags, and appearance metrics.
- **Documented JSON Export:** Exports full character profile, candidate groupings, appearance timestamps, and screen-time breakdowns with formal transparency disclaimers.
- **Frontend Studio Workspace (CharacterStudio.tsx):** Integrated dual-tab interface with live observation gallery, review dialogs, search/filter, and JSON download.
- **Complete System Reliability:** 51/51 backend Pytests and 52/52 frontend Vitests passing (100%), with automatic startup recovery and immutable source media.

---

## Graphify Integration & Codebase Knowledge Graph (Milestone 11)

ZezEdit incorporates [Graphify](https://github.com/Graphify-Labs/graphify) (`graphifyy`) for persistent structural AST extraction, community clustering, and cross-file navigation across backend FastAPI services, database schemas, and frontend React components.

- **Installation:**
  ```powershell
  uv tool install graphifyy
  # Or via pip
  pip install graphifyy
  ```
- **Platform Registration for Google Antigravity:**
  ```powershell
  cd D:\ZezEdit
  graphify antigravity install
  ```
  Writes `.agents/rules/graphify.md`, `.agents/workflows/graphify.md`, and configures the `graphify` skill.
- **Generate & Update Knowledge Graph:**
  ```powershell
  cd D:\ZezEdit
  graphify update . --force
  ```
  Generates:
  - `graphify-out/graph.json` (2,074 nodes, 5,772 edges)
  - `graphify-out/graph.html` (interactive WebGL visualizer)
  - `graphify-out/GRAPH_REPORT.md` (community structure & hub breakdown)
- **Key Navigation Commands:**
  - Shortest path: `graphify path "MediaLibraryView.tsx" "media_pipeline.py" --undirected`
  - Node explain: `graphify explain "media_pipeline.py"`
  - BFS traversal: `graphify query "how importing a video connects to the media database and backend"`

---

## Unslop Design System & Video-Centric Workspace (Milestone 11)

ZezEdit incorporates the [Unslop](https://github.com/heydamir/unslop) design skill (`/unslop`) to eliminate AI slop (purple glows, decorative gradients, milestone developer tags) and enforce a quiet, desktop-first video editing studio aesthetic.

- **Installation Location:**
  - Global: `%USERPROFILE%\.gemini\antigravity\skills\unslop`
  - Project-Scoped: `D:\ZezEdit\.agents\skills\unslop`
- **Design Principles Applied:**
  - **Color Palette:** Neutral graphite ramp (`#0d0f12` canvas, `#16191e` surface, `#262a33` hairlines) with purposeful signal accents.
  - **4px Spatial Rhythm:** Uniform padding, nested radii (`rounded-xl` for cards, `rounded-lg` for controls).
  - **Monochrome Quiet Chrome:** Sidebar navigation buttons and icons adopt secondary text role tones without competing colors.
  - **Tabular Figures:** Timecodes (`00:01:24.08`) and durations formatted with `tabular-nums`.
- **Video-Centric Editing Architecture (`VideoWorkspace.tsx`):**
  - Ingesting or clicking any video opens its dedicated 9-tab workspace: Overview, Video Analysis, Timestamped Transcript, Scene Cuts, AI Highlights, Smart Reframing, Shorts Export, Multi-Track Timeline, and Character Studio.
  - Seamless context preservation: Project ID and active Media Asset ID remain pinned across all sub-workspaces.
- **Intelligent Post-Import Action Flow (`PostImportModal.tsx`):**
  - Triggers immediately upon media file ingestion with four explicit options: "Analyze Video Now", "Open Video Workspace", "Import Another Video", and "Return to Media Library".

---

## Architecture & Documentation

- [Session 7 Completion Report: Complete Product Integration & Real-World Validation](docs/reports/session_7/SESSION_7_COMPLETION_REPORT.md)
- [End-to-End Product Flow Specification](docs/architecture/END_TO_END_PRODUCT_FLOW.md)
- [Session 6C Completion Report: Real Short Video Rendering & Batch Export](docs/reports/session_6c/SESSION_6C_COMPLETION_REPORT.md)
- [Video Rendering Architecture Design](docs/architecture/VIDEO_RENDERING_DESIGN.md)
- [Rendering Pipeline Audit](docs/architecture/RENDERING_PIPELINE_AUDIT.md)
- [Session 6B Completion Report: Central Process Manager & Storage Reclamation](docs/reports/session_6b/SESSION_6B_COMPLETION_REPORT.md)
- [Central Process Manager Architecture Design](docs/architecture/PROCESS_MANAGER_DESIGN.md)
- [User Data Storage Inventory & Retention Specification](docs/architecture/USER_DATA_STORAGE_INVENTORY.md)
- [Session 6A Completion Report: Reusable Intelligence & Non-Repeating Generate More](docs/reports/session_6a/SESSION_6A_COMPLETION_REPORT.md)
- [Product Restructure & Video-Centric Architecture Plan](docs/architecture/ZEZEDIT_PRODUCT_RESTRUCTURE_PLAN.md)
- [Product Restructure Completion Report](docs/reports/product_restructure/PRODUCT_RESTRUCTURE_COMPLETION_REPORT.md)
- [Session 0 Architecture Audit & Roadmap](docs/architecture/SESSION_0_AUDIT_REPORT.md)
- [Unified Video Studio Architecture Design](docs/architecture/UNIFIED_VIDEO_STUDIO_DESIGN.md)
- [Video Intelligence Pipeline Specification](docs/architecture/VIDEO_INTELLIGENCE_PIPELINE.md)
- [Database & API Design Specification](docs/architecture/DATABASE_AND_API_DESIGN.md)
- [Multi-Session Implementation Roadmap](docs/architecture/IMPLEMENTATION_ROADMAP.md)
- [Milestone 24 Active Parity Signoff & Regression Suite Report](docs/reports/milestone_24_restoration_report.md)
- [Milestone 23 Editorial & Notification Refinements Report](docs/reports/milestone_23_restoration_report.md)
- [Milestone 22 Parity Restoration & Progress Tracker Report](docs/reports/milestone_22_restoration_report.md)
- [Milestone 21 Authoritative Parity Audit & UI Assessment Report](docs/reports/milestone_21_audit_report.md)
- [Restoration Progress Tracker](docs/reconstruction/RESTORATION_PROGRESS_TRACKER.md)
- [Milestone 20 Production Reliability Report](docs/reports/milestone_20_production_reliability_report.md)
- [Milestone 19 Desktop Operations Center Report](docs/reports/milestone_19_desktop_operations_center_report.md)
- [Milestone 18 Unified Video-to-Shorts Pipeline Report](docs/reports/milestone_18_unified_video_to_shorts_pipeline_report.md)
- [Milestone 17 Core Product Workflow & Desktop Operations Report](docs/reports/milestone_17_core_product_workflow_report.md)
- [Milestone 15 Analysis Restoration Report](docs/reports/milestone_15_analysis_restoration_report.md)
- [Milestone 13 Parity Restoration Plan](docs/reports/milestone_13_parity_restoration_plan.md)
- [Milestone 12 Pre-Deletion Baseline Report](docs/reports/milestone_12_reconstruction_report.md)
- [System Audit & Verification Report (Milestone 11)](docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md)
- [UI & Feature Gap Analysis (Milestone 11)](docs/audit/UI_AND_FEATURE_GAP_ANALYSIS.md)
- [Video Workspace Architecture Specification](docs/architecture/VIDEO_WORKSPACE.md)
- [Milestone 11 Completion Report](docs/reports/milestone_11_completion_report.md)
- [Master Requirements](docs/MASTER_REQUIREMENTS.md)
- [Feature Status](docs/feature_status.md)
- [Verification Checklist](docs/feature_test_checklist.md)
- [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Database Design & Migrations](docs/architecture/DATABASE_DESIGN.md)
- [API Design](docs/architecture/API_DESIGN.md)
- [Job Orchestration](docs/architecture/JOB_ORCHESTRATION.md)
- [Media Pipeline](docs/architecture/MEDIA_PIPELINE.md)
- [Timeline Data Model](docs/architecture/TIMELINE_MODEL.md)
- [Character Studio Architecture](docs/architecture/CHARACTER_STUDIO.md)
- [Security & Data Safety](docs/architecture/SECURITY_AND_DATA_SAFETY.md)
- [Technology Decisions](docs/architecture/TECHNOLOGY_DECISIONS.md)