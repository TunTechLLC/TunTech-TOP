---
name: Signal-layer remediation plan in progress
description: Investigated signal-quality defects (silent JSON loss, ~60% cull, derived-as-Hypothesis); evidence-tagged plan written; no code changes yet — Phase 1 Defect E next
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

**Agreed sequence:** Phase 1 = E → A → D (small, test-gated), then re-run Cobalt and re-baseline.
Phase 2 = B + C (the design-heavy dedup + cap/confidence redesign), done deliberately on Opus.

**Working method agreed this session (load-bearing for trust):** evidence first; every fix gets a
pre-registered, reversible test that runs BEFORE any production change; tag claims
verified/inferred/unchecked; surface own gaps proactively. Several conclusions ran ahead of the
evidence earlier and had to be corrected — hold the line. Related: [[feedback_architecture]],
[[feedback_test_strategy]].

To resume: read `SIGNAL_LAYER_REMEDIATION_PLAN.md` (it has full evidence, file:line refs, the
proof outputs in `qa_review_extract/econ_proof_*.txt`, and the open questions).
