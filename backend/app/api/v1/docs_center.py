"""In-app documentation and knowledge center endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.schemas.core import (
    DocArticleDetailResponse,
    DocArticleDTO,
    DocCategoryDTO,
)

router = APIRouter(prefix="/docs", tags=["docs"])

DOC_CATEGORIES = [
    DocCategoryDTO(
        id="getting-started",
        name="Getting Started",
        description="Core architecture, CPU-first philosophy, and basic workflows.",
        article_count=4,
    ),
    DocCategoryDTO(
        id="workflow",
        name="Core Editing Workflow",
        description="The continuous pipeline from long video to exported shorts.",
        article_count=3,
    ),
    DocCategoryDTO(
        id="analysis-highlights",
        name="Analysis & Highlight Discovery",
        description="Understanding Whisper transcription, scene cuts, and 9-factor scoring.",
        article_count=3,
    ),
    DocCategoryDTO(
        id="reframing-export",
        name="Smart Reframing & Export",
        description="Aspect ratios (9:16, 1:1), OpenCV subject tracking, and FFmpeg encoding.",
        article_count=2,
    ),
    DocCategoryDTO(
        id="system-operations",
        name="System & Operations",
        description="Working queue, hardware resource monitoring, and AI providers.",
        article_count=4,
    ),
]

DOC_ARTICLES = [
    DocArticleDTO(
        id="architecture-overview",
        title="ZezEdit Architecture & CPU-First Execution",
        category="getting-started",
        summary="Why ZezEdit runs locally on Intel Core i3-1220P CPU baseline without requiring cloud GPUs.",
        tags=["architecture", "cpu-first", "sqlite", "offline"],
        reading_time_minutes=3,
    ),
    DocArticleDTO(
        id="quickstart-guide",
        title="Quickstart: First Video to Exported Short",
        category="getting-started",
        summary="Step-by-step walkthrough of importing, analyzing, selecting highlights, and exporting.",
        tags=["quickstart", "walkthrough", "tutorial"],
        reading_time_minutes=4,
    ),
    DocArticleDTO(
        id="next-video-workflow",
        title="Next Video Workflow & Project Isolation",
        category="workflow",
        summary="How to switch seamlessly between source videos without losing candidate reviews or timeline edits.",
        tags=["workflow", "next-video", "persistence", "projects"],
        reading_time_minutes=3,
    ),
    DocArticleDTO(
        id="timeline-editing-basics",
        title="Multi-Track Timeline & Clip Trimming",
        category="workflow",
        summary="Manipulating video and audio tracks, splitting clips, and precision boundary snapping.",
        tags=["timeline", "trimming", "tracks", "nle"],
        reading_time_minutes=4,
    ),
    DocArticleDTO(
        id="post-import-decisions",
        title="Source Media Ingestion & Validation",
        category="workflow",
        summary="Local import, external referencing vs managed storage, FFprobe metadata extraction, and proxy generation.",
        tags=["import", "media", "ffprobe", "storage"],
        reading_time_minutes=3,
    ),
    DocArticleDTO(
        id="multistage-analysis",
        title="Multi-Stage Video Analysis Pipeline",
        category="analysis-highlights",
        summary="Detailed breakdown of the 6 stages: Audio extraction, Whisper ASR, dialogue turns, scene detection, visual sampling, and vision.",
        tags=["analysis", "whisper", "scene-detection", "transcription"],
        reading_time_minutes=5,
    ),
    DocArticleDTO(
        id="highlight-scoring-engine",
        title="Explainable 9-Factor Highlight Scoring",
        category="analysis-highlights",
        summary="How candidate shorts are scored across semantic interest, narrative completeness, audio energy, and visual action.",
        tags=["highlights", "scoring", "candidates", "explainability"],
        reading_time_minutes=4,
    ),
    DocArticleDTO(
        id="transcript-corrections",
        title="Non-Destructive Transcript Corrections",
        category="analysis-highlights",
        summary="Editing speech recognition words without overwriting original Whisper transcripts.",
        tags=["transcript", "corrections", "captions"],
        reading_time_minutes=2,
    ),
    DocArticleDTO(
        id="smart-reframing-engine",
        title="Smart Reframing & Subject Tracking",
        category="reframing-export",
        summary="Converting 16:9 landscape to vertical 9:16 using OpenCV face & subject detection with smoothing.",
        tags=["reframing", "opencv", "9:16", "tracking", "keyframes"],
        reading_time_minutes=4,
    ),
    DocArticleDTO(
        id="rendering-export-pipeline",
        title="FFmpeg Export Pipeline & Presets",
        category="reframing-export",
        summary="Hardware-efficient H.264 rendering, burn-in captions, audio normalization, and container verification.",
        tags=["export", "ffmpeg", "rendering", "presets"],
        reading_time_minutes=3,
    ),
    DocArticleDTO(
        id="working-queue-guide",
        title="Working Queue & Job Orchestration",
        category="system-operations",
        summary="Monitoring background jobs, canceling tasks, retrying failures, and crash recovery.",
        tags=["queue", "jobs", "background", "recovery"],
        reading_time_minutes=3,
    ),
    DocArticleDTO(
        id="resource-inspector-guide",
        title="CPU & Memory Resource Inspector",
        category="system-operations",
        summary="Using the hover resource indicator to monitor real-time CPU, RAM, and background concurrency.",
        tags=["system", "resources", "psutil", "monitoring"],
        reading_time_minutes=2,
    ),
    DocArticleDTO(
        id="ai-providers-configuration",
        title="Configuring Ollama & Faster-Whisper",
        category="system-operations",
        summary="Setting up local Ollama instances, downloading Qwen models, and testing offline fallbacks.",
        tags=["ollama", "whisper", "ai-providers", "models"],
        reading_time_minutes=3,
    ),
    DocArticleDTO(
        id="troubleshooting-guide",
        title="Troubleshooting: FFmpeg, Out of Memory & AI Providers",
        category="system-operations",
        summary="Solutions for missing binaries, high CPU usage, Ollama connectivity issues, and worker recovery.",
        tags=["troubleshooting", "errors", "ffmpeg", "memory", "recovery"],
        reading_time_minutes=4,
    ),
    DocArticleDTO(
        id="keyboard-shortcuts",
        title="Keyboard Shortcuts & Studio Navigation",
        category="getting-started",
        summary="Boost editing productivity with playhead shortcuts, split cuts, zoom, and tab navigation.",
        tags=["shortcuts", "hotkeys", "navigation", "editing"],
        reading_time_minutes=2,
    ),
    DocArticleDTO(
        id="storage-directories",
        title="Storage Layout, File Boundaries & Retention",
        category="getting-started",
        summary="Detailed map of the 12 storage buckets, non-destructive media policy, and cleanup procedures.",
        tags=["storage", "directories", "retention", "cleanup", "boundaries"],
        reading_time_minutes=3,
    ),
]

DOC_CONTENT = {
    "architecture-overview": """# ZezEdit Architecture & CPU-First Execution

