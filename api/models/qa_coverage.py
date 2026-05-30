from pydantic import BaseModel
from typing import Literal


class QACoverageUpdate(BaseModel):
    """PATCH body for a QA coverage item. Only status can be updated —
    item content is set once at detection time."""
    status: Literal['pending', 'accepted', 'rejected']
