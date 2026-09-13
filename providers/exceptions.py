"""
Specific exception types for LLM provider failures.

Mirrors `orchestrator/exceptions.py`'s pattern: every unrecoverable
failure gets its own specific type (per `docs/coding_standards.md` and
`docs/agent_contract.md` -> *Error Handling*), never a bare
`Exception`, so callers can distinguish "not configured" from "the
network failed" from "the response was garbage."
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for every LLM provider error."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when a provider is used without the credentials it needs
    (e.g. no API key in configuration). Unrecoverable without a
    configuration change -- retrying the same call will never help."""


class ProviderRequestError(ProviderError):
    """Raised when the underlying API call itself fails: a network
    error, a timeout, or an error response from the provider. May be
    transient, but Release 0.5 does not implement retries (see
    `agents/shark_agent.py`'s module docstring for how callers are
    expected to degrade instead of retrying)."""


class ProviderResponseError(ProviderError):
    """Raised when the provider responds successfully at the transport
    level but the response is empty, malformed, or otherwise unusable
    (e.g. no text content block)."""


class ResearchProviderError(Exception):
    """Base class for every research-provider error.

    A deliberately separate hierarchy from `ProviderError` above:
    `BaseResearchProvider` (`providers/base_research_provider.py`) is a
    distinct abstraction from `BaseProvider` (LLM text generation),
    per Release 0.6 spec Part S -- conflating their exception
    hierarchies would blur that boundary.
    """


class ResearchProviderNotConfiguredError(ResearchProviderError):
    """Raised when a research provider is used without the credentials
    it needs."""


class ResearchProviderRequestError(ResearchProviderError):
    """Raised when the underlying search request itself fails."""


class ResearchProviderResponseError(ResearchProviderError):
    """Raised when a search request succeeds but its response is empty,
    malformed, or otherwise unusable."""
