import logging
import re
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.agent_run import AgentRunRepository
from api.db.repositories.pattern import PatternRepository
from api.db.repositories.signal import SignalRepository
from api.models.agent import AgentRunResponse, AgentRegistryEntry
from config import MODEL

logger = logging.getLogger(__name__)

router = APIRouter()


def get_repo() -> AgentRunRepository:
    return AgentRunRepository()


def get_pattern_repo() -> PatternRepository:
    return PatternRepository()


def get_signal_repo() -> SignalRepository:
    return SignalRepository()


def _parse_c_codes(text: str) -> list:
    """Parse C-code blocks from Skeptic output using the prescribed labeled-field format.

    Returns [] if [NONE DETECTED] is present or no C-code blocks are found.
    Each entry contains: c_code_id, type, entity, signal_a_id, signal_b_id,
    signal_ids (flat list of valid S-codes for SignalPanel badge mapping),
    and full_text (complete block for inline display).
    """
    if '[NONE DETECTED]' in text:
        return []
    results = []
    parts = re.split(r'(?=\[C\d{3,}\])', text)
    for part in parts:
        c_id_match = re.match(r'\[C(\d+)\]', part.strip())
        if not c_id_match:
            continue
        c_id     = f"C{c_id_match.group(1).zfill(3)}"
        type_m   = re.search(r'^Type:\s*(\w+)',          part, re.MULTILINE)
        entity_m = re.search(r'^Entity:\s*(.+)',          part, re.MULTILINE)
        sig_a_m  = re.search(r'^Signal A:\s*\[(\w+)\]',  part, re.MULTILINE)
        sig_b_m  = re.search(r'^Signal B:\s*\[(\w+)\]',  part, re.MULTILINE)
        raw_a    = sig_a_m.group(1) if sig_a_m else None
        raw_b    = sig_b_m.group(1) if sig_b_m else None
        sig_a    = raw_a if raw_a and raw_a.lower() != 'none' else None
        sig_b    = raw_b if raw_b and raw_b.lower() != 'none' else None
        results.append({
            'c_code_id':   c_id,
            'type':        type_m.group(1).strip() if type_m else 'unknown',
            'entity':      entity_m.group(1).strip() if entity_m else None,
            'signal_a_id': sig_a,
            'signal_b_id': sig_b,
            'signal_ids':  list(dict.fromkeys(
                               s for s in [sig_a, sig_b]
                               if s and re.match(r'^S\d+$', s)
                           )),
            'full_text':   part.strip(),
        })
    return results


@router.get("/agents/registry")
def get_agent_registry():
    """Return the full agent registry — all five agents with sequence and prerequisites.

    Note: This endpoint is not engagement-specific but is registered under
    /api/engagements for simplicity. Full URL: /api/engagements/agents/registry.
    Moving to /api/agents/registry is a Phase 3 cosmetic fix.
    Do not move without also updating api.js agents.registry() call.
    """
    from api.services.prompts import AGENT_REGISTRY
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
    repo:        AgentRunRepository = Depends(get_repo),
    signal_repo: SignalRepository   = Depends(get_signal_repo),
):
    """Return all agent runs for an engagement in chronological order."""
    runs      = repo.get_for_engagement(engagement_id)
    valid_ids = signal_repo.get_ids_for_engagement(engagement_id)
    for run in runs:
        raw        = re.findall(r'\bS\d{3,4}\b', run.get('output_full') or '')
        referenced = list(dict.fromkeys(raw))
        run['referenced_signal_ids'] = referenced
        ghosts = [sid for sid in referenced if sid not in valid_ids]
        run['signal_warnings'] = ghosts
        if ghosts:
            logger.warning(
                f"Agent {run.get('agent_name')} run {run.get('run_id')} "
                f"references unknown signal IDs: {ghosts}"
            )
    return runs


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
    from api.services.prompts import AGENT_REGISTRY
    from api.services.claude import call_claude
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
        'model_used':     MODEL,
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


@router.get("/{engagement_id}/agents/skeptic/c-codes")
def get_skeptic_c_codes(
    engagement_id: str,
    repo:          AgentRunRepository = Depends(get_repo),
):
    """Parse C-code blocks from the accepted Skeptic run using regex.
    No Claude call — fast enough for auto-fetch on SignalPanel mount.
    Returns empty list when no accepted Skeptic run exists."""
    skeptic_output = repo.get_accepted_output(engagement_id, 'Skeptic')
    if not skeptic_output:
        return {'c_codes': [], 'none_detected': False}
    c_codes       = _parse_c_codes(skeptic_output)
    none_detected = '[NONE DETECTED]' in skeptic_output and len(c_codes) == 0
    return {'c_codes': c_codes, 'none_detected': none_detected}


@router.post("/{engagement_id}/agents/skeptic/parse-recommendations")
async def parse_skeptic_recommendations(
    engagement_id: str,
    agent_repo:    AgentRunRepository = Depends(get_repo),
    pattern_repo:  PatternRepository  = Depends(get_pattern_repo),
):
    """Parse Skeptic output for downgrade recommendations (Claude) and C-codes (regex).
    Returns {downgrades, c_codes}. Raises 404 if no accepted Skeptic run exists.
    Each downgrade includes in_engagement flag — False when the pattern was not
    detected for this engagement. Those cards are shown disabled in PatternPanel."""
    from api.services.claude import extract_downgrade_recommendations

    skeptic_output = agent_repo.get_accepted_output(engagement_id, 'Skeptic')
    if not skeptic_output:
        raise HTTPException(status_code=404,
                            detail="No accepted Skeptic run found for this engagement")

    c_codes        = _parse_c_codes(skeptic_output)
    raw_downgrades = await extract_downgrade_recommendations(skeptic_output)

    library        = pattern_repo.get_library()
    library_names  = {p['pattern_id']: p['pattern_name'] for p in library}
    eng_patterns   = pattern_repo.get_for_engagement(engagement_id)
    pattern_lookup = {p['pattern_id']: p for p in eng_patterns}

    downgrades = []
    for d in raw_downgrades:
        pid  = d['pattern_id']
        ep   = pattern_lookup.get(pid)
        name = library_names.get(pid, '')
        if ep:
            downgrades.append({
                'pattern_id':             pid,
                'pattern_name':           name or ep.get('pattern_name', ''),
                'ep_id':                  ep['ep_id'],
                'current_confidence':     ep['confidence'],
                'recommended_confidence': d['recommended_confidence'],
                'reason':                 d['reason'],
                'in_engagement':          True,
            })
        else:
            downgrades.append({
                'pattern_id':             pid,
                'pattern_name':           name,
                'ep_id':                  None,
                'current_confidence':     None,
                'recommended_confidence': d['recommended_confidence'],
                'reason':                 d['reason'],
                'in_engagement':          False,
            })

    logger.info(
        f"Skeptic parse for {engagement_id}: "
        f"{len(downgrades)} downgrade(s), {len(c_codes)} C-code(s)"
    )
    return {'downgrades': downgrades, 'c_codes': c_codes}