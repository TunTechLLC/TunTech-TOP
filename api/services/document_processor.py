import os
import json
import logging
import hashlib
from pathlib import Path
from datetime import date

from api.db.repositories.processed_files import ProcessedFilesRepository
from api.utils.domains import VALID_DOMAINS, VALID_CONFIDENCES

logger = logging.getLogger(__name__)

VALID_FILE_TYPES = {'interview', 'financial', 'portfolio', 'sow', 'status', 'resource', 'delivery', 'other'}

FINANCIAL_EXTRACTION_PROMPT = """You are analyzing a financial document from a consulting firm diagnostic engagement.

Extract signals that are directly supported by data in the document. Focus on economics, margin, utilization, revenue, pricing, and financial health indicators.

Financial documents may contain tables of numbers with minimal narrative context.
When you see numerical data, infer the signal from the numbers themselves.
A gross margin of 31% in a row labeled 'Gross Margin' is a High confidence signal
even without a sentence explaining it. Use the row label as the signal name.

Each item must have exactly these fields:
- signal_name: string
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string
- normalized_band: string
- signal_confidence: string — exactly "High", "Medium", or "Hypothesis"
- source: string — always "Document"
- economic_relevance: string
- notes: string — include the specific data point from the document that supports this signal

Only extract signals with direct document evidence.

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
- signal_confidence: string — exactly "High", "Medium", or "Hypothesis"
- source: string — always "Document"
- economic_relevance: string
- notes: string — include the specific data point from the document

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
- signal_confidence: string — exactly "High", "Medium", or "Hypothesis"
- source: string — always "Document"
- economic_relevance: string
- notes: string — include the specific language from the SOW that supports this signal

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

A RAG status of Red on multiple projects is a High confidence Delivery Operations signal.
A pattern of late milestone completion is a High confidence signal.
Issues listed without owners or resolution dates indicate governance weakness — High confidence.
Budget overruns with specific percentages are High confidence Consulting Economics signals.

Return only signals that are clearly observable in the document. Do not infer signals
that are not supported by specific text.

Each item must have exactly these fields:
- signal_name: string — short descriptive name (e.g., "Multiple projects Red status")
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string — the specific value or observation (e.g., "3 of 7 projects Red")
- normalized_band: string — context for the value (e.g., "Above acceptable threshold")
- signal_confidence: string — exactly "High", "Medium", or "Hypothesis"
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

Specific numbers are high-value signals. A utilization rate of 71% against a 78% target
is a High confidence Resource Management signal. Extract it with the exact numbers as observed_value.

Return only signals that are clearly observable in the document.

Each item must have exactly these fields:
- signal_name: string — short descriptive name
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience", "AI Readiness", "Human Resources", "Finance and Commercial"
- observed_value: string — the specific value (e.g., "71% billable utilization")
- normalized_band: string — context (e.g., "Below 78% target")
- signal_confidence: string — exactly "High", "Medium", or "Hypothesis"
- source: string — always "Document"
- economic_relevance: string — brief note on economic impact, or empty string
- notes: string — direct reference from the document

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
    'delivery':   None,       # uses SIGNAL_EXTRACTION_PROMPT until DELIVERY_DOCUMENT_EXTRACTION_PROMPT built (post-Checkpoint 3)
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
        # interview, delivery, other — use SIGNAL_EXTRACTION_PROMPT via extract_signals_from_transcript
        raw = await extract_signals_from_transcript(content)
    else:
        message = await async_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=prompt,
            messages=[{"role": "user", "content": f"DOCUMENT:\n\n{content}"}],
        )
        raw = message.content[0].text

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
    }


async def process_engagement_files(engagement_id: str,
                                   interviews_folder: str,
                                   documents_folder: str,
                                   candidates_folder: str) -> dict:
    """Main entry point — scan both folders, process all unprocessed files.
    Returns summary of what was processed including all candidate file paths."""
    all_files = []
    all_files.extend(scan_folder(interviews_folder, engagement_id))
    all_files.extend(scan_folder(documents_folder, engagement_id))

    if not all_files:
        return {'files_processed': 0, 'total_candidates': 0, 'files': []}

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
            })

    total_candidates = sum(r.get('candidate_count', 0) for r in results)
    return {
        'files_processed':  len(results),
        'total_candidates': total_candidates,
        'files':            results,
    }