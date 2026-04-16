import os
import asyncio
import logging
import anthropic

from api.utils.domains import VALID_DOMAINS

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
async_client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), timeout=120.0, max_retries=0)

from config import MODEL, MAX_TOKENS

_DOMAIN_LIST = ', '.join(f'"{d}"' for d in sorted(VALID_DOMAINS))


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
   Mark every figure as CONFIRMED (from document evidence), DERIVED (arithmetic result of
   confirmed inputs — the computed value was never stated in any source), or INFERRED
   (calculated estimate with at least one non-confirmed input).
   Do not present inferred or derived figures as confirmed facts.
2. Margin Decomposition — break down where margin is being lost
3. Utilization Analysis — assess billable utilization against industry benchmarks
4. Economic Impact by Pattern — quantify the cost of each accepted pattern where possible.
   Use ranges not point estimates. Mark all figures CONFIRMED, DERIVED, or INFERRED.
5. ROI Case — build the business case for transformation investment
6. Interdependency Table — show how economic factors interact

Domains in scope: Sales & Pipeline, Sales-to-Delivery Transition, Delivery Operations,
Resource Management, Project Governance / PMO, Consulting Economics, Customer Experience,
AI Readiness, Human Resources, Finance and Commercial.

CRITICAL: Every dollar figure must be marked CONFIRMED, DERIVED, or INFERRED. The CFO will
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
6. Contradiction Report — a discrete pass over all signals in the case packet to surface
   cross-document conflicts, retractions, role discrepancies, and second-hand attributions.
   This section is separate from plausibility review. Produce it even if you found no issues
   in sections 1–5.

   FOUR TYPES TO DETECT:

   factual_conflict — two signals from different source documents make conflicting factual
   claims about the same entity (person, project, date, number, metric, or event).
   Precedence rules:
   - Interview vs. interview: flag both; note which is more recent.
   - Interview vs. document: interview takes precedence UNLESS the conflict involves a
     contractual term, a dated financial figure from prepared financials, or a formal
     operational record (SOW or status report authoritative as of its stated date). In
     those narrow cases, the document governs for the period it covers — flag the conflict
     for the consultant rather than resolving it silently.
   - Document vs. document: the more recent document takes precedence for current-state
     facts; flag both.

   retraction — a signal from a later interview contradicts or walks back a claim from
   an earlier one (same or different interviewee). The later statement is operative.
   Preserve both. Note whether the retraction was explicit ("actually, it's closer to...")
   or implicit (second speaker states a different fact without acknowledging the first).

   role_discrepancy — a named person's title or role differs between two sources.
   The interviewee's own self-stated title is authoritative regardless of document date
   or how an interviewer addressed them. If no self-stated title is available, flag both
   sources and note which document is more recent.

   second_hand_attribution — a signal whose evidence is one interviewee describing what
   another named person said or did, rather than a direct account. This is not a
   contradiction but an unconfirmed claim. Flag it so the Synthesizer knows the attribution
   cannot be treated as confirmed until the named party's own transcript is checked.
   Indicators: "John told me that...", "I heard from the CEO that...", "Apparently the
   Director decided to...", any claim about a named third party's intent, statement, or
   action sourced only from a second party's account.

   FORMAT — produce one entry per detected issue in this exact format:

   [C001]
   Type: factual_conflict
   Entity: <the person, project, metric, date, or event being described>
   Signal A: [S_ID] | Source: <file name> | Claim: "<exact value or quote>"
   Signal B: [S_ID] | Source: <file name> | Claim: "<exact value or quote>"
   Operative Fact: <which claim is authoritative and the specific reason — cite the
     applicable precedence rule. For document-wins cases, name the basis (contractual
     term / prepared financial figure / formal operational record) and note the conflict
     must be surfaced to the consultant, not silently resolved.>
   Findings at Risk: <domain(s) where any finding referencing either signal must be
     verified before acceptance>

   For second_hand_attribution entries, use this variation:
   Signal A: [S_ID] | Source: <file name> | Claim: "<what the interviewee reported>"
   Signal B: [none] | Source: unverified | Claim: "<what was attributed to the named party>"
   Operative Fact: Unconfirmed — attributed claim cannot be treated as direct evidence
     until the named party's own account is available.

   If no issues are detected across all four types, output exactly:
   [NONE DETECTED]

   Do not produce narrative commentary in this section. Every detected issue must use
   the labeled-field format above. No other format is acceptable.

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

   Contradiction Report resolution — required before generating any finding:
   For each C-code in the Skeptic's Contradiction Report, address it explicitly:
   - factual_conflict: state which claim you accept as operative and confirm that any
     finding touching the contradicted signal uses that claim, not the other. For
     document-wins cases the Skeptic flagged: surface the conflict in the finding itself
     rather than resolving it silently.
   - retraction: confirm the later statement is the operative fact used in findings.
   - role_discrepancy: confirm any finding that names the individual uses the
     authoritative title (interviewee's self-stated title if available).
   - second_hand_attribution: confirm that no finding presents the attributed claim as
     confirmed evidence. Treat it as unverified context only; do not base a finding's
     confidence on it.
   If the Contradiction Report shows [NONE DETECTED], acknowledge it in one sentence
   and continue.

   Attribution verification — silent pre-finalization gate, no output section:
   Before writing any finding that references a named individual (as a source of a
   statement, owner of an action, or subject of a characterization), verify all three:
   - Title accuracy: the title used in the finding matches the person's own self-stated
     title from their interview transcript. If a role_discrepancy C-code covers this
     person, use the authoritative title established there. Correct silently.
   - Statement traceability: the statement attributed to them appears in their own
     interview transcript, not only in another interviewee's account. Cross-reference
     any second_hand_attribution C-codes. If the attribution traces only to a second-hand
     account, apply the disclosure rule below — do not present it as direct evidence.
   - Second-hand disclosure: if the attribution is second-hand and cannot be resolved
     from the available transcripts, the finding must say "per [Role]'s account" to
     make the indirection visible. A second-hand attribution must not be the sole basis
     for a High-confidence finding — downgrade to Medium if no corroborating direct
     evidence exists.
   Apply all three checks before writing each finding. Do not produce a report of this
   process — correct the finding text and move on.

2. Integrated Findings — the consolidated set of findings across all domains.
   Use CONFIRMED/DERIVED/INFERRED notation on all dollar figures.
   Customer Experience standalone rule: If the case packet contains signals from a
   Customer Experience domain (NPS data, client satisfaction scores, client escalations,
   PM responsiveness scores, or survey response data), Customer Experience must be
   generated as a standalone integrated finding. It may not be dissolved into Delivery
   Operations, Project Governance, or any other domain finding even when the causal chain
   connects them. Cross-reference to the relevant delivery or governance findings is
   appropriate; consolidation is not.
   Confirmed notation rule: When writing economic impact for a finding, the
   CONFIRMED-labeled figure must be a dollar amount or omitted entirely — never a rate
   ($/hr), a percentage, or a target figure. If the only confirmed fact for a finding is
   a rate or percentage — for example, a $10/hr bill rate gap or a 5.4% margin variance —
   do not apply the CONFIRMED label. Instead, compute the dollar impact, label it DERIVED,
   and show the calculation inline. Do not apply CONFIRMED to rate card values, bill rate
   targets, or gap percentages under any circumstance.
3. Priority Zero Items — findings that must be addressed before any other work begins.
   These are blockers, not just high priorities.
4. Unresolved Dependencies — what remains uncertain and how it affects the recommendations.
5. Economic Summary — total economic impact range with CONFIRMED/DERIVED/INFERRED breakdown.

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

SIGNAL_EXTRACTION_PROMPT = f"""You are analyzing an interview transcript from a consulting firm diagnostic engagement.

Extract signals that are directly supported by evidence in the transcript. A signal is a specific, observable indicator of operational health or dysfunction.

Extract between 5 and 10 found signals per transcript. If you identify more than 10, keep only
the 10 most operationally significant. Only include signals where the evidence is clear
and specific. Do not extract speculative signals to reach a minimum count.
Do not over-extract weak inferences from thin evidence.

Each item in "found" must have exactly these fields:
- signal_name: string — a concise name for the signal (e.g. "Projects on schedule")
- domain: string — must be exactly one of: {_DOMAIN_LIST}
- observed_value: string — what was observed (e.g. "57%", "Low", "Increasing")
- normalized_band: string — context for the observed value (e.g. "Below 80% target", "No standard process exists")
- evidence_quality: string — COMPLETE THIS BEFORE assigning signal_confidence. Scan the full transcript for any other references to this same topic and list any of the following you find: [unclear] or [inaudible] markers in relevant passages; hedging language used by the interviewee ("I think", "roughly", "around", "probably", "I believe", "I'm not sure"); any statement elsewhere in the transcript that contradicts this one or gives a different figure; the interviewee expressing doubt, admitting an error, or failing to resolve an either/or question; the signal being an inference you drew rather than something the interviewee stated directly. Write "None" only if none of these exist for this topic anywhere in the transcript.
- signal_confidence: string — derived from evidence_quality:
    - Hypothesis: if evidence_quality contains anything other than "None"
    - Medium: if evidence_quality is "None" AND the signal is qualitative with no specific number or verifiable fact
    - High: if evidence_quality is "None" AND a specific number or verifiable fact was stated directly with no hedging
- source: string — always "Interview"
- economic_relevance: string — one short phrase (e.g. "Delivery margin", "Revenue stability") or empty string
- notes: string — include the VERBATIM quote from the transcript that supports this signal, followed by your brief interpretation. Format: "Quote: '[exact words]' — Interpretation: [your note]"
- library_signal_id: string — ONLY include when this signal matches an entry from the SIGNAL LIBRARY block. Use the exact signal_id (e.g. "SL-17"). Omit for freely-extracted signals.

Only extract signals with direct transcript evidence. Do not invent signals.

SIGNAL LIBRARY:
The user message includes a SIGNAL LIBRARY block listing Tier 1 signals to check against this transcript.
- For each listed signal where you find evidence: include it in "found" with all required fields plus "library_signal_id": "<SL-XX>"
- For each listed signal you actively checked but found no evidence for: add its signal_id to "not_observed"
- You may include freely-extracted signals not in the library in "found" — omit library_signal_id for these
- Report not_observed ONLY for signals that appear in the SIGNAL LIBRARY block above

CRITICAL OUTPUT FORMAT:
Your response must be a JSON object beginning with {{ and ending with }}
Do not include any text, explanation, or markdown before or after the JSON object
Do not use code fences or backticks of any kind
Your response must follow this structure exactly:
{{"found": [...signal objects...], "not_observed": ["SL-XX", ...]}}

Return format example:
{{
  "found": [
    {{
      "signal_name": "Projects on schedule",
      "domain": "Delivery Operations",
      "observed_value": "57%",
      "normalized_band": "Below 80% target",
      "evidence_quality": "None",
      "signal_confidence": "High",
      "source": "Interview",
      "economic_relevance": "Delivery margin",
      "notes": "Quote: 'eight of our fourteen active projects are on track, the rest are in some kind of trouble' — Interpretation: 57% on-schedule rate confirmed directly by CEO.",
      "library_signal_id": "SL-18"
    }}
  ],
  "not_observed": ["SL-17", "SL-23"]
}}"""

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
        timeout=300.0,
    )
    response = extract_text(message)
    logger.info(f"Claude API response received — {len(response)} chars")
    return response


