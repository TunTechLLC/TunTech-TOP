# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

**This file holds only remaining work.** Completed work lives in `PROGRESS.md`.

---

## CURRENT — Signal-Layer Remediation done; Decision Surfacing is next

The **Signal-Layer Remediation** (Phase 1+2: E, A, A2, D, B, C1, plus engagement-scoped dedup,
findings-cap, and Primary-Cause fixes) is **complete and re-baselined on E007** (2026-06-15) —
recorded in `PROGRESS.md`, detailed in `SIGNAL_LAYER_REMEDIATION_PLAN.md`. The re-baseline
validated the core mission: economics **E1/E2 now appear** (were missing in E006 v2), **no
silent file loss**, Cardinal flagged, **$3.5M Helix risk-framed** (not a loss). **C2 closed as
not-needed** — E1/E2 reached the deliverable, so selection isn't hiding them.

**The near-term label refinement is DONE** (`ab90fa9`, recorded in `PROGRESS.md`): the
`ECONOMICS_PROMPT` BRIGHT LINE rule now labels computed overrun/leakage figures INFERRED, not
CONFIRMED (verified on E007 — the $12K Pinnacle overrun is now INFERRED). So the only remaining
item is **Decision Surfacing (below) — and it is discretionary.**

**Discretionary, NOT necessary:** TOP doesn't systematically flag cross-document contradictions
(C3 72%/68%, A2 Cho-approval, C1 date, C2 37%/30% — all real in source, verified). That is the
**Decision Surfacing** feature below. But it is **not a correctness issue**: the answer key
itself rates these conflicts non-load-bearing (§6.5) — the findings/recommendations don't change
— and the consultant catches such discrepancies in review. Its value is review-burden reduction
and client-facing polish, not correctness. Build only if those savings justify a designed
feature across real engagements; otherwise defer.

---

## Code-Quality Remediation — top 5 from the scoped audit (NEW, 2026-06-15)

A scoped code-quality audit (`TOP_AUDIT_PLAN.md` → findings in `TOP_audit_findings.md`) found **47 items
(0 Critical · 13 High · 26 Medium · 8 Low)**. The **top 5 fix-first systemic issues** are turned into a
test-gated remediation plan: **`TOP_AUDIT_REMEDIATION_PLAN.md`**. The remaining Medium/Low items stay in
`TOP_audit_findings.md` as a punch-list. Ordering is **fix-first** (systemic reach × threat to data
integrity / deliverable correctness), not strict severity.

| # | Remediation item | Severity | Note |
|---|------------------|----------|------|
| 1 | Close remaining silent-failure swallows | High | The proven defect class — broad `except → return default` in `claude.py` (3 sites), `document_processor`, `report_sections`, `qa_revision`, 2 frontend sites |
| 2 | Enforce skill quality rules in code, not prompts | High | computed≠CONFIRMED, attribution-to-source, positive-finding-no-pattern — currently SOFT/NONE. Continues the D-label work; cross-doc-conflict half stays in Decision Surfacing below |
| 4 | One Claude I/O policy: `MAX_INPUT_CHARS` + retries | High | No input-size guard anywhere; shared client runs `max_retries=0`. Pairs with #1 to make Claude calls fail loud + bounded |
| 5 | Finish Rule-5 centralization | Medium | `prompts.py` builds `_DOMAIN_LIST` dynamically then hardcodes domains ×5 + enums; same drift in report_sections, document_processor, 2 routers, RoadmapPanel |

> **Item 3 (delete dead `signal.py` `bulk_create`) — ✅ DONE 2026-06-15 (`4bb9438`), recorded in `PROGRESS.md`.**
> Numbers 1/2/4/5 kept as-is for traceability to `TOP_AUDIT_REMEDIATION_PLAN.md`.

**Suggested execution order** (by cost/isolation, see plan): ~~3~~ → 4 → 1 → 2 → 5. Each ships as its own
commit with its pre-registered test landing first; re-run the 148-test baseline after each. **Priority vs.
features below is the consultant's call** — these are correctness/maintainability hardening, distinct from
the feature track.

---

