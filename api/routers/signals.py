import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.signal import SignalRepository
from api.models.signal import SignalCreate, SignalResponse, DomainSummaryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_repo() -> SignalRepository:
    return SignalRepository()


@router.get("/{engagement_id}/signals", response_model=list[SignalResponse])
def list_signals(
    engagement_id: str,
    repo: SignalRepository = Depends(get_repo)
):
    """Return all signals for an engagement grouped by domain."""
    return repo.get_for_engagement(engagement_id)


@router.get("/{engagement_id}/signals/summary", response_model=list[DomainSummaryResponse])
def signal_domain_summary(
    engagement_id: str,
    repo: SignalRepository = Depends(get_repo)
):
    """Return signal counts grouped by domain and confidence."""
    return repo.get_domain_summary(engagement_id)


@router.post("/{engagement_id}/signals", response_model=SignalResponse, status_code=201)
def create_signal(
    engagement_id: str,
    data: SignalCreate,
    repo: SignalRepository = Depends(get_repo)
):
    """Add a single signal to an engagement."""
    payload = data.model_dump()
    payload['engagement_id'] = engagement_id
    signal_id = repo.create(payload)
    signals = repo.get_for_engagement(engagement_id)
    signal = next((s for s in signals if s['signal_id'] == signal_id), None)
    if not signal:
        raise HTTPException(status_code=500, detail="Signal created but could not be retrieved")
    return signal