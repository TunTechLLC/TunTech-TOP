"""Editorial Check — Python pipeline.

Runs deterministic pattern-based checks against the rendered v1 roadmap text.
Each check returns items in the QA-3 schema with source='python'. The
orchestrator combines results, ready to pass to QAEditorialRepository.bulk_create.

This is a NEW module distinct from `narrator_auditor.py`. The two auditors
have different inputs and timing:
  - narrator_auditor.py reads NARRATOR JSON before Word render (pre-render).
  - editorial_auditor.py reads RENDERED v1 .docx text (post-render).

MVP scope (three checks):
  1. Internal signal codes leaking into client-facing prose (Tier 1)
  2. PMO/SOW used as abbreviations before their full forms are introduced
     (Tier 1)
  3. 'Operations Manager' co-occurring with 'Director of Operations' —
     terminology drift on the same role (Tier 1)

Skipped for MVP — add only if E004 smoke test shows demand:
  - Evidentiary label legend (CONFIRMED/DERIVED/INFERRED) missing
  - Broken section number references (Table 6 routing table)
  - British vs American spelling drift (cosmetic, low-stakes)
  - Cross-section numeric inconsistencies (overlaps with QA-2 semantic checks)
"""
import logging
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Check 1: Internal signal codes leaking into client-facing prose
# ---------------------------------------------------------------------------

# Signal IDs are 3-4 digit (S001 .. S9999). P-codes (patterns) and F-codes
# (findings) are deliberately skipped from MVP because P10/P11/P14 are also
# legitimate client project IDs in source materials — disambiguating between
# the two requires more context than a simple regex provides.
_SIGNAL_CODE_PATTERN = re.compile(r'\bS\d{3,4}\b')


def check_signal_codes_in_prose(roadmap_text: str) -> list[dict]:
    """Flag internal signal codes (S\\d{3,4}) in client-facing prose.

    Signal codes are internal database references. They should never appear
    in the rendered deliverable. Each unique code that appears is one item;
    the consultant can reject if a particular code is intentional context.
    """
    items = []
    seen = set()
    for match in _SIGNAL_CODE_PATTERN.finditer(roadmap_text):
        code = match.group()
        if code in seen:
            continue
        seen.add(code)
        start = max(0, match.start() - 60)
        end   = min(len(roadmap_text), match.end() + 60)
        context = roadmap_text[start:end].replace('\n', ' ').strip()
        items.append({
            'issue': (
                f"Internal signal reference code '{code}' appears in client-facing prose. "
                f"Signal codes are internal database references; the client cannot resolve "
                f"them and should not see them. Context: '...{context}...'"
            ),
            'category': 'context_gap',
            'location': f"Document body — search for '{code}'",
            'recommended_fix': (
                f"Replace '{code}' with a descriptive source attribution "
                f"(e.g. 'per Finance Lead interview' or 'per portfolio status report') "
                f"or remove the parenthetical entirely."
            ),
            'standard_term': None,
            'tier': 1,
            'source': 'python',
        })
    return items


# ---------------------------------------------------------------------------
# Check 2: PMO / SOW used as abbreviation before full form is introduced
# ---------------------------------------------------------------------------

_ACRONYM_DEFINITIONS = (
    ('PMO', 'Project Management Office',
     re.compile(r'\bPMO\b'),
     re.compile(r'\bproject management office\b', re.IGNORECASE)),
    ('SOW', 'Statement of Work',
     re.compile(r'\bSOW\b'),
     re.compile(r'\bstatement of work\b', re.IGNORECASE)),
)