ZezEdit is designed as a **local-first AI video editor and short-video generation studio**.

### Core Tenets

1. **CPU-First Execution:** The baseline environment is an **Intel Core i3-1220P CPU** with 16GB RAM. All pipelines—FFmpeg extraction, Faster-Whisper transcription (int8 quantized), PyAV scene detection, OpenCV Haar tracking, and rendering—are optimized to operate purely on CPU cores without requiring expensive cloud GPUs or dedicated CUDA hardware.
2. **Deterministic Offline Fallbacks:** If external LLMs or Ollama services are not installed or offline, ZezEdit gracefully falls back to deterministic heuristic engines for scene scoring, framing, and narrative clustering. Work is never blocked.
3. **Persistent SQLite State:** All project states, media assets, transcript corrections, candidate clips, timelines, and background job states are transactionally recorded in SQLite with Write-Ahead Logging (`WAL`) enabled.
4. **Non-Destructive Workflows:** Original user media files are never overwritten or altered. Derived proxies, thumbnails, waveform caches, and rendered exports are segregated in deterministic storage subdirectories.
""",
    "quickstart-guide": """# Quickstart: From Long Video to Exported Shorts

Follow this 5-step workflow to generate high-performing short clips:

### Step 1: Import Source Video
Navigate to **Media Library** or click **New Project** on the Dashboard. Drag-and-drop your `.mp4`, `.mov`, or `.mkv` source video. Choose **External Reference** (fastest, zero disk duplication) or **Copy to Managed Storage**.

### Step 2: Analyze Video
In the post-import dialog or **Video Workspace**, click **Start Analysis**. The 6-stage pipeline extracts 16kHz audio, transcribes speech with Faster-Whisper, detects visual scene boundaries, and samples key visual frames.

