"""Tests for document_processor utility functions.
These tests do not call Claude — they test local processing logic only.
"""
import io
import os
import tempfile
import pytest


def test_markdown_fence_stripping():
    """Verify JSON wrapped in code fences is cleaned correctly.
    Tests all fence variants Claude might produce despite being told not to."""
    from api.services.document_processor import strip_json_fences

    raw_json = '[{"signal_name": "test", "domain": "Delivery Operations"}]'

    # No fences — should pass through unchanged
    assert strip_json_fences(raw_json) == raw_json

    # ```json fence
    fenced_json = f'```json\n{raw_json}\n```'
    assert strip_json_fences(fenced_json) == raw_json

    # plain ``` fence
    fenced_plain = f'```\n{raw_json}\n```'
    assert strip_json_fences(fenced_plain) == raw_json

    # Extra whitespace
    fenced_whitespace = f'  ```json\n{raw_json}\n```  '
    assert strip_json_fences(fenced_whitespace) == raw_json


def test_file_type_detection():
    """Verify get_file_type correctly identifies file types from filename."""
    from api.services.document_processor import get_file_type

    assert get_file_type('E001_interview_CEO_Okafor.txt')        == 'interview'
    assert get_file_type('E001_financial_FY2025_PL.txt')         == 'financial'
    assert get_file_type('E001_sow_ProjectAlpha.txt')            == 'sow'
    assert get_file_type('E001_portfolio_March.txt')             == 'portfolio'
    assert get_file_type('E001_status_ProjectAlpha_March.txt')   == 'status'
    assert get_file_type('E001_resource_utilization_Q1.txt')     == 'resource'
    assert get_file_type('E001_delivery_risk_register.txt')      == 'delivery'
    assert get_file_type('E001_other_misc.txt')                  == 'other'
    assert get_file_type('E001_unknown_type_file.txt')           == 'other'
    # Type with uppercase — should normalize to lowercase
    assert get_file_type('E001_INTERVIEW_CEO.txt')               == 'interview'


def test_file_type_detection_new_convention():
    """Verify get_file_type works with Interview_/Doc_ convention and any extension."""
    from api.services.document_processor import get_file_type

    # Interview_ prefix — always 'interview' regardless of extension
    assert get_file_type('Interview_CEO.txt')              == 'interview'
    assert get_file_type('Interview_CEO.docx')             == 'interview'
    assert get_file_type('Interview_DirectorDelivery.pdf') == 'interview'

    # Doc_ prefix — stem determines type, extension irrelevant
    assert get_file_type('Doc_Financial.xlsx')             == 'financial'
    assert get_file_type('Doc_Financial_Q1.xlsx')          == 'financial'
    assert get_file_type('Doc_SOW.pdf')                    == 'sow'
    assert get_file_type('Doc_SOW_ProjectAlpha.pdf')       == 'sow'
    assert get_file_type('Doc_Portfolio.pptx')             == 'portfolio'
    assert get_file_type('Doc_StatusReport.pdf')           == 'status'
    assert get_file_type('Doc_Resource.xlsx')              == 'resource'
    assert get_file_type('Doc_Delivery.docx')              == 'delivery'
    assert get_file_type('Doc_Other.pdf')                  == 'other'


def test_supported_extensions():
    """Verify SUPPORTED_EXTENSIONS contains exactly the expected formats."""
    from api.services.document_processor import SUPPORTED_EXTENSIONS

    assert SUPPORTED_EXTENSIONS == {'.txt', '.docx', '.xlsx', '.pdf', '.pptx'}


def test_valid_domains_in_utils():
    """Verify domains.py contains exactly the expected 10 domains."""
    from api.utils.domains import VALID_DOMAINS

    expected = {
        'Sales & Pipeline',
        'Sales-to-Delivery Transition',
        'Delivery Operations',
        'Resource Management',
        'Project Governance / PMO',
        'Consulting Economics',
        'Customer Experience',
        'AI Readiness',
        'Human Resources',
        'Finance and Commercial',
    }
    assert VALID_DOMAINS == expected, (
        f"Domain mismatch: {VALID_DOMAINS.symmetric_difference(expected)}"
    )


def test_valid_confidences_in_utils():
    """Verify domains.py contains the correct confidence values."""
    from api.utils.domains import VALID_CONFIDENCES

    assert 'High' in VALID_CONFIDENCES
    assert 'Medium' in VALID_CONFIDENCES
    assert 'Hypothesis' in VALID_CONFIDENCES
    assert len(VALID_CONFIDENCES) == 3


# ---------------------------------------------------------------------------
# extract_text_from_file — unit tests using programmatically-created files
# No engagement, no Claude, no DB required.
# ---------------------------------------------------------------------------

def test_extract_txt_returns_content():
    from api.services.document_processor import extract_text_from_file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                    encoding='utf-8') as f:
        f.write('This is a test transcript.\nSecond line.')
        path = f.name
    try:
        result = extract_text_from_file(path, 'Interview_CEO.txt')
        assert 'test transcript' in result
        assert 'Second line' in result
    finally:
        os.unlink(path)


def test_extract_txt_empty_raises():
    from api.services.document_processor import extract_text_from_file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                    encoding='utf-8') as f:
        f.write('   \n  ')
        path = f.name
    try:
        with pytest.raises(ValueError, match='empty'):
            extract_text_from_file(path, 'Interview_CEO.txt')
    finally:
        os.unlink(path)