def check_undefined_acronyms_at_first_use(roadmap_text: str) -> list[dict]:
    """Flag critical acronyms (PMO, SOW) used before their full form is introduced.

    Tier 1 per the locked QA-3 rubric — these acronyms must be defined on
    first use in any CEO-facing section. The check is document-wide rather
    than section-scoped because the Executive Briefing is always near the top
    and first use almost always falls in a CEO read.
    """
    items = []
    for short, full, short_pat, full_pat in _ACRONYM_DEFINITIONS:
        short_match = short_pat.search(roadmap_text)
        if short_match is None:
            continue
        full_match = full_pat.search(roadmap_text)
        if full_match is not None and full_match.start() < short_match.start():
            continue  # properly introduced
        if full_match is None:
            issue_detail = (
                f"'{short}' is used as an abbreviation but '{full}' never appears "
                f"anywhere in the document."
            )
            fix_detail = f"Define on first use: replace the first '{short}' with '{full} ({short})'."
        else:
            issue_detail = (
                f"'{short}' is used at character {short_match.start()} but its full form "
                f"'{full}' is not introduced until character {full_match.start()}."
            )
            fix_detail = (
                f"Move the definition to first use — change the first occurrence of "
                f"'{short}' to '{full} ({short})' and keep subsequent uses abbreviated."
            )
        start = max(0, short_match.start() - 60)
        end   = min(len(roadmap_text), short_match.end() + 60)
        context = roadmap_text[start:end].replace('\n', ' ').strip()
        items.append({
            'issue': f"{issue_detail} Context: '...{context}...'",
            'category': 'context_gap',
            'location': f"First '{short}' occurrence — character {short_match.start()}",
            'recommended_fix': fix_detail,
            'standard_term': full,
            'tier': 1,
            'source': 'python',
        })
    return items


# ---------------------------------------------------------------------------
# Check 3: 'Operations Manager' vs 'Director of Operations' terminology drift
# ---------------------------------------------------------------------------

_OPS_MANAGER_PATTERN = re.compile(r'\bOperations Manager\b')
_DIR_OF_OPS_PATTERN  = re.compile(r'\bDirector of Operations\b')


def check_operations_role_drift(roadmap_text: str) -> list[dict]:
    """Flag co-occurrence of 'Operations Manager' and 'Director of Operations'.

    These are typically the same role rendered inconsistently. One item is
    produced regardless of count — naming the standard term to use.
    """
    ops_mgr = list(_OPS_MANAGER_PATTERN.finditer(roadmap_text))
    dir_ops = list(_DIR_OF_OPS_PATTERN.finditer(roadmap_text))
    if not ops_mgr or not dir_ops:
        return []
    return [{
        'issue': (
            f"'Operations Manager' appears {len(ops_mgr)} time(s) and "
            f"'Director of Operations' appears {len(dir_ops)} time(s) in the same "
            f"document. If these refer to the same role, they should be standardized. "
            f"Readers cannot tell whether the document describes one role or two."
        ),
        'category': 'terminology',
        'location': 'Multiple occurrences across the document',
        'recommended_fix': (
            "Standardize on 'Director of Operations' (the title used in source "
            "interviews and the Engagement Overview). Replace all occurrences of "
            "'Operations Manager' unless a distinct role is intended — in which "
            "case define both roles explicitly."
        ),
        'standard_term': 'Director of Operations',
        'tier': 1,
        'source': 'python',
    }]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_CHECKS = (
    ('signal_codes_in_prose',  check_signal_codes_in_prose),
    ('undefined_acronyms',     check_undefined_acronyms_at_first_use),
    ('operations_role_drift',  check_operations_role_drift),
)


def run_editorial_python_checks(roadmap_text: str) -> list[dict]:
    """Run all Python editorial checks against the rendered roadmap text.

    Each check is independent — a failure in one does not block others.
    Failures are logged at WARNING level. Returns the combined item list.
    """
    items = []
    for name, fn in _CHECKS:
        try:
            check_items = fn(roadmap_text)
            logger.info(f"editorial_auditor.{name}: {len(check_items)} item(s)")
            items.extend(check_items)
        except Exception as exc:
            logger.warning(
                f"editorial_auditor.{name} failed: {exc}", exc_info=True
            )
    return items
