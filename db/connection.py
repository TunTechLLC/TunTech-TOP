# TOP Database Connection
# All database access goes through this module
# Phase 2: swap this file for PostgreSQL connection, nothing else changes

import sqlite3
from config import DB_PATH


def get_connection():
    """Return a connection to TOP.db with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # rows behave like dictionaries
    return conn


def execute_query(sql, params=()):
    """Run a SELECT query and return all rows."""
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchall()


def execute_write(sql, params=()):
    """Run an INSERT, UPDATE, or DELETE and commit."""
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount


def execute_many(sql, param_list):
    """Run an INSERT for multiple rows and commit."""
    with get_connection() as conn:
        cursor = conn.executemany(sql, param_list)
        conn.commit()
        return cursor.rowcount
