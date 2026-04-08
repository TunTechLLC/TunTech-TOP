from pydantic import BaseModel
from typing import Optional


class RoadmapItemCreate(BaseModel):
    """Fields required to create a new roadmap item."""
    initiative_name:        str
    domain:                 str
    phase:                  str
    priority:               Optional[str] = "Medium"
    effort:                 Optional[str] = "Medium"
    estimated_impact:       Optional[str] = None
    finding_id:             Optional[str] = None
    owner:                  Optional[str] = None
    target_date:            Optional[str] = None
    status:                 Optional[str] = "Not Started"
    capability:             Optional[str] = None
    addressing_finding_ids: Optional[str] = None   # JSON array of finding_ids
    depends_on:             Optional[str] = None   # JSON array of item_ids


class RoadmapItemResponse(BaseModel):
    """Shape of roadmap item data returned to the frontend."""
    item_id:                str
    engagement_id:          str
    finding_id:             Optional[str] = None
    initiative_name:        str
    domain:                 str
    phase:                  str
    priority:               Optional[str] = None
    effort:                 Optional[str] = None
    estimated_impact:       Optional[str] = None
    owner:                  Optional[str] = None
    target_date:            Optional[str] = None
    status:                 Optional[str] = None
    created_date:           str
    finding_title:          Optional[str] = None
    capability:             Optional[str] = None
    addressing_finding_ids: Optional[str] = None
    depends_on:             Optional[str] = None
