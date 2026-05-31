# Memory Index

- [Architecture standards](feedback_architecture.md) — Think architect-first; TOP will move to cloud/multi-user — avoid shortcuts that become liabilities at scale
- [Write tool encoding](feedback_write_tool_encoding.md) — Write tool produces UTF-16 LE on Windows; use Python via Bash for plain-text config files that must be UTF-8
- [Test strategy](feedback_test_strategy.md) — pytest tests/ -v runs anytime; programmatic file creation for format tests; PDF is manual-only
- [Build order — Post-Assembly QA Stage top priority](project_build_order.md) — QA-1/2/3/4 shipped (QA-4 = in-place edit-list, Opus 4.7, reconciliation — NOT single-shot regeneration). QA-5 (QA Tab UI + v1↔v2 diff) is next, then Checkpoint 5.
- [Check skills directory for custom skills](feedback_skills_check.md) — Always ls ~/.claude/skills/ when asked about available skills; custom skills don't appear in system-reminder
- [Completed items move OUT of BACKLOG into PROGRESS](feedback_completed_items_move_to_progress.md) — When an item ships, DELETE its spec from BACKLOG; don't leave a "done" banner. Stated numerous times.
