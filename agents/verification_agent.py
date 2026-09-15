"""
Verification Agent for Shark Tank AI (Release 0.7).

Independently audits whether the three Sharks' final reasoning is
actually supported by the proposal, the founder's answers, and the
Market Reality Brief -- it does NOT evaluate the pitch itself and
never produces an `Offer` or any investment recommendation (that is
the Consensus Engine's job, `orchestrator/consensus_engine.py`, which
runs strictly after this agent -- Release 0.7 spec Part 15: "Verification
asks whether claims are supported; Consensus asks what the committee
should conclude"). Not a `BaseAgent` subclass, for the same reason
`ModeratorAgent`/`MarketResearchAgent` aren't: `BaseAgent`'s one
abstract method, `evaluate_pitch() -> Offer`, has no meaningful
implementation for a component that produces a `VerificationResult`,
not an investment position.

Runs once per session, during `SessionPhase.VERIFICATION`, after every
Shark's final deliberation is in and before the Consensus Engine runs
(`docs/state_machines.md`). Every Shark's offer, the pitch, the
founder's Question Round answers, and the Market Reality Brief are all
treated as untrusted content in the audit prompt
(`agents.prompt_safety.wrap_untrusted()`) -- a founder's proposal, a
retrieved web page, *or a Shark's own generated rationale* could
contain text that reads like an instruction, and none of them should
be able to change this agent's behavior (Release 0.7 spec Part 17).

Like every other real agent in this codebase, `verify()` *raises* a
specific `providers.exceptions.ProviderError` on failure rather than
degrading itself; `orchestrator/orchestrator.py` catches it and calls
`fallback_result()`.
"""

from __future__ import annotations

import json
from typing import Any

from agents.prompt_formatting import (
    format_financial_analysis,
    format_market_brief,
    format_offers,
    format_qa_transcript,
)
from agents.prompt_safety import wrap_untrusted
from config.logging_config import get_logger
from models.schemas import (
    CLAIM_STATUSES,
    VERIFICATION_SEVERITIES,
    ConversationMessage,
    FinancialAnalysisResult,
    MarketRealityBrief,
    Offer,
    Pitch,
    VerificationFinding,
    VerificationResult,
)
from models.enums import SpeakerRole
from prompts.loader import load_prompt
from providers.base_provider import BaseProvider
from providers.exceptions import ProviderNotConfiguredError, ProviderResponseError

logger = get_logger(__name__)

_MAX_TOKENS_VERIFICATION = 1400

#: The exact `subject` keys `shark_specific_findings` is organized
#: under -- the fixed committee order, matching every other per-Shark
#: structure in this codebase (`orchestrator/orchestrator.py`'s
#: `_sharks` list, `agents.prompt_formatting.format_offers()`).
_SHARK_SUBJECT_KEYS = ("conservative_vc", "growth_vc", "balanced_vc")


