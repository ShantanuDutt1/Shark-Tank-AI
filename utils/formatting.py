"""
Small text/number formatting helpers for Shark Tank AI's UI.
"""

from __future__ import annotations


def format_currency(amount: float) -> str:
    """Format a number as a USD currency string, e.g. 1234.5 -> '$1,234.50'."""
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format a fractional or whole-number percentage, e.g. 12.5 -> '12.5%'."""
    return f"{value:.1f}%"
