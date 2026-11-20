# ZEZEdit 2.0 — P1.8: Media Deduplication & Reference Counting

**Status:** ACCEPTED & VERIFIED  
**Milestone:** Priority 1 (P1.8)  
**Date:** 2026-11-20  
**Database Migration:** `0020_media_deduplication_and_reference_counting.sql` (Version 0020)  
**Quality Gates:**  
- **Backend Pytest:** 422/422 passed (exit code 0)  
- **Frontend Vitest:** 159/159 passed across 31 files (exit code 0)  
- **TypeScript Compiler:** 0 errors (`npx tsc --noEmit`)  
- **Production Build:** Vite clean bundle (`dist/index.html`, `dist/assets/`) built in 15.73s  
- **Database Integrity:** `PRAGMA integrity_check` = `ok`, `PRAGMA foreign_key_check` = `[]`  
- **Live Demonstrations:** 8/8 Scenarios Passed (`docs/reports/priority_1/p1_8_evidence/p1_8_evidence.json`)

---

## 1. Executive Summary

ZEZEdit 2.0 Priority P1.8 implements reliable, persistent, content-based media deduplication and reference counting for local and uploaded video files.

Prior to P1.8, uploading the same video multiple times—whether under identical or different filenames, or across different projects—allocated redundant physical storage and created uncoordinated database records.

P1.8 establishes:
1. **Clear Architectural Separation of Physical Files vs. Logical Media Assets:**
   - Physical video storage on disk is managed through canonical entries in `stored_media_files`, keyed uniquely by cryptographic `sha256`.
   - Project-level media assets in `media_assets` represent logical references within projects, pointing to a canonical `stored_media_files` record via `stored_file_id`.
2. **Streaming Content-Based Deduplication (Bounded Memory):**
   - Deduplication uses streaming single-pass cryptographic SHA-256 calculation in 64 KB chunks as bytes are written to disk.
   - Upon upload completion, if the computed SHA-256 matches an existing healthy physical file in `stored_media_files`, the staged `.uploading` part file is immediately unlinked (`part_path.unlink()`).
   - Zero redundant bytes are committed to permanent storage. The API response returns `is_deduplicated = true` and updates the canonical asset's reference count.
3. **Authoritative, Transactionally Verified Reference Counting:**
   - Reference counts are computed authoritatively from active media asset references (`availability_status != 'deleted'`).
   - Scalar subqueries in `list_media_assets` and `get_media_asset` eliminate O(N) query loops while ensuring zero column collision.
   - Stored file reference counts can be reconciled on demand via `/media/deduplication/reconcile`.
4. **Safe Deletion & Storage Reclamation:**
   - Deleting a media asset decrements the reference count of its canonical stored file.
   - If other projects or assets still reference the stored file (`remaining_references > 0`), the physical file is preserved intact on disk.
   - The underlying physical file is unlinked and its `stored_media_files` record purged only when the final remaining reference is removed (`remaining_references == 0`).
   - Project deletion (`delete_project`) cascades reference count adjustments safely across multi-project sharing, preserving physical files referenced by other projects.
5. **Relinking Isolation:**
   - Relinking a shared asset to a new physical file or replacing it via upload updates only that specific logical asset.
   - Other assets sharing the original physical file remain intact, and their reference counts are correctly decremented while the new file's reference count is incremented.
6. **Concurrency Safety:**
   - Simultaneous identical uploads are guarded against race conditions. Exactly one canonical physical file is retained, both uploads succeed and register separate logical assets, and all temporary `.uploading` part files are cleanly cleaned up.
7. **Frontend Transparency & Quiet UI:**
   - In accordance with the Unslop design principles, cards in `ShortVideoGeneratorLibrary.tsx` and `MediaLibraryView.tsx` display a quiet `Shared (N)` badge when `reference_count > 1`.
   - The technical metadata modal surfaces the Reference Count and canonical storage path.
   - The deletion confirmation dialog explicitly explains that deleting a shared asset preserves the underlying physical file for other referencing projects.

---

## 2. Database Schema Architecture (Migration 0020)

