"""
Founder Feedback Agent for Shark Tank AI (Release 0.9).

Produces a `models.schemas.FounderFeedbackReport`: a critical,
evidence-grounded synthesis of the *entire* simulation -- not another
Shark opinion, not a second Consensus Engine, and not a generic
startup-advice generator. It answers a question none of the existing
components answer: "what should the founder improve before pitching
real investors?" (Release 0.9 spec Part 3), by cross-referencing the
proposal, Moderator validation, Market Reality Research, the full
committee conversation, each Shark's offer, any negotiation outcomes,
Verification's audit, Consensus's recommendation, and the Advanced
Financial Analysis -- specifically so it can surface a discrepancy
none of the individual Sharks caught (spec Part 11's own worked
example: a founder market-size claim that Verification flagged as
unsupported but every Shark otherwise accepted).

Not a `BaseAgent` subclass, for the same reason `ModeratorAgent`/
`MarketResearchAgent`/`VerificationAgent`/`FinancialAnalyst` aren't:
its output is not an `Offer`, and it never makes or influences an
investment decision -- it runs strictly after the final outcome is
already determined (`SharkTankOrchestrator._complete_session()`), so
it cannot affect the Sharks, Verification, or Consensus even in
principle.

Every simulation artifact reaching this agent's prompt --the proposal,
founder answers, negotiation counters, retrieved web content (via the
Market Reality Brief), and every other agent's own generated text -- is
wrapped as untrusted content (`agents.prompt_safety.wrap_untrusted()`),
exactly like every other real agent in this codebase.

Like every other real agent, `generate()` *raises* a specific
`providers.exceptions.ProviderError` on failure rather than degrading
itself; `orchestrator/orchestrator.py` catches it and calls
`fallback_result()`.
"""

from __future__ import annotations

import json
from typing import Any

from agents.prompt_formatting import (
    format_consensus,
    format_financial_analysis,
    format_market_brief,
    format_negotiation_responses,
    format_offers,
    format_qa_transcript,
    format_validation_result,
    format_verification,
)
from agents.prompt_safety import wrap_untrusted
from agents.research_planner import classify_business_model
from config.logging_config import get_logger
from models.enums import SpeakerRole
from models.schemas import (
    ACTION_PRIORITIES,
    COMPANY_STAGES,
    INVESTOR_READINESS_ASSESSMENTS,
    ActionItem,
    ConsensusResult,
    ConversationMessage,
    FinancialAnalysisResult,
    FounderFeedbackReport,
    InvestorReadinessDimension,
    MarketRealityBrief,
    NegotiationResponse,
    Offer,
    Pitch,
    ProposalValidationResult,
    ReportEvidenceRef,
    VerificationResult,
)
from prompts.loader import load_prompt
from providers.base_provider import BaseProvider
from providers.exceptions import ProviderNotConfiguredError, ProviderResponseError

logger = get_logger(__name__)

_MAX_TOKENS_FOUNDER_FEEDBACK = 2000


