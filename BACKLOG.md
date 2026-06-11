# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---

## NEXT SESSION — RESUME HERE (paused 2026-06-11)

**Where we are:** The Strengths & Value-Case Reframe (Tracks 1–3) is BUILT, 110 tests pass,
and it is **uncommitted**. A **Cobalt Data Partners (E006)** dry run is **in progress,
paused after report v1 was generated.** Cobalt is a purpose-built test client (answer key:
`C:\001-cowork-projects\New-client\Cobalt-Data-Partners_TESTKEY\Cobalt_E006_ANSWER_KEY.md`)
that exercises both the value-case reframe and the QA-stage traps — it doubles as Checkpoint 5.

**Validated so far this run:** 15 Strength signals extracted (9 domains); 1 Positive
("Preserve") finding loaded; v1 generated. Narrator audit: 8 pass / 4 flagged (punch list below).

**Do next, in order:**
1. **Judge v1 substance** against the answer key — value-case checks (leads with the prize,
   "What to Preserve" before the roadmap, strengths thread in the Exec Summary, roadmap value
   spine) and findings F1–F9.
2. **Run the QA stage** (QA-1/2/3 → QA-4 revision → v2) on v1 — confirm it catches the planted
   traps: C1–C4 contradictions, A1–A2 attribution errors, the margin-compression false trail.
   This is the Checkpoint 5 validation.
3. **Build one prompt punch list.** Known from the v1 narrator audit:
   - **Executive-snapshot brevity** — sentences ran 26/25/21 words; the value-first reframe
     packs in more, so push the prompt to hold ≤20 words/sentence (the snapshot is NOT in the
     compress pass). *This is the one real audit flag worth fixing.*
   - economic_impact_narrative ran 3 sentences (max 2) — minor narrator discipline.
   - Accept: the ungrounded-figure flags are correct unlabeled summary figures (match the key);
     the Rule-1 "diversification in Scale" flag is a defensible placement.
   - Add whatever the substance read + QA surface.
4. **Apply all prompt fixes at once → one clean narrator regen** → re-run QA on the regen.
5. **Review and COMMIT** the full body of work (large + uncommitted — see PROGRESS.md
   "Strengths"/"Cobalt fixes" rows). Suggested: branch, commit Tracks 1–3 + the bug-fix bundle
   together. Run the byte-identity diff gate (E004 negatives unchanged) before commit — logic
   is unit-tested but the full doc-level diff was deferred.

**Checkpoint scripts:** `python scripts/valence_state.py E006` reports strength-signal and
Positive/Dual-finding counts (run after extraction/load to fail cheap). Watch `top.log` for
`TRUNCATED at max_tokens` during roadmap/narrator.

---


## Technical Debt — Address Before Next Major Feature

### Build Sequence — current

The Post-Assembly QA Stage is COMPLETE (QA-1/2/3/4/5 — see PROGRESS.md), and the
**Strengths & Value-Case Reframe (Tracks 1–3)** is now BUILT and in **Cobalt E006**
validation (the dry run that doubles as Checkpoint 5). 110 tests pass; the work is
**not yet committed**. See "NEXT SESSION — RESUME HERE" at the top of this file. Work top
to bottom.

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| — | Checkpoint 5 — Dry Run 5 | milestone | Validates QA Stage end-to-end |
| 1 | Editable Engagement Info | 1 | Nice-to-have; can slot anywhere |
| 2 | PowerPoint Export | 1 | Ships with audit checks |
| 3 | Standardize Economic Output | 1 | Priority driven by QA Stage data |
| 4 | Structured File Metadata Capture | 1 | Medium — convention works as workaround |
| 5 | Auto-Suggest Knowledge | 1 | Lowest — current manual flow works |
| 6 | Strengths & Value-Case Reframe | — | ✅ BUILT (Tracks 1–3) — in Cobalt E006 validation. Deferred: brief *restructure* (vs reframe) to first pilot; pattern-level valence |

---

## Post-Assembly QA Stage — COMPLETE

QA-1 (Coverage), QA-2 (Coherence), QA-3 (Editorial split) shipped 2026-05-30,
QA-4 (Revision) shipped 2026-05-31, and QA-5 (integrated QA Tab UI) shipped
2026-06-01 — see PROGRESS.md for full implementation details. The entire
Post-Assembly QA Stage is now built. Remaining QA work is validation only:
**Checkpoint 5** (below).

Cowork QA prompt artifacts at `C:\001-cowork-projects\Northstar-working`
remain available as regression-test reference data for Checkpoint 5.

---

## Strengths & Value-Case Reframe — "What to Preserve" (BUILT — IN VALIDATION)

**Status:** Tracks 1–3 BUILT 2026-06-11 (110 tests pass, **uncommitted**); in Cobalt E006
validation. Full implementation record is in PROGRESS.md; the original design rationale is in
git history (commit "Capture Strengths & Value-Case Reframe design") and embodied in the code.
This section now lists only what shipped and what remains.

### Shipped (Tracks 1–3)
- **Track 1** — valence on signals + findings (`Strength/Risk/Neutral`, `Positive/Dual/Negative`,
  NULL≡Negative); Skeptic challenges unsupported strengths; Synthesizer assembles "What to
  Preserve"; 422 relaxed for Positive findings (≥1 domain Strength signal instead of a pattern);
  strength-signal evidence chain; scorecard no longer subtracts for strengths; new "What to
  Preserve" report section before the roadmap (omitted when empty → negatives byte-identical);
  `migrate_valence.py`.
- **Track 2** — `executive_summary_strengths` narrator field ("right to win" thread), omittable.
- **Track 3** — Executive Brief value reframe: value-first snapshot (prize → cause → recoverable
  value → first move), whole-brief value-case posture, "Three Gaps to Close", roadmap value
  spine. **Reframe only — page restructure intentionally NOT done.**
- Skill: strengths evidence rule + Preserve-finding pattern exception. QA-2 `weak_grounding`
  catches generic praise.

### Remaining / deferred
1. **Finish the Cobalt E006 validation** + the prompt punch list — see "NEXT SESSION — RESUME
   HERE" at the top of this file (esp. the executive-snapshot ≤20-word brevity fix).
2. **Track 3 brief _restructure_** (reorder/cut/add page-1 blocks) — DEFERRED to first real
   client pilot. Only the reversible *reframe* was built; restructuring needs client signal.
3. **Pattern-level valence** — deferred (non-load-bearing; only buys per-pattern analytics).
4. **Discrete defect (open):** on the Executive Brief, the "Competitive AI Capability Gap" block
   renders as loose paragraphs between the problems heading and the 3-problem table instead of
   inside it. Fix independently of the reframe.
5. **Pre-commit:** run the byte-identity diff gate on E004 (negatives unchanged) — logic is
   unit-tested; the full doc-level diff was deferred.

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
