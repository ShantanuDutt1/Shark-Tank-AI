"""
Market Reality Research agent for Shark Tank AI (Release 0.6).

Answers, for a given pitch: "how realistic are this founder's market,
financial, growth, competitive, and valuation claims given current
external evidence?" Runs once per session, after `VALIDATION` and
before `QUESTION_ROUND` (`docs/state_machines.md`).

Two-step design, matching the separation between "gather evidence" and
"reason about it" that the rest of this codebase already uses for
Sharks:

1. `providers.base_research_provider.BaseResearchProvider.search()`
   gathers raw, provenance-carrying search results (production:
   `providers.anthropic_research_provider.AnthropicResearchProvider`;
   tests: `tests.fakes.MockResearchProvider`).
2. A plain `BaseProvider.generate()` call (the same kind
   `agents/shark_agent.py` and `agents/moderator_agent.py` make)
   synthesizes those raw results, plus the pitch itself, into a
   structured `models.schemas.MarketRealityBrief`.

Both the pitch and every raw search result are treated as untrusted
content (`agents.prompt_safety.wrap_untrusted()`) in the synthesis
prompt -- a founder's proposal *or* a retrieved web page could contain
text that reads like an instruction, and neither should be able to
change this agent's behavior (Release 0.6 spec Parts F and T).

Like `SharkAgent`, `research()` *raises* a specific
`ProviderError`/`ResearchProviderError` on failure rather than
degrading itself; `orchestrator/orchestrator.py` catches it and calls
`fallback_brief()`.
"""

from __future__ import annotations

import json
from typing import Any

from agents.prompt_safety import wrap_untrusted
from config.logging_config import get_logger
from models.schemas import (
    ClaimAssessment,
    MarketRealityBrief,
    Pitch,
    ResearchSource,
    ValuationEstimate,
)
from prompts.loader import load_prompt
from providers.base_provider import BaseProvider
from providers.base_research_provider import BaseResearchProvider, RawSearchResult
from providers.exceptions import (
    ProviderNotConfiguredError,
    ProviderResponseError,
    ResearchProviderError,
)

logger = get_logger(__name__)

_MAX_TOKENS_SYNTHESIS = 1800
_MAX_SEARCH_RESULTS = 8


