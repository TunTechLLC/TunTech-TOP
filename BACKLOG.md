# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---

## Before Checkpoint 4

*All items complete. Ready for Checkpoint 4.*

---

## After Checkpoint 4

### Updates to Report output
Executive Briefing — One-Page CEO Section (Section 1 of Report) — ✅ Complete
Problem: The Executive Summary is 4-5 paragraphs of dense prose. CEOs need a faster entry point — one page with the critical findings, numbers, and actions before the full narrative begins.
Design: A new Section 1 inserted before the current Executive Summary. One page maximum. Part of the existing report generation flow — no separate document, no new button, no new endpoint. All current sections shift down by one.
Structure:

One sentence: the single most important finding
Three Key Problems: finding title + one impact sentence each
Three Key Numbers: confirmed figures only, with plain-language labels
Three Actions: top three Priority Zero items as direct imperatives

Implementation:

New executive_briefing JSON field in the Narrator response with sub-fields for the one-sentence finding, problems array, numbers array, and actions array
New Section 1 assembled by report_generator.py before the Executive Summary
Page break after Section 1 so it always occupies its own page
Three Key Numbers must be CONFIRMED figures only — no INFERRED
Three Actions must come directly from Priority Zero items in the Synthesizer output
Three Key Problems must map to actual finding titles — not paraphrased

Build after: Report Narrator is fully validated and main report structure is stable.

Consultant Voice Compression — ✅ Complete
Applied to Executive Summary (4 prose strings) and Section 9 completion_criteria.
Parallel asyncio.gather calls; falls back to original on any failure.

Visual Generator Layer — Embedded Diagnostic Visuals
Problem: The report is entirely text and tables. Three specific visuals would significantly increase perceived value and make the diagnostic feel like a system rather than a document.
Three visuals (build in this order):

Economic Breakdown Chart — horizontal bar chart of confirmed exposure by finding. Embedded in Section 6. Generated with matplotlib. ✅ Complete
Roadmap Timeline — Gantt-style timeline showing Stabilize/Optimize/Scale phases with initiative names. Embedded at start of Section 8. Generated with matplotlib. ✅ Complete
Causal Chain Diagram — left-to-right flow showing how upstream failures produce downstream consequences. Nodes are finding titles, arrows show causal relationships from Root Cause Analysis. Embedded in Section 5. Generated as SVG.

Implementation: Each visual generated as a temporary PNG/SVG, embedded via python-docx add_picture(), then deleted. If generation fails, report generates without the visual and logs a warning.
Narrator addition required for Visual 3: New causal_chain JSON field listing finding-to-finding relationships for diagram node construction.
Build after: Consultant Voice Compression is validated.

Reader Guide Dynamic Section Numbers — ✅ Complete
_SECTION_MAP dict in report_generator.py; _ROLE_READING_GUIDE uses format placeholders resolved at render time. One place to update when section numbering shifts.

---

### Accuracy Guardrail Pass — ✅ Complete
Five fixes in one commit: narrator section refs dynamic (Option B), example names generic,
opd_section mapping corrected, bulk_create() sequential loop, stale comment fixed.

---

### Consultant Correction on Agent Outputs — ✅ Complete
Schema, backend, and frontend complete. See PROGRESS.md for details.

---

### Consultant Correction on Agent Outputs (archived spec)
**Problem:** There is no way to correct a specific claim in an agent's output before it
gets passed to subsequent agents. The only options are rerun (may not improve the specific
issue) or accept a flawed output and rely on the Skeptic to catch it. Neither is reliable
when one section of an otherwise good output is wrong.

**Design:** Add a `consultant_correction TEXT` field to AgentRuns. Surfaced in AgentPanel
as a collapsible text area on each accepted agent run — labeled clearly as "Consultant
Correction." When present, it is appended to that agent's output when assembled as a prior
agent input in `call_claude()`, formatted as:

```
CONSULTANT CORRECTION (added after review):
[correction text]
```

This keeps the original Claude output intact and visible, adds the correction clearly
labeled, and ensures downstream agents see both. The consultant only fills this in when
needed — it is optional and hidden by default.

**Schema change:** Add `consultant_correction TEXT` to AgentRuns.
**Backend:** `call_claude()` in `api/services/claude.py` — append correction to prior
output if present. `AgentRunRepository` — update GET and PATCH to include the field.
**Frontend:** `AgentPanel.jsx` — collapsible correction field on accepted run cards.

**Commit message:** Agent output correction — optional consultant correction field per agent run

---

### Pattern Name on Candidate Review Cards — ✅ Complete
Backend enriches detect response with pattern_name (consolidated duplicate get_library() call).
Frontend displays name on candidate card between ID and confidence badge.

---

---

### Remove Phase 1 CLI Layer
The original CLI tool (`top.py` + supporting modules) is fully superseded by the web UI
and is dead code. None of these are imported by the FastAPI app.

