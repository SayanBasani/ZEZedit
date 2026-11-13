"""Real-video verification script for Session 6A on 'Ek Mota Hathi Ghumne Chala.mp4'."""

import json
import sqlite3
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.services.highlight_discovery import HighlightDiscoveryEngine
from app.services.analysis_pipeline import VideoAnalysisPipeline, compute_source_signature


def run_real_video_verification():
    settings = get_settings()
    layout = StorageLayout.from_root(settings.storage_root)
    db_path = layout.db_file

    asset_id = "med_0eb2f3b6a7bc"
    project_id = "proj_344c9e189d9c"

    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        asset = conn.execute("SELECT * FROM media_assets WHERE id = ?", (asset_id,)).fetchone()
        if not asset:
            print(f"Error: Asset {asset_id} not found in database.")
            return

        print(f"=== REAL VIDEO VERIFICATION: {asset['original_filename']} ===")
        print(f"Asset ID: {asset_id}, Project ID: {project_id}")
        print(f"Duration: {asset['duration_seconds']:.1f}s, Resolution: {asset['width']}x{asset['height']}, Size: {asset['file_size_bytes']} bytes")

        # 1. Inspect existing source analysis
        analysis_pipe = VideoAnalysisPipeline(settings=settings, db_path=db_path)
        media_path = Path(asset["storage_path"])
        sig = compute_source_signature(media_path)
        print(f"Source file signature: {sig}")

        runs = conn.execute(
            "SELECT * FROM analysis_runs WHERE media_asset_id = ? AND status = 'completed' ORDER BY created_at DESC",
            (asset_id,),
        ).fetchall()
        print(f"Completed analysis runs found: {len(runs)}")
        analysis_run_id = runs[0]["id"] if runs else None

        if not analysis_run_id:
            print("No analysis run found. Triggering analysis...")
            analysis_run_id = analysis_pipe.create_analysis_run(media_asset_id=asset_id, project_id=project_id)
            import asyncio
            asyncio.run(analysis_pipe.execute_analysis(analysis_run_id))
            print(f"Analysis completed with run ID: {analysis_run_id}")

        cache_info = analysis_pipe.get_run_cache_info(analysis_run_id)
        print(f"Analysis cache valid: {cache_info['is_cache_valid']}")
        print(f"Persisted artifacts: {cache_info['records']}")

        # 2. Inspect existing novelty history before test
        history_before = conn.execute(
            "SELECT id, start_time, end_time, duration, title FROM media_generated_clips_history WHERE media_asset_id = ?",
            (asset_id,),
        ).fetchall()
        print(f"\nExisting clips recorded in novelty ledger: {len(history_before)}")
        for idx, h in enumerate(history_before[:5]):
            print(f"  [{idx+1}] {h['start_time']:.1f}s - {h['end_time']:.1f}s ({h['duration']:.1f}s): {h['title']}")
        if len(history_before) > 5:
            print(f"  ... and {len(history_before) - 5} more clips in ledger.")

    # 3. Test A: Run Highlight Discovery with AI Recommended settings reusing stored analysis
    print("\n--- TEST A: GENERATE WITH AI RECOMMENDED SETTINGS (REUSING ANALYSIS) ---")
    engine = HighlightDiscoveryEngine(settings=settings, db_path=db_path)
    start_t = time.perf_counter()

    batch_a = engine.discover_highlights(
        project_id=project_id,
        media_asset_id=asset_id,
        analysis_run_id=analysis_run_id,
        creative_direction="best_overall",
        aspect_ratio="9:16",
        duration_preference="ai_best_duration",
        novelty_mode="relaxed",  # since video already had 13 clips generated
        target_clip_count=None,  # AI Recommended dynamically!
    )
    duration_a = time.perf_counter() - start_t

    print(f"Discovery duration: {duration_a:.3f}s (reused stored analysis, no re-transcription or re-framing!)")
    print(f"Batch A candidates returned: {len(batch_a)}")
    gen_run_a = batch_a[0]["generation_run_id"] if batch_a else None

    intervals_a = []
    for idx, c in enumerate(batch_a):
        intervals_a.append((c["start_time"], c["end_time"]))
        print(f"  Candidate #{idx+1}: [{c['start_time']:.1f}s - {c['end_time']:.1f}s] ({c['duration']:.1f}s) Score: {c['quality_score']:.2f} | Title: {c['title']}")

    # 4. Test B: Generate More Shorts (Verifying Non-Repetition and Novelty Ledger)
    print("\n--- TEST B: GENERATE MORE SHORTS (NOVELTY NON-REPETITION CHECK) ---")
    start_b = time.perf_counter()
    batch_b = engine.discover_highlights(
        project_id=project_id,
        media_asset_id=asset_id,
        analysis_run_id=analysis_run_id,
        creative_direction="viral_punchy",
        aspect_ratio="1:1",
        duration_preference="ai_best_duration",
        novelty_mode="relaxed",
        target_clip_count=None,
        is_generate_more=True,
    )
    duration_b = time.perf_counter() - start_b

    print(f"Discovery duration: {duration_b:.3f}s (reused stored analysis!)")
    print(f"Batch B candidates returned: {len(batch_b)}")
    gen_run_b = batch_b[0]["generation_run_id"] if batch_b else None

    intervals_b = []
    for idx, c in enumerate(batch_b):
        intervals_b.append((c["start_time"], c["end_time"]))
        print(f"  Candidate #{idx+1}: [{c['start_time']:.1f}s - {c['end_time']:.1f}s] ({c['duration']:.1f}s) Score: {c['quality_score']:.2f} | Title: {c['title']}")

    # Check for exact duplicates between Batch A and Batch B
    duplicate_found = False
    for s_b, e_b in intervals_b:
        for s_a, e_a in intervals_a:
            if abs(s_b - s_a) < 2.0 and abs(e_b - e_a) < 2.0:
                print(f"ERROR: Duplicate interval found between batches: [{s_b}, {e_b}] vs [{s_a}, {e_a}]")
                duplicate_found = True

    if not duplicate_found:
        print("\nSUCCESS: Zero exact duplicates produced between Batch A and Batch B!")

    # Verify candidate generation runs in DB
    with sqlite_session(db_path) as conn:
        conn.row_factory = sqlite3.Row
        runs = conn.execute(
            "SELECT id, creative_direction, aspect_ratio, candidates_selected, novelty_exclusions, reused_analysis_run_id, is_novelty_exhausted FROM candidate_generation_runs WHERE media_asset_id = ? ORDER BY created_at DESC LIMIT 2",
            (asset_id,),
        ).fetchall()
        print("\nRecorded Generation Runs:")
        for r in runs:
            print(f"  Run ID: {r['id']}, Direction: {r['creative_direction']}, Ratio: {r['aspect_ratio']}, Selected: {r['candidates_selected']}, Novelty Exclusions: {r['novelty_exclusions']}, Reused Run: {r['reused_analysis_run_id']}, Novelty Exhausted: {bool(r['is_novelty_exhausted'])}")

        total_hist = conn.execute(
            "SELECT COUNT(*) FROM media_generated_clips_history WHERE media_asset_id = ?",
            (asset_id,),
        ).fetchone()[0]
        print(f"\nTotal persistent clip history ledger count now: {total_hist}")


if __name__ == "__main__":
    run_real_video_verification()
