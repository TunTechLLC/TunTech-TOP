import logging
from api.db.repositories.engagement import EngagementRepository
from api.db.repositories.signal     import SignalRepository
from api.db.repositories.pattern    import PatternRepository

logger = logging.getLogger(__name__)


class CasePacketService:
    """Assembles the structured case packet for Claude API calls.
    The case packet is the primary context document for all agent runs."""

    def __init__(self, engagement_id: str):
        self.engagement_id   = engagement_id
        self.engagement_repo = EngagementRepository()
        self.signal_repo     = SignalRepository()
        self.pattern_repo    = PatternRepository()

    def assemble(self) -> str:
        """Assemble the full four-section case packet.
        Used by agent runner — includes signals, patterns, and context."""
        engagement = self.engagement_repo.get_by_id(self.engagement_id)
        signals    = self.signal_repo.get_for_engagement(self.engagement_id)
        patterns   = self.pattern_repo.get_for_engagement(self.engagement_id)

        return "\n\n".join([
            self._section_1_context(engagement),
            self._section_2_signals(signals),
            self._section_3_patterns(patterns),
        ])

    def assemble_signals_only(self) -> str:
        """Assemble a signals-only case packet.
        Used by pattern detection — no patterns section needed."""
        engagement = self.engagement_repo.get_by_id(self.engagement_id)
        signals    = self.signal_repo.get_for_engagement(self.engagement_id)

        return "\n\n".join([
            self._section_1_context(engagement),
            self._section_2_signals(signals),
        ])

    def _section_1_context(self, engagement: dict) -> str:
        return f"""=== SECTION 1: ENGAGEMENT CONTEXT ===

Firm: {engagement['firm_name']}
Firm Size: {engagement['firm_size']} people
Service Model: {engagement.get('service_model', 'Not specified')}
Engagement: {engagement['engagement_name']}
Status: {engagement['status']}

STATED PROBLEM:
{engagement.get('stated_problem', 'Not provided')}

CLIENT HYPOTHESIS:
{engagement.get('client_hypothesis', 'Not provided')}

PREVIOUSLY TRIED:
{engagement.get('previously_tried', 'Not provided')}

CONSULTANT NOTES:
{engagement.get('consultant_notes') or 'None'}"""

    def _section_2_signals(self, signals: list) -> str:
        if not signals:
            return "=== SECTION 2: SIGNALS ===\n\nNo signals recorded."

        lines = ["=== SECTION 2: SIGNALS ===\n"]
        current_domain = None

        for s in sorted(signals, key=lambda x: x['domain']):
            if s['domain'] != current_domain:
                current_domain = s['domain']
                lines.append(f"\n--- {current_domain} ---")

            line = (
                f"[{s['signal_id']}] {s['signal_name']} | "
                f"{s['signal_confidence']} | "
                f"Observed: {s['observed_value']} | "
                f"Band: {s['normalized_band']} | "
                f"Source: {s['source']}"
            )
            if s.get('source_file'):
                line += f" | File: {s['source_file']}"
            if s.get('economic_relevance'):
                line += f" | Economic: {s['economic_relevance']}"
            lines.append(line)

            if s.get('notes'):
                lines.append(f"  Notes: {s['notes']}")

        return "\n".join(lines)

    def _section_3_patterns(self, patterns: list) -> str:
        if not patterns:
            return "=== SECTION 3: DETECTED PATTERNS ===\n\nNo patterns detected yet."

        lines = ["=== SECTION 3: DETECTED PATTERNS ===\n"]
        accepted   = [p for p in patterns if p['accepted'] == 1]
        unaccepted = [p for p in patterns if p['accepted'] == 0]

        if accepted:
            lines.append("ACCEPTED PATTERNS:")
            for p in accepted:
                line = (
                    f"[{p['pattern_id']}] {p['pattern_name']} | "
                    f"{p['confidence']} | "
                    f"Domain: {p['domain']}"
                )
                if p.get('economic_impact_est'):
                    line += f" | Economic: {p['economic_impact_est']}"
                lines.append(line)
                if p.get('notes'):
                    lines.append(f"  Notes: {p['notes']}")

        if unaccepted:
            lines.append("\nDETECTED (NOT YET ACCEPTED):")
            for p in unaccepted:
                lines.append(
                    f"[{p['pattern_id']}] {p['pattern_name']} | "
                    f"{p['confidence']} | "
                    f"Domain: {p['domain']}"
                )

        return "\n".join(lines)
