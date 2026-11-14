# ZezEdit 2.0 — Master Requirements Specification

**Version:** 2.0.0-alpha.1  
**Target Platform:** Windows 11 (CPU-First, Local-Only Capable)  
**Target Hardware Baseline:** Intel Core i3-1220P, ~20 GB RAM, Intel UHD Integrated Graphics (No NVIDIA GPU / No CUDA)  
**Local AI Runtime:** Ollama (`http://127.0.0.1:11434`, verified `qwen3-vl:4b-instruct`), Faster-Whisper (CPU), FFmpeg / FFprobe, OpenCV

---

## 1. Mission & Product Vision

ZezEdit 2.0 is a modular, local-first AI-assisted video editing application for Windows. Following the loss of the previous `D:\Antrigavity2\ZezEdit` source tree, ZezEdit 2.0 rebuilds the platform at `D:\ZezEdit` with strict data-safety boundaries, versioned database migrations, a single authoritative job orchestrator, and clean module isolation.

ZezEdit combines automated long-form video intelligence with CapCut/InShot-caliber manual timeline control:
1. Automated long-video ingestion, proxy generation, and multimodal analysis.
2. Context-aware highlight and viral-moment discovery (candidate clips with setup & payoff).
3. Automated Shorts/Reels generation (`9:16`, `16:9`, `1:1`).
4. Context-aware dynamic portrait reframing with manual override keyframes and non-destructive revisions.
5. Complete non-destructive multi-track manual timeline editor.
6. Project-aware conversational AI Video Editor executing strictly validated edit plans.
7. Independent Character Extraction Studio & persistent Character Library (non-3D; evidence-based).
8. Audio editing, background music ducking, animated captions, effects, transitions, and overlays.
9. Reliable background FFmpeg rendering with output validation.
10. Persistent projects, undo/redo history, job recovery, storage management, and diagnostics.

---

## 2. Hardware & Resource Constraints (Mandatory)

All features MUST comply with these baseline constraints:
- **Zero CUDA Dependency:** GPU acceleration (QuickSync/OpenCL/etc.) is strictly optional. Every pipeline step MUST execute reliably on CPU (`i3-1220P` class).
- **Large File Streaming:** Designed for long-form source files (1–2 GB+ MP4/MKV/MOV). Full decoded video frames MUST NOT be loaded into RAM at once.
- **Bounded Memory & Concurrency:**
  - Prefer FFmpeg subprocess streaming, keyframe/interval frame sampling, disk-backed proxies (`480p`/`720p`), bounded queues, and SQLite/JSON intermediate checkpoints.
  - Default maximum concurrent heavy jobs: `1` (configurable via `ZEZEDIT_MAX_CONCURRENT_JOBS`).
  - FFmpeg thread count bounded (`ZEZEDIT_FFMPEG_THREADS=4`) so Windows UI and Ollama remain responsive.

---

## 3. Core Functional Modules (A–J)

### Module A — Dashboard & Project Management
- Project creation, listing, recent projects, search, and safe archiving/deletion.
- Media inspection metadata display (codec, resolution, FPS, duration, audio layout).
- Persistent processing history, generation runs, and export history.

### Module B — Media Library
- Safe import of video and audio assets (streaming copy or registered immutable reference).
- FFprobe metadata extraction, thumbnail strip generation, and edit proxy generation.
- Search/filtering by filename, format, duration, and status.
- Clear state distinction between **Missing Media** (moved/renamed/unmounted external file, eligible for relinking) and **Explicitly Deleted Media**.

### Module C — Video Analysis
- FFmpeg/OpenCV scene cut detection.
- Local Faster-Whisper speech-to-text transcription and word/sentence segmentation.
- Sampled frame visual analysis via Ollama (`qwen3-vl:4b-instruct` or configured model) and OpenCV face/saliency detection.
- **Honesty Constraint:** Analysis outputs record confidence/evidence rather than claiming capabilities models cannot reliably verify (e.g., no unverified emotion/identity claims).

