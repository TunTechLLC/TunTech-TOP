import os
import re
import json
import asyncio
import logging
import anthropic

from api.services.prompts import (
    SIGNAL_EXTRACTION_PROMPT,
    FINDINGS_EXTRACTION_PROMPT,
    ROADMAP_EXTRACTION_PROMPT,
    REPORT_NARRATOR_PROMPT,
    COMPRESSION_PROMPT,
    DOWNGRADE_EXTRACTION_PROMPT,
    QA_COVERAGE_PROMPT,
    QA_COHERENCE_PROMPT,
    QA_EDITORIAL_VOICE_PROMPT,
    QA_REVISION_PROMPT,
)

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
async_client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), timeout=120.0, max_retries=0)

from config import MODEL, MAX_TOKENS

# Agents — especially the Synthesizer, which integrates all prior outputs and now also
# assembles the "What to Preserve" strengths — produce long outputs on rich engagements.
# The global 8000 cap truncated the Synthesizer mid-output on a large engagement. A ceiling
# costs nothing for short outputs (output is billed by tokens generated, not the cap), so
# match the narrator's 16000 to prevent truncation. Per-call override available below.
AGENT_MAX_TOKENS = max(MAX_TOKENS * 2, 16000)


def extract_text(message: anthropic.types.Message) -> str:
    """Extract text content from a Claude API response.
    Finds the first TextBlock in the content list.
    Raises ValueError if no text block is found."""
    for block in message.content:
        if hasattr(block, 'text'):
            return block.text
    raise ValueError("No text block found in Claude API response")


async def _stream_final_message(*, model, max_tokens, messages, system=None):
    """Call Claude via streaming and return the final Message.

    Streaming (not messages.create) is required for long Opus calls: a non-streaming
    request holds the connection open for the whole response and hits the client
    read-timeout on large input+output, so the server cuts it mid-flight. Proven
    empirically — a 142s Synthesizer streamed cleanly where the non-streaming path
    raised APITimeoutError. Returns the same Message shape as messages.create, so
    callers' extract_text()/stop_reason logic is unchanged.
    See https://docs.anthropic.com/en/api/errors#long-requests
    """
    params = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system is not None:
        params["system"] = system
    async with async_client.messages.stream(**params) as stream:
        return await stream.get_final_message()


