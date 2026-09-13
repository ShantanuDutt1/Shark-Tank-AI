"""
Test doubles for Shark Tank AI's provider abstraction.

`FakeProvider` implements `providers.base_provider.BaseProvider`
exactly like `AnthropicProvider` does, so tests exercise the real
`SharkAgent` / `SharkTankOrchestrator` code paths without ever making
a network call or requiring an API key (Release 0.5 spec section
B27). This is not a second provider abstraction -- it's the one
legitimate implementation of the existing one that belongs in tests.
"""

from __future__ import annotations

from typing import Any

from providers.base_provider import BaseProvider
from providers.base_research_provider import BaseResearchProvider, RawSearchResult
from providers.exceptions import (
    ProviderError,
    ProviderNotConfiguredError,
    ResearchProviderError,
    ResearchProviderNotConfiguredError,
)


class FakeProvider(BaseProvider):
    """A scriptable, offline `BaseProvider` double.

    - With `fixed_response` (the default mode): every call to
      `generate()` returns the same string.
    - With `responses`: a list of strings (or exception instances, to
      script a failure at a specific point) returned/raised one at a
      time, in order, across successive calls -- for tests where
      different calls need different scripted outcomes.
    - With `raise_error`: every call raises that `ProviderError`
      instance instead of returning anything, for testing failure
      paths.

    Every call's `messages` argument is recorded in `.calls`, in
    order, so a test can assert on exactly what a `SharkAgent` sent
    (e.g. that the persona's name appears in the system prompt, or
    that the founder's answer appears in the user prompt).
    """

    def __init__(
        self,
        *,
        fixed_response: str = "OK",
        responses: list[str] | None = None,
        raise_error: ProviderError | None = None,
        api_key: str | None = "fake-test-key",
        model: str = "fake-test-model",
    ) -> None:
        super().__init__(api_key=api_key, model=model)
        self._fixed_response = fixed_response
        self._responses = list(responses) if responses is not None else None
        self._raise_error = raise_error
        self.calls: list[list[dict[str, str]]] = []

    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self.calls.append(messages)
        if not self.is_configured:
            raise ProviderNotConfiguredError("FakeProvider has no api_key configured")
        if self._raise_error is not None:
            raise self._raise_error
        if self._responses is not None:
            if not self._responses:
                raise AssertionError("FakeProvider ran out of scripted responses")
            next_item = self._responses.pop(0)
            if isinstance(next_item, BaseException):
                raise next_item
            return next_item
        return self._fixed_response

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def last_user_message(self) -> str:
        """The `content` of the most recent call's last message (by
        convention, the user-turn prompt -- see `SharkAgent._generate()`,
        which always sends `[system, user]`)."""
        return self.calls[-1][-1]["content"]

    def last_system_message(self) -> str:
        """The `content` of the most recent call's system message."""
        return self.calls[-1][0]["content"]


def unconfigured_provider() -> FakeProvider:
    """A `FakeProvider` with no API key, for testing the
    not-configured path (`AnthropicProvider` raises the same way when
    `ANTHROPIC_API_KEY` is unset -- this exercises the same contract
    without needing to touch real settings/environment)."""
    return FakeProvider(api_key=None)


class MockResearchProvider(BaseResearchProvider):
    """A scriptable, offline `BaseResearchProvider` double (Release 0.6
    spec Part S: "the application must not make normal unit tests
    dependent on live websites").

    - With `results` (the default mode): every call to `search()`
      returns the same list of `RawSearchResult`.
    - With `raise_error`: every call raises that
      `ResearchProviderError` instead.

    Every call's `query` is recorded in `.queries`, in order.
    """

    def __init__(
        self,
        *,
        results: list[RawSearchResult] | None = None,
        raise_error: ResearchProviderError | None = None,
        configured: bool = True,
    ) -> None:
        self._results = results if results is not None else []
        self._raise_error = raise_error
        self._configured = configured
        self.queries: list[str] = []

    @property
    def is_configured(self) -> bool:
        return self._configured

    def search(self, query: str, max_results: int = 8) -> list[RawSearchResult]:
        self.queries.append(query)
        if not self._configured:
            raise ResearchProviderNotConfiguredError("MockResearchProvider is not configured")
        if self._raise_error is not None:
            raise self._raise_error
        return list(self._results[:max_results])
