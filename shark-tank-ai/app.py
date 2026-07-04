"""
Shark Tank AI — Streamlit application entry point.

Run with:
    streamlit run app.py

This entry point wires together configuration, logging, and the UI
layer. It is intentionally free of agent/orchestrator business logic —
the goal is a project scaffold that starts successfully with zero
configuration, ready for real functionality to be layered in.
"""

from __future__ import annotations

import streamlit as st

from config.logging_config import setup_logging, get_logger
from config.settings import get_settings
from ui.home import render_home
from ui.sidebar import render_sidebar


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

    render_sidebar(settings)
    render_home(settings)

    logger.debug("Page render complete.")


if __name__ == "__main__":
    main()
