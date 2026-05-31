from pydantic import BaseModel
from typing import Literal


class QARevisionOutcomeUpdate(BaseModel):
    """PATCH body for a QA revision edit. Only the outcome can be updated —
    used by QA-5 to let the consultant mark a flagged/manual item as handled.

    'manual_done' = consultant has applied a manual/flagged edit by hand.
    """
    outcome: Literal['applied', 'flagged_unresolved', 'manual', 'unaddressed', 'manual_done']
