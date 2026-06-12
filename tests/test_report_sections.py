"""Tests for api/services/report_sections.py pure helpers.

Focus: _classify_figure_type — the source-of-truth classifier that reads an economic
figure's NATURE from the economic_impact text the economics agent wrote, replacing the
old domain-lookup guess. Strings below are trimmed from the real E006 findings; this is
the regression guard for the "$127K Revenue at Risk" headline bug.
"""

from api.services.report_sections import _classify_figure_type, _prepopulate_display_figure
from api.routers.findings import _suggest_economic_figures


# ---------- direct_exposure: acute revenue at risk (drives the headline) ----------

def test_acute_revenue_at_risk_is_direct_exposure():
    """F052 Helix: the existential exposure. Was mis-defaulted to annual_drag by the
    'Finance and Commercial' domain map; must classify as direct_exposure so it becomes
    the 'Revenue at Risk' headline."""
    ei = ("$2.82M-$3.48M in revenue at risk in a non-renewal scenario (CONFIRMED magnitude: "
          "$3.48M from Financial Summary; $2.82M floor uses Portfolio Deck's 30% figure).")
    assert _classify_figure_type(ei, 'Finance and Commercial') == 'direct_exposure'


def test_regulatory_exposure_is_not_direct_exposure():
    """'regulatory exposure' / 'compliance exposure' must NOT capture the acute
    revenue-at-risk headline slot — the classifier keys on revenue/renewal loss phrasing,
    not the bare word 'exposure'."""
    ei = ("Regulatory exposure under HIPAA for unauthorized disclosure: up to $1.9M per "
          "violation category per year (INFERRED from regulatory schedule).")
    assert _classify_figure_type(ei, 'AI Readiness') != 'direct_exposure'


# ---------- opportunity: foregone / recoverable ----------

def test_opportunity_cost_per_year_is_opportunity_not_direct_exposure():
    """F054 PMO: $127K imputed opportunity cost. Was mis-defaulted to direct_exposure by
    the 'Project Governance / PMO' domain map (and wrongly became the headline). Must NOT
    be direct_exposure."""
    ei = ("Principal informal PMO opportunity cost -- billable hours diverted to ungoverned "
          "delivery management: $127K-$255K per year (INFERRED).")
    result = _classify_figure_type(ei, 'Project Governance / PMO')
    assert result == 'opportunity'
    assert result != 'direct_exposure'


def test_compound_text_classifies_by_primary_figure_not_secondary():
    """F055: the PRIMARY figure ($980K) is 'Foregone billable revenue' (opportunity), but a
    SECONDARY figure three sentences later says 'turnover cost / replacement cost'. The
    classifier must read the primary figure's lead-in, not the whole compound text."""
    ei = ("Foregone billable revenue from mid/junior underutilization: $980K-$1.64M per year "
          "(INFERRED: 30-35 staff x 27 point gap x recoverability factor x $245 rate). "
          "Hiring delay cost for two open senior reqs: ~$289K. "
          "Mid-level turnover cost at observed pace: $180K-$390K per year, replacement cost "
          "benchmarked at 75-150% of salary.")
    assert _classify_figure_type(ei, 'Resource Management') == 'opportunity'


# ---------- replacement_cost: turnover / rehire ----------

def test_turnover_cost_lead_is_replacement_cost():
    """F059: when the PRIMARY figure's lead-in is turnover/replacement, classify as such."""
    ei = ("Mid-level turnover cost at observed pace: $180K-$390K per year (INFERRED: 2 "
          "departures per 6 months x $90K-$195K replacement cost per engineer).")
    assert _classify_figure_type(ei, 'Human Resources') == 'replacement_cost'


# ---------- annual_drag and fallback ----------

def test_per_year_cost_without_other_signal_is_annual_drag():
    ei = "Change order leakage on fixed-fee engagements: $78K-$470K per year (INFERRED)."
    assert _classify_figure_type(ei, 'Delivery Operations') == 'annual_drag'


def test_no_signal_falls_back_to_domain_default():
    """When the text carries no nature signal, fall back to the domain map (prior behavior)
    — never regresses an unphrased figure, only corrects phrased ones."""
    ei = "The structural cost is significant but is captured under another finding."
    # Resource Management domain default is replacement_cost.
    assert _classify_figure_type(ei, 'Resource Management') == 'replacement_cost'


def test_empty_text_falls_back_to_domain_default():
    assert _classify_figure_type('', 'Finance and Commercial') == 'annual_drag'
    assert _classify_figure_type(None, 'Human Resources') == 'replacement_cost'


# ---------- valence-aware: a strength is funding capacity, never an exposure ----------

def test_strength_valence_is_funding_capacity():
    """The F060 bug: a Positive/Dual strength figure ($3.67M gross profit) carries no
    exposure/drag signal in its prose, so it fell through to the domain default
    (Consulting Economics -> annual_drag) and rendered as a 'drag'. With valence it must
    classify as funding_capacity instead."""
    ei = ("Reported gross profit of approximately $3.67M (DERIVED: $9.4M TTM revenue x 39% "
          "gross margin) provides the financial runway for structural investment.")
    assert _classify_figure_type(ei, 'Consulting Economics', 'Positive') == 'funding_capacity'
    assert _classify_figure_type(ei, 'Consulting Economics', 'Dual') == 'funding_capacity'
    # Without strength valence the same text+domain still falls back to the domain default.
    assert _classify_figure_type(ei, 'Consulting Economics') == 'annual_drag'


def test_suggest_economic_figures_blank_for_strength():
    """A strength has no exposure breakdown — the confirmed/derived/annual-drag exposure
    columns must come back empty so the review UI doesn't show a strength as a derived
    exposure / annual drag (the '$3.7M Annual Drag' on a strength)."""
    ei = ("Reported gross profit of approximately $3.67M (DERIVED) is the funding runway "
          "for the Year 1 structural investment.")
    blank = _suggest_economic_figures(ei, 'Consulting Economics', None, 'Positive')
    assert blank['suggested_confirmed_figure'] is None
    assert blank['suggested_derived_figure'] is None
    assert blank['suggested_annual_drag_figure'] is None
    # A negative finding in the same domain still gets the annual-drag suggestion.
    neg = _suggest_economic_figures(
        "Change order leakage: $470K per year (DERIVED).", 'Consulting Economics', None)
    assert neg['suggested_annual_drag_figure'] is not None


# ---------- unit-rate / sub-$1K figures are not engagement magnitudes (F007) ----------

def test_per_violation_unit_rates_yield_no_display_figure():
    """F007: a HIPAA penalty schedule ('$100-$50,000 per violation ... up to $1.9M per
    violation category') is a regulatory rate ceiling, not a clean economic magnitude.
    The extractor grabbed '$100' as the executive figure; it must now suggest no figure."""
    ei = ("Regulatory exposure under HIPAA for unauthorized disclosure: $100-$50,000 per "
          "violation with annual maximums up to $1.9M per violation category (INFERRED from "
          "regulatory schedule — an unmitigated risk exposure, not a current cost).")
    fig, _label, _ftype = _prepopulate_display_figure(ei, 'AI Readiness', None)
    assert fig is None


def test_annualized_figure_still_extracted():
    """The skip must not eat legitimate 'per year' annual figures — only per-unit rates."""
    ei = "Change order leakage on fixed-fee engagements: $78K-$470K per year (INFERRED)."
    fig, _label, _ftype = _prepopulate_display_figure(ei, 'Delivery Operations', None)
    assert fig is not None  # $78K survives — 'per year' is not a unit rate
