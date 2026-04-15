import asyncio
import json as json_lib
import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.finding import FindingRepository
from api.db.repositories.agent_run import AgentRunRepository
from api.db.repositories.pattern import PatternRepository
from api.db.repositories.signal import SignalRepository
from api.db.repositories.engagement import EngagementRepository
from api.models.finding import FindingCreate, FindingUpdate, FindingResponse
from api.utils.domains import DEFAULT_DOMAIN, VALID_DOMAINS, VALID_FINDING_CONFIDENCES, VALID_PRIORITIES, VALID_EFFORTS
from api.services.report_generator import _prepopulate_display_figure
from api.services.report_sections import (
    _parse_economic_figures, _format_display_figure, _parse_display_figure_to_float,
)
from api.services.claude import suggest_display_label

logger = logging.getLogger(__name__)

router = APIRouter()


_ANNUAL_DRAG_DOMAINS = frozenset({
    'Consulting Economics', 'Finance and Commercial',
    'Resource Management', 'Human Resources',
})


def _suggest_economic_figures(economic_impact: str, domain: str,
                               confirmed_rev: float | None) -> dict:
    """Suggest confirmed_figure, derived_figure, annual_drag_figure from
    economic_impact text. Returns dict with three suggested_* keys.
    Values are None when no parseable figure exists or field not applicable.
    Prepends ⚠ prefix if suggested value exceeds confirmed_rev."""
    conf_str, deriv_str, _ = _parse_economic_figures(economic_impact)

    def _build(raw_str: str):
        if raw_str == '\u2014':
            return None
        raw = raw_str.split(', ')[0]
        fmt = _format_display_figure(raw)
        if confirmed_rev is not None:
            val = _parse_display_figure_to_float(fmt)
            if val is not None and val > confirmed_rev:
                fmt = f'\u26a0 {fmt}'
        return fmt

    suggested_confirmed = _build(conf_str)
    suggested_derived   = _build(deriv_str)

    if domain in _ANNUAL_DRAG_DOMAINS:
        drag_str = deriv_str if deriv_str != '\u2014' else conf_str
        suggested_annual_drag = _build(drag_str)
    else:
        suggested_annual_drag = None

    return {
        'suggested_confirmed_figure':   suggested_confirmed,
        'suggested_derived_figure':     suggested_derived,
        'suggested_annual_drag_figure': suggested_annual_drag,
    }


def get_finding_repo() -> FindingRepository:
    return FindingRepository()


def get_agent_repo() -> AgentRunRepository:
    return AgentRunRepository()


def get_pattern_repo() -> PatternRepository:
    return PatternRepository()


def get_signal_repo() -> SignalRepository:
    return SignalRepository()


def get_engagement_repo() -> EngagementRepository:
    return EngagementRepository()


def _compute_evidence_summary(contributing_ep_ids: list, accepted_patterns: list,
                               domain: str, domain_signal_counts: dict) -> str:
    """Build a 1-line evidence summary for a finding.

    Format: "Supported by P06, P08 across Sales-to-Delivery Transition;
             6 signals (4 confirmed, 2 inferred)"

    confirmed = High confidence signals in domain
    inferred  = Medium + Hypothesis signals in domain
    """
    # Resolve contributing EP IDs to pattern IDs
    ep_to_pattern = {p['ep_id']: p['pattern_id'] for p in accepted_patterns}
    pattern_ids = sorted({
        ep_to_pattern[ep_id]
        for ep_id in contributing_ep_ids
        if ep_id in ep_to_pattern
    })

    # Signal counts for this domain
    counts = domain_signal_counts.get(domain, {})
    confirmed = counts.get('High', 0)
    inferred  = counts.get('Medium', 0) + counts.get('Hypothesis', 0)
    total     = confirmed + inferred

    pattern_str = ', '.join(pattern_ids) if pattern_ids else '(none)'
    if total > 0:
        signal_str = f"{total} signal{'s' if total != 1 else ''} ({confirmed} confirmed, {inferred} inferred)"
    else:
        signal_str = "no signals recorded"

    return f"Supported by {pattern_str} across {domain}; {signal_str}"


def _derive_confidence(contributing_ep_ids: list, accepted_patterns: list) -> str:
    """Derive finding confidence from contributing pattern confidence levels.

    High   = all supporting patterns are High
    Medium = mixed or all Medium
    Low    = any supporting pattern is Hypothesis
    """
    ep_to_confidence = {p['ep_id']: p.get('confidence', 'Medium') for p in accepted_patterns}
    confidences = [
        ep_to_confidence[ep_id]
        for ep_id in contributing_ep_ids
        if ep_id in ep_to_confidence
    ]
    if not confidences:
        return 'Medium'
    if any(c == 'Hypothesis' for c in confidences):
        return 'Low'
    if all(c == 'High' for c in confidences):
        return 'High'
    return 'Medium'


