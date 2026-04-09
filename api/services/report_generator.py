import os
import re
import json
import logging
import tempfile
from collections import defaultdict
from copy import deepcopy

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


def _resolve_initiative_codes(text: str, roadmap_by_id: dict | None) -> str:
    """Replace R-code references (e.g. R060, R065) with plain initiative names.
    Shared by the dependency table and key risks table.
    roadmap_by_id: item_id → initiative_name mapping built in _build()."""
    if not roadmap_by_id or not text:
        return text
    return re.sub(r'\bR\d+\b', lambda m: roadmap_by_id.get(m.group(0), m.group(0)), text)

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
        'domain_order':    None,
    },
    {
        'role':            'Director of Delivery',
        'priority':        'Section {s[domain_analysis]}{domain_clause}, Section {s[stabilize]}',
        'detail':          'Sections {s[root_cause]}, {s[optimize]}, {s[risks]}',
        'trigger_domains': {
            'Delivery Operations', 'Project Governance / PMO',
            'Resource Management', 'Customer Experience',
        },
        'domain_order':    [
            'Delivery Operations', 'Project Governance / PMO',
            'Resource Management', 'Customer Experience',
        ],
    },
    {
        'role':            'VP Sales / Business Development',
        'priority':        'Section {s[domain_analysis]}{domain_clause}, Section {s[stabilize]}',
        'detail':          'Section {s[dependencies]} (Dependencies)',
        'trigger_domains': {'Sales & Pipeline', 'Sales-to-Delivery Transition'},
        'domain_order':    ['Sales & Pipeline', 'Sales-to-Delivery Transition'],
    },
    {
        'role':            'Finance Lead',
        'priority':        'Section {s[domain_analysis]}{domain_clause}, Section {s[economic_impact]}',
        'detail':          'Sections {s[stabilize]}, {s[optimize]}',
        'trigger_domains': {'Finance and Commercial', 'Consulting Economics'},
        'domain_order':    ['Finance and Commercial', 'Consulting Economics'],
    },
    {
        'role':            'Project Manager / Senior Consultant',
        'priority':        'Section {s[what_happens_next]} (What Happens Next), Section {s[stabilize]}',
        'detail':          'Section {s[risks]} (Key Risks)',
        'trigger_domains': None,
        'domain_order':    None,
    },
    {
        'role':            'Operations / Admin',
        'priority':        'Section {s[domain_analysis]}{domain_clause}, Section {s[optimize]}',
        'detail':          'Section {s[what_happens_next]}',
        'trigger_domains': {'AI Readiness', 'Human Resources'},
        'domain_order':    ['AI Readiness', 'Human Resources'],
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
        conf, _, _ = _parse_economic_figures(f.get('economic_impact', ''))
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
_DERIVED_RE   = re.compile(r'\bDERIVED(?:-\w+)?',   re.IGNORECASE)
_INFERRED_RE  = re.compile(r'\bINFERRED(?:-\w+)?',  re.IGNORECASE)


def _is_label_context(clause: str, pos: int, matched_text: str) -> bool:
    """Return True only when a CONFIRMED/DERIVED/INFERRED label at `pos` is being
    used as an economic label rather than as an adjective modifier.

    Two valid label contexts:
    1. All-uppercase form (CONFIRMED, DERIVED, INFERRED, CONFIRMED-QUALIFIED) —
       the canonical form produced by the extraction prompts.
    2. Mixed/lowercase preceded by a delimiter (open paren, colon, dash, comma).

    Adjective uses like '$9.2M confirmed revenue' or '$185 confirmed target' are
    always lowercase with only whitespace before them — they fail both tests and
    are excluded. This prevents annual-revenue reference figures from being summed
    as if they were direct exposure claims.
    """
    if matched_text.isupper():      # canonical label form — accept regardless of position
        return True
    if pos == 0:                    # label at start of clause — treat as label
        return True
    pre = clause[max(0, pos - 5):pos].rstrip()
    if not pre:
        return True
    return bool(re.search(r'[\(\:\,\-\u2014\u2013]$', pre))


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


def _parse_display_figure_to_float(display_figure: str | None) -> float | None:
    """Parse a display_figure string to float for sorting and summing.

    Handles: '$526K', '~$1.1M', '\u26a0 $12M', '$35K\u2013$55K',
             '$186K \u2014 shared, see note'.

    Rules:
    - Strip leading warning prefix ('\u26a0 ')
    - Strip trailing note after em-dash separator (shared figure labels)
    - Range lower bound and K/M suffix handling delegated to _dollar_to_float
    - Returns None if parsing fails or input is None/empty. Never raises.
    """
    if not display_figure:
        return None
    s = display_figure.strip()
    if s.startswith('\u26a0 '):
        s = s[2:].strip()
    m = re.search(r'\s*\u2014', s)
    if m:
        s = s[:m.start()].strip()
    return _dollar_to_float(s)


def _parse_economic_figures(text: str):
    """Parse an economic_impact string into (confirmed, derived, inferred) figure strings.

    Handles label variants: CONFIRMED, CONFIRMED-QUALIFIED, DERIVED, INFERRED, INFERRED-UNVALIDATED.
    Labels must appear AFTER the dollar amount (within 80 chars) to be assigned to it.
    This prevents adjective uses like "confirmed overrun exposure: $85K" from incorrectly
    assigning the label to dollar amounts that appear before it in a noun phrase.

    Label precedence when multiple labels follow the same amount: CONFIRMED > DERIVED > INFERRED.
    Returns '—' for each column when no matching figures are found.
    """
    if not text:
        return '—', '—', '—'

    confirmed_figures = []
    derived_figures   = []
    inferred_figures  = []

    # Split on sentence boundaries — use '. ' (period + space) to avoid splitting
    # decimal numbers like $1.5M, and also split on semicolons and newlines.
    clauses = re.split(r'\.\s+|\.\s*$|;\s*|\n', text)

    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue

        conf_positions = [m.start() for m in _CONFIRMED_RE.finditer(clause)
                          if _is_label_context(clause, m.start(), m.group(0))]
        deriv_positions = [m.start() for m in _DERIVED_RE.finditer(clause)
                           if _is_label_context(clause, m.start(), m.group(0))]
        inf_positions  = [m.start() for m in _INFERRED_RE.finditer(clause)
                          if _is_label_context(clause, m.start(), m.group(0))]

        if not conf_positions and not deriv_positions and not inf_positions:
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
            conf_after  = [p for p in conf_positions  if p >= amt_end]
            deriv_after = [p for p in deriv_positions if p >= amt_end]
            inf_after   = [p for p in inf_positions   if p >= amt_end]

            d_conf  = min((p - amt_end for p in conf_after),  default=9999)
            d_deriv = min((p - amt_end for p in deriv_after), default=9999)
            d_inf   = min((p - amt_end for p in inf_after),   default=9999)

            closest = min(d_conf, d_deriv, d_inf)

            # Require label within 80 chars to avoid false positives
            if closest > 80:
                continue

            # Formula-input guard: if amt appears inside the parenthetical that
            # contains the winning label (e.g. "(DERIVED: 15% × $9.2M)"), it is
            # a calculation input cited in the formula, not the result being labelled.
            # Skip it so the actual result (the dollar amount before the paren) wins.
            if d_conf <= d_deriv and d_conf <= d_inf:
                _win_pos = amt_end + d_conf
            elif d_deriv <= d_inf:
                _win_pos = amt_end + d_deriv
            else:
                _win_pos = amt_end + d_inf

            _paren_open  = clause.rfind('(', 0, _win_pos)
            _paren_close = clause.find(')',  _win_pos)
            if (_paren_open != -1 and _paren_close != -1
                    and amt in clause[_paren_open:_paren_close]):
                continue  # amt is a formula input, not the result

            # Assign to the closest label; CONFIRMED > DERIVED > INFERRED on tie
            if d_conf <= d_deriv and d_conf <= d_inf:
                if amt not in confirmed_figures:
                    confirmed_figures.append(amt)
            elif d_deriv <= d_inf:
                if amt not in derived_figures:
                    derived_figures.append(amt)
            else:
                if amt not in inferred_figures:
                    inferred_figures.append(amt)

    # Cap at 3 figures per column so cells remain readable
    confirmed = ', '.join(confirmed_figures[:3]) if confirmed_figures else '—'
    derived   = ', '.join(derived_figures[:3])   if derived_figures   else '—'
    inferred  = ', '.join(inferred_figures[:3])  if inferred_figures  else '—'
    return confirmed, derived, inferred


# Domain → figure_type mapping for display figure pre-population
_DOMAIN_TO_FIGURE_TYPE = {
    'Consulting Economics':         'annual_drag',
    'Finance and Commercial':       'annual_drag',
    'Sales & Pipeline':             'concentration_risk',
    'Sales-to-Delivery Transition': 'direct_exposure',
    'Delivery Operations':          'direct_exposure',
    'Project Governance / PMO':     'direct_exposure',
    'Resource Management':          'replacement_cost',
    'Customer Experience':          'direct_exposure',
    'AI Readiness':                 'opportunity',
    'Human Resources':              'replacement_cost',
}


def _format_display_figure(raw: str) -> str:
    """Convert a raw extracted dollar string to compact display format.
    "$526,000" -> "$526K", "$1,200,000" -> "$1.2M", "$526K" -> "$526K" (pass-through).
    """
    val = _dollar_to_float(raw)
    if val is None:
        return raw
    if val >= 1_000_000:
        n = val / 1_000_000
        s = f"{n:.1f}"
        if s.endswith('.0'):
            s = s[:-2]
        return f"${s}M"
    if val >= 1_000:
        return f"${val / 1_000:.0f}K"
    return f"${val:.0f}"


def _prepopulate_display_figure(
    economic_impact_text: str,
    domain: str,
    confirmed_revenue: float | None,
    finding_title: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    """Extract a suggested display_figure, display_label, and figure_type
    from economic_impact text.

    Returns (display_figure, display_label, figure_type) or (None, None, None)
    if no extractable figure exists.

    Guardrail: if the parsed numeric value exceeds confirmed_revenue (when provided),
    prepend a warning prefix to display_figure so the frontend can show a red warning.
    If confirmed_revenue is None, skip the guardrail silently.
    """
    if not economic_impact_text:
        return None, None, None

    confirmed_str, derived_str, inferred_str = _parse_economic_figures(economic_impact_text)

    # Highest-confidence non-empty figure: CONFIRMED > DERIVED > INFERRED
    if confirmed_str != '\u2014':
        raw = confirmed_str.split(', ')[0]
    elif derived_str != '\u2014':
        raw = derived_str.split(', ')[0]
    elif inferred_str != '\u2014':
        raw = inferred_str.split(', ')[0]
    else:
        return None, None, None

    display_figure = _format_display_figure(raw)

    # Guardrail: flag if figure exceeds confirmed annual revenue
    if confirmed_revenue is not None:
        numeric = _dollar_to_float(raw)
        if numeric is not None and numeric > confirmed_revenue:
            display_figure = f'\u26a0 {display_figure}'

    figure_type   = _DOMAIN_TO_FIGURE_TYPE.get(domain, 'direct_exposure')
    display_label = ' '.join(finding_title.split()[:6]) if finding_title else None

    return display_figure, display_label, figure_type


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

        # Build cross-reference strings from _SECTION_MAP — single source of truth.
        # Passed to the narrator so the prompt never hardcodes section numbers.
        section_refs = {
            'domain_analysis_ref': (
                f"(see Section {_SECTION_MAP['domain_analysis']} — Domain Analysis for full findings)"
            ),
            'economic_impact_ref': (
                f"(see Section {_SECTION_MAP['economic_impact']} — Economic Impact Analysis)"
            ),
            'priority_zero_ref': (
                f"(see Section {_SECTION_MAP['priority_zero']} — Priority Zero Actions)"
            ),
        }

        narrative = await generate_report_narrative(
            synth_output, findings, roadmap, eng,
            interview_roles=interview_roles,
            document_types=document_types,
            total_signals=total_signals,
            domain_count=domain_count,
            section_refs=section_refs,
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
        self._add_cover_page_restriction(doc)

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
        self._build_executive_briefing(doc, findings, narrative, roadmap_by_id)

        # 1 — Executive Summary (four components — Change 1)
        doc.add_heading('Executive Summary', level=1)

        # Component A — 3-4 sentence opening paragraph (narrator)
        opening = narrative.get('executive_summary_opening', '')
        if opening:
            self._add_narrative_paragraphs(doc, _resolve_initiative_codes(opening, roadmap_by_id))
            doc.add_paragraph()

        # Component B — Key Findings at a Glance (sourced from structured data only)
        kf_rows = []
        margin_trend = narrative.get('margin_trend_brief', '')
        if margin_trend:
            kf_rows.append(('Margin Trend', margin_trend))
        # Revenue at Risk — sourced from structured display fields.
        # Preference order: direct_exposure findings (summed if multiple), then largest
        # of any include_in_executive finding, then placeholder.
        _exec_with_fig = [
            f for f in findings
            if f.get('include_in_executive') and f.get('display_figure')
        ]
        _direct = [f for f in _exec_with_fig if f.get('figure_type') == 'direct_exposure']
        _rar_label = 'Revenue at Risk'
        revenue_at_risk = None
        if len(_direct) == 1:
            revenue_at_risk = _direct[0]['display_figure']
        elif len(_direct) > 1:
            _total = sum(
                v for v in (_parse_display_figure_to_float(f['display_figure']) for f in _direct)
                if v is not None
            )
            if _total > 0:
                _fmt = (f'~${_total / 1_000_000:.1f}M' if _total >= 1_000_000
                        else f'~${int(round(_total / 1000))}K')
                revenue_at_risk = f'{_fmt}+'
        elif _exec_with_fig:
            _best = max(_exec_with_fig,
                        key=lambda f: _parse_display_figure_to_float(f['display_figure']) or 0)
            revenue_at_risk = _best['display_figure']
            _rar_label = 'Most urgent active exposure'
        else:
            revenue_at_risk = '[Set in FindingsPanel]'
        kf_rows.append((_rar_label, revenue_at_risk))
        high_findings   = [f for f in findings if f.get('priority') == 'High']
        primary_finding = high_findings[0] if high_findings else (findings[0] if findings else None)
        if primary_finding and primary_finding.get('root_cause'):
            rc  = primary_finding['root_cause']
            dot = rc.find('. ')
            cause_line = (rc[:dot] if dot > 0 else rc).strip()
            # Truncate to 10 words for the at-a-glance box — full explanation in Section 5
            words = cause_line.split()
            if len(words) > 10:
                cause_line = ' '.join(words[:10]) + '\u2026'
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
                self._add_narrative_paragraphs(doc, _resolve_initiative_codes(para_text, roadmap_by_id))

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
            self._add_narrative_paragraphs(doc, _resolve_initiative_codes(overview_para, roadmap_by_id))
        doc.add_paragraph()

        # 3 — Operational Maturity Overview
        doc.add_heading('Operational Maturity Overview', level=1)
        self._signal_table(doc, signals)
        doc.add_paragraph()

        # 4 — Domain Analysis
        doc.add_heading('Domain Analysis', level=1)
        self._findings_by_domain(doc, findings, narrative, roadmap_by_id)
        doc.add_paragraph()

        # 5 — Root Cause Analysis (prose only — finding bullets removed)
        doc.add_heading('Root Cause Analysis', level=1)
        root_cause = narrative.get('root_cause_narrative', '')
        if root_cause:
            self._add_narrative_paragraphs(doc, _resolve_initiative_codes(root_cause, roadmap_by_id))
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
            self._add_narrative_paragraphs(doc, _resolve_initiative_codes(econ_narrative, roadmap_by_id))
        doc.add_paragraph()

        # 7 — Future State
        doc.add_heading(f'Where {firm_name} Can Be in 18 Months', level=1)
        future_rows = narrative.get('future_state_table_rows', [])
        if future_rows and isinstance(future_rows, list):
            self._future_state_table(doc, future_rows)
            doc.add_paragraph()
        future_narrative = narrative.get('future_state_narrative', '')
        if future_narrative:
            self._add_narrative_paragraphs(doc, _resolve_initiative_codes(future_narrative, roadmap_by_id))
        doc.add_paragraph()

        # 8 — Transformation Roadmap
        doc.add_heading('Transformation Roadmap', level=1)

        # Visual 2 — Roadmap Timeline chart
        timeline_path = self._generate_roadmap_timeline(roadmap, initiative_details)
        if timeline_path:
            try:
                doc.add_picture(timeline_path, width=Inches(6.5))
                caption = doc.add_paragraph(
                    'Initiative timeline by phase. Months are approximate — '
                    'adjust at kickoff based on available capacity.'
                )
                caption.runs[0].italic = True
                caption.runs[0].font.size = Pt(9)
                caption.alignment = WD_ALIGN_PARAGRAPH.LEFT
                doc.add_paragraph()
            except Exception as e:
                logger.warning(f'Failed to embed roadmap timeline: {e}')
            finally:
                try:
                    os.remove(timeline_path)
                except OSError:
                    pass

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
                        self._add_narrative_paragraphs(doc, _resolve_initiative_codes(rationale, roadmap_by_id))
                        doc.add_paragraph()
                    self._roadmap_phase_table(doc, items, findings_by_id, initiative_details, roadmap_by_id)
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
            self._risk_table(doc, risk_rows, roadmap_by_id)
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
    # Cover page — distribution restriction
    # ------------------------------------------------------------------

    def _add_cover_page_restriction(self, doc):
        """Insert a distribution restriction note on the cover page, immediately
        below the existing 'Confidential — For internal use only' line.

        Scans doc.paragraphs for the confidentiality line and inserts after it
        via raw XML (python-docx has no insert_after API). Copies paragraph and
        run formatting from the confidentiality line so the new note inherits
        the same style (centering, italic, font size, etc.).

        Always present — the diagnostic context warrants it regardless of whether
        named individuals appear in this specific report.

        Logs a warning and skips gracefully if the line is not found (e.g. if the
        template places it in a text box or drawing object outside doc.paragraphs).
        """
        RESTRICTION_TEXT = (
            'Distribution: Restricted \u2014 Contains individual performance assessment data. '
            'Distribute only to CEO and Director of Delivery unless performance references '
            'have been reviewed and approved for broader distribution.'
        )
        for para in doc.paragraphs:
            if 'Confidential' in para.text:
                new_p = OxmlElement('w:p')

                # Copy paragraph properties (alignment, spacing, style) from source
                pPr_src = para._element.find(qn('w:pPr'))
                if pPr_src is not None:
                    new_p.append(deepcopy(pPr_src))

                # Build run, inheriting run formatting (italic, font size, color)
                new_r = OxmlElement('w:r')
                if para.runs:
                    rPr_src = para.runs[0]._element.find(qn('w:rPr'))
                    if rPr_src is not None:
                        new_r.append(deepcopy(rPr_src))

                new_t = OxmlElement('w:t')
                new_t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                new_t.text = RESTRICTION_TEXT
                new_r.append(new_t)
                new_p.append(new_r)

                para._element.addnext(new_p)
                logger.info('Distribution restriction note added to cover page')
                return

        logger.warning(
            'Cover page "Confidential" line not found in doc.paragraphs — '
            'distribution restriction note not added (text may be in a text box or drawing object)'
        )

    # ------------------------------------------------------------------
    # Executive Briefing — standalone CEO teaser page
    # ------------------------------------------------------------------

    def _build_executive_briefing(self, doc, findings: list, narrative: dict,
                                  roadmap_by_id: dict | None = None):
        """One-page standalone briefing shown to the CEO before the full report.

        Content sourcing:
          Problems    — executive_briefing.problems from Narrator: plain_title (5 words)
                        and impact_brief (20 words). finding_id validated against DB.
          Numbers     — executive_briefing.numbers from Narrator: label (4 words) and
                        finding_id. Dollar figure sourced from DB via _parse_economic_figures()
                        — CONFIRMED or DERIVED. finding_id validated against DB.
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

        # Executive Snapshot — three sentences, first thing on the page
        # Skips silently if key absent (backward compat with cached narrator outputs)
        snapshot = eb.get('executive_snapshot', '')
        if snapshot:
            self._add_narrative_paragraphs(doc, _resolve_initiative_codes(snapshot, roadmap_by_id))
            rule = doc.add_paragraph()
            pPr = rule._p.get_or_add_pPr()
            pBdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), '6')
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
        # Sourced from structured display fields — findings with include_in_executive = 1,
        # display_figure and display_label both set. Sorted by figure value descending.
        exec_findings = [
            f for f in findings
            if f.get('include_in_executive')
            and f.get('display_figure')
            and f.get('display_label')
        ]
        exec_findings.sort(
            key=lambda f: (_parse_display_figure_to_float(f['display_figure']) or -1),
            reverse=True,
        )
        number_rows = [
            (f['display_label'], f['display_figure'])
            for f in exec_findings[:3]
        ]

        self._briefing_block_header(doc, 'Three Numbers That Matter')
        if number_rows:
            tbl = doc.add_table(rows=0, cols=2)
            tbl.style = 'Table Grid'
            for label, amount in number_rows:
                row = tbl.add_row()
                row.cells[0].text = label
                amt_cell = row.cells[1]
                amt_run  = amt_cell.paragraphs[0].add_run(amount)
                amt_run.bold = True
            _set_col_widths(tbl, [4.5, 2.0])
            _left_align_table(tbl)
        else:
            ph = doc.add_paragraph(
                '[Complete Executive Display fields in FindingsPanel before delivery]'
            )
            if ph.runs:
                ph.runs[0].italic = True
                ph.runs[0].font.color.rgb = RGBColor(0xFF, 0x8C, 0x00)
                ph.runs[0].font.size = Pt(9)

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
            val_str = str(value)
            if val_str.startswith('['):
                run = row.cells[1].paragraphs[0].add_run(val_str)
                run.italic = True
                run.font.color.rgb = RGBColor(0xFF, 0x8C, 0x00)
                run.font.size = Pt(9)
            else:
                row.cells[1].text = val_str

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
            trigger = entry['trigger_domains']
            if trigger is not None and not (trigger & finding_domains):
                continue

            # Build domain_clause — only list domains that have accepted findings
            # in this engagement. Preserves domain_order for consistent display.
            domain_order = entry.get('domain_order')
            if domain_order:
                active = [d for d in domain_order if d in finding_domains]
                domain_clause = f' ({", ".join(active)})' if active else ''
            else:
                domain_clause = ''

            row = table.add_row()
            row.cells[0].text = entry['role']
            row.cells[1].text = entry['priority'].format(s=_SECTION_MAP, domain_clause=domain_clause)
            row.cells[2].text = entry['detail'].format(s=_SECTION_MAP, domain_clause=domain_clause)
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

    def _findings_by_domain(self, doc, findings: list, narrative: dict,
                            roadmap_by_id: dict | None = None):
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
                doc.add_paragraph(_resolve_initiative_codes(opening, roadmap_by_id))
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

                # Evidence summary — italic gray line below the table
                evidence = f.get('evidence_summary') or ''
                if evidence:
                    ev_para     = doc.add_paragraph()
                    ev_run      = ev_para.add_run(evidence)
                    ev_run.italic         = True
                    ev_run.font.size      = Pt(9)
                    ev_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

                # Key quotes — block-quoted verbatim excerpts
                raw_quotes = f.get('key_quotes') or ''
                if raw_quotes:
                    try:
                        quotes = json.loads(raw_quotes)
                    except (json.JSONDecodeError, TypeError):
                        quotes = []
                    for quote in quotes:
                        if not quote:
                            continue
                        q_para     = doc.add_paragraph(style='Quote')
                        q_run      = q_para.add_run(f'"{quote}"')
                        q_run.italic    = True
                        q_run.font.size = Pt(9)

                doc.add_paragraph()

            if closing:
                doc.add_paragraph(_resolve_initiative_codes(closing, roadmap_by_id))
                doc.add_paragraph()

    # ------------------------------------------------------------------
    # Table helpers — new sections
    # ------------------------------------------------------------------

    def _generate_economic_chart(self, findings: list):
        """Generate a horizontal bar chart of direct and derived economic exposure by finding.

        Includes both CONFIRMED (direct) and DERIVED (computed from confirmed inputs) figures.
        Uses the same deduplication logic as _economic_summary_table — seen_figures tracks
        unique dollar amounts so a figure shared between findings only produces one bar.

        Direct (CONFIRMED) bars render in dark navy; Derived bars render in steel blue.
        A legend is shown only when both types are present.

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

        _COLOR_DIRECT  = '#1F3864'   # dark navy — CONFIRMED (directly stated)
        _COLOR_DERIVED = '#4472C4'   # steel blue — DERIVED (computed from confirmed inputs)

        try:
            # Build chart data — same priority sort and dedup as _economic_summary_table
            seen_figures: dict = {}
            chart_data: list = []
            for f in sorted(findings,
                            key=lambda x: PRIORITY_ORDER.get(x.get('priority'), 2)):
                conf_str, deriv_str, _ = _parse_economic_figures(f.get('economic_impact', ''))
                # Prefer CONFIRMED over DERIVED per finding — same precedence as the table
                if conf_str != '—':
                    primary    = conf_str.split(', ')[0]
                    bar_color  = _COLOR_DIRECT
                    bar_type   = 'Direct'
                elif deriv_str != '—':
                    primary    = deriv_str.split(', ')[0]
                    bar_color  = _COLOR_DERIVED
                    bar_type   = 'Derived'
                else:
                    continue
                if primary in seen_figures:
                    continue                     # duplicate figure — skip
                seen_figures[primary] = True
                val = _dollar_to_float(primary)
                if val is None:
                    continue
                raw_title = f.get('finding_title') or ''
                label = raw_title[:40] + ('...' if len(raw_title) > 40 else '')
                chart_data.append((label, val, bar_color, bar_type))

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
            colors = [d[2] for d in chart_data]
            types  = [d[3] for d in chart_data]
            max_val = max(values)

            n = len(chart_data)
            fig, ax = plt.subplots(figsize=(8, max(3.0, n * 0.6)))

            bars = ax.barh(labels, values, color=colors, height=0.5)

            # Value label at the end of each bar
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_width() + max_val * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    _fmt(val),
                    va='center', ha='left', fontsize=9,
                )

            ax.set_xlabel('Exposure')
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
            ax.set_title('Direct and Derived Economic Exposure', fontsize=11, pad=8)

            # Show legend only when both bar types are present
            type_set = set(types)
            if len(type_set) > 1:
                from matplotlib.patches import Patch
                legend_elements = []
                if 'Direct' in type_set:
                    legend_elements.append(Patch(facecolor=_COLOR_DIRECT,  label='Direct (confirmed)'))
                if 'Derived' in type_set:
                    legend_elements.append(Patch(facecolor=_COLOR_DERIVED, label='Derived (calculated)'))
                ax.legend(handles=legend_elements, loc='lower right', fontsize=8)

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

    def _generate_roadmap_timeline(self, roadmap: list, initiative_details: dict):
        """Generate a Gantt-style timeline chart for the transformation roadmap.

        X-axis: months 1–18 with phase zone background shading.
        Y-axis: initiative names grouped by phase (Stabilize at top, Scale at bottom).
        Bars: colored by phase.

        Timeline for each item sourced from initiative_details (narrator output).
        Falls back to phase-level defaults (Stabilize 1–3, Optimize 3–9, Scale 9–18)
        when an item has no narrator detail — so the chart always renders even if
        the narrator omits some initiative_details entries.

        Returns path to a temporary PNG file, or None if generation fails or
        there is no roadmap data. Caller must delete the file after embedding.
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            logger.warning('matplotlib not installed — skipping roadmap timeline')
            return None

        if not roadmap:
            return None

        try:
            PHASE_ORDER = {'Stabilize': 0, 'Optimize': 1, 'Scale': 2}
            PHASE_COLORS = {
                'Stabilize': '#2E75B6',
                'Optimize':  '#ED7D31',
                'Scale':     '#70AD47',
            }
            PHASE_BG = {
                'Stabilize': '#EBF3FB',
                'Optimize':  '#FEF3EC',
                'Scale':     '#F0F7ED',
            }
            PHASE_DEFAULTS = {
                'Stabilize': (1, 3),
                'Optimize':  (3, 9),
                'Scale':     (9, 18),
            }

            def _parse_tl(s):
                """Parse 'Month X' or 'Months X-Y' → (start, end). None on failure."""
                if not s:
                    return None
                s = s.strip()
                m = re.match(r'Month\s+(\d+)$', s, re.I)
                if m:
                    v = int(m.group(1))
                    return (v, v)
                m = re.match(r'Months?\s+(\d+)\s*[-\u2013]\s*(\d+)$', s, re.I)
                if m:
                    return (int(m.group(1)), int(m.group(2)))
                return None

            # Build rows: (label, phase, start_month, end_month)
            rows = []
            for item in roadmap:
                phase    = item.get('phase') or 'Stabilize'
                raw_name = item.get('initiative_name') or ''
                label    = (raw_name[:35] + '…') if len(raw_name) > 35 else raw_name

                detail   = initiative_details.get(item.get('item_id', '')) or {}
                tl       = _parse_tl(detail.get('timeline', ''))
                if tl is None:
                    tl = PHASE_DEFAULTS.get(phase, (1, 18))

                rows.append((label, phase, tl[0], tl[1]))

            if not rows:
                return None

            # Sort by phase order, then start month — keeps phases visually grouped
            rows.sort(key=lambda r: (PHASE_ORDER.get(r[1], 9), r[2]))

            # barh draws bottom-to-top; reverse so Stabilize appears at top
            rows = list(reversed(rows))
            n = len(rows)

            fig_height = max(3.5, n * 0.46 + 1.2)
            fig, ax    = plt.subplots(figsize=(9, fig_height))

            # Phase zone background shading — non-overlapping intervals
            for phase_name, zone_start, zone_end in [
                ('Stabilize', 0.5, 3),
                ('Optimize',  3,   9),
                ('Scale',     9,   18.5),
            ]:
                ax.axvspan(zone_start, zone_end,
                           color=PHASE_BG.get(phase_name, '#F5F5F5'),
                           alpha=0.6, zorder=0)
                ax.text(
                    (zone_start + zone_end) / 2, 1.01,
                    phase_name,
                    ha='center', va='bottom',
                    fontsize=8, fontweight='bold',
                    color=PHASE_COLORS.get(phase_name, '#555555'),
                    transform=ax.get_xaxis_transform(),
                    clip_on=False,
                )

            # Bars
            for i, (label, phase, start, end) in enumerate(rows):
                width = max(end - start, 0.4)   # minimum visible width for single-month items
                ax.barh(i, width, left=start,
                        height=0.55,
                        color=PHASE_COLORS.get(phase, '#888888'),
                        alpha=0.85,
                        zorder=2)

            # Y-axis
            ax.set_yticks(range(n))
            ax.set_yticklabels([r[0] for r in rows], fontsize=8)
            ax.set_ylim(-0.6, n - 0.4)

            # X-axis
            ax.set_xlim(0.5, 18.5)
            ax.set_xticks([1, 3, 6, 9, 12, 15, 18])
            ax.set_xticklabels(
                ['Mo 1', 'Mo 3', 'Mo 6', 'Mo 9', 'Mo 12', 'Mo 15', 'Mo 18'],
                fontsize=8,
            )
            ax.set_xlabel('Timeline (months)', fontsize=9)

            # Clean spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.tick_params(left=False)
            ax.yaxis.grid(False)
            ax.xaxis.grid(False)

            # Legend
            legend_patches = [
                mpatches.Patch(
                    color=PHASE_COLORS[p], label=p, alpha=0.85
                )
                for p in ['Stabilize', 'Optimize', 'Scale']
                if any(r[1] == p for r in rows)
            ]
            ax.legend(handles=legend_patches, loc='lower right',
                      fontsize=8, frameon=True, framealpha=0.9)

            plt.tight_layout()

            tmp      = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            tmp_path = tmp.name
            tmp.close()
            fig.savefig(tmp_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            logger.info(f'Roadmap timeline chart generated — {n} initiatives')
            return tmp_path

        except Exception as exc:
            logger.warning(f'Roadmap timeline generation failed: {exc} — skipping chart')
            return None

    def _economic_summary_table(self, doc, findings: list):
        """Section 6 summary table.
        Columns: Finding | Confirmed Exposure | Derived Exposure | Annual Drag (Inferred) | Recovery Potential

        Confirmed = figure explicitly stated in a source document.
        Derived   = arithmetic result of confirmed inputs; value never stated in any source.
        Inferred  = estimate with at least one non-document input.
        Recovery Potential derives from the finding's priority field.
        A totals row closes the table; a disclaimer footnote clarifies that Confirmed and
        Derived totals are not additive."""
        rows_with_impact = [
            f for f in sorted(findings, key=lambda x: PRIORITY_ORDER.get(x.get('priority'), 2))
            if f.get('economic_impact')
        ]
        if not rows_with_impact:
            doc.add_paragraph('No economic impact data recorded for this engagement.')
            return

        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        for i, h in enumerate(['Finding', 'Confirmed Exposure', 'Derived Exposure',
                                'Annual Drag (Inferred)', 'Recovery Potential']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [1.7, 1.1, 1.1, 1.4, 1.2])

        recovery_map = {'High': 'High', 'Medium': 'Medium', 'Low': 'Low'}

        seen_confirmed   = {}   # figure string → first finding_title that used it
        seen_derived     = {}   # figure string → first finding_title that used it
        footnote_markers = {}   # figure string → marker symbol (shared pool for both types)
        footnotes        = []   # list of (marker, figure, first_title, label_type)
        _markers         = ['*', '**', '†', '††', '‡']

        for f in rows_with_impact:
            confirmed, derived, inferred = _parse_economic_figures(f.get('economic_impact', ''))
            primary_confirmed = confirmed.split(', ')[0] if confirmed != '—' else '—'
            primary_derived   = derived.split(', ')[0]   if derived   != '—' else '—'
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
                        footnotes.append((marker, primary_confirmed, seen_confirmed[primary_confirmed], 'confirmed'))
                    display_confirmed = f"{primary_confirmed} \u2014 shared, see note"
                else:
                    seen_confirmed[primary_confirmed] = f.get('finding_title', '')

            # Same dedup logic for derived figures
            display_derived = primary_derived
            if primary_derived != '—':
                if primary_derived in seen_derived:
                    if primary_derived not in footnote_markers:
                        marker = _markers[len(footnote_markers)] if len(footnote_markers) < len(_markers) else '*'
                        footnote_markers[primary_derived] = marker
                        footnotes.append((marker, primary_derived, seen_derived[primary_derived], 'derived'))
                    display_derived = f"{primary_derived} \u2014 shared, see note"
                else:
                    seen_derived[primary_derived] = f.get('finding_title', '')

            row = table.add_row()
            row.cells[0].text = f.get('finding_title') or ''
            row.cells[1].text = display_confirmed
            row.cells[2].text = display_derived
            row.cells[3].text = primary_inferred
            row.cells[4].text = recovery_map.get(f.get('priority', ''), '—')

        # Totals row
        # Sourced from structured display_figure fields: figure_type in (direct_exposure, annual_drag),
        # include_in_executive = 1, display_figure not null. Deduped by exact figure string match
        # (direct_exposure takes precedence). Sum displayed in Confirmed column; others show '—'.
        _qualifying = [
            f for f in findings
            if f.get('include_in_executive')
            and f.get('display_figure')
            and f.get('figure_type') in ('direct_exposure', 'annual_drag')
        ]
        _dedup: dict = {}
        for _f in _qualifying:
            _fig = _f['display_figure']
            if _fig not in _dedup or _f.get('figure_type') == 'direct_exposure':
                _dedup[_fig] = _f
        _deduped = list(_dedup.values())

        if _deduped:
            _total_val = 0.0
            _parseable = False
            for _f in _deduped:
                _val = _parse_display_figure_to_float(_f['display_figure'])
                if _val is not None:
                    _total_val += _val
                    _parseable  = True
            if _parseable:
                _fmt = (f'~${_total_val / 1_000_000:.1f}M' if _total_val >= 1_000_000
                        else f'~${int(round(_total_val / 1000))}K')
                total_display = (f'{_fmt}+ confirmed floor '
                                 f'(direct exposures only — see individual findings)')
            else:
                total_display = '[Set in FindingsPanel]'
        else:
            total_display = '[Set in FindingsPanel]'

        totals_row = table.add_row()
        for cell in totals_row.cells:
            _shade_cell(cell, 'F2F2F2')
        totals_row.cells[0].text = 'Total Identified Exposure'
        if totals_row.cells[0].paragraphs[0].runs:
            totals_row.cells[0].paragraphs[0].runs[0].bold = True
        if total_display.startswith('['):
            _run = totals_row.cells[1].paragraphs[0].add_run(total_display)
            _run.italic = True
            _run.font.color.rgb = RGBColor(0xFF, 0x8C, 0x00)
            _run.font.size = Pt(9)
        else:
            totals_row.cells[1].text = total_display
        totals_row.cells[2].text = '—'
        totals_row.cells[3].text = '—'
        totals_row.cells[4].text = '—'

        _left_align_table(table)

        # Footnotes for duplicate confirmed/derived figures (per-finding rows only)
        for marker, figure, first_title, label_type in footnotes:
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
                              initiative_details: dict, roadmap_by_id: dict | None = None):
        """Sections 8.3/8.4/8.5 phase tables.
        Columns: Initiative | Priority | Effort | Owner | Timeline | Success Metric

        Initiative cell is multi-line:
          - Bold initiative name
          - Capability (italic, 9pt) if present
          - Economic impact from linked findings (blue, 9pt) if addressing_finding_ids set
          - Prerequisites (gray, 9pt) if depends_on set
        """
        table = doc.add_table(rows=1, cols=6)
        table.style = 'Table Grid'
        headers = ['Initiative', 'Priority', 'Effort', 'Owner', 'Timeline', 'Success Metric']
        for i, h in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [2.2, 0.6, 0.6, 0.9, 0.8, 1.4])

        for item in items:
            item_id = item.get('item_id', '')
            details = initiative_details.get(item_id, {})

            row = table.add_row()

            # Initiative cell — multi-line
            init_cell = row.cells[0]
            # Clear default empty paragraph, add bold name
            init_cell.paragraphs[0].clear()
            name_run = init_cell.paragraphs[0].add_run(item.get('initiative_name') or '')
            name_run.bold = True
            name_run.font.size = Pt(9)

            # Capability line
            capability = item.get('capability') or ''
            if capability:
                cap_para = init_cell.add_paragraph()
                cap_run  = cap_para.add_run(f'Capability: {capability}')
                cap_run.italic    = True
                cap_run.font.size = Pt(8)
                cap_run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

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

        for r in rows:
            if not isinstance(r, dict):
                continue
            row = table.add_row()
            row.cells[0].text = _resolve_initiative_codes(r.get('initiative') or '', roadmap_by_id)
            row.cells[1].text = _resolve_initiative_codes(r.get('depends_on') or '', roadmap_by_id)
        _left_align_table(table)

    def _risk_table(self, doc, rows: list, roadmap_by_id: dict | None = None):
        """Section 8.7 Key Risks table.
        Columns: Risk | Likelihood | Mitigation
        roadmap_by_id: passed from _build() to resolve R-code references in
        mitigation text (e.g. 'R060' → initiative name)."""
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
            row.cells[0].text = _resolve_initiative_codes(r.get('risk') or '', roadmap_by_id)
            row.cells[1].text = r.get('likelihood') or ''
            row.cells[2].text = _resolve_initiative_codes(r.get('mitigation') or '', roadmap_by_id)
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
