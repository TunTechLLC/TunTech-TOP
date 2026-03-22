# TOP Findings Command
# Handles: populate-findings
# Simultaneously accepts contributing EngagementPatterns records

from datetime import date
from db.connection import execute_query, execute_write
from utils.ids import next_finding_id
from utils.formatting import (
    print_header, print_confirmation, print_error,
    prompt_text, prompt_choice, prompt_confirm, divider,
    prompt_domain, prompt_confidence, prompt_priority
)


def get_engagement(engagement_id):
    rows = execute_query(
        """SELECT e.engagement_id, e.engagement_name, c.firm_name
           FROM Engagements e
           JOIN Clients c ON e.client_id = c.client_id
           WHERE e.engagement_id = ?""",
        (engagement_id,)
    )
    return rows[0] if rows else None


def show_available_patterns(engagement_id):
    """Display patterns available to link to findings."""
    rows = execute_query(
        """SELECT ep.ep_id, ep.confidence, p.pattern_id, p.pattern_name, p.domain
           FROM EngagementPatterns ep
           JOIN Patterns p ON ep.pattern_id = p.pattern_id
           WHERE ep.engagement_id = ?
           ORDER BY CASE ep.confidence
               WHEN 'High' THEN 1
               WHEN 'Medium' THEN 2
               ELSE 3 END, p.domain""",
        (engagement_id,)
    )
    if not rows:
        return
    print("\n  Available patterns to link:")
    for r in rows:
        accepted = execute_query(
            "SELECT accepted FROM EngagementPatterns WHERE ep_id = ?",
            (r['ep_id'],)
        )
        flag = " (accepted)" if accepted and accepted[0]['accepted'] else ""
        print(f"    {r['ep_id']}  {r['confidence']:<12} {r['pattern_id']}  {r['pattern_name']}{flag}")


def show_available_patterns_simple(engagement_id):
    """Display patterns in compact form for reference during input."""
    rows = execute_query(
        """SELECT ep.ep_id, p.pattern_id, p.pattern_name, ep.confidence
           FROM EngagementPatterns ep
           JOIN Patterns p ON ep.pattern_id = p.pattern_id
           WHERE ep.engagement_id = ?
           ORDER BY CASE ep.confidence
               WHEN 'High' THEN 1
               WHEN 'Medium' THEN 2
               ELSE 3 END""",
        (engagement_id,)
    )
    print("\n  Patterns for this engagement:")
    for r in rows:
        print(f"    {r['ep_id']}  {r['confidence']:<12} {r['pattern_id']} — {r['pattern_name']}")
    print()


def get_valid_ep_ids(engagement_id):
    """Return set of valid ep_ids for this engagement."""
    rows = execute_query(
        "SELECT ep_id FROM EngagementPatterns WHERE engagement_id = ?",
        (engagement_id,)
    )
    return {r['ep_id'] for r in rows}


def prompt_pattern_id(engagement_id):
    """Prompt for primary pattern ID with validation."""
    valid = get_valid_ep_ids(engagement_id)
    while True:
        raw = input("  Primary pattern ep_id (or NONE): ").strip().upper()
        if raw == 'NONE' or raw == '':
            return None
        if raw in valid:
            # Get the pattern_id from ep_id
            rows = execute_query(
                "SELECT pattern_id FROM EngagementPatterns WHERE ep_id = ?",
                (raw,)
            )
            return rows[0]['pattern_id'] if rows else None
        print(f"  Invalid ep_id. Valid options: {', '.join(sorted(valid))}")


def prompt_contributing_eps(engagement_id):
    """Prompt for comma-separated list of contributing ep_ids."""
    valid = get_valid_ep_ids(engagement_id)
    while True:
        raw = input("  Contributing ep_ids (comma-separated, or NONE): ").strip().upper()
        if raw == 'NONE' or raw == '':
            return []
        ids = [x.strip() for x in raw.split(',')]
        invalid = [i for i in ids if i not in valid]
        if invalid:
            print(f"  Invalid ep_ids: {', '.join(invalid)}")
            print(f"  Valid options: {', '.join(sorted(valid))}")
        else:
            return ids


