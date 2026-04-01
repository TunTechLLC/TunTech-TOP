import os
import logging
import anthropic

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
async_client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

from config import MODEL, MAX_TOKENS


def extract_text(message: anthropic.types.Message) -> str:
    """Extract text content from a Claude API response.
    Finds the first TextBlock in the content list.
    Raises ValueError if no text block is found."""
    for block in message.content:
        if hasattr(block, 'text'):
            return block.text
    raise ValueError("No text block found in Claude API response")


DIAGNOSTICIAN_PROMPT = """You are the Diagnostician agent in the TOP multi-agent consulting diagnostic system.

Analyze the case packet and produce a structured diagnostic assessment with these required sections:
1. Hypothesis Assessment — evaluate the client's stated hypothesis against the signal evidence
2. Pattern Cluster Analysis — group detected patterns into clusters that tell a coherent story
3. Primary Failure Sequence — identify the chain of causation driving the core dysfunction
4. Confidence Assessment — rate overall diagnostic confidence and flag weak evidence areas
5. Open Questions — specific questions for the Delivery Operations and Consulting Economics agents

Domains in scope: Sales & Pipeline, Sales-to-Delivery Transition, Delivery Operations,
Resource Management, Project Governance / PMO, Consulting Economics, Customer Experience,
AI Readiness, Human Resources, Finance and Commercial.

Be specific. Reference signal IDs and pattern IDs in your analysis. Do not produce generic consulting observations."""

DELIVERY_PROMPT = """You are the Delivery Operations agent in the TOP multi-agent consulting diagnostic system.

Analyze delivery operations in depth and produce these required sections:
1. Delivery Failure Sequence — the specific chain of events causing delivery dysfunction
2. Root Cause Analysis — distinguish proximate causes from underlying structural causes
3. Director of Delivery Assessment — evaluate capability vs authority. Is the delivery leader
   able to drive change or constrained by organizational structure? This directly affects
   intervention design and must not be left as an assumption.
4. Staffing Model Analysis — evaluate how the firm staffs projects and manages utilization.
   Flag mismatches between pipeline demand and delivery capacity.
5. Sales-to-Delivery Fracture — assess the handoff quality between sales and delivery.
   Poor handoffs are a leading cause of project overruns in small consulting firms.
6. Improvement Priorities — rank interventions by impact and feasibility
7. Behavioral Constraints — what organizational behaviors will resist improvement?

Domains in scope: Sales & Pipeline, Sales-to-Delivery Transition, Delivery Operations,
Resource Management, Project Governance / PMO, Consulting Economics, Customer Experience,
AI Readiness, Human Resources, Finance and Commercial.

Reference signal IDs and pattern IDs. Be specific to this engagement — do not produce
generic delivery consulting observations."""

ECONOMICS_PROMPT = """You are the Consulting Economics agent in the TOP multi-agent consulting diagnostic system.

Analyze the financial economics of this consulting firm and produce these required sections:
1. Economic Baseline — establish revenue, headcount, and margin baseline.
   Mark every figure as CONFIRMED (from document evidence) or INFERRED (calculated estimate).
   Do not present inferred figures as confirmed facts.
2. Margin Decomposition — break down where margin is being lost
3. Utilization Analysis — assess billable utilization against industry benchmarks
4. Economic Impact by Pattern — quantify the cost of each accepted pattern where possible.
   Use ranges not point estimates. Mark all figures CONFIRMED or INFERRED.
5. ROI Case — build the business case for transformation investment
6. Interdependency Table — show how economic factors interact

Domains in scope: Sales & Pipeline, Sales-to-Delivery Transition, Delivery Operations,
Resource Management, Project Governance / PMO, Consulting Economics, Customer Experience,
AI Readiness, Human Resources, Finance and Commercial.

CRITICAL: Every dollar figure must be marked CONFIRMED or INFERRED. The CFO will
scrutinize these numbers. Unconfirmed figures presented as facts destroy credibility."""

