# Memory Index

- [Architecture standards](feedback_architecture.md) — Think architect-first; TOP will move to cloud/multi-user — avoid shortcuts that become liabilities at scale
- [Write tool encoding](feedback_write_tool_encoding.md) — Write tool produces UTF-16 LE on Windows; use Python via Bash for plain-text config files that must be UTF-8
- [Test strategy](feedback_test_strategy.md) — pytest tests/ -v runs anytime; programmatic file creation for format tests; PDF is manual-only
- [Build order — Audit Layer top priority](project_build_order.md) — Revised 2026-05-21. Narrator Output Auditor first; Word doc review burden (4–8 hrs) is the binding constraint.
- [Check skills directory for custom skills](feedback_skills_check.md) — Always ls ~/.claude/skills/ when asked about available skills; custom skills don't appear in system-reminder