@router.get("/{engagement_id}/findings")
async def list_findings(
    engagement_id: str,
    repo:     FindingRepository    = Depends(get_finding_repo),
    eng_repo: EngagementRepository = Depends(get_engagement_repo),
):
    """Return all findings for an engagement in priority order.
    For findings where display_figure is NULL, compute figure/type suggestions
    synchronously then fire parallel Claude calls to generate contextual labels.
    Suggestions are never written to the database."""
    rows          = repo.get_all(engagement_id)
    engagement    = eng_repo.get_by_id(engagement_id)
    confirmed_rev = (engagement or {}).get('confirmed_revenue')

    # Phase 1: synchronous figure/type pre-population
    enriched     = []
    label_indices = []   # positions in enriched that need a Claude label call
    for f in rows:
        row = dict(f)
        if row.get('display_figure') is None:
            clean_fig = row.get('suggested_figure')  # may not exist yet
            fig, _, ftype = _prepopulate_display_figure(
                row.get('economic_impact') or '',
                row.get('domain') or '',
                confirmed_rev,
                None,   # title-based label skipped — Claude generates it below
            )
            row['suggested_figure']      = fig
            row['suggested_label']       = None   # filled in Phase 2
            row['suggested_figure_type'] = ftype
            if fig is not None:
                label_indices.append(len(enriched))
        else:
            row['suggested_figure']      = None
            row['suggested_label']       = None
            row['suggested_figure_type'] = None

        # Economic figure suggestions — one parse per row, mask stored fields
        suggestions = _suggest_economic_figures(
            row.get('economic_impact') or '',
            row.get('domain') or '',
            confirmed_rev,
        )
        row['suggested_confirmed_figure']   = (suggestions['suggested_confirmed_figure']
                                                if row.get('confirmed_figure')   is None else None)
        row['suggested_derived_figure']     = (suggestions['suggested_derived_figure']
                                                if row.get('derived_figure')     is None else None)
        row['suggested_annual_drag_figure'] = (suggestions['suggested_annual_drag_figure']
                                                if row.get('annual_drag_figure') is None else None)

        enriched.append(row)

    # Phase 2: parallel Claude calls for labels
    if label_indices:
        tasks = []
        for i in label_indices:
            row = enriched[i]
            # Strip warning prefix before sending to Claude
            raw_fig = row['suggested_figure']
            clean   = raw_fig[2:] if raw_fig and raw_fig.startswith('\u26a0 ') else raw_fig
            tasks.append(suggest_display_label(
                row.get('finding_title') or '',
                row.get('economic_impact') or '',
                clean or '',
            ))
        labels = await asyncio.gather(*tasks)
        for i, label in zip(label_indices, labels):
            enriched[i]['suggested_label'] = label

    return enriched


@router.post("/{engagement_id}/findings",
             response_model=FindingResponse,
             status_code=201)