**Files to delete:**
- `top.py` — CLI entry point
- `commands/` — entire directory (8 modules: case_packet, patterns, agents, engagement, findings, roadmap, reporting, __init__)
- `db/` — root-level CLI database layer (`db/connection.py`, `db/__init__.py`) — separate from and not used by `api/db/`
- `utils/` — root-level utility package (`utils/__init__.py`, `utils/clipboard.py`) — separate from and not used by `api/utils/`

**Ad-hoc scripts to delete** (used during development, never cleaned up):
- `check_views.py`
- `test_narrator.py`
- `test_roadmap_extractor.py`
- `validate_template.py`
- `scripts/test_report_structure.py`

**Do NOT delete:** `api/services/case_packet.py` — this is the live `CasePacketService`
used by `api/routers/agents.py` and `api/routers/patterns.py`.

**Verification before deleting:** grep for any import of `from commands`, `from db.connection`,
`from utils.clipboard`, or `import top` in the `api/` directory to confirm no cross-references exist.

**Commit message:** Remove Phase 1 CLI layer — superseded by web UI

---

### Quick Wins Section in the Report
**Problem:** The report surfaces all roadmap items in three phase tables but does not
call out which items the client can act on immediately. Executives leave the presentation
wanting something concrete to do next week — the report should give them that explicitly.

**Note:** Section 8.1 (Priority Zero Actions) and Section 9 (Immediate Next Steps) now
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
DB Browser to update firm name, stated problem, hypothesis, etc.  Items such as stated problem, 
hypothesis, etc. should show on the screen after the intial save.  It can be in 
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

### Findings Enhancements — Pattern Enforcement, Evidence Summary, Key Quotes, and Confidence
Build all in one session. All modify FINDINGS_EXTRACTION_PROMPT, OPDFindings schema, and
FindingsPanel. Separating them means touching the same files multiple times.

**Note on finding confidence:** The `confidence` field on findings currently defaults to High
for all findings — same self-assessment problem as signals. The fix belongs here rather than
as a standalone change because confidence should be derived from supporting pattern confidence
levels, which requires the pattern enforcement work (Part 1) to be in place first.
Fix: include pattern confidence levels in the accepted patterns list sent to
`extract_findings_from_synthesizer()`, then add a derivation rule — High if all supporting
patterns are High, Medium if mixed or all Medium, Low if any supporting pattern is Hypothesis.

**Part 1 — Enforce Pattern-to-Finding Mapping:**
Every finding must reference at least one pattern (EP ID). Currently optional.
- Add validation in `api/routers/findings.py`: if `contributing_ep_ids` is empty, return 422
- Add client-side guard in FindingsPanel.jsx: disable Load Approved if any approved
  candidate has zero contributing patterns selected
- Parse Findings cards already show the checklist — this makes selection mandatory

**Part 2 — Evidence Summary:**
Each finding gets a 1–2 line evidence summary derived from its contributing patterns:
```
Supported by P06, P08, P10 across Sales-to-Delivery Transition;
6 signals (2 confirmed, 4 inferred)
```
- Computed at finding creation time from contributing pattern and signal count data
- Stored on the finding record (new `evidence_summary TEXT` column on OPDFindings)
- Displayed in FindingsPanel and in the report under each finding

**Part 3 — Key Quotes (Signal Attribution):**
Surface 2–3 direct verbatim quotes per finding in the Domain Analysis section of the report.
Transforms the deliverable from "consultant tells you what's wrong" to "your own people told
us what's wrong."

- Signal scope: fetch signals in the same domain as the finding. Each signal's `notes` field
  already contains a verbatim quote from the source transcript, captured at extraction time
  (format: "Quote: '[exact words]' — Interpretation: [note]"). No raw transcripts needed.
- During Parse Findings, Claude receives the domain-scoped signal notes alongside the
  Synthesizer output, and selects the 2–3 most compelling quotes per finding.
- Store as `key_quotes TEXT` (JSON array of strings) on the finding record.
- Surfaced in the report's Domain Analysis section after each finding's narrative paragraph.
- Displayed on the finding candidate card for review before loading.

**Schema changes (one migration, run together):**
- Add `evidence_summary TEXT` to OPDFindings
- Add `key_quotes TEXT` to OPDFindings

**Commit message:** Findings enhancements — pattern enforcement, evidence summary, key quotes

---

### Economic Impact Column in Phase Tables
**Context:** The phase tables (Sections 8.3/8.4/8.5) were designed with an Economic Impact
column, but it was removed before Checkpoint 4 because the roadmap-to-finding linkage
(`addressing_finding_ids`) is not yet built. The column currently doesn't exist in the report.

