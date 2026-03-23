from pydantic import BaseModel
from typing import Optional


class SignalCreate(BaseModel):
    """Fields required to create a new signal."""
    signal_name:       str
    domain:            str
    observed_value:    str
    normalized_band:   str
    signal_confidence: str
    source:            str
    interview_id:      Optional[str] = None
    economic_relevance: Optional[str] = None
    notes:             Optional[str] = None


class SignalResponse(BaseModel):
    """Shape of signal data returned to the frontend."""
    signal_id:         str
    engagement_id:     str
    signal_name:       str
    domain:            str
    observed_value:    str
    normalized_band:   str
    signal_confidence: str
    source:            str
    interview_id:      Optional[str] = None
    economic_relevance: Optional[str] = None
    notes:             Optional[str] = None
    created_date:      str

    model_config = {"from_attributes": True}


class DomainSummaryResponse(BaseModel):
    """Signal counts grouped by domain and confidence."""
    domain:           str
    signal_confidence: str
    signal_count:     int

    model_config = {"from_attributes": True}