"""
Chat-style conversation panel for Shark Tank AI.

Renders `st.session_state.conversation_history` — a list of typed
`models.schemas.ConversationMessage` produced by the active Session
Director (`orchestrator.orchestrator.SharkTankOrchestrator`) and
synced in by `ui.session_state.sync_from_director()` — as a real chat
transcript using Streamlit's native `st.chat_message`, one bubble per
message, oldest first. Release 0.4.1 replaced the previous custom
`<div>`-based transcript rendering with this (see
`docs/release_log.md` -> Release 0.4.1); the underlying data source is
unchanged, and the message model was not touched to make this happen.

No agent logic lives here. `get_example_conversation()` still returns
static placeholder dialogue for the pre-session (Idle) view only — it
makes no decisions and calls no model.
"""

from __future__ import annotations

from typing import Dict, List

import streamlit as st

from models.enums import SPEAKER_LABELS, SpeakerRole
from models.schemas import ConversationMessage
from utils.ids import new_id

#: Avatar shown next to each speaker's name in the chat transcript —
#: the only per-speaker visual distinction this module makes; no
#: custom CSS is needed on top of `st.chat_message`'s own styling.
_SPEAKER_AVATAR: Dict[SpeakerRole, str] = {
    SpeakerRole.MODERATOR: "🎙️",
    SpeakerRole.CONSERVATIVE_VC: "🛡️",
    SpeakerRole.GROWTH_VC: "🚀",
    SpeakerRole.BALANCED_VC: "⚖️",
    SpeakerRole.FOUNDER: "🐟",
}


def get_example_conversation() -> List[ConversationMessage]:
    """Return a static example transcript used to seed a pre-session view.

    Purely illustrative placeholder dialogue shown only while Idle
    (`ui/layout.py`'s `_seed_example_conversation_if_empty()` only uses
    this when `conversation_history` is empty) — the moment a real
    session starts, `ui.controls._handle_start_session()` clears it and
    this is fully replaced by the Session Director's own conversation.
    """
    example_lines = [
        (
            SpeakerRole.MODERATOR,
            "Welcome to Shark Tank AI. The committee will now review the "
            "submitted proposal.",
        ),
        (
            SpeakerRole.CONSERVATIVE_VC,
            "Before anything else — why will this business fail? Walk me "
            "through your existing customers and recurring revenue.",
        ),
        (
            SpeakerRole.FOUNDER,
            "We're focused on partnership-led growth, with three regional "
            "distributors already signed and recurring contracts in place.",
        ),
        (
            SpeakerRole.GROWTH_VC,
            "Set aside today's numbers for a moment — if everything works, "
            "how large could this actually become, and what's the "
            "mechanism that gets you there?",
        ),
        (
            SpeakerRole.BALANCED_VC,
            "Given the stage you're at and the evidence on the table so "
            "far, is the valuation you're asking for actually proportionate "
            "to the risk here?",
        ),
    ]
    return [
        ConversationMessage(
            id=new_id("example_"),
            speaker=speaker,
            content=content,
            turn_index=index,
        )
        for index, (speaker, content) in enumerate(example_lines)
    ]


def render_conversation_history() -> None:
    """Render the full conversation as a chat transcript."""
    st.subheader("Investment Committee Session")

    history: List[ConversationMessage] = st.session_state.conversation_history
    if not history:
        st.caption("No conversation yet.")
        return

    for entry in history:
        _render_message(entry)


def _render_message(entry: ConversationMessage) -> None:
    avatar = _SPEAKER_AVATAR.get(entry.speaker, "💬")
    label = SPEAKER_LABELS.get(entry.speaker, "Unknown")
    timestamp = entry.created_at.strftime("%H:%M:%S")

    with st.chat_message(entry.speaker.value, avatar=avatar):
        st.caption(f"{label} · {timestamp}")
        st.markdown(entry.content)
