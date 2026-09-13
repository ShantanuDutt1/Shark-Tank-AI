"""
Founder chat input for Shark Tank AI.

A single `st.chat_input`, enabled only when the active Session
Director reports `awaiting_founder_response` (Release 0.4.1 spec
section 7, "Chat Input Behavior") — never by a UI timer or a
locally-tracked flag. Release 0.4 used a separate text area + submit
button pair for this; Release 0.4.1 replaced it with `st.chat_input`
to match the rest of the chat-style conversion in `ui/conversation.py`
(see `docs/release_log.md` -> Release 0.4.1). `st.chat_input` clears
itself after every submission, so the manual "nonce" key-rotation
Release 0.4's text-area version needed is gone.

Submitting hands the response to the active
`orchestrator.orchestrator.SharkTankOrchestrator` via
`submit_founder_response()`, which appends the founder's message,
advances the turn sequence, and generates whatever comes next (the
following Shark's question, or the Internal Deliberation pipeline).
This module does not append to `conversation_history` itself, and does
not decide what happens next — it only captures the text, hands it
off, and re-syncs `st.session_state` from the director's resulting
state.

Rendered inside `ui/layout.py`'s `main_panel` container, so per
Streamlit's own chat_input behavior it stays inline, right below the
conversation history, rather than auto-pinning to the very bottom of
the page — which is already occupied by `ui/controls.py`'s Start/End
bar.

Release 0.5 note on responsiveness (spec section B24): the Session
Director's calls into `SharkAgent` are still fully synchronous, same
as Release 0.4 -- a real provider call now takes real wall-clock time,
most noticeably on the founder's third response, which synchronously
triggers all three Sharks' evaluation *and* deliberation before this
function's `st.rerun()` returns control to the browser. This module
adds a `st.spinner()` around that call as the smallest
architecture-compatible affordance for that latency (per spec section
B24: "do not introduce threads/background workers merely to make the
UI look asynchronous... correctness is more important than
animation") -- no threading, no background workers, no change to how
Streamlit reruns work.
"""

from __future__ import annotations

import streamlit as st

from ui.session_state import sync_from_director


def render_response_area() -> None:
    """Render the founder's single chat input."""
    is_enabled = bool(st.session_state.user_input_enabled)

    placeholder = (
        "Type your response to the committee..."
        if is_enabled
        else "Waiting for the committee..."
    )

    response_text = st.chat_input(
        placeholder,
        disabled=not is_enabled,
        key="founder_chat_input",
    )

    if response_text and is_enabled:
        director = st.session_state.get("_session_director")
        if director is not None:
            with st.spinner("The committee is responding..."):
                director.submit_founder_response(response_text.strip())
            sync_from_director(director)
            st.rerun()
