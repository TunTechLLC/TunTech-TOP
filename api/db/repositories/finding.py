import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_finding_id

logger = logging.getLogger(__name__)

# SQL constants
GET_ALL = """
    SELECT f.finding_id,
           f.engagement_id,
           f.pattern_id,
           f.finding_title,
           f.domain,
           f.confidence,
           f.operational_impact,
           f.economic_impact,
           f.root_cause,
           f.recommendation,
           f.priority,
           f.effort,
           f.opd_section,
           f.created_date,
           f.evidence_summary,
           f.key_quotes,
           f.display_figure,
           f.display_label,
           f.figure_type,
           f.include_in_executive,
           p.pattern_name
    FROM   OPDFindings f
    LEFT JOIN Patterns p ON f.pattern_id = p.pattern_id
    WHERE  f.engagement_id = ?
    ORDER  BY f.priority, f.finding_id
"""

INSERT_FINDING = """
    INSERT INTO OPDFindings (
        finding_id, engagement_id, pattern_id,
        finding_title, domain, confidence,
        operational_impact, economic_impact,
        root_cause, recommendation,
        priority, effort, opd_section, created_date,
        evidence_summary, key_quotes,
        display_figure, display_label, figure_type, include_in_executive
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

ACCEPT_PATTERN = """
    UPDATE EngagementPatterns
    SET    accepted = 1
    WHERE  ep_id = ?
"""

UPDATE_FINDING = """
    UPDATE OPDFindings
    SET    finding_title      = COALESCE(?, finding_title),
           domain             = COALESCE(?, domain),
           confidence         = COALESCE(?, confidence),
           operational_impact = COALESCE(?, operational_impact),
           economic_impact    = COALESCE(?, economic_impact),
           root_cause         = COALESCE(?, root_cause),
           recommendation     = COALESCE(?, recommendation),
           priority           = COALESCE(?, priority),
           effort             = COALESCE(?, effort),
           opd_section        = COALESCE(?, opd_section),
           evidence_summary   = COALESCE(?, evidence_summary),
           key_quotes         = COALESCE(?, key_quotes),
           display_figure     = COALESCE(?, display_figure),
           display_label      = COALESCE(?, display_label),
           figure_type        = COALESCE(?, figure_type),
           include_in_executive = COALESCE(?, include_in_executive)
    WHERE  finding_id = ?
"""

LOG_PREVIEW_LENGTH = 80


class FindingRepository(BaseRepository):
    """Handles all database operations for OPDFindings."""

    def get_all(self, engagement_id: str) -> list:
        """Return all findings for an engagement in priority order
        with pattern name joined in."""
        logger.info(f"Fetching findings for engagement: {engagement_id}")
        rows = self._query(GET_ALL, (engagement_id,))
        return [dict(row) for row in rows]

    def create(self, engagement_id: str, data: dict,
               contributing_ep_ids: list) -> str:
        """Create a finding and accept all contributing patterns atomically.
        If either operation fails both are rolled back.
        Returns the new finding_id.

        Expected keys in data:
            finding_title, domain, confidence,
            operational_impact, economic_impact,
            root_cause, recommendation,
            priority, effort, opd_section (optional),
            pattern_id (optional)
        """
        finding_id = next_finding_id()
        today      = date.today().isoformat()

        logger.info(f"Creating finding: {finding_id} for engagement: {engagement_id} "
                    f"accepting {len(contributing_ep_ids)} patterns")

        # Build atomic operations list — finding insert plus pattern accepts
        ops = [
            (INSERT_FINDING, (
                finding_id,
                engagement_id,
                data.get('pattern_id'),
                data['finding_title'],
                data['domain'],
                data['confidence'],
                data['operational_impact'],
                data['economic_impact'],
                data['root_cause'],
                data['recommendation'],
                data.get('priority', 'Medium'),
                data.get('effort', 'Medium'),
                data.get('opd_section'),
                today,
                data.get('evidence_summary'),
                data.get('key_quotes'),
                data.get('display_figure'),
                data.get('display_label'),
                data.get('figure_type'),
                data.get('include_in_executive', 0),
            ))
        ]

        # Add one accept operation per contributing pattern
        for ep_id in contributing_ep_ids:
            ops.append((ACCEPT_PATTERN, (ep_id,)))

        self._write_transaction(ops)
        return finding_id

    def update(self, finding_id: str, data: dict) -> None:
        """Update finding fields. Only provided fields are changed —
        None values leave the existing database value unchanged."""
        logger.info(f"Updating finding: {finding_id}")
        self._write(UPDATE_FINDING, (
            data.get('finding_title'),
            data.get('domain'),
            data.get('confidence'),
            data.get('operational_impact'),
            data.get('economic_impact'),
            data.get('root_cause'),
            data.get('recommendation'),
            data.get('priority'),
            data.get('effort'),
            data.get('opd_section'),
            data.get('evidence_summary'),
            data.get('key_quotes'),
            data.get('display_figure'),
            data.get('display_label'),
            data.get('figure_type'),
            data.get('include_in_executive'),
            finding_id
        ))