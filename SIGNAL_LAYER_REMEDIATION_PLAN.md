# Signal-Layer Remediation Plan — Handoff Doc

**Status:** **PHASE 1 + PHASE 2 (B, C1) COMPLETE & PUSHED.** Defects E, A, A2, D, B, C1
shipped, each test-gated, 147 tests pass. **Created:** 2026-06-13.

### ▶ RESUME HERE — re-baseline on a FRESH engagement
The signal-layer redesign is functionally done. **Next: the comprehensive re-baseline.**
- **Victor creates a FRESH engagement** on the Cobalt source (do NOT wipe E006 — it's the
  documented "before"), runs it end-to-end (process files → patterns → agents → findings →
  roadmap → report → QA), and grades v1/v2 against the answer key.
- **What to confirm at re-baseline:** E1/E2 economics now appear with correct labels; the
  Revenue-at-Risk headline is the $2.8M/$3.48M Helix exposure (DERIVED, not CONFIRMED); the
  big material signals (concentration, PMO/authority, renewal) survive; no whole-file silent
  loss; the main candidate set is bounded (~49 on E006) and reads as the *right* signals.
- **C2 decision is pending the re-baseline:** does any *material single-source derived*
  figure still get demoted to Hypothesis-and-hidden? If yes → add a derived-reserve in
  selection (safer than a rubric change). If no → C2 not needed.
- Open question still open: post-change **review-burden** number in practice (E006 main ≈ 49).

**Working method (load-bearing):** evidence first; pre-registered reversible test before any
production change; tag claims verified/inferred/unchecked; surface own gaps proactively;
commit + push each piece. Throwaway verification scripts live in `scripts/` (deletable).

