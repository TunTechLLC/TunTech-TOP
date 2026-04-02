# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---

## Before Checkpoint 4

### Economic Impact Reasoning — Make Figures CFO-Defensible
**Problem:** Economic impact figures currently show a conclusion and a label (CONFIRMED or
INFERRED) but not the reasoning. A CFO can challenge any number that isn't self-explanatory.
The goal is that the figure carries enough context that the CFO can follow the logic and
argue with the assumptions — not just reject the conclusion.

**Design:** The reasoning belongs on the finding, not the roadmap. The finding's
`economic_impact` field should carry the calculation, not just the result.

Example of what's needed:
- Current: "$280K/year overrun cost (INFERRED)"
- Target: "$280K/year overrun cost (INFERRED: 14 active projects × 30% average overrun
  rate × $67K average project value — overrun rate estimated from CEO interview; project
  value from pipeline document)"

**Changes needed:**
- Update `FINDINGS_EXTRACTION_PROMPT` in `api/services/claude.py` to require Claude to
  show its reasoning inline in the `economic_impact` field — calculation method, inputs
  used, and source of each input (interview, document, or industry benchmark)
- Update report sections that surface economic_impact to handle the longer format
- No schema changes — `economic_impact` is already free text

**Note:** This interacts with "Standardize Economic Output Generation" (After Checkpoint 4).
That item defines the formulas. This item ensures the reasoning is visible in the output.
Both are needed — this one first since it improves what we already generate.

**Commit message:** Economic impact reasoning — show calculation inline in findings

---

### Improve PATTERN_DETECTION_PROMPT for New Domain Coverage
**Problem:** On large signal sets, Claude anchors on numerically dominant domains
(Sales-to-Delivery, Delivery Operations) and under-detects sparse new domains
(AI Readiness, Human Resources, Finance and Commercial).

**Fix:** Add few-shot examples to PATTERN_DETECTION_PROMPT showing correct detection of
AI Readiness, Human Resources, and Finance and Commercial patterns. Add an explicit
instruction: "Ensure coverage across all domains represented in the signals — do not
omit a domain simply because it has fewer signals than others."

**File:** `api/services/claude.py` — PATTERN_DETECTION_PROMPT

**Test:** Run on E003 (102 signals including AI Readiness signals). Verify AI Readiness
patterns are detected on the first run.

**Commit message:** Improve PATTERN_DETECTION_PROMPT — few-shot examples and domain coverage

---

### Quick Wins Section in the Report
**Problem:** The report surfaces all roadmap items in three phase tables but does not
call out which items the client can act on immediately. Executives leave the presentation
wanting something concrete to do next week — the report should give them that explicitly.

**Design:** Add a "Quick Wins" section in the report immediately before the phase tables
in Section 8. Filter roadmap items where priority=High AND effort=Low. Display as a
short highlighted table — title, domain, and one-line description. Cap at 5 items.

If no items meet the criteria, omit the section entirely — do not show an empty table.

**Implementation:** Pure report generation logic in `api/services/report_generator.py`.
No schema changes. No frontend changes. No new endpoints.

**Commit message:** Quick wins section in report — high priority, low effort roadmap items

---

### Word Report Template — Additional Formatting Cleanup
Initial template issues fixed (heading numbers, title block, Client Name field population).
Additional formatting issues observed but not yet catalogued.

**Next session procedure:**
1. Generate report for E002 or E003
2. Open the Word doc and list every remaining formatting issue explicitly
3. Fix each one
4. Run `validate_template.py` to confirm required styles still present
5. Commit when the document looks clean

**Files:** `api/services/report_generator.py`, `assets/roadmap_template.docx`

**Commit message:** Word report template — additional formatting cleanup

---

## Checkpoint 4 — Dry Run 4 (New Client End-to-End)

**Goal:** Complete end-to-end run through browser with a brand new fictional client
(Dry Run 4). Validates all Checkpoint 4 improvements under realistic conditions.

**Pre-run setup:**
- Create a new fictional client folder structure on OneDrive
- Write 3–4 fictional interview transcripts (CEO, Director of Delivery, VP Sales minimum)
- Include 1–2 fictional documents (financial summary + at least one delivery document type)
- Include at least one AI Readiness signal to validate new domain coverage

**The run (entirely through browser):**
1. Create engagement via New Engagement form
2. Set folder paths via Edit Settings
3. Process Files — verify candidate count is in the 25–40 range (auto-cull working)
4. Review candidates, load signals
5. Detect Patterns — verify AI Readiness patterns are detected if signals are present
6. Review patterns, load
7. Run all 5 agents in sequence, review and accept each
8. Parse Findings, assign contributing patterns, load (expect 5–8 findings)
9. Parse Roadmap, review, load (expect 10–16 items)
10. Generate Report — verify file saved to disk and path shown (not browser download)
11. Open Word doc — verify all 8 sections populated with narrative prose

**Pass criteria:**
- All 5 AgentRuns with accepted=1
- 5–8 OPDFindings created
- 10–16 RoadmapItems created
- Signal candidate count was in the 25–40 range
- AI Readiness patterns detected (if signals present)
- Word doc saves to disk, path shown in Report panel
- Report narrative sections are mark-up quality, not placeholder text
- Zero DB Browser operations required
- Zero Claude.ai copy-pasting
- Total API cost under $2.00
- Cross-engagement report shows new engagement alongside E001, E002, E003

---

## After Checkpoint 4

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

### Findings Enhancements — Pattern Enforcement, Evidence Summary, and Key Quotes
Build all three in one session. All three modify FINDINGS_EXTRACTION_PROMPT, OPDFindings
schema, and FindingsPanel. Separating them means touching the same files three times.

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
