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

---

## Next Steps

**Current task:** Replace Report Download with Save-and-Show-Path (next Before Checkpoint 4 item)
**After that:** Work through BACKLOG.md top to bottom — Before Checkpoint 4, then Checkpoint 4.

---

## Test Data

| Engagement | Firm | Signals | Patterns | Agents | Findings | Roadmap |
|-----------|------|---------|----------|--------|---------|---------|
| E001 | Meridian Consulting Group | 33 | 32 | 5 accepted | 7 | 16 |
| E002 | Apex Technology Solutions | 33 | 21 | 5 accepted | 7 | 16 |
| E003 | (Fictional — Dry Run 3) | 102 | — | 5 accepted | — | — |

E001 and E002 are the primary reference engagements.
E003 was used to validate Report Narrator and Synthesizer-to-Roadmap Parser.
