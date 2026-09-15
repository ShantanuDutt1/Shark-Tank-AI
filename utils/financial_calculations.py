"""
Deterministic financial calculations for Shark Tank AI (Release 0.8).

Pure functions only -- no side effects, no imports from `ui/`,
`agents/`, `orchestrator/`, `providers/`, or `memory/`
(`docs/coding_standards.md` -> *`utils/`*). Every function returns
`None` rather than raising or guessing when a required input is
missing or a denominator is zero/invalid -- Release 0.8 spec Part 7:
"never manufacture a missing denominator," and Part 37: "division by
zero" is an explicit code-quality audit item.

Money and percentage values use plain `float`, consistent with every
other monetary field already in this codebase (`Pitch.ask_amount`,
`Offer.amount`, `ValuationEstimate.low/high`, `models.schemas
.NumericRange`, Release 0.6.1's `_compute_founder_implied_valuation`).
This is a deliberate consistency choice, not an oversight: these are
order-of-magnitude estimates carrying their own uncertainty labels
(`confidence` fields elsewhere), not cent-accurate accounting output
where `Decimal` would matter, and each function here performs one
independent division -- there is no chained arithmetic for
floating-point error to accumulate across.
"""

from __future__ import annotations


def implied_post_money_valuation(investment: float | None, equity_pct: float | None) -> float | None:
    """`investment / (equity_pct / 100)`. `None` if either input is
    missing or `equity_pct` is not strictly positive."""
    if investment is None or equity_pct is None or equity_pct <= 0:
        return None
    return investment / (equity_pct / 100)


def implied_pre_money_valuation(post_money: float | None, investment: float | None) -> float | None:
    """`post_money - investment`. `None` if either input is missing or
    the result would be negative (an investment larger than the
    post-money valuation is not a valid pre-money figure)."""
    if post_money is None or investment is None:
        return None
    pre_money = post_money - investment
    return pre_money if pre_money >= 0 else None


def revenue_multiple(valuation: float | None, revenue: float | None) -> float | None:
    """`valuation / revenue`. `None` if either input is missing or
    `revenue` is not strictly positive."""
    if valuation is None or revenue is None or revenue <= 0:
        return None
    return valuation / revenue


def arr_multiple(valuation: float | None, arr: float | None) -> float | None:
    """`valuation / ARR`. `None` if either input is missing or `arr` is
    not strictly positive."""
    if valuation is None or arr is None or arr <= 0:
        return None
    return valuation / arr


def gross_margin_pct(revenue: float | None, cogs: float | None) -> float | None:
    """`(revenue - cogs) / revenue * 100`. `None` if either input is
    missing or `revenue` is not strictly positive."""
    if revenue is None or cogs is None or revenue <= 0:
        return None
    return (revenue - cogs) / revenue * 100


def operating_margin_pct(operating_income: float | None, revenue: float | None) -> float | None:
    """`operating_income / revenue * 100`. `None` if either input is
    missing or `revenue` is not strictly positive."""
    if operating_income is None or revenue is None or revenue <= 0:
        return None
    return operating_income / revenue * 100


def revenue_growth_pct(current: float | None, previous: float | None) -> float | None:
    """`(current - previous) / previous * 100`. `None` if either input
    is missing or `previous` is not strictly positive."""
    if current is None or previous is None or previous <= 0:
        return None
    return (current - previous) / previous * 100


def monthly_burn(cash_start: float | None, cash_end: float | None, months: float | None) -> float | None:
    """`(cash_start - cash_end) / months`. `None` if any input is
    missing or `months` is not strictly positive. A negative result
    (cash grew rather than shrank) is returned as-is -- it is valid
    data (the company is cash-flow positive over the period), not an
    error."""
    if cash_start is None or cash_end is None or months is None or months <= 0:
        return None
    return (cash_start - cash_end) / months


def runway_months(cash: float | None, burn_per_month: float | None) -> float | None:
    """`cash / burn_per_month`. `None` if either input is missing, cash
    is negative, or `burn_per_month` is not strictly positive (a
    company that isn't burning cash has undefined/infinite runway by
    this formula, not zero -- returning `None` avoids implying either
    fabricated extreme)."""
    if cash is None or burn_per_month is None or cash < 0 or burn_per_month <= 0:
        return None
    return cash / burn_per_month


def dilution_pct(investment: float | None, post_money: float | None) -> float | None:
    """The investor's resulting ownership percentage:
    `investment / post_money * 100`. `None` if either input is missing
    or `post_money` is not strictly positive. Only reflects the terms
    of the single investment described -- never infers a pre-existing
    cap table the founder did not provide (spec Part 16)."""
    if investment is None or post_money is None or post_money <= 0:
        return None
    return investment / post_money * 100


def ltv_to_cac(ltv: float | None, cac: float | None) -> float | None:
    """`ltv / cac`. `None` if either input is missing or `cac` is not
    strictly positive."""
    if ltv is None or cac is None or cac <= 0:
        return None
    return ltv / cac


def apply_growth_delta(base_value: float | None, delta_pct: float | None) -> float | None:
    """`base_value * (1 + delta_pct / 100)` -- applies a scenario's
    assumption delta (e.g. "-15% growth vs. base case") to a base
    figure. `None` if either input is missing. Used to compute
    scenario-adjusted figures from LLM-proposed assumption deltas
    without ever letting the LLM perform the multiplication itself
    (spec Part 16)."""
    if base_value is None or delta_pct is None:
        return None
    return base_value * (1 + delta_pct / 100)
