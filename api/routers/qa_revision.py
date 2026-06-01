"""QA-4 Revision Agent — router.

Endpoints (all engagement-scoped, mounted under /api/engagements):
    GET   /{engagement_id}/qa-status                      — v1/v2 doc existence (QA-5 gate)
    POST  /{engagement_id}/qa-revision/run                 — apply accepted QA items, write v2
    GET   /{engagement_id}/qa-revision                     — list the recorded edits (QA-5)
    GET   /{engagement_id}/qa-revision/v1                  — download the v1 .docx
    GET   /{engagement_id}/qa-revision/v2                  — download the v2 .docx
    PATCH /{engagement_id}/qa-revision/{qa_revision_id}    — update an edit's outcome (QA-5)

The run endpoint is async — it calls Opus via generate_revision_edits, applies
the edits to the v1 .docx in place, and saves v2 alongside it. Re-runs replace
the prior revision record.
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

from api.db.repositories.engagement import EngagementRepository
from api.db.repositories.qa_revision import QARevisionRepository
from api.models.qa_revision import QARevisionOutcomeUpdate
from api.services.qa_inputs import V1_FILENAME_TEMPLATE, V2_FILENAME_TEMPLATE
from api.services.qa_revision import QARevisionService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_qa_revision_repo() -> QARevisionRepository:
    return QARevisionRepository()


@router.get("/{engagement_id}/qa-status")
def qa_status(engagement_id: str):
    """Report whether the v1 (Report Generator) and v2 (Revision) roadmap
    documents exist on disk. Backs QA-5's tab gate — the QA stage cannot run
    until a v1 document exists. Pure file-existence check; no generation."""
    eng = EngagementRepository().get_by_id(engagement_id)
    if eng is None:
        raise HTTPException(status_code=404, detail=f"Engagement {engagement_id} not found")
    reports_folder = eng.get('reports_folder') or ''

    def _exists(template: str) -> bool:
        if not reports_folder:
            return False
        return os.path.exists(
            os.path.join(reports_folder, template.format(engagement_id=engagement_id))
        )

    return {
        "engagement_id": engagement_id,
        "v1_exists": _exists(V1_FILENAME_TEMPLATE),
        "v2_exists": _exists(V2_FILENAME_TEMPLATE),
    }


@router.post("/{engagement_id}/qa-revision/run")
async def run_qa_revision(engagement_id: str):
    """Apply all accepted QA items to the v1 roadmap and write v2.

    Requires: a v1 roadmap on disk (Report Generator has run) and at least one
    accepted Coverage/Coherence/Editorial item. Returns a summary with counts of
    applied / flagged / manual edits and the saved v2 path.
    """
    logger.info(f"QA-4 revision run started for {engagement_id}")
    try:
        result = await QARevisionService(engagement_id).run()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result


@router.get("/{engagement_id}/qa-revision")
def list_qa_revision(
    engagement_id: str,
    repo: QARevisionRepository = Depends(get_qa_revision_repo),
):
    """Return all recorded revision edits for an engagement (backs QA-5's diff
    provenance and the manual-application worklist)."""
    return repo.get_for_engagement(engagement_id)


@router.get("/{engagement_id}/qa-revision/v1")
def download_v1(engagement_id: str):
    """Download the original (v1) roadmap document — the exact file the QA
    agents analyzed. Serves the saved file off disk; does NOT regenerate the
    report (unlike /report/download), so the v1↔v2 comparison stays faithful."""
    eng = EngagementRepository().get_by_id(engagement_id)
    if eng is None:
        raise HTTPException(status_code=404, detail=f"Engagement {engagement_id} not found")
    reports_folder = eng.get('reports_folder') or ''
    filename = V1_FILENAME_TEMPLATE.format(engagement_id=engagement_id)
    path = os.path.join(reports_folder, filename)
    if not reports_folder or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="v1 roadmap not found — generate the roadmap first")
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/{engagement_id}/qa-revision/v2")
def download_v2(engagement_id: str):
    """Download the revised (v2) roadmap document."""
    eng = EngagementRepository().get_by_id(engagement_id)
    if eng is None:
        raise HTTPException(status_code=404, detail=f"Engagement {engagement_id} not found")
    reports_folder = eng.get('reports_folder') or ''
    filename = V2_FILENAME_TEMPLATE.format(engagement_id=engagement_id)
    path = os.path.join(reports_folder, filename)
    if not reports_folder or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="v2 roadmap not found — run the revision first")
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.patch("/{engagement_id}/qa-revision/{qa_revision_id}")
def update_qa_revision(
    engagement_id: str,
    qa_revision_id: str,
    data: QARevisionOutcomeUpdate,
    repo: QARevisionRepository = Depends(get_qa_revision_repo),
):
    """Update an edit's outcome — used by QA-5 to mark a flagged/manual edit as
    handled ('manual_done')."""
    repo.update_outcome(qa_revision_id, data.outcome)
    return {"updated": qa_revision_id, "outcome": data.outcome}
