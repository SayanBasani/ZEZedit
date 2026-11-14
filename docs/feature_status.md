# ZezEdit 2.0 — Feature Status Tracker

**Last Updated:** 2026-11-14  
**Active Milestone:** Session 9 Completed — Critical Performance Diagnostics, Stuck Analysis Repair & Complete Short-Video Generation Validation (181 Backend Tests Passed, 120 Frontend Tests Passed, 100% Pass Rate)

Status legend:
- **Implemented:** Code exists, integrated end-to-end, and verified with tests / runtime execution.
- **Partial:** Core scaffolding or partial layer exists; remaining workflow scheduled for later milestones.
- **Planned:** Designed in architecture specs; implementation scheduled in an upcoming milestone.
- **Not Started:** Future backlog item.
- **Blocked:** External dependency or unresolved blocker prevents verification.

---

## Performance Diagnostics, Stuck Analysis Repair & Video Generation (Session 9)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S9-01 | AnyIO Worker Thread Offloading | Analysis API | Implemented | `backend/app/api/v1/analysis.py` | Offloads heavy CPU analysis tasks to AnyIO threadpool workers; reduced HTTP polling latency from timeout to 10.92ms average |
| S9-02 | Faster-Whisper Singleton Model Caching | Transcription | Implemented | `backend/app/services/transcription.py` | Thread-safe singleton model cache eliminates HuggingFace download/load overhead on recurring runs (0.00s warmup) |
| S9-03 | Whisper Streaming Progress & Non-VAD Primary Path | Pipeline & Transcription | Implemented | `backend/app/services/transcription.py` | Streaming segment callbacks with real work units (seconds transcribed), ETA calculation, and speech text ticker |
| S9-04 | Batched Keyframe Extraction Pass | Subject Tracker | Implemented | `backend/app/services/subject_tracker.py` | Replaced 91 sequential `ffmpeg.exe` subprocess calls with single batched pass; extraction speed improved 40.9x (2.23s) |
| S9-05 | Bounded Downscaled Subject Tracking | Subject Tracker | Implemented | `backend/app/services/subject_tracker.py` | 640px frame scaling, top-4 detection filter, and max-2 active TrackerMIL instances; reduced CPU tracking time from >100s to 11.5s |
| S9-06 | Stalled Job Process Exit Race Condition Fix | Job Orchestration | Implemented | `backend/app/services/jobs.py` | Added 15s grace period for terminated worker PIDs to prevent false-positive failures on clean FFmpeg exit |
| S9-07 | Real 5-Minute Video Analysis Live Execution | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Full live execution on `Ek Mota Hathi Ghumne Chala.mp4` (302.4s, 70MB) completed in 101.43s on CPU |
| S9-08 | Multi-Aspect Real MP4 Rendering & Output Verification | Export Pipeline | Implemented | `backend/app/services/export_service.py` | Verified 9:16 portrait (1080x1920), 1:1 square (1080x1080), 16:9 landscape (1920x1080); 100% clean decode with `-f null -` |
| S9-09 | Complete Parameter Matrix Validation | Highlights & Discovery | Implemented | `backend/app/services/highlight_discovery.py` | Validated all 7 creative directions, 4 quantity preferences, 5 duration modes, and zero-collision temporal novelty |
| S9-10 | Performance & Architecture Documentation | Documentation | Implemented | `docs/architecture/ANALYSIS_PERFORMANCE_AND_PROGRESS.md` | Formal root-cause audit, before/after benchmarks, and heartbeat protocol specifications |

---

## Real Object Tracking, Multi-Subject Intelligence & Temporal Novelty Correction (Session 8)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S8-01 | Temporal Novelty Correction & Containment Rejection | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Multi-layer overlap scoring with $R_{\min} = \frac{\text{Intersection}}{\min(\text{dur}_A, \text{dur}_B)}$; prevents containment duplicates (e.g. $[63.07, 87.31]$ vs $[63.07, 114.01]$) |
| S8-02 | Intra-Batch Overlap Deduplication & Alternative Cuts | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Validates every candidate against all candidates selected in current batch and clusters alternative cuts |
| S8-03 | CPU-Friendly Multi-Class Subject Detection | Vision Tracker | Implemented | `backend/app/services/subject_tracker.py` | YCrCb skin segmentation for `person`/`face` and Sobel gradient saliency for `vehicle`/`object`/`animal` |
| S8-04 | Genuine Temporal Tracking via TrackerMIL | Vision Tracker | Implemented | `backend/app/services/subject_tracker.py` | Persistent `TrackerMIL` instances maintain independent identities (`subject_1`, `subject_2`) across frames |
| S8-05 | Scene Cut Aware Track Termination | Vision Tracker | Implemented | `backend/app/services/subject_tracker.py` | Tracks strictly terminate across scene transitions; never smooths or tracks across scene cuts |
| S8-06 | Multi-Subject Framing Strategies | Framing Engine | Implemented | `backend/app/services/framing_engine.py` | Supports `primary_subject`, `two_person`, `group`/`all_subjects`, `action_object`, and `pinned_subject_id` |
| S8-07 | Dynamic Tracking Render Pipeline Integration | Export Service | Implemented | `backend/app/services/export_service.py` | `_resolve_keyframes` runs `ReframingService` dynamically on demand and compiles piecewise-linear FFmpeg crop expressions |
| S8-08 | Speaker-Focused Framing Capability Audit | UI & Docs | Implemented | `frontend/src/features/studio/CandidateClipEditorModal.tsx` | Distinguishes Available (Face/Person, Object, Group) from Unsupported (Deep AV speaker diarization on CPU) |
| S8-09 | Comprehensive Automated Verification Tests | Testing | Implemented | `backend/tests/test_session8_tracking_and_novelty.py` | 12 new automated tests for overlap, containment, multi-subject tracking, and dynamic filtergraph generation |
| S8-10 | Architecture & Design Specifications | Documentation | Implemented | `docs/architecture/OBJECT_AND_MULTI_SUBJECT_TRACKING.md`, `docs/architecture/TEMPORAL_NOVELTY_DESIGN.md` | Formal specs for object tracking, multi-subject framing, and novelty design |

---

---

## Complete Product Integration & Real-World Validation (Session 7)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S7-01 | End-to-End Product Workflow Mapping | Architecture Docs | Implemented | `docs/architecture/END_TO_END_PRODUCT_FLOW.md` | Full system diagram and 14-stage component/API/service/record mapping |
| S7-02 | Long-Form Source Video Analysis & Persistence | Pipeline / DB | Implemented | `backend/app/services/analysis_pipeline.py` | Verified on 5.04-min 1080p video (`Ek Mota Hathi`): 37 scenes, 74 transcript segments, 41 frames, 12 observations |
| S7-03 | Simplified Generator Configuration Defaults | Frontend Studio | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | AI Recommended quantity, Best Overall direction, 9:16 aspect ratio, AI Best Duration; advanced settings collapsed |
| S7-04 | Candidate Quality & Persistent Novelty Ledger | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Batch 1 (3 clips) and Batch 2 Generate More (3 clips) produced 6 distinct non-overlapping candidates (0 common IDs) |
| S7-05 | Candidate Clip Editing & Reframing Resolution | Clip Editor / Export | Implemented | `backend/app/services/clip_editing_service.py` | Non-destructive trim (65.0s-85.0s), manual crop coordinates (50%, 50%), and zoom (1.1x) verified in rendered output |
| S7-06 | Multi-Aspect Real Video Rendering & Output Verification | FFmpeg Pipeline | Implemented | `backend/app/services/export_service.py` | Rendered 4 real shorts: Two 9:16 vertical (20.52s, 30.08s), One 1:1 square edited (20.00s), One 16:9 landscape (45.36s) |
| S7-07 | In-Browser HTML5 Video Playback & Byte-Range Streaming | Frontend / API | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Live playback verified via Browser Subagent on 1:1 square short with burned subtitles and audio |
| S7-08 | Central Process Manager Integration & Lineage | Process Center | Implemented | `frontend/src/features/queue/WorkingQueueView.tsx` | Tracked 10 tasks (export_render & media_analysis) with source video association and execution logs |
| S7-09 | Honest Tracking & Saliency Capability Audit | Tracking Services | Implemented | `backend/app/services/subject_tracker.py` | Comprehensive capability audit: Haar cascades for face/upper body, color saliency fallback; multi-subject/speaker tracking marked unsupported |
| S7-10 | Storage Reclamation & Disk Usage Verification | Storage Services | Implemented | `backend/app/services/storage.py` | Verified category sizes: media (70.4 MB), exports (40.6 MB), analysis (1.7 MB), backups (26.6 MB), db (4.2 MB) |

---

