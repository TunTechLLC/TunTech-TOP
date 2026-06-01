---
name: Build order — Post-Assembly QA Stage COMPLETE
description: Build sequence. QA-1/2/3/4/5 ALL shipped. QA-5 = integrated QA tab (wraps 3 detection panels + verify-after revision edit-list comparison). Checkpoint 5 dry run is next.
metadata:
  type: project
---

Build order as of 2026-06-01. Post-Assembly QA Stage is COMPLETE: QA-1, QA-2,
QA-3 (split), QA-4 (in-place edit-list revision), and QA-5 (integrated QA Tab UI)
are ALL SHIPPED. **Checkpoint 5 dry run is the next work** — end-to-end QA Stage
validation with a new fictional client and planted defects. This stage replaced
the prior Auditor Session 2 + kill-switch sequence. Editable Engagement Info
downgraded from "hard requirement" to nice-to-have per consultant clarification
on 2026-05-30.

**QA-5 as-built (shipped 2026-06-01):** ONE `QA` tab (`QAPanel.jsx`) replaced the
three temporary `qa1`/`qa2`/`qa3` tabs. The three detection panels were WRAPPED,
not rebuilt (lowest regression risk) — each gained one additive optional
`onCountsChange` prop so the parent shows live counts in collapsible section
headers without lifting state. Gate: new `GET /{id}/qa-status` (pure file-existence,
in `qa_revision.py`); no v1 → "Generate the roadmap first". Added `GET /qa-revision/v1`
to serve the SAVED v1 off disk — `/report/download` regenerates and would desync
the comparison. **Comparison = the structured edit-list, NOT a raw docx text-diff**
(a text-diff would reintroduce the rendering noise QA-4's in-place-edit design
eliminated — confirmed with Victor before build). Revision is **verify-after**:
edits apply to make v2, then `QAPanel` shows `QARevisionEdits` grouped by outcome
(applied / needs-your-hand / manual / verify-coverage / handled), before→after,
source chip, match_method badge (non-exact sorted to top of "applied"). "Run Final
Revision" gates on ≥1 accepted item. "Mark handled" → `PATCH outcome:'manual_done'`.
**Soft sequencing only** — the old BACKLOG claim that Coherence consumes Coverage
items is stale (QA-2 is a standalone read). 93/93 tests pass (no new — trivial
file-existence endpoints, no TestClient harness in suite; verified in manual run).

