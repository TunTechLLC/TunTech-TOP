import json as json_lib
import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.finding import FindingRepository
from api.db.repositories.agent_run import AgentRunRepository
from api.db.repositories.pattern import PatternRepository
from api.models.finding import FindingCreate, FindingUpdate, FindingResponse
from api.utils.domains import VALID_DOMAINS, VALID_FINDING_CONFIDENCES, VALID_PRIORITIES, VALID_EFFORTS

logger = logging.getLogger(__name__)

router = APIRouter()


def get_finding_repo() -> FindingRepository:
    return FindingRepository()


def get_agent_repo() -> AgentRunRepository:
    return AgentRunRepository()


def get_pattern_repo() -> PatternRepository:
    return PatternRepository()


@router.get("/{engagement_id}/findings")
def list_findings(
    engagement_id: str,
    repo: FindingRepository = Depends(get_finding_repo)
):
    """Return all findings for an engagement in priority order."""
    return repo.get_all(engagement_id)


@router.post("/{engagement_id}/findings",
             response_model=FindingResponse,
             status_code=201)
def create_finding(
    engagement_id: str,
    data: FindingCreate,
    finding_repo: FindingRepository  = Depends(get_finding_repo),
    agent_repo:   AgentRunRepository = Depends(get_agent_repo)
):
    """Create a finding and accept contributing patterns atomically.

    Requires Synthesizer agent to be accepted first (enforced below).

    This endpoint is called by:
    1. Manual Add Finding form (current)
    2. Parse Findings flow — Step 8 Extension 2 (not yet built)
       Will add: POST /{engagement_id}/findings/parse-synthesizer
       That endpoint fetches accepted Synthesizer output, calls Claude to extract
       structured findings, and calls this endpoint for each approved finding.
    """
    synthesizer = agent_repo.get_accepted_output(engagement_id, 'Synthesizer')
    if not synthesizer:
        raise HTTPException(
            status_code=400,
            detail="Synthesizer agent must be accepted before creating findings"
        )

    payload = data.model_dump()
    contributing_ep_ids = payload.pop('contributing_ep_ids', [])

    finding_id = finding_repo.create(engagement_id, payload, contributing_ep_ids)

    findings = finding_repo.get_all(engagement_id)
    finding  = next((f for f in findings if f['finding_id'] == finding_id), None)
    if not finding:
        raise HTTPException(status_code=500, detail="Finding created but could not be retrieved")
    return finding


@router.patch("/{engagement_id}/findings/{finding_id}")
def update_finding(
    engagement_id: str,
    finding_id:    str,
    data:          FindingUpdate,
    repo:          FindingRepository = Depends(get_finding_repo)
):
    """Update finding fields. Only provided fields are changed."""
    repo.update(finding_id, data.model_dump(exclude_none=True))
    return {"updated": finding_id}


@router.post("/{engagement_id}/findings/parse-synthesizer")
async def parse_synthesizer_findings(
    engagement_id:  str,
    agent_repo:     AgentRunRepository = Depends(get_agent_repo),
    pattern_repo:   PatternRepository  = Depends(get_pattern_repo),
):
    """Extract structured finding candidates from the accepted Synthesizer output.
    Returns candidates array held in frontend state — nothing is persisted until
    the user loads approved findings via POST /{engagement_id}/findings.

    Each candidate includes suggested_pattern_ids (P-IDs) which the frontend
    maps to EP IDs for the contributing patterns checklist pre-population."""
    from api.services.claude import extract_findings_from_synthesizer

    synthesizer_output = agent_repo.get_accepted_output(engagement_id, 'Synthesizer')
    if not synthesizer_output:
        raise HTTPException(
            status_code=400,
            detail="Synthesizer agent must be accepted before parsing findings"
        )
    if len(synthesizer_output) < 500:
        raise HTTPException(
            status_code=400,
            detail=f"Synthesizer output_full is too short ({len(synthesizer_output)} chars) — "
                   f"the full output was not saved. Re-run and accept the Synthesizer agent."
        )

    all_patterns     = pattern_repo.get_for_engagement(engagement_id)
    accepted_patterns = [p for p in all_patterns if p.get('accepted') == 1]

    raw = await extract_findings_from_synthesizer(synthesizer_output, accepted_patterns)

    try:
        candidates = json_lib.loads(raw)
    except json_lib.JSONDecodeError:
        logger.error(f"Claude returned invalid JSON for findings extraction: {raw[:200]}")
        raise HTTPException(
            status_code=500,
            detail="Claude returned invalid JSON — try again"
        )

    cleaned = []
    for item in candidates:
        if item.get('domain') not in VALID_DOMAINS:
            item['domain'] = 'Delivery Operations'
        if item.get('confidence') not in VALID_FINDING_CONFIDENCES:
            item['confidence'] = 'Medium'
        if item.get('priority') not in VALID_PRIORITIES:
            item['priority'] = 'High'
        if item.get('effort') not in VALID_EFFORTS:
            item['effort'] = 'Medium'
        if not isinstance(item.get('opd_section'), int) or not (1 <= item['opd_section'] <= 9):
            item['opd_section'] = 4
        if not isinstance(item.get('suggested_pattern_ids'), list):
            item['suggested_pattern_ids'] = []
        cleaned.append(item)

    logger.info(f"parse-synthesizer: {len(cleaned)} candidates for {engagement_id}")
    return {'candidates': cleaned}