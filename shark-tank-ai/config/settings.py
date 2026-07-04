"""
Application configuration for Shark Tank AI.

Settings are loaded from environment variables (and an optional `.env`
file) using pydantic-settings. Every field has a safe default so the
application starts successfully even when no `.env` file is present and
no API keys have been configured yet.

Usage:
    from config.settings import get_settings

    settings = get_settings()
    print(settings.app_name)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings.

    All values can be overridden via environment variables or a `.env`
    file (see `.env.example`). None of the fields are required, so the
    app can start with zero configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General application settings ---
    app_name: str = Field(default="Shark Tank AI")
    app_env: str = Field(default="development")  # development | staging | production
    debug: bool = Field(default=True)

    # --- Streamlit / server settings ---
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8501)

    # --- Logging ---
    log_level: str = Field(default="INFO")
    log_to_file: bool = Field(default=False)
    log_file_path: str = Field(default="logs/app.log")

    # --- LLM provider settings (all optional; no functionality yet) ---
    llm_provider: str = Field(default="anthropic")
    llm_model: str = Field(default="claude-sonnet-4-6")
    anthropic_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)

    # --- Memory / persistence settings ---
    memory_backend: str = Field(default="in-memory")  # in-memory | sqlite | redis
    database_url: str = Field(default="sqlite:///./data/app.db")

    # --- Feature flags ---
    enable_multi_agent_debate: bool = Field(default=False)

    @property
    def is_production(self) -> bool:
        """Convenience flag for production-specific behavior."""
        return self.app_env.lower() == "production"

    @property
    def has_llm_credentials(self) -> bool:
        """Whether any LLM provider credentials have been configured."""
        return bool(self.anthropic_api_key or self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return a cached, process-wide Settings instance.

    Cached with lru_cache so environment variables are only parsed once
    per process, while remaining easy to reset in tests via
    `get_settings.cache_clear()`.
    """
    return Settings()
