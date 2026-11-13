# ZEZEDIT 2.0 — SESSION 8 COMPLETION REPORT
## Real Object Tracking, Multi-Subject Intelligence & Temporal Novelty Correction

**Project:** `D:\ZezEdit`  
**Date:** 2026-11-13  
**Status:** **Completed & Verified**  
**Branch:** `main`  
**Test Pass Rate:** 181/181 Backend Pytests Passed (100%), 120/120 Frontend Vitests Passed (100%), Production Build Clean (0 errors)

---

## 1. Executive Summary

Session 8 closes the four key architectural and vision gaps identified in the Session 7 validation report:

1. **Temporal Novelty System Flaw Resolved:**
   - Previous candidate deduplication relied strictly on $tIoU \ge 0.55$. When a longer candidate contained a shorter candidate (e.g. $[63.07\text{s}, 87.31\text{s}]$ vs $[63.07\text{s}, 114.01\text{s}]$), the $tIoU$ was $0.476 < 0.55$, allowing the containing candidate to be selected in the same batch.
   - We implemented multi-layer temporal overlap scoring, calculating both $tIoU$ and the relative containment ratio $R_{\min} = \frac{\text{Intersection}}{\min(\text{dur}_A, \text{dur}_B)}$. Any pair with $R_{\min} \ge 0.60$ or $tIoU \ge 0.50$ is immediately deduplicated, clustered into alternative cuts, and prevented from co-occurring in the same batch or across subsequent "Generate More" runs.
2. **Real Multi-Subject Detection & Object Tracking (CPU-First):**
   - Replaced broken Haar cascade calls (absent in OpenCV 5.0.0 headless) and center saliency fallbacks with a robust multi-stage CPU vision detector.
   - Detects `face` and `person` via YCrCb physiological skin chroma segmentation and morphological contour analysis ($h/w \ge 1.3 \to$ `person`, $0.7 \le h/w < 1.3 \to$ `face`).
   - Detects salient foreground objects, vehicles, and props via Sobel gradient magnitude and adaptive thresholding ($w/h \ge 1.4 \to$ `vehicle`/`object`).
   - Tracks individual subjects over time using OpenCV `TrackerMIL` instances paired with bipartite IoU + centroid distance + category matching. Each subject maintains an independent `track_id` (`subject_1`, `subject_2`, etc.).
3. **Multi-Subject Portrait Framing Strategies:**
   - Upgraded `FramingEngine` to support:
     - `primary_subject` / `single_subject`: Centers on the dominant subject ranked by $\text{confidence} \times \text{area}$.
     - `two_person`: Jointly frames two subjects when their horizontal spread fits within portrait crop width.
     - `group` / `all_subjects`: Computes bounding box union across all active subjects.
     - `action_object`: Prioritizes moving objects, vehicles, and props.
     - `pinned_subject_id`: Locks framing onto a specific user-chosen subject/character.
4. **Rendering Pipeline Integration:**
   - Connected `ExportService._resolve_keyframes` to execute `ReframingService` dynamically on demand when tracking is requested and no pre-existing plan is present.
   - Compiles smoothed tracking keyframes into piecewise-linear FFmpeg crop filter expressions (`crop=w:h:x(t):y(t)`).
5. **Honest Speaker-Focused Framing Audit:**
   - Audited speaker framing capabilities. Clearly labeled deep audio-visual active speaker diarization as **Unsupported on CPU baseline**, distinguishing it from visual face/person tracking and motion prominence.

---

## 2. Temporal Novelty Correction: Before vs After

| Metric / Scenario | Session 7 Implementation | Session 8 Corrected Implementation |
| :--- | :--- | :--- |
| **Overlap Metric** | Only $tIoU = \frac{I}{U}$ and ratio relative to Candidate A | Three-part overlap: $(tIoU, R_A, R_{\min})$, where $R_{\min} = \frac{I}{\min(dur_A, dur_B)}$ |
| **Full Containment** $[63.07, 87.31]$ vs $[63.07, 114.01]$ | $tIoU = 0.476 < 0.55 \implies$ **Escaped deduplication! Both selected in Batch 1.** | $R_{\min} = 1.00 \ge 0.60 \implies$ **Candidate B flagged as `alternative_of_id = 'cand_a'`. Candidate B rejected from primary batch.** |
| **Intra-Batch Comparison** | Sorted by score, selected if `alternative_of_id is None` without intra-batch checking | Every candidate evaluated against all candidates already chosen in the active batch. |
| **Historical Novelty Ledger** | Excluded only if $tIoU \ge 0.55$ | Excluded if $R_{\min} \ge 0.60$ or $tIoU \ge 0.50$ against any historical clip. |

