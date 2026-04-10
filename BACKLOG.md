# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---

## Document Cleanup — Complete Before First Client Engagement

### Remove Pattern Codes from Client-Facing Evidence Summary

**Problem:** The evidence summary line rendered 
after each finding table in Section 6 currently 
shows internal pattern codes (e.g. "Supported by 
P38, P39, P41, P43 across Consulting Economics; 
5 signals (5 confirmed, 0 inferred)"). Clients 
have no context for what P38 means. The pattern 
codes are internal TOP metadata that should not 
appear in a client deliverable.

**Fix:** In report_generator.py, find where the 
evidence summary line is rendered after each 
finding table. Replace the pattern ID list with 
plain English while preserving the meaningful 
information:

Current format:
"Supported by P38, P39, P41, P43 across 
Consulting Economics; 5 signals 
(5 confirmed, 0 inferred)"

New format:
"Supported by 5 directly observed signals 
across Consulting Economics"

Or if mixed confidence:
"Supported by 5 signals across Consulting 
Economics (3 directly observed, 2 reported)"

Rules:
- Remove all pattern codes entirely
- Keep the signal count
- Keep the domain name
- Keep the confidence breakdown using 
  client-facing language:
  High → "directly observed"
  Medium → "reported"
  Hypothesis → "preliminary"
- If all signals are High confidence, 
  use the simplified format with 
  "directly observed signals" only

This is a report_generator.py change only. 
No prompt changes. No database changes.

**Priority:** High — group with Future State Table fixes as a single Document Cleanup session

### Future State Table — Two Fixes

**Priority: High — group with Remove 
Pattern Codes as a single Document 
Cleanup session. All fixes are 
report_generator.py or 
REPORT_NARRATOR_PROMPT only. 
No schema changes. No frontend changes.**

Fix 1 — Strip CONFIRMED/INFERRED labels 
from the Metric column
The Metric column currently shows values 
like "Gross Margin (CONFIRMED (current); 
INFERRED (target))". Strip all 
parenthetical evidentiary labels from 
the Metric column only before rendering. 
Current State, Benchmark, and Target 
columns are unaffected.
report_generator.py change only.

Fix 2 — NPS benchmark should use 
confirmed prior period baseline not 
estimated industry average
Update REPORT_NARRATOR_PROMPT instruction 
for the future_state table benchmark 
field: "For metrics where a prior period 
confirmed value exists in the engagement 
data, always use that as the benchmark 
rather than an estimated industry 
average. The prior period confirmed 
value is more credible and more 
motivating for the client than an 
industry estimate."

---

## Technical Debt — Address Before Next Major Feature

### Split report_generator.py into orchestrator and section renderers

**Priority: High — do before any further Visual Generator Layer work**

`report_generator.py` now handles cover page, executive briefing, all report sections (1–9), economic tables, three visual embeds, and structured display field logic. Two visuals are already embedded, a third is pending. The file is becoming a maintenance liability — Sessions 1–3 alone added ~130 lines to it.

**Split into:**
- `report_generator.py` — orchestrator only; manages document assembly, calls section renderers in order, owns `generate_report()`
- `report_sections.py` — individual section renderers; one function per section; all `_build_*`, `_economic_*`, `_key_findings_*`, `_risk_table`, `_dependency_table`, `_findings_by_domain`, visual embed functions

**Constraints:**
- No behavior changes — pure structural refactor
- All existing tests must pass before and after
- Do this before adding causal chain diagram or any other visual work

**Commit message:** Refactor — split report_generator.py into orchestrator and section renderers

---
### Economic Breakdown Chart — Use Structured 
Display Fields Instead of Text Parser

**Problem:** The economic breakdown chart in 
Section 8 still uses _parse_economic_figures() 
to extract bar values from finding economic_impact 
text. This produces the same false positives that 
were fixed in the Three Numbers block and totals 
row — confirmed by $9.2M appearing as the bar 
value for the Structural Margin Compression finding 
when the correct figure is $368K–$828K.

**Fix:** Update the chart generation function in 
report_generator.py to source bar values from 
display_figure and display_label where 
include_in_executive = 1, using the same 
_parse_display_figure_to_float() utility already 
implemented for the other three locations.

Only findings with display_figure set and 
include_in_executive = 1 should appear as bars. 
If no findings have these fields set, omit the 
chart entirely rather than falling back to 
text parsing.

**Priority:** High — do before first paid 
client engagement. The $9.2M false positive 
on the chart would be immediately visible 
and credibility-damaging in a client meeting.

Also fix the per-finding rows in the Economic 
Impact table. The parser is still producing 
false positives on confirmed exposure extraction 
for some findings (confirmed: $9.2M appearing 
for Structural Margin Compression finding).

