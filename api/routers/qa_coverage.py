"""QA-1 Coverage Check Agent — router.

Endpoints (all engagement-scoped, mounted under /api/engagements):
    POST   /{engagement_id}/qa-coverage/run            — run detection, replace items
    GET    /{engagement_id}/qa-coverage                — list items grouped by tier
    PATCH  /{engagement_id}/qa-coverage/{qa_coverage_id} — update item status
    POST   /{engagement_id}/qa-coverage/confirm-tier-1 — batch accept all pending Tier 1

The run endpoint is async — calls Opus via detect_coverage_gaps. Re-runs replace
previous results (the consultant reviews the new tiered list from scratch).
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from api.db.repositories.qa_coverage import QACoverageRepository
from api.models.qa_coverage import QACoverageUpdate
from api.services.qa_inputs import (
    read_v1_roadmap_text,
    assemble_source_documents_block,
)
from api.services.claude import detect_coverage_gaps

logger = logging.getLogger(__name__)

router = APIRouter()


def get_qa_coverage_repo() -> QACoverageRepository:
    return QACoverageRepository()


@router.post("/{engagement_id}/qa-coverage/run")
async def run_qa_coverage(
    engagement_id: str,
    repo: QACoverageRepository = Depends(get_qa_coverage_repo),
):
    """Run QA-1 Coverage Check against the v1 roadmap and source documents.

    Replaces any existing coverage items for the engagement — re-detection
    starts fresh, and the consultant reviews the new tiered list (Tier 1
    confirmation resets on each run, per the locked architectural decision).

    Returns a summary with counts by tier and total items inserted.
    """
    logger.info(f"QA-1 run started for {engagement_id}")

    try:
        roadmap_v1_text = read_v1_roadmap_text(engagement_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        source_block = assemble_source_documents_block(engagement_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        items = await detect_coverage_gaps(source_block, roadmap_v1_text)
    except Exception as exc:
        logger.error(f"QA-1 coverage check failed for {engagement_id}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Coverage check failed (invalid model response) — try again",
        )

    # Re-detection replaces — delete then bulk insert
    repo.delete_for_engagement(engagement_id)
    count = repo.bulk_create(engagement_id, items)

    by_tier = {1: 0, 2: 0, 3: 0}
    for item in items:
        by_tier[item['tier']] += 1

    logger.info(
        f"QA-1 run completed for {engagement_id}: {count} items "
        f"(T1: {by_tier[1]}, T2: {by_tier[2]}, T3: {by_tier[3]})"
    )

    return {
        "engagement_id": engagement_id,
        "items_count":   count,
        "by_tier":       by_tier,
    }


@router.get("/{engagement_id}/qa-coverage")
def list_qa_coverage(
    engagement_id: str,
    repo: QACoverageRepository = Depends(get_qa_coverage_repo),
):
    """Return all QA coverage items for an engagement, ordered by tier
    then qa_coverage_id."""
    return repo.get_for_engagement(engagement_id)


@router.patch("/{engagement_id}/qa-coverage/{qa_coverage_id}")
def update_qa_coverage(
    engagement_id:  str,
    qa_coverage_id: str,
    data:           QACoverageUpdate,
    repo:           QACoverageRepository = Depends(get_qa_coverage_repo),
):
    """Update an item's status. Validated to one of pending/accepted/rejected."""
    repo.update_status(qa_coverage_id, data.status)
    return {"updated": qa_coverage_id, "status": data.status}


@router.post("/{engagement_id}/qa-coverage/confirm-tier-1")
def confirm_tier_1(
    engagement_id: str,
    repo:          QACoverageRepository = Depends(get_qa_coverage_repo),
):
    """Mark all pending Tier 1 items as accepted — the batch confirmation gate.

    Items already explicitly rejected by the consultant are left unchanged.
    This is what the 'Confirm Tier 1 — proceed' button calls before QA-4
    can run. Returns the count of items moved from pending to accepted.
    """
    count = repo.batch_accept_tier_1(engagement_id)
    logger.info(f"QA-1 Tier 1 confirmation: {count} items accepted for {engagement_id}")
    return {"updated": count}
