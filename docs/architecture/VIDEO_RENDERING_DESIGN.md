# ZezEdit 2.0 — Video Rendering & Export Pipeline Design Specification

## 1. Architectural Overview
This specification details the production pipeline for transforming discovered and edited video candidates into verified, playable short MP4 videos.

```
+---------------------------------------------------------------------------------------------------------+
|                                           VideoEditDashboard.tsx                                        |
|  [Select Candidates] -> [Edit Clip Modal (Trim, Frame, Track)] -> [Render Single / Batch Render (N)]    |
+---------------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------------+
|                                    Backend REST API: /exports/render & /batch                           |
|  - Validates source video exists on disk                                                                |
|  - Resolves CandidateClipEdit bounds (edited_start_time, edited_end_time, aspect_ratio, manual_crop_*)   |
|  - Enqueues JobRecord with media_asset_id and priority in JobOrchestrator                               |
|  - Creates unvalidated record in `exports` table                                                        |
+---------------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------------+
|                                  ExportService: 15-Stage FFmpeg Pipeline                                |
|  1. validating_request     6. validating_bounds      11. processing_audio (AudioPipeline)              |
|  2. loading_candidate      7. preparing_scratch      12. rendering_video (FFmpeg Subprocess + Progress) |
|  3. resolving_media        8. building_filtergraph   13. validating_output (OutputValidator)           |
|  4. resolving_framing      9. compiling_crop         14. publishing_export (Atomic Move)               |
|  5. resolving_tracking    10. generating_captions    15. completed (Update DB + Job Record)             |
+---------------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------------+
|                                OutputValidator (Mandatory Quality Gate)                                 |
|  - Checks container integrity and non-zero byte size                                                    |
|  - FFprobe: stream exists, H.264 video codec, AAC audio codec, target dimensions & duration            |
|  - FFmpeg null-sink decode test: verifies entire video decodes without fatal corruptions                |
+---------------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------------+
|                                  Generated Videos Library (Tab 3 in Dashboard)                          |
|  - Displays completed MP4 cards with playable in-browser HTML5 video player                             |
|  - Seek, pause, download MP4, delete output file, and re-render                                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Extended Preset Catalog

All standard aspect ratios from Short Video Generator will be supported natively in `STANDARD_EXPORT_PRESETS`:

| Preset ID | Ratio | Dimensions | Video Bitrate | Audio Bitrate | Target Platform |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `shorts_reels_9_16` | 9:16 | 1080x1920 | Auto (CRF 22) | 128 kbps AAC | YouTube Shorts, TikTok, Instagram Reels |
| `square_1_1` | 1:1 | 1080x1080 | Auto (CRF 22) | 128 kbps AAC | Instagram Feed, LinkedIn, Square Video |
| `landscape_16_9` | 16:9 | 1920x1080 | Auto (CRF 22) | 128 kbps AAC | YouTube Desktop, Widescreen Monitors |
| `portrait_4_5` | 4:5 | 1080x1350 | Auto (CRF 22) | 128 kbps AAC | Instagram Portrait Feed |
| `standard_4_3` | 4:3 | 1440x1080 | Auto (CRF 22) | 128 kbps AAC | Classic TV / Tablet Video |
| `tall_3_4` | 3:4 | 1080x1440 | Auto (CRF 22) | 128 kbps AAC | Portrait Tablets & Feeds |

---

## 3. Candidate Clip Edit Integration

When an export request arrives for `candidate_id`:
1. `ExportService` queries `candidate_clip_edits` for that candidate.
2. If an edit record exists:
   - `clip_start = edited_start_time`
   - `clip_end = edited_end_time`
   - `preset_id = resolved from edited aspect_ratio` (or explicit request)
   - `manual_crop_x_pct`, `manual_crop_y_pct`, `manual_crop_zoom` are used to generate custom crop coordinates if `framing_mode == 'manual'`.
3. If no edit record exists:
   - Falls back to `shorts_candidates.start_time` and `shorts_candidates.end_time`.

---

## 4. Batch Export Execution & Concurrency

1. When multiple candidates are selected:
   - A batch request is submitted to `POST /api/v1/projects/{pid}/exports/batch`.
   - Each candidate is scheduled with a linked job in `JobOrchestrator`.
   - Concurrency is throttled to `max_concurrent_jobs` (default: 1 on CPU-first systems).
   - Render jobs are queued and executed sequentially by worker workers without overloading CPU or RAM.
2. In the UI:
   - Candidate cards show checkboxes for batch selection.
   - A sticky bottom action bar appears when $\ge 1$ candidates are selected:
     - Count of selected items.
     - "Select All" / "Clear Selection".
     - "Render Selected (N)" button.
     - Real-time batch progress modal showing status per clip.

---

## 5. Output Verification & Safe Publishing

1. **Scratch Isolation:**
   - FFmpeg writes exclusively to `storage/temp/job_{job_id}/render_scratch.mp4`.
2. **OutputValidator Testing:**
   - Container probe (`ffprobe`).
   - Video stream validation (`v:0`).
   - Dimension validation (within $\pm 2$ px due to macroblock rounding).
   - Duration validation (within $\pm 0.75$ s of requested interval).
   - Full decoding check (`ffmpeg -v error -i <file> -f null -`).
3. **Atomic Move:**
   - Verified file moved to `storage/exports/{project_id}/{filename}`.
   - If a collision occurs, a timestamp suffix is appended.
4. **Failure Cleanup:**
   - If any step fails, `temp/job_{job_id}/` is completely wiped via `shutil.rmtree`.
   - The job is marked `failed` and the export record updated with `error_message`.