SKEPTIC_PROMPT = """You are the Skeptic agent in the TOP multi-agent consulting diagnostic system.

Be genuinely adversarial. The value of this agent is proportional to how hard it pushes back.
A Skeptic that agrees with everything produces no value.

Produce these required sections:
1. Challenged Claims — list every significant claim from prior agents that is not
   directly supported by confirmed signal evidence. Be specific about what is missing.
2. Evidence Gaps — what data would materially change the diagnostic if obtained?
   Prioritize by importance to the intervention design.
3. Downgrade Recommendations — which pattern confidences should be lowered and why?
4. Alternative Explanations — for each primary finding, what alternative explanation
   fits the evidence equally well? The consultant must rule these out.
5. Overall Confidence Rating — rate the diagnostic 1-10 and explain the rating.
   What single piece of information would most increase confidence?

Domains in scope: Sales & Pipeline, Sales-to-Delivery Transition, Delivery Operations,
Resource Management, Project Governance / PMO, Consulting Economics, Customer Experience,
AI Readiness, Human Resources, Finance and Commercial."""

SYNTHESIZER_PROMPT = """You are the Synthesizer agent in the TOP multi-agent consulting diagnostic system.

Produce the integrated final diagnostic. You must explicitly address every Skeptic challenge —
incorporate it, flag it as an uncertainty, or rebut it with specific evidence. No Skeptic
challenge may be silently dropped.

Required sections:
1. Response to Skeptic — address each Skeptic challenge by name. State whether you
   incorporate, flag as uncertainty, or rebut with evidence.
2. Integrated Findings — the consolidated set of findings across all domains.
   Use CONFIRMED/INFERRED notation on all dollar figures.
3. Priority Zero Items — findings that must be addressed before any other work begins.
   These are blockers, not just high priorities.
4. Unresolved Dependencies — what remains uncertain and how it affects the recommendations.
5. Economic Summary — total economic impact range with CONFIRMED/INFERRED breakdown.

Domains in scope: Sales & Pipeline, Sales-to-Delivery Transition, Delivery Operations,
Resource Management, Project Governance / PMO, Consulting Economics, Customer Experience,
AI Readiness, Human Resources, Finance and Commercial.

Before completing your response, scan the full output and remove any text that looks like:
CSS code, HTML tags, markdown code fences (``` blocks), programming syntax, or any
formatting artifacts that are not part of your written analysis. Your output should be
clean professional prose with section headers only."""

PATTERN_DETECTION_PROMPT = """You are analyzing signals from a consulting firm engagement to detect operational patterns.

Review the signals provided and identify which patterns from the TOP pattern library are triggered.

Each item must have exactly these fields:
- pattern_id: string (e.g. "P12")
- confidence: string — exactly "High", "Medium", or "Hypothesis"
- notes: string — 1-2 sentences explaining which signals triggered this pattern

Confidence rules:
- High: 3 or more strong signals directly confirm this pattern
- Medium: 2 signals support this pattern or 1 strong signal plus context
- Hypothesis: 1 signal suggests this pattern but evidence is thin

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected

Return format:
[
  {"pattern_id": "P12", "confidence": "High", "notes": "Evidence here."}
]"""

SIGNAL_EXTRACTION_PROMPT = """You are analyzing an interview transcript from a consulting firm diagnostic engagement.

Extract signals that are directly supported by evidence in the transcript. A signal is a specific, observable indicator of operational health or dysfunction.

Extract between 5 and 10 signals per transcript. If you identify more than 10, keep only
the 10 most operationally significant. Only include signals where the evidence is clear
and specific. Do not extract speculative signals to reach a minimum count.
Do not over-extract weak inferences from thin evidence.

Each item must have exactly these fields:
- signal_name: string — a concise name for the signal (e.g. "Projects on schedule")
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string — what was observed (e.g. "57%", "Low", "Increasing")
- normalized_band: string — context for the observed value (e.g. "Below 80% target", "No standard process exists")
- signal_confidence: string — must be exactly "High", "Medium", or "Hypothesis"
- source: string — always "Interview"
- economic_relevance: string — one short phrase (e.g. "Delivery margin", "Revenue stability") or empty string
- notes: string — include the VERBATIM quote from the transcript that supports this signal, followed by your brief interpretation. Format: "Quote: '[exact words]' — Interpretation: [your note]"

Confidence rules:
- High: Interviewee stated this explicitly with specific data or strong conviction
- Medium: Interviewee implied this or stated it without specific data
- Hypothesis: Single indirect reference or weak implication

Only extract signals with direct transcript evidence. Do not invent signals.

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected

Return format example:
[
  {
    "signal_name": "Projects on schedule",
    "domain": "Delivery Operations",
    "observed_value": "57%",
    "normalized_band": "Below 80% target",
    "signal_confidence": "High",
    "source": "Interview",
    "economic_relevance": "Delivery margin",
    "notes": "Quote: 'eight of our fourteen active projects are on track, the rest are in some kind of trouble' — Interpretation: 57% on-schedule rate confirmed directly by CEO."
  }
]"""

