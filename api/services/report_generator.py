import os
import re
import logging
import tempfile
from collections import defaultdict

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from lxml import etree

from api.db.repositories.engagement import EngagementRepository
from api.db.repositories.finding import FindingRepository
from api.db.repositories.roadmap import RoadmapRepository
from api.db.repositories.agent_run import AgentRunRepository
from api.db.repositories.processed_files import ProcessedFilesRepository
from api.db.repositories.reporting import ReportingRepository
from api.services.claude import generate_report_narrative

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {'High': 0, 'Medium': 1, 'Low': 2}

_TEMPLATE = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'roadmap_template.docx')


def _shade_cell(cell, hex_color: str):
    """Apply a solid background fill to a table cell. hex_color e.g. 'D9D9D9'."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  hex_color)
    tcPr.append(shd)


def _set_col_widths(table, widths_inches: list):
    """Set explicit column widths. widths_inches must match table column count."""
    for col_idx, width in enumerate(widths_inches):
        for cell in table.columns[col_idx].cells:
            cell.width = Inches(width)


def _left_align_table(table):
    """Force left alignment on every paragraph in every cell of a table.
    Overrides any justified alignment inherited from the document template."""
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT


# -------------------------------------------------------------------
# Domain audience mapping — Change 5
# -------------------------------------------------------------------

_DOMAIN_AUDIENCE = {
    'AI Readiness':                  'CEO, Director of Operations',
    'Consulting Economics':          'CEO, Finance Lead',
    'Customer Experience':           'CEO, Director of Delivery',
    'Delivery Operations':           'Director of Delivery',
    'Finance and Commercial':        'Finance Lead',
    'Project Governance / PMO':      'Director of Delivery',
    'Resource Management':           'Director of Delivery',
    'Sales & Pipeline':              'VP Sales, CEO',
    'Sales-to-Delivery Transition':  'VP Sales, Director of Delivery',
    'Human Resources':               'Director of Operations',
}

# -------------------------------------------------------------------
# Reader guide — Change 2
# -------------------------------------------------------------------

_ROLE_READING_GUIDE = [
    {
        'role':            'CEO / Founder',
        'priority':        'Executive Summary, Section 8.1, Section 9',
        'detail':          'Section 7 (Future State)',
        'trigger_domains': None,   # always include
    },
    {
        'role':            'Director of Delivery',
        'priority':        'Section 4 (Delivery Operations, Project Governance, Resource Management), Section 8.3',
        'detail':          'Sections 5, 8.4, 8.7',
        'trigger_domains': {'Delivery Operations', 'Project Governance / PMO', 'Resource Management'},
    },
    {
        'role':            'VP Sales / Business Development',
        'priority':        'Section 4 (Sales & Pipeline, Sales-to-Delivery Transition), Section 8.3',
        'detail':          'Section 8.6 (Dependencies)',
        'trigger_domains': {'Sales & Pipeline', 'Sales-to-Delivery Transition'},
    },
    {
        'role':            'Finance Lead',
        'priority':        'Section 4 (Finance and Commercial, Consulting Economics), Section 6',
        'detail':          'Sections 8.3, 8.4',
        'trigger_domains': {'Finance and Commercial', 'Consulting Economics'},
    },
    {
        'role':            'Project Manager / Senior Consultant',
        'priority':        'Section 9 (What Happens Next), Section 8.3',
        'detail':          'Section 8.7 (Key Risks)',
        'trigger_domains': None,   # always include
    },
    {
        'role':            'Operations / Admin',
        'priority':        'Section 4 (AI Readiness, Human Resources), Section 8.4',
        'detail':          'Section 9',
        'trigger_domains': {'AI Readiness', 'Human Resources'},
    },
]

# -------------------------------------------------------------------
# Interview role / document type derivation
# See CLAUDE.md — "File Naming Convention for OPD Engagements"
# -------------------------------------------------------------------

# Ordered (stem_substring, label) tuples — first match wins.
# More specific entries precede broader ones (e.g. 'directordelivery' before 'director').
# Matching is against the lowercased, underscore/space-stripped role stem.
_INTERVIEW_ROLE_MAP = (
    ('ceo',              'CEO'),
    ('directordelivery', 'Director of Delivery'),
    ('director',         'Director of Delivery'),
    ('vpsales',          'VP of Sales'),
    ('sales',            'VP of Sales'),
    ('financelead',      'Finance Lead'),
    ('finance',          'Finance Lead'),
    ('seniorconsultant', 'Senior Consultant and Project Manager'),
    ('consultant',       'Senior Consultant and Project Manager'),
    ('pm',               'Senior Consultant and Project Manager'),
    ('operations',       'Director of Operations'),
    ('admin',            'Director of Operations'),
)

_DOC_TYPE_MAP = (
    ('financial',      'financial performance documentation'),
    ('portfolio',      'project portfolio summary'),
    ('statusreport',   'project status report'),
    ('status',         'project status report'),
    ('clientfeedback', 'client satisfaction data'),
    ('feedback',       'client satisfaction data'),
    ('sow',            'Statement of Work'),
    ('other',          'supporting documentation'),
)

# Last-resort fallback when filename stem yields no _DOC_TYPE_MAP match.
# Keyed by ProcessedFiles.file_type — preserves backward compat for pre-convention files.
_FILE_TYPE_FALLBACK = {
    'financial': 'financial performance documentation',
    'sow':       'Statement of Work',
    'status':    'project status report',
    'resource':  'resource planning documentation',
    'delivery':  'delivery documentation',
}


def parse_file_role_and_type(filename: str, file_type: str) -> dict:
    """Parse a single ProcessedFile record into a structured role or document type.

    Kind detection priority:
      1. Interview_ prefix (case-insensitive) → interview
      2. Doc_ prefix (case-insensitive)       → document
      3. file_type == 'interview'             → interview
      4. anything else                        → document

    For interviews: strips _Followup and _N suffixes before role matching.
      Sets is_followup=True when _Followup suffix detected.
    For documents: falls back to _FILE_TYPE_FALLBACK[file_type] when stem
      yields no _DOC_TYPE_MAP match (backward compat for pre-convention files).
    Unrecognised stems are passed through (underscores → spaces) — never 'team member'.

    Returns one of:
      {'kind': 'interview', 'role': str, 'is_followup': bool}
      {'kind': 'document',  'document_type': str}
    """
    stem     = re.sub(r'\.[^.]+$', '', filename)   # strip extension
    name_low = filename.lower()

    # Determine kind and extract raw stem after prefix
    if name_low.startswith('interview_'):
        kind     = 'interview'
        raw_stem = stem[10:]            # len('Interview_') == 10
    elif name_low.startswith('doc_'):
        kind     = 'document'
        raw_stem = stem[4:]             # len('Doc_') == 4
    elif file_type == 'interview':
        kind     = 'interview'
        raw_stem = stem
    else:
        kind     = 'document'
        raw_stem = stem

    if kind == 'interview':
        is_followup = bool(re.search(r'_followup', raw_stem, re.I))
        role_stem   = re.sub(r'_followup.*$', '', raw_stem, flags=re.I)
        role_stem   = re.sub(r'_\d+$', '', role_stem)      # strip _2, _3, etc.
        role_key    = role_stem.lower().replace('_', '').replace(' ', '')

        for match_key, label in _INTERVIEW_ROLE_MAP:
            if match_key in role_key:
                return {'kind': 'interview', 'role': label, 'is_followup': is_followup}

        # Fallback: pass raw stem through — never substitute a generic placeholder
        return {'kind': 'interview', 'role': role_stem.replace('_', ' '),
                'is_followup': is_followup}

    # Document branch
    doc_key = raw_stem.lower().replace('_', '').replace(' ', '')

    for match_key, label in _DOC_TYPE_MAP:
        if match_key in doc_key:
            return {'kind': 'document', 'document_type': label}

    # Fallback 1: file_type label (backward compat for pre-convention files)
    if file_type in _FILE_TYPE_FALLBACK:
        return {'kind': 'document', 'document_type': _FILE_TYPE_FALLBACK[file_type]}

    # Fallback 2: pass raw stem through
    return {'kind': 'document', 'document_type': raw_stem.replace('_', ' ')}


def _extract_interview_roles(processed_files: list) -> list:
    """Derive interview role list using parse_file_role_and_type().
    Skips followup files (same role, different session). Deduplicates in encounter order."""
    roles = []
    for pf in processed_files:
        result = parse_file_role_and_type(pf.get('file_name', ''), pf.get('file_type', ''))
        if result['kind'] != 'interview':
            continue
        if result.get('is_followup'):
            continue
        role = result['role']
        if role not in roles:
            roles.append(role)
    return roles


def _extract_document_types(processed_files: list) -> list:
    """Derive document type list using parse_file_role_and_type().
    Deduplicates in encounter order."""
    types = []
    for pf in processed_files:
        result = parse_file_role_and_type(pf.get('file_name', ''), pf.get('file_type', ''))
        if result['kind'] != 'document':
            continue
        doc_type = result['document_type']
        if doc_type not in types:
            types.append(doc_type)
    return types


def _compute_confirmed_floor(findings: list) -> str | None:
    """Sum unique confirmed figures across all findings (deduplicates same dollar amount
    appearing in multiple findings). Returns a formatted '~$X.XM+' string or None."""
    seen = set()
    total_val = 0.0
    parseable = False
    for f in sorted(findings, key=lambda x: PRIORITY_ORDER.get(x.get('priority'), 2)):
        conf, _ = _parse_economic_figures(f.get('economic_impact', ''))
        if conf == '—':
            continue
        primary = conf.split(', ')[0]
        if primary in seen:
            continue
        seen.add(primary)
        val = _dollar_to_float(primary)
        if val is not None:
            total_val += val
            parseable = True
    if not parseable:
        return None
    if total_val >= 1_000_000:
        return f'~${total_val / 1_000_000:.1f}M+'
    return f'~${int(round(total_val / 1000))}K+'


# Matches dollar amounts including ranges and K/M suffixes, with optional ~ prefix.
# Examples: $85K  ~$463K  $150K–$612K  $1,070K  $1.5M
_DOLLAR_RE = re.compile(
    r'~?\$[\d,\.]+[KkMmBb]?(?:[–\-]\$?[\d,\.]+[KkMmBb]?)?',
    re.IGNORECASE
)
_CONFIRMED_RE = re.compile(r'\bCONFIRMED(?:-\w+)?', re.IGNORECASE)
_INFERRED_RE  = re.compile(r'\bINFERRED(?:-\w+)?',  re.IGNORECASE)


def _dollar_to_float(s: str) -> float | None:
    """Convert a dollar string to a float for summation in the totals row.
    Handles K/M suffixes, ~ prefix, commas, and ranges (takes lower bound).
    Returns None if parsing fails."""
    s = re.sub(r'[~$,\s]', '', s.strip())
    s = re.split(r'[–\-]', s)[0]   # lower bound of range
    multiplier = 1
    if s and s[-1].upper() == 'K':
        multiplier = 1_000;      s = s[:-1]
    elif s and s[-1].upper() == 'M':
        multiplier = 1_000_000;  s = s[:-1]
    elif s and s[-1].upper() == 'B':
        multiplier = 1_000_000_000; s = s[:-1]
    try:
        return float(s) * multiplier
    except (ValueError, AttributeError):
        return None


def _parse_economic_figures(text: str):
    """Parse an economic_impact string into (confirmed, inferred) figure strings.

    Handles label variants: CONFIRMED, CONFIRMED-QUALIFIED, INFERRED, INFERRED-UNVALIDATED.
    Labels must appear AFTER the dollar amount (within 80 chars) to be assigned to it.
    This prevents adjective uses like "confirmed overrun exposure: $85K" from incorrectly
    assigning the label to dollar amounts that appear before it in a noun phrase.
    Returns '—' for each column when no matching figures are found.
    """
    if not text:
        return '—', '—'

    confirmed_figures = []
    inferred_figures  = []

    # Split on sentence boundaries — use '. ' (period + space) to avoid splitting
    # decimal numbers like $1.5M, and also split on semicolons and newlines.
    clauses = re.split(r'\.\s+|\.\s*$|;\s*|\n', text)

    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue

        conf_positions = [m.start() for m in _CONFIRMED_RE.finditer(clause)]
        inf_positions  = [m.start() for m in _INFERRED_RE.finditer(clause)]

        if not conf_positions and not inf_positions:
            continue  # No labels in this clause

        for m in _DOLLAR_RE.finditer(clause):
            amt       = m.group(0)
            amt_end   = m.end()
            amt_start = m.start()

            # Skip dollar amounts inside parentheses — these are reference figures
            # cited as context from other findings, not direct exposure claims for
            # this finding. E.g. "($4,094,000 in top-3 client revenue, CONFIRMED)"
            # is a parenthetical qualifier, not the subject of the clause.
            pre_text = clause[:amt_start]
            if pre_text.count('(') > pre_text.count(')'):
                continue

            # Only consider labels that appear AFTER the dollar amount
            conf_after = [p for p in conf_positions if p >= amt_end]
            inf_after  = [p for p in inf_positions  if p >= amt_end]

            d_conf = min((p - amt_end for p in conf_after), default=9999)
            d_inf  = min((p - amt_end for p in inf_after),  default=9999)

            # Require label within 80 chars to avoid false positives
            if min(d_conf, d_inf) > 80:
                continue

            if d_conf <= d_inf:
                if amt not in confirmed_figures:
                    confirmed_figures.append(amt)
            else:
                if amt not in inferred_figures:
                    inferred_figures.append(amt)

    # Cap at 3 figures per column so cells remain readable
    confirmed = ', '.join(confirmed_figures[:3]) if confirmed_figures else '—'
    inferred  = ', '.join(inferred_figures[:3])  if inferred_figures  else '—'
    return confirmed, inferred


class ReportGeneratorService:
    """Generates the OPD Transformation Roadmap Word document.

    Nine sections (three-layer design — CEO / Leadership / Execution):
    1. Executive Summary — opening para + Key Findings box + 3 short paras + reference line
    How to Read This Document — prefatory page, excluded from TOC
    2. Engagement Overview — compact metadata + narrator paragraph
    3. Operational Maturity Overview — intro paragraph + renamed signal table + callout
    4. Domain Analysis — role callout + narrator opening/closing + finding tables per domain
    5. Root Cause Analysis — narrator prose only
    6. Economic Impact Analysis — economic summary table + narrator prose
    7. Future State — metrics table (narrator) + narrative (narrator)
    8. Transformation Roadmap — 8.1 Priority Zero | 8.2 Overview | 8.3-8.5 Phase Tables
                                 | 8.6 Dependencies | 8.7 Key Risks
    9. Immediate Next Steps — action table (narrator, execution-voice completion criteria)
    """

    def __init__(self, engagement_id: str):
        self.engagement_id = engagement_id

    async def generate(self) -> str:
        """Generate the OPD Word document. Returns the saved file path.
        Raises ValueError if the engagement is not found or has no accepted Synthesizer output."""
        eng = EngagementRepository().get_by_id(self.engagement_id)
        if not eng:
            raise ValueError(f"Engagement {self.engagement_id} not found")

        synth_output = AgentRunRepository().get_accepted_output(self.engagement_id, "Synthesizer")
        if not synth_output:
            raise ValueError(
                f"Engagement {self.engagement_id} has no accepted Synthesizer output. "
                "Complete and accept all five agents before generating the report."
            )

        findings        = FindingRepository().get_all(self.engagement_id)
        roadmap         = RoadmapRepository().get_all(self.engagement_id)
        signals         = ReportingRepository().get_engagement_signals(self.engagement_id)
        processed_files = ProcessedFilesRepository().get_for_engagement(self.engagement_id)

        interview_roles = _extract_interview_roles(processed_files)
        document_types  = _extract_document_types(processed_files)
        total_signals   = len(signals)
        domain_count    = len({s['domain'] for s in signals if s.get('domain')})

        narrative = await generate_report_narrative(
            synth_output, findings, roadmap, eng,
            interview_roles=interview_roles,
            document_types=document_types,
            total_signals=total_signals,
            domain_count=domain_count,
        )

        if os.path.exists(_TEMPLATE):
            doc = Document(_TEMPLATE)
        else:
            logger.warning(f"Template not found at {_TEMPLATE} — using default styles")
            doc = Document()
        self._build(doc, eng, findings, roadmap, signals, narrative)

        file_path = self._output_path(eng)
        doc.save(file_path)
        logger.info(f"Report saved: {file_path}")
        return file_path

    # ------------------------------------------------------------------
    # File path helpers
    # ------------------------------------------------------------------

    def _output_path(self, eng: dict) -> str:
        """Save report to the engagement's reports_folder.
        Falls back to the system temp directory if reports_folder is not set."""
        reports_dir = eng.get('reports_folder') or ''
        if reports_dir:
            os.makedirs(reports_dir, exist_ok=True)
            return os.path.join(reports_dir, f"OPD_Transformation_Roadmap_{self.engagement_id}.docx")
        return os.path.join(
            tempfile.gettempdir(),
            f"OPD_Transformation_Roadmap_{self.engagement_id}.docx"
        )

    # ------------------------------------------------------------------
    # Document assembly
    # ------------------------------------------------------------------

    def _build(self, doc, eng, findings, roadmap, signals, narrative: dict):
        firm_name = eng.get('firm_name') or self.engagement_id

        self._populate_content_controls(doc, firm_name)

        # Lookup dicts used across multiple sections
        findings_by_id = {f['finding_id']: f for f in findings}
        initiative_details = {
            d['item_id']: d
            for d in narrative.get('initiative_details', [])
            if isinstance(d, dict) and d.get('item_id')
        }

        # 1 — Executive Summary (four components — Change 1)
        doc.add_heading('Executive Summary', level=1)

        # Component A — 3-4 sentence opening paragraph (narrator)
        opening = narrative.get('executive_summary_opening', '')
        if opening:
            self._add_narrative_paragraphs(doc, opening)
            doc.add_paragraph()

        # Component B — Key Findings at a Glance (sourced from structured data only)
        kf_rows = []
        margin_trend = narrative.get('margin_trend_brief', '')
        if margin_trend:
            kf_rows.append(('Margin Trend', margin_trend))
        confirmed_floor = _compute_confirmed_floor(findings)
        if confirmed_floor:
            kf_rows.append(('Revenue at Risk', confirmed_floor))
        high_findings   = [f for f in findings if f.get('priority') == 'High']
        primary_finding = high_findings[0] if high_findings else (findings[0] if findings else None)
        if primary_finding and primary_finding.get('root_cause'):
            rc  = primary_finding['root_cause']
            dot = rc.find('. ')
            cause_line = (rc[:dot] if dot > 0 else rc[:120]).strip()
            if cause_line:
                kf_rows.append(('Primary Cause', cause_line))
        pz_rows = narrative.get('priority_zero_table_rows', [])
        if pz_rows and isinstance(pz_rows, list) and pz_rows[0].get('action'):
            kf_rows.append(('Act This Week', pz_rows[0]['action']))
        fs_rows = narrative.get('future_state_table_rows', [])
        if fs_rows and isinstance(fs_rows, list) and fs_rows[0].get('target'):
            kf_rows.append(('18-Month Target', fs_rows[0]['target']))
        if kf_rows:
            self._key_findings_box(doc, kf_rows)
            doc.add_paragraph()

        # Component C — three short narrative paragraphs (narrator, no CONFIRMED/INFERRED)
        for key in ('executive_summary_para1', 'executive_summary_para2',
                    'executive_summary_para3'):
            para_text = narrative.get(key, '')
            if para_text:
                self._add_narrative_paragraphs(doc, para_text)

        # Component D — multi-reader reference line (small muted font)
        ref_para = doc.add_paragraph()
        ref_run  = ref_para.add_run(
            'This document is intended for multiple readers. '
            'Refer to How to Read This Document (following the Engagement Overview) '
            'for a guide to which sections are most relevant to your role.'
        )
        ref_run.font.size      = Pt(9)
        ref_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        ref_para.alignment     = WD_ALIGN_PARAGRAPH.LEFT
        doc.add_paragraph()

        # How to Read This Document — prefatory page, excluded from TOC (Change 2)
        self._how_to_read_page(doc, findings, firm_name)
        doc.add_paragraph()

        # 2 — Engagement Overview (redesigned — Change 3)
        doc.add_heading('Engagement Overview', level=1)

        # Component A — compact 3-line metadata block
        for line in [
            f"Client: {firm_name}",
            f"Engagement Date: {eng.get('start_date') or '—'}",
            f"Reference: {self.engagement_id}",
        ]:
            p = doc.add_paragraph(line)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # Component B — narrator engagement overview paragraph
        overview_para = narrative.get('engagement_overview_paragraph', '')
        if overview_para:
            doc.add_paragraph()
            self._add_narrative_paragraphs(doc, overview_para)
        doc.add_paragraph()

        # 3 — Operational Maturity Overview
        doc.add_heading('Operational Maturity Overview', level=1)
        self._signal_table(doc, signals)
        doc.add_paragraph()

        # 4 — Domain Analysis
        doc.add_heading('Domain Analysis', level=1)
        self._findings_by_domain(doc, findings, narrative)
        doc.add_paragraph()

        # 5 — Root Cause Analysis (prose only — finding bullets removed)
        doc.add_heading('Root Cause Analysis', level=1)
        root_cause = narrative.get('root_cause_narrative', '')
        if root_cause:
            self._add_narrative_paragraphs(doc, root_cause)
        else:
            doc.add_paragraph('No root cause narrative generated.')
        doc.add_paragraph()

        # 6 — Economic Impact Analysis (summary table first, then prose)
        doc.add_heading('Economic Impact Analysis', level=1)
        self._economic_summary_table(doc, findings)
        doc.add_paragraph()
        econ_narrative = narrative.get('economic_impact_narrative', '')
        if econ_narrative:
            self._add_narrative_paragraphs(doc, econ_narrative)
        doc.add_paragraph()

        # 7 — Future State
        doc.add_heading(f'Where {firm_name} Can Be in 18 Months', level=1)
        future_rows = narrative.get('future_state_table_rows', [])
        if future_rows and isinstance(future_rows, list):
            self._future_state_table(doc, future_rows)
            doc.add_paragraph()
        future_narrative = narrative.get('future_state_narrative', '')
        if future_narrative:
            self._add_narrative_paragraphs(doc, future_narrative)
        doc.add_paragraph()

        # 8 — Transformation Roadmap
        doc.add_heading('Transformation Roadmap', level=1)

        # 8.1 — Priority Zero Actions
        doc.add_heading('Priority Zero Actions — Complete This Week', level=2)
        pz_rows = narrative.get('priority_zero_table_rows', [])
        if pz_rows and isinstance(pz_rows, list):
            self._priority_zero_table(doc, pz_rows)
        else:
            doc.add_paragraph('No Priority Zero items identified.')
        doc.add_paragraph()

        # 8.2 — Roadmap Overview
        doc.add_heading('Roadmap Overview', level=2)
        overview_rows = narrative.get('roadmap_overview_rows', [])
        if overview_rows and isinstance(overview_rows, list):
            self._roadmap_overview_table(doc, overview_rows)
        doc.add_paragraph()

        # 8.3 / 8.4 / 8.5 — Phase Tables
        if roadmap:
            for phase in ['Stabilize', 'Optimize', 'Scale']:
                items = [r for r in roadmap if r.get('phase') == phase]
                if items:
                    doc.add_heading(phase, level=2)
                    rationale = narrative.get('roadmap_rationale', {}).get(phase, '')
                    if rationale:
                        self._add_narrative_paragraphs(doc, rationale)
                        doc.add_paragraph()
                    self._roadmap_phase_table(doc, items, findings_by_id, initiative_details)
                    doc.add_paragraph()
        else:
            doc.add_paragraph('No roadmap items recorded.')

        # 8.6 — Initiative Dependencies
        doc.add_heading('Initiative Dependencies', level=2)
        dep_rows = narrative.get('dependency_table_rows', [])
        if dep_rows and isinstance(dep_rows, list):
            self._dependency_table(doc, dep_rows)
        else:
            doc.add_paragraph('No dependencies identified.')
        doc.add_paragraph()

        # 8.7 — Key Risks
        doc.add_heading('Key Risks', level=2)
        risk_rows = narrative.get('risk_table_rows', [])
        if risk_rows and isinstance(risk_rows, list):
            self._risk_table(doc, risk_rows)
        else:
            doc.add_paragraph('No risks identified in this engagement diagnostic.')
        doc.add_paragraph()

        # 9 — Immediate Next Steps
        doc.add_heading('What Happens Next', level=1)
        doc.add_paragraph(
            'The following actions should be completed within the next two weeks '
            'regardless of any other prioritization decisions.'
        )
        next_rows = narrative.get('next_steps_rows', [])
        if next_rows and isinstance(next_rows, list):
            self._next_steps_table(doc, next_rows)
        else:
            doc.add_paragraph('No next steps generated.')

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------

    def _populate_content_controls(self, doc, firm_name: str):
        """Populate named content controls in the template with engagement data.

        The Company content control is data-bound to docProps/app.xml.
        Word reads from app.xml on open, so we must update both the binding
        source and the sdtContent (for immediate visibility in the saved file).
        """
        _EXT_PROPS_RT = (
            'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'extended-properties'
        )
        _EXT_PROPS_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'

        for rel in doc.part.package.iter_rels():
            if rel.reltype == _EXT_PROPS_RT:
                part = rel.target_part
                root = etree.fromstring(part.blob)
                company_el = root.find(f'{{{_EXT_PROPS_NS}}}Company')
                if company_el is not None:
                    company_el.text = firm_name
                part._blob = etree.tostring(
                    root, xml_declaration=True, encoding='UTF-8', standalone=True
                )
                break

        for sdt in doc.element.body.findall('.//' + qn('w:sdt')):
            alias = sdt.find('.//' + qn('w:alias'))
            if alias is not None and alias.get(qn('w:val')) == 'Company':
                content = sdt.find(qn('w:sdtContent'))
                if content is not None:
                    for t in content.findall('.//' + qn('w:t')):
                        t.text = firm_name
                break

    # ------------------------------------------------------------------
    # Narrative helpers
    # ------------------------------------------------------------------

    def _add_narrative_paragraphs(self, doc, text: str):
        """Add each double-newline-separated paragraph as a Word paragraph, left-aligned."""
        for para in text.split('\n\n'):
            para = para.strip()
            if para:
                p = doc.add_paragraph(para)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # ------------------------------------------------------------------
    # Table helpers — existing
    # ------------------------------------------------------------------

    def _kv_table(self, doc, pairs: list):
        """Two-column key-value table. Skips blank values."""
        visible = [(k, v) for k, v in pairs if v and v.strip()]
        if not visible:
            return
        table = doc.add_table(rows=0, cols=2)
        table.style = 'Table Grid'
        for key, value in visible:
            row = table.add_row()
            row.cells[0].text = key
            row.cells[0].paragraphs[0].runs[0].bold = True
            _shade_cell(row.cells[0], 'F2F2F2')
            row.cells[1].text = value
        _set_col_widths(table, [1.6, 4.9])
        _left_align_table(table)

    def _key_findings_box(self, doc, rows: list):
        """Component B of Executive Summary — Key Findings at a Glance.
        Two-column table: bold label | value. Shading #F2F2F2.
        Outer border removed; thin inner row/column dividers retained.
        rows: list of (label, value) tuples — rows with falsy values are omitted."""
        visible = [(lbl, val) for lbl, val in rows if val]
        if not visible:
            return

        table = doc.add_table(rows=len(visible), cols=2)
        table.style = 'Table Grid'

        # Remove outer table border only (top/left/bottom/right)
        # Inner borders (insideH/insideV) are left to inherit from Table Grid style
        tbl   = table._tbl
        tblPr = tbl.find(qn('w:tblPr'))
        if tblPr is None:
            tblPr = OxmlElement('w:tblPr')
            tbl.insert(0, tblPr)
        tblBorders = OxmlElement('w:tblBorders')
        for edge in ('top', 'left', 'bottom', 'right'):
            b = OxmlElement(f'w:{edge}')
            b.set(qn('w:val'),   'none')
            b.set(qn('w:sz'),    '0')
            b.set(qn('w:space'), '0')
            b.set(qn('w:color'), 'auto')
            tblBorders.append(b)
        tblPr.append(tblBorders)

        for i, (label, value) in enumerate(visible):
            row = table.rows[i]
            _shade_cell(row.cells[0], 'F2F2F2')
            _shade_cell(row.cells[1], 'F2F2F2')
            row.cells[0].text = label
            if row.cells[0].paragraphs[0].runs:
                row.cells[0].paragraphs[0].runs[0].bold = True
            row.cells[1].text = str(value)

        _set_col_widths(table, [1.6, 4.9])
        _left_align_table(table)

    def _how_to_read_page(self, doc, findings: list, firm_name: str):
        """Prefatory 'How to Read This Document' page.
        Title uses a bold paragraph (not a heading style) so it is excluded from
        the Word TOC. Reader guide table rows are generated only for roles whose
        trigger domains have findings in this engagement."""
        # Title — bold 14pt paragraph, not a heading (keeps it off the TOC)
        title_para = doc.add_paragraph()
        title_run  = title_para.add_run('How to Read This Document')
        title_run.bold       = True
        title_run.font.size  = Pt(14)
        title_para.alignment = WD_ALIGN_PARAGRAPH.LEFT

        doc.add_paragraph()

        # Intro paragraph
        finding_domains = {f.get('domain', '') for f in findings if f.get('domain')}
        domain_count    = len(finding_domains)
        intro = doc.add_paragraph(
            f"This diagnostic covers findings across {domain_count} operational domains "
            f"and is intended to be used by multiple members of the {firm_name} leadership "
            f"and delivery team. Not every reader needs to read every section. The table "
            f"below identifies which sections are most relevant to each role."
        )
        intro.alignment = WD_ALIGN_PARAGRAPH.LEFT
        doc.add_paragraph()

        # Reader guide table — 3 columns
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        for i, h in enumerate(['If You Are', 'Priority Reading', 'For Full Detail']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [1.5, 3.0, 2.0])

        for entry in _ROLE_READING_GUIDE:
            if (entry['trigger_domains'] is None
                    or entry['trigger_domains'] & finding_domains):
                row = table.add_row()
                row.cells[0].text = entry['role']
                row.cells[1].text = entry['priority']
                row.cells[2].text = entry['detail']
        _left_align_table(table)

    def _signal_table(self, doc, signals: list):
        """Section 3: Operational Maturity Overview.

        Component A — intro paragraph derived from signal counts.
        Component B — domain summary table with client-readable column names.
          High → Directly Observed | Medium → Reported | Hypothesis → Preliminary
        Component C — evidence basis callout below the table.
        """
        if not signals:
            doc.add_paragraph('No signals recorded.')
            return

        counts = defaultdict(lambda: {'High': 0, 'Medium': 0, 'Hypothesis': 0, 'total': 0})
        for s in signals:
            d = s.get('domain', 'Unknown')
            c = s.get('signal_confidence', 'Medium')
            counts[d][c] = counts[d].get(c, 0) + 1
            counts[d]['total'] += 1

        total_signals = len(signals)
        domain_count  = len(counts)

        # Component A — introduction paragraph
        intro = (
            f"During this engagement, {total_signals} operational signals were identified "
            f"and reviewed across {domain_count} functional domains. "
            "Signals are classified by the strength of supporting evidence: "
            "Directly Observed signals are confirmed by multiple sources or documented "
            "evidence; Reported signals come from a single source and warrant validation "
            "before acting; Preliminary signals are inferred from indirect evidence and "
            "require further investigation before conclusions can be drawn. "
            "Domains with higher concentrations of Directly Observed signals have the "
            "strongest evidentiary basis for their findings."
        )
        p = doc.add_paragraph(intro)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        doc.add_paragraph()

        # Component B — domain summary table (renamed columns, no Evidence Basis column —
        # six-column version exceeds standard page margins; five-column fits at [2.0, 1.0, 1.1, 0.9, 0.9])
        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        for i, h in enumerate(['Domain', 'Signals Reviewed', 'Directly Observed',
                                'Reported', 'Preliminary']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [2.0, 1.0, 1.1, 0.9, 0.9])

        for domain in sorted(counts):
            c = counts[domain]
            row = table.add_row()
            row.cells[0].text = domain
            row.cells[1].text = str(c['total'])
            row.cells[2].text = str(c['High'])
            row.cells[3].text = str(c['Medium'])
            row.cells[4].text = str(c['Hypothesis'])
        _left_align_table(table)

        # Component C — evidence basis callout
        doc.add_paragraph()
        callout = doc.add_paragraph(
            "Domains with a high concentration of Directly Observed signals have the "
            "strongest evidentiary basis for their findings and are ready for immediate "
            "intervention design. Domains where Preliminary signals predominate may benefit "
            "from additional data collection before final recommendations are finalized."
        )
        callout.alignment = WD_ALIGN_PARAGRAPH.LEFT

    def _findings_by_domain(self, doc, findings: list, narrative: dict):
        """Findings grouped by domain.
        Each domain opens with a narrator paragraph, then finding tables, then a closing paragraph."""
        if not findings:
            doc.add_paragraph('No findings recorded.')
            return

        by_domain = defaultdict(list)
        for f in findings:
            by_domain[f.get('domain', 'Unknown')].append(f)

        domain_analysis = narrative.get('domain_analysis', {})

        for domain in sorted(by_domain):
            doc.add_heading(domain, level=2)

            # Primary audience callout — small italic muted line before opening paragraph
            audience = _DOMAIN_AUDIENCE.get(domain)
            if audience:
                callout     = doc.add_paragraph()
                callout_run = callout.add_run(f'Primary audience: {audience}')
                callout_run.italic          = True
                callout_run.font.size       = Pt(9)
                callout_run.font.color.rgb  = RGBColor(0x66, 0x66, 0x66)

            domain_data = domain_analysis.get(domain, {})
            opening = domain_data.get('opening', '') if isinstance(domain_data, dict) else ''
            closing = domain_data.get('closing', '') if isinstance(domain_data, dict) else ''

            if opening:
                doc.add_paragraph(opening)
                doc.add_paragraph()

            for f in by_domain[domain]:
                doc.add_heading(f.get('finding_title', ''), level=3)
                self._kv_table(doc, [
                    ('Confidence',         f.get('confidence') or ''),
                    ('Priority',           f.get('priority') or ''),
                    ('Effort',             f.get('effort') or ''),
                    ('Operational Impact', f.get('operational_impact') or ''),
                    ('Economic Impact',    f.get('economic_impact') or ''),
                    ('Root Cause',         f.get('root_cause') or ''),
                    ('Recommendation',     f.get('recommendation') or ''),
                ])
                doc.add_paragraph()

            if closing:
                doc.add_paragraph(closing)
                doc.add_paragraph()

    # ------------------------------------------------------------------
    # Table helpers — new sections
    # ------------------------------------------------------------------

    def _economic_summary_table(self, doc, findings: list):
        """Section 6 summary table.
        Columns: Finding | Confirmed Exposure | Annual Drag (Inferred) | Recovery Potential

        Confirmed Exposure and Annual Drag are parsed from the finding's economic_impact
        field — every value traces directly to source text. Recovery Potential derives
        from the finding's priority field. A totals row closes the table using the
        Consulting Economics finding as the aggregate drag source."""
        rows_with_impact = [
            f for f in sorted(findings, key=lambda x: PRIORITY_ORDER.get(x.get('priority'), 2))
            if f.get('economic_impact')
        ]
        if not rows_with_impact:
            doc.add_paragraph('No economic impact data recorded for this engagement.')
            return

        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        for i, h in enumerate(['Finding', 'Confirmed Exposure',
                                'Annual Drag (Inferred)', 'Recovery Potential']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [2.0, 1.4, 1.6, 1.5])

        recovery_map = {'High': 'High', 'Medium': 'Medium', 'Low': 'Low'}

        seen_confirmed   = {}   # figure string → first finding_title that used it
        footnote_markers = {}   # figure string → marker symbol
        footnotes        = []   # list of (marker, figure, first_title)
        _markers         = ['*', '**', '†']

        for f in rows_with_impact:
            confirmed, inferred = _parse_economic_figures(f.get('economic_impact', ''))
            primary_confirmed = confirmed.split(', ')[0] if confirmed != '—' else '—'
            primary_inferred  = inferred.split(', ')[0]  if inferred  != '—' else '—'

            # Detect duplicate confirmed figures — same dollar amount in two rows means
            # the same underlying cost is being cited twice, not two separate exposures.
            # Mark the second occurrence; add a footnote below the table.
            display_confirmed = primary_confirmed
            if primary_confirmed != '—':
                if primary_confirmed in seen_confirmed:
                    if primary_confirmed not in footnote_markers:
                        marker = _markers[len(footnote_markers)] if len(footnote_markers) < len(_markers) else '*'
                        footnote_markers[primary_confirmed] = marker
                        footnotes.append((marker, primary_confirmed, seen_confirmed[primary_confirmed]))
                    display_confirmed = f"{primary_confirmed}{footnote_markers[primary_confirmed]}"
                else:
                    seen_confirmed[primary_confirmed] = f.get('finding_title', '')

            row = table.add_row()
            row.cells[0].text = f.get('finding_title') or ''
            row.cells[1].text = display_confirmed
            row.cells[2].text = primary_inferred
            row.cells[3].text = recovery_map.get(f.get('priority', ''), '—')

        # Totals row
        # Confirmed floor: sum unique confirmed figures from seen_confirmed.
        # seen_confirmed holds only first occurrences — duplicates were footnoted above,
        # so this sum does not double-count any underlying cost.
        total_confirmed = '—'
        total_inferred  = '—'

        if seen_confirmed:
            total_val  = 0.0
            parseable  = False
            for fig in seen_confirmed:
                val = _dollar_to_float(fig)
                if val is not None:
                    total_val += val
                    parseable  = True
            if parseable:
                if total_val >= 1_000_000:
                    formatted = f'~${total_val / 1_000_000:.1f}M'
                else:
                    formatted = f'~${int(round(total_val / 1000))}K'
                total_confirmed = f'{formatted}+ confirmed floor'

        # Annual Drag: use aggregate inferred range from Consulting Economics finding if present.
        # If none exists, leave as '—' — do not fabricate an aggregate.
        econ_finding = next(
            (f for f in findings
             if f.get('domain') == 'Consulting Economics' and f.get('economic_impact')),
            None
        )
        if econ_finding:
            _, inf_str = _parse_economic_figures(econ_finding['economic_impact'])
            if inf_str != '—':
                parts      = [p.strip() for p in inf_str.split(', ')]
                range_parts = [p for p in parts if '–' in p]
                drag_range  = range_parts[0] if range_parts else parts[0]
                total_inferred = f'{drag_range} INFERRED annually'

        totals_row = table.add_row()
        for cell in totals_row.cells:
            _shade_cell(cell, 'F2F2F2')
        totals_row.cells[0].text = 'Total Identified Exposure'
        if totals_row.cells[0].paragraphs[0].runs:
            totals_row.cells[0].paragraphs[0].runs[0].bold = True
        totals_row.cells[1].text = total_confirmed
        totals_row.cells[2].text = total_inferred
        totals_row.cells[3].text = '—'

        _left_align_table(table)

        # Footnotes for duplicate confirmed figures — rendered as italic text below the table
        for marker, figure, first_title in footnotes:
            fn = doc.add_paragraph(
                f'{marker} {figure} also appears in "{first_title}" — '
                f'these represent the same underlying cost, not separate exposures. Do not sum.'
            )
            fn.runs[0].italic = True

    def _future_state_table(self, doc, rows: list):
        """Section 7 future state metrics table.
        Columns: Metric | Current State | Benchmark | Target"""
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        for i, h in enumerate(['Metric', 'Current State', 'Benchmark', 'Target']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [1.5, 1.5, 1.5, 2.0])

        for r in rows:
            if not isinstance(r, dict):
                continue
            row = table.add_row()
            metric = r.get('metric') or ''
            sourced = r.get('sourced_from', '')
            label = f' ({sourced})' if sourced else ''
            row.cells[0].text = metric + label
            row.cells[1].text = r.get('current_state') or ''
            row.cells[2].text = r.get('benchmark') or ''
            row.cells[3].text = r.get('target') or ''
        _left_align_table(table)

    def _priority_zero_table(self, doc, rows: list):
        """Section 8.1 Priority Zero table.
        Columns: Action | Owner | What This Unblocks"""
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        for i, h in enumerate(['Action', 'Owner', 'What This Unblocks']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [2.5, 1.2, 2.8])

        for r in rows:
            if not isinstance(r, dict):
                continue
            row = table.add_row()
            row.cells[0].text = r.get('action') or ''
            row.cells[1].text = r.get('owner') or ''
            row.cells[2].text = r.get('what_it_unblocks') or ''
        _left_align_table(table)

    def _roadmap_overview_table(self, doc, rows: list):
        """Section 8.2 Roadmap Overview table.
        Columns: Phase | Timeline | Key Outcomes"""
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        for i, h in enumerate(['Phase', 'Timeline', 'Key Outcomes']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [1.0, 1.2, 4.3])

        for r in rows:
            if not isinstance(r, dict):
                continue
            row = table.add_row()
            row.cells[0].text = r.get('phase') or ''
            row.cells[1].text = r.get('timeline') or ''
            outcomes = r.get('key_outcomes', [])
            if isinstance(outcomes, list):
                row.cells[2].text = '\n'.join(f'• {o}' for o in outcomes if o)
            else:
                row.cells[2].text = str(outcomes)
        _left_align_table(table)

    def _roadmap_phase_table(self, doc, items: list, findings_by_id: dict,
                              initiative_details: dict):
        """Sections 8.3/8.4/8.5 phase tables.
        Columns: Initiative | Priority | Effort | Owner | Timeline | Success Metric
        Economic Impact column omitted — roadmap-to-finding linkage not yet built.
        Add back when addressing_finding_ids is implemented in Roadmap Enhancements."""
        table = doc.add_table(rows=1, cols=6)
        table.style = 'Table Grid'
        headers = ['Initiative', 'Priority', 'Effort', 'Owner', 'Timeline', 'Success Metric']
        for i, h in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [1.8, 0.6, 0.6, 0.9, 0.9, 1.7])

        for item in items:
            item_id = item.get('item_id', '')
            details = initiative_details.get(item_id, {})

            row = table.add_row()
            row.cells[0].text = item.get('initiative_name') or ''
            row.cells[1].text = item.get('priority') or ''
            row.cells[2].text = item.get('effort') or ''
            row.cells[3].text = item.get('owner') or ''
            row.cells[4].text = details.get('timeline', '') or ''
            row.cells[5].text = details.get('success_metric', '') or ''
        _left_align_table(table)

    def _dependency_table(self, doc, rows: list):
        """Section 8.6 Initiative Dependencies table.
        Columns: Initiative | Depends On"""
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        for i, h in enumerate(['Initiative', 'Depends On']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [3.2, 3.3])

        for r in rows:
            if not isinstance(r, dict):
                continue
            row = table.add_row()
            row.cells[0].text = r.get('initiative') or ''
            row.cells[1].text = r.get('depends_on') or ''
        _left_align_table(table)

    def _risk_table(self, doc, rows: list):
        """Section 8.7 Key Risks table.
        Columns: Risk | Likelihood | Mitigation"""
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        for i, h in enumerate(['Risk', 'Likelihood', 'Mitigation']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [2.5, 0.8, 3.2])

        for r in rows:
            if not isinstance(r, dict):
                continue
            row = table.add_row()
            row.cells[0].text = r.get('risk') or ''
            row.cells[1].text = r.get('likelihood') or ''
            row.cells[2].text = r.get('mitigation') or ''
        _left_align_table(table)

    def _next_steps_table(self, doc, rows: list):
        """Section 9 Immediate Next Steps table.
        Columns: Action | Owner | Completion Criteria"""
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        for i, h in enumerate(['Action', 'Owner', 'Completion Criteria']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [2.5, 1.2, 2.8])

        for r in rows[:10]:  # cap at 10 rows per spec
            if not isinstance(r, dict):
                continue
            row = table.add_row()
            row.cells[0].text = r.get('action') or ''
            row.cells[1].text = r.get('owner') or ''
            row.cells[2].text = r.get('completion_criteria') or ''
        _left_align_table(table)
