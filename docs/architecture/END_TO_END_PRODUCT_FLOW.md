# ZEZEDIT 2.0 — END-TO-END PRODUCT FLOW & WORKFLOW MAPPING
## Architecture & System Integration Specification

**Version:** 2.0.0-alpha.1  
**Authoritative Path:** `docs/architecture/END_TO_END_PRODUCT_FLOW.md`  
**Date:** 2026-11-13  
**Project:** `D:\ZezEdit`

---

## 1. Complete Product Workflow Diagram

```
                 [ USER OPENS ZEZEDIT ]
                           ↓
             [ SHORT VIDEO GENERATOR LIBRARY ]
                           ↓
              (Upload MP4 / Drag-and-Drop)
                           ↓
              [ UPLOAD / VALIDATION ENGINE ]
                           ↓
               [ OPEN VIDEO DASHBOARD ]
                           ↓
              [ DEEP SOURCE VIDEO ANALYSIS ]
              (Scenes, Whisper, Frames, Audio)
                           ↓
               [ SAVE VIDEO INTELLIGENCE ]
             (Persistent Analysis Cache / DB)
                           ↓
            [ SHORT VIDEO GENERATOR ENGINE ]
          (Quantity, Creative Direction, Ratios)
                           ↓
             [ DISCOVER SHORT CANDIDATES ]
          (Multimodal Scoring & Natural Cuts)
                           ↓
                 [ PREVIEW CANDIDATES ]
                           ↓
          [ EDIT SELECTED CLIP (OPTIONAL) ]
       (Trimming, Aspect Ratio, Framing Modes)
                           ↓
                [ RENDER SINGLE / BATCH ]
            (FFmpeg 15-Stage Modular Engine)
                           ↓
             [ OUTPUT VERIFICATION GATE ]
             (FFprobe Stream & Decode Test)
                           ↓
            [ PLAY / DOWNLOAD / DELETE MP4 ]
               (Generated Videos Archive)
                           ↓
               [ GENERATE MORE SHORTS ]
              (Persistent Novelty Ledger:
            Reuses Analysis, Filters Duplicates)
```

---

## 2. Stage-by-Stage Component, API, Service & Record Mapping