Two options:
Option A — Extend the structured display fields 
approach to the table rows as well. Each finding's 
Confirmed Exposure, Derived Exposure, and Annual 
Drag columns are sourced from structured fields 
rather than parsed text.

Option B — Improve the parser false positive 
detection to catch cases where a revenue figure 
is referenced in a calculation context rather 
than as the finding's own exposure.

Option A is the correct long-term solution 
and is consistent with the architectural 
direction already established. Requires 
additional structured fields on OPDFindings 
for derived_figure and annual_drag_figure, 
following the same pattern as display_figure.

**Implementation scope — three sessions 
following Session 1-2-3 pattern:**

Session A — Schema and models:
- Add confirmed_figure REAL, 
  derived_figure REAL, and 
  annual_drag_figure REAL to OPDFindings
- All nullable — existing records 
  unaffected
- Update repository GET_ALL, INSERT, 
  UPDATE queries
- Update FindingCreate, FindingUpdate, 
  FindingResponse models
- Update findings router to accept 
  and store new fields

Session B — FindingsPanel UI and 
pre-population:
- Add confirmed_figure, derived_figure, 
  annual_drag_figure fields to the 
  Executive Display section in 
  FindingsPanel
- Same pre-population and suggestion 
  pattern as display_figure — parser 
  suggests, consultant reviews and 
  corrects before saving
- Same guardrail: if suggested figure 
  exceeds confirmed_revenue, show 
  red ⚠ warning
- Same lazy pre-population: only runs 
  when fields are null and finding 
  card is opened

Session C — Report generator:
- Update per-finding Economic Impact 
  table rows to source Confirmed 
  Exposure, Derived Exposure, and 
  Annual Drag columns from structured 
  fields instead of parser
- Update economic breakdown chart to 
  source bar values from display_figure 
  where include_in_executive = 1, 
  using _parse_display_figure_to_float() 
  already implemented
- If no findings have 
  include_in_executive = 1 with 
  display_figure set, omit chart 
  rather than falling back to 
  text parsing
- Placeholder behavior: if structured 
  fields not set, show "[Set in 
  FindingsPanel before delivery]" 
  in orange italic

Do not attempt all three sessions in 
one prompt. Each session is 
independently testable and committable.

**Sequencing note:** Sessions A and B do not touch report_generator.py and may be built before the report_generator.py split. Session C modifies report_generator.py and must follow the split.

---

### Claude API timeout

Add `timeout` parameter to `AsyncAnthropic` client initialization in `api/services/claude.py`. Use 120 seconds base timeout. Currently a hung Anthropic API call hangs the request indefinitely with no feedback to the frontend.

**One line change. Do this in the next available session regardless of other queue position — a hung call during a client engagement has no recovery path.**

**Commit message:** Set 120s timeout on AsyncAnthropic client

---

### Schema migrations table

Create a `schema_migrations` table in TOP.db with columns `(version TEXT, applied_at TEXT)`. Backfill one row per existing migration with the date applied (approximate is fine). Add a rule to CLAUDE.md: every future `ALTER TABLE` must have a corresponding entry inserted into `schema_migrations`.

**Why:** Multiple `ALTER TABLE` migrations have been applied manually with no record of which have been applied to a given DB. Rebuilding or moving the DB currently requires reconstructing migration history from git.

**Do in the same session as Claude API timeout.**

**Commit message:** Add schema_migrations table — backfill existing migrations, document rule in CLAUDE.md

---

### Domain Maturity Scoring
**Problem:** Section 3 (Operational Maturity Overview) shows signal counts by domain but
no maturity score. Clients respond to scorecards in a way they don't respond to tables.

**Design:**
- Compute a 1–5 maturity score per domain at report generation time from existing data:
  - Pattern count (more patterns = more problems = lower score)
  - Average pattern confidence (High-confidence patterns weight more heavily)
  - Finding severity (High-priority findings pull score down)
- Domains with zero signals AND zero patterns show "No data" — a score of 5 would be
  misleading since it could mean genuinely healthy or simply unexamined
- Show as a scorecard table in Section 3 alongside the existing signal count table
- No new database columns — computed entirely at report time
- Future value: as TOP accumulates data across engagements, scoring becomes benchmarked

**Scoring formula (starting point — refine after first use):**
- Base score: 5
- Subtract 0.5 per accepted High-confidence pattern in the domain
- Subtract 0.25 per accepted Medium-confidence pattern
- Subtract 0.5 per High-priority finding in the domain
- Floor at 1; show "No data" if zero signals and zero patterns

**File:** `api/services/report_generator.py` — add `_compute_domain_scores(engagement_id)`

**Commit message:** Domain maturity scoring — 1–5 score per domain in Section 3

---

### DEFAULT_DOMAIN Constant — Centralize Hardcoded Domain Fallback