### Module D — Highlight Discovery & Intelligent Candidate Discovery
- Analyze transcript + visual + scene-cut context before and after candidate windows to preserve setup and payoff without clipping sentences.
- **Natural Boundary Snapping:** Start times snap to word boundaries with 0.15s lead-in breathing room; end times snap to sentence terminal punctuation (`.`, `!`, `?`); aligns with visual scene cuts ($\le 0.45\text{s}$) to prevent flash frames and mid-sentence cutoffs.
- **Multimodal Signal Scoring (0–100):** Evaluates Hook Strength, Dialogue Interest, Emotional Signal, Action & Motion, Visual Presentation, and Narrative Completeness.
- **7 Creative Direction Profiles:** Adaptively alters score weights for Best Overall, Viral & Punchy, Dramatic, Action & Motion, Emotional / Sad, Engaging Dialogue, and Humorous.
- **Persistent Novelty & Non-Repetition Engine:** Records all generated intervals in `media_generated_clips_history`. Future discovery runs calculate temporal Intersection-over-Union ($\text{tIoU}$) against all historical intervals and strictly exclude candidates with $\text{tIoU} \ge 0.50$ or $\text{OverlapRatio} \ge 0.60$.
- **Honesty Constraint:** Ranking scores represent heuristic/multimodal attractiveness estimates—truthfully labeled as "Attractiveness estimate" or "Attractiveness: XX/100 (estimate)", never as guaranteed "viral probability."

### Module E — Smart Reframing
- Subject/face detection, single-person focus, two-person joint dialogue composition, and smooth velocity-clamped dynamic crop trajectories.
- Scene-cut awareness (never interpolates pan across a hard cut).
- Portrait (`9:16`) preview, headroom protection, manual override keyframes (`center_x`, `center_y`, `zoom`), and non-destructive revision renders (`_rev2.mp4`, etc.).
- **Authoritative Parity:** The frame preview evaluator and final FFmpeg filtergraph generator MUST share the exact same crop math function.

### Module F — Multi-Track Timeline Editor
- Shared timeline model supporting multiple video, audio, overlay, and text/caption tracks.
- Clip move, trim, split, ripple/delete, track visibility/mute/lock, zoom, scroll, snapping, playhead seek/scrub, undo/redo, and autosave.
- Bounded single-viewport NLE layout (learned from historical `BUG-08A-3`: prevents page-level scrollbar fighting).

### Module G — AI Video Editor
- Natural-language conversational assistant understanding active project state, transcript, timeline, and edit history.
- Strict separation of **Planning** (Ollama produces validated JSON `EditPlan` schema) vs **Execution** (deterministic executor applies timeline mutations after user preview & confirmation).
- Full undo/redo support. AI MUST NEVER execute arbitrary shell commands or raw filesystem calls.

### Module H — Character Extraction Studio
- Completely decoupled from Shorts generation (and strictly excludes historical 3D character mesh/rigging bloat).
- Scene-sampled visual observations, face detection + saliency fallback, provisional entity clustering, sampled screen-time estimates, human review (merge, separate, rename, reject), confirmed character profiles, and evidence-linked dialogue cues.
- **Honesty Constraint:** Visual clustering similarity is never claimed as biometric identity proof; timestamp overlap with speech is labeled as tentative attribution until human confirmation.

### Module I — Rendering & Export
- Multi-aspect targets (`9:16`, `16:9`, `1:1`), resolution & FPS presets, H.264 (`libx264`, `yuv420p`) and AAC encoding, burned-in/soft captions, effects, transitions.
- Draft preview renders vs final full-quality exports.
- Post-render FFprobe validation verifying non-zero duration, valid streams, and target dimensions.
- Overwrite protection (never silently overwrites existing export files).

### Module J — Settings & Diagnostics
- Authoritative Ollama model inventory via `GET /api/tags` (never hardcoded or stale cache without fallback; learned from `BUG-08A-7` and M13M.8).
- Asynchronous non-blocking model pull (`POST` -> `202` + status polling; learned from `BUG-08A-8`).
- FFmpeg/FFprobe availability diagnostics, storage breakdown by category (`media`, `proxies`, `exports`, `temp`, `backups`), CPU/RAM limits, live job monitor + logs, backup/restore controls.

---

## 4. Mandatory Data Protection & Reliability Rules

