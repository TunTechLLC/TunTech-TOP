# TOP — Backlog
## Build order: work top to bottom. Checkpoints are end-to-end dry runs with a new client.

---


## Technical Debt — Address Before Next Major Feature

### Build Sequence — current

The Post-Assembly QA Stage is COMPLETE: QA-1/2/3 shipped 2026-05-30; QA-4 shipped
2026-05-31 (in-place edit-list architecture, Opus 4.7, reconciliation); QA-5
integrated QA Tab UI shipped 2026-06-01 (see PROGRESS.md). **Checkpoint 5 is the
next work.** Work top to bottom.

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| — | Checkpoint 5 — Dry Run 5 | milestone | Validates QA Stage end-to-end |
| 1 | Editable Engagement Info | 1 | Nice-to-have; can slot anywhere |
| 2 | PowerPoint Export | 1 | Ships with audit checks |
| 3 | Standardize Economic Output | 1 | Priority driven by QA Stage data |
| 4 | Structured File Metadata Capture | 1 | Medium — convention works as workaround |
| 5 | Auto-Suggest Knowledge | 1 | Lowest — current manual flow works |
| 6 | Strengths & Value-Case Reframe | multi | Design captured below ("What to Preserve"). Three-track plan; brief reframe gated on first client pilot |

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

## Strengths & Value-Case Reframe — "What to Preserve" (DESIGN CAPTURED — NOT STARTED)

**Status:** Phase 1 design only. No code written. Stopped at the design gate by request.
Resume from these notes another day.

### Why this exists (commercial context)
TOP today produces an all-problems deliverable. That is a hard sell — a founder-led
consulting firm hears "your governance is broken" as "you are a bad leader," and gets
defensive. Clients also need to hear what they are doing **right**. The deeper reframe:
stop shipping a deficiency **audit** and start shipping a **value case** — same honest
findings, re-spined so the document sizes a recoverable prize and shows a winnable path,
instead of reading like a verdict.

**Commercial model that drives the brief design:** The plan is to sell the interviews +
the **Executive Brief** for ~$5k, presented live to the CEO. The brief is **page 1 of the
finished report** (after the TOC). If the CEO says yes in the room, Victor turns the page
into the full roadmap (already generated — TOP always builds the whole report; QA runs on
the full roadmap after it is built). So the brief is the **conversion artifact** and must
sell the rest. **Not yet piloted with a real client** — every design choice here, current
and proposed, is a hypothesis until there is client signal.

### Core design decision — valence as a field, NOT a strengths agent
Do **not** add a "strengths agent" — an agent incentivized to find strengths would fight
the Skeptic. Instead add **valence** as a dimension to the existing
signal → pattern → finding → synthesis pipeline:
- **Signal valence** (`Strength` / `Risk` / `Neutral`): tagged by the domain agent that
  already extracts the signal. A field, not a new pass. This is the SOURCE — positive
  evidence does not exist anywhere in the pipeline today, so it must enter here.
- **Finding valence**: `Positive` → a "Preserve" finding; `Dual` → strength-under-strain
  (strength + strain that share one root cause, e.g. a healthy win-rate trend AND an
  architect-contingent pipeline skew → one root → a "move" that protects the strength
  while fixing the strain); `Negative` → unchanged from today.
- **The Skeptic's mandate extends to strengths** — a strength that can't be traced to a
  named account, metric, or behavior dies exactly like an unsupported problem finding.
  This is the load-bearing guardrail against flattery-by-construction.
- **The Synthesizer ASSEMBLES "What to Preserve"** from validated positive/dual findings —
  it does not DERIVE praise. Sourcing and validation happen upstream.

### Where valence enters — the SEAM (differs from the original sketch; this is the verified-correct version)
Original sketch said "valence on signal → pattern → finding, minimum = push to the
pattern layer." **Code investigation showed the pattern layer is the wrong seam.** Two
findings forced the change:

1. **A "healthy" scorecard score is the ABSENCE of dysfunction, not the PRESENCE of
   strength.** `_compute_domain_scores` (`api/services/report_sections.py:28`) starts at
   5.0 and only ever **subtracts** (accepted pattern High −1.0 / Med −0.5 / Hyp −0.25;
   finding High −0.5 / Med −0.25). A domain scores 4.2 because *almost nothing was
   extracted from it* — there are no "positive patterns behind the score" to trigger a
   Preserve finding from. So positive evidence must be created upstream (signal
   extraction); the scorecard can't be its source.
2. **Patterns are constrained to a fixed dysfunction library (P01–P60).**
   `PatternDetectionResult` (`api/models/pattern.py`) validates `pattern_id` against the
   `Patterns` library; the agent **cannot invent a pattern**, and the library is a
   dysfunction catalog. A healthy domain has **zero** pattern instances, so "push valence
   to the pattern layer for healthy domains" produces nothing. A DUAL "strength-under-
   strain" cannot be a library entry.

**Verified-correct seam:** put valence on the **SIGNAL** (true source) and the **FINDING**
(carrier to the report). Make **DUAL a finding type assembled by the Synthesizer**, not a
pattern-library type. **Leave the pattern library untouched.** Pattern-level valence is
deferred and non-load-bearing (it only buys per-pattern analytics).

