import logging
from datetime import date
from .base import BaseRepository
from api.utils.ids import next_qa_revision_id

logger = logging.getLogger(__name__)

# SQL constants
GET_FOR_ENGAGEMENT = """
    SELECT qa_revision_id,
           engagement_id,
           edit_type,
           qa_source,
           source_item_id,
           anchor,
           context_before,
           new_text,
           reason,
           outcome,
           match_method,
           created_date
    FROM   QARevisionEdits
    WHERE  engagement_id = ?
    ORDER  BY qa_revision_id
"""

INSERT_EDIT = """
    INSERT INTO QARevisionEdits (
        qa_revision_id, engagement_id, edit_type, qa_source, source_item_id,
        anchor, context_before, new_text, reason, outcome, match_method, created_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

UPDATE_OUTCOME = """
    UPDATE QARevisionEdits
    SET    outcome = ?
    WHERE  qa_revision_id = ?
"""

DELETE_FOR_ENGAGEMENT = """
    DELETE FROM QARevisionEdits
    WHERE  engagement_id = ?
"""


class QARevisionRepository(BaseRepository):
    """Handles all database operations for QARevisionEdits.

    Unlike the QA-1/2/3 detection tables, these rows are not consultant-
    reviewed candidates — they are the record of what the QA-4 Revision Agent
    did to the document: one row per edit, with its application ``outcome``
    (applied / flagged_unresolved / manual). The rows back QA-5's diff
    provenance and the consultant's manual-application worklist.
    """

    def get_for_engagement(self, engagement_id: str) -> list:
        """Return all revision edits for an engagement, ordered by id."""
        logger.info(f"Fetching QA revision edits for engagement: {engagement_id}")
        rows = self._query(GET_FOR_ENGAGEMENT, (engagement_id,))
        return [dict(row) for row in rows]

    def bulk_create(self, engagement_id: str, edits: list) -> int:
        """Insert revision edits one at a time to ensure unique sequential QR
        IDs. Returns the number of rows inserted.

        Sequential loop required — list comprehension would call
        next_qa_revision_id() before any rows are written, producing duplicate
        IDs (same pattern documented on PatternRepository.bulk_create).

        Each edit dict must contain:
            edit_type ('replace'|'insert_after'|'manual'|'unaddressed'),
            qa_source ('coverage'|'coherence'|'editorial'),
            anchor, new_text, outcome
        Optional:
            source_item_id, context_before, reason, match_method (default None)
        """
        today = date.today().isoformat()
        count = 0
        for edit in edits:
            qr_id = next_qa_revision_id()
            self._write(INSERT_EDIT, (
                qr_id,
                engagement_id,
                edit['edit_type'],
                edit['qa_source'],
                edit.get('source_item_id'),
                edit['anchor'],
                edit.get('context_before'),
                edit['new_text'],
                edit.get('reason'),
                edit['outcome'],
                edit.get('match_method'),
                today,
            ))
            count += 1
        logger.info(f"Bulk created {count} QA revision edits for {engagement_id}")
        return count

    def update_outcome(self, qa_revision_id: str, outcome: str) -> None:
        """Update the outcome of a single revision edit.
        Used by QA-5 to mark a flagged/manual edit as handled ('manual_done')."""
        logger.info(f"Updating QA revision outcome: {qa_revision_id} → {outcome}")
        self._write(UPDATE_OUTCOME, (outcome, qa_revision_id))

    def delete_for_engagement(self, engagement_id: str) -> int:
        """Delete all revision edits for an engagement.
        Called before a re-run so the latest revision replaces the prior one."""
        count = self._write(DELETE_FOR_ENGAGEMENT, (engagement_id,))
        logger.info(f"Deleted {count} QA revision edits for {engagement_id}")
        return count
