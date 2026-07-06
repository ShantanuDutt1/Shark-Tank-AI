"""
Startup proposal intake panel for Shark Tank AI.

Lets the founder choose exactly one input type (Text, PDF, Audio,
Video) and provide their pitch through the matching widget, then
displays the "Session Stage" card underneath.

This module only detects *presence* of content (a non-empty text
area, or a file object being non-None) to flip
`st.session_state.proposal_uploaded`. It does not read, parse,
transcribe, or otherwise process the uploaded content — that is
explicitly out of scope for this milestone.
"""

from __future__ import annotations

from typing import List

import streamlit as st

from models.enums import PHASE_STAGE_MESSAGES, SessionPhase

PROPOSAL_TYPES: List[str] = ["Text", "PDF", "Audio", "Video"]


def render_proposal_panel() -> None:
    """Render the proposal input section and the session stage card."""
    st.subheader("Startup Proposal")

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
    elif proposal_type == "PDF":
        content_provided = _render_file_input(
            label="Upload proposal (PDF)",
            file_types=["pdf"],
            widget_key="proposal_pdf_uploader",
        )
    elif proposal_type == "Audio":
        content_provided = _render_file_input(
            label="Upload proposal (audio)",
            file_types=["mp3", "wav", "m4a"],
            widget_key="proposal_audio_uploader",
        )
    else:  # "Video"
        content_provided = _render_file_input(
            label="Upload proposal (video)",
            file_types=["mp4", "mov", "webm"],
            widget_key="proposal_video_uploader",
        )

    st.session_state.proposal_uploaded = content_provided

    _render_session_stage_card()


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


def _render_file_input(label: str, file_types: List[str], widget_key: str) -> bool:
    """Render a file uploader. Returns True if a file has been selected."""
    uploaded_file = st.file_uploader(label, type=file_types, key=widget_key)
    if uploaded_file is not None:
        st.session_state.proposal_content = uploaded_file.name
        st.session_state.proposal_filename = uploaded_file.name
        return True

    st.session_state.proposal_filename = None
    return False


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
