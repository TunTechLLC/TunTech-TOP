"""Mechanical checks on Report Narrator JSON output before Word render.

The auditor produces a structured trust report that lets the consultant skip
dimensions of review. Each check is a deterministic function — no Claude calls,
no DB writes. Failures include evidence (the offending text snippet).

Adding a check:
  1. Write a function check_X(narrator: dict, ctx: AuditContext) -> AuditResult
  2. Append it to AUDIT_CHECKS

Status values:
  - 'pass' — check applied and passed
  - 'fail' — check applied and failed (evidence populated)
  - 'na'   — check did not apply to this engagement (e.g. no findings of the required shape)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

STATUS_PASS = 'pass'
STATUS_FAIL = 'fail'
STATUS_NA   = 'na'


@dataclass
class AuditResult:
    dimension: str
    status: str
    evidence: str | None = None


@dataclass
class AuditContext:
    engagement_id: str
    findings: list[dict]
    roadmap: list[dict]
    processed_files: list[dict]
    signals: list[dict]
    signal_coverage: list[dict]
    firm_name: str = ''


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------

# Negative lookahead `(?![A-Za-z])` prevents the K/M/B suffix from consuming the first
# letter of a following word — e.g. "$130,000 Milestone" must match "$130,000", not "$130,000 M".
_DOLLAR_RE = re.compile(r'\$\d[\d,]*(?:\.\d+)?(?:\s*[KMB])?\+?(?![A-Za-z])', re.IGNORECASE)
_R_CODE_RE = re.compile(r'\bR\d{3,4}\b')
_F_CODE_RE = re.compile(r'\bF\d{3,4}\b')
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'])')
_EVIDENTIARY_LABELS = ('CONFIRMED', 'DERIVED', 'INFERRED')
# Dollar figures below this threshold are skipped by check_economic_figures_grounded —
# they're almost always unit rates ($175/hr) or small references, not the engagement-level
# economic impacts (typically $10K+) the audit tries to ground against DB structured fields.
_ECONOMIC_FIGURE_MIN = 1_000.0
_UNIT_RATE_SUFFIX_RE = re.compile(
    r'^\s*(?:per\s+(?:hour|day|hr|unit|month|year|week|engagement|deal|head|seat)'
    r'|/\s*(?:hr|hour|day|unit|month|year|week)'
    r'|an\s+hour)\b',
    re.IGNORECASE,
)
_PERSON_VERBS_RE = re.compile(
    r'\b(?:said|says|noted|mentioned|asked|explained|argued|reported|stated|'
    r'complained|confirmed|denied|expressed|emphasized|indicated|decided|refused|'
    r'agreed|recalled|observed|described|suggested|recommended|told|replied|'
    r'added|believes|believed|wants|wanted|thinks|thought|claims|claimed)\b',
    re.IGNORECASE,
)
_PERSON_CONTEXT_PREFIX_RE = re.compile(
    r'\b(?:according\s+to|per|interviewed)\s*$', re.IGNORECASE,
)
# Org-suffix pattern — a two-cap-word name followed by an org/process noun. Used to filter
# out client/account/project names that the simpler person-verb check can miss (e.g.
# "Glacier Point escalation" — escalation is not a person verb but signals an org context).
_ORG_SUFFIX_RE = re.compile(
    r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\s+'
    r"(?:account|engagement|project|relationship|client|deal|contract|"
    r"escalation|dispute|claim|recovery|operations|team|portfolio|"
    r"firm|company|organization|corp(?:oration)?|inc|llc|partners|group|"
    r"holdings|services|systems|solutions|associates|'s\b)",
    re.IGNORECASE,
)

_TOP_LEVEL_PROSE = (
    'executive_summary_opening',
    'executive_summary_para1',
    'executive_summary_para2',
    'executive_summary_para3',
    'executive_summary_strengths',
    'engagement_overview_paragraph',
    'root_cause_narrative',
    'economic_impact_narrative',
    'future_state_narrative',
    'execution_path_rationale',
    'margin_trend_brief',
)

_TABLE_KEYS = (
    'priority_zero_table_rows',
    'risk_table_rows',
    'dependency_table_rows',
    'next_steps_rows',
    'future_state_table_rows',
    'roadmap_overview_rows',
)


def _all_prose(narrator: dict) -> str:
    """Concatenate every prose-bearing field for cross-cutting scans (R-codes, dollars)."""
    parts: list[str] = []
    for k in _TOP_LEVEL_PROSE:
        v = narrator.get(k)
        if isinstance(v, str):
            parts.append(v)

    eb = narrator.get('executive_briefing') or {}
    if isinstance(eb, dict):
        for k in ('executive_snapshot',):
            v = eb.get(k)
            if isinstance(v, str):
                parts.append(v)
        for prob in (eb.get('problems') or []):
            if isinstance(prob, dict):
                for k in ('plain_title', 'impact_brief'):
                    v = prob.get(k)
                    if isinstance(v, str):
                        parts.append(v)
        for num in (eb.get('numbers') or []):
            if isinstance(num, dict) and isinstance(num.get('label'), str):
                parts.append(num['label'])

    da = narrator.get('domain_analysis') or {}
    if isinstance(da, dict):
        for v in da.values():
            if isinstance(v, dict) and isinstance(v.get('narrative'), str):
                parts.append(v['narrative'])

    rr = narrator.get('roadmap_rationale') or {}
    if isinstance(rr, dict):
        for v in rr.values():
            if isinstance(v, str):
                parts.append(v)

    for det in (narrator.get('initiative_details') or []):
        if isinstance(det, dict) and isinstance(det.get('success_metric'), str):
            parts.append(det['success_metric'])

    for tk in _TABLE_KEYS:
        for row in (narrator.get(tk) or []):
            if not isinstance(row, dict):
                continue
            for v in row.values():
                if isinstance(v, str):
                    parts.append(v)
                elif isinstance(v, list):
                    parts.extend(x for x in v if isinstance(x, str))

    return '\n'.join(parts)


def _normalize_dollar(raw: str) -> float | None:
    """Convert '$186K' / '$1.84M' / '$35,000' to a float. Returns None on failure."""
    s = raw.strip().lstrip('$').rstrip('+').strip()
    mult = 1.0
    if s and s[-1].upper() == 'K':
        mult, s = 1_000, s[:-1]
    elif s and s[-1].upper() == 'M':
        mult, s = 1_000_000, s[:-1]
    elif s and s[-1].upper() == 'B':
        mult, s = 1_000_000_000, s[:-1]
    s = s.replace(',', '').strip()
    try:
        return float(s) * mult
    except (ValueError, TypeError):
        return None


def _sentences(text: str) -> list[str]:
    text = (text or '').strip()
    if not text:
        return []
    return [p.strip() for p in _SENTENCE_SPLIT_RE.split(text) if p.strip()]


def _word_count(text: str) -> int:
    return len([w for w in (text or '').split() if w.strip()])


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n] + '…'


def _fmt_dollar(v: float) -> str:
    """Format a float as a short dollar string for evidence messages."""
    if v >= 1_000_000:
        return f'${v / 1_000_000:.1f}M'
    if v >= 1_000:
        return f'${v / 1_000:.0f}K'
    return f'${v:.0f}'


# ------------------------------------------------------------------
# Checks
# ------------------------------------------------------------------

def check_r_codes_resolve(narrator: dict, ctx: AuditContext) -> AuditResult:
    """Every R-code in prose resolves to a real roadmap item."""
    valid = {item.get('item_id') for item in ctx.roadmap if item.get('item_id')}
    referenced = set(_R_CODE_RE.findall(_all_prose(narrator)))
    ghosts = sorted(referenced - valid)
    dim = 'R-codes in prose resolve to real roadmap items'
    if not referenced:
        return AuditResult(dim, STATUS_NA, 'No R-codes found in prose')
    if not ghosts:
        return AuditResult(dim, STATUS_PASS)
    return AuditResult(dim, STATUS_FAIL, f'Ghost R-codes: {", ".join(ghosts)}')


def check_finding_ids_resolve(narrator: dict, ctx: AuditContext) -> AuditResult:
    """Every finding_id in executive_briefing (and F-codes in prose) resolves to a real finding."""
    valid = {f.get('finding_id') for f in ctx.findings if f.get('finding_id')}
    eb = narrator.get('executive_briefing') or {}
    referenced: set[str] = set()
    for prob in (eb.get('problems') or []):
        if isinstance(prob, dict) and prob.get('finding_id'):
            referenced.add(prob['finding_id'])
    for num in (eb.get('numbers') or []):
        if isinstance(num, dict) and num.get('finding_id'):
            referenced.add(num['finding_id'])
    referenced.update(_F_CODE_RE.findall(_all_prose(narrator)))
    ghosts = sorted(referenced - valid)
    dim = 'Finding IDs resolve to real findings'
    if not referenced:
        return AuditResult(dim, STATUS_NA, 'No finding references found')
    if not ghosts:
        return AuditResult(dim, STATUS_PASS)
    return AuditResult(dim, STATUS_FAIL, f'Ghost finding IDs: {", ".join(ghosts)}')


def check_economic_figures_grounded(narrator: dict, ctx: AuditContext) -> AuditResult:
    """Every dollar figure in prose matches a finding structured figure, or carries
    a CONFIRMED/DERIVED/INFERRED label nearby.

    Skips: unit rates ($175 per hour) and figures under $1,000 (almost always rates
    or small references, not engagement-level economic impacts).
    """
    db_figs: set[float] = set()
    for f in ctx.findings:
        for col in ('confirmed_figure', 'derived_figure', 'annual_drag_figure'):
            v = f.get(col)
            if isinstance(v, (int, float)):
                db_figs.add(float(v))
        disp = f.get('display_figure')
        if isinstance(disp, str) and disp.strip():
            parsed = _normalize_dollar(disp)
            if parsed is not None:
                db_figs.add(parsed)

    text = _all_prose(narrator)
    matches = list(_DOLLAR_RE.finditer(text))
    dim = 'Economic figures grounded in DB or labeled (CONFIRMED/DERIVED/INFERRED)'
    if not matches:
        return AuditResult(dim, STATUS_NA, 'No dollar figures in narrator prose')

    actionable = 0    # figures that survived filtering and were actually checked
    ungrounded: list[str] = []
    for m in matches:
        raw = m.group(0)
        val = _normalize_dollar(raw)
        if val is None:
            continue
        # Skip unit rates and small references — not engagement-level economic impacts
        if val < _ECONOMIC_FIGURE_MIN:
            continue
        tail_short = text[m.end():m.end() + 30]
        if _UNIT_RATE_SUFFIX_RE.match(tail_short):
            continue
        actionable += 1
        # Match if any DB figure is within 5% (handles $1.84M vs $1.8M rounding)
        if db_figs and any(
            abs(val - db) / max(val, db, 1.0) < 0.05 for db in db_figs
        ):
            continue
        # Accept if any evidentiary label sits within 120 chars after the figure
        tail = text[m.end():m.end() + 120].upper()
        if any(label in tail for label in _EVIDENTIARY_LABELS):
            continue
        # Or within 60 chars before
        head = text[max(0, m.start() - 60):m.start()].upper()
        if any(label in head for label in _EVIDENTIARY_LABELS):
            continue
        ctx_start = max(0, m.start() - 30)
        ctx_end = min(len(text), m.end() + 30)
        snippet = text[ctx_start:ctx_end].replace('\n', ' ').strip()
        ungrounded.append(f'"{raw}" — ...{snippet}...')

    if not ungrounded:
        if actionable == 0:
            return AuditResult(dim, STATUS_NA,
                               'No engagement-level economic figures in prose (only unit rates/small amounts)')
        return AuditResult(dim, STATUS_PASS, f'{actionable} figure(s) checked')
    preview = ' | '.join(ungrounded[:5]) + (f' [+{len(ungrounded) - 5} more]' if len(ungrounded) > 5 else '')
    return AuditResult(dim, STATUS_FAIL, f'{len(ungrounded)} ungrounded figure(s): {preview}')


def check_root_cause_paragraphs(narrator: dict, ctx: AuditContext) -> AuditResult:
    """root_cause_narrative is exactly 4 paragraphs (Rule from REPORT_NARRATOR_PROMPT)."""
    text = narrator.get('root_cause_narrative') or ''
    dim = 'Root cause narrative is exactly 4 paragraphs'
    if not text.strip():
        return AuditResult(dim, STATUS_FAIL, 'root_cause_narrative is missing or empty')
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) == 4:
        return AuditResult(dim, STATUS_PASS)
    return AuditResult(dim, STATUS_FAIL, f'Found {len(paragraphs)} paragraph(s), expected 4')


def check_economic_impact_length(narrator: dict, ctx: AuditContext) -> AuditResult:
    """economic_impact_narrative is at most 2 sentences."""
    text = narrator.get('economic_impact_narrative') or ''
    dim = 'Economic impact narrative is at most 2 sentences'
    if not text.strip():
        return AuditResult(dim, STATUS_NA, 'No economic impact narrative')
    n = len(_sentences(text))
    if n <= 2:
        return AuditResult(dim, STATUS_PASS)
    return AuditResult(dim, STATUS_FAIL, f'{n} sentences (max 2): "{_truncate(text, 240)}"')


def check_executive_snapshot(narrator: dict, ctx: AuditContext) -> AuditResult:
    """executive_snapshot has at most 3 sentences and each is at most 20 words."""
    snap = (narrator.get('executive_briefing') or {}).get('executive_snapshot') or ''
    dim = 'Executive snapshot: at most 3 sentences, each at most 20 words'
    if not snap.strip():
        return AuditResult(dim, STATUS_FAIL, 'executive_snapshot is missing or empty')
    sents = _sentences(snap)
    issues: list[str] = []
    if len(sents) > 3:
        issues.append(f'{len(sents)} sentences')
    long_sents = [(i + 1, _word_count(s)) for i, s in enumerate(sents) if _word_count(s) > 20]
    if long_sents:
        issues.append('long sentences: ' + ', '.join(f'#{i} ({n} words)' for i, n in long_sents))
    if not issues:
        return AuditResult(dim, STATUS_PASS)
    return AuditResult(dim, STATUS_FAIL, '; '.join(issues))


def check_success_metric_format(narrator: dict, ctx: AuditContext) -> AuditResult:
    """Every success_metric follows 'Track: ... Complete: ...' format (Rule 9)."""
    details = narrator.get('initiative_details') or []
    dim = 'success_metric uses "Track: ... Complete: ..." format'
    if not details:
        return AuditResult(dim, STATUS_NA, 'No initiative_details to check')
    pattern = re.compile(r'Track:\s*.+?Complete:\s*.+', re.IGNORECASE | re.DOTALL)
    failures: list[str] = []
    for det in details:
        if not isinstance(det, dict):
            continue
        item_id = det.get('item_id') or '?'
        metric = det.get('success_metric') or ''
        if not pattern.search(metric):
            failures.append(f'{item_id}: "{_truncate(metric, 80)}"')
    if not failures:
        return AuditResult(dim, STATUS_PASS)
    preview = ' | '.join(failures[:5]) + (f' [+{len(failures) - 5} more]' if len(failures) > 5 else '')
    return AuditResult(dim, STATUS_FAIL, f'{len(failures)} item(s) missing format: {preview}')


def check_domain_analysis_length(narrator: dict, ctx: AuditContext) -> AuditResult:
    """Each domain_analysis narrative is at most 3 sentences."""
    da = narrator.get('domain_analysis') or {}
    dim = 'Domain analysis narratives at most 3 sentences each'
    if not da:
        return AuditResult(dim, STATUS_NA, 'No domain_analysis entries')
    failures: list[str] = []
    for domain, payload in da.items():
        if not isinstance(payload, dict):
            continue
        n = len(_sentences(payload.get('narrative') or ''))
        if n > 3:
            failures.append(f'{domain}: {n} sentences')
    if not failures:
        return AuditResult(dim, STATUS_PASS)
    return AuditResult(dim, STATUS_FAIL, '; '.join(failures))


def check_quick_wins_eligibility(narrator: dict, ctx: AuditContext) -> AuditResult:
    """Roadmap items eligible for the Quick Wins section are all priority=High + effort=Low.

    Quick wins is computed from the roadmap by the renderer (priority=High AND effort=Low,
    capped at 5). This check verifies the underlying roadmap data is consistent — that any
    item the renderer will pick actually satisfies both criteria.
    """
    eligible = [r for r in ctx.roadmap if r.get('priority') == 'High' and r.get('effort') == 'Low']
    dim = 'Quick Wins items satisfy High priority + Low effort'
    if not eligible:
        return AuditResult(dim, STATUS_NA, 'No qualifying items — section will be omitted')
    return AuditResult(dim, STATUS_PASS, f'{len(eligible)} qualifying item(s) (rendered cap: 5)')


def check_coverage_completeness(narrator: dict, ctx: AuditContext) -> AuditResult:
    """Signal coverage map populated for this engagement."""
    dim = 'Signal coverage map present'
    if ctx.signal_coverage:
        return AuditResult(dim, STATUS_PASS, f'{len(ctx.signal_coverage)} coverage row(s)')
    return AuditResult(dim, STATUS_NA,
                       'No coverage rows — engagement processed before coverage feature, '
                       'or all library signals were observed')


def check_rule1_concentration(narrator: dict, ctx: AuditContext) -> AuditResult:
    """Rule 1 — revenue concentration stabilization belongs in Stabilize, not Scale."""
    has_concentration = any(
        'concentration' in (f.get('finding_title') or '').lower()
        or 'concentration' in (f.get('root_cause') or '').lower()
        for f in ctx.findings
    )
    dim = 'Rule 1 — concentration stabilization not placed in Scale'
    if not has_concentration:
        return AuditResult(dim, STATUS_NA, 'No revenue concentration finding in engagement')

    suspect: list[str] = []
    for item in ctx.roadmap:
        name = (item.get('initiative_name') or '').lower()
        looks_like_stabilization = (
            'concentration' in name
            or ('stabiliz' in name and 'account' in name)
            or ('stabiliz' in name and 'client' in name)
        )
        if looks_like_stabilization and item.get('phase') == 'Scale':
            suspect.append(f"{item.get('item_id', '?')}: {item.get('initiative_name', '?')}")
    if not suspect:
        return AuditResult(dim, STATUS_PASS)
    return AuditResult(dim, STATUS_FAIL, 'Stabilization-shaped initiatives in Scale: ' + '; '.join(suspect))


_ROLE_TOKENS = {
    'Director', 'Chief', 'Vice', 'President', 'Senior', 'Lead', 'Manager', 'Officer',
    'Executive', 'Project', 'Operations', 'Sales', 'Finance', 'Marketing', 'Engineering',
    'Delivery', 'Account', 'Client', 'Customer', 'Consulting', 'Consultant', 'Partner',
    'Head', 'Principal', 'Associate', 'Analyst', 'Coordinator',
}


def check_no_individual_names(narrator: dict, ctx: AuditContext) -> AuditResult:
    """Individual IC names should not appear in risk_table_rows (HR exposure prevention).

    Heuristic, two-stage:
      1. Extract candidate names from signal notes — two capitalized words, neither
         a role token, AND appearing with a person-verb context nearby (said, noted,
         "according to X", etc.). Pure proper-noun patterns without person context
         are filtered out — eliminates "Glacier Point" and similar org/project names.
      2. Exclude any candidate that also appears in a finding title or root_cause.
         Findings are anonymized — names appearing there are commercial/org references.

    Dimension labeled "potential" so the consultant treats flags as review prompts,
    not categorical violations.
    """
    risk_rows = narrator.get('risk_table_rows') or []
    dim = 'No individual names in risk rows (potential HR exposure)'
    if not risk_rows:
        return AuditResult(dim, STATUS_NA, 'No risk_table_rows')

    name_re = re.compile(r'\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b')
    candidates: set[str] = set()
    for s in ctx.signals:
        notes = s.get('notes') or ''
        for m in name_re.finditer(notes):
            first, second = m.group(1), m.group(2)
            if first in _ROLE_TOKENS or second in _ROLE_TOKENS:
                continue
            head = notes[max(0, m.start() - 30):m.start()]
            tail = notes[m.end():m.end() + 80]
            has_person_context = (
                _PERSON_VERBS_RE.search(tail)
                or _PERSON_VERBS_RE.search(head)
                or _PERSON_CONTEXT_PREFIX_RE.search(head)
            )
            if has_person_context:
                candidates.add(f'{first} {second}')

    # Exclude the engagement firm name if known
    if ctx.firm_name:
        candidates.discard(ctx.firm_name)

    # Exclude commercial/org references that appear in finding titles or root_cause —
    # those texts are anonymized, so names appearing there are not individuals.
    finding_text = ' '.join(
        ((f.get('finding_title') or '') + ' ' + (f.get('root_cause') or ''))
        for f in ctx.findings
    )
    org_matches = name_re.findall(finding_text)
    org_names = {f'{a} {b}' for a, b in org_matches}
    candidates -= org_names

    # Exclude any candidate that appears with an org-suffix pattern (X account, X engagement,
    # X escalation, etc.) anywhere in the source data or the narrator's own output. This
    # catches client/project names the person-verb filter misses.
    org_scan_text = (
        ' '.join((s.get('notes') or '') for s in ctx.signals)
        + ' ' + finding_text
        + ' ' + _all_prose(narrator)
    )
    candidates -= set(_ORG_SUFFIX_RE.findall(org_scan_text))

    if not candidates:
        return AuditResult(dim, STATUS_NA, 'No candidate individual names detected after filtering')

    hits: list[str] = []
    for row in risk_rows:
        if not isinstance(row, dict):
            continue
        row_text = ' '.join(v for v in row.values() if isinstance(v, str))
        for name in candidates:
            if name in row_text:
                hits.append(f'"{name}" in risk: "{_truncate(row.get("risk") or "?", 60)}"')
    if not hits:
        return AuditResult(dim, STATUS_PASS)
    preview = ' | '.join(hits[:5]) + (f' [+{len(hits) - 5} more]' if len(hits) > 5 else '')
    return AuditResult(dim, STATUS_FAIL, preview)


def check_revenue_at_risk_coherence(narrator: dict, ctx: AuditContext) -> AuditResult:
    """The executive 'Revenue at Risk' headline must be the largest exposure on the page.

    The renderer (report_generator) selects the 'Revenue at Risk' headline from findings
    tagged ``figure_type == 'direct_exposure'``. If a materially larger non-strength
    executive figure exists, the headline is understating the firm's risk — almost always
    a figure_type mis-tag, where the true existential exposure is tagged 'annual_drag'
    while a smaller cost is tagged 'direct_exposure'. This is the class behind the E006
    "$127K vs $2.8M Helix exposure" and E004 "$186K" headline errors — a real DB figure
    landing in the wrong executive slot, which check_economic_figures_grounded cannot catch
    (the number IS grounded, just mis-placed).

    Strengths (Positive/Dual valence) are excluded — a strength figure is not an exposure.
    Dimension marked 'potential' — a review prompt, not a categorical violation.
    """
    dim = 'Revenue-at-risk headline is the largest executive exposure (potential mis-tag)'

    exec_figs: list[tuple[dict, float]] = []
    for f in ctx.findings:
        if not f.get('include_in_executive'):
            continue
        if (f.get('valence') or '').lower() in ('positive', 'dual'):
            continue
        val = _normalize_dollar(f.get('display_figure') or '')
        if val is not None:
            exec_figs.append((f, val))

    direct = [(f, v) for (f, v) in exec_figs if f.get('figure_type') == 'direct_exposure']
    if not direct:
        # No direct_exposure finding → the renderer does not emit a "Revenue at Risk"
        # headline (it falls back to the largest figure under a different label).
        return AuditResult(dim, STATUS_NA,
                           "No direct_exposure finding — no 'Revenue at Risk' headline produced")

    headline_val = sum(v for (_, v) in direct)  # renderer sums when more than one
    others = [(f, v) for (f, v) in exec_figs if f.get('figure_type') != 'direct_exposure']
    if not others:
        return AuditResult(dim, STATUS_PASS,
                           f'Headline revenue-at-risk ({_fmt_dollar(headline_val)}) is the only executive exposure')

    big_f, big_v = max(others, key=lambda fv: fv[1])
    direct_label = '; '.join(
        (f.get('display_label') or f.get('finding_title') or '?') for f, _ in direct
    )
    # Require a 1.5x material gap so near-ties from rounding do not flag.
    if big_v >= headline_val * 1.5:
        return AuditResult(
            dim, STATUS_FAIL,
            f"Headline 'Revenue at Risk' is {_fmt_dollar(headline_val)} "
            f"({_truncate(direct_label, 50)}), but a larger executive figure "
            f"{_fmt_dollar(big_v)} (\"{_truncate(big_f.get('display_label') or big_f.get('finding_title') or '?', 50)}\", "
            f"tagged {big_f.get('figure_type') or 'untyped'}) suggests the headline understates "
            f"the risk — verify figure_type tags."
        )
    return AuditResult(dim, STATUS_PASS,
                       f'Headline revenue-at-risk ({_fmt_dollar(headline_val)}) is the largest executive exposure')


# ------------------------------------------------------------------
# Registry and orchestrator
# ------------------------------------------------------------------

AUDIT_CHECKS: tuple[Callable[[dict, AuditContext], AuditResult], ...] = (
    check_r_codes_resolve,
    check_finding_ids_resolve,
    check_economic_figures_grounded,
    check_root_cause_paragraphs,
    check_economic_impact_length,
    check_executive_snapshot,
    check_success_metric_format,
    check_domain_analysis_length,
    check_quick_wins_eligibility,
    check_coverage_completeness,
    check_rule1_concentration,
    check_no_individual_names,
    check_revenue_at_risk_coherence,
)


def audit_narrator_output(narrator: dict, ctx: AuditContext) -> dict:
    """Run all mechanical checks. Returns a structured trust report:

        {
            'summary': {'pass': N, 'fail': N, 'na': N},
            'results': [{'dimension', 'status', 'evidence'}, ...],
        }
    """
    results: list[AuditResult] = []
    for check in AUDIT_CHECKS:
        try:
            results.append(check(narrator, ctx))
        except Exception as e:
            results.append(AuditResult(
                dimension=check.__name__,
                status=STATUS_FAIL,
                evidence=f'Check raised {type(e).__name__}: {e}',
            ))
    return {
        'summary': {
            'pass': sum(1 for r in results if r.status == STATUS_PASS),
            'fail': sum(1 for r in results if r.status == STATUS_FAIL),
            'na':   sum(1 for r in results if r.status == STATUS_NA),
        },
        'results': [
            {'dimension': r.dimension, 'status': r.status, 'evidence': r.evidence}
            for r in results
        ],
    }
