# TOP Patterns Command
# Handles: detect-patterns, load-patterns

import os
from datetime import date
from db.connection import execute_query, execute_write
from utils.formatting import print_header, print_confirmation, print_error, prompt_confirm, divider
from utils.clipboard import copy_to_clipboard


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


def run_detect(engagement_id):
    """Query signals and copy to clipboard for Claude pattern detection."""
    print_header(f"DETECT PATTERNS — {engagement_id}")

    # Verify engagement exists
    eng = get_engagement(engagement_id)
    if not eng:
        print_error(f"Engagement {engagement_id} not found.")
        return

    print(f"  Client:     {eng['firm_name']}")
    print(f"  Engagement: {eng['engagement_name']}")

    # Query signals
    rows = execute_query(
        """SELECT domain, signal_name, observed_value, normalized_band,
                  signal_confidence, source, notes
           FROM vw_EngagementSignals
           WHERE engagement_id = ?
           ORDER BY domain, signal_confidence DESC""",
        (engagement_id,)
    )

    if not rows:
        print_error("No signals found for this engagement.")
        return

    print(f"\n  Signals found: {len(rows)}")
    divider()

    # Format as clean text block
    lines = []
    lines.append(f"ENGAGEMENT SIGNALS — {eng['firm_name']} ({engagement_id})")
    lines.append(f"Generated: {date.today().isoformat()}")
    lines.append(f"Total signals: {len(rows)}")
    lines.append("")

    current_domain = None
    for row in rows:
        if row['domain'] != current_domain:
            current_domain = row['domain']
            lines.append(f"--- {current_domain} ---")
        lines.append(
            f"  Signal:      {row['signal_name']}"
        )
        lines.append(
            f"  Observed:    {row['observed_value']}"
        )
        lines.append(
            f"  Band:        {row['normalized_band']}"
        )
        lines.append(
            f"  Confidence:  {row['signal_confidence']}  |  Source: {row['source']}"
        )
        if row['notes']:
            lines.append(f"  Notes:       {row['notes']}")
        lines.append("")

    output = "\n".join(lines)

    # Copy to clipboard
    if copy_to_clipboard(output):
        print_confirmation("Signal data copied to clipboard.")
    else:
        print("  Signal data:")
        print(output)

    print()
    print("  NEXT STEPS:")
    print("  1. Open Claude in a new conversation")
    print("  2. Paste your Signal-to-Pattern Mapping Table content")
    print("  3. Paste the signal data (already on clipboard)")
    print("  4. Paste the pattern detection prompt from Agent Prompt Master")
    print("  5. Save Claude's INSERT statements to a .sql file")
    print(f"  6. Run: python top.py load-patterns {engagement_id} <file.sql>")
    print()


def run_load(engagement_id, sql_file):
    """Load EngagementPatterns INSERT statements from a .sql file."""
    print_header(f"LOAD PATTERNS — {engagement_id}")

    # Verify engagement exists
    eng = get_engagement(engagement_id)
    if not eng:
        print_error(f"Engagement {engagement_id} not found.")
        return

    # Verify file exists
    if not os.path.exists(sql_file):
        print_error(f"File not found: {sql_file}")
        return

    print(f"  Client:     {eng['firm_name']}")
    print(f"  Engagement: {eng['engagement_name']}")
    print(f"  File:       {sql_file}")
    divider()

    # Read and parse the SQL file
    with open(sql_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into individual statements
    statements = [
        s.strip() for s in content.split(';')
        if s.strip() and not s.strip().startswith('--')
    ]

    if not statements:
        print_error("No SQL statements found in file.")
        return

    print(f"  Statements found: {len(statements)}")

    # Validate all statements before writing any
    errors = []
    inserts = []
    for i, stmt in enumerate(statements, 1):
        if not stmt.upper().startswith('INSERT INTO ENGAGEMENTPATTERNS'):
            errors.append(f"Statement {i} is not an INSERT INTO EngagementPatterns.")
            continue
        if f"'{engagement_id}'" not in stmt and f'"{engagement_id}"' not in stmt:
            errors.append(f"Statement {i} does not contain engagement_id {engagement_id}.")
            continue
        inserts.append(stmt)

    if errors:
        print_error("Validation failed. No records written.")
        for e in errors:
            print(f"    {e}")
        return

    print(f"  Valid inserts: {len(inserts)}")

    # Show confidence summary from statements
    high = sum(1 for s in inserts if "'High'" in s)
    medium = sum(1 for s in inserts if "'Medium'" in s)
    hypothesis = sum(1 for s in inserts if "'Hypothesis'" in s)
    print(f"  High: {high}  Medium: {medium}  Hypothesis: {hypothesis}")
    divider()

    if not prompt_confirm(f"Load {len(inserts)} patterns into database?"):
        print("  Cancelled.")
        return

    # Execute all inserts
    success = 0
    failed = 0
    for stmt in inserts:
        try:
            execute_write(stmt)
            success += 1
        except Exception as e:
            print_error(f"Failed: {e}")
            print(f"    Statement: {stmt[:80]}...")
            failed += 1

    divider()
    print_confirmation(f"{success} patterns loaded successfully.")
    if failed:
        print_error(f"{failed} patterns failed — check statements above.")

    # Verify
    counts = execute_query(
        """SELECT confidence, COUNT(*) as n
           FROM EngagementPatterns
           WHERE engagement_id = ?
           GROUP BY confidence
           ORDER BY confidence""",
        (engagement_id,)
    )
    print()
    print("  Database now contains:")
    for row in counts:
        print(f"    {row['confidence']}: {row['n']}")
    print()