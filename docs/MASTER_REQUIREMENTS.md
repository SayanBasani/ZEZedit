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

- **Priority 0 (P0.9 Accepted — P0 Fully Stabilized 9/9):** Production Stabilization & Hardening (Full backend suite 359/359 passing across 44 test files, Frontend 120/120 tests passed across 26 test files, TypeScript 0 errors, Single-Port Windows Production Serving verified, Database foreign keys & orphan exports reconciled, Job queue state machine, cancellation, subprocess kill, monotonic progress, retry idempotency, restart recovery verified, Windows launcher reliability verified, production serving verified, data persistence & crash recovery verified across 21 demonstrations, 100% data intact across all restarts).
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
- **Session 10 (Completed):** Safe Website Data Reset, Full System Audit & Real Video Analysis-to-Export Validation:
  - Safely reset all website user-generated data (1.77 GB reclaimed, 634 user files purged across media, exports, cache, temp) after creating and verifying a clean safety backup at `storage/backups/session10_prereset_backup/`.
  - Database schema, migrations 0001-0016, and system settings preserved; default workspace re-created clean with `PRAGMA integrity_check` = `ok`.
  - Parallelized thumbnail extraction in `scene_detector.py` and `frame_sampler.py` using `ThreadPoolExecutor(max_workers=6)` for ~5x faster execution on long videos.
  - Validated end-to-end video intelligence pipeline on real long-form Matroska video `D:\videos\BLACK TORCH S01E02.mkv` (236.38 MB, 1430.144s / ~23.8 minutes, 1 video stream, 3 audio streams, 3 subtitle streams).
  - Executed 17-stage video analysis in 498.90s (~8.3 min, ~3x real-time speed): 490 transcript segments, 279 dialogue turns, 354 scenes, 50 frames, 12 visual observations.
  - Validated Short Video Candidate Discovery across all creative directions (Best Overall, Action, Dialogue, Emotional, Educational, Dramatic, Humor), clip quantities (1, 3, 5), duration options (15s, 30s, 60s), and aspect ratios (9:16, 1:1, 16:9).
  - Validated "Generate More Shorts" (Batch 2) with strict novelty: returned 3 novel candidates with 0 duplicate IDs, $R_{\min} < 0.85$, and $tIoU < 0.70$.
  - Rendered real MP4 short videos in 9:16 portrait (`exp_e8d1e3049bd9`), 1:1 square (`exp_1213ece782a6`), and 16:9 landscape (`exp_a0b40e2de760`) with faststart `moov` atom preceding `mdat` and 100% clean FFmpeg null-sink decode (`-f null -`, 0 errors).
  - Verified HTTP 206 Partial Content byte-range seeking and direct download endpoints.
  - Verified Central Process Manager lifecycle tracking for upload, analysis, discovery, and rendering.
  - Full regression pass: 181/181 backend pytests passed (100%), 120/120 frontend vitests passed (100%), 0 TypeScript compilation errors, production build verified.
  - Graphify updated: 3,266 nodes, 8,940 edges, 175 communities.
- **Session 12 (Completed):** Independent Acceptance Testing, Job Reliability Stress Testing & Session 11 Defect Repair:
  - Hardened process liveness detection in `JobOrchestrator`: strictly checks `is_dedicated_child_proc = (pid and pid != os.getpid() and psutil.pid_exists(pid))` so in-process worker threads sharing Uvicorn's PID are never falsely granted child-process exemption.
  - Implemented 16-case job lifecycle stress suite in `test_session12_job_lifecycle_stress.py` covering normal completion, slow stages, thread crashes, deadlocks, restart recovery, cancellation, and race conditions (16/16 passed).
  - Scalable server-side exports API (`GET /projects/{id}/exports` with pagination, search, status, and aspect filters). Verified sub-15ms response on 1,000 export records.
  - Browser verification on `Visionquest S01E08.mkv`: verified modal, inline playback, and decoupled script preservation.
- **Session 13 (Completed):** Video Understanding, Shortlist Quality Audit & Dialogue Grounding:
  - Replaced turn ID placeholders (`speaker_turn_01`) in generated scripts with Whisper speech transcripts.
  - Multi-subject framing heuristic audit and speaker tracking fallback evaluation.
- **Session 14 (Completed):** Reliability, Rendering & Quality Acceptance:
  - Strictly enforced job lifecycle state invariants: terminal states (`failed`, `cancelled`, `completed`) are strictly immutable in `JobOrchestrator`.
  - Removed obsolete "stalled heal" backdoor (`is_stalled_heal`), ensuring failed jobs never transition to completed merely upon reaching 100% progress.
  - Heartbeat ticker inactivity bounds (`max_inactive_seconds=180.0`, `max_stage_seconds=1800.0`) actively prevent deadlock and premature stall abortion during Whisper transcription, scene detection, and frame sampling.
  - Creative Direction Differentiation: integrated humor vocabulary scoring, witty banter velocity detection, multi-speaker Q&A detection, and educational cues, achieving up to 100% candidate differentiation across all 7 styles on `Visionquest S01E08.mkv` (5,193 candidate intervals).
  - Full 7-Scenario Rendering Matrix: verified 9:16 portrait static crop, 9:16 moving pan, 9:16 subject-tracking, 9:16 with ASS captions + loudnorm audio transcode, 1:1 square crop, 16:9 landscape letterbox/scale, and 3-audio stream MKV transcode (`BLACK TORCH S01E02.mkv`). 100% clean bitstream decode (`-f null -`) with 0 errors across all outputs.
  - Frontend timeout verified: 180s API timeout in `apiClient.ts` eliminates the 15s browser abort alert; interactive live UI verification confirmed on `http://localhost:5173/videos/med_290ccbe1f97d`.
  - Script & Video persistence isolation verified: deleting an export safely removes the rendered MP4 file while strictly preserving the candidate script and source media asset.
