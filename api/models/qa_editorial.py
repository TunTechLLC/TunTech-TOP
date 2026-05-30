from pydantic import BaseModel
from typing import Literal


class QAEditorialUpdate(BaseModel):
    """PATCH body for a QA editorial item. Only status can be updated."""
    status: Literal['pending', 'accepted', 'rejected']