async def call_claude(
    case_packet:   str,
    prior_outputs: list,
    prompt:        str,
    max_tokens:    int = None,
) -> str:
    """Assemble case packet plus prior agent outputs and call Claude API.
    Uses async client — do not call with synchronous client, it blocks the event loop.
    max_tokens defaults to AGENT_MAX_TOKENS; a truncated response is logged loudly."""
    parts = [f"CASE PACKET:\n\n{case_packet}"]
    if prior_outputs:
        for i, output in enumerate(prior_outputs, 1):
            if output:
                parts.append(f"PRIOR AGENT OUTPUT {i}:\n\n{output}")
    user_message = "\n\n---\n\n".join(parts)
    cap = max_tokens or AGENT_MAX_TOKENS
    logger.info(f"Calling Claude API — context length: {len(user_message)} chars, max_tokens={cap}")
    message = await _stream_final_message(
        model=MODEL,
        max_tokens=cap,
        system=prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    if getattr(message, 'stop_reason', None) == 'max_tokens':
        logger.warning(
            f"call_claude: agent output TRUNCATED at max_tokens={cap} — output is "
            f"incomplete. Re-run with a higher cap before accepting."
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
    message = await _stream_final_message(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SIGNAL_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": user_content}],
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
    message = await _stream_final_message(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=FINDINGS_EXTRACTION_PROMPT,
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
        message = await _stream_final_message(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=COMPRESSION_PROMPT,
            messages=[{"role": "user", "content": text}],
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
    NARRATOR_MAX_TOKENS = max(MAX_TOKENS * 3, 24000)

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

    # VALIDATED STRENGTHS — Positive/Dual findings that survived the Skeptic. Feeds the
    # narrator's executive_summary_strengths field (Track 2). Empty when none exist, in
    # which case the block is omitted and the narrator returns null for that field, so the
    # Executive Summary renders byte-identically to a negative-only report.
    strength_findings = [
        f for f in findings if (f.get('valence') or '').lower() in ('positive', 'dual')
    ]
    strength_lines = []
    if strength_findings:
        strength_lines.append(
            "VALIDATED STRENGTHS (use ONLY these for executive_summary_strengths — each "
            "survived the Skeptic and is tied to a specific account, metric, or behavior; "
            "frame as leverage for the transformation, never generic praise):\n"
        )
        for f in strength_findings:
            kind = ('strength-under-strain'
                    if (f.get('valence') or '').lower() == 'dual' else 'strength')
            strength_lines.append(
                f"[{f.get('finding_id', '')}] ({kind}) {f['finding_title']} | "
                f"Domain: {f.get('domain', '')}"
            )
            if f.get('operational_impact'):
                strength_lines.append(f"  What is working: {f['operational_impact']}")
            if f.get('root_cause'):
                strength_lines.append(f"  Why it works: {f['root_cause']}")
            if f.get('recommendation'):
                strength_lines.append(f"  How to protect it: {f['recommendation']}")
            strength_lines.append("")

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
    ])
    if strength_lines:
        message_parts.append("\n".join(strength_lines))
    message_parts.append("\n".join(roadmap_lines))

    user_message = "\n\n".join(message_parts)

    logger.info(
        f"Generating report narrative — {len(synthesizer_output)} chars synthesizer, "
        f"{len(findings)} findings, {len(roadmap)} roadmap items, "
        f"max_tokens={NARRATOR_MAX_TOKENS}"
    )

    message = await _stream_final_message(
        model=MODEL,
        max_tokens=NARRATOR_MAX_TOKENS,
        system=REPORT_NARRATOR_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    if getattr(message, 'stop_reason', None) == 'max_tokens':
        logger.warning(
            f"generate_report_narrative: narrator output TRUNCATED at "
            f"max_tokens={NARRATOR_MAX_TOKENS} — report JSON is incomplete and may fail to "
            f"parse or render. Raise NARRATOR_MAX_TOKENS and regenerate."
        )
    raw = extract_text(message)
    logger.info(f"Narrator response received — {len(raw)} chars")

    sections = _parse_narrator_json(raw)
    logger.info(f"Narrator sections parsed — keys: {list(sections.keys())}")

    exec_keys = [
        k for k in ('executive_summary_opening', 'executive_summary_para1',
                    'executive_summary_para2', 'executive_summary_para3',
                    'executive_summary_strengths')
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
    message = await _stream_final_message(
        model=MODEL,
        max_tokens=AGENT_MAX_TOKENS,
        system=ROADMAP_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    if getattr(message, 'stop_reason', None) == 'max_tokens':
        logger.warning(
            f"extract_roadmap_from_synthesizer: roadmap JSON TRUNCATED at "
            f"max_tokens={AGENT_MAX_TOKENS} — the array is cut off and will fail to parse. "
            f"Raise the cap and re-extract."
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


async def extract_downgrade_recommendations(skeptic_output: str) -> list[dict]:
    """Extract pattern downgrade recommendations from a Skeptic agent output.

    Returns a validated list of dicts with pattern_id, recommended_confidence,
    and reason. Items with invalid pattern_id format or confidence value are
    dropped. Returns [] on any failure — never raises.
    max_tokens=500: the response is a small JSON array, never legitimately larger.
    """
    user_message = DOWNGRADE_EXTRACTION_PROMPT + "\n" + skeptic_output
    try:
        message = await async_client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": user_message}],
            timeout=60.0,
        )
        raw = extract_text(message).strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        start = raw.find('[')
        end   = raw.rfind(']')
        if start == -1 or end == -1 or end <= start:
            logger.warning("extract_downgrade_recommendations: no JSON array in response")
            return []
        raw = raw[start:end + 1]
        items = json.loads(raw)
    except Exception as exc:
        logger.warning(f"extract_downgrade_recommendations failed: {exc}")
        return []

    valid_confidences = {'High', 'Medium', 'Hypothesis'}
    result = []
    for item in items:
        pid    = item.get('pattern_id', '')
        conf   = item.get('recommended_confidence', '')
        reason = item.get('reason', '')
        if not (isinstance(pid, str) and pid.startswith('P') and pid[1:].isdigit()):
            logger.warning(f"extract_downgrade_recommendations: dropped invalid pattern_id {pid!r}")
            continue
        if conf not in valid_confidences:
            logger.warning(f"extract_downgrade_recommendations: dropped invalid confidence {conf!r}")
            continue
        result.append({'pattern_id': pid, 'recommended_confidence': conf, 'reason': reason})

    logger.info(f"extract_downgrade_recommendations: {len(result)} valid recommendation(s)")
    return result


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


# ---------------------------------------------------------------------------
# Post-Assembly QA Stage — Coverage Check (QA-1)
# ---------------------------------------------------------------------------

QA_COVERAGE_MODEL = "claude-opus-4-7"
QA_COVERAGE_MAX_TOKENS = 16000


async def detect_coverage_gaps(
    source_documents_block: str,
    roadmap_v1_text: str,
    model: str = QA_COVERAGE_MODEL,
) -> list[dict]:
    """Detect items present in source documents that are missing or only partially
    addressed in the v1 roadmap. Used by the QA-1 Coverage Check Agent.

    Args:
        source_documents_block: pre-assembled string containing all source documents,
            each preceded by ``=== SOURCE: <filename> ===`` header.
        roadmap_v1_text: full text of v1 roadmap (extracted from .docx).
        model: Claude model ID. Defaults to claude-opus-4-7 — latest Opus, the
            most capable model for detection-quality tasks. Bump this constant
            when newer Opus releases. Explicit override of global TOP_MODEL
            (Sonnet) — keeps the rest of TOP on Sonnet.

    Returns:
        Validated list of item dicts. Items with invalid tier or appears_in_roadmap
        values are dropped with a warning. Returns [] on API failure, parse failure,
        or empty response — never raises.
    """
    user_message = (
        f"SOURCE DOCUMENTS:\n\n{source_documents_block}"
        f"\n\n---\n\n"
        f"ROADMAP V1:\n\n{roadmap_v1_text}"
    )
    logger.info(
        f"detect_coverage_gaps: source block {len(source_documents_block)} chars, "
        f"roadmap {len(roadmap_v1_text)} chars, model={model}"
    )
    # Streaming required — per Anthropic guidance, long requests (large input +
    # large output) must stream or the server cuts the connection mid-flight.
    # See https://docs.anthropic.com/en/api/errors#long-requests
    try:
        async with async_client.messages.stream(
            model=model,
            max_tokens=QA_COVERAGE_MAX_TOKENS,
            system=QA_COVERAGE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            message = await stream.get_final_message()
        raw = extract_text(message).strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        start = raw.find('[')
        end   = raw.rfind(']')
        if start == -1 or end == -1 or end <= start:
            logger.warning("detect_coverage_gaps: no JSON array in response")
            return []
        raw = raw[start:end + 1]
        items = json.loads(raw)
    except Exception as exc:
        logger.warning(f"detect_coverage_gaps failed: {exc}")
        return []

    valid_tiers = {1, 2, 3}
    valid_roadmap_states = {0, 1}
    required_fields = (
        'source_file', 'who_said_it', 'what_was_said',
        'location_in_source', 'appears_in_roadmap', 'tier',
    )
    result = []
    for item in items:
        # Required-string field validation
        if not all(isinstance(item.get(f), str) and item.get(f).strip() for f in required_fields[:4]):
            logger.warning(f"detect_coverage_gaps: dropped item missing required string field — {item!r}")
            continue
        tier = item.get('tier')
        appears = item.get('appears_in_roadmap')
        if tier not in valid_tiers:
            logger.warning(f"detect_coverage_gaps: dropped item with invalid tier {tier!r}")
            continue
        if appears not in valid_roadmap_states:
            logger.warning(f"detect_coverage_gaps: dropped item with invalid appears_in_roadmap {appears!r}")
            continue
        # Normalize roadmap_location: must be None when appears_in_roadmap=0, else a string
        roadmap_location = item.get('roadmap_location')
        if appears == 0:
            roadmap_location = None
        elif not isinstance(roadmap_location, str) or not roadmap_location.strip():
            logger.warning(f"detect_coverage_gaps: dropped partial-coverage item with empty roadmap_location")
            continue
        result.append({
            'source_file':        item['source_file'].strip(),
            'who_said_it':        item['who_said_it'].strip(),
            'what_was_said':      item['what_was_said'].strip(),
            'location_in_source': item['location_in_source'].strip(),
            'appears_in_roadmap': appears,
            'roadmap_location':   roadmap_location,
            'tier':               tier,
        })

    logger.info(f"detect_coverage_gaps: {len(result)} valid coverage gap(s) returned")
    return result


# ---------------------------------------------------------------------------
# Post-Assembly QA Stage — Coherence Check (QA-2)
# ---------------------------------------------------------------------------

QA_COHERENCE_MODEL = "claude-opus-4-7"
QA_COHERENCE_MAX_TOKENS = 16000
QA_COHERENCE_VALID_CATEGORIES = {
    'contradiction', 'priority_mismatch', 'weak_grounding', 'missing_root_cause',
}


async def detect_coherence_issues(
    roadmap_v1_text: str,
    model: str = QA_COHERENCE_MODEL,
) -> list[dict]:
    """Detect internal coherence issues in the v1 roadmap document. Used by
    the QA-2 Coherence Check Agent.

    Standalone read — only the v1 roadmap is passed in. The prompt explicitly
    instructs the agent not to flag source-vs-doc coverage gaps (QA-1's job).

    Args:
        roadmap_v1_text: full text of v1 roadmap (extracted from .docx).
        model: Claude model ID. Defaults to claude-opus-4-7 — same model used
            for QA-1 detection; matches the proven Cowork quality bar.

    Returns:
        Validated list of item dicts. Items with invalid category, tier, or
        sections_involved are dropped with warnings. Returns [] on any failure.
    """
    user_message = f"ROADMAP V1:\n\n{roadmap_v1_text}"
    logger.info(
        f"detect_coherence_issues: roadmap {len(roadmap_v1_text)} chars, model={model}"
    )
    # Streaming required for long outputs — same reasoning as QA-1.
    try:
        async with async_client.messages.stream(
            model=model,
            max_tokens=QA_COHERENCE_MAX_TOKENS,
            system=QA_COHERENCE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            message = await stream.get_final_message()
        raw = extract_text(message).strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        start = raw.find('[')
        end   = raw.rfind(']')
        if start == -1 or end == -1 or end <= start:
            logger.warning("detect_coherence_issues: no JSON array in response")
            return []
        raw = raw[start:end + 1]
        items = json.loads(raw)
    except Exception as exc:
        logger.warning(f"detect_coherence_issues failed: {exc}")
        return []

    valid_tiers = {1, 2, 3}
    required_str_fields = ('issue', 'category', 'recommended_fix')
    result = []
    for item in items:
        if not all(isinstance(item.get(f), str) and item.get(f).strip() for f in required_str_fields):
            logger.warning(
                f"detect_coherence_issues: dropped item missing required string field — {item!r}"
            )
            continue
        tier = item.get('tier')
        category = item.get('category')
        sections = item.get('sections_involved')
        if tier not in valid_tiers:
            logger.warning(f"detect_coherence_issues: dropped item with invalid tier {tier!r}")
            continue
        if category not in QA_COHERENCE_VALID_CATEGORIES:
            logger.warning(f"detect_coherence_issues: dropped item with invalid category {category!r}")
            continue
        if not isinstance(sections, list) or not all(isinstance(s, str) and s.strip() for s in sections):
            logger.warning(
                f"detect_coherence_issues: dropped item with invalid sections_involved {sections!r}"
            )
            continue
        result.append({
            'issue':             item['issue'].strip(),
            'category':          category,
            'sections_involved': [s.strip() for s in sections],
            'recommended_fix':   item['recommended_fix'].strip(),
            'tier':              tier,
        })

    logger.info(f"detect_coherence_issues: {len(result)} valid coherence issue(s) returned")
    return result


# ---------------------------------------------------------------------------
# Post-Assembly QA Stage — Editorial Voice/Audience Check (QA-3, Claude pipe)
# ---------------------------------------------------------------------------

QA_EDITORIAL_VOICE_MODEL = "claude-opus-4-7"
QA_EDITORIAL_VOICE_MAX_TOKENS = 8000
QA_EDITORIAL_VOICE_VALID_CATEGORIES = {'voice', 'context_gap'}


async def detect_editorial_voice(
    roadmap_v1_text: str,
    model: str = QA_EDITORIAL_VOICE_MODEL,
) -> list[dict]:
    """Detect voice/audience editorial issues in the v1 roadmap. Used by the
    QA-3 Editorial Check (Claude pipeline).

    Narrow scope by design: only voice intrusions, tense-shift issues, and
    audience-inappropriate language in CEO-facing sections. Other editorial
    issues (signal codes leaking, undefined acronyms, terminology drift) are
    handled by the deterministic Python pipeline in editorial_auditor.py.

    Args:
        roadmap_v1_text: full text of v1 roadmap.
        model: Claude model ID. Defaults to Opus 4.7.

    Returns:
        Validated list of item dicts with source='claude' attached. Items
        with invalid category or tier are dropped with warnings. Returns []
        on any failure — never raises.
    """
    user_message = f"ROADMAP V1:\n\n{roadmap_v1_text}"
    logger.info(
        f"detect_editorial_voice: roadmap {len(roadmap_v1_text)} chars, model={model}"
    )
    try:
        async with async_client.messages.stream(
            model=model,
            max_tokens=QA_EDITORIAL_VOICE_MAX_TOKENS,
            system=QA_EDITORIAL_VOICE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            message = await stream.get_final_message()
        raw = extract_text(message).strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        start = raw.find('[')
        end   = raw.rfind(']')
        if start == -1 or end == -1 or end <= start:
            logger.warning("detect_editorial_voice: no JSON array in response")
            return []
        raw = raw[start:end + 1]
        items = json.loads(raw)
    except Exception as exc:
        logger.warning(f"detect_editorial_voice failed: {exc}")
        return []

    valid_tiers = {1, 2, 3}
    required_str_fields = ('issue', 'category', 'location', 'recommended_fix')
    result = []
    for item in items:
        if not all(isinstance(item.get(f), str) and item.get(f).strip() for f in required_str_fields):
            logger.warning(
                f"detect_editorial_voice: dropped item missing required string field — {item!r}"
            )
            continue
        tier = item.get('tier')
        category = item.get('category')
        if tier not in valid_tiers:
            logger.warning(f"detect_editorial_voice: dropped item with invalid tier {tier!r}")
            continue
        if category not in QA_EDITORIAL_VOICE_VALID_CATEGORIES:
            logger.warning(
                f"detect_editorial_voice: dropped item with invalid category {category!r}"
            )
            continue
        result.append({
            'issue':           item['issue'].strip(),
            'category':        category,
            'location':        item['location'].strip(),
            'recommended_fix': item['recommended_fix'].strip(),
            'standard_term':   None,
            'tier':            tier,
            'source':          'claude',
        })

    logger.info(f"detect_editorial_voice: {len(result)} valid voice/audience item(s) returned")
    return result


# ---------------------------------------------------------------------------
# Post-Assembly QA Stage — Revision Agent (QA-4)
# ---------------------------------------------------------------------------

QA_REVISION_MODEL = "claude-opus-4-7"
# Higher than the global TOP_MAX_TOKENS (8000) — a full edit list against an
# ~80K-char document ran ~13-19K output tokens in the QA-4 Step 0 model test.
# Per-call value; does NOT change the global default. Streaming required.
QA_REVISION_MAX_TOKENS = 32000
QA_REVISION_VALID_TYPES = {'replace', 'insert_after', 'manual'}
QA_REVISION_VALID_SOURCES = {'coverage', 'coherence', 'editorial'}


async def generate_revision_edits(
    roadmap_v1_text: str,
    accepted_items_block: str,
    model: str = QA_REVISION_MODEL,
) -> list[dict]:
    """Produce a structured edit list that applies the accepted QA items to the
    v1 roadmap. Used by the QA-4 Revision Agent.

    This is judgment work — deciding how each accepted item maps to a concrete
    text edit. Locating the anchors in the document and applying the edits is
    deterministic and lives in code (api/services/qa_revision.py), not here.

    Args:
        roadmap_v1_text: full text of v1 roadmap (extracted from the .docx).
        accepted_items_block: pre-assembled string of accepted Coverage,
            Coherence, and Editorial items (see qa_inputs.assemble_accepted_qa_items_block).
        model: Claude model ID. Defaults to claude-opus-4-7 — locked for QA-4
            after the Step 0 model test (97% clean anchor applicability vs 91%
            for 4.8, and 4.8 over-flagged simple edits as manual). Explicit
            override of global TOP_MODEL (Sonnet).

    Returns:
        Validated list of edit dicts, each with keys: type, anchor,
        context_before, new_text, qa_source, reason. Malformed edits are
        dropped with a warning. Returns [] on API/parse failure — never raises.
        Outcome and match_method are NOT set here — the applier assigns them.
    """
    user_message = (
        f"ROADMAP V1:\n\n{roadmap_v1_text}"
        f"\n\n---\n\n"
        f"ACCEPTED QA ITEMS:\n\n{accepted_items_block}"
    )
    logger.info(
        f"generate_revision_edits: roadmap {len(roadmap_v1_text)} chars, "
        f"accepted items {len(accepted_items_block)} chars, model={model}"
    )
    # Streaming required — long input + long output. Non-streaming requests are
    # cut server-side on long generations (see detect_coverage_gaps note).
    try:
        async with async_client.messages.stream(
            model=model,
            max_tokens=QA_REVISION_MAX_TOKENS,
            system=QA_REVISION_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            message = await stream.get_final_message()
        if message.stop_reason == "max_tokens":
            logger.warning(
                "generate_revision_edits: response truncated at max_tokens — "
                "edit list may be incomplete"
            )
        raw = extract_text(message).strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        start = raw.find('[')
        end   = raw.rfind(']')
        if start == -1 or end == -1 or end <= start:
            logger.warning("generate_revision_edits: no JSON array in response")
            return []
        edits = json.loads(raw[start:end + 1])
    except Exception as exc:
        logger.warning(f"generate_revision_edits failed: {exc}")
        return []

    result = []
    for edit in edits:
        etype = edit.get('type')
        qa_source = edit.get('qa_source')
        anchor = edit.get('anchor')
        new_text = edit.get('new_text')
        if etype not in QA_REVISION_VALID_TYPES:
            logger.warning(f"generate_revision_edits: dropped edit with invalid type {etype!r}")
            continue
        if qa_source not in QA_REVISION_VALID_SOURCES:
            logger.warning(f"generate_revision_edits: dropped edit with invalid qa_source {qa_source!r}")
            continue
        if not isinstance(anchor, str) or not anchor.strip():
            logger.warning(f"generate_revision_edits: dropped edit with empty anchor — {edit!r}")
            continue
        if not isinstance(new_text, str) or not new_text.strip():
            logger.warning(f"generate_revision_edits: dropped edit with empty new_text — {edit!r}")
            continue
        context_before = edit.get('context_before')
        reason = edit.get('reason')
        source_item_id = edit.get('source_item_id')
        result.append({
            'type':           etype,
            'anchor':         anchor,
            'context_before': context_before if isinstance(context_before, str) else '',
            'new_text':       new_text,
            'qa_source':      qa_source,
            'source_item_id': source_item_id.strip() if isinstance(source_item_id, str) else '',
            'reason':         reason.strip() if isinstance(reason, str) else '',
        })

    logger.info(f"generate_revision_edits: {len(result)} valid edit(s) returned")
    return result
