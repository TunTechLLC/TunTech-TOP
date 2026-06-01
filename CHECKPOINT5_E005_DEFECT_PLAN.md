# Checkpoint 5 — Defect Plan (E005, Stratum Cloud Partners)

**This is a test artifact, not an engagement step.** It exists only to validate the
Post-Assembly QA Stage end-to-end. You plant known defects, run the pipeline, and
confirm each one is caught by the right agent at the right tier. It is the "answer
key" that turns a dry run into a real checkpoint. You do this once for the
checkpoint; never on a real client engagement.

**Pairing:** the engagement source lives in
`...\005_Stratum\` (interviews `02_Interviews`, documents `03_Client_Documents`).
Keep this plan and anything in `08_Misc` **out of** the processing folders.

---

## How to use this

1. **Phase A — source plant** is already done (baked into the SOW). Nothing to do.
2. **Phase B — risk-row name** is done in the app *before* generating the report.
3. **Phase C — generate v1**, then confirm the Narrator Trust Report catches Phase B.
4. **Phase D — inject the v1-level defects** into the v1 `.docx` (they are errors that
   only exist *after* generation, so they can't be planted in source).
5. **Phase E — run QA-1/2/3** and confirm each defect is caught at the expected tier.
6. **Phase F — run the revision**, accept the caught items, confirm v2 is clean
   (especially §10.7/10.8 — the applier fix) and structured data/figures intact.
7. Fill in the **Results** table and score against **Pass criteria**.

---

## Planted defects

| ID | Catcher | Phase | Where | Expected tier |
|----|---------|-------|-------|---------------|
| D1 | QA-1 Coverage | A (pre-planted) | SOW §6 — dated critical dependency | T1–T2 |
| D2 | QA-2 Coherence | D (inject into v1) | Executive Briefing — margin figure | T1 |
| D3 | QA-3 Editorial (Python) | D (inject into v1) | a Domain finding — leaked S-code | T1 |
| D5 | Narrator Auditor (Session 1) | B (app, pre-report) | a Key Risk item — individual's name | n/a (carry-forward) |

> D4 (undefined acronym) is optional. QA-3's Python acronym check uses a small fixed
> list (PMO/SOW). If you want a deterministic bonus catch, leave "PMO" unexpanded at
> its first use in the Executive Briefing when injecting D2/D3.

---

### D1 — Coverage (QA-1) — ALREADY PLANTED
- **File:** `03_Client_Documents\Doc_SOW_Pelican_CoreBanking.docx`, Section 6
  (Client Responsibilities).
- **The item:** *"Pelican Financial must provision production AWS account access and
  complete the joint security architecture sign-off no later than June 12, 2026.
  This item is on the critical path. Any delay … shifts all downstream milestones …"*
- **Why it should reach the roadmap:** it's a specific, dated, near-term critical-path
  dependency — exactly the kind of time-sensitive item that belongs in Priority Zero /
  near-term actions and that pipelines tend to drop into generic prose.
- **Expected catch:** QA-1 produces a coverage item noting the June 12 security sign-off
  dependency is missing from / under-surfaced in the v1 roadmap.
- **Pass:** QA-1 flags it, at Tier 1 or Tier 2.

### D2 — Coherence (QA-2) — inject into v1 (Phase D)
- **Where:** v1 `.docx`, the **Executive Briefing** margin sentence.
- **Inject:** state that gross margin *"declined from 41% to 33% — an 8-point erosion."*
- **The contradiction:** every other section (Financial Summary table, Domain Analysis,
  Economic Impact) uses **38.6% → 33.1%, a 5.5-point** decline. 41%/8pt vs 38.6%/5.5pt
  is a cross-section numeric contradiction.
- **Expected catch:** QA-2 flags the margin-figure contradiction across sections.
- **Pass:** QA-2 item names it, at **Tier 1** (objective error).

### D3 — Editorial (QA-3 Python) — inject into v1 (Phase D)
- **Where:** v1 `.docx`, the plain-English summary of any Domain Analysis finding.
- **Inject:** append an internal signal code to a sentence, e.g. *"… (per S047)."*
- **Expected catch:** QA-3 Python pipeline flags the leaked `S047` code
  (`\bS\d{3,4}\b`), `source = python`.
- **Pass:** QA-3 item flags S047, at **Tier 1**.

### D5 — Narrator Auditor Session 1 — plant in the app (Phase B)
- **Where:** the **Roadmap** tab, a **Key Risk** item, *before* generating the report.
- **Plant:** add/edit a risk row that names an individual, e.g.
  *"Daniel Reyes is a single point of failure on the Pelican migration."*
  (Daniel Reyes is the SOW's named lead architect — thematically consistent.)
- **Expected catch:** when you generate the report, the **Narrator Audit — Trust Report**
  panel in the Report tab flags the *individual-names-in-risk-rows* dimension (HR-exposure
  heuristic) as failed, citing the name.
- **Pass:** the Trust Report shows that dimension flagged on the v1 run.
- **Note:** this validates the *carry-forward* Session-1 auditor, which runs at report
  generation — before the QA stage.

---

## Results (fill in during the run)

| ID | Caught? | By the expected agent? | Tier (got / expected) | Notes |
|----|---------|------------------------|-----------------------|-------|
| D1 | | | / T1–T2 | |
| D2 | | | / T1 | |
| D3 | | | / T1 | |
| D5 | | | n/a | |

**False positives to watch:** note any Tier-1 item that is *not* a real error
(Tier-1 precision is a pass criterion — overrides should be rare exceptions).

---

## Pass criteria (from BACKLOG — Checkpoint 5)

- QA tab appears once v1 exists; QA-1/2/3 each run and produce tiered items.
- **Each planted defect (D1–D3) is caught at the correct tier** — Tier-1 defects appear
  as Tier 1, not buried in Tier 3.
- **Tier-1 precision:** no false-Tier-1 items.
- D5: the Narrator Trust Report catches the planted risk-row name on v1.
- Consultant reaches a defined endpoint — no items left pending.
- Revision produces v2 incorporating accepted items **without breaking structured data,
  economic figures, or analytical voice**, and **§10.7/10.8 stay clean** (the applier fix).
- v1 and v2 both accessible; the edit-list comparison shows the changes.
- Carry-forward still works: evidence summaries (no P-codes) + 2–3 quotes per finding;
  capability statements on roadmap items; economic context; ≥1 dependency surfaced;
  Quick Wins; domain maturity scorecard with "No data" for unexamined domains.
