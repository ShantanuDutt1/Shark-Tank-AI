"""
Shark agent.

Release 0.5 replaced the Release 0.4/0.4.1 deterministic templates with
real, provider-backed investment reasoning: `evaluate_pitch()` produces
a real structured `Offer` from an LLM call, `ask_question()` generates
a pitch-adaptive question instead of a fixed template, and
`deliberate()` produces a real (at most two-sentence) deliberation
line. Release 0.6 grounds all three in real external evidence -- each
now optionally takes a `market_brief: MarketRealityBrief` (Release 0.6
spec Part C) -- and adds `negotiate()` for the new Negotiation phase
(spec Part J).

Founder-provided content (the pitch description, the Q&A transcript)
is wrapped as untrusted data (`agents.prompt_safety.wrap_untrusted()`)
in every prompt this class builds -- Release 0.6 spec Part F: a
founder's text must never be able to override these instructions
merely by asking to.

Failure handling follows `docs/agent_contract.md` -> *Error Handling*'s
layering: this class *raises* a specific `providers.exceptions
.ProviderError` subtype when the provider is unconfigured, fails, or
returns something unusable -- it does not silently degrade itself.
Deciding what to do about that failure belongs to the Session Director
(`orchestrator/orchestrator.py`), which is why `fallback_question()`,
`fallback_offer()`, `fallback_deliberation()`, and
`fallback_negotiation_response()` are separate public methods here
rather than being folded into try/except blocks inside the real
methods themselves: the Director calls them explicitly when it catches
a `ProviderError`, so the fallback path is visible at the
orchestration layer, not hidden inside the agent.
"""

from __future__ import annotations

import json
import re
from typing import Any

from agents.base_agent import BaseAgent
from agents.prompt_safety import wrap_untrusted
from config.logging_config import get_logger
from models.enums import SPEAKER_LABELS, SpeakerRole
from models.schemas import (
    ConversationMessage,
    MarketRealityBrief,
    NegotiationResponse,
    Offer,
    Pitch,
    SharkPersona,
)
from prompts.loader import load_prompt
from providers.exceptions import ProviderNotConfiguredError, ProviderResponseError

logger = get_logger(__name__)

#: The three philosophy-based personas from `docs/agent_personas.md`
#: sections 5-7. `risk_tolerance` is a coarse, illustrative placement
#: on the model's existing 0.0-1.0 scale, not a tuned input -- no
#: scoring or weighting logic reads this field directly; it is only
#: ever surfaced to the LLM as descriptive persona context.
CONSERVATIVE_PERSONA = SharkPersona(
    id="conservative_vc",
    name="Conservative VC",
    investment_style="capital-preservation",
    personality_traits=["skeptical", "precise", "evidence-seeking"],
    risk_tolerance=0.15,
    core_attitude="Why will this fail?",
    priorities=[
        "Capital preservation",
        "Positive or near-term cash flow",
        "A proven, not merely theoretical, market",
        "Low downside risk",
        "Existing paying customers",
        "A path to profitability",
        "Strong value-add potential for the amount invested",
    ],
)
GROWTH_PERSONA = SharkPersona(
    id="growth_vc",
    name="Growth VC",
    investment_style="asymmetric-upside",
    personality_traits=["energetic", "ambitious", "mechanism-focused"],
    risk_tolerance=0.9,
    core_attitude="How big can this get, and what's the mechanism that gets it there?",
    priorities=[
        "Growth rate over current profitability",
        "High-risk, high-reward opportunities",
        "Monopoly or category-defining potential",
        "Explosive, not merely steady, growth",
        "Undiscovered or underserved markets",
        "Genuine innovation",
        "Durable competitive advantage",
    ],
)
BALANCED_PERSONA = SharkPersona(
    id="balanced_vc",
    name="Balanced VC",
    investment_style="risk-adjusted-return",
    personality_traits=["even-keeled", "synthesizing", "proportionate"],
    risk_tolerance=0.5,
    core_attitude="Is the risk-adjusted return here actually attractive?",
    priorities=[
        "A reasonable balance of risk and reward",
        "A credible path to profitability",
        "Defensibility against competitors",
        "Sustainable, not just explosive, growth",
        "Founder execution ability",
        "Practical, evidence-backed upside",
    ],
)