- **Session 16 (Completed):** Product Acceptance, Short-Form Quality & Workflow Completion:
  - Addressed all 6 architectural audit questions from Sessions 13–15 regarding Whisper execution chunks, stale queued states, and worker claiming concurrency.
  - Implemented `claim_next_queued_job` with atomic single-statement SQL UPDATE `WHERE id = ? AND status = 'queued'`, guaranteeing two concurrent workers cannot claim the same job (verified under 5 concurrent threads).
  - Implemented background queue dispatching loop in `JobOrchestrator.dispatch_queued_jobs` and automatic stale queue timeout reclamation (`cleanup_stale_queued_jobs`, 1800s timeout).
  - Resolved thumbnail 500 error on global media assets; implemented dynamic JPEG synthesis and caching.
  - Added dedicated Edit Short Video Script modal on Generated Scripts tab; verified full persistence of user-edited Title, Hook sentence, and Dialogue to SQLite across browser page refreshes.
  - Completed qualitative short-video evaluation across 7 core criteria (opening interest, narrative completeness, ending intentionality, dialogue coherence, visual relevance, creative direction, duration suitability).
  - Replaced speculative marketing terminology ("viral", "neural" claims for CV heuristics) with accurate technical capability labels.
  - Full regression gates verified: 4/4 acceptance tests in `test_session16_product_acceptance.py` passed, 120/120 frontend vitests passed across 26 suites, 0 TypeScript errors (`tsc --noEmit`), clean production build in 13.35s, and Graphify code knowledge graph updated.
- **Session 18 (Completed):** Queue Architecture Repair, Regression Stabilization & Integration Acceptance:
  - Audited full queue dispatcher lifecycle from end to end across `media_analysis`, `candidate_generation`, and `export_render`.
  - Fixed startup orphan reconciliation query in `recover_interrupted_jobs`, preserving active queued analysis runs and exports linked to queued jobs.
  - Fixed `_terminate_pid_tree` to strictly safeguard `os.getpid()`, terminating only child subprocesses (e.g. FFmpeg) without terminating the test runner or host process.
  - Repaired endpoint signatures in `highlights.py`: fixed missing `response` parameter in `generate_more_highlights` and unified `X-Job-Id` emission for asynchronous candidate discovery.
  - Fixed timing race conditions in frontend unit tests (`aiProviderManager.test.tsx` and `processesManager.test.tsx`), achieving 100% clean test passes:
    - Backend Pytest Suite: **250 passed, 0 failed, 0 skipped** (297.08s).
    - Frontend Vitest Suite: **26 test files passed, 120 passed, 0 failed** (27.83s).
    - TypeScript Compiler: **0 errors** (`npx tsc --noEmit`).
    - Production Build: **`npm run build` completed in 7.49s**.
  - Real Multimodal Queue Integration:
    - Candidate Generation: `job_bedad53ef5d2` on `Ek Mota Hathi Ghumne Chala.mp4` completed in 1.28s, persisting 2 new candidates.
    - Export Render: `job_0af7b48be499` on candidate `cand_d36872d51977` completed in 55.4s, generating valid 9:16 vertical 1080x1920 MP4 (17.1 MB) with ASS karaoke captions and dynamic crop, verified with FFprobe.
  - Interactive browser verification: verified Video Edit Dashboard, Generate Shorts modal, script editing, reload persistence, inline 9:16 playback, and Process Manager HUD.
- **Session 19 (Completed):** Final Product Acceptance Audit & Remaining Work Inventory:
  - Evidence-based audit of all product workflows: Media Library, Video Analysis, Candidate Discovery & Scripts, Video Editing & Rendering, Generated Videos & Scripts, Queue & Process Manager, Reliability & Storage, and UI & Usability.
  - Rigorous completion percentage derivation: **100.0% active product scope parity verified (90/90 requirements)**; **90.0% total historical requirements (10 deferred Character Studio requirements)**.
  - Automated quality gates: **250/250 backend tests passed (287.94s)**, **120/120 frontend vitests passed across 26 test files (18.49s)**, **0 TypeScript errors**, **clean production build in 6.70s**.
  - Interactive web browser verification across all 8 core views: Media Library, Video Edit Dashboard (Home, Shorts, Videos, Scripts, Frames, Transcript, Scenes), Generate Shorts Modal, Central Process Manager, AI Provider Manager, and Storage Management.
  - Final acceptance audit report generated at `docs/reports/session_19/SESSION_19_FINAL_ACCEPTANCE_AUDIT.md`.
- **Session 20 (Completed):** Multimodal Video Intelligence, Automatic Short Generation & Permanent Novelty Management:
  - Immediate modal dismissal and multi-step non-blocking progress banner.
  - Automatic export rendering on candidate discovery.
  - Decoupled video and script lifecycle (video deletion preserves script and novelty history; re-renders from script).
  - Sanitized content-derived download filenames.
- **Session 21 (Completed):** Multimodal Intelligence Completion, Real Subject Tracking & Permanent Novelty Verification:
  - Moving-subject tracking with OpenCV TrackerMIL + motion differencing and dynamic 9:16 portrait framing expressions.
  - Permanent novelty ledger surviving deletions of exports and scripts.
  - Full visual and audio timeline coverage metrics ($\ge 80\%$) and temporal alignment context query.
