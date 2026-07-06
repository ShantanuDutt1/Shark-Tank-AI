"""
Shark Tank AI — Streamlit application entry point.

Run with:
    streamlit run app.py

This entry point wires together configuration, logging, and the UI
layer. It contains no agent, orchestration, memory, or LLM logic —
only what's needed to configure the process and hand off to
`ui/layout.py`, which composes the full page.
"""

from __future__ import annotations

import streamlit as st

from config.logging_config import get_logger, setup_logging
from config.settings import get_settings
from ui.layout import render_app


def main() -> None:
    """Application entry point."""
    settings = get_settings()

    setup_logging(
        log_level=settings.log_level,
        log_to_file=settings.log_to_file,
        log_file_path=settings.log_file_path,
    )
    logger = get_logger(__name__)
    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)

    st.set_page_config(
        page_title=settings.app_name,
        page_icon="🦈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_app()

    logger.debug("Page render complete.")


if __name__ == "__main__":
    main()
