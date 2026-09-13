"""
Anthropic provider implementation for Shark Tank AI.

Implements `BaseProvider` against the real `anthropic` SDK. This is
the only piece of code in the repository that imports `anthropic` or
knows anything about its request/response shapes — per
`docs/architecture.md` -> LLM Provider Layer, agents talk only to
`BaseProvider.generate()` and never see an Anthropic-specific type.

Credentials come exclusively from `config.settings.Settings`
(`ANTHROPIC_API_KEY` / `.env`), which itself reads from environment
variables — never hardcoded, never read from `st.session_state` or any
other source. See `agents/shark_agent.py` for how a Shark constructs
its `messages` and handles this provider's failures.
"""

from __future__ import annotations

from typing import Any

import anthropic

from config.logging_config import get_logger
from providers.base_provider import BaseProvider
from providers.exceptions import (
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderResponseError,
)

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1024

# anthropic SDK exceptions that represent a failed request (network,
# timeout, auth, rate limit, server error, ...) as opposed to a
# programming error on our side. Anything else is left to propagate
# as-is rather than being silently reclassified.
_REQUEST_FAILURE_TYPES = (anthropic.APIError, anthropic.AnthropicError)


class AnthropicProvider(BaseProvider):
    """`BaseProvider` implementation backed by the Anthropic Messages API."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        super().__init__(api_key=api_key, model=model or DEFAULT_MODEL)
        self._client: anthropic.Anthropic | None = None

    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate a text completion for `messages`.

        `messages` follows the common `[{"role": ..., "content": ...}]`
        convention shared across providers (see `BaseProvider`); any
        leading `role="system"` entries are pulled out and passed as
        the Anthropic API's separate top-level `system` parameter --
        that translation is exactly the provider-specific detail
        `agents/shark_agent.py` should never need to know about.

        `kwargs["tools"]`, if given, is forwarded to the API as-is
        (used by `providers.anthropic_research_provider
        .AnthropicResearchProvider` to enable Anthropic's server-side
        web search tool) -- this provider does not interpret or
        validate tool definitions itself.

        Raises:
            ProviderNotConfiguredError: no API key is configured.
            ProviderRequestError: the API call itself failed (network,
                auth, rate limit, timeout, server error).
            ProviderResponseError: the call succeeded but returned no
                usable text content.
        """
        if not self.is_configured:
            raise ProviderNotConfiguredError(
                "AnthropicProvider has no API key configured "
                "(set ANTHROPIC_API_KEY in the environment or .env)"
            )

        system_prompt, chat_messages = _split_system_messages(messages)
        if not chat_messages:
            raise ProviderResponseError("No non-system messages to send to the provider")

        max_tokens = kwargs.get("max_tokens", DEFAULT_MAX_TOKENS)

        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": chat_messages,
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt
        if kwargs.get("tools"):
            create_kwargs["tools"] = kwargs["tools"]

        try:
            response = self._get_client().messages.create(**create_kwargs)
        except _REQUEST_FAILURE_TYPES as exc:
            # Never log the messages themselves (may contain founder-
            # submitted pitch text) or the API key -- only what kind of
            # failure this was, per docs/coding_standards.md and this
            # release's spec section B29.
            logger.warning("Anthropic request failed: %s", type(exc).__name__)
            raise ProviderRequestError(f"Anthropic request failed: {exc}") from exc

        text = _extract_text(response)
        if not text:
            logger.warning("Anthropic response contained no usable text content")
            raise ProviderResponseError("Anthropic response contained no text content")
        return text

    def _get_client(self) -> anthropic.Anthropic:
        """Lazily construct the SDK client on first use.

        Deferred rather than built in `__init__` so that constructing
        an `AnthropicProvider` (e.g. to check `is_configured`) never
        touches the network or requires a key, and so tests can swap
        in a fake client without an `Anthropic()` call ever happening.
        """
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client


def _split_system_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    """Split `messages` into a combined system prompt and the remaining
    user/assistant turns, preserving order of the non-system messages."""
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    chat_messages = [m for m in messages if m.get("role") != "system"]
    return "\n\n".join(system_parts), chat_messages


def _extract_text(response: Any) -> str:
    """Concatenate every text content block in an Anthropic `Message`
    response. Returns an empty string if there is none (e.g. the model
    only returned a tool-use block, which this provider doesn't send
    tools to trigger, but defends against anyway)."""
    blocks = getattr(response, "content", None) or []
    text_parts = [block.text for block in blocks if getattr(block, "type", None) == "text"]
    return "".join(text_parts).strip()
