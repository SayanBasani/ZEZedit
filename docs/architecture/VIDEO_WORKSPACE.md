# ZezEdit 2.0 — Video Workspace Architecture
**Specification: Video-Centric Editing Architecture & Context Flow**  
**Target:** `D:\ZezEdit`  
**Milestone:** 11  
**Status:** Approved Architecture

---

## 1. Overview

In professional editing software, a media asset is not an isolated database record viewed on a separate page; it is the fundamental editing subject. 

The **Video Workspace** (`VideoWorkspace.tsx`) is the central editing hub for a specific video asset within an active project. When a video is selected—either directly from the Media Library or immediately following ingestion via the Post-Import Action Screen—the application transitions into the Video Workspace with full context preservation.

```
Project Context (selectedProjectId)
   └── Media Asset Context (selectedMediaAsset)
          └── Video Workspace (activeWorkspaceTab)
                 ├── 1. Overview (Playback, Metadata, Status, Summary)
                 ├── 2. Analysis (Transcription, Scenes, Visual AI trigger & logs)
                 ├── 3. Transcript (Searchable Whisper segments with click-to-seek)
                 ├── 4. Scenes (Visual cuts, keyframe thumbnail filmstrip)
                 ├── 5. AI Highlights (Scored moments, viral ranking, candidate approval)
                 ├── 6. Smart Reframing (9:16 portrait composition, dynamic crops)
                 ├── 7. Shorts & Export (Aspect ratio presets, subtitles, render queue)
                 ├── 8. Timeline Editor (Multi-track editing, trims, AI text editing)
                 └── 9. Character Studio (Facial recognition, character identity library)
```

---

## 2. Context & State Flow

### A. State Hierarchy
- **Level 1: Global Application State (`App.tsx`)**
  - `projects: ProjectItem[]`
  - `selectedProjectId: string`
  - `selectedMediaAsset: MediaAssetItem | null`
  - `activeTab: NavSection` (`dashboard` | `projects` | `media` | `workspace` | `settings` | `diagnostics`)
  - `activeWorkspaceSubTab: VideoWorkspaceSubTab`

- **Level 2: Video Workspace State (`VideoWorkspace.tsx`)**
  - Props: `projectId: string`, `asset: MediaAssetItem`, `onBack: () => void`, `activeSubTab?: string`
  - Internal state:
    - Active sub-tab selection
    - Shared video player currentTime / duration / playing state
    - Current analysis run data (loaded from `/api/v1/projects/{pid}/media/{mid}/analysis/runs`)
    - Analysis trigger status & real job polling
    - Transcripts, scenes, and visual observations

### B. Shared Media URL & Thumbnail Resolution
- **Stream/Preview URL**:
  - If proxy exists and is ready: `/api/v1/projects/{pid}/media/{mid}/proxy`
  - Otherwise raw media stream: `/api/v1/projects/{pid}/media/{mid}/stream`
- **Thumbnail URL**:
  - `/api/v1/projects/{pid}/media/{mid}/thumbnail`

---

## 3. Sub-Workspace Breakdown

### 1. Overview Tab
- **Video Player**: HTML5 video preview with scrub controls, timecode display, play/pause, volume, and playback speed.
- **Media Specs Card**: Filename, duration formatted (`MM:SS.ms`), resolution, container format, video codec, audio channels, sample rate, bit rate, file size, storage type (`Managed` vs `External`).
- **Processing Matrix**: Badges for Thumbnail Generated, Proxy Status, Transcription Status, Scene Cuts Detected, Highlights Computed, Reframing Ready.
- **Quick Actions**: "Run Full Analysis", "Discover Highlights", "Open Timeline", "Quick 9:16 Export".

### 2. Analysis Tab
- Form to configure analysis options:
  - Whisper Speech-to-Text (model size, language)
  - Scene Cut Detection (threshold)
  - Visual Understanding (sampling interval, Ollama model if available)
- Real-time persistent Job Orchestrator progress bar (`job_...` status polling).
- Live execution log console.

### 3. Transcript & Audio Tab
- Whisper transcript segments with millisecond start/end timestamps.
- Interactive search filter.
- Click-to-seek: clicking any transcript segment automatically moves the video player's playhead to that exact timestamp.
- Speaker turn tags (if diarization / speaker turns available).

### 4. Scenes Tab
- Visual filmstrip of detected scene cuts.
- Scene start/end timecodes, duration, and keyframe thumbnail.
- Clicking a scene jumps the player to the scene start.

### 5. AI Highlights Tab
- Embedded `HighlightsWorkspace` scoped to the current active asset.
- Lists scored Shorts candidates with overall score, engagement score, humor, visual quality, and explanation.
- Boundary trimmer for candidate adjustment.
- Candidate approval and direct send-to-reframing.

### 6. Smart Reframing Tab
- Embedded `ReframingWorkspace` scoped to the current active asset.
- Portrait 9:16 preview canvas with bounding box overlays for detected faces/subjects.
- Mode switcher: Single Subject, Two-Person Split, Group Framing.
- Keyframe crop adjustment slider.

### 7. Shorts & Export Tab
- Embedded `ExportStudio` scoped to the current active asset.
- Output presets: 9:16 Vertical Shorts (1080x1920), 1:1 Square, 16:9 Landscape.
- Subtitle burnt-in styling (font size, color, animation).
- Audio loudness normalization (EBU R128).
- Real FFmpeg export job trigger with live progress bar and downloadable output video.

### 8. Timeline Editor Tab
- Embedded `TimelineEditor` initialized with the active project's media assets and pre-populated with active asset clips.
- Multi-track timeline (Video, Overlay, Audio tracks).
- Clip trimming, splitting, ripple delete.
- Natural language AI Editor integration.

### 9. Character Studio Tab
- Embedded `CharacterStudio` scoped to the current active asset.
- Face clusters discovered in the video.
- Name assignment and Character Library persistence.

---

## 4. Post-Import Action Flow

When any file finishes uploading or importing via `MediaLibraryView.tsx`:
1. The `PostImportModal` is triggered immediately with the newly imported asset's details.
2. The modal presents four clear choices:
   - **Analyze Video Now**: Opens analysis config modal / triggers analysis and transitions into `VideoWorkspace` (Analysis tab).
   - **Open Video Workspace**: Transitions directly to `VideoWorkspace` (Overview tab) without running heavy compute.
   - **Import Another Video**: Closes modal and opens file picker for additional ingestion.
   - **Back to Media Library**: Closes modal and stays in the asset grid.
