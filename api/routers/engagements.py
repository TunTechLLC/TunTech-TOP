import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.engagement import EngagementRepository
from api.models.engagement import EngagementCreate, EngagementResponse, EngagementSettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


def get_repo() -> EngagementRepository:
    """Dependency injection — provides EngagementRepository to route functions."""
    return EngagementRepository()


@router.get("/", response_model=list[EngagementResponse])
def list_engagements(repo: EngagementRepository = Depends(get_repo)):
    """Return all engagements with summary counts for the dashboard."""
    return repo.get_all()


@router.get("/{engagement_id}", response_model=EngagementResponse)
def get_engagement(
    engagement_id: str,
    repo: EngagementRepository = Depends(get_repo)
):
    """Return full detail for a single engagement."""
    engagement = repo.get_by_id(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail=f"Engagement {engagement_id} not found")
    return engagement


@router.post("/", response_model=EngagementResponse, status_code=201)
def create_engagement(
    data: EngagementCreate,
    repo: EngagementRepository = Depends(get_repo)
):
    """Create a new client and engagement. Returns the created engagement."""
    engagement_id = repo.create(data.model_dump())
    engagement = repo.get_by_id(engagement_id)
    if not engagement:
        raise HTTPException(status_code=500, detail="Engagement created but could not be retrieved")
    return engagement

@router.patch("/{engagement_id}/settings")
def update_settings(
    engagement_id: str,
    data: EngagementSettingsUpdate,
    repo: EngagementRepository = Depends(get_repo)
):
    """Update folder settings for an engagement."""
    fields = data.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided")
    repo.update_settings(engagement_id, fields)
    return repo.get_by_id(engagement_id)