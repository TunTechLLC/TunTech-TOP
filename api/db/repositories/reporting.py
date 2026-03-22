import logging
from .base import BaseRepository

logger = logging.getLogger(__name__)

# SQL constants
GET_PATTERN_FREQUENCY = """
    SELECT *
    FROM   vw_PatternFrequency
    ORDER  BY times_detected DESC
"""

GET_PATTERN_FREQUENCY_BY_DOMAIN = """
    SELECT *
    FROM   vw_PatternFrequencyByDomain
    ORDER  BY domain, times_detected DESC
"""

GET_ACCEPTED_PATTERNS = """
    SELECT *
    FROM   vw_AcceptedPatterns
    ORDER  BY engagement_id, pattern_id
"""

GET_ECONOMIC_IMPACT = """
    SELECT *
    FROM   vw_EconomicImpactByEngagement
    ORDER  BY engagement_id
"""

GET_AGENT_RUN_LOG = """
    SELECT *
    FROM   vw_AgentRunLog
    ORDER  BY engagement_id, created_date
"""

GET_ENGAGEMENT_SUMMARY = """
    SELECT *
    FROM   vw_OPDSummary
    ORDER  BY firm_name, finding_id
"""

GET_ENGAGEMENT_OVERVIEW = """
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

GET_ENGAGEMENT_SIGNALS = """
    SELECT *
    FROM   vw_EngagementSignals
    WHERE  engagement_id = ?
    ORDER  BY domain, signal_confidence DESC
"""


class ReportingRepository(BaseRepository):
    """Handles all cross-engagement reporting queries.
    All methods query views — no direct table access."""

    def get_pattern_frequency(self) -> list:
        """Return pattern detection and acceptance counts across
        all engagements. Used for the cross-engagement dashboard."""
        logger.info("Fetching pattern frequency")
        rows = self._query(GET_PATTERN_FREQUENCY)
        return [dict(row) for row in rows]

    def get_pattern_frequency_by_domain(self) -> list:
        """Return pattern frequency grouped by domain."""
        logger.info("Fetching pattern frequency by domain")
        rows = self._query(GET_PATTERN_FREQUENCY_BY_DOMAIN)
        return [dict(row) for row in rows]

    def get_accepted_patterns(self) -> list:
        """Return all accepted patterns across all engagements
        with client context."""
        logger.info("Fetching accepted patterns")
        rows = self._query(GET_ACCEPTED_PATTERNS)
        return [dict(row) for row in rows]

    def get_economic_impact(self) -> list:
        """Return economic impact estimates by finding
        across all engagements."""
        logger.info("Fetching economic impact")
        rows = self._query(GET_ECONOMIC_IMPACT)
        return [dict(row) for row in rows]

    def get_agent_run_log(self) -> list:
        """Return all agent runs across all engagements
        with engagement context."""
        logger.info("Fetching agent run log")
        rows = self._query(GET_AGENT_RUN_LOG)
        return [dict(row) for row in rows]

    def get_engagement_summary(self) -> list:
        """Return OPD findings detail across all engagements.
        One row per finding — used for the cross-engagement findings view."""
        logger.info("Fetching OPD summary")
        rows = self._query(GET_ENGAGEMENT_SUMMARY)
        return [dict(row) for row in rows]

    def get_engagement_overview(self) -> list:
        """Return one row per engagement with all key counts.
        Used for the cross-engagement summary grid."""
        logger.info("Fetching engagement overview")
        rows = self._query(GET_ENGAGEMENT_OVERVIEW)
        return [dict(row) for row in rows]

    def get_engagement_signals(self, engagement_id: str) -> list:
        """Return all signals for an engagement from the signals view.
        Used by CasePacketService for case packet assembly."""
        logger.info(f"Fetching engagement signals for: {engagement_id}")
        rows = self._query(GET_ENGAGEMENT_SIGNALS, (engagement_id,))
        return [dict(row) for row in rows]