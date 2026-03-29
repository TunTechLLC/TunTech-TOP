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

**Phase 2 — Browser-based diagnostic tool**
Read PROGRESS.md for detailed current status, next steps, and test procedures.

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

**The two-step detect-then-load for pattern detection** — Detect returns results for human review.
Load saves them. Prevents bad Claude output from automatically entering the database.

**The Synthesizer prerequisite on finding creation** — Findings must always be informed by
complete agent analysis. The Synthesizer must be accepted before any finding can be created,
whether via Parse Findings (Step 8 Extension 2) or manual Add Finding form.

**interview_id is nulled out on all signal creates** — Foreign key constraint fix.
Empty string is not a valid foreign key value.

---

## Database

**TOP.db** at path from TOP_DB_PATH env var.
14 tables. ID format: prefix + 3-digit zero-padded number (C001, E001, S001, EP001, etc.)
ID generation: `api/utils/ids.py` using MAX+1 logic — reads config.py DB_PATH directly.

**Dry run data:**
- E001 — Meridian Consulting Group (33 signals, 32 patterns, 5 agent runs accepted, 7 findings, 16 roadmap items)
- E002 — Apex Technology Solutions (33 signals, 21 patterns, 5 agent runs, 7 findings, 16 roadmap items)

**Patterns:** P01–P60 after new domain inserts (58 total)
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
| Engagement header counts don't refresh after write operations | EngagementDetail.jsx | After Checkpoint 3 |
| Only first candidate file shows after multi-file processing | SignalPanel.jsx | Step 8 Ext 1 Cleanup |
| No reprocess button — must use DB Browser to clear ProcessedFiles | SignalPanel.jsx | After Checkpoint 3 |
| Candidate JSON files accumulate in candidates folder | document_processor.py | After Checkpoint 3 — archive to processed/ subfolder |
| Agent registry URL is under /api/engagements but is not engagement-specific | agents.py | Phase 3 cosmetic fix — do not move without updating api.js |
| process-files endpoint runs synchronously — long transcripts could timeout | signals.py | Phase 3 — background tasks |

---

## What Is Not Yet Built (Stubs Exist)

- **`api/services/report_generator.py`** — exists as a stub with NotImplementedError. Build in Step 10.
- **`GET /{engagement_id}/report/download`** — exists as a 501 stub in reporting.py. Build in Step 10.
- **Parse Findings button** — comment placeholder in FindingsPanel.jsx. Build in Step 8 Extension 2.
- **`POST /{engagement_id}/findings/parse-synthesizer`** — not yet built. Build in Step 8 Extension 2.
- **CrossEngagement.jsx** — placeholder route in App.jsx. Build in Step 9.

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
- python-docx — needed for Step 10 report generation
