# TOP — TunTech Operations Platform
## Development Progress
*Read this at the start of every Claude Code session alongside CLAUDE.md*

---

## Current Status

**Phase A (Backend):** ✅ Complete — Checkpoint 1 passed
**Phase B (Frontend):** 🔄 In progress — Steps 4–8 Extension 1 complete, Checkpoint 2 passed

**Where we are:** All pre-Claude Code cleanup is complete. Step 8 Extension 1 (file processing
and signal extraction) is complete and verified. Ready to build Step 8 Extension 1 Cleanup,
then Step 8 Extension 2.

---

## Completed Steps

| Step | Description | Status |
|------|-------------|--------|
| 1–3 | Database schema, 14 tables, repositories, API utils | ✅ |
| 4 | FastAPI app, 8 routers, CORS, logging, error handler | ✅ |
| 5 | Dashboard + NewEngagement components | ✅ |
| 6 | EngagementDetail, 8 tabs, Edit Settings | ✅ |
| 7 | All panel components (Signal, Pattern, Agent, Finding, Roadmap, Knowledge, Report) | ✅ |
| 8 | Document processing pipeline | ✅ |
| 8 Ext 1 | File processing and signal extraction | ✅ Complete and verified |

---

## Next Steps (in order)

### NEXT: Step 8 Extension 1 Cleanup — File Type Expansion

**What it does:** Adds three new extraction prompts and updates the document processor
to handle status reports, resource/utilization documents, and a general delivery document type.

**Files to change:**
- `api/services/claude.py` — add STATUS_EXTRACTION_PROMPT, RESOURCE_EXTRACTION_PROMPT, DELIVERY_DOCUMENT_EXTRACTION_PROMPT
- `api/services/document_processor.py` — add status, resource, delivery to PROMPT_MAP and valid types set

**New file type to prompt mapping:**

| Type keyword | Prompt | Document type |
|-------------|--------|---------------|
| interview | SIGNAL_EXTRACTION_PROMPT | Any interview transcript |
| financial | FINANCIAL_EXTRACTION_PROMPT | P&L, margin reports, revenue data |
| sow | SOW_EXTRACTION_PROMPT | Statements of work, contracts |
| resource | RESOURCE_EXTRACTION_PROMPT (new) | Utilization reports, staffing data |
| status | STATUS_EXTRACTION_PROMPT (new) | Project status reports, RAG dashboards |
| delivery | DELIVERY_DOCUMENT_EXTRACTION_PROMPT (new) | Risk registers, retrospectives, proposals |
| other | SIGNAL_EXTRACTION_PROMPT | Anything else |

**Test procedure:**
1. Create E003_status_test.txt with a mock status report (3-5 lines of fake project health data)
2. Set E003 folder paths in Edit Settings if not already set
3. Click Process Files — verify processing completes
4. Verify candidates are delivery/governance domain focused
5. Delete test record: in DB Browser run DELETE FROM ProcessedFiles WHERE file_name = 'E003_status_test.txt'
6. Delete any test signals that were loaded

**Commit message:** Step 8 Ext 1 Cleanup — file type expansion (status, resource, delivery prompts)

---

### Step 8 Extension 1 Cleanup — Multi-File Review Fix

**What it does:** Merges candidates from all files processed in a batch into one review list
with a source_file label on each candidate card.

**Problem:** Frontend only shows candidates from first processed file. Files 2+ are written
correctly but not displayed.

**Files to change:**
- `api/services/document_processor.py` — process_engagement_files() returns list of ALL candidate file paths
- `api/routers/signals.py` — process-files endpoint returns all candidate file paths
- `frontend/src/components/SignalPanel.jsx` — fetch ALL candidate files, merge into one array with source_file field, show source label on each card

**Test procedure:**
1. Create two test transcript files for E003
2. Click Process Files
3. Verify all candidates from both files appear in one review list
4. Verify each candidate shows which source file it came from
5. Load approved candidates, verify signal count increases correctly
6. Clean up test records from ProcessedFiles and Signals tables

**Commit message:** Step 8 Ext 1 Cleanup — multi-file review fix

---

