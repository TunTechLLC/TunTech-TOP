import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_qa_editorial_id

logger = logging.getLogger(__name__)

GET_FOR_ENGAGEMENT = """
    SELECT qa_editorial_id,
           engagement_id,
           issue,
           category,
           location,
           recommended_fix,
           standard_term,
           tier,
           source,
           status,
           created_date
    FROM   QAEditorialItems
    WHERE  engagement_id = ?
    ORDER  BY tier, qa_editorial_id
"""

INSERT_ITEM = """
    INSERT INTO QAEditorialItems (
        qa_editorial_id, engagement_id, issue, category, location,
        recommended_fix, standard_term, tier, source, status, created_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
"""

UPDATE_STATUS = """
    UPDATE QAEditorialItems
    SET    status = ?
    WHERE  qa_editorial_id = ?
"""

BATCH_ACCEPT_TIER_1 = """
    UPDATE QAEditorialItems
    SET    status = 'accepted'
    WHERE  engagement_id = ?
      AND  tier = 1
      AND  status = 'pending'
"""

DELETE_FOR_ENGAGEMENT = """
    DELETE FROM QAEditorialItems
    WHERE  engagement_id = ?
"""

VALID_CATEGORIES = (
    'formatting', 'grammar', 'terminology', 'voice', 'context_gap',
)
VALID_SOURCES = ('python', 'claude')


class QAEditorialRepository(BaseRepository):
    """Handles all database operations for QAEditorialItems.

    Items have a `source` field distinguishing items produced by the
    Python mechanical pipeline (editorial_auditor.py) from items produced
    by the focused Claude voice/audience check. UI surfaces the distinction
    so consultants know which pipeline flagged each item.
    """

    def get_for_engagement(self, engagement_id: str) -> list:
        """Return all QA editorial items for an engagement, ordered by tier
        then qa_editorial_id."""
        logger.info(f"Fetching QA editorial items for engagement: {engagement_id}")
        rows = self._query(GET_FOR_ENGAGEMENT, (engagement_id,))
        return [dict(row) for row in rows]

    def bulk_create(self, engagement_id: str, items: list) -> int:
        """Insert multiple editorial items one at a time to ensure unique
        sequential QE IDs. Returns rowcount.

        Sequential loop required — same pattern as PatternRepository.bulk_create.

        Each item dict must contain:
            issue, category, location, recommended_fix, tier (int), source.
        Optional:
            standard_term (string or None).
        """
        today = date.today().isoformat()
        count = 0
        for item in items:
            qe_id = next_qa_editorial_id()
            self._write(INSERT_ITEM, (
                qe_id,
                engagement_id,
                item['issue'],
                item['category'],
                item['location'],
                item['recommended_fix'],
                item.get('standard_term'),
                item['tier'],
                item['source'],
                today,
            ))
            count += 1
        logger.info(f"Bulk created {count} QA editorial items for {engagement_id}")
        return count

    def update_status(self, qa_editorial_id: str, status: str) -> None:
        """Update the status of a single item. Valid: pending/accepted/rejected."""
        logger.info(f"Updating QA editorial status: {qa_editorial_id} → {status}")
        self._write(UPDATE_STATUS, (status, qa_editorial_id))

    def batch_accept_tier_1(self, engagement_id: str) -> int:
        """Mark all pending Tier 1 editorial items as accepted.
        Rejected items left unchanged. Returns rowcount."""
        count = self._write(BATCH_ACCEPT_TIER_1, (engagement_id,))
        logger.info(f"Batch accepted {count} Tier 1 editorial items for {engagement_id}")
        return count

    def delete_for_engagement(self, engagement_id: str) -> int:
        """Delete all editorial items for an engagement.
        Called before re-detection so re-runs replace, not append."""
        count = self._write(DELETE_FOR_ENGAGEMENT, (engagement_id,))
        logger.info(f"Deleted {count} QA editorial items for {engagement_id}")
        return count
