"""
Startup proposal intake panel for Shark Tank AI.

Lets the founder choose Text or PDF and provide their pitch through
the matching widget, then displays the "Session Stage" card
underneath. Audio and Video were removed in Release 0.4.1 — they were
never processed by anything downstream and only misled founders into
thinking they were supported.

This module detects *presence* of content (a non-empty text area) to
flip `st.session_state.proposal_uploaded`. For a PDF upload, it goes
further: it actually extracts the PDF's text (`utils.pdf_extraction
.extract_pdf_text()`), so the founder's real proposal content --  not
just a filename -- reaches validation, research, and the Sharks
(Release 0.6 spec Part P). It does not do anything beyond plain text
extraction (no OCR, no layout/structure recovery) -- that remains
explicitly out of scope.

Once a session has been started (`ui.session_state._session_director`
is set — the same key `ui/controls.py` and `ui/response.py` check),
the input widgets are replaced with a read-only summary of what was
actually submitted. Release 0.4's editable text area kept re-rendering
during an active session, which made it look like the proposal could
still be changed after the committee had already received it; Release
0.4.1 fixes that by locking it once `start_session()` has been called,
and it stays locked through `SESSION_COMPLETE` so the founder can see
exactly what was pitched. It becomes editable again only after a full
reset (`ui.session_state.reset_session_state()`), which also clears
its content.

That locked summary embeds the founder's own proposal text into raw
HTML (`unsafe_allow_html=True`, needed for the shared `.stka-stage-card`
styling) — `html.escape()` it first, or a founder typing e.g.
`<script>` into the proposal box would have it interpreted as markup
rather than displayed as text (an XSS bug fixed in Release 0.4.1;
see `docs/release_log.md`).
"""

from __future__ import annotations

import html

import streamlit as st

from models.enums import PHASE_STAGE_MESSAGES, SessionPhase
from utils.pdf_extraction import PdfExtractionError, extract_pdf_text
from utils.report_rendering import render_founder_report_pdf

PROPOSAL_TYPES: list[str] = ["Text", "PDF"]


def render_proposal_panel() -> None:
    """Render the proposal input section and the session stage card."""
    st.subheader("Startup Proposal")

    if _proposal_is_locked():
        _render_locked_proposal_summary()
    else:
        _render_proposal_input()

    _render_session_stage_card()
    _render_market_reality_summary()
    _render_investment_committee_summary()
    _render_founder_report_section()


def _proposal_is_locked() -> bool:
    """Whether the proposal should be read-only rather than editable.

    True for the entire lifetime of a session that has been started —
    from Start Session through Session Complete — since
    `orchestrator.orchestrator.SharkTankOrchestrator.start_session()`
    has already captured the proposal by then and editing the box
    further would have no effect. `_session_director` is the same flag
    `ui/controls.py` uses to decide whether Start/End are enabled, so
    this introduces no second source of truth.
    """
    return st.session_state.get("_session_director") is not None


