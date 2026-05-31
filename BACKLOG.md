# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---


## Technical Debt — Address Before Next Major Feature

### Build Sequence — current

QA-1, QA-2, QA-3 shipped 2026-05-30; QA-4 shipped 2026-05-31 (in-place
edit-list architecture, Opus 4.7, reconciliation — see PROGRESS.md). QA-5 is
the next work, followed by Checkpoint 5. Work top to bottom.

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| 1 | QA-5 QA Tab UI | 1 | Integrated tab; runs QA-1/2/3 + revision; v1↔v2 diff view |
| — | Checkpoint 5 — Dry Run 5 | milestone | Validates QA Stage end-to-end |
| 2 | Editable Engagement Info | 1 | Nice-to-have; can slot anywhere |
| 3 | PowerPoint Export | 1 | Ships with audit checks |
| 4 | Standardize Economic Output | 1 | Priority driven by QA Stage data |
| 5 | Structured File Metadata Capture | 1 | Medium — convention works as workaround |
| 6 | Auto-Suggest Knowledge | 1 | Lowest — current manual flow works |

---

## Post-Assembly QA Stage — remaining work

QA-1 (Coverage), QA-2 (Coherence), QA-3 (Editorial split) shipped 2026-05-30,
and QA-4 (Revision) shipped 2026-05-31 — see PROGRESS.md for full implementation
details. **QA-5 is the only remaining QA item.** Decisions locked during the
QA-1/2/3 build that apply forward:

- **Model parameter pattern** — Claude calls in QA-N functions pass
  `model="claude-opus-4-7"` explicitly via the per-call parameter on
  `api/services/claude.py` rather than changing global `TOP_MODEL`. Keeps
  the rest of TOP on Sonnet while QA agents target the proven detection
  model. QA-4 followed this pattern (Opus 4.7); QA-5 is frontend-only.
- **Streaming required** — `async_client.messages.stream()` for any
  long Claude call. Non-streaming requests get cut server-side on long
  generations (QA-1 first attempt timed out at 5 minutes).
- **Tiering and Tier 1 UI** — established in QA-1/2/3 and inherited by
  the QA-5 integrated tab.

Cowork QA prompt artifacts at `C:\001-cowork-projects\Northstar-working`
remain available as regression-test reference data.

### QA-5: Frontend — QA Tab

**Problem:** The three QA agents and the revision
agent need a UI surface in the existing React
frontend.

**What to build:** A new tab in the engagement
view (after the existing report/roadmap tab) that
presents the QA workflow.

**Layout:**
- Top section: status indicator showing whether
  the Report Generator has produced a first-pass
  roadmap document. If not, display a message:
  "Generate the roadmap first." The QA tab cannot
  run until a first-pass document exists.
- Three collapsible sections: Coverage, Coherence,
  Editorial
- Each section shows agent status (not run / running /
  complete) and item count (total / accepted /
  rejected)
- Each section expands to show items in a table with
  Accept/Reject controls matching existing agent
  runner pattern
- Sections should be runnable in order: Coverage
  first, then Coherence (which uses accepted
  Coverage items as context), then Editorial (which
  runs independently but is sequenced last for
  workflow clarity)
- A "Run Final Revision" button at the bottom that
  becomes active only after at least one QA agent
  has been run and items reviewed
- The revised roadmap document displays below the
  button after the revision agent completes
- Both the first-pass and revised documents should
  be accessible (e.g. "View Original" / "View
  Revised" toggle or tabs)

**Architecture:**
- All frontend API calls through api.js
- Follow existing agent runner component patterns
- New API endpoints in the existing router pattern
  for each QA table's CRUD operations and agent
  run triggers
- Revision agent trigger endpoint separate from
  QA agent triggers


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

## Checkpoint 5 — Dry Run 5 (Post-Assembly QA Stage Validation)

**Goal:** End-to-end run with a new fictional client validating the Post-Assembly
QA Stage (QA-1 through QA-5) and the Narrator Output Auditor Session 1. Also
validates that all features shipped since Checkpoint 4 (Findings enhancements, Roadmap
enhancements, Domain Maturity Scoring, A1–A5 accuracy items) continue to work end-to-end.

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
