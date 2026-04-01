"""One-off script to test Roadmap Extractor raw output quality.
Run from the repo root:
    python test_roadmap_extractor.py E002
    python test_roadmap_extractor.py E003

Prints extracted candidates grouped by phase so quality can be assessed.
Delete this file after prompt iteration is complete.
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from api.db.repositories.engagement import EngagementRepository
from api.db.repositories.finding import FindingRepository
from api.db.repositories.agent_run import AgentRunRepository
from api.services.claude import extract_roadmap_from_synthesizer


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

    print(f"\nEngagement: {eng['firm_name']}  ({engagement_id})")
    print(f"Synthesizer output: {len(synth_output)} chars   Findings: {len(findings)}")
    print("=" * 72)

    raw = await extract_roadmap_from_synthesizer(synth_output, findings)

    try:
        candidates = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print("Raw output:")
        print(raw[:500])
        return

    print(f"\n{len(candidates)} candidates extracted\n")

    for phase in ['Stabilize', 'Optimize', 'Scale']:
        phase_items = [c for c in candidates if c.get('phase') == phase]
        if not phase_items:
            continue
        print(f"\n{'─' * 72}")
        print(f"  {phase.upper()} ({len(phase_items)} items)")
        print(f"{'─' * 72}")
        for item in phase_items:
            print(f"\n  [{item.get('priority','?')} priority / {item.get('effort','?')} effort]")
            print(f"  {item.get('initiative_name','')}")
            print(f"  Domain: {item.get('domain','')}")
            if item.get('estimated_impact'):
                print(f"  Impact: {item['estimated_impact']}")
            if item.get('rationale'):
                print(f"  Rationale: {item['rationale']}")

    # Flag any invalid field values
    from api.utils.domains import VALID_DOMAINS
    valid_phases    = {'Stabilize', 'Optimize', 'Scale'}
    valid_priority  = {'High', 'Medium', 'Low'}
    valid_effort    = {'High', 'Medium', 'Low'}
    issues = []
    for i, c in enumerate(candidates):
        if c.get('domain') not in VALID_DOMAINS:
            issues.append(f"Item {i}: invalid domain '{c.get('domain')}'")
        if c.get('phase') not in valid_phases:
            issues.append(f"Item {i}: invalid phase '{c.get('phase')}'")
        if c.get('priority') not in valid_priority:
            issues.append(f"Item {i}: invalid priority '{c.get('priority')}'")
        if c.get('effort') not in valid_effort:
            issues.append(f"Item {i}: invalid effort '{c.get('effort')}'")
    if issues:
        print(f"\nVALIDATION ISSUES:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\nAll field values valid.")


if __name__ == "__main__":
    engagement_id = sys.argv[1] if len(sys.argv) > 1 else "E002"
    asyncio.run(main(engagement_id))
