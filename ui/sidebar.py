"""
Sidebar component for Shark Tank AI.

Renders the "Settings" panel: LLM provider selection (with
provider-specific configuration fields), developer/diagnostic
toggles, and read-only integration status indicators.

Everything here is configuration UI only. No LLM calls are made, no
memory/MCP/ADK connections are attempted — the status fields simply
display whatever is currently in `st.session_state`, which for now is
always the static placeholder values set in `ui/session_state.py`.
"""

from __future__ import annotations

import streamlit as st

from models.enums import LLMProvider


def render_sidebar() -> None:
    """Render the full sidebar: title, provider settings, toggles, status."""
    with st.sidebar:
        st.title("Settings")

        _render_llm_provider_section()
        st.divider()
        _render_toggles_section()
        st.divider()
        _render_status_section()


def _render_llm_provider_section() -> None:
    st.subheader("LLM Provider")

    provider_value = st.radio(
        "Provider",
        options=[LLMProvider.GEMINI.value, LLMProvider.OLLAMA.value],
        format_func=_format_provider_label,
        index=0 if st.session_state.selected_provider == LLMProvider.GEMINI.value else 1,
        key="sidebar_provider_radio",
        label_visibility="collapsed",
    )
    st.session_state.selected_provider = provider_value

    if provider_value == LLMProvider.GEMINI.value:
        st.session_state.gemini_api_key = st.text_input(
            "API key",
            value=st.session_state.gemini_api_key,
            type="password",
            key="sidebar_gemini_api_key",
        )
        st.session_state.gemini_model = st.text_input(
            "Model",
            value=st.session_state.gemini_model,
            key="sidebar_gemini_model",
        )
        st.session_state.selected_model = st.session_state.gemini_model
    else:
        st.session_state.ollama_host = st.text_input(
            "Host URL",
            value=st.session_state.ollama_host,
            key="sidebar_ollama_host",
        )
        st.session_state.ollama_model = st.text_input(
            "Model",
            value=st.session_state.ollama_model,
            key="sidebar_ollama_model",
        )
        st.session_state.selected_model = st.session_state.ollama_model


def _format_provider_label(value: str) -> str:
    return "Gemini API" if value == LLMProvider.GEMINI.value else "Ollama"


def _render_toggles_section() -> None:
    st.subheader("Toggles")

    st.session_state.verbose_mode = st.toggle(
        "Verbose Mode",
        value=st.session_state.verbose_mode,
        key="sidebar_verbose_toggle",
    )
    st.session_state.developer_mode = st.toggle(
        "Developer Mode",
        value=st.session_state.developer_mode,
        key="sidebar_developer_toggle",
    )
    # Intentionally disabled: this toggle has no effect yet. A future
    # milestone (agent reasoning traces) will wire it up without
    # requiring any change to this component.
    st.toggle(
        "Show Reasoning",
        value=False,
        disabled=True,
        key="sidebar_show_reasoning_toggle",
        help="Not available yet — enabled in a future milestone.",
    )


def _render_status_section() -> None:
    st.subheader("Integration Status")

    st.text(f"Memory: {st.session_state.memory_status}")
    st.text(f"MCP: {st.session_state.mcp_status}")
    st.text(f"ADK: {st.session_state.adk_status}")
