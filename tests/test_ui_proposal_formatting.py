"""
Tests for `ui.proposal._format_currency_range()` (Release 0.8).

A pure formatting helper worth testing directly -- Release 0.8 spec
Part 33 ("No Fake Precision") requires rounded ranges like
"$2.5M-$3.5M", never over-precise figures like "$3,184,721".
"""

from __future__ import annotations

from ui.proposal import _format_currency_range


def test_millions_are_rounded_to_one_decimal():
    assert _format_currency_range(2_500_000, 3_500_000) == "$2.5M-$3.5M"


def test_thousands_are_rounded_to_whole_number():
    assert _format_currency_range(50_000, 150_000) == "$50K-$150K"


def test_no_fake_precision_from_a_precise_underlying_float():
    """The classic case this guards against: a valuation figure like
    $3,184,721.37 must render as a rounded "$3.2M", never with its
    full precision."""
    result = _format_currency_range(3_184_721.37, 3_184_721.37)
    assert result == "$3.2M"
    assert "3,184,721" not in result


def test_single_value_when_low_equals_high():
    assert _format_currency_range(2_000_000, 2_000_000) == "$2.0M"


def test_single_value_when_only_one_bound_present():
    assert _format_currency_range(2_000_000, None) == "$2.0M"
    assert _format_currency_range(None, 3_000_000) == "$3.0M"


def test_both_missing_returns_none():
    assert _format_currency_range(None, None) is None


def test_small_values_below_a_thousand():
    assert _format_currency_range(500, 800) == "$500-$800"
