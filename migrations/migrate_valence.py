"""
Valence Migration (Strengths & Value-Case Reframe — Track 1)
============================================================
Adds a nullable `valence` column to Signals and OPDFindings so positive
evidence ("What to Preserve") can flow through the diagnostic pipeline.

  - Signals.valence    : 'Strength' | 'Risk' | 'Neutral'  (NULL ≡ unset)
  - OPDFindings.valence : 'Positive' | 'Dual' | 'Negative' (NULL ≡ Negative,
                          i.e. today's behavior — backward compatible)

Run once from the repo root:
    python migrations/migrate_valence.py

Verify with:
    python migrations/migrate_valence.py --verify

Idempotent:
  - PRAGMA-guarded ALTER TABLE ADD COLUMN (skips if the column already exists)
  - INSERT OR IGNORE for the schema_migrations records
"""

import os
import sqlite3
import sys
from datetime import date

# DB path — respects TOP_DB_PATH env var (same as the app and tests)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

db_path = os.environ.get("TOP_DB_PATH") or DB_PATH
today = date.today().isoformat()


RECORD_SIGNAL_MIGRATION = """
INSERT OR IGNORE INTO schema_migrations (version, applied_at)
VALUES ('signals_valence', ?);
"""

RECORD_FINDING_MIGRATION = """
INSERT OR IGNORE INTO schema_migrations (version, applied_at)
VALUES ('opdfindings_valence', ?);
"""


def _add_column_if_missing(conn, table: str, column: str, decl: str) -> bool:
    """Add `column` to `table` if it is not already present. Returns True if added."""
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column in cols:
        print(f"  {table}.{column} already present")
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
    conn.commit()
    print(f"  added column {table}.{column}")
    return True


def run(verify_only: bool = False):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    if verify_only:
        print("-- Verification --")
        for table in ("Signals", "OPDFindings"):
            cols = [c["name"] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            print(f"{table}.valence present: {'valence' in cols}")
        for version in ("signals_valence", "opdfindings_valence"):
            row = conn.execute(
                "SELECT applied_at FROM schema_migrations WHERE version = ?", (version,)
            ).fetchone()
            print(f"schema_migrations '{version}': {dict(row) if row else 'NOT RECORDED'}")
        conn.close()
        return

    print("-- Step 1: Add Signals.valence --")
    _add_column_if_missing(conn, "Signals", "valence", "TEXT")
    conn.execute(RECORD_SIGNAL_MIGRATION, (today,))
    conn.commit()

    print("-- Step 2: Add OPDFindings.valence --")
    _add_column_if_missing(conn, "OPDFindings", "valence", "TEXT")
    conn.execute(RECORD_FINDING_MIGRATION, (today,))
    conn.commit()

    conn.close()
    print("\nMigration complete. Run with --verify to confirm.")


if __name__ == "__main__":
    verify_only = "--verify" in sys.argv
    run(verify_only=verify_only)
