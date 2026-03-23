from pydantic import BaseModel
from typing import Optional


class FindingCreate(BaseModel):
    """Fields required to create a new OPD finding."""
    finding_title:      str
    domain:             str
    confidence:         str
    operational_impact: str
    economic_impact:    str
    root_cause:         str
    recommendation:     str
    priority:           Optional[str] = "Medium"
    effort:             Optional[str] = "Medium"
    opd_section:        Optional[int] = None
    pattern_id:         Optional[str] = None
    contributing_ep_ids: list[str] = []


class FindingUpdate(BaseModel):
    """All fields optional — only provided fields are updated."""
    finding_title:      Optional[str] = None
    domain:             Optional[str] = None
    confidence:         Optional[str] = None
    operational_impact: Optional[str] = None
    economic_impact:    Optional[str] = None
    root_cause:         Optional[str] = None
    recommendation:     Optional[str] = None
    priority:           Optional[str] = None
    effort:             Optional[str] = None
    opd_section:        Optional[int] = None


class FindingResponse(BaseModel):
    """Shape of finding data returned to the frontend."""
    finding_id:         str
    engagement_id:      str
    pattern_id:         Optional[str] = None
    finding_title:      str
    domain:             str
    confidence:         str
    operational_impact: str
    economic_impact:    str
    root_cause:         str
    recommendation:     str
    priority:           Optional[str] = None
    effort:             Optional[str] = None
    opd_section:        Optional[int] = None
    created_date:       str
    pattern_name:       Optional[str] = None

    model_config = {"from_attributes": True}