| Stage # | Workflow Step | Frontend Component | Backend API Endpoint | Backend Service | Primary Database Records | Background Job Type | Error & Fallback Behavior |
|---|---|---|---|---|---|---|---|
| **1** | Open Library & List Videos | `ShortVideoGeneratorLibrary.tsx` | `GET /api/v1/media` | `MediaService.list_media_assets` | `media_assets` | None | Shows empty state if zero assets. |
| **2** | Upload / Ingest Video | `ShortVideoGeneratorLibrary.tsx` (Drag/Drop file picker) | `POST /api/v1/projects/{pid}/media/upload` | `MediaService.register_stored_media` | `media_assets`, `jobs` | `video_upload` | Client-side MIME check; FFprobe container validation; rejects non-video files cleanly. |
| **3** | Open Video Dashboard | `VideoEditDashboard.tsx` (`/videos/:assetId`) | `GET /api/v1/media/{id}`, `GET /api/v1/analysis` | `MediaService.get_media_asset` | `media_assets`, `analysis_runs` | None | 404 alert and redirect back to library if asset is missing. |
| **4** | Deep Source Analysis | `VideoEditDashboard.tsx` (Tab: "Video Analysis Details" or Banner) | `POST /api/v1/projects/{pid}/analysis/start` | `UnifiedAnalysisPipeline`, `JobOrchestrator` | `analysis_runs`, `jobs`, `video_scenes`, `transcript_segments`, `extracted_frames` | `video_analysis` | Resume from cached stages; Faster-Whisper VAD fallback; graceful degradation on audio-less media. |
| **5** | Save Video Intelligence | Automatic upon pipeline completion | `GET /api/v1/projects/{pid}/analysis/{id}/telemetry` | `AnalysisStorage`, `AnalysisTelemetry` | `analysis_runs` (status='completed') | `video_analysis` | Deterministic `size:mtime:hash64k` signature prevents redundant re-analysis. |
| **6** | Configure Short Generation | `VideoEditDashboard.tsx` (Tab: "Short Video Generator") | `POST /api/v1/projects/{pid}/highlights/generate` | `HighlightDiscoveryService` | `generation_runs`, `shorts_candidates` | `candidate_generation` | Validates clip count (1-20), aspect ratio, duration window; loads saved analysis in ~0.12s. |
| **7** | Preview Candidates | `VideoEditDashboard.tsx` (Tab: "Generated Shorts") | `GET /api/v1/projects/{pid}/highlights?media_asset_id={id}` | `HighlightDiscoveryService.list_highlights` | `shorts_candidates` | None | Displays attractiveness score breakdown, duration, boundaries, and transcript preview. |
| **8** | Edit Candidate Clip | `CandidateClipEditorModal.tsx` | `POST /api/v1/projects/{pid}/highlights/{id}/edit` | `ClipEditingService` | `candidate_clip_edits` | None | Non-destructive edits: preserves original candidate boundaries, saves trim and crop offsets in SQLite. |
| **9** | Submit Render (Single/Batch) | `VideoEditDashboard.tsx` ("Render MP4" or sticky batch bar) | `POST /api/v1/projects/{pid}/exports/render` or `/exports/batch` | `ExportService`, `JobOrchestrator` | `exports`, `jobs` | `export_render` | Resolves clip edits, passes `media_asset_id` to `JobOrchestrator`, runs FFmpeg filter graph. |
| **10** | Output Verification Gate | Backend Automatic | Internal within `ExportService.execute_render_job` | `OutputValidator` | `exports.validation_status` | Part of `export_render` | FFprobe stream checks + FFmpeg null-sink decode test. Marks `failed` if corrupt or truncated. |
| **11** | Play / Download MP4 | `VideoEditDashboard.tsx` (Tab: "Generated Videos") | `GET /api/v1/projects/{pid}/exports/{id}/video` & `/download` | `FastAPI StreamingResponse` & `FileResponse` | `exports` | None | HTTP 206 byte-range streaming for instant playback and seeking; direct attachment download. |
| **12** | Generate More Shorts | `VideoEditDashboard.tsx` ("Generate More Shorts" button) | `POST /api/v1/projects/{pid}/highlights/generate-more` | `HighlightDiscoveryService` (Novelty Ledger) | `generation_runs`, `shorts_candidates`, `candidate_novelty_history` | `candidate_generation` | Reuses source analysis; evaluates temporal overlap & transcript similarity; honestly detects exhaustion. |
| **13** | Process Monitoring | `ProcessesManagerView.tsx` (`/processes`) | `GET /api/v1/processes`, `POST /processes/{id}/cancel` | `JobOrchestrator` | `jobs` | All jobs | Real-time progress %, stage description, source video title, graceful subprocess cancellation & retry. |
| **14** | Storage Reclamation | `SettingsManager.tsx` (Tab: "Storage & Data") | `GET /api/v1/storage/cleanup-preview`, `POST /storage/clear-all-user-data` | `StorageReclamationService` | All tables except migrations & settings | `storage_cleanup` | Sweeps managed directories, VACUUMs SQLite WAL, safely preserves external files and core software. |

---

## 3. Verified System Invariants

1. **Source Immutability:** Source video files on disk are strictly read-only and never modified, overwritten, or relocated.
2. **Analysis Reusability:** Source video intelligence is computed once and persisted across sessions. Subsequent generation batches query SQLite and JSON checkpoints in milliseconds.
3. **Candidate Non-Repetition:** The novelty ledger tracks all generated candidates by temporal window, IoU overlap, and transcript token similarity.
4. **Export Isolation:** Each render job executes in a temporary isolated scratch folder before atomic publication to `storage/exports/{project_id}/`.
5. **Output Verification:** No export is marked `completed` without passing strict FFprobe stream and FFmpeg decode validation.