**Problem:** The string `'Delivery Operations'` is hardcoded as a fallback default in 3 backend
files and 4 frontend components. If the default ever changes it must be updated in 7 places.

**Backend — add to `api/utils/domains.py`:**
```python
DEFAULT_DOMAIN = 'Delivery Operations'
```
Replace hardcoded strings in:
- `api/services/document_processor.py` — invalid domain fallback in `process_file()`
- `api/routers/findings.py` — invalid domain fallback in parse-synthesizer
- `api/routers/roadmap.py` — invalid domain fallback in parse-synthesizer

**Frontend — add to `src/constants.js`:**
```javascript
export const DEFAULT_DOMAIN = 'Delivery Operations'
```
Replace hardcoded strings in:
- `SignalPanel.jsx` — `EMPTY_FORM` default + inline candidate card fallback
- `FindingsPanel.jsx` — `EMPTY_FORM` default + inline candidate card fallback
- `RoadmapPanel.jsx` — `EMPTY_FORM` default + two inline candidate card fallbacks

**Also flag:** Domain lists are hardcoded in all extraction prompts in `document_processor.py`
and `claude.py` instead of being injected from `VALID_DOMAINS`. This is the same violation
at a larger scale — domain added to `domains.py` without updating prompt strings would be
silently ignored by Claude. Consider dynamic prompt injection in the same session.

**Commit message:** Centralize DEFAULT_DOMAIN constant — remove hardcoded domain fallbacks

---

### Visual Generator Layer — Status

| Visual | Description | Status |
|--------|-------------|--------|
| Visual 1 — Economic Breakdown Chart | Horizontal bar chart of confirmed exposures by finding, embedded in Section 6 before economic summary table. matplotlib (Agg backend), temp PNG deleted after embed. | ✅ Complete — pending fix to use structured display fields (see Economic Breakdown Chart backlog item) |
| Visual 2 — Roadmap Timeline | Gantt-style horizontal bar chart at start of Section 8. Phase zone shading, bars colored by phase, sourced from narrator initiative_details. | ✅ Complete |
| Visual 3 — Causal Chain Diagram | Left-to-right SVG flow showing how upstream failures produce downstream consequences. Nodes are finding titles, arrows show causal relationships from Root Cause Analysis. Embedded in Section 5. | Not built — pending |

**Build Visual 3 after:** `report_generator.py` split (see Technical Debt section above). Do not add another visual to the existing monolithic file.

**Visual 3 design:**
- New `causal_chain` JSON field in narrator output — finding-to-finding relationships for diagram node construction
- Generated as a temporary SVG, embedded via python-docx add_picture(), then deleted
- If generation fails, report generates without the visual and logs a warning

**Commit message:** Visual 3 — causal chain diagram in Section 5

---

### Quick Wins Section in the Report
**Problem:** The report surfaces all roadmap items in three phase tables but does not
call out which items the client can act on immediately. Executives leave the presentation
wanting something concrete to do next week — the report should give them that explicitly.

**Note:** Section Priority Zero Actions and Section Immediate Next Steps now
address the most urgent items from the Synthesizer output. Quick Wins as defined here —
a filtered table of priority=High AND effort=Low roadmap items — is still distinct and
worth adding, but is lower priority than before given the new sections.

**Design:** Add a "Quick Wins" subsection in Section 8 between the Roadmap Overview (8.2)
and the phase tables (8.3). Filter roadmap items where priority=High AND effort=Low.
Display as a short highlighted table — title, domain, and one-line description. Cap at 5 items.

If no items meet the criteria, omit the section entirely — do not show an empty table.

**Implementation:** Pure report generation logic in `api/services/report_generator.py`.
No schema changes. No frontend changes. No new endpoints.

**Commit message:** Quick wins section in report — high priority, low effort roadmap items

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

## Checkpoint 5 — Dry Run 5 (Full Feature Validation)

**Goal:** End-to-end run with a new fictional client validating all post-Checkpoint 4
features: key quotes, roadmap capabilities, economic linkage, dependency mapping, and
domain maturity scoring.

**Pre-run setup:**
- New fictional client with 3–4 interview transcripts and 1–2 supporting documents
- Transcripts should use named fictional roles (CEO, Director of Delivery, etc.) so
  key quotes are attributable in the report

**Pass criteria:**
- Every finding has a plain English evidence summary (no P-codes) and 2–3 key quotes in the report
- Every roadmap item has a capability statement in the report
- Economic impact context appears under roadmap items and as a phase-level narrative
- At least one roadmap item has dependencies set — prerequisites appear in report
- Quick wins section appears in Section 8 (if qualifying items exist)
- Domain maturity scorecard appears in Section 3 — "No data" shown for unexamined domains
- PowerPoint generated without errors — opens correctly with all slides populated
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
