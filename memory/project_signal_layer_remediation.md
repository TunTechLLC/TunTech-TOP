---
name: Signal-layer remediation plan in progress
description: Signal-layer remediation — Phase 1 (E, A, A2, D) AND Phase 2 (B dedup, C1 quality-gated selection) SHIPPED & pushed, 147 tests pass. Next: comprehensive re-baseline on a FRESH engagement; C2 deferred
metadata:
  type: project
---

As of 2026-06-13: a full evidence-based investigation of TOP's signal layer is
complete and an evidence-tagged remediation plan is written to
`SIGNAL_LAYER_REMEDIATION_PLAN.md` (repo root). **No code changes have been made yet.**

Triggered by ChatGPT rating the Cobalt E006 v2 roadmap 7/10. Investigation found
the economics gap (missing E1/E2) is one symptom of systemic signal-layer defects:

- **Defect A** — silent JSON-parse swallow loses whole files (`document_processor.py:631-634`);
  hit E006/CTO (verified) + E004/Operations (inferred). Highest severity (data loss).
- **Defect B** — weak exact-name dedup lets restatements (concentration ×5) consume cap slots.
- **Defect C** — 5/domain cap + confidence-only sort culls ~60% of signals (E004/E005/E006 all
  ~59-61%); derived figures become Hypothesis and get dropped first (why economics died).
- **Defect D** — Consulting Economics agent re-invents/mislabels economics it never receives;
  **fix proven** (worksheet routed in + grounding rule: 1/8 → 8/8, E3 label fixed).
- **Defect E** — pipeline runs on Sonnet; standardize to Opus 4.7 via `config.py` + make
  `call_claude` stream. **Do first.**

**Phase 1 SHIPPED & pushed 2026-06-14:** E (`4c0b058` + doc-path fix) = Opus 4.7 + streaming
helper for all 7 long calls; A (`3d45cce`) = JSON robustness (pure parser raises + retry +
fail-loud, never silent file loss); A2 (`1ec8329`) = QA agents + narrator fail loud (shared
`_parse_json_array`, never mask a parse failure as "0 issues clean"); D (`13b1093`) =
ECONOMICS_PROMPT precedence/labeling (exposure DERIVED not CONFIRMED; fixes E3). 136 tests pass.
**Phase 2 SHIPPED & pushed:** B (`dc93ee3`) = semantic dedup (cluster_duplicate_signals +
_reconcile_partition + _merge_cluster; within-domain enforced; corroboration upgrades); C1
(`f7c02e7`) = quality-gated selection (_select_candidates: keep all High, top-3 Medium/domain
with strength reserve, global ceiling 55) replacing the fixed per-domain cap. Economics fixed
end-to-end (B→C1→D): on E006, 120 raw → 65 deduped → 49 main, E1 AND E2 reach the agent.
**Next:** comprehensive re-baseline on a FRESH engagement (Victor creates; do NOT wipe E006).
**C2 deferred** (single-source derived → Hypothesis demotion) — evaluate at re-baseline; if a
material single-source derived figure is still hidden, add a derived-reserve in selection
(safer than a rubric change).

**Working method agreed this session (load-bearing for trust):** evidence first; every fix gets a
pre-registered, reversible test that runs BEFORE any production change; tag claims
verified/inferred/unchecked; surface own gaps proactively. Several conclusions ran ahead of the
evidence earlier and had to be corrected — hold the line. Related: [[feedback_architecture]],
[[feedback_test_strategy]].

To resume: read `SIGNAL_LAYER_REMEDIATION_PLAN.md` (it has full evidence, file:line refs, the
proof outputs in `qa_review_extract/econ_proof_*.txt`, and the open questions).