**Why:** E004 Cowork three-pass QA produced ~65 verifiable items (27 Coverage, 21
Coherence, 31 Editorial) with near-zero noise rate. Three Tier-1 errors confirmed
end-to-end against source: $186K mislabel in Executive Briefing ("EBITDA lost per
point of growth" applied to annual bench cost); $540K vs $727K arithmetic error in
Economic Impact narrative; P14 "this week" PM assignment urgency dropped from
Priority Zero. None of these are catchable by Narrator Auditor Session 1's
mechanical Python checks — they are semantic, cross-section, or source-coverage
failures. ChatGPT v44 demonstrated single-shot full-document revision applies
accepted items without breaking structured data labels, economic figures, or
analytical voice — proving the mechanism for QA-4. Kill-switch retired because
E004 produced the evidence the kill-switch was waiting for.

**Model evidence:** The three Cowork QA passes were run on **Opus (latest, currently 4.7)**. The
v44 single-shot revision was run on **ChatGPT**. No Claude data point exists
yet on the revision task — QA-4 model selection requires empirical validation
against the v44 reference before locking.

**How to apply (updated 2026-06-01 — QA-1/2/3/4/5 ALL shipped):**
- **Next session: Checkpoint 5 dry run.** The QA Stage is fully built; the next
  work is end-to-end validation with a new fictional client and planted defects
  (Coverage/Coherence/Editorial + a narrator-level defect). See BACKLOG.md
  Checkpoint 5 pass criteria.
- _(historical) QA-5 QA Tab UI — shipped 2026-06-01._ Integrated engagement tab that runs
  QA-1/2/3 detection + the QA-4 revision in sequence and renders the v1↔v2 diff.
  Backend endpoints all exist (`/api/engagements/{id}/qa-coverage|qa-coherence|
  qa-editorial|qa-revision`). QA-4 exposes run / list / v2-download / patch-outcome.
- **QA-4 shipped with a REVERSED architecture (2026-05-31):** NOT single-shot
  full-document regeneration. Diff analysis of the v44 reference proved it was an
  in-place edit of v43 (72% identical, all 29 tables preserved, **0 deletions**),
  so regeneration would pollute the v1↔v2 diff and defeat the comparison goal.
  As-built: Claude returns a structured **edit list** (anchor + `context_before`
  + new_text + `source_item_id`); code applies edits to v1.docx in place via a
  tolerant matcher (exact→context→fuzzy→**flag**, run-level replace preserving
  formatting) and saves v2.docx. v1 never modified. The table-cell limitation was
  fixed with a **prompt-only** single-cell-anchor instruction (no applier code).
- **Reconciliation is the load-bearing trust feature:** every edit carries
  `source_item_id`; accepted items with no edit are recorded `unaddressed`. The
  E004 smoke proved this caught 19 of 49 accepted items that would otherwise have
  been silently dropped — invisible in v2 AND in the diff review.
- **QA-3 implementation refinement (vs original BACKLOG language):** the Python
  pipeline lives in NEW module `api/services/editorial_auditor.py`, not as an
  extension of `narrator_auditor.py`. The two auditors check different artifacts
  (pre-render JSON vs post-render text) and mixing them muddies the contract.
- **QA-2 implementation refinement:** does NOT pass QA-1 accepted items as
  context (deviation from BACKLOG flagged before build). Standalone read
  matches Cowork's actual workflow and "do not generate X" instructions are
  fragile in LLM prompts.

**Model selection — locked 2026-05-30:**
- **QA-1, QA-2, QA-3's Claude check: Opus (latest, currently 4.7).** Matches the Cowork detection
  model that produced the ~65 items with near-zero noise on E004. Implementation:
  pass `model="claude-opus-4-7"` to specific call functions in
  `api/services/claude.py`, do NOT change global `TOP_MODEL` default — keeps the
  rest of TOP on Sonnet.
- **QA-4 model: Opus 4.7 — LOCKED 2026-05-31.** Step 0 empirical test (throwaway
  script, real E004 v43 + accepted items) compared 4.7 vs 4.8 on the edit-list
  task with a hardened prompt: **4.7 won** (97% clean anchor applicability, 35
  auto-applied) over 4.8 (91%, 21 auto-applied — 4.8 over-flagged simple edits as
  `manual`). Counterintuitive but real: 4.8 is a more conservative *critic*, which
  is the wrong trait for an *apply-already-accepted-items* task. The mandatory
  QA-5 diff review is the safety backstop, so maximal correct automation wins.
  `model="claude-opus-4-7"` passed per-call (global TOP_MODEL stays Sonnet), same
  pattern as QA-1/2/3. NOTE: 4.8 may be the better pick for the *detection* agents
  (QA-1/2/3) — untested; a separate experiment if ever revisited.

**Versioning convention — locked 2026-05-30:**
- **v1 and v2 saved as separate files.** Naming:
  `OPD_Roadmap_<engagement_id>_v1.docx` (Report Generator output) and
  `OPD_Roadmap_<engagement_id>_v2.docx` (QA-4 Revision output). Neither
  overwrites the other. Both live in the engagement's reports_folder.
- **Report Generator filename update required when QA-4 ships.** Append `_v1`
  to the Report Generator's output filename in
  `api/services/report_generator.py` so the convention is consistent — even
  on engagements where QA-4 hasn't been run, the Report Generator's output
  is the v1 of a pair.
- **Rationale:** Keeping v1 is load-bearing — audit trail per engagement, diff
  view substance (the mandatory v2 review diffs against v1), cross-engagement
  pattern signal (recurring v1→v2 deltas drive future upstream improvements),
  and consultant trust (side-by-side proves QA earned its keep).

**Tiering — locked 2026-05-30:**
- **Each QA detection item carries a `tier` field (1, 2, 3).** Tier 1 = obvious
  accept (factual errors, contradictions, time-sensitive source items flagged
  as decision-required); Tier 2 = judgment call; Tier 3 = low confidence.
  Rubric is agent-specific (see BACKLOG QA-1/QA-2/QA-3 sections).
- **Tier 1 UI: batch confirmation, not per-item.** Tier 1 items default-accepted,
  shown collapsed with per-item unaccept override. Consultant clicks one
  "Confirm Tier 1 — proceed" per agent. Tier 2 shown expanded for individual
  accept/reject. Tier 3 collapsed by default, labeled "Low confidence —
  expand to review". Per-item Tier 1 confirmation was rejected: produces
  rubber-stamp fatigue without adding real safety. Real safety is the
  mandatory v2 diff view in QA-5.
- **Frame: confidence and risk reduction, not time savings.** Consultant
  explicitly chose this framing on 2026-05-30. Time savings from QA Stage
  are real but bounded (1–5 hours per engagement). The value is structured
  judgment with a defined endpoint instead of paranoid blank-slate scanning.
  Checkpoint 5 pass criteria reflect this framing.

## Build Order

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| ✅ | Narrator Output Auditor — Session 1 (mechanical checks) | 1 | Shipped 2026-05-21 |
| ✅ | QA-1 Coverage Check Agent | 1 | Shipped 2026-05-30 — 34 items on E004 smoke |
| ✅ | QA-2 Coherence Check Agent | 1 | Shipped 2026-05-30 — 10 items on E004 smoke ($186K mislabel caught) |
| ✅ | QA-3 Editorial Check (split) | 1 | Shipped 2026-05-30 — 9 items on E004 smoke (6 Python in editorial_auditor.py + 3 Claude voice) |
| ✅ | QA-4 Revision Agent | 1 | Shipped 2026-05-31 — **in-place edit-list** (NOT single-shot regeneration), Opus 4.7, reconciliation. E004 smoke: 49 accepted → 29 applied, 19 unaddressed surfaced |
| ✅ | QA-5 QA Tab UI | 1 | Shipped 2026-06-01 — one `QA` tab wrapping the 3 detection panels + verify-after revision edit-list comparison; `qa-status` gate + `qa-revision/v1` download. Build clean, 93/93 |
| — | Checkpoint 5 — Dry Run 5 | milestone | NEXT — validates QA Stage end-to-end |
| 1 | Editable Engagement Info | 1 | Nice-to-have; can slot anywhere |
| 2 | PowerPoint Export | 1 | Ships with audit checks |
| 3 | Standardize Economic Output | 1 | Priority driven by QA Stage data |
| 4 | Structured File Metadata Capture | 1 | Medium — convention works as workaround |
| 5 | Auto-Suggest Knowledge | 1 | Lowest — current manual flow works |

## E004 Artifacts — Evidence Base

QA artifacts live in `C:\001-cowork-projects\Northstar-working`:
- `OPD_Transformation_Roadmap_E004 v43.docx` — baseline (Report Generator v1)
- `OPD_Transformation_Roadmap_E004_v44_ChatGPT.docx` — ChatGPT-revised v2
- `E004_Gap_Analysis.xlsx` — Coverage pass (27 items)
- `E004_Roadmap_Internal_Audit.docx` — Coherence pass (21 items)
- `E004_Roadmap_Editorial_Review.docx` — Editorial pass (31 items)

Extracted text copies in `C:\Dev\TunTech\TOP\qa_review_extract\`. Use these as
regression test material when building QA-1, QA-2, QA-3 prompts.

## Completed Phases (historical context)

The Accuracy and Review phase (A1–A5), Domain Maturity Scoring, and Narrator
Output Auditor Session 1 shipped between 2026-04-24 and 2026-05-21. See
PROGRESS.md for the full record.

| Item | Why it shipped first |
|------|----------------------|
| A1 — Agent Grounding Guards | Diagnostician and Delivery prompts had no hallucination guards while Economics/Skeptic/Synthesizer/Narrator did |
| A2 — Agent Review UI | Agent outputs were unstructured prose; verifying signal citations required tab-switching |
| A3 — Skeptic Recommendations as Actionable UI | Skeptic generated pattern downgrades and C-codes with no UI affordance |
| A4 — Evidence Traceability on Findings | Findings candidate cards showed prose only — no pattern→signal→quote chain |
| A5 — Signal ID Validation | Ghost signal references in agent output propagated through the pipeline unchecked |
| Domain Maturity Scoring | Section 2 scorecard, independent feature |
| Narrator Output Auditor Session 1 | 12 mechanical Python checks on raw narrator JSON before Word render. Two post-test passes hardened false positives. 57/57 tests pass. |

## Architectural Finding (2026-05-30 — current)

Mechanical Python checks (Narrator Auditor Session 1) catch format-level violations
but not the highest-stakes errors. The error classes that embarrass the consultant
in front of a paying client are:

1. **Coverage failures** — specific source items (named risks, time-sensitive
   decisions, behavioral quotes that establish causal chains) dropped between
   Synthesizer and rendered document. Distributed across Synthesizer judgment,
   Narrator prose generation, and Report Generator template surfacing.
2. **Coherence failures** — semantic mislabels, cross-section number mismatches,
   arithmetic errors in narrative, priority/effort inconsistencies between
   finding cards and initiative tables.
3. **Editorial failures** — internal codes leaking, undefined acronyms, role
   terminology drift, voice intrusions (vendor pitch tone in analytical document).

Auditor Session 1 catches none of these. QA-1, QA-2, and QA-3 are the right shape
because they read the rendered document and either compare it to source (QA-1) or
read it standalone for internal consistency (QA-2, QA-3). The detect-review-revise
pattern matches the existing detect-review-load pattern used elsewhere in TOP.

**QA-4 architecture — CORRECTED 2026-05-31.** The 2026-05-30 plan assumed
single-shot full-document regeneration. That was reversed during the build:
diffing the v44 reference against v43 showed v44 is an *in-place edit* (72%
identical, all 29 tables preserved, 0 deletions), not a regeneration. Two
consequences made in-place editing correct, not optional: (1) regenerating v2
from full text would pollute the v1↔v2 diff with rendering noise, defeating the
consultant's comparison goal; (2) a structured edit-list keeps Claude from
touching the 72% that should not change. So as-built QA-4 = edit-list in, code
applies to v1.docx in place. The per-item-patch label was a red herring — this is
one Claude call returning many edits, not N calls. See PROGRESS.md QA-4 row.

## Architectural Finding (2026-05-21 — superseded but preserved)

The 2026-05-21 framing held that Word doc review burden (4–8 hours per engagement,
driven by lack of confidence rather than known errors) was the binding constraint,
and that mechanical Python auditing of narrator JSON was the right shape. The
shape was partially right (Session 1 shipped and works as designed) but
incomplete — Session 1's dimensions miss the failure modes that actually produce
client-embarrassment risk. The QA Stage covers the missing dimensions.

The 2026-05-21 discipline rule still applies to any audit prompt: check specific
named violations, structured output, one rule = one check. Applied to QA-2 and
QA-3's Claude pieces — do not let them drift into kitchen-sink editorial agents.

Related memories: [[feedback_architecture]] (architect-first thinking — QA Stage
must survive multi-user cloud migration without rework; structured data preserved
across revision is part of that constraint).
