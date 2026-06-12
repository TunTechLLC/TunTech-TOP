"""Tests for api/services/narrator_auditor.py — pure functions, no DB or Claude required."""

from api.services.narrator_auditor import (
    AuditContext,
    audit_narrator_output,
    check_r_codes_resolve,
    check_finding_ids_resolve,
    check_root_cause_paragraphs,
    check_economic_impact_length,
    check_executive_snapshot,
    check_success_metric_format,
    check_domain_analysis_length,
    check_rule1_concentration,
    check_economic_figures_grounded,
    check_no_individual_names,
    check_revenue_at_risk_coherence,
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_NA,
)


def _empty_ctx():
    return AuditContext(
        engagement_id='E999',
        findings=[],
        roadmap=[],
        processed_files=[],
        signals=[],
        signal_coverage=[],
    )


# ---------- check_r_codes_resolve ----------

def test_r_codes_pass_when_all_resolve():
    narrator = {
        'executive_summary_opening': 'The governance initiative R001 must precede R002.',
    }
    ctx = AuditContext('E1', [], [{'item_id': 'R001'}, {'item_id': 'R002'}], [], [], [])
    result = check_r_codes_resolve(narrator, ctx)
    assert result.status == STATUS_PASS


def test_r_codes_fail_when_ghost():
    narrator = {
        'executive_summary_opening': 'R001 must precede R999 — a fabricated reference.',
    }
    ctx = AuditContext('E1', [], [{'item_id': 'R001'}], [], [], [])
    result = check_r_codes_resolve(narrator, ctx)
    assert result.status == STATUS_FAIL
    assert 'R999' in result.evidence


def test_r_codes_na_when_no_codes_in_prose():
    narrator = {'executive_summary_opening': 'The pricing governance initiative comes first.'}
    ctx = AuditContext('E1', [], [{'item_id': 'R001'}], [], [], [])
    result = check_r_codes_resolve(narrator, ctx)
    assert result.status == STATUS_NA


# ---------- check_finding_ids_resolve ----------

def test_finding_ids_pass_when_all_valid():
    narrator = {
        'executive_briefing': {
            'problems': [{'finding_id': 'F001', 'plain_title': 'x', 'impact_brief': 'y'}],
            'numbers':  [{'finding_id': 'F002', 'label': 'z'}],
        }
    }
    ctx = AuditContext('E1', [{'finding_id': 'F001'}, {'finding_id': 'F002'}], [], [], [], [])
    result = check_finding_ids_resolve(narrator, ctx)
    assert result.status == STATUS_PASS


def test_finding_ids_fail_when_ghost_in_briefing():
    narrator = {
        'executive_briefing': {
            'problems': [{'finding_id': 'F099', 'plain_title': 'x', 'impact_brief': 'y'}],
        }
    }
    ctx = AuditContext('E1', [{'finding_id': 'F001'}], [], [], [], [])
    result = check_finding_ids_resolve(narrator, ctx)
    assert result.status == STATUS_FAIL
    assert 'F099' in result.evidence


# ---------- check_root_cause_paragraphs ----------

def test_root_cause_passes_with_four_paragraphs():
    narrator = {'root_cause_narrative': 'Para 1.\n\nPara 2.\n\nPara 3.\n\nPara 4.'}
    assert check_root_cause_paragraphs(narrator, _empty_ctx()).status == STATUS_PASS


def test_root_cause_fails_with_three_paragraphs():
    narrator = {'root_cause_narrative': 'Para 1.\n\nPara 2.\n\nPara 3.'}
    result = check_root_cause_paragraphs(narrator, _empty_ctx())
    assert result.status == STATUS_FAIL
    assert '3' in result.evidence


def test_root_cause_fails_when_empty():
    assert check_root_cause_paragraphs({}, _empty_ctx()).status == STATUS_FAIL


# ---------- check_economic_impact_length ----------

