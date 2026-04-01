# TOP — TunTech Operations Platform
## Auto-read by Claude Code at the start of every session

---

## What This Is

A locally hosted consulting diagnostic tool that automates the OPD (Operational Performance
Diagnostic) workflow. Single user — Victor Richardson, TunTech LLC. Not a product. Build for
maintainability and clarity, not scale or polish.

**Stack:** FastAPI backend (port 8000) + React/Vite frontend (port 5173) + SQLite + Anthropic Claude API

**Start backend:** `uvicorn api.main:app --port 8000 --reload` (from C:\Dev\TunTech\TOP)
**Start frontend:** `cd frontend && npm run dev`
**Browser:** http://localhost:5173
**Run tests:** `pytest tests/ -v`

**DB location:** `C:\Users\varic\OneDrive\100_TunTech\TOP\TOP.db`
**Code location:** `C:\Dev\TunTech\TOP\`
**Log location:** reads from TOP_LOG_PATH env var, defaults to `C:\Dev\TunTech\TOP\top.log`

---

## Current Phase

**Phase 2 — Post-Checkpoint 3 backlog work in progress**
Read PROGRESS.md for completed steps. Read BACKLOG.md for what to build next and in what order.

---

## Architecture Rules — Read These Before Writing Any Code

- **All SQL lives exclusively in `api/db/repositories/`** — never in routers or services
- **All API calls from frontend go through `src/api.js`** — never fetch() directly in components
- **All Claude API calls go through `api/services/claude.py`** — nowhere else
- **All domain/constant lists come from `api/utils/domains.py` (backend) and `src/constants.js` (frontend)** — never hardcoded in components or prompts
- **Routers are thin HTTP wrappers** — no business logic, no SQL
- **Repositories inherit from BaseRepository** — never open SQLite directly
- **`config.py` is the single source of truth for environment-specific values** — DB_PATH, LOG_PATH, MODEL, MAX_TOKENS all read from environment variables with local defaults
- **Use async Claude client (AsyncAnthropic) for all Claude API calls** — the synchronous client blocks the event loop and hangs indefinitely. We learned this the hard way.
- **Use sequential loop in bulk_create() methods, never list comprehension** — list comprehension generates duplicate IDs. We learned this the hard way.

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| TOP_DB_PATH | SQLite database path | C:\Users\varic\OneDrive\100_TunTech\TOP\TOP.db |
| TOP_LOG_PATH | Log file path | C:\Dev\TunTech\TOP\top.log |
| TOP_MODEL | Claude model to use | claude-sonnet-4-6 |
| TOP_MAX_TOKENS | Max tokens per Claude call | 8000 |
| ANTHROPIC_API_KEY | Anthropic API key | (required, no default) |

Tests monkeypatch TOP_DB_PATH to use a temporary database. Never hardcode paths.

---

## Key Design Decisions — Do Not Reverse These

**The atomic transaction in FindingRepository.create()** — Finding creation and pattern acceptance
must be atomic. If this were two separate calls and the second failed you would have orphaned data.

**The MD5 hash in ProcessedFiles** — Duplicate detection by content not filename. Rename-safe.
A file can be renamed without triggering reprocessing. If content changes, hash changes, reprocesses.

**The async Claude client** — Sync client blocks the event loop. Always use AsyncAnthropic.

**The sequential loop in bulk_create()** — List comprehension generated duplicate IDs.
Sequential loop with next_id() call per iteration is the correct pattern.

**The detect-review-load pattern** — Used across Signals, Patterns, Findings, and Roadmap.
Claude returns candidates for human review; nothing is written to the database until the
consultant explicitly loads approved items. Prevents bad Claude output from entering the
database automatically.

**The Synthesizer prerequisite on finding creation** — Findings must always be informed by
complete agent analysis. The Synthesizer must be accepted before any finding can be created,
whether via Parse Findings or the manual Add Finding form.

**interview_id is nulled out on all signal creates** — Foreign key constraint fix.
Empty string is not a valid foreign key value.

**Auto-cull before candidate review** — After extraction, candidates are deduplicated by
domain + signal_name, capped at 5 per domain, and Hypothesis-confidence signals are
separated into a hidden "show all" toggle. Target: 25–40 main candidates regardless of
input file count.

---

## Database

**TOP.db** at path from TOP_DB_PATH env var.
14 tables. ID format: prefix + 3-digit zero-padded number (C001, E001, S001, EP001, etc.)
ID generation: `api/utils/ids.py` using MAX+1 logic — reads config.py DB_PATH directly.

**Dry run data:**
- E001 — Meridian Consulting Group (33 signals, 32 patterns — modified by testing)
- E002 — Apex Technology Solutions (33 signals, 21 patterns, 5 agent runs, 7 findings, 16 roadmap items)
- E003 — Used for Report Narrator and Synthesizer-to-Roadmap validation (102 signals)

**Patterns:** P01–P60 (58 total)
- P01–P47: Original 7 domains
- P48–P51: AI Readiness
- P52–P56: Human Resources
- P57–P60: Finance and Commercial

---

## Agent Sequence (enforced by prerequisite validation)

1. Diagnostician — no prerequisites
2. Delivery Operations — requires Diagnostician accepted
3. Consulting Economics — requires Diagnostician accepted
4. Skeptic — requires Diagnostician + Delivery Operations + Consulting Economics accepted
5. Synthesizer — requires all four above accepted

---

## Known Issues (Do Not Try To Fix Unless Specified)

| Issue | Location | Fix Timing |
|-------|----------|------------|
| Engagement header counts don't refresh after write operations | EngagementDetail.jsx | Before Checkpoint 4 |
| No reprocess button — must use DB Browser to clear ProcessedFiles | signals.py + SignalPanel.jsx | Before Checkpoint 4 |
| Candidate JSON files accumulate in candidates folder | signals.py load-candidates | Before Checkpoint 4 — archive to processed/ subfolder |
| DELIVERY_DOCUMENT_EXTRACTION_PROMPT not yet written — falls back to SIGNAL_EXTRACTION_PROMPT | document_processor.py:182 | Before Checkpoint 4 |
| Agent registry URL is under /api/engagements but is not engagement-specific | agents.py | Phase 3 cosmetic fix — do not move without updating api.js |
| process-files endpoint runs synchronously — long transcripts could timeout | signals.py | Phase 3 — background tasks |

---

## What Is Not Yet Built

See BACKLOG.md for full specs and build order. Summary of items before Checkpoint 4:

- Word report template formatting cleanup (in progress)
- DELIVERY_DOCUMENT_EXTRACTION_PROMPT
- Reprocess button (frontend + backend)
- Candidate file archival after loading
- Engagement header count refresh
- Replace report browser download with save-and-show-path
- Improve PATTERN_DETECTION_PROMPT for new domain coverage

After Checkpoint 4: Knowledge auto-suggest, Findings Enhancements (pattern enforcement +
evidence summary + key quotes), Roadmap Enhancements (capability + economic linkage +
dependencies), Domain Maturity Scoring, PowerPoint export.

---

## Things That Look Wrong But Are Intentional

- **`/api/engagements/agents/registry` is not engagement-specific** — registered under engagements prefix for simplicity. Deferred cosmetic fix. Do not move it without updating api.js.
- **`output_doc_link` field on AgentRuns** — legacy Phase 1 field. Never populated for new runs. Left in schema to avoid migration. Ignore it.
- **`prompt_version` field on AgentRuns** — always "2.0", never read by frontend. Legacy field. Ignore it.
- **No response_model= on GET endpoints** — intentional. Removed to prevent silent data drops when database fields are not in the Pydantic model.

---

## Do Not Do These Things

- Do not use synchronous Anthropic client — it blocks the event loop
- Do not install Tailwind v4 — use v3 (v3.4.19) only — v4 is incompatible
- Do not put SQL in routers or services
- Do not call fetch() directly in React components — use api.js
- Do not hardcode domain lists in components or prompts — import from constants.js / domains.py
- Do not use list comprehension to generate IDs in bulk_create() — causes duplicate IDs
- Do not add inline pattern library endpoint to agents router — it belongs in reporting router
- Do not move agent registry endpoint without updating api.js and frontend components
- Do not add ORM (SQLAlchemy) — clean SQL in repositories is the right pattern for this project

---

## Dependencies

- Python 3.14
- Node 24.x / npm 11.x
- Tailwind CSS v3.4.19 (v4 incompatible)
- FastAPI, uvicorn, anthropic, pydantic — see requirements.txt
- React, react-router-dom, vite — see frontend/package.json
- python-docx 1.2.0 — used by report_generator.py for Word document generation
