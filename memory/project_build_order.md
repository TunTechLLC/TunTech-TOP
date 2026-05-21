---
name: Build order — Audit Layer is the top priority
description: Build sequence revised 2026-05-21. Narrator Output Auditor → Editable Engagement Info → Checkpoint 5, then remaining technical debt. Driven by Word doc review burden as binding constraint on confidence.
metadata:
  type: project
---

Build order as of 2026-05-21. Audit layer is the top priority because Word doc review
burden (4–8 hours/engagement, driven by lack of confidence rather than known errors) is
the binding constraint on multi-engagement throughput. Audit infrastructure also changes
the build economics of every future report feature — once it exists, new output ships
with its own checks instead of extending the review window.

**Why:** Prompt-based quality enforcement has hit diminishing returns. Adding more rules
to REPORT_NARRATOR_PROMPT trades one violation for another. Architectural review on
2026-05-21 concluded that a post-generation audit layer (mechanical Python checks on
narrator JSON output) is the right shape — produces a credible trust report so the
consultant can skip dimensions of review, rather than trying to "find errors the
consultant misses."

**How to apply:** Treat the audit layer as the gate to scaling beyond first paid client.
Build items 4–9 only after the audit infrastructure exists, so each new output feature
ships with its own checks rather than extending the review window. Kill-switch built
into the sequence — if Session 1 doesn't compress review time on the next engagement,
do not build Session 2.

## Build Order

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| ✅ | Narrator Output Auditor — Session 1 (mechanical checks) | 1 | Shipped 2026-05-21 |
| — | Measure Word doc review time on next engagement | — | Kill-switch decision point |
| 1 | Narrator Output Auditor — Session 2 (narrow Claude checks) | 1 | Conditional on kill-switch result |
| 2 | Editable Engagement Info | 1 | Hard requirement before first paid client |
| — | Checkpoint 5 — Dry Run 5 | milestone | Validates items 1–2 |
| 3 | PowerPoint Export | 1 | Ships with audit checks |
| 4 | Visual 3 — Causal Chain | 1 | Ships with audit checks |
| 5 | Standardize Economic Output | 1 | Priority driven by auditor data |
| 6 | Three Systemic Drivers Section | 1 | Low — may be redundant with Visual 3 |
| 7 | Structured File Metadata Capture | 1 | Medium — convention works as workaround |
| 8 | Auto-Suggest Knowledge | 1 | Lowest — current manual flow works |

## Completed Phases (historical context)

The Accuracy and Review phase (A1–A5) and Domain Maturity Scoring shipped between
2026-04-24 and 2026-05-21. See PROGRESS.md for the full record.

| Item | Why it shipped first |
|------|----------------------|
| A1 — Agent Grounding Guards | Diagnostician and Delivery prompts had no hallucination guards while Economics/Skeptic/Synthesizer/Narrator did |
| A2 — Agent Review UI | Agent outputs were unstructured prose; verifying signal citations required tab-switching |
| A3 — Skeptic Recommendations as Actionable UI | Skeptic generated pattern downgrades and C-codes with no UI affordance |
| A4 — Evidence Traceability on Findings | Findings candidate cards showed prose only — no pattern→signal→quote chain |
| A5 — Signal ID Validation | Ghost signal references in agent output propagated through the pipeline unchecked |
| Domain Maturity Scoring | Section 2 scorecard, independent feature |
| Narrator Output Auditor Session 1 | 12 mechanical Python checks on raw narrator JSON before Word render. Audit returns trust report consumed by ReportPanel. Two post-test passes hardened false positives (dollar regex letter-eating, org-name vs person-name distinction). 57/57 tests pass. |

## Architectural Findings (2026-04-24 — original)

The Accuracy/Review prioritization was driven by these findings. Still relevant for
understanding why A1–A5 sequenced ahead of output quality features.

- Agent prompt gaps: first two agents had no grounding guards
- Agent review UI gap: unstructured prose made review impractical
- Skeptic integration gap: recommendations had no UI to act on
- Evidence chain gap: findings shown without underlying evidence
- Signal ID validation gap: ghost references unchecked

## Architectural Finding (2026-05-21 — new)

Review burden is the binding constraint on engagement throughput. Consultant spends
4–8 hours per engagement on Word doc review and ~4 hours on intermediate stage review.
The Word doc review is an unbounded paranoid scan because failure modes are unpredictable.
Prompt-based enforcement has hit diminishing returns.

The audit layer addresses this directly: produces a credible trust report so clean
verdicts let the consultant skip dimensions of review, focusing remaining time on
irreducible consultant judgment (client appropriateness, voice, strategic coherence).

**Scope decision:** audit the narrator JSON output before Word render, not the roadmap
alone. Earlier framing as "Roadmap Auditor" was too narrow — the leakage modes (R-codes,
economic figures, anonymization, length rules) span the whole narrator output.

**Discipline rule for Session 2 (if built):** audit prompts only check specific named
violations, structured output, one rule = one check. New quality concern → new audit
rule, never broaden scope. Otherwise the auditor accumulates the same prompt bloat that
broke REPORT_NARRATOR_PROMPT.

Related memories: [[feedback_architecture]] (architect-first thinking applies here —
audit layer must scale to multi-user cloud version without rework).
