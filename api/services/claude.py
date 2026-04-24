import os
import asyncio
import logging
import anthropic

from api.services.prompts import (
    SIGNAL_EXTRACTION_PROMPT,
    FINDINGS_EXTRACTION_PROMPT,
    ROADMAP_EXTRACTION_PROMPT,
    REPORT_NARRATOR_PROMPT,
    COMPRESSION_PROMPT,
)

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
async_client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), timeout=120.0, max_retries=0)

from config import MODEL, MAX_TOKENS


def extract_text(message: anthropic.types.Message) -> str:
    """Extract text content from a Claude API response.
    Finds the first TextBlock in the content list.
    Raises ValueError if no text block is found."""
    for block in message.content:
        if hasattr(block, 'text'):
            return block.text
    raise ValueError("No text block found in Claude API response")


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
    logger.info(f"Findings extraction complete — {len(clean)} chars")
    return clean


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
    if clean.startswith('```json'):
        clean = clean[7:]
    elif clean.startswith('```'):
        clean = clean[3:]
    if clean.endswith('```'):
        clean = clean[:-3]
    clean = clean.strip()
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
    NARRATOR_MAX_TOKENS = max(MAX_TOKENS * 2, 16000)

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

    findings_by_id = {f.get('finding_id'): f for f in findings if f.get('finding_id')}

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

    context_lines = [
        "ENGAGEMENT CONTEXT:\n",
        f"Firm: {engagement.get('firm_name', '')}",
        f"Firm Size: {engagement.get('firm_size', '')} people",
        f"Service Model: {engagement.get('service_model', '')}",
        f"Stated Problem: {engagement.get('stated_problem', '')}",
        f"Client Hypothesis: {engagement.get('client_hypothesis', '')}",
        f"Total signals identified: {total_signals} across {domain_count} domains",
    ]

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
