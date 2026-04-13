---
name: Agreed build order — Technical Debt and Signal Library phase
description: Code-verified build sequence for the current backlog phase, with consolidation decisions and key investigation findings
type: project
---

Agreed build order for the current phase (post-Checkpoint 4, pre-Checkpoint 5). Derived from
full code investigation on 2026-04-13 — not just backlog reading.

**Why:** Victor asked for architect-first reasoning and thorough code verification before
finalizing order. The order below reflects what was actually found in the code, not
just what the backlog describes.

## Build Order

| # | Item | Sessions | Notes |
|---|------|----------|-------|
| 1 | Document Cleanup | 1 | P-codes in evidence summary + future state table labels |
| 2 | Split report_generator.py | 1 | Gates Economic C and Visual 3 — do before any more additions |
| 3 | Economic Structured Fields A+B | 2 | Schema + UI only, no report_generator.py touch |
| 4 | Economic Structured Fields C | 1 | Requires split; updates report_sections.py (new file) |
| 5 | Signal Library Sessions 1–3 | 3 | Includes DEFAULT_DOMAIN constant and domain injection fix |
| 6 | Editable Engagement Info | 1 | Real gap but lower urgency |
| 7 | Domain Maturity Scoring | 1 | Independent |
| 8 | Visual 3 — Causal Chain | 1 | Requires split (already done at step 2) |

## Key Consolidation Decisions

- **DEFAULT_DOMAIN as standalone session eliminated.** The constant add goes into Signal Library
  Session 1 (trivial). The domain injection fix (hardcoded domain lists in extraction prompts)
  goes into Signal Library Session 2 — you're rewriting all extraction prompts for the library
  anyway. Touching them twice is wrong.

- **Economic A+B come AFTER the split**, not before. They don't require it, but adding new
  fields to the clean post-split structure is better than adding to the monolith then splitting.

## Key Code Investigation Findings (2026-04-13)

**report_generator.py**
- 2,114 lines. ReportGeneratorService class starts at line 583. ~30 renderer methods.
- Split is fully justified and urgent.

**P-codes issue (Document Cleanup)**
- `_compute_evidence_summary()` in `api/routers/findings.py:40-70` generates the P-code string.
- Rendered verbatim in `_findings_by_domain` at `report_generator.py:1471-1477`.
- Fix is render-time string transformation in report_generator.py only. No DB change.

**Future state table labels (Document Cleanup)**
- `_future_state_table` at `report_generator.py:1939-1941` explicitly appends `(sourced_from)`
  to the Metric column. Fix: remove those three lines. Fix 2 is a prompt change in claude.py.

**Economic chart (Economic Session C)**
- `_generate_economic_chart` calls `_parse_economic_figures` at line 1534. Still on text parser.
- Only the totals row (lines 1860-1892) already uses structured display_figure fields.
- `confirmed_figure`, `derived_figure`, `annual_drag_figure` do NOT exist in schema, model,
  or repository. Sessions A/B/C are all genuinely needed.

**Signal Library**
- Zero implementation. No library_signal_id, no SignalLibrary table, no SignalCoverage table.
- Domain lists in ALL 6 extraction prompts in document_processor.py are hardcoded literal
  strings — NOT injected from VALID_DOMAINS. VALID_DOMAINS is only used for validation.
- DEFAULT_DOMAIN: confirmed in 7 locations (3 backend, 4 frontend).

**Editable Engagement Info**
- EngagementRepository has only update_settings() for folder paths.
- No PATCH endpoint exists for firm_name, stated_problem, client_hypothesis, etc.
- Real gap — confirmed by reading engagements.py router and engagement repository.
