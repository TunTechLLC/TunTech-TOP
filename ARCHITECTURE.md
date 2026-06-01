# TOP — Architecture Reference
## TunTech Operations Platform

*For new developers and architects. Read alongside CLAUDE.md, which contains rules
that must not be violated. This document describes what the system is and how it works;
CLAUDE.md describes what you must never do.*

---

## What This System Does

TOP automates the Operational Performance Diagnostic (OPD) consulting workflow.
A consultant loads client interview transcripts and documents, runs a five-agent
AI analysis pipeline, reviews and approves outputs at each stage, then generates
a structured Word report.

The defining constraint is **human review at every AI output boundary**. Nothing
Claude produces is persisted to the database automatically. The consultant explicitly
approves or rejects every signal, pattern, finding, and roadmap item before it enters
the system.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + Tailwind CSS v3 |
| Backend | FastAPI (Python 3.14) + Uvicorn |
| Database | SQLite (single file, path from env var) |
| AI | Anthropic Claude API (async client only) |
| Report generation | python-docx + matplotlib |
| File extraction | python-docx (Word), openpyxl (Excel), pdfplumber (PDF), python-pptx (PowerPoint) |

The frontend runs on port 5173. The backend runs on port 8000.
They communicate exclusively through the REST API — the frontend never touches
the database directly.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser (React)                   │
│  Dashboard → EngagementDetail → [8 panel tabs]      │
│  All API calls go through src/api.js — never fetch() │
└────────────────────┬────────────────────────────────┘
                     │ HTTP / REST
┌────────────────────▼────────────────────────────────┐
│                  FastAPI Backend                     │
│                                                      │
│  api/routers/          ← thin HTTP wrappers only    │
│  api/services/         ← business logic             │
│  api/db/repositories/  ← all SQL lives here         │
│  api/utils/            ← IDs, domains, formatting   │
│  config.py             ← env-var config (one place) │
└──────────┬──────────────────────────┬───────────────┘
           │                          │
