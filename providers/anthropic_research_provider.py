"""
Anthropic-backed research provider.

Implements `BaseResearchProvider` by asking an `AnthropicProvider` to
run its request through Anthropic's server-side web search tool and
self-report the sources it actually retrieved as structured JSON. This
is a real, internet-connected search when `ANTHROPIC_API_KEY` is
configured -- not a simulation and not the model's unaided training
knowledge -- using only the credential the application already
requires for everything else (Release 0.6 spec Part S: no new search
vendor/API key is introduced).

**Documented limitation:** this provider does not independently
re-fetch or verify each URL the model reports; it trusts the model's
self-report of what the tool actually returned. The model is
explicitly instructed never to fabricate a URL
(`prompts/market_research_search.txt`), and a fabricated or
inconsistent-looking source is exactly the kind of risk
`docs/architecture.md` -> Market Reality Research documents as a
known limitation of this approach, not a solved problem. A future
release could replace this with a provider backed by a dedicated
search API and independent URL verification without changing
`BaseResearchProvider`'s interface.
"""

from __future__ import annotations

import json

from config.logging_config import get_logger
from prompts.loader import load_prompt
from providers.base_provider import BaseProvider
from providers.base_research_provider import BaseResearchProvider, RawSearchResult
from providers.exceptions import (
    ProviderError,
    ResearchProviderRequestError,
    ResearchProviderResponseError,
)

logger = get_logger(__name__)

#: Anthropic's server-side web search tool. `max_uses` bounds how many
#: individual searches the model may run per call, so one Market
#: Reality Research pass can't spiral into unbounded tool use.
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 6}

_MAX_TOKENS_SEARCH = 2000


class AnthropicResearchProvider(BaseResearchProvider):
    """`BaseResearchProvider` implementation backed by an `AnthropicProvider`."""

    def __init__(self, llm_provider: BaseProvider) -> None:
        self._llm_provider = llm_provider

    @property
    def is_configured(self) -> bool:
        return self._llm_provider.is_configured

    def search(self, query: str, max_results: int = 8) -> list[RawSearchResult]:
        template = load_prompt("market_research_search")
        prompt = template.replace("{query}", query).replace("{max_results}", str(max_results))
        messages = [{"role": "user", "content": prompt}]

        try:
            raw = self._llm_provider.generate(
                messages, max_tokens=_MAX_TOKENS_SEARCH, tools=[WEB_SEARCH_TOOL]
            )
        except ProviderError as exc:
            logger.warning("Research search request failed: %s", type(exc).__name__)
            raise ResearchProviderRequestError(f"Research search failed: {exc}") from exc

        data = _parse_json_object(raw)
        results = data.get("results", [])
        if not isinstance(results, list):
            raise ResearchProviderResponseError("Search response 'results' was not a list")

        parsed: list[RawSearchResult] = []
        for item in results[:max_results]:
            try:
                parsed.append(
                    RawSearchResult(
                        title=str(item["title"]),
                        url=str(item["url"]),
                        snippet=str(item.get("snippet") or ""),
                        published_date=item.get("published_date"),
                    )
                )
            except (KeyError, TypeError):
                # Skip a malformed individual result rather than
                # failing the whole search -- a partial, honest result
                # set is preferable to discarding everything.
                continue
        return parsed


def _parse_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        stripped = text.lstrip()
        if stripped[:4].lower() == "json":
            text = stripped[4:]
        text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ResearchProviderResponseError(f"Could not parse search JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ResearchProviderResponseError("Search response JSON was not an object")
    return data