class FounderFeedbackAgent:
    """Synthesizes the full simulation into a critical, evidence-grounded
    founder feedback report. Not a Shark; makes no investment decision."""

    def __init__(self, provider: BaseProvider | None = None) -> None:
        self.provider = provider

    def generate(
        self,
        session_id: str,
        pitch: Pitch,
        validation_result: ProposalValidationResult | None,
        market_brief: MarketRealityBrief | None,
        conversation: list[ConversationMessage],
        final_offers: dict[SpeakerRole, Offer],
        negotiation_responses: dict[SpeakerRole, NegotiationResponse],
        verification: VerificationResult | None,
        consensus: ConsensusResult | None,
        financial_analysis: FinancialAnalysisResult | None,
    ) -> FounderFeedbackReport:
        """Produce a real `FounderFeedbackReport` synthesizing every
        input above.

        Raises `providers.exceptions.ProviderError` (or a subclass) if
        the provider is unconfigured, the request fails, or the
        response can't be parsed -- callers should catch that and use
        `fallback_result()` instead of stalling session completion.
        """
        if self.provider is None or not self.provider.is_configured:
            raise ProviderNotConfiguredError("FounderFeedbackAgent has no provider configured")

        business_model = (financial_analysis.business_model if financial_analysis else "") or (
            classify_business_model(pitch.description)[0]
        )
        prompt = self._build_prompt(
            pitch,
            validation_result,
            market_brief,
            conversation,
            final_offers,
            negotiation_responses,
            verification,
            consensus,
            financial_analysis,
            business_model,
        )
        messages = [{"role": "user", "content": prompt}]
        raw = self.provider.generate(messages, max_tokens=_MAX_TOKENS_FOUNDER_FEEDBACK)
        data = _parse_json_object(raw)
        return _build_report(session_id, pitch, business_model, data)

    def fallback_result(self, session_id: str, pitch: Pitch, reason: str) -> FounderFeedbackReport:
        """An honest "no report was possible" result, used when
        `generate()` raises. Never fabricates feedback -- an empty
        report is preferable to invented findings (spec Part 22: a
        report-generation failure must never be silently substituted
        with fabricated feedback, or confused with a genuine outcome
        like Shark rejection)."""
        return FounderFeedbackReport(
            report_status="unavailable",
            session_id=session_id,
            pitch_id=pitch.id,
            company_name=pitch.company_name,
            limitations=(
                f"The founder feedback report could not be generated ({reason}); no "
                "synthesis of the simulation was produced for this session."
            ),
        )

    def _build_prompt(
        self,
        pitch: Pitch,
        validation_result: ProposalValidationResult | None,
        market_brief: MarketRealityBrief | None,
        conversation: list[ConversationMessage],
        final_offers: dict[SpeakerRole, Offer],
        negotiation_responses: dict[SpeakerRole, NegotiationResponse],
        verification: VerificationResult | None,
        consensus: ConsensusResult | None,
        financial_analysis: FinancialAnalysisResult | None,
        business_model: str,
    ) -> str:
        template = load_prompt("founder_feedback")
        rendered = template
        rendered = rendered.replace("{business_model}", business_model)
        rendered = rendered.replace("{company_name}", pitch.company_name)
        rendered = rendered.replace("{ask_summary}", _format_ask_summary(pitch))
        rendered = rendered.replace(
            "{wrapped_pitch}", wrap_untrusted(pitch.description, label="founder_pitch")
        )
        rendered = rendered.replace(
            "{wrapped_validation}",
            wrap_untrusted(format_validation_result(validation_result), label="validation_result"),
        )
        rendered = rendered.replace(
            "{wrapped_market_brief}",
            wrap_untrusted(format_market_brief(market_brief), label="market_reality_brief"),
        )
        rendered = rendered.replace(
            "{wrapped_transcript}",
            wrap_untrusted(format_qa_transcript(conversation), label="conversation_transcript"),
        )
        rendered = rendered.replace(
            "{wrapped_offers}",
            wrap_untrusted(format_offers(final_offers), label="shark_evaluations"),
        )
        rendered = rendered.replace(
            "{wrapped_negotiations}",
            wrap_untrusted(
                format_negotiation_responses(negotiation_responses), label="negotiation_outcomes"
            ),
        )
        rendered = rendered.replace(
            "{wrapped_verification}",
            wrap_untrusted(format_verification(verification), label="verification_findings"),
        )
        rendered = rendered.replace(
            "{wrapped_consensus}",
            wrap_untrusted(format_consensus(consensus), label="consensus_result"),
        )
        rendered = rendered.replace(
            "{wrapped_financial_analysis}",
            wrap_untrusted(
                format_financial_analysis(financial_analysis), label="financial_analysis"
            ),
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
        raise ProviderResponseError(f"Could not parse founder feedback JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProviderResponseError("Founder feedback response JSON was not an object")
    return data


def _build_report(
    session_id: str, pitch: Pitch, business_model: str, data: dict[str, Any]
) -> FounderFeedbackReport:
    stage = str(data.get("stage") or "").strip().lower()
    if stage not in COMPANY_STAGES:
        stage = "unclear"

    return FounderFeedbackReport(
        report_status="completed",
        session_id=session_id,
        pitch_id=pitch.id,
        company_name=pitch.company_name,
        stage=stage,
        stage_rationale=str(data.get("stage_rationale") or ""),
        business_model=business_model,
        executive_summary=str(data.get("executive_summary") or ""),
        strengths=[str(s) for s in (data.get("strengths") or [])],
        needs_work=[str(s) for s in (data.get("needs_work") or [])],
        critical_issues=[str(s) for s in (data.get("critical_issues") or [])],
        investor_readiness=_readiness_from_json(data.get("investor_readiness")),
        valuation_feedback=str(data.get("valuation_feedback") or ""),
        financial_feedback=str(data.get("financial_feedback") or ""),
        action_plan=_action_plan_from_json(data.get("action_plan")),
        evidence_references=_evidence_refs_from_json(data.get("evidence_references")),
        limitations=str(data.get("limitations") or ""),
    )


def _readiness_from_json(items: Any) -> list[InvestorReadinessDimension]:
    if not isinstance(items, list):
        return []
    dimensions: list[InvestorReadinessDimension] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        assessment = str(item.get("assessment") or "").strip().lower()
        if assessment not in INVESTOR_READINESS_ASSESSMENTS:
            assessment = "insufficient_evidence"
        dimension = str(item.get("dimension") or "").strip()
        if not dimension:
            continue
        try:
            dimensions.append(
                InvestorReadinessDimension(
                    dimension=dimension,
                    assessment=assessment,
                    rationale=str(item.get("rationale") or ""),
                )
            )
        except (TypeError, ValueError):
            continue
    return dimensions


def _action_plan_from_json(items: Any) -> list[ActionItem]:
    if not isinstance(items, list):
        return []
    plan: list[ActionItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        priority = str(item.get("priority") or "").strip().lower()
        if priority not in ACTION_PRIORITIES:
            priority = "later"
        problem = str(item.get("problem") or "").strip()
        action = str(item.get("action") or "").strip()
        if not problem or not action:
            continue
        try:
            plan.append(
                ActionItem(
                    priority=priority,
                    problem=problem,
                    why_it_matters=str(item.get("why_it_matters") or ""),
                    action=action,
                    evidence_needed=str(item.get("evidence_needed") or ""),
                )
            )
        except (TypeError, ValueError):
            continue
    return plan


def _evidence_refs_from_json(items: Any) -> list[ReportEvidenceRef]:
    if not isinstance(items, list):
        return []
    refs: list[ReportEvidenceRef] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip()
        if not subject:
            continue
        try:
            refs.append(
                ReportEvidenceRef(
                    subject=subject,
                    source=str(item.get("source") or ""),
                    detail=str(item.get("detail") or ""),
                )
            )
        except (TypeError, ValueError):
            continue
    return refs
