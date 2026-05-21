# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---


## Technical Debt — Address Before Next Major Feature

### Build Sequence — Revised 2026-05-21

Revised after architectural review of roadmap/report review burden (4–8 hours per
engagement on the Word document, driven by lack of confidence rather than known errors).
The audit layer is now the top priority because it changes the build economics of every
future report feature — once it exists, new output ships with its own checks instead of
extending the review window. Work top to bottom within this section.

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| ✅ | Narrator Output Auditor — Session 1 (mechanical checks) | 1 | Shipped 2026-05-21 — see PROGRESS.md |
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

---



### Narrator Output Auditor

**Status:** Session 1 shipped 2026-05-21. Kill-switch decision pending — measure Word
doc review time on next engagement before building Session 2.

**Problem framing (preserved for context):** 4–8 hours of review time on the final
Word document per engagement, driven by lack of confidence rather than known errors.
Prompt-based enforcement (rules in REPORT_NARRATOR_PROMPT) hit diminishing returns;
adding a rule traded one violation for another. The auditor produces a structured
trust report so clean dimensions can be skipped — the test-suite framing.

**Session 1 — shipped.** Full details in PROGRESS.md. 12 mechanical Python checks
in `api/services/narrator_auditor.py`. Audit runs as part of `/report/generate` and
is surfaced as a Trust Report panel in ReportPanel.jsx.

**Audit-only endpoint — deferred from Session 1.** BACKLOG originally specified an
"Audit only" button that re-runs checks without regenerating the doc. This requires
caching the narrator JSON output (schema change — new `ReportNarratives` table, or
storing narrator output as an AgentRun row). Session 1 shipped without it: the audit
runs as part of `/report/generate` and the trust panel persists in localStorage for
re-display after navigation. If the kill-switch validates the framing, consider this
as a small follow-up before Session 2 — useful when consultants want to test injected
errors against the same narrator output or re-display the audit panel without paying
the 30–60s narrator regeneration cost.

---

**Kill-switch — measurement before Session 2**

After Session 1 ships, run the first engagement and measure Word doc review time.
- If review time drops meaningfully (e.g., 4–8 hours → 1–3 hours): framing
  validated. Proceed to Session 2.
- If review time does not drop: framing is wrong. Stop. Do not build Session 2.

This decision point is built into the sequence intentionally — the auditor is
recommended on strong-but-not-certain evidence and the kill-switch protects
against speculative investment in Session 2.

---

**Session 2 — narrow Claude checks (conditional on Session 1 results)**

Only build if Session 1 demonstrates measurable review-time compression. Targets
dimensions Python cannot check — cross-section coherence, evidence-finding
alignment, narrative tone. Each check is a focused Claude call with structured
output (pass/fail + evidence). Same trust-report surface as Session 1.

Specific Session 2 checks are to be determined by what remains in the manual
review after Session 1 — data-driven, not speculative.

Discipline rule: audit prompts only check specific named violations, structured
output, one rule = one check. New quality concern → new audit rule, never
broaden scope.

**Commit message (when built):** Narrator Output Auditor Session 2 — narrow
Claude checks for [specific dimensions identified from Session 1 measurement]

---

**Interaction with the rest of the backlog**

Once the auditor exists, every new report feature ships with its own audit checks.
This changes the build economics: adding output no longer adds review burden.
Applies to:
- PowerPoint Export — checks that slides match the Word doc data
- Visual 3 (Causal Chain) — checks that every node resolves to a real finding,
  no orphan arrows
- Standardize Economic Output — auditor data will reveal which formulas leak
  most often, driving prioritization
- Future report features

---

### Visual Generator Layer — Status

| Visual | Description | Status |
|--------|-------------|--------|
| Visual 3 — Causal Chain Diagram | Left-to-right SVG flow showing how upstream failures produce downstream consequences. Nodes are finding titles, arrows show causal relationships from Root Cause Analysis. Embedded in Section 5. | Not built — pending |

**Visual 3 design:**
- New `causal_chain` JSON field in narrator output — finding-to-finding relationships for diagram node construction
- Generated as a temporary SVG, embedded via python-docx add_picture(), then deleted
- If generation fails, report generates without the visual and logs a warning

