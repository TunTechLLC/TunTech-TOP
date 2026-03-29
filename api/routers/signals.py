import os
import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.signal import SignalRepository
from api.models.signal import SignalCreate, SignalResponse, DomainSummaryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_repo() -> SignalRepository:
    return SignalRepository()


@router.get("/{engagement_id}/signals")
def list_signals(
    engagement_id: str,
    repo: SignalRepository = Depends(get_repo)
):
    """Return all signals for an engagement grouped by domain."""
    return repo.get_for_engagement(engagement_id)


@router.get("/{engagement_id}/signals/summary")
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
    if not payload.get('interview_id'):
        payload['interview_id'] = None
    signal_id = repo.create(payload)
    signals = repo.get_for_engagement(engagement_id)
    signal = next((s for s in signals if s['signal_id'] == signal_id), None)
    if not signal:
        raise HTTPException(status_code=500, detail="Signal created but could not be retrieved")
    return signal


@router.post("/{engagement_id}/signals/process-files")
async def process_files(
    engagement_id: str,
    repo: SignalRepository = Depends(get_repo)
):
    """Scan engagement folders for unprocessed files and extract signals via Claude.
    Writes candidate JSON files to the candidates folder.
    Returns summary of what was processed including all candidate file paths."""
    from api.db.repositories.engagement import EngagementRepository
    from api.services.document_processor import process_engagement_files

    eng = EngagementRepository().get_by_id(engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    interviews_folder = eng.get('interviews_folder') or ''
    documents_folder  = eng.get('documents_folder')  or ''
    candidates_folder = eng.get('candidates_folder')  or ''

    if not candidates_folder:
        raise HTTPException(
            status_code=400,
            detail="Candidates folder not set. Update engagement settings first."
        )

    result = await process_engagement_files(
        engagement_id,
        interviews_folder,
        documents_folder,
        candidates_folder,
    )
    return result


@router.get("/{engagement_id}/signals/read-candidates")
def read_candidates(
    engagement_id: str,
    file: str
):
    """Read a candidate JSON file and return its contents for browser review."""
    import json as json_lib
    if not file or not os.path.exists(file):
        raise HTTPException(status_code=404, detail="Candidate file not found")
    with open(file, 'r', encoding='utf-8') as f:
        return json_lib.load(f)


@router.post("/{engagement_id}/signals/load-candidates")
def load_candidates(
    engagement_id: str,
    payload: dict,
    repo: SignalRepository = Depends(get_repo)
):
    """Load approved candidates into the Signals table.
    Expects: {candidate_file, approved_indices, candidates}"""
    candidates = payload.get('candidates', [])

    if not candidates:
        raise HTTPException(status_code=400, detail="No candidates provided")

    loaded = 0
    for signal in candidates:
        signal_payload = {
            'engagement_id':      engagement_id,
            'signal_name':        signal.get('signal_name', ''),
            'domain':             signal.get('domain', ''),
            'observed_value':     signal.get('observed_value', ''),
            'normalized_band':    signal.get('normalized_band', ''),
            'signal_confidence':  signal.get('signal_confidence', 'Medium'),
            'source':             signal.get('source', 'Interview'),
            'interview_id':       None,
            'economic_relevance': signal.get('economic_relevance', ''),
            'notes':              signal.get('notes', ''),
        }
        repo.create(signal_payload)
        loaded += 1

    return {'signals_loaded': loaded}