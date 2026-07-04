"""
Tests for application configuration.
"""

from __future__ import annotations

from config.settings import Settings, get_settings


def test_settings_load_with_defaults(monkeypatch):
    """Settings should load successfully with no environment variables set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = get_settings()

    assert isinstance(settings, Settings)
    assert settings.app_name == "Shark Tank AI"
    assert settings.has_llm_credentials is False


def test_settings_is_cached():
    """get_settings() should return the same instance across calls."""
    first = get_settings()
    second = get_settings()
    assert first is second


def test_has_llm_credentials_true_when_key_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.has_llm_credentials is True
