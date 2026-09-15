"""
Consensus Engine for Shark Tank AI (Release 0.7).

Reconciles the three Sharks' independent final evaluations, their
deliberation, the Market Reality Brief, and the Verification Agent's
audit findings into one formal investment recommendation. Lives in
`orchestrator/`, not `agents/` -- per Release 0.7 spec Part 11 ("an
equivalent location if the existing architecture strongly suggests
otherwise") and `docs/folder_structure.md`'s own long-standing
"Future expansion" note under `orchestrator/`, which already
anticipated "a real Consensus Engine aggregation step... plugged into
`_run_deliberation_pipeline()`'s existing placeholder extension
points." It is deliberately NOT another LLM persona pretending to be a
fourth Shark: it has no investment philosophy of its own and never
independently evaluates the pitch -- its only job is reconciling
already-produced, structured committee output.

Explicitly NOT a majority vote (Release 0.7 spec Part 12): a single
Shark's well-supported concern, or the Verification Agent finding a
material problem with the majority's reasoning, can outweigh a 2-1
split. Deterministic numeric facts (per-Shark implied valuations, the
interested/declined tally) are computed in Python (`_compute_facts()`)
and handed to the LLM as given facts, per spec Part 16's "use the LLM
for interpretation/reconciliation, not arithmetic that can safely be
deterministic" -- the LLM is never asked to compute these numbers
itself.

Like every other real agent/engine in this codebase, `reconcile()`
*raises* a specific `providers.exceptions.ProviderError` on failure
rather than degrading itself; `orchestrator/orchestrator.py` catches
it and calls `fallback_result()`.
"""

from __future__ import annotations

import json
from typing import Any

from agents.prompt_formatting import (
    format_financial_analysis,
    format_market_brief,
    format_offers,
    format_qa_transcript,
    format_verification,
)
from agents.prompt_safety import wrap_untrusted
from config.logging_config import get_logger
from models.enums import SpeakerRole
from models.schemas import (
    CONSENSUS_RECOMMENDATIONS,
    QUALITY_RATINGS,
    ConsensusResult,
    ConversationMessage,
    FinancialAnalysisResult,
    MarketRealityBrief,
    NumericRange,
    Offer,
    Pitch,
    ValuationEstimate,
    VerificationResult,
)
from prompts.loader import load_prompt
from providers.base_provider import BaseProvider
from providers.exceptions import ProviderNotConfiguredError, ProviderResponseError

logger = get_logger(__name__)

_MAX_TOKENS_CONSENSUS = 1200

#: Committee order used everywhere else in this codebase
#: (`orchestrator/orchestrator.py`'s `_sharks` list,
#: `agents.prompt_formatting.format_offers()`).
_SHARK_ORDER = (SpeakerRole.CONSERVATIVE_VC, SpeakerRole.GROWTH_VC, SpeakerRole.BALANCED_VC)


