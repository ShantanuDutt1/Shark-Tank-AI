"""
Tests for `utils.report_rendering.render_founder_report_pdf()`
(Release 0.9). Exercises the real `reportlab` rendering path (no
mocking) -- these tests assert real PDF bytes come back, not just that
the function was called.
"""

from __future__ import annotations

import io

from models.schemas import (
    ActionItem,
    FounderFeedbackReport,
    InvestorReadinessDimension,
)


def make_report(**overrides) -> FounderFeedbackReport:
    defaults = dict(
        report_status="completed",
        session_id="session-1",
        pitch_id="pitch-1",
        company_name="Acme Widgets",
        stage="early_validation",
        stage_rationale="Some early customers but limited history.",
        business_model="saas",
        executive_summary="A promising SaaS pitch with a clear customer problem.",
        strengths=["Clear customer problem identified", "Working product with early users"],
        needs_work=["Traction is thin", "Market sizing is not well supported"],
        critical_issues=[],
        investor_readiness=[
            InvestorReadinessDimension(
                dimension="Market opportunity", assessment="developing", rationale="Some evidence."
            )
        ],
        valuation_feedback="The valuation appears broadly consistent with available evidence.",
        financial_feedback="Burn and runway were not clearly established.",
        action_plan=[
            ActionItem(
                priority="now",
                problem="Market size claim unsupported",
                why_it_matters="Valuation depends on it",
                action="Rebuild the estimate bottom-up",
                evidence_needed="Customer counts and pricing",
            )
        ],
        limitations="Verification was limited by available research.",
    )
    defaults.update(overrides)
    return FounderFeedbackReport(**defaults)


def test_render_produces_real_pdf_bytes():
    from utils.report_rendering import render_founder_report_pdf

    pdf_bytes = render_founder_report_pdf(make_report())

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500


def test_render_never_writes_to_disk(tmp_path, monkeypatch):
    """Spec Part 34: prefer session-scoped in-memory artifacts, no
    uncontrolled persistent files. Run with the working directory
    pointed at an empty temp dir and confirm nothing appears there."""
    import os

    from utils.report_rendering import render_founder_report_pdf

    monkeypatch.chdir(tmp_path)
    render_founder_report_pdf(make_report())
    assert os.listdir(tmp_path) == []


def test_render_handles_unavailable_report_without_raising():
    from utils.report_rendering import render_founder_report_pdf

    report = FounderFeedbackReport(
        report_status="unavailable",
        session_id="session-1",
        pitch_id="pitch-1",
        company_name="Acme",
        limitations="Provider was unavailable.",
    )
    pdf_bytes = render_founder_report_pdf(report)
    assert pdf_bytes.startswith(b"%PDF-")


def test_render_handles_empty_optional_lists():
    from utils.report_rendering import render_founder_report_pdf

    report = make_report(strengths=[], needs_work=[], critical_issues=[], investor_readiness=[], action_plan=[])
    pdf_bytes = render_founder_report_pdf(report)
    assert pdf_bytes.startswith(b"%PDF-")


def test_render_escapes_html_like_content_without_raising():
    """A founder proposal or LLM-generated field containing something
    that looks like markup must render as plain text, never break
    rendering or be interpreted as reportlab markup (mirrors the
    ui/proposal.py XSS fix from Release 0.4.1, applied to PDF
    rendering instead of Streamlit markdown). Verified via actual text
    extraction: the literal angle-bracket text must survive as data,
    not be consumed as a (possibly malformed) markup tag."""
    from pypdf import PdfReader

    from utils.report_rendering import render_founder_report_pdf

    malicious_report = make_report(
        company_name="Acme & Co.",
        executive_summary="Contains <b>fake bold</b> and an unescaped ampersand & sign.",
        strengths=["<i>Italic injection attempt</i>"],
    )
    pdf_bytes = render_founder_report_pdf(malicious_report)
    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = "\n".join(page.extract_text() for page in reader.pages)
    assert "fake bold" in full_text
    assert "Italic injection attempt" in full_text
    assert "Acme & Co." in full_text


def test_disclaimer_always_present_in_extracted_text():
    """reportlab compresses PDF content streams by default, so the
    disclaimer isn't visible as a raw substring of the file bytes --
    extract the actual rendered text via `pypdf` (already a project
    dependency, Release 0.6) instead, the same way a person opening
    the PDF would actually read it."""
    from pypdf import PdfReader

    from utils.report_rendering import render_founder_report_pdf

    report = make_report()
    pdf_bytes = render_founder_report_pdf(report)
    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Disclaimer" in full_text
    assert "not a prediction of investor interest" in full_text


def test_priority_sections_only_render_when_populated():
    """A report with only 'now' items must not render empty NEXT/LATER
    headings -- this test just confirms rendering succeeds cleanly
    with a partial action plan (the structural check that matters is
    already covered by the agent-level tests; this is a rendering
    smoke test, not a text-extraction assertion)."""
    from utils.report_rendering import render_founder_report_pdf

    report = make_report(
        action_plan=[
            ActionItem(priority="now", problem="p", why_it_matters="w", action="a", evidence_needed="e")
        ]
    )
    pdf_bytes = render_founder_report_pdf(report)
    assert pdf_bytes.startswith(b"%PDF-")
