# ZezEdit 2.0 — Local-First AI Video Editor

ZezEdit 2.0 is a modular, CPU-first, local-first AI-assisted video editor for Windows 11.

---

## 1. Prerequisites

- **Operating System:** Windows 11 (64-bit)
- **Hardware Baseline:** Multi-core CPU (tested on Intel Core i3-1220P), ~20 GB RAM recommended (no CUDA / dedicated GPU required)
- **Python:** Python 3.11+ (tested with Python 3.14.6)
- **Node.js & npm:** Node.js 20+ and npm 10+ (tested with Node v24.18.1 / npm 12.2.0; do not use pnpm)
- **Media Tools:** `ffmpeg` and `ffprobe` available on `PATH` (tested with FFmpeg 9.0.2) or configured explicitly in `.env`
- **Local AI Runtime (Optional):** Ollama running at `http://127.0.0.1:11434` (verified with `qwen3-vl:4b-instruct`)

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

## 3. Environment setup

1. Copy `.env.example` to `.env` in `D:\ZezEdit`:

```powershell
cd D:\ZezEdit
Copy-Item .env.example .env
```

2. Review `ZEZEDIT_STORAGE_ROOT` in `.env` (defaults to `D:\ZezEdit\storage`). Never point `ZEZEDIT_STORAGE_ROOT` to a drive root such as `D:\` or an OS system folder; startup validation explicitly rejects unsafe roots.
3. On backend startup, FastAPI automatically creates the isolated storage subdirectories (`db`, `media`, `proxies`, `thumbnails`, `analysis`, `timelines`, `shorts`, `exports`, `temp`, `backups`, `logs`) and initializes `storage\db\zezedit.db` via forward-only SQLite migrations in `backend\migrations\`.

### Storage & User Data Retention Layout

All user videos, databases, and rendered files are strictly confined to `D:\ZezEdit\storage`:
- **Databases**: `storage\db\zezedit.db` (SQLite with WAL journaling).
- **Uploaded Media**: `storage\media\{project_id}\{filename}`.
- **Proxies & Thumbnails**: `storage\proxies\` and `storage\thumbnails\`.
- **Analysis Data & Keyframes**: `storage\analysis\{run_id}\`.
- **Rendered Shorts Exports**: `storage\exports\{project_id}\*.mp4`.
- **Temporary Files & PIDs**: `storage\temp\` (including `zezedit.pid`).
- **Database Backups**: `storage\backups\`.
- **System Logs**: `storage\logs\` (including `launcher_stdout.log` and `launcher_stderr.log`).

---

## 4. First-time setup

Before launching production mode for the first time, build the frontend production distribution:

```powershell
cd D:\ZezEdit\frontend
npm run build
```

This compiles optimized client assets into `frontend\dist` (`index.html` and `assets/`). The one-click launcher will also automatically run this build if `frontend\dist` is missing.

---

## 5. One-click Windows startup

To start ZEZEdit in production mode:
- Double-click `Start-ZEZEdit.bat` in File Explorer, OR
- Run from Windows PowerShell / Command Prompt:

```cmd
D:\ZezEdit\Start-ZEZEdit.bat
```

Or using PowerShell:

```powershell
.\Start-ZEZEdit.ps1 [-NoBrowser] [-ValidateOnly] [-Port 8000] [-TimeoutSeconds 30]
```

**What the launcher does automatically:**
1. Resolves workspace root dynamically from the script location (can be called from any current working directory or shortcut).
2. Verifies Python virtual environment (Python 3.11+) and core dependencies.
3. Verifies `.env` configuration file (copies from `.env.example` if missing, masks secrets).
4. Verifies FFmpeg and FFprobe availability on `PATH`.
5. Checks frontend production build in `frontend\dist` (auto-builds via `npm run build` if missing).
6. Checks port ownership and probes `http://127.0.0.1:8000/health`:
   - If an existing healthy ZEZEdit instance is detected, reports status without spawning duplicates.
   - If occupied by an unrelated foreign process, displays actionable error without killing it.
7. Cleans stale PID files from prior crashed sessions if the previous process is not running.
8. Starts the FastAPI server as a detached background process (immune to parent job object limits or console closure).
9. Records structured process ownership in `storage\temp\zezedit_process.json` and PID in `storage\temp\zezedit.pid`.
10. Polls `http://127.0.0.1:8000/health` with proxy-immune HTTP probes until readiness is confirmed.
11. Opens the application in your default web browser at `http://127.0.0.1:8000` (unless `-NoBrowser` is specified).

