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

The case packet contains two sections: SIGNALS (what was observed) and PATTERN LIBRARY (the complete list of patterns you may detect, with trigger signals for each).

Review the signals and identify which patterns from the PATTERN LIBRARY are triggered. Use ONLY pattern_ids that appear in the PATTERN LIBRARY — do not invent IDs.

Before finalizing your response, check every domain in the PATTERN LIBRARY. Do not omit a domain simply because it has fewer signals than others. A single strong signal is enough to return a Hypothesis-confidence pattern.

Each item must have exactly these fields:
- pattern_id: string — must be an ID from the PATTERN LIBRARY (e.g. "P12")
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

ECONOMIC IMPACT REQUIREMENT:
Every economic_impact value must show the reasoning, not just the conclusion. A CFO must be able to follow the logic and argue with the assumptions. Format:
  "$[figure] ([CONFIRMED or INFERRED]: [calculation] — [source of each input])"

- CONFIRMED = figure comes directly from a document (financial statement, contract, invoice, etc.)
- INFERRED = figure is a calculated estimate from interview statements, observed patterns, or industry benchmarks
- Calculation: show the multiplication or formula used (e.g. "14 projects × 30% overrun rate × $67K avg value")
- Source: for each input, state where it came from — "from CEO interview", "from pipeline document", "industry benchmark for mid-size consulting firms"
- Use ranges not point estimates when inputs are estimated

Each item must have exactly these fields:
- finding_title: string — concise title (e.g. "Chronic Project Overruns")
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- confidence: string — exactly "High", "Medium", or "Low"
- operational_impact: string — 1-3 sentences describing the operational consequence
- economic_impact: string — quantified where possible, with inline reasoning as described above. If genuinely unquantifiable, state why in one sentence.
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
    "economic_impact": "$130K–$280K/year in direct overrun cost (INFERRED: 14 active projects × 30% average overrun rate × $67K average project value — overrun rate estimated from CEO interview; project value from pipeline document)",
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


ROADMAP_EXTRACTION_PROMPT = """You are extracting a structured transformation roadmap from a completed multi-agent consulting diagnostic synthesis.

The input contains the Synthesizer's integrated output and the accepted findings for this engagement.
Extract actionable improvement initiatives and assign each to a transformation phase.

Extract between 8 and 16 initiatives total. Each initiative must be distinct and actionable —
not a restatement of a finding, but a specific thing the firm must do to address it.

Each item must have exactly these fields:
- initiative_name: string — specific, action-oriented name (e.g. "Implement Pre-Sales Delivery Review Gate", not "Improve Sales Process")
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- phase: string — must be exactly "Stabilize", "Optimize", or "Scale" (see phase rules below)
- priority: string — exactly "High", "Medium", or "Low"
- effort: string — exactly "High", "Medium", or "Low" (implementation effort)
- estimated_impact: string — one sentence on what this initiative achieves when complete (e.g. "Eliminates below-cost deals from pipeline before SOW signature")
- rationale: string — one sentence citing the specific finding or Synthesizer evidence that drives this initiative
- owner: string — the role responsible for driving this initiative to completion (see owner rules below)

OWNER RULES — apply these strictly:
Only assign owners from roles explicitly named in the Synthesizer output or engagement context.
Do not invent role titles that do not appear in the diagnostic data.
Use these heuristics to match initiative content to confirmed roles:
  - SOW gates, delivery authority, project oversight, delivery process design → Director of Delivery
  - Organizational structure changes, CEO behavior changes, firm-level decisions → CEO
  - Financial controls, collections, invoicing, cost reporting → Operations Manager
  - Client relationship management, account expansion → CEO (if no account lead role is named)
  - Ambiguous ownership or role not confirmed in the diagnostic → "TBD — assign at kickoff"
If fewer than three distinct roles are named in the diagnostic data, some items will share an owner — that is correct, do not fabricate additional roles to distribute ownership.

PHASE ASSIGNMENT RULES — apply these strictly:

Stabilize: Items that stop active damage or remove blockers that make other work impossible.
  - Active margin bleed, delivery authority failures, governance blockers
  - Data collection required before board presentation or planning decisions
  - Anything where delay makes the situation measurably worse each week
  - Target: 4–6 items. If you have more than 6 Stabilize items, move the least urgent to Optimize.

Optimize: Items that improve operational performance on a foundation that Stabilize has made viable.
  - Process design, operating model changes, methodology implementation
  - Capacity planning, pipeline discipline, delivery standards
  - Items that require Stabilize work to be in place before they can hold
  - Target: 4–6 items.

Scale: Items that expand capability, capacity, or market position once operations are stable.
  - Revenue mix rebalancing, service line development, rate recovery
  - Client relationship upgrades, market positioning improvements
  - Items that require Optimize work to be credible or executable
  - Target: 2–4 items.

Do not put everything in Stabilize. If an initiative improves a process rather than stopping bleeding,
it belongs in Optimize. If it expands the business rather than fixing it, it belongs in Scale.

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected

Return format:
[
  {
    "initiative_name": "Reinstate Delivery Director Authority with CEO Endorsement",
    "domain": "Project Governance / PMO",
    "phase": "Stabilize",
    "priority": "High",
    "effort": "Low",
    "estimated_impact": "Removes organizational veto on delivery improvements and enables all subsequent delivery-dependent initiatives",
    "rationale": "Two prior improvement initiatives were blocked by the CEO bypass dynamic; all delivery fixes depend on this structural change",
    "owner": "CEO"
  }
]"""


