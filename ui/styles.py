"""
Shared styling for Shark Tank AI.

All custom CSS lives in one place so every UI component references
the same class names instead of scattering inline styles. This module
only injects CSS — it contains no application logic.
"""

from __future__ import annotations

import streamlit as st

_CSS = """
<style>
/* ---------- Header ---------- */
.stka-header-title {
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 0.1rem;
}
.stka-subtitle {
    font-size: 1.05rem;
    color: var(--stka-muted, #808495);
    margin-bottom: 1.1rem;
}

/* ---------- Progress stepper ---------- */
.stka-stepper {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 1.4rem;
}
.stka-step {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    border: 1px solid rgba(128, 132, 149, 0.35);
    white-space: nowrap;
}
.stka-step-index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.2rem;
    height: 1.2rem;
    border-radius: 50%;
    font-size: 0.68rem;
    background: rgba(128, 132, 149, 0.18);
}
.stka-step-pending {
    opacity: 0.45;
}
.stka-step-done {
    opacity: 0.75;
    border-color: rgba(46, 160, 67, 0.5);
}
.stka-step-done .stka-step-index {
    background: rgba(46, 160, 67, 0.25);
}
.stka-step-active {
    opacity: 1;
    border-color: #ff4b4b;
    box-shadow: 0 0 0 1px rgba(255, 75, 75, 0.25);
}
.stka-step-active .stka-step-index {
    background: #ff4b4b;
    color: white;
}

/* ---------- Session stage card ---------- */
.stka-stage-card {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    padding: 0.9rem 1.1rem;
    border-radius: 0.6rem;
    background: rgba(128, 132, 149, 0.08);
    border: 1px solid rgba(128, 132, 149, 0.25);
    margin: 0.8rem 0 1.2rem 0;
}
.stka-stage-card-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--stka-muted, #808495);
}
.stka-stage-card-message {
    font-size: 1rem;
    font-weight: 500;
}

/* ---------- Conversation history ---------- */
.stka-speaker-bubble {
    border-radius: 0.6rem;
    padding: 0.7rem 1rem;
    margin-bottom: 0.65rem;
    border-left: 4px solid rgba(128, 132, 149, 0.5);
    background: rgba(128, 132, 149, 0.06);
}
.stka-speaker-meta {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.25rem;
}
.stka-speaker-name {
    font-weight: 700;
    font-size: 0.85rem;
}
.stka-speaker-timestamp {
    font-size: 0.72rem;
    color: var(--stka-muted, #808495);
}
.stka-speaker-message {
    font-size: 0.95rem;
    line-height: 1.4;
}

.stka-speaker-moderator {
    border-left-color: #808495;
    background: rgba(128, 132, 149, 0.10);
}
.stka-speaker-growth {
    border-left-color: #2ea043;
    background: rgba(46, 160, 67, 0.08);
}
.stka-speaker-financial {
    border-left-color: #d4a72c;
    background: rgba(212, 167, 44, 0.10);
}
.stka-speaker-technical {
    border-left-color: #1f6feb;
    background: rgba(31, 111, 235, 0.08);
}
.stka-speaker-marketing {
    border-left-color: #a371f7;
    background: rgba(163, 113, 247, 0.09);
}
.stka-speaker-risk {
    border-left-color: #ff4b4b;
    background: rgba(255, 75, 75, 0.08);
}
.stka-speaker-founder {
    border-left-color: #58a6ff;
    background: rgba(88, 166, 255, 0.10);
    margin-left: 1.5rem;
}

/* ---------- Bottom control bar ---------- */
/* `position: sticky` (rather than `fixed`) keeps this anchored to the
   bottom of the normal document flow without needing to target
   Streamlit's internal container classes, which change between
   versions. The spacer above it reserves room so it doesn't overlap
   the last piece of real content. */
.stka-bottom-bar-spacer {
    height: 0.5rem;
}
.stka-bottom-bar {
    position: sticky;
    bottom: 0;
    z-index: 100;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    padding: 0.9rem 1rem;
    margin-top: 1rem;
    border-top: 1px solid rgba(128, 132, 149, 0.35);
    background: var(--stka-bar-bg, rgba(14, 17, 23, 0.92));
    backdrop-filter: blur(6px);
}
.stka-bottom-bar-instruction {
    font-size: 0.92rem;
    font-weight: 500;
}
</style>
"""


def inject_global_styles() -> None:
    """Inject the application's shared CSS once per page render."""
    st.markdown(_CSS, unsafe_allow_html=True)
