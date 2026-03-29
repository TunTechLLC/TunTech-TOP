from pydantic import BaseModel
from typing import Optional


class KnowledgeCreate(BaseModel):
    """Fields required to create a knowledge promotion."""
    promotion_type:  str
    description:     str
    applied_to:      Optional[str] = None
    finding_id:      Optional[str] = None
    pattern_id:      Optional[str] = None
    promotion_date:  Optional[str] = None


class KnowledgeResponse(BaseModel):
    """Shape of knowledge promotion data returned to the frontend."""
    promotion_id:   str
    engagement_id:  str
    finding_id:     Optional[str] = None
    pattern_id:     Optional[str] = None
    promotion_type: str
    description:    str
    applied_to:     Optional[str] = None
    promotion_date: str
    created_date:   str
    finding_title:  Optional[str] = None
    pattern_name:   Optional[str] = None
