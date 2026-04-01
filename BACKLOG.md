# TOP — Backlog
## Items deferred from Phase 2 — build after Checkpoint 3 unless noted

---

## Deferred to After Checkpoint 3

### Auto-Suggest Knowledge Promotions from Synthesizer Output
**Problem:** Knowledge promotions are fully manual — consultant must identify and
type insights worth promoting. Should follow the same detect-review-load pattern
as findings and roadmap.

**Design:** After Synthesizer is accepted, add a "Suggest Knowledge" button that
calls Claude to extract 3–5 reusable insights from the Synthesizer output —
observations that would be useful across future engagements, not just this one.
Present as cards with Accept / Reject per item. Accepted items call the existing
knowledge create endpoint.

**New prompt needed:** KNOWLEDGE_EXTRACTION_PROMPT in claude.py
**New endpoint needed:** `POST /{engagement_id}/knowledge/suggest`

---

### Replace Report Browser Download with Save-and-Show-Path
**Problem:** Download Report streams the file to the browser, which saves a redundant
copy to the Downloads folder. For a locally hosted single-user tool, the file is already
saved to reports_folder on disk — the browser download adds no value.

**Fix:** Change the Report tab to show a confirmation message with the full file path
after generation instead of triggering a browser download. Add an "Open folder" button
that calls a new backend endpoint to open the reports_folder in Windows Explorer
(via `os.startfile(reports_folder)`). Remove the FileResponse streaming from the
download endpoint or keep it as a secondary option.

**New endpoint:** `POST /{engagement_id}/report/generate` — saves file, returns
`{"saved_to": "C:\\...\\OPD_Report_E003.docx"}`. Frontend displays the path.
**Optional:** `POST /{engagement_id}/report/open-folder` — calls `os.startfile()`.

---

### Roadmap Item Edit and Delete
**Problem:** Once a roadmap item is saved there is no way to edit or delete it
from the browser. Typos and wrong field values require DB Browser to fix.

**Fix:** Add an Edit button per row that opens an inline edit form (same fields as
the add form), and a Delete button with a confirmation prompt.
**New endpoint needed:** `DELETE /{engagement_id}/roadmap/{item_id}`
PATCH already exists for update.

---

### Add Field Labels to Finding Candidate Review Cards
**Problem:** The Parse Findings candidate review cards show unlabeled text inputs.
The OPD section number field shows "4" with no context. Users cannot tell which
field is which without counting positions.

**Fix:** Add a small label above each input/textarea/select in the candidate card,
matching the labels used in the manual Add Finding form. Minimal change —
just add `<div className="text-xs text-gray-500 mb-0.5">Label</div>` above each field.

---

### Improve PATTERN_DETECTION_PROMPT for New Domain Coverage
**Problem:** Second pattern detection run on E003 (102 signals, including clear AI Readiness
signals) returned zero AI Readiness patterns. First run detected 3, but errored before loading.
Claude is non-deterministic and with a large signal set tends to anchor on the most
numerically dominant domains (Sales-to-Delivery, Delivery Operations) and under-detect
sparse new domains.

**Fix:** Add few-shot examples to PATTERN_DETECTION_PROMPT showing correct detection of
AI Readiness, Human Resources, and Finance and Commercial patterns. Add an explicit
instruction: "Ensure coverage across all domains represented in the signals — do not
omit a domain simply because it has fewer signals than others."

---

### Disable Agent Buttons While Any Agent Is Running
**Problem:** Re-run buttons on earlier agents remain enabled while the Skeptic or
Synthesizer is actively running. Accidentally re-running an earlier agent mid-sequence
would invalidate the in-progress agent's context.

**Fix:** Track a single `anyRunning` boolean in AgentPanel. When any agent call is
in flight, disable all run/re-run buttons across the panel until the call completes.
**Implementation:** One shared `useState` in AgentPanel passed as a prop or managed
via a running agent name string — if `runningAgent !== null`, all buttons disabled.

---

### Auto-Cull Signal Candidates Before Review
**Problem:** Claude over-extracts signals from rich transcripts. 110 candidates from 6 files
is unworkable for manual review. The consultant should only see a pre-filtered set.

**Design:**
- After extraction, score each candidate against two criteria:
  1. Deduplicate — if two candidates from different files have the same domain +
     similar signal_name (fuzzy match or exact domain+observed_value), keep the
     higher-confidence one and drop the duplicate
  2. Filter by confidence — drop all Hypothesis signals by default; show count of
     dropped signals so the consultant can opt back in if needed
- Apply in `document_processor.py` after all files are processed, before writing
  the merged candidate list to the frontend
- Target output: 25–40 candidates regardless of input file count

