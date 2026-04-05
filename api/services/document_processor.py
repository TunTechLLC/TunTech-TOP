import os
import json
import logging
import hashlib
import shutil
from pathlib import Path
from datetime import date

from api.db.repositories.processed_files import ProcessedFilesRepository
from api.utils.domains import VALID_DOMAINS, VALID_CONFIDENCES
from api.services.claude import extract_text

logger = logging.getLogger(__name__)

VALID_FILE_TYPES = {'interview', 'financial', 'portfolio', 'sow', 'status', 'resource', 'delivery', 'other'}

FINANCIAL_EXTRACTION_PROMPT = """You are analyzing a financial document from a consulting firm diagnostic engagement.

Extract signals that are directly supported by data in the document. Focus on economics, margin, utilization, revenue, pricing, and financial health indicators.

Financial documents may contain tables of numbers with minimal narrative context.
When you see numerical data, infer the signal from the numbers themselves.
A gross margin percentage in a row labeled 'Gross Margin' is directly readable —
use the row label as the signal name and apply the confidence rules below.

Each item must have exactly these fields:
- signal_name: string
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string
- normalized_band: string
- evidence_quality: string — COMPLETE THIS BEFORE assigning signal_confidence. Scan the document for any issues with this signal's evidence: contradictory figures elsewhere in the document for this metric; whether the figure is inferred by you rather than explicitly stated; missing labels or context that make interpretation ambiguous. Write "None" only if the evidence is explicitly stated, clearly labeled, and unambiguous.
- signal_confidence: string — derived from evidence_quality:
    - Hypothesis: if evidence_quality contains anything other than "None"
    - Medium: if evidence_quality is "None" AND the signal is qualitative with no specific number
    - High: if evidence_quality is "None" AND a specific number is explicitly stated with a clear label
- source: string — always "Document"
- economic_relevance: string
- notes: string — include the specific data point from the document that supports this signal

Only extract signals with direct document evidence.
Extract no more than 10 signals. If you identify more, keep only the 10 most operationally significant.

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected"""

PORTFOLIO_EXTRACTION_PROMPT = """You are analyzing a project portfolio or status report from a consulting firm diagnostic engagement.

Extract signals related to delivery performance, project health, governance, and resource utilization.

Look specifically for:
- RAG status indicators (Red/Amber/Green) on individual projects
- Schedule variance — planned vs actual dates
- Budget variance — planned vs actual cost
- Resource utilization percentages
- Issues and risks listed in the report
- Projects described as 'at risk', 'delayed', or 'escalated'

Each item must have exactly these fields:
- signal_name: string
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string
- normalized_band: string
- evidence_quality: string — COMPLETE THIS BEFORE assigning signal_confidence. Scan the document for any issues with this signal's evidence: contradictory figures elsewhere in the document for this metric; whether the figure is inferred by you rather than explicitly stated; missing labels or context that make interpretation ambiguous. Write "None" only if the evidence is explicitly stated, clearly labeled, and unambiguous.
- signal_confidence: string — derived from evidence_quality:
    - Hypothesis: if evidence_quality contains anything other than "None"
    - Medium: if evidence_quality is "None" AND the signal is qualitative with no specific number
    - High: if evidence_quality is "None" AND a specific number is explicitly stated with a clear label
- source: string — always "Document"
- economic_relevance: string
- notes: string — include the specific data point from the document

Extract no more than 10 signals. If you identify more, keep only the 10 most operationally significant.

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected"""

SOW_EXTRACTION_PROMPT = """You are analyzing a Statement of Work or contract from a consulting firm diagnostic engagement.

Extract signals related to SOW quality, scope definition, acceptance criteria, assumptions, and sales-to-delivery transition indicators.

Focus particularly on:
- Presence or absence of measurable acceptance criteria
- Clarity of deliverable definitions
- Inclusion of an assumptions section
- Change control provisions
- Whether delivery team involvement is evident from document language
- Success criteria that are measurable vs vague

Each item must have exactly these fields:
- signal_name: string
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string
- normalized_band: string
- evidence_quality: string — COMPLETE THIS BEFORE assigning signal_confidence. Note any of the following: the signal is an inference from document tone rather than an explicit statement; contradictory language about the same element appears elsewhere in the document; the evidence is a single ambiguous phrase requiring interpretation. Write "None" only if the signal is unambiguously observable without interpretation.
- signal_confidence: string — derived from evidence_quality:
    - Hypothesis: if evidence_quality contains anything other than "None"
    - Medium: if evidence_quality is "None" AND the signal is qualitative with no specific number
    - High: if evidence_quality is "None" AND the presence or absence of a structural element is directly and unambiguously demonstrable
- source: string — always "Document"
- economic_relevance: string
- notes: string — include the specific language from the SOW that supports this signal

Extract no more than 10 signals. If you identify more, keep only the 10 most operationally significant.

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected"""