### Step 3: Discover AI Highlights
Open **AI Highlights** in the Video Workspace. Configure target clip duration (e.g. 15s–60s) and target count. Click **Start Discovery**. The engine evaluates speech turns, conversation context, audio energy, and scene boundaries to propose candidates with explainable scores.

### Step 4: Review and Trim
Review proposed clips in the preview player. Approve or reject moments. Use the manual boundary sliders to adjust start/end timestamps to sentence edges.

### Step 5: Reframe & Export
Click **Send to Smart Reframing** to convert 16:9 to vertical 9:16. Adjust subject crop tracking if needed. Then click **Send to Export** to render your finalized short via FFmpeg.
""",
    "next-video-workflow": """# Next Video Workflow & Project Isolation

When editing multiple source videos, ZezEdit ensures seamless switching without state pollution:

### Transitioning to Next Video
In any Video Workspace screen, click the **Next Video** button in the top header. A transition modal will appear showing:
- Recently modified source videos with analysis/shorts status.
- Resumable videos with approved shorts awaiting export.
- Option to import a new source video immediately.

### Automatic State Preservation
Before switching videos, ZezEdit:
1. Commits any uncommitted boundary trims or transcript corrections to SQLite.
2. Preserves all approved/rejected candidate statuses.
3. Keeps active background rendering jobs running in the Working Queue.
4. Restores the exact workspace tab and playback position when you return to a previous video.

### Strict Isolation
Each source video is linked to an independent project namespace. Candidate IDs, timeline tracks, and export revisions will never bleed into another video.
""",
    "timeline-editing-basics": """# Multi-Track Timeline & Clip Trimming

The **Timeline Editor** provides standard NLE editing capabilities for fine-tuning clips:

- **Track V1 (Video):** Primary video track where candidate shorts or source segments are placed.
- **Track A1 / A2 (Audio):** Synchronized dialogue and background audio tracks.
- **Track C1 (Captions):** Subtitle track populated automatically from Whisper speech segments.
- **Trimming:** Drag clip start and end edges with sub-frame precision.
- **Snapping:** Clips automatically snap to playhead positions and adjacent cut points.
- **Zoom & Navigation:** Zoom in/out of the timeline using the slider controls.
""",
    "post-import-decisions": """# Source Media Ingestion & Validation

When importing videos into ZezEdit:

1. **Integrity Validation:** FFprobe automatically probes the container, duration, video codec, audio sample rate, pixel format, and dimensions.
2. **Storage Layout:** Videos can be linked as **External Reference** (stays at current disk path) or copied into the project's `storage/projects/{project_id}/media/` directory.
3. **Proxy Generation:** For high-resolution files (4K/60fps), proxy files are generated at 480p to maintain smooth 60fps scrubbing on CPU.
""",
    "multistage-analysis": """# Multi-Stage Video Analysis Pipeline

ZezEdit runs a 6-stage video understanding pipeline:

1. **Stage 1 — Audio Extraction:** Demuxes audio into high-fidelity 16kHz mono 16-bit PCM WAV. Checks for silent tracks or missing channels.
2. **Stage 2 — Speech Recognition:** Faster-Whisper transcribes speech into text segments and word-level timestamps (`start`, `end`, `probability`).
3. **Stage 3 — Dialogue & Turn Detection:** Detects pauses and punctuation to cluster continuous conversational turns.
4. **Stage 4 — Scene Cut Detection:** PyAV content detector identifies scene transitions and saves JPEG thumbnail frames at each scene midpoint.
5. **Stage 5 — Frame Sampling:** Samples representative frames across every scene for visual inference.
6. **Stage 6 — Visual Understanding:** Queries local Ollama (`qwen3-vl:4b-instruct`) or deterministic heuristic fallbacks for frame description, motion, and luminance.
""",
    "highlight-scoring-engine": """# Explainable 9-Factor Highlight Scoring

ZezEdit avoids black-box "virality" guessing. Instead, it evaluates candidate moments against 9 transparent editorial criteria:

1. **Semantic Interest:** Key subject presence and topic relevance.
2. **Narrative Completeness:** Has a discernible setup, event, and payoff.
3. **Conversation Structure:** Complete sentences without truncated speech mid-thought.
4. **Visual Interest:** Scene changes, motion delta, and visual clarity.
5. **Audio Evidence:** Vocal projection, lack of background noise, speech clarity.
6. **Opening Clarity:** Strong initial hook within the first 3 seconds.
7. **Ending Completeness:** Natural cadence without sudden jarring cuts.
8. **Duration Suitability:** Closeness to optimal short duration (typically 20s–45s).
9. **Context Penalty:** Penalizes moments that require external references to understand.
""",
    "transcript-corrections": """# Non-Destructive Transcript Corrections

