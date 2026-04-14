# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---

## Technical Debt — Address Before Next Major Feature

### Build Sequence — Verified 2026-04-13

Full code investigation confirmed this order. Work top to bottom within this section.

| # | Item | Sessions |
|---|------|----------|
| 1 | Economic Structured Fields — Session C | 1 |
| 2 | Signal Library — Sessions 1–3 (includes DEFAULT_DOMAIN) | 3 |
| 3 | Editable Engagement Info | 1 |
| 4 | Domain Maturity Scoring | 1 |
| 5 | Visual 3 — Causal Chain | 1 |

DEFAULT_DOMAIN standalone session eliminated — see note on that item below.

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

**Implementation scope — one remaining session:**

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

**Sequencing note:** Session C modifies report_sections.py and must follow the split (already done).

---

### Signal Library — Implementation

**Priority: High — foundational to diagnostic quality across all future engagements**

**Problem:** TOP currently free-generates signal
names from transcripts with no predefined catalog.
Signals like "Presence of PMO function" or
"Revenue per Consultant" only appear if an
interviewee mentions them. Signal names are
inconsistent across engagements making
cross-engagement comparison meaningless.
Absence of a signal — which is itself diagnostic —
is never recorded.

**Reference document:** `Signals/TOP_Signal_Library.md`
in the repo. Contains 80 signals across
all 10 domains with full definitions, maturity
bands or threshold ranges, none_indicators,
and pattern linkage. This is the authoritative
content source for implementation.

**Schema surface (three changes):**

1. New SignalLibrary table — columns include
   signal_id, signal_name, domain, signal_type,
   definition, priority_tier (INTEGER DEFAULT 2),
   threshold_bands (JSON), maturity_levels (JSON),
   none_indicators, contributing_patterns,
   created_date. Seed from TOP_Signal_Library.md.
2. New SignalCoverage table — not-observed
   gaps only, no status column
3. ALTER TABLE OPDSignals ADD COLUMN
   library_signal_id TEXT (nullable FK
   to SignalLibrary)

Full DDL is in TOP_Signal_Library.md
Schema Reference section.

**Two signal types requiring different
extraction handling:**

Numeric signals — Claude reads an observed
value and maps it to a threshold band.
Report: observed value + band label + source.

Maturity signals — Claude reads qualitative
evidence and maps to None/Informal/Defined/
Managed/Optimized.
CRITICAL: Only assign None if none_indicators
are present. If topic not discussed, output
not_observed. Never infer None from silence.

**Extraction prompt changes:**

Document prompts: domain-filtered signal slice
only (see Domain Filter Map in library file).
Interview prompts: full library — interviewees
span all domains.

Output format: found signals in standard
candidate format + not_observed array of
signal_ids for SignalCoverage rows.

**Implementation scope — significant.
Do not attempt in one session:**

Session 1: SignalLibrary table + seeding
script from TOP_Signal_Library.md +
SignalCoverage table + library_signal_id
column on OPDSignals. Also add
DEFAULT_DOMAIN constant to domains.py
and constants.js; replace 7 hardcoded
fallback strings (see DEFAULT_DOMAIN item).

Session 2: Update extraction prompts with
domain-filtered library injection +
not_observed output format. Also fix
domain list injection — all 6 prompts in
document_processor.py have hardcoded domain
lists instead of injecting from VALID_DOMAINS.
Fix this here, not in a separate session.

Session 3: Router changes to write
SignalCoverage rows from not_observed
output + SignalPanel UI updates to show
coverage gaps.

**Build after:** Document Cleanup session
and Economic Impact Table structured
fields are complete.

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
### Executive Briefing Sharpness + Execution 
Path Section

**Problem:** Two related issues identified 
from external feedback:

1. The Executive Briefing reads like analysis 
   rather than landing like a punch. Sentences 
   are long and dense. Key insights are buried 
   inside paragraphs rather than standing alone. 
   A CEO reading this page in 5 minutes should 
   feel the weight of the problem immediately.

2. The document has no clear answer to 
   "then what?" — after reading the roadmap, 
   the client does not know how implementation 
   gets done or what role the consultant plays 
   going forward. This is a conversion gap, 
   not just a document gap.

**Fix 1 — Executive Briefing prose style**

Update REPORT_NARRATOR_PROMPT instruction 
for the executive_briefing opening paragraph:

