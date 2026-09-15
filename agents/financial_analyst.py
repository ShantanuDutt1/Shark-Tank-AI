"""
Financial Analyst for Shark Tank AI (Release 0.8).

Produces a structured, evidence-grounded `models.schemas
.FinancialAnalysisResult`: financial facts extracted with explicit
provenance, deterministic calculations computed in Python (never by
the LLM), scenario valuations with identified assumption sources, and
structured risk/upside factors. Not a Shark, not a `BaseAgent`
subclass (same reason `ModeratorAgent`/`MarketResearchAgent`/
`VerificationAgent` aren't -- its output is not an `Offer`).

Runs once per session, during `SessionPhase.ADVANCED_ANALYSIS`, after
every Shark's final deliberation (their offers are shown as context,
per Release 0.8 spec Part 19's "common analytical foundation") and
before Verification (so Verification can audit this analysis, per
spec Part 20 -- see `docs/architecture.md` -> Advanced Financial
Analysis for the full ordering rationale, which deviates from the
spec's own suggested diagram order for exactly this reason).

Two-step design, matching the separation this codebase already uses
for Market Reality Research: (1) one LLM call extracts financial facts
(with provenance), proposes scenario assumption *deltas* (never final
numbers), and identifies consistency/risk/upside factors; (2) Python
(`utils/financial_calculations.py`) performs every actual calculation
-- implied valuation, multiples, margins, growth, burn, runway,
dilution, and the scenario valuations themselves -- from the extracted
facts and `pitch.ask_amount`/`equity_offered_pct`/`valuation` (already
extracted by the Moderator in Release 0.6; not re-extracted here).
This bounds LLM usage to one call per session, per spec Part 38.

Every piece of content that did not originate from this module's own
prompt template -- the pitch, founder answers, market research, and
the Sharks' own generated rationale -- is wrapped as untrusted content
(`agents.prompt_safety.wrap_untrusted()`) before reaching the prompt,
exactly like `VerificationAgent`/`ConsensusEngine` (Release 0.7).

Like every other real agent in this codebase, `analyze()` *raises* a
specific `providers.exceptions.ProviderError` on failure rather than
degrading itself; `orchestrator/orchestrator.py` catches it and calls
`fallback_result()`.
"""

from __future__ import annotations

import json
from typing import Any

from agents.prompt_formatting import format_market_brief, format_offers, format_qa_transcript
from agents.prompt_safety import wrap_untrusted
from agents.research_planner import classify_business_model
from config.logging_config import get_logger
from models.enums import SpeakerRole
from models.schemas import (
    ASSUMPTION_SOURCES,
    CONSISTENCY_ASSESSMENTS,
    FINANCIAL_FACT_PROVENANCE,
    SCENARIO_LABELS,
    UPSIDE_BASIS,
    VERIFICATION_SEVERITIES,
    ConsistencyFinding,
    ConversationMessage,
    FinancialAnalysisResult,
    FinancialFact,
    MarketRealityBrief,
    Offer,
    Pitch,
    RiskFactor,
    ScenarioValuation,
    UpsideFactor,
    ValuationEstimate,
)
from prompts.loader import load_prompt
from providers.base_provider import BaseProvider
from providers.exceptions import ProviderNotConfiguredError, ProviderResponseError
from utils.financial_calculations import (
    apply_growth_delta,
    arr_multiple,
    dilution_pct,
    gross_margin_pct,
    implied_post_money_valuation,
    implied_pre_money_valuation,
    ltv_to_cac,
    monthly_burn,
    operating_margin_pct,
    revenue_growth_pct,
    revenue_multiple,
    runway_months,
)

logger = get_logger(__name__)

_MAX_TOKENS_FINANCIAL_ANALYSIS = 1600