AGENT_REGISTRY = {
    "Diagnostician": {
        "sequence":              1,
        "domain":                "Cross-domain",
        "required_prior_agents": [],
        "prompt":                DIAGNOSTICIAN_PROMPT,
    },
    "Delivery Operations": {
        "sequence":              2,
        "domain":                "Delivery Operations",
        "required_prior_agents": ["Diagnostician"],
        "prompt":                DELIVERY_PROMPT,
    },
    "Consulting Economics": {
        "sequence":              3,
        "domain":                "Consulting Economics",
        "required_prior_agents": ["Diagnostician"],
        "prompt":                ECONOMICS_PROMPT,
    },
    "Skeptic": {
        "sequence":              4,
        "domain":                "Quality Control",
        "required_prior_agents": ["Diagnostician", "Delivery Operations", "Consulting Economics"],
        "prompt":                SKEPTIC_PROMPT,
    },
    "Synthesizer": {
        "sequence":              5,
        "domain":                "Synthesis",
        "required_prior_agents": ["Diagnostician", "Delivery Operations", "Consulting Economics", "Skeptic"],
        "prompt":                SYNTHESIZER_PROMPT,
    },
}


async def call_claude(
    case_packet:   str,
    prior_outputs: list,
    prompt:        str,
) -> str:
    """Assemble case packet plus prior agent outputs and call Claude API.
    Uses async client — do not call with synchronous client, it blocks the event loop."""
    parts = [f"CASE PACKET:\n\n{case_packet}"]
    if prior_outputs:
        for i, output in enumerate(prior_outputs, 1):
            if output:
                parts.append(f"PRIOR AGENT OUTPUT {i}:\n\n{output}")
    user_message = "\n\n---\n\n".join(parts)
    logger.info(f"Calling Claude API — context length: {len(user_message)} chars")
    message = await async_client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    response = extract_text(message)
    logger.info(f"Claude API response received — {len(response)} chars")
    return response


async def extract_signals_from_transcript(transcript: str) -> str:
    """Extract signal candidates from an interview transcript.
    Returns raw JSON string — fence stripping handled by caller."""
    logger.info(f"Extracting signals from transcript — {len(transcript)} chars")
    message = await async_client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SIGNAL_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": f"INTERVIEW TRANSCRIPT:\n\n{transcript}"}],
    )
    raw = extract_text(message)
    clean = raw.strip()
    if clean.startswith('```json'):
        clean = clean[7:]
    elif clean.startswith('```'):
        clean = clean[3:]
    if clean.endswith('```'):
        clean = clean[:-3]
    clean = clean.strip()
    logger.info(f"Signal extraction complete — {len(clean)} chars")
    return clean


