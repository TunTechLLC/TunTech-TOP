import os
import json
import logging
import hashlib
from pathlib import Path
from datetime import date

from api.db.repositories.signal import SignalRepository
from api.db.repositories.processed_files import ProcessedFilesRepository

logger = logging.getLogger(__name__)

VALID_TYPES = {'interview', 'financial', 'portfolio', 'sow', 'other'}

FINANCIAL_EXTRACTION_PROMPT = """You are analyzing a financial document from a consulting firm diagnostic engagement.

Extract signals that are directly supported by data in the document. Focus on economics, margin, utilization, revenue, pricing, and financial health indicators.

Return ONLY a JSON array — no preamble, no explanation, no markdown code fences.

Each item must have exactly these fields:
- signal_name: string
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience"
- observed_value: string
- normalized_band: string
- signal_confidence: string — exactly "High", "Medium", or "Hypothesis"
- source: string — always "Document"
- economic_relevance: string
- notes: string — include the specific data point from the document that supports this signal

Only extract signals with direct document evidence. Return format:
[{"signal_name": "...", "domain": "...", "observed_value": "...", "normalized_band": "...", "signal_confidence": "High", "source": "Document", "economic_relevance": "...", "notes": "..."}]"""

PORTFOLIO_EXTRACTION_PROMPT = """You are analyzing a project portfolio or status report from a consulting firm diagnostic engagement.

Extract signals related to delivery performance, project health, governance, and resource utilization.

Return ONLY a JSON array — no preamble, no explanation, no markdown code fences.

Each item must have exactly these fields:
- signal_name: string
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience"
- observed_value: string
- normalized_band: string
- signal_confidence: string — exactly "High", "Medium", or "Hypothesis"
- source: string — always "Document"
- economic_relevance: string
- notes: string — include the specific data point from the document

Return format:
[{"signal_name": "...", "domain": "...", "observed_value": "...", "normalized_band": "...", "signal_confidence": "High", "source": "Document", "economic_relevance": "...", "notes": "..."}]"""

SOW_EXTRACTION_PROMPT = """You are analyzing a Statement of Work or contract from a consulting firm diagnostic engagement.

Extract signals related to SOW quality, scope definition, acceptance criteria, assumptions, and sales-to-delivery transition indicators.

Return ONLY a JSON array — no preamble, no explanation, no markdown code fences.

Each item must have exactly these fields:
- signal_name: string
- domain: string — must be exactly one of: "Sales & Pipeline", "Sales-to-Delivery Transition", "Delivery Operations", "Resource Management", "Project Governance / PMO", "Consulting Economics", "Customer Experience"
- observed_value: string
- normalized_band: string
- signal_confidence: string — exactly "High", "Medium", or "Hypothesis"
- source: string — always "Document"
- economic_relevance: string
- notes: string — include the specific language from the SOW that supports this signal

Return format:
[{"signal_name": "...", "domain": "...", "observed_value": "...", "normalized_band": "...", "signal_confidence": "High", "source": "Document", "economic_relevance": "...", "notes": "..."}]"""

PROMPT_MAP = {
    'interview':  None,   # uses SIGNAL_EXTRACTION_PROMPT from claude.py
    'financial':  FINANCIAL_EXTRACTION_PROMPT,
    'portfolio':  PORTFOLIO_EXTRACTION_PROMPT,
    'sow':        SOW_EXTRACTION_PROMPT,
    'other':      None,   # uses SIGNAL_EXTRACTION_PROMPT from claude.py
}


def get_file_type(file_name: str) -> str:
    """Extract file type from filename.
    Expected format: {engagement_id}_{type}_{description}.txt
    Returns 'other' if type cannot be determined."""
    parts = Path(file_name).stem.split('_')
    if len(parts) >= 2 and parts[1].lower() in VALID_TYPES:
        return parts[1].lower()
    return 'other'


def hash_file(file_path: str) -> str:
    """Generate MD5 hash of file contents for duplicate detection."""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


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
            'path':      file_path,
            'name':      file_name,
            'type':      get_file_type(file_name),
            'hash':      file_hash,
        })

    return candidates


async def process_file(file_info: dict, engagement_id: str,
                       candidates_folder: str) -> dict:
    """Process a single file — extract signals via Claude and write
    candidate JSON to the candidates folder.
    Returns summary dict with file name and candidate count."""
    from api.services.claude import (
        extract_signals_from_transcript,
        SIGNAL_EXTRACTION_PROMPT,
    )
    import anthropic

    file_type = file_info['type']
    file_path = file_info['path']
    file_name = file_info['name']

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    logger.info(f"Processing {file_type} file: {file_name} ({len(content)} chars)")

    if file_type == 'interview' or file_type == 'other':
        raw = await extract_signals_from_transcript(content)
    else:
        from api.services.claude import async_client, MODEL, MAX_TOKENS
        prompt = PROMPT_MAP[file_type]
        message = await async_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=prompt,
            messages=[{"role": "user", "content": f"DOCUMENT:\n\n{content}"}],
        )
        raw = message.content[0].text

    clean = raw.strip()
    if clean.startswith('```'):
        clean = clean.split('\n', 1)[1] if '\n' in clean else clean
        clean = clean.rsplit('```', 1)[0].strip()

    try:
        candidates = json.loads(clean)
    except json.JSONDecodeError:
        logger.error(f"Claude returned invalid JSON for {file_name}: {raw[:80]}")
        candidates = []

    valid_domains = {
        'Sales & Pipeline', 'Sales-to-Delivery Transition', 'Delivery Operations',
        'Resource Management', 'Project Governance / PMO', 'Consulting Economics',
        'Customer Experience'
    }
    valid_confidences = {'High', 'Medium', 'Hypothesis'}

    cleaned = []
    for item in candidates:
        if item.get('domain') not in valid_domains:
            item['domain'] = 'Delivery Operations'
        if item.get('signal_confidence') not in valid_confidences:
            item['signal_confidence'] = 'Medium'
        item['interview_id'] = None
        cleaned.append(item)

    stem = Path(file_name).stem
    candidate_file = os.path.join(candidates_folder, f"{stem}_candidates.json")
    os.makedirs(candidates_folder, exist_ok=True)

    with open(candidate_file, 'w', encoding='utf-8') as f:
        json.dump({
            'engagement_id': engagement_id,
            'source_file':   file_name,
            'file_type':     file_type,
            'processed_date': date.today().isoformat(),
            'candidates':    cleaned,
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
    Returns summary of what was processed."""
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
                'file_name': file_info['name'],
                'error':     str(e),
                'candidate_count': 0,
            })

    total_candidates = sum(r.get('candidate_count', 0) for r in results)
    return {
        'files_processed':  len(results),
        'total_candidates': total_candidates,
        'files':            results,
    }