Automatic speech recognition sometimes mishears names or jargon:

- **Inline Correction:** Click on any transcript segment in the Analysis Workspace to edit text.
- **Original Preservation:** Original Whisper output is preserved in `transcript_segments`; corrections are stored in `transcript_corrections` with a foreign key reference.
- **Export Synchronization:** Corrected words are automatically embedded when generating `.srt`, `.vtt`, or burning captions into exported shorts.
""",
    "smart-reframing-engine": """# Smart Reframing & Subject Tracking

Transform horizontal 16:9 videos into vertical 9:16 shorts:

- **Target Ratios:** 9:16 (TikTok/Shorts/Reels), 1:1 (Square), 4:5 (Social Feed).
- **Tracking Algorithm:** OpenCV Haar cascade identifies human faces and prominent figures across scene intervals.
- **Trajectory Smoothing:** Trajectory generator applies moving-average smoothing to prevent erratic jerky camera movement.
- **Manual Keyframes:** Creators can override automatic crops with custom anchor points directly on the canvas.
""",
    "rendering-export-pipeline": """# FFmpeg Export Pipeline & Presets

Rendering exports use optimized FFmpeg profiles:

- **Video Codec:** `libx264` with `-preset veryfast` or `medium` for balanced CPU utilization and visual fidelity.
- **Audio Codec:** `aac` at 192kbps stereo 48kHz.
- **Burn-in Subtitles:** Dynamic ASS subtitle filter applied with styling (font, font size, stroke outline, primary color).
- **Verification:** Resulting MP4 files are validated with FFprobe to ensure duration, audio sync, and container integrity before being marked `completed`.
""",
    "working-queue-guide": """# Working Queue & Job Orchestration

All intensive operations run asynchronously via `JobOrchestrator`:

- **Job States:** `queued` → `running` → `completed` | `failed` | `cancelled` | `interrupted`.
- **Cancellation:** Click the **Cancel** button to stop active FFmpeg or analysis processes immediately.
- **Retry:** Failed jobs can be retried with one click.
- **Crash Recovery:** If the computer shuts down unexpectedly, in-flight jobs are recovered cleanly on backend restart without corrupting SQLite databases.
""",
    "resource-inspector-guide": """# CPU & Memory Resource Inspector

Monitor your hardware without switching applications:

- **Indicator:** The header status pill displays real-time CPU% and RAM%.
- **Hover Panel:** Hover over the indicator to reveal total CPU load, process CPU, total RAM, available RAM, and backend memory footprint.
- **Worker Slots:** Displays active and pending background jobs against the configured CPU concurrency limit.
- **Zero Overhead:** Metrics are sampled with bounded intervals, consuming negligible CPU.
""",
    "ai-providers-configuration": """# Configuring Ollama & Faster-Whisper

ZezEdit supports local offline AI providers:

### Ollama Setup
1. Install Ollama from [ollama.com](https://ollama.com).
2. Pull the vision model: `ollama pull qwen3-vl:4b-instruct`.
3. In ZezEdit, go to **AI Providers**, verify the URL (`http://127.0.0.1:11434`), and click **Test Connection**.

### Faster-Whisper
Faster-Whisper runs built-in on CPU using CTranslate2 and `int8` quantization. The `tiny` or `base` models download on first analysis and remain permanently cached in local storage.
""",
    "troubleshooting-guide": """# Troubleshooting: FFmpeg, Memory & AI Providers

Resolve common operational errors and system health warnings:

### 1. FFmpeg or FFprobe Not Detected
- **Symptom:** Yellow or red dependency badge in the top header.
- **Cause:** FFmpeg binaries are not located on system `PATH` or configured paths.
- **Fix:** Install FFmpeg via package manager (`winget install Gyan.FFmpeg`) or place binaries in your storage root. Navigate to **Studio Settings** to verify the path.

### 2. High Memory or CPU Usage
- **Symptom:** Resource Inspector shows >85% RAM utilization or slow scrubbing.
- **Cause:** High-bitrate 4K footage loaded without proxy playback.
- **Fix:** Enable **Proxy Generation** in the Media Library. Proxies render at 480p/720p with lightweight intra-frame codecs, reducing CPU load by 70%.
- **Job Limit:** In `config.json`, decrease `max_concurrent_jobs` from `2` to `1` on machines with limited core counts.

### 3. Ollama Offline or Connection Refused
- **Symptom:** Warning in AI Provider Manager: `Connection refused on http://127.0.0.1:11434`.
- **Cause:** Ollama service is stopped or running on an alternate port.
- **Fix:** Start Ollama from your desktop tray or terminal (`ollama serve`). ZezEdit will automatically fall back to deterministic CPU heuristics in the interim without aborting analysis.

### 4. Background Job Interrupted
- **Symptom:** Job status shows `interrupted` after system reboot.
- **Fix:** Open the **Working Queue**, locate the interrupted job, and click the **Retry** icon. The job resumes from the latest verified checkpoint without re-running completed stages.
""",
    "keyboard-shortcuts": """# Keyboard Shortcuts & Studio Navigation

Speed up your timeline and review workflows:

### Playback & Scrubbing
- `Space`: Play / Pause video playback
- `J`: Scrub backward (1x / 2x / 4x)
- `K`: Pause playback
- `L`: Scrub forward (1x / 2x / 4x)
- `Left Arrow`: Step backward 1 frame
- `Right Arrow`: Step forward 1 frame
- `Home` / `End`: Jump to beginning or end of clip

### Timeline Editing
- `S`: Split active clip at playhead position
- `[`: Set candidate / clip in-point
- `]`: Set candidate / clip out-point
- `Ctrl + Z`: Undo timeline action
- `Ctrl + Shift + Z`: Redo timeline action
- `+` / `-`: Zoom in / out on timeline tracks

### Navigation
- `Esc`: Close floating Resource Inspector or modal dialogs
""",
    "storage-directories": """# Storage Layout, File Boundaries & Retention

ZezEdit organizes all project data within a deterministic, sandboxed storage directory structure:

### Storage Directory Map
- `/db/`: SQLite transactional database (`zezedit.db`, WAL, and SHM indices).
- `/media/`: Imported and managed original video files.
- `/proxies/`: Lightweight H.264 480p/720p scrubbing proxies.
- `/thumbnails/`: Frame thumbnails sampled at scene cuts.
- `/analysis/`: Extracted 16kHz WAV audio, speech JSON segments, and face tracking metadata.
- `/timelines/`: Multi-track sequence EDL definitions and clip history.
- `/shorts/`: Approved candidate configurations and portrait crop keyframes.
- `/exports/`: Final rendered MP4 short videos and burned-in captions.
- `/temp/`: Temporary render segments and FFmpeg pipes (cleaned automatically).
- `/backups/`: Automated hourly SQLite database snapshots.
- `/logs/`: Structured worker process output logs.

### Non-Destructive Ingestion Policy
Importing a video never modifies the source file on disk. When external referencing is selected, ZezEdit stores read-only pointers.
""",
}


@router.get("/categories", response_model=List[DocCategoryDTO])
def list_doc_categories() -> List[DocCategoryDTO]:
    """List all documentation categories and article counts."""
    return DOC_CATEGORIES


@router.get("/articles", response_model=List[DocArticleDTO])
def list_doc_articles(
    category: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
) -> List[DocArticleDTO]:
    """List documentation articles with optional category and search filtering."""
    results = DOC_ARTICLES

    if category:
        results = [a for a in results if a.category == category]

    if query:
        q = query.lower().strip()
        results = [
            a for a in results
            if q in a.title.lower() or q in a.summary.lower() or any(q in t.lower() for t in a.tags)
        ]

    return results


@router.get("/articles/{article_id}", response_model=DocArticleDetailResponse)
def get_doc_article(article_id: str) -> DocArticleDetailResponse:
    """Retrieve full markdown content and metadata for a documentation article."""
    article = next((a for a in DOC_ARTICLES if a.id == article_id), None)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found")

    content = DOC_CONTENT.get(article_id, f"# {article.title}\n\n{article.summary}")

    # Find related articles in same category
    related = [a.id for a in DOC_ARTICLES if a.category == article.category and a.id != article.id][:3]

    return DocArticleDetailResponse(
        id=article.id,
        title=article.title,
        category=article.category,
        summary=article.summary,
        markdown_content=content,
        tags=article.tags,
        related_article_ids=related,
        updated_at="2026-11-12T06:30:00Z",
    )
