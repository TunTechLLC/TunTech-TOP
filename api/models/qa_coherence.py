from pydantic import BaseModel
from typing import Literal


class QACoherenceUpdate(BaseModel):
    """PATCH body for a QA coherence item. Only status can be updated."""
    status: Literal['pending', 'accepted', 'rejected']
