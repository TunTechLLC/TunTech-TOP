from pydantic import BaseModel
from typing import Optional


class RoadmapItemCreate(BaseModel):
    """Fields required to create a new roadmap item."""
    initiative_name:  str
    domain:           str
    phase:            str
    priority:         Optional[str] = "Medium"
    effort:           Optional[str] = "Medium"
    estimated_impact: Optional[str] = None
    finding_id:       Optional[str] = None
    owner:            Optional[str] = None
    target_date:      Optional[str] = None
    status:           Optional[str] = "Not Started"


class RoadmapItemResponse(BaseModel):
    """Shape of roadmap item data returned to the frontend."""
    item_id:          str
    engagement_id:    str
    finding_id:       Optional[str] = None
    initiative_name:  str
    domain:           str
    phase:            str
    priority:         Optional[str] = None
    effort:           Optional[str] = None
    estimated_impact: Optional[str] = None
    owner:            Optional[str] = None
    target_date:      Optional[str] = None
    status:           Optional[str] = None
    created_date:     str
    finding_title:    Optional[str] = None

    model_config = {"from_attributes": True}