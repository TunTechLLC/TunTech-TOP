import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_knowledge_id

logger = logging.getLogger(__name__)

# SQL constants
GET_ALL = """
    SELECT k.promotion_id,
           k.engagement_id,
           k.finding_id,
           k.pattern_id,
           k.promotion_type,
           k.description,
           k.applied_to,
           k.promotion_date,
           k.created_date,
           f.finding_title,
           p.pattern_name
    FROM   KnowledgePromotions k
    LEFT JOIN OPDFindings f ON k.finding_id = f.finding_id
    LEFT JOIN Patterns p    ON k.pattern_id = p.pattern_id
    WHERE  k.engagement_id = ?
    ORDER  BY k.promotion_type, k.created_date
"""

INSERT_KNOWLEDGE = """
    INSERT INTO KnowledgePromotions (
        promotion_id, engagement_id, finding_id,
        pattern_id, promotion_type, description,
        applied_to, promotion_date, created_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

LOG_PREVIEW_LENGTH = 80


class KnowledgeRepository(BaseRepository):
    """Handles all database operations for KnowledgePromotions."""

    def get_all(self, engagement_id: str) -> list:
        """Return all knowledge promotions for an engagement
        grouped by promotion_type with finding and pattern names joined in."""
        logger.info(f"Fetching knowledge promotions for engagement: {engagement_id}")
        rows = self._query(GET_ALL, (engagement_id,))
        return [dict(row) for row in rows]

    def create(self, engagement_id: str, data: dict) -> str:
        """Create a knowledge promotion. Returns the new promotion_id.

        Expected keys in data:
            promotion_type, description,
            finding_id (optional), pattern_id (optional),
            applied_to (optional), promotion_date (optional)
        """
        promotion_id = next_knowledge_id()
        today        = date.today().isoformat()

        logger.info(f"Creating knowledge promotion: {promotion_id} "
                    f"for engagement: {engagement_id}")

        self._write(INSERT_KNOWLEDGE, (
            promotion_id,
            engagement_id,
            data.get('finding_id'),
            data.get('pattern_id'),
            data['promotion_type'],
            data['description'],
            data.get('applied_to', ''),
            data.get('promotion_date', today),
            today
        ))

        return promotion_id