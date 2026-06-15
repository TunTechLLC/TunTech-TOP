# TOP — Code-Quality Remediation Plan (from the scoped audit)

**Created:** 2026-06-15. **Source:** `TOP_audit_findings.md` (scoped audit per `TOP_AUDIT_PLAN.md`).
**Scope of THIS plan:** the **top 5 fix-first systemic issues** only — the highest-leverage subset, not all
47 findings. The remaining Medium/Low items stay catalogued in `TOP_audit_findings.md` as a punch-list.

**Ordering = fix-first priority** (systemic reach × threat to data integrity / deliverable correctness),
matching the findings doc. This is *not* strict severity — see Item 3.

**Working method (inherited from `SIGNAL_LAYER_REMEDIATION_PLAN.md`, load-bearing):** evidence first; a
**pre-registered, reversible test that runs BEFORE the production change**; tag each claim
**[VERIFIED] / [INFERRED] / [UNCHECKED]**; commit + push each item separately. Line numbers below are
approximate (`~`) — confirm exact lines at implementation time before editing.

---

## Item 1 — Close the remaining silent-failure swallows  *(systemic; the proven defect class)*

**Problem [VERIFIED pattern; specific line numbers INFERRED from audit agents]:** Broad
`except Exception → return []/None/default` still exists and can convert a transient/parse failure into a
confident-but-empty result — the exact mechanism that previously lost a whole CTO interview. Sites:
- `claude.py:~546-575` `extract_downgrade_recommendations` → returns `[]` on any exception (drops Skeptic downgrades silently).
- `claude.py:~595-630` `suggest_display_label` → returns `None` on any exception.
- `claude.py:~369-374` `generate_report_narrative` finding-id parse → `except Exception: fids = []`.
- `document_processor.py:~323-324,331-332` `_build_library_block` → `except … pass` on malformed library JSON.
- `report_sections.py:~1304-1318,1374-1386` `key_quotes` parse → silent `[]`.
- `qa_revision.py:~231-234` `insert_paragraph_after` → `except Exception: pass` on style set.
- Frontend: `PatternPanel.jsx:42` `.catch(() => {})`; `api.js:~5,13` `handle()` swallows non-JSON error bodies.

**Fix:** For each: narrow the catch to the *expected* parse exception (`json.JSONDecodeError`/`ValueError`);
let API/timeout exceptions propagate (caught by the global handler → 500); `logger.warning(...context...)`
before any *legitimately*-empty return. Frontend: surface the error into existing error state (and use the
shared banner from Item-adjacent cleanup), never an empty `catch`.

**Test (pre-registered):** unit-feed a malformed/empty response into each helper → assert it **raises or logs
+ returns a sentinel the caller distinguishes**, never a silent default; assert a *legitimately* empty
response still returns `[]`/`None` cleanly. Frontend: mock a failing fetch → assert an error renders.

**Side effects:** some paths that used to 200-with-empty will now 500 — that is the intended behavior
(loud, not silent). Confirm each caller renders the error.

**Commit message:** `Audit-fix 1: narrow silent except-swallows in claude/doc-processor/report/qa + frontend`

---

## Item 2 — Enforce deliverable-quality skill rules in code, not just prompts  *(highest leverage)*

**Problem [enforcement levels VERIFIED via cross-check; one sub-claim UNCHECKED, see below]:** Three
load-bearing `top-deliverable-quality` rules are enforced only by prompt instruction (SOFT) or not at all
(NONE), so a single model slip ships a bad client deliverable with no backstop:
- **Computed figure labeled CONFIRMED** — SOFT (`ECONOMICS_PROMPT` bright line ~97-99 only). The whole
  D-label remediation was about this; there is still no deterministic check.
- **Attribution: named person/title must trace to a source** — NONE.
- **Positive (Preserve) finding must carry NO pattern** — the Strength-signal half is HARD
  (`findings.py:~328-338`) but nothing rejects a positive finding that *also* has `contributing_ep_ids`.
  **[UNCHECKED]** — confirm the exact field/validation path in `findings.py` before coding.