## Real Video Rendering, Clip Editing & Batch Export (Session 6C)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S6C-01 | Architecture Audit & 15-Stage Pipeline Design | Architecture Docs | Implemented | `docs/architecture/RENDERING_PIPELINE_AUDIT.md`, `VIDEO_RENDERING_DESIGN.md` | Answered 15 architectural questions, 15-stage filter chain specification |
| S6C-02 | Preset Catalog Extension for All Aspect Ratios | Export Models | Implemented | `backend/app/models/export.py` | Added `9:16`, `16:9`, `1:1`, `4:5`, `4:3`, `3:4` presets with strict dimensions |
| S6C-03 | Candidate Clip Editing Resolution & Custom Framing | Export Service | Implemented | `backend/app/services/export_service.py` | Seamlessly reads `candidate_clip_edits`, applies edited timestamps and manual/center crop expressions |
| S6C-04 | Process Manager Scoping for Render Jobs | Backend Services | Implemented | `backend/app/services/export_service.py` | Associates `media_asset_id` on job creation so jobs link to source video filename in Central Process Manager |
| S6C-05 | Direct MP4 Download & HTTP 206 Partial Content Streaming | Backend API | Implemented | `backend/app/api/v1/exports.py` | Added `/projects/{pid}/exports/{export_id}/download` and `/video` byte-range streaming |
| S6C-06 | Generated Short Videos Archive & In-Browser Player | Frontend Studio | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Dedicated Generated Videos tab with playable cards, HTML5 modal player, seek/controls, download, delete |
| S6C-07 | Multi-Candidate Batch Selection & Sticky Batch Bar | Frontend Studio | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Checkboxes, Select All, Clear Selection, and "Render Selected (N)" batch execution |
| S6C-08 | Post-Render Output Verification via OutputValidator | Export Pipeline | Implemented | `backend/app/services/export_service.py` | Mandates FFprobe stream inspection and FFmpeg null-sink decode verification before marking completed |
| S6C-09 | Comprehensive Automated Test Suites | Testing | Implemented | `backend/tests/test_session6c_rendering_and_batch_export.py`, `frontend/src/test/session6c_rendering.test.tsx` | 5 new backend tests, 3 new frontend tests; 169 backend & 120 frontend tests pass 100% |
| S6C-10 | Real Media Rendering & Browser Playback Verification | Verification | Implemented | `storage/exports/default/` | Rendered 9:16, 1:1, 16:9 MP4s and confirmed in-browser playback with Browser Subagent |

---

## Core Foundation & Architecture (Milestone 1)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| FND-01 | Versioned Architecture & Design Blueprint (11 docs + README) | Docs | Implemented | `docs/architecture/` | Covers all 18 required architectural decisions |
| FND-02 | Configurable Storage Root & Directory Layout | Core / Storage | Implemented | `backend/app/core/storage.py` | Separates media, proxies, thumbnails, analysis, exports, temp, backups, db |
| FND-03 | Path Confinement & Anti-Root Recursive Deletion Guard | Core / Security | Implemented | `backend/app/core/security.py` | Blocks traversal, root deletion, and storage escapes |
| FND-04 | Structured Logging & Centralized Error Handling | Core / API | Implemented | `backend/app/core/logging.py`, `backend/app/core/errors.py` | Standard JSON-friendly logs and uniform error envelopes |
| FND-05 | SQLite WAL Connection & Forward-Only SQL Migration Runner | DB / Migrations | Implemented | `backend/app/db/migrator.py`, `backend/migrations/0001_initial_schema.sql` | Baseline metadata schema |
| FND-06 | FastAPI App Entry Point & `/api/v1/health` Endpoint | Backend API | Implemented | `backend/app/main.py`, `backend/app/api/v1/health.py` | Probes SQLite, storage root, FFmpeg, FFprobe, and Ollama |
| FND-07 | Minimal Bounded React/Vite/Tailwind Shell & Backend Connectivity Check | Frontend | Implemented | `frontend/src/app/App.tsx`, `frontend/src/services/apiClient.ts` | Stationary sidebar + scrollable main container (`BUG-08A-1/2` fix baked in) |

---

## Core Backend, Database & Project Management (Milestone 2)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M2-01 | Database Migration `0002_core_management.sql` | DB / Migrations | Implemented | `backend/migrations/0002_core_management.sql` | Upgrades projects & jobs, creates `media_assets` and `project_events` |
| M2-02 | Project Management Lifecycle & Events Service | Core Services | Implemented | `backend/app/services/projects.py` | Create, get, list, update, archive, restore, protected delete, events |
| M2-03 | Media Metadata & External Relinking Service | Core Services | Implemented | `backend/app/services/media.py` | Register external/stored media, metadata updates, mark missing, relinking |
| M2-04 | Persistent Job Orchestration & State Machine | Core Services | Implemented | `backend/app/services/jobs.py` | Strict transitions, cancellation, retries, startup recovery of interrupted jobs |
| M2-05 | Application Settings & Secret Redaction | Core Services | Implemented | `backend/app/services/settings_service.py` | SQLite JSON persistence, secret redaction (`[REDACTED]`) |
| M2-06 | Storage Inspection & Space Management | Core Services | Implemented | `backend/app/services/storage.py` | Real disk usage, category sizes, boundary checks |
| M2-07 | Online SQLite Backup & Restore Verification | Core Services | Implemented | `backend/app/services/backup_service.py` | Uses `sqlite3.backup()`, integrity check verification, safety snapshots |
| M2-08 | Versioned REST Endpoints (`/api/v1/*`) | Backend API | Implemented | `backend/app/api/v1/` | `projects`, `media`, `jobs`, `settings`, `backups`, `capabilities` |
| M2-09 | Frontend Project Workspace & Centralized Client | Frontend | Implemented | `frontend/src/features/projects/ProjectsView.tsx` | Create, list, archive/restore, delete projects, typed API client |
| M2-10 | Full Pytest Suite (12 unit + integration tests) | Testing | Implemented | `backend/tests/test_milestone2_core.py` | 100% pass covering migrations, state machine, relinking, backups |

---

## Frontend Application Shell, Dashboard & Design System (Milestone 3)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M3-01 | Design System Tokens & Unified Styling | UI Design System | Implemented | `frontend/tailwind.config.js`, `frontend/src/styles/index.css` | Canvas, surface, borders, text tiers, semantic accents |
| M3-02 | Dark / Light / System Mode & Theme Provider | UI Context | Implemented | `frontend/src/context/ThemeContext.tsx` | Instant sync, zero flicker, localStorage persistence |
| M3-03 | Component Library (Buttons, Inputs, Badges, Cards, Modals, States) | UI Components | Implemented | `frontend/src/components/ui/` | Fully accessible, typed with variants and animations |
| M3-04 | Responsive Studio Application Shell | UI Shell | Implemented | `frontend/src/app/App.tsx` | Fixed-height desktop sidebar + mobile drawer, active task badges |
| M3-05 | Studio Dashboard View | Features / Dashboard | Implemented | `frontend/src/features/dashboard/DashboardView.tsx` | Live metrics, recent projects, real-time background job monitor |
| M3-06 | Projects Management Interface | Features / Projects | Implemented | `frontend/src/features/projects/ProjectsManager.tsx` | Grid/list view modes, status filters, search, archive, delete modal |
| M3-07 | Settings Interface | Features / Settings | Implemented | `frontend/src/features/settings/SettingsManager.tsx` | Hardware CPU limits, proxy scrub resolution, export presets, Ollama status |
| M3-08 | Frontend Vitest Test Suite (17 tests) | Testing | Implemented | `frontend/src/test/` | 100% pass covering components, contexts, and feature views |
| M3-09 | Production Bundle Verification | Build | Implemented | `dist/` | Production build clean in 1.86s, 60 kB gzip bundle |

---

## Media Ingestion, Import & Media Library (Milestone 4)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M4-01 | Database Migration `0003_media_pipeline.sql` | DB / Migrations | Implemented | `backend/migrations/0003_media_pipeline.sql` | Adds `proxy_status` column and indexing to `media_assets` |
| M4-02 | FFprobe Technical Metadata Extraction Service | Media Services | Implemented | `backend/app/services/media_probe.py` | Robust parsing of video, audio, image streams, fps, DAR, orientation |
| M4-03 | FFmpeg Deterministic Thumbnail Generation | Media Services | Implemented | `backend/app/services/media_thumbnail.py` | Representative video frame seeks, downscaled JPEGs, artwork extraction |
| M4-04 | FFmpeg Proxy Transcode Engine (360p, 480p, 720p) | Media Services | Implemented | `backend/app/services/media_proxy.py` | CPU-bounded H.264 transcoding, fast-start atoms, thread confinement |
| M4-05 | Streaming Media Import Pipeline | Media Services | Implemented | `backend/app/services/media_pipeline.py` | Supports reference mode, copy mode, chunked streaming, disk space check |
| M4-06 | Versioned Media REST Endpoints | Backend API | Implemented | `backend/app/api/v1/media.py` | Import, streaming upload, thumbnail serving, proxy stream, stats, relink |
| M4-07 | Frontend Media Library View | Features / Media | Implemented | `frontend/src/features/media/MediaLibraryView.tsx` | Grid/list view, metrics cards, search/filter/sort, details drawer, import modal |
| M4-08 | Backend Media Integration Test Suite (6 tests) | Testing | Implemented | `backend/tests/test_milestone4_media.py` | Real FFmpeg/FFprobe tests, synthetic video/audio, proxies, 100% pass |
| M4-09 | Frontend Media Vitest Suite (6 tests) | Testing | Implemented | `frontend/src/test/mediaLibrary.test.tsx` | Covers grid/list toggle, type/status filtering, search, import dialog |

