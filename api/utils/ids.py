# TOP Auto-ID Generation
# Never manually increment IDs - always use these functions

import os
import sqlite3
from config import DB_PATH


def next_id(table: str, id_column: str, prefix: str, pad: int) -> str:
    """Generic next-ID generator.

    Reads the current maximum numeric suffix from the given table/column
    and returns the next value as a zero-padded string.

    Examples:
        prefix='C',  pad=3 -> 'C001', 'C002', ...
        prefix='EP', pad=3 -> 'EP001', 'EP002', ...

    Uses TOP_DB_PATH environment variable if set (for tests),
    otherwise falls back to DB_PATH from config.py.
    """
    db_path = os.environ.get("TOP_DB_PATH") or DB_PATH
    sql = (
        f"SELECT MAX(CAST(SUBSTR({id_column}, {len(prefix) + 1}) AS INTEGER)) "
        f"AS max_id FROM {table}"
    )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(sql).fetchone()
        current_max = row["max_id"] or 0
    finally:
        conn.close()
    next_num = current_max + 1
    return f"{prefix}{str(next_num).zfill(pad)}"


def next_client_id():
    return next_id("Clients", "client_id", "C", 3)

def next_engagement_id():
    return next_id("Engagements", "engagement_id", "E", 3)

def next_interview_id():
    return next_id("Interviews", "interview_id", "I", 3)

def next_signal_id():
    return next_id("Signals", "signal_id", "S", 3)

def next_document_id():
    return next_id("Documents", "document_id", "D", 3)

def next_ep_id():
    return next_id("EngagementPatterns", "ep_id", "EP", 3)

def next_agent_run_id():
    return next_id("AgentRuns", "run_id", "AR", 3)

def next_finding_id():
    return next_id("OPDFindings", "finding_id", "F", 3)

def next_roadmap_id():
    return next_id("RoadmapItems", "item_id", "R", 3)

def next_knowledge_id():
    return next_id("KnowledgePromotions", "promotion_id", "KP", 3)

def next_processed_file_id():
    return next_id("ProcessedFiles", "file_id", "PF", 3)

def next_coverage_id():
    return next_id("SignalCoverage", "coverage_id", "SC", 3)