---
name: Check skills directory for custom skills
description: Always check ~/.claude/skills/ when asked about available skills — custom skills are not surfaced in the system-reminder
type: feedback
originSessionId: eed0da9a-9109-400d-ae3c-ab62c23bca29
---
When asked "what skills are available?", always check `~/.claude/skills/` in addition to the system-reminder skill list. Custom user skills live there and are not automatically registered in the system-reminder.

**Why:** The system-reminder only shows harness-registered skills. User-created skills in ~/.claude/skills/ exist on disk but won't appear in that list, causing them to be silently omitted from answers.

**How to apply:** On any "what skills are available" question, run `ls ~/.claude/skills/` and read any unfamiliar .md files to include their descriptions in the answer.