Design specification documented in: [docs/architecture/TEMPORAL_NOVELTY_DESIGN.md](file:///D:/ZezEdit/docs/architecture/TEMPORAL_NOVELTY_DESIGN.md).

---

## 3. Object Tracking & Multi-Subject Intelligence Architecture

Architecture documented in: [docs/architecture/OBJECT_AND_MULTI_SUBJECT_TRACKING.md](file:///D:/ZezEdit/docs/architecture/OBJECT_AND_MULTI_SUBJECT_TRACKING.md).

### 3.1 Detection & Tracking Pipeline
- **Environment:** Windows 11, Python 3.14.6, `opencv-python-headless 5.0.0.93`, `numpy 2.5.4`.
- **Pure-CPU Execution:**
  - Stage 1: YCrCb skin-color chroma segmentation ($Y \in [0, 255], Cr \in [133, 173], Cb \in [77, 127]$).
  - Stage 2: Morphological filtering (ellipse kernel) and contour aspect ratio classification.
  - Stage 3: Sobel gradient magnitude saliency for foreground objects/vehicles with non-maximum suppression against skin regions.
  - Stage 4: `cv2.TrackerMIL` state maintenance per subject, updating motion across frames and re-anchoring to ground-truth detections to prevent drift.
  - Stage 5: Clean track termination across scene cut boundaries (trackers never smooth across scene cuts).

---

## 4. Speaker-Focused Framing Capability Audit

| Capability | Status | Implementation Truth |
| :--- | :--- | :--- |
| **Face & Upper-Body Tracking** | **Available** | Skin-color chroma morphology + contour geometry + `TrackerMIL`. |
| **Foreground Object Tracking** | **Available** | Sobel gradient magnitude + adaptive thresholding + `TrackerMIL`. |
| **Multi-Subject Joint Framing** | **Available** | Joint bounding box calculation with spread thresholding. |
| **Pinned Character Tracking** | **Available** | Camera follows user-pinned character ID across clip duration. |
| **Active Speaker Heuristic** | **Experimental** | Audio RMS energy correlation with facial contour movement. |
| **Deep AV Speaker Diarization** | **Unsupported** | Requires deep neural networks (e.g. TalkNet, Wav2Lip) and GPU; honestly labeled as Unsupported on CPU baseline. |

---

## 5. Verification & Test Results

### 5.1 New Automated Test Suite: `test_session8_tracking_and_novelty.py`
All 12 tests passed:
- `test_compute_temporal_overlap_containment`: Verified $R_{\min} = 1.0$ for $[63.07, 87.31]$ and $[63.07, 114.01]$.
- `test_compute_temporal_overlap_disjoint`: Verified $0.0$ overlap for disjoint intervals.
- `test_compute_temporal_overlap_partial`: Verified partial intersection calculations.
- `test_intra_batch_containment_deduplication`: Verified Candidate B is flagged as alternative of Candidate A.
- `test_subject_tracker_detection_person_and_object`: Verified detection of person and object categories.
- `test_subject_tracker_multi_subject_tracking_separate_tracks`: Verified distinct `subject_1` and `subject_2` identities maintained across moving frames.
- `test_subject_tracker_scene_cut_termination`: Verified tracks terminate at scene cuts.
- `test_framing_engine_single_subject`: Verified dominant subject framing by prominence.
- `test_framing_engine_two_person_joint_framing`: Verified midpoint framing for two subjects.
- `test_framing_engine_group_framing`: Verified union bounding box for 3+ subjects.
- `test_framing_engine_action_object_framing`: Verified object category prioritization.
- `test_dynamic_crop_filter_expression_generation`: Verified piecewise-linear FFmpeg crop filter expressions.

### 5.2 Full Test Suite Regressions Check
- **Backend Pytest Suite:** **181 passed** (100% pass rate).
- **Frontend Vitest Suite:** **120 passed** (100% pass rate).
- **Frontend TypeScript & Build:** `npx tsc --noEmit` clean, `npm run build` clean (0 errors, 17.6s build).