- **Session 22 (Completed):** End-to-End Generation Repair, Multimodal Acceptance & Real Video Export Verification:
  - Resolved the zero-video defect: Generate Shorts automatically discovers candidates, persists reusable scripts, and renders physical 1080x1920 MP4 files.
  - Accurate dynamic navigation tab label showing in-progress rendering status (`Generated Videos (N completed, M rendering)`).
  - Surfaced 1-click "Render Missing Videos (N)" recovery action across all relevant dashboard tabs.
  - Concurrency lock protection in `ExportService.execute_render_job` preventing duplicate worker execution race conditions.
  - Verified 260+ backend tests, 120 frontend vitests, 0 TypeScript errors, clean production build, and live browser verification with real 1080x1920 MP4 exports on disk.
  - Final verdict: `COMPLETE AND VERIFIED`.
- **Session 23 (Completed):** Real-Media AI Quality Validation & Professional Video Acceptance:
  - Honest multi-tier coverage model: distinguishes total duration, scene detection, decoded frames approx, sampled frames count, deep vision LLM frames, local CV frames, semantic visual span, density (fpm), and unprocessed intervals.
  - Coarse-to-fine sampling: scene midpoints plus fine context frames around dialogue and high-motion moments.
  - Full-duration audio intelligence: Faster-Whisper int8, language detection probability, word timestamps, silence detection, and truthful handling of unsupported sound-event recognition (`Not Installed`).
  - Moving-subject tracking across 6 controlled movement scenarios with $\ge 85\%$ subject visibility in rendered 9:16 vertical MP4 video crops.
  - Real-media human-reviewable evaluation across 10 qualitative criteria for 3 test media: `Ek Mota Hathi Ghumne Chala.mp4`, `BLACK TORCH S01E02.mkv`, and `Visionquest S01E08.mkv`.
  - Full automated regression test suites: 268/268 backend pytest passed (714.38s), 120/120 frontend vitests passed across 26 test files (21.20s), 0 TypeScript compiler errors, clean production build in 6.62s.
  - Final verdict: `BETA READY WITH DOCUMENTED LIMITATIONS`.
- **Session 24 (Implemented & Tested):** Windows Production Mode, One-Click Launcher & Release Hardening:
  - Unified single-port production frontend serving: FastAPI hosts the compiled Vite distribution (`frontend/dist`) on `http://127.0.0.1:8000` with SPA routing and asset protection.
  - One-click Windows startup & shutdown scripts: `Start-ZEZEdit.bat`, `Start-ZEZEdit.ps1`, `Stop-ZEZEdit.bat`, and `Stop-ZEZEdit.ps1` with 6-stage boot validation and non-destructive PID-tracked process lifecycle management.
  - Multi-state readiness health check: exposed `/health` and `/api/v1/health` evaluating process liveness, SQLite structural integrity (`PRAGMA integrity_check(1)`), storage writability, FFmpeg/FFprobe binaries, Ollama LLM, Faster-Whisper, background queue dispatcher, and frontend build presence.
  - Client-side deep link & direct refresh support: full React Router support on direct URL refresh without 404s.
  - Quality gates: 274 backend tests, 120 frontend tests, 0 TypeScript errors, clean production build verified.
- **P0.1 Project Audit & Failure Inventory (Completed):**
  - Comprehensive evidence-based repository audit conducted across Git state, documentation, tests, database, media storage, and launcher lifecycle.
  - P0 Status: **In Progress / Implemented but Uncommitted**.
  - Known Blockers: `P0.1-GIT-001` (Uncommitted working tree), `P0.5-DB-001` (Orphan export records from historical test runs).
- **P0.2 Backend Test Baseline, Root-Cause Diagnosis and Safe Repair (Accepted):**
  - Authoritative execution of complete backend test suite: **274/274 passed (0 failures, 0 skips, 0 errors)** in **584.05s** (exit code 0).
  - Verified job cancellation transition and queue CPU pressure test bypass.
  - Zero database records, user media, exports, or backups were deleted or altered (all tests isolated in `tmp_path`).
  - Backend imports and compilation verified clean (exit code 0).
- **P0.3 Frontend Stability, Real Browser Demonstrations and Output Review (Accepted):**
  - Frontend Vitest suite: **26/26 test files passed, 120/120 tests passed** in **20.49s** (exit code 0).
  - TypeScript typecheck passed with **0 errors**; clean production build in **7.51s**.
  - Executed 10 real browser demonstration workflows on `http://127.0.0.1:8000`: Home Media Library, Video Edit Dashboard (8 tabs), Shorts, Scripts, Videos (6 vertical MP4s), inline/modal playback, scene cut transitions, engine telemetry, Process Manager, and direct deep-link SPA refresh.
  - Inspected 12 screenshots saved to `docs/reports/priority_0/p0_3_evidence/`; 0 console exceptions.
- **P0.4 TypeScript and Production Build Stability (Accepted):**
  - Verified TypeScript compiler (`npx tsc --noEmit`): **0 errors**.
  - Verified Vite production build (`npm run build`): **0 errors** in **6.99s**.
  - Verified bundled static asset integrity: HTML shell, JavaScript chunks, CSS stylesheets, vendor chunks, and font/media assets.
  - Executed 5 browser acceptance demonstrations verifying production SPA routing, direct deep-link refresh, asset loading, interactive modal workflows, and responsive viewports.
