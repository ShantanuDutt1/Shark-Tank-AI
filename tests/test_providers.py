"""
Tests for `providers.anthropic_provider.AnthropicProvider`.

Never makes a real network call: `_get_client()` is monkeypatched to
return a fake object shaped like the bits of the `anthropic` SDK this
module actually touches (`client.messages.create(...)` returning
something with a `.content` list of text blocks), per Release 0.5
spec section B27 ("do not make the test suite depend on live
Anthropic API calls").
"""

from __future__ import annotations

from types import SimpleNamespace

import anthropic
import pytest

from providers.anthropic_provider import AnthropicProvider
from providers.exceptions import (
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderResponseError,
)


def _text_response(text: str) -> SimpleNamespace:
    """A fake Anthropic `Message`-shaped response with one text block."""
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


class _FakeMessages:
    def __init__(self, result=None, exception=None, captured_kwargs=None):
        self._result = result
        self._exception = exception
        self._captured_kwargs = captured_kwargs if captured_kwargs is not None else {}

    def create(self, **kwargs):
        self._captured_kwargs.update(kwargs)
        if self._exception is not None:
            raise self._exception
        return self._result


class _FakeClient:
    def __init__(self, messages: _FakeMessages) -> None:
        self.messages = messages


def _provider_with_fake_client(provider: AnthropicProvider, fake_messages: _FakeMessages) -> None:
    provider._client = _FakeClient(fake_messages)  # bypass _get_client()'s lazy real construction


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------


def test_missing_api_key_raises_not_configured():
    provider = AnthropicProvider(api_key=None)
    with pytest.raises(ProviderNotConfiguredError):
        provider.generate([{"role": "user", "content": "hello"}])


def test_is_configured_reflects_api_key_presence():
    assert AnthropicProvider(api_key="sk-test").is_configured is True
    assert AnthropicProvider(api_key=None).is_configured is False


def test_default_model_is_set_when_none_given():
    provider = AnthropicProvider(api_key="sk-test")
    assert provider.model


# ---------------------------------------------------------------------
# Successful generation
# ---------------------------------------------------------------------


def test_successful_generation_returns_text():
    provider = AnthropicProvider(api_key="sk-test")
    captured: dict = {}
    _provider_with_fake_client(
        provider, _FakeMessages(result=_text_response("Hello there."), captured_kwargs=captured)
    )

    result = provider.generate([{"role": "user", "content": "hi"}])

    assert result == "Hello there."
    assert captured["model"] == provider.model
    assert captured["messages"] == [{"role": "user", "content": "hi"}]
    assert "system" not in captured


def test_system_role_messages_are_split_into_system_param():
    provider = AnthropicProvider(api_key="sk-test")
    captured: dict = {}
    _provider_with_fake_client(
        provider, _FakeMessages(result=_text_response("ok"), captured_kwargs=captured)
    )

    provider.generate(
        [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "hi"},
        ]
    )

    assert captured["system"] == "You are a helpful assistant."
    assert captured["messages"] == [{"role": "user", "content": "hi"}]


def test_max_tokens_kwarg_is_forwarded():
    provider = AnthropicProvider(api_key="sk-test")
    captured: dict = {}
    _provider_with_fake_client(
        provider, _FakeMessages(result=_text_response("ok"), captured_kwargs=captured)
    )

    provider.generate([{"role": "user", "content": "hi"}], max_tokens=42)

    assert captured["max_tokens"] == 42


# ---------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------


def test_api_error_is_wrapped_as_provider_request_error():
    provider = AnthropicProvider(api_key="sk-test")
    fake_request = SimpleNamespace(method="POST", url="https://api.anthropic.com/v1/messages")
    api_error = anthropic.APIConnectionError(message="connection failed", request=fake_request)
    _provider_with_fake_client(provider, _FakeMessages(exception=api_error))

    with pytest.raises(ProviderRequestError):
        provider.generate([{"role": "user", "content": "hi"}])


def test_empty_response_raises_provider_response_error():
    provider = AnthropicProvider(api_key="sk-test")
    _provider_with_fake_client(provider, _FakeMessages(result=_text_response("")))

    with pytest.raises(ProviderResponseError):
        provider.generate([{"role": "user", "content": "hi"}])


def test_response_with_no_text_blocks_raises_provider_response_error():
    provider = AnthropicProvider(api_key="sk-test")
    non_text_response = SimpleNamespace(content=[SimpleNamespace(type="tool_use", text=None)])
    _provider_with_fake_client(provider, _FakeMessages(result=non_text_response))

    with pytest.raises(ProviderResponseError):
        provider.generate([{"role": "user", "content": "hi"}])


def test_no_non_system_messages_raises_provider_response_error():
    provider = AnthropicProvider(api_key="sk-test")
    with pytest.raises(ProviderResponseError):
        provider.generate([{"role": "system", "content": "only a system message"}])
