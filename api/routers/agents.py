import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.agent_run import AgentRunRepository
from api.models.agent import AgentRunResponse, AgentRegistryEntry

logger = logging.getLogger(__name__)

router = APIRouter()


def get_repo() -> AgentRunRepository:
    return AgentRunRepository()


@router.get("/agents/registry")
def get_agent_registry():
    """Return the full agent registry — all five agents with sequence and prerequisites.

    Note: This endpoint is not engagement-specific but is registered under
    /api/engagements for simplicity. Full URL: /api/engagements/agents/registry.
    Moving to /api/agents/registry is a Phase 3 cosmetic fix.
    Do not move without also updating api.js agents.registry() call.
    """
    from api.services.claude import AGENT_REGISTRY
    return [
        {
            'name':                  key,
            'sequence':              entry['sequence'],
            'domain':                entry['domain'],
            'required_prior_agents': entry['required_prior_agents'],
        }
        for key, entry in sorted(
            AGENT_REGISTRY.items(),
            key=lambda x: x[1]['sequence']
        )
    ]


@router.get("/{engagement_id}/agents")
def list_agent_runs(
    engagement_id: str,
    repo: AgentRunRepository = Depends(get_repo)
):
    """Return all agent runs for an engagement in chronological order."""
    return repo.get_for_engagement(engagement_id)


@router.post("/{engagement_id}/agents/{agent_name}/run")
async def run_agent(
    engagement_id: str,
    agent_name:    str,
    repo:          AgentRunRepository = Depends(get_repo)
):
    """Execute an agent via Claude API.
    Validates prerequisites, assembles context, calls Claude, stores output.

    Stores full Claude output in output_full.
    Stores truncated summary (500 chars) in output_summary.
    Does not populate prompt_version — git tracks prompt history.
    """
    from api.services.claude import AGENT_REGISTRY, call_claude
    from api.services.case_packet import CasePacketService

    if agent_name not in AGENT_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent: {agent_name}. Valid agents: {list(AGENT_REGISTRY.keys())}"
        )

    agent = AGENT_REGISTRY[agent_name]

    missing = repo.validate_prerequisites(
        engagement_id,
        agent['required_prior_agents']
    )
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Prerequisites not met. Accept these agents first: {missing}"
        )

    case_packet   = CasePacketService(engagement_id).assemble()
    # Use get_prior_output() — returns output_full with consultant_correction
    # appended if one has been saved. get_accepted_output() is for prerequisite
    # validation only; this path builds the actual downstream agent context.
    prior_outputs = [
        repo.get_prior_output(engagement_id, required)
        for required in agent['required_prior_agents']
    ]

    logger.info(f"Running agent {agent_name} for engagement {engagement_id}")
    output = await call_claude(case_packet, prior_outputs, agent['prompt'])

    # Store full output in output_full, truncated summary in output_summary
    summary = output[:500] + '...' if len(output) > 500 else output

    run_id = repo.create({
        'engagement_id':  engagement_id,
        'agent_name':     agent_name,
        'output_full':    output,
        'output_summary': summary,
        'model_used':     'claude-sonnet-4-6',
    })

    logger.info(f"Agent {agent_name} run complete. run_id: {run_id}")
    return {'run_id': run_id, 'agent_name': agent_name, 'output': output}


@router.patch("/{engagement_id}/agents/{run_id}/accept")
def accept_agent_run(
    engagement_id: str,
    run_id:        str,
    repo:          AgentRunRepository = Depends(get_repo)
):
    """Accept an agent run. Sets accepted=1 and unlocks the next agent."""
    repo.accept(run_id)
    logger.info(f"Agent run accepted: {run_id}")
    return {'accepted': run_id}


@router.patch("/{engagement_id}/agents/{run_id}/reject")
def reject_agent_run(
    engagement_id: str,
    run_id:        str,
    repo:          AgentRunRepository = Depends(get_repo)
):
    """Reject an agent run. Allows the agent to be re-run."""
    repo.reject(run_id)
    logger.info(f"Agent run rejected: {run_id}")
    return {'rejected': run_id}


@router.patch("/{engagement_id}/agents/{run_id}/correction")
def update_agent_correction(
    engagement_id: str,
    run_id:        str,
    data:          dict,
    repo:          AgentRunRepository = Depends(get_repo)
):
    """Save or clear the consultant correction on an accepted agent run.

    The correction is appended to this agent's output when it is passed as
    prior context to downstream agents via get_prior_output(). It does not
    modify the stored output_full — the original Claude response is preserved.
    Pass empty string to clear an existing correction.
    """
    correction = data.get('consultant_correction', '')
    repo.update_correction(run_id, correction)
    logger.info(f"Correction updated for run: {run_id} — {len(correction or '')} chars")
    return {'updated': run_id}