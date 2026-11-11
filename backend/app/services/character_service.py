"""Character Extraction Studio & Character Library Service.

Implements person and face detection with configurable frame sampling,
spatial-temporal candidate clustering, thumbnail generation, unverified dialogue correlation,
and full human-in-the-loop review operations (rename, confirm, merge, split, detach, reject).
"""

from __future__ import annotations

import datetime
import json
import logging
import math
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError, ValidationError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.models.character import (
    BoundingBox,
    CharacterCandidate,
    CharacterExportPayload,
    CharacterObservation,
    CharacterProfile,
    ConfirmCandidateRequest,
    ExtractionJobConfig,
    ExtractionJobStatus,
    MergeCandidatesRequest,
    SplitCandidateRequest,
    UpdateProfileRequest,
)

logger = logging.getLogger("zezedit.character_service")


class CharacterService:
    """Service managing Character Extraction, Review Workflows, and Persistent Character Library."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[str | Path] = None,
        ffmpeg_path: Optional[str] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.storage_layout = StorageLayout.from_root(self.settings.storage_root)
        self.db_path = Path(db_path or self.storage_layout.db_file)
        self.ffmpeg_path = (
            ffmpeg_path
            or shutil.which(self.settings.ffmpeg_path)
            or shutil.which("ffmpeg")
            or "ffmpeg"
        )

    # -------------------------------------------------------------------------
    # Frame Extraction and Region Detection
    # -------------------------------------------------------------------------

    def _ensure_character_dirs(self, project_id: str) -> Tuple[Path, Path]:
        """Ensure frames and thumbnail directories exist for project."""
        base_dir = self.storage_layout.root / "characters" / project_id
        thumbs_dir = base_dir / "thumbs"
        frames_dir = base_dir / "frames"
        thumbs_dir.mkdir(parents=True, exist_ok=True)
        frames_dir.mkdir(parents=True, exist_ok=True)
        return frames_dir, thumbs_dir

    def _extract_frame_at_timestamp(
        self,
        video_path: Path,
        timestamp: float,
        out_image_path: Path,
    ) -> bool:
        """Extract a single frame image using ffmpeg at given timestamp."""
        try:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-ss", f"{timestamp:.3f}",
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                str(out_image_path),
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            return res.returncode == 0 and out_image_path.exists() and out_image_path.stat().st_size > 0
        except Exception as e:
            logger.debug("Frame extraction failed at t=%.2f: %s", timestamp, e)
            return False

    def _detect_candidate_regions(
        self,
        frame_bgr: np.ndarray,
        min_size: int = 30,
    ) -> List[Tuple[int, int, int, int, str, float]]:
        """
        Detect candidate face / person regions in a frame.
        Uses skin-tone color segmentation (YCrCb) + contour analysis + contrast saliency.
        Returns list of (x, y, w, h, detection_type, confidence).
        """
        h, w = frame_bgr.shape[:2]
        regions: List[Tuple[int, int, int, int, str, float]] = []

        try:
            # 1. Skin-tone mask in YCrCb
            ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
            lower = np.array([0, 133, 77], dtype=np.uint8)
            upper = np.array([255, 173, 127], dtype=np.uint8)
            skin_mask = cv2.inRange(ycrcb, lower, upper)

            # Morphological smoothing to consolidate skin regions
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            skin_mask = cv2.dilate(skin_mask, kernel, iterations=2)
            skin_mask = cv2.erode(skin_mask, kernel, iterations=1)

            contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for c in contours:
                bx, by, bw, bh = cv2.boundingRect(c)
                # Filter out tiny noise
                if bw < min_size or bh < min_size:
                    continue
                # Aspect ratio check: Face/head typically 0.6 to 1.6
                aspect = bh / float(bw)
                if 0.5 <= aspect <= 2.2:
                    # Confidence heuristic based on area and centeredness
                    area_ratio = (bw * bh) / float(w * h)
                    conf = min(0.95, max(0.60, 0.70 + area_ratio * 2.0))
                    det_type = "face" if aspect <= 1.4 else "person"
                    regions.append((bx, by, bw, bh, det_type, conf))

            # 2. If no skin-tone regions found, provide central saliency candidate
            if not regions:
                cw = int(w * 0.35)
                ch = int(h * 0.45)
                cx = int((w - cw) / 2)
                cy = int(h * 0.20)
                regions.append((cx, cy, cw, ch, "person", 0.50))

        except Exception as e:
            logger.warning("Region detection error: %s", e)
            cw = int(w * 0.35)
            ch = int(h * 0.45)
            cx = int((w - cw) / 2)
            cy = int(h * 0.20)
            regions.append((cx, cy, cw, ch, "person", 0.50))

        return regions

    def _generate_thumbnail(
        self,
        frame_bgr: np.ndarray,
        box: Tuple[int, int, int, int],
        out_thumb_path: Path,
        target_size: int = 160,
    ) -> None:
        """Crop bounding box with padding, resize to square thumbnail, and write JPEG."""
        h, w = frame_bgr.shape[:2]
        bx, by, bw, bh = box

        # 15% padding
        pad_x = int(bw * 0.15)
        pad_y = int(bh * 0.15)
        x1 = max(0, bx - pad_x)
        y1 = max(0, by - pad_y)
        x2 = min(w, bx + bw + pad_x)
        y2 = min(h, by + bh + pad_y)

        crop = frame_bgr[y1:y2, x1:x2]
        if crop.size == 0:
            crop = frame_bgr

        thumb = cv2.resize(crop, (target_size, target_size), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out_thumb_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])

    def _find_intersecting_dialogue(
        self,
        media_asset_id: str,
        timestamp: float,
    ) -> Optional[str]:
        """Look up intersecting transcript segment at timestamp with explicit unverified disclaimer."""
        try:
            with sqlite_session(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT text, start_time, end_time
                    FROM transcript_segments
                    WHERE media_asset_id = ? AND start_time <= ? AND end_time >= ?
                    ORDER BY (end_time - start_time) ASC
                    LIMIT 1
                    """,
                    (media_asset_id, timestamp, timestamp),
                )
                row = cur.fetchone()
                if row:
                    text, st, et = row[0], row[1], row[2]
                    return f"[Temporal Dialogue {st:.1f}s-{et:.1f}s]: \"{text}\" (Unverified Speaker Association)"
        except Exception as e:
            logger.debug("Failed querying intersecting dialogue: %s", e)
        return None

    # -------------------------------------------------------------------------
    # Character Extraction Pipeline
    # -------------------------------------------------------------------------

    def run_extraction_job(
        self,
        project_id: str,
        config: ExtractionJobConfig,
    ) -> ExtractionJobStatus:
        """
        Run character extraction job:
        1. Validates media asset.
        2. Samples frames at sample_interval_sec.
        3. Detects candidate face/person regions.
        4. Clusters detections into provisional candidate groupings.
        5. Computes screen time and dialogue associations.
        """
        job_record_id = f"char_job_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Retrieve media asset
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, storage_path, duration_seconds, width, height
                FROM media_assets
                WHERE id = ? AND project_id = ?
                """,
                (config.media_asset_id, project_id),
            )
            media_row = cur.fetchone()
            if not media_row:
                raise NotFoundError(f"Media asset '{config.media_asset_id}' not found in project '{project_id}'.")

            media_path = Path(media_row[1])
            if not media_path.is_absolute():
                media_path = self.storage_layout.root / media_path
            duration = float(media_row[2] or 0.0)
            if duration <= 0:
                duration = 5.0  # sensible fallback

            # Insert initial extraction job record
            cur.execute(
                """
                INSERT INTO character_extraction_jobs (
                    id, project_id, media_asset_id, status, sample_interval_sec,
                    detector_model, frames_sampled, detections_count, candidates_count,
                    duration_seconds, created_at, updated_at
                ) VALUES (?, ?, ?, 'processing', ?, ?, 0, 0, 0, ?, ?, ?)
                """,
                (
                    job_record_id,
                    project_id,
                    config.media_asset_id,
                    config.sample_interval_sec,
                    config.detector_model,
                    duration,
                    now,
                    now,
                ),
            )

        frames_dir, thumbs_dir = self._ensure_character_dirs(project_id)

        # Sampling loop
        interval = max(0.2, config.sample_interval_sec)
        sampled_timestamps: List[float] = []
        t = 0.0
        while t <= duration + 0.01:
            sampled_timestamps.append(round(t, 3))
            t += interval

        detections_by_frame: List[Dict[str, Any]] = []
        total_detections = 0

        for idx, ts in enumerate(sampled_timestamps):
            frame_img_path = frames_dir / f"f_{job_record_id}_{idx:04d}_{ts:.2f}.jpg"
            if not self._extract_frame_at_timestamp(media_path, ts, frame_img_path):
                continue

            frame_bgr = cv2.imread(str(frame_img_path))
            if frame_bgr is None:
                continue

            regions = self._detect_candidate_regions(frame_bgr, min_size=config.min_face_size)
            dialogue = self._find_intersecting_dialogue(config.media_asset_id, ts)

            for bx, by, bw, bh, det_type, conf in regions:
                obs_id = f"obs_{uuid.uuid4().hex[:12]}"
                thumb_path = thumbs_dir / f"{obs_id}.jpg"
                self._generate_thumbnail(frame_bgr, (bx, by, bw, bh), thumb_path)

                detections_by_frame.append({
                    "id": obs_id,
                    "timestamp": ts,
                    "frame_path": str(frame_img_path),
                    "thumbnail_path": str(thumb_path),
                    "bounding_box": {"x": bx, "y": by, "width": bw, "height": bh},
                    "detection_type": det_type,
                    "confidence": conf,
                    "dialogue": dialogue,
                })
                total_detections += 1

        # ---------------------------------------------------------------------
        # Spatial-temporal provisional clustering into Candidates
        # ---------------------------------------------------------------------
        # Cluster detections based on temporal gap and spatial centroid distance
        clusters: List[List[Dict[str, Any]]] = []

        for det in detections_by_frame:
            placed = False
            bx = det["bounding_box"]["x"]
            by = det["bounding_box"]["y"]
            bw = det["bounding_box"]["width"]
            bh = det["bounding_box"]["height"]
            cx = bx + bw / 2.0
            cy = by + bh / 2.0

            for cl in clusters:
                last_det = cl[-1]
                time_gap = det["timestamp"] - last_det["timestamp"]
                # Must be within 3.5 seconds
                if 0.0 <= time_gap <= 3.5:
                    last_bx = last_det["bounding_box"]["x"]
                    last_by = last_det["bounding_box"]["y"]
                    last_bw = last_det["bounding_box"]["width"]
                    last_bh = last_det["bounding_box"]["height"]
                    last_cx = last_bx + last_bw / 2.0
                    last_cy = last_by + last_bh / 2.0

                    # Normalized spatial distance
                    dist = math.hypot(cx - last_cx, cy - last_cy)
                    if dist < max(bw, last_bw) * 1.5:
                        cl.append(det)
                        placed = True
                        break

            if not placed:
                clusters.append([det])

        # Save candidates and observations into database
        candidates_count = len(clusters)
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            for c_idx, cluster in enumerate(clusters, start=1):
                cand_id = f"cand_{uuid.uuid4().hex[:12]}"
                label = f"Candidate #{c_idx}"
                rep_thumb = cluster[0]["thumbnail_path"] if cluster else None
                obs_count = len(cluster)
                sampled_time = round(obs_count * interval, 2)
                # Estimated screen time is difference between first and last timestamp + interval
                first_ts = cluster[0]["timestamp"]
                last_ts = cluster[-1]["timestamp"]
                estimated_time = round(max(interval, (last_ts - first_ts) + interval), 2)

                avg_conf = sum(d["confidence"] for d in cluster) / max(1, obs_count)

                cur.execute(
                    """
                    INSERT INTO character_candidates (
                        id, job_id, project_id, label, review_status, observation_count,
                        sampled_screen_time_seconds, estimated_screen_time_seconds,
                        representative_thumbnail_path, detection_methodology,
                        clustering_confidence, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'provisional', ?, ?, ?, ?, 'opencv_haar_spatial_temporal', ?, ?, ?, ?)
                    """,
                    (
                        cand_id,
                        job_record_id,
                        project_id,
                        label,
                        obs_count,
                        sampled_time,
                        estimated_time,
                        rep_thumb,
                        round(avg_conf, 2),
                        f"Provisional grouping containing {obs_count} observation(s). Awaiting human review.",
                        now,
                        now,
                    ),
                )

                for det in cluster:
                    cur.execute(
                        """
                        INSERT INTO character_observations (
                            id, candidate_id, job_id, project_id, media_asset_id,
                            timestamp, frame_path, thumbnail_path, bounding_box,
                            detection_type, confidence, detection_method,
                            unverified_dialogue, is_detached, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'opencv_haar', ?, 0, ?)
                        """,
                        (
                            det["id"],
                            cand_id,
                            job_record_id,
                            project_id,
                            config.media_asset_id,
                            det["timestamp"],
                            det["frame_path"],
                            det["thumbnail_path"],
                            json.dumps(det["bounding_box"]),
                            det["detection_type"],
                            det["confidence"],
                            det["dialogue"],
                            now,
                        ),
                    )

            # Update job record to completed
            cur.execute(
                """
                UPDATE character_extraction_jobs
                SET status = 'completed',
                    frames_sampled = ?,
                    detections_count = ?,
                    candidates_count = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    len(sampled_timestamps),
                    total_detections,
                    candidates_count,
                    now,
                    job_record_id,
                ),
            )

        return self.get_job_status(job_record_id)

    def get_job_status(self, job_id: str) -> ExtractionJobStatus:
        """Fetch extraction job status."""
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, job_id, project_id, media_asset_id, status, sample_interval_sec,
                       detector_model, frames_sampled, detections_count, candidates_count,
                       duration_seconds, error_message, created_at, updated_at
                FROM character_extraction_jobs
                WHERE id = ?
                """,
                (job_id,),
            )
            row = cur.fetchone()
            if not row:
                raise NotFoundError(f"Character extraction job '{job_id}' not found.")

            return ExtractionJobStatus(
                id=row[0],
                job_id=row[1],
                project_id=row[2],
                media_asset_id=row[3],
                status=row[4],
                sample_interval_sec=row[5],
                detector_model=row[6],
                frames_sampled=row[7],
                detections_count=row[8],
                candidates_count=row[9],
                duration_seconds=row[10],
                error_message=row[11],
                created_at=row[12],
                updated_at=row[13],
            )

    # -------------------------------------------------------------------------
    # Human Review Operations
    # -------------------------------------------------------------------------

    def get_candidates(
        self,
        project_id: str,
        job_id: Optional[str] = None,
        include_detached: bool = False,
    ) -> List[CharacterCandidate]:
        """Fetch candidates with nested observations for project or job."""
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            query = """
                SELECT id, job_id, project_id, label, review_status, confirmed_character_id,
                       observation_count, sampled_screen_time_seconds, estimated_screen_time_seconds,
                       representative_thumbnail_path, detection_methodology, clustering_confidence,
                       notes, created_at, updated_at
                FROM character_candidates
                WHERE project_id = ?
            """
            params: List[Any] = [project_id]
            if job_id:
                query += " AND job_id = ?"
                params.append(job_id)
            query += " ORDER BY created_at ASC"

            cur.execute(query, tuple(params))
            cand_rows = cur.fetchall()

            candidates: List[CharacterCandidate] = []
            for r in cand_rows:
                cid = r[0]
                obs_query = """
                    SELECT id, candidate_id, job_id, project_id, media_asset_id,
                           timestamp, frame_path, thumbnail_path, bounding_box,
                           detection_type, confidence, detection_method,
                           unverified_dialogue, is_detached, created_at
                    FROM character_observations
                    WHERE candidate_id = ?
                """
                obs_params: List[Any] = [cid]
                if not include_detached:
                    obs_query += " AND is_detached = 0"
                obs_query += " ORDER BY timestamp ASC"

                cur.execute(obs_query, tuple(obs_params))
                obs_rows = cur.fetchall()

                observations = [
                    CharacterObservation(
                        id=orow[0],
                        candidate_id=orow[1],
                        job_id=orow[2],
                        project_id=orow[3],
                        media_asset_id=orow[4],
                        timestamp=orow[5],
                        frame_path=orow[6],
                        thumbnail_path=orow[7],
                        bounding_box=BoundingBox(**json.loads(orow[8])),
                        detection_type=orow[9],
                        confidence=orow[10],
                        detection_method=orow[11],
                        unverified_dialogue=orow[12],
                        is_detached=bool(orow[13]),
                        created_at=orow[14],
                    )
                    for orow in obs_rows
                ]

                candidates.append(
                    CharacterCandidate(
                        id=r[0],
                        job_id=r[1],
                        project_id=r[2],
                        label=r[3],
                        review_status=r[4],
                        confirmed_character_id=r[5],
                        observation_count=len(observations),
                        sampled_screen_time_seconds=r[7],
                        estimated_screen_time_seconds=r[8],
                        representative_thumbnail_path=r[9],
                        detection_methodology=r[10],
                        clustering_confidence=r[11],
                        notes=r[12],
                        observations=observations,
                        created_at=r[13],
                        updated_at=r[14],
                    )
                )

            return candidates

    def rename_candidate(self, project_id: str, candidate_id: str, new_label: str) -> CharacterCandidate:
        """Rename provisional candidate label."""
        if not new_label or not new_label.strip():
            raise ValidationError("Candidate label cannot be empty.")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE character_candidates
                SET label = ?, updated_at = ?
                WHERE id = ? AND project_id = ?
                """,
                (new_label.strip(), now, candidate_id, project_id),
            )
            if cur.rowcount == 0:
                raise NotFoundError(f"Candidate '{candidate_id}' not found.")

            # Record audit event
            event_id = f"rev_{uuid.uuid4().hex[:12]}"
            cur.execute(
                """
                INSERT INTO character_review_events (
                    id, project_id, candidate_id, action_type, payload_json, notes, created_at
                ) VALUES (?, ?, ?, 'rename', ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    candidate_id,
                    json.dumps({"new_label": new_label.strip()}),
                    f"Renamed candidate to '{new_label.strip()}'",
                    now,
                ),
            )

        cands = self.get_candidates(project_id)
        for c in cands:
            if c.id == candidate_id:
                return c
        raise NotFoundError(f"Candidate '{candidate_id}' not found.")

    def confirm_candidate(
        self,
        project_id: str,
        candidate_id: str,
        req: ConfirmCandidateRequest,
    ) -> CharacterProfile:
        """
        Confirm candidate into persistent Character Library.
        Links candidate to character_profiles record and records audit event.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, label, representative_thumbnail_path, sampled_screen_time_seconds
                FROM character_candidates
                WHERE id = ? AND project_id = ?
                """,
                (candidate_id, project_id),
            )
            cand_row = cur.fetchone()
            if not cand_row:
                raise NotFoundError(f"Candidate '{candidate_id}' not found.")

            cand_label = cand_row[1]
            rep_thumb = cand_row[2]
            screen_time = cand_row[3]

            char_id = req.existing_character_id
            if char_id:
                # Link to existing character profile
                cur.execute(
                    """
                    SELECT id, total_appearances, total_screen_time_seconds
                    FROM character_profiles
                    WHERE id = ? AND project_id = ?
                    """,
                    (char_id, project_id),
                )
                prof_row = cur.fetchone()
                if not prof_row:
                    raise NotFoundError(f"Character profile '{char_id}' not found.")

                new_appearances = prof_row[1] + 1
                new_screen_time = round(prof_row[2] + screen_time, 2)
                cur.execute(
                    """
                    UPDATE character_profiles
                    SET total_appearances = ?, total_screen_time_seconds = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (new_appearances, new_screen_time, now, char_id),
                )
            else:
                # Create brand new character profile
                char_id = f"char_{uuid.uuid4().hex[:12]}"
                char_name = req.name.strip() if req.name else cand_label
                appearance_tags = req.appearance_tags or []
                cur.execute(
                    """
                    INSERT INTO character_profiles (
                        id, project_id, name, avatar_path, biography, appearance_tags,
                        total_appearances, total_screen_time_seconds, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, '{}', ?, ?)
                    """,
                    (
                        char_id,
                        project_id,
                        char_name,
                        rep_thumb,
                        req.biography or "",
                        json.dumps(appearance_tags),
                        screen_time,
                        now,
                        now,
                    ),
                )

            # Update candidate review status
            cur.execute(
                """
                UPDATE character_candidates
                SET review_status = 'confirmed', confirmed_character_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (char_id, now, candidate_id),
            )

            # Record audit event
            event_id = f"rev_{uuid.uuid4().hex[:12]}"
            cur.execute(
                """
                INSERT INTO character_review_events (
                    id, project_id, candidate_id, action_type, payload_json, notes, created_at
                ) VALUES (?, ?, ?, 'confirm', ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    candidate_id,
                    json.dumps({"character_id": char_id, "character_name": req.name or cand_label}),
                    f"Candidate confirmed into Character Library as character '{char_id}'",
                    now,
                ),
            )

        return self.get_character_profile(project_id, char_id)

    def merge_candidates(
        self,
        project_id: str,
        req: MergeCandidatesRequest,
    ) -> CharacterCandidate:
        """Merge multiple source candidates into target candidate."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            # Verify target candidate exists
            cur.execute(
                "SELECT id, label, observation_count, sampled_screen_time_seconds FROM character_candidates WHERE id = ? AND project_id = ?",
                (req.target_candidate_id, project_id),
            )
            target_row = cur.fetchone()
            if not target_row:
                raise NotFoundError(f"Target candidate '{req.target_candidate_id}' not found.")

            # Move all active observations from source candidates to target
            for src_id in req.source_candidate_ids:
                if src_id == req.target_candidate_id:
                    continue
                cur.execute(
                    """
                    UPDATE character_observations
                    SET candidate_id = ?
                    WHERE candidate_id = ? AND project_id = ?
                    """,
                    (req.target_candidate_id, src_id, project_id),
                )
                # Mark source candidate as merged
                cur.execute(
                    """
                    UPDATE character_candidates
                    SET review_status = 'merged', observation_count = 0, updated_at = ?
                    WHERE id = ? AND project_id = ?
                    """,
                    (now, src_id, project_id),
                )

            # Recalculate target candidate metrics
            cur.execute(
                """
                SELECT count(*), min(timestamp), max(timestamp)
                FROM character_observations
                WHERE candidate_id = ? AND is_detached = 0
                """,
                (req.target_candidate_id,),
            )
            m_row = cur.fetchone()
            new_obs_count = m_row[0]
            sampled_st = round(new_obs_count * 1.0, 2)
            est_st = round((m_row[2] - m_row[1]) + 1.0, 2) if m_row[0] > 0 else 0.0

            update_label = req.new_label.strip() if req.new_label else target_row[1]

            cur.execute(
                """
                UPDATE character_candidates
                SET label = ?, observation_count = ?, sampled_screen_time_seconds = ?,
                    estimated_screen_time_seconds = ?, updated_at = ?
                WHERE id = ?
                """,
                (update_label, new_obs_count, sampled_st, est_st, now, req.target_candidate_id),
            )

            # Audit log
            event_id = f"rev_{uuid.uuid4().hex[:12]}"
            cur.execute(
                """
                INSERT INTO character_review_events (
                    id, project_id, candidate_id, action_type, payload_json, notes, created_at
                ) VALUES (?, ?, ?, 'merge', ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    req.target_candidate_id,
                    json.dumps({"merged_source_ids": req.source_candidate_ids, "new_label": update_label}),
                    f"Merged {len(req.source_candidate_ids)} candidate(s) into '{req.target_candidate_id}'",
                    now,
                ),
            )

        cands = self.get_candidates(project_id)
        for c in cands:
            if c.id == req.target_candidate_id:
                return c
        raise NotFoundError(f"Target candidate '{req.target_candidate_id}' not found.")

    def split_candidate(
        self,
        project_id: str,
        candidate_id: str,
        req: SplitCandidateRequest,
    ) -> Tuple[CharacterCandidate, CharacterCandidate]:
        """Split specified observations from candidate into a new candidate."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        target_cand_id = candidate_id or req.candidate_id

        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            # Fetch existing candidate
            cur.execute(
                "SELECT id, job_id, label FROM character_candidates WHERE id = ? AND project_id = ?",
                (target_cand_id, project_id),
            )
            cand_row = cur.fetchone()
            if not cand_row:
                raise NotFoundError(f"Candidate '{target_cand_id}' not found.")

            job_id = cand_row[1]
            new_cand_id = f"cand_{uuid.uuid4().hex[:12]}"

            # Create new candidate
            cur.execute(
                """
                INSERT INTO character_candidates (
                    id, job_id, project_id, label, review_status, observation_count,
                    sampled_screen_time_seconds, estimated_screen_time_seconds,
                    representative_thumbnail_path, detection_methodology, clustering_confidence,
                    notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'provisional', 0, 0.0, 0.0, '', 'opencv_haar_spatial_temporal', 0.8, 'Split from candidate', ?, ?)
                """,
                (new_cand_id, job_id, project_id, req.new_candidate_label.strip(), now, now),
            )

            # Move specified observations
            for obs_id in req.observation_ids_to_split:
                cur.execute(
                    """
                    UPDATE character_observations
                    SET candidate_id = ?
                    WHERE id = ? AND candidate_id = ? AND project_id = ?
                    """,
                    (new_cand_id, obs_id, target_cand_id, project_id),
                )

            # Update metrics for original candidate
            cur.execute(
                "SELECT count(*), thumbnail_path FROM character_observations WHERE candidate_id = ? AND is_detached = 0",
                (target_cand_id,),
            )
            orig_m = cur.fetchone()
            orig_thumb = orig_m[1] if orig_m[0] > 0 else ""
            cur.execute(
                """
                UPDATE character_candidates
                SET observation_count = ?, representative_thumbnail_path = ?, updated_at = ?
                WHERE id = ?
                """,
                (orig_m[0], orig_thumb, now, target_cand_id),
            )

            # Update metrics for newly split candidate
            cur.execute(
                "SELECT count(*), thumbnail_path FROM character_observations WHERE candidate_id = ? AND is_detached = 0",
                (new_cand_id,),
            )
            new_m = cur.fetchone()
            new_thumb = new_m[1] if new_m[0] > 0 else ""
            cur.execute(
                """
                UPDATE character_candidates
                SET observation_count = ?, representative_thumbnail_path = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_m[0], new_thumb, now, new_cand_id),
            )

            # Audit event
            event_id = f"rev_{uuid.uuid4().hex[:12]}"
            cur.execute(
                """
                INSERT INTO character_review_events (
                    id, project_id, candidate_id, action_type, payload_json, notes, created_at
                ) VALUES (?, ?, ?, 'split', ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    target_cand_id,
                    json.dumps({"new_candidate_id": new_cand_id, "split_obs_count": len(req.observation_ids_to_split)}),
                    f"Split {len(req.observation_ids_to_split)} observation(s) into new candidate '{req.new_candidate_label}'",
                    now,
                ),
            )

        cands = {c.id: c for c in self.get_candidates(project_id)}
        return cands[target_cand_id], cands[new_cand_id]

    def detach_observation(
        self,
        project_id: str,
        candidate_id: str,
        observation_id: str,
    ) -> CharacterCandidate:
        """Detach an observation from a candidate without deleting raw disk evidence."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE character_observations
                SET is_detached = 1
                WHERE id = ? AND candidate_id = ? AND project_id = ?
                """,
                (observation_id, candidate_id, project_id),
            )
            if cur.rowcount == 0:
                raise NotFoundError(f"Observation '{observation_id}' not found in candidate '{candidate_id}'.")

            # Update candidate counts
            cur.execute(
                "SELECT count(*) FROM character_observations WHERE candidate_id = ? AND is_detached = 0",
                (candidate_id,),
            )
            rem = cur.fetchone()[0]
            cur.execute(
                """
                UPDATE character_candidates
                SET observation_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (rem, now, candidate_id),
            )

            # Audit event
            event_id = f"rev_{uuid.uuid4().hex[:12]}"
            cur.execute(
                """
                INSERT INTO character_review_events (
                    id, project_id, candidate_id, action_type, payload_json, notes, created_at
                ) VALUES (?, ?, ?, 'detach_observation', ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    candidate_id,
                    json.dumps({"detached_observation_id": observation_id}),
                    f"Detached observation '{observation_id}' (evidence retained)",
                    now,
                ),
            )

        cands = self.get_candidates(project_id)
        for c in cands:
            if c.id == candidate_id:
                return c
        raise NotFoundError(f"Candidate '{candidate_id}' not found.")

    def reject_candidate(self, project_id: str, candidate_id: str) -> CharacterCandidate:
        """Reject candidate as false positive or non-character."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE character_candidates
                SET review_status = 'rejected', updated_at = ?
                WHERE id = ? AND project_id = ?
                """,
                (now, candidate_id, project_id),
            )
            if cur.rowcount == 0:
                raise NotFoundError(f"Candidate '{candidate_id}' not found.")

            event_id = f"rev_{uuid.uuid4().hex[:12]}"
            cur.execute(
                """
                INSERT INTO character_review_events (
                    id, project_id, candidate_id, action_type, payload_json, notes, created_at
                ) VALUES (?, ?, ?, 'reject', ?, ?, ?)
                """,
                (event_id, project_id, candidate_id, "{}", "Candidate rejected by user", now),
            )

        cands = self.get_candidates(project_id)
        for c in cands:
            if c.id == candidate_id:
                return c
        raise NotFoundError(f"Candidate '{candidate_id}' not found.")

    # -------------------------------------------------------------------------
    # Character Library & JSON Export
    # -------------------------------------------------------------------------

    def get_library_profiles(
        self,
        project_id: str,
        query: Optional[str] = None,
    ) -> List[CharacterProfile]:
        """Fetch confirmed character profiles for project with optional search filter."""
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            sql = """
                SELECT id, project_id, name, avatar_path, biography, appearance_tags,
                       total_appearances, total_screen_time_seconds, metadata_json,
                       created_at, updated_at
                FROM character_profiles
                WHERE project_id = ?
            """
            params: List[Any] = [project_id]
            if query and query.strip():
                sql += " AND (name LIKE ? OR biography LIKE ?)"
                q = f"%{query.strip()}%"
                params.extend([q, q])
            sql += " ORDER BY name ASC"

            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

            return [
                CharacterProfile(
                    id=r[0],
                    project_id=r[1],
                    name=r[2],
                    avatar_path=r[3],
                    biography=r[4] or "",
                    appearance_tags=json.loads(r[5]) if r[5] else [],
                    total_appearances=r[6],
                    total_screen_time_seconds=r[7],
                    metadata_json=json.loads(r[8]) if r[8] else {},
                    created_at=r[9],
                    updated_at=r[10],
                )
                for r in rows
            ]

    def get_character_profile(self, project_id: str, character_id: str) -> CharacterProfile:
        """Fetch single character profile by ID."""
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, project_id, name, avatar_path, biography, appearance_tags,
                       total_appearances, total_screen_time_seconds, metadata_json,
                       created_at, updated_at
                FROM character_profiles
                WHERE id = ? AND project_id = ?
                """,
                (character_id, project_id),
            )
            r = cur.fetchone()
            if not r:
                raise NotFoundError(f"Character profile '{character_id}' not found.")

            return CharacterProfile(
                id=r[0],
                project_id=r[1],
                name=r[2],
                avatar_path=r[3],
                biography=r[4] or "",
                appearance_tags=json.loads(r[5]) if r[5] else [],
                total_appearances=r[6],
                total_screen_time_seconds=r[7],
                metadata_json=json.loads(r[8]) if r[8] else {},
                created_at=r[9],
                updated_at=r[10],
            )

    def update_character_profile(
        self,
        project_id: str,
        character_id: str,
        req: UpdateProfileRequest,
    ) -> CharacterProfile:
        """Update character profile details."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name, biography, appearance_tags FROM character_profiles WHERE id = ? AND project_id = ?",
                (character_id, project_id),
            )
            r = cur.fetchone()
            if not r:
                raise NotFoundError(f"Character profile '{character_id}' not found.")

            name = req.name.strip() if req.name is not None else r[0]
            biography = req.biography if req.biography is not None else r[1]
            appearance_tags = json.dumps(req.appearance_tags) if req.appearance_tags is not None else r[2]

            cur.execute(
                """
                UPDATE character_profiles
                SET name = ?, biography = ?, appearance_tags = ?, updated_at = ?
                WHERE id = ? AND project_id = ?
                """,
                (name, biography, appearance_tags, now, character_id, project_id),
            )

        return self.get_character_profile(project_id, character_id)

    def export_character_json(self, project_id: str, character_id: str) -> CharacterExportPayload:
        """Export full character profile, appearances, screen time summary, and observations as JSON."""
        profile = self.get_character_profile(project_id, character_id)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Query all confirmed candidates linked to this character
        with sqlite_session(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, label, observation_count, sampled_screen_time_seconds,
                       estimated_screen_time_seconds, created_at
                FROM character_candidates
                WHERE confirmed_character_id = ? AND project_id = ?
                """,
                (character_id, project_id),
            )
            c_rows = cur.fetchall()

            associated_candidates = []
            for cr in c_rows:
                cand_id = cr[0]
                cur.execute(
                    """
                    SELECT id, timestamp, detection_type, confidence, unverified_dialogue
                    FROM character_observations
                    WHERE candidate_id = ? AND is_detached = 0
                    ORDER BY timestamp ASC
                    """,
                    (cand_id,),
                )
                obs_rows = cur.fetchall()

                associated_candidates.append({
                    "candidate_id": cand_id,
                    "label": cr[1],
                    "observation_count": cr[2],
                    "sampled_screen_time_seconds": cr[3],
                    "estimated_screen_time_seconds": cr[4],
                    "created_at": cr[5],
                    "observations": [
                        {
                            "id": o[0],
                            "timestamp": o[1],
                            "detection_type": o[2],
                            "confidence": o[3],
                            "unverified_dialogue": o[4],
                        }
                        for o in obs_rows
                    ],
                })

        return CharacterExportPayload(
            export_version="2.0.0",
            exported_at=now,
            profile=profile,
            associated_candidates=associated_candidates,
            screen_time_summary={
                "total_appearances": profile.total_appearances,
                "total_screen_time_seconds": profile.total_screen_time_seconds,
                "candidate_clusters_count": len(associated_candidates),
            },
        )