- **P0.5 Database and API Consistency (Accepted):**
  - Resolved 16 SQLite foreign key check violations in `exports` (8) and `reframing_plans` (8) caused by legacy candidate deletions under inactive foreign keys; updated references to `NULL` honoring `ON DELETE SET NULL`.
  - Reconciled 5 missing historical export records (`exp_babf8b3065df`, `exp_ca31e61dd86b`, `exp_bb4e7d91afd2`, `exp_6443662c1cc0`, `exp_949ab5572f83`): marked `status = 'failed'`, `validation_status = 'invalid'`, zero rows deleted.
  - Enforced storage root directory boundary (`is_relative_to`) on export streaming, downloading, and file deletion; out-of-root access returns HTTP 403 Forbidden.
  - Created automated test suite `test_p0_5_database_and_api_consistency.py` (7/7 passed); export pipeline coverage tests (12/12 passed).
  - Executed all 6 live demonstration cases: DB integrity `ok`, valid 206 byte-range streaming, missing export 404, export deletion cascade isolation, 403 path traversal defense, and idempotent reconciliation.
- **P0.5-R1 Database/API Regression and Reconciliation Safety Closure (Accepted):**
  - Executed full backend pytest suite across all 41 test files: **281/281 passed in 362.83s (exit code 0)** with zero failures or skips.
  - Hardened `BackupService.reconcile_database_consistency` with explicit `BEGIN IMMEDIATE` transaction boundaries, ensuring atomic rollback on interruption and serialization under concurrent write workloads.
  - Audited `POST /api/v1/system/db-reconcile`: confirmed local-only binding, non-POST rejection (404/405), no sensitive stack trace leakage, and guaranteed idempotency.
  - Added 5 new concurrency/transaction tests to `test_p0_5_database_and_api_consistency.py` (12/12 passed): rollback on write interruption, 4 concurrent threads, active export write during reconciliation, multi-connection FK enforcement, and record preservation.
  - Executed 4 demonstration cases: real database read-only audit (0 FK violations, 44 exports, 33 verified MP4s, backup ok), endpoint access control, isolated reconciliation snapshot comparison, and full production API regression.
- **P0.6 Job Queue, Cancellation and Worker Reliability (Accepted):**
  - Enforced strict state transitions across `VALID_TRANSITIONS` preventing illegal jumps (e.g. failed/cancelled to completed).
  - Hardened cancellation: terminated child process subtrees (`_terminate_pid_tree`), unlinked scratch render files, and prevented FFmpeg loops from swallowing cancellation.
  - Enforced non-decreasing monotonic progress capped at 99.0% during execution, reserving 100.0% exclusively for completion with verified artifacts.
  - Hardened watchdog stall detection without fake progress tickers; preserved progress percent on failure.
  - Verified idempotent retry: reset to `queued`, incremented retry attempt, cleared error messages, reset progress, and prevented duplicate exports/candidates.
  - Hardened restart recovery (`recover_interrupted_jobs`) with cross-table synchronization to `interrupted`.
  - Authored automated regression suite `test_p0_6_job_queue_and_cancellation.py` (20/20 passed) and executed 8 live demonstration cases (`run_p0_6_demos.py`).
- **P0.7 Windows Launcher Reliability & Process Lifecycle Safety (Accepted):**
  - Robust script path resolution: dynamically resolves workspace root from `$PSScriptRoot` or `$MyInvocation.MyCommand.Path` across `Start-ZEZEdit.ps1`, `Stop-ZEZEdit.ps1`, `Start-ZEZEdit.bat`, and `Stop-ZEZEdit.bat`, allowing reliable execution from external working directories or shortcuts.
  - Structured process ownership tracking: FastAPI lifespan records structured JSON metadata in `storage/temp/zezedit_process.json` (`pid`, `port`, `host`, `project_root`, `role`, `command_line`, `start_time`, `version`) and PID in `storage/temp/zezedit.pid`; unlinks both cleanly on shutdown.
  - Port conflict defense & unrelated process protection: inspects existing listeners using `Get-NetTCPConnection` filtering out dead sockets (PID 0); distinguishes healthy ZEZEdit instances from unrelated applications; foreign listeners are safely preserved without termination, yielding actionable diagnostic errors.
  - Stale PID cleanup & PID reuse protection: verifies process command line via CIM before terminating; safely preserves unrelated processes reusing recorded PIDs; cleans stale PID and metadata files from crashed sessions.
  - Detached background daemon spawning: spawns background uvicorn server via WMI `Win32_Process.Create` detached from parent console job object limits, eliminating stdout/stderr handle locking and stream blocking on PowerShell process exit.
  - Proxy-immune readiness health polling: `Get-ZezEditHealth` uses basic parsing, localhost proxy bypass, and 5s timeout to eliminate WPAD latency and Ollama probe false timeouts.
  - Automated regression test suite: authored `backend/tests/test_p0_7_windows_launcher_reliability.py` (**18/18 tests passed in 15.29s**); Session 24 launcher tests verified (**6/6 passed in 2.72s**).
  - Live Windows demonstrations: authored `backend/scripts/run_p0_7_demos.py` covering all 8 live demonstration cases (**8/8 passed**).
