"""
Session state model for Shark Tank AI.

Streamlit's `st.session_state` is the only place state can persist
across reruns, so this module is the single source of truth for what
keys exist and what they default to. Every other UI module reads and
writes through these same keys — none of them invent their own
ad-hoc state.

This module contains no agent logic, LLM calls, or automatic phase
transitions of its own. `current_phase`, `conversation_history`,
`user_input_enabled`, and (as of Release 0.4.1) `session_running` are
never decided here or in any other `ui/` module directly — they are
copied from the active `orchestrator.orchestrator.SharkTankOrchestrator`
instance (held in the `_session_director` key) via `sync_from_director()`
below, which is the "future bridge" `docs/architecture.md` -> *Event
Bus* describes: the Session Director owns real session/turn state; the
UI only ever displays a synced copy of it, immediately after each
user-triggered call into the director (`ui/controls.py`,
`ui/response.py`).

Two different kinds of "clear" exist, and Release 0.4.1 keeps them
distinct (see `docs/release_log.md` -> Release 0.4.1):

- `clear_active_session()` — discards only the *previous session's*
  runtime state (its `SharkTankOrchestrator`, its conversation, its
  turn state) so Start Session never inherits a prior session. It
  deliberately leaves the founder's current proposal input untouched.
- `reset_session_state()` — a full return to Idle, used by End Session:
  clears the proposal too.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from models.enums import LLMProvider, SessionPhase
from models.schemas import Pitch
from utils.ids import new_id


def _default_state() -> Dict[str, Any]:
    """Build a fresh dictionary of default session state values.

    Returns a new dict each call so callers never share mutable
    defaults (e.g. the empty list for `conversation_history`).
    """
    return {
        # --- Session lifecycle ---
        "current_phase": SessionPhase.IDLE.value,
        # Whether a session is actively progressing -- True from Start
        # Session until either Session Complete or a reset. This is a
        # pure projection of the active director's `phase`, recomputed
        # by sync_from_director() on every sync; nothing sets it by
        # hand (Release 0.4.1 fix -- see module docstring).
        "session_running": False,
        # The active orchestrator.orchestrator.SharkTankOrchestrator instance
        # for the in-progress (or just-completed) session, or None when
        # Idle. Owned exclusively by ui/controls.py (creates it on Start
        # Session, clears it on End Session) and cleared by
        # reset_session_state(). No other ui/ module writes this key;
        # ui/response.py only reads it to hand off a founder response.
        # Not JSON-serializable, but st.session_state accepts arbitrary
        # Python objects, and this key is never rendered directly.
        "_session_director": None,
        # --- Conversation ---
        "conversation_history": [],
        # --- LLM provider configuration (UI-only; no calls are made) ---
        "selected_provider": LLMProvider.ANTHROPIC.value,
        "selected_model": "",
        "gemini_api_key": "",
        "gemini_model": "gemini-1.5-pro",
        "ollama_host": "http://localhost:11434",
        "ollama_model": "llama3",
        # --- Proposal intake ---
        "proposal_type": "Text",
        "proposal_uploaded": False,
        "proposal_content": "",
        "proposal_filename": None,
        # --- Interaction control ---
        "user_input_enabled": False,
        # --- Developer / diagnostic toggles ---
        "verbose_mode": False,
        "developer_mode": False,
        "show_reasoning": False,
        # --- Backend integration status (placeholders for future milestones) ---
        "memory_status": "Not Connected",
        "mcp_status": "Unavailable",
        "adk_status": "Unavailable",
    }


# The set of keys this application manages. Used only for
# documentation/introspection purposes elsewhere in the codebase.
APP_STATE_KEYS = tuple(_default_state().keys())


def init_session_state() -> None:
    """Ensure every default key exists in `st.session_state`.

    Safe to call on every rerun: existing values are left untouched,
    only missing keys are populated. Call this once, early, in
    `ui/layout.py` before any component reads `st.session_state`.
    """
    defaults = _default_state()
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session_state() -> None:
    """Fully reset the session back to a fresh Idle state.

    Clears *all* keys in `st.session_state` (including any
    widget-bound keys created by input components, and the founder's
    proposal), then re-applies the defaults. This is what End Session
    calls: no partial reset, no confirmation dialog — a full return to
    Idle, including the proposal itself.
    """
    st.session_state.clear()
    init_session_state()


def clear_active_session() -> None:
    """Discard the *previous* session's runtime state before starting a
    new one — the Session Director, its conversation, its turn state —
    without touching the founder's current proposal input.

    This is the Release 0.4.1 fix for the proposal-persistence bug:
    `ui.controls._handle_start_session()` used to call
    `reset_session_state()` (a *full* reset, including the proposal)
    immediately after capturing the just-submitted proposal, which
    cleared `proposal_content`/`proposal_uploaded` even though the
    backend had already received it — so the proposal box visibly went
    blank the instant a session started. This function clears only the
    keys that must never leak from one session into the next, leaving
    every `proposal_*` key (and every setting/toggle) exactly as the
    founder left it.

    `reset_session_state()` remains the only thing that clears the
    proposal itself, used by End Session and by nothing else.
    """
    defaults = _default_state()
    for key in (
        "_session_director",
        "current_phase",
        "session_running",
        "conversation_history",
        "user_input_enabled",
    ):
        st.session_state[key] = defaults[key]


def build_pitch_from_state() -> Pitch:
    """Build a placeholder `Pitch` from whatever the founder has entered
    into the `proposal_content` / `proposal_filename` keys defined
    above.

    Lives here rather than in `ui/proposal.py` so that
    `ui/controls.py` (which needs it to start a session) never has to
    import another UI component module directly — see
    `docs/folder_structure.md` -> `ui/` -> *Responsibility*
    ("individual components do not import each other directly").

    Release 0.4 does not parse the proposal into a founder name,
    company name, ask amount, or equity — those keep `models.schemas
    .Pitch`'s Release 0.4 defaults, and the raw content becomes
    `description` (or, for a file upload, the filename, since content
    isn't read/parsed yet). Structured proposal parsing belongs to a
    future validation-focused release, not this one (Release 0.4 spec
    section 8).
    """
    content = st.session_state.proposal_content
    if not isinstance(content, str):
        content = ""
    filename = st.session_state.proposal_filename
    description = content.strip() if content.strip() else (filename or "")
    return Pitch(id=new_id("pitch_"), description=description)


def sync_from_director(director: Any) -> None:
    """Copy read-only Session Director state into `st.session_state`.

    Called after every user-triggered call into the active
    `SharkTankOrchestrator` (`ui/controls.py`'s Start Session,
    `ui/response.py`'s Submit Response) so the UI always renders
    exactly what the director reports, never a value a UI component
    computed or advanced on its own. `director` is typed `Any` here
    rather than imported as `SharkTankOrchestrator` to avoid `ui/`
    depending on `orchestrator/` any more tightly than this one
    read-only sync point requires.

    `session_running` is derived from `director.phase` rather than
    tracked as an independent flag (Release 0.4.1 fix): it is `True`
    for every phase between Idle and Session Complete, and `False` at
    both ends. Deriving it here — instead of `ui/controls.py` setting
    it to `True` by hand on Start and never updating it again — is
    what makes natural completion (the backend reaching
    `SessionPhase.SESSION_COMPLETE` on its own, with no further UI
    click) correctly flip it back to `False`.
    """
    st.session_state.current_phase = director.phase.value
    st.session_state.conversation_history = director.conversation
    st.session_state.user_input_enabled = director.awaiting_founder_response
    st.session_state.session_running = director.phase not in (
        SessionPhase.IDLE,
        SessionPhase.SESSION_COMPLETE,
    )