---

## Video Analysis Engine, Transcription & Visual Understanding (Milestone 5)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M5-01 | Database Migration `0004_video_analysis.sql` | DB / Migrations | Implemented | `backend/migrations/0004_video_analysis.sql` | Schema for analysis runs, transcript segments, turns, scenes, frames, observations |
| M5-02 | 16kHz Mono Audio Extractor | Analysis Services | Implemented | `backend/app/services/audio_extractor.py` | FFmpeg extraction to ephemeral WAV scratch |
| M5-03 | Faster-Whisper CPU Speech Transcriber | Analysis Services | Implemented | `backend/app/services/transcription.py` | CPU-first Faster-Whisper (`int8`), segment timestamps, word tokens, PyAV 14+ compat |
| M5-04 | Dialogue & Speech Turn Segmentation | Analysis Services | Implemented | `backend/app/services/speech_segmentation.py` | Conversational pause thresholding, turn grouping, statement/question/exclamation |
| M5-05 | FFmpeg Visual Scene Cut Detection | Analysis Services | Implemented | `backend/app/services/scene_detector.py` | Cut extraction via FFmpeg scene filter, timestamps, midpoint representative frames |
| M5-06 | Controlled Downscaled Frame Sampling | Analysis Services | Implemented | `backend/app/services/frame_sampler.py` | Keyframe extraction downscaled to 640px max dimension, capped per profile |
| M5-07 | Visual Understanding via Local Ollama | Analysis Services | Implemented | `backend/app/services/visual_understanding.py` | Queries `qwen3-vl:4b-instruct` with conservative language; deterministic heuristic fallback |
| M5-08 | Multimodal Temporal Context Aggregator | Analysis Services | Implemented | `backend/app/services/temporal_aggregator.py` | Unifies scenes, speech turns, transcript segments, and vision at any timestamp |
| M5-09 | Analysis Pipeline Coordinator & REST API | Backend API | Implemented | `backend/app/services/analysis_pipeline.py`, `backend/app/api/v1/analysis.py` | 8-stage coordinator, async background execution, cancellation, REST endpoints |
| M5-10 | Interactive Frontend Analysis Workspace | Features / Analysis | Implemented | `frontend/src/features/analysis/AnalysisWorkspace.tsx` | Synchronized player, scrub bar, searchable transcript, scene cuts, vision tags, context inspector |
| M5-11 | Backend Analysis Test Suite (7 tests) | Testing | Implemented | `backend/tests/test_milestone5_analysis.py` | Audio extraction, scenes, speech turns, frames, fallback, aggregator, API flow (100% pass) |
| M5-12 | Frontend Analysis Vitest Suite (3 tests) | Testing | Implemented | `frontend/src/test/analysis.test.tsx` | Workspace rendering, transcript, speech turns, tab switching, context inspector (100% pass) |

---

## AI Highlight Discovery, Contextual Clip Selection & Shorts Candidate Ranking (Milestone 6)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M6-01 | Database Migration `0005_highlight_candidates.sql` | DB / Migrations | Implemented | `backend/migrations/0005_highlight_candidates.sql` | Schema for `shorts_candidates`, versioned scoring, gate results, overlap groups |
| M6-02 | Candidate Dataclass Entity | Backend Models | Implemented | `backend/app/models/entities.py` | `ShortsCandidateRecord` dataclass mapping |
| M6-03 | Context-Aware Boundary Snapping & Lead Buffers | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Snapping to scene cuts (±0.6s), sentence boundaries, 0.3s lead-in, 0.5s lead-out |
| M6-04 | 9-Component Explainable Scoring Engine (`2.0.0-m6`) | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Semantic, narrative, conversation, visual, audio, opening, ending, duration, context penalty |
| M6-05 | Three-Tier Quality Gate Enforcement | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Categorizes into `recommended`, `needs_review`, `rejected` with failure reasons |
| M6-06 | Temporal Overlap Clustering & Deduplication | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Groups clips with $\text{IoU} \ge 0.65$ into alternative cuts under `overlap_group_id` |
| M6-07 | Ollama AI Content Explanation & Deterministic Fallback | Discovery Engine | Implemented | `backend/app/services/highlight_discovery.py` | Generates hook, why_it_works, strengths, risks with local LLM or heuristic fallback |
| M6-08 | Shorts Candidates REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/highlights.py` | Discover, overview counts, candidate detail, boundary patch, approve, reject, restore, bulk review, render queue |
| M6-09 | Frontend Highlights & Shorts Studio Workspace | Features / Highlights | Implemented | `frontend/src/features/highlights/HighlightsWorkspace.tsx` | Metrics, filter tabs, candidate cards, boundary slider inspector, score breakdown, alternative cuts |
| M6-10 | Backend Automated Pytest Suite (3 tests) | Testing | Implemented | `backend/tests/test_milestone6_highlights.py` | Engine generation, quality gates, full REST lifecycle (100% pass) |
| M6-11 | Frontend Vitest Test Suite (5 tests) | Testing | Implemented | `frontend/src/test/highlights.test.tsx` | Studio rendering, status tabs, boundary fine-tuning, approve/reject, queue toggle (100% pass) |

---

## Smart Reframing, Subject Tracking & Portrait Composition (Milestone 7)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M7-01 | Database Migration `0006_smart_reframing.sql` | DB / Migrations | Implemented | `backend/migrations/0006_smart_reframing.sql` | Schema for `reframing_plans` and `reframing_revisions` with range indexing |
| M7-02 | Subject Detection & Tracking Service | Reframing Engine | Implemented | `backend/app/services/subject_tracker.py` | CPU-first OpenCV Haar Cascades (frontal/profile face, upper body), saliency fallback, IoU/centroid association, 1.2s gap bridging |
| M7-03 | Framing Engine & Geometry Resolution | Reframing Engine | Implemented | `backend/app/services/framing_engine.py` | Aspect ratios (9:16, 1:1, 16:9), even integer dimension clamping, single/two-person/group strategies, headroom factor |
| M7-04 | Velocity-Constrained Dynamic Crop Smoothing | Reframing Engine | Implemented | `backend/app/services/framing_engine.py` | Window-weighted smoothing with `max_pan_velocity` limits, strict scene-cut isolation (instant step, zero blurring across cuts) |
| M7-05 | Preview / Renderer Mathematical Parity | Reframing Engine | Implemented | `backend/app/services/framing_engine.py`, `backend/app/services/reframing_renderer.py` | Consumes identical piecewise linear interpolation formula `interpolate_crop_at(t)` and filter expressions |
| M7-06 | Dynamic FFmpeg Filtergraph Renderer | Reframing Engine | Implemented | `backend/app/services/reframing_renderer.py` | Piecewise-linear time-varying crop filter (`crop=w:h:x:y`), scale to target (1080x1920), libx264, yuv420p, audio sync |
| M7-07 | Non-Destructive Revision History Ledger | Reframing Services | Implemented | `backend/app/services/reframing_service.py` | Versioned plan revisions, manual override retention, restore revision, render dispatch |
| M7-08 | Smart Reframing REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/reframing.py` | Analyze plan, preview crop, manual override patch, revisions list, restore revision, render revision, video stream |
| M7-09 | Reframing Review Workspace Frontend | Features / Reframing | Implemented | `frontend/src/features/reframing/ReframingWorkspace.tsx` | Dual viewports (source landscape overlay & true 9:16 portrait viewport), manual crop sliders, zoom/headroom, revisions modal, render trigger |
| M7-10 | Backend Automated Test Suite (6 tests) | Testing | Implemented | `backend/tests/test_milestone7_reframing.py` | Geometry, strategies, smoothing, expression parity, real FFmpeg rendering, API lifecycle & revisions (100% pass) |
| M7-11 | Frontend Vitest Test Suite (5 tests) | Testing | Implemented | `frontend/src/test/reframing.test.tsx` | Dual viewports, manual adjustment, revision drawer, restore revision, render action (100% pass) |

---

