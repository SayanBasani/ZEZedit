# ZezEdit 2.0 — Security & Data Safety Architecture

## 1. Threat Model & Context

ZezEdit runs locally on a single user's Windows 11 workstation, executing external tools (`FFmpeg`, `FFprobe`, `Ollama`). Following the accidental recursive deletion incident that destroyed the earlier workspace, data safety and filesystem containment are first-class engineering guarantees—NOT optional best practices.

---

## 2. Hard Storage Boundary & Anti-Root Deletion Guarantees

Implemented cleanly in Milestone 1 (`backend/app/core/storage.py` and `backend/app/core/security.py`):

1. **Non-Root `ZEZEDIT_STORAGE_ROOT` Validation:**
   - Startup refuses any storage root resolving to a filesystem/drive root (`C:\`, `D:\`, `/`), Windows system directories (`C:\Windows`, `Program Files`), or a user's top-level home directory (`C:\Users\<name>`).
2. **Path Confinement (`resolve_contained_path`):**
   - Before reading, writing, or deleting any managed path, `Path.resolve(strict=False)` resolves symlinks/junctions and `..` segments and checks `target.is_relative_to(allowed_parent)`.
   - Any escape raises `AppError(code="PATH_OUTSIDE_BOUNDARY", status_code=403)` immediately.
3. **Structural Prohibition Against Storage Root Deletion:**
   - Every recursive delete helper (`safe_delete_directory` / `safe_delete_file`) checks that:
     - `target != storage_root`
     - `target` is NOT an immediate structural root folder (`media/`, `db/`, `exports/`, `backups/`) unless performing an explicit scoped child artifact removal inside an owned sub-path (e.g., `temp/jobs/{job_id}/` or `projects/{project_id}/`).
   - Bulk temporary cleanup iterates strictly over owned `temp/jobs/{job_id}/` directories and **NEVER** runs recursive deletes across parent folders or user media.

---

## 3. Source Media Immutability & Missing vs Deleted Distinction

- **Source Immutability:** Imported assets placed in `storage/media/` (or referenced externally with checksums) are opened **read-only** by FFmpeg/OpenCV. ZezEdit never performs in-place transcoding or re-muxing onto original source files.
- **Missing vs Explicitly Deleted States:**
  - If a file check fails because a user moved/unplugged an external drive or renamed a file outside ZezEdit, `media_assets.availability_status` becomes **`missing`**. All timeline clips, analysis, and project metadata remain intact, and the UI guides the user to **Relink Media**.
  - A file is marked **`deleted`** ONLY via an explicit user-confirmed deletion workflow confirming whether project references should also be removed.
- **Automatic Cleanup Rule:** Scheduled or idle maintenance NEVER deletes user project files, source media, exports, or databases. Only completed/expired `temp/jobs/` scratch artifacts whose owning jobs are terminal (`completed`/`failed`/`cancelled`) may be purged safely.

---

## 4. Export Overwrite & Confirmation Rules

- Export/render endpoints default to generating non-destructive version filenames (`{name}_rev2.mp4`, or timestamped suffixes).
- Overwriting an existing user export file MUST return `409 Conflict` (`EXPORT_OVERWRITE_REQUIRES_CONFIRM`) unless the client sends explicit confirmation metadata from a UI confirmation dialog.

---

## 5. AI Video Editor Security Boundary

The local AI model (`qwen3-vl:4b-instruct` or future models) is **untrusted text/JSON input**:
1. **Zero Shell or OS Access:** The AI runtime has zero access to `subprocess`, `os.system`, PowerShell, or arbitrary file read/write tools.
2. **Intent Router + Schema Validation Gate:** AI responses must deserialize cleanly into typed Pydantic `EditPlan` operations (`trim`, `split`, `caption_style`, `audio_volume`, etc.) verified by an independent deterministic validator (`plan_validator.py`) against actual project bounds (clip IDs exist, timestamps within duration).
3. **Preview & User Confirmation:** Non-read-only edit plans are presented visually before mutating any saved timeline state, and every applied AI plan records an undoable timeline revision (`author="ai_editor"`).

---

## 6. Backup & Restore Strategy

- **Distinct `backups/` Storage Category:** Automated pre-migration SQLite snapshots (`pre_migration_NNNN.db`) and user-initiated project backups (`backup_{timestamp}.zip`) reside exclusively in `storage/backups/`, clearly distinguished in UI and disk analyzers from active working data.
- **Consistent SQLite Backup:** Uses Python `sqlite3.Connection.backup()` API (safe while WAL mode is active) rather than raw file copying while transactions may be in flight.
- **Restore Guard:** Restoring a backup creates a safety snapshot of current state first (`pre_restore_*.db`), validates archive manifest & SQLite integrity (`PRAGMA integrity_check`), and prevents overwriting newer active projects silently.