def _render_locked_proposal_summary() -> None:
    filename = st.session_state.proposal_filename
    content = st.session_state.proposal_content or ""
    display_text = filename if filename else content
    proposal_type = st.session_state.proposal_type

    # display_text is founder-controlled free text -- escape it before
    # interpolating into raw HTML (see module docstring for the bug
    # this fixes).
    safe_display_text = html.escape(display_text)

    st.markdown(
        '<div class="stka-stage-card">'
        f'<span class="stka-stage-card-label">Submitted Proposal ({proposal_type})</span>'
        f'<span class="stka-stage-card-message">{safe_display_text}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def _render_market_reality_summary() -> None:
    """A concise, optional Market Reality Research summary (Release
    0.6 spec Part O: "may be exposed in an appropriate UI location...
    do not dump a giant research report into the chat"). Collapsed by
    default; only rendered once the brief exists (after
    `MARKET_RESEARCH` has completed). Every value shown here is
    plain-text via `st.markdown`'s default (escaped) rendering, not
    `unsafe_allow_html` -- see `ui/conversation.py` for why that's
    already safe by default.
    """
    director = st.session_state.get("_session_director")
    brief = getattr(director, "market_brief", None) if director is not None else None
    if brief is None:
        return

    with st.expander("Market Reality Research", expanded=False):
        if brief.is_fallback:
            st.caption(brief.research_limitations or "Market research was not available.")
            return

        if brief.industry:
            st.markdown(f"**Industry:** {brief.industry}")
        if brief.market_summary:
            st.markdown(f"**Market:** {brief.market_summary}")

        valuation = brief.valuation
        if valuation.confidence == "insufficient_evidence" or valuation.low is None:
            st.markdown("**Market-informed valuation:** insufficient evidence for an estimate.")
        else:
            st.markdown(
                f"**Market-informed valuation range:** ${valuation.low:,.0f}"
                f"-${valuation.high:,.0f} (confidence: {valuation.confidence})"
            )
        if brief.valuation_comparison:
            st.markdown(f"**Founder ask vs. evidence:** {brief.valuation_comparison}")
        if brief.sources:
            st.caption(f"Based on {len(brief.sources)} retrieved source(s).")


#: Founder-facing labels for `ConsensusResult.recommendation`
#: (Release 0.7) -- kept in the UI layer since `models/schemas.py`
#: owns data shapes only, not display strings
#: (`docs/coding_standards.md` -> Modularity).
_RECOMMENDATION_LABELS: dict[str, str] = {
    "invest": "Invest",
    "invest_with_conditions": "Invest with conditions",
    "do_not_invest": "Do not invest",
    "insufficient_evidence": "Insufficient evidence to decide",
    "unavailable": "Unavailable (technical issue)",
}

#: Same bounded vocabulary as `models.schemas.QUALITY_RATINGS`
#: (Release 0.8) -- capitalized for display only; the underlying value
#: stored on `ConsensusResult` stays lowercase/machine-readable.
_QUALITY_LABELS: dict[str, str] = {
    "strong": "Strong",
    "moderate": "Moderate",
    "weak": "Weak",
    "insufficient_evidence": "Insufficient evidence",
}


def _format_currency_range(low: float | None, high: float | None) -> str | None:
    """Round a valuation figure to at most 2-3 significant digits
    before display -- Release 0.8 spec Part 33 ("No Fake Precision"):
    prefer "$2.5M-$3.5M" over "$3,184,721" unless the data genuinely
    supports that precision, which this codebase's own valuation
    estimates never claim to (every value here already carries its own
    `confidence` label, never "exact"). Returns `None` if both bounds
    are missing."""
    if low is None and high is None:
        return None

    def _round(value: float) -> str:
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:.0f}K"
        return f"${value:,.0f}"

    if low is not None and high is not None and low != high:
        return f"{_round(low)}-{_round(high)}"
    return _round(low if low is not None else high)  # type: ignore[arg-type]


def _render_investment_committee_summary() -> None:
    """A concise, optional Investment Committee summary (Verification +
    Consensus + Advanced Financial Analysis, Release 0.7/0.8) -- same
    pattern as `_render_market_reality_summary()`: collapsed by
    default, only rendered once a real `ConsensusResult` exists,
    plain-text via `st.markdown`'s default escaping. Never shows
    chain-of-thought, raw verification/financial-analysis reasoning, or
    internal agent prompts -- only the structured, already-concise
    fields on `ConsensusResult` (Release 0.8 spec Part 32's example
    layout: business/financial/deal quality, growth, risk, valuation,
    strengths, risks, conditions).
    """
    director = st.session_state.get("_session_director")
    consensus = getattr(director, "consensus_result", None) if director is not None else None
    if consensus is None:
        return

    with st.expander("Investment Committee", expanded=False):
        if consensus.recommendation == "unavailable":
            st.caption(
                consensus.evidence_limitations
                or "The committee's formal consensus was not available."
            )
            return

        label = _RECOMMENDATION_LABELS.get(consensus.recommendation, consensus.recommendation)
        st.markdown(f"**Recommendation:** {label}  (confidence: {consensus.confidence:.2f})")

        quality_rows = [
            ("Business quality", consensus.business_quality),
            ("Financial health", consensus.financial_health),
            ("Deal quality", consensus.deal_quality),
        ]
        for row_label, value in quality_rows:
            st.markdown(f"**{row_label}:** {_QUALITY_LABELS.get(value, value)}")

        valuation_text = _format_currency_range(
            consensus.recommended_valuation_range.low, consensus.recommended_valuation_range.high
        )
        if valuation_text:
            st.markdown(
                f"**Recommended valuation range:** {valuation_text} "
                f"(confidence: {consensus.recommended_valuation_range.confidence})"
            )

        if consensus.growth_profile:
            st.markdown(f"**Growth potential:** {consensus.growth_profile}")
        if consensus.risk_profile:
            st.markdown(f"**Risk:** {consensus.risk_profile}")
        if consensus.scenario_summary:
            st.markdown(f"**Scenarios:** {consensus.scenario_summary}")
        if consensus.investment_thesis:
            st.markdown(f"**Thesis:** {consensus.investment_thesis}")
        if consensus.key_strengths:
            st.markdown("**Key strengths:**")
            for item in consensus.key_strengths:
                st.markdown(f"- {item}")
        if consensus.key_risks:
            st.markdown("**Key risks:**")
            for item in consensus.key_risks:
                st.markdown(f"- {item}")
        if consensus.conditions:
            st.markdown("**Conditions:**")
            for item in consensus.conditions:
                st.markdown(f"- {item}")
        if consensus.recommendation == "insufficient_evidence":
            st.caption(
                consensus.evidence_limitations
                or "The evidence available did not support a confident recommendation."
            )


