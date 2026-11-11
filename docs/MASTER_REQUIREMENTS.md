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

### Module D — Highlight Discovery
- Analyze transcript + visual + scene-cut context before and after candidate windows to preserve setup and payoff without clipping sentences.
- Group related moments and produce ranked candidate clips for user review.
- **Honesty Constraint:** Ranking scores represent heuristic/model relevance rankings—never presented as "verified viral probability."

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
- **Milestone 9 (Next):** Multi-Track Timeline Editor (Shared Model, Bounded NLE UI, Undo/Redo, Autosave).
- **Milestone 10:** Conversational AI Video Editor (Intent Router, Schema-Validated Edit Plans, Safe Executor).
- **Milestone 11:** Character Extraction Studio & Persistent Character Library.
- **Milestone 12:** Final Packaging, Multi-Format Archiving & Project Backup.
