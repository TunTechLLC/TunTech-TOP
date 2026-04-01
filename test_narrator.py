"""One-off script to test Report Narrator raw output quality.
Run from the repo root:
    python test_narrator.py E001
    python test_narrator.py E003

Prints each parsed section so quality can be assessed before wiring into the document.
Delete this file after prompt iteration is complete.
"""
import asyncio
import sys
import os

# Ensure repo root is on path
sys.path.insert(0, os.path.dirname(__file__))

from api.db.repositories.engagement import EngagementRepository
from api.db.repositories.finding import FindingRepository
from api.db.repositories.roadmap import RoadmapRepository
from api.db.repositories.agent_run import AgentRunRepository
from api.services.claude import generate_report_narrative


async def main(engagement_id: str):
    eng = EngagementRepository().get_by_id(engagement_id)
    if not eng:
        print(f"Engagement {engagement_id} not found")
        return

    synth_output = AgentRunRepository().get_accepted_output(engagement_id, "Synthesizer")
    if not synth_output:
        print(f"No accepted Synthesizer output for {engagement_id}")
        return

    findings = FindingRepository().get_all(engagement_id)
    roadmap  = RoadmapRepository().get_all(engagement_id)

    print(f"\nEngagement: {eng['firm_name']}  ({engagement_id})")
    print(f"Synthesizer output: {len(synth_output)} chars")
    print(f"Findings: {len(findings)}   Roadmap items: {len(roadmap)}")
    print("=" * 72)

    sections = await generate_report_narrative(synth_output, findings, roadmap, eng)

    if not sections:
        print("ERROR: generate_report_narrative returned empty dict")
        return

    SECTION_ORDER = [
        "executive_summary",
        "root_cause_narrative",
        "economic_impact_narrative",
        "roadmap_rationale:Stabilize",
        "roadmap_rationale:Optimize",
        "roadmap_rationale:Scale",
    ]

    # Print fixed sections first
    for key in SECTION_ORDER:
        if key in sections:
            print(f"\n{'=' * 72}")
            print(f"  {key.upper()}")
            print(f"{'=' * 72}")
            print(sections[key])

    # Then domain analysis sections
    domain_keys = [k for k in sections if k.startswith("domain_analysis:")]
    for key in sorted(domain_keys):
        domain = key[len("domain_analysis:"):]
        print(f"\n{'=' * 72}")
        print(f"  DOMAIN ANALYSIS: {domain}")
        print(f"{'=' * 72}")
        print(sections[key])

    # Report any unexpected keys
    all_expected = set(SECTION_ORDER) | set(domain_keys)
    unexpected = set(sections.keys()) - all_expected
    if unexpected:
        print(f"\nUnexpected keys in output: {unexpected}")


if __name__ == "__main__":
    engagement_id = sys.argv[1] if len(sys.argv) > 1 else "E001"
    asyncio.run(main(engagement_id))