## Rendering Engine, Export Pipeline & Automatic Shorts Generation (Milestone 8)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M8-01 | Database Migration `0007_export_pipeline.sql` | DB / Migrations | Implemented | `backend/migrations/0007_export_pipeline.sql` | Schema for `exports` table with preset, configuration JSON, validation details, and indexes |
| M8-02 | Standard Export Presets Catalog | Export Services | Implemented | `backend/app/models/export.py` | YouTube Shorts / Reels (9:16), Landscape (16:9), Square Social (1:1) with CRF and codec defaults |
| M8-03 | Configurable Caption & Subtitle Engine | Export Services | Implemented | `backend/app/services/caption_engine.py` | ASS subtitle generator supporting word-highlight, phrase bursts, sentences, styling, and safe margins |
| M8-04 | Audio Processing & Fallback Synthesis | Export Services | Implemented | `backend/app/services/audio_pipeline.py` | Volume controls, fade in/out, EBU R128 loudness normalization, resample 48kHz, silent audio fallback |
| M8-05 | 15-Stage Modular Rendering Pipeline | Export Services | Implemented | `backend/app/services/export_service.py` | End-to-end coordinator integrating smart reframing keyframes, scaling, ASS burn-in, audio, and publishing |
| M8-06 | Subprocess Tracking & Real Process Cancellation | Export Services | Implemented | `backend/app/services/export_service.py` | Popen process registration, real-time progress parsing (`out_time_us`), and graceful process termination |
| M8-07 | Post-Render Output Validation Gate | Export Services | Implemented | `backend/app/services/output_validator.py` | Rigorous FFprobe stream inspection (dimensions, duration tolerance, codecs) + test frame decoding |
| M8-08 | Export REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/exports.py` | Presets, submit render, fast preview, list exports, export details, cancel, delete, HTTP 206 video stream |
| M8-09 | Frontend Shorts Export Studio Workspace | Features / Exports | Implemented | `frontend/src/features/exports/ExportStudio.tsx` | Preset selector, caption customization, audio sliders, live progress monitor, video player, export history |
| M8-10 | Backend Automated Pytest Suite (7 tests) | Testing | Implemented | `backend/tests/test_milestone8_export.py` | Presets, captions, audio filters, validation gate, full render, API lifecycle, cancellation (100% pass) |
| M8-11 | Frontend Vitest Test Suite (5 tests) | Testing | Implemented | `frontend/src/test/exports.test.tsx` | Studio rendering, tab switching, caption styling, render job monitor, export history (100% pass) |

---

## AI Video Editor, Multi-Track Timeline & Non-Destructive Editing (Milestone 9)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M9-01 | Database Migration `0008_timeline_editor.sql` | DB / Migrations | Implemented | `backend/migrations/0008_timeline_editor.sql` | Tables for `timelines`, `timeline_tracks`, `timeline_clips`, `timeline_commands`, `ai_conversations`, `ai_editing_plans`, `ai_messages` |
| M9-02 | Authoritative Timeline & Multi-Track Service | Timeline Core | Implemented | `backend/app/services/timeline_service.py` | Timeline CRUD, default tracks initialization (V2, V1, A1, A2), track mute/lock/visibility, duration recalculation |
| M9-03 | Validated Reversible Editing Commands Layer | Timeline Core | Implemented | `backend/app/services/timeline_command_service.py` | `InsertClip`, `MoveClip`, `TrimClip`, `SplitClip`, `DeleteClip`, `DuplicateClip`, `UpdateClipProps`, `AddTextOverlay` |
| M9-04 | Persistent Undo & Redo History Engine | Timeline Core | Implemented | `backend/app/services/timeline_command_service.py` | Transactional forward/inverse payloads surviving app restarts and crashes |
| M9-05 | AI Video Editor Assistant Service | AI Assistant | Implemented | `backend/app/services/ai_editor_service.py` | Context aggregation (media, transcripts, highlights, timeline state), query answering, structured plan generation with warnings |
| M9-06 | User Approval Gate & Safe Execution Engine | AI Assistant | Implemented | `backend/app/services/ai_editor_service.py` | Plan review card, user approval execution mapping safely into command layer; no silent or destructive execution |
| M9-07 | Multi-Track Timeline FFmpeg Rendering Pipeline | Timeline Core | Implemented | `backend/app/services/timeline_renderer.py` | Video layering, libass text overlays, multi-track audio mixing (`amix`), loudness normalization, Milestone 8 `OutputValidator` gate |
| M9-08 | Timeline & AI REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/timeline.py` | 23 REST endpoints covering timeline CRUD, tracks, clips, undo/redo, AI conversation, plans, and render |
| M9-09 | Frontend Timeline & AI Editor Workspace | Features / Timeline | Implemented | `frontend/src/features/timeline/TimelineEditor.tsx` | Toolbar, preview monitor, Inspector properties panel, AI assistant chat with plan review card, multi-track lanes and playhead |
| M9-10 | Backend Automated Test Suite (6 tests) | Testing | Implemented | `backend/tests/test_milestone9_timeline.py` | Timeline CRUD, clip operations/validation, persistent undo/redo, AI assistant, multi-track render, API lifecycle (100% pass) |
| M9-11 | Frontend Vitest Test Suite (5 tests) | Testing | Implemented | `frontend/src/test/timeline.test.tsx` | Sequence rendering, clip inspection, undo/redo, AI plan approval, render trigger (100% pass) |

---