def test_economic_impact_passes_with_two_sentences():
    narrator = {'economic_impact_narrative': 'First sentence. Second sentence.'}
    assert check_economic_impact_length(narrator, _empty_ctx()).status == STATUS_PASS


def test_economic_impact_fails_with_three_sentences():
    narrator = {'economic_impact_narrative': 'First. Second. Third.'}
    result = check_economic_impact_length(narrator, _empty_ctx())
    assert result.status == STATUS_FAIL


# ---------- check_executive_snapshot ----------

def test_snapshot_passes_with_short_sentences():
    snap = 'The diagnosis is structural. Active risk is client churn. CEO acts this week.'
    narrator = {'executive_briefing': {'executive_snapshot': snap}}
    assert check_executive_snapshot(narrator, _empty_ctx()).status == STATUS_PASS


def test_snapshot_fails_with_long_sentence():
    # 25-word first sentence — must trip the at-most-20-words rule
    snap = (
        'The diagnosis is structural and complex with many compounding factors that '
        'span multiple domains and require careful sequenced intervention across the firm '
        'over the next quarter. Short. Short.'
    )
    narrator = {'executive_briefing': {'executive_snapshot': snap}}
    result = check_executive_snapshot(narrator, _empty_ctx())
    assert result.status == STATUS_FAIL
    assert 'words' in result.evidence.lower() or 'long' in result.evidence.lower()


def test_snapshot_fails_with_too_many_sentences():
    snap = 'One. Two. Three. Four.'
    narrator = {'executive_briefing': {'executive_snapshot': snap}}
    result = check_executive_snapshot(narrator, _empty_ctx())
    assert result.status == STATUS_FAIL


# ---------- check_success_metric_format ----------

def test_success_metric_passes_with_format():
    narrator = {'initiative_details': [
        {'item_id': 'R001', 'success_metric': 'Track: First report produced. Complete: All engagements visible.'},
    ]}
    assert check_success_metric_format(narrator, _empty_ctx()).status == STATUS_PASS


def test_success_metric_fails_without_format():
    narrator = {'initiative_details': [
        {'item_id': 'R001', 'success_metric': 'All engagements have rate visibility.'},
    ]}
    result = check_success_metric_format(narrator, _empty_ctx())
    assert result.status == STATUS_FAIL
    assert 'R001' in result.evidence


# ---------- check_domain_analysis_length ----------

def test_domain_analysis_passes_with_short_narratives():
    narrator = {'domain_analysis': {
        'Delivery Operations': {'narrative': 'One. Two. Three.'},
        'Sales & Pipeline':    {'narrative': 'A. B.'},
    }}
    assert check_domain_analysis_length(narrator, _empty_ctx()).status == STATUS_PASS


def test_domain_analysis_fails_with_long_narrative():
    narrator = {'domain_analysis': {
        'Delivery Operations': {'narrative': 'One. Two. Three. Four.'},
    }}
    result = check_domain_analysis_length(narrator, _empty_ctx())
    assert result.status == STATUS_FAIL
    assert 'Delivery Operations' in result.evidence


# ---------- check_rule1_concentration ----------

def test_rule1_na_when_no_concentration_finding():
    ctx = AuditContext('E1', [{'finding_title': 'Margin Compression'}], [], [], [], [])
    assert check_rule1_concentration({}, ctx).status == STATUS_NA


def test_rule1_fails_when_concentration_initiative_in_scale():
    ctx = AuditContext(
        'E1',
        [{'finding_title': 'Revenue Concentration on Single Client'}],
        [{'item_id': 'R010', 'initiative_name': 'Account Concentration Stabilization', 'phase': 'Scale'}],
        [], [], [],
    )
    result = check_rule1_concentration({}, ctx)
    assert result.status == STATUS_FAIL
    assert 'R010' in result.evidence


def test_rule1_passes_when_concentration_initiative_in_stabilize():
    ctx = AuditContext(
        'E1',
        [{'finding_title': 'Revenue Concentration on Single Client'}],
        [{'item_id': 'R010', 'initiative_name': 'Account Concentration Stabilization', 'phase': 'Stabilize'}],
        [], [], [],
    )
    assert check_rule1_concentration({}, ctx).status == STATUS_PASS


