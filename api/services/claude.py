import os
import logging
import anthropic

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL          = "claude-sonnet-4-6"
MAX_TOKENS     = 8000
PROMPT_VERSION = "2.0"

DIAGNOSTICIAN_PROMPT = "You are the Diagnostician agent in the TOP multi-agent consulting diagnostic system. Analyze the case packet and produce a structured diagnostic assessment including: hypothesis assessment, pattern cluster analysis, primary failure sequence, confidence assessment, and open questions for specialist agents."

DELIVERY_PROMPT = "You are the Delivery Operations agent in the TOP multi-agent consulting diagnostic system. Analyze delivery operations and produce: delivery failure sequence, root cause analysis, improvement priorities, behavioral constraints, and Director of Delivery assessment."

ECONOMICS_PROMPT = "You are the Consulting Economics agent in the TOP multi-agent consulting diagnostic system. Analyze the financial economics and produce: economic baseline, margin decomposition, utilization analysis, economic impact by pattern, ROI case, and interdependency table."

SKEPTIC_PROMPT = "You are the Skeptic agent in the TOP multi-agent consulting diagnostic system. Challenge prior agent outputs and produce: challenged claims, evidence gaps, downgrade recommendations, alternative explanations, and overall confidence rating."

SYNTHESIZER_PROMPT = "You are the Synthesizer agent in the TOP multi-agent consulting diagnostic system. Produce the integrated final diagnostic including: response to Skeptic, integrated findings, priority zero items, unresolved dependencies, and economic summary."

PATTERN_DETECTION_PROMPT = """You are analyzing signals from a consulting firm engagement to detect operational patterns.

Review the signals provided and identify which patterns from the TOP pattern library are triggered. Return ONLY a JSON array with no preamble, no explanation, no markdown code fences.

Each item must have exactly these fields:
- pattern_id: string (e.g. "P12")
- confidence: string — exactly "High", "Medium", or "Hypothesis"
- notes: string — 1-2 sentences explaining which signals triggered this pattern

Confidence rules:
- High: 3 or more strong signals directly confirm this pattern
- Medium: 2 signals support this pattern or 1 strong signal plus context
- Hypothesis: 1 signal suggests this pattern but evidence is thin

The next EP ID starts at [NEXT_EP_ID] for engagement [ENGAGEMENT_ID].

Return format:
[
  {"pattern_id": "P12", "confidence": "High", "notes": "Evidence here."}
]"""

AGENT_REGISTRY = {
    "Diagnostician": {
        "sequence":              1,
        "domain":                "Cross-domain",
        "required_prior_agents": [],
        "prompt":                DIAGNOSTICIAN_PROMPT,
    },
    "Delivery Operations": {
        "sequence":              2,
        "domain":                "Delivery Operations",
        "required_prior_agents": ["Diagnostician"],
        "prompt":                DELIVERY_PROMPT,
    },
    "Consulting Economics": {
        "sequence":              3,
        "domain":                "Consulting Economics",
        "required_prior_agents": ["Diagnostician"],
        "prompt":                ECONOMICS_PROMPT,
    },
    "Skeptic": {
        "sequence":              4,
        "domain":                "Quality Control",
        "required_prior_agents": ["Diagnostician", "Delivery Operations", "Consulting Economics"],
        "prompt":                SKEPTIC_PROMPT,
    },
    "Synthesizer": {
        "sequence":              5,
        "domain":                "Synthesis",
        "required_prior_agents": ["Diagnostician", "Delivery Operations", "Consulting Economics", "Skeptic"],
        "prompt":                SYNTHESIZER_PROMPT,
    },
}


async def call_claude(
    case_packet:   str,
    prior_outputs: list,
    prompt:        str,
) -> str:
    parts = [f"CASE PACKET:\n\n{case_packet}"]
    if prior_outputs:
        for i, output in enumerate(prior_outputs, 1):
            if output:
                parts.append(f"PRIOR AGENT OUTPUT {i}:\n\n{output}")
    user_message = "\n\n---\n\n".join(parts)
    logger.info(f"Calling Claude API - context length: {len(user_message)} chars")
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    response = message.content[0].text
    logger.info(f"Claude API response received - {len(response)} chars")
    return response