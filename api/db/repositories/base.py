import sqlite3
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

class BaseRepository:

    def __init__(self):
        self._db_path = DB_PATH

    def _get_connection(self):
        import os
        from config import DB_PATH
        db_path = os.environ.get("TOP_DB_PATH") or DB_PATH
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _query(self, sql: str, params: tuple = ()) -> list:
        """Run a SELECT query and return all rows."""
        logger.info(f"Query: {sql[:80]}")
        with self._get_connection() as conn:
            return conn.execute(sql, params).fetchall()

    def _write(self, sql: str, params: tuple = ()) -> int:
        """Run an INSERT, UPDATE, or DELETE and commit. Returns rowcount."""
        logger.info(f"Write: {sql[:80]}")
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount

    def _write_many(self, sql: str, param_list: list) -> int:
        """Run a batch INSERT and commit. Returns rowcount."""
        logger.info(f"Write many: {sql[:80]} — {len(param_list)} rows")
        with self._get_connection() as conn:
            cursor = conn.executemany(sql, param_list)
            conn.commit()
            return cursor.rowcount

    def _write_transaction(self, operations: list) -> None:
        """Execute multiple writes atomically. Rolls back everything if any operation fails.
        operations is a list of (sql, params) tuples."""
        logger.info(f"Transaction: {len(operations)} operations")
        conn = self._get_connection()
        try:
            for sql, params in operations:
                conn.execute(sql, params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            conn.close()

            