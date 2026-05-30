import json
import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_qa_coherence_id

logger = logging.getLogger(__name__)

# SQL constants
GET_FOR_ENGAGEMENT = """
    SELECT qa_coherence_id,
           engagement_id,
           issue,
           category,
           sections_involved,
           recommended_fix,
           tier,
           status,
           created_date
    FROM   QACoherenceItems
    WHERE  engagement_id = ?
    ORDER  BY tier, qa_coherence_id
"""

INSERT_ITEM = """
    INSERT INTO QACoherenceItems (
        qa_coherence_id, engagement_id, issue, category,
        sections_involved, recommended_fix, tier, status, created_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
"""

UPDATE_STATUS = """
    UPDATE QACoherenceItems
    SET    status = ?
    WHERE  qa_coherence_id = ?
"""

BATCH_ACCEPT_TIER_1 = """
    UPDATE QACoherenceItems
    SET    status = 'accepted'
    WHERE  engagement_id = ?
      AND  tier = 1
      AND  status = 'pending'
"""

DELETE_FOR_ENGAGEMENT = """
    DELETE FROM QACoherenceItems
    WHERE  engagement_id = ?
"""

VALID_CATEGORIES = (
    'contradiction', 'priority_mismatch', 'weak_grounding', 'missing_root_cause',
)


class QACoherenceRepository(BaseRepository):
    """Handles all database operations for QACoherenceItems.

    sections_involved is stored as a JSON array in a TEXT column — same
    pattern as findings.key_quotes. get_for_engagement returns it as a
    parsed list of strings; bulk_create serializes the list to JSON.
    """

    def get_for_engagement(self, engagement_id: str) -> list:
        """Return all QA coherence items for an engagement, ordered by tier
        then qa_coherence_id. sections_involved is deserialized to a list."""
        logger.info(f"Fetching QA coherence items for engagement: {engagement_id}")
        rows = self._query(GET_FOR_ENGAGEMENT, (engagement_id,))
        result = []
        for row in rows:
            item = dict(row)
            try:
                item['sections_involved'] = json.loads(item['sections_involved'] or '[]')
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    f"QACoherenceItems.{item['qa_coherence_id']}: sections_involved "
                    f"not parseable as JSON — returning empty list"
                )
                item['sections_involved'] = []
            result.append(item)
        return result

    def bulk_create(self, engagement_id: str, items: list) -> int:
        """Insert multiple coherence items one at a time to ensure unique
        sequential QH IDs. Returns the number of rows inserted.

        Sequential loop required — list comprehension would call
        next_qa_coherence_id() before any rows are written (same pattern
        documented on PatternRepository.bulk_create).

        Each item dict must contain:
            issue, category, sections_involved (list), recommended_fix,
            tier (int 1/2/3)
        """
        today = date.today().isoformat()
        count = 0
        for item in items:
            qh_id = next_qa_coherence_id()
            sections_json = json.dumps(item.get('sections_involved', []))
            self._write(INSERT_ITEM, (
                qh_id,
                engagement_id,
                item['issue'],
                item['category'],
                sections_json,
                item['recommended_fix'],
                item['tier'],
                today,
            ))
            count += 1
        logger.info(f"Bulk created {count} QA coherence items for {engagement_id}")
        return count

    def update_status(self, qa_coherence_id: str, status: str) -> None:
        """Update the status of a single QA coherence item.
        Valid statuses: pending, accepted, rejected."""
        logger.info(f"Updating QA coherence status: {qa_coherence_id} → {status}")
        self._write(UPDATE_STATUS, (status, qa_coherence_id))

    def batch_accept_tier_1(self, engagement_id: str) -> int:
        """Mark all pending Tier 1 coherence items for an engagement as accepted.
        Items already explicitly rejected are left unchanged. Returns rowcount."""
        count = self._write(BATCH_ACCEPT_TIER_1, (engagement_id,))
        logger.info(f"Batch accepted {count} Tier 1 coherence items for {engagement_id}")
        return count

    def delete_for_engagement(self, engagement_id: str) -> int:
        """Delete all coherence items for an engagement.
        Called before re-detection (re-runs replace, not append)."""
        count = self._write(DELETE_FOR_ENGAGEMENT, (engagement_id,))
        logger.info(f"Deleted {count} QA coherence items for {engagement_id}")
        return count
