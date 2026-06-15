# TOP — Scoped Code-Quality Audit (kickoff)

**Read-only. Plan mode. Make NO changes.** This is the agreed *scoped* version of a code-quality
audit — not the full exhaustive "every Low-severity smell" sweep (that would produce a long,
noise-heavy report for a single-user, explicitly-not-a-product tool; see CLAUDE.md "build for
maintainability and clarity, not scale or polish").

## Why scoped (the agreement)
A long remediation session (see `SIGNAL_LAYER_REMEDIATION_PLAN.md`) surfaced a recurring *class*
of real defect — silent failures, an architecture-rule violation, a data-scoping bug, missing
truncation guards, a skill-rule the code didn't enforce. The audit's job is to find the **rest of
that class systematically**, not to list naming nits. High signal, not exhaustiveness.

## Scope
**IN:** Critical / High / Medium findings; systemic patterns (note once + list locations);
the 5 locked architecture-rule violations; deliverable-quality skill-enforcement gaps.
**Low:** include ONLY where it's a genuine maintainability liability (e.g. a 2k-line file), not
every smell.
**OUT of audit target:** tests (but DO note missing coverage on critical paths), `migrations/`,
generated files, vendor/`node_modules`, the throwaway nothing-left-in `scripts/` (only
`valence_state.py` remains).

## Method (so later modules don't get a degraded review as context fills)
1. **PHASE 1 — MAP:** inventory main modules, responsibilities, data/control flow. Confirm before going deeper.
2. **PHASE 2 — AUDIT, module by module.** After each module, **APPEND** findings to
   `TOP_audit_findings.md` (don't hold them all in context). Consider fanning out **Explore**
   agents per module to keep each review fresh. Every finding: file + function + line numbers,
   category, severity, the *specific* problem, and a *precise* fix (e.g. "split into
   validate_signal(), map_pattern(), emit_finding()" — not "consider refactoring").
3. **PHASE 3 — DELIVERABLE:** `TOP_audit_findings.md` organized by severity (Critical first), then
   by module. Top: one-paragraph exec summary + finding count per category. Bottom: top 5 systemic
   issues to fix first, with why.

## Categories to evaluate (high-signal subset)
Error handling / silent failures (the proven recurring problem); async correctness (blocking
calls in async paths, unawaited coroutines); separation-of-concerns / layering; coupling &
cohesion; DRY across the 5 agents and the report code; function/file complexity
(single-responsibility, length, nesting); data access (SQL outside repositories, N+1,
unparameterized); dead code; prompt construction / token-context inefficiency; missing tests on
critical paths.

## The 5 locked architecture rules — flag any violation, with file:line
1. Async Claude client mandatory — no synchronous/blocking Claude calls.
2. `bulk_create()` must use a **sequential loop** — no concurrent/batched ID generation.
3. **All SQL in repositories** — none in routers/services. (One inline Claude call in
   `document_processor.py` was already moved to `claude.py` this remediation — verify no others.)
4. **All Claude API calls route through `claude.py`** — missing retries/timeouts is a sub-finding.
5. Domain logic in `api/utils/domains.py`; shared constants in `src/constants.js` — flag scattered
   hardcoded values.

## Likely hotspots (from the remediation reading — start here)
- `api/services/report_sections.py` (~2k lines), `api/services/report_generator.py`,
  `api/services/document_processor.py`, `api/services/claude.py` — size/complexity.
- Silent-failure sweep: `extract_downgrade_recommendations` / `suggest_display_label` (return
  default on failure — confirm acceptable), other `except ... : return/pass` swallows, frontend
  `catch {}` blocks in `src/`.
- Cross-check the **top-deliverable-quality skill** (confidence labeling, attribution verification,
  pattern-to-finding mapping, economic validation) against what the code actually enforces.

## To start (fresh session)
"Read TOP_AUDIT_PLAN.md and run the scoped audit in plan mode." Then proceed PHASE 1 → confirm
inventory → PHASE 2 (append per module) → PHASE 3.
