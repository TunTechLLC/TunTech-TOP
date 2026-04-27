# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---

## Accuracy and Human-in-the-Loop — Address Before First Real Client

These items address accuracy risk and reviewer effectiveness. They are higher priority than
all output quality and feature work below. Identified via architectural review 2026-04-24.

**All A-series items complete.** ✅

---

## Technical Debt — Address Before Next Major Feature

### Build Sequence — Verified 2026-04-15

Full code investigation confirmed this order. Work top to bottom within this section.

| # | Item | Sessions |
|---|------|----------|
| 1 | Domain Maturity Scoring | 1 |
| 5 | Visual 3 — Causal Chain | 1 |
| 6 | Three Systemic Drivers Section | 1 |
| 7 | Auto-Suggest Knowledge | 1 |
| 8 | Standardize Economic Output | 1 |
| 9 | Structured File Metadata Capture | 1 |
| 10 | Editable Engagement Info | 1 |
| 11 | PowerPoint Export | 1 |
| — | Checkpoint 5 — Dry Run 5 | milestone |

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
