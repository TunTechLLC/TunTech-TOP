# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

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

### Claude API timeout

Add `timeout` parameter to `AsyncAnthropic` client initialization in `api/services/claude.py`. Use 120 seconds base timeout. Currently a hung Anthropic API call hangs the request indefinitely with no feedback to the frontend.

**One line change.** Do in the next available session.

**Commit message:** Set 120s timeout on AsyncAnthropic client

---

### Schema migrations table

Create a `schema_migrations` table in TOP.db with columns `(version TEXT, applied_at TEXT)`. Backfill one row per existing migration with the date applied (approximate is fine). Add a rule to CLAUDE.md: every future `ALTER TABLE` must have a corresponding entry inserted into `schema_migrations`.

**Why:** Multiple `ALTER TABLE` migrations have been applied manually with no record of which have been applied to a given DB. Rebuilding or moving the DB currently requires reconstructing migration history from git.

**Do in the same session as Claude API timeout.**

**Commit message:** Add schema_migrations table — backfill existing migrations, document rule in CLAUDE.md

---

## After Checkpoint 4

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
| Visual 1 — Economic Breakdown Chart | Horizontal bar chart of confirmed exposures by finding, embedded in Section 6 before economic summary table. matplotlib (Agg backend), temp PNG deleted after embed. | ✅ Complete |
| Visual 2 — Roadmap Timeline | Gantt-style horizontal bar chart at start of Section 8. Phase zone shading, bars colored by phase, sourced from narrator initiative_details. | ✅ Complete |
| Visual 3 — Causal Chain Diagram | Left-to-right SVG flow showing how upstream failures produce downstream consequences. Nodes are finding titles, arrows show causal relationships from Root Cause Analysis. Embedded in Section 5. | Not built — pending |

**Build Visual 3 after:** `report_generator.py` split (see Technical Debt section below). Do not add another visual to the existing monolithic file.

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

**Build after:** Findings Enhancements — finding economic data must be clean first.

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

## Checkpoint 5 — Dry Run 5 (Full Feature Validation)

**Goal:** End-to-end run with a new fictional client validating all post-Checkpoint 4
features: key quotes, roadmap capabilities, economic linkage, dependency mapping, and
domain maturity scoring.

**Pre-run setup:**
- New fictional client with 3–4 interview transcripts and 1–2 supporting documents
- Transcripts should use named fictional roles (CEO, Director of Delivery, etc.) so
  key quotes are attributable in the report

**Pass criteria:**
- Every finding has an evidence summary (P-codes) and 2–3 key quotes in the report
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
