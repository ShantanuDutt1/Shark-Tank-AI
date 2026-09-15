"""
Tests for `utils.financial_calculations` (Release 0.8). Pure functions,
no fixtures needed -- every edge case (missing input, zero/negative
denominator) must return `None`, never raise, never fabricate.
"""

from __future__ import annotations

import pytest

from utils.financial_calculations import (
    apply_growth_delta,
    arr_multiple,
    dilution_pct,
    gross_margin_pct,
    implied_post_money_valuation,
    implied_pre_money_valuation,
    ltv_to_cac,
    monthly_burn,
    operating_margin_pct,
    revenue_growth_pct,
    revenue_multiple,
    runway_months,
)


def test_implied_post_money_valuation():
    assert implied_post_money_valuation(500_000, 10) == pytest.approx(5_000_000)


def test_implied_post_money_valuation_missing_inputs():
    assert implied_post_money_valuation(None, 10) is None
    assert implied_post_money_valuation(500_000, None) is None


def test_implied_post_money_valuation_zero_or_negative_equity():
    assert implied_post_money_valuation(500_000, 0) is None
    assert implied_post_money_valuation(500_000, -5) is None


def test_implied_pre_money_valuation():
    assert implied_pre_money_valuation(5_000_000, 500_000) == pytest.approx(4_500_000)


def test_implied_pre_money_valuation_negative_result_is_none():
    """An investment larger than the post-money figure is not a valid
    pre-money value -- never return a fabricated negative number."""
    assert implied_pre_money_valuation(400_000, 500_000) is None


def test_revenue_multiple():
    assert revenue_multiple(5_000_000, 1_000_000) == pytest.approx(5.0)


def test_revenue_multiple_zero_revenue_is_none():
    assert revenue_multiple(5_000_000, 0) is None


def test_arr_multiple():
    assert arr_multiple(5_000_000, 500_000) == pytest.approx(10.0)


def test_gross_margin_pct():
    assert gross_margin_pct(1_000_000, 300_000) == pytest.approx(70.0)


def test_gross_margin_pct_zero_revenue_is_none():
    assert gross_margin_pct(0, 100) is None


def test_gross_margin_pct_negative_cogs_still_computes():
    """Not every negative input is invalid -- COGS itself must be
    non-negative in reality, but this function trusts its caller to
    have validated that separately; the formula itself handles it."""
    assert gross_margin_pct(1_000_000, 1_200_000) == pytest.approx(-20.0)


def test_operating_margin_pct():
    assert operating_margin_pct(100_000, 1_000_000) == pytest.approx(10.0)


def test_revenue_growth_pct():
    assert revenue_growth_pct(1_500_000, 1_000_000) == pytest.approx(50.0)


def test_revenue_growth_pct_missing_previous_is_none():
    assert revenue_growth_pct(1_500_000, None) is None


def test_revenue_growth_pct_zero_previous_is_none():
    assert revenue_growth_pct(1_500_000, 0) is None


def test_monthly_burn():
    assert monthly_burn(600_000, 400_000, 4) == pytest.approx(50_000)


def test_monthly_burn_cash_flow_positive_returns_negative_not_error():
    """Cash grew over the period -- a legitimate result, not an error."""
    assert monthly_burn(400_000, 600_000, 4) == pytest.approx(-50_000)


def test_monthly_burn_zero_months_is_none():
    assert monthly_burn(600_000, 400_000, 0) is None


def test_runway_months():
    assert runway_months(300_000, 50_000) == pytest.approx(6.0)


def test_runway_months_zero_burn_is_none():
    """Zero burn implies infinite runway by the raw formula -- return
    None rather than fabricating either 0 or infinity."""
    assert runway_months(300_000, 0) is None


def test_runway_months_negative_cash_is_none():
    assert runway_months(-1000, 50_000) is None


def test_dilution_pct():
    assert dilution_pct(500_000, 5_000_000) == pytest.approx(10.0)


def test_dilution_pct_never_infers_existing_cap_table():
    """Only reflects the single investment's own terms -- there is no
    parameter for prior dilution because none should be inferred."""
    import inspect

    sig = inspect.signature(dilution_pct)
    assert set(sig.parameters) == {"investment", "post_money"}


def test_ltv_to_cac():
    assert ltv_to_cac(3000, 1000) == pytest.approx(3.0)


def test_ltv_to_cac_zero_cac_is_none():
    assert ltv_to_cac(3000, 0) is None


def test_apply_growth_delta_positive():
    assert apply_growth_delta(1_000_000, 20) == pytest.approx(1_200_000)


def test_apply_growth_delta_negative():
    assert apply_growth_delta(1_000_000, -15) == pytest.approx(850_000)


def test_apply_growth_delta_missing_base_is_none():
    assert apply_growth_delta(None, 20) is None


# ---------------------------------------------------------------------
# Every function: missing-input matrix (spec section 37: "division by
# zero" / "negative/invalid values" must never raise)
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "fn,args",
    [
        (implied_post_money_valuation, (None, None)),
        (implied_pre_money_valuation, (None, None)),
        (revenue_multiple, (None, None)),
        (arr_multiple, (None, None)),
        (gross_margin_pct, (None, None)),
        (operating_margin_pct, (None, None)),
        (revenue_growth_pct, (None, None)),
        (monthly_burn, (None, None, None)),
        (runway_months, (None, None)),
        (dilution_pct, (None, None)),
        (ltv_to_cac, (None, None)),
        (apply_growth_delta, (None, None)),
    ],
)
def test_every_function_handles_all_missing_inputs_without_raising(fn, args):
    assert fn(*args) is None