1. **Immutable Source Media:** Imported source videos/audio MUST NEVER be overwritten, transcoded in place, or altered.
2. **Non-Destructive Edits:** Timeline edits, crop overrides, and AI edits store declarative operations and versioned snapshots.
3. **Versioned Migrations:** All SQLite schema modifications MUST use numbered SQL migration scripts tracked in `schema_migrations`.
4. **Single Authoritative Job Queue:** Only one centralized job queue owns background work, process PIDs, retries, cancellations, and startup recovery.
5. **Path Containment & No Root Recursive Deletion:** Every resolved filesystem target is verified to live inside an explicitly permitted storage subdirectory. Recursive deletion of the configured `ZEZEDIT_STORAGE_ROOT` is structurally prohibited at code level.
6. **Confirmations & Ownership:** Destructive file actions require explicit confirmation tokens/requests. Temporary files carry job/project ownership tags and bounded TTL cleanup that never touches user assets or projects.

---

## 5. Planned Milestone Sequence

- **Milestone 1 (Completed):** Architecture Redesign, Documentation Blueprint, Migration Runner, Path Safety Core, FastAPI + React Skeleton, Health/Diagnostics Verification.
- **Milestone 2 (Completed):** Core Backend, Database, Persistent Projects, Storage Management, SQLite Backups & REST Foundation.
- **Milestone 3 (Completed):** Frontend Application Shell, Dashboard, Unified Design System, Responsive Layout & Studio Theme.
- **Milestone 4 (Completed):** Media Ingestion, Streaming Import, FFprobe Metadata Extraction, Thumbnails, Proxy Pipeline & Relinking.
- **Milestone 5 (Completed):** Video Analysis Engine (FFmpeg Scenes, Faster-Whisper CPU Transcription, Frame Sampling, Ollama/Fallback Visual Understanding, Multimodal Context Aggregation).
- **Milestone 6 (Completed):** AI Highlight Discovery, Contextual Clip Selection, Explainable 9-Component Scoring Engine, Quality Gates & Shorts Candidate Studio.
- **Milestone 7 (Completed):** Smart Reframing Engine, CPU-First Subject Tracking, Dynamic Trajectory Smoothing, Scene-Cut Isolation, Preview/Render Math Parity, Dual Viewports Review Workspace, Non-Destructive Revisions & Real FFmpeg Rendering.
- **Milestone 8 (Completed):** Rendering Engine, Export Pipeline & Automatic Shorts Generation (15-Stage Modular Pipeline, Presets, Caption & ASS Subtitle Engine, Audio Processing, Process Tracking, Output Validation Gate, Export Studio).
- **Milestone 9 (Completed):** AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Shared Timeline Architecture, Reversible Commands, Persistent Undo/Redo, AI Assistant Planning & Review Gate, Multi-Track Rendering Integration).
- **Milestone 10 (Completed):** Character Extraction Studio, Character Library, System Integration & End-to-End Reliability (CPU-First Frame Sampling, YCrCb Contour & Saliency Detection, Provisional Spatial-Temporal Clustering, Non-Destructive Review Operations, Persistent Library & JSON Export).
- **Milestone 11 (Completed):** Product UX Restoration, Unslop UI Redesign, Graphify Integration, Unified Video Workspace & Post-Import Guided Ingestion Flow.
- **Milestone 12 (Completed):** Pre-Deletion Baseline Reconstruction & Feature Parity Specification (Forensic Recovery of 13M.12 / 13M.13, Feature Parity Matrix, Historical vs Current Audit, Restoration Roadmap).
- **Milestone 13 (Completed):** ZezEdit 1.0 Exact Feature, Workflow, UI & Architecture Restoration Plan (100 Immutable Parity Requirements `ZEZ-001`–`ZEZ-100`, Standardized Scorecard: 89% Restored, Restoration Implementation Schedule).
- **Milestone 17 (Completed):** Core Product Workflow, Working Queue & Desktop Operations (Continuous Video-to-Shorts Pipeline, Next Video Transition Modal, Hardware Resource Inspector `ResourceInspector.tsx`, Working Queue Screen `WorkingQueueView.tsx`, AI Provider Manager `AIProviderManager.tsx`, In-App Documentation Center `DocumentationView.tsx`, Scope Deferral of Character Studio).
- **Milestone 18 (Completed):** Unified Video-to-Shorts Production Pipeline (Authoritative Lifecycle State Machine `WorkflowStateMachine` with 18 explicit stages, Workflow Telemetry API, Multiple Shorts Batch Export Endpoint & Modal `BatchExportModal.tsx`, Authoritative Workflow Banner & Stepper in Video Workspace, Per-Video Autosave & Multi-Video Isolation).
- **Milestone 19 (Completed):** Desktop Operations Center, Working Queue, Resource Inspector and AI Provider Manager (Real background-job lifecycle management, job cancellation & retry state machine, live queue stats & task-type distribution breakdown, compact hover-activated hardware Resource Inspector with Escape/click-outside dismiss & click-to-pin, AI Provider Manager with local-first task engine routing & secret masking, Documentation Center with 16 comprehensive guides across 5 categories, and real Subsystem Diagnostics API).
- **Milestone 20 (Completed):** Production Hardening, Long-Video Performance, Storage Management & Recovery (`ZEZ-018` Media Relinking, Storage Breakdown & Cache Cleanup).
- **Milestone 21 (Completed):** Authoritative ZezEdit 1.0 Restoration Audit, Graphify-First Code Investigation & UI Quality Assessment (`ZEZ-054` Manual Keyframe Placement & Interpolation).
- **Milestone 22 (Completed):** Evidence-Based ZezEdit 1.0 Restoration + Permanent Progress Tracker (`ZEZ-050` Dual-Viewport Reframing Review Modal, `ZEZ-051` Interactive Draggable Crop Rectangle, `ZEZ-052` Timeline Keyframe Diamond Scrubber).
- **Milestone 23 (Completed):** Continue ZezEdit 1.0 Parity Restoration (`ZEZ-080` AI Assistant Plan Version History Drawer & Restore, `ZEZ-008` Global Floating Toast Notification System).
- **Milestone 24 (Completed):** ZezEdit 1.0 Parity Restoration, Independent Verification and Cumulative Progress Accounting (`ZEZ-099` Automated Regression Test Suite Expansion & 100% Active Scope Parity Sign-off: 121 backend tests, 88 frontend tests, 209 cumulative tests).
- **Milestone 25 (Completed):** ZezEdit 1.0 Restoration, Requirement Verification and Permanent Progress Tracking (Formal Independent Audit and Verification of all 90 Active Requirements: 100% active parity verified, 209 tests passed).
- **Milestone 26 (Completed):** ZezEdit 1.0 Complete Parity Restoration (Final Independent Verification, Audit, Code Graph Synchronization & Parity Certification).
- **Milestone 27 (Completed):** ZezEdit 1.0 Parity Restoration, End-to-End Validation and Permanent Progress Accounting (Exhaustive Full-Stack Re-Verification, 121 backend + 88 frontend tests, 100% active parity verified).
- **Milestone 28 (Completed):** ZezEdit 1.0 Parity Restoration, Partial Feature Completion and Cumulative Progress Tracking (Re-verified 209 tests, 100% active scope verified, 0 remaining active requirements).
- **Milestone 29 (Completed):** ZezEdit 1.0 Restoration, Functional Completion and Cumulative Progress Management (Full-stack independent re-verification, 121 backend + 88 frontend tests, 100% active parity verified).
- **Milestone 30 (Completed):** ZezEdit 1.0 Parity Restoration, Independent Verification and Cumulative Completion Control (Comprehensive re-audit, 209 tests passed, 100% active parity verified, 0 remaining active requirements).
- **Session 0 (Completed):** Complete Project Audit, Architecture Redesign & Multi-Session Implementation Plan (Unified Video Studio architecture, 5 comprehensive design blueprints under `docs/architecture/`).
- **Session 1 (Completed):** Navigation Simplification & Media Library Focus (Removal of disconnected studio tools from sidebar, direct "Open Video Studio" primary action on media cards, unslopped design system).
- **Session 2 (Completed):** Dedicated Single-Video Studio: Workspace, Navigation, Configuration and Backend Integration (`/studio/:assetId` dedicated route, `SingleVideoStudio.tsx`, Global Analysis Progress Bar, Upfront Generation Configuration Bar, Framed Preview Player with dynamic aspect-ratio framing, Generated Shorts Showcase with candidate discovery & direct export triggers, collapsible intelligence drawers, full Vitest test coverage).