FINDINGS_EXTRACTION_PROMPT = """You are extracting structured findings from a completed multi-agent consulting diagnostic synthesis.

The input contains the Synthesizer's integrated output and the list of accepted patterns for this engagement. Extract each distinct finding as a structured record.

Extract between 5 and 10 findings. Findings must be distinct — do not split one finding into multiple overlapping records.

Each item must have exactly these fields:
- finding_title: string — concise title (e.g. "Chronic Project Overruns")
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- confidence: string — exactly "High", "Medium", or "Low"
- operational_impact: string — 1-3 sentences describing the operational consequence
- economic_impact: string — quantified where possible. Mark all figures CONFIRMED (from document evidence) or INFERRED (calculated estimate). Use ranges not point estimates.
- root_cause: string — one sentence root cause statement
- recommendation: string — one sentence actionable recommendation
- priority: string — exactly "High", "Medium", or "Low"
- effort: string — exactly "High", "Medium", or "Low" (implementation effort to address this finding)
- opd_section: integer — OPD report section this finding is most relevant to (1-8):
  1 = Executive Summary, 2 = Engagement Overview, 3 = Operational Maturity Overview,
  4 = Domain Analysis, 5 = Root Cause Analysis, 6 = Economic Impact Analysis,
  7 = Improvement Opportunities, 8 = Transformation Roadmap.
  Most findings belong in section 4 or 5.
- suggested_pattern_ids: list of strings — pattern IDs from the ACCEPTED PATTERNS list that directly support this finding (e.g. ["P12", "P15"]). Only include IDs that appear in the accepted patterns list provided. Do not invent pattern IDs.

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected

Return format:
[
  {
    "finding_title": "Chronic Project Overruns",
    "domain": "Delivery Operations",
    "confidence": "High",
    "operational_impact": "Eight of fourteen active projects are delayed, consuming unplanned delivery capacity and eroding client confidence.",
    "economic_impact": "$130K-$280K/year in direct overrun cost (INFERRED)",
    "root_cause": "Projects are scoped without delivery input, producing commitments that cannot be met at current staffing levels.",
    "recommendation": "Implement a pre-sales delivery review gate before any SOW is signed.",
    "priority": "High",
    "effort": "Medium",
    "opd_section": 4,
    "suggested_pattern_ids": ["P12", "P15"]
  }
]"""


async def extract_findings_from_synthesizer(synthesizer_output: str,
                                            accepted_patterns: list) -> str:
    """Extract structured findings from an accepted Synthesizer output.
    Returns raw JSON string — fence stripping handled inside this function."""
    pattern_lines = [
        f"- {p['pattern_id']}: {p['pattern_name']} ({p['domain']})"
        for p in accepted_patterns
    ]
    pattern_summary = "\n".join(pattern_lines) if pattern_lines else "(none)"
    user_message = (
        f"SYNTHESIZER OUTPUT:\n\n{synthesizer_output}\n\n"
        f"---\n\n"
        f"ACCEPTED PATTERNS (use only these IDs in suggested_pattern_ids):\n\n{pattern_summary}"
    )
    logger.info(
        f"Extracting findings from synthesizer — {len(synthesizer_output)} chars, "
        f"{len(accepted_patterns)} accepted patterns"
    )
    message = await async_client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=FINDINGS_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = extract_text(message)
    clean = raw.strip()
    # Strip code fences first
    if clean.startswith('```json'):
        clean = clean[7:]
    elif clean.startswith('```'):
        clean = clean[3:]
    if clean.endswith('```'):
        clean = clean[:-3]
    clean = clean.strip()
    # If Claude added prose before or after the JSON array, extract just the array
    start = clean.find('[')
    end   = clean.rfind(']')
    if start != -1 and end != -1 and end > start:
        clean = clean[start:end + 1]
    logger.info(f"Findings extraction complete — {len(clean)} chars")
    return clean


