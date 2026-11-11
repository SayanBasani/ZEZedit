# ZezEdit 2.0 — Local-First AI Video Editor

ZezEdit 2.0 is a modular, CPU-first, local-first AI-assisted video editor for Windows 11.

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

## 4. Exact Windows PowerShell commands to run the frontend

Development server (`http://127.0.0.1:5173`, proxying `/api` to `http://127.0.0.1:8000`):

```powershell
cd D:\ZezEdit\frontend
npm run dev
```

Production TypeScript check & Vite bundle build:

```powershell
cd D:\ZezEdit\frontend
npm run build
```

---

## 5. Exact Windows PowerShell commands to run the backend

Start FastAPI via Uvicorn (`http://127.0.0.1:8000`):

```powershell
cd D:\ZezEdit\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run backend automated tests:

```powershell
cd D:\ZezEdit\backend
.\.venv\Scripts\pytest
```

Run frontend unit tests:

```powershell
cd D:\ZezEdit\frontend
npm test
```

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

## Architecture & Documentation

- [Master Requirements](docs/MASTER_REQUIREMENTS.md)
- [Feature Status](docs/feature_status.md)
- [Verification Checklist](docs/feature_test_checklist.md)
- [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Database Design & Migrations](docs/architecture/DATABASE_DESIGN.md)
- [API Design](docs/architecture/API_DESIGN.md)
- [Job Orchestration](docs/architecture/JOB_ORCHESTRATION.md)
- [Media Pipeline](docs/architecture/MEDIA_PIPELINE.md)
- [Timeline Data Model](docs/architecture/TIMELINE_MODEL.md)
- [Security & Data Safety](docs/architecture/SECURITY_AND_DATA_SAFETY.md)
- [Technology Decisions](docs/architecture/TECHNOLOGY_DECISIONS.md)
