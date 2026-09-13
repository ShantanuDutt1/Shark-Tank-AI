"""
Bottom control bar for Shark Tank AI.

Renders the sticky instruction label and the Start Session / End
Session buttons.

- "Start Session" is disabled until a proposal has been provided, or
  while a session is already running. On click it creates a fresh
  `orchestrator.orchestrator.SharkTankOrchestrator` (the Session
  Director) and hands it the submitted proposal via `start_session()`.
  Every phase transition from `PROPOSAL_UPLOADED` onward is decided by
  that call, not by this module — this module only clears the
  *previous* session's runtime state first (`ui.session_state
  .clear_active_session()` — deliberately not the proposal itself; see
  that function's docstring for the Release 0.4.1 bug this fixes),
  then syncs whatever the director reports.
- "End Session" is disabled whenever no session is actively running
  (Idle, or a session that already reached `SESSION_COMPLETE` on its
  own — nothing left to stop). When enabled and clicked, it tells the
  active director the session ended, then fully resets session state
  back to Idle, including the proposal, with no confirmation dialog,
  per spec.
"""

from __future__ import annotations

import streamlit as st

from models.enums import PHASE_LABELS, SessionPhase
from orchestrator.orchestrator import SharkTankOrchestrator
from ui.session_state import (
    build_pitch_from_state,
    clear_active_session,
    reset_session_state,
    sync_from_director,
)


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
            disabled=not st.session_state.session_running,
            use_container_width=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if start_clicked:
        _handle_start_session()

    if end_clicked:
        _handle_end_session()


def _handle_start_session() -> None:
    # Capture the proposal before clearing the previous session's
    # runtime state below.
    pitch = build_pitch_from_state()

    # Discard only the previous session's Session Director, conversation,
    # and turn state -- never the proposal itself. See
    # ui.session_state.clear_active_session()'s docstring for the bug
    # this fixes (Release 0.4.1).
    clear_active_session()

    director = SharkTankOrchestrator()
    with st.spinner("The committee is convening..."):
        director.start_session(pitch)

    st.session_state["_session_director"] = director
    sync_from_director(director)
    st.rerun()


def _handle_end_session() -> None:
    director = st.session_state.get("_session_director")
    if director is not None:
        reason = (
            "completed"
            if director.phase == SessionPhase.SESSION_COMPLETE
            else "reset"
        )
        director.end_session(reason=reason)
    reset_session_state()
    st.rerun()


def _get_instruction_label() -> str:
    if not st.session_state.proposal_uploaded:
        return "Upload a startup proposal to begin."

    try:
        phase = SessionPhase(st.session_state.current_phase)
    except ValueError:
        phase = SessionPhase.IDLE

    if phase == SessionPhase.SESSION_COMPLETE:
        return (
            "Session complete. Review the conversation above, or click "
            "\u201cStart Session\u201d to begin a new pitch."
        )

    if not st.session_state.session_running:
        return "Proposal ready. Click \u201cStart Session\u201d to begin the committee review."

    phase_label = PHASE_LABELS.get(phase, "In progress")
    return f"Session in progress — current phase: {phase_label}."