STATUS_EXTRACTION_PROMPT = """You are analyzing a project status report from a consulting firm diagnostic engagement.

Extract signals related to delivery health, project performance, and governance quality.

Focus on:
- Schedule status — on track, delayed, at risk, milestone completions
- Budget status — on budget, over budget, variance amounts
- Issues and risks — are they listed with owners and resolution dates?
- Escalations — what has been escalated and to whom?
- Action items — are they tracked with owners and due dates?
- Overall project health indicators — RAG status, confidence levels

Return only signals that are clearly observable in the document. Do not infer signals
that are not supported by specific text.
Extract no more than 10 signals. If you identify more, keep only the 10 most operationally significant.

Each item must have exactly these fields:
- signal_name: string — short descriptive name (e.g., "Multiple projects Red status")
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string — the specific value or observation (e.g., "3 of 7 projects Red")
- normalized_band: string — context for the value (e.g., "Above acceptable threshold")
- evidence_quality: string — COMPLETE THIS BEFORE assigning signal_confidence. Scan the document for any issues with this signal's evidence: contradictory figures elsewhere in the document for this metric; whether the figure is inferred by you rather than explicitly stated; missing labels or context that make interpretation ambiguous. Write "None" only if the evidence is explicitly stated, clearly labeled, and unambiguous.
- signal_confidence: string — derived from evidence_quality:
    - Hypothesis: if evidence_quality contains anything other than "None"
    - Medium: if evidence_quality is "None" AND the signal is qualitative with no specific number
    - High: if evidence_quality is "None" AND a specific number is explicitly stated with a clear label
- source: string — always "Document"
- economic_relevance: string — brief note on economic impact, or empty string
- notes: string — direct quote or specific reference from the document

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected"""

RESOURCE_EXTRACTION_PROMPT = """You are analyzing a resource utilization or staffing report from a consulting firm diagnostic engagement.

Extract signals related to utilization rates, staffing patterns, capacity, and resource management.

Focus on:
- Overall utilization percentage and target (e.g., 71% actual vs 78% target)
- Individual consultant utilization spread — are some overloaded while others are underutilized?
- Bench time — how many consultants are unbilled and for how long?
- Staffing assignment patterns — are projects understaffed or overstaffed?
- Hiring activity — open positions, time-to-fill, attrition
- Capacity vs pipeline alignment — do you have the right skills for upcoming work?

Return only signals that are clearly observable in the document.
Extract no more than 10 signals. If you identify more, keep only the 10 most operationally significant.

Each item must have exactly these fields:
- signal_name: string — short descriptive name
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string — the specific value (e.g., "71% billable utilization")
- normalized_band: string — context (e.g., "Below 78% target")
- evidence_quality: string — COMPLETE THIS BEFORE assigning signal_confidence. Scan the document for any issues with this signal's evidence: contradictory figures elsewhere in the document for this metric; whether the figure is inferred by you rather than explicitly stated; missing labels or context that make interpretation ambiguous. Write "None" only if the evidence is explicitly stated, clearly labeled, and unambiguous.
- signal_confidence: string — derived from evidence_quality:
    - Hypothesis: if evidence_quality contains anything other than "None"
    - Medium: if evidence_quality is "None" AND the signal is qualitative with no specific number
    - High: if evidence_quality is "None" AND a specific number is explicitly stated with a clear label
- source: string — always "Document"
- economic_relevance: string — brief note on economic impact, or empty string
- notes: string — direct reference from the document

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected"""