**UI addition:** Show "X Hypothesis signals hidden — show all" toggle above the review list.

**Commit scope:** document_processor.py dedup logic + SignalPanel.jsx toggle

---

### Report Narrator — Narrative Layer for the OPD Report
**Problem:** The current report generator produces a diagnostic database formatted as a
Word document — structured tables and bullet lists assembled from field values. The output
is factually accurate but reads like a database printout, not a consulting deliverable.
A senior consultant would need hours to transform it into something presentable to a CEO.

**Design:** Add a Report Narrator agent that runs before `report_generator.py` assembles
the Word document. The Narrator receives the full Synthesizer output plus all accepted
findings and roadmap data, and writes the narrative prose sections of the report. The
structured tables stay exactly as they are — generated from structured data. The Narrator
writes the connective tissue around them.

**Quality target:** The output should be 80% ready to send after 30–60 minutes of
consultant review and polish. Mark-up quality, not rewrite quality.

**Inputs to the Narrator:**
- Full accepted Synthesizer output (primary narrative input — this is the story)
- All accepted findings with structured fields (grounding — these are the facts)
- Roadmap items grouped by phase (sequencing — these are the actions)
- Engagement record (context — firm name, stated problem, client hypothesis)

**Narrator-generated sections:**
- Section 1: Executive Summary — 4–5 paragraphs of prose. Lead with the finding, not
  background. Paragraph 1: strategic situation. Paragraph 2: client hypothesis vs
  diagnostic reality. Paragraph 3: economic stakes. Paragraph 4: Priority Zero items
  and sequencing. Paragraph 5: what successful execution positions the firm to achieve.
- Section 4: Domain Analysis — each domain opens with a 2–3 sentence narrative paragraph
  before the finding table. After the table, 2–3 sentences connecting this domain's
  findings to other domains.
- Section 5: Root Cause Analysis — connected prose narrative, not a bullet list of
  repeated finding titles. Show the causal chain across findings.
- Section 6: Economic Impact — a summary table of all confirmed and inferred figures
  plus 3–4 sentences of narrative connecting the numbers to business stakes.
- Section 7: Improvement Opportunities — a short narrative paragraph per finding
  explaining the recommendation in context, not just the recommendation field repeated.
- Section 8: Transformation Roadmap — a brief rationale paragraph before each phase
  table explaining why these items are sequenced this way.

**Sections that stay as structured data (no Narrator):**
- Section 2: Engagement Overview — auto-generated table from engagement record
- Section 3: Operational Maturity Overview — auto-generated signal domain summary table
- Roadmap tables within Section 8 — auto-generated from RoadmapItems

**Writing rules for the REPORT_NARRATOR_PROMPT:**
- Write as a senior consultant, not as an AI summarizing data
- Lead with the most important insight, not with background
- Use specific numbers and signal references — do not generalize
- Use CONFIRMED/INFERRED notation on all dollar figures exactly as they appear in source
- Balance prose with structure — tables where data is tabular, prose where analysis is narrative
- Do not repeat the same content across sections
- Do not hedge excessively — state conclusions clearly where evidence supports them
- Tone: direct, evidence-grounded, written for a CEO audience

**Quality reference — example Executive Summary opening paragraph (target quality):**
"Vantage Point Consulting is experiencing a structural profitability crisis that is
accelerating. Gross margin has declined from 33.1% in FY2023 to 27.8% in Q1 2026 —
a three-year directional trend, not a cyclical dip — while EBITDA has compressed from
11.2% to 7.6% over the same period. At the current trajectory, annualized EBITDA falls
below $300,000 INFERRED, which constrains the firm's ability to reinvest, absorb delivery
failures, or sustain the talent required to stop the decline."

Key characteristics of target quality: leads with the finding not the background, uses
specific confirmed figures, states the business consequence clearly, no hedging.

**Implementation:**
- New prompt: `REPORT_NARRATOR_PROMPT` in `api/services/claude.py`
- New async function: `generate_report_narrative(engagement_id)` in `claude.py`
  - Assembles Synthesizer output + all findings + roadmap items + engagement context
  - Calls Claude with REPORT_NARRATOR_PROMPT
  - Returns structured dict with keys for each narrator-generated section
- Update `ReportGeneratorService.generate()` in `api/services/report_generator.py`
  - Call `generate_report_narrative()` first
  - Use returned narrative sections as prose content in the document
  - Weave narrative paragraphs before/after structured tables in each section
- No new endpoints, no database changes, no frontend changes

