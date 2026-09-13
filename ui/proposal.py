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
