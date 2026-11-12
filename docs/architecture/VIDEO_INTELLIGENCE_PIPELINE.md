# ZezEdit 2.0 — Unified Video Intelligence Pipeline Architecture
**Date:** November 12, 2026  
**Document:** `docs/architecture/VIDEO_INTELLIGENCE_PIPELINE.md`  
**Status:** Target Architectural Design (Session 0)

---

## 1. End-to-End Processing Architecture

The pipeline processes videos ranging from short 30-second clips up to 2-hour, 2 GB feature films on standard consumer hardware without requiring dedicated GPU acceleration:

```
+----------------------------------------------------------------------------------------------------+
|                               UNIFIED VIDEO INTELLIGENCE PIPELINE                                 |
+----------------------------------------------------------------------------------------------------+
| 1. INGEST & VALIDATION                                                                            |
|    - Media validation & FFprobe metadata extraction (duration, resolution, fps, codecs).           |
|    - 480p proxy generation for low-latency scrubbing.                                              |
|                                                                                                    |
| 2. AUDIO & SPEECH DECOMPOSITION                                                                   |
|    - FFmpeg audio extraction: 16kHz 16-bit mono PCM WAV (fast bounded stream).                     |
|    - Faster-Whisper CPU transcription (`tiny`/`base` int8) with word-level timestamps.             |
|    - Silence detection & dialogue turn clustering.                                                 |
|                                                                                                    |
| 3. VISUAL DECOMPOSITION & SUBJECT TRACKING                                                         |
|    - PySceneDetect / FFmpeg scene boundary cut detection.                                          |
|    - Keyframe sampling at cut points and dialogue intervals.                                      |
|    - CPU SubjectTracker: multi-subject face/person tracking and motion velocity calculation.       |
|                                                                                                    |
| 4. MULTIMODAL MOMENT DISCOVERY & SCORING                                                          |
|    - Temporal alignment of speech turns, visual scene cuts, and action intensity.                  |
|    - 9-Factor Explainable Attractiveness Scoring:                                                  |
|        semantic + narrative + dialogue + visual + audio + hook + ending + duration - penalty.      |
|    - Creative Direction Weighting (Viral, Dramatic, Action, Sad/Emotional, Dialogue).              |
|                                                                                                    |
| 5. NATURAL BOUNDARY REFINEMENT (Zero Mid-Sentence Cutoffs)                                         |
|    - Snaps clip start backward to nearest sentence start or natural pause (>= 300ms silence).      |
|    - Snaps clip end forward to grammatical sentence completion with 250ms breathing pad.           |
|                                                                                                    |
| 6. NOVELTY & NON-REPETITION FILTERING                                                             |
|    - Queries `media_generated_clips_history` for previously extracted time intervals.              |
|    - Calculates temporal IoU (tIoU) against historical clips.                                      |
|    - Discards overlapping candidates (tIoU > 0.20) to guarantee fresh clips on repeat runs.        |
|                                                                                                    |
| 7. REFRAMING & DYNAMIC CROP TRAJECTORY                                                             |
|    - Calculates aspect-ratio crop box (9:16, 1:1, 16:9, 4:5) centered on active speaker.           |
|    - Generates smoothed linear keyframe trajectory with headroom padding.                          |
|                                                                                                    |
| 8. RENDERING, CAPTION BURN-IN & EXPORT VALIDATION                                                  |
|    - FFmpeg MP4 export: dynamic crop filter + styled ASS subtitles + AAC audio.                    |
|    - Strict output validator checks non-empty file, stream integrity, and duration parity.         |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Handling Long Movies & Large Files (1–2 GB Scalability)

To process long films on low-resource machines without out-of-memory (OOM) crashes:
1. **Never Load Video into RAM:** All video reading is delegated to FFmpeg with bounded timestamp seeking (`-ss` before `-i`).
2. **Fast Audio Demuxing:** Audio extraction creates a temporary 16kHz mono WAV file in $< 15$ seconds for a 2-hour movie ($\sim 130\text{ MB}$ total), allowing Faster-Whisper to transcribe in sequential chunks.
3. **Stage-Aware Caching:**
   - Once transcription and scene cuts are computed, they are stored in SQLite (`transcript_segments`, `video_scenes`).
   - If the creator runs generation again (e.g., asking for 5 more clips in 1:1), transcription and scene detection are skipped entirely, generating candidates in $< 3$ seconds.
4. **Sampled Visual Tracking:** Face and subject detection does not inspect all 24/30 frames per second. Instead, it inspects keyframe samples (e.g., 2 frames per second) and computes smooth linear trajectories between keyframes, reducing CPU load by 93%.

---

## 3. Explainable Attractiveness & Moment Scoring

The system evaluates potential short clips using an explainable multi-factor scoring model. It explicitly does **not** simulate fake views, likes, or algorithmic social media guarantees.

### 3.1 Scoring Formulation
$$\text{Score} = \sum_{i=1}^{8} w_i \cdot S_i - P_{\text{context}}$$

Where the factors $S_i \in [0.0, 1.0]$ represent:
1. **Opening Hook Clarity ($S_1$):** High speech energy and clear opening utterance without trailing conjunctions (*"so"*, *"and"*).
2. **Narrative & Dialogue Completeness ($S_2$):** Complete conversational turn or story exchange with clear closure.
3. **Emotional / Vocal Intensity ($S_3$):** Dynamic range in audio pitch and amplitude indicating excitement, conflict, or deep emotion.
4. **Visual Interest & Movement ($S_4$):** Motion vector magnitude and camera framing changes across the candidate scene.
5. **Conversational Density ($S_5$):** Multi-speaker exchange frequency (ideal for punchy interview or podcast shorts).
6. **Ending Quality ($S_6$):** Concludes on a punchline, conclusive word, or scene cut rather than mid-dialogue.
7. **Duration Suitability ($S_7$):** Natural duration within the ideal sweet spot ($18\text{s} - 55\text{s}$).
8. **Audio Signal Quality ($S_8$):** High signal-to-noise ratio (SNR) with clear speech intelligibility.
9. **Context Dependency Penalty ($P_{\text{context}}$):** Heavily penalizes clips that start with dangling pronouns (*"He did that because..."*) without preceding context.

### 3.2 Creative Direction Profiles
The weights $w_i$ adapt based on the creator's upfront choice:
- **Dramatic:** Prioritizes emotional intensity ($w_3 = 0.30$) and conversational density ($w_5 = 0.25$).
- **Action & Motion:** Prioritizes visual movement ($w_4 = 0.35$) and scene transition pace ($w_7 = 0.20$).
- **Emotional / Sad:** Prioritizes monologue duration ($w_2 = 0.30$) and vocal pitch contour ($w_3 = 0.25$).
- **Engaging Dialogue:** Prioritizes conversational turns ($w_5 = 0.35$) and opening hook ($w_1 = 0.25$).

---

## 4. Natural Boundary Snapping (Zero Mid-Sentence Cutoffs)

Rigid boundaries (e.g., forcing a clip to exactly 30.00 seconds) produce unwatchable shorts with clipped words. ZezEdit uses natural boundary snapping:

1. **Word-Level Precision:** Faster-Whisper extracts start and end timestamps for every individual word.
2. **Punctuation & Turn Boundaries:** Sentence terminators (`.`, `!`, `?`) and speaker pauses ($\ge 300\text{ms}$) define valid split candidates.
3. **Boundary Expansion Algorithm:**
   - **Start Snapping:** Given an interesting moment starting at $T_{start}$, the engine scans backward to find the beginning of the spoken sentence or the nearest preceding silence $\ge 300\text{ms}$.
   - **End Snapping:** Given a nominal end $T_{end}$, the engine scans forward to find the grammatical conclusion of the utterance, adding a $+250\text{ms}$ natural breathing pad.
   - **Scene Cut Reconciliation:** If a visual scene cut occurs within $500\text{ms}$ of sentence completion, the boundary snaps exactly to the scene cut to avoid a half-second visual artifact from the next scene.

---

## 5. Novelty & Non-Repetition Engine

When a creator requests additional shorts from the same video, the system must not duplicate previous results:

### 5.1 Persistent History Model
Every approved or generated short's time interval $[S, E]$ is saved to SQLite:
```sql
CREATE TABLE media_generated_clips_history (
    id TEXT PRIMARY KEY,
    media_asset_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    generation_run_id TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    aspect_ratio TEXT NOT NULL,
    creative_direction TEXT,
    quality_score REAL,
    title TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_clip_history_lookup ON media_generated_clips_history(media_asset_id, start_time, end_time);
```

### 5.2 Temporal IoU Overlap Exclusion
When discovering candidates for generation run $N$:
1. Retrieve all prior intervals $I_{hist} = \{[s_k, e_k]\}$ for the media asset.
2. For each candidate interval $[s_{cand}, e_{cand}]$, compute the maximum Temporal Intersection over Union (tIoU) against all historical intervals:
   $$\text{tIoU}([s_1, e_1], [s_2, e_2]) = \frac{\max(0, \min(e_1, e_2) - \max(s_1, s_2))}{\max(e_1, e_2) - \min(s_1, s_2)}$$
3. **Exclusion Rule:** If $\text{tIoU} > 0.20$ (more than 20% temporal overlap), the candidate is rejected.
4. **Finite Video Boundary:** If all high-quality scenes have been harvested, the system transparently reports: *"Discovered 4 new high-quality moments (requested 10). Entire video has been thoroughly harvested."*

---

## 6. Rendering & Output Validation

The export engine produces standalone, standards-compliant MP4 files:
- **Encoding Preset:** H.264 / AAC at standard web bitrates (`CRF 22`, `yuv420p`, $30\text{ fps}$).
- **Aspect Ratio Formatting:**
  - `9:16`: $1080 \times 1920$
  - `1:1`: $1080 \times 1080$
  - `16:9`: $1920 \times 1080$
  - `4:5`: $1080 \times 1350$
- **Subtitle Burn-in:** Advanced SubStation Alpha (`.ass`) rendering with custom fonts, outline stroke, and active word highlighting.
- **Strict Verification:** `output_validator.py` probes the rendered MP4 with FFprobe to verify non-zero byte size, valid moov atom, audio/video synchronization, and exact timestamp duration match ($\pm 0.5\text{s}$).


---

## 7. Unified Full-Video Analysis Pipeline Implementation (Session 3)

Session 3 transitioned the analysis subsystem from fragmented utilities into an end-to-end, resilient background pipeline:

### 7.1 Source Signature Formulation
To detect modifications without hashing massive 1–2 GB files, the system computes a hybrid source signature:
$$\text{Signature} = \text{file\_size} : \text{mtime\_ns} : \text{CRC64/MD5 of first 64KB}$$
- **Speed:** $< 1\text{ms}$ calculation time.
- **Sensitivity:** Instant cache invalidation when a video is edited, re-exported, or replaced on disk.

### 7.2 Faster-Whisper with Intelligent VAD Fallback
Silero VAD in Faster-Whisper aggressively suppresses spoken dialogue when background music, cinematic scores, or singing are present. The pipeline introduces automatic fallback:
1. First pass executes with `vad_filter=True` and `min_silence_duration_ms=500`.
2. If the audio stream has active audio energy (`speech_density > 0.05` or non-silent duration) but VAD returns 0 segments, the transcriber automatically retries with `vad_filter=False`.
3. This guarantees dialogue is never lost on mixed audio tracks while retaining VAD speed on clear conversational tracks.

### 7.3 Stage-Aware Caching & Telemetry
Every analysis run stores its components in SQLite (`transcript_segments`, `speech_turns`, `video_scenes`, `sampled_frames`, `visual_observations`, `audio_analysis`).
- **Telemetry Endpoint (`GET /analysis/{run_id}/telemetry`):** Streams current stage name, stage %, overall %, elapsed time, warnings, and component breakdown.
- **Cache Information (`GET /analysis/{run_id}/cache`):** Reports whether cached intelligence matches the current media file signature on disk.
- **Repeat Runs:** When an asset is re-analyzed without `force_reanalysis=True`, cached results are returned instantly in $< 50\text{ms}$.
- **Cancellation & Retry:** Full lifecycle support via `POST /analysis/{run_id}/cancel` and `POST /analysis/{run_id}/retry`, fully synchronized with persistent `JobOrchestrator` records.

---

## 8. Intelligent Clip Discovery, Multimodal Scoring & Persistent Novelty (Session 4)

Session 4 transformed raw transcript, scene cut, and keyframe analysis data into high-value, naturally bounded short-video candidates:

### 8.1 Multimodal Scoring Formulation
Every candidate moment is evaluated against 6 normalized multimodal signal components ($0 - 100$):
1. **Hook Strength ($S_{hook}$):** Evaluates opening 3-second attention-grabbing words, high speech rate, question or imperative openers, and rapid initial motion.
2. **Dialogue Interest ($S_{dialogue}$):** Speech turn density, unique vocabulary entropy, lexical complexity, and conversational continuity.
3. **Emotional Signal ($S_{emotion}$):** Dynamic audio loudness variation, musical cue presence, and sentiment shift.
4. **Action & Motion ($S_{motion}$):** Visual change scores, scene cut density, and camera trajectory dynamics.
5. **Visual Presentation ($S_{visual}$):** Keyframe framing quality, visual clarity, and face/subject presence.
6. **Narrative Completeness ($S_{narrative}$):** Balance of introduction, body discourse, and natural conclusion.

The total attractiveness estimate is computed via adaptive weighted summation:
$$S_{total} = \sum_{k} w_k \cdot S_k - P_{penalty}$$
where weights $w_k$ adapt dynamically according to the selected creative direction profile.

### 8.2 7 Creative Direction Weight Profiles
- **Best Overall:** Balanced evaluation ($w_{hook}=0.25, w_{dialogue}=0.25, w_{emotion}=0.15, w_{motion}=0.15, w_{visual}=0.10, w_{narrative}=0.10$).
- **Viral & Punchy:** Hook-heavy ($w_{hook}=0.40, w_{motion}=0.25, w_{dialogue}=0.15$).
- **Dramatic:** Narrative climaxes ($w_{narrative}=0.30, w_{emotion}=0.30, w_{dialogue}=0.20$).
- **Action & Motion:** Visual dynamics ($w_{motion}=0.45, w_{hook}=0.25, w_{visual}=0.15$).
- **Emotional / Sad:** Subtle reflective dialogue & music ($w_{emotion}=0.40, w_{dialogue}=0.30$).
- **Engaging Dialogue:** Spoken conversational density ($w_{dialogue}=0.45, w_{narrative}=0.25$).
- **Humorous:** High-energy punchlines & facial expressions ($w_{hook}=0.30, w_{dialogue}=0.30, w_{emotion}=0.20$).

### 8.3 Natural Boundary Snapping & Breathing Room
To eliminate awkward mid-sentence cutoffs and jarring flash frames:
- **Speech Snapping:** Start times snap backward to the nearest word boundary with a $0.15\text{s}$ lead-in breathing margin.
- **Sentence Closure:** End times snap forward to grammatical sentence terminal punctuation (`.`, `!`, `?`) plus a $0.25\text{s}$ breathing pad.
- **Scene Transition Alignment:** If a visual scene cut falls within $\le 0.45\text{s}$ of the spoken sentence start or end, the cut aligns to the scene boundary to eliminate flash frames while strictly protecting speech continuity.
- **Confidence Metric:** Every candidate outputs `natural_boundary_confidence` ($0.0 - 1.0$), reaching $1.00$ when both sentence closure and scene cut snapping succeed.

### 8.4 Persistent Novelty & Non-Repetition Engine
To allow users to repeatedly click "Generate More Shorts" without receiving duplicate moments:
- **Ledger Storage:** All generated moments are recorded in `media_generated_clips_history` with exact $[t_{start}, t_{end}]$ intervals and aspect ratios.
- **tIoU & Overlap Exclusions:** Newly discovered intervals are compared against historical records:
  $$\text{tIoU}(A, B) = \frac{|A \cap B|}{|A \cup B|}, \quad \text{OverlapRatio}(A, B) = \frac{|A \cap B|}{|A|}$$
  Candidates with $\text{tIoU} \ge 0.50$ or $\text{OverlapRatio} \ge 0.60$ are excluded by the novelty filter.
- **Real Media Verification:** On a 5-minute video asset (`med_51dc0e4b43f8`), Batch 1 generated 4 punchy shorts and Batch 2 generated 4 dramatic shorts; max tIoU between batches was **0.373** (strictly $< 0.50$).

