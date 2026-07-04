"""
Shared pytest fixtures for Shark Tank AI tests.
"""

from __future__ import annotations

import pytest

from config.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Ensure each test gets a fresh Settings instance."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
