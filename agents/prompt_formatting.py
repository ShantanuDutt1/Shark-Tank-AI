"""
Shared prompt-rendering helpers for Shark Tank AI.

Extracted in Release 0.7 from `agents/shark_agent.py`, where
`format_market_brief()` and `format_qa_transcript()` originated as
private helpers (`_format_market_brief()`/`_format_qa_transcript()`).
The Verification Agent and Consensus Engine (`agents/verification_agent.py`,
`orchestrator/consensus_engine.py`) need the exact same renderings of a
`MarketRealityBrief`, a conversation transcript, and a Shark's `Offer`
that `SharkAgent` already builds for its own prompts -- duplicating
that formatting logic a second and third time would violate
`docs/coding_standards.md` -> *Modularity: No Duplicated Logic*, so it
now lives here instead, and `SharkAgent` imports it like any other
consumer.

Pure formatting only -- no provider calls, no business logic, no
untrusted-content wrapping (callers apply `agents.prompt_safety
.wrap_untrusted()` themselves at the point a formatted string is
spliced into a prompt, exactly as `SharkAgent` already does; keeping
that wrapping decision at the call site, not baked in here, mirrors
Release 0.6/0.6.1's existing convention).
"""

from __future__ import annotations

from models.enums import SPEAKER_LABELS, SpeakerRole
from models.schemas import (
    ConsensusResult,
    ConversationMessage,
    FinancialAnalysisResult,
    MarketRealityBrief,
    NegotiationResponse,
    Offer,
    ProposalValidationResult,
    VerificationResult,
)


def format_qa_transcript(conversation: list[ConversationMessage]) -> str:
    """Render the Shark/Founder exchange so far as plain text, for
    inclusion in a prompt. Moderator narration is omitted -- it carries
    no evaluative content a Shark, the Verification Agent, or the
    Consensus Engine needs."""
    relevant_roles = (
        SpeakerRole.CONSERVATIVE_VC,
        SpeakerRole.GROWTH_VC,
        SpeakerRole.BALANCED_VC,
        SpeakerRole.FOUNDER,
    )
    relevant = [m for m in conversation if m.speaker in relevant_roles]
    if not relevant:
        return "(No questions have been asked yet.)"
    lines = [f"{SPEAKER_LABELS.get(m.speaker, m.speaker.value)}: {m.content}" for m in relevant]
    return "\n".join(lines)


def format_offer(offer: Offer) -> str:
    """Render a single `Offer` as plain text for inclusion in a
    prompt. Distinguishes a genuine decline from a technical failure
    (Release 0.6.1's `evaluation_available`) so a reader of the prompt
    -- Verification or Consensus, as of Release 0.7 -- never mistakes
    one for the other."""
    if not offer.evaluation_available:
        return f"Evaluation unavailable (technical failure). {offer.rationale}"
    if not offer.interested:
        return f"Not interested. Reasoning: {offer.rationale}"
    parts = [f"Interested: ${offer.amount:,.0f} for {offer.equity_pct:.1f}% equity."]
    if offer.conditions:
        parts.append(f"Conditions: {offer.conditions}")
    parts.append(f"Reasoning: {offer.rationale}")
    return " ".join(parts)


def format_offers(offers: dict[SpeakerRole, Offer]) -> str:
    """Render all three Sharks' offers as a labeled plain-text block,
    in the fixed committee order (Conservative, Growth, Balanced) --
    used by the Verification Agent and Consensus Engine (Release 0.7),
    which both need every Shark's position at once, unlike a single
    Shark's own prompt."""
    order = (SpeakerRole.CONSERVATIVE_VC, SpeakerRole.GROWTH_VC, SpeakerRole.BALANCED_VC)
    lines = []
    for role in order:
        offer = offers.get(role)
        if offer is None:
            continue
        label = SPEAKER_LABELS.get(role, role.value)
        lines.append(f"{label} (confidence {offer.confidence:.2f}): {format_offer(offer)}")
    return "\n".join(lines) if lines else "(No Shark offers are available.)"


