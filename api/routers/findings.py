import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.finding import FindingRepository
from api.db.repositories.agent_run import AgentRunRepository
from api.models.finding import FindingCreate, FindingUpdate, FindingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_finding_repo() -> FindingRepository:
    return FindingRepository()


def get_agent_repo() -> AgentRunRepository:
    return AgentRunRepository()


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