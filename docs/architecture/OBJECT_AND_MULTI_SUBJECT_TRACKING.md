# Object Detection, Multi-Subject Intelligence & Framing Architecture

**Project:** ZezEdit 2.0  
**Session:** Session 8  
**Component:** Computer Vision, Multi-Subject Tracking & Portrait Framing  
**Status:** Implemented & Verified  

---

## 1. Executive Summary

Previous iterations of ZezEdit relied on Haar cascades (which were absent in modern headless OpenCV runtimes) and static center-weighted saliency heuristics. In Session 7, multi-subject framing was identified as using a simple bounding-box union without independent temporal identities, and speaker-focused framing was reported without clear technical grounding.

Session 8 implements **genuine, CPU-friendly multi-subject detection, temporal object tracking, and multi-strategy portrait framing**. The system runs on commodity CPUs without requiring monolithic deep learning weight downloads or dedicated GPU acceleration, while maintaining temporal identities for distinct subjects across frames.

---

## 2. Multi-Stage Detection Pipeline

The detection pipeline is implemented in `SubjectTracker.detect_subjects_in_frame()` (`backend/app/services/subject_tracker.py`) and operates entirely on CPU:

```
[ Sampled Frame ]
       │
       ├───> [ YCrCb Skin Color Segmentation ]
       │            │
       │            ├──> Morphological Open/Close (5x5 ellipse)
       │            ├──> Contour Extraction & Area Filtering (0.15% - 85% frame area)
       │            └──> Geometric Classification:
       │                   • Aspect Ratio (h/w) >= 1.3  ──> "person" (confidence: 0.88)
       │                   • Aspect Ratio 0.7 <= h/w < 1.3 ──> "face" (confidence: 0.90)
       │
       ├───> [ Foreground Contrast / Sobel Gradient Saliency ]
       │            │
       │            ├──> Sobel X/Y Gradient Magnitude & Adaptive Threshold
       │            ├──> Non-Maximum Suppression vs Skin Bounding Boxes (IoU > 0.3)
       │            └──> Geometric Classification:
       │                   • Aspect Ratio (w/h) >= 1.4  ──> "vehicle" (confidence: 0.80)
       │                   • Aspect Ratio 0.8 <= w/h < 1.4 ──> "object" (confidence: 0.78)
       │
       └───> [ Saliency Fallback ]
                    └──> Applied only when zero foreground subjects are isolated
                         (Center third region, confidence: 0.50)
```

---

## 3. Temporal Tracking Engine (TrackerMIL + Multi-Target Association)

Rather than treating each frame as an isolated detection or merging all subjects into one large box, `SubjectTracker` tracks individual subjects across time using `cv2.TrackerMIL`:

### 3.1 Tracking State Lifecycle

1. **MIL Tracker State**: For each active track `tid`, a dedicated `cv2.TrackerMIL` instance is retained in memory.
2. **Motion Prediction**: On arrival of frame $t_k$, each active tracker computes `ok, bbox = tracker.update(frame)`.
3. **Detection Matching**: Fresh detections in frame $t_k$ are associated with active tracks using a composite metric:
   $$\text{Score} = 0.50 \cdot \text{IoU}(\text{box}_{\text{pred}}, \text{box}_{\text{det}}) + 0.35 \cdot \left(1 - \frac{d_{\text{centroid}}}{\text{diagonal}}\right) + 0.15 \cdot \mathbb{I}(\text{cat}_{\text{track}} = \text{cat}_{\text{det}})$$
4. **Drift Correction**: When a detection matches an active track, the MIL tracker is re-initialized with the ground-truth detection box to prevent cumulative tracker drift.
5. **Occlusion & Gap Bridging**: When an active track is temporarily unobserved by the detector:
   - If TrackerMIL continues to track successfully, its predicted bounding box is recorded with a $0.85\times$ confidence decay factor.
   - If TrackerMIL also fails, the last observed position is carried forward up to `gap_tolerance_seconds` ($1.2\text{s}$) before marking the track inactive.
6. **Scene Boundary Cuts**: Tracks are strictly terminated across scene cuts. Trackers never smooth or track across visual scene boundaries.

---

## 4. Multi-Subject Framing Strategies

`FramingEngine` (`backend/app/services/framing_engine.py`) consumes the temporal tracks and calculates authoritative portrait crop keyframes:

| Strategy | Behavior | Applicable Scenarios |
| :--- | :--- | :--- |
| **`primary_subject`** / **`single_subject`** | Ranks active subjects by $\text{confidence} \times \text{area}$ and centers the crop window on the dominant subject with headroom offset. | Solo speakers, vloggers, primary interviewees |
| **`two_person`** | Jointly frames both subjects if their horizontal spread $\le 95\%$ of portrait crop width; otherwise centers between them with warning. | Two-person dialogues, podcasts, interviews |
| **`group`** / **`all_subjects`** | Computes the bounding box union enclosing all active subjects. Clamps to maximum crop width if group width exceeds portrait limits. | Group discussions, panels, stage performances |
| **`action_object`** / **`object_tracking`** | Prioritizes tracks with category in `{"object", "vehicle", "animal"}` or subjects displaying highest motion velocity. | Moving vehicles, pets, product demonstrations |
| **`pinned_subject_id`** | Locks the crop camera onto a specific character or subject ID chosen by the user in the UI. | Selected character focus |
| **`auto`** | Dynamically switches strategy based on active subject count ($1 \to$ single, $2 \to$ two-person, $\ge 3 \to$ group). | Default automated workflow |

---

## 5. Rendering Pipeline Integration

Dynamic reframing is tightly connected to FFmpeg export via `ExportService._resolve_keyframes`:

1. **Pre-computed Plan**: If a candidate has an approved reframing plan or revision, its `CropKeyframe` trajectory is directly loaded.
2. **On-Demand Generation**: If no pre-computed plan exists and framing mode is non-manual, `ExportService` invokes `ReframingService.analyze_and_create_plan()`, executing `SubjectTracker` and `FramingEngine` dynamically.
3. **Filtergraph Compilation**: Keyframe trajectories are simplified (collinear points pruned) and compiled into piecewise-linear FFmpeg crop filter expressions:
   $$\text{crop}=w:h:x(t):y(t)$$
   evaluated dynamically during encoding via nested `if(lte(t, t_next), ...)` expressions.
4. **Manual Mode**: Honors user-specified percentage offsets ($x\%$, $y\%$) and digital zoom multipliers.

---

## 6. Speaker-Focused Framing Capability Audit

To prevent misleading claims or "fake AI" labeling, ZezEdit establishes an honest, verified capability matrix:

| Capability | Status | Implementation Details |
| :--- | :--- | :--- |
| **Face & Upper-Body Tracking** | **Available** | Real-time skin-color morphology + geometry classification + `TrackerMIL`. |
| **Salient Foreground Object Tracking** | **Available** | Sobel gradient magnitude + adaptive contour segmentation + `TrackerMIL`. |
| **Multi-Subject Joint Framing** | **Available** | Prominence ranking, joint bounding box calculation, spread thresholding. |
| **Pinned Character Tracking** | **Available** | Subject ID continuity across keyframe generation. |
| **Active Speaker Heuristic** | **Experimental** | Audio RMS energy correlation with facial contour movement (heuristic only). |
| **Deep Audio-Visual Speaker Diarization** | **Unsupported** | Requires heavy neural networks (e.g. TalkNet, Wav2Lip, SyncNet) and GPU acceleration. Clearly labeled as Unsupported on CPU baseline. |