# ---------- check_economic_figures_grounded ----------

def test_economic_figures_pass_when_matched():
    narrator = {'executive_summary_opening': 'Annual loss is $186K from delivery overruns.'}
    ctx = AuditContext(
        'E1',
        [{'confirmed_figure': 186_000.0, 'derived_figure': None, 'annual_drag_figure': None}],
        [], [], [], [],
    )
    assert check_economic_figures_grounded(narrator, ctx).status == STATUS_PASS


def test_economic_figures_pass_with_derived_label():
    narrator = {'executive_summary_opening': 'The margin gap is $644K (DERIVED: rate gap × hours).'}
    ctx = AuditContext('E1', [], [], [], [], [])
    assert check_economic_figures_grounded(narrator, ctx).status == STATUS_PASS


def test_economic_figures_pass_with_confirmed_label():
    """CONFIRMED label nearby grounds the figure, same as DERIVED."""
    narrator = {'executive_summary_opening': 'The most immediate exposure is the $130,000 (CONFIRMED) Milestone 4 payment.'}
    ctx = AuditContext('E1', [], [], [], [], [])
    assert check_economic_figures_grounded(narrator, ctx).status == STATUS_PASS


def test_economic_figures_pass_with_inferred_label():
    """INFERRED label nearby grounds the figure too."""
    narrator = {'executive_summary_opening': 'Industry data suggests $2.5M (INFERRED) in annual peer benchmark variance.'}
    ctx = AuditContext('E1', [], [], [], [], [])
    assert check_economic_figures_grounded(narrator, ctx).status == STATUS_PASS


def test_economic_figures_skips_hourly_rates():
    """Unit rates like '$175 per hour' are not economic impacts — skip them."""
    narrator = {'executive_summary_opening':
                'The fixed-fee project priced at $175 per hour achieves only 26% margin.'}
    ctx = AuditContext('E1', [], [], [], [], [])
    # No DB figures, no labels — would fail without the rate-skip logic
    assert check_economic_figures_grounded(narrator, ctx).status == STATUS_NA


def test_economic_figures_skips_small_amounts():
    """Figures under $1,000 are unit references, not engagement-level impacts."""
    narrator = {'executive_summary_opening':
                'The target rate of $185 has not been enforced; current realization is $172.'}
    ctx = AuditContext('E1', [], [], [], [], [])
    assert check_economic_figures_grounded(narrator, ctx).status == STATUS_NA


def test_economic_figures_fail_when_unmatched_and_no_label():
    narrator = {'executive_summary_opening': 'Annual loss is $500,000 from delivery overruns.'}
    ctx = AuditContext(
        'E1',
        [{'confirmed_figure': 186_000.0, 'derived_figure': None, 'annual_drag_figure': None}],
        [], [], [], [],
    )
    result = check_economic_figures_grounded(narrator, ctx)
    assert result.status == STATUS_FAIL
    assert '$500,000' in result.evidence


# ---------- check_no_individual_names ----------

def test_no_names_na_when_no_risk_rows():
    narrator = {'risk_table_rows': []}
    assert check_no_individual_names(narrator, _empty_ctx()).status == STATUS_NA


def test_no_names_fail_when_name_appears_in_risk():
    narrator = {'risk_table_rows': [
        {'risk': 'Sarah Chen continues to absorb scope without governance.',
         'likelihood': 'High',
         'mitigation': 'Define a decision rights matrix.'},
    ]}
    ctx = AuditContext(
        'E1',
        [],
        [],
        [],
        [{'notes': 'Sarah Chen said the PM was overallocated for three months.'}],
        [],
    )
    result = check_no_individual_names(narrator, ctx)
    assert result.status == STATUS_FAIL
    assert 'Sarah Chen' in result.evidence