**Test procedure:**
1. Run against E001 Meridian — it has accepted Synthesizer, findings, and roadmap
2. Download the report
3. Read Section 1 — should be 4–5 paragraphs of prose that tell the story, not a placeholder
4. Read one Domain Analysis section — should open with a narrative paragraph before the table
5. Check that CONFIRMED/INFERRED notation is preserved from the Synthesizer output
6. Assess: would you mark this up or rewrite it? Target is mark-up quality.
7. Run against E003 to validate across a different engagement profile

**Prompt refinement:** Expect 2–3 iterations on REPORT_NARRATOR_PROMPT before quality
is consistently at the mark-up threshold. This is normal — prompt quality is the variable.

---

### Enforce Pattern-to-Finding Mapping
**Requirement:**
- Every finding must reference 1+ patterns (Pxx)
- Patterns must be explicitly linked, not inferred
- Finding inherits domain (if consistent across patterns) and economic model types

**Rules:**
- No orphan findings — must map to at least one pattern
- If multiple patterns, they must share a common root cause OR be explicitly grouped
  under a single control point

**Output (internal, not UI yet):**
```
Finding F001:
Patterns: P06, P08, P10
Domains: Sales-to-Delivery Transition
Economic Models: Delivery Overrun Loss, Delay / Start Lag
```

**Implementation:**
- Require at least one `contributing_ep_id` when creating a finding (currently optional)
- Store the inherited economic model types from contributing patterns on the finding record

---

### Standardize Economic Output Generation
This is the most consequential system improvement. Every number in the report becomes
reproducible. For each economic formula type in the pattern library, define:

**A. Inputs**
- Required variables (e.g. Idle Hours, Bill Rate)
- Source: Confirmed (from data) or Estimated (from interview / assumption)

**B. Assumptions**
- Default values if inputs are missing
- Acceptable ranges
- Override rules

**C. Range Logic**
- When to output a point estimate vs a range
- How the range is calculated (Low = conservative assumption, High = aggressive assumption)

**Example — Delivery Overrun Loss:**
```
Inputs:
  - Overrun Hours (estimated or confirmed)
  - Cost Rate (confirmed or estimated)

Assumptions:
  - Overrun % range: 10%–25% if not explicitly measured

Range Logic:
  - Low = 10% overrun scenario
  - High = 25% overrun scenario
```

Build after the pattern-to-finding mapping is enforced.

---

### Lightweight Evidence Summary on Findings
Keep this simple. Do not over-engineer.

**Requirement:** Each finding includes 1–2 lines:
```
Evidence Summary:
Supported by P06, P08, P10 across sales-to-delivery transition;
6 signals (2 confirmed, 4 inferred); observed across 3 projects
```

**Rules:**
- Must include: pattern IDs, signal count (optional but strong), confirmation mix if available
- This becomes straightforward once pattern-to-finding mapping is enforced

---

### Synthesizer-to-Roadmap Parser
Same detect-review-load pattern as the findings parser (Step 8 Extension 2).
Auto-generate roadmap items from accepted Synthesizer output.
Build after findings parser is validated in Checkpoint 3.
The Synthesizer output contains roadmap suggestions but they are less structured than
the findings section — parsing is harder and should be validated separately.

---

### PDF Processing
`document_processor.py` currently only handles `.txt` files.
Real client documents are PDFs.
**Library decision locked in:** PyMuPDF (also called `fitz`).
**Where conversion happens:** `document_processor.py` — detect `.pdf` extension,
convert to text automatically before sending to Claude. No change to the rest of the pipeline.
Install: `pip install pymupdf`

---

### Candidate File Cleanup (Archive After Loading)
Candidate JSON files accumulate in the candidates folder indefinitely.
**Decision locked in:** Archive to `processed/` subfolder after loading, not delete.
The candidate file is a useful audit trail — shows exactly what Claude extracted,
what was approved, what notes were attached.
**Implementation:** In the `load-candidates` endpoint, after signals are written,
call `shutil.move(candidate_file_path, candidates_folder/processed/)`.
One line of Python.

---

### Reprocess Button
Currently must delete from ProcessedFiles table in DB Browser to reprocess a file.
Add a Reprocess button to SignalPanel that clears the specific file hash from
ProcessedFiles table through the browser.
**New endpoint needed:** `DELETE /{engagement_id}/signals/processed-files/{file_hash}`

---

### Engagement Header Count Refresh
Signal/pattern/finding counts in the EngagementDetail header do not refresh after
write operations. Requires F5 page refresh to update.
**Fix:** Pass a refresh callback from EngagementDetail down to each panel component.
When a panel writes data (loads signals, loads patterns, creates finding), it calls
the refresh callback which re-fetches the engagement header data.

---

### Word Report Template Cleanup
The generated `.docx` uses default python-docx styles (Table Grid, Heading 1-3, List Bullet).
Needs visual polish before client delivery: column widths, font sizing, header row shading,
consistent spacing. Consider a custom document template (`.dotx`) as the base for `Document()`.
Not blocking — the content is correct and readable. Build after Report Narrator is validated —
the template cleanup and the narrative layer are separate concerns.

