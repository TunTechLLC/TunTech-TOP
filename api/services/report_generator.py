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
# Section map — single source of truth for section numbers.
# Update only here when sections are added, removed, or reordered.
# Only sections referenced by number in the reader guide need entries.
# -------------------------------------------------------------------

_SECTION_MAP = {
    'domain_analysis':   6,
    'root_cause':        7,
    'economic_impact':   8,
    'future_state':      9,
    'roadmap':           10,
    'priority_zero':     '10.1',
    'roadmap_overview':  '10.2',
    'stabilize':         '10.3',
    'optimize':          '10.4',
    'scale':             '10.5',
    'dependencies':      '10.6',
    'risks':             '10.7',
    'what_happens_next': 11,
}

# -------------------------------------------------------------------
# Reader guide — priority/detail are format strings resolved against
# _SECTION_MAP at render time. Change section numbers in _SECTION_MAP
# only — the guide strings update automatically.
# -------------------------------------------------------------------

_ROLE_READING_GUIDE = [
    {
        'role':            'CEO / Founder',
        'priority':        'Executive Summary, Section {s[priority_zero]}, Section {s[what_happens_next]}',
        'detail':          'Section {s[future_state]} (Future State)',
        'trigger_domains': None,
    },
    {
        'role':            'Director of Delivery',
        'priority':        'Section {s[domain_analysis]} (Delivery Operations, Project Governance, Resource Management), Section {s[stabilize]}',
        'detail':          'Sections {s[root_cause]}, {s[optimize]}, {s[risks]}',
        'trigger_domains': {'Delivery Operations', 'Project Governance / PMO', 'Resource Management'},
    },
    {
        'role':            'VP Sales / Business Development',
        'priority':        'Section {s[domain_analysis]} (Sales & Pipeline, Sales-to-Delivery Transition), Section {s[stabilize]}',
        'detail':          'Section {s[dependencies]} (Dependencies)',
        'trigger_domains': {'Sales & Pipeline', 'Sales-to-Delivery Transition'},
    },
    {
        'role':            'Finance Lead',
        'priority':        'Section {s[domain_analysis]} (Finance and Commercial, Consulting Economics), Section {s[economic_impact]}',
        'detail':          'Sections {s[stabilize]}, {s[optimize]}',
        'trigger_domains': {'Finance and Commercial', 'Consulting Economics'},
    },
    {
        'role':            'Project Manager / Senior Consultant',
        'priority':        'Section {s[what_happens_next]} (What Happens Next), Section {s[stabilize]}',
        'detail':          'Section {s[risks]} (Key Risks)',
        'trigger_domains': None,
    },
    {
        'role':            'Operations / Admin',
        'priority':        'Section {s[domain_analysis]} (AI Readiness, Human Resources), Section {s[optimize]}',
        'detail':          'Section {s[what_happens_next]}',
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
        roadmap_by_id  = {
            item['item_id']: item.get('initiative_name', '')
            for item in roadmap if item.get('item_id')
        }
        initiative_details = {
            d['item_id']: d
            for d in narrative.get('initiative_details', [])
            if isinstance(d, dict) and d.get('item_id')
        }

        # Executive Briefing — unnumbered standalone page, before all numbered sections
        self._build_executive_briefing(doc, findings, narrative)

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
        # Revenue at Risk — sourced from Sales-to-Delivery Transition or Sales & Pipeline
        # confirmed figure; avoids summing across domains (which produces an unverifiable total).
        revenue_at_risk = None
        for _domain in ('Sales-to-Delivery Transition', 'Sales & Pipeline'):
            _rev_f = next(
                (f for f in findings
                 if f.get('domain') == _domain and f.get('economic_impact')),
                None
            )
            if _rev_f:
                _conf, _ = _parse_economic_figures(_rev_f.get('economic_impact', ''))
                if _conf != '—':
                    revenue_at_risk = _conf.split(', ')[0]
                    break
        if revenue_at_risk:
            kf_rows.append(('Revenue at Risk', revenue_at_risk))
        high_findings   = [f for f in findings if f.get('priority') == 'High']
        primary_finding = high_findings[0] if high_findings else (findings[0] if findings else None)
        if primary_finding and primary_finding.get('root_cause'):
            rc  = primary_finding['root_cause']
            dot = rc.find('. ')
            cause_line = (rc[:dot] if dot > 0 else rc).strip()
            if cause_line:
                kf_rows.append(('Primary Cause', cause_line))
        pz_rows = narrative.get('priority_zero_table_rows', [])
        if pz_rows and isinstance(pz_rows, list) and pz_rows[0].get('action'):
            kf_rows.append(('Act This Week', pz_rows[0]['action']))
        fs_rows = narrative.get('future_state_table_rows', [])
        if fs_rows and isinstance(fs_rows, list):
            # Prefer gross margin row — named metric with current baseline makes the
            # target concrete. Fall back to first row if no gross margin row exists.
            _gm_row = next(
                (r for r in fs_rows
                 if isinstance(r, dict) and 'gross margin' in (r.get('metric') or '').lower()),
                None
            )
            _target_row = _gm_row or (fs_rows[0] if isinstance(fs_rows[0], dict) else None)
            if _target_row and _target_row.get('target'):
                _label = '18-Month Gross Margin Target' if _gm_row else '18-Month Target'
                _current = _target_row.get('current_state', '')
                _val = (_target_row['target'] + f' (currently {_current})'
                        if _current else _target_row['target'])
                kf_rows.append((_label, _val))
        if kf_rows:
            self._key_findings_box(doc, kf_rows)
            doc.add_paragraph()

        # Component C — three short narrative paragraphs (narrator, no CONFIRMED/INFERRED)
        for key in ('executive_summary_para1', 'executive_summary_para2',
                    'executive_summary_para3'):
            para_text = narrative.get(key, '')
            if para_text:
                self._add_narrative_paragraphs(doc, para_text)

        doc.add_paragraph()

        # How to Read This Document — standalone page between Exec Summary and Engagement Overview.
        # Appears in TOC (heading style) but without a section number (w:numPr stripped).
        # Page break before it ensures it starts on its own page.
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

        # 6 — Economic Impact Analysis (chart + summary table + prose)
        doc.add_heading('Economic Impact Analysis', level=1)

        chart_path = self._generate_economic_chart(findings)
        if chart_path:
            try:
                doc.add_picture(chart_path, width=Inches(6))
                caption = doc.add_paragraph(
                    'Confirmed exposures only. See table below for full economic '
                    'impact including inferred figures.'
                )
                caption.runs[0].italic = True
                caption.runs[0].font.size = Pt(9)
                caption.alignment = WD_ALIGN_PARAGRAPH.LEFT
                doc.add_paragraph()
            except Exception as e:
                logger.warning(f'Failed to embed economic chart: {e}')
            finally:
                try:
                    os.remove(chart_path)
                except OSError:
                    pass

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
            self._dependency_table(doc, dep_rows, roadmap_by_id)
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
    # Executive Briefing — standalone CEO teaser page
    # ------------------------------------------------------------------

    def _build_executive_briefing(self, doc, findings: list, narrative: dict):
        """One-page standalone briefing shown to the CEO before the full report.

        Content sourcing:
          Headline    — executive_briefing.headline from Narrator; falls back to first
                        sentence of executive_summary_opening.
          Problems    — executive_briefing.problems from Narrator: plain_title (5 words)
                        and impact_brief (20 words). finding_id validated against DB.
          Numbers     — executive_briefing.numbers from Narrator: label (4 words) and
                        finding_id. Dollar figure sourced from DB via _parse_economic_figures()
                        — CONFIRMED only. finding_id validated against DB.
          Actions     — priority_zero_table_rows[0:3] from existing Narrator output.

        Visual: bold paragraph header anchors each block; spacer paragraphs between blocks.
        Page break after ensures the briefing always occupies its own page.
        """
        findings_by_id = {f['finding_id']: f for f in findings if f.get('finding_id')}
        eb = narrative.get('executive_briefing') or {}

        # Heading — Heading 1 so it appears in TOC; section number suppressed
        heading_para = doc.add_heading('Executive Briefing', level=1)
        pPr = heading_para._p.get_or_add_pPr()
        numPr = pPr.find(qn('w:numPr'))
        if numPr is not None:
            pPr.remove(numPr)

        doc.add_paragraph()

        # Component A — Headline
        headline = eb.get('headline', '').strip()
        if not headline:
            opening = narrative.get('executive_summary_opening', '')
            dot = opening.find('. ')
            headline = (opening[:dot + 1] if dot > 0 else opening).strip()
        if headline:
            p = doc.add_paragraph()
            run = p.add_run(headline)
            run.bold = True
            run.font.size = Pt(13)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

            # Thin horizontal rule separates the opening statement from the three blocks
            rule = doc.add_paragraph()
            pPr = rule._p.get_or_add_pPr()
            pBdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), '6')      # 0.75pt line
            bottom.set(qn('w:space'), '1')
            bottom.set(qn('w:color'), 'auto')
            pBdr.append(bottom)
            pPr.append(pBdr)

        # Component B — Three Critical Problems
        # Narrator supplies plain_title + impact_brief per finding_id.
        # finding_id validated against DB — invalid IDs are skipped silently.
        raw_problems = eb.get('problems', [])
        problem_rows = []
        for item in (raw_problems[:3] if isinstance(raw_problems, list) else []):
            if not isinstance(item, dict):
                continue
            fid          = item.get('finding_id', '')
            plain_title  = item.get('plain_title', '').strip()
            impact_brief = item.get('impact_brief', '').strip()
            if not plain_title or not impact_brief:
                continue
            if fid not in findings_by_id:
                logger.warning(
                    f"Executive briefing: problem finding_id {fid!r} not in findings — skipping"
                )
                continue
            problem_rows.append((plain_title, impact_brief))

        if problem_rows:
            self._briefing_block_header(doc, 'Three Critical Problems')
            tbl = doc.add_table(rows=0, cols=1)
            tbl.style = 'Table Grid'
            for plain_title, impact_brief in problem_rows:
                row = tbl.add_row()
                cell = row.cells[0]
                # First paragraph — bold title
                title_para = cell.paragraphs[0]
                title_para.clear()
                title_run = title_para.add_run(plain_title)
                title_run.bold = True
                title_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                # Second paragraph — normal-weight impact sentence
                impact_para = cell.add_paragraph()
                impact_para.add_run(impact_brief)
                impact_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _set_col_widths(tbl, [6.5])
            _left_align_table(tbl)

        # Component C — Three Numbers That Matter
        # Narrator supplies label + finding_id (ordered by urgency: immediate → structural → existential).
        # Dollar figure sourced from DB — CONFIRMED only. Invalid or INFERRED entries are skipped.
        raw_numbers = eb.get('numbers', [])
        number_rows = []
        for item in (raw_numbers[:3] if isinstance(raw_numbers, list) else []):
            if not isinstance(item, dict):
                continue
            fid   = item.get('finding_id', '')
            label = item.get('label', '').strip()
            if not label:
                continue
            if fid not in findings_by_id:
                logger.warning(
                    f"Executive briefing: number finding_id {fid!r} not in findings — skipping"
                )
                continue
            conf_str, _ = _parse_economic_figures(
                findings_by_id[fid].get('economic_impact', '')
            )
            if conf_str == '—':
                logger.warning(
                    f"Executive briefing: finding {fid} has no CONFIRMED figure — skipping number row"
                )
                continue
            primary = conf_str.split(', ')[0]
            number_rows.append((label, primary))

        if number_rows:
            self._briefing_block_header(doc, 'Three Numbers That Matter')
            tbl = doc.add_table(rows=0, cols=2)
            tbl.style = 'Table Grid'
            for label, amount in number_rows:
                row = tbl.add_row()
                row.cells[0].text = label
                row.cells[1].text = amount
                if row.cells[1].paragraphs[0].runs:
                    row.cells[1].paragraphs[0].runs[0].bold = True
            _set_col_widths(tbl, [4.5, 2.0])
            _left_align_table(tbl)

        # Component D — What Must Happen This Week
        pz_source = narrative.get('priority_zero_table_rows', [])
        action_rows = [
            r for r in (pz_source[:3] if isinstance(pz_source, list) else [])
            if isinstance(r, dict) and r.get('action')
        ]

        if action_rows:
            self._briefing_block_header(doc, 'What Must Happen This Week')
            tbl = doc.add_table(rows=0, cols=1)
            tbl.style = 'Table Grid'
            for r in action_rows:
                row = tbl.add_row()
                row.cells[0].text = r['action']
            _set_col_widths(tbl, [6.5])
            _left_align_table(tbl)

        # Page break after — briefing always occupies its own page
        doc.add_page_break()

    # ------------------------------------------------------------------
    # Narrative helpers
    # ------------------------------------------------------------------

    def _briefing_block_header(self, doc, text: str):
        """Styled section anchor for Executive Briefing blocks.
        Bold, 11pt, all caps, 14pt space before, 4pt space after."""
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.bold           = True
        run.font.size      = Pt(11)
        run.font.all_caps  = True
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after  = Pt(4)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

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
        Title uses Heading 1 style (appears in Word TOC) with section number
        suppressed via w:numPr removal and a page break forced before it.
        Reader guide table rows are generated only for roles whose trigger
        domains have findings in this engagement."""
        # Title — Heading 1 so it appears in TOC; numPr stripped to suppress
        # section number; pageBreakBefore forces it onto its own page.
        heading_para = doc.add_heading('How to Read This Document', level=1)
        pPr = heading_para._p.get_or_add_pPr()
        numPr = pPr.find(qn('w:numPr'))
        if numPr is not None:
            pPr.remove(numPr)
        pbBefore = OxmlElement('w:pageBreakBefore')
        pbBefore.set(qn('w:val'), 'true')
        pPr.append(pbBefore)

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
                row.cells[1].text = entry['priority'].format(s=_SECTION_MAP)
                row.cells[2].text = entry['detail'].format(s=_SECTION_MAP)
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

    def _generate_economic_chart(self, findings: list):
        """Generate a horizontal bar chart of confirmed economic exposure by finding.

        Uses the same deduplication logic as _economic_summary_table — seen_confirmed
        ensures duplicated figures produce only one bar (primary occurrence wins).
        Only findings with a parseable confirmed figure receive a bar.

        Returns the path to a temporary PNG file, or None if generation fails or
        there is no chart-worthy data. Caller must delete the file after embedding.
        """
        try:
            import matplotlib
            matplotlib.use('Agg')   # non-interactive backend — no display required
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning('matplotlib not installed — skipping economic chart')
            return None

        try:
            # Build chart data — same priority sort and dedup as _economic_summary_table
            seen_confirmed: dict = {}
            chart_data: list = []
            for f in sorted(findings,
                            key=lambda x: PRIORITY_ORDER.get(x.get('priority'), 2)):
                conf_str, _ = _parse_economic_figures(f.get('economic_impact', ''))
                if conf_str == '—':
                    continue
                primary = conf_str.split(', ')[0]
                if primary in seen_confirmed:
                    continue                     # duplicate figure — skip
                seen_confirmed[primary] = True
                val = _dollar_to_float(primary)
                if val is None:
                    continue
                raw_title = f.get('finding_title') or ''
                label = raw_title[:40] + ('...' if len(raw_title) > 40 else '')
                chart_data.append((label, val))

            if not chart_data:
                return None

            def _fmt(v: float) -> str:
                if v >= 1_000_000:
                    return f'${v / 1_000_000:.1f}M'
                return f'${int(round(v / 1000))}K'

            # Sort ascending — barh draws bottom-to-top, so largest ends up at top
            chart_data.sort(key=lambda x: x[1])
            labels = [d[0] for d in chart_data]
            values = [d[1] for d in chart_data]
            max_val = max(values)

            n = len(chart_data)
            fig, ax = plt.subplots(figsize=(8, max(3.0, n * 0.6)))

            bars = ax.barh(labels, values, color='#1F3864', height=0.5)

            # Value label at the end of each bar
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_width() + max_val * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    _fmt(val),
                    va='center', ha='left', fontsize=9,
                )

            ax.set_xlabel('Confirmed Exposure')
            ax.set_xlim(0, max_val * 1.20)      # headroom for value labels
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.yaxis.grid(False)
            ax.xaxis.grid(False)
            ax.tick_params(left=False)
            ax.xaxis.set_major_formatter(
                plt.FuncFormatter(lambda v, _: _fmt(v))
            )

            plt.tight_layout()

            tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            tmp_path = tmp.name
            tmp.close()
            fig.savefig(tmp_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            return tmp_path

        except Exception as exc:
            logger.warning(f'Economic chart generation failed: {exc} — skipping chart')
            return None

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
            for fig, fig_title in seen_confirmed.items():
                # Exclude concentration and relationship-risk findings — these represent
                # structural exposure (e.g. revenue concentration), not a directly
                # recoverable cost. Including them inflates the total vs. what intervention
                # can realistically address.
                _title_low = (fig_title or '').lower()
                if 'concentration' in _title_low or 'relationship risk' in _title_low:
                    continue
                val = _dollar_to_float(fig)
                if val is not None:
                    total_val += val
                    parseable  = True
            if parseable:
                if total_val >= 1_000_000:
                    formatted = f'~${total_val / 1_000_000:.1f}M'
                else:
                    formatted = f'~${int(round(total_val / 1000))}K'
                total_confirmed = f'{formatted}+ (non-overlapping direct exposures)'

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

    def _dependency_table(self, doc, rows: list, roadmap_by_id: dict | None = None):
        """Section 8.6 Initiative Dependencies table.
        Columns: Initiative | Depends On
        roadmap_by_id: item_id → initiative_name mapping used to resolve R-code
        references the narrator emits (e.g. 'R066') into human-readable names."""
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        for i, h in enumerate(['Initiative', 'Depends On']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [3.2, 3.3])

        def _resolve_rcodes(text: str) -> str:
            if not roadmap_by_id or not text:
                return text
            def _sub(m):
                return roadmap_by_id.get(m.group(0), m.group(0))
            return re.sub(r'\bR\d+\b', _sub, text)

        for r in rows:
            if not isinstance(r, dict):
                continue
            row = table.add_row()
            row.cells[0].text = _resolve_rcodes(r.get('initiative') or '')
            row.cells[1].text = _resolve_rcodes(r.get('depends_on') or '')
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
