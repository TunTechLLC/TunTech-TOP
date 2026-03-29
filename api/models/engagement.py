from pydantic import BaseModel
from typing import Optional


class EngagementCreate(BaseModel):
    """Fields required to create a new engagement."""
    firm_name:         str
    firm_size:         int
    service_model:     Optional[str] = None
    stated_problem:    Optional[str] = None
    client_hypothesis: Optional[str] = None
    previously_tried:  Optional[str] = None
    client_notes:      Optional[str] = None
    consultant_notes:  Optional[str] = None


class EngagementSettingsUpdate(BaseModel):
    """Fields for updating engagement folder settings."""
    interviews_folder: Optional[str] = None
    documents_folder:  Optional[str] = None
    candidates_folder: Optional[str] = None


class EngagementResponse(BaseModel):
    """Shape of engagement data returned to the frontend."""
    engagement_id:     str
    engagement_name:   str
    status:            str
    firm_name:         str
    firm_size:         Optional[int] = None
    service_model:     Optional[str] = None
    signal_count:      Optional[int] = 0
    pattern_count:     Optional[int] = 0
    finding_count:     Optional[int] = 0
    roadmap_count:     Optional[int] = 0
    stated_problem:    Optional[str] = None
    client_hypothesis: Optional[str] = None
    previously_tried:  Optional[str] = None
    client_notes:      Optional[str] = None
    consultant_notes:  Optional[str] = None
    interviews_folder: Optional[str] = None
    documents_folder:  Optional[str] = None
    candidates_folder: Optional[str] = None
    start_date:        Optional[str] = None
    created_date:      Optional[str] = None