Applied migration `backend/migrations/0020_media_deduplication_and_reference_counting.sql`:

```sql
-- Migration 0020: Media Deduplication & Reference Counting
CREATE TABLE IF NOT EXISTS stored_media_files (
    id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE,
    storage_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    mime_type TEXT,
    container_format TEXT,
    duration_seconds REAL,
    width INTEGER,
    height INTEGER,
    fps REAL,
    video_codec TEXT,
    audio_codec TEXT,
    is_external INTEGER NOT NULL DEFAULT 0,
    reference_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_verified_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_stored_media_files_sha256 ON stored_media_files(sha256);
CREATE INDEX IF NOT EXISTS idx_stored_media_files_storage_path ON stored_media_files(storage_path);

-- Add stored_file_id column to media_assets if not present
ALTER TABLE media_assets ADD COLUMN stored_file_id TEXT REFERENCES stored_media_files(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_media_assets_stored_file_id ON media_assets(stored_file_id);
```

### 2.1 Schema Invariants
- `stored_media_files.sha256 UNIQUE`: Guarantees at the database level that exactly one canonical physical record exists for any given file content.
- `stored_media_files.reference_count`: Maintains the active reference count, synchronized with `SELECT COUNT(*) FROM media_assets WHERE stored_file_id = ? AND availability_status != 'deleted'`.
- `media_assets.stored_file_id`: Links each logical project asset to its canonical physical record.
- **Backfill Safety:** Migration 0020 automatically backfilled pre-existing media assets into `stored_media_files` by inspecting unique SHA-256 digests and associating each existing `media_assets` row with its corresponding canonical stored file.

---

## 3. Backend Implementation Architecture

### 3.1 Entity Model & Data Types (`backend/app/models/entities.py`)
- Added `StoredMediaFileRecord` representing the physical file row:
  - `id`, `sha256`, `storage_path`, `file_size_bytes`, `mime_type`, `container_format`, `duration_seconds`, `width`, `height`, `fps`, `video_codec`, `audio_codec`, `is_external`, `reference_count`, `created_at`, `updated_at`, `last_verified_at`.
- Updated `MediaAssetRecord` with deduplication fields:
  - `stored_file_id: Optional[str] = None`
  - `reference_count: int = 1`
  - `is_shared: bool = False` (convenience property: `reference_count > 1`)
  - `is_deduplicated: bool = False`

### 3.2 Schemas (`backend/app/schemas/core.py`)
- `MediaAssetResponse`: Added `stored_file_id`, `reference_count`, `is_shared`, `is_deduplicated`.
- `MediaBatchUploadItemResult`: Added `is_deduplicated` and `reference_count`.
- `MediaDeduplicationStatsResponse`:
  - `total_media_assets: int`
  - `unique_stored_files: int`
  - `deduplicated_assets: int`
  - `shared_stored_files: int`
  - `bytes_saved: int`
  - `total_physical_bytes: int`

### 3.3 Media Ingestion & Deduplication Pipeline (`backend/app/services/media_pipeline.py`)
During `import_uploaded_media`:
1. Incremental streaming writes chunks (1 MB buffer) to `.uploading` part file while updating SHA-256 digest.
2. Upon stream completion, computes final SHA-256 and checks `stored_media_files` via `get_stored_media_file_by_sha256(sha256)`.
3. If an existing stored file is found and its physical file is verified healthy on disk:
   - Part file is removed immediately: `part_path.unlink()`.
   - The existing canonical storage path is reused for the new logical asset.
   - `is_deduplicated` flag is set to `True`.
   - Existing thumbnail/proxy paths are reused when available.
4. If not found or if the existing physical file was missing:
   - Probes the part file via FFprobe.
   - Atomically renames part file to destination path: `os.replace(part_path, final_path)`.
   - Registers new stored file record in `stored_media_files`.
5. Registers logical `media_assets` record linked to `stored_file_id`.
6. Recalculates authoritative reference count.