DELIVERY_DOCUMENT_EXTRACTION_PROMPT = """You are analyzing a delivery document from a consulting firm diagnostic engagement.

Delivery documents include risk registers, project retrospectives, portfolio summaries, and proposals.
Extract signals that are directly supported by evidence in the document.

Focus on:

Risk registers:
- Open risk count and severity distribution — how many High/Medium/Low risks are open?
- Mitigation coverage — are risks listed without mitigations or owners?
- Risk ownership gaps — risks with no assigned owner
- Escalated risks — items flagged for management attention

Retrospectives:
- Recurring issues — problems that appear across multiple retrospectives
- Action item completion — were prior retro actions actually resolved?
- Process improvement adoption — were changes from past retros implemented?
- Team health indicators — morale, capacity, or workload signals in retro language

Portfolio summaries:
- Aggregate delivery health — overall on-track / at-risk / red counts across the portfolio
- Capacity vs pipeline alignment — is current staffing sufficient for the active portfolio?
- Revenue recognition patterns — delayed milestones affecting invoicing

Proposals:
- Scope definition quality — are deliverables specific and measurable, or vague?
- Delivery methodology — is how delivery will be executed described, or absent?
- Assumptions coverage — is there an explicit assumptions section?
- Pricing structure — fixed fee, T&M, or hybrid; any margin risk indicators in the structure

Return only signals that are clearly observable in the document.
Extract no more than 10 signals. If you identify more, keep only the 10 most operationally significant.

Each item must have exactly these fields:
- signal_name: string — short descriptive name (e.g., "High open risk count with no mitigations")
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string — the specific observation (e.g., "14 of 22 risks unmitigated")
- normalized_band: string — context for the value (e.g., "Above acceptable threshold")
- evidence_quality: string — COMPLETE THIS BEFORE assigning signal_confidence. Note any of the following: the signal is inferred from document tone or pattern rather than explicitly stated; contradictory data appears elsewhere in the document; the evidence is a single ambiguous entry requiring interpretation. Write "None" only if the signal is unambiguously stated and supportable by direct reference.
- signal_confidence: string — derived from evidence_quality:
    - Hypothesis: if evidence_quality contains anything other than "None"
    - Medium: if evidence_quality is "None" AND the signal is qualitative with no specific number or count
    - High: if evidence_quality is "None" AND a specific number or count is explicitly stated with a clear label
- source: string — always "Document"
- economic_relevance: string — brief note on economic impact, or empty string
- notes: string — direct reference or quote from the document that supports this signal

CRITICAL OUTPUT FORMAT:
Your response must begin with the character [ and end with the character ]
Do not include any text, explanation, or markdown before or after the JSON array
Do not use code fences or backticks of any kind
If your response does not begin with [, it is invalid and will be rejected"""

PROMPT_MAP = {
    'interview':  None,       # uses SIGNAL_EXTRACTION_PROMPT from claude.py
    'financial':  FINANCIAL_EXTRACTION_PROMPT,
    'portfolio':  PORTFOLIO_EXTRACTION_PROMPT,
    'sow':        SOW_EXTRACTION_PROMPT,
    'status':     STATUS_EXTRACTION_PROMPT,
    'resource':   RESOURCE_EXTRACTION_PROMPT,
    'delivery':   DELIVERY_DOCUMENT_EXTRACTION_PROMPT,
    'other':      None,       # uses SIGNAL_EXTRACTION_PROMPT from claude.py
}


def get_file_type(file_name: str) -> str:
    """Extract file type from filename.
    Expected format: {engagement_id}_{type}_{description}.txt
    Returns 'other' if type cannot be determined or is not recognized."""
    parts = Path(file_name).stem.split('_')
    if len(parts) >= 2 and parts[1].lower() in VALID_FILE_TYPES:
        return parts[1].lower()
    return 'other'


def hash_file(file_path: str) -> str:
    """Generate MD5 hash of file contents for duplicate detection."""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def strip_json_fences(text: str) -> str:
    """Remove markdown code fences from Claude response.
    Handles ```json, ```, and no-fence cases.
    The CRITICAL OUTPUT FORMAT instruction reduces fence frequency but
    this remains as a safety net."""
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    return text.strip()


def scan_folder(folder_path: str, engagement_id: str) -> list[dict]:
    """Scan a folder for unprocessed .txt files belonging to this engagement.
    Returns list of dicts with path, name, type, hash."""
    if not folder_path or not os.path.exists(folder_path):
        return []

    pf_repo = ProcessedFilesRepository()
    candidates = []

    for file_name in sorted(os.listdir(folder_path)):
        if not file_name.endswith('.txt'):
            continue
        if not file_name.startswith(engagement_id):
            continue

        file_path = os.path.join(folder_path, file_name)
        file_hash = hash_file(file_path)

        if pf_repo.already_processed(file_hash):
            logger.info(f"Skipping already processed file: {file_name}")
            continue

        candidates.append({
            'path': file_path,
            'name': file_name,
            'type': get_file_type(file_name),
            'hash': file_hash,
        })

    return candidates


