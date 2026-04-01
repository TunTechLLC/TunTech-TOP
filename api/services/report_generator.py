import os
import logging
import tempfile
from collections import defaultdict
from datetime import date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from api.db.repositories.engagement import EngagementRepository
from api.db.repositories.finding import FindingRepository
from api.db.repositories.roadmap import RoadmapRepository
from api.db.repositories.agent_run import AgentRunRepository
from api.db.repositories.reporting import ReportingRepository
from api.services.claude import generate_report_narrative

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {'High': 0, 'Medium': 1, 'Low': 2}


class ReportGeneratorService:
    """Generates the OPD Transformation Roadmap Word document.

    Eight sections:
    1. Executive Summary — narrator prose
    2. Engagement Overview — from engagement record
    3. Operational Maturity Overview — signal domain summary table
    4. Domain Analysis — narrator opening/closing paragraphs + finding tables
    5. Root Cause Analysis — narrator prose + finding root_cause bullet list
    6. Economic Impact Analysis — narrator prose + finding economic_impact bullet list
    7. Improvement Opportunities — recommendations in priority order
    8. Transformation Roadmap — narrator phase rationale + RoadmapItems tables
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

        # Cover line
        doc.add_heading('OPD Transformation Roadmap', 0)
        sub = doc.add_paragraph(
            f"{firm_name}  |  {date.today().strftime('%B %Y')}"
        )
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

        # 1 — Executive Summary
        doc.add_heading('1. Executive Summary', level=1)
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
        doc.add_heading('2. Engagement Overview', level=1)
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
        doc.add_heading('3. Operational Maturity Overview', level=1)
        self._signal_table(doc, signals)
        doc.add_paragraph()

        # 4 — Domain Analysis
        doc.add_heading('4. Domain Analysis', level=1)
        self._findings_by_domain(doc, findings, narrative)
        doc.add_paragraph()

        # 5 — Root Cause Analysis
        doc.add_heading('5. Root Cause Analysis', level=1)
        root_cause = narrative.get('root_cause_narrative', '')
        if root_cause:
            self._add_narrative_paragraphs(doc, root_cause)
            doc.add_paragraph()
        if findings:
            for f in sorted(findings, key=lambda x: PRIORITY_ORDER.get(x.get('priority'), 2)):
                p = doc.add_paragraph(style='List Bullet')
                p.add_run(f"{f['finding_title']}: ").bold = True
                p.add_run(f.get('root_cause') or '')
        else:
            doc.add_paragraph('No findings recorded.')
        doc.add_paragraph()

        # 6 — Economic Impact Analysis
        doc.add_heading('6. Economic Impact Analysis', level=1)
        econ_narrative = narrative.get('economic_impact_narrative', '')
        if econ_narrative:
            self._add_narrative_paragraphs(doc, econ_narrative)
            doc.add_paragraph()
        if findings:
            for f in sorted(findings, key=lambda x: PRIORITY_ORDER.get(x.get('priority'), 2)):
                if f.get('economic_impact'):
                    p = doc.add_paragraph(style='List Bullet')
                    p.add_run(f"{f['finding_title']}: ").bold = True
                    p.add_run(f['economic_impact'])
        else:
            doc.add_paragraph('No findings recorded.')
        doc.add_paragraph()

        # 7 — Improvement Opportunities
        doc.add_heading('7. Improvement Opportunities', level=1)
        if findings:
            for f in sorted(findings, key=lambda x: PRIORITY_ORDER.get(x.get('priority'), 2)):
                p = doc.add_paragraph(style='List Bullet')
                p.add_run(f"[{f.get('priority', '')} / {f.get('effort', '')} effort]  ").bold = True
                p.add_run(f"{f['finding_title']}: ").bold = True
                p.add_run(f.get('recommendation') or '')
        else:
            doc.add_paragraph('No findings recorded.')
        doc.add_paragraph()

        # 8 — Transformation Roadmap
        doc.add_heading('8. Transformation Roadmap', level=1)
        if roadmap:
            for phase in ['Stabilize', 'Optimize', 'Scale']:
                items = [r for r in roadmap if r.get('phase') == phase]
                if items:
                    doc.add_heading(phase, level=2)
                    rationale = narrative.get(f'roadmap_rationale:{phase}', '')
                    if rationale:
                        self._add_narrative_paragraphs(doc, rationale)
                        doc.add_paragraph()
                    self._roadmap_table(doc, items)
                    doc.add_paragraph()
        else:
            doc.add_paragraph('No roadmap items recorded.')

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
    # Table helpers
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
            row.cells[1].text = value

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

        for domain in sorted(by_domain):
            doc.add_heading(domain, level=2)

            # Narrator domain analysis — split opening and closing paragraphs
            domain_prose = narrative.get(f'domain_analysis:{domain}', '')
            if domain_prose:
                paras = [p.strip() for p in domain_prose.split('\n\n') if p.strip()]
                opening = paras[0] if paras else ''
                closing = paras[1] if len(paras) > 1 else ''
            else:
                opening = closing = ''

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

    def _roadmap_table(self, doc, items: list):
        """Five-column roadmap table for a single phase."""
        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        for i, h in enumerate(['Initiative', 'Domain', 'Priority', 'Effort', 'Estimated Impact']):
            cell = table.rows[0].cells[i]
            cell.text = h
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True

        for item in items:
            row = table.add_row()
            row.cells[0].text = item.get('initiative_name') or ''
            row.cells[1].text = item.get('domain') or ''
            row.cells[2].text = item.get('priority') or ''
            row.cells[3].text = item.get('effort') or ''
            row.cells[4].text = item.get('estimated_impact') or ''
