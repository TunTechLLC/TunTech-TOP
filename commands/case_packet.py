# TOP Case Packet Command
# Handles: case-packet

from datetime import date
from db.connection import execute_query
from utils.formatting import print_header, print_confirmation, print_error, divider
from utils.clipboard import copy_to_clipboard
from config import BASE_DIR


def get_engagement(engagement_id):
    """Return engagement and client info or None if not found."""
    rows = execute_query(
        """SELECT e.engagement_id, e.engagement_name, e.stated_problem,
                  e.client_hypothesis, e.previously_tried, e.notes,
                  c.firm_name, c.firm_size, c.service_model
           FROM Engagements e
           JOIN Clients c ON e.client_id = c.client_id
           WHERE e.engagement_id = ?""",
        (engagement_id,)
    )
    return rows[0] if rows else None


def get_signals(engagement_id):
    """Return all signals for this engagement."""
    return execute_query(
        """SELECT domain, signal_name, observed_value, normalized_band,
                  signal_confidence, source, notes
           FROM vw_EngagementSignals
           WHERE engagement_id = ?
           ORDER BY domain,
                    CASE signal_confidence
                        WHEN 'High' THEN 1
                        WHEN 'Medium' THEN 2
                        ELSE 3 END""",
        (engagement_id,)
    )


def get_patterns(engagement_id):
    """Return all EngagementPatterns with full pattern definitions."""
    return execute_query(
        """SELECT ep.ep_id, ep.confidence, ep.economic_impact_est, ep.notes as ep_notes,
                  p.pattern_id, p.pattern_name, p.domain, p.economic_model,
                  p.economic_formula, p.trigger_signals, p.operational_impact,
                  p.likely_root_cause, p.recommended_improvements
           FROM EngagementPatterns ep
           JOIN Patterns p ON ep.pattern_id = p.pattern_id
           WHERE ep.engagement_id = ?
           ORDER BY CASE ep.confidence
                        WHEN 'High' THEN 1
                        WHEN 'Medium' THEN 2
                        ELSE 3 END,
                    p.domain""",
        (engagement_id,)
    )


def format_case_packet(eng, signals, patterns):
    """Format all data into a structured case packet text document."""
    lines = []

    # ── SECTION 1 — ENGAGEMENT HEADER ──────────────────────────
    lines.append("=" * 70)
    lines.append("SECTION 1 — ENGAGEMENT HEADER")
    lines.append("=" * 70)
    lines.append(f"Client:           {eng['firm_name']}")
    lines.append(f"Engagement:       {eng['engagement_name']}")
    lines.append(f"Engagement ID:    {eng['engagement_id']}")
    lines.append(f"Firm size:        {eng['firm_size']} total headcount")
    lines.append(f"Service model:    {eng['service_model']}")
    lines.append(f"Generated:        {date.today().isoformat()}")
    lines.append("")
    lines.append(f"Stated problem:")
    lines.append(f"  {eng['stated_problem']}")
    lines.append("")
    lines.append(f"Client hypothesis:")
    lines.append(f"  {eng['client_hypothesis']}")
    lines.append("")
    lines.append(f"Previously tried:")
    lines.append(f"  {eng['previously_tried']}")
    lines.append("")
    if eng['notes']:
        lines.append(f"Consultant notes:")
        lines.append(f"  {eng['notes']}")
        lines.append("")

    # ── SECTION 2 — SIGNAL BLOCK ────────────────────────────────
    lines.append("=" * 70)
    lines.append(f"SECTION 2 — SIGNAL BLOCK ({len(signals)} signals)")
    lines.append("=" * 70)

    current_domain = None
    for s in signals:
        if s['domain'] != current_domain:
            current_domain = s['domain']
            lines.append("")
            lines.append(f"[ {current_domain} ]")
            lines.append("-" * 50)

        lines.append(f"Signal:     {s['signal_name']}")
        lines.append(f"Observed:   {s['observed_value']}")
        lines.append(f"Band:       {s['normalized_band']}")
        lines.append(f"Confidence: {s['signal_confidence']}  |  Source: {s['source']}")
        if s['notes']:
            lines.append(f"Notes:      {s['notes']}")
        lines.append("")

    # ── SECTION 3 — PATTERN BLOCK ───────────────────────────────
    high    = [p for p in patterns if p['confidence'] == 'High']
    medium  = [p for p in patterns if p['confidence'] == 'Medium']
    hypo    = [p for p in patterns if p['confidence'] == 'Hypothesis']

    lines.append("=" * 70)
    lines.append(f"SECTION 3 — PATTERN BLOCK")
    lines.append(f"High: {len(high)}  Medium: {len(medium)}  Hypothesis: {len(hypo)}")
    lines.append("=" * 70)

    for confidence_group, label in [
        (high, "HIGH CONFIDENCE"),
        (medium, "MEDIUM CONFIDENCE"),
        (hypo, "HYPOTHESIS")
    ]:
        if not confidence_group:
            continue
        lines.append("")
        lines.append(f"--- {label} ---")
        for p in confidence_group:
            lines.append(f"Pattern:        {p['pattern_id']} — {p['pattern_name']}")
            lines.append(f"Domain:         {p['domain']}")
            lines.append(f"Economic model: {p['economic_model'] or 'N/A'}")
            lines.append(f"Formula:        {p['economic_formula'] or 'N/A'}")
            if p['economic_impact_est']:
                lines.append(f"Impact est:     {p['economic_impact_est'][:120]}")
            if p['ep_notes']:
                lines.append(f"Notes:          {p['ep_notes'][:120]}")
            lines.append("")

    # ── SECTION 4 — KNOWLEDGE INJECTION ─────────────────────────
    lines.append("=" * 70)
    lines.append("SECTION 4 — KNOWLEDGE INJECTION")
    lines.append("High confidence pattern definitions (from Patterns table)")
    lines.append("=" * 70)

    for p in high:
        lines.append("")
        lines.append(f"Pattern: {p['pattern_id']} — {p['pattern_name']}")
        lines.append(f"Domain:  {p['domain']}")
        if p['trigger_signals']:
            lines.append(f"Trigger signals:")
            lines.append(f"  {p['trigger_signals']}")
        if p['operational_impact']:
            lines.append(f"Operational impact:")
            lines.append(f"  {p['operational_impact']}")
        if p['likely_root_cause']:
            lines.append(f"Likely root cause:")
            lines.append(f"  {p['likely_root_cause']}")
        if p['recommended_improvements']:
            lines.append(f"Recommended improvements:")
            lines.append(f"  {p['recommended_improvements']}")
        lines.append("")

    lines.append("Medium confidence patterns (name and domain only):")
    for p in medium:
        lines.append(f"  {p['pattern_id']} — {p['pattern_name']} | {p['domain']}")

    lines.append("")
    lines.append("Hypothesis patterns (names only):")
    for p in hypo:
        lines.append(f"  {p['pattern_id']} — {p['pattern_name']}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF CASE PACKET")
    lines.append("=" * 70)

    return "\n".join(lines)


