# ZezEdit 2.0 — Media Storage & Processing Pipeline

## 1. Storage Separation & Source Immutability

All binary media lives strictly inside configured `ZEZEDIT_STORAGE_ROOT`, separated by lifecycle and ownership:

| Subdirectory | Purpose | Mutable? | Deletion / Cleanup Policy |
|---|---|---|---|
| `media/` | Original imported video & audio assets | **NO (Immutable)** | Explicit user-confirmed deletion only; never altered or overwritten |
| `proxies/` | Low-bitrate H.264 480p proxies for smooth timeline scrubbing | Derived | Regenerable; cleaned only on project deletion or explicit user storage purge |
| `thumbnails/` | JPEG cover frames & timeline scrub strips | Derived | Regenerable per asset/short |
| `analysis/` | Cached scene JSON, Whisper transcripts, tracking telemetry JSON | Derived | Checkpoint artifacts per project |
| `timelines/` | Exported timeline sequence JSON backups | Project Data | Preserved with project |
| `shorts/` | Rendered Shorts & non-destructive revisions (`{id}.mp4`, `{id}_rev2.mp4`) | User Outputs | Never overwritten; explicit confirmation to delete |
| `exports/` | Final 16:9 / 9:16 / 1:1 timeline exports | User Outputs | Never overwritten silently |
| `temp/` | Ephemeral FFmpeg/Whisper scratch (`temp/jobs/{job_id}/`) | Scratch | Strictly owned by `job_id`; purged when job completes/fails/cancels |
| `backups/` | SQLite pre-migration & user-triggered zip/db snapshots | Archive | Strictly distinct from working state |
| `logs/` | Rotating app logs + per-job logs | Diagnostics | Size-capped rolling logs |
| `db/` | SQLite WAL files (`zezedit.db`, `-wal`, `-shm`) | System State | Snapshotted before migrations |

---

## 2. Large-File (1–2 GB+) Streaming Pipeline (CPU-First)

To handle 1–2 GB+ video files safely within 20 GB RAM without OOM or UI freezes:
1. **No Full-Video RAM Buffering:** Never decode an entire video into `numpy` arrays in memory.
2. **Metadata Probe First:** `ffprobe -v quiet -print_format json -show_format -show_streams` inspects dimensions, codecs, SAR/DAR, rotation tags, audio layout, and duration in milliseconds.
3. **Chunked / Sampled Frame Extraction:**
   - **Scene Detection & Tracking:** OpenCV reads sampled frames or FFmpeg extracts downscaled (`640x360`) sparse frames via pipe/sequential iteration rather than caching thousands of 1080p frames in RAM.
   - **Audio Extraction:** Single-channel `16kHz PCM WAV` extracted to `temp/jobs/{job_id}/audio.wav` via `ffmpeg -vn -ac 1 -ar 16000` for CPU Faster-Whisper (`int8` compute type recommended on i3-1220P).
4. **Edit Proxies:** Long 1080p/4K clips generate a lightweight `480p` fast-keyframe MP4 proxy (`-g 15 -preset veryfast -threads 4`) so HTML5 `<video>` timeline scrubbing in the browser stays responsive while final exports still render directly from the original immutable `media/` source.

---

## 3. Smart Reframing & Portrait Rendering Architecture

Preserving verified architectural solutions from historical Milestone 13M.12–13 (`milestone_13m12_verification_report.md`):

### Framing Strategy Selection
- **Dynamic Subject Tracking (`smart_crop`):** Primary portrait mode filling full 1080x1920 height without black bars or small horizontal strips.
- **Two-Person Dialogue Joint Framing:** Evaluates joint bounding midpoint (`group_cx, group_cy`) keeping both speakers inside the 9:16 window rather than jumping erratically or falling back prematurely to blur padding.
- **Blur-Fill Fallback Threshold:** Reserved strictly for user selection or extreme multi-subject wide spreads (>65% frames exceeding span thresholds); when active, scales foreground cleanly (`scale=1080:-2`) over blurred backdrop.

### Authoritative Crop Math & Preview Parity
- One deterministic function (`evaluate_crop_at_timestamp`) computes `(crop_x, crop_y, crop_w, crop_h)` from:
  1. Validated user **Manual Override Keyframes** (highest precedence, scene-segment isolated)
  2. Smoothed **Automatic Tracking Trajectory** (EMA smoothed + velocity-clamped, snapped cleanly at scene cuts without dragging pan across cuts)
  3. **Safe Center Fallback**
- Both the **Frame Preview API** (rendering JPEG crop box overlays) and the **FFmpeg Filtergraph Compiler** consume this exact function, ensuring 100% WYSIWYG mathematical parity.
- **Non-Destructive Revisions:** Saving manual overrides renders `{short_id}_rev{N}.mp4` + `{short_id}_rev{N}_diagnostics.json` alongside revision 1 so users can compare or roll back anytime.

---

## 4. Final Rendering & Output Validation

Every export job runs two mandatory stages:
1. **Deterministic FFmpeg Execution:**
   - Subprocess invoked via explicit `argv` list (never `shell=True`), bounded with `-threads 4`, `-movflags +faststart`, `-pix_fmt yuv420p`, `libx264`, and `aac`.
   - Writes to `storage/temp/jobs/{job_id}/output.mp4` first, then atomically moves/renames to target `exports/` or `shorts/` path only after validation passes.
   - Refuses to overwrite an existing output path unless explicit overwrite/new-revision confirmation is supplied.
2. **Post-Render FFprobe Verification Gate:**
   - Verifies file exists and `size > 0`.
   - Verifies decoded duration is within tolerance of requested timeline/clip duration.
   - Verifies exact target resolution (`1080x1920`, `1920x1080`, `1080x1080`) and expected audio presence.