┌──────────▼──────────┐   ┌──────────▼──────────────┐
│   SQLite (TOP.db)   │   │   Anthropic Claude API   │
│                     │   │   (AsyncAnthropic only)  │
│  18 entity tables   │   │   All calls via          │
│  DB_PATH env var    │   │   api/services/claude.py │
└─────────────────────┘   └─────────────────────────┘
```

---

## Layer Responsibilities

### `api/routers/`
HTTP endpoints only. No business logic. No SQL. A router function receives a request,
calls a service or repository, and returns a response. If you find business logic in a
router, it is a bug.

### `api/services/`
Business logic and external API calls.

| File | Responsibility |
|------|---------------|
| `claude.py` | All Claude API **call functions** (async). Detection, extraction, narrator, and QA call wrappers. |
| `prompts.py` | All prompt constants and the `AGENT_REGISTRY` (split out of `claude.py` in A1). |
| `document_processor.py` | File scanning, text extraction, file-type routing, signal candidate processing. |
| `case_packet.py` | Assembles the structured context document fed to every agent. |
| `report_generator.py` | Word document generation, chart generation, narrator assembly. Output is `_v1.docx`. |
| `report_sections.py` | Per-section report builders, including the domain maturity scorecard. |
| `narrator_auditor.py` | 12 mechanical checks on the narrator JSON before render (the "Trust Report"). |
| `editorial_auditor.py` | QA-3 Python pipeline — deterministic editorial checks on the rendered v1 text. |
| `qa_inputs.py` | Assembles v1 text + source / accepted-item blocks for the QA agents; holds the v1/v2 filename templates. |
| `qa_revision.py` | QA-4 — applies the Claude edit list to v1 in place, writes v2, reconciles unaddressed items. |

### `api/db/repositories/`
All SQL lives here and only here. Every repository inherits from `BaseRepository`,
which provides `_query()`, `_write()`, `_write_many()`, and `_write_transaction()`.
Never open a SQLite connection outside this layer.

### `api/utils/`

| File | Responsibility |
|------|---------------|
| `domains.py` | Single source of truth for all enumerated values (domains, confidences, priorities, phases, etc.). Import here — never hardcode. |
| `ids.py` | ID generation via MAX+1 logic. One function per entity type. |

### `config.py`
Single source of truth for environment-backed configuration. Every path and
model name comes from here. Tests monkeypatch env vars — never hardcode paths.

---

## Database Schema

**19 tables total:** 18 entity tables + `schema_migrations` tracking table. ID format: prefix + 3-digit zero-padded number.

The reporting layer uses 7 read-only SQL views queried exclusively through `ReportingRepository`: `vw_PatternFrequency`, `vw_PatternFrequencyByDomain`, `vw_AcceptedPatterns`, `vw_EconomicImpactByEngagement`, `vw_AgentRunLog`, `vw_OPDSummary`, `vw_EngagementSignals`. Views are not entity tables and have no ID generators.

```
Clients          C001
Engagements      E001   → FK: client_id → Clients
Signals          S001   → engagement_id
Interviews       (FK target for Signals.interview_id — currently nulled out)
Documents        engagement_id
Patterns         P01    (static reference library — P01–P60, never engagement-specific; P01–P45 cover the original 7 domains, P48–P51 AI Readiness, P52–P56 Human Resources, P57–P60 Finance and Commercial)
EngagementPatterns EP001 → engagement_id, pattern_id → Patterns
AgentRuns        AR001  → engagement_id
OPDFindings      F001   → engagement_id, pattern_id → Patterns
RoadmapItems     R001   → engagement_id, finding_id → OPDFindings
KnowledgePromotions KP001 → engagement_id
ProcessedFiles   PF001  → engagement_id
SignalCoverage   SC001  → engagement_id (signal coverage map used by the report)
SignalLibrary           (static reference library of reusable signal definitions — not engagement-specific)
QACoverageItems  QC001  → engagement_id (QA-1 Coverage Check detection candidates)
QACoherenceItems QH001  → engagement_id (QA-2 Coherence Check detection candidates)
QAEditorialItems QE001  → engagement_id (QA-3 Editorial Check detection candidates)
QARevisionEdits  QR001  → engagement_id (QA-4 Revision edit records — one row per edit)
schema_migrations         (version TEXT, applied_at TEXT — no ID prefix)
```

The 7 reporting views and the two static reference libraries (`Patterns` P01–P60,
`SignalLibrary`) are not engagement-scoped and have no per-engagement reset.

### Key column notes

**Engagements**
- `interviews_folder`, `documents_folder`, `candidates_folder`, `reports_folder`: folder paths set via the `PATCH .../settings` endpoint. Used by document processing and report generation. All nullable — not set at creation time.

**Signals**
- `signal_confidence`: `High` | `Medium` | `Hypothesis`
- `source`: `Interview` | `Document` | `Observation`
- `source_file`: filename the signal was extracted from (enables reprocessing)
- `notes`: verbatim quote + interpretation in format `"Quote: '...' — Interpretation: ..."`

**EngagementPatterns**
- `accepted`: `0` = detected, not yet accepted | `1` = consultant accepted
- Acceptance is atomic with finding creation (see Design Decisions)

**OPDFindings**
- `confidence`: `High` | `Medium` | `Low` (evidence quality of the finding)
- `economic_impact`: free text with inline notation — `CONFIRMED` (stated in source), `DERIVED` (arithmetic of confirmed inputs), or `INFERRED` (estimated)
- `priority`: `High` | `Medium` | `Low` — derived from economic impact type and severity
- `opd_section`: 1–9, which report section this finding belongs in
- `evidence_summary`: plain English summary of supporting evidence (no pattern codes)
- `key_quotes`: verbatim quotes from source materials supporting this finding
- `display_figure`: formatted dollar figure for the Executive Summary Key Findings box (e.g. `~$368K`)
- `display_label`: short label for the display figure (e.g. `Annual delivery overrun cost`)
- `figure_type`: `direct_exposure` | other — controls how multiple figures are combined in the Key Findings box
- `include_in_executive`: `0` | `1` — whether this finding's figure appears in the Executive Summary

**RoadmapItems**
- `capability`: plain English statement of the capability this initiative builds
- `addressing_finding_ids`: comma-separated finding IDs this initiative addresses (beyond the FK `finding_id`)
- `depends_on`: comma-separated item IDs that must complete before this item can start

**AgentRuns**
- `output_full`: complete Claude response, never modified after storage
- `consultant_correction`: appended to the agent's output when passed to downstream agents via `get_prior_output()`. Does not alter `output_full`.
- `accepted`: gate for the prerequisite chain

**ProcessedFiles**
- `file_hash`: MD5 hash of file content — duplicate detection is content-based, not name-based
- A renamed file with unchanged content is not reprocessed
- A file whose content changes produces a new hash and is reprocessed

### Test data inventory

| Engagement | Firm | Signals | Patterns | Agents | Findings | Roadmap |
|-----------|------|---------|----------|--------|---------|---------|
| E001 | Meridian Consulting Group | 33 | 32 | 5 accepted | 7 | 16 |
| E002 | Apex Technology Solutions | 33 | 21 | 5 accepted | 7 | 16 |
| E003 | (Fictional — Dry Run 3) | 102 | — | 5 accepted | Yes | Yes |
| E004 | (Fictional — Dry Run 4) | — | — | 5 accepted | Yes | Yes |

E001 and E002 are the primary reference engagements. E003 is the primary report
testing engagement — 102 signals, full agent sequence, findings and roadmap
generated. E004 is the Checkpoint 4 validation engagement — end-to-end dry run,
all features validated.

---

## The Five-Agent Pipeline

Agents run in a fixed sequence enforced by prerequisite validation. An agent cannot
run until all its prerequisites are accepted by the consultant.

```
1. Diagnostician       no prerequisites
        ↓