---

## 6. Normal shutdown

To stop the running production server cleanly:
- Double-click `Stop-ZEZEdit.bat`, OR
- Run from Windows PowerShell / Command Prompt:

```cmd
D:\ZezEdit\Stop-ZEZEdit.bat
```

Or using PowerShell:

```powershell
.\Stop-ZEZEdit.ps1 [-GracefulTimeoutSeconds 5]
```

**Process Ownership & Termination Safety:**
1. Inspects structured ownership in `storage\temp\zezedit_process.json` and `storage\temp\zezedit.pid`.
2. **PID Reuse Protection:** Inspects the process command line via CIM/WMI before terminating. If a non-ZEZEdit process is running with that PID, it is safely preserved and the stale PID file is cleaned.
3. **Graceful Shutdown First:** Sends graceful termination signal (`taskkill /PID <pid> /T`), allowing in-flight jobs and SQLite WAL writes to flush cleanly.
4. **Child Process Cleanup:** Cleans owned child processes without terminating unrelated system processes.
5. Removes PID and metadata files upon successful shutdown. Idempotent: safe to run multiple times.

---

## 7. Development-mode startup

For developers actively modifying backend Python or frontend React source code:

1. Start backend development server with auto-reload:

```powershell
cd D:\ZezEdit\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

2. In a separate terminal, start frontend Vite dev server (`http://localhost:5173`):

```powershell
cd D:\ZezEdit\frontend
npm run dev
```

Vite proxies `/api` calls directly to `http://127.0.0.1:8000`.

---

## 8. Troubleshooting

- **Port 8000 already in use:**
  Run `Stop-ZEZEdit.bat` to clear previous instances, or check `netstat -ano | findstr :8000`.
- **FFmpeg not found:**
  Ensure FFmpeg is installed and added to Windows `PATH`, or set `ZEZEDIT_FFMPEG_PATH=C:\path\to\ffmpeg.exe` in `D:\ZezEdit\.env`.
- **Ollama / AI models unreachable:**
  Ensure Ollama is running (`ollama serve` or open Ollama app). If Ollama is offline, ZEZEdit operates in `ready_with_optional_unavailable` mode using fast local OpenCV color and motion heuristics.
- **Frontend build missing or blank page:**
  Run `cd D:\ZezEdit\frontend; npm run build`. Check that `frontend\dist\index.html` exists.
- **Inspect server logs:**
  Review `storage\logs\launcher_stdout.log`, `storage\logs\launcher_stderr.log`, and `storage\logs\zezedit.log`.

---

## 9. Reports & Historical Acceptance Audits

### Priority 1 — Video Ingestion, Upload & Core Pipeline Reports
- **[P1.6 Media Library, Metadata and Asset Management Report](docs/reports/priority_1/P1_6_MEDIA_LIBRARY_AND_METADATA.md)** (Final Verdict: `MEDIA LIBRARY & ASSET MANAGEMENT ACCEPTED`)
- **[P1.5 Upload Integrity, File Validation and Atomic Persistence Report](docs/reports/priority_1/P1_5_UPLOAD_INTEGRITY_AND_VALIDATION.md)** (Final Verdict: `INTEGRITY CONTRACT & ATOMIC PUBLICATION ACCEPTED`)
- **[P1.4 Upload Failure Handling, Retry and Recovery Report](docs/reports/priority_1/P1_4_UPLOAD_FAILURE_RETRY_AND_RECOVERY.md)** (Final Verdict: `FAILURE HANDLING & RETRY ACCEPTED`)
- **[P1.3-R1 Large Upload Acceptance Evidence Reconciliation Report](docs/reports/priority_1/P1_3_R1_LARGE_UPLOAD_EVIDENCE_RECONCILIATION.md)** (Final Verdict: `LARGE UPLOAD EVIDENCE RECONCILED & ACCEPTED`)
- **[P1.3 Large-File Video Ingestion, Streaming and Bounded Memory Report](docs/reports/priority_1/P1_3_LARGE_FILE_STREAMING_AND_BOUNDED_MEMORY.md)** (Final Verdict: `STREAMING & BOUNDED MEMORY ACCEPTED`)
- **[P1.2 Accurate Byte-Based Upload Progress Report](docs/reports/priority_1/P1_2_BYTE_ACCURATE_UPLOAD_PROGRESS.md)** (Final Verdict: `BYTE-ACCURATE UPLOAD PROGRESS ACCEPTED & VERIFIED`)
- **[P1.1-R1 Real Browser Upload Acceptance and Scope Verification Report](docs/reports/priority_1/P1_1_R1_BROWSER_UPLOAD_ACCEPTANCE.md)** (Final Verdict: `REAL BROWSER UPLOAD ACCEPTED`)
- **[P1.1 Single and Multiple Video Upload Report](docs/reports/priority_1/P1_1_SINGLE_AND_MULTIPLE_UPLOAD.md)** (Final Verdict: `SINGLE & MULTIPLE UPLOAD VERIFIED`)