### Code investigation findings (verified 2026-06-08 against current code)
- **Signals**: `Signals` table has **no valence column**. 7 extraction prompts, all
  dysfunction-framed: `SIGNAL_EXTRACTION_PROMPT` (interview/other) in
  `api/services/prompts.py`; 6 doc prompts (financial/portfolio/sow/status/resource/
  delivery) in `api/services/document_processor.py`. Insert path:
  `SignalRepository.create` / `bulk_create`.
- **Findings**: `OPDFindings` has **no valence column**. `create_finding`
  (`api/routers/findings.py`) **enforces ≥1 contributing pattern (422)** — this blocks a
  Preserve finding for a healthy domain (no patterns to link). Must relax for
  `valence='positive'` (require ≥1 referenced Strength **signal** instead). Findings
  extracted from Synthesizer via `FINDINGS_EXTRACTION_PROMPT`; `_build_evidence_chain`
  walks pattern notes only — needs a strength-signal path for Preserve findings.
- **Scorecard latent bug**: every finding subtracts regardless of valence — a Preserve
  finding with a priority would WRONGLY lower a healthy domain's score. Fix:
  Positive/Dual findings do not subtract; optionally ADD a small increment for a validated
  strength so a Healthy score is *backed* by a Preserve finding instead of dead-ending.
- **Report**: `report_generator._build` renders the brief as page 1
  (`_build_executive_briefing`); `_findings_by_domain` renders ALL findings (Positive
  findings must be EXCLUDED here — they belong in "What to Preserve"). "What to Preserve"
  section goes **before the Transformation Roadmap** (`report_generator.py:359`).
  `_SECTION_MAP` numbers shift by one when a numbered section is inserted before the
  roadmap — must update the map (drives reader-guide cross-refs).
- **Migration pattern**: nullable `ALTER TABLE` + `schema_migrations` record; see
  `migrations/migrate_qa_revision.py` for the template. Add `valence` to the two
  `CREATE TABLE`s in `tests/test_repositories.py`.

### THE ROLLOUT PLAN — three tracks split by risk (this is the key decision)
Reasoning: the Executive Brief and Executive Summary are Victor's heavily-invested,
**unpiloted** design. The real risk is not "a change breaks the design" — it's that we
guess wrong about what converts a CEO with zero client data and reshape the one tuned
conversion artifact blind. So split by risk:

**Track 1 — DO NOW. Safe. Never touches the brief or summary.**
The capability itself: valence on signals + findings; the Skeptic mandate extension; the
Synthesizer/findings-extraction emitting Preserve/Dual; a dedicated **"What to Preserve"
section in the report body, before the roadmap**; the scorecard fix (strengths stop
subtracting, optionally add). This gives the system the capability and a real home for
strengths without risking the conversion page.

**Track 2 — Reversible, additive. Extends the existing Executive Summary (Victor invited
additions here).** Add a "what's working / where you have the right to win" thread plus
strengths-as-leverage ("your strong client relationships let you reprice without churn")
and the current→future climb. Note the summary ALREADY carries trajectory (margin trend,
18-month target, aggregate "Revenue at Risk") — EXTEND it, don't bolt on a duplicate.

**Track 3 — DEFER TO THE PILOT. The one-page Executive Brief reframe.**
Do not redesign the one-pager blind. It is the exact thing that needs real client signal
before reshaping. After the first pilot, tune it against evidence as a redline approved
line by line. See the brief-reframe guidance below for what that change will be.