**Fix:**
- `narrator_auditor.py`: add `check_confirmed_not_computed` — for each economic figure labeled CONFIRMED,
  scan surrounding prose for derivation markers (`×`/`*`/`+`/"per"/"times"/"calculated"/"derived from"/a
  `$N op N` shape) → FAIL with figure+label. Mirrors the prompt bright line.
- `narrator_auditor.py`: add `check_attribution_traces_to_source` — extract person+role mentions; FAIL if a
  person name appears in no `ctx.processed_files` text (heuristic, catches the E004 "wrong CFO" class).
- `findings.py` create/parse: `if valence == 'positive' and contributing_ep_ids: raise HTTPException(...)`.

**Test (pre-registered):** craft an input where a computed figure is labeled CONFIRMED → assert the new
check FAILs; a correctly-ESTIMATED one → PASS. A finding naming a person absent from sources → FAIL. A
positive finding with a pattern id → 4xx; without → OK. Run on a known-good E007 deliverable → no new
false-positives (tune markers if so).

**Side effects:** could surface pre-existing borderline cases in old engagements — expected; review-only,
forward-applied (auditor runs on new report generations).

**Commit message:** `Audit-fix 2: deterministic skill-rule checks (confirmed≠computed, attribution, positive-no-pattern)`

> **Overlap note:** the cross-document-contradiction gap (audit Medium) is the same north star as the
> BACKLOG **Decision Surfacing** feature — keep that there; this item covers only the three HIGH gaps.

---

## Item 3 — Delete the dead `signal.py` `bulk_create` method  *(most severe single defect; dormant)*

> **✅ DONE 2026-06-15 (`4bb9438`).** Method removed (37 lines); no orphaned imports; 148 tests pass.
> Recorded in `PROGRESS.md`.

**Problem [VERIFIED in source + zero callers/tests]:** `signal.py:127-161` builds the full `params` list
calling `next_signal_id()` for every row **before** the single `_write_many()` commit → every row reads the
same `MAX+1` → **duplicate IDs**. Its docstring (lines 134-137) claims the opposite ("commits each ID before
the next call reads the new MAX"). It is **completely dead**: grep finds **no caller** (the live load path
`load_candidates` uses per-signal `repo.create()`) and **no test** (every `bulk_create` test targets
pattern/qa_* repos). The "Tally CSV import" the docstring cites **does not exist** anywhere in the codebase,
backlog, or plans. *Ranked 3rd despite being the most severe single defect because it is dormant — strict
severity would rank it 1st.*

**Fix — DELETE the method** (not rewrite). Removing a broken, untested, uncalled method is strictly better
than fixing a bug in code that never runs: it eliminates the landmine and the misleading docstring, and
removes ~35 lines. No orphaned imports (`INSERT_SIGNAL`, `next_signal_id`, `date` all still used by
`create()`). `pattern.py:104-113` remains the reference pattern (plus four QA repos), so nothing is lost.
*If* Tally CSV import is ever built, re-add a correct ~10-line sequential loop then — cheaper and safer than
carrying a fixed-but-unexercised method now.

**Test (pre-registered):** confirm the deletion is safe before/after — `pytest tests/ -v` stays green (148
baseline), and a fresh `grep -rn "\.bulk_create" api/` shows no signal caller. No new test needed (deleting,
not adding behavior). *(If the consultant instead wants to KEEP it for an imminent CSV-import feature, fall
back to: sequential loop mirroring `pattern.py` + a regression test asserting 3 distinct IDs.)*

**Side effects:** none — method is uncalled and untested.

**Commit message:** `Audit-fix 3: remove dead SignalRepository.bulk_create (broken Rule-2 landmine, no callers)`

---

## Item 4 — One Claude I/O policy: input-size guard + retries  *(pairs with Item 1)*

**Problem [`max_retries=0` VERIFIED via agent read of `claude.py:~25`; truncation absence is structural]:**
No `MAX_INPUT_CHARS` guard precedes any Claude call, so an oversized transcript / case packet can silently
overflow the context window (lost signals or a failed call); and the shared `AsyncAnthropic` runs
`max_retries=0`, so transient 429/5xx/network blips become hard failures — which the Item-1 swallows then
hide. Affected callers: `document_processor` extraction (`~617-660`), `qa_revision` (`~283`), the
`claude.py` long-input functions.

