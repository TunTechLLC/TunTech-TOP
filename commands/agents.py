# TOP Agents Command
# Handles: log-agent-run, accept-agents

from datetime import date
from db.connection import execute_query, execute_write
from utils.ids import next_agent_run_id
from utils.formatting import (
    print_header, print_confirmation, print_error,
    prompt_text, prompt_confirm, divider
)
from config import VALID_AGENTS


def get_engagement(engagement_id):
    """Return engagement and client info or None if not found."""
    rows = execute_query(
        """SELECT e.engagement_id, e.engagement_name, c.firm_name
           FROM Engagements e
           JOIN Clients c ON e.client_id = c.client_id
           WHERE e.engagement_id = ?""",
        (engagement_id,)
    )
    return rows[0] if rows else None


def run_log(engagement_id, agent_name):
    """Log a completed agent run."""
    print_header(f"LOG AGENT RUN — {engagement_id}")

    # Verify engagement exists
    eng = get_engagement(engagement_id)
    if not eng:
        print_error(f"Engagement {engagement_id} not found.")
        return

    # Validate agent name
    matched = None
    for valid in VALID_AGENTS:
        if agent_name.lower() == valid.lower():
            matched = valid
            break

    if not matched:
        print_error(f"Unknown agent: {agent_name}")
        print(f"  Valid agents: {', '.join(VALID_AGENTS)}")
        return

    # Check if this agent already logged for this engagement
    existing = execute_query(
        """SELECT run_id FROM AgentRuns
           WHERE engagement_id = ? AND agent_name = ?""",
        (engagement_id, matched)
    )
    if existing:
        print(f"  Warning: {matched} already logged as {existing[0]['run_id']} for this engagement.")
        if not prompt_confirm("Log another run for this agent anyway?"):
            print("  Cancelled.")
            return

    print(f"  Client:     {eng['firm_name']}")
    print(f"  Engagement: {eng['engagement_name']}")
    print(f"  Agent:      {matched}")
    divider()

    # Collect run details
    drive_link = prompt_text("Google Drive link to output file")
    summary    = prompt_text("One-sentence summary of output")

    # Generate ID and write
    run_id  = next_agent_run_id()
    today   = date.today().isoformat()
    model   = "claude-sonnet-4-6"

    divider()
    print(f"  Run ID:   {run_id}")
    print(f"  Agent:    {matched}")
    print(f"  Summary:  {summary[:60]}...")

    if not prompt_confirm("Log this agent run?"):
        print("  Cancelled.")
        return

    execute_write(
        """INSERT INTO AgentRuns VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (run_id, engagement_id, matched, model, today,
         "v1.0", summary, drive_link, today)
    )

    print_confirmation(f"Agent run logged: {run_id}")

    # Show what's been run vs still needed
    divider()
    runs = execute_query(
        """SELECT agent_name, run_id, accepted
           FROM AgentRuns
           WHERE engagement_id = ?
           ORDER BY run_id""",
        (engagement_id,)
    )
    logged = {r['agent_name'] for r in runs}
    print("  Agent run status:")
    for agent in VALID_AGENTS:
        status = "DONE" if agent in logged else "pending"
        print(f"    {agent:<20} {status}")

    all_done = all(a in logged for a in VALID_AGENTS)
    if all_done:
        print()
        print(f"  All agents complete. Run: python top.py accept-agents {engagement_id}")
    print()


def run_accept(engagement_id):
    """Set accepted=1 on all AgentRuns for this engagement."""
    print_header(f"ACCEPT AGENT RUNS — {engagement_id}")

    eng = get_engagement(engagement_id)
    if not eng:
        print_error(f"Engagement {engagement_id} not found.")
        return

    # Show what will be accepted
    runs = execute_query(
        """SELECT run_id, agent_name, accepted
           FROM AgentRuns
           WHERE engagement_id = ?
           ORDER BY run_id""",
        (engagement_id,)
    )

    if not runs:
        print_error("No agent runs found for this engagement.")
        return

    print(f"  Client:     {eng['firm_name']}")
    print(f"  Engagement: {eng['engagement_name']}")
    divider()
    print("  Runs to accept:")
    for r in runs:
        status = "already accepted" if r['accepted'] else "will be accepted"
        print(f"    {r['run_id']}  {r['agent_name']:<20} {status}")

    divider()
    if not prompt_confirm("Accept all agent runs for this engagement?"):
        print("  Cancelled.")
        return

    count = execute_write(
        "UPDATE AgentRuns SET accepted = 1 WHERE engagement_id = ?",
        (engagement_id,)
    )

    print_confirmation(f"{count} agent runs accepted.")
    print(f"\n  Next step: python top.py case-packet {engagement_id}")
    print()