def accept_patterns(ep_ids):
    """Set accepted=1 on a list of ep_ids."""
    for ep_id in ep_ids:
        execute_write(
            "UPDATE EngagementPatterns SET accepted = 1 WHERE ep_id = ?",
            (ep_id,)
        )


def run(engagement_id):
    """Interactive loop to populate OPDFindings."""
    print_header(f"POPULATE FINDINGS — {engagement_id}")

    eng = get_engagement(engagement_id)
    if not eng:
        print_error(f"Engagement {engagement_id} not found.")
        return

    print(f"  Client:     {eng['firm_name']}")
    print(f"  Engagement: {eng['engagement_name']}")

    # Show existing findings
    existing = execute_query(
        "SELECT finding_id, finding_title, priority FROM OPDFindings WHERE engagement_id = ? ORDER BY priority",
        (engagement_id,)
    )
    if existing:
        print(f"\n  Existing findings ({len(existing)}):")
        for f in existing:
            print(f"    {f['finding_id']}  Priority {f['priority']}  {f['finding_title']}")

    # Show available patterns
    show_available_patterns_simple(engagement_id)

    findings_created = 0
    patterns_accepted = []

    while True:
        divider()
        print(f"  FINDING #{len(existing) + findings_created + 1}")
        divider()

        # Core fields
        title      = prompt_text("Finding title")
        domain     = prompt_domain()
        confidence = prompt_confidence()
        priority   = input("  Priority number (1 = highest): ").strip()

        # Pattern linkage
        print()
        print("  Pattern linkage — reference the pattern list above.")
        primary_pattern = prompt_pattern_id(engagement_id)
        contributing    = prompt_contributing_eps(engagement_id)

        # Narrative fields
        print()
        operational_impact = prompt_text("Operational impact (what is happening and why it matters)")
        economic_impact    = prompt_text("Economic impact (dollar range with CONFIRMED/INFERRED notation)")
        root_cause         = prompt_text("Root cause (one sentence)")
        recommendation     = prompt_text("Primary recommendation (one sentence)")

        # Optional fields
        opd_section = prompt_text("OPD report section number (optional)", required=False)

        # Effort and complexity
        effort     = prompt_priority()

        # Confirm
        divider()
        finding_id = next_finding_id()
        print(f"  Finding ID:  {finding_id}")
        print(f"  Title:       {title}")
        print(f"  Domain:      {domain}")
        print(f"  Confidence:  {confidence}")
        print(f"  Priority:    {priority}")
        print(f"  Pattern:     {primary_pattern or 'None'}")
        print(f"  Contributing: {', '.join(contributing) or 'None'}")

        if not prompt_confirm("Write this finding to database?"):
            print("  Skipped.")
        else:
            today = date.today().isoformat()
            execute_write(
                "INSERT INTO OPDFindings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    finding_id,
                    engagement_id,
                    primary_pattern,
                    title,
                    domain,
                    confidence,
                    operational_impact,
                    economic_impact,
                    root_cause,
                    recommendation,
                    int(priority) if priority.isdigit() else None,
                    effort,
                    opd_section or None,
                    today
                )
            )

            # Accept contributing patterns
            all_eps = contributing
            if primary_pattern:
                # Find the ep_id for this pattern
                ep_rows = execute_query(
                    "SELECT ep_id FROM EngagementPatterns WHERE engagement_id = ? AND pattern_id = ?",
                    (engagement_id, primary_pattern)
                )
                if ep_rows:
                    all_eps = list(set(contributing + [ep_rows[0]['ep_id']]))

            if all_eps:
                accept_patterns(all_eps)
                patterns_accepted.extend(all_eps)

            print_confirmation(f"Finding {finding_id} created.")
            if all_eps:
                print_confirmation(f"Patterns accepted: {', '.join(all_eps)}")
            findings_created += 1

        # Continue?
        print()
        if not prompt_confirm("Add another finding?"):
            break

    # Summary
    divider()
    print_confirmation(f"Session complete: {findings_created} findings created.")
    if patterns_accepted:
        print_confirmation(f"Patterns accepted: {', '.join(set(patterns_accepted))}")
    if findings_created > 0:
        print(f"\n  Next step: python top.py populate-roadmap {engagement_id}")
    print()