class VerificationAgent:
    """Audits the committee's final reasoning for evidentiary support."""

    def __init__(self, provider: BaseProvider | None = None) -> None:
        self.provider = provider

    def verify(
        self,
        pitch: Pitch,
        market_brief: MarketRealityBrief | None,
        offers: dict[SpeakerRole, Offer],
        conversation: list[ConversationMessage],
        financial_analysis: FinancialAnalysisResult | None = None,
    ) -> VerificationResult:
        """Produce a real `VerificationResult` auditing `offers` against
        `pitch`, `conversation`, `market_brief`, and (Release 0.8)
        `financial_analysis`.

        `financial_analysis`, when given, extends the audit to also
        cover the Advanced Financial Analysis step's own extracted
        facts, deterministic calculations, and scenario assumptions --
        findings land in the existing `financial_issues`/
        `valuation_issues` lists, per spec Part 20 ("extend verification
        where necessary... do not duplicate the entire Verification
        system"); no new `VerificationResult` fields were needed.

        Raises `providers.exceptions.ProviderError` (or a subclass) if
        the provider is unconfigured, the request fails, or the
        response can't be parsed -- callers should catch that and use
        `fallback_result()` instead of letting the session stall.
        """
        if self.provider is None or not self.provider.is_configured:
            raise ProviderNotConfiguredError("VerificationAgent has no provider configured")

        prompt = self._build_prompt(pitch, market_brief, offers, conversation, financial_analysis)
        messages = [{"role": "user", "content": prompt}]
        raw = self.provider.generate(messages, max_tokens=_MAX_TOKENS_VERIFICATION)
        data = _parse_json_object(raw)
        return _result_from_json(data)

    def fallback_result(self, reason: str) -> VerificationResult:
        """An honest "verification could not be completed" result, used
        when `verify()` raises. Never fabricates a finding -- an empty
        result is preferable to an invented audit (spec Part 24:
        "Verification unavailable" must be distinct from a completed
        verification that found nothing wrong)."""
        return VerificationResult(
            verification_status="unavailable",
            overall_confidence=0.0,
            research_limitations=(
                f"Verification could not be completed ({reason}); the committee's reasoning "
                "was not independently audited for this session."
            ),
        )

    def _build_prompt(
        self,
        pitch: Pitch,
        market_brief: MarketRealityBrief | None,
        offers: dict[SpeakerRole, Offer],
        conversation: list[ConversationMessage],
        financial_analysis: FinancialAnalysisResult | None,
    ) -> str:
        template = load_prompt("verification")
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
        parts.append(f"(implied valuation ${pitch.valuation:,.0f})")
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
        raise ProviderResponseError(f"Could not parse verification JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProviderResponseError("Verification response JSON was not an object")
    return data


def _result_from_json(data: dict[str, Any]) -> VerificationResult:
    confidence = data.get("overall_confidence")
    try:
        overall_confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None else 0.0
    except (TypeError, ValueError):
        overall_confidence = 0.0

    shark_findings_raw = data.get("shark_specific_findings") or {}
    shark_specific_findings: dict[str, list[VerificationFinding]] = {}
    if isinstance(shark_findings_raw, dict):
        for key in _SHARK_SUBJECT_KEYS:
            shark_specific_findings[key] = _findings_from_json(shark_findings_raw.get(key))

    return VerificationResult(
        verification_status="completed",
        overall_confidence=overall_confidence,
        verified_findings=_findings_from_json(data.get("verified_findings")),
        unsupported_claims=_findings_from_json(data.get("unsupported_claims")),
        contradictions=_findings_from_json(data.get("contradictions")),
        financial_issues=_findings_from_json(data.get("financial_issues")),
        valuation_issues=_findings_from_json(data.get("valuation_issues")),
        research_limitations=str(data.get("research_limitations") or ""),
        shark_specific_findings=shark_specific_findings,
        material_risks=[str(r) for r in (data.get("material_risks") or [])],
        recommendations=[str(r) for r in (data.get("recommendations") or [])],
        sources_or_evidence_references=[
            str(r) for r in (data.get("sources_or_evidence_references") or [])
        ],
    )


def _findings_from_json(items: Any) -> list[VerificationFinding]:
    if not isinstance(items, list):
        return []
    findings: list[VerificationFinding] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        assessment = str(item.get("assessment") or "").strip().lower()
        if assessment not in CLAIM_STATUSES:
            assessment = "insufficient_evidence"
        severity = str(item.get("severity") or "").strip().lower()
        if severity not in VERIFICATION_SEVERITIES:
            severity = "low"
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        try:
            findings.append(
                VerificationFinding(
                    subject=str(item.get("subject") or ""),
                    claim=str(item.get("claim") or ""),
                    assessment=assessment,
                    evidence=str(item.get("evidence") or ""),
                    severity=severity,
                    confidence=confidence,
                )
            )
        except (TypeError, ValueError):
            continue
    return findings