- **P0.8 Production Frontend Serving and SPA Routing (Accepted):**
  - Single-port FastAPI production serving on `http://127.0.0.1:8000` directly serving compiled Vite single-page application (`frontend/dist`) alongside REST API.
  - Route evaluation hierarchy: exact REST API routes (`/api/v1/*`), health endpoints (`/health`), and Swagger documentation (`/docs`, `/openapi.json`, `/redoc`) strictly take precedence over SPA catch-all; unmatched API routes return `HTTP 404 JSON` and never fall back to `index.html`.
  - Missing static asset 404 protection: requests with known static extensions (`STATIC_EXTENSIONS` set) or targeting `/assets/` return `HTTP 404 JSON` (`detail="Static asset not found"`), preventing browser HTML syntax errors (`Uncaught SyntaxError: Unexpected token '<'`).
  - SPA client-side deep links: direct URLs (`/videos`, `/videos/:id`, `/studio/:id`, `/projects`, `/settings`, `/processes`, `/queue`, etc.) cleanly return `index.html` with `HTTP 200` (`text/html; charset=utf-8`), supporting bookmarking, hard refreshes, and history navigation.
  - Security filtering: path traversal probes containing `..`, `%2e%2e`, `\`, `%5c` blocked with `HTTP 400 Bad Request`; sensitive file probes (`.env`, `.db`, `.sqlite`, `.py`, `.log`, `.bak`, `storage/`, `backend/`, hidden dotfiles) blocked with `HTTP 403 Forbidden`.
  - Zero Vite runtime dependency: Vite development server (port 5173) is closed and unused in production mode.
  - Automated regression test suite: authored `backend/tests/test_p0_8_production_frontend_serving.py` (**15/15 tests passed in 6.19s**).
  - Live Windows demonstrations: authored `backend/scripts/run_p0_8_demos.py` covering all 6 demonstration groups (**6/6 passed**).
  - Full regression baseline verified: 339/339 backend pytest passed (exit code 0); 120/120 frontend vitests passed across 26 files (exit code 0); 0 TypeScript compiler errors; clean Vite production build (18.54s).
  - Database non-destructive integrity: 0 FK violations, 93 jobs, 44 exports, 1 project, 5 media assets preserved.
- **P0.8-R1 Production Serving Evidence Reconciliation (Accepted):**
  - Resolved previous database audit exit code 1: diagnosed as a PowerShell CLI syntax parsing error on unescaped `SELECT count(*)`; verified zero database defects via `audit_database_p0_8_r1.py` (0 FK violations, `['ok']` integrity, 93 jobs, 44 exports, 1 project, 5 media assets, 34 physical MP4 exports, 0 missing completed exports).
  - Independent Chromium browser subagent verification of live Windows production server (`http://127.0.0.1:8000`): verified root library, direct deep links (`/videos/med_5e0235303b02`, `/processes`, `/settings`), reload survival, 0 console exceptions, and captured 4 genuine screenshots in `docs/reports/priority_0/p0_8_evidence/`.
  - Re-verified focused regression suites: P0.8 tests (15/15 passed), P0.7 tests (18/18 passed), Session 24 launcher tests (6/6 passed), full backend suite (339/339 passed), frontend vitests (120/120 passed), TypeScript (0 errors), Vite production build (dist clean).
- **P0.9 Restart, Recovery and Data Persistence Verification (Accepted):**
  - Final task of Master Priority P0 (Application Stabilization: 9/9 accepted).
  - Established pre-test and post-test baseline SHA-256 manifests (`baseline_manifest.json`): 5/5 source media assets (100% hash invariant), 34/34 physical export files (100% hash invariant).
  - Created safety backup `backup_p0_9_pre_test_20261116T034733Z.db` (11,956,224 bytes, 100% verified integrity, 0 FK violations).
  - Authored automated regression suite `test_p0_9_restart_and_persistence.py` (**20/20 passed in 1.98s**, exit code 0) covering clean restart, uncommitted WAL recovery, simulated SIGKILL/hard crash, interrupted job reconciliation (`running`/`cancelling` -> `interrupted`), worker recovery, media/script/analysis/export persistence, and atomic partial upload/export cleanup.
  - Executed all 21 live demonstration cases in `run_p0_9_demos.py` (**21/21 passed**, exit code 0) saved to `docs/reports/priority_0/p0_9_evidence/p0_9_demo_results.json`.
  - Full Quality Gates re-verified: Backend Pytest **359/359 passed in 560.31s** (44 test files, 0 failures, 0 skips), Frontend Vitest **120/120 passed in 17.32s** (26 test files), TypeScript compilation **0 errors**, Production build **dist/ built in 4.10s** (481.98 kB).
  - Database non-destructive integrity audit: 0 FK violations, 93 jobs, 44 exports, 1 project, 5 media assets preserved intact.
  - Graphify updated: 3,713 nodes, 10,535 edges, 168 communities.
- **P0.9-R1 Restart and Persistence Evidence Reconciliation (Accepted):**
  - Independently verified and reproduced all persistence claims via `run_p0_9_r1_reconciliation.py` (**exit code 0 in 121.99s**).
  - Genuine isolated OS process-crash test: child Python process (PID 54244) killed mid-transaction via OS `kill()`, verifying clean SQLite automatic rollback and 0 FK violations.
  - Committed WAL transaction persistence: child Python process (PID 19096) committed data and killed via OS `kill()` before checkpointing, verifying data recovery and `PRAGMA integrity_check` = `ok`.
  - Database backup and restore verification: created backup (`backup_r1_audit_20261116T061626Z.db`, 11,956,224 bytes, SHA-256 `8f5a48c63d8d...`), restored into isolated database file, verified 100% record count match across all 5 key tables, 0 FK violations, and confirmed production database remained unchanged.
  - Five consecutive real launcher cycles: verified PIDs (25140, 48380, 45900, 46376, 46900), HTTP 200 on `/health`, `/`, `/api/v1/media`, `/api/v1/jobs`, `/api/v1/projects/default/exports`, and clean port release. External CWD launch from temp directory verified.
  - Worker process recovery: child worker process (PID 31968) terminated via OS `kill()`, identified as interrupted, progress 45.0% preserved, retried to queued, executed retry to completion with validated artifact (43 bytes).
  - Media & export persistence: 5 source media files (100% SHA-256 match) and 34 physical export MP4s (100% SHA-256 match) verified against `baseline_manifest.json`; FFprobe stream check and HTTP 206 byte-range seeking verified.
  - Interrupted upload & render safety: partial upload file purged, FFmpeg killed mid-render, scratch file purged, pre-existing export protected against overwrite, retry render verified.
  - Full Quality Gates re-verified: Backend Pytest **359/359 passed in 345.44s**, Frontend Vitest **120/120 passed in 9.68s**, TypeScript **0 errors**, Vite build **dist/ built in 2.52s**.
  - All 9 P0 tasks are now **ACCEPTED**. Work stopped before Priority 1 (P1).

