import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_qa_coverage_id

logger = logging.getLogger(__name__)

# SQL constants
GET_FOR_ENGAGEMENT = """
    SELECT qa_coverage_id,
           engagement_id,
           source_file,
           who_said_it,
           what_was_said,
           location_in_source,
           appears_in_roadmap,
           roadmap_location,
           tier,
           status,
           created_date
    FROM   QACoverageItems
    WHERE  engagement_id = ?
    ORDER  BY tier, qa_coverage_id
"""

INSERT_ITEM = """
    INSERT INTO QACoverageItems (
        qa_coverage_id, engagement_id, source_file, who_said_it,
        what_was_said, location_in_source, appears_in_roadmap,
        roadmap_location, tier, status, created_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
"""

UPDATE_STATUS = """
    UPDATE QACoverageItems
    SET    status = ?
    WHERE  qa_coverage_id = ?
"""

BATCH_ACCEPT_TIER_1 = """
    UPDATE QACoverageItems
    SET    status = 'accepted'
    WHERE  engagement_id = ?
      AND  tier = 1
      AND  status = 'pending'
"""

DELETE_FOR_ENGAGEMENT = """
    DELETE FROM QACoverageItems
    WHERE  engagement_id = ?
"""


class QACoverageRepository(BaseRepository):
    """Handles all database operations for QACoverageItems."""

    def get_for_engagement(self, engagement_id: str) -> list:
        """Return all QA coverage items for an engagement, ordered by tier then id."""
        logger.info(f"Fetching QA coverage items for engagement: {engagement_id}")
        rows = self._query(GET_FOR_ENGAGEMENT, (engagement_id,))
        return [dict(row) for row in rows]

    def bulk_create(self, engagement_id: str, items: list) -> int:
        """Insert multiple QA coverage items one at a time to ensure unique
        sequential QC IDs. Returns the number of rows inserted.

        Uses sequential loop intentionally — list comprehension would call
        next_qa_coverage_id() before any rows are written, producing
        duplicate IDs. Do not refactor to batch insert. (Same pattern as
        PatternRepository.bulk_create.)

        Each item dict must contain:
            source_file, who_said_it, what_was_said, location_in_source,
            appears_in_roadmap (int 0/1/2), tier (int 1/2/3)
        Optional:
            roadmap_location (defaults to None)
        """
        today = date.today().isoformat()
        count = 0
        for item in items:
            qa_id = next_qa_coverage_id()
            self._write(INSERT_ITEM, (
                qa_id,
                engagement_id,
                item['source_file'],
                item['who_said_it'],
                item['what_was_said'],
                item['location_in_source'],
                item['appears_in_roadmap'],
                item.get('roadmap_location'),
                item['tier'],
                today,
            ))
            count += 1
        logger.info(f"Bulk created {count} QA coverage items for {engagement_id}")
        return count

    def update_status(self, qa_coverage_id: str, status: str) -> None:
        """Update the status of a single QA coverage item.
        Valid statuses: pending, accepted, rejected."""
        logger.info(f"Updating QA coverage status: {qa_coverage_id} → {status}")
        self._write(UPDATE_STATUS, (status, qa_coverage_id))

    def batch_accept_tier_1(self, engagement_id: str) -> int:
        """Mark all pending Tier 1 items for an engagement as accepted.
        Items already explicitly rejected by the consultant are left unchanged.
        Returns the number of rows updated.

        This is the 'Confirm Tier 1 — proceed' gate before QA-4 can run."""
        count = self._write(BATCH_ACCEPT_TIER_1, (engagement_id,))
        logger.info(f"Batch accepted {count} Tier 1 items for {engagement_id}")
        return count

    def delete_for_engagement(self, engagement_id: str) -> int:
        """Delete all QA coverage items for an engagement.
        Called before bulk_create on re-detection to replace existing results.
        Mirrors PatternRepository.delete_unaccepted_for_engagement intent —
        re-running detection replaces, does not append."""
        count = self._write(DELETE_FOR_ENGAGEMENT, (engagement_id,))
        logger.info(f"Deleted {count} QA coverage items for {engagement_id}")
        return count