### Phase 1 — shipped record
- **E** (`4c0b058`, completed by the doc-path fix in same series) — model → Opus 4.7 in
  `config.py`; `_stream_final_message` helper; all 7 long Claude calls stream (6 in
  `claude.py` + the document-extraction path moved out of `document_processor.py` into
  `claude.py`'s `extract_signals_from_document`, fixing a CLAUDE.md violation). The 2 tiny
  calls stay non-streaming. Proven: Synthesizer 142s streams clean (would've timed out).
- **A** (`3d45cce`) — JSON robustness. `_parse_extraction_response` (pure, raises) +
  `_extract_signals_with_retry` (one regenerate-retry, then raise). Failed file is NOT
  marked processed → re-attempted next run. `SignalPanel.jsx` surfaces failed files.
- **A2** (`1ec8329`) — same anti-pattern in the QA layer. Shared `_parse_json_array`
  (raises on failure, `[]` only for legitimately-empty). 4 QA functions + narrator stop
  swallowing; narrator raises RuntimeError (→500 not 404). QA routers surface clean 500;
  QA panels already render the error.
- **D** (`13b1093`) — `ECONOMICS_PROMPT` precedence/labeling block: preserve source labels;
  computed/exposure figures are DERIVED not CONFIRMED, exposure is "risk not loss". Fixes
  E3 mislabel. Verified on real E006 input: $3.48M → DERIVED, "risk, not realized".

### Phase 2 — shipped record
- **B** (`dc93ee3`) — semantic dedup. `cluster_duplicate_signals` (Opus, within-domain) +
  `_reconcile_partition` (tolerates duplicate/missing model indices) + `_merge_cluster`
  (representative + union sources + one corroboration upgrade if ≥2 sources). Exact-name
  pre-pass; within-domain ENFORCED in code; graceful FLAGGED fallback. E006: 120 raw → ~65/67.
- **C1** (`f7c02e7`) — quality-gated selection replacing the fixed per-domain cap.
  `_select_candidates`: keep ALL High/domain, top-3 Medium (corroboration-ranked, strength
  reserve), global ceiling 55 (worst-first trim, per-domain floor). `MEDIUM_PER_DOMAIN=3`,
  `MAIN_CANDIDATE_CEILING=55`. E006: 65 deduped → 49 main; E1 AND E2 in main.
- **Economics fix now complete end-to-end:** B corroborates E1/E2 to Medium → C1 keeps them
  → they reach the Consulting Economics agent → D preserves their labels.

### Follow-ons
- **C2** (single-source derived → Hypothesis demotion) DEFERRED — evaluate at re-baseline.
- D's full effect depended on B+C delivering the figures — now satisfied.
**How we work now (agreed):** every problem claim cites evidence; every fix gets a
**pre-registered, reversible test that runs BEFORE any production change** (the standard set
by the economics proof). Tag each item verified / inferred / unchecked. Do not get ahead of
the evidence.

---

## 0. How we got here

ChatGPT rated the Cobalt E006 v2 roadmap **7/10**. Victor expected ≥8 and asked whether
ChatGPT was wrong or there's real work on TOP. Verdict: **ChatGPT was essentially right.**
Investigating the biggest gap (missing economics E1/E2) uncovered a **systemic signal-layer
quality problem**, not a one-client issue.

**Reviewed artifacts:**
- Answer key: `C:\001-cowork-projects\New-client\Cobalt-Data-Partners_TESTKEY\Cobalt_E006_ANSWER_KEY.md`
- v2 doc reviewed by ChatGPT: same folder, `OPD_Transformation_Roadmap_E006_v2.docx`
- Extracted v2 text: `qa_review_extract/E006_v2_full.txt`
- Proof outputs: `qa_review_extract/econ_proof_control.txt`, `econ_proof_treatment.txt`
- Throwaway proof scripts: `scripts/econ_grounding_proof.py`, `econ_grounding_proof_treat.py`,
  `scripts/cto_extraction_probe.py` (safe to delete — they make Claude calls, change nothing)

---

## 1. The five unknowns — CLOSED with evidence

**#1 — CTO zero-signal failure = silent JSON-parse swallow. Reproducible, model-dependent.**
- Re-ran extraction on `Interview_CTO_Raj_Malhotra.txt` (16,723 chars): **Sonnet 4.6 emitted
  malformed JSON** (parse error line 51) → `document_processor.py:631-634` logs and sets
  `candidates = []` (no retry, no surfacing). **Opus 4.7 returned 10 valid signals.**
- A whole stakeholder interview was lost silently. [VERIFIED]

**#1b — It has recurred.** `ProcessedFiles.signal_count = 0` on **2 of 3 modern engagements**:
- E006 `Interview_CTO_Raj_Malhotra.txt` (cause VERIFIED above)
- E004 `Interview_Operations_Sandra_Okafor.txt` (same signature; cause INFERRED, not re-run)

**#2 — ~60% cull is systemic, not E006-specific.** raw (`ProcessedFiles.signal_count`) → loaded
(`Signals`): **E004 109→45 (59%), E005 99→41 (59%), E006 120→47 (61%)**. Confirms Victor's
prior. (E001–E003 show negative numbers — counts predate/bypass current pipeline; unusable.) [VERIFIED]

**#3 — Patterns AND agents consume ONLY loaded signals.** `patterns.py:50,57`; `signal.py:26-27`
(no confidence filter); `case_packet.py:73`. The cull is the single chokepoint that decides
signal quality for everything downstream. Loaded Hypothesis signals do reach them. [VERIFIED]

**#4 — Loaded "High-heavy" is cap selection bias; derived = cull-first.** RAW (120):
**58 High / 14 Medium / 48 Hypothesis**. LOADED (47): 37/5/5. Cap sorts confidence-only, so
**43 of 48 Hypothesis culled**. The rubric (`prompts.py` SIGNAL_EXTRACTION_PROMPT +
the per-doc prompts) makes anything **derived/hedged** a Hypothesis → the derived economics
(E1/E2) became Hypothesis and were dropped first. [VERIFIED]

**#5 — Changes are forward-only; cost is review volume; 2 tests pin behavior.** `process-files`
writes candidate files; `load-candidates` (`signals.py:101`) is a **separate** step → dedup/cap
changes affect only future runs, not already-loaded engagements. `tests/test_repositories.py:484,522`
assert `_apply_domain_cap(cap=5)` reserve behavior (must update if cap changes). [VERIFIED]

---

## 2. The economics proof (the one thing that earned trust this session)

Reconstructed the REAL E006 Consulting Economics agent input (case packet + Diagnostician prior,
via `CasePacketService` + `AgentRunRepository`), ran two conditions on Opus 4.7, zero TOP changes:

| Answer-key figure | CONTROL (current input/prompt) | TREATMENT (worksheet routed in + grounding rule) |
|---|---|---|
| E1 overrun $12K / ~$48K | absent | reproduced, **ESTIMATED** |
| E2 retainer +$2,600 / −$8,950 / −$107.4K | absent | reproduced, **DERIVED/ASSUMED** |
| E3 $3.48M label | present but **CONFIRMED (wrong)** | preserved as **ESTIMATED exposure, NOT loss** |
| **Score** | **1/8** | **8/8** |

**Important correction made mid-investigation:** the economics was NOT lost at extraction (an
earlier claim). It WAS extracted with full figures (candidate files show
"Fixed-Bid Project Overrun Leakage" and "Retainer Product Profitability (Underwater Retainers)"
with $12K/$48K/$8,950/−$107,400) — but classified **Hypothesis** (derived) and **culled by the
5/domain cap** before reaching the DB or the agent. Loss is at CULLING, not extraction.

---

## 3. Evidence-tagged remediation plan

### Defect A — Silent JSON-parse swallow loses whole files
- **Problem [VERIFIED E006 / INFERRED E004]:** `document_processor.py:631-634` stores empty on
  bad JSON — no retry, no surfacing. 2 of 3 engagements hit; lost CTO + (likely) Operations.
- **Fix:** (1) JSON repair/retry on parse failure; (2) unrecoverable → surface loudly (never
  silent-empty); (3) Opus reduces incidence but does NOT replace this fix (model-independent bug).
- **Test (pre-registered):** feed the captured malformed Sonnet output through the repair path →
  assert ≥1 signal recovered OR a visible error (not silent empty); then re-process E004/Sandra +
  E006/CTO and confirm signals appear.
- **Severity: highest (data loss).** Side effects: none to loaded data.

### Defect B — Weak semantic dedup inflates the cull
- **Problem [VERIFIED]:** dedup keys on exact `domain+signal_name`; concentration restated ×5,
  over-allocation ×5 survive as separate candidates and consume cap slots.
- **Fix:** semantic dedup merging restatements of one signal (keep strongest evidence + all source
  attributions). Judgment work → Claude-assisted or normalized-meaning key. **Needs design.**
- **Test:** run new dedup on E006's 120 raw candidates → concentration cluster collapses to 1
  WITHOUT dropping distinct Sales signals (win/loss, pipeline depth); spot-check vs hand judgment.
- Side effects: changes future review sets; update dedup tests.

### Defect C — Cap + confidence-only sort drops distinct material signals; derived = cull-first
- **Problem [VERIFIED]:** 63/120 culled by 5/domain cap; 8/10 domains at cap; High-confidence
  findings-core casualties (PMO-informal=F3, renewal-RFI=F1, change-order-absent=F6). 48 raw
  Hypothesis → 5 loaded. `_apply_domain_cap` sorts confidence-only.
- **Fix (coupled with B):** after better dedup — (1) raise the domain cap modestly (Victor OK'd a
  slight raise); (2) stop auto-demoting grounded-but-derived figures to cull-first Hypothesis
  (rubric change; possibly an economics/derived reserve like the existing `strength_reserve`).
- **Test:** re-run cull on E006 with (better dedup + raised cap + economics not auto-demoted) →
  confirm E1/E2 AND the High casualties survive while total stays in a sane review target; report
  new loaded count.
- Side effects: review volume up; update `test_repositories.py:484,522`; revisit "25–40 target".

### Defect D — Economics grounding on the agent
- **Problem [VERIFIED]:** agent re-invents/mislabels economics it never receives.
- **Fix:** grounding/precedence block in `ECONOMICS_PROMPT` (`prompts.py:66`): prefer/preserve
  source-labeled figures; never relabel exposure/ESTIMATED as CONFIRMED. Worksheet-routing becomes
  optional backstop once B+C let economics signals survive.
- **Test: ALREADY VALIDATED** (proof above, 1/8 → 8/8). Re-validate live after B+C.
- Side effects: prompt-only.

### Defect E — Model standardization + streaming (cross-cutting)
- **Problem [VERIFIED]:** pipeline on Sonnet 4.6; Opus parsed CTO where Sonnet failed; treatment
  call timed out non-streaming; `call_claude` (`claude.py:46`, used by ALL agents) does not stream.
- **Fix:** centralize model in `config.py:16` → `claude-opus-4-7` (the 4 QA constants in
  `claude.py` are already 4.7, so this makes the whole system 4.7). Make `call_claude` stream.
- **Test:** run 2 agents on Opus via streaming → no timeout, sane output.
- Side effects: cost/latency up. **Sequence first** so all other work is validated on the ship model.

---

## 4. Recommended sequencing (AGREED)

**Phase 1 — small, high-confidence fixes (each test-gated, ship together):**
1. **E** (model + streaming) — first; everything else then validated on Opus.
2. **A** (JSON robustness) — NOT skipped despite Opus reducing incidence; data-integrity.
3. **D** (economics grounding) — cheapest, already proven.
→ then **re-run Cobalt E006 end-to-end and re-baseline.**

**Phase 2 — the signal-quality redesign (deliberate, separate):**
4. **B + C** (semantic dedup + cap/confidence) — the design-heavy core; do on Opus, against the
   re-baselined numbers, with full attention (this is where care matters most).

**Before any code:** persist this doc (done) + git checkpoint.

---

## 5. Model decision (locked by Victor 2026-06-13)
Standardize on **Opus 4.7 globally for now** (via `config.py`), can bump to 4.8+ later as a
one-line change. QA-4 revision stays effectively 4.7 (its hardcoded constants), which is the
desired carve-out. Streaming in `call_claude` is a prerequisite (see Defect E).

---

## 6. Open questions NOT yet closed (named, not hidden)
- E004/Sandra zero-signal cause is **inferred** (same signature), not re-run-confirmed.
- How much better dedup ALONE relieves the cap (a number, not yet measured — it's the Defect B test).
- Whether the confidence-rubric change **over-promotes noise** on non-economics signals (Defect C
  test must check both directions).
- Post-change **review-burden number** (unknown until B+C test).

---

## 7. Trust note for whoever resumes this
This session involved several corrections where conclusions ran ahead of the investigation
(e.g., "economics lost at extraction" — wrong, it was culling). The working agreement is:
**evidence first, pre-registered reversible tests before production changes, tag confidence,
surface your own gaps before the user has to.** Hold to it.
