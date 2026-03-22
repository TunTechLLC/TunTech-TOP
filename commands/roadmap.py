# TOP Roadmap Command
# Handles: populate-roadmap

from datetime import date
from db.connection import execute_query, execute_write
from utils.ids import next_roadmap_id
from utils.formatting import (
    print_header, print_confirmation, print_error,
    prompt_text, prompt_confirm, divider,
    prompt_domain, prompt_phase, prompt_priority
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


def show_findings(engagement_id):
    """Display OPDFindings available to link to roadmap items."""
    rows = execute_query(
        """SELECT finding_id, finding_title, priority
           FROM OPDFindings
           WHERE engagement_id = ?
           ORDER BY priority""",
        (engagement_id,)
    )
    if not rows:
        print("  No findings found for this engagement.")
        return
    print("\n  Findings available to link:")
    for r in rows:
        print(f"    {r['finding_id']}  Priority {r['priority']}  {r['finding_title']}")
    print()


def get_valid_finding_ids(engagement_id):
    """Return set of valid finding_ids for this engagement."""
    rows = execute_query(
        "SELECT finding_id FROM OPDFindings WHERE engagement_id = ?",
        (engagement_id,)
    )
    return {r['finding_id'] for r in rows}


def prompt_finding_id(engagement_id):
    """Prompt for a finding ID to link, with validation."""
    valid = get_valid_finding_ids(engagement_id)
    while True:
        raw = input("  Linked finding_id (or NONE): ").strip().upper()
        if raw == 'NONE' or raw == '':
            return None
        if raw in valid:
            return raw
        print(f"  Invalid finding_id. Valid options: {', '.join(sorted(valid))}")


def show_existing_items(engagement_id):
    """Show roadmap items already created for this engagement."""
    rows = execute_query(
        """SELECT item_id, phase, initiative_name
           FROM RoadmapItems
           WHERE engagement_id = ?
           ORDER BY phase, item_id""",
        (engagement_id,)
    )
    if rows:
        print(f"\n  Existing roadmap items ({len(rows)}):")
        current_phase = None
        for r in rows:
            if r['phase'] != current_phase:
                current_phase = r['phase']
                print(f"    [{current_phase}]")
            print(f"      {r['item_id']}  {r['initiative_name']}")
    return len(rows)


def run(engagement_id):
    """Interactive loop to populate RoadmapItems."""
    print_header(f"POPULATE ROADMAP — {engagement_id}")

    eng = get_engagement(engagement_id)
    if not eng:
        print_error(f"Engagement {engagement_id} not found.")
        return

    print(f"  Client:     {eng['firm_name']}")
    print(f"  Engagement: {eng['engagement_name']}")

    existing_count = show_existing_items(engagement_id)
    show_findings(engagement_id)

    items_created = 0

    while True:
        divider()
        print(f"  ROADMAP ITEM #{existing_count + items_created + 1}")
        divider()

        # Core fields
        initiative_name = prompt_text("Initiative name")
        domain          = prompt_domain()
        phase           = prompt_phase()
        priority        = prompt_priority()
        effort          = prompt_choice("Effort", ["High", "Medium", "Low"])
        estimated_impact = prompt_text("Estimated impact (economic or operational)")
        owner           = prompt_text("Owner (role or name)")
        target_date     = prompt_text("Target date (YYYY-MM-DD or approximate)")
        finding_id      = prompt_finding_id(engagement_id)

        # Confirm
        divider()
        item_id = next_roadmap_id()
        print(f"  Item ID:    {item_id}")
        print(f"  Initiative: {initiative_name}")
        print(f"  Phase:      {phase}")
        print(f"  Priority:   {priority}  |  Effort: {effort}")
        print(f"  Owner:      {owner}")
        print(f"  Target:     {target_date}")
        print(f"  Finding:    {finding_id or 'None'}")

        if not prompt_confirm("Write this roadmap item to database?"):
            print("  Skipped.")
        else:
            today = date.today().isoformat()
            execute_write(
                "INSERT INTO RoadmapItems VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    engagement_id,
                    finding_id,
                    initiative_name,
                    domain,
                    phase,
                    priority,
                    effort,
                    estimated_impact,
                    owner,
                    target_date,
                    'Proposed',
                    today
                )
            )
            print_confirmation(f"Roadmap item {item_id} created.")
            items_created += 1

        print()
        if not prompt_confirm("Add another roadmap item?"):
            break

    # Summary
    divider()
    print_confirmation(f"Session complete: {items_created} roadmap items created.")

    # Show totals by phase
    if items_created > 0:
        counts = execute_query(
            """SELECT phase, COUNT(*) as n
               FROM RoadmapItems
               WHERE engagement_id = ?
               GROUP BY phase
               ORDER BY CASE phase
                   WHEN 'Stabilize' THEN 1
                   WHEN 'Optimize' THEN 2
                   WHEN 'Scale' THEN 3 END""",
            (engagement_id,)
        )
        print("\n  Roadmap totals:")
        for r in counts:
            print(f"    {r['phase']}: {r['n']} items")
        print(f"\n  Next step: python top.py cross-engagement-report")
    print()