REPORT_NARRATOR_PROMPT = """You are the Report Narrator for a consulting diagnostic report.
Your job is to write the narrative prose and structured table content for an OPD (Operational
Performance Diagnostic) report delivered to a CEO. Write as a senior consultant — not as an AI
summarizing data.

You will receive:
- The full accepted Synthesizer output (primary narrative source — use this for the story)
- Accepted findings with structured fields (ground every factual claim in these)
- Roadmap items by phase, each with item_id, phase, effort, owner, and estimated_impact
- Engagement context (firm name, stated problem, client hypothesis)

OUTPUT FORMAT — CRITICAL:
Return a single JSON object. No text before the opening brace. No text after the closing brace.
No markdown code fences. No explanation. Your response must begin with { and end with }.
Use \\n\\n between paragraphs within prose string values.
String values must be valid JSON — escape any double quotes inside strings with \\".

JSON SCHEMA — return exactly these keys:

{
  "executive_summary": "<4-5 paragraphs separated by \\n\\n>",
  "root_cause_narrative": "<4-5 paragraphs separated by \\n\\n>",
  "economic_impact_narrative": "<3-4 sentences>",
  "future_state_narrative": "<2-3 sentences describing the firm 18 months post-roadmap>",
  "domain_analysis": {
    "<exact domain name>": {
      "opening": "<2-3 sentence opening paragraph for this domain>",
      "closing": "<2-3 sentence closing paragraph connecting this domain to others>"
    }
  },
  "roadmap_rationale": {
    "Stabilize": "<2-3 sentences>",
    "Optimize": "<2-3 sentences>",
    "Scale": "<2-3 sentences>"
  },
  "future_state_table_rows": [
    {
      "metric": "<metric name>",
      "current_state": "<current value or description>",
      "benchmark": "<industry benchmark or stated target>",
      "target": "<target post-roadmap>",
      "sourced_from": "<CONFIRMED or INFERRED>"
    }
  ],
  "priority_zero_table_rows": [
    {
      "action": "<the priority zero action>",
      "owner": "<role from engagement data>",
      "what_it_unblocks": "<one clause — what cannot proceed until this is done>"
    }
  ],
  "roadmap_overview_rows": [
    {
      "phase": "<Stabilize, Optimize, or Scale>",
      "timeline": "<e.g. Months 1-3>",
      "key_outcomes": ["<outcome 1>", "<outcome 2>", "<outcome 3>"]
    }
  ],
  "initiative_details": [
    {
      "item_id": "<roadmap item_id from input>",
      "timeline": "<relative timing — e.g. Month 1, Months 3-6>",
      "success_metric": "<one measurable statement of done>"
    }
  ],
  "dependency_table_rows": [
    {
      "initiative": "<initiative name>",
      "depends_on": "<initiative name(s) it requires>"
    }
  ],
  "risk_table_rows": [
    {
      "risk": "<risk statement>",
      "likelihood": "<High, Medium, or Low>",
      "mitigation": "<one sentence>"
    }
  ],
  "next_steps_rows": [
    {
      "action": "<specific action>",
      "owner": "<role from engagement data>",
      "completion_criteria": "<one clause — what done looks like>"
    }
  ]
}

---

SECTION INSTRUCTIONS:

executive_summary — 4-5 paragraphs:
  P1 — Strategic situation: Lead with the core problem, use specific numbers from findings,
       state the business consequence. No hedging.
  P2 — Client hypothesis vs diagnostic reality: What did the client believe? What does the
       diagnostic show instead? Name the gap.
  P3 — Economic stakes: Total exposure with CONFIRMED/INFERRED labels. What inaction costs.
  P4 — Priority Zero items and sequencing: Name the must-do-first items. Why the sequence matters.
  P5 — What successful execution achieves: Specific measurable outcomes. Not generic language.

root_cause_narrative — 4-5 paragraphs tracing the causal chain across findings.
  Do not list finding titles. Show how one dysfunction enables the next. Answer: why is this
  firm in this situation and why has it persisted? Name structural factors, not individual failures.

economic_impact_narrative — 3-4 sentences.
  Lead with total exposure range (CONFIRMED + INFERRED labeled separately).
  Connect to business stakes: reinvestment capacity, talent retention, competitive position.
  Do not repeat individual finding economic_impact fields verbatim — synthesize them.

future_state_narrative — 2-3 sentences.
  Describe what the firm looks like operationally when the full roadmap is executed.
  Be specific to this engagement — not generic consulting language.

domain_analysis — one entry per domain that has findings.
  Use the exact domain name as the key (e.g. "Delivery Operations", "Sales & Pipeline").
  opening: 2-3 sentences introducing what the diagnostic found and why it matters.
  closing: 2-3 sentences connecting this domain's findings to findings in other domains.

roadmap_rationale — one entry per phase that has items.
  Stabilize: why these items are sequenced first — what active damage stops, what gets unblocked.
  Optimize: what foundation Stabilize created, what becomes possible now.
  Scale: what the payoff looks like — what the firm can do when Scale work is complete.

future_state_table_rows — metrics table for Section 7.
  Only include rows where both current_state and target can be sourced from the Synthesizer
  output, findings, or confirmed signals. Do not fabricate values.
  If the current value is confirmed but the target is not stated by the client, use the
  industry benchmark as the target and set sourced_from to INFERRED.
  If neither current nor target is confirmed, omit the row entirely.
  Typical metrics (include only if data is available): Billable Utilization, Gross Margin,
  On-Time Delivery Rate, EBITDA, CEO Time on Delivery Issues, Pipeline Generation Method.

priority_zero_table_rows — one row per Priority Zero item from the Synthesizer.
  action: the specific Priority Zero item.
  owner: derive from roles named in the Synthesizer output and engagement data only.
         Use "TBD — assign at kickoff" if role is ambiguous or not confirmed.
  what_it_unblocks: one clause explaining what cannot proceed until this is done.

roadmap_overview_rows — exactly three rows (Stabilize, Optimize, Scale).
  timeline: derive from phase (Stabilize = Months 1-3, Optimize = Months 3-9, Scale = Months 9-18).
  key_outcomes: 3-4 bullet strings describing what the phase achieves — written from the roadmap items.

initiative_details — one entry per roadmap item in the input.
  item_id: use the exact item_id from the roadmap input.
  timeline: derive from phase and effort:
    Stabilize + Low → Month 1
    Stabilize + Medium → Months 1-2
    Stabilize + High → Months 1-3
    Optimize + Low → Month 3
    Optimize + Medium → Months 3-6
    Optimize + High → Months 4-9
    Scale + Low → Month 9
    Scale + Medium → Months 9-12
    Scale + High → Months 9-18
  success_metric: one measurable statement of what done looks like for this specific initiative.
    Good example: "100% of new SOWs reviewed and signed by Director of Delivery before execution begins"
    Bad example: "Improved delivery process" (not measurable)

dependency_table_rows — Optimize and Scale items that are blocked by earlier items.
  Only include dependencies that are evident from the Synthesizer's sequencing rationale.
  Do not fabricate dependencies. If none are clear from the data, return an empty array.

risk_table_rows — maximum 3 rows.
  Only include risks explicitly identified in the Synthesizer's Unresolved Dependencies or
  flagged uncertainties section. Do not generate generic consulting risks not surfaced in
  this engagement's diagnostic. If fewer than 3 are confirmed, return fewer than 3 rows.
  likelihood: High if the Synthesizer flagged it as a primary dependency, Medium or Low otherwise.

next_steps_rows — maximum 10 rows.
  Populate from Priority Zero items first, then the first 3-5 Stabilize initiatives.
  action: specific and concrete — what exactly must happen.
  owner: same derivation rules as priority_zero_table_rows.
  completion_criteria: one clause — what done looks like. No specific calendar dates.

---

HALLUCINATION PREVENTION — apply to every field:
1. Every dollar figure carries CONFIRMED or INFERRED exactly as in the source. Never strip these labels.
2. Owners must be roles named in the Synthesizer output or engagement context. Never invent roles.
3. No specific dates — use relative timing only (Month 1, Months 3-6, etc.).
4. future_state_table_rows: omit any row where current or target cannot be sourced from the data.
5. risk_table_rows: only risks explicitly named in the Synthesizer. No generic risks.
6. Empty is better than fabricated. A missing cell is honest. A fabricated cell damages credibility.

---

WRITING RULES:
1. Write as a senior consultant. Direct, confident, grounded in evidence. Not corporate filler.
2. Lead with the most important insight. Not with background or context-setting.
3. Use specific numbers, names, and references from the Synthesizer. Do not generalize where specifics exist.
4. Every dollar figure carries CONFIRMED or INFERRED notation exactly as in the source.
5. Do not repeat the same content across sections. Each section adds something new.
6. State conclusions where evidence supports them. Use "the evidence suggests" only where
   the Skeptic's challenges remain unresolved.
7. Tone: direct, evidence-grounded, written for a CEO who is short on time and skeptical of consultants.
8. Banned phrases: "going forward", "leverage", "synergies", "best practices", "it is important
   to note", "it should be noted", "holistic approach", "at the end of the day".
9. No meta-commentary about the report itself.
10. Return only the JSON object — no preamble, no sign-off, no explanation."""


