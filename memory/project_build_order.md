---
name: Agreed build order — Accuracy and Review phase, then Technical Debt
description: Current build sequence: 5 accuracy/review items before all output quality features. Identified via architectural review 2026-04-24.
type: project
---

Agreed build order as of 2026-04-24. Accuracy and human-in-the-loop items are now the
top priority before first real client engagement. Technical debt items follow.

**Why:** Architectural review found that the first two agent prompts lack grounding guards,
the agent review UI makes meaningful verification impractical, and Skeptic recommendations
have no UI affordances. These are higher risk to client deliverable accuracy than any output
quality feature.

## Build Order — Accuracy and Review (do first)

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| A1 | Agent Grounding Guards | 1 | Prompt-only. DIAGNOSTICIAN_PROMPT + DELIVERY_PROMPT in claude.py |
| A2 | Agent Review UI Redesign | 2–3 | Parse signal IDs from output, inline reference cards, sort case packet by confidence |
| A3 | Skeptic Recommendations as Actionable UI | 1–2 | Pattern downgrade cards in PatternPanel, C-code badges in SignalPanel |
| A4 | Evidence Traceability on Findings | 1 | Full signal chain on candidate review cards |
| A5 | Signal ID Validation on Agent Output | 1 | Flag ghost references at accept time |

## Build Order — Technical Debt (after accuracy items)

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| 1 | Domain Maturity Scoring | 1 | Independent |
| 5 | Visual 3 — Causal Chain | 1 | Requires split (already done) |
| 6 | Three Systemic Drivers Section | 1 | Low priority — may be redundant with causal chain |
| 7 | Auto-Suggest Knowledge | 1 | Detect-review-load for knowledge panel |
| 8 | Standardize Economic Output | 1 | After economic structured fields work (done) |
| 9 | Structured File Metadata Capture | 1 | Medium priority — filename convention is working workaround |
| 10 | Editable Engagement Info | 1 | Real gap — needed before first paid client |
| 11 | PowerPoint Export | 1 | After domain maturity scoring |
| — | Checkpoint 5 — Dry Run 5 | milestone | Full feature validation |

## Key Architectural Findings (2026-04-24)

**Agent prompt gaps:**
- DIAGNOSTICIAN_PROMPT and DELIVERY_PROMPT have no grounding guards — no prohibition on
  fabricating signal references or asserting facts not in the case packet
- Economics, Skeptic, Synthesizer, and Narrator prompts all have explicit grounding/hallucination
  prevention sections. First two agents do not.

**Agent review UI gap:**
- Agent outputs shown as raw prose in scrollable pre box — no structured signal reference display
- Verifying a single signal citation requires switching tabs and hunting manually
- In practice this means agents are accepted without meaningful review

**Skeptic integration gap:**
- Skeptic recommends pattern downgrades and generates C-codes, but these are prose-only
- No UI affordance connects Skeptic output to Pattern panel or Signal panel
- Recommendations not acted on because there is no mechanism to act on them

**Evidence chain gap:**
- Findings candidate cards show prose fields only — no pattern→signal→quote chain
- Accept/reject decisions made without seeing the underlying evidence

**Signal ID validation gap:**
- Ghost signal references in agent output propagate through the pipeline unchecked
- Low probability but high impact — surfaces in real engagement conditions