class MarketResearchAgent:
    """Gathers and synthesizes external market evidence for a pitch."""

    def __init__(
        self,
        llm_provider: BaseProvider | None = None,
        research_provider: BaseResearchProvider | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.research_provider = research_provider

    def research(self, pitch: Pitch) -> MarketRealityBrief:
        """Produce a real Market Reality Brief for `pitch`.

        Raises `ProviderNotConfiguredError`/`ProviderRequestError`/
        `ProviderResponseError` if the synthesis LLM call fails. A
        failed or unconfigured *research provider* is handled more
        gently -- it degrades to zero raw search results (and a noted
        limitation), not a raised exception, since the LLM can still
        produce a (clearly lower-confidence) brief from the pitch
        alone.
        """
        if self.llm_provider is None or not self.llm_provider.is_configured:
            raise ProviderNotConfiguredError("MarketResearchAgent has no LLM provider configured")

        raw_results, research_note = self._gather_evidence(pitch)
        prompt = self._build_synthesis_prompt(pitch, raw_results, research_note)
        messages = [{"role": "user", "content": prompt}]
        raw = self.llm_provider.generate(messages, max_tokens=_MAX_TOKENS_SYNTHESIS)
        data = _parse_json_object(raw)
        return _brief_from_json(pitch, data, raw_results)

    def fallback_brief(self, pitch: Pitch, reason: str) -> MarketRealityBrief:
        """An honest "no research was possible" brief, used when
        `research()` raises. Never fabricates market size, valuation,
        or claim assessments."""
        return MarketRealityBrief(
            pitch_id=pitch.id,
            valuation=ValuationEstimate(confidence="insufficient_evidence"),
            research_limitations=(
                f"Market research could not be completed ({reason}); no external "
                "evidence was gathered for this session. The committee's "
                "questions and evaluation below rely only on the proposal and "
                "the founder's answers."
            ),
            is_fallback=True,
        )

    def _gather_evidence(self, pitch: Pitch) -> tuple[list[RawSearchResult], str]:
        """Best-effort raw evidence gathering. Returns `(results, note)`
        where `note` explains degraded/absent evidence for inclusion in
        the synthesis prompt -- never raises."""
        if self.research_provider is None or not self.research_provider.is_configured:
            return [], "No research provider was configured; no live web search was performed."
        try:
            query = _build_search_query(pitch)
            results = self.research_provider.search(query, max_results=_MAX_SEARCH_RESULTS)
            if not results:
                return [], "The search provider returned no results for this proposal."
            return results, ""
        except ResearchProviderError as exc:
            # Evidence-gathering is explicitly best-effort: a failed
            # search must not block the whole research step (Release
            # 0.6 spec Part Q) -- degrade to "no evidence" and let the
            # LLM synthesis call still run (at lower confidence). Only
            # `ResearchProviderError` (the interface's documented
            # failure contract, per `BaseResearchProvider.search()`)
            # is caught here; anything else is a genuine bug and
            # propagates normally, per `docs/coding_standards.md`.
            logger.warning("Research evidence gathering failed: %s", type(exc).__name__)
            return [], f"Web search failed ({type(exc).__name__}); no live evidence was gathered."

    def _build_synthesis_prompt(
        self, pitch: Pitch, raw_results: list[RawSearchResult], research_note: str
    ) -> str:
        template = load_prompt("market_research_synthesis")
        ask_summary = _format_ask_summary(pitch)
        search_results_text = _format_raw_results(raw_results) or "(No search results available.)"
        if research_note:
            search_results_text = f"{research_note}\n\n{search_results_text}"

        rendered = template
        rendered = rendered.replace("{company_name}", pitch.company_name)
        rendered = rendered.replace("{ask_summary}", ask_summary)
        rendered = rendered.replace(
            "{wrapped_pitch}", wrap_untrusted(pitch.description, label="founder_pitch")
        )
        rendered = rendered.replace(
            "{wrapped_search_results}",
            wrap_untrusted(search_results_text, label="retrieved_search_results"),
        )
        return rendered


def _build_search_query(pitch: Pitch) -> str:
    description = pitch.description[:300]
    return (
        f"{pitch.company_name}: {description} -- market size, growth, competitors, "
        "typical margins/multiples, and comparable funding or acquisition transactions"
    )


def _format_ask_summary(pitch: Pitch) -> str:
    parts = []
    if pitch.ask_amount is not None:
        parts.append(f"${pitch.ask_amount:,.0f}")
    if pitch.equity_offered_pct is not None:
        parts.append(f"for {pitch.equity_offered_pct:.1f}% equity")
    if pitch.valuation is not None:
        parts.append(f"(implied valuation ${pitch.valuation:,.0f})")
    return " ".join(parts) if parts else "Not stated."


def _format_raw_results(results: list[RawSearchResult]) -> str:
    if not results:
        return ""
    lines = []
    for r in results:
        date_part = f" ({r.published_date})" if r.published_date else ""
        lines.append(f"- {r.title}{date_part} [{r.url}]: {r.snippet}")
    return "\n".join(lines)


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
        raise ProviderResponseError(f"Could not parse market research JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProviderResponseError("Market research response JSON was not an object")
    return data


def _brief_from_json(
    pitch: Pitch, data: dict, raw_results: list[RawSearchResult]
) -> MarketRealityBrief:
    valuation_data = data.get("valuation") or {}
    valuation = ValuationEstimate(
        methodology=str(valuation_data.get("methodology") or ""),
        low=_optional_float(valuation_data.get("low")),
        high=_optional_float(valuation_data.get("high")),
        assumptions=str(valuation_data.get("assumptions") or ""),
        confidence=str(valuation_data.get("confidence") or "insufficient_evidence"),
    )

    sources = [
        ResearchSource(
            title=r.title,
            url=r.url,
            source_type="web_search",
            published_date=r.published_date,
            relevant_fact=r.snippet,
            reliability="unverified",
        )
        for r in raw_results
    ]

    return MarketRealityBrief(
        pitch_id=pitch.id,
        industry=str(data.get("industry") or ""),
        business_model=str(data.get("business_model") or ""),
        market_summary=str(data.get("market_summary") or ""),
        market_size_estimate=str(data.get("market_size_estimate") or ""),
        market_growth=str(data.get("market_growth") or ""),
        competitors=[str(c) for c in (data.get("competitors") or [])],
        financial_benchmarks=str(data.get("financial_benchmarks") or ""),
        relevant_transactions=str(data.get("relevant_transactions") or ""),
        valuation=valuation,
        founder_implied_valuation=_optional_float(data.get("founder_implied_valuation")),
        valuation_comparison=str(data.get("valuation_comparison") or ""),
        validated_claims=_claims_from_json(data.get("validated_claims")),
        unsupported_claims=_claims_from_json(data.get("unsupported_claims")),
        material_discrepancies=[str(d) for d in (data.get("material_discrepancies") or [])],
        research_limitations=str(data.get("research_limitations") or ""),
        sources=sources,
        is_fallback=False,
    )


def _claims_from_json(items: Any) -> list[ClaimAssessment]:
    if not isinstance(items, list):
        return []
    claims = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            claims.append(
                ClaimAssessment(
                    claim=str(item.get("claim", "")),
                    external_evidence=str(item.get("external_evidence", "")),
                    assessment=str(item.get("assessment", "")),
                )
            )
        except (TypeError, ValueError):
            continue
    return claims


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
