"""
ProcessedFiles — engagement-scoped content-hash uniqueness
==========================================================
Changes the ProcessedFiles UNIQUE constraint from UNIQUE(file_hash) (global) to
UNIQUE(engagement_id, file_hash) (per engagement).

Why: duplicate detection is by content hash. The global constraint wrongly blocked a
duplicate/parallel engagement — or another client with identical-content files — from
recording (and therefore processing) its own copies. Scoping the uniqueness to the
engagement matches the application-level check (already_processed) and the project rule
that all data is scoped to engagement_id.

SQLite cannot ALTER a constraint in place, so this rebuilds the table (data preserved
via an explicit column-listed copy, inside a transaction).

Run once from the repo root:
    python migrations/migrate_processed_files_hash_scope.py
Verify:
    python migrations/migrate_processed_files_hash_scope.py --verify

Idempotent: if the constraint is already engagement-scoped, it only records the migration.
"""

import os
import sqlite3
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

db_path = os.environ.get("TOP_DB_PATH") or DB_PATH
today = date.today().isoformat()

NEW_TABLE = """
CREATE TABLE ProcessedFiles_new (
    file_id        TEXT PRIMARY KEY,
    engagement_id  TEXT NOT NULL,
    file_name      TEXT NOT NULL,
    file_hash      TEXT NOT NULL,
    file_type      TEXT NOT NULL,
    processed_date TEXT NOT NULL,
    signal_count   INTEGER DEFAULT 0,
    status         TEXT DEFAULT 'processed',
    UNIQUE(engagement_id, file_hash)
);
"""

COPY = """
INSERT INTO ProcessedFiles_new
    (file_id, engagement_id, file_name, file_hash, file_type, processed_date, signal_count, status)
SELECT
    file_id, engagement_id, file_name, file_hash, file_type, processed_date, signal_count, status
FROM ProcessedFiles
"""


def _is_scoped(conn):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='ProcessedFiles'"
    ).fetchone()
    if not row or not row[0]:
        return None  # table missing
    norm = row[0].lower().replace(" ", "").replace("\n", "")
    return "unique(engagement_id,file_hash)" in norm


def _record(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations "
                 "(version TEXT PRIMARY KEY, applied_at TEXT)")
    conn.execute("INSERT OR IGNORE INTO schema_migrations (version, applied_at) "
                 "VALUES ('processed_files_engagement_scoped_hash', ?)", (today,))


def verify():
    conn = sqlite3.connect(db_path)
    try:
        scoped = _is_scoped(conn)
        rows = conn.execute("SELECT COUNT(*) FROM ProcessedFiles").fetchone()[0]
        applied = conn.execute(
            "SELECT applied_at FROM schema_migrations "
            "WHERE version='processed_files_engagement_scoped_hash'"
        ).fetchone()
        print(f"DB: {db_path}")
        print(f"engagement-scoped UNIQUE present: {scoped}")
        print(f"ProcessedFiles rows: {rows}")
        print(f"migration recorded: {applied[0] if applied else 'NO'}")
    finally:
        conn.close()


def migrate():
    conn = sqlite3.connect(db_path)
    try:
        scoped = _is_scoped(conn)
        if scoped is None:
            print("[skip] ProcessedFiles table does not exist — nothing to migrate")
            return
        if scoped:
            _record(conn)
            conn.commit()
            print("[skip] ProcessedFiles already engagement-scoped — recorded, nothing to rebuild")
            return
        before = conn.execute("SELECT COUNT(*) FROM ProcessedFiles").fetchone()[0]
        conn.execute("PRAGMA foreign_keys=off")
        conn.execute("BEGIN")
        conn.execute(NEW_TABLE)
        conn.execute(COPY)
        conn.execute("DROP TABLE ProcessedFiles")
        conn.execute("ALTER TABLE ProcessedFiles_new RENAME TO ProcessedFiles")
        _record(conn)
        conn.commit()
        conn.execute("PRAGMA foreign_keys=on")
        after = conn.execute("SELECT COUNT(*) FROM ProcessedFiles").fetchone()[0]
        if before != after:
            print(f"[WARN] row count changed during rebuild: {before} -> {after} — investigate")
        else:
            print(f"[ok] rebuilt ProcessedFiles with UNIQUE(engagement_id, file_hash) "
                  f"— {after} rows preserved")
    finally:
        conn.close()


if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify()
    else:
        migrate()
        verify()
