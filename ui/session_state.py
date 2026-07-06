"""
Session state model for Shark Tank AI.

Streamlit's `st.session_state` is the only place state can persist
across reruns, so this module is the single source of truth for what
keys exist and what they default to. Every other UI module reads and
writes through these same keys — none of them invent their own
ad-hoc state.

This module contains no agent logic, LLM calls, or automatic phase
transitions. It only defines *what* state exists and *how* to
initialize or fully reset it; every value change driven by user
interaction happens in the component that owns that interaction
(e.g. `ui/controls.py` decides when `current_phase` advances).
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from models.enums import LLMProvider, SessionPhase


def _default_state() -> Dict[str, Any]:
    """Build a fresh dictionary of default session state values.

    Returns a new dict each call so callers never share mutable
    defaults (e.g. the empty list for `conversation_history`).
    """
    return {
        # --- Session lifecycle ---
        "current_phase": SessionPhase.IDLE.value,
        "session_running": False,
        # --- Conversation ---
        "conversation_history": [],
        "response_input_nonce": 0,
        # --- LLM provider configuration (UI-only; no calls are made) ---
        "selected_provider": LLMProvider.GEMINI.value,
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
    widget-bound keys created by input components), then re-applies
    the defaults. This matches the "End Session" requirement: no
    partial reset, no confirmation dialog — a full return to Idle.
    """
    st.session_state.clear()
    init_session_state()
