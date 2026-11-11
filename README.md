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
