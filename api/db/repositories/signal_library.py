import logging
from .base import BaseRepository

logger = logging.getLogger(__name__)

# SQL constants
GET_ALL = """
    SELECT signal_id, signal_name, domain, signal_type, definition,
           priority_tier, threshold_bands, maturity_levels, none_indicators,
           contributing_patterns, created_date
    FROM   SignalLibrary
    ORDER  BY priority_tier, domain, signal_name
"""

GET_BY_ID = """
    SELECT signal_id, signal_name, domain, signal_type, definition,
           priority_tier, threshold_bands, maturity_levels, none_indicators,
           contributing_patterns, created_date
    FROM   SignalLibrary
    WHERE  signal_id = ?
"""

GET_BY_DOMAIN = """
    SELECT signal_id, signal_name, domain, signal_type, definition,
           priority_tier, threshold_bands, maturity_levels, none_indicators,
           contributing_patterns, created_date
    FROM   SignalLibrary
    WHERE  domain = ?
    ORDER  BY priority_tier, signal_name
"""


class SignalLibraryRepository(BaseRepository):
    """Read-only access to the signal library.
    Library signals are seeded by migration; never created at runtime."""

    def get_all(self) -> list:
        """Return all 80 library signals ordered by priority tier, domain, name."""
        logger.info("Fetching all signal library entries")
        rows = self._query(GET_ALL)
        return [dict(row) for row in rows]

    def get_by_id(self, signal_id: str) -> dict | None:
        """Return a single library signal by its SL-xx ID, or None if not found."""
        logger.info(f"Fetching signal library entry: {signal_id}")
        rows = self._query(GET_BY_ID, (signal_id,))
        return dict(rows[0]) if rows else None

    def get_by_domain(self, domain: str) -> list:
        """Return all library signals for a given domain, ordered by priority tier."""
        logger.info(f"Fetching signal library entries for domain: {domain}")
        rows = self._query(GET_BY_DOMAIN, (domain,))
        return [dict(row) for row in rows]
