"""
Turn-based conversation history panel for Shark Tank AI.

This is explicitly not a chat widget: it renders a linear, read-only
history of everything said so far, one styled block per message. New
entries are appended by other components (currently only
`ui/response.py`, when the founder submits a reply) — this module's
only job is display, plus seeding the initial example transcript.

No agent logic lives here. `get_example_conversation()` returns static
placeholder dialogue so the panel isn't empty before real agents
exist; it makes no decisions and calls no model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from models.enums import SPEAKER_LABELS, SpeakerRole

_SPEAKER_CSS_CLASS: Dict[SpeakerRole, str] = {
    SpeakerRole.MODERATOR: "stka-speaker-moderator",
    SpeakerRole.CONSERVATIVE_VC: "stka-speaker-conservative",
    SpeakerRole.GROWTH_VC: "stka-speaker-growth",
    SpeakerRole.BALANCED_VC: "stka-speaker-balanced",
    SpeakerRole.FOUNDER: "stka-speaker-founder",
}


def get_example_conversation() -> List[Dict[str, Any]]:
    """Return a static example transcript used to seed a fresh session.

    Every message shares one timestamp (the moment the session was
    seeded) since these are illustrative placeholder messages, not a
    real recorded exchange.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    return [
        {
            "speaker": SpeakerRole.MODERATOR.value,
            "timestamp": timestamp,
            "message": "Welcome to Shark Tank AI. The committee will now review the submitted proposal.",
        },
        {
            "speaker": SpeakerRole.CONSERVATIVE_VC.value,
            "timestamp": timestamp,
            "message": "Before anything else — why will this business fail? Walk me through your existing customers and recurring revenue.",
        },
        {
            "speaker": SpeakerRole.FOUNDER.value,
            "timestamp": timestamp,
            "message": "We're focused on partnership-led growth, with three regional distributors already signed and recurring contracts in place.",
        },
        {
            "speaker": SpeakerRole.GROWTH_VC.value,
            "timestamp": timestamp,
            "message": "Set aside today's numbers for a moment — if everything works, how large could this actually become, and what's the mechanism that gets you there?",
        },
        {
            "speaker": SpeakerRole.BALANCED_VC.value,
            "timestamp": timestamp,
            "message": "Given the stage you're at and the evidence on the table so far, is the valuation you're asking for actually proportionate to the risk here?",
        },
    ]


def render_conversation_history() -> None:
    """Render the full conversation history panel."""
    st.subheader("Investment Committee Session")

    history = st.session_state.conversation_history
    if not history:
        st.caption("No conversation yet.")
        return

    for entry in history:
        _render_message(entry)


def _render_message(entry: Dict[str, Any]) -> None:
    raw_speaker = entry.get("speaker", SpeakerRole.MODERATOR.value)
    try:
        speaker = SpeakerRole(raw_speaker)
    except ValueError:
        speaker = SpeakerRole.MODERATOR

    css_class = _SPEAKER_CSS_CLASS.get(speaker, "stka-speaker-moderator")
    label = SPEAKER_LABELS.get(speaker, "Unknown")
    timestamp = entry.get("timestamp", "--:--:--")
    message = entry.get("message", "")

    st.markdown(
        f'<div class="stka-speaker-bubble {css_class}">'
        '<div class="stka-speaker-meta">'
        f'<span class="stka-speaker-name">{label}</span>'
        f'<span class="stka-speaker-timestamp">{timestamp}</span>'
        "</div>"
        f'<div class="stka-speaker-message">{message}</div>'
        "</div>",
        unsafe_allow_html=True,
    )