2. Delivery Operations  requires: Diagnostician accepted
3. Consulting Economics requires: Diagnostician accepted
        ↓
4. Skeptic              requires: Diagnostician + Delivery + Economics accepted
        ↓
5. Synthesizer          requires: all four above accepted
```

### What each agent produces

| Agent | Output |
|-------|--------|
| **Diagnostician** | Hypothesis assessment, pattern cluster analysis, primary failure sequence, confidence assessment, open questions for downstream agents |
| **Delivery Operations** | Delivery failure sequence, root cause, sales-to-delivery fracture points, staffing model assessment, improvement priorities |
| **Consulting Economics** | Economic baseline (CONFIRMED/DERIVED/INFERRED), margin decomposition, utilization analysis, economic impact by pattern, ROI case |
| **Skeptic** | Challenged claims, evidence gaps, downgrade recommendations, alternative explanations, overall confidence rating, **Contradiction Report** (Section 6 — structured C-codes for factual conflicts, retractions, role discrepancies, second-hand attributions) |
| **Synthesizer** | Integrated final diagnostic resolving all Skeptic challenges and C-codes; produces the source document for Parse Findings and Parse Roadmap |

### How agent context is assembled

Each agent receives two inputs:

1. **Case packet** — assembled by `CasePacketService.assemble()`:
   - Section 1: Engagement context (firm, hypothesis, stated problem)
   - Section 2: All accepted signals with domain, confidence, source, source_file, and verbatim notes
   - Section 3: Accepted and detected patterns

2. **Prior agent outputs** — each required prior agent's `output_full` plus any
   `consultant_correction` appended as a block. Assembled by `get_prior_output()` per agent.

The two are joined and sent as the user message. The agent's prompt is the system message.

### Consultant corrections

After accepting an agent run, a consultant can add a correction note in the UI.
The correction is stored in `consultant_correction` on the AgentRun record and
appended to that agent's output when it is passed as prior context to downstream
agents. The original `output_full` is never modified.

---

## The Detect-Review-Load Pattern

The core pattern used for signals, patterns, findings, and roadmap items.
**Claude never writes directly to the database.** The consultant reviews every
AI output before it is persisted.

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  DETECT  │ →  │  REVIEW  │ →  │   LOAD   │
│          │    │          │    │          │
│ Claude   │    │ Consultant│    │ Approved │
│ produces │    │ approves/ │    │ items    │
│ candidates    │ rejects   │    │ written  │
│ (not yet │    │ each item │    │ to DB    │
│ in DB)   │    │           │    │          │
└──────────┘    └──────────┘    └──────────┘
```

