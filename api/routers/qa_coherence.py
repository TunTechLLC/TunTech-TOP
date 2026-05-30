"""QA-2 Coherence Check Agent — router.

Endpoints (all engagement-scoped, mounted under /api/engagements):
    POST   /{engagement_id}/qa-coherence/run             — run detection, replace items
    GET    /{engagement_id}/qa-coherence                 — list items grouped by tier
    PATCH  /{engagement_id}/qa-coherence/{qa_coherence_id} — update item status
    POST   /{engagement_id}/qa-coherence/confirm-tier-1  — batch accept all pending Tier 1

Standalone read — input is only the v1 roadmap (no source documents). Re-runs
replace previous results, same as QA-1.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from api.db.repositories.qa_coherence import QACoherenceRepository
from api.models.qa_coherence import QACoherenceUpdate
from api.services.qa_inputs import read_v1_roadmap_text
from api.services.claude import detect_coherence_issues

logger = logging.getLogger(__name__)

router = APIRouter()


def get_qa_coherence_repo() -> QACoherenceRepository:
    return QACoherenceRepository()


@router.post("/{engagement_id}/qa-coherence/run")
async def run_qa_coherence(
    engagement_id: str,
    repo: QACoherenceRepository = Depends(get_qa_coherence_repo),
):
    """Run QA-2 Coherence Check against the v1 roadmap.

    Standalone close-read of the rendered document — no source materials
    needed. Replaces any existing coherence items for the engagement.
    Returns a summary with counts by tier and total items inserted.
    """
    logger.info(f"QA-2 run started for {engagement_id}")

    try:
        roadmap_v1_text = read_v1_roadmap_text(engagement_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    items = await detect_coherence_issues(roadmap_v1_text)

    repo.delete_for_engagement(engagement_id)
    count = repo.bulk_create(engagement_id, items)

    by_tier = {1: 0, 2: 0, 3: 0}
    by_category = {
        'contradiction': 0, 'priority_mismatch': 0,
        'weak_grounding': 0, 'missing_root_cause': 0,
    }
    for item in items:
        by_tier[item['tier']] += 1
        by_category[item['category']] += 1

    logger.info(
        f"QA-2 run completed for {engagement_id}: {count} items "
        f"(T1: {by_tier[1]}, T2: {by_tier[2]}, T3: {by_tier[3]})"
    )

    return {
        "engagement_id": engagement_id,
        "items_count":   count,
        "by_tier":       by_tier,
        "by_category":   by_category,
    }


@router.get("/{engagement_id}/qa-coherence")
def list_qa_coherence(
    engagement_id: str,
    repo: QACoherenceRepository = Depends(get_qa_coherence_repo),
):
    """Return all QA coherence items for an engagement, ordered by tier then id.
    sections_involved is returned as a parsed JSON array of strings."""
    return repo.get_for_engagement(engagement_id)


@router.patch("/{engagement_id}/qa-coherence/{qa_coherence_id}")
def update_qa_coherence(
    engagement_id:   str,
    qa_coherence_id: str,
    data:            QACoherenceUpdate,
    repo:            QACoherenceRepository = Depends(get_qa_coherence_repo),
):
    """Update an item's status — pending / accepted / rejected."""
    repo.update_status(qa_coherence_id, data.status)
    return {"updated": qa_coherence_id, "status": data.status}


@router.post("/{engagement_id}/qa-coherence/confirm-tier-1")
def confirm_tier_1(
    engagement_id: str,
    repo:          QACoherenceRepository = Depends(get_qa_coherence_repo),
):
    """Batch-accept all pending Tier 1 coherence items. Rejected items
    are left unchanged. Returns count of items moved to accepted."""
    count = repo.batch_accept_tier_1(engagement_id)
    logger.info(f"QA-2 Tier 1 confirmation: {count} items accepted for {engagement_id}")
    return {"updated": count}
