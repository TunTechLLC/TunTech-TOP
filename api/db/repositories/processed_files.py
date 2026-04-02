import logging
import hashlib
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_processed_file_id

logger = logging.getLogger(__name__)

GET_FOR_ENGAGEMENT = """
    SELECT file_id, engagement_id, file_name, file_hash,
           file_type, processed_date, signal_count, status
    FROM   ProcessedFiles
    WHERE  engagement_id = ?
    ORDER  BY processed_date DESC
"""

GET_BY_HASH = """
    SELECT file_id FROM ProcessedFiles WHERE file_hash = ?
"""

GET_FULL_BY_HASH = """
    SELECT file_id, engagement_id, file_name, file_hash,
           file_type, processed_date, signal_count, status
    FROM   ProcessedFiles WHERE file_hash = ?
"""

DELETE_BY_HASH = """
    DELETE FROM ProcessedFiles WHERE file_hash = ?
"""

INSERT_FILE = """
    INSERT INTO ProcessedFiles (
        file_id, engagement_id, file_name, file_hash,
        file_type, processed_date, signal_count, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


class ProcessedFilesRepository(BaseRepository):

    def get_for_engagement(self, engagement_id: str) -> list:
        rows = self._query(GET_FOR_ENGAGEMENT, (engagement_id,))
        return [dict(row) for row in rows]

    def already_processed(self, file_hash: str) -> bool:
        rows = self._query(GET_BY_HASH, (file_hash,))
        return len(rows) > 0

    def get_by_hash(self, file_hash: str) -> dict | None:
        rows = self._query(GET_FULL_BY_HASH, (file_hash,))
        return dict(rows[0]) if rows else None

    def delete_by_hash(self, file_hash: str) -> int:
        """Delete a processed file record by hash. Returns rowcount."""
        return self._write(DELETE_BY_HASH, (file_hash,))

    def mark_processed(self, engagement_id: str, file_name: str,
                       file_hash: str, file_type: str, signal_count: int) -> str:
        file_id = next_processed_file_id()
        self._write(INSERT_FILE, (
            file_id, engagement_id, file_name, file_hash,
            file_type, date.today().isoformat(), signal_count, 'processed'
        ))
        logger.info(f"Marked file as processed: {file_name} ({signal_count} signals)")
        return file_id

    @staticmethod
    def hash_file(file_path: str) -> str:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()