**Decision point after Checkpoint 4:** If the absence of economic impact in the phase tables
is noticed or missed during the dry run or client review, add it back as part of Roadmap
Enhancements (Part 2 — Economic Linkage). If nobody misses it, it may not be worth building.

**If adding back:** The `addressing_finding_ids` field in Roadmap Enhancements (below) is the
correct mechanism. When that feature is built, restore the Economic Impact column in
`_roadmap_phase_table` and populate it from the linked findings.

---

### Roadmap Enhancements — Capability, Economic Linkage, and Dependencies
Build all three in one session. All three modify ROADMAP_EXTRACTION_PROMPT, RoadmapItems
schema, and RoadmapPanel. **Build after Findings Enhancements** — economic linkage requires
findings to exist and be clean before roadmap items can reference them.

**Prerequisite note:** addressing_finding_ids is populated by Claude at parse time using
the findings already in the database. If Parse Roadmap is run before Parse Findings,
addressing_finding_ids will be empty and economic display will be omitted gracefully.
For best results, parse findings before parsing the roadmap.

**Part 1 — Capability Statement:**
Each roadmap item describes what the organization will be able to do once the item is done.

Methodology: A capability → one or more deliverables → one or more requirements.
The roadmap captures the capability. Deliverables and requirements are defined in the
implementation engagement — that is a separate scope of work.

Example:
- Item: "Implement project intake process"
- Capability: "The ability to consistently scope, price, and initiate client engagements
  before delivery begins, such that every project enters delivery with a signed SOW,
  defined scope, and agreed success criteria."

- Add `capability TEXT` column to RoadmapItems
- Generated by Claude at Synthesizer-to-Roadmap parse time as a structured output field
- Editable on the candidate review card before loading
- Displayed in RoadmapPanel under each item and in the report labeled "Capability:"

**Part 2 — Economic Linkage:**
Each roadmap item identifies which findings it addresses. This makes per-item ROI visible
and enables phase-level economic context.

- Add `addressing_finding_ids TEXT` (JSON array of finding IDs) to RoadmapItems
- Populated by Claude at parse time — Claude receives the existing findings list and
  identifies which findings each roadmap item addresses
- At report time: display the economic_impact text from linked findings under each item
- Phase-level summary: Claude generates a 1–2 sentence narrative synthesis of the economic
  stakes for each phase, based on the economic_impact text from all findings linked to items
  in that phase. This is a narrative synthesis, not an arithmetic sum — economic_impact is
  free text (e.g. "$200K–400K INFERRED") and cannot be summed reliably.
- Maintain CONFIRMED/INFERRED notation throughout

**Part 3 — Dependency Mapping:**
Answers "why this order?" and "what breaks if we skip ahead?" — the two questions every
client asks when reviewing a roadmap.

- Add `depends_on TEXT` (JSON array of RoadmapItem IDs) to RoadmapItems — not a single FK.
  Items commonly have multiple prerequisites.
- In RoadmapPanel, add a "Depends on" multi-select to the add/edit form
- In the report, surface dependencies in two places:
  1. Section 8 opening paragraph — sequencing rationale explaining why the phases are
     ordered as they are and which items are load-bearing for others ("why this order?")
  2. Under each dependent item in the phase tables — "Prerequisites: [item A], [item B]"
     ("what breaks if you skip ahead?")
- No circular dependency validation needed — single-user tool, trust the consultant

**Schema changes (one migration, run together):**
- Add `capability TEXT` to RoadmapItems
- Add `addressing_finding_ids TEXT` to RoadmapItems
- Add `depends_on TEXT` to RoadmapItems

**Confirm:** `PATCH /{engagement_id}/roadmap/{item_id}` already exists — verify it handles
all new fields, add if not.

**Commit message:** Roadmap enhancements — capability, economic linkage, dependencies

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
3. Situation and client hypothesis vs. diagnostic reality
4. Domain maturity scorecard
5. Key findings by domain (one slide per domain)
6. Economic stakes summary
7. Transformation roadmap — Stabilize phase
8. Transformation roadmap — Optimize phase
9. Transformation roadmap — Scale phase
10. Quick wins — immediate actions

**Implementation:**
- New function `generate_pptx(engagement_id)` in `api/services/report_generator.py`
- Uses python-pptx library — check if already in requirements.txt, add if not
- New endpoint `POST /{engagement_id}/report/generate-pptx` — saves file alongside the
  Word doc in reports_folder, returns `{"saved_to": "C:\\...\\OPD_Roadmap_E004.pptx"}`
- New button in ReportPanel.jsx — "Generate Presentation" alongside Generate Report
- Content pulled from same data as Word report — no new data sources needed

**Build after:** Roadmap Enhancements (capability, economic linkage, dependencies) —
the slides should include capability statements and economic context per roadmap item.
Content quality features should be in place before the presentation layer is built.

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