async def extract_signals_from_transcript(transcript: str, library_block: str = '') -> str:
    """Extract signal candidates from an interview transcript.
    library_block is a pre-built SIGNAL LIBRARY section injected after the transcript.
    Returns raw JSON string — fence stripping handled by caller."""
    logger.info(f"Extracting signals from transcript — {len(transcript)} chars")
    user_content = f"INTERVIEW TRANSCRIPT:\n\n{transcript}"
    if library_block:
        user_content += f"\n\n---\n\n{library_block}"
    message = await async_client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SIGNAL_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        timeout=300.0,
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
  "$[figure] ([CONFIRMED, DERIVED, or INFERRED]: [calculation] — [source of each input])"

- CONFIRMED = figure appears explicitly in a source document (financial statement, contract, invoice, etc.)
- DERIVED = figure is the arithmetic result of two or more CONFIRMED inputs; the computed value was never stated in any source document. Use this when you multiply or divide confirmed figures to produce a new number (e.g. confirmed bill rate gap × confirmed billable hours → rate leakage dollar amount; confirmed margin % endpoints → EBITDA erosion figure).
- INFERRED = figure is a calculated estimate where at least one input comes from an interview statement, observed pattern, or industry benchmark rather than a document
- Calculation: show the multiplication or formula used (e.g. "14 projects × 30% overrun rate × $67K avg value")
- Source: for each input, state where it came from — "from CEO interview", "from pipeline document", "industry benchmark for mid-size consulting firms"
- Use ranges not point estimates when inputs are estimated

CLASSIFICATION RULE: If every input to a calculation is CONFIRMED, the result is DERIVED — not CONFIRMED (the result was never stated in a document) and not INFERRED (no estimates were used). If any input is estimated, benchmarked, or sourced only from an interview, the result is INFERRED.