#: Percentage-point tolerance below which a stated vs. computed figure
#: is still called "consistent" -- a small gap is normal rounding in a
#: founder's own quick mental math, not a red flag. Beyond
#: `_MATERIAL_INCONSISTENCY_THRESHOLD`, the gap is "materially
#: inconsistent" rather than merely "potentially" -- both thresholds
#: are deliberately coarse and documented here rather than left
#: implicit.
_INCONSISTENCY_TOLERANCE_PCT_POINTS = 5.0
_MATERIAL_INCONSISTENCY_THRESHOLD_PCT_POINTS = 15.0


class FinancialAnalyst:
    """Extracts financial facts and computes deterministic financial
    analysis for a pitch. Not a Shark; makes no investment decision."""

    def __init__(self, provider: BaseProvider | None = None) -> None:
        self.provider = provider

    def analyze(
        self,
        pitch: Pitch,
        market_brief: MarketRealityBrief | None,
        offers: dict[SpeakerRole, Offer],
        conversation: list[ConversationMessage],
    ) -> FinancialAnalysisResult:
        """Produce a real `FinancialAnalysisResult` for `pitch`.

        Raises `providers.exceptions.ProviderError` (or a subclass) if
        the provider is unconfigured, the request fails, or the
        response can't be parsed -- callers should catch that and use
        `fallback_result()` instead of letting the session stall.
        """
        if self.provider is None or not self.provider.is_configured:
            raise ProviderNotConfiguredError("FinancialAnalyst has no provider configured")

        business_model, _ = classify_business_model(pitch.description)
        prompt = self._build_prompt(pitch, market_brief, offers, conversation, business_model)
        messages = [{"role": "user", "content": prompt}]
        raw = self.provider.generate(messages, max_tokens=_MAX_TOKENS_FINANCIAL_ANALYSIS)
        data = _parse_json_object(raw)
        return _build_result(pitch, market_brief, business_model, data)

    def fallback_result(self, reason: str) -> FinancialAnalysisResult:
        """An honest "no financial analysis was possible" result, used
        when `analyze()` raises. Never fabricates a fact, calculation,
        or scenario."""
        return FinancialAnalysisResult(
            analysis_status="unavailable",
            research_limitations=(
                f"Financial analysis could not be completed ({reason}); no structured "
                "financial facts, calculations, or scenarios were produced for this session."
            ),
        )

    def _build_prompt(
        self,
        pitch: Pitch,
        market_brief: MarketRealityBrief | None,
        offers: dict[SpeakerRole, Offer],
        conversation: list[ConversationMessage],
        business_model: str,
    ) -> str:
        template = load_prompt("financial_analysis")
        rendered = template
        rendered = rendered.replace("{business_model}", business_model)
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
        return rendered