def run(engagement_id):
    """Assemble case packet and copy to clipboard."""
    print_header(f"CASE PACKET — {engagement_id}")

    eng = get_engagement(engagement_id)
    if not eng:
        print_error(f"Engagement {engagement_id} not found.")
        return

    print(f"  Client:     {eng['firm_name']}")
    print(f"  Engagement: {eng['engagement_name']}")
    divider()

    # Query all data
    signals = get_signals(engagement_id)
    patterns = get_patterns(engagement_id)

    print(f"  Signals:  {len(signals)}")
    print(f"  Patterns: {len(patterns)}")

    if not signals:
        print_error("No signals found. Cannot assemble case packet.")
        return

    if not patterns:
        print_error("No patterns found. Run detect-patterns and load-patterns first.")
        return

    # Format
    case_packet_text = format_case_packet(eng, signals, patterns)

    # Save to file
    safe_name = eng['firm_name'].replace(' ', '_').replace('/', '_')
    today = date.today().strftime('%Y-%m')
    filename = f"{safe_name}_CasePacket_{today}.txt"
    output_path = BASE_DIR / "reports" / filename

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(case_packet_text)

    print_confirmation(f"Case packet saved to: {output_path}")

    # Copy to clipboard
    if copy_to_clipboard(case_packet_text):
        print_confirmation("Case packet copied to clipboard.")

    divider()
    print("  NEXT STEPS:")
    print("  1. Open Agent Prompt Master from TOP/07_Admin/")
    print("  2. Open Claude — new conversation")
    print("  3. Paste the case packet (already on clipboard)")
    print("  4. Paste Agent 1 — Diagnostician prompt")
    print("  5. Run agent, save output to 05_Agent_Outputs/")
    print(f"  6. Run: python top.py log-agent-run {engagement_id} Diagnostician")
    print()

    # Word count estimate
    word_count = len(case_packet_text.split())
    token_estimate = word_count // 0.75
    print(f"  Case packet size: ~{word_count} words / ~{int(token_estimate)} tokens")
    if token_estimate > 8000:
        print("  WARNING: Case packet may be large for Claude context.")
        print("  Consider trimming Medium/Hypothesis pattern notes.")
    print()