- **Session 3 (Completed):** Unified Full-Video Analysis Pipeline (Sequential background pipeline, bounded memory streaming for 1–2 GB movies without RAM bloat, deterministic `size:mtime:hash64k` source signature & instant cache invalidation, Faster-Whisper int8 speech recognition with automatic VAD retry fallback for mixed audio / dialogue over music, persistent `JobOrchestrator` linkage with synchronized checkpoints, live stage telemetry endpoint `GET /analysis/{id}/telemetry` and cache query `GET /analysis/{id}/cache`, cancellation `POST /analysis/{id}/cancel` and retry `POST /analysis/{id}/retry`, audio-less media support, and frontend Studio live progress banner with real-time stage description, elapsed timer, and cancel/retry controls).
- **Session 4 (Completed):** Intelligent Candidate Discovery, Multimodal Scoring, Natural Boundaries & Persistent Non-Repetition (`highlight_discovery.py`, 7 creative direction weighting profiles, sentence-boundary snap, scene-cut boundary snap, multimodal scoring, persistent novelty ledger with overlap rejection).
- **Session 5 (Completed):** Interactive Clip Preview, Editing, Smart Reframing & Subject Tracking (`CandidateClipEditorModal.tsx`, 9:16 and 1:1 aspect ratio overlays, manual framing offset sliders, CPU Haar cascade subject tracking, trim handles, migration 0014 `candidate_clip_edits`).
- **Product Restructure & UI Redesign (Completed):** Restored original ZezEdit workflow organized entirely around the Video:
  - Streamlined primary sidebar: `Dashboard`, `Short Video Generator`, `Working Queue`, `AI Providers`, `Settings`.
  - Direct video ingestion (drag & drop / file picker) with client-side format validation, automatic filename-derived title, and zero manual project/grouping requirements.
  - Dedicated Video Edit Dashboard (`/videos/:assetId`) featuring persistent header with title and real-time multi-stage loading bar (% completed and time remaining) + 8 top horizontal tabs:
    1. `Home`: Video player and pure technical metadata table only.
    2. `Short Video Generator`: Preset & custom clip count, 18 creative directions / contexts, aspect ratios (`9:16`, `1:1`, `16:9`, `4:5`), tracking modes (face, upper body, object, multi-subject), duration range, and Generate Shorts button.
    3. `Generated Shorts`: Candidate short cards with attractiveness score, cut timestamps, "Edit Clip" modal integration, and "Export MP4" trigger.
    4. `Generated Scripts`: Script cards preserving hook sentence, dialogue transcript, narrative flow, and 1-click "Regenerate Video from Script" button.
    5. `Analyzed Frames`: Keyframe gallery with timestamps and observation tags with click-to-seek playback.
    6. `Voice & Transcript Analysis`: Searchable speech turns with timestamped dialogue and click-to-seek.
    7. `Scene Analysis`: Detected scene transitions with inclusion/exclusion checkboxes for short generation.
    8. `Video Analysis Details`: Deep pipeline component status and cache telemetry.
  - Single-button "Clear All Application Data" in Settings (`Storage & Data` tab) with explicit `DELETE` confirmation modal and backend API `POST /api/v1/storage/clear-all-data` cleanly sweeping all managed storage and resetting database tables.