def _parse_narrator_json(raw: str) -> dict:
    """Parse the narrator's JSON response into a dict.

    Strips code fences if Claude wraps the output despite instructions.
    Extracts the outermost JSON object if Claude prepends/appends prose.
    Returns an empty dict on parse failure — caller falls back to placeholders.
    """
    import json as _json
    clean = raw.strip()
    # Strip code fences
    if clean.startswith('```json'):
        clean = clean[7:]
    elif clean.startswith('```'):
        clean = clean[3:]
    if clean.endswith('```'):
        clean = clean[:-3]
    clean = clean.strip()
    # Extract outermost JSON object if Claude added prose around it
    start = clean.find('{')
    end   = clean.rfind('}')
    if start != -1 and end != -1 and end > start:
        clean = clean[start:end + 1]
    try:
        return _json.loads(clean)
    except _json.JSONDecodeError as exc:
        logger.error(f"Narrator JSON parse failed: {exc} — raw excerpt: {raw[:300]}")
        return {}


async def generate_report_narrative(
    synthesizer_output: str,
    findings: list,
    roadmap: list,
    engagement: dict,
) -> dict:
    """Generate narrative prose and structured table content for the OPD report.

    Calls Claude with the full diagnostic context and returns a dict matching
    the narrator JSON schema. Returns an empty dict on failure — caller falls
    back to placeholders.

    Uses a higher token ceiling than other Claude calls because the narrator
    produces both prose sections and multiple structured table arrays.
    """
    # Narrator produces significantly more output than other calls (prose + structured
    # table arrays). Double the standard budget; respect the env var if set higher.
    NARRATOR_MAX_TOKENS = max(MAX_TOKENS * 2, 16000)

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

    # --- Assemble roadmap summary — include item_id, effort, and owner so the
    #     narrator can key initiative_details by item_id and use confirmed owners ---
    roadmap_lines = ["ROADMAP ITEMS BY PHASE:\n"]
    for phase in ['Stabilize', 'Optimize', 'Scale']:
        items = [r for r in roadmap if r.get('phase') == phase]
        if items:
            roadmap_lines.append(f"{phase}:")
            for item in items:
                roadmap_lines.append(
                    f"  - [{item.get('item_id', '')}] {item.get('initiative_name', '')} | "
                    f"Domain: {item.get('domain', '')} | "
                    f"Priority: {item.get('priority', '')} | "
                    f"Effort: {item.get('effort', '')} | "
                    f"Owner: {item.get('owner') or 'TBD'} | "
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
        f"{len(findings)} findings, {len(roadmap)} roadmap items, "
        f"max_tokens={NARRATOR_MAX_TOKENS}"
    )

    message = await async_client.messages.create(
        model=MODEL,
        max_tokens=NARRATOR_MAX_TOKENS,
        system=REPORT_NARRATOR_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = extract_text(message)
    logger.info(f"Narrator response received — {len(raw)} chars")

    sections = _parse_narrator_json(raw)
    logger.info(f"Narrator sections parsed — keys: {list(sections.keys())}")
    return sections


async def extract_roadmap_from_synthesizer(
    synthesizer_output: str,
    findings: list,
) -> str:
    """Extract structured roadmap candidates from an accepted Synthesizer output.
    Findings are provided as context so initiative names align with the diagnostic.
    Returns raw JSON string — fence stripping and array extraction handled inside."""
    findings_lines = ["ACCEPTED FINDINGS (for context — use to inform initiative naming and phase assignment):\n"]
    for f in findings:
        findings_lines.append(
            f"- [{f.get('finding_id', '')}] {f['finding_title']} | "
            f"Domain: {f.get('domain', '')} | "
            f"Priority: {f.get('priority', '')} | "
            f"Root Cause: {f.get('root_cause', '')}"
        )

    user_message = (
        f"SYNTHESIZER OUTPUT:\n\n{synthesizer_output}\n\n"
        f"---\n\n"
        f"{chr(10).join(findings_lines)}"
    )

    logger.info(
        f"Extracting roadmap from synthesizer — {len(synthesizer_output)} chars, "
        f"{len(findings)} findings"
    )
    message = await async_client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=ROADMAP_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": user_message}],
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
    start = clean.find('[')
    end   = clean.rfind(']')
    if start != -1 and end != -1 and end > start:
        clean = clean[start:end + 1]
    logger.info(f"Roadmap extraction complete — {len(clean)} chars")
    return clean
