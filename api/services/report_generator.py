import os
import logging
import tempfile
from collections import defaultdict

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches
from lxml import etree

from api.db.repositories.engagement import EngagementRepository
from api.db.repositories.finding import FindingRepository
from api.db.repositories.roadmap import RoadmapRepository
from api.db.repositories.agent_run import AgentRunRepository
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


class ReportGeneratorService:
    """Generates the OPD Transformation Roadmap Word document.

    Nine sections:
    1. Executive Summary — narrator prose
    2. Engagement Overview — from engagement record
    3. Operational Maturity Overview — signal domain summary table
    4. Domain Analysis — narrator opening/closing paragraphs + finding tables
    5. Root Cause Analysis — narrator prose only (no bullet repeat)
    6. Economic Impact Analysis — economic summary table + narrator prose
    7. Future State — metrics table (narrator) + narrative (narrator)
    8. Transformation Roadmap — 8.1 Priority Zero | 8.2 Overview | 8.3-8.5 Phase Tables
                                 | 8.6 Dependencies | 8.7 Key Risks
    9. Immediate Next Steps — action table (narrator)
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

        findings = FindingRepository().get_all(self.engagement_id)
        roadmap  = RoadmapRepository().get_all(self.engagement_id)
        signals  = ReportingRepository().get_engagement_signals(self.engagement_id)

        narrative = await generate_report_narrative(synth_output, findings, roadmap, eng)

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

        # 1 — Executive Summary
        doc.add_heading('Executive Summary', level=1)
        exec_summary = narrative.get('executive_summary', '')
        if exec_summary:
            self._add_narrative_paragraphs(doc, exec_summary)
        else:
            doc.add_paragraph(
                '[To be completed by consultant. '
                'Summarize the engagement context, key findings, and recommended priorities.]'
            ).italic = True
        doc.add_paragraph()

        # 2 — Engagement Overview
        doc.add_heading('Engagement Overview', level=1)
        self._kv_table(doc, [
            ('Client',             firm_name),
            ('Engagement',         eng.get('engagement_name') or ''),
            ('Start Date',         eng.get('start_date') or ''),
            ('Firm Size',          str(eng.get('firm_size') or '')),
            ('Service Model',      eng.get('service_model') or ''),
            ('Status',             eng.get('status') or ''),
            ('Stated Problem',     eng.get('stated_problem') or ''),
            ('Client Hypothesis',  eng.get('client_hypothesis') or ''),
            ('Previously Tried',   eng.get('previously_tried') or ''),
        ])
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
        doc.add_heading('8.1  Priority Zero Actions — Complete This Week', level=2)
        pz_rows = narrative.get('priority_zero_table_rows', [])
        if pz_rows and isinstance(pz_rows, list):
            self._priority_zero_table(doc, pz_rows)
        else:
            doc.add_paragraph('No Priority Zero items identified.')
        doc.add_paragraph()

        # 8.2 — Roadmap Overview
        doc.add_heading('8.2  Roadmap Overview', level=2)
        overview_rows = narrative.get('roadmap_overview_rows', [])
        if overview_rows and isinstance(overview_rows, list):
            self._roadmap_overview_table(doc, overview_rows)
        doc.add_paragraph()

        # 8.3 / 8.4 / 8.5 — Phase Tables
        phase_labels = {'Stabilize': '8.3', 'Optimize': '8.4', 'Scale': '8.5'}
        if roadmap:
            for phase, label in phase_labels.items():
                items = [r for r in roadmap if r.get('phase') == phase]
                if items:
                    doc.add_heading(f'{label}  {phase}', level=2)
                    rationale = narrative.get('roadmap_rationale', {}).get(phase, '')
                    if rationale:
                        self._add_narrative_paragraphs(doc, rationale)
                        doc.add_paragraph()
                    self._roadmap_phase_table(doc, items, findings_by_id, initiative_details)
                    doc.add_paragraph()
        else:
            doc.add_paragraph('No roadmap items recorded.')

        # 8.6 — Initiative Dependencies
        doc.add_heading('8.6  Initiative Dependencies', level=2)
        dep_rows = narrative.get('dependency_table_rows', [])
        if dep_rows and isinstance(dep_rows, list):
            self._dependency_table(doc, dep_rows)
        else:
            doc.add_paragraph('No dependencies identified.')
        doc.add_paragraph()

        # 8.7 — Key Risks
        doc.add_heading('8.7  Key Risks', level=2)
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
        """Add each double-newline-separated paragraph as a Word paragraph."""
        for para in text.split('\n\n'):
            para = para.strip()
            if para:
                doc.add_paragraph(para)

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

    def _signal_table(self, doc, signals: list):
        """Domain summary: domain, total signals, counts by confidence."""
        if not signals:
            doc.add_paragraph('No signals recorded.')
            return

        counts = defaultdict(lambda: {'High': 0, 'Medium': 0, 'Hypothesis': 0, 'total': 0})
        for s in signals:
            d = s.get('domain', 'Unknown')
            c = s.get('signal_confidence', 'Medium')
            counts[d][c] = counts[d].get(c, 0) + 1
            counts[d]['total'] += 1

        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        for i, h in enumerate(['Domain', 'Total', 'High', 'Medium', 'Hypothesis']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [2.5, 0.7, 0.7, 0.8, 0.8])

        for domain in sorted(counts):
            c = counts[domain]
            row = table.add_row()
            row.cells[0].text = domain
            row.cells[1].text = str(c['total'])
            row.cells[2].text = str(c['High'])
            row.cells[3].text = str(c['Medium'])
            row.cells[4].text = str(c['Hypothesis'])

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
        """Section 6 summary table: Finding | Priority | Economic Impact.
        Only rows with an economic_impact value are shown."""
        rows_with_impact = [
            f for f in sorted(findings, key=lambda x: PRIORITY_ORDER.get(x.get('priority'), 2))
            if f.get('economic_impact')
        ]
        if not rows_with_impact:
            doc.add_paragraph('No economic impact data recorded for this engagement.')
            return

        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        for i, h in enumerate(['Finding', 'Priority', 'Economic Impact']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [2.5, 0.7, 3.3])

        for f in rows_with_impact:
            row = table.add_row()
            row.cells[0].text = f.get('finding_title') or ''
            row.cells[1].text = f.get('priority') or ''
            row.cells[2].text = f.get('economic_impact') or ''

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

    def _roadmap_phase_table(self, doc, items: list, findings_by_id: dict,
                              initiative_details: dict):
        """Sections 8.3/8.4/8.5 phase tables.
        Columns: Initiative | Priority | Effort | Owner | Timeline | Success Metric | Economic Impact"""
        table = doc.add_table(rows=1, cols=7)
        table.style = 'Table Grid'
        headers = ['Initiative', 'Priority', 'Effort', 'Owner',
                   'Timeline', 'Success Metric', 'Economic Impact']
        for i, h in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True
            _shade_cell(cell, 'D9D9D9')
        _set_col_widths(table, [1.6, 0.6, 0.6, 0.9, 0.8, 1.2, 0.8])

        for item in items:
            item_id = item.get('item_id', '')
            details = initiative_details.get(item_id, {})
            linked_finding = findings_by_id.get(item.get('finding_id') or '', {})
            econ_impact = linked_finding.get('economic_impact', '') or ''

            row = table.add_row()
            row.cells[0].text = item.get('initiative_name') or ''
            row.cells[1].text = item.get('priority') or ''
            row.cells[2].text = item.get('effort') or ''
            row.cells[3].text = item.get('owner') or ''
            row.cells[4].text = details.get('timeline', '') or ''
            row.cells[5].text = details.get('success_metric', '') or ''
            row.cells[6].text = econ_impact

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