- **Session 6A (Completed):** AI-First Video Analysis, Simple Short Generation, Advanced Settings & Non-Repeating Generate More:
  - Deep source analysis stored once and reused for all subsequent short generation requests without redundant processing (~0.12s discovery execution vs multi-minute re-analysis).
  - Video Intelligence Status Banner on the Video Edit Dashboard with cache status indicator and manual "Re-Analyze Source Video" override.
  - Simplified Short Video Generator UI: clean, calm default form featuring 4 core options:
    1. Quantity: AI Recommended clip count default with quick preset pills (1, 3, 5, 10, 15, Custom).
    2. Creative Direction: 2 clean cards (Best Overall vs Discover Varied / Viral-Style Moments).
    3. Target Aspect Ratio: 9:16 Vertical default with standard presets (1:1, 16:9, 4:5, 4:3, 3:4).
    4. Duration: AI Selects Best Duration default with preset ranges (Short 15–30s, Medium 30–60s, Long 60–90s, Custom).
  - Collapsible Advanced Settings (collapsed by default):
    - 18 creative directions: 7 active supported profiles, 11 badged "Coming Soon" with disabled state.
    - Subject tracking modes (Auto Speaker, Single Subject, Two-Person, Saliency Fallback).
    - Scene focus modes (All Scenes, Action Heavy, Dialogue Only).
    - Novelty policy controls (Strict vs Relaxed).
    - Per-video configuration persistence in `localStorage` with "Save Video Preferences" and "Reset to Defaults".
  - Persistent Non-Repetition ("Generate More Shorts"):
    - Multi-layer novelty filter: exact timestamp matching (<2.5s tolerance), temporal IoU / asymmetric overlap guards, transcript token similarity.
    - Aspect-ratio independent rejection: changing aspect ratio tests candidates against all historical clips.
    - Honest novelty exhaustion: returns 0 duplicates and sets `is_novelty_exhausted = True` when all moments are exhausted.
  - Generated Shorts Management:
    - Clear distinction between Discovered Candidate and Rendered MP4.
    - Batch filter dropdown and "Generate More Shorts" button in Tab 3 header.
  - Real Video Verification on 73.3MB media file (`Ek Mota Hathi Ghumne Chala.mp4`):
    - Reused analysis `run_b0ebbcb45a17` in 0.127s.
    - Batch A produced 2 new candidates; Batch B "Generate More" evaluated 366 candidates and generated 0 duplicates with honest exhaustion detection.
  - Comprehensive Automated Regression Parity: 152/152 backend tests and 106/106 frontend tests passing.
