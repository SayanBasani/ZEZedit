import sys
import json
import sqlite3
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings
from app.services.highlight_discovery import HighlightDiscoveryEngine

def main():
    settings = Settings()
    db_path = str(settings.storage_root / "db" / "zezedit.db")
    engine = HighlightDiscoveryEngine(settings=settings, db_path=db_path)

    project_id = "proj_0f8238e5761d"
    media_asset_id = "med_51dc0e4b43f8"
    analysis_run_id = "run_9110df16b355"

    print("=== LIVE VERIFICATION: SESSION 4 CANDIDATE DISCOVERY & NOVELTY ===")
    print(f"Project ID: {project_id}")
    print(f"Media Asset ID: {media_asset_id}")
    print(f"Analysis Run ID: {analysis_run_id}")

    # 1. First Discovery Run (Batch 1: viral_punchy)
    print("\n--- BATCH 1: Discovering 4 'viral_punchy' shorts ---")
    batch1 = engine.discover_highlights(
        project_id=project_id,
        media_asset_id=media_asset_id,
        analysis_run_id=analysis_run_id,
        target_clip_count=4,
        creative_direction="viral_punchy",
        aspect_ratio="9:16",
        min_duration=12,
        max_duration=60,
    )
    print(f"Discovered {len(batch1)} candidates in Batch 1:")
    for i, c in enumerate(batch1, 1):
        print(f"  #{i}: [{c['start_time']:.1f}s - {c['end_time']:.1f}s] ({c['duration']:.1f}s) '{c['title']}'")
        print(f"       Score: {c['quality_score']:.2f} | Boundary Conf: {c.get('natural_boundary_confidence', 0):.2f}")
        bd = c.get('score_breakdown', {})
        print(f"       Hook: {bd.get('hook_strength', 0)} | Dialogue: {bd.get('dialogue_interest', 0)} | Motion: {bd.get('action_motion', 0)}")

    # 2. Check Generation Runs Table
    runs = engine.get_generation_runs(media_asset_id)
    print(f"\nTotal generation runs in database: {len(runs)}")
    run1 = runs[0]
    print(f"Run 1 ID: {run1['id']} | Selected: {run1['candidates_selected']} | Exclusions: {run1['novelty_exclusions']}")

    # 3. Check Novelty History
    hist = engine.get_novelty_history(media_asset_id)
    print(f"Total historical clips tracked: {hist['total_clips_generated']}")
    print(f"Total duration covered: {hist['total_duration_covered']:.1f}s")

    # 4. Generate More (Batch 2: dramatic)
    print("\n--- BATCH 2: Generating More Shorts ('dramatic') with Persistent Novelty ---")
    batch2 = engine.discover_highlights(
        project_id=project_id,
        media_asset_id=media_asset_id,
        analysis_run_id=analysis_run_id,
        target_clip_count=4,
        creative_direction="dramatic",
        aspect_ratio="9:16",
        min_duration=12,
        max_duration=60,
    )
    print(f"Discovered {len(batch2)} candidates in Batch 2:")
    for i, c in enumerate(batch2, 1):
        print(f"  #{i}: [{c['start_time']:.1f}s - {c['end_time']:.1f}s] ({c['duration']:.1f}s) '{c['title']}'")
        print(f"       Score: {c['quality_score']:.2f} | Boundary Conf: {c.get('natural_boundary_confidence', 0):.2f}")
        bd = c.get('score_breakdown', {})
        print(f"       Hook: {bd.get('hook_strength', 0)} | Dialogue: {bd.get('dialogue_interest', 0)} | Emotional: {bd.get('emotional_signal', 0)}")

    # 5. Check Non-Repetition (tIoU between batch 1 and batch 2)
    def compute_tiou(s1, e1, s2, e2):
        inter = max(0.0, min(e1, e2) - max(s1, s2))
        union = max(e1, e2) - min(s1, s2)
        return inter / union if union > 0 else 0.0

    print("\n--- NON-REPETITION (tIoU) AUDIT ---")
    max_tiou = 0.0
    for c2 in batch2:
        for c1 in batch1:
            tiou = compute_tiou(c1['start_time'], c1['end_time'], c2['start_time'], c2['end_time'])
            if tiou > max_tiou:
                max_tiou = tiou
            if tiou >= 0.50:
                print(f"VIOLATION! Candidate '{c2['title']}' overlaps '{c1['title']}' with tIoU = {tiou:.2f} >= 0.50")
    print(f"Maximum tIoU across all candidates between Batch 1 and Batch 2: {max_tiou:.3f} (Must be < 0.50)")
    assert max_tiou < 0.50, f"Novelty violation: max tIoU {max_tiou} >= 0.50!"
    print("SUCCESS: Persistent novelty non-repetition verified on real media!")

    # 6. Final Status
    runs_after = engine.get_generation_runs(media_asset_id)
    hist_after = engine.get_novelty_history(media_asset_id)
    print(f"\nFinal State: {len(runs_after)} runs, {hist_after['total_clips_generated']} total clips in history.")

if __name__ == "__main__":
    main()
