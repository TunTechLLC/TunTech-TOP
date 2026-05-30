"""Input assembly helpers for the Post-Assembly QA Stage (QA-1 / QA-2 / QA-3).

Provides:
- read_v1_roadmap_text: reads the rendered v1 .docx and returns extracted text.
- assemble_source_documents_block: reads all processed source files for an
  engagement and returns a prompt-ready block with `=== SOURCE: ===` headers.

Both helpers raise on missing inputs so the router can return clear 422s before
spending tokens on a Claude call.
"""
import os
import logging

from api.db.repositories.engagement import EngagementRepository
from api.db.repositories.processed_files import ProcessedFilesRepository
from api.services.document_processor import extract_text_from_file

logger = logging.getLogger(__name__)

# Filename produced by report_generator._output_path. When QA-4 ships, this
# convention changes to ``OPD_Transformation_Roadmap_{engagement_id}_v1.docx``
# and the Report Generator filename is updated in lockstep (see BACKLOG QA-4
# Versioning convention). Until then, the Report Generator output IS the v1.
V1_FILENAME_TEMPLATE = "OPD_Transformation_Roadmap_{engagement_id}.docx"


def read_v1_roadmap_text(engagement_id: str) -> str:
    """Return the extracted text of the v1 roadmap document for an engagement.

    Raises:
        ValueError: engagement not found, or reports_folder not configured.
        FileNotFoundError: v1 roadmap file does not exist (Report Generator
            has not yet been run for this engagement).
    """
    eng = EngagementRepository().get_by_id(engagement_id)
    if eng is None:
        raise ValueError(f"Engagement {engagement_id} not found")

    reports_folder = eng.get('reports_folder') or ''
    if not reports_folder:
        raise ValueError(
            f"Engagement {engagement_id} has no reports_folder configured — "
            f"cannot locate v1 roadmap"
        )

    filename = V1_FILENAME_TEMPLATE.format(engagement_id=engagement_id)
    file_path = os.path.join(reports_folder, filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"v1 roadmap not found at {file_path} — generate the roadmap first"
        )

    text = extract_text_from_file(file_path, filename)
    logger.info(
        f"read_v1_roadmap_text: {engagement_id} → {len(text)} chars from {filename}"
    )
    return text


def assemble_source_documents_block(engagement_id: str) -> str:
    """Read all processed source documents for an engagement and concatenate
    them into a prompt-ready block.

    Each document is preceded by a header line matching the format the QA
    prompts expect:
        === SOURCE: <filename> ===

    Files are read in alphabetical order by file_name so output is deterministic.
    Files that fail extraction (missing on disk, unsupported format, library
    not installed) are logged at WARNING level and skipped — a partial block is
    better than no QA pass.

    Raises:
        ValueError: engagement not found, docs_folder not configured, no
            processed files exist, or every file failed extraction.
    """
    eng = EngagementRepository().get_by_id(engagement_id)
    if eng is None:
        raise ValueError(f"Engagement {engagement_id} not found")

    # Source files live in either documents_folder (Doc_*) or interviews_folder
    # (Interview_*) — the convention is enforced by parse_file_role_and_type.
    # We try the appropriate folder for each file based on prefix; fall back to
    # the other folder if the first miss.
    documents_folder  = eng.get('documents_folder')  or ''
    interviews_folder = eng.get('interviews_folder') or ''
    if not documents_folder and not interviews_folder:
        raise ValueError(
            f"Engagement {engagement_id} has neither documents_folder nor "
            f"interviews_folder configured — cannot locate source documents"
        )

    files = ProcessedFilesRepository().get_for_engagement(engagement_id)
    if not files:
        raise ValueError(
            f"Engagement {engagement_id} has no processed files — "
            f"process source documents first"
        )

    sorted_files = sorted(files, key=lambda f: f['file_name'])

    def _resolve_path(file_name: str) -> str | None:
        """Return the on-disk path for a source file. Tries the folder matching
        the filename prefix first, falls back to the other folder."""
        primary = interviews_folder if file_name.startswith('Interview_') else documents_folder
        fallback = documents_folder if file_name.startswith('Interview_') else interviews_folder
        for folder in (primary, fallback):
            if folder:
                candidate = os.path.join(folder, file_name)
                if os.path.exists(candidate):
                    return candidate
        return None

    parts = []
    skipped = []
    for file_record in sorted_files:
        file_name = file_record['file_name']
        file_path = _resolve_path(file_name)
        if file_path is None:
            logger.warning(
                f"assemble_source_documents_block: {file_name} not on disk "
                f"in documents_folder or interviews_folder — skipped"
            )
            skipped.append(file_name)
            continue
        try:
            text = extract_text_from_file(file_path, file_name)
        except Exception as exc:
            logger.warning(
                f"assemble_source_documents_block: {file_name} extraction failed: {exc} — skipped"
            )
            skipped.append(file_name)
            continue
        parts.append(f"=== SOURCE: {file_name} ===\n\n{text}")

    if not parts:
        raise ValueError(
            f"Engagement {engagement_id}: all {len(sorted_files)} source documents "
            f"failed extraction — cannot run QA-1"
        )

    block = "\n\n".join(parts)
    logger.info(
        f"assemble_source_documents_block: {engagement_id} → "
        f"{len(parts)} document(s), {len(block)} chars total"
        + (f", {len(skipped)} skipped: {skipped}" if skipped else "")
    )
    return block
