import json as json_lib
import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.roadmap import RoadmapRepository
from api.db.repositories.agent_run import AgentRunRepository
from api.db.repositories.finding import FindingRepository
from api.models.roadmap import RoadmapItemCreate, RoadmapItemResponse
from api.utils.domains import DEFAULT_DOMAIN, VALID_DOMAINS, VALID_PRIORITIES, VALID_EFFORTS

logger = logging.getLogger(__name__)

router = APIRouter()


VALID_PHASES = {'Stabilize', 'Optimize', 'Scale'}


def get_repo() -> RoadmapRepository:
    return RoadmapRepository()


def get_agent_repo() -> AgentRunRepository:
    return AgentRunRepository()


def get_finding_repo() -> FindingRepository:
    return FindingRepository()


@router.get("/{engagement_id}/roadmap")
def list_roadmap_items(
    engagement_id: str,
    repo: RoadmapRepository = Depends(get_repo)
):
    """Return all roadmap items for an engagement ordered by phase and priority."""
    return repo.get_all(engagement_id)


@router.post("/{engagement_id}/roadmap/parse-synthesizer")
async def parse_synthesizer_roadmap(
    engagement_id: str,
    agent_repo:    AgentRunRepository = Depends(get_agent_repo),
    finding_repo:  FindingRepository  = Depends(get_finding_repo),
):
    """Extract structured roadmap candidates from the accepted Synthesizer output.
    Returns candidates array held in frontend state — nothing is persisted until
    the user loads approved items via POST /{engagement_id}/roadmap."""
    from api.services.claude import extract_roadmap_from_synthesizer

    synthesizer_output = agent_repo.get_accepted_output(engagement_id, 'Synthesizer')
    if not synthesizer_output:
        raise HTTPException(
            status_code=400,
            detail="Synthesizer agent must be accepted before parsing roadmap"
        )
    if len(synthesizer_output) < 100:
        raise HTTPException(
            status_code=400,
            detail=f"Synthesizer output is too short ({len(synthesizer_output)} chars) — "
                   f"re-run and accept the Synthesizer agent."
        )

    findings = finding_repo.get_all(engagement_id)

    raw = await extract_roadmap_from_synthesizer(synthesizer_output, findings)

    try:
        candidates = json_lib.loads(raw)
    except json_lib.JSONDecodeError:
        logger.error(f"Claude returned invalid JSON for roadmap extraction: {raw[:200]}")
        raise HTTPException(
            status_code=500,
            detail="Claude returned invalid JSON — try again"
        )

    # Build set of valid finding IDs for addressing_finding_ids validation
    valid_finding_ids = {f['finding_id'] for f in findings if f.get('finding_id')}

    cleaned = []
    for item in candidates:
        if item.get('domain') not in VALID_DOMAINS:
            item['domain'] = DEFAULT_DOMAIN
        if item.get('phase') not in VALID_PHASES:
            item['phase'] = 'Stabilize'
        if item.get('priority') not in VALID_PRIORITIES:
            item['priority'] = 'Medium'
        if item.get('effort') not in VALID_EFFORTS:
            item['effort'] = 'Medium'
        if not isinstance(item.get('capability'), str):
            item['capability'] = ''
        # Validate addressing_finding_ids — keep only IDs that exist in this engagement
        raw_fids = item.get('addressing_finding_ids')
        if isinstance(raw_fids, list):
            valid_fids = [fid for fid in raw_fids if fid in valid_finding_ids]
            item['addressing_finding_ids'] = json_lib.dumps(valid_fids)
        else:
            item['addressing_finding_ids'] = json_lib.dumps([])
        cleaned.append(item)

    logger.info(f"parse-synthesizer roadmap: {len(cleaned)} candidates for {engagement_id}")
    return {'candidates': cleaned}


@router.get("/{engagement_id}/roadmap/{phase}")
def list_roadmap_by_phase(
    engagement_id: str,
    phase:         str,
    repo:          RoadmapRepository = Depends(get_repo)
):
    """Return roadmap items for a specific phase.
    Phase values: Stabilize, Optimize, Scale"""
    if phase not in ('Stabilize', 'Optimize', 'Scale'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase: {phase}. Must be Stabilize, Optimize, or Scale"
        )
    return repo.get_by_phase(engagement_id, phase)


@router.post("/{engagement_id}/roadmap",
             response_model=RoadmapItemResponse,
             status_code=201)
def create_roadmap_item(
    engagement_id: str,
    data:          RoadmapItemCreate,
    repo:          RoadmapRepository = Depends(get_repo)
):
    """Create a roadmap item."""
    item_id = repo.create(engagement_id, data.model_dump())
    items   = repo.get_all(engagement_id)
    item    = next((i for i in items if i['item_id'] == item_id), None)
    if not item:
        raise HTTPException(status_code=500, detail="Roadmap item created but could not be retrieved")
    return item


@router.patch("/{engagement_id}/roadmap/{item_id}")
def update_roadmap_item(
    engagement_id: str,
    item_id:       str,
    data:          dict,
    repo:          RoadmapRepository = Depends(get_repo)
):
    """Update a roadmap item."""
    items = repo.get_all(engagement_id)
    if not any(i['item_id'] == item_id for i in items):
        raise HTTPException(status_code=404, detail="Roadmap item not found")
    repo.update(item_id, engagement_id, data)
    items = repo.get_all(engagement_id)
    return next(i for i in items if i['item_id'] == item_id)


@router.delete("/{engagement_id}/roadmap/{item_id}", status_code=204)
def delete_roadmap_item(
    engagement_id: str,
    item_id:       str,
    repo:          RoadmapRepository = Depends(get_repo)
):
    """Delete a roadmap item."""
    items = repo.get_all(engagement_id)
    if not any(i['item_id'] == item_id for i in items):
        raise HTTPException(status_code=404, detail="Roadmap item not found")
    repo.delete(item_id, engagement_id)
