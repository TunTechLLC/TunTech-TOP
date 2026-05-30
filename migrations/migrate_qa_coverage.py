"""
QA-1 Coverage Items Migration
=============================
Creates the QACoverageItems table used by the Post-Assembly QA Stage
Coverage Check Agent. Idempotent — safe to re-run.

Run once from the repo root:
    python migrations/migrate_qa_coverage.py

Verify with:
    python migrations/migrate_qa_coverage.py --verify

Idempotent:
  - CREATE TABLE IF NOT EXISTS for QACoverageItems
  - INSERT OR IGNORE for schema_migrations record
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


CREATE_QA_COVERAGE_ITEMS = """
CREATE TABLE IF NOT EXISTS QACoverageItems (
    qa_coverage_id      TEXT PRIMARY KEY,
    engagement_id       TEXT NOT NULL,
    source_file         TEXT NOT NULL,
    who_said_it         TEXT NOT NULL,
    what_was_said       TEXT NOT NULL,
    location_in_source  TEXT NOT NULL,
    appears_in_roadmap  INTEGER NOT NULL,
    roadmap_location    TEXT,
    tier                INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',
    created_date        TEXT NOT NULL
);
"""

RECORD_MIGRATION = """
INSERT OR IGNORE INTO schema_migrations (version, applied_at)
VALUES ('qa_coverage_items', ?);
"""


def run(verify_only: bool = False):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    if verify_only:
        print("-- Verification --")
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()]
        print(f"QACoverageItems table exists: {'QACoverageItems' in tables}")

        cols = conn.execute("PRAGMA table_info(QACoverageItems)").fetchall()
        print(f"QACoverageItems columns: {[c['name'] for c in cols]}")

        row_count = conn.execute("SELECT COUNT(*) FROM QACoverageItems").fetchone()[0]
        print(f"QACoverageItems rows: {row_count}")

        migration = conn.execute(
            "SELECT applied_at FROM schema_migrations WHERE version = 'qa_coverage_items'"
        ).fetchone()
        print(f"schema_migrations entry: {dict(migration) if migration else 'NOT RECORDED'}")
        conn.close()
        return

    print("-- Step 1: Create QACoverageItems table --")
    conn.execute(CREATE_QA_COVERAGE_ITEMS)
    conn.commit()
    print("  OK")

    print("-- Step 2: Record schema migration --")
    conn.execute(RECORD_MIGRATION, (today,))
    conn.commit()
    print("  OK")

    conn.close()
    print("\nMigration complete. Run with --verify to confirm.")


if __name__ == "__main__":
    verify_only = "--verify" in sys.argv
    run(verify_only=verify_only)