### Signals — full example

**DETECT**
1. Consultant clicks "Process Files" in SignalPanel
2. `POST /api/engagements/{id}/signals/process-files`
3. `scan_folder()` finds unprocessed files (`.txt`, `.docx`, `.xlsx`, `.pdf`, `.pptx`) in the engagement's folders
4. MD5 hash check against ProcessedFiles — already-processed files are skipped
5. Each new file is sent to Claude with the appropriate extraction prompt
6. Claude returns JSON candidates (signal_name, domain, confidence, notes, etc.)
7. Candidates are deduplicated across files, capped at 5 per domain, hypothesis signals separated
8. Merged candidates written to `candidates/` folder as a JSON file
9. Files marked as processed in ProcessedFiles

**REVIEW**
10. Frontend reads candidate JSON via `GET .../signals/read-candidates`
11. Candidate cards displayed — main candidates visible, hypothesis signals collapsed
12. Consultant checks/unchecks each candidate

**LOAD**
13. Consultant clicks "Load Approved"
14. `POST .../signals/load-candidates` with the approved subset
15. Each approved signal inserted via `SignalRepository.create()` — sequential loop, never list comprehension
16. Candidate JSON archived to `candidates/processed/`

**REPROCESS** (if needed)
- `DELETE .../signals/processed-files/{file_hash}` atomically deletes signals from that file and removes the ProcessedFiles record
- Next "Process Files" run re-extracts the file as new

### The same pattern applied elsewhere

| Domain | Detect endpoint | Load endpoint |
|--------|----------------|---------------|
| Patterns | `POST .../patterns/detect` | `POST .../patterns/load` |
| Findings | `POST .../findings/parse-synthesizer` | `POST .../findings` |
| Roadmap | `POST .../roadmap/parse-synthesizer` | `POST .../roadmap` |

---

## API Endpoint Inventory

### Engagements
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/engagements/` | List all with summary counts |
| GET | `/api/engagements/{id}` | Single engagement detail |
| POST | `/api/engagements/` | Create (client + engagement atomically) |
| PATCH | `/api/engagements/{id}/settings` | Update folder paths |

### Signals
| Method | Path | Purpose |
|--------|------|---------|
| GET | `.../signals` | All signals grouped by domain |
| GET | `.../signals/summary` | Domain/confidence counts |
| POST | `.../signals` | Add single signal manually |
| POST | `.../signals/process-files` | Scan folders, extract via Claude |
| GET | `.../signals/read-candidates` | Read candidate JSON for review |
| POST | `.../signals/load-candidates` | Persist approved candidates |
| GET | `.../signals/processed-files` | List processed files |
| DELETE | `.../signals/processed-files/{hash}` | Delete signals + clear for reprocess |

### Patterns
| Method | Path | Purpose |
|--------|------|---------|
| GET | `.../patterns` | All detected patterns |
| POST | `.../patterns/detect` | Run Claude pattern detection |
| POST | `.../patterns/load` | Persist validated results |
| PATCH | `.../patterns/{ep_id}` | Update confidence or economic estimate |

### Agents
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/engagements/agents/registry` | Full agent registry |
| GET | `.../agents` | Agent runs for engagement |
| POST | `.../agents/{name}/run` | Execute agent (validates prerequisites) |
| PATCH | `.../agents/{run_id}/accept` | Accept run, unlock next agent |
| PATCH | `.../agents/{run_id}/reject` | Reject, allow re-run |
| PATCH | `.../agents/{run_id}/correction` | Save/clear consultant correction |

### Findings
| Method | Path | Purpose |
|--------|------|---------|
| GET | `.../findings` | All findings in priority order |
| POST | `.../findings` | Create + accept contributing patterns (atomic) |
| PATCH | `.../findings/{id}` | Update finding fields |
| POST | `.../findings/parse-synthesizer` | Extract candidates from Synthesizer output |

### Roadmap
| Method | Path | Purpose |
|--------|------|---------|
| GET | `.../roadmap` | All items ordered by phase and priority |
| GET | `.../roadmap/{phase}` | Items for Stabilize / Optimize / Scale |
| POST | `.../roadmap/parse-synthesizer` | Extract candidates from Synthesizer output |
| POST | `.../roadmap` | Create item |
| PATCH | `.../roadmap/{item_id}` | Update item |
| DELETE | `.../roadmap/{item_id}` | Delete item |

