"""
Small ID-generation utility for Shark Tank AI.

Centralized here so every part of the app creates IDs the same way.
"""

from __future__ import annotations

import uuid


def new_id(prefix: str = "") -> str:
    """Generate a unique identifier, optionally prefixed (e.g. 'pitch_')."""
    suffix = uuid.uuid4().hex[:12]
    return f"{prefix}{suffix}" if prefix else suffix
