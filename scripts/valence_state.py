"""
Valence state checkpoint — quick mid-run diagnostic for the Strengths / value-case feature.

Run AFTER signal extraction + candidate load (and again after findings parse/load) to
confirm strengths actually landed in the DB BEFORE paying for the full pipeline. Reads only.

    python scripts/valence_state.py            # defaults to E006
    python scripts/valence_state.py E007
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

db_path = os.environ.get("TOP_DB_PATH") or DB_PATH
engagement_id = sys.argv[1] if len(sys.argv) > 1 else "E006"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row


def breakdown(table: str, label: str) -> dict:
    rows = conn.execute(
        f"SELECT COALESCE(valence, '(none)') AS v, COUNT(*) AS n "
        f"FROM {table} WHERE engagement_id = ? GROUP BY v ORDER BY v",
        (engagement_id,),
    ).fetchall()
    total = sum(r["n"] for r in rows)
    print(f"\n{label} ({total} total):")
    for r in (rows or []):
        print(f"  {r['v']:<10} {r['n']}")
    if not rows:
        print("  (none)")
    return {r["v"]: r["n"] for r in rows}


print(f"=== Valence state for {engagement_id} ===  db={db_path}")

sig = breakdown("Signals", "Signals by valence")
strength_domains = conn.execute(
    "SELECT domain, COUNT(*) AS n FROM Signals "
    "WHERE engagement_id = ? AND valence = 'Strength' GROUP BY domain ORDER BY n DESC",
    (engagement_id,),
).fetchall()
if strength_domains:
    print("  Strength signals by domain:")
    for r in strength_domains:
        print(f"    {r['domain']}: {r['n']}")

fnd = breakdown("OPDFindings", "Findings by valence")
conn.close()

strengths = sig.get("Strength", 0)
positives = fnd.get("Positive", 0) + fnd.get("Dual", 0)

print("\n--- Verdict ---")
if strengths == 0:
    print("  [!] 0 Strength signals - strengths did NOT survive extraction.")
    print("      Check: did the source contain evidence-backed strengths? "
          "valence coercion warnings in top.log? domain cap?")
else:
    print(f"  [ok] {strengths} Strength signal(s) in the DB - strengths reached review.")

if fnd:  # findings exist → post-parse/load stage
    if positives == 0:
        print("  [!] 0 Positive/Dual findings — strengths did not become Preserve findings "
              "(check Synthesizer assembly, parse-synthesizer, or the 422 guard).")
    else:
        print(f"  [ok] {positives} Positive/Dual finding(s) - the value case has content to render.")
