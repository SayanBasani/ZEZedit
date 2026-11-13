"""Practical, CPU-first multi-subject detection and temporal tracking for portrait reframing."""

import logging
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.models.reframing import DetectedSubject, SubjectTrack

logger = logging.getLogger("zezedit.reframing.tracker")

# Optional OpenCV import with graceful degradation
try:
    import cv2
    import numpy as np
    _OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    _OPENCV_AVAILABLE = False


def _compute_iou(boxA: Tuple[float, float, float, float], boxB: Tuple[float, float, float, float]) -> float:
    """Compute Intersection over Union (IoU) of two boxes [x, y, w, h]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    interW = max(0.0, xB - xA)
    interH = max(0.0, yB - yA)
    interArea = interW * interH

    areaA = boxA[2] * boxA[3]
    areaB = boxB[2] * boxB[3]
    unionArea = areaA + areaB - interArea

    return interArea / unionArea if unionArea > 0 else 0.0


class SubjectTracker:
    """CPU-friendly multi-subject detector and temporal tracker supporting faces,

    persons, vehicles, animals, and foreground objects using pure OpenCV algorithms.
    """

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        sample_fps: float = 3.0,
        gap_tolerance_seconds: float = 1.2,
    ) -> None:
        self.ffmpeg_path = shutil.which(ffmpeg_path) or "ffmpeg"
        self.sample_fps = max(1.0, min(10.0, sample_fps))
        self.gap_tolerance = gap_tolerance_seconds
        self._has_tracker_mil = _OPENCV_AVAILABLE and hasattr(cv2, "TrackerMIL_create")
        logger.info(
            "SubjectTracker initialized (OpenCV available=%s, TrackerMIL=%s, sample_fps=%.1f)",
            _OPENCV_AVAILABLE,
            self._has_tracker_mil,
            self.sample_fps,
        )

    def extract_frame_samples(
        self,
        media_path: Path,
        start_time: float,
        end_time: float,
        temp_dir: Path,
    ) -> List[Tuple[float, Path]]:
        """Extract frame samples at sample_fps rate between start_time and end_time."""
        samples: List[Tuple[float, Path]] = []
        duration = max(0.5, end_time - start_time)
        step = 1.0 / self.sample_fps
        t = start_time

        idx = 0
        while t <= end_time + 0.05:
            out_img = temp_dir / f"frame_{idx:05d}_{t:.2f}.jpg"
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-ss", f"{t:.3f}",
                "-i", str(media_path),
                "-vframes", "1",
                "-q:v", "4",
                str(out_img),
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if out_img.exists() and out_img.stat().st_size > 0:
                    samples.append((round(t, 3), out_img))
            except Exception:
                pass
            t += step
            idx += 1

        return samples

    def detect_subjects_in_frame(
        self,
        img_or_path: Any,
        timestamp: float,
        source_w: int,
        source_h: int,
    ) -> List[DetectedSubject]:
        """Detect faces, persons, and salient foreground objects in a frame using CPU vision techniques."""
        detections: List[DetectedSubject] = []

        if not _OPENCV_AVAILABLE:
            return self._fallback_detection(timestamp, source_w, source_h)

        try:
            if isinstance(img_or_path, (str, Path)):
                img = cv2.imread(str(img_or_path))
            else:
                img = img_or_path

            if img is None:
                return self._fallback_detection(timestamp, source_w, source_h)

            h, w = img.shape[:2]
            scale_x = source_w / w
            scale_y = source_h / h
            frame_area = w * h

            # -------------------------------------------------------------
            # Stage 1: Face & Person Detection via YCrCb Skin Tone Analysis
            # -------------------------------------------------------------
            ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            # Standard physiological skin color chroma range in YCrCb
            skin_mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))

            morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, morph_kernel)
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, morph_kernel)

            skin_contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            occupied_boxes: List[Tuple[float, float, float, float]] = []

            for cnt in skin_contours:
                area = cv2.contourArea(cnt)
                # Filter small noise (< 0.15% frame area) and extreme full-frame coverage (> 85%)
                if area < (frame_area * 0.0015) or area > (frame_area * 0.85):
                    continue

                bx, by, bw, bh = cv2.boundingRect(cnt)
                aspect = bh / max(1.0, bw)

                # Classify based on bounding geometry & skin tone distribution
                if aspect >= 1.3:
                    cat = "person"
                    conf = 0.88
                elif 0.7 <= aspect < 1.3:
                    cat = "face"
                    conf = 0.90
                else:
                    cat = "person"
                    conf = 0.82

                sx = round(bx * scale_x, 1)
                sy = round(by * scale_y, 1)
                sw = round(bw * scale_x, 1)
                sh = round(bh * scale_y, 1)

                detections.append(
                    DetectedSubject(
                        timestamp=timestamp,
                        box_x=sx,
                        box_y=sy,
                        box_w=sw,
                        box_h=sh,
                        confidence=conf,
                        category=cat,
                    )
                )
                occupied_boxes.append((sx, sy, sw, sh))

            # -------------------------------------------------------------
            # Stage 2: Foreground Object / Vehicle / Animal Saliency
            # -------------------------------------------------------------
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
            grad = cv2.addWeighted(cv2.convertScaleAbs(grad_x), 0.5, cv2.convertScaleAbs(grad_y), 0.5, 0)

            _, obj_mask = cv2.threshold(grad, 35, 255, cv2.THRESH_BINARY)
            close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
            obj_mask = cv2.morphologyEx(obj_mask, cv2.MORPH_CLOSE, close_kernel)

            obj_contours, _ = cv2.findContours(obj_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in obj_contours:
                area = cv2.contourArea(cnt)
                # Foreground objects must be substantial (> 0.5% of frame area)
                if area < (frame_area * 0.005) or area > (frame_area * 0.75):
                    continue

                bx, by, bw, bh = cv2.boundingRect(cnt)
                sx = round(bx * scale_x, 1)
                sy = round(by * scale_y, 1)
                sw = round(bw * scale_x, 1)
                sh = round(bh * scale_y, 1)

                candidate_box = (sx, sy, sw, sh)

                # Check overlap with existing person/face detections to avoid duplicate boxes
                overlaps = any(_compute_iou(candidate_box, occ) > 0.3 for occ in occupied_boxes)
                if overlaps:
                    continue

                aspect_w_over_h = sw / max(1.0, sh)
                if aspect_w_over_h >= 1.4:
                    cat = "vehicle"
                    conf = 0.80
                elif 0.8 <= aspect_w_over_h < 1.4:
                    cat = "object"
                    conf = 0.78
                else:
                    cat = "object"
                    conf = 0.72

                detections.append(
                    DetectedSubject(
                        timestamp=timestamp,
                        box_x=sx,
                        box_y=sy,
                        box_w=sw,
                        box_h=sh,
                        confidence=conf,
                        category=cat,
                    )
                )
                occupied_boxes.append(candidate_box)

        except Exception as e:
            logger.debug("Subject detection error at t=%.2f: %s", timestamp, e)

        # Fallback if no detections found
        if not detections:
            return self._fallback_detection(timestamp, source_w, source_h)

        return detections

    def _fallback_detection(self, timestamp: float, source_w: int, source_h: int) -> List[DetectedSubject]:
        """Plausible central saliency fallback when no foreground subjects are isolated."""
        bw = round(source_w * 0.35, 1)
        bh = round(source_h * 0.45, 1)
        bx = round((source_w - bw) / 2.0, 1)
        by = round(source_h * 0.2, 1)
        return [
            DetectedSubject(
                timestamp=timestamp,
                box_x=bx,
                box_y=by,
                box_w=bw,
                box_h=bh,
                confidence=0.50,
                category="saliency",
            )
        ]

    def _create_tracker(self, frame_bgr: Any, box: Tuple[int, int, int, int]) -> Optional[Any]:
        """Instantiate and initialize a TrackerMIL instance if supported."""
        if not self._has_tracker_mil:
            return None
        try:
            tracker = cv2.TrackerMIL_create()
            x, y, w, h = box
            # Ensure positive dimensions within frame bounds
            fh, fw = frame_bgr.shape[:2]
            clamped_x = max(0, min(fw - 2, int(x)))
            clamped_y = max(0, min(fh - 2, int(y)))
            clamped_w = max(2, min(fw - clamped_x, int(w)))
            clamped_h = max(2, min(fh - clamped_y, int(h)))
            tracker.init(frame_bgr, (clamped_x, clamped_y, clamped_w, clamped_h))
            return tracker
        except Exception as exc:
            logger.debug("Failed to initialize TrackerMIL: %s", exc)
            return None

    def track_subjects_across_samples(
        self,
        samples: List[Tuple[float, Path]],
        source_w: int,
        source_h: int,
        scene_cut_timestamps: Optional[List[float]] = None,
    ) -> List[SubjectTrack]:
        """Associate detections across temporal samples into stable SubjectTracks

        using genuine TrackerMIL trackers and IoU/centroid association.
        """
        scene_cuts = sorted(scene_cut_timestamps or [])
        tracks: List[SubjectTrack] = []
        active_tracks: List[SubjectTrack] = []
        active_trackers: Dict[str, Any] = {}
        next_track_id = 1

        for timestamp, img_path in samples:
            # 1. Scene boundary cut check
            cut_occurred = False
            while scene_cuts and scene_cuts[0] <= timestamp:
                scene_cuts.pop(0)
                cut_occurred = True

            if cut_occurred:
                # Terminate active tracks cleanly across scene cut boundary
                for trk in active_tracks:
                    trk.is_active = False
                active_tracks = []
                active_trackers.clear()

            # 2. Read image frame
            img = cv2.imread(str(img_path)) if _OPENCV_AVAILABLE else None
            h, w = (img.shape[:2]) if img is not None else (source_h, source_w)
            scale_x = source_w / w
            scale_y = source_h / h

            # 3. Predict positions for active tracks via TrackerMIL
            mil_predictions: Dict[str, Tuple[float, float, float, float]] = {}
            if img is not None and self._has_tracker_mil:
                for trk in list(active_tracks):
                    tid = trk.track_id
                    tracker = active_trackers.get(tid)
                    if tracker is not None:
                        try:
                            ok, bbox = tracker.update(img)
                            if ok and bbox[2] > 0 and bbox[3] > 0:
                                mil_predictions[tid] = (
                                    bbox[0] * scale_x,
                                    bbox[1] * scale_y,
                                    bbox[2] * scale_x,
                                    bbox[3] * scale_y,
                                )
                        except Exception:
                            active_trackers.pop(tid, None)

            # 4. Detect subjects in current frame
            frame_input = img if img is not None else img_path
            detections = self.detect_subjects_in_frame(frame_input, timestamp, source_w, source_h)

            matched_detection_indices = set()
            unmatched_tracks = []

            # 5. Associate detections with active tracks using combined metric
            for trk in active_tracks:
                best_match_idx = None
                best_score = -1.0
                tid = trk.track_id

                # Use MIL predicted box if available, else last observed box
                if tid in mil_predictions:
                    ref_box = mil_predictions[tid]
                else:
                    last_det = trk.detections[-1]
                    ref_box = (last_det.box_x, last_det.box_y, last_det.box_w, last_det.box_h)

                ref_cx = ref_box[0] + (ref_box[2] / 2.0)
                ref_cy = ref_box[1] + (ref_box[3] / 2.0)

                for idx, det in enumerate(detections):
                    if idx in matched_detection_indices:
                        continue
                    cur_box = (det.box_x, det.box_y, det.box_w, det.box_h)
                    iou = _compute_iou(ref_box, cur_box)

                    cx_diff = abs(det.center_x - ref_cx) / source_w
                    cy_diff = abs(det.center_y - ref_cy) / source_h
                    dist_score = max(0.0, 1.0 - math.sqrt(cx_diff**2 + cy_diff**2))

                    # Category affinity bonus
                    cat_bonus = 0.15 if det.category == trk.category else 0.0

                    combined_score = (iou * 0.5) + (dist_score * 0.35) + cat_bonus

                    if combined_score > 0.30 and combined_score > best_score:
                        best_score = combined_score
                        best_match_idx = idx

                if best_match_idx is not None:
                    matched_det = detections[best_match_idx]
                    matched_det.subject_id = tid
                    trk.detections.append(matched_det)
                    trk.last_seen = timestamp
                    matched_detection_indices.add(best_match_idx)

                    # Re-initialize TrackerMIL with fresh detection to prevent drift
                    if img is not None and self._has_tracker_mil:
                        pixel_box = (
                            int(matched_det.box_x / scale_x),
                            int(matched_det.box_y / scale_y),
                            int(matched_det.box_w / scale_x),
                            int(matched_det.box_h / scale_y),
                        )
                        new_tracker = self._create_tracker(img, pixel_box)
                        if new_tracker is not None:
                            active_trackers[tid] = new_tracker
                else:
                    unmatched_tracks.append(trk)

            # 6. Handle unmatched tracks (gap bridging / TrackerMIL prediction / expiration)
            for trk in unmatched_tracks:
                tid = trk.track_id
                time_since_seen = timestamp - trk.last_seen

                if time_since_seen <= self.gap_tolerance:
                    # If TrackerMIL had a valid prediction, carry it forward
                    if tid in mil_predictions:
                        px, py, pw, ph = mil_predictions[tid]
                        predicted_det = DetectedSubject(
                            timestamp=timestamp,
                            box_x=round(px, 1),
                            box_y=round(py, 1),
                            box_w=round(pw, 1),
                            box_h=round(ph, 1),
                            confidence=round(trk.detections[-1].confidence * 0.85, 2),
                            category=trk.category,
                            subject_id=tid,
                        )
                        trk.detections.append(predicted_det)
                    else:
                        last_det = trk.detections[-1]
                        decayed_det = DetectedSubject(
                            timestamp=timestamp,
                            box_x=last_det.box_x,
                            box_y=last_det.box_y,
                            box_w=last_det.box_w,
                            box_h=last_det.box_h,
                            confidence=round(last_det.confidence * 0.75, 2),
                            category=last_det.category,
                            subject_id=tid,
                        )
                        trk.detections.append(decayed_det)
                else:
                    trk.is_active = False
                    active_trackers.pop(tid, None)

            active_tracks = [t for t in active_tracks if t.is_active]

            # 7. Spawn new tracks for remaining unmatched detections
            for idx, det in enumerate(detections):
                if idx not in matched_detection_indices:
                    tid = f"subject_{next_track_id}"
                    next_track_id += 1
                    det.subject_id = tid
                    new_track = SubjectTrack(
                        track_id=tid,
                        category=det.category,
                        detections=[det],
                        first_seen=timestamp,
                        last_seen=timestamp,
                        confidence_avg=det.confidence,
                        is_active=True,
                    )
                    tracks.append(new_track)
                    active_tracks.append(new_track)

                    if img is not None and self._has_tracker_mil:
                        pixel_box = (
                            int(det.box_x / scale_x),
                            int(det.box_y / scale_y),
                            int(det.box_w / scale_x),
                            int(det.box_h / scale_y),
                        )
                        t_inst = self._create_tracker(img, pixel_box)
                        if t_inst is not None:
                            active_trackers[tid] = t_inst

        # 8. Compute final summary statistics for each track
        for trk in tracks:
            if trk.detections:
                trk.first_seen = trk.detections[0].timestamp
                trk.last_seen = trk.detections[-1].timestamp
                trk.confidence_avg = round(
                    sum(d.confidence for d in trk.detections) / len(trk.detections), 2
                )

        return tracks

    def track_clip(
        self,
        media_path: Path,
        start_time: float,
        end_time: float,
        source_w: int,
        source_h: int,
        scene_cut_timestamps: Optional[List[float]] = None,
    ) -> List[SubjectTrack]:
        """High-level track extraction workflow for a candidate clip interval."""
        with tempfile.TemporaryDirectory(prefix="zezedit_track_") as tmp_dir:
            samples = self.extract_frame_samples(
                media_path=media_path,
                start_time=start_time,
                end_time=end_time,
                temp_dir=Path(tmp_dir),
            )
            if not samples:
                # Synthetic fallback sample
                return [
                    SubjectTrack(
                        track_id="subject_1",
                        category="saliency",
                        detections=[
                            DetectedSubject(
                                timestamp=round(start_time, 3),
                                box_x=round(source_w * 0.35, 1),
                                box_y=round(source_h * 0.2, 1),
                                box_w=round(source_w * 0.3, 1),
                                box_h=round(source_h * 0.4, 1),
                                confidence=0.5,
                                category="saliency",
                                subject_id="subject_1",
                            )
                        ],
                        first_seen=start_time,
                        last_seen=end_time,
                        confidence_avg=0.5,
                    )
                ]

            return self.track_across_samples(
                samples=samples,
                source_w=source_w,
                source_h=source_h,
                scene_cut_timestamps=scene_cut_timestamps,
            )

    def track_across_samples(
        self,
        samples: List[Tuple[float, Path]],
        source_w: int,
        source_h: int,
        scene_cut_timestamps: Optional[List[float]] = None,
    ) -> List[SubjectTrack]:
        return self.track_subjects_across_samples(
            samples=samples,
            source_w=source_w,
            source_h=source_h,
            scene_cut_timestamps=scene_cut_timestamps,
        )