- **Session 6B (Completed):** Central Process Manager + Complete User Data Deletion & Storage Reclamation:
  - **Part A — Central Process Manager:**
    - Sidebar navigation relabeled to **Processes** with backwards-compatible routing (`/processes` alongside `/queue`).
    - Centralized monitoring dashboard for all background operations across all source videos (Upload, Validation, Analysis, Whisper, Frames, Scenes, Tracking, Highlights, Short generation, Clip editing, Reframing, MP4 export, Cache cleanup, Clear data).
    - Multi-dimensional filtering by Category (Media, Analysis, Generation, Rendering, Storage), Status (All, Running, Queued, Completed, Failed, Cancelled), Source Video selector, and fast substring search across process ID, job type, video title, and stage.
    - Process lifecycle controls: Stop/Cancel (gracefully terminates running OS process trees via `psutil` and unlinks temporary file handles), Retry (creates new linked attempt preserving original job record with retry lineage), Delete Record (removes terminal record without touching media), Clear Completed History (purges finished jobs).
    - Detailed process drawer displaying execution telemetry, elapsed/remaining time, child/parent lineage, and live formatted log stream.
    - Backend startup crash recovery: marks stale `running`/`cancelling` jobs as `interrupted` upon daemon restart.
    - Full API parity across `/api/v1/processes` and `/api/v1/jobs`.
  - **Part B — Complete User Data Deletion & Storage Reclamation:**
    - Root cause analysis and resolution for previous disk reclamation failures: single video deletion now removes all associated files on disk (`media/`, `proxies/`, `thumbnails/`, `analysis/`), SQLite WAL mode compactor executes `PRAGMA wal_checkpoint(TRUNCATE); VACUUM; PRAGMA wal_checkpoint(TRUNCATE);`, and active file handles are cleanly closed.
    - Storage Cleanup Preview endpoint (`GET /api/v1/storage/cleanup-preview`) reporting item counts (videos, clips, frames, temp files) and estimated reclaimable bytes.
    - Complete Storage Reclamation endpoint (`POST /api/v1/storage/clear-all-user-data`) requiring strict confirmation (`DELETE ALL USER DATA` or `DELETE`):
      - Terminates all active child processes.
      - Sweeps and recreates all managed storage subdirectories (`media/`, `proxies/`, `thumbnails/`, `analysis/`, `characters/`, `timelines/`, `shorts/`, `exports/`, `temp/`).
      - Preserves external files outside `storage_root` and preserves `schema_migrations` and `app_settings`.
      - Truncates database tables in dependency-safe order and resets default project.
      - Executes double WAL truncation and SQLite vacuum, returning exact pre/post byte measurements.
    - UI integration in Settings > Storage with live storage metrics, preview breakdown, active job warnings, and confirmation modal.
    - Comprehensive Automated Regression Parity: 164/164 backend tests and 115/115 frontend tests passing.