Each item must have exactly these fields:
- finding_title: string — concise title (e.g. "Chronic Project Overruns")
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- confidence: string — exactly "High", "Medium", or "Low"
- operational_impact: string — 1-3 sentences describing the operational consequence
- economic_impact: string — quantified where possible, with inline reasoning as described above. If genuinely unquantifiable, state why in one sentence.
- root_cause: string — one sentence root cause statement
- recommendation: string — one sentence actionable recommendation
- priority: string — derived from these criteria, apply in order, first match wins:
    - High: finding addresses active margin bleed or financial loss occurring now, OR is a structural blocker that prevents other improvements from working, OR has CONFIRMED or DERIVED economic impact (confirmed-input calculation)
    - Medium: finding improves operational performance but does not stop active damage, OR has INFERRED economic impact based on estimates or benchmarks, OR is supported primarily by qualitative evidence without a specific dollar figure
    - Low: finding improves quality, capability, or process maturity with no direct economic impact, or is a longer-horizon improvement that requires Stabilize and Optimize work to be complete first
- effort: string — exactly "High", "Medium", or "Low" (implementation effort to address this finding)
- opd_section: integer — OPD report section this finding is most relevant to (1-9):
  1 = Executive Summary, 2 = Engagement Overview, 3 = Operational Maturity Overview,
  4 = Domain Analysis, 5 = Root Cause Analysis, 6 = Economic Impact Analysis,
  7 = Future State, 8 = Transformation Roadmap, 9 = What Happens Next.
  Most findings belong in section 4 or 5.
