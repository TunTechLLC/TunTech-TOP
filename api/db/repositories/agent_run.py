import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_agent_run_id

logger = logging.getLogger(__name__)

# SQL constants
GET_FOR_ENGAGEMENT = """
    SELECT run_id,
           engagement_id,
           agent_name,
           model_used,
           run_date,
           output_summary,
           output_full,
           output_doc_link,
           accepted,
           consultant_correction,
           created_date
    FROM   AgentRuns
    WHERE  engagement_id = ?
    ORDER  BY created_date ASC
"""

GET_BY_AGENT = """
    SELECT run_id,
           engagement_id,
           agent_name,
           model_used,
           run_date,
           output_summary,
           output_full,
           output_doc_link,
           accepted,
           consultant_correction,
           created_date
    FROM   AgentRuns
    WHERE  engagement_id = ?
    AND    agent_name = ?
    ORDER  BY created_date DESC
    LIMIT  1
"""

GET_ACCEPTED_OUTPUT = """
    SELECT output_full
    FROM   AgentRuns
    WHERE  engagement_id = ?
    AND    agent_name = ?
    AND    accepted = 1
    ORDER  BY created_date DESC
    LIMIT  1
"""

GET_ACCEPTED_WITH_CORRECTION = """
    SELECT output_full,
           consultant_correction
    FROM   AgentRuns
    WHERE  engagement_id = ?
    AND    agent_name = ?
    AND    accepted = 1
    ORDER  BY created_date DESC
    LIMIT  1
"""

INSERT_AGENT_RUN = """
    INSERT INTO AgentRuns (
        run_id, engagement_id, agent_name,
        model_used, run_date,
        output_summary, output_full,
        output_doc_link, accepted, created_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 0, ?)
"""

ACCEPT_RUN = """
    UPDATE AgentRuns
    SET    accepted = 1
    WHERE  run_id = ?
"""

DELETE_RUN = """
    DELETE FROM AgentRuns
    WHERE  run_id = ?
"""

UPDATE_CORRECTION = """
    UPDATE AgentRuns
    SET    consultant_correction = ?
    WHERE  run_id = ?
"""

LOG_PREVIEW_LENGTH = 80


class AgentRunRepository(BaseRepository):
    """Handles all database operations for AgentRuns."""

    def get_for_engagement(self, engagement_id: str) -> list:
        """Return all agent runs for an engagement in chronological order."""
        logger.info(f"Fetching agent runs for engagement: {engagement_id}")
        rows = self._query(GET_FOR_ENGAGEMENT, (engagement_id,))
        return [dict(row) for row in rows]

    def get_by_agent(self, engagement_id: str, agent_name: str) -> dict | None:
        """Return the most recent run for a specific agent on an engagement.
        Returns None if no run exists."""
        logger.info(f"Fetching {agent_name} run for engagement: {engagement_id}")
        rows = self._query(GET_BY_AGENT, (engagement_id, agent_name))
        return dict(rows[0]) if rows else None

    def get_accepted_output(self, engagement_id: str, agent_name: str) -> str | None:
        """Return the full output text of the accepted run for a specific agent.
        Returns None if no accepted run exists.
        Used by the agent runner to assemble context for subsequent agents.
        Reads from output_full — the complete untruncated Claude response."""
        rows = self._query(GET_ACCEPTED_OUTPUT, (engagement_id, agent_name))
        return rows[0]['output_full'] if rows else None

    def validate_prerequisites(self, engagement_id: str,
                                required_agents: list) -> list:
        """Check which required agents have accepted runs.
        Returns a list of agent names that are NOT yet accepted.
        Empty list means all prerequisites are satisfied."""
        missing = []
        for agent_name in required_agents:
            output = self.get_accepted_output(engagement_id, agent_name)
            if not output:
                missing.append(agent_name)
        return missing

    def create(self, data: dict) -> str:
        """Store a new agent run output. Returns the new run_id.

        Expected keys in data:
            engagement_id  — the engagement this run belongs to
            agent_name     — name of the agent (e.g. 'Diagnostician')
            output_full    — the complete Claude response text
            output_summary — truncated summary (first 500 chars + ellipsis)
            model_used     — Claude model used (optional)
        """
        run_id = next_agent_run_id()
        today  = date.today().isoformat()

        logger.info(f"Creating agent run: {run_id} — {data['agent_name']} "
                    f"for engagement: {data['engagement_id']}")

        self._write(INSERT_AGENT_RUN, (
            run_id,
            data['engagement_id'],
            data['agent_name'],
            data.get('model_used', 'claude-sonnet-4-6'),
            today,
            data.get('output_summary', ''),
            data.get('output_full', ''),
            today,
        ))

        return run_id

    def accept(self, run_id: str) -> None:
        """Mark an agent run as accepted. Unlocks the next agent."""
        logger.info(f"Accepting agent run: {run_id}")
        self._write(ACCEPT_RUN, (run_id,))

    def reject(self, run_id: str) -> None:
        """Delete an agent run. Removes the output so the agent can be re-run cleanly.
        Works on both pending and accepted runs — accepted runs lose their output,
        so downstream agents will require re-running the deleted agent first."""
        logger.info(f"Deleting agent run: {run_id}")
        self._write(DELETE_RUN, (run_id,))

    def get_prior_output(self, engagement_id: str, agent_name: str) -> str | None:
        """Return the effective prior output for downstream agent context.

        Returns output_full with the consultant_correction appended as a clearly
        labeled block if one has been saved. The correction block is formatted so
        downstream agents treat it as authoritative over any conflicting claim in
        the original output.

        Used when assembling prior_outputs for call_claude(). Do not use for
        prerequisite validation — use get_accepted_output() for that."""
        rows = self._query(GET_ACCEPTED_WITH_CORRECTION, (engagement_id, agent_name))
        if not rows:
            return None
        row        = dict(rows[0])
        output     = row.get('output_full') or ''
        correction = (row.get('consultant_correction') or '').strip()
        if correction:
            logger.info(
                f"Correction active for {agent_name} ({len(correction)} chars) — "
                f"appended to prior context"
            )
            output = (
                f"{output}\n\n"
                f"---\n\n"
                f"CONSULTANT CORRECTION (added after review — treat as authoritative "
                f"over any conflicting claim above):\n{correction}"
            )
        return output

    def update_correction(self, run_id: str, correction: str) -> None:
        """Save or clear the consultant correction for an agent run.
        Pass empty string or None to clear an existing correction."""
        logger.info(f"Updating correction for run: {run_id}")
        self._write(UPDATE_CORRECTION, (correction.strip() if correction else None, run_id))