- **P1.1 — Single and Multiple Video Upload (ACCEPTED & VERIFIED):**
  - Implemented and verified single video upload and multiple video batch upload operations via `POST /api/v1/projects/{project_id}/media/batch-upload` and `POST /api/v1/media/batch-upload`.
  - Added robust server-side validation: rejected empty 0-byte uploads (`400 EMPTY_MEDIA_FILE`), unsupported formats (`400 UNSUPPORTED_MEDIA_TYPE` / `400 CORRUPT_MEDIA`), and path traversal attempts (`400 PATH_TRAVERSAL_DETECTED`).
  - Preserved filename fidelity: filenames with Unicode, spaces, dashes, and brackets (`Hindi-English [BollyFlix] 01.mp4`) safely recorded in database metadata.
  - Implemented non-destructive file collision handling with 8-character unique hex prefixes, ensuring repeated uploads of identical filenames never overwrite previous assets.
  - Partial batch failure resilience: in mixed valid/invalid batches, valid files are successfully imported and registered while invalid files report structured per-item error reasons without dropping valid files.
  - **P1.1-R1 Real Browser Acceptance & Scope Closure:** Executed 5 real-browser demonstrations using Chrome DevTools Protocol against the production server (`http://127.0.0.1:8000`). Verified single upload auto-navigation, 3-file batch upload, mixed-validity error reporting banner, repeated uploads without collision, and mobile-width (375x812) responsive dropzone. Clarified upload buffering boundary: P1.1 provides standard multipart upload with Starlette spooling and 1 MB chunk copying; P1.3 reserves true socket streaming (>1GB) without tempfile spooling and resumability.
  - Frontend UI integration in both `ShortVideoGeneratorLibrary.tsx` and `MediaLibraryView.tsx` with Unslop quiet design compliance, multi-file selection support, and clean navigation to `/videos/:id`.
  - Five mandatory independent live demonstrations passed: Demo A (single upload), Demo B (3-video batch), Demo C (mixed validity), Demo D (Unicode & path traversal), Demo E (repeated upload collision).
  - Full Quality Gates verified: Backend Pytest **366/366 passed in 402.33s**, Frontend Vitest **122/122 passed in 9.05s**, TypeScript **0 errors**, Vite build in **2.41s**, Graphify updated (3,756 nodes, 10,749 edges), database 0 FK violations, and production media/exports 100% hash invariant.

- **P1.2 — Accurate Byte-Based Upload Progress (ACCEPTED & VERIFIED):**
  - Implemented true, byte-based upload progress for single and multiple video uploads via `XMLHttpRequest.upload.onprogress` in `frontend/src/services/apiClient.ts` without simulated timers or fabricated increments.
  - Guaranteed mathematical accuracy: percentage strictly computed as `(loaded / total) * 100` and capped at 100%; loaded bytes enforced strictly monotonic (`loaded[i] >= loaded[i-1]`) even during network packet reordering or multipart boundary reconciliation.
  - Handled indeterminate sizes honestly: when `lengthComputable === false` or size is unknown, displays byte counter without fabricating artificial percentages.
  - Explicit transfer state machine: `uploading` -> `processing` -> `completed` / `aborted` / `error`. Distinct `"Processing on server..."` state visually separates network wire transmission from server-side FFprobe analysis and database persistence.
  - User cancellation & abort support: one-click cancel button triggers `AbortController.abort()` and `xhr.abort()`, cleanly aborting in-flight transfers and leaving zero orphan records in SQLite and zero orphan files on disk.
  - UI Design compliance with Unslop: created `UploadProgressPanel.tsx` using quiet graphite neutrals, subtle emerald/amber/red status pills, 4px grid rhythm, human-readable `formatBytes`, and integrated into both `ShortVideoGeneratorLibrary.tsx` and `MediaLibraryView.tsx`.
  - Backend controlled testing: added `test_delay_seconds` query parameter (defaulting to 0.0) in `backend/app/api/v1/media.py` enabling automated browser tests to capture the server processing state at 100% transmission deterministically.
  - Six mandatory independent live browser demonstrations executed via Chrome DevTools Protocol (CDP) against Windows production server: Demo A (single upload progress & dashboard auto-navigation), Demo B (3-file batch aggregate progress), Demo C (120 KB/s throttled transfer monotonicity verification), Demo D (transfer abort & zero DB orphans), Demo E (server processing delay verification at 100%), Demo F (mobile 375x812 responsive viewport).
  - Quality Gates 100% Passing: Backend Pytest **369/369 passed in 342.05s**, Frontend Vitest **135/135 passed (27 test files) in 9.68s**, TypeScript **0 errors**, Vite build clean in **2.39s**, Graphify updated (**3,809 nodes, 10,915 edges, 194 communities**), database 0 FK violations and integrity `ok`, 5 original media and 34 exports 100% SHA-256 invariant.

