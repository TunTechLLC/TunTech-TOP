from pydantic import BaseModel
from typing import Optional

LOG_PREVIEW_LENGTH = 80


class EngagementCreate(BaseModel):
    """Fields required to create a new client and engagement."""
    firm_name:         str
    firm_size:         int
    service_model:     str
    stated_problem:    str
    client_hypothesis: str
    previously_tried:  str
    client_notes:      Optional[str] = None
    consultant_notes:  Optional[str] = None


class EngagementUpdate(BaseModel):
    """All fields optional — only provided fields are updated."""
    status:            Optional[str] = None
    consultant_notes:  Optional[str] = None


class EngagementResponse(BaseModel):
    """Shape of data returned to the frontend."""
    engagement_id:  str
    engagement_name: str
    status:         str
    firm_name:      str
    firm_size:      int
    signal_count:   int = 0
    pattern_count:  int = 0
    finding_count:  int = 0

    model_config = {"from_attributes": True}