"""
Structural test for report_generator.py — zero API cost.

Builds a Word document using a mock narrative dict with all new section keys
populated. Use this to verify layout, column widths, and heading structure
before making any real Claude calls.

Usage (from repo root):
    python scripts/test_report_structure.py [engagement_id]

Defaults to E003 if no engagement_id is provided.
The output file is saved to the system temp directory and the path is printed.
"""
import sys
import os
import asyncio

# Add repo root to path so api.* imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.report_generator import ReportGeneratorService
from api.db.repositories.engagement import EngagementRepository
from api.db.repositories.finding import FindingRepository
from api.db.repositories.roadmap import RoadmapRepository
from api.db.repositories.reporting import ReportingRepository
from api.db.repositories.agent_run import AgentRunRepository


MOCK_NARRATIVE = {
    "executive_summary": (
        "Vantage Point is generating revenue but not margin. "
        "With gross margin at 28% against a 38-40% benchmark and six of fourteen active projects "
        "in overrun, the firm is converting client wins into delivery losses at a structural level. "
        "The revenue line looks healthy; the economics beneath it do not.\n\n"
        "The client believed the problem was a Director of Delivery who lacked the skills to "
        "manage a growing team. The diagnostic shows the opposite: a Director of Delivery who "
        "has the skills but not the authority. The CEO is the de facto delivery decision-maker, "
        "and every improvement initiative that has been attempted has stalled at that point.\n\n"
        "The total economic exposure across confirmed and inferred findings is $420K-$780K annually "
        "(INFERRED). The confirmed component — AR aging and below-cost SOWs — accounts for "
        "$180K-$240K (CONFIRMED). The remainder is margin leakage from delivery overruns and "
        "underpriced renewals.\n\n"
        "Before any process work begins, two structural decisions must be made this week: "
        "the CEO must formally reinstate the Director of Delivery's authority in writing, and the "
        "AR collection process must be assigned to a non-delivery owner. Without these two changes, "
        "the roadmap cannot hold.\n\n"
        "If the roadmap is executed in sequence, Vantage Point will exit the 18-month horizon with "
        "gross margin above 36%, billable utilization at 72-75%, and a pipeline that does not depend "
        "entirely on the CEO's network."
    ),
    "root_cause_narrative": (
        "The firm's current condition traces to a single structural failure that was present "
        "before the growth phase began: the CEO never delegated delivery authority. "
        "When the firm was small, this was functional — the CEO knew every project. "
        "As the firm scaled to fourteen active projects, it became a bottleneck that now touches "
        "every operational domain.\n\n"
        "Because the CEO controls staffing, scope, and pricing decisions, the Director of Delivery "
        "cannot enforce project discipline. When a project overruns, the Director escalates — "
        "the CEO decides. When a client pushes scope, the CEO absorbs it. "
        "The result is that delivery commitments are made without delivery input, and the Director "
        "of Delivery is held accountable for outcomes they did not control.\n\n"
        "This authority vacuum created a downstream pressure on project economics. "
        "SOWs are written to win, not to deliver — there is no pre-sales review gate requiring "
        "delivery sign-off before signature. Projects enter delivery already behind. "
        "Overruns compound the margin loss that was baked in at the sales stage.\n\n"
        "The AR aging problem is a symptom of the same dynamic. Invoicing is tied to delivery "
        "milestones, but milestone confirmation requires the CEO, who is occupied with the next "
        "sales cycle. Collections sit in a queue. The $95K-$140K in aged AR (CONFIRMED) is not a "
        "collections problem — it is a governance problem.\n\n"
        "This has persisted because each symptom looks like a separate issue: a difficult client, "
        "a missed deadline, a slow-paying account. The diagnostic shows they share a root. "
        "The fix is not a process — it is a structural decision about who has authority."
    ),
    "economic_impact_narrative": (
        "Total economic exposure across all findings is $420K-$780K annually (INFERRED), "
        "with $180K-$240K traceable to confirmed document evidence. "
        "At current revenue levels, this represents 12-22% of gross revenue leaving the business "
        "through preventable operational failures — margin that cannot be reinvested in talent, "
        "tooling, or market development. "
        "A firm operating at this level of value leakage cannot fund the capability investments "
        "required to compete for larger, more complex engagements."
    ),
    "future_state_narrative": (
        "When the roadmap is complete, Vantage Point will operate with a delivery function that "
        "runs without CEO intervention on day-to-day decisions: projects will enter delivery with "
        "signed SOWs and defined scope, the Director of Delivery will have real authority to "
        "enforce project discipline, and the pipeline will be generated through a structured BD "
        "function rather than founder relationships alone. "
        "The firm will be positioned to pursue engagements that its current operating model "
        "cannot support."
    ),
    "domain_analysis": {
        "Delivery Operations": {
            "opening": (
                "Delivery Operations is the highest-impact domain in this diagnostic. "
                "Six of fourteen active projects are in overrun, and the delivery authority "
                "structure that would allow the Director of Delivery to intervene does not exist "
                "in practice. Every delivery improvement initiative attempted in the past 18 months "
                "has been blocked at the CEO decision point."
            ),
            "closing": (
                "The delivery authority failure is not contained to this domain. "
                "It creates the conditions for pre-commitment failures in Sales-to-Delivery "
                "Transition and the margin compression visible in Consulting Economics. "
                "Restoring delivery authority is a prerequisite for work in both adjacent domains."
            )
        },
        "Consulting Economics": {
            "opening": (
                "The economics of this firm are structurally misaligned with its delivery capacity. "
                "Gross margin of 28% against a 38-40% benchmark reflects a combination of "
                "below-cost SOWs, delivery overruns, and underpriced renewals — each of which "
                "has a identifiable root cause in the diagnostic data."
            ),
            "closing": (
                "The economic findings are downstream of the delivery and governance findings. "
                "Margin cannot be recovered by pricing discipline alone if projects continue to "
                "overrun after the SOW is signed. The economic recovery depends on the structural "
                "changes in Delivery Operations and Project Governance."
            )
        }
    },
    "roadmap_rationale": {
        "Stabilize": (
            "The Stabilize initiatives address active margin bleed and the authority failures "
            "that make all subsequent work impossible. Restoring delivery authority and implementing "
            "the SOW gate must precede any process work — without them, new processes will be "
            "bypassed at the first difficult client conversation."
        ),
        "Optimize": (
            "Optimize work builds on the structural foundation that Stabilize establishes. "
            "With delivery authority restored and SOW discipline in place, the firm can implement "
            "capacity planning and pipeline discipline that will actually hold. "
            "These initiatives cannot be executed out of sequence."
        ),
        "Scale": (
            "Scale initiatives are the payoff of the prior 9 months of structural work. "
            "A firm with stable delivery and disciplined economics can pursue larger engagements, "
            "recover rate, and reduce its dependence on founder-sourced revenue. "
            "These are expansion moves, not repair moves."
        )
    },
    "future_state_table_rows": [
        {
            "metric": "Gross Margin",
            "current_state": "28%",
            "benchmark": "38-40%",
            "target": "36-40%",
            "sourced_from": "CONFIRMED"
        },
        {
            "metric": "Billable Utilization",
            "current_state": "62%",
            "benchmark": "75%",
            "target": "72-75%",
            "sourced_from": "INFERRED"
        },
        {
            "metric": "On-Time Delivery Rate",
            "current_state": "57%",
            "benchmark": "85%",
            "target": "80%+",
            "sourced_from": "CONFIRMED"
        },
        {
            "metric": "CEO Time on Delivery",
            "current_state": "Primary decision point for all staffing, scope, and pricing",
            "benchmark": "Strategic oversight only",
            "target": "Delivery decisions delegated — CEO not in delivery chain",
            "sourced_from": "CONFIRMED"
        }
    ],
    "priority_zero_table_rows": [
        {
            "action": "CEO formally reinstates Director of Delivery authority in writing",
            "owner": "CEO",
            "what_it_unblocks": "All delivery process improvements — without this, the Director cannot enforce any new process"
        },
        {
            "action": "Assign AR collection ownership to non-delivery staff",
            "owner": "Operations Manager",
            "what_it_unblocks": "Recovery of $95K-$140K aged AR and prevention of continued aging"
        }
    ],
    "roadmap_overview_rows": [
        {
            "phase": "Stabilize",
            "timeline": "Months 1-3",
            "key_outcomes": [
                "Delivery authority restored and documented",
                "SOW gate in place — no project enters delivery without Director sign-off",
                "AR collection process off the CEO's desk",
                "Active overrun projects stabilized with recovery plans"
            ]
        },
        {
            "phase": "Optimize",
            "timeline": "Months 3-9",
            "key_outcomes": [
                "Capacity planning model operational",
                "Pipeline discipline — no below-cost deals entering SOW stage",
                "Delivery standards documented and enforced",
                "Utilization tracking visible to Director of Delivery"
            ]
        },
        {
            "phase": "Scale",
            "timeline": "Months 9-18",
            "key_outcomes": [
                "Structured BD function generating pipeline independent of CEO network",
                "Rate recovery on renewals",
                "Firm positioned for engagements above current average project value"
            ]
        }
    ],
    "initiative_details": [
        {
            "item_id": "RM001",
            "timeline": "Month 1",
            "success_metric": "Written policy distributed to all delivery staff with CEO signature; Director of Delivery approves 100% of new SOWs before execution begins"
        },
        {
            "item_id": "RM002",
            "timeline": "Month 1",
            "success_metric": "AR aging report reviewed weekly; all accounts >60 days assigned a collection action with named owner"
        },
        {
            "item_id": "RM003",
            "timeline": "Months 1-2",
            "success_metric": "100% of new SOWs include delivery review sign-off before client signature; zero below-threshold-margin SOWs executed"
        },
        {
            "item_id": "RM004",
            "timeline": "Months 3-6",
            "success_metric": "Capacity model updated monthly; no new project assigned without confirmed available capacity"
        },
        {
            "item_id": "RM005",
            "timeline": "Months 9-12",
            "success_metric": "At least 30% of new pipeline generated through non-CEO channels within 12 months"
        }
    ],
    "dependency_table_rows": [
        {
            "initiative": "Implement Pre-Sales Delivery Review Gate",
            "depends_on": "Reinstate Delivery Director Authority"
        },
        {
            "initiative": "Implement Capacity Planning Model",
            "depends_on": "Reinstate Delivery Director Authority, Implement Pre-Sales Delivery Review Gate"
        },
        {
            "initiative": "Structured BD Function",
            "depends_on": "Implement Capacity Planning Model, Delivery Standards Documentation"
        }
    ],
    "risk_table_rows": [
        {
            "risk": "CEO continues to make delivery decisions informally despite written policy",
            "likelihood": "High",
            "mitigation": "Establish a 30-day review with the Director of Delivery to surface bypass incidents; CEO commits to escalation protocol at engagement kickoff"
        },
        {
            "risk": "Client pushback on SOW gate causes deal loss during Stabilize phase",
            "likelihood": "Medium",
            "mitigation": "Frame the SOW gate to clients as a quality control step that reduces scope disputes — pilot with two new engagements before full rollout"
        },
        {
            "risk": "Director of Delivery capacity is insufficient to absorb new governance responsibilities",
            "likelihood": "Medium",
            "mitigation": "Audit current Director workload in Month 1; if capacity is constrained, identify which delivery tasks can be delegated before adding governance responsibilities"
        }
    ],
    "next_steps_rows": [
        {
            "action": "CEO signs written delivery authority policy and distributes to team",
            "owner": "CEO",
            "completion_criteria": "Policy document signed, dated, and in the hands of all delivery staff"
        },
        {
            "action": "Assign AR collection ownership to Operations Manager",
            "owner": "CEO",
            "completion_criteria": "Operations Manager has access to AR aging report and is named owner of all accounts >30 days"
        },
        {
            "action": "Director of Delivery reviews all six overrunning projects and produces recovery plans",
            "owner": "Director of Delivery",
            "completion_criteria": "Recovery plan for each overrunning project reviewed with CEO; client communications plan in place where needed"
        },
        {
            "action": "Draft SOW review checklist with Director of Delivery",
            "owner": "Director of Delivery",
            "completion_criteria": "Checklist covers scope definition, delivery capacity confirmation, and margin floor; reviewed by CEO before use"
        },
        {
            "action": "Schedule engagement kickoff with TunTech team to review roadmap sequencing",
            "owner": "CEO",
            "completion_criteria": "Kickoff meeting scheduled; attendees confirmed; agenda distributed"
        }
    ]
}