async def process_file(file_info: dict, engagement_id: str,
                       candidates_folder: str) -> dict:
    """Process a single file — extract signals via Claude and write
    candidate JSON to the candidates folder.
    Returns summary dict with file name, candidate count, and candidate file path."""
    from api.services.claude import (
        extract_signals_from_transcript,
        async_client,
        MODEL,
        MAX_TOKENS,
    )

    file_type = file_info['type']
    file_path = file_info['path']
    file_name = file_info['name']

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    logger.info(f"Processing {file_type} file: {file_name} ({len(content)} chars)")

    prompt = PROMPT_MAP.get(file_type)

    if prompt is None:
        # interview, other — use SIGNAL_EXTRACTION_PROMPT via extract_signals_from_transcript
        raw = await extract_signals_from_transcript(content)
    else:
        message = await async_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=prompt,
            messages=[{"role": "user", "content": f"DOCUMENT:\n\n{content}"}],
        )
        raw = extract_text(message)

    clean = strip_json_fences(raw)

    try:
        candidates = json.loads(clean)
    except json.JSONDecodeError:
        logger.error(f"Claude returned invalid JSON for {file_name}: {raw[:200]}")
        candidates = []

    cleaned = []
    for item in candidates:
        if item.get('domain') not in VALID_DOMAINS:
            logger.warning(f"Invalid domain '{item.get('domain')}' in {file_name} — defaulting to Delivery Operations")
            item['domain'] = 'Delivery Operations'
        if item.get('signal_confidence') not in VALID_CONFIDENCES:
            logger.warning(f"Invalid confidence '{item.get('signal_confidence')}' in {file_name} — defaulting to Medium")
            item['signal_confidence'] = 'Medium'
        item['interview_id'] = None
        item['source_file'] = file_name
        cleaned.append(item)

    stem = Path(file_name).stem
    os.makedirs(candidates_folder, exist_ok=True)
    candidate_file = os.path.join(candidates_folder, f"{stem}_candidates.json")

    with open(candidate_file, 'w', encoding='utf-8') as f:
        json.dump({
            'engagement_id':  engagement_id,
            'source_file':    file_name,
            'file_type':      file_type,
            'processed_date': date.today().isoformat(),
            'candidates':     cleaned,
        }, f, indent=2)

    logger.info(f"Wrote {len(cleaned)} candidates to {candidate_file}")

    return {
        'file_name':       file_name,
        'file_hash':       file_info['hash'],
        'file_type':       file_type,
        'candidate_count': len(cleaned),
        'candidate_file':  candidate_file,
        'candidates':      cleaned,
    }


def _apply_domain_cap(candidates: list[dict], cap: int = 5) -> tuple[list[dict], int]:
    """Cap candidates per domain, keeping highest-confidence entries first.
    Confidence order: High > Medium > Hypothesis.
    Returns (capped_list, count_removed)."""
    CONFIDENCE_RANK = {'High': 2, 'Medium': 1, 'Hypothesis': 0}
    by_domain: dict[str, list[dict]] = {}
    for c in candidates:
        domain = c.get('domain', '')
        by_domain.setdefault(domain, []).append(c)
    capped = []
    for domain_candidates in by_domain.values():
        sorted_dc = sorted(
            domain_candidates,
            key=lambda c: CONFIDENCE_RANK.get(c.get('signal_confidence', ''), 0),
            reverse=True,
        )
        capped.extend(sorted_dc[:cap])
    return capped, len(candidates) - len(capped)


def _deduplicate_candidates(candidates: list[dict]) -> tuple[list[dict], int]:
    """Deduplicate candidates by (domain, normalized signal_name).
    When two candidates share the same domain and signal name (case-insensitive,
    stripped), keep the higher-confidence one (High > Medium > Hypothesis).
    Returns (deduped_list, count_removed)."""
    CONFIDENCE_RANK = {'High': 2, 'Medium': 1, 'Hypothesis': 0}
    seen: dict[tuple, dict] = {}
    for candidate in candidates:
        key = (
            candidate.get('domain', ''),
            candidate.get('signal_name', '').lower().strip(),
        )
        if key not in seen:
            seen[key] = candidate
        else:
            existing_rank = CONFIDENCE_RANK.get(seen[key].get('signal_confidence', ''), 0)
            incoming_rank = CONFIDENCE_RANK.get(candidate.get('signal_confidence', ''), 0)
            if incoming_rank > existing_rank:
                seen[key] = candidate
    deduped = list(seen.values())
    return deduped, len(candidates) - len(deduped)