**Commit message:** Visual 3 — causal chain diagram in Section 5

---

### Editable Engagement Info
Need to be able to edit engagement information after initial entry — should not require
DB Browser to update firm name, stated problem, hypothesis, etc. Items such as stated problem,
hypothesis, etc. should show on the screen after the initial save. It can be in
a collapsed section like settings is so it doesn't take up a lot of the screen.

**Priority: High — needed before first paid client engagement.** Engagement data will need correction mid-engagement (revised hypothesis, corrected firm name, etc.) and DB Browser is not a viable workaround in a live setting.

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

**Build after:** Domain Maturity Scoring — the scorecard slide requires maturity scores
to be computed. Build maturity scoring first, then PowerPoint.

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
### Three Systemic Drivers Section

**Problem:** The document presents findings across 
9 domains and 16 roadmap items but never explicitly 
names the 2-3 upstream structural conditions that 
most findings trace back to. A CEO reading the 
document absorbs detail but may not walk away with 
a crisp mental model of what is actually wrong at 
the structural level.

**Design:** A new section between Executive Summary 
and How to Read This Document. Half a page maximum. 
Each driver gets a bold 3-5 word name and one 
sentence explanation. No finding cross-references 
in this section — the domain analysis carries that 
detail.

**Implementation:**
- New Narrator JSON field: systemic_drivers array 
  with driver_name (3-5 words) and 
  driver_explanation (one sentence) per driver
- New REPORT_NARRATOR_PROMPT instruction: 
  "Identify 2-3 systemic drivers — the upstream 
  structural conditions that are the root cause 
  of the majority of findings. A driver is not 
  a finding; it is the condition that produces 
  multiple findings. Every accepted finding should 
  be traceable to at least one driver."
- New section in report_generator.py between 
  Executive Summary and How to Read This Document
- Section map already dynamic — section numbers 
  update automatically

**Priority:** Low — build after causal chain 
diagram. May be redundant once the causal chain 
diagram visually shows the same relationships.

**Build after:** Causal chain diagram is complete.
---

## Checkpoint 5 — Dry Run 5 (Audit Layer + Editable Engagement Info Validation)

**Goal:** End-to-end run with a new fictional client validating the Narrator Output
Auditor (Session 1, plus Session 2 if built) and Editable Engagement Info. Also
validates that all features shipped since Checkpoint 4 (Findings enhancements, Roadmap
enhancements, Domain Maturity Scoring, A1–A5 accuracy items) continue to work end-to-end.

**Pre-run setup:**
- New fictional client with 3–4 interview transcripts and 1–2 supporting documents
- Transcripts should use named fictional roles (CEO, Director of Delivery, etc.) so
  key quotes are attributable in the report
- A planted defect in the narrator output that the auditor should catch (e.g., a
  fabricated R-code or a named individual in a risk row) — validates auditor catches
  real violations
- Engagement metadata that requires mid-engagement correction (e.g., revised
  hypothesis after second interview) — validates Editable Engagement Info

**Pass criteria — Auditor:**
- Audit panel appears in ReportPanel before Word doc rendering
- Planted defect is caught and surfaced with evidence
- All other dimensions report clean
- Word doc review time on the dry run is measurably lower than prior dry runs
  (target: under 2 hours; baseline: 4–8 hours)

**Pass criteria — Editable Engagement Info:**
- Firm name, stated problem, hypothesis can be edited after initial save
- Edited fields appear correctly in the final report
- No DB Browser operations required during the engagement

**Pass criteria — Carry-forward (must still work):**
- Every finding has a plain English evidence summary (no P-codes) and 2–3 key quotes
- Every roadmap item has a capability statement
- Economic impact context appears under roadmap items and as phase-level narrative
- At least one roadmap item has dependencies set — prerequisites appear in report
- Quick wins section appears in Section 10.3 (if qualifying items exist)
- Domain maturity scorecard appears in Section 2 — "No data" shown for unexamined domains
- All Checkpoint 4 pass criteria still met

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