def _render_founder_report_section() -> None:
    """The Founder Feedback Report download (Release 0.9) -- only
    rendered once the session has actually finished
    (`SessionPhase.SESSION_COMPLETE`) and a real
    `FounderFeedbackReport` exists on the director. Rendering the PDF
    here, on demand, rather than in `_complete_session()`, keeps report
    *generation* (an LLM call, already done once by the orchestrator)
    fully separate from report *rendering* (pure, cheap, and safe to
    redo every rerun) -- `render_founder_report_pdf()` never calls a
    provider and never touches disk (see `utils/report_rendering.py`).

    Session isolation falls out of the existing architecture with no
    extra code here: `ui/controls.py::_handle_start_session()` builds a
    brand-new `SharkTankOrchestrator` per session, so `director
    .founder_report` is always `None` until this session's own report
    is generated -- there is no way for a prior session's report to
    appear here (Release 0.9 spec Part 26).
    """
    director = st.session_state.get("_session_director")
    if director is None or director.phase != SessionPhase.SESSION_COMPLETE:
        return
    report = getattr(director, "founder_report", None)
    if report is None:
        return

    with st.expander("Founder Feedback Report", expanded=True):
        if report.report_status == "unavailable":
            st.caption(
                report.limitations
                or "The founder feedback report could not be generated due to a technical issue."
            )
            return

        st.markdown(
            "A two-page, evidence-grounded feedback report on this pitch is ready. "
            "It reflects the full simulation, not just the Sharks' offers."
        )
        pdf_bytes = render_founder_report_pdf(report)
        st.download_button(
            label="Download Founder Feedback Report (PDF)",
            data=pdf_bytes,
            file_name="founder_feedback_report.pdf",
            mime="application/pdf",
            key="founder_report_download_button",
        )
        st.caption(report.disclaimer)


def _render_proposal_input() -> None:
    proposal_type = st.radio(
        "Input type",
        options=PROPOSAL_TYPES,
        horizontal=True,
        index=_current_type_index(),
        key="proposal_type_radio",
    )
    st.session_state.proposal_type = proposal_type

    if proposal_type == "Text":
        content_provided = _render_text_input()
    else:  # "PDF"
        content_provided = _render_pdf_input()

    st.session_state.proposal_uploaded = content_provided


def _current_type_index() -> int:
    try:
        return PROPOSAL_TYPES.index(st.session_state.proposal_type)
    except ValueError:
        return 0


def _render_text_input() -> bool:
    """Render the large text area for a typed pitch. Returns True if non-empty."""
    existing_value = st.session_state.proposal_content
    if not isinstance(existing_value, str):
        existing_value = ""

    text_value = st.text_area(
        "Describe the startup pitch",
        value=existing_value,
        height=220,
        key="proposal_text_area",
        placeholder="Describe the business, the ask, and the opportunity...",
        label_visibility="collapsed",
    )
    st.session_state.proposal_content = text_value
    st.session_state.proposal_filename = None
    return bool(text_value and text_value.strip())


def _render_pdf_input() -> bool:
    """Render the PDF uploader and extract its actual text content.

    `proposal_content` is set to the PDF's *extracted text*, not its
    filename (Release 0.6 spec Part P: "Do not silently treat the
    filename as proposal content") -- `proposal_filename` is kept
    separately, purely for display in the locked summary card. If
    extraction fails (a scanned image with no text layer, a corrupt
    file), that is surfaced as an explicit error, and the proposal is
    not marked as uploaded -- never silently treated as an empty-but-
    valid submission.
    """
    uploaded_file = st.file_uploader("Upload proposal (PDF)", type=["pdf"], key="proposal_pdf_uploader")
    if uploaded_file is None:
        st.session_state.proposal_filename = None
        return False

    st.session_state.proposal_filename = uploaded_file.name

    try:
        extracted_text = extract_pdf_text(uploaded_file.getvalue())
    except PdfExtractionError as exc:
        st.error(f"Could not read this PDF: {exc}")
        st.session_state.proposal_content = ""
        return False

    st.session_state.proposal_content = extracted_text
    return bool(extracted_text.strip())


def _render_session_stage_card() -> None:
    try:
        phase = SessionPhase(st.session_state.current_phase)
    except ValueError:
        phase = SessionPhase.IDLE

    message = PHASE_STAGE_MESSAGES.get(phase, PHASE_STAGE_MESSAGES[SessionPhase.IDLE])

    st.markdown(
        '<div class="stka-stage-card">'
        '<span class="stka-stage-card-label">Session Stage</span>'
        f'<span class="stka-stage-card-message">{message}</span>'
        "</div>",
        unsafe_allow_html=True,
    )