def create_finding(
    engagement_id: str,
    data:          FindingCreate,
    finding_repo:  FindingRepository  = Depends(get_finding_repo),
    agent_repo:    AgentRunRepository = Depends(get_agent_repo),
    pattern_repo:  PatternRepository  = Depends(get_pattern_repo),
    signal_repo:   SignalRepository   = Depends(get_signal_repo),
):
    """Create a finding and accept contributing patterns atomically.
    Requires Synthesizer accepted. Requires at least one contributing pattern.
    Computes evidence_summary server-side at creation time."""
    synthesizer = agent_repo.get_accepted_output(engagement_id, 'Synthesizer')
    if not synthesizer:
        raise HTTPException(
            status_code=400,
            detail="Synthesizer agent must be accepted before creating findings"
        )

    payload = data.model_dump()
    contributing_ep_ids = payload.pop('contributing_ep_ids', [])

    if not contributing_ep_ids:
        raise HTTPException(
            status_code=422,
            detail="At least one contributing pattern must be selected. "
                   "Every finding must be supported by at least one accepted pattern."
        )

    # Compute evidence_summary unless already provided (Parse Findings flow passes it through)
    if not payload.get('evidence_summary'):
        # Use all loaded patterns — accepted=1 is set atomically when findings are created,
        # so at first finding creation time accepted_patterns would otherwise be empty.
        accepted_patterns = pattern_repo.get_for_engagement(engagement_id)

        domain_summary_rows = signal_repo.get_domain_summary(engagement_id)
        domain_signal_counts: dict = {}
        for row in domain_summary_rows:
            d = row['domain']
            if d not in domain_signal_counts:
                domain_signal_counts[d] = {}
            domain_signal_counts[d][row['signal_confidence']] = row['signal_count']

        payload['evidence_summary'] = _compute_evidence_summary(
            contributing_ep_ids, accepted_patterns,
            payload.get('domain', ''), domain_signal_counts
        )

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
    signal_repo:    SignalRepository   = Depends(get_signal_repo),
):
    """Extract structured finding candidates from the accepted Synthesizer output.
    Returns candidates array held in frontend state — nothing is persisted until
    the user loads approved findings via POST /{engagement_id}/findings.

    Each candidate includes:
    - suggested_pattern_ids (P-IDs) for the contributing patterns checklist
    - key_quotes selected verbatim from domain signal notes by Claude
    - confidence derived from contributing pattern confidence levels (backend)
    - evidence_summary computed from pattern IDs and domain signal counts (backend)
    """
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

    # Use all loaded patterns — accepted=1 is set atomically when findings are created,
    # so at parse time (before any findings exist) accepted_patterns would otherwise be empty.
    accepted_patterns = pattern_repo.get_for_engagement(engagement_id)

    # Build signals_by_domain for key quote selection
    all_signals = signal_repo.get_for_engagement(engagement_id)
    signals_by_domain: dict = {}
    for s in all_signals:
        domain = s.get('domain', '')
        notes  = (s.get('notes') or '').strip()
        if domain and notes:
            signals_by_domain.setdefault(domain, []).append(notes)

    # Build domain signal counts for evidence summary computation
    domain_summary_rows = signal_repo.get_domain_summary(engagement_id)
    domain_signal_counts: dict = {}
    for row in domain_summary_rows:
        d = row['domain']
        if d not in domain_signal_counts:
            domain_signal_counts[d] = {}
        domain_signal_counts[d][row['signal_confidence']] = row['signal_count']

    raw = await extract_findings_from_synthesizer(
        synthesizer_output, accepted_patterns, signals_by_domain
    )

    try:
        candidates = json_lib.loads(raw)
    except json_lib.JSONDecodeError:
        logger.error(f"Claude returned invalid JSON for findings extraction: {raw[:200]}")
        raise HTTPException(
            status_code=500,
            detail="Claude returned invalid JSON — try again"
        )

    # EP ID lookup for pattern resolution
    pid_to_ep  = {p['pattern_id']: p['ep_id'] for p in accepted_patterns}
    ep_by_epid = {p['ep_id']: p for p in accepted_patterns}

    cleaned = []
    for item in candidates:
        if item.get('domain') not in VALID_DOMAINS:
            item['domain'] = DEFAULT_DOMAIN
        if item.get('priority') not in VALID_PRIORITIES:
            item['priority'] = 'High'
        if item.get('effort') not in VALID_EFFORTS:
            item['effort'] = 'Medium'
        if not isinstance(item.get('opd_section'), int) or not (1 <= item['opd_section'] <= 9):
            item['opd_section'] = 4
        if not isinstance(item.get('suggested_pattern_ids'), list):
            item['suggested_pattern_ids'] = []
        if not isinstance(item.get('key_quotes'), list):
            item['key_quotes'] = []

        # Resolve suggested P-IDs to EP IDs for contributing patterns checklist
        ep_ids = [
            pid_to_ep[pid]
            for pid in item['suggested_pattern_ids']
            if pid in pid_to_ep
        ]

        # Derive confidence from contributing pattern confidence levels (deterministic)
        item['confidence'] = _derive_confidence(ep_ids, accepted_patterns)
        if item['confidence'] not in VALID_FINDING_CONFIDENCES:
            item['confidence'] = 'Medium'

        # Compute evidence summary so it's visible on the candidate review card
        item['evidence_summary'] = _compute_evidence_summary(
            ep_ids, accepted_patterns,
            item['domain'], domain_signal_counts
        )

        # Serialise key_quotes to JSON string for storage
        item['key_quotes'] = json_lib.dumps(item['key_quotes'])

        cleaned.append(item)

    logger.info(f"parse-synthesizer: {len(cleaned)} candidates for {engagement_id}")
    return {'candidates': cleaned}