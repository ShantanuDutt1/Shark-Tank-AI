"""
Deterministic PII anonymization for founder-submitted content.

Release 0.6 spec Part E: focused, testable redaction of unnecessary
direct identifiers (email addresses, phone numbers, street addresses)
from proposal text before it is stored, displayed, or sent to a
provider -- not a general-purpose PII/NLP pipeline, and not a
destructive rewrite of the proposal's substance.

Deliberately regex-based and deterministic (no LLM call): the same
input always produces the same output, it requires no network access
or API key, and its behavior is exhaustively unit-testable
(`tests/test_pii.py`). This trades recall (it will miss PII a more
sophisticated NLP-based detector would catch) for precision,
predictability, and zero cost -- appropriate for a "focused" scope per
the spec, not a claim of comprehensive PII detection.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Matches common North American phone formats: (555) 123-4567,
# 555-123-4567, 555.123.4567, +1 555 123 4567, 5551234567 (10 digits in
# a row is common enough to be worth catching, at the cost of
# occasionally matching a non-phone 10-digit number like an order ID --
# an acceptable false positive for a privacy-focused redactor).
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
)

# A number followed by 1-4 words then a common street suffix -- enough
# to catch "123 Main Street" / "4500 Elm Ave" without trying to be a
# full address parser.
_STREET_ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+(?:[A-Za-z0-9.'-]+\s+){1,4}"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|"
    r"Court|Ct|Way|Place|Pl|Circle|Cir|Terrace|Ter)\b\.?",
    re.IGNORECASE,
)

EMAIL_PLACEHOLDER = "[REDACTED EMAIL]"
PHONE_PLACEHOLDER = "[REDACTED PHONE]"
ADDRESS_PLACEHOLDER = "[REDACTED ADDRESS]"


def anonymize_pii(text: str) -> str:
    """Redact email addresses, phone numbers, and street addresses from
    `text`, replacing each with a labeled placeholder.

    Everything else in `text` -- the business description, market
    claims, numbers that aren't part of a matched pattern -- is left
    untouched: this is privacy protection, not destruction of useful
    proposal information (spec Part E).
    """
    if not text:
        return text
    redacted = _EMAIL_RE.sub(EMAIL_PLACEHOLDER, text)
    redacted = _STREET_ADDRESS_RE.sub(ADDRESS_PLACEHOLDER, redacted)
    redacted = _PHONE_RE.sub(PHONE_PLACEHOLDER, redacted)
    return redacted