### Knowledge
| Method | Path | Purpose |
|--------|------|---------|
| GET | `.../knowledge` | List knowledge promotions |
| POST | `.../knowledge` | Create promotion |

### Reporting
The reporting router is mounted at `/api` (not `/api/engagements`). Engagement-specific report endpoints use `/api/{id}/report/...`.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/cross-engagement` | Cross-engagement analytics views (7 views as structured JSON) |
| GET | `/api/patterns/library` | Full P01–P60 pattern library |
| GET | `/api/{id}/report/download` | Generate Word report and stream to browser |
| POST | `/api/{id}/report/generate` | Generate Word report, save to disk, return file path |
| POST | `/api/{id}/report/open-folder` | Open reports folder in Windows Explorer |
| GET | `/api/health` | Health check |

### Post-Assembly QA Stage
Routers mounted under `/api/engagements`. Coverage / Coherence / Editorial share the
same CRUD shape; only Coverage is expanded below.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `.../qa-status` | Whether the v1 / v2 roadmap docs exist (QA tab gate) |
| POST | `.../qa-coverage/run` | Run QA-1 Coverage Check (Opus, streamed) |
| GET | `.../qa-coverage` | List coverage items |
| PATCH | `.../qa-coverage/{id}` | Set an item's status |
| POST | `.../qa-coverage/confirm-tier-1` | Batch-accept Tier 1 items |
| … | `.../qa-coherence/*`, `.../qa-editorial/*` | QA-2 / QA-3 — same shape as qa-coverage |
| POST | `.../qa-revision/run` | Run QA-4 Revision — apply accepted items, write v2 |
| GET | `.../qa-revision` | List revision edits (backs the v1↔v2 comparison) |
| GET | `.../qa-revision/v1` | Download the saved v1 .docx (no regeneration) |
| GET | `.../qa-revision/v2` | Download the revised v2 .docx |
| PATCH | `.../qa-revision/{id}` | Mark a flagged/manual edit handled |

---

## Frontend Structure

All API calls go through `src/api.js`. Components never call `fetch()` directly.
Domain/constant lists come from `src/constants.js` — never hardcoded in components.

```
src/
├── api.js              All API calls — one function per endpoint
├── constants.js        DOMAINS, CONFIDENCE_LEVELS, FINDING_CONFIDENCES, etc.
└── components/
    ├── Dashboard.jsx          Engagement list, navigate to detail
    ├── NewEngagement.jsx      Create engagement form
    ├── EngagementDetail.jsx   Main view — tabbed panel container
    ├── SignalPanel.jsx        Signals: process files, review candidates, load, reprocess
    ├── PatternPanel.jsx       Patterns: detect, review, load, update
    ├── AgentPanel.jsx         Run agents, accept/reject, add corrections
    ├── FindingsPanel.jsx      Parse findings, create/edit manually
    ├── RoadmapPanel.jsx       Parse roadmap, manage items by phase
    ├── KnowledgePanel.jsx     Knowledge promotions
    ├── ReportPanel.jsx        Generate report, open folder, Narrator Trust Report
    ├── QAPanel.jsx            Integrated QA tab — v1 gate, 3 detection sections, verify-after revision
    ├── QACoveragePanel.jsx    QA-1 Coverage Check (wrapped by QAPanel)
    ├── QACoherencePanel.jsx   QA-2 Coherence Check (wrapped by QAPanel)
    ├── QAEditorialPanel.jsx   QA-3 Editorial Check (wrapped by QAPanel)
    └── CrossEngagement.jsx    Cross-engagement analytics
```

---

## File Naming Convention and Prompt Routing

Files dropped into an engagement folder are routed to a specialized extraction prompt
based on their filename prefix and stem. Using the wrong name means the wrong prompt
runs — client feedback processed as a generic signal, financials missing ratio analysis, etc.

### Supported file formats

`scan_folder()` accepts `.txt`, `.docx`, `.xlsx`, `.pdf`, and `.pptx`. All other
extensions are silently skipped. Text extraction is handled by
`extract_text_from_file()` in `document_processor.py`:

| Extension | Library | Notes |
|-----------|---------|-------|
| `.txt` | built-in | UTF-8 read |
| `.docx` | python-docx | Paragraphs + table cells in document order |
| `.xlsx` | openpyxl | Sheet-by-sheet; rows as tab-separated values; formula cells return cached values |
| `.pdf` | pdfplumber | Text-based PDFs only; scanned/image pages are skipped with a DEBUG log; file skipped if no pages yield text |
| `.pptx` | python-pptx | Text frames + speaker notes per slide |

Libraries are imported lazily inside `extract_text_from_file()` — the app starts
even if one is missing; that format raises `ValueError` and the file is skipped.

### Interview files — prefix `Interview_`

All interview files route to `SIGNAL_EXTRACTION_PROMPT` regardless of stem.
Any supported extension may be used (`.txt`, `.docx`, `.pdf`, etc.).

```
Interview_CEO.txt
Interview_DirectorDelivery.docx
Interview_VPSales.txt
Interview_FinanceLead.txt
Interview_SeniorConsultant.txt
Interview_Operations.txt
Interview_CEO_Followup.txt    ← same role, deduped in report
Interview_CEO_2.txt           ← second session, deduped in report
```

### Document files — prefix `Doc_`

Stem (after `Doc_`) determines the extraction prompt.
Any supported extension may be used (`.txt`, `.xlsx`, `.pdf`, `.pptx`, etc.).

| Filename stem | Prompt |
|---|---|
| `Doc_Financial*` | `FINANCIAL_EXTRACTION_PROMPT` |
| `Doc_Portfolio*` | `PORTFOLIO_EXTRACTION_PROMPT` |
| `Doc_SOW*` | `SOW_EXTRACTION_PROMPT` |
| `Doc_StatusReport*` | `STATUS_EXTRACTION_PROMPT` |
| `Doc_Resource*` | `RESOURCE_EXTRACTION_PROMPT` |
| `Doc_Delivery*` | `DELIVERY_DOCUMENT_EXTRACTION_PROMPT` |
| `Doc_ClientFeedback*` | `SIGNAL_EXTRACTION_PROMPT` (generic) |
| `Doc_Other*` | `SIGNAL_EXTRACTION_PROMPT` (generic) |

Routing is implemented in `get_file_type()` in `api/services/document_processor.py`.
Stem matching is case-insensitive substring — `Doc_StatusReport_Q1.xlsx` matches `status`.

### Parsing rules

Implemented in `parse_file_role_and_type()` in `report_generator.py`. These rules govern
how the narrator labels participants and documents in the Engagement Overview section.

- `Interview_` prefix → interview; role derived from the stem after the prefix
- `Doc_` prefix → document; type derived from the stem after the prefix
- No convention prefix → falls back to the `file_type` field from `ProcessedFiles`,
  then tries stem matching. Preserves backward compat for E001/E002/E003.
- `_Followup` suffix → role is recognised but omitted from the narrator's role list
- `_2` (or any `_N`) suffix → stripped before matching; deduplication handles
  repeated sessions
- Unrecognised stem → raw stem passed through (underscores → spaces). Never uses
  "team member" or any other generic placeholder.

### Role display labels

Used by the narrator for the Engagement Overview paragraph. Stem substring (case-insensitive)
matches in the order listed.

| Stem substring | Display label |
|---|---|
| `CEO` / `chief exec` | CEO |
| `DirectorDelivery` / `Director` | Director of Delivery *(Director alone maps to Delivery)* |
| `VPSales` / `Sales` | VP of Sales |
| `FinanceLead` / `Finance` | Finance Lead |
| `SeniorConsultant` / `Consultant` / `PM` | Senior Consultant and Project Manager |
| `Operations` / `Admin` | Director of Operations |

### Document type display labels

Used by the narrator for the Engagement Overview paragraph. Stem substring (case-insensitive).

| Stem substring | Display label |
|---|---|
| `Financial` | financial performance documentation |
| `Portfolio` | project portfolio summary |
| `SOW` | Statement of Work |
| `StatusReport` / `Status` | project status report |
| `ClientFeedback` / `Feedback` | client satisfaction data |
| `Other` | supporting documentation |

### Legacy files (E001–E003)

Files named `{engagement_id}_{type}_{desc}.txt` are still supported via the legacy
path in `get_file_type()`. New engagements should use the `Interview_` / `Doc_` convention.

---

## Report Generation

The Word report is generated by `ReportGeneratorService` in `api/services/report_generator.py`.

### Nine-section structure

| Section | Content | Source |
|---------|---------|--------|
| Executive Briefing | One-page CEO teaser (headline, 3 problems, 3 numbers, immediate actions) | Narrator (validated against DB) |
| 1. Executive Summary | Opening + Key Findings box + 3 narrative paragraphs | Narrator |
| How to Read | Prefatory page with role-based reading guide | Static template + dynamic domain names |
| 2. Engagement Overview | Metadata + engagement narrative + domain maturity scorecard (1–5, traffic-light) | Narrator + ProcessedFiles |
| 3. Operational Maturity Overview | Signal count table by domain | Signals table |
| 4. Domain Analysis | Per-domain findings with narrative | Narrator + OPDFindings |
| 5. Root Cause Analysis | Narrative prose | Narrator |
| 6. Economic Impact Analysis | Chart + 5-column summary table + narrative | OPDFindings + Narrator |
| 7. Future State | Metrics table + narrative | Narrator |
| 8. Transformation Roadmap | Gantt chart + 8.1 Priority Zero + 8.2 Overview + 8.3–8.5 Phase tables (Stabilize / Optimize / Scale) + 8.6 Initiative Dependencies + 8.7 Key Risks | RoadmapItems + Narrator |
| 9. What Happens Next | Immediate actions + completion criteria | Narrator |

### Economic figure notation

Every dollar figure in `economic_impact` carries one of three labels:
- `CONFIRMED` — figure stated explicitly in a source document
- `DERIVED` — arithmetic result of confirmed inputs; result never stated in any source
- `INFERRED` — estimate with at least one non-document input

Parsed by `_parse_economic_figures()` which returns a 3-tuple `(confirmed, derived, inferred)`.
The Section 6 table has five columns: Finding | Confirmed Exposure | Derived Exposure | Annual Drag (Inferred) | Recovery Potential.

### Narrator
The Narrator is a separate Claude call (`generate_report_narrative()`) that produces a large JSON object with all prose sections. It runs after all five agents are accepted and findings/roadmap are loaded. Its output drives the narrative content of the report. It does not write to the database — it is called at report generation time and its output is used immediately.

---

## Post-Assembly QA Stage

After the v1 report is generated, an optional QA stage reviews and revises it. It
applies the same detect-review discipline as the rest of TOP, but on the *rendered
document* rather than on signals/patterns.

### Versioning
The Report Generator writes `OPD_Transformation_Roadmap_<id>_v1.docx`; QA-4 writes
`_v2.docx` alongside it. v1 is never modified, so the v1↔v2 diff is exactly the QA
contribution. `qa_inputs.py` holds both filename templates.

### The agents
- **QA-1 Coverage** (`qa_coverage`) — compares the rendered v1 against the source
  documents; flags source items dropped from the roadmap.
- **QA-2 Coherence** (`qa_coherence`) — standalone read of v1 for contradictions, math
  errors, mislabels, and priority mismatches (does *not* consult source documents).
- **QA-3 Editorial** (`qa_editorial`) — split pipeline: a deterministic Python checker
  (`editorial_auditor.py` — leaked signal codes, undefined acronyms, terminology drift)
  plus a narrow Claude voice/audience check.
- **QA-4 Revision** (`qa_revision`) — one Opus call returns a structured edit list;
  `qa_revision.py` applies each edit to v1 in place (tolerant matcher: exact → context →
  fuzzy/flag; never silently corrupts), writes v2, and reconciles every accepted item
  (any with no edit is recorded `unaddressed` so nothing is silently dropped).

Detection agents and the revision use Opus (`model="claude-opus-4-7"` passed per-call;
global `TOP_MODEL` stays Sonnet) and stream responses. Each detection item carries a
`tier` (1 obvious / 2 judgment / 3 low-confidence) driving the tiered review UI.

### Narrator Output Auditor (Session 1)
`narrator_auditor.py` runs 12 mechanical Python checks on the narrator JSON *before* the
Word render (during report generation), surfaced as the "Trust Report" in `ReportPanel`.
It is distinct from the QA stage: it checks pre-render JSON; the QA agents check the
rendered document.

### Frontend
A single **QA** tab (`QAPanel.jsx`) gates on a v1 document existing, wraps the three
detection panels as collapsible sections, and presents the QA-4 revision as a
verify-after edit-list comparison (grouped by outcome) with v1/v2 downloads.

---

## Key Design Decisions

These decisions exist for specific reasons. Reversing them has consequences.

### Async Claude client only
`AsyncAnthropic` is used for all Claude API calls. The synchronous client blocks the
event loop, causing the FastAPI server to hang indefinitely on any Claude call.

### Sequential loop in bulk_create()
`bulk_create()` methods use a sequential loop, not list comprehension.
List comprehension generates all IDs before any inserts, producing duplicate IDs
when `next_id()` reads MAX() twice before any row is written.

### Atomic transaction in FindingRepository.create()
Finding creation and pattern acceptance are one transaction. If they were separate
calls, a failure after the finding was created but before patterns were accepted
would leave the finding without any supporting evidence — orphaned data.

### MD5 hash in ProcessedFiles
Duplicate detection is content-based, not name-based. Renaming a file does not
trigger reprocessing. Changing file content (new interview session) does.

### Synthesizer prerequisite on findings
Findings can only be created after the Synthesizer is accepted. Findings must be
informed by the complete multi-agent analysis — not a shortcut past the pipeline.

### interview_id nulled out on signal creates
`interview_id` is a foreign key. Empty string is not a valid FK value in SQLite
with foreign keys enabled. It is set to NULL, not empty string.

### No response_model= on GET endpoints
Removed to prevent silent data drops. Pydantic response models silently drop
database fields that are not declared in the model, masking schema evolution.

### All domain/constant lists from a single source
`api/utils/domains.py` (backend) and `src/constants.js` (frontend) are the only
places where domain names, confidence levels, priorities, etc. are defined.
They must be kept in sync. Never hardcode these in components, prompts, or SQL.

---

## Configuration Reference

All values in `config.py`, all overridable via environment variable.

| Variable | Default | Purpose |
|----------|---------|---------|
| `TOP_DB_PATH` | `C:\Users\varic\OneDrive\100_TunTech\TOP\TOP.db` | SQLite database |
| `TOP_LOG_PATH` | `C:\Dev\TunTech\TOP\top.log` | Log file (rotating, 5MB) |
| `TOP_MODEL` | `claude-sonnet-4-6` | Claude model for all calls |
| `TOP_MAX_TOKENS` | `8000` | Max tokens per Claude call |
| `ANTHROPIC_API_KEY` | (required, no default) | Anthropic API key |

Tests monkeypatch `TOP_DB_PATH` to a temporary file. Never hardcode paths.

---

## What Is Not Yet Built

See `PROGRESS.md` for completed work and `BACKLOG.md` for remaining specs.

**Shipped since this list was first written:** the Findings and Roadmap enhancements,
Domain Maturity Scoring, the A1–A5 accuracy/review series, the Narrator Output Auditor
(Session 1), and the full **Post-Assembly QA Stage** (QA-1 through QA-5).

**Remaining:**

- Checkpoint 5 — Dry Run 5 (end-to-end validation of the QA Stage)
- Editable engagement info (post-creation)
- PowerPoint export
- Standardize economic output generation
- Structured file metadata capture at processing time
- Knowledge auto-suggest (detect-review-load for knowledge promotions)

### Phase 3 (future)
- PostgreSQL migration: swap `_get_connection()` and `?` → `%s` — no other changes required
- Multi-user auth: add `users` table, `user_id` on Engagements, `WHERE user_id = ?` in queries
- AWS hosting: RDS + S3 for files, update CORS and `VITE_API_URL`
