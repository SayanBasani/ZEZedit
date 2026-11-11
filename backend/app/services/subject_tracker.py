"""Practical, CPU-first subject detection and temporal tracking for portrait reframing."""

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
    _OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None
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
    """CPU-friendly multi-subject detector and temporal tracker."""

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        sample_fps: float = 3.0,
        gap_tolerance_seconds: float = 1.2,
    ) -> None:
        self.ffmpeg_path = shutil.which(ffmpeg_path) or "ffmpeg"
        self.sample_fps = max(1.0, min(10.0, sample_fps))
        self.gap_tolerance = gap_tolerance_seconds
        self._cascade_frontal = None
        self._cascade_profile = None
        self._cascade_body = None
        self._init_cascades()

    def _init_cascades(self) -> None:
        if not _OPENCV_AVAILABLE:
            logger.info("OpenCV not yet loaded; tracker will use fallback detection heuristics")
            return

        try:
            cascade_dir = cv2.data.haarcascades
            frontal_path = str(Path(cascade_dir) / "haarcascade_frontalface_default.xml")
            profile_path = str(Path(cascade_dir) / "haarcascade_profileface.xml")
            body_path = str(Path(cascade_dir) / "haarcascade_upperbody.xml")

            if Path(frontal_path).exists():
                self._cascade_frontal = cv2.CascadeClassifier(frontal_path)
            if Path(profile_path).exists():
                self._cascade_profile = cv2.CascadeClassifier(profile_path)
            if Path(body_path).exists():
                self._cascade_body = cv2.CascadeClassifier(body_path)

            logger.info("Loaded OpenCV Haar cascades for face & body detection")
        except Exception as e:
            logger.warning("Could not initialize Haar cascades: %s", e)

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
        img_path: Path,
        timestamp: float,
        source_w: int,
        source_h: int,
    ) -> List[DetectedSubject]:
        """Detect faces and subjects in a sampled frame using OpenCV or fallback."""
        detections: List[DetectedSubject] = []

        if _OPENCV_AVAILABLE and self._cascade_frontal:
            try:
                img = cv2.imread(str(img_path))
                if img is not None:
                    # Resize for CPU speed if very large
                    h, w = img.shape[:2]
                    scale_x = source_w / w
                    scale_y = source_h / h

                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    gray = cv2.equalizeHist(gray)

                    # 1. Frontal faces
                    faces = self._cascade_frontal.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=4,
                        minSize=(int(source_w * 0.05), int(source_h * 0.05)),
                    )

                    for (x, y, fw, fh) in faces:
                        detections.append(
                            DetectedSubject(
                                timestamp=timestamp,
                                box_x=round(x * scale_x, 1),
                                box_y=round(y * scale_y, 1),
                                box_w=round(fw * scale_x, 1),
                                box_h=round(fh * scale_y, 1),
                                confidence=0.88,
                                category="face",
                            )
                        )

                    # 2. Profile faces if no frontal faces found
                    if not detections and self._cascade_profile:
                        profiles = self._cascade_profile.detectMultiScale(
                            gray,
                            scaleFactor=1.1,
                            minNeighbors=3,
                            minSize=(int(source_w * 0.05), int(source_h * 0.05)),
                        )
                        for (x, y, fw, fh) in profiles:
                            detections.append(
                                DetectedSubject(
                                    timestamp=timestamp,
                                    box_x=round(x * scale_x, 1),
                                    box_y=round(y * scale_y, 1),
                                    box_w=round(fw * scale_x, 1),
                                    box_h=round(fh * scale_y, 1),
                                    confidence=0.75,
                                    category="face",
                                )
                            )

                    # 3. Upper body if no faces found
                    if not detections and self._cascade_body:
                        bodies = self._cascade_body.detectMultiScale(
                            gray,
                            scaleFactor=1.1,
                            minNeighbors=3,
                            minSize=(int(source_w * 0.1), int(source_h * 0.15)),
                        )
                        for (x, y, bw, bh) in bodies:
                            detections.append(
                                DetectedSubject(
                                    timestamp=timestamp,
                                    box_x=round(x * scale_x, 1),
                                    box_y=round(y * scale_y, 1),
                                    box_w=round(bw * scale_x, 1),
                                    box_h=round(bh * scale_y, 1),
                                    confidence=0.70,
                                    category="upper_body",
                                )
                            )
            except Exception as e:
                logger.debug("OpenCV detection error at t=%.2f: %s", timestamp, e)

        # Fallback: Center-weighted visual saliency
        if not detections:
            # Plausible central third region
            bw = source_w * 0.35
            bh = source_h * 0.45
            bx = (source_w - bw) / 2.0
            by = source_h * 0.2
            detections.append(
                DetectedSubject(
                    timestamp=timestamp,
                    box_x=round(bx, 1),
                    box_y=round(by, 1),
                    box_w=round(bw, 1),
                    box_h=round(bh, 1),
                    confidence=0.50,
                    category="saliency",
                )
            )

        return detections

    def track_subjects_across_samples(
        self,
        samples: List[Tuple[float, Path]],
        source_w: int,
        source_h: int,
        scene_cut_timestamps: Optional[List[float]] = None,
    ) -> List[SubjectTrack]:
        """Associate detections across temporal samples into stable SubjectTracks."""
        scene_cuts = sorted(scene_cut_timestamps or [])
        tracks: List[SubjectTrack] = []
        active_tracks: List[SubjectTrack] = []
        next_track_id = 1

        for timestamp, img_path in samples:
            # Check if this timestamp crossed a scene cut
            cut_occurred = False
            while scene_cuts and scene_cuts[0] <= timestamp:
                cut_time = scene_cuts.pop(0)
                # If cut happened strictly between previous frame and this frame
                cut_occurred = True

            if cut_occurred:
                # Terminate all active tracks across scene cut boundary
                for trk in active_tracks:
                    trk.is_active = False
                active_tracks = []

            # Detect in current frame
            detections = self.detect_subjects_in_frame(img_path, timestamp, source_w, source_h)

            matched_detection_indices = set()
            unmatched_tracks = []

            # Try matching with active tracks using IoU & centroid proximity
            for trk in active_tracks:
                best_match_idx = None
                best_score = -1.0
                last_det = trk.detections[-1]
                last_box = (last_det.box_x, last_det.box_y, last_det.box_w, last_det.box_h)

                for idx, det in enumerate(detections):
                    if idx in matched_detection_indices:
                        continue
                    cur_box = (det.box_x, det.box_y, det.box_w, det.box_h)
                    iou = _compute_iou(last_box, cur_box)

                    # Normalized centroid distance (0.0 to 1.0)
                    cx_diff = abs(det.center_x - last_det.center_x) / source_w
                    cy_diff = abs(det.center_y - last_det.center_y) / source_h
                    dist_score = max(0.0, 1.0 - math.sqrt(cx_diff**2 + cy_diff**2))

                    combined_score = (iou * 0.6) + (dist_score * 0.4)

                    if combined_score > 0.35 and combined_score > best_score:
                        best_score = combined_score
                        best_match_idx = idx

                if best_match_idx is not None:
                    matched_det = detections[best_match_idx]
                    matched_det.subject_id = trk.track_id
                    trk.detections.append(matched_det)
                    trk.last_seen = timestamp
                    matched_detection_indices.add(best_match_idx)
                else:
                    unmatched_tracks.append(trk)

            # Handle detection gaps: carry forward or terminate
            for trk in unmatched_tracks:
                if (timestamp - trk.last_seen) <= self.gap_tolerance:
                    # Bridge gap with decaying confidence
                    last_det = trk.detections[-1]
                    decayed_det = DetectedSubject(
                        timestamp=timestamp,
                        box_x=last_det.box_x,
                        box_y=last_det.box_y,
                        box_w=last_det.box_w,
                        box_h=last_det.box_h,
                        confidence=round(last_det.confidence * 0.8, 2),
                        category=last_det.category,
                        subject_id=trk.track_id,
                    )
                    trk.detections.append(decayed_det)
                else:
                    trk.is_active = False

            # Remove inactive tracks
            active_tracks = [t for t in active_tracks if t.is_active]

            # Spawn new tracks for remaining unmatched detections
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

        # Compute average confidence for each track
        for trk in tracks:
            if trk.detections:
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
                                box_x=source_w * 0.35,
                                box_y=source_h * 0.2,
                                box_w=source_w * 0.3,
                                box_h=source_h * 0.4,
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