### 3.4 Media Service Reference Management (`backend/app/services/media.py`)
- `recalculate_stored_file_reference_count(stored_file_id)`:
  - Executes `SELECT COUNT(*) FROM media_assets WHERE (stored_file_id = ? OR sha256 = ?) AND availability_status != 'deleted'`.
  - Updates `stored_media_files.reference_count`.
- `delete_media_asset(media_id)`:
  - Calculates remaining active references for the canonical stored file.
  - If `remaining_references > 0`:
    - Deletes logical `media_assets` row.
    - Decrements stored file's reference count.
    - **Preserves physical file on disk.**
  - If `remaining_references == 0`:
    - Deletes logical `media_assets` row.
    - Unlinks physical file on disk.
    - Purges canonical `stored_media_files` record.
- `reconcile_reference_counts()`:
  - Scans all `stored_media_files` and synchronizes `reference_count` with actual active `media_assets` counts.

### 3.5 Project Cascading Safety (`backend/app/services/projects.py`)
In `delete_project(project_id)`:
- Queries all `stored_file_ids` associated with the project's media assets prior to deletion.
- Executes cascade delete of project records.
- For each affected stored file, recalculates remaining references across other projects.
- Preserves physical files that still have references in other projects; reclaims disk space only for files whose references drop to 0.

### 3.6 API Endpoints (`backend/app/api/v1/media.py`)
- `GET /api/v1/projects/{project_id}/media/deduplication/stats` (and `/media/deduplication/stats`)
- `POST /api/v1/projects/{project_id}/media/deduplication/reconcile` (and `/media/deduplication/reconcile`)

---

## 4. Frontend Integration

### 4.1 UI Components
- **`ShortVideoGeneratorLibrary.tsx`:**
  - Surfaced `Shared (N)` badge in both Grid and List card views when `reference_count > 1`.
  - Added Reference Count and Physical Storage path rows to the technical specifications inspection modal.
  - Updated deletion confirmation dialog: when deleting a shared asset, alerts the user that the underlying file will remain intact because other projects or assets depend on it.
- **`MediaLibraryView.tsx`:**
  - Added `Shared (N)` indicator in card metadata.
  - Updated deletion modal with shared asset preservation explanation.

### 4.2 TypeScript & API Client
- Added `MediaDeduplicationStats` interface and deduplication fields to `MediaAssetItem` and `MediaBatchUploadItemResult`.
- Added `getDeduplicationStats(projectId?)` and `reconcileReferenceCounts(projectId?)` to `frontend/src/services/apiClient.ts`.

---

## 5. Live Demonstration Results

The automated demonstration runner `backend/scripts/run_p1_8_demos.py` executed all 8 required demonstrations matching Section 12 specifications. Evidence is recorded in `docs/reports/priority_1/p1_8_evidence/p1_8_evidence.json`.

