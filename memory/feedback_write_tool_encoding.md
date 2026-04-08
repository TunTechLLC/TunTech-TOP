---
name: Write tool produces UTF-16 LE on Windows
description: The Write tool on this Windows environment produces UTF-16 LE encoded files — use Python to write plain-text config files that must be UTF-8
type: feedback
---

The Write tool produces UTF-16 LE encoded files on this Windows environment. Discovered when rewriting `requirements.txt` — pip could not read it and the first 4 bytes showed `61 00 6e 00` (UTF-16 LE without BOM) instead of `61 6e 6e 6f` (UTF-8).

**Why:** The Write tool uses the system default encoding on Windows, which can be UTF-16 LE. Plain-text config files consumed by external tools (pip, CI, etc.) must be UTF-8.

**How to apply:** When rewriting any plain-text config file (requirements.txt, .env, .cfg, etc.), do not use the Write tool. Instead use this Python one-liner via Bash:

```python
python -c "
content = open('path/to/file', encoding='utf-16-le').read()
open('path/to/file', 'w', encoding='utf-8', newline='\n').write(content)
"
```

Or write new content directly:
```python
python -c "
open('path/to/file', 'w', encoding='utf-8', newline='\n').write('''line1\nline2\n''')
"
```

For source code files (.py, .js, .jsx, .md) the encoding issue has not caused problems — only observed on requirements.txt so far.