### Priority 0 — Windows Release Hardening & Stability Reports
- **[P0.9-R1 Restart and Persistence Evidence Reconciliation Report](docs/reports/priority_0/P0_9_R1_EVIDENCE_RECONCILIATION.md)** (Final Verdict: `EVIDENCE RECONCILED & ACCEPTED`)
- **[P0.9 Restart, Recovery and Data Persistence Verification Report](docs/reports/priority_0/P0_9_RESTART_AND_DATA_PERSISTENCE.md)** (Final Verdict: `RESTART & DATA PERSISTENCE ACCEPTED`)
- **[P0.8-R1 Production Serving Evidence Reconciliation Report](docs/reports/priority_0/P0_8_R1_EVIDENCE_RECONCILIATION.md)** (Final Verdict: `EVIDENCE RECONCILED & ACCEPTED`)
- **[P0.8 Production Frontend Serving & SPA Routing Report](docs/reports/priority_0/P0_8_PRODUCTION_FRONTEND_SERVING.md)** (Final Verdict: `PRODUCTION FRONTEND SERVING VERIFIED & ACCEPTED`)
- **[P0.7 Windows Launcher Reliability & Process Lifecycle Safety Report](docs/reports/priority_0/P0_7_WINDOWS_LAUNCHER_RELIABILITY.md)** (Final Verdict: `WINDOWS LAUNCHER ACCEPTED`)
- **[P0.6 Job Queue, Cancellation and Worker Reliability Report](docs/reports/priority_0/P0_6_JOB_QUEUE_AND_CANCELLATION.md)** (Final Verdict: `JOB QUEUE & WORKER RELIABILITY ACCEPTED`)
- **[P0.5-R1 Database/API Regression and Reconciliation Safety Closure Report](docs/reports/priority_0/P0_5_R1_REGRESSION_AND_SAFETY_CLOSURE.md)** (Final Verdict: `DATABASE CONSISTENCY & SAFETY ACCEPTED`)
- **[P0.5 Database and API Consistency Report](docs/reports/priority_0/P0_5_DATABASE_AND_API_CONSISTENCY.md)** (Final Verdict: `RECONCILIATION VERIFIED`)
- **[P0.4 TypeScript and Production Build Stability Report](docs/reports/priority_0/P0_4_TYPESCRIPT_AND_PRODUCTION_BUILD_STABILITY.md)** (Final Verdict: `TYPESCRIPT & PRODUCTION BUILD ACCEPTED`)
- **[P0.3-R1 Browser Evidence Reconciliation Report](docs/reports/priority_0/P0_3_R1_BROWSER_EVIDENCE_RECONCILIATION.md)** (Final Verdict: `BROWSER RECONCILIATION ACCEPTED`)
- **[P0.3 Frontend Stability & Real Browser Acceptance Report](docs/reports/priority_0/P0_3_FRONTEND_BROWSER_ACCEPTANCE.md)** (Final Verdict: `FRONTEND STABILITY ACCEPTED`)
- **[P0.2 Backend Test Baseline Diagnosis and Safe Repair Report](docs/reports/priority_0/P0_2_BACKEND_TEST_BASELINE.md)** (Final Verdict: `BACKEND BASELINE ACCEPTED`)
- **[P0.1 Complete Project Audit and Failure Inventory](docs/reports/priority_0/P0_1_PROJECT_AUDIT.md)** (Final Verdict: `AUDIT COMPLETE`)