def format_market_brief(brief: MarketRealityBrief | None) -> str:
    """Render a `MarketRealityBrief` as plain text for inclusion in a
    prompt, or an explicit "none available" note -- never silently
    omitted, so a prompt always makes clear whether external evidence
    exists (Release 0.6 spec Part C)."""
    if brief is None:
        return "(No market research is available for this session.)"
    if brief.is_fallback:
        return f"(Market research was not available: {brief.research_limitations})"

    lines = [
        f"Industry: {brief.industry or 'unknown'}",
        f"Business model: {brief.business_model or 'unknown'}",
        f"Market summary: {brief.market_summary or 'Insufficient evidence'}",
        f"Market size: {brief.market_size_estimate or 'Insufficient evidence'}",
        f"Market growth: {brief.market_growth or 'Insufficient evidence'}",
    ]
    if brief.competitors:
        lines.append(f"Competitors/comparables: {', '.join(brief.competitors)}")
    if brief.financial_benchmarks:
        lines.append(f"Financial benchmarks: {brief.financial_benchmarks}")
    if brief.relevant_transactions:
        lines.append(f"Relevant transactions: {brief.relevant_transactions}")
    if brief.has_conflicting_evidence:
        lines.append(
            "Conflicting evidence found (do not treat one source as settled fact): "
            f"{brief.conflicting_evidence_notes or 'sources disagreed on at least one figure.'}"
        )
    if brief.failed_objectives:
        lines.append(
            "Research categories that could not be completed (technical failure, not "
            f"negative evidence): {', '.join(brief.failed_objectives)}"
        )

    valuation = brief.valuation
    if valuation.confidence == "insufficient_evidence" or valuation.low is None:
        lines.append("Market-informed valuation: insufficient evidence for a defensible estimate.")
    else:
        lines.append(
            f"Market-informed valuation range: ${valuation.low:,.0f}-${valuation.high:,.0f} "
            f"(methodology: {valuation.methodology}; confidence: {valuation.confidence})"
        )
    if brief.founder_implied_valuation is not None:
        lines.append(f"Founder's implied valuation: ${brief.founder_implied_valuation:,.0f}")
    if brief.valuation_comparison:
        lines.append(f"Valuation comparison: {brief.valuation_comparison}")

    for claim in brief.unsupported_claims:
        lines.append(
            f'Unsupported/aggressive claim: "{claim.claim}" -- {claim.assessment} '
            f"({claim.external_evidence})"
        )
    for discrepancy in brief.material_discrepancies:
        lines.append(f"Material discrepancy: {discrepancy}")
    if brief.research_limitations:
        lines.append(f"Research limitations: {brief.research_limitations}")

    return "\n".join(lines)


def format_verification(result: VerificationResult | None) -> str:
    """Render a `VerificationResult` as plain text for inclusion in the
    Consensus Engine's prompt (Release 0.7) -- never silently omitted,
    so Consensus always knows whether a real audit happened."""
    if result is None:
        return "(No verification is available for this session.)"
    if result.verification_status == "unavailable":
        return f"(Verification was not available: {result.research_limitations})"

    lines = [f"Overall verification confidence: {result.overall_confidence:.2f}"]
    for label, findings in (
        ("Unsupported claims", result.unsupported_claims),
        ("Contradictions", result.contradictions),
        ("Financial issues", result.financial_issues),
        ("Valuation issues", result.valuation_issues),
    ):
        for finding in findings:
            lines.append(
                f"{label} ({finding.severity}, {finding.subject}): \"{finding.claim}\" -- "
                f"{finding.assessment}: {finding.evidence}"
            )
    for subject, findings in result.shark_specific_findings.items():
        for finding in findings:
            lines.append(
                f"Shark-specific finding for {subject} ({finding.severity}): "
                f'"{finding.claim}" -- {finding.assessment}: {finding.evidence}'
            )
    if result.material_risks:
        lines.append("Material risks: " + "; ".join(result.material_risks))
    if result.research_limitations:
        lines.append(f"Research limitations: {result.research_limitations}")
    if not lines[1:]:
        lines.append("No unsupported claims, contradictions, or issues were found.")
    return "\n".join(lines)


def format_financial_analysis(result: FinancialAnalysisResult | None) -> str:
    """Render a `FinancialAnalysisResult` as plain text for inclusion
    in a prompt (Release 0.8) -- used by both the Verification Agent
    (to audit the analysis) and the Consensus Engine (to incorporate
    it). Never silently omitted, so a prompt always makes clear
    whether financial analysis exists."""
    if result is None:
        return "(No financial analysis is available for this session.)"
    if result.analysis_status == "unavailable":
        return f"(Financial analysis was not available: {result.research_limitations})"

    lines = [f"Business model: {result.business_model or 'unknown'}"]
    for fact in result.financial_facts:
        value_text = f"{fact.value:,.2f}" if fact.value is not None else "missing"
        lines.append(f"Fact [{fact.provenance}] {fact.metric} = {value_text} ({fact.note or 'no note'})")

    def _fmt(label: str, value: float | None, unit: str = "") -> None:
        if value is not None:
            lines.append(f"{label}: {value:,.2f}{unit}")

    _fmt("Implied post-money valuation", result.implied_post_money_valuation, " USD")
    _fmt("Implied pre-money valuation", result.implied_pre_money_valuation, " USD")
    _fmt("Revenue multiple", result.revenue_multiple, "x")
    _fmt("ARR multiple", result.arr_multiple, "x")
    _fmt("Gross margin", result.gross_margin_pct, "%")
    _fmt("Operating margin", result.operating_margin_pct, "%")
    _fmt("Revenue growth", result.revenue_growth_pct, "%")
    _fmt("Monthly burn", result.monthly_burn, " USD")
    _fmt("Runway", result.runway_months, " months")
    _fmt("Dilution", result.dilution_pct, "%")
    _fmt("LTV/CAC", result.ltv_to_cac, "x")

    for finding in result.consistency_findings:
        lines.append(f"Consistency [{finding.assessment}] {finding.subject}: {finding.explanation}")
    for scenario in result.scenarios:
        v = scenario.valuation
        if v.confidence == "insufficient_evidence" or v.low is None:
            lines.append(f"Scenario {scenario.scenario}: insufficient evidence for a valuation.")
        else:
            lines.append(
                f"Scenario {scenario.scenario}: ${v.low:,.0f}-${v.high:,.0f} "
                f"(assumption basis: {scenario.assumption_basis}; {scenario.assumptions})"
            )
    for risk in result.risk_factors:
        lines.append(
            f"Risk [{risk.severity}, {risk.category}]: {risk.description} "
            f"(mitigable: {risk.mitigable}, material: {risk.material})"
        )
    for upside in result.upside_factors:
        lines.append(f"Upside [{upside.basis}, {upside.category}]: {upside.description}")
    if result.business_quality_summary:
        lines.append(f"Business quality summary: {result.business_quality_summary}")
    if result.financial_health_summary:
        lines.append(f"Financial health summary: {result.financial_health_summary}")
    if result.research_limitations:
        lines.append(f"Research limitations: {result.research_limitations}")

    return "\n".join(lines)


