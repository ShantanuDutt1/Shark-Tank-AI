"""Tests for utils.pii.anonymize_pii."""

from __future__ import annotations

from utils.pii import anonymize_pii


def test_email_is_redacted():
    result = anonymize_pii("Reach me at jane.doe@example.com for details.")
    assert "jane.doe@example.com" not in result
    assert "[REDACTED EMAIL]" in result


def test_phone_number_is_redacted():
    result = anonymize_pii("Call us at (555) 123-4567 anytime.")
    assert "555" not in result or "[REDACTED PHONE]" in result
    assert "[REDACTED PHONE]" in result


def test_various_phone_formats_are_redacted():
    for phone in ["555-123-4567", "555.123.4567", "+1 555 123 4567", "5551234567"]:
        result = anonymize_pii(f"Call {phone} now.")
        assert "[REDACTED PHONE]" in result, phone


def test_street_address_is_redacted():
    result = anonymize_pii("Our office is at 4500 Elm Avenue, Springfield.")
    assert "[REDACTED ADDRESS]" in result
    assert "4500 Elm Avenue" not in result


def test_business_content_is_preserved():
    text = "We sell eco-friendly packaging with 40% gross margins and $2M ARR."
    result = anonymize_pii(text)
    assert result == text


def test_empty_string_is_unchanged():
    assert anonymize_pii("") == ""


def test_multiple_pii_types_in_one_text():
    text = (
        "Contact founder@startup.io or (555) 987-6543. "
        "HQ at 12 Baker Street. We have 500 customers."
    )
    result = anonymize_pii(text)
    assert "founder@startup.io" not in result
    assert "987-6543" not in result
    assert "12 Baker Street" not in result
    assert "500 customers" in result


def test_anonymization_is_deterministic():
    text = "Email me at a@b.com."
    assert anonymize_pii(text) == anonymize_pii(text)
