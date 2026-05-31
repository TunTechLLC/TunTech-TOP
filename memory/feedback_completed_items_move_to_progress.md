---
name: Completed items move OUT of BACKLOG into PROGRESS
description: When an item ships, DELETE its spec from BACKLOG.md and record it in PROGRESS.md — do not leave it in BACKLOG with a "done/shipped" banner
metadata:
  type: feedback
---

When a backlog item is completed, it must be **removed from `BACKLOG.md`
entirely** and its record placed in `PROGRESS.md`. Do not leave the completed
item's spec in BACKLOG marked "✅ SHIPPED" or "done" — delete it. BACKLOG holds
only not-yet-done work; PROGRESS holds completed work. These are mutually
exclusive: an item lives in exactly one file.

**Why:** Victor has stated this numerous times and was frustrated to find QA-4's
spec still sitting in BACKLOG after it shipped (2026-05-31), even though it had a
SHIPPED banner. A "done" item lingering in the backlog defeats the purpose of the
backlog (a list of remaining work) and makes the build order ambiguous.

**How to apply:** As part of shipping ANY item — same session, before declaring
it done — (1) write the full as-built record as a row/entry in PROGRESS.md, and
(2) delete the item's section and its build-sequence-table row from BACKLOG.md.
Updating the build-sequence table's numbering is not enough; the item's spec
prose must also be removed. Treat "move to PROGRESS" literally as a move, not a
copy-and-mark. Related: [[project_build_order]].
