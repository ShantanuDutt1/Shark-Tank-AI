"""
Sidebar component for Shark Tank AI.

Renders the "Settings" panel: LLM provider selection (with
provider-specific configuration fields), developer/diagnostic
toggles, and read-only integration status indicators.

As of Release 0.5, Anthropic is the only provider with a real
`BaseProvider` implementation (`providers/anthropic_provider.py`); its
section below is read-only status (is a key configured, which model)
rather than an editable field, because its credentials come
exclusively from `config.settings.Settings` (environment / `.env`),
never from a value typed into this sidebar -- see
`orchestrator/orchestrator.py`'s `_build_default_provider()`. Gemini
and Ollama have no implementation behind them yet; their sections
keep the same editable fields Release 0.3.x shipped (nothing reads
these values), but are now explicitly labeled "not yet implemented"
so selecting them doesn't imply they do something.
"""

from __future__ import annotations

import streamlit as st

from config.settings import get_settings
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

    options = [LLMProvider.ANTHROPIC.value, LLMProvider.GEMINI.value, LLMProvider.OLLAMA.value]
    provider_value = st.radio(
        "Provider",
        options=options,
        format_func=_format_provider_label,
        index=options.index(st.session_state.selected_provider)
        if st.session_state.selected_provider in options
        else 0,
        key="sidebar_provider_radio",
        label_visibility="collapsed",
    )
    st.session_state.selected_provider = provider_value

    if provider_value == LLMProvider.ANTHROPIC.value:
        _render_anthropic_status()
    elif provider_value == LLMProvider.GEMINI.value:
        st.caption("Not implemented yet — selecting this has no effect.")
        st.session_state.gemini_api_key = st.text_input(
            "API key",
            value=st.session_state.gemini_api_key,
            type="password",
            key="sidebar_gemini_api_key",
            disabled=True,
        )
        st.session_state.gemini_model = st.text_input(
            "Model",
            value=st.session_state.gemini_model,
            key="sidebar_gemini_model",
            disabled=True,
        )
        st.session_state.selected_model = st.session_state.gemini_model
    else:
        st.caption("Not implemented yet — selecting this has no effect.")
        st.session_state.ollama_host = st.text_input(
            "Host URL",
            value=st.session_state.ollama_host,
            key="sidebar_ollama_host",
            disabled=True,
        )
        st.session_state.ollama_model = st.text_input(
            "Model",
            value=st.session_state.ollama_model,
            key="sidebar_ollama_model",
            disabled=True,
        )
        st.session_state.selected_model = st.session_state.ollama_model


def _render_anthropic_status() -> None:
    """Read-only status for the one real provider.

    No editable API-key field here: per `docs/architecture.md` -> LLM
    Provider Layer, the key comes only from `ANTHROPIC_API_KEY` /
    `.env` via `config.settings.Settings`, never from sidebar input --
    this just reports what's already configured.
    """
    settings = get_settings()
    st.session_state.selected_model = settings.llm_model

    if settings.anthropic_api_key:
        st.success(f"API key configured. Model: {settings.llm_model}")
    else:
        st.warning(
            "No ANTHROPIC_API_KEY configured — Sharks will fall back to "
            "deterministic placeholder questions and evaluations. Set "
            "ANTHROPIC_API_KEY in your environment or .env file."
        )


def _format_provider_label(value: str) -> str:
    if value == LLMProvider.ANTHROPIC.value:
        return "Anthropic (Claude)"
    if value == LLMProvider.GEMINI.value:
        return "Gemini API (not implemented)"
    return "Ollama (not implemented)"


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
