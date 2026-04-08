import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_ep_id

logger = logging.getLogger(__name__)

# SQL constants
GET_FOR_ENGAGEMENT = """
    SELECT ep.ep_id,
           ep.engagement_id,
           ep.pattern_id,
           ep.confidence,
           ep.economic_impact_est,
           ep.accepted,
           ep.notes,
           ep.created_date,
           p.pattern_name,
           p.domain,
           p.operational_impact,
           p.economic_model
    FROM   EngagementPatterns ep
    JOIN   Patterns p ON ep.pattern_id = p.pattern_id
    WHERE  ep.engagement_id = ?
    ORDER  BY ep.pattern_id
"""

GET_LIBRARY = """
    SELECT pattern_id,
           pattern_name,
           domain,
           trigger_signals,
           operational_impact,
           likely_root_cause,
           recommended_improvements,
           economic_model,
           economic_formula
    FROM   Patterns
    ORDER  BY pattern_id
"""

INSERT_PATTERN = """
    INSERT INTO EngagementPatterns (
        ep_id, engagement_id, pattern_id,
        confidence, economic_impact_est,
        accepted, notes, created_date
    ) VALUES (?, ?, ?, ?, NULL, 0, ?, ?)
"""

ACCEPT_PATTERN = """
    UPDATE EngagementPatterns
    SET    accepted = 1
    WHERE  ep_id = ?
"""

UPDATE_ECONOMIC_ESTIMATE = """
    UPDATE EngagementPatterns
    SET    economic_impact_est = ?
    WHERE  ep_id = ?
"""

LOG_PREVIEW_LENGTH = 80


class PatternRepository(BaseRepository):
    """Handles all database operations for Patterns and EngagementPatterns."""

    def get_for_engagement(self, engagement_id: str) -> list:
        """Return all detected patterns for an engagement with full
        pattern library details joined in."""
        logger.info(f"Fetching patterns for engagement: {engagement_id}")
        rows = self._query(GET_FOR_ENGAGEMENT, (engagement_id,))
        return [dict(row) for row in rows]

    def get_library(self) -> list:
        """Return the full pattern library P01-P60.
        Used for pattern detection validation and frontend display."""
        logger.info("Fetching full pattern library")
        rows = self._query(GET_LIBRARY)
        return [dict(row) for row in rows]

    def bulk_create(self, rows: list) -> int:
        """Insert multiple EngagementPatterns one at a time to ensure
        unique sequential EP IDs. Returns the number of rows inserted.

        Uses sequential loop intentionally — list comprehension caused
        duplicate EP IDs because next_ep_id() was called before any
        rows were written. Do not refactor to batch insert.
        """
        today = date.today().isoformat()
        count = 0
        for row in rows:
            ep_id = next_ep_id()
            self._write(INSERT_PATTERN, (
                ep_id,
                row['engagement_id'],
                row['pattern_id'],
                row['confidence'],
                row.get('notes', ''),
                today,
            ))
            count += 1
        logger.info(f"Bulk created {count} engagement patterns")
        return count

    def accept_contributing(self, ep_ids: list) -> int:
        """Set accepted=1 on a list of EngagementPatterns.
        Called by FindingRepository.create() inside a transaction —
        do not call this directly for finding creation."""
        logger.info(f"Accepting {len(ep_ids)} patterns: {ep_ids}")
        count = 0
        for ep_id in ep_ids:
            count += self._write(ACCEPT_PATTERN, (ep_id,))
        return count

    def update_economic_estimate(self, ep_id: str, estimate: str) -> None:
        """Update the economic impact estimate for a single pattern."""
        logger.info(f"Updating economic estimate for {ep_id}: {estimate}")
        self._write(UPDATE_ECONOMIC_ESTIMATE, (estimate, ep_id))