**Fix:** In `claude.py`: (1) add a shared `MAX_INPUT_CHARS` constant + a small pre-flight check that raises a
clear `ValueError` (or truncates + warns, decide per call site) — reuse from `document_processor`/`qa_revision`
rather than re-implementing; (2) set `max_retries=2-3` on the client **or** add one explicit retry wrapper —
single source, not duplicated per function.

**Test (pre-registered):** feed an over-limit input → assert a clear `ValueError`/truncation-warning, not a
silent oversize call. Simulate a transient API error (monkeypatch) → assert it is retried, not surfaced as a
hard failure on the first blip. Confirm a normal-size call is unaffected.

**Side effects:** latency on retried calls; very large inputs now fail fast with a clear message instead of
silently degrading — intended.

**Commit message:** `Audit-fix 4: shared MAX_INPUT_CHARS guard + non-zero max_retries in claude.py`

---

## Item 5 — Finish the centralization refactor (Rule 5)  *(prevents label/validator drift)*

**Problem [VERIFIED via agent reads; confirm exact lines]:** `prompts.py` already builds `_DOMAIN_LIST`
dynamically (line 8) but then **hardcodes** the domain list in all 5 agent prompts (`~20-22,50-52,81-83,
191-193,614-616`) and the confidence/priority/effort/phase vocabularies (`~639,819,829,894-896`). The same
drift exists in `report_sections.py` (`_DOMAIN_AUDIENCE`, `_ROLE_READING_GUIDE`, inline headers),
`document_processor.py` (`DOMAIN_FILTER_MAP` `~21-32`), routers (`findings.py` `_ANNUAL_DRAG_DOMAINS` `~27-30`,
`roadmap.py` `VALID_PHASES` `~15`), and `RoadmapPanel.jsx:5` (`STATUSES`). These literals silently desync from
`domains.py`/`constants.js` and from the validators — reintroducing the labeling drift Item 2 guards against.

**Fix:**
- `prompts.py`: derive `_DOMAIN_LIST_PROSE`, `_CONFIDENCES_PROSE`, `_PRIORITIES_PROSE`, `_EFFORTS_PROSE`,
  `_PHASES_PROSE` from the `domains.py` imports; interpolate everywhere (also removes ~600 tokens/engagement).
- Move `DOMAIN_FILTER_MAP`, `_ANNUAL_DRAG_DOMAINS`, `VALID_PHASES`, `_DOMAIN_AUDIENCE`/`_ROLE_READING_GUIDE`
  into `api/utils/domains.py` (or a `report_constants.py`); import at use sites.
- `constants.js`: add `ROADMAP_STATUSES`; import in `RoadmapPanel.jsx`.

**Test (pre-registered):** snapshot the rendered agent prompts before/after → assert byte-identical domain/
enum text (pure refactor, no semantic change). A frontend render test for the status dropdown. Optionally a
guard test asserting no module outside `domains.py`/`constants.js` defines a domain literal.

**Side effects:** none functional if snapshots match; the win is future-proofing against silent drift.

**Commit message:** `Audit-fix 5: source all domain/enum/status literals from domains.py / constants.js (Rule 5)`

---

## Suggested implementation sequence

Priority order above is fix-first; for *execution*, group by cost/isolation:

1. **Item 3** first — ~5 lines + a test, fully isolated, removes a landmine. Quick win.
2. **Item 4** — small, central, and makes Item 1 meaningful (failures become loud + bounded).
3. **Item 1** — the swallow sweep, now that retries/guards exist to back it.
4. **Item 2** — the new auditor checks; validate against a known-good E007 deliverable for false-positives.
5. **Item 5** — pure refactor; do last so it doesn't churn lines the other items touch.

Ship each as its own commit (and push), with its pre-registered test landing first. Re-run `pytest tests/ -v`
(148-test baseline) after each.
