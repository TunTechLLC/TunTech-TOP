# TOP Reporting Command
# Handles: cross-engagement-report

from datetime import date
from db.connection import execute_query
from utils.formatting import print_header, print_confirmation, print_error, divider
from config import REPORTS_DIR


def format_table(rows, columns):
    """Format query rows as a plain text table."""
    if not rows:
        return "  No data.\n"

    # Calculate column widths
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val = str(row[col]) if row[col] is not None else ""
            widths[col] = max(widths[col], len(val))

    # Header
    lines = []
    header = "  " + "  ".join(col.ljust(widths[col]) for col in columns)
    separator = "  " + "  ".join("-" * widths[col] for col in columns)
    lines.append(header)
    lines.append(separator)

    # Rows
    for row in rows:
        line = "  " + "  ".join(
            str(row[col]).ljust(widths[col]) if row[col] is not None else "".ljust(widths[col])
            for col in columns
        )
        lines.append(line)

    return "\n".join(lines) + "\n"


def section(title, rows, columns):
    """Format a named section with a table."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  {title}")
    lines.append("=" * 70)
    if not rows:
        lines.append("  No data.")
    else:
        lines.append(f"  Records: {len(rows)}")
        lines.append("")
        lines.append(format_table(rows, columns))
    lines.append("")
    return "\n".join(lines)


def run():
    """Run all cross-engagement views and save to timestamped report."""
    print_header("CROSS-ENGAGEMENT REPORT")

    today = date.today().isoformat()
    lines = []

    lines.append("TOP CROSS-ENGAGEMENT REPORT")
    lines.append(f"Generated: {today}")
    lines.append(f"TunTech Operations Platform — Phase 1")
    lines.append("")

    # ── 1. Pattern Frequency ────────────────────────────────────
    print("  Running pattern frequency view...")
    try:
        rows = execute_query(
            """SELECT * FROM vw_PatternFrequency
               WHERE times_detected > 0
               ORDER BY times_accepted DESC, times_detected DESC"""
        )
        lines.append(section(
            "1. PATTERN FREQUENCY — ALL ENGAGEMENTS",
            rows,
            ["pattern_id", "pattern_name", "domain", "times_detected", "times_accepted"]
        ))
    except Exception as e:
        lines.append(f"Pattern frequency view error: {e}\n")

    # ── 2. Pattern Frequency by Domain ──────────────────────────
    print("  Running domain frequency view...")
    try:
        rows = execute_query(
            """SELECT * FROM vw_PatternFrequencyByDomain
               ORDER BY times_accepted DESC, times_detected DESC"""
        )
        lines.append(section(
            "2. PATTERN FREQUENCY BY DOMAIN",
            rows,
            ["domain", "times_detected", "times_accepted"]
        ))
    except Exception as e:
        lines.append(f"Domain frequency view error: {e}\n")

    # ── 3. Accepted Patterns ─────────────────────────────────────
    print("  Running accepted patterns view...")
    try:
        rows = execute_query(
            """SELECT * FROM vw_AcceptedPatterns
               ORDER BY start_date DESC, pattern_id"""
        )
        lines.append(section(
            "3. ACCEPTED PATTERNS — ALL ENGAGEMENTS",
            rows,
            ["engagement_id", "firm_name", "pattern_id", "pattern_name", "confidence"]
        ))
    except Exception as e:
        lines.append(f"Accepted patterns view error: {e}\n")

    # ── 4. Economic Impact by Engagement ─────────────────────────
    print("  Running economic impact view...")
    try:
        rows = execute_query(
            "SELECT * FROM vw_EconomicImpactByEngagement"
        )
        lines.append(section(
            "4. ECONOMIC IMPACT BY ENGAGEMENT",
            rows,
            ["engagement_id", "firm_name", "finding_id", "finding_title",
             "confidence", "economic_impact"]
        ))
    except Exception as e:
        lines.append(f"Economic impact view error: {e}\n")

    # ── 5. Agent Run Log ─────────────────────────────────────────
    print("  Running agent run log view...")
    try:
        rows = execute_query(
            """SELECT * FROM vw_AgentRunLog
               ORDER BY run_date DESC"""
        )
        lines.append(section(
            "5. AGENT RUN LOG — ALL ENGAGEMENTS",
            rows,
            ["run_id", "firm_name", "agent_name", "run_date", "accepted"]
        ))
    except Exception as e:
        lines.append(f"Agent run log view error: {e}\n")

    # ── 6. Engagement Summary ────────────────────────────────────
    print("  Running engagement summary...")
    try:
        rows = execute_query(
            """SELECT
                e.engagement_id,
                c.firm_name,
                e.status,
                COUNT(DISTINCT s.signal_id)    as signals,
                COUNT(DISTINCT ep.ep_id)       as patterns,
                SUM(ep.accepted)               as accepted,
                COUNT(DISTINCT f.finding_id)   as findings,
                COUNT(DISTINCT r.item_id)      as roadmap_items,
                COUNT(DISTINCT kp.promotion_id) as knowledge
               FROM Engagements e
               JOIN Clients c ON e.client_id = c.client_id
               LEFT JOIN Signals s ON s.engagement_id = e.engagement_id
               LEFT JOIN EngagementPatterns ep ON ep.engagement_id = e.engagement_id
               LEFT JOIN OPDFindings f ON f.engagement_id = e.engagement_id
               LEFT JOIN RoadmapItems r ON r.engagement_id = e.engagement_id
               LEFT JOIN KnowledgePromotions kp ON kp.engagement_id = e.engagement_id
               GROUP BY e.engagement_id
               ORDER BY e.start_date"""
        )
        lines.append(section(
            "6. ENGAGEMENT SUMMARY",
            rows,
            ["engagement_id", "firm_name", "status", "signals",
             "patterns", "accepted", "findings", "roadmap_items", "knowledge"]
        ))
    except Exception as e:
        lines.append(f"Engagement summary error: {e}\n")

    # ── Save report ──────────────────────────────────────────────
    filename = f"cross_engagement_{today}.txt"
    output_path = REPORTS_DIR / filename

    full_report = "\n".join(lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_report)

    divider()
    print_confirmation(f"Report saved to: {output_path}")
    print()

    # Print engagement summary to screen
    print("  ENGAGEMENT SUMMARY:")
    divider()
    try:
        for row in execute_query(
            """SELECT e.engagement_id, c.firm_name, e.status,
                      COUNT(DISTINCT s.signal_id) as signals,
                      COUNT(DISTINCT ep.ep_id) as patterns
               FROM Engagements e
               JOIN Clients c ON e.client_id = c.client_id
               LEFT JOIN Signals s ON s.engagement_id = e.engagement_id
               LEFT JOIN EngagementPatterns ep ON ep.engagement_id = e.engagement_id
               GROUP BY e.engagement_id ORDER BY e.start_date"""
        ):
            print(f"  {row['engagement_id']}  {row['firm_name']:<35} "
                  f"{row['status']:<10} "
                  f"{row['signals']} signals  {row['patterns']} patterns")
    except Exception as e:
        print_error(f"Summary error: {e}")

    print()
    print("  PATTERN HIGHLIGHTS:")
    divider()
    try:
        highlights = execute_query(
            """SELECT pattern_id, pattern_name, times_detected, times_accepted
               FROM vw_PatternFrequency
               WHERE times_accepted > 0
               ORDER BY times_accepted DESC, times_detected DESC
               LIMIT 10"""
        )
        for row in highlights:
            bar = "█" * row['times_accepted'] + "░" * (row['times_detected'] - row['times_accepted'])
            print(f"  {row['pattern_id']:<6} {row['pattern_name']:<40} "
                  f"detected: {row['times_detected']}  accepted: {row['times_accepted']}  {bar}")
    except Exception as e:
        print_error(f"Highlights error: {e}")

    print()
