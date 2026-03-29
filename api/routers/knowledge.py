import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.knowledge import KnowledgeRepository
from api.models.knowledge import KnowledgeCreate, KnowledgeResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_repo() -> KnowledgeRepository:
    return KnowledgeRepository()


@router.get("/{engagement_id}/knowledge")
def list_knowledge(
    engagement_id: str,
    repo: KnowledgeRepository = Depends(get_repo)
):
    """Return all knowledge promotions for an engagement."""
    return repo.get_all(engagement_id)


@router.post("/{engagement_id}/knowledge",
             response_model=KnowledgeResponse,
             status_code=201)
def create_knowledge(
    engagement_id: str,
    data:          KnowledgeCreate,
    repo:          KnowledgeRepository = Depends(get_repo)
):
    """Create a knowledge promotion."""
    promotion_id = repo.create(engagement_id, data.model_dump())
    promotions   = repo.get_all(engagement_id)
    promotion    = next((k for k in promotions if k['promotion_id'] == promotion_id), None)
    if not promotion:
        raise HTTPException(status_code=500, detail="Knowledge promotion created but could not be retrieved")
    return promotion