class ConsensusEngine:
    """Reconciles Shark positions and Verification findings into one
    formal recommendation. Not a `BaseAgent` -- see module docstring."""

    def __init__(self, provider: BaseProvider | None = None) -> None:
        self.provider = provider

    def reconcile(
        self,
        pitch: Pitch,
        market_brief: MarketRealityBrief | None,
        offers: dict[SpeakerRole, Offer],
        verification: VerificationResult,
        conversation: list[ConversationMessage],
        financial_analysis: FinancialAnalysisResult | None = None,
    ) -> ConsensusResult:
        """Produce a real `ConsensusResult` from `offers`, `verification`,
        `market_brief`, `financial_analysis` (Release 0.8), and the
        session's conversation.

        Raises `providers.exceptions.ProviderError` (or a subclass) if
        the provider is unconfigured, the request fails, or the
        response can't be parsed -- callers should catch that and use
        `fallback_result()` instead of letting the session stall.
        """
        if self.provider is None or not self.provider.is_configured:
            raise ProviderNotConfiguredError("ConsensusEngine has no provider configured")

        prompt = self._build_prompt(
            pitch, market_brief, offers, verification, conversation, financial_analysis
        )
        messages = [{"role": "user", "content": prompt}]
        raw = self.provider.generate(messages, max_tokens=_MAX_TOKENS_CONSENSUS)
        data = _parse_json_object(raw)
        return _result_from_json(data)

    def fallback_result(self, reason: str) -> ConsensusResult:
        """An honest "no formal recommendation was reached" result,
        used when `reconcile()` raises. `recommendation="unavailable"`
        is reserved for exactly this path -- never confused with a
        genuine `"insufficient_evidence"` conclusion the engine
        actually reached (spec Part 14)."""
        return ConsensusResult(
            recommendation="unavailable",
            confidence=0.0,
            evidence_limitations=(
                f"Consensus could not be reached ({reason}); no formal committee "
                "recommendation was produced for this session."
            ),
        )

    def _build_prompt(
        self,
        pitch: Pitch,
        market_brief: MarketRealityBrief | None,
        offers: dict[SpeakerRole, Offer],
        verification: VerificationResult,
        conversation: list[ConversationMessage],
        financial_analysis: FinancialAnalysisResult | None,
    ) -> str:
        template = load_prompt("consensus")
        rendered = template
        rendered = rendered.replace("{company_name}", pitch.company_name)
        rendered = rendered.replace("{ask_summary}", _format_ask_summary(pitch))
        rendered = rendered.replace(
            "{wrapped_pitch}", wrap_untrusted(pitch.description, label="founder_pitch")
        )
        rendered = rendered.replace(
            "{wrapped_transcript}",
            wrap_untrusted(format_qa_transcript(conversation), label="conversation_transcript"),
        )
        rendered = rendered.replace(
            "{wrapped_market_brief}",
            wrap_untrusted(format_market_brief(market_brief), label="market_reality_brief"),
        )
        rendered = rendered.replace(
            "{wrapped_offers}",
            wrap_untrusted(format_offers(offers), label="shark_evaluations"),
        )
        rendered = rendered.replace(
            "{wrapped_verification}",
            wrap_untrusted(format_verification(verification), label="verification_findings"),
        )
        rendered = rendered.replace(
            "{wrapped_financial_analysis}",
            wrap_untrusted(
                format_financial_analysis(financial_analysis), label="financial_analysis"
            ),
        )
        rendered = rendered.replace("{computed_facts}", _compute_facts(offers))
        return rendered


def _format_ask_summary(pitch: Pitch) -> str:
    parts = []
    if pitch.ask_amount is not None:
        parts.append(f"${pitch.ask_amount:,.0f}")
    if pitch.equity_offered_pct is not None:
        parts.append(f"for {pitch.equity_offered_pct:.1f}% equity")
    if pitch.valuation is not None:
        parts.append(f"(implied valuation ${pitch.valuation:,.0f})")
    return " ".join(parts) if parts else "Not stated."


def _compute_facts(offers: dict[SpeakerRole, Offer]) -> str:
    """Deterministic Python arithmetic over `offers`, rendered as plain
    text for the LLM to use as given facts -- never asked to recompute
    itself (spec Part 16)."""
    evaluated = [offers[role] for role in _SHARK_ORDER if role in offers]
    available = [o for o in evaluated if o.evaluation_available]
    unavailable_count = len(evaluated) - len(available)
    interested = [o for o in available if o.interested]

    lines = [
        f"{len(available)} of {len(evaluated)} Sharks completed a real evaluation "
        f"({unavailable_count} unavailable due to technical failure).",
        f"{len(interested)} of {len(available)} evaluated Sharks are interested.",
    ]
    for offer in interested:
        if offer.amount is not None and offer.equity_pct and offer.equity_pct > 0:
            implied_valuation = offer.amount / (offer.equity_pct / 100)
            lines.append(
                f"{offer.shark_id}: ${offer.amount:,.0f} for {offer.equity_pct:.1f}% equity "
                f"(implied valuation ${implied_valuation:,.0f})."
            )
        elif offer.amount is not None and offer.equity_pct is not None:
            lines.append(
                f"{offer.shark_id}: ${offer.amount:,.0f} for {offer.equity_pct:.1f}% equity "
                "(implied valuation not computable)."
            )
    return "\n".join(lines)