| Demo | Description | Verification Criterion | Result | Evidence Details |
|---|---|---|---|---|
| **Demo A** | First Upload (Baseline) | Canonical stored file created, physical file verified on disk, `reference_count == 1`, `is_deduplicated == false` | **PASSED** | Media ID: `med_4864fa72b581`, Stored File: `smf_2578158cb66b9d63`, Size: 71,735 bytes, SHA-256: `2578158c...` |
| **Demo B** | Duplicate Upload (Same Project) | SHA-256 match detected, part file unlinked, canonical storage path reused, `reference_count == 2`, `is_deduplicated == true`, physical disk delta == 0 bytes | **PASSED** | Media ID: `med_07de29dbd76e`, Reused Path: `4f54bc0b_raw_footage_alpha.mp4`, Storage Delta: 0 bytes |
| **Demo C** | Non-Duplicate Upload (Different File) | Different content creates independent stored file and physical file, `reference_count == 1` | **PASSED** | Media ID: `med_6f2c7c6c2083`, Stored File: `smf_c965c12eb2286f66`, Size: 60,311 bytes, SHA-256: `c965c12e...` |
| **Demo D** | Multi-Project Sharing | Identical asset uploaded to 3 separate projects; all point to single stored file (`reference_count == 4`); HTTP 206 streaming functional across all | **PASSED** | Projects: `proj_27ed14b89522`, `proj_5dda03feca40`, `proj_5d7f245a1328`; Total References: 4; Streaming verified |
| **Demo E** | Safe Deletion (Remaining References) | Deleting one shared asset decrements `reference_count` to 3; physical file is retained on disk; streaming remains functional on remaining assets | **PASSED** | Deleted Asset: `med_07de29dbd76e`, Physical File Retained: `True`, Remaining Ref Count: 3 |
| **Demo F** | Safe Deletion (Storage Reclamation) | Deleting the final remaining reference reclaims physical file from disk; `stored_media_files` record is cleanly purged | **PASSED** | Final Deleted Asset: `med_33d1db19d2a4`, File Unlinked: `True`, Stored File Record Purged: `True` |
| **Demo G** | Concurrent Uploads (Race Condition Safety) | Two simultaneous uploads of identical content resolve safely; exactly 1 physical file kept; 0 orphaned part files | **PASSED** | Uploads: `med_711be9081ffc`, `med_954818a08432`; Stored File: `smf_2578158cb66b9d63`; Physical File Count: 1; Orphan Parts: 0 |
| **Demo H** | Relinking Isolation | Relinking one shared asset to a new file updates only that asset; other sharing asset retains original file and decrements ref count to 1 | **PASSED** | Relinked: `med_6865bdd343df` -> `asset_2.mp4`; Isolated: `med_656db24d4414` (retained `shared_h1.mp4`, Ref Count = 1) |

---

## 6. Automated Test Suites & Quality Gates

### 6.1 Backend Test Results
- Dedicated P1.8 Test Suite: `backend/tests/test_p1_8_media_deduplication.py`
  - **15 passed in 17.76s** (100% pass rate) covering:
    - `test_migration_0020_and_schema_integrity`
    - `test_first_upload_registers_stored_file`
    - `test_duplicate_upload_reuses_stored_file_and_reclaims_part_file`
    - `test_different_file_creates_independent_stored_file`
    - `test_multi_project_sharing_and_reference_counts`
    - `test_delete_asset_with_remaining_references_retains_physical_file`
    - `test_delete_asset_final_reference_reclaims_physical_file`
    - `test_delete_project_cascades_and_retains_shared_files`
    - `test_concurrent_duplicate_uploads_race_safety`
    - `test_relink_shared_asset_isolates_other_assets`
    - `test_reconcile_reference_counts`
    - `test_deduplication_stats_endpoint`
    - `test_stream_deduplicated_media_http_206`
    - `test_local_media_import_deduplication`
    - `test_corrupt_physical_file_fallback`
- P1.7 Regression Suite: `backend/tests/test_p1_7_media_relinking.py`
  - **9 passed in 6.50s**
- Full Backend Test Suite:
  - **422 passed** across all test files with 0 failures and 0 errors.

### 6.2 Frontend Test Results
- Dedicated P1.8 Unit Test Suite: `frontend/src/test/mediaDeduplication.test.tsx`
  - **5 passed in 252ms** covering:
    - Rendering `Shared (N)` badge when `reference_count > 1`
    - Omitting `Shared` badge when `reference_count <= 1`
    - Displaying Reference Count in technical specs modal
    - Deletion confirmation warning for shared assets
    - Deletion confirmation warning for unshared assets
- Full Frontend Vitest Suite:
  - **159 passed** across 31 test files in 13.29s.

### 6.3 Static Analysis & Build Verification
- TypeScript Check: `npx tsc --noEmit` — **0 errors**.
- Production Build: `npm run build` — **Built cleanly in 15.73s** (`dist/` clean).
- Database Checks:
  - `PRAGMA integrity_check`: `[('ok',)]`
  - `PRAGMA foreign_key_check`: `[]` (0 violations)

---

## 7. Conclusion

ZEZEdit 2.0 Priority P1.8 (Media Deduplication & Reference Counting) is complete, thoroughly verified, and accepted. It establishes robust storage optimization, guarantees data safety through authoritative reference counting, prevents physical file deletion until all references are gone, and maintains 100% backward compatibility with all P0 and P1.1–P1.7 capabilities.