- **P1.3 — Large-File Video Ingestion, Streaming and Bounded Memory (ACCEPTED & VERIFIED):**
  - Implemented large-video upload architecture capable of handling multi-gigabyte files on Windows without loading full files into application memory.
  - Strictly bounded memory footprint: verified on real 1.21 GB video (`Visionquest S01E08.mkv`, 1,298,314,363 bytes) with an RSS delta of only +1.25 MB (0.1% ratio).
  - Incremental 1 MB disk writing buffer (`upload_chunk_size_bytes = 1024 * 1024`) with simultaneous on-the-fly SHA-256 calculation (`hasher.update(chunk)`), eliminating redundant secondary file passes.
  - Tier 1 Pre-Flight validation (`LargeUploadPreflightMiddleware`): intercepts Content-Length before reading body, immediately returning 413 `REQUEST_ENTITY_TOO_LARGE` for payloads exceeding 2.5 GB or 507 `INSUFFICIENT_STORAGE` when disk free space is below required headroom (500 MB).
  - Tier 2 In-Flight stream enforcement: cumulative byte counter and periodic disk space verification every 50 MB; immediate file closure and unlinking on error or client disconnect (`asyncio.CancelledError`).
  - Temporary directory confinement in `storage/temp/uploads/` with automated startup purge of stale orphaned files.
  - Heavy upload concurrency throttling via `_UPLOAD_SEMAPHORE` (max 2 parallel heavy transfers returning 429 `TOO_MANY_CONCURRENT_UPLOADS` when saturated).
  - Demonstrations verified: 8 passed, 1 honest qualification (Demo D ~2 GB asset limitation honestly documented as BLOCKED).
  - P1.3-R1 Evidence Reconciliation & Failure at Scale:
    - Gap A: Real 1.21 GB video uploaded through Chrome CDP browser UI (`input[type=file]` -> React -> XHR); navigated to dashboard in 9.61s (128.84 MB/s); 100% SHA-256 match; HTTP 206 range request verified; RSS delta +1.10 MB (0.08% ratio).
    - Gap B: Cancellation at genuine scale on real 247 MB file (`BLACK TORCH S01E02.mkv`) throttled at 8 MB/s; cancelled actively after 15,761,408 bytes transmitted; verified UI reports cancellation, 0 DB records, partial file unlinked, and subsequent upload succeeded (`med_430f8016b361`).
    - Gap C: Client disconnect at genuine scale on real 247 MB file; severed TCP connection after 52,428,800 bytes (~50 MB) transmitted; verified server-side disconnect detection, partial file unlinked, 0 DB records, clean media library, and subsequent upload succeeded (`med_4d3997fe227e`).
    - Gap D1 & D2: Pre-flight and in-flight insufficient storage (HTTP 507) handling verified; request body not consumed on pre-flight, in-flight guard halts stream and unlinks destination, server remains healthy.
    - Implementation correctness: malformed Content-Length handling (HTTP 400), chunked limit enforcement, and volume disk checks verified.
  - Quality Gates 100% Passing: Backend Pytest **378/378 passed in 353.97s**, Frontend Vitest **135/135 passed (27 test files) in 9.65s**, TypeScript **0 errors**, Vite build clean in **2.45s**, Graphify updated (**3,905 nodes, 11,178 edges, 188 communities**), database 0 FK violations and integrity `ok`, 5 original media and 34 exports 100% SHA-256 invariant.

- **P1.4 — Upload Failure Handling, Retry and Recovery (ACCEPTED & VERIFIED):**
  - Formalized upload state machine: `queued`, `uploading`, `processing`, `completed`, `failed`, `cancelled`, and `retrying` with unique `attemptId` and `attemptCount` tracking per upload attempt.
  - Stale callback protection: all XHR event listeners check captured `attemptId`, silently discarding delayed or out-of-order events from prior attempts or terminal states to prevent race conditions.
  - Deterministic error classification: differentiates retryable failures (network disconnects, timeouts, 408, 429, 500, 502, 503, 504, user cancellation, DB registration drop) from terminal non-retryable failures (400, 413, 415, corrupt files, 0-byte empty files) with UI `(Non-retryable)` badges.
  - In-memory full-restart retry: retries restart honestly from byte zero using the retained in-memory browser `File` object; if DOM `File` reference is lost on page reload, displays clear guidance instructing user to re-select the file.
  - Item-level selective batch retry: failed or cancelled items within multi-file batch uploads can be independently retried without restarting or re-uploading succeeded files.
  - Safe backend atomic operations: video streams write to `.uploading` part files before atomic `os.replace` rename to destination; Windows file handles safely closed before unlinking; automated startup sweep purges stale partial files from prior runs.
  - Rapid duplicate submission guard: UI disables retry buttons and guards in-flight operations against concurrent duplicate submissions.
  - 10/10 Independent Live Demonstrations verified (Demos A–J): Demo A (network interruption retry), Demo B (server 500 retry), Demo C (concurrency 429 retry), Demo D (client cancellation retry), Demo E (batch partial failure & item-level retry), Demo F (rapid duplicate guard), Demo G (DB finalization recovery), Demo H (startup stale sweeper), Demo I (page reload lost reference explanation), Demo J (stale callback idempotency).
  - Quality Gates 100% Passing: Backend Pytest **384/384 passed in 340.09s**, Frontend Vitest **143/143 passed (28 test files) in 19.81s**, TypeScript **0 errors**, Vite build clean in **8.15s**, Graphify updated (**3,944 nodes, 11,332 edges, 167 communities**), database 0 FK violations and integrity `ok`, 5 original media and 34 exports 100% SHA-256 invariant.

