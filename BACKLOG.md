# TOP — Backlog
## Items deferred from Phase 2 — build after Checkpoint 3 unless noted

---

## Deferred to After Checkpoint 3

### Synthesizer-to-Roadmap Parser
Same detect-review-load pattern as the findings parser (Step 8 Extension 2).
Auto-generate roadmap items from accepted Synthesizer output.
Build after findings parser is validated in Checkpoint 3.
The Synthesizer output contains roadmap suggestions but they are less structured than
the findings section — parsing is harder and should be validated separately.

### PDF Processing
`document_processor.py` currently only handles `.txt` files.
Real client documents are PDFs.
**Library decision locked in:** PyMuPDF (also called `fitz`).
**Where conversion happens:** `document_processor.py` — detect `.pdf` extension,
convert to text automatically before sending to Claude. No change to the rest of the pipeline.
Install: `pip install pymupdf`

### Candidate File Cleanup (Archive After Loading)
Candidate JSON files accumulate in the candidates folder indefinitely.
**Decision locked in:** Archive to `processed/` subfolder after loading, not delete.
The candidate file is a useful audit trail — shows exactly what Claude extracted,
what was approved, what notes were attached.
**Implementation:** In the `load-candidates` endpoint, after signals are written,
call `shutil.move(candidate_file_path, candidates_folder/processed/)`.
One line of Python.

### Reprocess Button
Currently must delete from ProcessedFiles table in DB Browser to reprocess a file.
Add a Reprocess button to SignalPanel that clears the specific file hash from
ProcessedFiles table through the browser.
**New endpoint needed:** `DELETE /{engagement_id}/signals/processed-files/{file_hash}`

### Engagement Header Count Refresh
Signal/pattern/finding counts in the EngagementDetail header do not refresh after
write operations. Requires F5 page refresh to update.
**Fix:** Pass a refresh callback from EngagementDetail down to each panel component.
When a panel writes data (loads signals, loads patterns, creates finding), it calls
the refresh callback which re-fetches the engagement header data.

### Multi-File Candidate Review (Merge All Files)
Currently only the first candidate file displays after multi-file processing.
Files 2+ are processed and written correctly but the frontend ignores them.
**Fix:** Merge all candidate files from a processing batch into one review list
with a `source_file` label on each candidate card so you know which interview
each signal came from.
**Files to change:** `document_processor.py`, `signals.py` router, `SignalPanel.jsx`
This is actually a Step 8 Extension 1 cleanup item — prioritize before Checkpoint 3.

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
