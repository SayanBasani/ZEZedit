import sqlite3
from pathlib import Path

db_path = Path("D:/ZezEdit/storage/db/zezedit.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print(f"Total tables: {len(tables)}")
print("Tables:", tables)

for t in ["shorts_candidates", "reframing_plans", "reframing_revisions", "candidate_generation_runs", "media_generated_clips_history"]:
    if t in tables:
        cols = [dict(c) for c in conn.execute(f"PRAGMA table_info({t})").fetchall()]
        print(f"\n--- Columns in {t} ---")
        for c in cols:
            print(f"  {c['name']} ({c['type']})")
