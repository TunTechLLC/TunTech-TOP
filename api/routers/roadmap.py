import logging
from fastapi import APIRouter, HTTPException, Depends
from api.db.repositories.roadmap import RoadmapRepository
from api.models.roadmap import RoadmapItemCreate, RoadmapItemResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_repo() -> RoadmapRepository:
    return RoadmapRepository()


@router.get("/{engagement_id}/roadmap",
            response_model=list[RoadmapItemResponse])
def list_roadmap_items(
    engagement_id: str,
    repo: RoadmapRepository = Depends(get_repo)
):
    """Return all roadmap items for an engagement ordered by phase and priority."""
    return repo.get_all(engagement_id)


@router.get("/{engagement_id}/roadmap/{phase}",
            response_model=list[RoadmapItemResponse])
def list_roadmap_by_phase(
    engagement_id: str,
    phase:         str,
    repo:          RoadmapRepository = Depends(get_repo)
):
    """Return roadmap items for a specific phase.
    Phase values: Stabilize, Optimize, Scale"""
    if phase not in ('Stabilize', 'Optimize', 'Scale'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase: {phase}. Must be Stabilize, Optimize, or Scale"
        )
    return repo.get_by_phase(engagement_id, phase)


@router.post("/{engagement_id}/roadmap",
             response_model=RoadmapItemResponse,
             status_code=201)
def create_roadmap_item(
    engagement_id: str,
    data:          RoadmapItemCreate,
    repo:          RoadmapRepository = Depends(get_repo)
):
    """Create a roadmap item."""
    item_id = repo.create(engagement_id, data.model_dump())
    items   = repo.get_all(engagement_id)
    item    = next((i for i in items if i['item_id'] == item_id), None)
    if not item:
        raise HTTPException(status_code=500, detail="Roadmap item created but could not be retrieved")
    return item