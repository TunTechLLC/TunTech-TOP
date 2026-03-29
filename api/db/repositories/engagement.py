import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_client_id, next_engagement_id

logger = logging.getLogger(__name__)

GET_ALL = """
    SELECT e.engagement_id,
           e.engagement_name,
           e.status,
           c.firm_name,
           c.firm_size,
           COUNT(DISTINCT s.signal_id)   AS signal_count,
           COUNT(DISTINCT ep.ep_id)      AS pattern_count,
           COUNT(DISTINCT f.finding_id)  AS finding_count,
           COUNT(DISTINCT r.item_id)     AS roadmap_count
    FROM   Engagements e
    JOIN   Clients c
           ON e.client_id = c.client_id
    LEFT JOIN Signals s
           ON s.engagement_id = e.engagement_id
    LEFT JOIN EngagementPatterns ep
           ON ep.engagement_id = e.engagement_id
    LEFT JOIN OPDFindings f
           ON f.engagement_id = e.engagement_id
    LEFT JOIN RoadmapItems r
           ON r.engagement_id = e.engagement_id
    GROUP  BY e.engagement_id
    ORDER  BY e.start_date DESC
"""

GET_BY_ID = """
    SELECT e.*,
           c.firm_name,
           c.firm_size,
           c.service_model,
           COUNT(DISTINCT s.signal_id)   AS signal_count,
           COUNT(DISTINCT ep.ep_id)      AS pattern_count,
           COUNT(DISTINCT f.finding_id)  AS finding_count,
           COUNT(DISTINCT r.item_id)     AS roadmap_count
    FROM   Engagements e
    JOIN   Clients c
           ON e.client_id = c.client_id
    LEFT JOIN Signals s
           ON s.engagement_id = e.engagement_id
    LEFT JOIN EngagementPatterns ep
           ON ep.engagement_id = e.engagement_id
    LEFT JOIN OPDFindings f
           ON f.engagement_id = e.engagement_id
    LEFT JOIN RoadmapItems r
           ON r.engagement_id = e.engagement_id
    WHERE  e.engagement_id = ?
    GROUP  BY e.engagement_id
"""

INSERT_CLIENT = """
    INSERT INTO Clients (
        client_id, firm_name, firm_size,
        service_model, notes, created_date
    ) VALUES (?, ?, ?, ?, ?, ?)
"""

INSERT_ENGAGEMENT = """
    INSERT INTO Engagements (
        engagement_id, client_id, engagement_name,
        status, start_date, end_date, engagement_type,
        stated_problem, client_hypothesis,
        previously_tried, notes, created_date
    ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
"""

LOG_PREVIEW_LENGTH = 80


class EngagementRepository(BaseRepository):
    """Handles all database operations for Clients and Engagements."""

    def get_all(self) -> list:
        """Return summary list of all engagements for the dashboard."""
        logger.info("Fetching all engagements")
        rows = self._query(GET_ALL)
        return [dict(row) for row in rows]

    def get_by_id(self, engagement_id: str) -> dict | None:
        """Return full detail for a single engagement including client info."""
        logger.info(f"Fetching engagement: {engagement_id}")
        rows = self._query(GET_BY_ID, (engagement_id,))
        return dict(rows[0]) if rows else None

    def create(self, data: dict) -> str:
        """Create a new client and engagement together in a single transaction.
        Returns the new engagement_id."""
        client_id     = next_client_id()
        engagement_id = next_engagement_id()
        today         = date.today().isoformat()
        eng_name      = f"{data['firm_name']} OPD {today[:7]}"

        logger.info(f"Creating engagement: {engagement_id} for {data['firm_name']}")

        self._write_transaction([
            (INSERT_CLIENT, (
                client_id,
                data['firm_name'],
                data['firm_size'],
                data['service_model'],
                data.get('client_notes', ''),
                today
            )),
            (INSERT_ENGAGEMENT, (
                engagement_id,
                client_id,
                eng_name,
                'Active',
                today,
                'OPD',
                data['stated_problem'],
                data['client_hypothesis'],
                data['previously_tried'],
                data.get('consultant_notes', ''),
                today
            )),
        ])

        return engagement_id

    def update_settings(self, engagement_id: str, fields: dict) -> None:
        """Update folder settings fields on an engagement."""
        set_clause = ', '.join([f"{k} = ?" for k in fields.keys()])
        values = list(fields.values()) + [engagement_id]
        self._write(
            f"UPDATE Engagements SET {set_clause} WHERE engagement_id = ?",
            tuple(values)
        )
        logger.info(f"Updated settings for {engagement_id}: {list(fields.keys())}")