### Step 8 Extension 2 — Synthesizer-to-Findings Parser

**What it does:** Automated extraction of structured findings from the accepted Synthesizer
agent output. Replaces manual finding entry as the primary workflow.

**New backend:**
- FINDINGS_EXTRACTION_PROMPT in api/services/claude.py
- extract_findings_from_synthesizer(synthesizer_output, accepted_patterns) async function in claude.py
- POST /{engagement_id}/findings/parse-synthesizer endpoint in api/routers/findings.py
  - Fetches accepted Synthesizer output via AgentRunRepository.get_accepted_output(engagement_id, "Synthesizer")
  - Fetches accepted EngagementPatterns for contributing pattern context
  - Calls extraction function, validates fields
  - Returns candidates array (held in frontend state, not persisted until loaded)

**New frontend (FindingsPanel.jsx):**
- Parse Findings button — show only when Synthesizer is accepted AND findings count == 0
- Finding candidates review section — editable cards with contributing patterns checklist
- Load Approved Findings button — calls api.findings.create() for each approved finding
- On success: clear candidates, refresh findings list

**FindingCreate schema each candidate must match:**
- finding_title: str
- domain: str (one of 10 valid domains from constants.js)
- confidence: str (High / Medium / Low)
- operational_impact: str
- economic_impact: str
- root_cause: str
- recommendation: str
- priority: str (High / Medium / Low)
- effort: str (High / Medium / Low)
- opd_section: int (1-8)
- contributing_ep_ids: list of str (EP IDs of accepted patterns)

**Test procedure:**
1. In DB Browser: DELETE FROM OPDFindings WHERE engagement_id = 'E001'
2. In DB Browser: UPDATE EngagementPatterns SET accepted=0 WHERE engagement_id = 'E001'
3. In browser, navigate to E001 Meridian, Findings tab
4. Click Parse Findings button
5. Verify 7 candidates appear matching original findings
6. Assign contributing patterns on each card
7. Click Load Approved Findings
8. Verify 7 findings appear with correct data
9. Verify contributing patterns are accepted (accepted=1 in EngagementPatterns)

**Commit message:** Step 8 Ext 2 — Synthesizer-to-Findings parser

---

### Step 9 — Cross-Engagement Report Screen

**What it does:** Read-only screen with three tables — pattern frequency, economic impact,
and agent run log across all engagements. No write operations.

**Backend:** Already exists — GET /api/cross-engagement returns all 7 view results.

**New file:** frontend/src/components/CrossEngagement.jsx

**Three sections:**
1. Pattern Frequency — all patterns sorted by times_detected desc, highlight rows where times_detected >= 2
2. Economic Impact by Engagement — firm_name, patterns_accepted, impact_summary, link to engagement
3. Agent Run Log — firm_name, agent_name, run_date, accepted badge, output_summary

**App.jsx change:** Replace CrossEngagementPlaceholder with CrossEngagement component

**Test procedure:**
1. Navigate to Cross-Engagement Report from Dashboard
2. Verify all three sections show data from E001 and E002
3. Verify patterns detected in both engagements are highlighted

**Commit message:** Step 9 — cross-engagement report screen

---

### Step 10 — Word Report Download

**What it does:** Generates OPD Transformation Roadmap Word document. Primary client deliverable.

**New file:** api/services/report_generator.py (stub exists with NotImplementedError — implement it)

**ReportGeneratorService.generate(engagement_id):**
- Reads all findings, roadmap items by phase, accepted patterns, engagement context, accepted agent summaries
- Builds 8-section Word doc using python-docx
- Saves to 04_Agent_Outputs folder if derivable from documents_folder path
- Always returns file as browser download

**Eight sections:**
1. Executive Summary — blank placeholder
2. Engagement Overview — auto from engagement record
3. Operational Maturity Overview — signal domain summary table
4. Domain Analysis — findings grouped by domain
5. Root Cause Analysis — finding root_cause fields
6. Economic Impact Analysis — finding economic_impact fields
7. Improvement Opportunities — recommendations in priority order
8. Transformation Roadmap — RoadmapItems as three tables (Stabilize/Optimize/Scale)

