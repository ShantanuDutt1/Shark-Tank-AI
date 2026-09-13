"""
Research provider abstraction for Shark Tank AI.

Release 0.6 spec Part S: a small, replaceable interface for gathering
raw external evidence (web search results), kept deliberately separate
from `BaseProvider` (LLM text generation) -- `agents/market_research_agent.py`
depends on this interface to *gather* evidence and on `BaseProvider`
(via a plain `generate()` call) to *reason about* it, mirroring how
`agents/shark_agent.py` already separates "what to say" from "how to
say it via a specific vendor."

Production: `providers/anthropic_research_provider.py`. Testing:
`tests.fakes.MockResearchProvider`. Neither the application nor
`MarketResearchAgent` should ever import a search-vendor-specific type
directly -- only this module's `BaseResearchProvider` / `RawSearchResult`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class RawSearchResult(BaseModel):
    """One raw search result, before any analysis or synthesis.

    Deliberately thin -- `title`/`url`/`snippet`/`published_date` are
    exactly what a search step can honestly claim to have retrieved.
    Reliability assessment and relevance to a specific founder claim
    are added later, by `agents/market_research_agent.py`'s synthesis
    step, as `models.schemas.ResearchSource` -- never fabricated here.
    """

    title: str
    url: str
    snippet: str = ""
    published_date: str | None = None


class BaseResearchProvider(ABC):
    """Abstract interface for gathering raw web evidence for a query."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this provider has what it needs to actually search
        (e.g. an API key) -- checked before every `search()` call, the
        same way `BaseProvider.is_configured` is checked before
        `generate()`."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, max_results: int = 8) -> list[RawSearchResult]:
        """Run a single search for `query` and return up to
        `max_results` raw results.

        Must raise a `providers.exceptions.ResearchProviderError`
        subclass on failure (unconfigured, request failure, or an
        unusable response) -- must never return a fabricated result or
        a fabricated URL.
        """
        raise NotImplementedError
