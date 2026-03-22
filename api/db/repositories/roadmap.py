import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_roadmap_id

logger = logging.getLogger(__name__)

# SQL constants
GET_ALL = """
    SELECT r.item_id,
           r.engagement_id,
           r.finding_id,
           r.initiative_name,
           r.domain,
           r.phase,
           r.priority,
           r.effort,
           r.estimated_impact,
           r.owner,
           r.target_date,
           r.status,
           r.created_date,
           f.finding_title
    FROM   RoadmapItems r
    LEFT JOIN OPDFindings f ON r.finding_id = f.finding_id
    WHERE  r.engagement_id = ?
    ORDER  BY r.phase, r.priority, r.item_id
"""

GET_BY_PHASE = """
    SELECT r.item_id,
           r.engagement_id,
           r.finding_id,
           r.initiative_name,
           r.domain,
           r.phase,
           r.priority,
           r.effort,
           r.estimated_impact,
           r.owner,
           r.target_date,
           r.status,
           r.created_date
    FROM   RoadmapItems r
    WHERE  r.engagement_id = ?
    AND    r.phase = ?
    ORDER  BY r.priority, r.item_id
"""

INSERT_ROADMAP_ITEM = """
    INSERT INTO RoadmapItems (
        item_id, engagement_id, finding_id,
        initiative_name, domain, phase,
        priority, effort, estimated_impact,
        owner, target_date, status, created_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

LOG_PREVIEW_LENGTH = 80


class RoadmapRepository(BaseRepository):
    """Handles all database operations for RoadmapItems."""

    def get_all(self, engagement_id: str) -> list:
        """Return all roadmap items for an engagement ordered by
        phase and priority with finding title joined in."""
        logger.info(f"Fetching roadmap items for engagement: {engagement_id}")
        rows = self._query(GET_ALL, (engagement_id,))
        return [dict(row) for row in rows]

    def get_by_phase(self, engagement_id: str, phase: str) -> list:
        """Return roadmap items for a specific phase.
        Phase values: Stabilize, Optimize, Scale"""
        logger.info(f"Fetching {phase} roadmap items for engagement: {engagement_id}")
        rows = self._query(GET_BY_PHASE, (engagement_id, phase))
        return [dict(row) for row in rows]

    def create(self, engagement_id: str, data: dict) -> str:
        """Create a roadmap item. Returns the new item_id.

        Expected keys in data:
            initiative_name, domain, phase, priority, effort,
            estimated_impact, finding_id (optional),
            owner (optional), target_date (optional)
        """
        item_id = next_roadmap_id()
        today   = date.today().isoformat()

        logger.info(f"Creating roadmap item: {item_id} for engagement: {engagement_id}")

        self._write(INSERT_ROADMAP_ITEM, (
            item_id,
            engagement_id,
            data.get('finding_id'),
            data['initiative_name'],
            data['domain'],
            data['phase'],
            data.get('priority', 'Medium'),
            data.get('effort', 'Medium'),
            data.get('estimated_impact', ''),
            data.get('owner', ''),
            data.get('target_date'),
            data.get('status', 'Not Started'),
            today
        ))

        return item_id