- suggested_pattern_ids: list of strings — pattern IDs from the ACCEPTED PATTERNS list that directly support this finding (e.g. ["P12", "P15"]). Only include IDs that appear in the accepted patterns list provided. Do not invent pattern IDs.
- key_quotes: list of 2–3 strings — verbatim quotes selected from the DOMAIN SIGNALS provided for this finding's domain. Each quote must appear word-for-word in the signal notes provided. Do not paraphrase, summarise, or fabricate quotes. If fewer than 2 quotes are available for the domain, include what exists. If no signal notes are provided for the domain, return an empty list.

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
    "priority": "Medium",
    "effort": "Medium",
    "opd_section": 4,
    "suggested_pattern_ids": ["P12", "P15"],
    "key_quotes": [
      "We sign the SOW and then tell delivery what we sold them — by then it's too late to push back.",
      "I've never once seen a delivery lead in the room during a proposal."
    ]
  }
]"""


async def extract_findings_from_synthesizer(synthesizer_output: str,
                                            accepted_patterns: list,
                                            signals_by_domain: dict | None = None) -> str:
    """Extract structured findings from an accepted Synthesizer output.
    signals_by_domain: {domain: [notes strings]} — used for key quote selection.
    Returns raw JSON string — fence stripping handled inside this function."""
    pattern_lines = [
        f"- {p['pattern_id']}: {p['pattern_name']} ({p['domain']}, confidence: {p.get('confidence', 'Unknown')})"
        for p in accepted_patterns
    ]
    pattern_summary = "\n".join(pattern_lines) if pattern_lines else "(none)"

    # Build domain signals block for key quote selection
    if signals_by_domain:
        domain_blocks = []
        for domain, notes_list in signals_by_domain.items():
            if notes_list:
                notes_text = "\n".join(f"  - {n}" for n in notes_list)
                domain_blocks.append(f"{domain}:\n{notes_text}")
        signals_section = (
            "---\n\n"
            "DOMAIN SIGNALS (select key_quotes verbatim from these notes only):\n\n"
            + "\n\n".join(domain_blocks)
        ) if domain_blocks else ""
    else:
        signals_section = ""

    user_message = (
        f"SYNTHESIZER OUTPUT:\n\n{synthesizer_output}\n\n"
        f"---\n\n"
        f"ACCEPTED PATTERNS (use only these IDs in suggested_pattern_ids):\n\n{pattern_summary}\n\n"
        + (signals_section if signals_section else "")
    )
    logger.info(
        f"Extracting findings from synthesizer — {len(synthesizer_output)} chars, "
        f"{len(accepted_patterns)} accepted patterns, "
        f"{sum(len(v) for v in (signals_by_domain or {}).values())} signal notes"
    )
    message = await async_client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=FINDINGS_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        timeout=300.0,
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
- capability: string — one sentence describing what the organisation will be able to do once this initiative is complete, stated as an organisational capability (e.g. "The ability to consistently scope and price engagements before delivery begins, such that every project enters delivery with a signed SOW and agreed success criteria.")
- addressing_finding_ids: list of strings — the finding_ids from ACCEPTED FINDINGS that this initiative directly addresses. Use the exact finding_id values (e.g. ["F001", "F003"]). If no accepted findings are provided or none are relevant, return an empty list [].

OWNER RULES — apply these strictly:
Only assign owners from roles explicitly named in the Synthesizer output or engagement context.
Do not invent role titles that do not appear in the diagnostic data.
NEVER use a person's name as an owner — always use the role title (e.g. "Director of Delivery",
not "Sarah Chen"). Individual consultant and PM names must never appear anywhere in the output.
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
    "owner": "CEO",
    "capability": "The ability to make and enforce delivery decisions without CEO override, such that process changes implemented in Optimize and Scale phases are not reversed at the project level.",
    "addressing_finding_ids": ["F002", "F005"]
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
  "executive_briefing": {
    "executive_snapshot": "<EXACTLY THREE SENTENCES. Sentence 1: primary diagnosis in plain language. Sentence 2: most urgent active risk with dollar figure if one is confirmed. Sentence 3: what must happen this week and who owns it. No qualifications. Readable in under 30 seconds.>",
    "problems": [
      {
        "finding_id": "<exact finding_id from ACCEPTED FINDINGS — e.g. F001>",
        "plain_title": "<5 words maximum — the business problem in plain English a CEO would recognize. NOT a diagnostic label. Bad: 'Delivery Margin Compression Pattern'. Good: 'Projects consistently run over budget'.>",
        "impact_brief": "<20 words maximum, single sentence — what this is costing the firm right now. Be specific: name a figure, a percentage, or a named consequence.>"
      }
    ],
    "numbers": [
      {
        "finding_id": "<exact finding_id the CONFIRMED or DERIVED figure comes from — the figure will be sourced from that finding's economic_impact field, not from this object>",
        "label": "<4 words maximum — plain English label for this number. Bad: 'Economic Impact from F003'. Good: 'Annual delivery overrun cost'.>"
      }
    ]
  },
  "executive_summary_opening": "<3-4 sentences. Single most important finding, written for a CEO who reads nothing else. Lead with the headline — not background. No CONFIRMED/DERIVED/INFERRED labels.>",
  "executive_summary_para1": "<2-3 sentences. Client hypothesis vs diagnostic reality. Direct. No CONFIRMED/DERIVED/INFERRED labels. End with exactly the text labeled 'domain_analysis_ref' from the SECTION REFERENCES block.>",
  "executive_summary_para2": "<2-3 sentences. Economic stakes in plain language. 2-3 key figures maximum. No CONFIRMED/DERIVED/INFERRED labels. End with exactly the text labeled 'economic_impact_ref' from the SECTION REFERENCES block.>",
  "executive_summary_para3": "<2-3 sentences. Why sequencing matters — what must happen first and why the order is not optional. No labels. End with exactly the text labeled 'priority_zero_ref' from the SECTION REFERENCES block.>",
  "margin_trend_brief": "<one line — current gross margin % to prior gross margin % over X years with direction, e.g. '42% → 35% over 3 years (declining)'. Derive from Consulting Economics finding or Synthesizer output. Return null if not determinable from the data.>",
  "engagement_overview_paragraph": "<4-6 sentences. Who was interviewed by role. What documents were reviewed by type. Engagement objective. Signal count. Derive roles and document types only from the PROCESSED FILES list — do not fabricate.>",
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
      "benchmark": "<prior period confirmed value from engagement data if available; industry benchmark only if no prior period data exists>",
      "target": "<target post-roadmap>",
      "sourced_from": "<CONFIRMED, DERIVED, or INFERRED>"
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
  ],
  "execution_path_recommendation": "<internal | guided | partner — one of these three values only>",
  "execution_path_rationale": "<one sentence — why this specific firm needs this execution path. Ground in firm size, presence or absence of a dedicated operations function, and confirmed leadership bandwidth signals from this engagement. No generic consulting language. Do not use CONFIRMED/DERIVED/INFERRED labels.>"
}

---

SECTION INSTRUCTIONS:

executive_briefing — structured object for the one-page CEO teaser:
  This page is shown to a CEO before they decide whether to pay for the full report.
  Every field must be specific to this engagement. Generic language is a failure here.

  executive_snapshot: exactly three sentences. The Executive Snapshot opens the Executive
    Briefing page. It is the first thing a reader sees. Sentence 1: primary diagnosis in
    plain language. Sentence 2: most urgent active risk with a dollar figure if one is
    confirmed. Sentence 3: what must happen this week and who owns it. No headers, no
    sub-bullets, no qualifications. Readable in under 30 seconds.
    Do not use CONFIRMED, DERIVED, or INFERRED labels anywhere in this field. State
    figures directly without qualification labels.
    PROSE STYLE: Write in short declarative sentences. Each sentence expresses exactly one
    idea. No sentence should exceed 20 words. Do not embed the key insight inside a
    subordinate clause — pull it out as its own sentence. The reader must feel the weight
    of the problem after reading the snapshot, not need to parse compound logic to find it.
    Wrong: "Northstar's margin problem is not a PM execution problem — it is a pricing and
    governance problem: gross margin has compressed from 40% to 31% over four years because
    the CEO retains unilateral authority over pricing, SOW execution, and change order
    acceptance with no governance gates, and that authority has been used in ways that lock
    in losses before delivery begins."
    Right: "Northstar's margin problem is not a PM execution problem. It is a pricing and
    governance problem. Gross margin has fallen from 40% to 31% in four years. The cause
    is not delivery failure — it is a decision structure that locks in losses before
    delivery begins."

  problems: exactly 3 entries (or fewer if fewer than 3 findings exist).
    finding_id: must be an ID that appears in the ACCEPTED FINDINGS list — e.g. F001.
      Do not invent finding IDs.
    plain_title: 5 words maximum. Must follow ACTIVE VOICE — a subject doing something
      to the business. The subject must be identifiable. The verb must be active.
      Wrong (no subject, passive): "Bill rates eroding every year"
      Wrong (diagnostic label): "Delivery Margin Compression Pattern"
      Right: "Discounting is bleeding margin annually" (subject + active verb + consequence)
      Right: "Growth is destroying profitability" (subject + active verb + consequence)
      All three plain_title values must follow this active-voice pattern consistently.
      ACCURACY RULE: Plain titles must be accurate to the finding even when compressed.
      Do not use words that introduce meanings not present in the source finding. Brevity
      is secondary to accuracy — a slightly longer title that is correct is preferable to
      a punchy title that misrepresents the finding. Specific example of what to avoid:
      do not use the word "unsigned" to describe a SOW that was executed without delivery
      review — these are different conditions. The SOW was signed; the problem is that
      delivery did not review it before signature. Match the compression to the actual
      condition, not the most dramatic interpretation of it.
      NON-ACCUSATORY RULE: Plain titles must describe structural conditions, not personal
      failures. Do not use emotionally charged words (killing, destroying, sabotaging,
      undermining) when describing leadership behavior. Do not name the CEO or any
      individual in a problem title — describe the process or structural condition instead.
      Wrong: "CEO overrides are killing change orders"
      Right: "Change control is bypassed at the leadership level"
    impact_brief: 20 words maximum, single sentence. What is this costing the firm today?
      Name a figure, percentage, or specific named consequence. Do not generalize.
      Do not use CONFIRMED, DERIVED, or INFERRED labels. State figures directly.
    Select the 3 most important findings — High priority first.

  numbers: exactly 3 entries (or fewer if fewer than 3 confirmed or derived figures exist).
    Only CONFIRMED or DERIVED figures may appear here — never INFERRED.
    Order by urgency: (1) most immediate at-risk figure, (2) most structural annual drag,
    (3) most existential risk. The ordering conveys the story — immediate → chronic → fatal.
    finding_id: the finding the confirmed figure comes from. Must be a real finding ID.
    label: 6 words maximum. Plain English — what does this number represent?
      No calculation formulas. No source citations. No CONFIRMED/DERIVED/INFERRED labels.
      Bad: "Calculated from: 52,571 implied billable hours × $10/hr gap"
      Bad: "Economic Impact from F003"
      Good: "Annual rate gap cost"
      Good: "Annual delivery overrun cost"

executive_summary_opening — 3-4 sentences:
  The single most important finding this engagement produced. Written for a CEO who reads
  nothing else. Lead with the headline — not background, not context-setting.
  If the finding has a dollar figure, use it. Do not label it CONFIRMED, DERIVED, or INFERRED
  here — those labels belong in Sections 4, 6, and all tables, not in Executive Summary prose.

executive_summary_para1 — 2-3 sentences:
  Client hypothesis vs diagnostic reality. What did the client believe was causing the
  problem? What does the diagnostic show instead? Name the gap directly. No labels.
  Close the paragraph with exactly the text labeled 'domain_analysis_ref' from the SECTION
  REFERENCES block in the input. Copy it verbatim — do not alter the section number or wording.

executive_summary_para2 — 2-3 sentences:
  Economic stakes in plain language. Include 2-3 key figures maximum. Do not use
  CONFIRMED/DERIVED/INFERRED labels here — those appear in the Economic Impact section. State
  what is at stake and what inaction costs.
  Close the paragraph with exactly the text labeled 'economic_impact_ref' from the SECTION
  REFERENCES block in the input. Copy it verbatim — do not alter the section number or wording.

executive_summary_para3 — 2-3 sentences:
  Why sequencing matters. What must happen first and why the order is not optional.
  Focus on the Priority Zero items — not a summary of the full roadmap.
  Close the paragraph with exactly the text labeled 'priority_zero_ref' from the SECTION
  REFERENCES block in the input. Copy it verbatim — do not alter the section number or wording.

margin_trend_brief — one line or null:
  Derive from the Consulting Economics finding's economic_impact field or from the
  Synthesizer output's Economic Summary section. Format as: "42% → 35% over 3 years
  (declining)" or "flat at ~38% for 2 years". Return null if no margin trend data is
  present in the Synthesizer output or findings.

engagement_overview_paragraph — 4-6 sentences:
  Sentence 1: Who was interviewed — roles only, not names. Derive exclusively from the
    PROCESSED FILES list provided in the input — do not include any role not present.
  Sentences 2-3: What documents were reviewed — types only, not filenames. Derive
    exclusively from the PROCESSED FILES list.
  Sentence 4: Engagement objective using the stated problem from engagement context.
  Sentence 5: Total signal count across all domains — use the exact count from context.
  CRITICAL: Do not invent sources, roles, or document types absent from the file list.
  A missing sentence is better than a fabricated one.

root_cause_narrative — 4-5 paragraphs tracing the causal chain across findings.
  Do not list finding titles. Show how one dysfunction enables the next. Answer: why is this
  firm in this situation and why has it persisted? Name structural factors, not individual failures.

economic_impact_narrative — 3-4 sentences.
  Lead with total exposure range (CONFIRMED + DERIVED + INFERRED labeled separately).
  Connect to business stakes: reinvestment capacity, talent retention, competitive position.
  Do not repeat individual finding economic_impact fields verbatim — synthesize them.

future_state_narrative — 2-3 sentences plus one required CEO day sentence.
  Describe what the firm looks like operationally when the full roadmap is executed.
  Be specific to this engagement — not generic consulting language.
  REQUIRED: Include exactly one sentence that describes what the CEO's day looks like
  operationally 18 months from now — specifically what they are no longer doing that
  they are doing today. This sentence must be grounded in confirmed signals about current
  CEO time consumption. It must name the CEO's actual role burdens from the diagnostic data.
  Wrong (generic): "The CEO focuses on strategic priorities rather than operational issues."
  Right (specific, grounded in signals): "David Park's Tuesday is spent on new client
  relationships and market positioning — not on escalation calls from a CTO whose project
  went past deadline, staffing decisions that require his personal approval, or scope disputes
  that have bypassed the Director of Delivery."
  The CEO name and specific operational burdens must come from confirmed signals in the
  engagement data. Do not invent details not present in the diagnostic. If no CEO time
  consumption signals are confirmed, omit this sentence rather than fabricate it.

domain_analysis — one entry per domain that has findings.
  Use the exact domain name as the key (e.g. "Delivery Operations", "Sales & Pipeline").
  opening: 2-3 sentences introducing what the diagnostic found and why it matters.
  closing: 2-3 sentences connecting this domain's findings to findings in other domains.

roadmap_rationale — one entry per phase that has items.
  Stabilize: why these items are sequenced first — what active damage stops, what gets unblocked.
    Include 1–2 sentences on the economic stakes of this phase if any Stabilize items have
    "Addresses economic impact" data in the ROADMAP ITEMS input — synthesize the exposure being
    stopped or protected, using CONFIRMED/DERIVED/INFERRED notation. Omit if no economic data.
  Optimize: what foundation Stabilize created, what becomes possible now.
    Include 1–2 sentences on economic stakes if relevant Optimize items have economic linkage data.
  Scale: what the payoff looks like — what the firm can do when Scale work is complete.
    Include 1–2 sentences on economic stakes if relevant Scale items have economic linkage data.

future_state_table_rows — metrics table for Section 7.
  Only include rows where both current_state and target can be sourced from the Synthesizer
  output, findings, or confirmed signals. Do not fabricate values.
  If the current value is confirmed but the target is not stated by the client, use the
  industry benchmark as the target and set sourced_from to INFERRED.
  If neither current nor target is confirmed, omit the row entirely.
  Typical metrics (include only if data is available): Billable Utilization, Gross Margin,
  On-Time Delivery Rate, EBITDA, CEO Time on Delivery Issues, Pipeline Generation Method.
  For the benchmark column, prefer a prior period confirmed value from the engagement data
  over an estimated industry average — it is more credible and more motivating for the client.
  Use an industry benchmark only when no prior period confirmed value exists.

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

risk_table_rows — between 3 and 6 rows. Do not cap at 3. Include all risks that are
  directly evidenced by the diagnostic data.
  For each risk, consider all four categories:
    1. Adoption risks — will the named owner actually change behavior?
    2. Capacity risks — does the named owner have bandwidth to execute alongside current duties?
    3. Evidence gap risks — what confirmed uncertainty could change the intervention design
       if resolved differently?
    4. Organizational dynamics risks — what people or trust issues could slow execution?
  Every risk must be grounded in a specific signal, finding, or Skeptic-flagged uncertainty
  from this engagement. Do not generate generic transformation risks (change management
  resistance, budget overruns) that are not specifically evidenced in the diagnostic data.
  Do not name individual ICs in risk descriptions — use role references only.
  likelihood: High if the Synthesizer flagged it as a primary dependency; Medium or Low otherwise.

next_steps_rows — maximum 10 rows.
  Populate from Priority Zero items first, then the first 3-5 Stabilize initiatives.
  action: specific and concrete — what exactly must happen.
  owner: same derivation rules as priority_zero_table_rows.
  completion_criteria: Write as if handing a work order to the person who owns it. They
    should be able to read their row and know exactly what done looks like without asking
    anyone. Use active voice. Name the owner as the subject of the sentence. Be specific
    about the deliverable — not the strategic outcome.
    WRONG: "A PM coverage plan is approved and a handoff document is completed"
    RIGHT: "[Responsible Role] has returned to full-time [their primary responsibility].
    A named [role] is covering [Project Name] with a written handoff plan signed by both parties."
    Remove all strategic framing: no "positions the firm to", no "enables future" language.
    Just what done looks like. No specific calendar dates. Use role titles from the engagement
    data only — never invent names or project names not present in the input.

execution_path_recommendation — one of three values: "internal", "guided", or "partner".
  Select based on firm size and capacity signals from this engagement:
  "internal": firm has a dedicated operations or transformation function; leadership
    bandwidth is confirmed available for ownership of Stabilize initiatives.
  "guided": firm lacks a dedicated transformation function; leadership is stretched or
    capacity signals show over-allocation; or firm is under 75 people without a
    named transformation owner. This is the correct choice for most engagements.
  "partner": firm lacks both internal transformation capacity AND sufficient leadership
    bandwidth for a guided model; delivery is in active crisis or leadership is fully
    absorbed by operational firefighting.
  Default rule: firms under 75 people without a dedicated transformation function → "guided".
  When in doubt between "internal" and "guided", choose "guided".

execution_path_rationale — one sentence. Explain why this specific firm needs the
  recommended execution path. Ground in firm size, presence or absence of a dedicated
  operations function, and confirmed leadership bandwidth signals from the engagement.
  This sentence will appear bold in the client report — write it as a direct statement
  to the reader, not as a meta-description.
  Wrong: "Guided execution is recommended for most firms at this stage."
  Right: "At 45 people with no dedicated operations function and a CEO currently named
  as owner of four Stabilize initiatives, internal execution would concentrate
  implementation risk on leadership that is already over-allocated."
  Do not use CONFIRMED/DERIVED/INFERRED labels in this sentence.

---

## Roadmap Quality Rules

The following rules must be applied when generating roadmap content.
Check each rule against the engagement data before finalizing roadmap output.

CONDITIONALITY: Apply each rule only when its trigger condition is directly evidenced
in the accepted findings, Synthesizer output, or engagement context provided in the
input. Do not apply a rule based on inference when the trigger condition is not
explicitly present in the data. Content required by a rule must still be grounded
in the engagement data — do not fabricate delegation mechanisms, contingency paths,
or capacity model details that have no basis in the input.

### Sequencing Rules

Rule 1 — Revenue concentration stabilization precedes growth:
When a finding identifies a single client representing a disproportionate share of
revenue AND relationship deterioration signals are present in that finding or the
Synthesizer output (declining NPS, active escalation, no account plan, or client
communication gaps), the account stabilization initiative must be placed in Stabilize.
Only account expansion initiatives belong in Scale. Stabilization and expansion are
different actions with different urgency.

Rule 2 — Rate floor policy belongs in Stabilize, not Optimize:
When billable rate realization is below target and rate card non-enforcement is
identified as an active ongoing loss, the roadmap must include a rate floor policy
and approval workflow draft in Stabilize (not Optimize). Deal-level rate reporting
infrastructure belongs in Optimize. The policy does not require the reporting
infrastructure to exist before it can be drafted and communicated.

Rule 3 — Change order governance must be portfolio-wide from Month 1:
When change order discipline is identified as a finding, the change order governance
initiative must be portfolio-wide from Month 1 of Stabilize. Do not scope it to
specific at-risk projects — this creates two tiers of enforcement and the ungoverned
projects will absorb scope without commercial capture. Portfolio-wide enforcement
is the only effective implementation.

Rule 4 — Confirmed AI contractual liability is a Stabilize concern:
When a finding documents confirmed AI tool use on active client engagements without
an AI usage policy or SOW AI clause, the AI governance policy initiative must be
placed in Stabilize at High priority. The absence of a policy on active client
engagements is a confirmed contractual liability today, not a future risk. AI service
offering development belongs in Scale.

Rule 5 — PM attrition requires structural capacity model, not just hiring:
When PM attrition events or chronic PM over-allocation are identified in the findings
or Synthesizer output, the roadmap must include a structural PM capacity model
initiative — a pipeline-to-PM-demand forecasting model with a defined bench reserve
target — in addition to any hiring recommendation. A hiring recommendation without
a capacity model solves the immediate gap but does not prevent recurrence. The
capacity model belongs in Stabilize or early Optimize depending on the severity
of the current gap.

Rule 6 — CEO bottleneck requires structural delegation in risk register:
When a finding identifies leadership bottleneck or decision centralization AND the
CEO is assigned ownership of more than two Stabilize initiatives in the roadmap
input, the risk_table_rows entry for CEO reversion risk must include at least one
structural delegation mechanism as a mitigation — a written decision rights matrix
with defined thresholds, a fractional operating resource, or an explicit opt-out
delegation model. A tracking log or review cadence alone is not a mitigation for
a bottleneck risk rated High likelihood.

Rule 12 — Active client escalation requires contingency planning:
When a finding documents an active client escalation with confirmed financial exposure
AND the SOW lacks contractual protection (no liquidated damages clause, missing
client obligation enforcement language, or below-rate pricing with no floor), the
priority_zero_table_rows entry for that escalation must include three components:
  1. Primary path — the recommended immediate action
  2. Contingency path — what to do if the primary path fails or the client escalates
  3. Exposure boundary — the maximum confirmed financial exposure and the contractual
     basis, or explicit acknowledgment that the boundary is indeterminate without
     legal review
Do not generate a single-bullet P0 action for an active escalation with confirmed
financial exposure. A live dispute requires a primary path, a fallback, and a known
exposure boundary.

### Dependency and Timing Rules

Rule 13 — Sequential data dependencies must be explicitly sequenced:
Before finalizing initiative_details timelines within each phase, check for sequential
data dependencies: does any initiative require clean, reliable data that another
initiative in the same phase is responsible for producing?

If yes: the dependent initiative must be placed later in the phase timeline or moved
to the next phase. Show the dependency explicitly in the initiative description:
"Prerequisite: [Initiative A] must be producing reliable [data type] before this
initiative can execute. Realistic start: [month]."

Specific rule: any initiative that deploys a model, framework, or process that
calibrates against historical actuals requires that the actuals dataset exists in
usable form today, or that the infrastructure producing it is fully operational
before model deployment begins. Do not show these as concurrent.

Common patterns where this fires:
- Estimation model deployment depends on PSA or project tracking data being clean
- Pricing governance enforcement depends on deal-level rate reporting existing
- PM performance management depends on project-level margin visibility existing
- Capacity forecasting depends on utilization tracking being reliable

---

HALLUCINATION PREVENTION — apply to every field:
1. Every dollar figure carries CONFIRMED, DERIVED, or INFERRED exactly as in the source. Never strip these labels.
2. Owners must be roles named in the Synthesizer output or engagement context. Never invent roles.
3. No specific dates — use relative timing only (Month 1, Months 3-6, etc.).
4. future_state_table_rows: omit any row where current or target cannot be sourced from the data.
5. risk_table_rows: only risks explicitly named in the Synthesizer. No generic risks.
6. Empty is better than fabricated. A missing cell is honest. A fabricated cell damages credibility.
7. executive_briefing.problems: every finding_id must match an ID in ACCEPTED FINDINGS exactly.
   Do not invent finding IDs. plain_title must describe the actual finding, not a generic
   business problem. impact_brief must be grounded in the finding's evidence.
8. executive_briefing.numbers: every finding_id must match an ID in ACCEPTED FINDINGS exactly.
   Only CONFIRMED or DERIVED figures — never INFERRED. Do not invent figures; the actual dollar
   amount will be sourced from the finding's economic_impact field at render time — your
   finding_id is the link, not the figure itself.

---

PRIVACY / ANONYMIZATION — apply to every field:
Individual consultant, PM, and IC names must never appear in the report in any context that
describes their performance, overrun rate, utilization, departure, or other individual
performance data. This protects the firm from HR exposure when the report is distributed.

Replace named individuals with role-based references:
  - Named PMs with overrun patterns → "two project managers with confirmed estimation
    overrun patterns" or "PM-A" and "PM-B" if multiple individuals must be distinguished
  - Named consultants with utilization issues → "one senior consultant above 100% utilization"
  - Named departures → "two PM departures in [month/year]" — role and timing only

This rule applies to: root_cause_narrative, domain_analysis opening/closing paragraphs,
initiative_details success_metric, next_steps_rows completion_criteria, risk_table_rows.

This does NOT apply to:
  - Named client contacts in leadership roles (CEO, Director of Delivery, VP of Sales) —
    these are accountability references, not performance data
  - Named client organizations or project names used as commercial references
    (e.g. "Glacier Point account", "Meridian Financial project")

When you find individual IC names in the Synthesizer output, anonymize them in your output.
A missing name is always better than a name that creates HR exposure in a distributed document.

---

SYSTEM REFERENCE CODES — NEVER USE IN PROSE:
R-codes (R060, R061, R062, etc.) are internal system identifiers for roadmap items.
They are meaningless to the client and must never appear in generated prose.
Always reference initiatives by their plain initiative name.

Correct:   "the governance policy initiative must precede the methodology development work"
Incorrect: "the governance policy (R063) must precede the methodology development (R072)"

This applies to every prose field: executive_snapshot, executive_summary_opening,
executive_summary_para1/2/3, root_cause_narrative, economic_impact_narrative,
future_state_narrative, roadmap_rationale, domain_analysis opening/closing paragraphs,
and all initiative_details prose fields.

---

WRITING RULES:
1. Write as a senior consultant. Direct, confident, grounded in evidence. Not corporate filler.
2. Lead with the most important insight. Not with background or context-setting.
3. Use specific numbers, names, and references from the Synthesizer. Do not generalize where specifics exist.
4. Every dollar figure carries CONFIRMED, DERIVED, or INFERRED notation exactly as in the source.
5. Do not repeat the same content across sections. Each section adds something new.
6. State conclusions where evidence supports them. Use "the evidence suggests" only where
   the Skeptic's challenges remain unresolved.
7. Tone: direct, evidence-grounded, written for a CEO who is short on time and skeptical of consultants.
8. Banned phrases: "going forward", "leverage", "synergies", "best practices", "it is important
   to note", "it should be noted", "holistic approach", "at the end of the day".
9. No meta-commentary about the report itself.
10. Return only the JSON object — no preamble, no sign-off, no explanation."""