## Remaining features — build order

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| 1 | Decision Surfacing (forks as pre-reasoned decisions) | TBD | **Discretionary, NOT necessary.** E007 showed TOP doesn't flag cross-doc conflicts (C1/C2/C3/A2) — but they're non-load-bearing (answer key §6.5) and the consultant catches them in review. Value is review-burden/polish, not correctness. See below. |
| 2 | Editable Engagement Info | 1 | Nice-to-have; can slot anywhere |
| 3 | PowerPoint Export | 1 | Ships with audit checks |
| 4 | Standardize Economic Output | 1 | Priority driven by QA Stage data |
| 5 | Structured File Metadata Capture | 1 | Medium — convention works as workaround |
| 6 | Auto-Suggest Knowledge | 1 | Lowest — current manual flow works |

---

## Decision Surfacing — turn forks into pre-reasoned decisions (NEW)

**Problem:** TOP sometimes leaves a genuine judgment fork as a *silent field* the consultant
must discover by reading the weeds, instead of surfacing it as an explicit, pre-reasoned
decision. Example from E006: two findings both reference Helix risk — F001's $2.82M–$3.48M
concentration exposure and F002's $1.25M engagement-at-risk. The F002 finding text already
says "captured in the Helix concentration exposure … not separately additive," yet TOP still
presents $1.2M as a stand-alone Direct Exposure field, leaving the consultant to *notice* the
overlap and avoid a double-counted executive total. A good junior would surface it: "F002's
$1.2M overlaps F001 (the finding says so) — recommend not counting it separately; confirm?"

**Principle (consultant-stated):** TOP should do the weeds correctly and turn every real fork
into a pre-reasoned "this OR that, because X" decision — the consultant reviews flagged
judgment, never re-checks the arithmetic. The signals are already in the data: the agents
write "not separately additive," "cross-reference Finding N," and the C1/C2/C3 cross-document
conflicts.

**Design (to scope deliberately, built once on the committed base — not a reactive patch):**
- Detect overlap/conflict signals the agents already emit (additivity language,
  cross-references, the cross-document conflicts).
- Where a safe default exists, apply it and note it (e.g. exclude an overlapping figure from
  the executive sum, with a one-line rationale).
- Where genuine judgment is required, surface a compact decision card — "this or that,
  because X" plus a recommendation — instead of a silent field.
- Extend the narrator-auditor / QA guard family rather than inventing a parallel mechanism
  (the `check_revenue_at_risk_coherence` guard is the first instance of this shape).

**Why now / why not yet:** This is the right north star, but it is a designed feature. Scope
it as its own session after Checkpoint 5 closes.

---

### Editable Engagement Info
Need to be able to edit engagement information after initial entry — should not require
DB Browser to update firm name, stated problem, hypothesis, etc. Items such as stated problem,
hypothesis, etc. should show on the screen after the initial save. It can be in
a collapsed section like settings is so it doesn't take up a lot of the screen.

**Priority: Nice-to-have (downgraded 2026-05-30).** Consultant clarified that this
was originally framed as "before first paid client" but is in practice a workflow
convenience, not a hard requirement — DB Browser is acceptable as a mid-engagement
workaround. Slots anywhere in the build sequence.

---

### Auto-Suggest Knowledge Promotions
**Problem:** Knowledge promotions are the only panel that remains fully manual.
Every other panel (Signals, Patterns, Findings, Roadmap) follows the detect-review-load
pattern. Knowledge should too. Also, existing knowledge promotions have no Edit or Delete.

**Design — Suggest flow (mirrors Findings parse pattern):**
- "Suggest Knowledge" button in KnowledgePanel — show after Synthesizer is accepted
- Calls Claude with KNOWLEDGE_EXTRACTION_PROMPT
- Claude receives: full Synthesizer output + all accepted findings + engagement context
- Returns 3–5 reusable insights as reviewable cards — observations useful across future
  engagements, not specific to this one
- Each card is editable before saving (inline text edit on the card)
- Accept / Reject per card
- "Load Approved" saves accepted items via existing knowledge create endpoint
- On success: clear candidates, refresh knowledge list

