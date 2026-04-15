import os
import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.signal import SignalRepository
from api.db.repositories.processed_files import ProcessedFilesRepository
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
    """Load approved candidates into the Signals table and archive candidate files.
    Expects: {candidates: [...], merged_candidate_file: str (optional)}"""
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
            'source_file':        signal.get('source_file'),
            'library_signal_id':  signal.get('library_signal_id'),
        }
        repo.create(signal_payload)
        loaded += 1

    # Write SignalCoverage gaps from not_observed in the merged candidate file — non-fatal
    merged_file = payload.get('merged_candidate_file')
    if merged_file and os.path.exists(merged_file):
        try:
            import json as _json
            from api.db.repositories.signal_coverage import SignalCoverageRepository
            with open(merged_file, 'r', encoding='utf-8') as _f:
                merged_data = _json.load(_f)
            not_observed = merged_data.get('not_observed', [])
            if not_observed:
                coverage_repo = SignalCoverageRepository()
                source_file = os.path.basename(merged_file)
                coverage_repo.delete_for_engagement(engagement_id)
                coverage_rows = [
                    {'engagement_id': engagement_id, 'signal_id': sid, 'source_file': source_file}
                    for sid in not_observed
                ]
                written = coverage_repo.bulk_create(coverage_rows)
                logger.info(f"Wrote {written} SignalCoverage rows for {engagement_id}")
        except Exception as _e:
            logger.warning(f"SignalCoverage write failed (non-fatal): {_e}")

    # Archive candidate files — non-fatal if it fails
    if merged_file:
        from api.services.document_processor import archive_candidate_files
        candidates_folder = os.path.dirname(merged_file)
        archive_candidate_files(engagement_id, candidates_folder, merged_file)

    return {'signals_loaded': loaded}


@router.get("/{engagement_id}/signals/coverage")
def list_coverage(engagement_id: str):
    """Return Tier 1 library signal gaps for an engagement.
    These are signals that were checked during extraction but not found in any file."""
    from api.db.repositories.signal_coverage import SignalCoverageRepository
    return SignalCoverageRepository().get_for_engagement(engagement_id)


@router.get("/{engagement_id}/signals/processed-files")
def list_processed_files(engagement_id: str):
    """Return all processed files for an engagement."""
    return ProcessedFilesRepository().get_for_engagement(engagement_id)


@router.delete("/{engagement_id}/signals/processed-files/{file_hash}", status_code=200)
def reprocess_file(
    engagement_id: str,
    file_hash: str,
    repo: SignalRepository = Depends(get_repo),
):
    """Delete signals loaded from a specific file and remove its ProcessedFiles record.
    The file will be treated as new on the next Process Files run.
    Uses a transaction — both deletes succeed or neither does."""
    pf_repo = ProcessedFilesRepository()
    record = pf_repo.get_by_hash(file_hash)
    if not record:
        raise HTTPException(status_code=404, detail="Processed file record not found")
    if record['engagement_id'] != engagement_id:
        raise HTTPException(status_code=403, detail="File does not belong to this engagement")

    file_name = record['file_name']

    from api.db.repositories.signal import DELETE_BY_SOURCE_FILE
    from api.db.repositories.processed_files import DELETE_BY_HASH

    pf_repo._write_transaction([
        (DELETE_BY_SOURCE_FILE, (engagement_id, file_name)),
        (DELETE_BY_HASH,        (file_hash,)),
    ])

    logger.info(f"Reprocess: removed signals and ProcessedFiles record for {file_name}")
    return {'file_name': file_name, 'status': 'ready_for_reprocess'}