- **Session 6C (Completed):** Real Short Video Rendering, Clip Editing, Batch Export & Output Verification:
  - 15-stage modular FFmpeg video rendering pipeline transforming short video candidates into playable, verified H.264/AAC MP4 files.
  - Full candidate lifecycle: Preview, Select, Edit, Render Single, Batch Select, Batch Render.
  - Candidate clip editing integration: `ExportService` seamlessly respects `CandidateClipEditorModal` timestamp trims (`edited_start_time`, `edited_end_time`) and manual crop parameters (`manual_crop_x_pct`, `manual_crop_y_pct`, `manual_crop_zoom`).
  - Extended aspect-ratio preset catalog with `9:16` (1080x1920), `16:9` (1920x1080), `1:1` (1080x1080), `4:5` (1080x1350), `4:3` (1440x1080), and `3:4` (1080x1440).
  - Background rendering linked to `JobOrchestrator` with `media_asset_id` association, displaying jobs with source video filename in Central Process Manager.
  - Dedicated "Generated Videos" archive tab in `VideoEditDashboard.tsx` with playable video cards, technical metadata badges (resolution, aspect ratio, duration, size, codec, verification status), direct MP4 download link, and deletion.
  - In-browser HTML5 video player modal featuring seek bar, play/pause controls, elapsed/total time, download action, and partial content (HTTP 206) streaming.
  - Mandatory post-render output verification via `OutputValidator` requiring FFprobe stream checks and FFmpeg null-sink decode verification before marking exports completed.
  - Multi-aspect real video verification: rendered vertical `9:16`, square `1:1`, and landscape `16:9` MP4s, verified with FFprobe and live in-browser playback via Browser Subagent.
  - Comprehensive Automated Regression Parity: 169/169 backend tests passing (100%) and 120/120 frontend tests passing (100%).
- **Session 7 (Completed):** Complete Product Integration, Real-World Validation & Workflow Refinement:
  - Validated complete end-to-end workflow on real 5.04-minute 1080p long video (`Ek Mota Hathi Ghumne Chala.mp4`, 73.4 MB).
  - Deep source analysis completed in 109.4s: extracted 37 scenes, 74 transcript segments, 41 sampled frames, and 12 visual observations.
  - Reusable video intelligence persistence confirmed across application restarts.
  - Simplified default generator verified (AI Recommended clip count, Best Overall direction, 9:16 vertical, AI Best Duration; advanced settings collapsed).
  - Multi-batch candidate discovery and persistent novelty ledger: Batch 1 (3 clips in 0.292s) and Batch 2 Generate More (3 clips in 0.282s) produced 6 distinct non-overlapping clips (0 duplicate IDs).
  - Candidate clip editing integration: verified non-destructive trims (65.0s–85.0s), custom crop coordinates, and zoom.
  - Rendered 4 real shorts: Two 9:16 vertical (20.52s, 30.08s), One 1:1 square edited (20.00s), One 16:9 landscape (45.36s).
  - All 4 rendered MP4s verified with FFprobe and passed `OutputValidator` decode checks.
  - In-browser HTML5 video player modal verified with smooth playback, seeking, and synchronized burned subtitles via Browser Subagent.
  - Central Process Manager verified tracking all 10 render and analysis jobs with execution telemetry and source video linkage.
  - Honest tracking capability audit: OpenCV Haar cascades for face/upper body, color saliency fallback; multi-subject/speaker tracking marked unsupported.
  - Full regression pass: 169/169 backend pytests passed (100%), 120/120 frontend vitests passed (100%), 0 TypeScript compilation errors.