## Character Extraction Studio, Character Library & System Integration (Milestone 10)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M10-01 | Database Migration `0009_character_studio.sql` | DB / Migrations | Implemented | `backend/migrations/0009_character_studio.sql` | Schema for `character_extraction_jobs`, `character_profiles`, `character_candidates`, `character_observations`, `character_review_events` |
| M10-02 | Configurable Frame Sampling & Region Detection | Character Core | Implemented | `backend/app/services/character_service.py` | CPU-first OpenCV skin/saliency detection, non-saturating frame sampling, bounding box & confidence tracking |
| M10-03 | Spatial-Temporal Candidate Clustering | Character Core | Implemented | `backend/app/services/character_service.py` | Provisional visual candidate groupings without claiming biometric identity verification |
| M10-04 | Dialogue & Observation Association | Character Core | Implemented | `backend/app/services/character_service.py` | Cropped thumbnail generation, transcript temporal intersection, explicit unverified speaker association disclaimer |
| M10-05 | Human-in-the-Loop Review Controls | Character Core | Implemented | `backend/app/services/character_service.py` | Rename candidate, confirm to library, merge candidate groups, split observations, reject, non-destructive detach |
| M10-06 | Persistent Character Library & Documented JSON Export | Character Core | Implemented | `backend/app/services/character_service.py` | Project-wide character repository, bio/tag management, appearance totals, versioned JSON export payload |
| M10-07 | Character Studio REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/characters.py` | 12 REST endpoints covering extraction jobs, candidate listing/patching, review actions, library queries, and export |
| M10-08 | Frontend Character Studio Workspace | Features / Characters | Implemented | `frontend/src/features/characters/CharacterStudio.tsx` | Two tabs (Candidate Review & Character Library), extraction controls, observation gallery, review modals, JSON viewer |
| M10-09 | Full End-to-End System Integration & Reliability | System | Implemented | `frontend/src/app/App.tsx`, `backend/app/main.py` | All 10 modules seamlessly connected; startup recovery, zero regressions across 51 backend + 52 frontend tests |
| M10-10 | Backend Automated Test Suite (4 tests) | Testing | Implemented | `backend/tests/test_milestone10_character.py` | Extraction & observations, review workflow (rename, detach, split, merge, confirm), library & export, REST API (100% pass) |
| M10-11 | Frontend Vitest Test Suite (6 tests) | Testing | Implemented | `frontend/src/test/characters.test.tsx` | Studio rendering, observation inspector, inline rename, confirm modal, library tab, JSON export download (100% pass) |

---

## Full Repository Audit, Evidence-Based Verification & Technical Debt Assessment (Milestone 11)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M11-01 | Full System Architecture Audit | Documentation | Implemented | `docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md` | Exhaustive verification of all 10 milestones, identifying real processing vs heuristics vs fallbacks |
| M11-02 | Implementation Classification & Honesty Audit | Audit | Implemented | `docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md` | Explicit breakdown distinguishing deep neural models, CV algorithms, rule-based heuristics, and offline fallbacks |
| M11-03 | Critical Technical Debt & Defect Registry | Audit / Quality | Implemented | `docs/audit/ZezEdit_2_0_SYSTEM_AUDIT.md` | Catalog of 10 ranked defects (DEF-01 through DEF-10) with reproduction steps, impacts, and corrective paths |
| M11-04 | React Error Boundary & Startup Crash Protection | Frontend Shell | Implemented | `frontend/src/components/ui/ErrorBoundary.tsx` | Catches unhandled render errors, presents user recovery action, eliminates blank-screen failure modes |
| M11-05 | Dark Mode Form Controls & Dropdown Unslop | UI Design System | Implemented | `frontend/src/styles/index.css`, `frontend/src/components/ui/Input.tsx` | Enforces `color-scheme: dark` and explicit background/text styling across all native select and option controls |
| M11-06 | Controlled Automated Test Verification | Testing | Implemented | `backend/tests/`, `frontend/src/test/` | 51/51 Pytest passing (100%), 52/52 Vitest passing (100%), 0 TypeScript errors, 2.29s Vite production build |
| M11-07 | SQLite WAL Integrity & FK Conformance | DB / Storage | Implemented | `storage/db/zezedit.db` | Verified 0 FK errors, database integrity check `ok`, all 9 migrations accounted for |
| M11-08 | Unslop Design System Installation & Redline Polish | Design / Shell | Implemented | `.agents/skills/unslop/`, `frontend/src/` | Applied Unslop 9-pass redline review, removed visual slop, quiet chrome, 4px grid |
| M11-09 | Graphify Knowledge Graph Build & Navigation | Tooling / Architecture | Implemented | `graphify-out/`, `.agents/rules/graphify.md` | Extracted 2,074 nodes, 5,772 edges across 113 communities; shortest path & explain verified |
| M11-10 | Unified Video Workspace Hub | Frontend Architecture | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | 9 integrated sub-workspaces for the active video asset preserving project and media context |
| M11-11 | Intelligent Post-Import Action Screen | Media Ingestion | Implemented | `frontend/src/features/media/PostImportModal.tsx` | Instant post-import action dialog with 4 distinct paths and live persistent job progress tracking |
| M11-12 | Full End-to-End User Journey Verification | Quality / E2E | Implemented | `docs/reports/milestone_11/` | Real browser verification across all 12 application views with live captured screenshot evidence |

---

## Pre-Deletion Baseline Reconstruction & Feature Parity Specification (Milestone 12)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M12-01 | Pre-Deletion Historical Baseline Specification | Reconstruction | Implemented | `docs/reconstruction/PRE_DELETION_BASELINE.md` | Authoritative recovery of historical state before Nov 11 deletion across all 20 application areas |
| M12-02 | Forensic Evidence Extraction (13M.12 & 13M.13) | Forensics | Implemented | `docs/reconstruction/PRE_DELETION_BASELINE.md` | Rigorous evidence extraction from surviving transcripts, 13M.12 report, and VS Code history |
| M12-03 | Feature Parity Matrix & Historical Gap Analysis | Specification | Implemented | `docs/reconstruction/FEATURE_PARITY_MATRIX.md` | Feature-by-feature parity analysis comparing pre-deletion capabilities against current ZezEdit 2.0 |
| M12-04 | Prioritized Restoration Roadmap | Architecture | Implemented | `docs/reconstruction/RESTORATION_ROADMAP.md` | 10-tier dependency-ordered implementation roadmap establishing exact sequence to achieve full parity |
| M12-05 | 13M.12 Mathematical Model & Test Recovery | CV / Tracking | Implemented | `docs/reconstruction/PRE_DELETION_BASELINE.md` | Verified 10/10 tracking tests, 113 backend pytest suite, 81 frontend vitest suite, and 3 contact sheets |
| M12-06 | 13M.13 Implementation & Partial Status Classification | UI / Revisions | Implemented | `docs/reconstruction/PRE_DELETION_BASELINE.md` | Documented 42 KB `ReframingReviewModal.tsx`, revision DB schema, and interrupted test status |
| M12-07 | Milestone 12 Comprehensive Reconstruction Report | Documentation | Implemented | `docs/reports/milestone_12_reconstruction_report.md` | 14-section formal milestone reconstruction and feature parity report |

---

## ZezEdit 1.0 Exact Feature Parity Specification (Milestone 13)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M13-01 | Immutable ZezEdit 1.0 Parity Specification | Specification | Implemented | `docs/reconstruction/ZEZEDIT_1_0_PARITY_SPECIFICATION.md` | 100 discrete requirements (`ZEZ-001` to `ZEZ-100`) covering all 10 product domains |
| M13-02 | Standardized Parity Scorecard Matrix | Tracking | Implemented | `docs/reconstruction/FEATURE_PARITY_MATRIX.md` | Authoritative measurement: 89 RESTORED (89%), 11 VERIFIED_PARTIAL (11%), 0 BLOCKED/UNRECOVERABLE |
| M13-03 | Parity Restoration Implementation Roadmap | Architecture | Implemented | `docs/reconstruction/RESTORATION_ROADMAP.md` | 5-phase dependency-ordered execution plan leading directly to complete feature parity |
| M13-04 | Milestone 13 Parity Restoration Plan Report | Documentation | Implemented | `docs/reports/milestone_13_parity_restoration_plan.md` | 12-section formal report detailing feature inventory, evidence paths, and next milestone |

---

## Video Analysis, AI Understanding & Temporal Context Restoration (Milestone 15)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M15-01 | Database Migration `0010_transcript_corrections_and_audio.sql` | DB / Migrations | Implemented | `backend/migrations/0010_transcript_corrections_and_audio.sql` | Adds `transcript_corrections` and `audio_analysis` tables with indexes |
| M15-02 | Audio Stream Inspection & Robust Silence Detection | Analysis Services | Implemented | `backend/app/services/audio_extractor.py` | FFprobe inspection, multi-channel handling, silent video fallback, and FFmpeg `silencedetect` |
| M15-03 | Real Scene Thumbnail Extraction & Serving | Analysis Services | Implemented | `backend/app/services/scene_detector.py`, `backend/app/api/v1/analysis.py` | Extracts scene representative JPEG thumbnails on disk; `/scene-thumbnail/{scene_id}` streaming endpoint |
| M15-04 | Non-Destructive Transcript Corrections (`ZEZ-025`) | Analysis / Captions | Implemented | `backend/app/api/v1/analysis.py`, `backend/app/services/export_service.py` | Full CRUD REST API; dynamically overlays raw Whisper text and applies to ASS export captions |
| M15-05 | Stage-Aware Analysis Caching & Fingerprinting (`ZEZ-029`) | Analysis Pipeline | Implemented | `backend/app/services/analysis_pipeline.py` | Checksum/mtime caching avoids re-running Whisper on unchanged media; supports `force_reanalysis` |
| M15-06 | Analysis Run History Selector (`ZEZ-030`) | Backend / Frontend | Implemented | `backend/app/api/v1/analysis.py`, `frontend/src/features/analysis/AnalysisWorkspace.tsx` | All runs preserved; dropdown selector allows historical inspection and comparison |
| M15-07 | Studio Dark UI Restoration & Lightbox (`ZEZ-027`, `ZEZ-098`) | Frontend UI | Implemented | `frontend/src/features/analysis/AnalysisWorkspace.tsx` | Unslop design compliance; Audio analysis panel, real thumbnails grid, lightbox modal, and inline editor |
| M15-08 | Backend Automated Parity Test Suite (6 tests) | Testing | Implemented | `backend/tests/test_milestone15_analysis_parity.py` | Stream inspection, silent video, scene thumbnails, caching, transcript corrections, temporal context (100% pass) |

---

## Core Product Workflow, Working Queue & Desktop Operations (Milestone 17)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M17-01 | Continuous Main Video to Shorts Pipeline | Workflow | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Full continuous workflow from import to analysis, highlight discovery, trimming, reframing, and export |
| M17-02 | Next Video Edit Workflow & Transition Modal | Workspace | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Dedicated Next Video button, auto-saving workspace state, and video switching dialog |
| M17-03 | Hardware Resource Inspector (`ZEZ-006`) | Monitoring | Implemented | `backend/app/api/v1/health.py`, `frontend/src/components/system/ResourceInspector.tsx` | Real-time CPU, RAM, process RSS, worker concurrency, and floating hover window |
| M17-04 | Working Queue & Job Orchestration (`ZEZ-094`, `ZEZ-095`) | Queue / Ops | Implemented | `backend/app/api/v1/jobs.py`, `frontend/src/features/queue/WorkingQueueView.tsx` | Full queue status tabs, queue distribution chart, job execution timeline logs |
| M17-05 | AI Provider Manager & Live Test Probe | AI Providers | Implemented | `backend/app/api/v1/ai_providers.py`, `frontend/src/features/providers/AIProviderManager.tsx` | Ollama, Faster-Whisper, and deterministic heuristic fallback cards, with live ping and model discovery |
| M17-06 | In-App Studio Documentation Center (`ZEZ-009`)| Docs / Help | Implemented | `backend/app/api/v1/docs_center.py`, `frontend/src/features/docs/DocumentationView.tsx` | Searchable categories, article listings, markdown renderer with 13 comprehensive guides |
| M17-07 | Scope Adjustment: Character Studio Deferred | Governance | Implemented | `docs/reconstruction/FEATURE_PARITY_MATRIX.md` | Character Studio deferred out of active priorities per M17 directive; preserved in DB and code |
| M17-08 | Regression Test Suite Expansion | Testing | Implemented | `backend/tests/test_milestone17_core_operations.py`, `frontend/src/test/milestone17_operations.test.tsx` | 61/61 backend pytest (100% pass), 56/56 frontend vitest (100% pass) |

---

## Unified Video-to-Shorts Production Pipeline (Milestone 18)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M18-01 | Authoritative Lifecycle State Machine | Pipeline Core | Implemented | `backend/app/services/workflow_state.py` | 18 explicit workflow lifecycle stages; self-healing dynamic derivation from SQLite tables and in-flight jobs |
| M18-02 | Workflow Telemetry & Next-Actions API | Backend API | Implemented | `backend/app/api/v1/media.py` | `GET /projects/{project_id}/media/{asset_id}/workflow` returning stage, stepper, counters, and available next actions |
| M18-03 | Multiple Shorts Batch Export Endpoint | Backend API | Implemented | `backend/app/api/v1/exports.py` | `POST /projects/{project_id}/exports/batch` enqueuing parallel independent render jobs with skipped candidate validation |
| M18-04 | Batch Export Multiple Shorts Modal | Frontend Studio | Implemented | `frontend/src/features/exports/BatchExportModal.tsx` | 9:16 / 1:1 / 16:9 aspect ratios, animated word captions, audio loudness normalization, multi-selection |
| M18-05 | Workflow Stage Header Banner & Progress Stepper | Frontend Studio | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Pipeline badge, 5-stage stepper (Ingest → Analysis → Highlights → Review → Export), telemetry counters |
| M18-06 | Dynamic Primary Next-Action Execution Dispatch | Workflow | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Context-aware 1-click action button dispatching Start Analysis, Discover Highlights, Review, Batch Export, Next Video |
| M18-07 | Per-Video State Persistence & Auto-save | Workspace Core | Implemented | `frontend/src/features/workspace/VideoWorkspace.tsx` | Restores active tab and video state from `localStorage`; real-time "✓ Auto-saved" visual confirmation |
| M18-08 | Multi-Video Strict Cross-Project Data Isolation | Architecture | Implemented | `backend/app/services/workflow_state.py` | Zero cross-project or cross-media state leakage; verified by automated multi-tenant test suites |
| M18-09 | Automated Backend Integration Test Suite | Testing | Implemented | `backend/tests/test_milestone18_unified_pipeline.py` | 5 comprehensive integration tests covering lifecycle, API, batch export, skipped candidates, data isolation (100% pass) |
| M18-10 | Automated Frontend Vitest Test Suite | Testing | Implemented | `frontend/src/test/milestone18_pipeline.test.tsx` | 3 vitest tests covering modal rendering, candidate selection, aspect ratio options, and API dispatch (100% pass) |

---

## Desktop Operations Center, Working Queue, Resource Inspector and AI Provider Manager (Milestone 19)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M19-01 | Real Working Queue & Cancellation / Retry Engine | Job Queue | Implemented | `backend/app/services/jobs.py`, `backend/app/api/v1/jobs.py` | Cancels active worker states; retries failed jobs without duplicate renders; logs `job_retried` timeline events |
| M19-02 | Queue Chart & Task Type Distribution Breakdown | Operations UI | Implemented | `frontend/src/features/queue/WorkingQueueView.tsx` | Visual queue bar, live counts (running/pending/completed/failed/cancelled), task type pills, duration column |
| M19-03 | Hardware Resource Inspector & Accessibility Controls | System Monitoring | Implemented | `frontend/src/components/system/ResourceInspector.tsx` | Hover activation with grace buffer, click-to-pin, Escape key dismiss, outside click dismiss, accessibility roles |
| M19-04 | AI Provider Manager & Studio Task Engine Routing | AI Providers | Implemented | `frontend/src/features/providers/AIProviderManager.tsx` | Ollama, Faster-Whisper, and heuristic cards, 4-task engine routing grid, live ping probe, and secret token masking |
| M19-05 | In-App Documentation Center Expansion | Docs / Help | Implemented | `backend/app/api/v1/docs_center.py`, `frontend/src/features/docs/DocumentationView.tsx` | 16 articles across 5 categories, including troubleshooting, keyboard shortcuts, and storage layout guides |
| M19-06 | Subsystem Diagnostics Probe API | Health / System | Implemented | `backend/app/api/v1/health.py`, `frontend/src/features/dashboard/FoundationOverview.tsx` | `GET /api/v1/system/diagnostics` probing SQLite WAL, storage buckets, FFmpeg/FFprobe binaries, Ollama, Whisper, host CPU/RAM |
| M19-07 | Automated Operations Backend Test Suite | Testing | Implemented | `backend/tests/test_milestone19_desktop_operations.py` | 6 integration tests covering diagnostics, cancellation, retries, stats, provider resiliency, and docs search (100% pass) |
| M19-08 | Automated Operations Frontend Vitest Suite | Testing | Implemented | `frontend/src/test/milestone19_desktop_operations.test.tsx` | 4 tests covering ResourceInspector, WorkingQueueView, AIProviderManager, and DocumentationView (100% pass) |

---

## Production Hardening, Long-Video Performance, Storage Management & Recovery (Milestone 20)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M20-01 | Large Video Streaming Import & Media Integrity | Media Pipeline | Implemented | `backend/app/services/media_pipeline.py`, `backend/app/services/media.py` | 64KB bounded chunk streaming import; FFprobe metadata persistence; source media integrity scanner (`online`, `missing`, `corrupted`) |
| M20-02 | Safe Media Relinking with Candidate Verification | Media / Relink | Implemented | `backend/app/services/media.py`, `backend/app/api/v1/media.py` | Candidate duration, resolution, size comparison with discrepancy warnings; force relink protection; preserves analysis and candidate history |
| M20-03 | Memory-Aware Video Processing & Disk Caching | Video / Frames | Implemented | `backend/app/services/frame_sampler.py`, `backend/app/services/audio_extractor.py` | Timestamp seeking (`-ss` before `-i`); downscaling to 640px; disk frame caching; bounded 16kHz mono audio chunk extraction |
| M20-04 | Resource-Aware Worker Management & Priority Scheduling | Job Orchestrator | Implemented | `backend/app/services/jobs.py` | Single queue architecture; configurable concurrency; host CPU/RAM pressure guard; strict priority dispatch (200 > 150 > 100 > 50) |
| M20-05 | Granular Job Checkpoints & Crash Recovery | Recovery Core | Implemented | `backend/app/services/jobs.py`, `backend/migrations/0011_*.sql` | Persists completed units and intermediate artifacts; restart recovery preserves checkpoints for idempotent resume without work duplication |
| M20-06 | Categorized Storage Breakdown & Low-Storage Guard | Storage Service | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | Real filesystem measurement across 9 categories; low storage threshold (< 5GB) warning |
| M20-07 | Safe Disposable Cache Cleanup Preview & Execution | Storage Ops | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | Scans strictly disposable `temp/` buffers; cryptographic confirmation token; guarantees source media, projects, and exports are never deleted |
| M20-08 | Database Diagnostics & PRAGMA Verification | Database Ops | Implemented | `backend/app/services/backup_service.py`, `backend/app/api/v1/settings.py` | Live `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, WAL mode confirmation, table row counts, orphaned record detection |
| M20-09 | Online Database Backups & Pre-Restore Safety Copy | Backups Core | Implemented | `backend/app/services/backup_service.py`, `backend/app/api/v1/settings.py` | Verified SQLite online backups; pre-restore automatic safety snapshots; recovery readiness status reporting |
| M20-10 | Multi-Tab Studio Settings Manager | Settings UI | Implemented | `frontend/src/features/settings/SettingsManager.tsx` | 6 dedicated tabs: General, Processing & Performance, Storage Management, Backups & Recovery, AI Providers, Diagnostics |
| M20-11 | Media Library Integrity & Relink Dialog | Media UI | Implemented | `frontend/src/features/media/MediaLibraryView.tsx` | Batch project media integrity check button; missing file relink dialog with candidate comparison preview and force override |
| M20-12 | Comprehensive Automated Test Suites | Testing / QA | Implemented | `backend/tests/test_milestone20_production_reliability.py`, `frontend/src/test/milestone20_production_hardening.test.tsx` | 7 backend pytest tests (100% pass); 5 frontend vitest tests (100% pass); 68/68 total vitest tests passing |