def test_no_names_skips_org_name_without_verb_context():
    """'Glacier Point' is an org/account name — appears in signals without person-verbs.
    Must not be flagged as an individual name."""
    narrator = {'risk_table_rows': [
        {'risk': 'Glacier Point client escalates to formal dispute.',
         'likelihood': 'High',
         'mitigation': 'Activate contingency plan.'},
    ]}
    ctx = AuditContext(
        'E1',
        [],
        [],
        [],
        [
            {'notes': 'The Glacier Point engagement is over budget by 18%.'},
            {'notes': 'Glacier Point requested a status update last week.'},
        ],
        [],
    )
    result = check_no_individual_names(narrator, ctx)
    # Glacier Point has no person-verb context — should not be flagged
    assert result.status in (STATUS_NA, STATUS_PASS)


def test_no_names_skips_org_suffix_pattern_in_narrator():
    """Glacier Point escalation — 'escalation' is an org-suffix, not a person attribute.
    Even when signal notes use person-like verbs, the org-suffix pattern in narrator
    output should keep the name from being flagged."""
    narrator = {'risk_table_rows': [
        {'risk': 'Glacier Point escalation intensifies before the recovery plan.',
         'likelihood': 'High',
         'mitigation': 'Activate Priority Zero contingency.'},
    ]}
    ctx = AuditContext(
        'E1',
        [],
        [],
        [],
        # Glacier Point appears with "said" elsewhere — would normally make it a candidate
        [{'notes': 'Glacier Point said they would escalate by Q3.'}],
        [],
    )
    result = check_no_individual_names(narrator, ctx)
    assert result.status in (STATUS_NA, STATUS_PASS)


def test_dollar_regex_does_not_eat_following_letter():
    """Regex must not consume the first letter of a following word as a K/M/B suffix.
    '$13 below' must match '$13', not '$13 b'.
    '$130,000 Milestone' must match '$130,000', not '$130,000 M'.
    """
    from api.services.narrator_auditor import _DOLLAR_RE
    text = 'The rate was $172 per hour — $13 below target — against a $185 goal.'
    matches = [m.group(0) for m in _DOLLAR_RE.finditer(text)]
    assert '$13' in matches
    assert '$13 b' not in matches and '$13 B' not in matches

    text2 = 'The $130,000 Milestone 4 payment is at risk.'
    matches2 = [m.group(0) for m in _DOLLAR_RE.finditer(text2)]
    assert '$130,000' in matches2
    assert all('M' not in m or m.endswith('M') and m[:-1].replace(',', '').replace('.', '').isdigit() or 'M' in m and m.upper().endswith('M')
               for m in matches2)
    # Tighter check: the matched text for $130,000 should be exactly "$130,000"
    matched_130k = [m for m in matches2 if '130' in m]
    assert matched_130k == ['$130,000']


def test_dollar_regex_still_catches_suffix_amounts():
    """The suffix fix must not break legitimate K/M/B suffix matches."""
    from api.services.narrator_auditor import _DOLLAR_RE
    text = 'Annual drag is $1.84M with $186K bench cost and $221K+ floor.'
    matches = [m.group(0) for m in _DOLLAR_RE.finditer(text)]
    assert '$1.84M' in matches
    assert '$186K' in matches
    assert '$221K+' in matches


def test_no_names_excludes_names_in_finding_text():
    """Names appearing in finding titles are commercial/org references — excluded
    from candidates even if they have verb-like context elsewhere."""
    narrator = {'risk_table_rows': [
        {'risk': 'Meridian Financial relationship at risk.',
         'likelihood': 'High',
         'mitigation': 'Quarterly executive review.'},
    ]}
    ctx = AuditContext(
        'E1',
        [{'finding_title': 'Meridian Financial Concentration Risk',
          'root_cause': 'Single-client dependency.'}],
        [],
        [],
        [{'notes': 'Meridian Financial said the SLA was missed in March.'}],
        [],
    )
    result = check_no_individual_names(narrator, ctx)
    assert result.status in (STATUS_NA, STATUS_PASS)