- **Session 8 (Completed):** Real Object Tracking, Multi-Subject Intelligence & Temporal Novelty Correction:
  - Corrected temporal novelty calculation flaw: added relative containment ratio $R_{\min} = \frac{\text{Intersection}}{\min(\text{dur}_A, \text{dur}_B)}$ to prevent longer containing cuts (e.g. $[63.07, 87.31]$ vs $[63.07, 114.01]$) from co-occurring in the same batch or across subsequent Generate More runs.
  - Implemented intra-batch candidate overlap validation and alternative cut clustering in `HighlightDiscoveryEngine`.
  - Replaced legacy cascade calls with modern, CPU-friendly multi-stage vision detector: YCrCb skin chroma segmentation for `face` and `person` ($h/w \ge 1.3 \to$ person, $0.7 \le h/w < 1.3 \to$ face) and Sobel gradient magnitude for foreground objects/vehicles ($w/h \ge 1.4 \to$ vehicle/object).
  - Implemented genuine temporal object tracking using OpenCV `TrackerMIL` instances, preserving independent track identities (`subject_1`, `subject_2`, etc.) across frame samples.
  - Scene-cut aware track termination: active tracks terminate strictly at scene transitions.
  - Multi-subject framing strategies in `FramingEngine`: `primary_subject` (prominence-ranked), `two_person` (joint framing), `group`/`all_subjects` (union bounding box), `action_object` (object/vehicle prioritization), and `pinned_subject_id`.
  - Dynamic tracking render pipeline integration: `ExportService._resolve_keyframes` dynamically executes `ReframingService` on demand and compiles piecewise-linear FFmpeg crop expressions (`crop=w:h:x(t):y(t)`).
  - Speaker-focused framing capability audit: clearly distinguished Available capabilities (Face/Person, Object, Group framing) from Unsupported capabilities (Deep neural AV speaker diarization on CPU baseline).
  - Full automated verification: 12 new tests in `test_session8_tracking_and_novelty.py`, 181/181 backend pytests passed (100%), 120/120 frontend vitests passed (100%), clean TypeScript build.
- **Session 9 (Completed):** Critical Performance Diagnostics, Stuck Analysis Repair & Complete Short-Video Generation Validation:
  - Forensic diagnosis of pipeline freeze on 5-minute video `Ek Mota Hathi Ghumne Chala.mp4` (302.4s, 70MB): Starlette event loop blocking by synchronous Whisper/FFmpeg tasks resolved with AnyIO threadpool worker offloading.
  - HTTP polling latency during heavy transcription reduced from infinite/timeout to 10.92ms average (max 79ms).
  - Implemented Faster-Whisper singleton model caching in `_WHISPER_CACHE`, dropping recurring model load times to 0.00s.
  - Fixed VAD filter zero-yield pitfall with direct non-VAD primary processing and streaming segment callbacks with real work units (seconds transcribed), ETA calculation, and speech text ticker.
  - Live analysis on real test video completed in 101.43s on CPU.
  - Replaced 91 sequential FFmpeg subprocess calls in `SubjectTracker.extract_frame_samples` with single batched extraction pass (40.9x speedup, 2.23s).
  - OpenCV TrackerMIL optimization: downscaled frames to 640px, filtered top 4 salient subjects, capped active trackers to 2 (reduced tracking from >100s to 11.5s).
  - Resolved stalled job false-positive detection on clean process exit with a 15-second grace period.
  - Verified default short video generation, all 7 creative directions, 4 quantity options, 5 duration modes, and zero-collision temporal novelty.
  - Real MP4 rendering verified across 9:16 portrait (1080x1920), 1:1 square (1080x1080), and 16:9 landscape (1920x1080) with 100% clean FFmpeg null-sink decode (`-f null -`).
  - Full automated verification: 181/181 backend pytests passed (100%), 120/120 frontend vitests passed (100%), 0 TypeScript compilation errors.