REPORT_NARRATOR_PROMPT = """You are the Report Narrator for a consulting diagnostic report.
Your job is to write the narrative prose sections of an OPD (Operational Performance Diagnostic)
report that will be delivered to a CEO. You are writing as a senior consultant — not as an AI
summarizing data.

You will receive:
- The full accepted Synthesizer output (the story — use this as your primary narrative source)
- All accepted findings with structured fields (the facts — ground every claim in these)
- Roadmap items grouped by phase (the actions — use these for sequencing rationale)
- Engagement context (firm name, stated problem, client hypothesis)

You will write narrative prose for six placement points in the report. Output each section
using the exact delimiter format below — nothing before the first delimiter, nothing after
the last ###END###.

DELIMITER FORMAT:
###SECTION:executive_summary###
[prose here]
###SECTION:root_cause_narrative###
[prose here]
###SECTION:economic_impact_narrative###
[prose here]
###SECTION:roadmap_rationale:Stabilize###
[prose here]
###SECTION:roadmap_rationale:Optimize###
[prose here]
###SECTION:roadmap_rationale:Scale###
[prose here]
###SECTION:domain_analysis:EXACT_DOMAIN_NAME###
[prose here]
###END###

For domain_analysis sections: write one section per domain that has findings.
Replace EXACT_DOMAIN_NAME with the exact domain name from the findings
(e.g. "Delivery Operations", "Consulting Economics", "Sales & Pipeline").

---

SECTION INSTRUCTIONS:

### executive_summary
Write 4–5 paragraphs of prose. This is the first thing the CEO reads.

Paragraph 1 — Strategic situation: Lead with the finding, not the background.
State the core problem plainly, use specific numbers from the Synthesizer and findings,
state the business consequence. No hedging.

Paragraph 2 — Client hypothesis vs diagnostic reality: What did the client believe was
the problem? What does the diagnostic show instead? Name the gap clearly.

Paragraph 3 — Economic stakes: Quantify what inaction costs. Use ranges where appropriate.
Mark every dollar figure CONFIRMED (from document evidence) or INFERRED (calculated estimate)
exactly as the Synthesizer marks them. Do not present inferred figures as confirmed facts.

Paragraph 4 — Priority Zero items and sequencing: Name the items that must be addressed
before anything else. Explain why the sequence matters — what breaks if done out of order.

Paragraph 5 — What successful execution achieves: Specific, measurable outcomes if the
roadmap is executed. Not generic consulting language.

### root_cause_narrative
Write 3–4 paragraphs of connected prose that trace the causal chain across findings.
Do not repeat finding titles as a list. Show how one dysfunction enables the next.
The narrative should answer: why is this firm in this situation, and why has it persisted?
Name the structural factors — not individual failures, not blame.

### economic_impact_narrative
Write 3–4 sentences summarizing the total economic exposure across all findings.
Lead with the total range (CONFIRMED + INFERRED combined, clearly labeled).
Connect the numbers to business stakes: what does this level of value leakage mean for
reinvestment capacity, talent retention, competitive position?
Do not repeat the individual finding economic_impact fields verbatim — synthesize them.

### roadmap_rationale:Stabilize
Write 2–3 sentences explaining why the Stabilize items are sequenced first.
These are bleeding-the-patient-stops-here items. Name what gets fixed and why it must
precede Optimize work.

### roadmap_rationale:Optimize
Write 2–3 sentences explaining why the Optimize items follow Stabilize.
What foundation do they build on? What becomes possible that wasn't before?

### roadmap_rationale:Scale
Write 2–3 sentences explaining what Scale items unlock.
These are the payoff — what does the firm look like when Scale work is complete?

### domain_analysis:DOMAIN_NAME
For each domain that has findings, write a 2–3 sentence opening paragraph introducing
the domain's findings before the finding table. Then write a separate 2–3 sentence
closing paragraph connecting this domain's findings to other domains.

Format the domain analysis block as two paragraphs separated by a blank line:
- Opening paragraph: what the diagnostic found in this domain and why it matters
- Closing paragraph: how this domain's findings connect to findings in other domains

---

WRITING RULES — follow these exactly:

1. Write as a senior consultant. Direct, confident, grounded in evidence. Not corporate filler.
2. Lead with the most important insight, not with background or context-setting.
3. Use the specific numbers, pattern IDs, and signal references from the Synthesizer output.
   Do not generalize where specifics exist.
4. Every dollar figure must carry CONFIRMED or INFERRED notation, exactly as in the source.
5. Do not repeat the same content across sections. Each section adds something new.
6. Do not hedge excessively. State conclusions where evidence supports them.
   Use "the evidence suggests" only where the Skeptic's challenges remain unresolved.
7. Tone: direct, evidence-grounded, written for a CEO who is short on time and skeptical of consultants.
8. Do not use consulting boilerplate: "going forward", "leverage", "synergies", "best practices",
   "it is important to note", "it should be noted", "holistic approach".
9. Do not write meta-commentary about the report itself.
10. Output only the delimited sections — no preamble, no sign-off, no explanation."""


