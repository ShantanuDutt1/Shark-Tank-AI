"""
Prompt template loader for Shark Tank AI.

Loads plain-text prompt templates from this directory so agents can
reference them by name without hardcoding prompt text in Python
modules. No prompt content has been finalized yet.
"""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template file by name (without extension).

    Example: load_prompt("shark_persona_system")
    """
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")