def _parse_json_object(raw: str) -> dict[str, Any]:
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
        raise ProviderResponseError(f"Could not parse consensus JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProviderResponseError("Consensus response JSON was not an object")
    return data


def _result_from_json(data: dict[str, Any]) -> ConsensusResult:
    recommendation = str(data.get("recommendation") or "").strip().lower()
    if recommendation not in CONSENSUS_RECOMMENDATIONS or recommendation == "unavailable":
        # "unavailable" is reserved for fallback_result() -- a real LLM
        # response claiming it is either a parsing problem or a model
        # not following instructions; treat it as unparseable rather
        # than letting the model claim its own unavailability.
        raise ProviderResponseError(f"Consensus JSON had an invalid recommendation: {recommendation!r}")

    try:
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0

    return ConsensusResult(
        recommendation=recommendation,
        confidence=confidence,
        investment_thesis=str(data.get("investment_thesis") or ""),
        key_strengths=[str(s) for s in (data.get("key_strengths") or [])],
        key_risks=[str(s) for s in (data.get("key_risks") or [])],
        material_disagreements=[str(s) for s in (data.get("material_disagreements") or [])],
        verification_summary=str(data.get("verification_summary") or ""),
        valuation_assessment=str(data.get("valuation_assessment") or ""),
        recommended_valuation_range=_valuation_from_json(data.get("recommended_valuation_range")),
        recommended_investment_range=_range_from_json(
            data.get("recommended_investment_range"), validator=_validate_non_negative
        ),
        recommended_equity_range=_range_from_json(
            data.get("recommended_equity_range"), validator=_validate_percentage
        ),
        conditions=[str(s) for s in (data.get("conditions") or [])],
        decision_rationale=str(data.get("decision_rationale") or ""),
        evidence_limitations=str(data.get("evidence_limitations") or ""),
        business_quality=_validate_quality_rating(data.get("business_quality")),
        deal_quality=_validate_quality_rating(data.get("deal_quality")),
        financial_health=_validate_quality_rating(data.get("financial_health")),
        growth_profile=str(data.get("growth_profile") or ""),
        risk_profile=str(data.get("risk_profile") or ""),
        scenario_summary=str(data.get("scenario_summary") or ""),
    )


def _validate_quality_rating(value: Any) -> str:
    rating = str(value or "").strip().lower()
    return rating if rating in QUALITY_RATINGS else "insufficient_evidence"


def _valuation_from_json(data: Any) -> ValuationEstimate:
    data = data or {}
    if not isinstance(data, dict):
        data = {}
    return ValuationEstimate(
        methodology=str(data.get("methodology") or ""),
        low=_validate_non_negative(_optional_float(data.get("low"))),
        high=_validate_non_negative(_optional_float(data.get("high"))),
        assumptions=str(data.get("assumptions") or ""),
        confidence=str(data.get("confidence") or "insufficient_evidence"),
    )


def _range_from_json(data: Any, *, validator: Any) -> NumericRange:
    data = data or {}
    if not isinstance(data, dict):
        data = {}
    return NumericRange(
        low=validator(_optional_float(data.get("low"))),
        high=validator(_optional_float(data.get("high"))),
        confidence=str(data.get("confidence") or "insufficient_evidence"),
    )


def _validate_non_negative(value: float | None) -> float | None:
    """Reject a negative dollar amount rather than silently passing it
    through (Release 0.7 spec Part 28: 'numeric overflow/invalid
    financial values' is an explicit security-review item), mirroring
    `agents/shark_agent.py::_validate_amount()`."""
    if value is None:
        return None
    if value < 0:
        raise ProviderResponseError(f"Consensus range value cannot be negative: {value!r}")
    return value


def _validate_percentage(value: float | None) -> float | None:
    """Reject an equity percentage outside `[0, 100]`, mirroring
    `agents/shark_agent.py::_validate_equity_pct()`."""
    if value is None:
        return None
    if value < 0 or value > 100:
        raise ProviderResponseError(f"Consensus equity range value out of [0, 100]: {value!r}")
    return value


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