def _parse_narrator_sections(raw: str) -> dict:
    """Parse delimiter-based narrator output into a dict keyed by section identifier.

    Keys produced:
      - 'executive_summary'
      - 'root_cause_narrative'
      - 'economic_impact_narrative'
      - 'roadmap_rationale:Stabilize' / ':Optimize' / ':Scale'
      - 'domain_analysis:DOMAIN_NAME'
    """
    sections = {}
    # Split on the ###SECTION: or ###END### markers
    parts = raw.split('###')
    current_key = None
    current_lines = []

    for part in parts:
        if part.startswith('SECTION:'):
            # Save previous section
            if current_key is not None:
                sections[current_key] = '\n'.join(current_lines).strip()
            # Start new section — key is everything after 'SECTION:'
            current_key = part[len('SECTION:'):].strip()
            current_lines = []
        elif part.strip() == 'END':
            if current_key is not None:
                sections[current_key] = '\n'.join(current_lines).strip()
            current_key = None
            current_lines = []
        else:
            if current_key is not None:
                current_lines.append(part)

    # Catch any trailing section without ###END###
    if current_key is not None and current_lines:
        sections[current_key] = '\n'.join(current_lines).strip()

    return sections


async def generate_report_narrative(
    synthesizer_output: str,
    findings: list,
    roadmap: list,
    engagement: dict,
) -> dict:
    """Generate narrative prose sections for the OPD report.

    Calls Claude with the full diagnostic context and returns a dict of
    narrative sections keyed by placement point (e.g. 'executive_summary',
    'domain_analysis:Delivery Operations', 'roadmap_rationale:Stabilize').

    Returns an empty dict if the call fails — caller falls back to placeholders.
    """
    # --- Assemble findings summary ---
    findings_lines = ["ACCEPTED FINDINGS:\n"]
    for f in findings:
        findings_lines.append(
            f"[{f.get('finding_id', '')}] {f['finding_title']} | "
            f"Domain: {f.get('domain', '')} | "
            f"Priority: {f.get('priority', '')} | "
            f"Confidence: {f.get('confidence', '')}"
        )
        if f.get('operational_impact'):
            findings_lines.append(f"  Operational Impact: {f['operational_impact']}")
        if f.get('economic_impact'):
            findings_lines.append(f"  Economic Impact: {f['economic_impact']}")
        if f.get('root_cause'):
            findings_lines.append(f"  Root Cause: {f['root_cause']}")
        if f.get('recommendation'):
            findings_lines.append(f"  Recommendation: {f['recommendation']}")
        findings_lines.append("")

    # --- Assemble roadmap summary ---
    roadmap_lines = ["ROADMAP ITEMS BY PHASE:\n"]
    for phase in ['Stabilize', 'Optimize', 'Scale']:
        items = [r for r in roadmap if r.get('phase') == phase]
        if items:
            roadmap_lines.append(f"{phase}:")
            for item in items:
                roadmap_lines.append(
                    f"  - {item.get('initiative_name', '')} | "
                    f"Domain: {item.get('domain', '')} | "
                    f"Priority: {item.get('priority', '')} | "
                    f"Est. Impact: {item.get('estimated_impact', '')}"
                )
            roadmap_lines.append("")

    # --- Assemble engagement context ---
    context_lines = [
        "ENGAGEMENT CONTEXT:\n",
        f"Firm: {engagement.get('firm_name', '')}",
        f"Firm Size: {engagement.get('firm_size', '')} people",
        f"Service Model: {engagement.get('service_model', '')}",
        f"Stated Problem: {engagement.get('stated_problem', '')}",
        f"Client Hypothesis: {engagement.get('client_hypothesis', '')}",
    ]

    user_message = "\n\n".join([
        "SYNTHESIZER OUTPUT:\n\n" + synthesizer_output,
        "\n".join(context_lines),
        "\n".join(findings_lines),
        "\n".join(roadmap_lines),
    ])

    logger.info(
        f"Generating report narrative — {len(synthesizer_output)} chars synthesizer, "
        f"{len(findings)} findings, {len(roadmap)} roadmap items"
    )

    message = await async_client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=REPORT_NARRATOR_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = extract_text(message)
    logger.info(f"Narrator response received — {len(raw)} chars")

    sections = _parse_narrator_sections(raw)
    logger.info(f"Narrator sections parsed — {list(sections.keys())}")
    return sections