async def _run(engagement_id: str):
    eng = EngagementRepository().get_by_id(engagement_id)
    if not eng:
        print(f"ERROR: Engagement {engagement_id} not found")
        return

    findings = FindingRepository().get_all(engagement_id)
    roadmap  = RoadmapRepository().get_all(engagement_id)
    signals  = ReportingRepository().get_engagement_signals(engagement_id)

    print(f"Engagement: {eng.get('firm_name')} ({engagement_id})")
    print(f"  Findings: {len(findings)}")
    print(f"  Roadmap items: {len(roadmap)}")
    print(f"  Signals: {len(signals)}")
    print(f"  Using mock narrative — no Claude API call")

    svc = ReportGeneratorService(engagement_id)

    from docx import Document
    import os
    template = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'assets', 'roadmap_template.docx'
    )
    doc = Document(template) if os.path.exists(template) else Document()
    svc._build(doc, eng, findings, roadmap, signals, MOCK_NARRATIVE)

    out_path = svc._output_path(eng)
    doc.save(out_path)
    print(f"\nSaved: {out_path}")
    print("\nVerify:")
    print("  [ ] Section 5 prose only — no bullet list")
    print("  [ ] Section 6 has economic summary table, then narrative — no bullets")
    print("  [ ] Section 7 Future State exists with metrics table")
    print("  [ ] Section 7 old Improvement Opportunities is gone")
    print("  [ ] Section 8.1 Priority Zero table with Owner + What This Unblocks")
    print("  [ ] Section 8.2 Roadmap Overview table with key outcomes as bullets")
    print("  [ ] Each phase table has Owner, Timeline, Success Metric, Economic Impact columns")
    print("  [ ] Section 8.6 dependency table exists")
    print("  [ ] Section 8.7 risk table exists")
    print("  [ ] Section 9 Immediate Next Steps exists")


if __name__ == '__main__':
    eid = sys.argv[1] if len(sys.argv) > 1 else 'E003'
    asyncio.run(_run(eid))
