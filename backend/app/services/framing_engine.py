"""Authoritative portrait crop geometry, multi-strategy framing, and trajectory smoothing."""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from app.models.reframing import CropKeyframe, DetectedSubject, SubjectTrack

logger = logging.getLogger("zezedit.reframing.engine")

ASPECT_RATIOS = {
    "9:16": (9, 16),
    "1:1": (1, 1),
    "16:9": (16, 9),
    "4:5": (4, 5),
}


class FramingEngine:
    """Calculates authoritative portrait crop geometry, tracks framing targets,

    and applies scene-cut aware trajectory smoothing.
    """

    def __init__(
        self,
        target_aspect_ratio: str = "9:16",
        base_zoom: float = 1.0,
        headroom_factor: float = 0.15,
        smoothing_window_seconds: float = 0.8,
        max_pan_velocity_pct: float = 0.5,  # Max fraction of source width moved per second
    ) -> None:
        self.target_aspect_ratio = target_aspect_ratio
        self.ar_w, self.ar_h = ASPECT_RATIOS.get(target_aspect_ratio, (9, 16))
        self.base_zoom = max(0.8, min(2.5, base_zoom))
        self.headroom_factor = max(0.05, min(0.35, headroom_factor))
        self.smoothing_window = max(0.2, min(3.0, smoothing_window_seconds))
        self.max_pan_velocity = max_pan_velocity_pct

    def calculate_crop_dimensions(
        self,
        source_w: int,
        source_h: int,
        zoom: float = 1.0,
    ) -> Tuple[int, int]:
        """Compute crop window width and height for target aspect ratio, rounded to even numbers."""
        effective_zoom = max(0.7, min(3.0, zoom))
        aspect = self.ar_w / self.ar_h

        # Height-dominant calculation (standard for vertical portrait crop from landscape)
        raw_crop_h = source_h / effective_zoom
        raw_crop_w = raw_crop_h * aspect

        # If computed width exceeds source width (e.g. wide aspect ratio or already portrait source)
        if raw_crop_w > source_w:
            raw_crop_w = float(source_w)
            raw_crop_h = raw_crop_w / aspect

        # Clamp within source bounds
        raw_crop_w = min(float(source_w), raw_crop_w)
        raw_crop_h = min(float(source_h), raw_crop_h)

        # Round down to nearest even integer for encoder compatibility
        crop_w = int(raw_crop_w // 2) * 2
        crop_h = int(raw_crop_h // 2) * 2

        return max(2, crop_w), max(2, crop_h)

    def select_framing_target(
        self,
        tracks: List[SubjectTrack],
        timestamp: float,
        source_w: int,
        source_h: int,
        preferred_strategy: str = "auto",
        pinned_subject_id: Optional[str] = None,
    ) -> Tuple[float, float, str, int, List[str]]:
        """Determine target center (x, y), effective strategy, subject count, and warnings

        for a specific timestamp.
        """
        warnings: List[str] = []

        # Find active subjects at this timestamp (within ±0.5s of detection)
        active_dets: List[DetectedSubject] = []
        for trk in tracks:
            # Find detection closest in time
            matching = [d for d in trk.detections if abs(d.timestamp - timestamp) <= 0.6]
            if matching:
                best = min(matching, key=lambda d: abs(d.timestamp - timestamp))
                active_dets.append(best)

        # If user pinned a specific subject / character
        if pinned_subject_id:
            pinned = [d for d in active_dets if d.subject_id == pinned_subject_id]
            if pinned:
                d = pinned[0]
                target_x = d.center_x
                target_y = max(0.0, d.box_y - (self.headroom_factor * source_h)) + (d.box_h / 2.0)
                return target_x, target_y, "single_subject", 1, warnings
            else:
                # Character was temporarily obscured; maintain closest observation from track
                for trk in tracks:
                    if trk.subject_id == pinned_subject_id and trk.detections:
                        closest = min(trk.detections, key=lambda d: abs(d.timestamp - timestamp))
                        if abs(closest.timestamp - timestamp) <= 3.0:
                            target_x = closest.center_x
                            target_y = max(0.0, closest.box_y - (self.headroom_factor * source_h)) + (closest.box_h / 2.0)
                            return target_x, target_y, "single_subject", 1, warnings

        subject_count = len(active_dets)

        # Fallback if no subjects detected
        if subject_count == 0:
            warnings.append(f"No subjects detected at t={timestamp:.2f}s; applied center fallback")
            return (source_w / 2.0, source_h / 2.0, "fallback", 0, warnings)

        # Single subject framing / Primary subject framing
        if subject_count == 1 or preferred_strategy in ("single_subject", "primary_subject"):
            # Select most prominent subject by (confidence, area)
            d = max(active_dets, key=lambda x: (x.confidence, x.box_w * x.box_h))
            target_x = d.center_x
            target_y = max(0.0, d.box_y - (self.headroom_factor * source_h * 0.5)) + (d.box_h / 2.0)
            return target_x, target_y, "single_subject", 1, warnings

        # Object tracking / action object
        if preferred_strategy in ("action_object", "object_tracking"):
            obj_dets = [d for d in active_dets if d.category in ("object", "vehicle", "animal")]
            target_det = max(obj_dets, key=lambda x: (x.confidence, x.box_w * x.box_h)) if obj_dets else active_dets[0]
            target_x = target_det.center_x
            target_y = max(0.0, target_det.box_y - (self.headroom_factor * source_h * 0.5)) + (target_det.box_h / 2.0)
            return target_x, target_y, "action_object", 1, warnings

        # Two-person framing
        if preferred_strategy == "two_person" or subject_count == 2:
            sorted_dets = sorted(active_dets, key=lambda x: (x.confidence, x.box_w * x.box_h), reverse=True)
            d1, d2 = sorted_dets[0], sorted_dets[1]
            min_x = min(d1.box_x, d2.box_x)
            max_x = max(d1.box_x + d1.box_w, d2.box_x + d2.box_w)
            spread_x = max_x - min_x

            # Check if both can fit in portrait crop
            crop_w, _ = self.calculate_crop_dimensions(source_w, source_h, self.base_zoom)
            if spread_x <= crop_w * 0.95:
                # Joint region framing
                target_x = (min_x + max_x) / 2.0
                target_y = min(d1.center_y, d2.center_y)
                return target_x, target_y, "two_person", 2, warnings
            else:
                # Subjects are too far apart for standard portrait crop
                warnings.append(f"Two subjects spread ({spread_x:.0f}px) exceeds portrait width ({crop_w}px)")
                target_x = (min_x + max_x) / 2.0
                target_y = min(d1.center_y, d2.center_y)
                return target_x, target_y, "two_person", 2, warnings

        # Group framing / all subjects (3+ subjects or explicit all_subjects / group)
        min_x = min(d.box_x for d in active_dets)
        max_x = max(d.box_x + d.box_w for d in active_dets)
        group_w = max_x - min_x
        crop_w, _ = self.calculate_crop_dimensions(source_w, source_h, self.base_zoom)

        if group_w > crop_w:
            warnings.append(f"Group width ({group_w:.0f}px) wider than crop ({crop_w}px); safe centered crop")

        target_x = (min_x + max_x) / 2.0
        target_y = sum(d.center_y for d in active_dets) / subject_count
        return target_x, target_y, "group", subject_count, warnings

    def clamp_crop_rect(
        self,
        center_x: float,
        center_y: float,
        crop_w: int,
        crop_h: int,
        source_w: int,
        source_h: int,
    ) -> Tuple[int, int]:
        """Convert center coordinates to clamped top-left (crop_x, crop_y).

        Guarantees that crop window stays strictly inside [0, source_w] and [0, source_h].
        """
        raw_x = center_x - (crop_w / 2.0)
        raw_y = center_y - (crop_h / 2.0)

        max_x = max(0, source_w - crop_w)
        max_y = max(0, source_h - crop_h)

        clamped_x = max(0.0, min(float(max_x), raw_x))
        clamped_y = max(0.0, min(float(max_y), raw_y))

        # Round to even integer
        final_x = int(round(clamped_x / 2.0)) * 2
        final_y = int(round(clamped_y / 2.0)) * 2

        # Final sanity clamp
        final_x = min(max_x, max(0, final_x))
        final_y = min(max_y, max(0, final_y))

        return final_x, final_y

    def smooth_crop_trajectory(
        self,
        raw_keyframes: List[CropKeyframe],
        source_w: int,
        source_h: int,
        scene_cut_timestamps: Optional[List[float]] = None,
    ) -> List[CropKeyframe]:
        """Apply velocity-constrained moving average smoothing to crop positions.

        CRITICAL: Never smooths across scene boundaries. Camera jumps instantly at scene cuts.
        """
        if len(raw_keyframes) <= 1:
            return raw_keyframes

        scene_cuts = set(round(t, 2) for t in (scene_cut_timestamps or []))

        # Split keyframes into disjoint segments by scene cuts
        segments: List[List[CropKeyframe]] = []
        current_segment: List[CropKeyframe] = []

        for kf in raw_keyframes:
            # If current keyframe is near a scene cut, end segment
            is_cut = any(abs(kf.timestamp - c) <= 0.2 for c in scene_cuts)
            if is_cut and current_segment:
                segments.append(current_segment)
                current_segment = []
                kf.is_scene_boundary = True

            current_segment.append(kf)

        if current_segment:
            segments.append(current_segment)

        smoothed_all: List[CropKeyframe] = []

        # Smooth each scene segment independently
        for seg in segments:
            if len(seg) <= 2:
                smoothed_all.extend(seg)
                continue

            # Moving average window
            half_window = max(1, int(round((self.smoothing_window * 0.5) * (len(seg) / max(0.1, seg[-1].timestamp - seg[0].timestamp)))))
            seg_smoothed: List[CropKeyframe] = []

            for i in range(len(seg)):
                cur_kf = seg[i]
                if cur_kf.is_manual_override:
                    # Never smooth away a manual user override
                    seg_smoothed.append(cur_kf)
                    continue

                start_idx = max(0, i - half_window)
                end_idx = min(len(seg), i + half_window + 1)
                window_slice = seg[start_idx:end_idx]

                avg_target_x = sum(k.target_center_x or (k.crop_x + k.crop_w / 2.0) for k in window_slice) / len(window_slice)
                avg_target_y = sum(k.target_center_y or (k.crop_y + k.crop_h / 2.0) for k in window_slice) / len(window_slice)

                # Clamp previous velocity if available
                if seg_smoothed:
                    prev_kf = seg_smoothed[-1]
                    dt = max(0.01, cur_kf.timestamp - prev_kf.timestamp)
                    max_move = self.max_pan_velocity * source_w * dt

                    prev_center_x = prev_kf.crop_x + (prev_kf.crop_w / 2.0)
                    delta_x = avg_target_x - prev_center_x
                    if abs(delta_x) > max_move:
                        avg_target_x = prev_center_x + (math.copysign(max_move, delta_x))

                # Recompute clamped crop rect
                crop_x, crop_y = self.clamp_crop_rect(
                    center_x=avg_target_x,
                    center_y=avg_target_y,
                    crop_w=cur_kf.crop_w,
                    crop_h=cur_kf.crop_h,
                    source_w=source_w,
                    source_h=source_h,
                )

                smoothed_kf = CropKeyframe(
                    timestamp=cur_kf.timestamp,
                    crop_x=crop_x,
                    crop_y=crop_y,
                    crop_w=cur_kf.crop_w,
                    crop_h=cur_kf.crop_h,
                    zoom=cur_kf.zoom,
                    headroom=cur_kf.headroom,
                    subject_count=cur_kf.subject_count,
                    framing_strategy=cur_kf.framing_strategy,
                    is_scene_boundary=cur_kf.is_scene_boundary,
                    is_manual_override=cur_kf.is_manual_override,
                    target_center_x=round(avg_target_x, 1),
                    target_center_y=round(avg_target_y, 1),
                )
                seg_smoothed.append(smoothed_kf)

            smoothed_all.extend(seg_smoothed)

        return smoothed_all

    def generate_framing_keyframes(
        self,
        tracks: List[SubjectTrack],
        start_time: float,
        end_time: float,
        source_w: int,
        source_h: int,
        keyframe_interval: float = 0.25,  # 4 keyframes per second
        scene_cut_timestamps: Optional[List[float]] = None,
        manual_overrides: Optional[List[Dict[str, Any]]] = None,
        preferred_strategy: str = "auto",
        pinned_subject_id: Optional[str] = None,
    ) -> Tuple[List[CropKeyframe], List[str]]:
        """Generate authoritative time-varying crop keyframe trajectory for clip interval."""
        all_warnings: List[str] = []
        raw_keyframes: List[CropKeyframe] = []
        overrides_by_time = {round(ov["timestamp"], 2): ov for ov in (manual_overrides or [])}

        duration = max(0.5, end_time - start_time)
        t = start_time

        crop_w, crop_h = self.calculate_crop_dimensions(source_w, source_h, self.base_zoom)

        while t <= end_time + 0.05:
            timestamp = round(t, 3)

            # Check for manual user override at or near this timestamp
            matching_ov = None
            for ov_t, ov_data in overrides_by_time.items():
                if abs(ov_t - timestamp) <= (keyframe_interval * 0.6):
                    matching_ov = ov_data
                    break

            if matching_ov:
                # Use user's manual adjustments
                ov_zoom = matching_ov.get("zoom", self.base_zoom)
                ov_cw, ov_ch = self.calculate_crop_dimensions(source_w, source_h, ov_zoom)
                ov_cx = matching_ov.get("crop_x")
                ov_cy = matching_ov.get("crop_y")

                if ov_cx is None or ov_cy is None:
                    # Centered on override target
                    target_x = matching_ov.get("target_center_x", source_w / 2.0)
                    target_y = matching_ov.get("target_center_y", source_h / 2.0)
                    ov_cx, ov_cy = self.clamp_crop_rect(target_x, target_y, ov_cw, ov_ch, source_w, source_h)

                kf = CropKeyframe(
                    timestamp=timestamp,
                    crop_x=int(ov_cx),
                    crop_y=int(ov_cy),
                    crop_w=ov_cw,
                    crop_h=ov_ch,
                    zoom=ov_zoom,
                    headroom=matching_ov.get("headroom", self.headroom_factor),
                    subject_count=1,
                    framing_strategy="manual",
                    is_manual_override=True,
                    target_center_x=ov_cx + (ov_cw / 2.0),
                    target_center_y=ov_cy + (ov_ch / 2.0),
                )
                raw_keyframes.append(kf)
            else:
                # Automatic AI framing (honoring pinned subject / character focus)
                target_x, target_y, strat, scount, warns = self.select_framing_target(
                    tracks=tracks,
                    timestamp=timestamp,
                    source_w=source_w,
                    source_h=source_h,
                    preferred_strategy=preferred_strategy,
                    pinned_subject_id=pinned_subject_id,
                )
                all_warnings.extend(warns)

                cx, cy = self.clamp_crop_rect(target_x, target_y, crop_w, crop_h, source_w, source_h)

                kf = CropKeyframe(
                    timestamp=timestamp,
                    crop_x=cx,
                    crop_y=cy,
                    crop_w=crop_w,
                    crop_h=crop_h,
                    zoom=self.base_zoom,
                    headroom=self.headroom_factor,
                    subject_count=scount,
                    framing_strategy=strat,
                    target_center_x=round(target_x, 1),
                    target_center_y=round(target_y, 1),
                )
                raw_keyframes.append(kf)

            t += keyframe_interval

        # Apply trajectory smoothing with scene cut boundary awareness
        smoothed_keyframes = self.smooth_crop_trajectory(
            raw_keyframes=raw_keyframes,
            source_w=source_w,
            source_h=source_h,
            scene_cut_timestamps=scene_cut_timestamps,
        )

        # Deduplicate warnings
        unique_warnings = list(dict.fromkeys(all_warnings))
        return smoothed_keyframes, unique_warnings

    @staticmethod
    def interpolate_crop_at(
        keyframes: List[CropKeyframe],
        timestamp: float,
    ) -> Dict[str, Any]:
        """Interpolate exact crop geometry at any continuous timestamp.

        Used by both the interactive frontend preview and the rendering verification checker.
        """
        if not keyframes:
            return {"crop_x": 0, "crop_y": 0, "crop_w": 1080, "crop_h": 1920, "zoom": 1.0}

        if timestamp <= keyframes[0].timestamp:
            k = keyframes[0]
            return {
                "crop_x": k.crop_x,
                "crop_y": k.crop_y,
                "crop_w": k.crop_w,
                "crop_h": k.crop_h,
                "zoom": k.zoom,
                "strategy": k.framing_strategy,
            }

        if timestamp >= keyframes[-1].timestamp:
            k = keyframes[-1]
            return {
                "crop_x": k.crop_x,
                "crop_y": k.crop_y,
                "crop_w": k.crop_w,
                "crop_h": k.crop_h,
                "zoom": k.zoom,
                "strategy": k.framing_strategy,
            }

        # Find enclosing pair
        for i in range(len(keyframes) - 1):
            k1 = keyframes[i]
            k2 = keyframes[i + 1]

            if k1.timestamp <= timestamp <= k2.timestamp:
                # If k2 is a scene boundary cut, snap directly without interpolation
                if k2.is_scene_boundary:
                    k = k2 if (timestamp - k1.timestamp) > (k2.timestamp - timestamp) else k1
                    return {
                        "crop_x": k.crop_x,
                        "crop_y": k.crop_y,
                        "crop_w": k.crop_w,
                        "crop_h": k.crop_h,
                        "zoom": k.zoom,
                        "strategy": k.framing_strategy,
                    }

                span = max(0.001, k2.timestamp - k1.timestamp)
                alpha = (timestamp - k1.timestamp) / span

                interp_x = int(round(k1.crop_x + alpha * (k2.crop_x - k1.crop_x)))
                interp_y = int(round(k1.crop_y + alpha * (k2.crop_y - k1.crop_y)))
                interp_w = int(round(k1.crop_w + alpha * (k2.crop_w - k1.crop_w)))
                interp_h = int(round(k1.crop_h + alpha * (k2.crop_h - k1.crop_h)))
                interp_zoom = round(k1.zoom + alpha * (k2.zoom - k1.zoom), 3)

                return {
                    "crop_x": interp_x,
                    "crop_y": interp_y,
                    "crop_w": interp_w,
                    "crop_h": interp_h,
                    "zoom": interp_zoom,
                    "strategy": k1.framing_strategy,
                }

        k = keyframes[-1]
        return {
            "crop_x": k.crop_x,
            "crop_y": k.crop_y,
            "crop_w": k.crop_w,
            "crop_h": k.crop_h,
            "zoom": k.zoom,
            "strategy": k.framing_strategy,
        }