- **P1.5 — Upload Integrity, File Validation and Atomic Persistence (ACCEPTED & VERIFIED):**
  - Strict upload integrity contract: established complete contract fields across backend model (`MediaAssetRecord`), Pydantic response (`MediaAssetResponse`), and frontend TypeScript (`MediaAssetItem`), recording `sha256`, `integrity_status`, `upload_attempt_id`, `integrity_details_json`, and `last_integrity_check`.
  - Migration 0017 applied: schema migration `0017_upload_integrity_contract.sql` added integrity columns and dedicated indexes (`idx_media_assets_sha256`, `idx_media_assets_integrity_status`) with backward-compatible SQLite table alteration.
  - Streaming single-pass cryptographic hashing: computed SHA-256 incrementally in 64 KB chunks as bytes stream directly to disk, avoiding full-file in-memory buffering or secondary disk read passes.
  - Byte-count and file-size verification: validates received byte counts against `X-Expected-File-Size` / `Content-Length`. Truncated or oversized uploads are rejected with HTTP 400 `BYTE_COUNT_MISMATCH` before publication.
  - Checksum mismatch rejection: declared client hashes (`X-Expected-Sha256`) are compared against server-computed SHA-256; mismatches reject with HTTP 400 `CHECKSUM_MISMATCH`.
  - Pre-publication media validation: FFprobe probes staged `.uploading` part files before atomic rename. Rejects corrupt files, truncated containers, zero-byte uploads (`EMPTY_MEDIA_FILE`), plain text (`CORRUPT_MEDIA`), and audio-only media masquerading as video (`400 NO_VIDEO_STREAM`). Valid multi-stream MKVs with multiple audio/subtitle tracks are accepted and stream topologies accurately registered.
  - Two-phase atomic publication lifecycle: staged `.uploading` part file is probed and verified, then atomically published to final destination via `os.replace()`, followed by transactional database registration. Failures at either stage automatically roll back and unlink files, preventing ghost records or orphaned storage leaks.
  - 12/12 Independent Live Demonstrations verified (Demos A–L): Demo A (valid MP4 contract & range streaming), Demo B (multi-stream MKV), Demo C (corrupt video rejection), Demo D (truncated video rejection), Demo E (zero-byte, text, audio rejection), Demo F (byte-count mismatch), Demo G (checksum mismatch), Demo H (storage/database failure rollback), Demo I (duplicate filenames & concurrency), Demo J (retry integrity & idempotency), Demo K (1.21 GB Visionquest integrity match), Demo L (restart and persistence verification).
  - Quality Gates 100% Passing: Backend Pytest **393/393 passed in 359.79s**, Frontend Vitest **143/143 passed (28 test files) in 10.66s**, TypeScript **0 errors**, Vite build clean in **14.73s**, Graphify updated (**3,990 nodes, 11,490 edges, 168 communities**), SQLite `integrity_check` = `ok`, 0 FK violations, and 100% SHA-256 invariance on all 5 source media files and 34 physical exports.

- **P1.6 — Media Library, Metadata and Asset Management (ACCEPTED & VERIFIED):**
  - Complete Source Discovery Without Pollution: strictly separates original uploaded videos (`media_type == "video"`) from generated exports, candidate clips, and temporary files. Verified zero leakage across 100 library items and 44 database exports.
  - Performance Indexing (Migration 0018): added b-tree indexes on `created_at`, `original_filename`, `file_size_bytes`, `duration_seconds`, `media_type`, and `width/height` to guarantee fast querying.
  - Enriched Technical Badges: cards surface resolution badges (4K, 1440p, 1080p, 720p, 480p), container format, video codec, audio codec, duration, file size, integrity status, and analysis status.
  - Debounced Search & Filtering: 300ms debounced case-insensitive search across filenames and asset ID prefixes (`med_...`) with space and unicode support; multi-criteria filtering by format, codec, resolution, and analysis status.
  - Allowlisted Server-Side Sorting: strict SQL sorting on `created_at`, `original_filename COLLATE NOCASE`, `file_size_bytes`, `duration_seconds`, and `(width * height)` with SQL injection immunity.
  - Server-Side Pagination: scalable responses with `total_count`, `total_pages`, and verified zero overlap between pages.
  - Stream Topology & Provenance Inspection: detail modal showing full audio/video stream breakdown, bitrates, sample rates, channel layout, language tags, pixel formats, SHA-256 hashes, and attempt IDs.
  - Chunked HTTP 206 Partial Content Streaming: native HTML5 video player with byte-range seeking, `Accept-Ranges`, 416 range bounds validation, and path traversal defense.
  - Atomic Metadata Refresh & Thumbnail Regeneration: explicit POST endpoints for FFprobe metadata re-probing (preserving SHA-256) and on-demand timestamp thumbnail regeneration with fallback handling.
  - Dependency-Safe Asset Deletion: returns HTTP 409 Conflict when active background jobs or dependent exports exist; enables safe storage reclamation via `force_with_exports=true`.
  - Responsive Mobile Reflow: verified 375x812 mobile layout with 0px horizontal overflow.
  - 14/14 Independent Live Demonstrations verified (Demos A–N): Demo A (library discovery), Demo B (technical badges), Demo C (search), Demo D (filtering), Demo E (sorting & SQLi defense), Demo F (pagination), Demo G (inspection modal & topology), Demo H (HTTP 206 range seeking), Demo I (metadata refresh), Demo J (thumbnail regeneration), Demo K (409 dependency rejection), Demo L (force deletion & storage reclamation), Demo M (mobile 375x812 layout), Demo N (baseline SHA-256 invariance).
  - Quality Gates 100% Passing: Backend Pytest **398/398 passed**, Frontend Vitest **148/148 passed (29 test files)**, TypeScript **0 errors**, Vite build clean in **2.90s**, Graphify updated (**4,044 nodes, 11,714 edges, 159 communities**), SQLite `integrity_check` = `ok`, 0 FK violations, and 100% SHA-256 invariance on all 93 registered baseline media files and exports.












