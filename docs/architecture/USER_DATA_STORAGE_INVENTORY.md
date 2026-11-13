# ZezEdit 2.0 User Data Storage Inventory & Retention Specification

## 1. Overview
ZezEdit is a local-first AI video editing application designed to run entirely on the user's workstation. Large video files (1–2+ GB), audio streams, intermediate analysis artifacts, character crops, thumbnails, and preview proxies can rapidly consume significant disk space.

This document serves as the authoritative inventory of all directories and files managed under `storage_root` (`D:\ZezEdit\storage`), detailing:
1. Exact directory layout and purpose
2. File types and estimated disk impact
3. Ownership and lifecycle rules
4. Path containment safety enforcement
5. Preservation rules during User Data Reclamation

---

## 2. Directory Layout & Storage Inventory

All application storage is rooted at `storage_root = D:\ZezEdit\storage`.

```
D:\ZezEdit\storage\
├── db\
│   ├── zezedit.db                      # SQLite primary database file
│   ├── zezedit.db-shm                  # SQLite shared memory index (WAL mode)
│   └── zezedit.db-wal                  # SQLite write-ahead log (WAL mode)
├── media\                              # Managed uploaded and imported videos
│   └── <media_asset_id>.<ext>          # Stored source video files
├── proxies\                            # Fast scrubbing 720p/540p video proxies
│   └── <media_asset_id>_proxy.mp4
├── thumbnails\                         # Video and clip visual thumbnails
│   ├── <media_asset_id>_thumb.jpg
│   └── <short_id>_thumb.jpg
├── analysis\                           # Multi-modal video analysis artifacts
│   └── <media_asset_id>\
│       ├── frames\                     # Extracted keyframes (JPEG/PNG)
│       │   ├── frame_0001.jpg
│       │   └── ...
│       ├── audio\                      # Extracted raw WAV/AAC audio
│       │   └── audio.wav
│       ├── whisper\                    # Whisper transcription JSON & VTT
│       │   └── transcript.json
│       ├── scene_cuts.json             # PySceneDetect cut timestamps
│       └── tracking\                   # YOLO/DeepSORT tracking matrices
│           └── detections.json
├── characters\                         # Character discovery and crop samples
│   └── <character_id>\
│       ├── face_sample_0.jpg
│       └── face_embedding.npy
├── timelines\                          # Clip timeline definitions and drafts
│   └── <short_id>_timeline.json
├── shorts\                             # Generated short video project specs
│   └── <short_id>\
│       └── manifest.json
├── exports\                            # Final rendered shorts (MP4 H.264/AAC)
│   └── <export_id>_<title>.mp4
└── temp\                               # Intermediate rendering & processing chunks
    └── <job_id>\
        ├── chunk_001.ts
        └── ...
```

---

## 3. Directory Categories & Space Impact

| Directory | Typical Size Range | Reclaimable on Single Video Delete | Reclaimable on Clear All User Data |
| :--- | :--- | :---: | :---: |
| `media/` | 100 MB – 5 GB per video | Yes (if stored inside `storage/media/`) | Yes |
| `proxies/` | 20 MB – 200 MB per video | Yes | Yes |
| `thumbnails/` | 50 KB – 500 KB per video/clip | Yes | Yes |
| `analysis/` | 100 MB – 2 GB per video | Yes (entire folder unlinked) | Yes |
| `characters/` | 1 MB – 50 MB | If linked to video | Yes |
| `timelines/` | 10 KB – 1 MB | Yes | Yes |
| `shorts/` | 10 KB – 2 MB | Yes | Yes |
| `exports/` | 20 MB – 300 MB per short | If linked to video | Yes |
| `temp/` | 100 MB – 5 GB (transient) | N/A (cleaned on job completion) | Yes |
| `db/` | 500 KB – 100 MB | Rows deleted | Re-initialized & VACUUMed |

---

## 4. Path Containment & Safety Guarantees

Accidental file deletion outside managed directories is prevented through strict path containment verification in `StorageService`:

```python
def _is_safe_path(target_path: Path, storage_root: Path) -> bool:
    try:
        resolved_target = target_path.resolve()
        resolved_root = storage_root.resolve()
        return resolved_root in resolved_target.parents or resolved_target == resolved_root
    except (ValueError, RuntimeError):
        return False
```

### Safety Rules:
1. **Never Delete External Source Files**: If a user imports or registers an external video located outside `storage_root` (e.g. `C:\Users\...\Videos\keynote.mp4`), ZezEdit records `source_path`. When deleting the video asset or executing "Clear All User Data", ZezEdit **only** deletes generated proxies, thumbnails, and analysis caches. The user's external source file is **never touched**.
2. **Never Delete System / Code Directories**: The data deletion service operates strictly inside `storage_root`. It has zero permissions or routines to touch `backend/`, `frontend/`, `node_modules/`, `.venv/`, or repository git trees.
3. **Handle Open Windows File Handles Gracefully**: Active FFmpeg or Python background worker processes often lock `.mp4` or `.wav` files on Windows (`[WinError 32] The process cannot access the file because it is being used by another process`).
   - Prior to storage deletion, ZezEdit inspects all running jobs in the database and terminates their child subprocess trees (`psutil`).
   - `shutil.rmtree(..., ignore_errors=True)` and try/except loops ensure that temporary file handle delays do not crash the cleanup routine.

---

## 5. Complete User Data Reclamation Lifecycle

When the user triggers `POST /api/v1/storage/clear-all-user-data` (or via Settings > Storage > "Clear All User Data"):

1. **Safety Confirmation Gate**: The payload must include `confirmation: "DELETE ALL USER DATA"` or `"DELETE"`.
2. **Active Job Termination**: Any active or running jobs are immediately cancelled and their OS subprocess trees terminated.
3. **Disk Sweep**: All files and subdirectories under `media/`, `proxies/`, `thumbnails/`, `analysis/`, `characters/`, `timelines/`, `shorts/`, `exports/`, and `temp/` are deleted. The directory skeletons are immediately recreated.
4. **Database Row Truncation**: User tables are emptied in dependency-safe order:
   - `export_jobs`
   - `timeline_tracks`
   - `video_timelines`
   - `characters`
   - `short_candidates`
   - `video_scenes`
   - `video_transcripts`
   - `jobs`
   - `media_assets`
   - `projects`
5. **Preserved Tables**:
   - `schema_migrations`: Preserves DB version state (e.g., migration `0016`).
   - `app_settings`: Preserves user configurations and API keys.
6. **Default Project Re-creation**: The default project `default` ("Default Project") is inserted so the app remains immediately usable.
7. **SQLite WAL Compaction**:
   - `PRAGMA wal_checkpoint(TRUNCATE);`
   - `VACUUM;`
   - `PRAGMA wal_checkpoint(TRUNCATE);`
   This flushes the WAL log to the main DB file, compacts the physical DB file, and truncates the WAL file, returning reclaimed disk space to the OS.
8. **Telemetry & Audit**: The endpoint calculates `pre_cleanup_bytes`, `post_cleanup_bytes`, and `reclaimed_bytes`, returning exact measurements to the user.
