"""
Market Reality Research agent for Shark Tank AI (Release 0.6, hardened
in Release 0.6.1).

Answers, for a given pitch: "how realistic are this founder's market,
financial, growth, competitive, and valuation claims given current
external evidence?" Runs once per session, after `VALIDATION` and
before `QUESTION_ROUND` (`docs/state_machines.md`).

Three-step design as of Release 0.6.1 (Release 0.6 had two; a planning
step was inserted first per spec Parts A/4-5 -- "research should begin
with an explicit research plan," not one broad, undifferentiated
query):

1. `agents.research_planner.build_research_plan()` -- a pure, offline,
   keyword-heuristic step that decides which small set of evidence
   categories (3-8) actually matter for this pitch's business model,
   before any network call happens.
2. `providers.base_research_provider.BaseResearchProvider.search()`,
   called once per planned objective, gathers raw, provenance-carrying
   search results (production:
   `providers.anthropic_research_provider.AnthropicResearchProvider`;
   tests: `tests.fakes.MockResearchProvider`). A failed individual
   objective is recorded and skipped, not treated as a total research
   failure (spec Part C §17, "partial research").
3. A plain `BaseProvider.generate()` call (the same kind
   `agents/shark_agent.py` and `agents/moderator_agent.py` make)
   synthesizes the deduplicated raw results, plus the pitch itself,
   into a structured `models.schemas.MarketRealityBrief`.

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
from urllib.parse import urlsplit

from agents.prompt_safety import wrap_untrusted
from agents.research_planner import build_research_plan
from config.logging_config import get_logger
from models.schemas import (
    CLAIM_STATUSES,
    ClaimAssessment,
    MarketRealityBrief,
    Pitch,
    ResearchPlan,
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
_MAX_RESULTS_PER_OBJECTIVE = 4

#: Domain-quality heuristic for `_classify_source_reliability()`,
#: following the source hierarchy documented in `docs/architecture.md`
#: -> Market Reality Research and Release 0.6 spec Part C §8. Coarse
#: substring matching on the URL's hostname -- not a claim of
#: independently verified quality, just a conservative, testable
#: signal. Anything not matched here stays "unverified" (spec Part C
#: §8: "if quality cannot be established, explicitly mark it
#: uncertain/unverified").
_HIGH_RELIABILITY_DOMAIN_MARKERS: tuple[str, ...] = (
    ".gov",
    ".gov.uk",
    "europa.eu",
    "sec.gov",
    "census.gov",
    "bls.gov",
    "worldbank.org",
    "imf.org",
    "oecd.org",
)
_MEDIUM_RELIABILITY_DOMAIN_MARKERS: tuple[str, ...] = (
    "bloomberg.com",
    "reuters.com",
    "wsj.com",
    "ft.com",
    "forbes.com",
    "techcrunch.com",
    "crunchbase.com",
    "pitchbook.com",
    "statista.com",
    "mckinsey.com",
    "gartner.com",
)


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
        gently -- it degrades to zero (or partial) raw search results
        (and a noted limitation), not a raised exception, since the
        LLM can still produce a (clearly lower-confidence) brief from
        the pitch alone.
        """
        if self.llm_provider is None or not self.llm_provider.is_configured:
            raise ProviderNotConfiguredError("MarketResearchAgent has no LLM provider configured")

        plan = build_research_plan(pitch)
        raw_results, failed_categories, research_note = self._gather_evidence(plan)
        deduped_results, duplicates_removed = _dedupe_results(raw_results)
        if duplicates_removed:
            dedup_note = f"{duplicates_removed} duplicate source(s) were removed before synthesis."
            research_note = f"{research_note}\n{dedup_note}" if research_note else dedup_note

        prompt = self._build_synthesis_prompt(pitch, deduped_results, research_note)
        messages = [{"role": "user", "content": prompt}]
        raw = self.llm_provider.generate(messages, max_tokens=_MAX_TOKENS_SYNTHESIS)
        data = _parse_json_object(raw)
        return _brief_from_json(
            pitch,
            data,
            deduped_results,
            research_objectives=[objective.category for objective in plan.objectives],
            failed_objectives=failed_categories,
        )

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

    def _gather_evidence(
        self, plan: ResearchPlan
    ) -> tuple[list[RawSearchResult], list[str], str]:
        """Best-effort raw evidence gathering across every objective in
        `plan`. Returns `(results, failed_categories, note)` where
        `note` explains degraded/absent/partial evidence for inclusion
        in the synthesis prompt -- never raises.

        A failed *individual* objective is recorded in
        `failed_categories` and skipped, never treated as a reason to
        abandon the rest of the plan (Release 0.6.1 spec Part C §17,
        "partial research"). This is deliberately distinct from "the
        search succeeded but found nothing" -- see
        `models.schemas.MarketRealityBrief.failed_objectives`'s
        docstring: research failure must never be represented as
        negative evidence (spec Part C §16).
        """
        if self.research_provider is None or not self.research_provider.is_configured:
            return [], [], "No research provider was configured; no live web search was performed."

        objectives = plan.objectives
        if not objectives:
            return [], [], "The research plan produced no objectives."

        all_results: list[RawSearchResult] = []
        failed_categories: list[str] = []
        for objective in objectives:
            try:
                results = self.research_provider.search(
                    objective.query, max_results=_MAX_RESULTS_PER_OBJECTIVE
                )
                all_results.extend(results)
            except ResearchProviderError as exc:
                # Evidence-gathering is explicitly best-effort: a
                # failed search must not block the rest of the plan
                # (Release 0.6 spec Part Q / 0.6.1 spec Part C §17).
                # Only `ResearchProviderError` (the interface's
                # documented failure contract, per
                # `BaseResearchProvider.search()`) is caught here;
                # anything else is a genuine bug and propagates
                # normally, per `docs/coding_standards.md`.
                logger.warning(
                    "Research objective '%s' failed: %s", objective.category, type(exc).__name__
                )
                failed_categories.append(objective.category)

        if len(failed_categories) == len(objectives):
            return (
                [],
                failed_categories,
                (
                    "Web search failed for every planned research category "
                    f"({', '.join(failed_categories)}); no live evidence was gathered."
                ),
            )
        if not all_results:
            note = "The search provider returned no results for any planned research category."
            if failed_categories:
                note += (
                    f" ({len(failed_categories)} of {len(objectives)} categories also failed "
                    f"outright: {', '.join(failed_categories)}.)"
                )
            return [], failed_categories, note
        if failed_categories:
            return (
                all_results,
                failed_categories,
                (
                    f"Some research categories could not be completed "
                    f"({', '.join(failed_categories)}); evidence below reflects only the "
                    "categories that succeeded."
                ),
            )
        return all_results, [], ""

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


