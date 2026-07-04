"""
Home page component for the Shark Tank AI Streamlit app.

Renders a placeholder landing page describing the intended product
while no agent, orchestrator, or provider functionality exists yet.
"""

from __future__ import annotations

import streamlit as st

from config.settings import Settings


def render_home(settings: Settings) -> None:
    """Render the main landing page content."""
    st.title("🦈 Shark Tank AI")
    st.subheader("Pitch your startup to a panel of AI investors")

    st.markdown(
        """
        Welcome to **Shark Tank AI** — an AI multi-agent application where
        founders pitch their startup idea and a panel of AI-driven "shark"
        investors evaluate the pitch, ask questions, and negotiate a deal.

        > **Project status:** This is currently a scaffold. The interface
        > below is a placeholder — pitch submission, agent evaluation, and
        > negotiation logic have not been implemented yet.
        """
    )

    with st.form("pitch_form_placeholder"):
        st.text_input("Company name", placeholder="e.g. Acme Robotics", disabled=False)
        st.text_area("Pitch description", placeholder="Describe your business...")
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Amount requested ($)", min_value=0.0, step=1000.0)
        with col2:
            st.number_input("Equity offered (%)", min_value=0.0, max_value=100.0, step=0.5)

        submitted = st.form_submit_button("Pitch to the Sharks")

    if submitted:
        st.info(
            "Pitch submission is not yet implemented. "
            "This scaffold does not contain any agent or orchestrator logic."
        )

    st.divider()
    st.caption(f"Running as **{settings.app_name}** in `{settings.app_env}` mode.")
