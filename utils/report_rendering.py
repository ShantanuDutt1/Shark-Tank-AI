"""
Founder Feedback Report PDF rendering for Shark Tank AI (Release 0.9).

Pure rendering only -- takes an already-generated
`models.schemas.FounderFeedbackReport` and returns PDF bytes in
memory; no provider calls, no business logic, no filesystem writes.
Reuses `reportlab` (already a project dependency since Release 0.6,
used by `tests/test_pdf_extraction.py` to generate test fixture PDFs)
rather than introducing a new PDF library -- Release 0.9 spec Part 34:
"if PDF generation is already available, reuse it."

Every piece of report text is HTML-escaped
(`xml.sax.saxutils.escape()`) before being placed inside a
`reportlab.platypus.Paragraph`, which interprets a small HTML-like
markup language -- founder- or model-generated text containing a
literal `<`/`&`/`>` must render as plain text, never be parsed as
markup (the same class of bug `ui/proposal.py`'s `html.escape()` fix
addressed for Streamlit in Release 0.4.1).

Deliberately produces bytes in memory (`io.BytesIO`), never a file on
disk -- `ui/proposal.py` hands the bytes straight to
`st.download_button()`. This is what makes the artifact lifecycle
trivial (Release 0.9 spec Part 26/34): there is no temporary file to
clean up, no path to reuse incorrectly, and no risk of a stale report
surviving a session reset, because nothing is ever written to disk in
the first place.
"""

from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from models.schemas import FounderFeedbackReport

_STAGE_LABELS: dict[str, str] = {
    "idea": "Idea stage",
    "pre_validation": "Pre-validation",
    "early_validation": "Early validation",
    "early_revenue": "Early revenue",
    "growth": "Growth stage",
    "later_stage": "Later stage",
    "unclear": "Stage unclear",
}

_READINESS_LABELS: dict[str, str] = {
    "strong": "Strong",
    "developing": "Developing",
    "weak": "Weak",
    "unclear": "Unclear",
    "insufficient_evidence": "Insufficient evidence",
}

_PRIORITY_LABELS: dict[str, str] = {"now": "NOW", "next": "NEXT", "later": "LATER"}


def render_founder_report_pdf(report: FounderFeedbackReport) -> bytes:
    """Render `report` to a PDF and return its bytes. Never raises on
    a report with `report_status="unavailable"` -- it renders an
    honest one-page notice instead (spec Part 21: "do not silently
    substitute fabricated feedback")."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title="Founder Feedback Report",
    )
    styles = getSampleStyleSheet()
    small_italic = ParagraphStyle(
        "SmallItalic", parent=styles["Italic"], fontSize=8, textColor="#555555"
    )
    section_heading = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6
    )

    story: list = []
    _add_header(story, report, styles)

    if report.report_status == "unavailable":
        story.append(Paragraph("Founder Feedback Report — Unavailable", section_heading))
        story.append(
            Paragraph(
                "This report could not be generated due to a technical issue. Your "
                "simulation outcome above is unaffected.",
                styles["Normal"],
            )
        )
        if report.limitations:
            story.append(Spacer(1, 6))
            story.append(Paragraph(escape(report.limitations), styles["Normal"]))
        story.append(Spacer(1, 18))
        story.append(Paragraph(escape(report.disclaimer), small_italic))
        doc.build(story)
        return buffer.getvalue()

    _add_page_one(story, report, styles, section_heading)
    story.append(PageBreak())
    _add_page_two(story, report, styles, section_heading)

    story.append(Spacer(1, 18))
    story.append(Paragraph(escape(report.disclaimer), small_italic))

    doc.build(story)
    return buffer.getvalue()


def _add_header(story: list, report: FounderFeedbackReport, styles) -> None:
    story.append(Paragraph("Shark Tank AI — Founder Feedback Report", styles["Title"]))
    if report.company_name:
        story.append(Paragraph(escape(report.company_name), styles["Heading2"]))
    generated = report.generated_at.strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generated: {generated}", styles["Normal"]))
    story.append(Spacer(1, 12))


def _add_page_one(story: list, report: FounderFeedbackReport, styles, section_heading) -> None:
    story.append(Paragraph("Page 1 — Critical Assessment", section_heading))

    stage_label = _STAGE_LABELS.get(report.stage, report.stage)
    story.append(Paragraph(f"<b>Apparent stage:</b> {escape(stage_label)}", styles["Normal"]))
    if report.stage_rationale:
        story.append(Paragraph(escape(report.stage_rationale), styles["Normal"]))
    if report.business_model:
        story.append(
            Paragraph(f"<b>Business model:</b> {escape(report.business_model)}", styles["Normal"])
        )

    if report.executive_summary:
        story.append(Paragraph("Executive Summary", section_heading))
        story.append(Paragraph(escape(report.executive_summary), styles["Normal"]))

    _add_bulleted_section(story, "Strong", report.strengths, styles, section_heading)
    _add_bulleted_section(story, "Needs Work", report.needs_work, styles, section_heading)
    _add_bulleted_section(story, "Critical", report.critical_issues, styles, section_heading)

    if report.investor_readiness:
        story.append(Paragraph("Investor-Readiness Dimensions", section_heading))
        items = []
        for dim in report.investor_readiness:
            label = _READINESS_LABELS.get(dim.assessment, dim.assessment)
            text = f"<b>{escape(dim.dimension)}:</b> {escape(label)}"
            if dim.rationale:
                text += f" — {escape(dim.rationale)}"
            items.append(ListItem(Paragraph(text, styles["Normal"])))
        story.append(ListFlowable(items, bulletType="bullet"))

    if report.valuation_feedback:
        story.append(Paragraph("Valuation", section_heading))
        story.append(Paragraph(escape(report.valuation_feedback), styles["Normal"]))

    if report.financial_feedback:
        story.append(Paragraph("Financial / Commercial Notes", section_heading))
        story.append(Paragraph(escape(report.financial_feedback), styles["Normal"]))


def _add_page_two(story: list, report: FounderFeedbackReport, styles, section_heading) -> None:
    story.append(Paragraph("Page 2 — Action Plan", section_heading))

    for priority in ("now", "next", "later"):
        items = [item for item in report.action_plan if item.priority == priority]
        if not items:
            continue
        story.append(Paragraph(_PRIORITY_LABELS[priority], section_heading))
        flowable_items = []
        for item in items:
            lines = [f"<b>{escape(item.problem)}</b>"]
            if item.why_it_matters:
                lines.append(f"Why it matters: {escape(item.why_it_matters)}")
            lines.append(f"Action: {escape(item.action)}")
            if item.evidence_needed:
                lines.append(f"Evidence needed: {escape(item.evidence_needed)}")
            flowable_items.append(ListItem(Paragraph("<br/>".join(lines), styles["Normal"])))
        story.append(ListFlowable(flowable_items, bulletType="bullet"))

    if not report.action_plan:
        story.append(Paragraph("No specific action items were identified.", styles["Normal"]))

    if report.limitations:
        story.append(Paragraph("Limitations", section_heading))
        story.append(Paragraph(escape(report.limitations), styles["Normal"]))


def _add_bulleted_section(story: list, title: str, items: list[str], styles, section_heading) -> None:
    if not items:
        return
    story.append(Paragraph(title, section_heading))
    story.append(
        ListFlowable(
            [ListItem(Paragraph(escape(item), styles["Normal"])) for item in items],
            bulletType="bullet",
        )
    )
