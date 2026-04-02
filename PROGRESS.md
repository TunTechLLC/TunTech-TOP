# TOP — TunTech Operations Platform
## Development Progress
*Read this at the start of every Claude Code session alongside CLAUDE.md*

---

## Current Status

**Phase A (Backend):** ✅ Complete — Checkpoint 1 passed
**Phase B (Frontend):** ✅ Complete — Checkpoint 3 passed 2026-03-30

**Where we are:** Post-Checkpoint 3 backlog work in progress. See BACKLOG.md for remaining
Before Checkpoint 4 items and build order.

---

## Completed Steps

| Step | Description | Status |
|------|-------------|--------|
| 1–3 | Database schema, 14 tables, repositories, API utils | ✅ |
| 4 | FastAPI app, 8 routers, CORS, logging, error handler | ✅ |
| 5 | Dashboard + NewEngagement components | ✅ |
| 6 | EngagementDetail, 8 tabs, Edit Settings | ✅ |
| 7 | All panel components (Signal, Pattern, Agent, Finding, Roadmap, Knowledge, Report) | ✅ |
| 8 | Document processing pipeline | ✅ |
| 8 Ext 1 | File processing and signal extraction | ✅ |
| 8 Ext 1 Cleanup | Multi-file review fix (source_file label, parallel fetch) | ✅ |
| 8 Ext 1 Cleanup | File type expansion — STATUS and RESOURCE prompts (DELIVERY deferred) | ✅ |
| 8 Ext 1 Cleanup | Auto-cull signal candidates — dedup, domain cap, hypothesis filter/toggle | ✅ |
| 8 Ext 2 | Synthesizer-to-Findings parser | ✅ |
| 9 | Cross-engagement report screen | ✅ |
| 10 | Word report download | ✅ |
| Backlog | Report Narrator — narrative prose layer for OPD report | ✅ Validated (E002, E003) |
| Backlog | Synthesizer-to-Roadmap Parser — detect-review-load for roadmap items | ✅ Validated (E002) |
| Backlog | Add field labels to Finding candidate review cards | ✅ |
| Backlog | Disable agent buttons while any agent is running | ✅ |
| Backlog | Roadmap item edit and delete | ✅ |
| Backlog | Word report template — custom .docx, table column widths, header shading | ✅ |
| Backlog | DELIVERY_DOCUMENT_EXTRACTION_PROMPT — risk registers, retrospectives, portfolio summaries, proposals | ✅ |
| Backlog | Signal candidate labels — field labels added to candidate review cards | ✅ |
| Backlog | Reprocess button — source_file column on Signals, delete+reprocess endpoint, processed files UI | ✅ |
| Backlog | Candidate file cleanup — archive merged and individual candidate files to processed/ after loading | ✅ |
| Backlog | Engagement header count refresh — onRefresh callback from EngagementDetail to all panels | ✅ |
| Backlog | Replace report download with save-and-show-path — generate endpoint, open-folder endpoint | ✅ |
| Backlog | OPD report major restructure — Sections 5-9 rebuilt, new Sections 7 / 8.1-8.7 / 9 | ✅ Validated (E003) |
| Backlog | Report Narrator — rewrite to JSON output, 8 new structured sections (future state, priority zero, roadmap overview, initiative details, dependencies, risks, next steps) | ✅ |
| Backlog | ROADMAP_EXTRACTION_PROMPT — owner field with role-based derivation and "TBD — assign at kickoff" fallback | ✅ |
| Backlog | Section 6 economic summary table — _parse_economic_figures() parses CONFIRMED/INFERRED from free text, primary figure per cell, clean totals row from Consulting Economics finding | ✅ |
| Backlog | ReportPanel — remove stale sections list, persist last saved path via localStorage | ✅ |
| Backlog | Word report template — additional formatting cleanup (heading numbers, economic table, section structure verified on E003) | ✅ |

---

## Next Steps

**Current task:** Economic Impact Reasoning — update FINDINGS_EXTRACTION_PROMPT to show inline calculation reasoning (inputs, method, source per figure)
**After that:** Improve PATTERN_DETECTION_PROMPT, then Checkpoint 4.

---

## Test Data

| Engagement | Firm | Signals | Patterns | Agents | Findings | Roadmap |
|-----------|------|---------|----------|--------|---------|---------|
| E001 | Meridian Consulting Group | 33 | 32 | 5 accepted | 7 | 16 |
| E002 | Apex Technology Solutions | 33 | 21 | 5 accepted | 7 | 16 |
| E003 | (Fictional — Dry Run 3) | 102 | — | 5 accepted | Yes | Yes |

E001 and E002 are the primary reference engagements.
E003 is the primary report testing engagement — 102 signals, full agent sequence, findings and roadmap generated.
