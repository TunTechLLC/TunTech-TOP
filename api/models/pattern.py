from pydantic import BaseModel, field_validator
from typing import Optional


class PatternDetectionResult(BaseModel):
    """Shape of a single pattern returned by Claude API during detection.
    Validated before any database write occurs."""
    pattern_id: str
    confidence: str
    notes:      Optional[str] = None

    @field_validator('pattern_id')
    @classmethod
    def must_be_valid_format(cls, v):
        if not v.startswith('P') or not v[1:].isdigit():
            raise ValueError(f"Invalid pattern_id format: {v}")
        return v

    @field_validator('confidence')
    @classmethod
    def must_be_valid_confidence(cls, v):
        if v not in ('High', 'Medium', 'Hypothesis'):
            raise ValueError(f"Invalid confidence value: {v}")
        return v


class PatternUpdate(BaseModel):
    """Fields that can be updated on an EngagementPattern."""
    confidence:          Optional[str] = None
    economic_impact_est: Optional[str] = None


class EngagementPatternResponse(BaseModel):
    """Shape of engagement pattern data returned to the frontend."""
    ep_id:               str
    engagement_id:       str
    pattern_id:          str
    confidence:          str
    economic_impact_est: Optional[str] = None
    accepted:            int
    notes:               Optional[str] = None
    created_date:        str
    pattern_name:        Optional[str] = None
    domain:              Optional[str] = None
    operational_impact:  Optional[str] = None
    economic_model:      Optional[str] = None

    model_config = {"from_attributes": True}


class PatternLibraryResponse(BaseModel):
    """Shape of a pattern library entry."""
    pattern_id:               str
    pattern_name:             str
    domain:                   str
    trigger_signals:          Optional[str] = None
    operational_impact:       Optional[str] = None
    likely_root_cause:        Optional[str] = None
    recommended_improvements: Optional[str] = None
    economic_model:           Optional[str] = None
    economic_formula:         Optional[str] = None

    model_config = {"from_attributes": True}