def _format_ask_summary(pitch: Pitch) -> str:
    parts = []
    if pitch.ask_amount is not None:
        parts.append(f"${pitch.ask_amount:,.0f}")
    if pitch.equity_offered_pct is not None:
        parts.append(f"for {pitch.equity_offered_pct:.1f}% equity")
    if pitch.valuation is not None:
        parts.append(f"(founder-stated valuation ${pitch.valuation:,.0f})")
    return " ".join(parts) if parts else "Not stated."


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
        raise ProviderResponseError(f"Could not parse financial analysis JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProviderResponseError("Financial analysis response JSON was not an object")
    return data


def _build_result(
    pitch: Pitch, market_brief: MarketRealityBrief | None, business_model: str, data: dict[str, Any]
) -> FinancialAnalysisResult:
    facts = _facts_from_json(data.get("financial_facts"))
    facts_by_metric = {f.metric: f.value for f in facts if f.value is not None}

    valuation_anchor = _valuation_anchor(pitch, facts_by_metric)
    current_revenue = facts_by_metric.get("current_revenue")

    computed_post_money = implied_post_money_valuation(pitch.ask_amount, pitch.equity_offered_pct)
    computed_pre_money = implied_pre_money_valuation(computed_post_money, pitch.ask_amount)
    computed_revenue_multiple = revenue_multiple(valuation_anchor, current_revenue)
    computed_arr_multiple = arr_multiple(valuation_anchor, facts_by_metric.get("arr"))
    computed_gross_margin = gross_margin_pct(current_revenue, facts_by_metric.get("cogs"))
    computed_operating_margin = operating_margin_pct(
        facts_by_metric.get("operating_income"), current_revenue
    )
    computed_growth = revenue_growth_pct(current_revenue, facts_by_metric.get("previous_period_revenue"))
    computed_burn = monthly_burn(
        facts_by_metric.get("cash_previous_period"),
        facts_by_metric.get("cash_on_hand"),
        facts_by_metric.get("burn_period_months"),
    )
    effective_burn = computed_burn if computed_burn is not None else facts_by_metric.get("stated_monthly_burn")
    computed_runway = runway_months(facts_by_metric.get("cash_on_hand"), effective_burn)
    computed_dilution = dilution_pct(pitch.ask_amount, computed_post_money)
    computed_ltv_cac = ltv_to_cac(facts_by_metric.get("ltv"), facts_by_metric.get("cac"))

    consistency_findings = _findings_from_json(data.get("consistency_findings"))
    consistency_findings.extend(
        _run_sanity_checks(facts_by_metric, computed_gross_margin, computed_burn, computed_runway)
    )

    scenarios = _build_scenarios(
        data.get("scenarios") or {}, market_brief, current_revenue, computed_revenue_multiple
    )

    return FinancialAnalysisResult(
        analysis_status="completed",
        business_model=business_model,
        financial_facts=facts,
        consistency_findings=consistency_findings,
        implied_post_money_valuation=computed_post_money,
        implied_pre_money_valuation=computed_pre_money,
        revenue_multiple=computed_revenue_multiple,
        arr_multiple=computed_arr_multiple,
        gross_margin_pct=computed_gross_margin,
        operating_margin_pct=computed_operating_margin,
        revenue_growth_pct=computed_growth,
        monthly_burn=effective_burn,
        runway_months=computed_runway,
        dilution_pct=computed_dilution,
        ltv_to_cac=computed_ltv_cac,
        scenarios=scenarios,
        risk_factors=_risk_factors_from_json(data.get("risk_factors")),
        upside_factors=_upside_factors_from_json(data.get("upside_factors")),
        business_quality_summary=str(data.get("business_quality_summary") or ""),
        financial_health_summary=str(data.get("financial_health_summary") or ""),
        research_limitations=str(data.get("research_limitations") or ""),
    )


def _valuation_anchor(pitch: Pitch, facts_by_metric: dict[str, float]) -> float | None:
    """The valuation figure used as the basis for revenue/ARR
    multiples and scenario computation: the deterministically implied
    post-money valuation when the deal terms support one, falling back
    to the founder's own stated valuation (Moderator-extracted,
    Release 0.6) when they don't -- never a value invented here."""
    post_money = implied_post_money_valuation(pitch.ask_amount, pitch.equity_offered_pct)
    if post_money is not None:
        return post_money
    return pitch.valuation


def _facts_from_json(items: Any) -> list[FinancialFact]:
    if not isinstance(items, list):
        return []
    facts: list[FinancialFact] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        metric = str(item.get("metric") or "").strip()
        if not metric:
            continue
        provenance = str(item.get("provenance") or "").strip().lower()
        if provenance not in FINANCIAL_FACT_PROVENANCE:
            provenance = "missing"
        value = _optional_float(item.get("value"))
        if provenance == "missing":
            value = None
        try:
            facts.append(
                FinancialFact(
                    metric=metric,
                    value=value,
                    provenance=provenance,
                    note=str(item.get("note") or ""),
                )
            )
        except (TypeError, ValueError):
            continue
    return facts


def _findings_from_json(items: Any) -> list[ConsistencyFinding]:
    if not isinstance(items, list):
        return []
    findings: list[ConsistencyFinding] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        assessment = str(item.get("assessment") or "").strip().lower()
        if assessment not in CONSISTENCY_ASSESSMENTS:
            assessment = "insufficient_information"
        try:
            findings.append(
                ConsistencyFinding(
                    subject=str(item.get("subject") or ""),
                    assessment=assessment,
                    explanation=str(item.get("explanation") or ""),
                )
            )
        except (TypeError, ValueError):
            continue
    return findings


def _run_sanity_checks(
    facts_by_metric: dict[str, float],
    computed_gross_margin: float | None,
    computed_burn: float | None,
    computed_runway: float | None,
) -> list[ConsistencyFinding]:
    """Deterministic consistency checks (Release 0.8 spec Part 8),
    comparing a founder-stated figure against the same figure computed
    independently from other stated inputs. Never raises; a check that
    can't run (a required input missing) is simply skipped -- absence
    of a check is not itself a finding."""
    findings: list[ConsistencyFinding] = []

    stated_margin = facts_by_metric.get("stated_gross_margin_pct")
    if stated_margin is not None and computed_gross_margin is not None:
        findings.append(
            _compare_stated_vs_computed("gross margin", stated_margin, computed_gross_margin, "pp")
        )

    stated_burn = facts_by_metric.get("stated_monthly_burn")
    if stated_burn is not None and computed_burn is not None and stated_burn > 0:
        relative_gap_pct = abs(stated_burn - computed_burn) / stated_burn * 100
        findings.append(
            _compare_stated_vs_computed("monthly burn", stated_burn, computed_burn, "%", relative_gap_pct)
        )

    stated_runway = facts_by_metric.get("stated_runway_months")
    if stated_runway is not None and computed_runway is not None and stated_runway > 0:
        relative_gap_pct = abs(stated_runway - computed_runway) / stated_runway * 100
        findings.append(
            _compare_stated_vs_computed("runway", stated_runway, computed_runway, "%", relative_gap_pct)
        )

    for metric, label in (
        ("stated_gross_margin_pct", "gross margin"),
        ("churn_pct", "churn"),
        ("retention_pct", "retention"),
        ("customer_concentration_pct", "customer concentration"),
    ):
        value = facts_by_metric.get(metric)
        if value is not None and (value < 0 or value > 100):
            findings.append(
                ConsistencyFinding(
                    subject=label,
                    assessment="materially_inconsistent",
                    explanation=f"Stated {label} of {value}% is outside a valid 0-100 range.",
                )
            )

    for metric, label in (
        ("current_revenue", "current revenue"),
        ("cogs", "COGS"),
        ("cash_on_hand", "cash on hand"),
        ("customer_count", "customer count"),
    ):
        value = facts_by_metric.get(metric)
        if value is not None and value < 0:
            findings.append(
                ConsistencyFinding(
                    subject=label,
                    assessment="materially_inconsistent",
                    explanation=f"Stated {label} of {value:,.0f} is negative, which is not logically valid.",
                )
            )

    return findings


def _compare_stated_vs_computed(
    label: str, stated: float, computed: float, unit: str, precomputed_gap_pct: float | None = None
) -> ConsistencyFinding:
    gap = precomputed_gap_pct if precomputed_gap_pct is not None else abs(stated - computed)
    if gap <= _INCONSISTENCY_TOLERANCE_PCT_POINTS:
        assessment = "consistent"
    elif gap <= _MATERIAL_INCONSISTENCY_THRESHOLD_PCT_POINTS:
        assessment = "potentially_inconsistent"
    else:
        assessment = "materially_inconsistent"
    return ConsistencyFinding(
        subject=label,
        assessment=assessment,
        explanation=(
            f"Founder-stated {label} ({stated:,.1f}{unit}) vs. independently computed "
            f"{label} ({computed:,.1f}{unit}) from other stated figures."
        ),
    )


def _risk_factors_from_json(items: Any) -> list[RiskFactor]:
    if not isinstance(items, list):
        return []
    factors: list[RiskFactor] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "").strip().lower()
        if severity not in VERIFICATION_SEVERITIES:
            severity = "low"
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        try:
            factors.append(
                RiskFactor(
                    category=str(item.get("category") or ""),
                    description=str(item.get("description") or ""),
                    severity=severity,
                    evidence=str(item.get("evidence") or ""),
                    confidence=confidence,
                    mitigable=bool(item.get("mitigable", True)),
                    material=bool(item.get("material", True)),
                )
            )
        except (TypeError, ValueError):
            continue
    return factors