def test_extract_unsupported_extension_raises():
    from api.services.document_processor import extract_text_from_file
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
        f.write(b'col1,col2\nval1,val2\n')
        path = f.name
    try:
        with pytest.raises(ValueError, match='unsupported'):
            extract_text_from_file(path, 'data.csv')
    finally:
        os.unlink(path)


def test_extract_docx_paragraphs_and_tables():
    """Word document: verify both paragraph text and table cell text are extracted."""
    pytest.importorskip('docx', reason='python-docx not installed')
    from docx import Document
    from api.services.document_processor import extract_text_from_file

    doc = Document()
    doc.add_paragraph('CEO stated delivery margins are under pressure.')
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = 'Project'
    table.cell(0, 1).text = 'Status'
    table.cell(1, 0).text = 'Alpha'
    table.cell(1, 1).text = 'At risk'

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        path = f.name
    doc.save(path)

    try:
        result = extract_text_from_file(path, 'Interview_CEO.docx')
        assert 'delivery margins' in result
        assert 'At risk' in result
        assert 'Project' in result
    finally:
        os.unlink(path)


def test_extract_docx_empty_raises():
    pytest.importorskip('docx', reason='python-docx not installed')
    from docx import Document
    from api.services.document_processor import extract_text_from_file

    doc = Document()
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        path = f.name
    doc.save(path)

    try:
        with pytest.raises(ValueError, match='no extractable text'):
            extract_text_from_file(path, 'Doc_SOW.docx')
    finally:
        os.unlink(path)


def test_extract_xlsx_sheets_and_rows():
    """Excel: verify sheet headers and row data are extracted."""
    pytest.importorskip('openpyxl', reason='openpyxl not installed')
    import openpyxl
    from api.services.document_processor import extract_text_from_file

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'P&L'
    ws.append(['Metric', 'Value'])
    ws.append(['Gross Margin', '42%'])
    ws.append(['Revenue', '2400000'])

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    wb.save(path)

    try:
        result = extract_text_from_file(path, 'Doc_Financial.xlsx')
        assert '[Sheet: P&L]' in result
        assert 'Gross Margin' in result
        assert '42%' in result
    finally:
        os.unlink(path)


def test_extract_xlsx_empty_raises():
    pytest.importorskip('openpyxl', reason='openpyxl not installed')
    import openpyxl
    from api.services.document_processor import extract_text_from_file

    wb = openpyxl.Workbook()
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    wb.save(path)

    try:
        with pytest.raises(ValueError, match='no extractable data'):
            extract_text_from_file(path, 'Doc_Financial.xlsx')
    finally:
        os.unlink(path)


def test_extract_pptx_slides_and_notes():
    """PowerPoint: verify slide text and speaker notes are extracted."""
    pytest.importorskip('pptx', reason='python-pptx not installed')
    from pptx import Presentation
    from pptx.util import Inches
    from api.services.document_processor import extract_text_from_file

    prs = Presentation()
    slide_layout = prs.slide_layouts[1]  # Title and Content
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = 'Delivery Overview'
    slide.placeholders[1].text = 'Three projects are currently at risk.'

    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = 'CEO confirmed this in the follow-up call.'

    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
        path = f.name
    prs.save(path)

    try:
        result = extract_text_from_file(path, 'Doc_StatusReport.pptx')
        assert '[Slide 1]' in result
        assert 'Delivery Overview' in result
        assert 'at risk' in result
        assert 'CEO confirmed' in result
    finally:
        os.unlink(path)


def test_extract_pptx_empty_raises():
    pytest.importorskip('pptx', reason='python-pptx not installed')
    from pptx import Presentation
    from api.services.document_processor import extract_text_from_file

    prs = Presentation()
    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
        path = f.name
    prs.save(path)

    try:
        with pytest.raises(ValueError, match='no extractable text'):
            extract_text_from_file(path, 'Doc_StatusReport.pptx')
    finally:
        os.unlink(path)


def test_archive_candidate_files_new_convention():
    """archive_candidate_files() must archive Interview_/Doc_ named candidate files,
    not just legacy engagement_id-prefixed ones."""
    import json
    from api.services.document_processor import archive_candidate_files

    with tempfile.TemporaryDirectory() as candidates_folder:
        # Merged file
        merged = os.path.join(candidates_folder, 'E005_merged_candidates.json')
        # Individual files — new naming convention (no engagement_id prefix)
        interview_file = os.path.join(candidates_folder, 'Interview_CEO_candidates.json')
        doc_file = os.path.join(candidates_folder, 'Doc_Financial_candidates.json')

        for path in [merged, interview_file, doc_file]:
            with open(path, 'w') as f:
                json.dump({}, f)

        archive_candidate_files('E005', candidates_folder, merged)

        processed_dir = os.path.join(candidates_folder, 'processed')
        archived = os.listdir(processed_dir)

        assert 'E005_merged_candidates.json' in archived
        assert 'Interview_CEO_candidates.json' in archived
        assert 'Doc_Financial_candidates.json' in archived
        # All three moved — none left in candidates_folder root
        assert not os.path.exists(merged)
        assert not os.path.exists(interview_file)
        assert not os.path.exists(doc_file)
