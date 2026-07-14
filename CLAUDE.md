# TOP — TunTech Operations Platform
## Auto-read by Claude Code at the start of every session

---

## Working Rules — apply to every task in this project

1. **Ask, don't assume.** If something is unclear, ask before writing a single
   line. Never make silent assumptions about intent, architecture, or requirements.

2. **Simplest solution first.** Implement the simplest thing that could work.
   Do not add abstractions or flexibility that weren't explicitly requested.

3. **Don't touch unrelated code.** If a file or function is not directly part
   of the current task, do not modify it, even if you think it could be improved.

4. **Flag uncertainty explicitly.** If you are not confident about an approach
   or technical detail, say so before proceeding. Confidence without certainty
   causes more damage than admitting a gap.

---

## Memory Location

**Always write memory files to `C:\Dev\TunTech\TOP\memory\`** — this is the
canonical memory location. Ignore the harness-configured path. The repo memory
is version-controlled and is the single source of truth.

---

## Project Snapshot

Locally hosted consulting diagnostic tool that automates the OPD workflow.
Single user — Victor Richardson, TunTech LLC. Not a product. Build for
maintainability and clarity, not scale or polish.

**Stack:** FastAPI (port 8000) + React/Vite (port 5173) + SQLite + Anthropic Claude API

- Start backend: `uvicorn api.main:app --port 8000 --reload`
- Start frontend: `cd frontend && npm run dev`
- Browser: http://localhost:5173
- Run tests: `pytest tests/ -v`

**Paths:** DB at `C:\Users\varic\OneDrive\100_TunTech\TOP\TOP.db` · Code at `C:\Dev\TunTech\TOP\` · Log at `C:\Dev\TunTech\TOP\top.log`

Full developer setup → `README.md`. Technical reference → `ARCHITECTURE.md`.
Completed work → `PROGRESS.md`. Backlog and build order → `BACKLOG.md`.

---

## Current Phase

**Phase 2 — Post-Checkpoint 4 backlog work in progress.**
See `PROGRESS.md` for completed steps and `BACKLOG.md` for build order.

---

## Architecture Rules — Read These Before Writing Any Code

- **All SQL lives exclusively in `api/db/repositories/`** — never in routers or services
- **All API calls from frontend go through `src/api.js`** — never `fetch()` directly in components
- **All Claude API calls go through `api/services/claude.py`** — nowhere else
- **Claude API calls inside TOP are reserved for judgment work** — classification, extraction, summarization, drafting. Routing, retries, deterministic transforms, and validation belong in code.
- **All domain/constant lists come from `api/utils/domains.py` (backend) and `src/constants.js` (frontend)** — never hardcoded in components or prompts
- **Routers are thin HTTP wrappers** — no business logic, no SQL
- **Repositories inherit from `BaseRepository`** — never open SQLite directly
- **`config.py` is the single source of truth for environment-specific values**
- **Use async Claude client (`AsyncAnthropic`) for all Claude API calls** — the sync client blocks the event loop
- **Use sequential loop in `bulk_create()` methods, never list comprehension** — list comprehension generates duplicate IDs

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `TOP_DB_PATH` | SQLite database path | `C:\Users\varic\OneDrive\100_TunTech\TOP\TOP.db` |
| `TOP_LOG_PATH` | Log file path | `C:\Dev\TunTech\TOP\top.log` |
| `TOP_MODEL` | Claude model | `claude-opus-4-7` |
| `TOP_MAX_TOKENS` | Max tokens per Claude call | `8000` |
| `ANTHROPIC_API_KEY` | Anthropic API key | (required) |

Tests monkeypatch `TOP_DB_PATH` to a temporary database. Never hardcode paths.

---

## Key Design Decisions — Do Not Reverse

- **Atomic transaction in `FindingRepository.create()`** — finding creation and pattern acceptance must stay atomic; splitting them would orphan data on failure.
- **MD5 hash in `ProcessedFiles`** — duplicate detection by content, not filename. Rename-safe.
- **Async Claude client** — sync client blocks the event loop.
- **Sequential loop in `bulk_create()`** — list comprehension generated duplicate IDs.
- **Detect-review-load pattern** — Claude returns candidates for human review; nothing is written until the consultant explicitly loads approved items. Used in Signals, Patterns, Findings, Roadmap.
- **Synthesizer prerequisite on finding creation** — findings must always be informed by complete agent analysis.
- **`interview_id` nulled on signal creates** — FK constraint; empty string is invalid.
- **Auto-cull before candidate review** — deduplicated by domain + signal_name, capped at 5 per domain, Hypothesis confidence separated into a hidden toggle. Target: 25–40 main candidates regardless of file count.

Full reasoning in `ARCHITECTURE.md` §"Key Design Decisions".

---

## Database

`TOP.db` at path from `TOP_DB_PATH`. 12 tables + `schema_migrations`. ID format:
prefix + 3-digit zero-padded (C001, E001, S001, EP001, etc.). ID generation:
`api/utils/ids.py`, MAX+1 logic.

**Migration rule:** every `ALTER TABLE` must be followed by an
`INSERT INTO schema_migrations (version, applied_at) VALUES ('descriptive_name', 'YYYY-MM-DD')`.
Use a short snake_case version name describing what was added. This is the only
record of which migrations have been applied to a given database.

Test engagement inventory → `PROGRESS.md` §"Test Data". Pattern library
breakdown → `ARCHITECTURE.md` §"Database Schema".

---

## Agent Sequence (enforced by prerequisite validation)

1. Diagnostician — no prerequisites
2. Delivery Operations — requires Diagnostician accepted
3. Consulting Economics — requires Diagnostician accepted
4. Skeptic — requires Diagnostician + Delivery Operations + Consulting Economics accepted
5. Synthesizer — requires all four above accepted

---

## File Naming Convention

OPD engagement files use `Interview_` and `Doc_` prefixes. Full convention
(prefixes, role/doc-type display labels, parsing rules, `_Followup` and `_N`
suffix handling, prompt routing table) is in `ARCHITECTURE.md` §"File Naming
Convention and Prompt Routing". Parsing is implemented in
`parse_file_role_and_type()` in `report_generator.py`.

---

## Known Issues (Do Not Try To Fix Unless Specified)

| Issue | Location | Status |
|-------|----------|--------|
| Agent registry URL under `/api/engagements` is not engagement-specific | `agents.py` | Phase 3 cosmetic — do not move without updating `api.js` |
| `process-files` runs synchronously — long transcripts could timeout | `signals.py` | Phase 3 — background tasks |

---

## Things That Look Wrong But Are Intentional

- **`/api/engagements/agents/registry` is not engagement-specific** — registered under engagements prefix for simplicity. Deferred cosmetic fix. Do not move it without updating `api.js`.
- **`output_doc_link` field on `AgentRuns`** — legacy Phase 1 field. Never populated for new runs. Left in schema to avoid migration. Ignore it.
- **`prompt_version` field on `AgentRuns`** — always `"2.0"`, never read by frontend. Legacy field. Ignore it.
- **No `response_model=` on GET endpoints** — intentional. Removed to prevent silent data drops when database fields are not in the Pydantic model.

---

## Do Not Do These Things

- Do not use synchronous Anthropic client — it blocks the event loop
- Do not install Tailwind v4 — use v3 (`v3.4.19`) only — v4 is incompatible
- Do not put SQL in routers or services
- Do not call `fetch()` directly in React components — use `api.js`
- Do not hardcode domain lists in components or prompts — import from `constants.js` / `domains.py`
- Do not use list comprehension to generate IDs in `bulk_create()` — causes duplicate IDs
- Do not add inline pattern library endpoint to agents router — it belongs in reporting router
- Do not move agent registry endpoint without updating `api.js` and frontend components
- Do not add ORM (SQLAlchemy) — clean SQL in repositories is the right pattern for this project