**Design — Edit/Delete on existing promotions:**
- Edit button per row — inline edit form (same fields as the Add form)
- Delete button with confirmation prompt
- New endpoint needed: `DELETE /{engagement_id}/knowledge/{knowledge_id}`
- Check whether `PATCH /{engagement_id}/knowledge/{knowledge_id}` exists — add if not

**New prompt:** `KNOWLEDGE_EXTRACTION_PROMPT` in `api/services/claude.py`
**New endpoints:**
- `POST /{engagement_id}/knowledge/suggest`
- `DELETE /{engagement_id}/knowledge/{knowledge_id}`
- `PATCH /{engagement_id}/knowledge/{knowledge_id}` (if not already present)

**Commit message:** Knowledge panel — suggest-review-load + edit/delete on existing promotions

---
### PowerPoint Export
**Problem:** Every engagement requires a PowerPoint presentation to the client. Victor
currently builds this manually from the Word document — typically after the roadmap is
finalized and before the client meeting. This is significant manual work per engagement
and creates a risk that the deck and the Word doc drift apart if the roadmap is updated
after the presentation.

**Design:** Generate a starting-point PPTX from the same data that drives the Word report.
Use a PowerPoint template named presentation_template.pptx that resides in the assets folder,
which is the same folder where the Word template resides.
Victor tweaks it to presentation quality before the client meeting — same expectation as
the Word document. The goal is to eliminate the blank-slide starting point, not the
consultant's judgment.

**Suggested slide structure:**
1. Title slide
2. Agenda
3. Transformation Process Review
4. Situation and client hypothesis vs. diagnostic reality
5. Domain maturity scorecard
6. Key findings by domain (one slide per domain)
7. Economic stakes summary
8. Transformation roadmap — Stabilize phase
9. Transformation roadmap — Optimize phase
10. Transformation roadmap — Scale phase
11. Quick wins — immediate actions

**Implementation:**
- New function `generate_pptx(engagement_id)` in `api/services/report_generator.py`
- Uses python-pptx library — check if already in requirements.txt, add if not
- New endpoint `POST /{engagement_id}/report/generate-pptx` — saves file alongside the
  Word doc in reports_folder, returns `{"saved_to": "C:\\...\\OPD_Roadmap_E004.pptx"}`
- New button in ReportPanel.jsx — "Generate Presentation" alongside Generate Report
- Content pulled from same data as Word report — no new data sources needed

**Commit message:** PowerPoint export — generate starting-point presentation from roadmap data

---

### Standardize Economic Output Generation
For each economic formula type in the pattern library, define inputs, assumptions,
default values, acceptable ranges, and range logic (point estimate vs range).

**Example — Delivery Overrun Loss:**
```
Inputs: Overrun Hours (estimated or confirmed), Cost Rate (confirmed or estimated)
Assumptions: Overrun % range 10%–25% if not explicitly measured
Range Logic: Low = 10% scenario, High = 25% scenario
```

**Build after:** Economic Breakdown Chart structured fields work (Sessions A–C) — finding economic data must be clean and in structured fields before standardizing the formulas that produce it.

---

### Structured File Metadata Capture at Processing Time

**Problem:** The Engagement Overview section of the OPD report derives interview roles and
document types by parsing filenames using a naming convention. This is fragile — it depends
on the consultant following the convention precisely, fails silently when files are named
differently, and produces generic fallback labels when parsing fails. The short-term
workaround is a documented filename convention (see CLAUDE.md). The correct solution is
capturing role and document subtype as structured fields at the moment a file is processed.

**Design:**
When a consultant processes a file in the Signal Panel, add two optional fields to the
processing UI:

For interview files:
- "Interviewee Role" — free text or dropdown
  Examples: CEO, Director of Delivery, VP Sales, Finance Lead, Senior Consultant,
  Operations Lead
  Stored as: `interview_role TEXT` in ProcessedFiles

For document files:
- "Document Type" — dropdown
  Options: Financial Summary, Portfolio Report, SOW, Project Status Report,
  Client Feedback, Other (free text)
  Stored as: `document_subtype TEXT` in ProcessedFiles