def format_validation_result(result: ProposalValidationResult | None) -> str:
    """Render a `ProposalValidationResult` as plain text for inclusion
    in a prompt (Release 0.9) -- used by the Founder Feedback Agent,
    which needs the Moderator's structured extraction (including
    `missing_information`, otherwise discarded after `Pitch` is built)
    as one of its inputs."""
    if result is None:
        return "(No validation result is available for this session.)"
    lines = [f"Accepted: {result.accepted}"]
    if result.reason:
        lines.append(f"Reason: {result.reason}")
    if result.missing_information:
        lines.append("Missing information noted at validation: " + "; ".join(result.missing_information))
    return "\n".join(lines)


def format_negotiation_responses(responses: dict[SpeakerRole, NegotiationResponse]) -> str:
    """Render every Shark's negotiation response as a labeled
    plain-text block, in the fixed committee order -- used by the
    Founder Feedback Agent (Release 0.9). Empty (no negotiation
    happened, e.g. no Shark made an offer) renders an explicit note
    rather than being silently omitted."""
    order = (SpeakerRole.CONSERVATIVE_VC, SpeakerRole.GROWTH_VC, SpeakerRole.BALANCED_VC)
    lines = []
    for role in order:
        response = responses.get(role)
        if response is None:
            continue
        label = SPEAKER_LABELS.get(role, role.value)
        amount = f"${response.amount:,.0f}" if response.amount is not None else "n/a"
        equity = f"{response.equity_pct:.1f}%" if response.equity_pct is not None else "n/a"
        lines.append(
            f"{label}: decision={response.decision}, amount={amount}, equity={equity} -- "
            f"{response.rationale}"
        )
    return "\n".join(lines) if lines else "(No negotiation took place this session.)"


def format_consensus(result: ConsensusResult | None) -> str:
    """Render a `ConsensusResult` as plain text for inclusion in a
    prompt (Release 0.9) -- used by the Founder Feedback Agent, which
    treats Consensus as informative input, not unquestionable truth
    (spec Part 11: the report may note where evidence suggests a
    different emphasis than Consensus reached, as long as it says so
    explicitly)."""
    if result is None:
        return "(No consensus result is available for this session.)"
    if result.recommendation == "unavailable":
        return f"(Consensus was not available: {result.evidence_limitations})"

    lines = [
        f"Recommendation: {result.recommendation} (confidence: {result.confidence:.2f})",
        f"Business quality: {result.business_quality}",
        f"Deal quality: {result.deal_quality}",
        f"Financial health: {result.financial_health}",
    ]
    if result.investment_thesis:
        lines.append(f"Investment thesis: {result.investment_thesis}")
    if result.key_strengths:
        lines.append("Key strengths: " + "; ".join(result.key_strengths))
    if result.key_risks:
        lines.append("Key risks: " + "; ".join(result.key_risks))
    if result.material_disagreements:
        lines.append("Material disagreements: " + "; ".join(result.material_disagreements))
    if result.valuation_assessment:
        lines.append(f"Valuation assessment: {result.valuation_assessment}")
    if result.growth_profile:
        lines.append(f"Growth profile: {result.growth_profile}")
    if result.risk_profile:
        lines.append(f"Risk profile: {result.risk_profile}")
    if result.scenario_summary:
        lines.append(f"Scenario summary: {result.scenario_summary}")
    if result.conditions:
        lines.append("Conditions: " + "; ".join(result.conditions))
    if result.evidence_limitations:
        lines.append(f"Evidence limitations: {result.evidence_limitations}")
    return "\n".join(lines)