**Backend endpoint:** GET /{engagement_id}/report/download in reporting.py (501 stub exists — implement it)
**Frontend:** Enable Download Report button in ReportPanel.jsx

**Test procedure:**
1. Click Download Report on E001 Meridian
2. Verify Word doc downloads and opens correctly
3. Verify all 8 sections contain real data from E001
4. Verify Section 1 is blank
5. Verify roadmap shows all 16 items grouped by phase

**Commit message:** Step 10 — Word report download

---

### New Domain Implementation (Before Checkpoint 3)

Reference doc: TOP_New_Domain_Expansion.docx in OneDrive\100_TunTech\Admin\

1. Run SQL INSERTs for P48-P60 in DB Browser — verify SELECT COUNT(*) FROM Patterns returns 58
2. Verify all 10 domains are in config.py DOMAINS list and api/utils/domains.py
3. Verify all 10 domains are in src/constants.js
4. Verify all extraction prompts reference all 10 domains
5. Verify valid_domains sets in document_processor.py and patterns.py have all 10 domains
6. Update Diagnostic Question Library (manual doc update)
7. Dry run 3 fictional client must include at least one AI Readiness signal

**Verification checklist:**
- SELECT COUNT(*) FROM Patterns returns 58
- SignalPanel domain dropdown shows all 10 domains
- FindingsPanel domain dropdown shows all 10 domains
- RoadmapPanel domain dropdown shows all 10 domains
- All extraction prompts include all 10 domains
- valid_domains in document_processor.py includes all 10 domains
- valid_domains in patterns.py detect endpoint includes all 10 domains

---

### Checkpoint 3 — Full Automated Diagnostic Run

**Goal:** Complete end-to-end run through browser with zero DB Browser intervention
and zero Claude.ai copy-pasting.

**Pre-run setup:**
- P48-P60 inserted in DB Browser
- Dry run 3 fictional client folder structure created on OneDrive
- 3-4 fictional interview transcripts written (CEO, Director of Delivery, VP Sales minimum)
- 1-2 fictional documents (financial summary + portfolio report)
- At least one transcript includes a clear AI Readiness signal

**The run (entirely through browser):**
1. Create engagement via New Engagement form
2. Set folder paths via Edit Settings
3. Process Files, review candidates, load (expect 25-35 signals)
4. Detect Patterns, review, load
5. Run all 5 agents in sequence, review and accept each
6. Parse Findings, assign contributing patterns, load (expect 5-8 findings)
7. Add roadmap items (manual entry — Synthesizer-to-Roadmap parser is post-Checkpoint 3)
8. Add knowledge promotions
9. Download Report, verify Word doc

**Pass criteria:**
- All 5 AgentRuns with accepted=1
- 5-8 OPDFindings created
- 10-16 RoadmapItems created
- Word doc downloads with all 8 sections populated
- Zero DB Browser operations required
- Zero Claude.ai copy-pasting
- Total API cost under $2.00
- Cross-engagement report shows new engagement alongside E001 and E002

---

## Known Issues

| Issue | Impact | Fix in |
|-------|--------|--------|
| Only first candidate file shows after multi-file processing | Medium | Step 8 Ext 1 Cleanup |
| Engagement header counts do not refresh after writes | Cosmetic — F5 fixes | After Checkpoint 3 |
| No progress feedback during long processing runs | UX only | After Checkpoint 3 |
| Candidate JSON files accumulate in candidates folder | Low for personal tool | After Checkpoint 3 |
| No reprocess button — must use DB Browser | Low — workaround exists | After Checkpoint 3 |
| No PDF support — only .txt files processed | Friction for real engagements | After Checkpoint 3 |

---

## Test Data

| Engagement | Firm | Signals | Patterns | Agents | Findings | Roadmap |
|-----------|------|---------|----------|--------|---------|---------|
| E001 | Meridian Consulting Group | 33 | 32 | 5 accepted | 7 | 16 |
| E002 | Apex Technology Solutions | 33 | 21 | 5 | 7 | 16 |

Use E001 for Step 8 Extension 2 testing — it has an accepted Synthesizer.
Use E001 and E002 together for cross-engagement report verification.