"Write the opening paragraph in short 
declarative sentences. Each sentence is 
one idea. No sentence should exceed 20 words. 
Do not embed the key insight inside a clause — 
pull it out as its own sentence. The reader 
should feel the weight of the problem after 
three sentences, not after three paragraphs.

Wrong style:
'Northstar's margin problem is not a PM 
execution problem — it is a pricing and 
governance problem: gross margin has compressed 
from 40% to 31% over four years because the 
CEO retains unilateral authority over pricing, 
SOW execution, and change order acceptance 
with no governance gates, and that authority 
has been used in ways that lock in losses 
before delivery begins.'

Right style:
'Northstar's margin problem is not a PM 
execution problem. It is a pricing and 
governance problem. Gross margin has fallen 
from 40% to 31% in four years. The cause is 
not delivery failure — it is a decision 
structure that locks in losses before delivery 
begins.'"

This is a REPORT_NARRATOR_PROMPT change only.
No report_generator.py changes needed.

**Fix 2 — How This Gets Implemented section**

Add a new subsection to Section 11 
(What Happens Next) titled 
"How This Gets Implemented."

The Narrator generates this section from 
engagement data. It should produce three 
short paragraphs covering:

Path 1 — Internal Execution
If the firm has sufficient internal capacity 
and leadership bandwidth, the roadmap can 
be executed internally. The Priority Zero 
actions require leadership decisions only. 
The Stabilize phase requires process design 
and governance changes that internal leaders 
can own with clear accountability.

Path 2 — Guided Execution (recommended 
for most firms at this stage)
A structured advisory engagement where the 
consultant provides weekly or biweekly 
leadership alignment, roadmap sequencing, 
and accountability review. The client executes. 
The consultant ensures the work gets done 
correctly and in the right order. This is 
the recommended model for firms without 
a dedicated transformation function.

Path 3 — Partner-Supported Execution
For firms that lack both internal capacity 
and a structured advisory relationship, 
specific initiatives can be staffed through 
fractional resources — fractional PMO, 
contractor PMs, finance operations support. 
The consultant architects the solution and 
directs the resources.

The Narrator should select which path to 
recommend based on firm size and the 
capacity signals observed in the engagement 
data. Firms under 60 people with no dedicated 
operations function should default to 
recommending Path 2.

**Implementation:**
- New Narrator JSON field: 
  execution_path_recommendation — 
  one of "internal" | "guided" | "partner"
- New REPORT_NARRATOR_PROMPT instruction 
  to generate the execution path narrative
- New subsection in report_generator.py 
  within Section 11, rendered after the 
  existing What Happens Next content

**Trigger for recommendation logic 
in Narrator prompt:**
"Based on the firm's headcount, the 
presence or absence of a dedicated 
operations or transformation function, 
and the leadership bandwidth signals 
observed in this engagement, recommend 
one of three execution paths: internal, 
guided, or partner-supported. Most firms 
under 75 people without a dedicated 
transformation function should be 
recommended the guided execution path."

**Priority:** High — do before first 
paid client engagement. This directly 
addresses the conversion gap identified 
by an experienced IT consulting practitioner. 
The "then what?" question will be asked 
in every client meeting.

**Scope:**
- REPORT_NARRATOR_PROMPT — two changes 
  (executive briefing style, execution 
  path recommendation)
- report_generator.py — one new subsection 
  in Section 11
- No schema changes
- No frontend changes

**Do in a single focused session.**
**Commit message:** "Narrator — sharper 
Executive Briefing prose style + 
How This Gets Implemented section 
in What Happens Next"

---

### DEFAULT_DOMAIN Constant — Centralize Hardcoded Domain Fallback

**Do not build as a standalone session. Split across Signal Library Sessions 1 and 2:**
- **Session 1:** Add `DEFAULT_DOMAIN = 'Delivery Operations'` to `api/utils/domains.py` and
  `src/constants.js`. Replace the 7 hardcoded fallback strings in backend and frontend files.
- **Session 2:** Fix domain list injection in all extraction prompts — the domain lists in all
  6 prompts in `document_processor.py` are hardcoded literal strings, not injected from
  `VALID_DOMAINS`. Signal Library Session 2 rewrites all extraction prompts anyway — fix
  the injection at that point. Touching these prompts twice is wrong.

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
