"""
Founder response input for Shark Tank AI.

Exactly one multiline text box plus one submit button — this is not a
chat input, it's a single turn-based response control. It is disabled
by default; a future milestone (once the committee actually asks a
question) will flip `st.session_state.user_input_enabled` to True.
Nothing in this module enables it itself.

Submitting appends a single "Founder (User)" entry to
`conversation_history` and clears the text box. No agent reacts to it
yet — that wiring belongs to a future milestone.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from models.enums import SpeakerRole


def render_response_area() -> None:
    """Render the response text area and submit button."""
    st.subheader("Founder Response")

    is_enabled = bool(st.session_state.user_input_enabled)

    # The key includes a nonce that increments after every successful
    # submission. Streamlit has no built-in way to clear a text_area's
    # value in place, so rotating the key forces a fresh, empty widget
    # on the next render instead.
    widget_key = f"user_response_input_{st.session_state.response_input_nonce}"

    response_text = st.text_area(
        "Your response",
        value="",
        height=120,
        key=widget_key,
        disabled=not is_enabled,
        placeholder="Type your response to the committee...",
        label_visibility="collapsed",
    )

    submit_col, _spacer_col = st.columns([1, 4])
    with submit_col:
        submitted = st.button(
            "Submit Response",
            key="submit_response_button",
            disabled=not is_enabled,
            use_container_width=True,
        )

    if submitted and response_text and response_text.strip():
        st.session_state.conversation_history.append(
            {
                "speaker": SpeakerRole.FOUNDER.value,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "message": response_text.strip(),
            }
        )
        st.session_state.response_input_nonce += 1
        st.rerun()