**Database change:**
```sql
ALTER TABLE ProcessedFiles ADD COLUMN interview_role TEXT;
ALTER TABLE ProcessedFiles ADD COLUMN document_subtype TEXT;
```
Both columns are nullable — existing records are unaffected. The filename convention
parsing remains as a fallback when these fields are null.

**Frontend change:**
In `SignalPanel.jsx`, add the appropriate field to the file processing form based on
the selected `file_type`:
- If `file_type` is `"interview"`: show "Interviewee Role" text input (optional,
  placeholder: e.g. "CEO")
- If `file_type` is one of `financial`/`sow`/`status`/`document`: show "Document Type"
  dropdown (optional)

**Backend change:**
In `signals.py` router, accept `interview_role` and `document_subtype` as optional fields
in the process-files request and store them in ProcessedFiles.

**Narrator input change:**
In `generate_report_narrative()`, prefer the structured `interview_role` and
`document_subtype` fields from ProcessedFiles over the filename convention parsing
when they are populated. Fall back to filename parsing when they are null.

**Priority:** Medium — the filename convention is a working workaround. Build this after
the Report Narrator is fully validated and before the first paid client engagement.

**Commit scope:**
ProcessedFiles migration, `signals.py` router update, `SignalPanel.jsx` form addition,
`generate_report_narrative()` input assembly update

---

## Deferred slices (parent features built; these pieces intentionally not done)

- **Track 3 brief _restructure_** (reorder/cut/add page-1 blocks) — deferred to first real
  client pilot. Only the reversible *reframe* was built; restructuring needs client signal.
- **Pattern-level valence** — deferred (non-load-bearing; only buys per-pattern analytics).
- **Executive Brief "Competitive AI Capability Gap" block** renders as loose paragraphs
  between the problems heading and the 3-problem table instead of inside it. Discrete defect;
  fix independently of the reframe.
- **Executive `display_label` suggestion quality** — the strength's label was mis-suggested as
  "Hidden margin cost from overtime" for a $3.7M funding-capacity figure (figure/label
  mismatch, surfaced in the E006 v1 review). Improve the label suggestion, or leave it to the
  consultant edit. Candidate for folding into the Decision Surfacing work.

---

## Checkpoint 5 — Dry Run 5 (Post-Assembly QA Stage Validation)

**Goal:** End-to-end run with a new fictional client validating the Post-Assembly
QA Stage (QA-1 through QA-5) and the Narrator Output Auditor Session 1. Also
validates that all features shipped since Checkpoint 4 (Findings enhancements, Roadmap
enhancements, Domain Maturity Scoring, A1–A5 accuracy items, the value-case reframe, and
the economic-figure-classification fix) continue to work end-to-end.

**Pre-run setup:**
- New fictional client with 3–4 interview transcripts and 1–2 supporting documents
- Transcripts should use named fictional roles (CEO, Director of Delivery, etc.) so
  key quotes are attributable in the report