# ---------- audit_narrator_output orchestrator ----------

def test_orchestrator_returns_summary_and_results():
    narrator = {
        'root_cause_narrative': 'P1.\n\nP2.\n\nP3.\n\nP4.',
        'executive_briefing': {'executive_snapshot': 'A. B. C.'},
    }
    report = audit_narrator_output(narrator, _empty_ctx())
    assert 'summary' in report
    assert 'results' in report
    assert {'pass', 'fail', 'na'} <= report['summary'].keys()
    assert len(report['results']) >= 10  # we have 13 checks
    # Every result has the three required keys
    for r in report['results']:
        assert {'dimension', 'status', 'evidence'} <= r.keys()
        assert r['status'] in ('pass', 'fail', 'na')


def test_orchestrator_catches_check_exceptions():
    # Pass a malformed narrator and make sure no exception escapes
    narrator = {'executive_briefing': 'this should be a dict, not a string'}
    report = audit_narrator_output(narrator, _empty_ctx())
    assert isinstance(report['results'], list)
    assert len(report['results']) > 0


# ---------- check_revenue_at_risk_coherence ----------

def _exec_finding(label, figure, ftype, valence='Negative'):
    return {
        'include_in_executive': 1,
        'valence': valence,
        'display_figure': figure,
        'figure_type': ftype,
        'display_label': label,
    }


def test_rar_fails_when_headline_dwarfed_by_larger_exposure():
    """The real E006 bug: the only direct_exposure finding is the $127K PMO opportunity
    cost, while the $2.8M Helix existential exposure is mis-tagged annual_drag. The headline
    'Revenue at Risk' understates the risk 22x — must flag."""
    findings = [
        _exec_finding('Ungoverned delivery management opportunity cost', '$127K', 'direct_exposure'),
        _exec_finding('Helix non-renewal revenue exposure', '$2.8M', 'annual_drag'),
        _exec_finding('Recoverable revenue left on table', '$980K', 'replacement_cost'),
    ]
    ctx = AuditContext('E006', findings, [], [], [], [])
    result = check_revenue_at_risk_coherence({}, ctx)
    assert result.status == STATUS_FAIL
    assert '$127K' in result.evidence
    assert '$2.8M' in result.evidence


def test_rar_passes_when_headline_is_largest_exposure():
    """Correctly tagged: the Helix exposure is the direct_exposure and is the largest figure."""
    findings = [
        _exec_finding('Helix non-renewal revenue exposure', '$2.8M', 'direct_exposure'),
        _exec_finding('Ungoverned delivery management opportunity cost', '$127K', 'annual_drag'),
        _exec_finding('Recoverable revenue left on table', '$980K', 'replacement_cost'),
    ]
    ctx = AuditContext('E006', findings, [], [], [], [])
    assert check_revenue_at_risk_coherence({}, ctx).status == STATUS_PASS


def test_rar_na_when_no_direct_exposure():
    """No direct_exposure finding → renderer emits no 'Revenue at Risk' headline → NA."""
    findings = [
        _exec_finding('Annual overrun drag', '$2.8M', 'annual_drag'),
        _exec_finding('Recoverable revenue', '$980K', 'replacement_cost'),
    ]
    ctx = AuditContext('E006', findings, [], [], [], [])
    assert check_revenue_at_risk_coherence({}, ctx).status == STATUS_NA


def test_rar_ignores_strength_findings():
    """A Positive-valence strength ($3.7M funding capacity) is not an exposure — it must not
    count as the 'larger figure' and trigger a false flag against a correct headline."""
    findings = [
        _exec_finding('Helix non-renewal revenue exposure', '$2.8M', 'direct_exposure'),
        _exec_finding('Gross profit funding capacity retained', '$3.7M', 'annual_drag', valence='Positive'),
    ]
    ctx = AuditContext('E006', findings, [], [], [], [])
    assert check_revenue_at_risk_coherence({}, ctx).status == STATUS_PASS