### Milestone & Session Acceptance Reports
- [Session 24 Windows Production Mode, One-Click Launcher & Release Hardening Report](docs/reports/session_24/SESSION_24_WINDOWS_PRODUCTION_READINESS.md) (Final Verdict: `PRODUCTION MODE VERIFIED`)
- [Session 23 Real-Media AI Quality Validation & Professional Video Acceptance Report](docs/reports/session_23/SESSION_23_PROFESSIONAL_QUALITY_ACCEPTANCE.md) (Final Verdict: `BETA READY WITH DOCUMENTED LIMITATIONS`)
- [Session 22 End-to-End Generation Repair & Real Video Export Acceptance Report](docs/reports/session_22/SESSION_22_END_TO_END_GENERATION_ACCEPTANCE.md) (Final Verdict: `COMPLETE AND VERIFIED`)
- **Authoritative Session 20 Workflow Report:** [`docs/reports/session_20/SESSION_20_MULTIMODAL_WORKFLOW_ACCEPTANCE.md`](file:///D:/ZezEdit/docs/reports/session_20/SESSION_20_MULTIMODAL_WORKFLOW_ACCEPTANCE.md)
- **Authoritative Session 19 Final Audit Report:** [`docs/reports/session_19/SESSION_19_FINAL_ACCEPTANCE_AUDIT.md`](file:///D:/ZezEdit/docs/reports/session_19/SESSION_19_FINAL_ACCEPTANCE_AUDIT.md)

---

## 7. ZezEdit 1.0 Parity Specification & Restoration (Milestones 12–30)

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

## Media Ingestion, Formats & Proxy Pipeline (Milestone 4 & Priority 1.1–1.3)

- **Supported Video Formats:** MP4, MOV, MKV, WebM, AVI, M4V, MPEG/MPG, TS, FLV, WMV
- **Supported Audio Formats:** MP3, WAV, AAC, M4A, FLAC, OGG, Opus, WMA
- **Supported Image Formats:** JPEG, PNG, WEBP, GIF, BMP, TIFF
- **Import Workflows:**
  - *External Reference:* References original files on disk with zero duplication, extracting metadata and generating cached thumbnails.
  - *Managed Copy:* Streams large files into `storage/media/{project_subdir}/` in 1 MB chunks without buffering entire files in memory.
  - *Streaming Single Upload:* `POST /api/v1/projects/{project_id}/media/upload` and `POST /api/v1/media/upload` accept chunked uploads directly to storage with automatic project assignment.
  - *Batch Multi-Video Upload (P1.1):* `POST /api/v1/projects/{project_id}/media/batch-upload` and `POST /api/v1/media/batch-upload` allow selecting and uploading multiple videos in one operation, with detailed per-file results and partial-failure tolerance.
  - *Safe Filename & Collision Handling (P1.1):* Non-destructive storage naming with unique 8-character hex prefixes, verbatim preservation of Unicode, spaces, and brackets in database metadata, and strict rejection of path traversal sequences (`400 PATH_TRAVERSAL_DETECTED`).
  - *Accurate Byte-Based Upload Progress (P1.2):* Real-time byte tracking via `XMLHttpRequest.upload.onprogress` with strictly monotonic loaded bytes, mathematical percentage calculation, clean visual separation between wire transmission and server processing, and immediate user cancellation via `AbortController`. Implemented with quiet graphite Unslop design in `UploadProgressPanel.tsx` across `ShortVideoGeneratorLibrary` and `MediaLibraryView`.
  - *Large-File Streaming & Bounded Memory (P1.3):* Robust large-file streaming up to 2.5 GB ceiling with strictly bounded memory (verified on 1.21 GB video with only +1.25 MB RSS delta), incremental 1 MB disk writing with on-the-fly SHA-256 calculation, Tier 1 pre-flight validation (413 payload too large / 507 insufficient disk space before reading request bodies), Tier 2 in-flight stream limits and periodic disk headroom checks, client disconnect cleanup, startup orphaned upload purging, and concurrency throttling (max 2 parallel heavy transfers returning 429 when saturated).
  - *Upload Failure Handling, Retry and Recovery (P1.4):* Formalized upload state machine (`queued`, `uploading`, `processing`, `completed`, `failed`, `cancelled`, `retrying`) tracking unique `attemptId` and `attemptCount`, stale callback protection discarding outdated XHR events, deterministic error classification (retryable network/server/timeout drops vs. terminal 400/413/415/corrupt/empty files), item-level selective retry in batch uploads without re-uploading succeeded files, safe full-restart retry from byte zero with honest guidance when DOM `File` reference is lost on page reload, atomic `.uploading` part file renaming, and automated startup sweeping of stale partial uploads.
  - *Upload Integrity, File Validation and Atomic Persistence (P1.5):* Strict end-to-end integrity contracts backed by Migration 0017 schema enhancements (`sha256`, `integrity_status`, `upload_attempt_id`, `integrity_details_json`). Enforces exact byte-count matching (`X-Expected-File-Size` vs received bytes), streaming single-pass SHA-256 calculation without second disk reads, pre-publication FFprobe container validation on staged `.uploading` part files, explicit rejection of corrupt, truncated, zero-byte, plain-text, and audio-only files masquerading as video (`400 NO_VIDEO_STREAM` / `CORRUPT_MEDIA`), support for multi-stream MKVs, two-phase atomic publication via `os.replace()`, and automatic physical rollback on storage or database registration failures.
  - *Media Library, Metadata and Asset Management (P1.6):* Pure source video discovery guaranteed by Migration 0018 performance indexes, preventing exports or generated artifacts from polluting the library. Projecting enriched technical badges (format, codecs, duration, file size, resolution, upload date, verified integrity status, analysis state). Provides 300ms debounced case-insensitive search across filenames and asset ID prefixes, multi-criteria format/codec/resolution filtering, allowlisted server-side sorting with SQLi defense, server-side pagination with zero page overlap, detailed stream topology inspection modal, chunked HTTP 206 Partial Content video seeking with native HTML5 player, atomic metadata refresh preserving SHA-256, on-demand thumbnail regeneration with fallback handling, dependency-safe deletion with 409 Conflict protection (`ACTIVE_OPERATION_IN_PROGRESS`, `DEPENDENCY_CONFLICT`) requiring `force_with_exports=true` for safe disk space reclamation, and responsive mobile reflow (375x812 with 0px overflow).
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

- [P1.6 Media Library, Metadata and Asset Management Report](docs/reports/priority_1/P1_6_MEDIA_LIBRARY_AND_METADATA.md)
- [P1.5 Upload Integrity, File Validation and Atomic Persistence Report](docs/reports/priority_1/P1_5_UPLOAD_INTEGRITY_AND_VALIDATION.md)
- [P1.4 Upload Failure Handling, Retry and Recovery Report](docs/reports/priority_1/P1_4_UPLOAD_FAILURE_RETRY_AND_RECOVERY.md)
- [P1.3-R1 Large Upload Acceptance Evidence Reconciliation Report](docs/reports/priority_1/P1_3_R1_LARGE_UPLOAD_EVIDENCE_RECONCILIATION.md)
- [P1.3 Large-File Video Ingestion, Streaming and Bounded Memory Report](docs/reports/priority_1/P1_3_LARGE_FILE_STREAMING_AND_BOUNDED_MEMORY.md)
- [P1.2 Accurate Byte-Based Upload Progress Report](docs/reports/priority_1/P1_2_BYTE_ACCURATE_UPLOAD_PROGRESS.md)
- [P1.1-R1 Real Browser Upload Acceptance and Scope Verification Report](docs/reports/priority_1/P1_1_R1_BROWSER_UPLOAD_ACCEPTANCE.md)
- [P1.1 Single and Multiple Video Upload Report](docs/reports/priority_1/P1_1_SINGLE_AND_MULTIPLE_UPLOAD.md)
- [P0.9-R1 Restart and Persistence Evidence Reconciliation Report](docs/reports/priority_0/P0_9_R1_EVIDENCE_RECONCILIATION.md)
- [P0.9 Restart, Recovery and Data Persistence Verification Report](docs/reports/priority_0/P0_9_RESTART_AND_DATA_PERSISTENCE.md)
- [P0.8-R1 Production Serving Evidence Reconciliation Report](docs/reports/priority_0/P0_8_R1_EVIDENCE_RECONCILIATION.md)
- [P0.8 Production Frontend Serving and SPA Routing Report](docs/reports/priority_0/P0_8_PRODUCTION_FRONTEND_SERVING.md)
- [P0.7 Windows Launcher Reliability and Process Lifecycle Report](docs/reports/priority_0/P0_7_WINDOWS_LAUNCHER_RELIABILITY.md)
- [P0.6 Job Queue, Cancellation and Worker Reliability Report](docs/reports/priority_0/P0_6_JOB_QUEUE_AND_CANCELLATION.md)
- [P0.5-R1 Database/API Regression and Reconciliation Safety Closure Report](docs/reports/priority_0/P0_5_R1_REGRESSION_AND_SAFETY_CLOSURE.md)
- [P0.5 Database and API Consistency Verification Report](docs/reports/priority_0/P0_5_DATABASE_AND_API_CONSISTENCY.md)
- [P0.4 TypeScript and Production Build Stability Report](docs/reports/priority_0/P0_4_TYPESCRIPT_AND_BUILD_STABILITY.md)
- [P0.3-R1 Browser Evidence Reconciliation Report](docs/reports/priority_0/P0_3_R1_BROWSER_EVIDENCE_RECONCILIATION.md)
- [P0.3 Frontend Stability, Real Browser Demonstrations and Output Review](docs/reports/priority_0/P0_3_FRONTEND_BROWSER_ACCEPTANCE.md)
- [P0.2 Backend Test Baseline Verification Report](docs/reports/priority_0/P0_2_BACKEND_TEST_BASELINE.md)
- [P0.1 Project Audit & Failure Inventory Report](docs/reports/priority_0/P0_1_PROJECT_AUDIT.md)

- [Session 19 Final Product Acceptance Audit & Remaining Work Inventory](docs/reports/session_19/SESSION_19_FINAL_ACCEPTANCE_AUDIT.md)
- [Session 18 Queue Stabilization & Acceptance Report](docs/reports/session_18/SESSION_18_QUEUE_STABILIZATION_REPORT.md)
- [Session 16 Product Acceptance, Short-Form Quality & Workflow Completion Report](docs/reports/session_16/SESSION_16_PRODUCT_ACCEPTANCE_REPORT.md)
- [Session 15 Endurance & Recovery Report: Long-Video Endurance, Job Recovery & Production Workflow Verification](docs/reports/session_15/SESSION_15_ENDURANCE_REPORT.md)
- [Session 14 Acceptance Report: Reliability, Rendering & Quality Acceptance](docs/reports/session_14/SESSION_14_ACCEPTANCE_REPORT.md)
- [Session 12 Acceptance Report: Independent Acceptance Testing, Job Reliability Stress Testing & Session 11 Defect Repair](docs/reports/session_12/SESSION_12_ACCEPTANCE_REPORT.md)
- [Session 11 Completion Report: Recurring Job Failure Repair, Video Dashboard Simplification & Inline Video Library](docs/reports/session_11/SESSION_11_COMPLETION_REPORT.md)
- [Session 9 Completion Report: Critical Performance Diagnostics & Generation Validation](docs/reports/session_9/SESSION_9_COMPLETION_REPORT.md)
- [Analysis Performance, Progress Streaming & Short Generation Architecture](docs/architecture/ANALYSIS_PERFORMANCE_AND_PROGRESS.md)
- [Session 8 Completion Report: Real Object Tracking, Multi-Subject Intelligence & Temporal Novelty Correction](docs/reports/session_8/SESSION_8_COMPLETION_REPORT.md)
- [Object Detection, Multi-Subject Intelligence & Framing Architecture](docs/architecture/OBJECT_AND_MULTI_SUBJECT_TRACKING.md)
- [Temporal Novelty & Candidate Deduplication Architecture](docs/architecture/TEMPORAL_NOVELTY_DESIGN.md)
- [Session 7 Completion Report: Complete Product Integration & Real-World Validation](docs/reports/session_7/SESSION_7_COMPLETION_REPORT.md)
- [End-to-End Product Flow Specification](docs/architecture/END_TO_END_PRODUCT_FLOW.md)
- [Session 6C Completion Report: Real Short Video Rendering & Batch Export](docs/reports/session_6c/SESSION_6C_COMPLETION_REPORT.md)
- [Video Rendering Architecture Design](docs/architecture/VIDEO_RENDERING_DESIGN.md)
- [Rendering Pipeline Audit](docs/architecture/RENDERING_PIPELINE_AUDIT.md)
- [Session 6B Completion Report: Central Process Manager & Storage Reclamation](docs/reports/session_6b/SESSION_6B_COMPLETION_REPORT.md)
- [Central Process Manager Architecture Design](docs/architecture/PROCESS_MANAGER_DESIGN.md)
- [Session 16 Product Acceptance, Short-Form Quality & Workflow Completion Report](docs/reports/session_16/SESSION_16_PRODUCT_ACCEPTANCE_REPORT.md)
- [Session 23 Real-Media AI Quality Validation & Professional Video Acceptance Report](docs/reports/session_23/SESSION_23_PROFESSIONAL_QUALITY_ACCEPTANCE.md)
- [Session 22 End-to-End Generation Repair & Real Video Export Acceptance Report](docs/reports/session_22/SESSION_22_END_TO_END_GENERATION_ACCEPTANCE.md)
- [Session 15 Long-Video Endurance, Job Recovery & Production Workflow Report](docs/reports/session_15/SESSION_15_ENDURANCE_REPORT.md)
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