#: Deterministic, persona-appropriate opening questions -- the
#: Release 0.4 behavior, now used only as `fallback_question()`'s
#: content when the provider is unavailable, per this module's
#: docstring.
_FALLBACK_QUESTION_TEMPLATES: dict[SpeakerRole, str] = {
    SpeakerRole.CONSERVATIVE_VC: (
        "Before anything else — why will {company} fail? Walk me through "
        "your existing customers and recurring revenue."
    ),
    SpeakerRole.GROWTH_VC: (
        "Set aside today's numbers for a moment — if everything works, how "
        "large could {company} actually become, and what's the mechanism "
        "that gets you there?"
    ),
    SpeakerRole.BALANCED_VC: (
        "Given the stage you're at and the evidence on the table so far, "
        "is the valuation you're asking for proportionate to the risk "
        "here?"
    ),
}

_MAX_TOKENS_QUESTION = 200
_MAX_TOKENS_EVALUATION = 600
_MAX_TOKENS_DELIBERATION = 150
_MAX_TOKENS_NEGOTIATION = 300


class SharkAgent(BaseAgent):
    """A single Shark, distinguished by investment philosophy, not domain."""

    def __init__(
        self,
        role: SpeakerRole,
        persona: SharkPersona,
        provider: Any = None,
    ) -> None:
        if role not in _FALLBACK_QUESTION_TEMPLATES:
            raise ValueError(f"SharkAgent role must be a voting Shark, got {role!r}")
        super().__init__(persona=persona, provider=provider)
        self.role = role

    # ------------------------------------------------------------------
    # Question Round
    # ------------------------------------------------------------------

    def ask_question(
        self,
        pitch: Pitch,
        conversation: list[ConversationMessage] | None = None,
        market_brief: MarketRealityBrief | None = None,
        own_evaluation: Offer | None = None,
    ) -> str:
        """Generate a pitch-adaptive question for the Question Round.

        `market_brief`, if given, lets the question probe a gap or
        discrepancy the research surfaced (Release 0.6 spec Part H).
        `own_evaluation`, if given, is this Shark's preliminary
        evaluation of the pitch (from `evaluate_pitch()`, called just
        before this in the Question Round -- see
        `orchestrator/orchestrator.py`); not currently read by the
        prompt itself, accepted for forward compatibility with a
        future release that wants the question to explicitly reference
        the Shark's own stated concerns.

        Raises `providers.exceptions.ProviderError` (or a subclass) if
        the provider is unconfigured, the request fails, or the
        response is empty -- callers should catch that and use
        `fallback_question()` instead of letting the session stall.
        """
        prompt = self._render(
            "adaptive_question", pitch, conversation or [], market_brief=market_brief
        )
        raw = self._generate(prompt, max_tokens=_MAX_TOKENS_QUESTION)
        question = raw.strip().strip('"')
        if not question:
            raise ProviderResponseError("Provider returned an empty question")
        return question

    def fallback_question(self, pitch: Pitch) -> str:
        """The Release 0.4 deterministic template, used when
        `ask_question()` raises. Not an LLM call."""
        template = _FALLBACK_QUESTION_TEMPLATES[self.role]
        return template.format(company=pitch.company_name)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_pitch(self, pitch: Pitch, context: dict[str, Any] | None = None) -> Offer:
        """Produce this Shark's real, structured evaluation of `pitch`.

        `context["conversation"]`, if provided, is the session's
        `ConversationMessage` history so far (Question Round Q&A) --
        used to ground the evaluation in what the founder has actually
        said, not just the original pitch text. `context["market_brief"]`
        (Release 0.6), if provided, is the session's `MarketRealityBrief`
        -- external evidence to weigh alongside the founder's claims.

        Called twice per session as of Release 0.6: once during the
        Question Round (a preliminary evaluation, informing that
        Shark's own question) and once during Internal Deliberation
        (a final evaluation, now also informed by the founder's actual
        answers) -- see `orchestrator/orchestrator.py`.

        Raises `providers.exceptions.ProviderError` (or a subclass) if
        the provider is unconfigured, the request fails, or the
        response can't be parsed into the expected JSON shape --
        callers should catch that and use `fallback_offer()`.
        """
        context = context or {}
        conversation = context.get("conversation", [])
        market_brief = context.get("market_brief")
        prompt = self._render("pitch_analysis", pitch, conversation, market_brief=market_brief)
        raw = self._generate(prompt, max_tokens=_MAX_TOKENS_EVALUATION)
        data = _parse_json_object(raw)
        return self._offer_from_json(pitch, data)

    def fallback_offer(self, pitch: Pitch, reason: str) -> Offer:
        """An honest "no real decision was made" `Offer`, used when
        `evaluate_pitch()` raises. `confidence=0.0` is reserved for
        exactly this path -- see `Offer`'s docstring in
        `models/schemas.py`. Never fabricates an amount, equity
        figure, or investment interest.

        `evaluation_available=False` (Release 0.6.1) is the
        authoritative signal that this is a technical failure, not a
        genuine decision -- `interested=False` alone would be
        indistinguishable from a real decline. Callers rendering or
        aggregating this `Offer` must check `evaluation_available`
        first (spec Part Q §15: a provider failure must never be
        presented to the founder as an investment rejection).
        """
        return Offer(
            shark_id=self._shark_id(),
            pitch_id=pitch.id,
            interested=False,
            amount=None,
            equity_pct=None,
            conditions=None,
            rationale=(
                "This Shark could not complete a real evaluation right now "
                f"({reason}); no investment decision was made."
            ),
            confidence=0.0,
            evaluation_available=False,
        )

    # ------------------------------------------------------------------
    # Internal Deliberation
    # ------------------------------------------------------------------

    def deliberate(
        self,
        pitch: Pitch,
        own_evaluation: Offer,
        conversation: list[ConversationMessage] | None = None,
        market_brief: MarketRealityBrief | None = None,
    ) -> str:
        """Produce this Shark's at-most-two-sentence deliberation line.

        The founder never sees this method invoked -- the Session
        Director only calls it during `SessionPhase.INTERNAL_DELIBERATION`,
        after the founder has been excluded from the turn sequence.

        Raises `providers.exceptions.ProviderError` (or a subclass) on
        failure; callers should use `fallback_deliberation()`.
        """
        prompt = self._render(
            "deliberation",
            pitch,
            conversation or [],
            own_evaluation=own_evaluation,
            market_brief=market_brief,
        )
        raw = self._generate(prompt, max_tokens=_MAX_TOKENS_DELIBERATION)
        text = raw.strip()
        if not text:
            raise ProviderResponseError("Provider returned an empty deliberation line")
        return _limit_to_two_sentences(text)

    def fallback_deliberation(self, own_evaluation: Offer) -> str:
        """A short, honest deliberation line used when `deliberate()`
        raises. Not an LLM call, and not a fabricated position."""
        persona_name = self.persona.name if self.persona else self.role.value
        if own_evaluation.confidence <= 0.0:
            return f"{persona_name} wasn't able to form a real opinion on this one."
        stance = "I'd want in on this" if own_evaluation.interested else "I'd pass on this one"
        return f"{stance}, based on what's been shared so far."

    # ------------------------------------------------------------------
    # Negotiation (Release 0.6)
    # ------------------------------------------------------------------

    def negotiate(
        self,
        pitch: Pitch,
        own_offer: Offer,
        founder_counter: str,
        conversation: list[ConversationMessage] | None = None,
    ) -> NegotiationResponse:
        """Respond to the founder's one counter-offer against `own_offer`.

        Only ever called for a Shark whose `own_offer.interested` was
        `True` -- the Session Director never negotiates with a Shark
        who already declined (spec Part J, "for each relevant Shark").
        `founder_counter` is treated as untrusted founder content, like
        every other founder-authored text this class handles.

        Raises `providers.exceptions.ProviderError` (or a subclass) on
        failure; callers should use `fallback_negotiation_response()`.
        """
        prompt = self._render_negotiation(pitch, own_offer, founder_counter)
        raw = self._generate(prompt, max_tokens=_MAX_TOKENS_NEGOTIATION)
        data = _parse_json_object(raw)
        return self._negotiation_response_from_json(pitch, data)

    def fallback_negotiation_response(self, pitch: Pitch, reason: str) -> NegotiationResponse:
        """An honest, conservative fallback used when `negotiate()`
        raises. Uses `decision="unavailable"` (Release 0.6.1) rather
        than `"rejected"`: a technical failure is not a genuine
        negotiated outcome, and rendering it as a rejection/"walk
        away" would misrepresent a provider failure as an investment
        decision nobody actually made (spec Part Q §15). No amount,
        equity figure, or acceptance is fabricated either way."""
        return NegotiationResponse(
            shark_id=self._shark_id(),
            pitch_id=pitch.id,
            decision="unavailable",
            amount=None,
            equity_pct=None,
            conditions=None,
            rationale=(
                f"This Shark could not process your counter-offer right now ({reason}); "
                "no negotiation decision was made, so the original offer does not proceed."
            ),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate(self, user_prompt: str, *, max_tokens: int) -> str:
        if self.provider is None:
            raise ProviderNotConfiguredError(
                f"{self._shark_id()} has no provider configured"
            )
        system_prompt = self._system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.provider.generate(messages, max_tokens=max_tokens)

    def _system_prompt(self) -> str:
        persona = self.persona
        assert persona is not None  # every SharkAgent is constructed with one
        template = load_prompt("shark_persona_system")
        priorities_text = "\n".join(f"- {p}" for p in persona.priorities) or "(none specified)"
        return _render_template(
            template,
            name=persona.name,
            investment_style=persona.investment_style,
            personality_traits=", ".join(persona.personality_traits) or "(none specified)",
            core_attitude=persona.core_attitude or "(none specified)",
            priorities=priorities_text,
        )

    def _render(
        self,
        prompt_name: str,
        pitch: Pitch,
        conversation: list[ConversationMessage],
        **extra: Any,
    ) -> str:
        template = load_prompt(prompt_name)
        persona = self.persona
        assert persona is not None
        values = {
            "name": persona.name,
            "company_name": pitch.company_name,
            "founder_name": pitch.founder_name,
            "pitch_description": wrap_untrusted(pitch.description, label="founder_pitch"),
            "qa_transcript": wrap_untrusted(
                _format_qa_transcript(conversation), label="conversation_transcript"
            ),
        }
        if "own_evaluation" in extra:
            values["own_evaluation"] = _format_offer_for_prompt(extra["own_evaluation"])
        if "market_brief" in extra:
            values["market_brief"] = _format_market_brief(extra["market_brief"])
        return _render_template(template, **values)

    def _render_negotiation(self, pitch: Pitch, own_offer: Offer, founder_counter: str) -> str:
        template = load_prompt("negotiation")
        persona = self.persona
        assert persona is not None
        values = {
            "name": persona.name,
            "company_name": pitch.company_name,
            "pitch_description": wrap_untrusted(pitch.description, label="founder_pitch"),
            "own_offer": _format_offer_for_prompt(own_offer),
            "wrapped_counter": wrap_untrusted(founder_counter, label="founder_counter_offer"),
        }
        return _render_template(template, **values)

    def _shark_id(self) -> str:
        return self.persona.id if self.persona else self.role.value

    def _offer_from_json(self, pitch: Pitch, data: dict[str, Any]) -> Offer:
        try:
            interested = bool(data["interested"])
            rationale = str(data.get("rationale") or "").strip()
            confidence = float(data.get("confidence", 0.5))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderResponseError(f"Evaluation JSON missing/invalid fields: {exc}") from exc

        if not rationale:
            raise ProviderResponseError("Evaluation JSON had an empty rationale")

        # confidence=0.0 is reserved for the fallback path (see
        # fallback_offer()'s docstring) -- clamp a real evaluation's
        # self-reported confidence to a tiny positive floor so it's
        # never confused with "no real evaluation happened."
        confidence = max(0.01, min(1.0, confidence))

        amount = _validate_amount(_optional_float(data.get("amount")))
        equity_pct = _validate_equity_pct(_optional_float(data.get("equity_pct")))
        conditions = data.get("conditions")
        conditions = str(conditions).strip() if conditions else None

        return Offer(
            shark_id=self._shark_id(),
            pitch_id=pitch.id,
            interested=interested,
            amount=amount if interested else None,
            equity_pct=equity_pct if interested else None,
            conditions=conditions,
            rationale=rationale,
            confidence=confidence,
        )

    def _negotiation_response_from_json(self, pitch: Pitch, data: dict[str, Any]) -> NegotiationResponse:
        decision = str(data.get("decision") or "").strip().lower()
        if decision not in ("accepted", "rejected", "modified"):
            raise ProviderResponseError(f"Negotiation JSON had an invalid decision: {decision!r}")

        rationale = str(data.get("rationale") or "").strip()
        if not rationale:
            raise ProviderResponseError("Negotiation JSON had an empty rationale")

        amount = _validate_amount(_optional_float(data.get("amount")))
        equity_pct = _validate_equity_pct(_optional_float(data.get("equity_pct")))
        conditions = data.get("conditions")
        conditions = str(conditions).strip() if conditions else None

        if decision == "rejected":
            amount, equity_pct = None, None

        return NegotiationResponse(
            shark_id=self._shark_id(),
            pitch_id=pitch.id,
            decision=decision,
            amount=amount,
            equity_pct=equity_pct,
            conditions=conditions,
            rationale=rationale,
        )


def _render_template(template: str, **values: str) -> str:
    """Fill `{name}`-style placeholders via plain string replacement,
    not `str.format()` -- `prompts/pitch_analysis.txt` contains a
    literal JSON schema whose braces would otherwise need escaping."""
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _format_qa_transcript(conversation: list[ConversationMessage]) -> str:
    """Render the Shark/Founder exchange so far as plain text, for
    inclusion in a prompt. Moderator narration is omitted -- it carries
    no evaluative content a Shark needs."""
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


def _format_offer_for_prompt(offer: Offer) -> str:
    if not offer.interested:
        return f"Not interested. Reasoning: {offer.rationale}"
    parts = [f"Interested: ${offer.amount:,.0f} for {offer.equity_pct:.1f}% equity."]
    if offer.conditions:
        parts.append(f"Conditions: {offer.conditions}")
    parts.append(f"Reasoning: {offer.rationale}")
    return " ".join(parts)


def _format_market_brief(brief: MarketRealityBrief | None) -> str:
    """Render a `MarketRealityBrief` as plain text for inclusion in a
    prompt, or an explicit "none available" note -- never silently
    omitted, so a Shark's prompt always makes clear whether external
    evidence exists (Release 0.6 spec Part C)."""
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
            f"Conflicting evidence found (do not treat one source as settled fact): "
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
        lines.append(f"Unsupported/aggressive claim: \"{claim.claim}\" -- {claim.assessment} ({claim.external_evidence})")
    for discrepancy in brief.material_discrepancies:
        lines.append(f"Material discrepancy: {discrepancy}")
    if brief.research_limitations:
        lines.append(f"Research limitations: {brief.research_limitations}")

    return "\n".join(lines)


def _parse_json_object(raw: str) -> dict[str, Any]:
    """Parse a provider response expected to be a single JSON object,
    tolerating a markdown code fence some models wrap it in."""
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
        raise ProviderResponseError(f"Could not parse JSON from provider response: {exc}") from exc
    if not isinstance(data, dict):
        raise ProviderResponseError("Provider response JSON was not an object")
    return data


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _validate_equity_pct(value: float | None) -> float | None:
    """Reject an equity percentage outside `[0, 100]` rather than
    silently passing through a nonsensical value (Release 0.6 spec
    Part Q/W: "validate numerical values... controlled failure is
    preferable to invented data")."""
    if value is None:
        return None
    if value < 0 or value > 100:
        raise ProviderResponseError(f"equity_pct out of valid range [0, 100]: {value!r}")
    return value


def _validate_amount(value: float | None) -> float | None:
    """Reject a negative investment amount."""
    if value is None:
        return None
    if value < 0:
        raise ProviderResponseError(f"amount cannot be negative: {value!r}")
    return value


def _limit_to_two_sentences(text: str) -> str:
    """Enforce the product's "at most two sentences" deliberation rule
    (Release 0.5 spec section B15) even if the model doesn't perfectly
    comply. A simple split, not full sentence-boundary detection."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(s for s in sentences[:2] if s).strip()
