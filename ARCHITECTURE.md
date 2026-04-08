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
│  12 tables          │   │   All calls via          │
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
| `claude.py` | All Claude API calls. All prompt constants. The AGENT_REGISTRY. |
| `document_processor.py` | File scanning, text extraction, signal candidate processing. |
| `report_generator.py` | Word document generation, chart generation, narrator assembly. |
| `case_packet.py` | Assembles the structured context document fed to every agent. |

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

**12 tables.** ID format: prefix + 3-digit zero-padded number.

```
Clients          C001
Engagements      E001   → FK: client_id → Clients
Signals          S001   → engagement_id
Interviews       (FK target for Signals.interview_id — currently nulled out)
Documents        engagement_id
Patterns         P01    (static reference library — P01–P60, never engagement-specific)
EngagementPatterns EP001 → engagement_id, pattern_id → Patterns
AgentRuns        AR001  → engagement_id
OPDFindings      F001   → engagement_id, pattern_id → Patterns
RoadmapItems     R001   → engagement_id, finding_id → OPDFindings
KnowledgePromotions KP001 → engagement_id
ProcessedFiles   PF001  → engagement_id
```

### Key column notes

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

**AgentRuns**
- `output_full`: complete Claude response, never modified after storage
- `consultant_correction`: appended to the agent's output when passed to downstream agents via `get_prior_output()`. Does not alter `output_full`.
- `accepted`: gate for the prerequisite chain

**ProcessedFiles**
- `file_hash`: MD5 hash of file content — duplicate detection is content-based, not name-based
- A renamed file with unchanged content is not reprocessed
- A file whose content changes produces a new hash and is reprocessed

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
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/cross-engagement` | Cross-engagement analytics views |
| GET | `/api/patterns/library` | Full P01–P60 pattern library |
| POST | `.../report/generate` | Generate Word report, save to disk |
| POST | `.../report/open-folder` | Open reports folder in Explorer |

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
    ├── ReportPanel.jsx        Generate report, open folder
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
| 2. Engagement Overview | Metadata + engagement narrative paragraph | Narrator + ProcessedFiles |
| 3. Operational Maturity Overview | Signal count table by domain | Signals table |
| 4. Domain Analysis | Per-domain findings with narrative | Narrator + OPDFindings |
| 5. Root Cause Analysis | Narrative prose | Narrator |
| 6. Economic Impact Analysis | Chart + 5-column summary table + narrative | OPDFindings + Narrator |
| 7. Future State | Metrics table + narrative | Narrator |
| 8. Transformation Roadmap | Priority Zero + overview + Gantt chart + 3 phase tables | RoadmapItems + Narrator |
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

See `BACKLOG.md` for full specs. Summary of major planned features:

- Findings enhancements: pattern enforcement, evidence summary, key quotes
- Roadmap enhancements: capability statements, economic linkage, dependency mapping
- Domain maturity scoring (1–5 per domain, computed at report time)
- Knowledge auto-suggest (detect-review-load for knowledge promotions)
- PowerPoint export
- Editable engagement info (post-creation)

### Phase 3 (future)
- PostgreSQL migration: swap `_get_connection()` and `?` → `%s` — no other changes required
- Multi-user auth: add `users` table, `user_id` on Engagements, `WHERE user_id = ?` in queries
- AWS hosting: RDS + S3 for files, update CORS and `VITE_API_URL`
