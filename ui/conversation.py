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
    SpeakerRole.GROWTH_INVESTOR: "stka-speaker-growth",
    SpeakerRole.FINANCIAL_INVESTOR: "stka-speaker-financial",
    SpeakerRole.TECHNICAL_INVESTOR: "stka-speaker-technical",
    SpeakerRole.MARKETING_INVESTOR: "stka-speaker-marketing",
    SpeakerRole.RISK_INVESTOR: "stka-speaker-risk",
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
            "speaker": SpeakerRole.GROWTH_INVESTOR.value,
            "timestamp": timestamp,
            "message": "Can you walk us through your customer acquisition strategy for the next 12 months?",
        },
        {
            "speaker": SpeakerRole.FOUNDER.value,
            "timestamp": timestamp,
            "message": "We're focused on partnership-led growth, with three regional distributors already signed.",
        },
        {
            "speaker": SpeakerRole.FINANCIAL_INVESTOR.value,
            "timestamp": timestamp,
            "message": "What does your current burn rate look like, and how many months of runway remain?",
        },
        {
            "speaker": SpeakerRole.TECHNICAL_INVESTOR.value,
            "timestamp": timestamp,
            "message": "How defensible is your core technology against a well-funded competitor entering the space?",
        },
        {
            "speaker": SpeakerRole.MARKETING_INVESTOR.value,
            "timestamp": timestamp,
            "message": "Your brand positioning is compelling — how do you plan to scale that message beyond your initial market?",
        },
        {
            "speaker": SpeakerRole.RISK_INVESTOR.value,
            "timestamp": timestamp,
            "message": "Walk us through your biggest regulatory or operational risk and how you're mitigating it.",
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
