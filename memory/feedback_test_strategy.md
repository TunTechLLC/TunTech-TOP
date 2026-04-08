---
name: Test strategy for TOP
description: How to test TOP — what can run automatically, what requires manual verification, and the pattern for writing new tests
type: feedback
---

Run `pytest tests/ -v` from `C:\Dev\TunTech\TOP` at any time — no engagement, no Claude calls, no DB setup required. 21 tests as of 2026-04-08.

**Why:** Most features touch Claude or the database, but the processing and utility logic can be tested with programmatically-created files and a temp DB. Keeping a runnable suite means regressions are caught before engaging a real client.

**How to apply:**

- Always run `pytest tests/ -v` after any backend change before committing
- New tests for file processing logic: create test files programmatically (python-docx, openpyxl, python-pptx) in a tempfile — no real engagement folder needed
- New tests for repository logic: use the existing pattern in `test_repositories.py` — monkeypatch `TOP_DB_PATH` to a temp file
- PDF extraction is the one format without an automated test — pdfplumber has no test file generation API. Always verify manually with a real text-based PDF when touching PDF extraction logic
- Use `pytest.importorskip('module')` for tests that require optional libraries so the suite doesn't fail if a library is missing
- Tests live in `tests/test_document_processor.py` and `tests/test_repositories.py`
