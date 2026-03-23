import json
import logging
from datetime import date
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.pattern import PatternRepository
from api.db.repositories.signal import SignalRepository
from api.models.pattern import (PatternDetectionResult, PatternUpdate,
                                EngagementPatternResponse)

logger = logging.getLogger(__name__)

router = APIRouter()

LOG_PREVIEW_LENGTH = 80


def get_pattern_repo() -> PatternRepository:
    return PatternRepository()


def get_signal_repo() -> SignalRepository:
    return SignalRepository()


@router.get("/{engagement_id}/patterns",
            response_model=list[EngagementPatternResponse])
def list_patterns(
    engagement_id: str,
    repo: PatternRepository = Depends(get_pattern_repo)
):
    """Return all detected patterns for an engagement."""
    return repo.get_for_engagement(engagement_id)


@router.post("/{engagement_id}/patterns/detect")
async def detect_patterns(
    engagement_id: str,
    pattern_repo: PatternRepository = Depends(get_pattern_repo),
    signal_repo:  SignalRepository  = Depends(get_signal_repo)
):
    """Run pattern detection via Claude API.
    Returns validated JSON results for consultant review before loading."""
    from api.services.claude import call_claude, PATTERN_DETECTION_PROMPT
    from api.services.case_packet import CasePacketService

    signals = signal_repo.get_for_engagement(engagement_id)
    if len(signals) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Pattern detection requires at least 10 signals. Found: {len(signals)}"
        )

    case_packet = CasePacketService(engagement_id).assemble_signals_only()

    next_ep = pattern_repo.get_next_ep_id(engagement_id)
    prompt  = PATTERN_DETECTION_PROMPT.replace('[NEXT_EP_ID]', next_ep)
    prompt  = prompt.replace('[ENGAGEMENT_ID]', engagement_id)

    raw = await call_claude(case_packet, [], prompt)

    try:
        raw_list = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"Claude returned invalid JSON for pattern detection: {raw[:LOG_PREVIEW_LENGTH]}")
        raise HTTPException(status_code=422, detail="Claude did not return valid JSON")

    try:
        results = [PatternDetectionResult(**item) for item in raw_list]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Pattern validation failed: {str(e)}")

    library_ids = {p['pattern_id'] for p in pattern_repo.get_library()}
    invalid     = [r.pattern_id for r in results if r.pattern_id not in library_ids]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unknown pattern_ids: {invalid}")

    return [r.model_dump() for r in results]


@router.post("/{engagement_id}/patterns/load", status_code=201)
def load_patterns(
    engagement_id: str,
    patterns: list[PatternDetectionResult],
    repo: PatternRepository = Depends(get_pattern_repo)
):
    """Load validated pattern detection results into the database."""
    rows = [
        {
            'engagement_id': engagement_id,
            'pattern_id':    p.pattern_id,
            'confidence':    p.confidence,
            'notes':         p.notes or ''
        }
        for p in patterns
    ]
    count = repo.bulk_create(rows)
    return {'patterns_loaded': count}


@router.patch("/{engagement_id}/patterns/{ep_id}")
def update_pattern(
    engagement_id: str,
    ep_id:         str,
    data:          PatternUpdate,
    repo:          PatternRepository = Depends(get_pattern_repo)
):
    """Update confidence or economic estimate on an engagement pattern."""
    if data.economic_impact_est is not None:
        repo.update_economic_estimate(ep_id, data.economic_impact_est)
    return {"updated": ep_id}
