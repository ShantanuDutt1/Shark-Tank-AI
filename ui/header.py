"""
Top header component for Shark Tank AI.

Renders the application title, subtitle, and the session progress
stepper. The stepper is purely a display component: it reads
`st.session_state.current_phase` and highlights the matching step. It
does not decide when the phase changes — that responsibility belongs
to whichever component drives a given transition (currently only
`ui/controls.py`, on explicit button clicks).
"""

from __future__ import annotations

import streamlit as st

from models.enums import PHASE_LABELS, PHASE_ORDER


def render_header() -> None:
    """Render the title, subtitle, and progress stepper."""
    st.markdown('<div class="stka-header-title">Shark Tank AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="stka-subtitle">Autonomous Multi Agent Investment Committee</div>',
        unsafe_allow_html=True,
    )
    _render_progress_stepper(st.session_state.current_phase)


def _render_progress_stepper(current_phase_value: str) -> None:
    """Render a horizontal stepper with exactly one active phase.

    `current_phase_value` is the raw string stored in session state
    (Streamlit session state values must be JSON-serializable-ish, so
    the enum's `.value` is stored rather than the enum instance).
    """
    phase_values = [phase.value for phase in PHASE_ORDER]
    try:
        current_index = phase_values.index(current_phase_value)
    except ValueError:
        current_index = 0

    steps_html = []
    for index, phase in enumerate(PHASE_ORDER):
        if index < current_index:
            state_class = "stka-step-done"
        elif index == current_index:
            state_class = "stka-step-active"
        else:
            state_class = "stka-step-pending"

        label = PHASE_LABELS[phase]
        steps_html.append(
            f'<div class="stka-step {state_class}">'
            f'<span class="stka-step-index">{index + 1}</span>'
            f'<span class="stka-step-label">{label}</span>'
            f"</div>"
        )

    st.markdown(f'<div class="stka-stepper">{"".join(steps_html)}</div>', unsafe_allow_html=True)
