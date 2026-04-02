---
name: Architecture standards
description: Victor expects architect-level thinking on all solution proposals — cloud and multi-user future must be considered
type: feedback
---

Think like an architect on every solution proposal. Victor is building TOP as a single-user local tool today, but it will move to cloud hosting and multi-user (AWS, multi-tenant) in Phase 3. Solutions that are fine for single-user but become liabilities at scale should be flagged or avoided.

**Why:** Victor explicitly corrected a quick-fix proposal and asked for the architecturally correct solution. He does not want to accumulate technical debt that creates rework at cloud migration time.

**How to apply:**
- When proposing options, evaluate each against the cloud/multi-user future, not just today's single-user context
- Lead with the option that scales correctly, explain why
- Don't propose shortcuts that couple concerns or add per-request DB queries where the client already holds the reference
- "Single-user local tool" is not a reason to take an architectural shortcut — it is a reason to keep things simple, which is different
