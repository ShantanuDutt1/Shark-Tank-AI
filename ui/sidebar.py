"""
Sidebar component for the Shark Tank AI Streamlit app.

Displays application status and configuration info. No agent
interaction happens here yet.
"""

from __future__ import annotations

import streamlit as st

from config.settings import Settings


def render_sidebar(settings: Settings) -> None:
    """Render the sidebar with environment and configuration status."""
    with st.sidebar:
        st.title("🦈 Shark Tank AI")
        st.caption(f"Environment: `{settings.app_env}`")

        st.divider()
        st.subheader("Status")

        if settings.has_llm_credentials:
            st.success(f"LLM provider configured: {settings.llm_provider}")
        else:
            st.warning(
                "No LLM API key configured yet. "
                "Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in your `.env` file."
            )

        st.info("No agent logic has been implemented yet — this is a project scaffold.")

        st.divider()
        st.caption(f"Memory backend: `{settings.memory_backend}`")
        st.caption(f"Log level: `{settings.log_level}`")
