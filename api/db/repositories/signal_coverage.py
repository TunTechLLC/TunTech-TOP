import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_coverage_id

logger = logging.getLogger(__name__)

# SQL constants
GET_FOR_ENGAGEMENT = """
    SELECT sc.coverage_id,
           sc.engagement_id,
           sc.signal_id,
           sc.source_file,
           sc.created_date,
           sl.signal_name,
           sl.domain,
           sl.priority_tier
    FROM   SignalCoverage sc
    JOIN   SignalLibrary sl ON sc.signal_id = sl.signal_id
    WHERE  sc.engagement_id = ?
    ORDER  BY sl.domain, sl.priority_tier
"""

INSERT_COVERAGE = """
    INSERT INTO SignalCoverage (coverage_id, engagement_id, signal_id, source_file, created_date)
    VALUES (?, ?, ?, ?, ?)
"""


class SignalCoverageRepository(BaseRepository):
    """Tracks which library signals have been observed in an engagement.
    Gaps are library signals not present in SignalCoverage for the engagement."""

    def get_for_engagement(self, engagement_id: str) -> list:
        """Return all coverage records for an engagement, joined with library metadata."""
        logger.info(f"Fetching signal coverage for engagement: {engagement_id}")
        rows = self._query(GET_FOR_ENGAGEMENT, (engagement_id,))
        return [dict(row) for row in rows]

    def create(self, data: dict) -> str:
        """Create a single coverage record. Returns the new coverage_id.

        Expected keys in data:
            engagement_id, signal_id, source_file
        """
        coverage_id = next_coverage_id()
        today = date.today().isoformat()

        logger.info(f"Creating coverage record: {coverage_id} for engagement: {data['engagement_id']}")

        self._write(INSERT_COVERAGE, (
            coverage_id,
            data['engagement_id'],
            data['signal_id'],
            data['source_file'],
            today,
        ))

        return coverage_id

    def bulk_create(self, rows: list) -> int:
        """Insert multiple coverage records in a single batch operation.
        Returns the number of rows inserted.

        Each item in rows must be a dict with keys: engagement_id, signal_id, source_file.

        Sequential loop — never list comprehension. next_coverage_id() uses MAX+1
        logic; list comprehension evaluates all calls before any row is written,
        producing duplicate IDs."""
        today = date.today().isoformat()

        params = []
        for row in rows:
            params.append((
                next_coverage_id(),
                row['engagement_id'],
                row['signal_id'],
                row['source_file'],
                today,
            ))

        logger.info(f"Bulk creating {len(params)} coverage records")
        return self._write_many(INSERT_COVERAGE, params)
