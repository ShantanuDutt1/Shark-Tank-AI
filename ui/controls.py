"""
Bottom control bar for Shark Tank AI.

Renders the sticky instruction label and the Start Session / End
Session buttons.

- "Start Session" is disabled until a proposal has been provided. On
  click it marks the session as running and, if still Idle, advances
  the phase to "Proposal Uploaded" — a direct, explicit consequence of
  a single button click, not an automatic multi-step transition. Later
  phases (Validation, Question Round, etc.) are only ever set by
  future milestones' own logic, never by this module.
- "End Session" is always enabled. On click it fully resets session
  state back to Idle, with no confirmation dialog, per spec.
"""

from __future__ import annotations

import streamlit as st

from models.enums import PHASE_LABELS, SessionPhase
from ui.session_state import reset_session_state


def render_control_bar() -> None:
    """Render the sticky bottom bar and handle Start/End Session clicks."""
    st.markdown('<div class="stka-bottom-bar-spacer"></div>', unsafe_allow_html=True)
    st.markdown('<div class="stka-bottom-bar">', unsafe_allow_html=True)

    st.markdown(
        f'<div class="stka-bottom-bar-instruction">{_get_instruction_label()}</div>',
        unsafe_allow_html=True,
    )

    col_start, col_end = st.columns(2)
    with col_start:
        start_clicked = st.button(
            "Start Session",
            key="start_session_button",
            disabled=not st.session_state.proposal_uploaded or st.session_state.session_running,
            use_container_width=True,
        )
    with col_end:
        end_clicked = st.button(
            "End Session",
            key="end_session_button",
            use_container_width=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if start_clicked:
        _handle_start_session()

    if end_clicked:
        _handle_end_session()


def _handle_start_session() -> None:
    st.session_state.session_running = True
    if st.session_state.current_phase == SessionPhase.IDLE.value:
        st.session_state.current_phase = SessionPhase.PROPOSAL_UPLOADED.value
    st.rerun()


def _handle_end_session() -> None:
    reset_session_state()
    st.rerun()


def _get_instruction_label() -> str:
    if not st.session_state.proposal_uploaded:
        return "Upload a startup proposal to begin."

    if not st.session_state.session_running:
        return "Proposal ready. Click \u201cStart Session\u201d to begin the committee review."

    try:
        phase = SessionPhase(st.session_state.current_phase)
    except ValueError:
        phase = SessionPhase.IDLE
    phase_label = PHASE_LABELS.get(phase, "In progress")
    return f"Session in progress — current phase: {phase_label}."