def _upside_factors_from_json(items: Any) -> list[UpsideFactor]:
    if not isinstance(items, list):
        return []
    factors: list[UpsideFactor] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        basis = str(item.get("basis") or "").strip().lower()
        if basis not in UPSIDE_BASIS:
            basis = "hypothesis"
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        try:
            factors.append(
                UpsideFactor(
                    category=str(item.get("category") or ""),
                    description=str(item.get("description") or ""),
                    basis=basis,
                    evidence=str(item.get("evidence") or ""),
                    confidence=confidence,
                )
            )
        except (TypeError, ValueError):
            continue
    return factors


def _build_scenarios(
    raw_scenarios: dict[str, Any],
    market_brief: MarketRealityBrief | None,
    current_revenue: float | None,
    base_multiple: float | None,
) -> list[ScenarioValuation]:
    """Builds all three scenarios. `base` reuses the existing
    Market Reality-informed valuation range (Release 0.6) as its
    anchor when available -- never recomputed. `downside`/`upside`
    apply the LLM-proposed revenue growth delta (a plain percentage,
    never a final valuation) to `current_revenue` via
    `utils.financial_calculations.apply_growth_delta()`, then multiply
    by the same `base_multiple` already computed for `revenue_multiple`
    above -- both steps are Python arithmetic, never the LLM's own
    calculation (spec Part 16)."""
    scenarios: list[ScenarioValuation] = []

    base_valuation = ValuationEstimate(confidence="insufficient_evidence")
    if market_brief is not None and not market_brief.is_fallback:
        if market_brief.valuation.confidence != "insufficient_evidence" and market_brief.valuation.low is not None:
            base_valuation = market_brief.valuation
    scenarios.append(
        ScenarioValuation(
            scenario="base",
            valuation=base_valuation,
            assumption_basis="market_evidence" if base_valuation.low is not None else "insufficient_evidence",
            assumptions="Market-informed valuation range from Market Reality Research."
            if base_valuation.low is not None
            else "",
        )
    )

    for label in ("downside", "upside"):
        raw = raw_scenarios.get(label) if isinstance(raw_scenarios, dict) else None
        raw = raw if isinstance(raw, dict) else {}
        assumption_basis = str(raw.get("assumption_basis") or "").strip().lower()
        if assumption_basis not in ASSUMPTION_SOURCES:
            assumption_basis = "insufficient_evidence"
        assumptions_text = str(raw.get("assumptions") or "")
        delta_pct = _optional_float(raw.get("revenue_growth_delta_pct"))

        scenario_revenue = apply_growth_delta(current_revenue, delta_pct)
        if scenario_revenue is not None and base_multiple is not None:
            point = scenario_revenue * base_multiple
            valuation = ValuationEstimate(
                methodology=f"Revenue multiple applied to {label}-case revenue assumption.",
                low=point,
                high=point,
                assumptions=assumptions_text,
                confidence="low",
            )
        else:
            valuation = ValuationEstimate(
                confidence="insufficient_evidence", assumptions=assumptions_text
            )
        scenarios.append(
            ScenarioValuation(
                scenario=label,
                valuation=valuation,
                assumption_basis=assumption_basis,
                assumptions=assumptions_text,
            )
        )

    # Preserve the fixed downside/base/upside order regardless of dict
    # iteration order above.
    order = {label: i for i, label in enumerate(SCENARIO_LABELS)}
    scenarios.sort(key=lambda s: order.get(s.scenario, len(order)))
    return scenarios


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
