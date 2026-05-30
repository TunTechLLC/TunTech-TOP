"""QA-3 Editorial Check Agent — router.

Split implementation: deterministic Python checks via editorial_auditor.py
plus a focused Claude voice/audience check via detect_editorial_voice.

The run endpoint orchestrates Python first (cheap, fast, deterministic),
then Claude (network-bound, more expensive), then combines results and
persists. Each item carries a `source` field ('python' or 'claude') so the
UI can surface which pipeline produced it.

Endpoints:
    POST   /{engagement_id}/qa-editorial/run            — run both pipelines, replace items
    GET    /{engagement_id}/qa-editorial                — list items grouped by tier
    PATCH  /{engagement_id}/qa-editorial/{qa_editorial_id} — update status
    POST   /{engagement_id}/qa-editorial/confirm-tier-1 — batch accept pending Tier 1
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

from api.db.repositories.qa_editorial import QAEditorialRepository
from api.models.qa_editorial import QAEditorialUpdate
from api.services.qa_inputs import read_v1_roadmap_text
from api.services.editorial_auditor import run_editorial_python_checks
from api.services.claude import detect_editorial_voice

logger = logging.getLogger(__name__)

router = APIRouter()


def get_qa_editorial_repo() -> QAEditorialRepository:
    return QAEditorialRepository()


@router.post("/{engagement_id}/qa-editorial/run")
async def run_qa_editorial(
    engagement_id: str,
    repo: QAEditorialRepository = Depends(get_qa_editorial_repo),
):
    """Run QA-3 Editorial Check (Python mechanical + Claude voice).

    Python checks run first (deterministic, near-instant). Claude voice
    check runs second (network call). Items from both pipelines are combined
    and stored. Re-runs replace previous items.

    Returns a summary with counts by tier, by source, and by category.
    """
    logger.info(f"QA-3 run started for {engagement_id}")

    try:
        roadmap_v1_text = read_v1_roadmap_text(engagement_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Python pipeline first — fast, deterministic, always succeeds
    python_items = run_editorial_python_checks(roadmap_v1_text)
    logger.info(f"QA-3 Python pipeline: {len(python_items)} items")

    # Claude voice/audience pipeline — network call
    claude_items = await detect_editorial_voice(roadmap_v1_text)
    logger.info(f"QA-3 Claude pipeline: {len(claude_items)} items")

    items = python_items + claude_items
    repo.delete_for_engagement(engagement_id)
    count = repo.bulk_create(engagement_id, items)

    by_tier = {1: 0, 2: 0, 3: 0}
    by_source = {'python': 0, 'claude': 0}
    by_category = {}
    for item in items:
        by_tier[item['tier']] += 1
        by_source[item['source']] += 1
        by_category[item['category']] = by_category.get(item['category'], 0) + 1

    logger.info(
        f"QA-3 run completed for {engagement_id}: {count} items "
        f"(T1: {by_tier[1]}, T2: {by_tier[2]}, T3: {by_tier[3]}; "
        f"Python: {by_source['python']}, Claude: {by_source['claude']})"
    )

    return {
        "engagement_id": engagement_id,
        "items_count":   count,
        "by_tier":       by_tier,
        "by_source":     by_source,
        "by_category":   by_category,
    }


@router.get("/{engagement_id}/qa-editorial")
def list_qa_editorial(
    engagement_id: str,
    repo: QAEditorialRepository = Depends(get_qa_editorial_repo),
):
    """Return all QA editorial items for an engagement, ordered by tier."""
    return repo.get_for_engagement(engagement_id)


@router.patch("/{engagement_id}/qa-editorial/{qa_editorial_id}")
def update_qa_editorial(
    engagement_id:   str,
    qa_editorial_id: str,
    data:            QAEditorialUpdate,
    repo:            QAEditorialRepository = Depends(get_qa_editorial_repo),
):
    """Update an item's status — pending / accepted / rejected."""
    repo.update_status(qa_editorial_id, data.status)
    return {"updated": qa_editorial_id, "status": data.status}


@router.post("/{engagement_id}/qa-editorial/confirm-tier-1")
def confirm_tier_1(
    engagement_id: str,
    repo:          QAEditorialRepository = Depends(get_qa_editorial_repo),
):
    """Batch-accept all pending Tier 1 editorial items.
    Rejected items left unchanged."""
    count = repo.batch_accept_tier_1(engagement_id)
    logger.info(f"QA-3 Tier 1 confirmation: {count} items accepted for {engagement_id}")
    return {"updated": count}
