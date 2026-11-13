# ZezEdit 2.0 — Rendering Architecture & Verification Audit

**Project Root:** `D:\ZezEdit`  
**Date:** 2026-11-13  
**Status:** COMPLETE AUDIT FOR SESSION 6C  

---

## 1. Executive Summary

This audit independently inspects the current rendering architecture, backend export pipeline, clip editing services, reframing/tracking integrations, process orchestration, and frontend dashboards to determine what is already functional and what gaps must be bridged in Session 6C.

The core conclusion: **ZezEdit has a powerful 15-stage backend export engine (`export_service.py`), FFmpeg execution pipeline with progress polling, ASS caption generator, and output validator (`output_validator.py`). However, there are critical disconnections between candidate editing/discovery and the final rendering and playback experience:**
1. Discovered candidates have an "Export MP4" button in `VideoEditDashboard.tsx` that triggers `submitExportRender`, but:
   - Discovered candidate edits from `candidate_clip_edits` (trim timestamps, framing offsets, and aspect ratios) are not automatically resolved by `export_service.py` unless explicitly specified.
   - The user cannot select multiple candidates in `VideoEditDashboard.tsx` and click "Render Selected" (Batch Export is only hooked in tests and the legacy timeline view).
   - Generated MP4 outputs do not appear in a dedicated, playable "Generated Videos" section in the video dashboard; the user has no direct UI to play, pause, seek, download, or re-render their completed MP4s within that video's workspace.
2. Preset support in `export.py` only defines `9:16`, `16:9`, and `1:1`. The new options (`4:5`, `4:3`, `3:4`) must be supported in the preset dictionary.
3. The Process Manager (`WorkingQueueView.tsx`) tracks jobs, but `export_render` jobs must link `media_asset_id` so they appear scoped to the video.

---

## 2. Answers to the 15 Audit Questions

| # | Question | Status | Architectural Findings & Evidence |
| :--- | :--- | :---: | :--- |
| **1** | **Can the application render a candidate directly into an MP4?** | **Fully Implemented** | `POST /projects/{pid}/exports/render` and `export_service.py` execute an FFmpeg subprocess encoding H.264 video with faststart MP4 container. |
| **2** | **Does it use the candidate's actual source timestamps?** | **Partially Implemented** | `export_service.py` reads `shorts_candidates.start_time` and `end_time`. **Gap:** If the candidate was trimmed via `candidate_clip_edits`, `export_service` currently ignores the edited bounds and uses the unedited candidate row. |
| **3** | **Does it apply the requested aspect ratio?** | **Partially Implemented** | `STANDARD_EXPORT_PRESETS` supports `9:16`, `16:9`, and `1:1`. **Gap:** Candidate selection allows `4:5`, `4:3`, and `3:4`, which fall back to centered `9:16` because presets are missing. |
| **4** | **Does it use actual subject tracking data?** | **Fully Implemented** | `ReframingService` and `reframing_renderer.py` load bounding boxes from `reframing_plans` / `reframing_revisions` and compile dynamic `crop=w:h:x:y` expressions. |
| **5** | **Does it support crop and reframing?** | **Fully Implemented** | `build_crop_filter_expression()` computes crop width, height, and keyframe interpolation curves. |
| **6** | **Does it preserve or process audio correctly?** | **Fully Implemented** | `AudioPipeline` (`audio_pipeline.py`) inspects source audio, configures AAC 128k, applies volume scaling, optional fade-in/out, and EBU R128 loudness normalization. Handles silent video safely. |
| **7** | **Does it support subtitles or captions?** | **Fully Implemented** | `CaptionEngine` (`caption_engine.py`) compiles Whisper transcript segments into ASS subtitle files (`word_highlight`, `standard`) and burns them in via `-vf ass=captions.ass`. |
| **8** | **Can users edit the clip before rendering?** | **Partially Implemented** | `CandidateClipEditorModal.tsx` and `clip_editing_service.py` exist and save trim/framing in `candidate_clip_edits`. **Gap:** The render trigger doesn't pass the edited parameters to `submit_export_job`. |
| **9** | **Can multiple candidates be rendered in one batch?** | **Backend-Only** | Backend endpoint `POST /projects/{pid}/exports/batch` exists and is tested. **Gap:** `VideoEditDashboard.tsx` lacks multi-select checkboxes and a "Render Selected" action bar. |
| **10** | **Are outputs stored in a predictable managed location?** | **Fully Implemented** | Rendered MP4s are saved to `storage/exports/{project_id}/{clean_title}_{aspect}_{id}.mp4` under `storage_root`. |
| **11** | **Are output records linked to the source video and candidate?** | **Fully Implemented** | `exports` table contains `media_asset_id`, `candidate_id`, `project_id`, and `render_job_id` foreign keys. |
| **12** | **Does the Process Manager display render jobs?** | **Partially Implemented** | Process Manager lists `export_render` jobs. **Gap:** `submit_export_job` didn't pass `media_asset_id` to `create_job()`, so it did not associate with the video title in the Process Manager table. |
| **13** | **Can a user cancel a render safely?** | **Fully Implemented** | `_ACTIVE_RENDER_PROCESSES` tracks Popen instances; `cancel_export_render` kills the FFmpeg process and unlinks temp files. |
| **14** | **Are incomplete files removed after failed renders?** | **Fully Implemented** | `execute_render_job` renders to `temp/job_{job_id}/render_scratch.mp4`. If FFmpeg fails or validation fails, `shutil.rmtree(job_temp_dir)` deletes all scratch files. Only verified MP4s are moved to `exports/`. |
| **15** | **Are completed outputs verified as valid playable videos?** | **Fully Implemented** | `OutputValidator` (`output_validator.py`) inspects container, video codec, audio codec, resolution, and duration with FFprobe, and executes an FFmpeg decoding test (`-f null`). |

---

## 3. Capability Classification Summary

### Fully Implemented and Verified
- **FFmpeg Execution Engine:** Out-of-process subprocess rendering with faststart MP4.
- **Output Verification:** Mandatory FFprobe and null-sink decoding checks before publishing.
- **Audio Pipeline:** Normalization, volume scaling, fade filters, silent video handling.
- **Captions Engine:** Styled ASS generation and filtergraph burn-in.
- **Cancellation & Cleanup:** Process killing and temporary directory cleanup on failure.
- **Streaming Delivery:** HTTP 206 Partial Content byte-range video streaming endpoint.

### Partially Implemented (Require Enhancement in Session 6C)
- **Candidate Edit Linkage:** Connect `candidate_clip_edits` table to `export_service.py` so trimmed timestamps and framing overrides are rendered.
- **Aspect Ratio Presets:** Add `4:5`, `4:3`, and `3:4` to `STANDARD_EXPORT_PRESETS` in `export.py`.
- **Process Manager Linkage:** Pass `media_asset_id` when creating `export_render` jobs.

### Backend-Only / Missing in UI
- **Batch Selection & Render:** Multi-select candidates in `VideoEditDashboard.tsx` and submit batch export.
- **Generated Videos Library:** Dedicated tab/section in `VideoEditDashboard.tsx` listing completed MP4s with playable video player, seek, download, and delete actions.
- **Candidate Render Status Indicators:** Clear state badges (Discovered, Selected, Rendering, Rendered, Failed) on candidate cards.