---

## Phase 3 Items

### PostgreSQL Migration
Only two changes needed when the time comes:
1. `BaseRepository._get_connection()` — swap `sqlite3` for `psycopg2`, update connection string
2. Parameter placeholders — `?` becomes `%s` throughout all SQL constants
Everything else — repositories, routers, services — is database-agnostic and unchanged.
**Config:** Set `TOP_DB_PATH` env var to PostgreSQL connection string.

### Background Task Processing for Document Files
Current `process-files` endpoint runs synchronously — FastAPI awaits full Claude processing
before returning. For long transcripts or many files this could approach timeout limits.
**Phase 3 design:** Background task with job table, polling endpoint, and status tracking.
For Phase 2 dry runs, synchronous is acceptable. If a transcript causes a timeout, split it
into two files as a workaround.

### Agent Registry URL Cleanup
`GET /api/engagements/agents/registry` is registered under the engagements prefix but is
not engagement-specific. Cosmetic issue only — the frontend calls it correctly.
**Phase 3 fix:** Move to `/api/agents/registry` in a dedicated agents router registered
under `/api`. Update `api.js` and `AgentPanel.jsx` accordingly.

### AWS Hosting
When moving to AWS:
- `_get_connection()` uses RDS connection string — set via `TOP_DB_PATH` env var
- File processing reads from S3 instead of local filesystem — `document_processor.py` gets S3 client
- Log path set via `TOP_LOG_PATH` env var pointing to CloudWatch or mounted volume
- `main.py` CORS origins updated to production domain
- Frontend built with `VITE_API_URL=https://top.tuntechllc.com/api`
No architectural changes required — all configuration driven.

### Multi-User Auth
When adding a second user:
1. Add `users` table
2. Add `user_id` column to `Engagements` table
3. Add WHERE filter to all engagement queries: `WHERE user_id = ?`
4. Add auth layer (FastAPI middleware + JWT or session)
Nothing in the current schema conflicts with this — `engagement_id` is already the
correct scoping key for all user data.

### Custom Domain
`top.tuntechllc.com` — add DNS record pointing to AWS load balancer when hosted.
No code changes needed — driven by `VITE_API_URL` build env var.

---

## New Patterns (Run Before Dry Run 3)

SQL INSERT statements ready in `TOP_New_Domain_Expansion.docx` (OneDrive\100_TunTech\Admin\).
Run in DB Browser against TOP.db before dry run 3.

| Pattern ID | Name | Domain |
|-----------|------|--------|
| P48 | No AI Delivery Capability | AI Readiness |
| P49 | No AI Service Offering | AI Readiness |
| P50 | AI Governance Absence | AI Readiness |
| P51 | Business Model Not AI-Ready | AI Readiness |
| P52 | High Voluntary Turnover | Human Resources |
| P53 | No Career Development Framework | Human Resources |
| P54 | Weak Hiring Process | Human Resources |
| P55 | Immature HR Function | Human Resources |
| P56 | Weak Manager Development | Human Resources |
| P57 | Weak Collections Discipline | Finance and Commercial |
| P58 | No Cash Flow Visibility | Finance and Commercial |
| P59 | Weak Contract Governance | Finance and Commercial |
| P60 | Immature Financial Infrastructure | Finance and Commercial |

After running: `SELECT COUNT(*) FROM Patterns` should return 58.

---

## Prompt Improvements (Lower Priority — After Checkpoint 3)

- **DELIVERY_DOCUMENT_EXTRACTION_PROMPT** — general purpose prompt for risk registers,
  retrospectives, portfolio summaries, proposals. Not needed for dry run 3 if those
  document types are not included.
- **PATTERN_DETECTION_PROMPT** — add examples of good vs weak detections to calibrate
  confidence levels more precisely.
- **Delivery Operations agent prompt** — expand from current single paragraph to
  multi-section instruction matching original Phase 1 quality. Current version is adequate
  but thinner than the original Google Doc prompt.

---

## Architectural Notes for Future Reference

- **Do not add SQLAlchemy** — clean SQL in repositories is the right pattern for this project.
  PostgreSQL migration only requires changing `_get_connection()` and `?` to `%s`.
- **Do not add global state** — all data must be scoped to `engagement_id`.
  Cross-engagement reporting queries across all engagements by design — that is intentional.
  Any new feature should be scoped to an engagement, not global.
- **Knowledge promotions stay manual** — auto-extraction is possible but these are
  qualitative judgments requiring consultant review. The form is the right interface permanently.
