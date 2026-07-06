"""
Page layout composition for Shark Tank AI.

This is the single place that assembles every UI component into the
full page. `app.py` calls only `render_app()` — it has no knowledge of
individual components, so the page can be rearranged here without
touching the entry point.
"""

from __future__ import annotations

import streamlit as st

from ui.conversation import get_example_conversation, render_conversation_history
from ui.controls import render_control_bar
from ui.header import render_header
from ui.proposal import render_proposal_panel
from ui.response import render_response_area
from ui.session_state import init_session_state
from ui.sidebar import render_sidebar
from ui.styles import inject_global_styles


def render_app() -> None:
    """Render the entire Shark Tank AI page, in order, top to bottom."""
    init_session_state()
    inject_global_styles()
    _seed_example_conversation_if_empty()

    render_header()
    render_sidebar()

    main_panel = st.container()
    with main_panel:
        render_proposal_panel()
        st.divider()
        render_conversation_history()
        render_response_area()

    render_control_bar()


def _seed_example_conversation_if_empty() -> None:
    """Populate the conversation panel with example dialogue on first load.

    Only runs when history is empty, so it never overwrites a session
    already in progress — including right after `reset_session_state()`,
    which is the intended behavior: a fresh session should show the
    example transcript again.
    """
    if not st.session_state.conversation_history:
        st.session_state.conversation_history = get_example_conversation()
