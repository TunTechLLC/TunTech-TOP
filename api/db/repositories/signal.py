import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_signal_id

logger = logging.getLogger(__name__)

# SQL constants
GET_FOR_ENGAGEMENT = """
    SELECT s.signal_id,
           s.engagement_id,
           s.interview_id,
           s.signal_name,
           s.domain,
           s.observed_value,
           s.normalized_band,
           s.signal_confidence,
           s.economic_relevance,
           s.source,
           s.notes,
           s.source_file,
           s.created_date
    FROM   Signals s
    WHERE  s.engagement_id = ?
    ORDER  BY s.domain, s.signal_confidence DESC
"""

GET_DOMAIN_SUMMARY = """
    SELECT domain,
           signal_confidence,
           COUNT(*) AS signal_count
    FROM   Signals
    WHERE  engagement_id = ?
    GROUP  BY domain, signal_confidence
    ORDER  BY domain
"""

INSERT_SIGNAL = """
    INSERT INTO Signals (
        signal_id, engagement_id, interview_id,
        signal_name, domain, observed_value,
        normalized_band, signal_confidence,
        economic_relevance, source, notes, created_date, source_file
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

DELETE_BY_SOURCE_FILE = """
    DELETE FROM Signals
    WHERE  engagement_id = ? AND source_file = ?
"""

LOG_PREVIEW_LENGTH = 80


class SignalRepository(BaseRepository):
    """Handles all database operations for Signals."""

    def get_for_engagement(self, engagement_id: str) -> list:
        """Return all signals for an engagement ordered by domain
        and confidence. Used for case packet assembly and pattern detection."""
        logger.info(f"Fetching signals for engagement: {engagement_id}")
        rows = self._query(GET_FOR_ENGAGEMENT, (engagement_id,))
        return [dict(row) for row in rows]

    def get_domain_summary(self, engagement_id: str) -> list:
        """Return signal counts grouped by domain and confidence level.
        Used for the engagement detail overview panel."""
        logger.info(f"Fetching domain summary for engagement: {engagement_id}")
        rows = self._query(GET_DOMAIN_SUMMARY, (engagement_id,))
        return [dict(row) for row in rows]

    def create(self, data: dict) -> str:
        """Create a single signal. Returns the new signal_id.

        Expected keys in data:
            engagement_id, signal_name, domain,
            observed_value, normalized_band, signal_confidence,
            source, interview_id (optional), economic_relevance (optional),
            notes (optional)
        """
        signal_id = next_signal_id()
        today     = date.today().isoformat()

        logger.info(f"Creating signal: {signal_id} for engagement: {data['engagement_id']}")

        self._write(INSERT_SIGNAL, (
            signal_id,
            data['engagement_id'],
            data.get('interview_id'),
            data['signal_name'],
            data['domain'],
            data['observed_value'],
            data['normalized_band'],
            data['signal_confidence'],
            data.get('economic_relevance', ''),
            data['source'],
            data.get('notes', ''),
            today,
            data.get('source_file'),
        ))

        return signal_id

    def delete_by_source_file(self, engagement_id: str, source_file: str) -> int:
        """Delete all signals for an engagement that came from a specific source file.
        Returns the number of rows deleted."""
        logger.info(f"Deleting signals for engagement {engagement_id} from source file: {source_file}")
        return self._write(DELETE_BY_SOURCE_FILE, (engagement_id, source_file))

    def bulk_create(self, rows: list) -> int:
        """Insert multiple signals in a single batch operation.
        Returns the number of rows inserted.

        Each item in rows must be a dict with the same keys as create().
        Used for Tally CSV import."""
        today = date.today().isoformat()

        params = [(
            next_signal_id(),
            row['engagement_id'],
            row.get('interview_id'),
            row['signal_name'],
            row['domain'],
            row['observed_value'],
            row['normalized_band'],
            row['signal_confidence'],
            row.get('economic_relevance', ''),
            row['source'],
            row.get('notes', ''),
            today
        ) for row in rows]

        logger.info(f"Bulk creating {len(params)} signals")
        return self._write_many(INSERT_SIGNAL, params)