### Brief-reframe guidance (Track 3 — what a McKinsey partner would do)
Observed on the real E005 brief: it is a **full page, 100% problem/risk-framed** — zero
strengths, numbers framed as exposure/loss ($550K / $435K / $378K). The page has no free
space; anything added displaces something tuned. BUT the brief already has the **best,
hardest part**: a *challenger reframe* ("your margin problem is not a tooling/PM problem —
it's a structural operating-model failure"). Keep that.

A partner would NOT say "open with strengths" (flattery on page 1 reads soft and gets
discounted) and would NOT say "beat them down." The diagnosis: the brief is negative
**without a prize and without signaling the fight is winnable**. Three surgical, mostly-
**reframe** (not restructure) moves:
1. **Reframe loss → recoverable value — same numbers, opposite valence.** "$378K annual
   margin erosion cost" → "$378K/yr recoverable margin"; "Revenue at risk" → "value at
   stake". Adds nothing; relabels what exists.
2. **Anchor the insight to a prize + target up front** (sized, in the first 3 lines).
3. **Use the strength as the reason it's winnable, not as praise** — "this is a structural
   governance gap, not a talent or client problem — which is exactly why it's fixable."
Posture shift: "we're on the same side of the table" — honesty in the *diagnosis*, warmth
in the *posture*; keep every hard fact.

Illustrative before/after (NOT a spec — uses E005 content, which is a defect-test
engagement):
> **Now:** "Stratum's margin problem is not a tooling or PM-capacity problem. It is a
> structural operating model failure… Gross margin has fallen from 41% to 33.1%…"
>
> **Reframe:** "Stratum has the delivery talent and client relationships to run at 37%+
> margin. Today it runs at 33.1%, down from 41% in 24 months — and the cause is not
> tooling or PM capacity. It's one structural gap: Sales commits scope and price before
> Delivery ever sees the deal. That's the most fixable kind of problem, and closing it
> puts an estimated $378K a year back in the business."

Same insight, same numbers, same candor — opens on a prize and a winnable fight instead of
a wound, with **zero new blocks**. **Reframe now (low-risk, reversible, strong prior);
restructure (reorder/cut blocks) only after pilot signal.** The direction (value-framed,
answer-first, "winnable prize") is a decades-established executive-communication prior, not
a coin flip — pilot *from* it.

### Skill + QA changes
- Add a **strengths evidence rule** to the `top-deliverable-quality` skill: every strength
  names an account, metric, or behavior; no generic praise ("strong team"); mirror the
  existing "documented pattern" / "CONFIRMED opportunity" evidence rules.
- Keep the line clean: **sourcing** strengths is upstream (extraction prompts + Synthesizer
  + the Skeptic as generation-time gate); **enforcing** "no strength without specific
  evidence" is the QA stage — extend QA-2 Coherence's existing `weak_grounding` category to
  catch generic praise in the rendered "What to Preserve" section. QA can kill a bad
  strength; it cannot generate a good one.

### Backward compatibility
- New `valence` columns nullable; NULL ≡ today's negative behavior. Existing negative
  findings must stay **byte-for-byte behavior-identical**.
- Zero positive/dual findings ⇒ **OMIT** the "What to Preserve" section entirely
  (byte-identical to today's deliverable). Do NOT print "no preservable strengths
  surfaced." A Healthy domain with no Preserve finding becomes a **QA flag**, not a report
  line — keeps the dead-end visible to the consultant without polluting a clean
  negative-only deliverable.

### Blast radius (Track 1 minimum)
Migration (`migrate_valence.py`: ALTER Signals + OPDFindings, schema_migrations records) ·
`models/signal.py` · `models/finding.py` · `db/repositories/signal.py` ·
`db/repositories/finding.py` · `document_processor.py` (extraction prompts — minimum:
interview + financial/status/portfolio; full: all 7) · `prompts.py`
(`SIGNAL_EXTRACTION_PROMPT`, `SKEPTIC_PROMPT`, `SYNTHESIZER_PROMPT`,
`FINDINGS_EXTRACTION_PROMPT` — all **holistic rewrites**, never spliced) ·
`case_packet.py` (`_section_2_signals` surfaces valence to agents) ·
`routers/findings.py` (relax 422 for `valence='positive'`; parse-synthesizer
default/validate valence; strength-signal evidence path) · `report_sections.py`
(`_compute_domain_scores` fix, new `_what_to_preserve` renderer, exclude Positive from
`_findings_by_domain`, `_SECTION_MAP` renumber) · `report_generator.py` (call
`_what_to_preserve` before the roadmap) · frontend (`SignalPanel.jsx` valence badge/edit,
`FindingsPanel.jsx` Preserve/Dual rendering, `constants.js` VALENCE list) · skill ·
`tests/test_repositories.py` schema + new tests.
**Untouched / must stay identical:** negative-finding create/update/render, pattern
detection (minimum), roadmap extraction, narrator prompt (the "What to Preserve" section is
rendered deterministically from finding fields — deliberately avoids touching the ~700-line
narrator prompt).

### Open decisions to confirm before coding
1. Seam relocation: valence on **signal + finding**, DUAL as a finding type, pattern
   library untouched (vs. the original "valence to the pattern layer"). **Recommended.**
2. Relax the ≥1-pattern 422 guard for Positive findings (require ≥1 Strength signal
   instead). **Required**, or strengths can't become findings.
3. Empty section ⇒ **omit** (byte-identical); Healthy-domain gap caught by QA. **Recommended.**
4. Scope for the pilot: ship **Track 1 + Track 2**; hold **Track 3 (brief reframe)** for
   first-pilot signal. **Recommended.**

### Test plan
Migration idempotency + `--verify` · repo round-trip (signal + finding valence persists /
NULL defaults) · `_compute_domain_scores`: Preserve finding does NOT lower the score
(golden assertion on E004 numbers proving negatives unchanged) · `_what_to_preserve`
renders only Positive/Dual, empty ⇒ section omitted (doc byte-identical) · **diff harness**:
generate pre-change vs post-change on E004/E005 with zero strength findings → negative
findings byte-for-byte identical · E005-style dry run: a Healthy domain emits a Preserve
finding, a Dual finding renders strength/strain/move, negatives diff clean.

### Separate small defect found during this design (fix independently)
On the Executive Brief, the **"Competitive AI Capability Gap"** block renders as loose
paragraphs BETWEEN the "Three Critical Problems" heading and the 3-problem table, instead
of inside the table — confirmed unintentional. Likely a 4th problem the narrator emitted
that didn't land in the table structure. Discrete bug on the conversion artifact; fix on
its own, separate from the reframe work above.

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