- Planted defects matched to QA Stage dimensions:
  - Coverage: a specific time-sensitive item in source (e.g., "decision needed
    this week") that the v1 roadmap should drop — validates QA-1 catches it
  - Coherence: a planted contradiction or mislabeled number across sections
    (analogous to the $186K mislabel from E004) — validates QA-2 catches it
  - Editorial: an internal signal code left in a finding card, or an undefined
    acronym in the Executive Briefing — validates QA-3 catches it
- Narrator-level defect for Session 1 Auditor (e.g., fabricated R-code or named
  individual in a risk row) — confirms Session 1 still functions

**Pass criteria — QA Stage (confidence and risk reduction framing):**
- QA tab appears in the engagement view after the Report Generator produces v1
- QA-1, QA-2, QA-3 each run, produce items with tier ratings, and support the
  tiered UI (Tier 1 collapsed-with-batch-confirm, Tier 2 expanded, Tier 3
  collapsed-with-opt-in)
- Each planted defect is caught at the correct tier (Tier 1 defects appear
  as Tier 1, not buried in Tier 3)
- Tier 1 precision: no false-Tier-1 items (every Tier 1 is a real error or
  required addition — overrides are rare exceptions, not routine)
- Consultant reaches a defined endpoint with documented decisions per item
  (no items remaining in "pending" state)
- QA-4 Revision produces v2 incorporating all accepted items without breaking
  structured data, economic figures, or the analytical voice
- v1 and v2 are both accessible; diff view shows the changes
- v2 is delivery-ready without requiring a paranoid blank-slate scan

**Pass criteria — Narrator Auditor Session 1 (carry-forward):**
- Audit panel appears in ReportPanel on v1 before QA Stage runs
- Planted narrator-level defect is caught and surfaced

**Pass criteria — Carry-forward (must still work):**
- Every finding has a plain English evidence summary (no P-codes) and 2–3 key quotes
- Every roadmap item has a capability statement
- Economic impact context appears under roadmap items and as phase-level narrative
- At least one roadmap item has dependencies set — prerequisites appear in report
- Quick wins section appears in Section 10.3 (if qualifying items exist)
- Domain maturity scorecard appears in Section 2 — "No data" shown for unexamined domains
- All Checkpoint 4 pass criteria still met

**Pass criteria — Value-case reframe + economic-figure fix (added 2026-06-12):**
- Deliverable leads with strengths and reads as a value case, not a deficiency audit
- "What to Preserve" section renders before the roadmap; strengths are not shown as
  exposures/drags in the economic table or chart
- The executive "Revenue at Risk" headline is the firm's largest exposure (no small
  mis-tagged figure captures the slot); `check_revenue_at_risk_coherence` passes
- Strength findings carry `funding_capacity` type, not an exposure/drag type

---

## Phase 3 Items

### Background Task Processing for Document Files
Current `process-files` endpoint runs synchronously — for long transcripts or many files
this could approach timeout limits. For Phase 2 dry runs, synchronous is acceptable.
**Phase 3 design:** Background task with job table, polling endpoint, and status tracking.
Workaround: split large transcripts into two files.

### PostgreSQL Migration
Only two changes needed when the time comes:
1. `BaseRepository._get_connection()` — swap `sqlite3` for `psycopg2`, update connection string
2. Parameter placeholders — `?` becomes `%s` throughout all SQL constants

Everything else — repositories, routers, services — is database-agnostic and unchanged.

### Agent Registry URL Cleanup
`GET /api/engagements/agents/registry` is registered under the engagements prefix but is
not engagement-specific. Cosmetic issue only.
**Phase 3 fix:** Move to `/api/agents/registry`. Update `api.js` and `AgentPanel.jsx`.

### Multi-user remote version
Multi-user remote version requires: 
auth/session management, engagement-level access controls, structured interview intake 
for non-consultant interviewers, finding source attribution for remote reviewers, 
PostgreSQL migration, hosted infrastructure. Prerequisite: solo version validated across 
minimum 3 engagements.

### AWS Hosting
- `_get_connection()` uses RDS connection string via `TOP_DB_PATH` env var
- File processing reads from S3 — `document_processor.py` gets S3 client
- `main.py` CORS origins updated to production domain
- Frontend built with `VITE_API_URL=https://top.tuntechllc.com/api`
No architectural changes required.

### Multi-User Auth
1. Add `users` table
2. Add `user_id` column to `Engagements` table
3. Add `WHERE user_id = ?` filter to all engagement queries
4. Add auth middleware (FastAPI + JWT or session)

### Custom Domain
`top.tuntechllc.com` — DNS record pointing to AWS load balancer.
No code changes — driven by `VITE_API_URL` build env var.

---

## Architectural Notes for Future Reference

- **Do not add SQLAlchemy** — clean SQL in repositories is the right pattern for this project.
  PostgreSQL migration only requires changing `_get_connection()` and `?` to `%s`.
- **Do not add global state** — all data must be scoped to `engagement_id`.
  Cross-engagement reporting queries across all engagements by design — that is intentional.
  Any new feature should be scoped to an engagement, not global.
- **Classify economic figures by nature, not domain** — `figure_type` (and the
  confirmed/derived/annual-drag suggestions) are read from the figure's economic nature
  (the agent's `economic_impact` text + valence), with the domain map only as a fallback.
  Do not reintroduce domain-only classification — it mis-routes the executive headline.