COMPRESSION_PROMPT = """You are a copy editor for a senior consulting report.
Compress the text for brevity. Target 25-30% shorter.

PRESERVE EXACTLY — do not alter or remove:
- All dollar figures, percentages, and numeric values
- All names (firm names, role names, person names)
- All CONFIRMED, DERIVED, and INFERRED labels
- Any text in parentheses beginning with "(see Section"
- All factual claims — only change how they are expressed, not what they say
- All specific completion criteria details — do not generalize what done looks like

COMPRESS BY:
- Removing redundant phrases and filler words
- Shortening multi-clause sentences to direct statements
- Eliminating throat-clearing openers ("It should be noted that...", "It is worth mentioning...")
- Merging short sequential sentences that repeat the same point

If you cannot compress without losing meaning or specifics, return the original text unchanged.
Return only the compressed text. No explanation. No markup. No commentary."""


async def compress_narrative(text: str, section_name: str) -> str:
    """Compress a narrator prose string for brevity (target 25-30% reduction).

    Preserves all figures, names, CONFIRMED/DERIVED/INFERRED labels, and factual claims.
    Falls back to the original text if the call fails, returns empty output, or
    produces output longer than the input.
    section_name is used for logging only.
    """
    if not text or not text.strip():
        return text
    try:
        message = await async_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=COMPRESSION_PROMPT,
            messages=[{"role": "user", "content": text}],
            timeout=300.0,
        )
        compressed = extract_text(message).strip()
        if not compressed:
            logger.warning(f"Compression empty for {section_name} — using original")
            return text
        orig_words = len(text.split())
        comp_words = len(compressed.split())
        if comp_words >= orig_words:
            logger.warning(
                f"Compression produced no reduction for {section_name} "
                f"({orig_words} → {comp_words} words) — using original"
            )
            return text
        logger.info(
            f"Compression {section_name}: {orig_words} → {comp_words} words "
            f"({round((1 - comp_words / orig_words) * 100)}% reduction)"
        )
        return compressed
    except Exception as exc:
        logger.warning(f"Compression failed for {section_name}: {exc} — using original")
        return text


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
    interview_roles: list = None,
    document_types: list = None,
    total_signals: int = 0,
    domain_count: int = 0,
    section_refs: dict = None,
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

    # --- Build findings lookup for economic linkage resolution ---
    findings_by_id = {f.get('finding_id'): f for f in findings if f.get('finding_id')}

    # --- Assemble roadmap summary — include item_id, effort, owner, capability,
    #     and resolved economic linkage so the narrator can synthesize economic
    #     stakes per phase and key initiative_details by item_id ---
    roadmap_lines = ["ROADMAP ITEMS BY PHASE:\n"]
    for phase in ['Stabilize', 'Optimize', 'Scale']:
        items = [r for r in roadmap if r.get('phase') == phase]
        if items:
            roadmap_lines.append(f"{phase}:")
            for item in items:
                line = (
                    f"  - [{item.get('item_id', '')}] {item.get('initiative_name', '')} | "
                    f"Domain: {item.get('domain', '')} | "
                    f"Priority: {item.get('priority', '')} | "
                    f"Effort: {item.get('effort', '')} | "
                    f"Owner: {item.get('owner') or 'TBD'} | "
                    f"Est. Impact: {item.get('estimated_impact', '')}"
                )
                if item.get('capability'):
                    line += f" | Capability: {item['capability']}"
                # Resolve addressing_finding_ids to economic_impact strings
                raw_ids = item.get('addressing_finding_ids') or '[]'
                try:
                    import json as _json
                    fids = _json.loads(raw_ids)
                except Exception:
                    fids = []
                econ_parts = [
                    findings_by_id[fid]['economic_impact']
                    for fid in fids
                    if fid in findings_by_id and findings_by_id[fid].get('economic_impact')
                ]
                if econ_parts:
                    line += f" | Addresses economic impact: {'; '.join(econ_parts)}"
                roadmap_lines.append(line)
            roadmap_lines.append("")

    # --- Assemble engagement context ---
    context_lines = [
        "ENGAGEMENT CONTEXT:\n",
        f"Firm: {engagement.get('firm_name', '')}",
        f"Firm Size: {engagement.get('firm_size', '')} people",
        f"Service Model: {engagement.get('service_model', '')}",
        f"Stated Problem: {engagement.get('stated_problem', '')}",
        f"Client Hypothesis: {engagement.get('client_hypothesis', '')}",
        f"Total signals identified: {total_signals} across {domain_count} domains",
    ]

    # --- Assemble processed file context (for engagement_overview_paragraph) ---
    file_lines = [
        "PROCESSED FILES (use only this list to derive interview roles and document "
        "types for engagement_overview_paragraph — do not invent sources not listed):\n"
    ]
    roles = interview_roles or []
    docs  = document_types  or []
    file_lines.append(
        f"Interviews conducted with: {', '.join(roles)}" if roles
        else "Interviews conducted: not available"
    )
    file_lines.append(
        f"Documents reviewed: {', '.join(docs)}" if docs
        else "Documents reviewed: not available"
    )

    # --- Assemble section cross-references from caller (sourced from _SECTION_MAP in
    #     report_generator.py — the single source of truth for section numbers).
    #     Injected as the first block so Claude sees current numbers before prose instructions.
    message_parts = []
    if section_refs:
        ref_lines = [
            "SECTION REFERENCES (copy these strings verbatim when instructed — "
            "do not alter section numbers or wording):"
        ]
        for key, text in section_refs.items():
            ref_lines.append(f"{key}: {text}")
        message_parts.append("\n".join(ref_lines))

    message_parts.extend([
        "SYNTHESIZER OUTPUT:\n\n" + synthesizer_output,
        "\n".join(context_lines),
        "\n".join(file_lines),
        "\n".join(findings_lines),
        "\n".join(roadmap_lines),
    ])

    user_message = "\n\n".join(message_parts)

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
        timeout=600.0,
    )
    raw = extract_text(message)
    logger.info(f"Narrator response received — {len(raw)} chars")

    sections = _parse_narrator_json(raw)
    logger.info(f"Narrator sections parsed — keys: {list(sections.keys())}")

    # --- Post-process prose for brevity (Executive Summary + Section 9) ---
    # Compress each prose string in parallel — failures fall back to originals.

    exec_keys = [
        k for k in ('executive_summary_opening', 'executive_summary_para1',
                    'executive_summary_para2', 'executive_summary_para3')
        if sections.get(k)
    ]
    if exec_keys:
        compressed = await asyncio.gather(
            *[compress_narrative(sections[k], k) for k in exec_keys]
        )
        for k, v in zip(exec_keys, compressed):
            sections[k] = v

    next_steps = sections.get('next_steps_rows', [])
    if isinstance(next_steps, list):
        indices = [
            i for i, row in enumerate(next_steps)
            if isinstance(row, dict) and row.get('completion_criteria')
        ]
        if indices:
            compressed_criteria = await asyncio.gather(
                *[compress_narrative(
                    next_steps[i]['completion_criteria'],
                    f'next_steps_row_{i}'
                ) for i in indices]
            )
            for idx, val in zip(indices, compressed_criteria):
                next_steps[idx]['completion_criteria'] = val

    return sections