def _dedupe_results(results: list[RawSearchResult]) -> tuple[list[RawSearchResult], int]:
    """Drop later results whose URL normalizes to one already seen.

    A lightweight strategy, deliberately not a syndication/near-
    duplicate detector (Release 0.6.1 spec Part C §20: "do not over-
    engineer this... a lightweight deduplication strategy is
    sufficient") -- it only catches the same URL reported more than
    once (e.g. by two different planned objectives), not two different
    URLs republishing the same underlying statistic.
    """
    seen: set[str] = set()
    deduped: list[RawSearchResult] = []
    for result in results:
        key = _normalize_url(result.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped, len(results) - len(deduped)


def _normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip().lower())
    return f"{parsed.netloc}{parsed.path.rstrip('/')}"


def _classify_source_reliability(url: str) -> str:
    """A coarse, deterministic source-quality tier from `url`'s
    hostname, per the preferred-source hierarchy documented in
    `docs/architecture.md` -> Market Reality Research (government/
    regulatory and major public statistics sources first, then
    recognized financial/industry publications and data providers).
    Never claims a quality this codebase can't actually establish --
    anything not matched stays `"unverified"`, the conservative
    default (spec Part C §8).
    """
    host = urlsplit(url.strip().lower()).netloc
    if any(marker in host for marker in _HIGH_RELIABILITY_DOMAIN_MARKERS):
        return "high"
    if any(marker in host for marker in _MEDIUM_RELIABILITY_DOMAIN_MARKERS):
        return "medium"
    return "unverified"


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
    pitch: Pitch,
    data: dict,
    raw_results: list[RawSearchResult],
    *,
    research_objectives: list[str],
    failed_objectives: list[str],
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
            reliability=_classify_source_reliability(r.url),
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
        founder_implied_valuation=_compute_founder_implied_valuation(pitch),
        valuation_comparison=str(data.get("valuation_comparison") or ""),
        validated_claims=_claims_from_json(data.get("validated_claims")),
        unsupported_claims=_claims_from_json(data.get("unsupported_claims")),
        material_discrepancies=[str(d) for d in (data.get("material_discrepancies") or [])],
        research_limitations=str(data.get("research_limitations") or ""),
        sources=sources,
        is_fallback=False,
        research_objectives=research_objectives,
        failed_objectives=failed_objectives,
        has_conflicting_evidence=bool(data.get("has_conflicting_evidence", False)),
        conflicting_evidence_notes=str(data.get("conflicting_evidence_notes") or ""),
    )


def _compute_founder_implied_valuation(pitch: Pitch) -> float | None:
    """A deterministic `ask_amount / (equity_offered_pct / 100)`
    calculation, computed in Python rather than trusted from the
    synthesis LLM's own arithmetic (Release 0.6.1 spec Part C §10/§12:
    "never fabricate missing financial values... every derived metric
    must be explicitly marked as derived"). `None` whenever either
    input is missing or the equity percentage is non-positive -- never
    guessed."""
    if pitch.ask_amount is None or pitch.equity_offered_pct is None:
        return None
    if pitch.equity_offered_pct <= 0:
        return None
    return pitch.ask_amount / (pitch.equity_offered_pct / 100)


def _claims_from_json(items: Any) -> list[ClaimAssessment]:
    if not isinstance(items, list):
        return []
    claims = []
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip().lower()
        if status not in CLAIM_STATUSES:
            status = "insufficient_evidence"
        try:
            claims.append(
                ClaimAssessment(
                    claim=str(item.get("claim", "")),
                    external_evidence=str(item.get("external_evidence", "")),
                    assessment=str(item.get("assessment", "")),
                    status=status,
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