---

## Editorial & Notification Refinements (Milestone 23)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| M23-01 | AI Assistant Plan Version History & Restore API | Timeline API | Implemented | `backend/app/api/v1/timeline.py`, `backend/app/services/ai_editor_service.py` | `GET /timelines/{id}/ai/plans` listing version history; `POST /timelines/{id}/ai/plans/{plan_id}/restore` rolling back / applying plan operations |
| M23-02 | Interactive Plan Version History Drawer (`ZEZ-080`) | Timeline UI | Implemented | `frontend/src/features/timeline/TimelineEditor.tsx` | Slide-over drawer in AI tab with dynamic version counter badge, timestamps, status badges (`executed`, `proposed`, `rejected`), operations diff breakdown, and 1-click restore |
| M23-03 | Global Floating Toast Notification System (`ZEZ-008`) | System UI | Implemented | `frontend/src/components/system/ToastNotificationCenter.tsx`, `frontend/src/main.tsx`, `frontend/src/app/App.tsx` | Fixed bottom-right container, 4-second self-dismiss timers, pause on hover, action button hooks, and background job transition alerts (`running` -> `completed`/`failed`) |
| M23-04 | Automated Test Suites for Plan History & Toasts | Testing / QA | Implemented | `backend/tests/test_milestone9_timeline.py`, `frontend/src/test/notifications.test.tsx`, `frontend/src/test/timeline.test.tsx` | 80/80 backend pytest tests passing; 73/73 frontend vitest tests passing; verified via live browser verification with screenshot evidence |

---

---

## Unified Single-Video Studio Evolution (Sessions 0–3)