async def process_engagement_files(engagement_id: str,
                                   interviews_folder: str,
                                   documents_folder: str,
                                   candidates_folder: str) -> dict:
    """Main entry point — scan both folders, process all unprocessed files.
    Returns summary of what was processed including merged candidate file path
    and cull counts (dedup_count, hypothesis_count)."""
    all_files = []
    all_files.extend(scan_folder(interviews_folder, engagement_id))
    all_files.extend(scan_folder(documents_folder, engagement_id))

    if not all_files:
        return {'files_processed': 0, 'total_candidates': 0, 'files': [],
                'merged_candidate_file': None, 'dedup_count': 0, 'hypothesis_count': 0}

    pf_repo = ProcessedFilesRepository()
    results = []

    for file_info in all_files:
        try:
            result = await process_file(file_info, engagement_id, candidates_folder)
            pf_repo.mark_processed(
                engagement_id=engagement_id,
                file_name=file_info['name'],
                file_hash=file_info['hash'],
                file_type=file_info['type'],
                signal_count=result['candidate_count'],
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {file_info['name']}: {e}")
            results.append({
                'file_name':       file_info['name'],
                'error':           str(e),
                'candidate_count': 0,
                'candidates':      [],
            })

    # Collect all candidates from all files, annotating each with its source file
    all_candidates = []
    for result in results:
        source_file = result.get('file_name', '')
        for c in result.get('candidates', []):
            all_candidates.append({**c, 'source_file': source_file})

    # Deduplicate across files
    deduped, dedup_count = _deduplicate_candidates(all_candidates)

    # Per-domain cap: keep top 5 per domain by confidence
    capped, domain_cap_count = _apply_domain_cap(deduped, cap=5)

    # Separate High/Medium from Hypothesis
    main_candidates = [c for c in capped if c.get('signal_confidence') != 'Hypothesis']
    hypothesis_candidates = [c for c in capped if c.get('signal_confidence') == 'Hypothesis']
    hypothesis_count = len(hypothesis_candidates)

    # Write merged candidate file
    merged_file = os.path.join(candidates_folder, f"{engagement_id}_merged_candidates.json")
    with open(merged_file, 'w', encoding='utf-8') as f:
        json.dump({
            'engagement_id':         engagement_id,
            'candidates':            main_candidates,
            'hypothesis_candidates': hypothesis_candidates,
            'dedup_count':           dedup_count,
            'domain_cap_count':      domain_cap_count,
            'hypothesis_count':      hypothesis_count,
        }, f, indent=2)

    logger.info(
        f"Merged candidates for {engagement_id}: "
        f"{len(main_candidates)} main, {hypothesis_count} hypothesis, "
        f"{dedup_count} duplicates removed, {domain_cap_count} removed by domain cap"
    )

    total_candidates = sum(r.get('candidate_count', 0) for r in results)
    return {
        'files_processed':       len(results),
        'total_candidates':      total_candidates,
        'files':                 results,
        'merged_candidate_file': merged_file,
        'dedup_count':           dedup_count,
        'domain_cap_count':      domain_cap_count,
        'hypothesis_count':      hypothesis_count,
    }


def archive_candidate_files(engagement_id: str, candidates_folder: str,
                            merged_file: str) -> None:
    """Move candidate JSON files to candidates_folder/processed/ after loading.
    Archives the merged file and all individual per-file candidate JSONs for
    this engagement. Logs and continues on any failure — signals are already
    loaded and archival failure must not affect the caller."""
    if not candidates_folder or not os.path.exists(candidates_folder):
        logger.warning(f"archive_candidate_files: candidates_folder not found — {candidates_folder}")
        return

    processed_dir = os.path.join(candidates_folder, 'processed')
    try:
        os.makedirs(processed_dir, exist_ok=True)
    except OSError as e:
        logger.warning(f"archive_candidate_files: could not create processed/ dir — {e}")
        return

    files_to_archive = []

    # Merged file passed explicitly from the client
    if merged_file and os.path.exists(merged_file):
        files_to_archive.append(merged_file)

    # Individual per-file candidate JSONs for this engagement
    for entry in os.scandir(candidates_folder):
        if (entry.is_file()
                and entry.name.startswith(engagement_id + '_')
                and entry.name.endswith('_candidates.json')
                and entry.path != merged_file):
            files_to_archive.append(entry.path)

    for file_path in files_to_archive:
        dest = os.path.join(processed_dir, os.path.basename(file_path))
        try:
            shutil.move(file_path, dest)
            logger.info(f"Archived candidate file: {os.path.basename(file_path)}")
        except OSError as e:
            logger.warning(f"archive_candidate_files: could not move {file_path} — {e}")