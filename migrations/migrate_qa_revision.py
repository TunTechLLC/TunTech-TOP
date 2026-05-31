"""
QA-4 Revision Edits Migration
=============================
Creates the QARevisionEdits table used by the Post-Assembly QA Stage
Revision Agent (QA-4). One row per edit the agent returns, with its
application outcome.

Run once from the repo root:
    python migrations/migrate_qa_revision.py

Verify with:
    python migrations/migrate_qa_revision.py --verify

Idempotent:
  - CREATE TABLE IF NOT EXISTS for QARevisionEdits
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


CREATE_QA_REVISION_EDITS = """
CREATE TABLE IF NOT EXISTS QARevisionEdits (
    qa_revision_id   TEXT PRIMARY KEY,
    engagement_id    TEXT NOT NULL,
    edit_type        TEXT NOT NULL,
    qa_source        TEXT NOT NULL,
    source_item_id   TEXT,
    anchor           TEXT NOT NULL,
    context_before   TEXT,
    new_text         TEXT NOT NULL,
    reason           TEXT,
    outcome          TEXT NOT NULL,
    match_method     TEXT,
    created_date     TEXT NOT NULL
);
"""

RECORD_MIGRATION = """
INSERT OR IGNORE INTO schema_migrations (version, applied_at)
VALUES ('qa_revision_edits', ?);
"""

RECORD_SOURCE_ITEM_MIGRATION = """
INSERT OR IGNORE INTO schema_migrations (version, applied_at)
VALUES ('qa_revision_source_item_id', ?);
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
        print(f"QARevisionEdits table exists: {'QARevisionEdits' in tables}")

        cols = conn.execute("PRAGMA table_info(QARevisionEdits)").fetchall()
        print(f"QARevisionEdits columns: {[c['name'] for c in cols]}")

        row_count = conn.execute("SELECT COUNT(*) FROM QARevisionEdits").fetchone()[0]
        print(f"QARevisionEdits rows: {row_count}")

        migration = conn.execute(
            "SELECT applied_at FROM schema_migrations WHERE version = 'qa_revision_edits'"
        ).fetchone()
        print(f"schema_migrations entry: {dict(migration) if migration else 'NOT RECORDED'}")
        conn.close()
        return

    print("-- Step 1: Create QARevisionEdits table --")
    conn.execute(CREATE_QA_REVISION_EDITS)
    conn.commit()
    print("  OK")

    print("-- Step 2: Ensure source_item_id column exists (idempotent) --")
    cols = [c['name'] for c in conn.execute("PRAGMA table_info(QARevisionEdits)").fetchall()]
    if 'source_item_id' not in cols:
        conn.execute("ALTER TABLE QARevisionEdits ADD COLUMN source_item_id TEXT")
        conn.commit()
        conn.execute(RECORD_SOURCE_ITEM_MIGRATION, (today,))
        conn.commit()
        print("  added column source_item_id")
    else:
        conn.execute(RECORD_SOURCE_ITEM_MIGRATION, (today,))
        conn.commit()
        print("  already present")

    print("-- Step 3: Record schema migration --")
    conn.execute(RECORD_MIGRATION, (today,))
    conn.commit()
    print("  OK")

    conn.close()
    print("\nMigration complete. Run with --verify to confirm.")


if __name__ == "__main__":
    verify_only = "--verify" in sys.argv
    run(verify_only=verify_only)