| ID | Feature / Capability | Module | Status | Main Path | Notes |
|---|---|---|---|---|---|
| S0-01 | Architectural Audit, Multi-Session Blueprint & Schema Design | Architecture | Implemented | `docs/architecture/SESSION_0_AUDIT_REPORT.md`, `docs/architecture/UNIFIED_VIDEO_STUDIO_DESIGN.md` | Single-video workflow roadmap, database & API migration specs, and unified studio design blueprint |
| S1-01 | Navigation Simplification & Sidebar Streamlining | App Shell | Implemented | `frontend/src/app/App.tsx`, `frontend/src/components/layout/Sidebar.tsx` | Removed disconnected standalone tools (Video Analysis, Highlights, Reframing, Shorts Export); streamlined sidebar to Media Library |
| S1-02 | Unslopped Media Library with Dedicated "Open Video Studio" Action | Media Library | Implemented | `frontend/src/features/media/MediaLibraryView.tsx` | Removed all emojis; single unified primary action on video cards to enter Dedicated Studio |
| S2-01 | Dedicated `/studio/:assetId` Route & Synchronized History | Routing / Navigation | Implemented | `frontend/src/app/App.tsx`, `frontend/src/features/studio/SingleVideoStudio.tsx` | Pure React state URL synchronization with `window.history.pushState` and `popstate` support; direct URL hydration |
| S2-02 | Global Analysis Progress Bar with Stage & Percentage Telemetry | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Real-time measurable progress bar with stage status, percentage, elapsed time, and cancellation trigger |
| S2-03 | Upfront Generation Configuration Bar | Studio Controls | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Upfront aspect ratio selection (9:16, 1:1, 16:9, 4:5), clip count (5, 6, 10, 15, 20), creative direction (Best Overall, Dramatic, Action, Emotional/Sad, Dialogue, Funny) |
| S2-04 | Framed Video Preview Player with Dynamic Ratio Adaptation | Video Studio | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Aspect-ratio constrained preview container, scrub bar, transport controls, and direct candidate seek |
| S2-05 | Generated Shorts Showcase with Direct Export Triggers | Studio Showcase | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Candidate shorts cards with virality scores, duration badges, category pills, seeking triggers, and 1-click MP4 export |
| S2-06 | Collapsible Deep Intelligence Drawers | Studio Intelligence | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Collapsible drawers for Timestamped Transcript, Detected Scene Cuts, and Detailed Media Metadata |
| S2-07 | Comprehensive Vitest Automated Test Suite | Testing / QA | Implemented | `frontend/src/test/singleVideoStudio.test.tsx` | 6 comprehensive tests covering loading, upfront controls, discovery trigger, export submission, and drawers (19/19 test files, 94/94 tests pass) |
| S3-01 | Database Migration `0012_unified_analysis_pipeline.sql` | DB / Migrations | Implemented | `backend/migrations/0012_unified_analysis_pipeline.sql` | Added `job_id`, `source_signature`, `stage_details_json`, `checkpoint_data_json` to `analysis_runs` |
| S3-02 | Bounded Memory Streaming Pipeline for 1–2 GB Movies | Analysis Core | Implemented | `backend/app/services/analysis_pipeline.py` | Out-of-process streaming FFmpeg demuxing, scene detection, and frame sampling without loading full video into RAM |
| S3-03 | Sub-Millisecond Source Signature Calculation & Invalidation | Analysis Core | Implemented | `backend/app/services/analysis_pipeline.py` | Hybrid `size:mtime:hash64k` signature; instant cache invalidation upon file change |
| S3-04 | Faster-Whisper Automatic VAD Fallback | Speech AI | Implemented | `backend/app/services/transcription.py` | Automatic fallback to `vad_filter=False` when VAD classifies dialogue over music as silence; verified on Hindi rhymes |
| S3-05 | Persistent JobOrchestrator Linkage & Checkpoint Sync | Jobs / Pipeline | Implemented | `backend/app/services/analysis_pipeline.py`, `backend/app/services/jobs.py` | Synchronized `media_analysis` jobs, priority 150, stage progress, and non-clamping completion checkpoints |
| S3-06 | Granular Stage Telemetry & Cache Inspection APIs | Backend API | Implemented | `backend/app/api/v1/analysis.py` | `GET /analysis/{id}/telemetry` and `GET /analysis/{id}/cache` exposing stage, pct, timings, warnings, and component breakdown |
| S3-07 | Analysis Cancellation & Retry State Transitions | Backend API | Implemented | `backend/app/api/v1/analysis.py` | `POST /analysis/{id}/cancel` and `POST /analysis/{id}/retry` synchronized with JobOrchestrator state machines |
| S3-08 | Single-Video Studio Real Progress Banner & Telemetry UI | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Live stage telemetry polling (1.5s), elapsed time, cancel/retry action buttons, cache info badge, and distinct stage milestones |
| S3-09 | Automated Test Suite for Session 3 Unified Analysis | Testing / QA | Implemented | `backend/tests/test_session3_unified_analysis.py` | 7 comprehensive tests covering signatures, job linkage, telemetry, caching, cancel, retry, and audio-less video (100% pass) |
| S4-01 | Multimodal Candidate Discovery Engine | Highlights Core | Implemented | `backend/app/services/highlight_discovery.py` | Multi-signal discovery analyzing transcript dialogue, speech turns, scene cuts, keyframe visual semantics, and audio energy with explainable scoring |
| S4-02 | Natural Boundary Snapping & Breathing Room | Highlights Core | Implemented | `backend/app/services/highlight_discovery.py` | Speech closure on terminal punctuation (`.`, `!`, `?`), 0.15s lead-in margin, and scene cut snapping preventing flash frames and mid-sentence cuts |
| S4-03 | 7 Creative Direction Profiles & Adaptive Weighting | Intelligence Core | Implemented | `backend/app/services/highlight_discovery.py` | Distinct multimodal weighting profiles for Best Overall, Viral & Punchy, Dramatic, Action & Motion, Emotional / Sad, Engaging Dialogue, and Humorous |
| S4-04 | Persistent Novelty & Non-Repetition Engine | Novelty Core | Implemented | `backend/app/services/highlight_discovery.py` | tIoU $\ge 0.50$ and OverlapRatio $\ge 0.60$ novelty exclusion checks against historical intervals; verified $<0.38$ max overlap on real media |
| S4-05 | Database Migration `0013_candidate_discovery_novelty.sql` | DB / Migrations | Implemented | `backend/migrations/0013_candidate_discovery_novelty.sql` | Schema migration for `candidate_generation_runs`, `media_generated_clips_history`, and candidate boundary confidence columns |
| S4-06 | REST Endpoints for Discovery, Runs & Novelty History | Backend API | Implemented | `backend/app/api/v1/highlights.py` | `POST /highlights/generate-more`, `GET /highlights/runs`, `GET /highlights/runs/{id}`, and `GET /highlights/history` |
| S4-07 | Single-Video Studio Candidate Cards with Multimodal Score Popovers | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Candidate cards with Attractiveness estimate, Natural Cut confidence badge, creative direction pill, and expandable 6-signal breakdown grid |
| S4-08 | Candidate Batches Drawer & Novelty Tracking Ledger UI | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | Drawer tab for candidate discovery runs, batch filtering, requested vs selected counts, and novelty exclusions |
| S4-09 | Comprehensive Test Suites for Candidate Discovery & Novelty | Testing / QA | Implemented | `backend/tests/test_session4_candidate_discovery.py`, `frontend/src/test/session4_candidate_discovery.test.tsx` | 5/5 backend tests and 4/4 frontend tests passing (100% pass across 28 backend tests and 98 frontend tests) |
| S5-01 | Database Migration `0014_candidate_clip_edits.sql` | DB / Migrations | Implemented | `backend/migrations/0014_candidate_clip_edits.sql` | Dedicated candidate clip edits schema preserving original candidate discovery data and novelty records |
| S5-02 | Candidate Clip Editing & Persistence Service | Core Services | Implemented | `backend/app/services/clip_editing_service.py` | Isolated edit state management: timestamp bounds validation, duration computation, aspect ratio framing, manual crop offsets, and reset-to-original |
| S5-03 | Candidate Clip Editing REST API Endpoints | Backend API | Implemented | `backend/app/api/v1/clip_edits.py` | `GET/PUT /media/{mid}/candidates/{cid}/edit`, `POST .../edit/reset`, `POST .../edit/track` |
| S5-04 | Interval-Bounded Smart Subject Tracking | Reframing Core | Implemented | `backend/app/services/reframing_service.py`, `backend/app/services/subject_tracker.py` | Supports explicit interval `start_time` and `end_time` tracking via OpenCV Haar cascades and central saliency fallback without full video decode |
| S5-05 | Interactive Candidate Clip Editor Modal | Studio UI | Implemented | `frontend/src/features/studio/CandidateClipEditorModal.tsx` | Bounded clip loop player, dynamic aspect ratio crop box overlay, timeline trimming handles with +/-0.5s adjusters, aspect ratio buttons (9:16, 1:1, 16:9, 4:5), and framing mode tabs |
| S5-06 | Single-Video Studio Candidate Card "Edit Clip" Integration | Studio UI | Implemented | `frontend/src/features/studio/SingleVideoStudio.tsx` | "Edit Clip" button on discovered candidate cards launching the focused clip editor modal |
| S5-07 | Automated Unit & Integration Test Suites | Testing / QA | Implemented | `backend/tests/test_session5_clip_editing.py`, `frontend/src/test/session5_clip_editing.test.tsx` | 4/4 backend tests and 4/4 frontend tests passing (100% pass across 11 unified pipeline tests and 102 frontend tests) |
| PR-01 | Single-Button Clear All Application Data API | Storage Core | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | `POST /storage/clear-all-data` with explicit `DELETE` confirmation; sweeps all managed storage subdirectories and database tables while preserving migrations and app settings |
| PR-02 | Clear All Data Unit Test Suite | Testing / QA | Implemented | `backend/tests/test_storage_clear_all_data.py` | 2/2 tests verifying token validation, file deletion across managed directories, SQLite database truncation, and default workspace re-creation |
| PR-03 | Direct Video Ingestion & Short Video Generator Library | Library UI | Implemented | `frontend/src/features/videos/ShortVideoGeneratorLibrary.tsx` | Direct drag & drop / file picker with video type validation, auto-title derivation, and card grid with "Open Video Dashboard" CTA |
| PR-04 | Dedicated Video Edit Dashboard (`/videos/:assetId`) | Dashboard UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Centralized video workspace with top persistent header, real-time stage progress bar & ETA, and 8 dedicated horizontal tabs |
| PR-05 | 8 Dedicated Video Inspection & Generation Tabs | Studio UI | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | 1. Home (Player + Specs), 2. Short Generator (18 directions, presets, tracking), 3. Generated Shorts (Cards, Edit Modal, Export), 4. Generated Scripts (Cards, Regenerate Video), 5. Analyzed Frames, 6. Voice & Transcript, 7. Scene Analysis, 8. Video Details |
| PR-06 | Clear All Application Data Confirmation Modal | Settings UI | Implemented | `frontend/src/features/settings/SettingsManager.tsx` | High-impact warning card and dialog requiring typing `DELETE` to execute total wipeout |
| PR-07 | Video-Centric Frontend Automated Tests | Testing / QA | Implemented | `frontend/src/test/productRestructure.test.tsx` | 2/2 tests verifying ShortVideoGeneratorLibrary and VideoEditDashboard tabs (104 frontend tests pass) |
| S6A-01 | Reusable Video Intelligence Engine & Sub-Second Cache Validation | Intelligence Core | Implemented | `backend/app/services/highlight_discovery.py` | Full video analysis executed once; all subsequent short generations reuse stored audio, scenes, transcripts, and frames in ~0.12s |
| S6A-02 | Simplified 4-Option Default Generator UI & Graphite Unslopped Layout | UI / Dashboard | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Clean, calm default form: Option 1 AI Recommended clip count, Option 2 Best Overall / Varied, Option 3 9:16 Vertical, Option 4 AI Selects Best Duration |
| S6A-03 | Collapsible Advanced Settings & Per-Video Persistence | Studio Controls | Implemented | `frontend/src/features/videos/VideoEditDashboard.tsx` | Collapsed by default; 7 active supported creative directions, 11 disabled "Coming Soon", tracking modes, scene focus, novelty policy, localStorage config persistence |
| S6A-04 | Multi-Layer Persistent Novelty & Temporal Overlap Engine | Novelty Core | Implemented | `backend/app/services/highlight_discovery.py` | Exact interval matching (<2.5s tolerance), strict temporal IoU / asymmetric overlap guards, transcript token similarity checks |
| S6A-05 | Aspect-Ratio Independent Rejection & Honest Exhaustion Handling | Highlights Core | Implemented | `backend/app/services/highlight_discovery.py` | Changing aspect ratios tests against all recorded moments; detects exhaustion honestly with `is_novelty_exhausted` and warning banner |
| S6A-06 | Database Migration `0015_reusable_intelligence_and_generate_more.sql` | DB / Migrations | Implemented | `backend/migrations/0015_reusable_intelligence_and_generate_more.sql` | Added `generation_type`, `reused_analysis_run_id`, `duration_preference`, and `is_novelty_exhausted` to `candidate_generation_runs` |
| S6A-07 | Real Video Verification on 73.3MB Media File | Testing / QA | Implemented | `backend/scripts/verify_session6a_real_video.py` | Verified on `Ek Mota Hathi Ghumne Chala.mp4` (0.127s discovery time, 0 duplicates generated, novelty exhaustion recorded) |
| S6A-08 | Comprehensive Automated Test Suites | Testing / QA | Implemented | `backend/tests/test_session6a_reusable_intelligence_and_generate_more.py` | 6/6 dedicated session tests passing (152/152 backend tests, 106/106 frontend tests passing) |
| S6B-01 | Database Migration `0016_process_manager_and_storage_reclamation.sql` | DB / Migrations | Implemented | `backend/migrations/0016_process_manager_and_storage_reclamation.sql` | Adds `media_asset_id` and `parent_job_id` columns with indexes to `jobs` table |
| S6B-02 | Central Process Manager Dashboard & Subprocess Lineage | Core Services | Implemented | `frontend/src/features/queue/WorkingQueueView.tsx`, `backend/app/services/jobs.py` | Unified table of background tasks across all videos, Category & Status filters, video picker, search, retry attempt lineage, and subprocess tree cancellation via `psutil` |
| S6B-03 | Process Details Drawer with Live Logs & Elapsed/ETA Timers | Dashboard UI | Implemented | `frontend/src/features/queue/WorkingQueueView.tsx` | Slide-over drawer with process metadata, progress bar, duration counters, retry tree, and raw execution logs |
| S6B-04 | Process Manager API Parity across `/processes` and `/jobs` | Backend API | Implemented | `backend/app/api/v1/jobs.py`, `backend/app/api/v1/__init__.py` | Full route parity for listing, getting, cancelling, retrying, and deleting jobs |
| S6B-05 | Stale Process Crash Recovery on Startup | Jobs / Core | Implemented | `backend/app/services/jobs.py` | Auto-detects interrupted running/cancelling jobs on server startup and flags them as `interrupted` |
| S6B-06 | Single Video Deletion Storage Reclamation | Media Core | Implemented | `backend/app/services/media.py` | Deletes associated physical files (`media/`, `proxies/`, `thumbnails/`, `analysis/`) and marks active jobs cancelled on single video delete |
| S6B-07 | Complete User Data Cleanup & Physical Storage Reclamation | Storage Core | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | Sweeps all managed storage directories, terminates active jobs, empties user DB tables, compacts SQLite physical file with double WAL checkpoints, and re-creates default project |
| S6B-08 | Storage Cleanup Preview API & Reclaimed Byte Telemetry | Storage Core | Implemented | `backend/app/services/storage.py`, `backend/app/api/v1/settings.py` | Computes item counts (videos, clips, frames, temp files), estimated reclaimable bytes, and pre/post physical disk delta |
| S6B-09 | Settings Storage Manager UI Integration | Settings UI | Implemented | `frontend/src/features/settings/SettingsManager.tsx` | "Refresh Storage Usage" button, dynamic cleanup preview breakdown, active jobs warnings, and `DELETE ALL USER DATA` confirmation modal |
| S6B-10 | Automated Test Suites for Process Manager & Storage Reclamation | Testing / QA | Implemented | `backend/tests/test_process_manager_lifecycle.py`, `backend/tests/test_storage_reclamation_e2e.py`, `frontend/src/test/processesManager.test.tsx`, `frontend/src/test/storageReclamation.test.tsx` | 8/8 backend lifecycle tests, 4/4 backend storage tests, 9/9 frontend process manager tests, 2/2 frontend storage tests (100% pass) |

| ID | Feature / Capability | Module | Status | Planned Milestone |
|---|---|---|---|---|
| M14 | Interactive Reframing Review, Draggable Crop Canvas & Keyframe Diamonds (`ZEZ-050`–`054`) | Reframing Core | Planned | Milestone 14 |
| M15 | System Alerts, Resource Monitoring, In-App Documentation & AI Version Drawer | Shell / UI | Planned | Milestone 15 |
| M16 | Timeline Advanced Multi-Track Audio Mixing, Ducking & Karaoke Captions | Timeline Core | Planned | Milestone 16 |
| M17 | Full Regression Test Parity ($\ge 120$ Backend Tests, $\ge 85$ Frontend Tests) | Testing / QA | Planned | Milestone 17 |
| M18 | Real Vision & Face Detection Engine (YuNet ONNX / MobileFaceNet CPU Re-ID) | Vision Core | Planned | Milestone 18 |
| M19 | Performance Optimization & Hardware Acceleration (QuickSync / NVENC Presets) | Performance | Planned | Milestone 19 |
| M20 | Production Desktop Packaging & Offline Installer (Electron / Tauri Distribution) | Packaging | Planned | Milestone 20 |