async def extract_roadmap_from_synthesizer(
    synthesizer_output: str,
    findings: list,
) -> str:
    """Extract structured roadmap candidates from an accepted Synthesizer output.
    Findings are provided as context so initiative names align with the diagnostic.
    Returns raw JSON string — fence stripping and array extraction handled inside."""
    findings_lines = [
        "ACCEPTED FINDINGS (use finding_ids exactly as shown for addressing_finding_ids):\n"
    ]
    for f in findings:
        findings_lines.append(
            f"- [{f.get('finding_id', '')}] {f['finding_title']} | "
            f"Domain: {f.get('domain', '')} | "
            f"Priority: {f.get('priority', '')} | "
            f"Root Cause: {f.get('root_cause', '')} | "
            f"Economic Impact: {f.get('economic_impact', '')}"
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
        timeout=300.0,
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


async def suggest_display_label(
    finding_title: str,
    economic_impact_text: str,
    figure: str,
) -> str | None:
    """Call Claude to generate a 4-6 word plain English display label suitable
    for a CEO executive briefing number.
    Returns the label string or None if the call fails for any reason.
    Never raises — callers treat None as 'show blank with placeholder text'."""
    user_message = (
        "You are writing a label for a number that will appear in the executive "
        "briefing of a consulting diagnostic report. The label must be 4-6 words, "
        "plain English, suitable for a CEO to read at a glance.\n\n"
        f"Finding title: {finding_title}\n"
        f"Primary figure: {figure}\n"
        f"Economic context: {economic_impact_text[:200]}\n\n"
        "Return only the label. No explanation. No punctuation at the end.\n"
        "Examples of good labels:\n"
        "'Annual gross profit shortfall'\n"
        "'At-risk portfolio revenue'\n"
        "'Single-client churn exposure'\n"
        "'Annual bench cost drag'"
    )
    try:
        message = await async_client.messages.create(
            model=MODEL,
            max_tokens=20,
            messages=[{"role": "user", "content": user_message}],
            timeout=30.0,
        )
        label = extract_text(message).strip().strip("'\"")
        return label if label else None
    except Exception:
        logger.warning("suggest_display_label: Claude call failed — returning None", exc_info=True)
        return None
