"""
Session Director for Shark Tank AI.

`docs/architecture.md` -> *Session Director* describes
`SharkTankOrchestrator` as "the class this responsibility will grow
into." Release 0.4 was the first growth: driving the User Session
State Machine (`docs/state_machines.md`) forward using a fixed panel
of three Sharks plus a Moderator, coordinated through an Event Bus
(`orchestrator/event_bus.py`) and a Turn Controller
(`orchestrator/turn_controller.py`). Release 0.5 was the second: real,
provider-backed Shark questions/evaluation/deliberation. Release 0.6
is the third: real Moderator validation & extraction, real Market
Reality Research grounding every Shark's reasoning in external
evidence, and a real Negotiation phase -- this class's own job is
still unchanged: sequencing *when* each of those things happens, never
generating content itself.

The Release 0.6 session flow this class now drives:

    IDLE -> PROPOSAL_UPLOADED -> VALIDATION -> MARKET_RESEARCH
         -> QUESTION_ROUND -> INTERNAL_DELIBERATION -> VERIFICATION
         -> CONSENSUS -> INVESTMENT_DECISION -> NEGOTIATION
         -> SESSION_COMPLETE

Two Shark evaluations happen per session as of Release 0.6, both via
the same `SharkAgent.evaluate_pitch()`: a *preliminary* one during each
Shark's Question Round turn (informing, though not yet directly
quoted in, that Shark's own question -- spec Part B stages 4-5), and a
*final* one during Internal Deliberation, now also informed by the
founder's actual answers (stage 6) -- the final one is what becomes
that Shark's real offer in `INVESTMENT_DECISION` (stage 7).
`VERIFICATION` and `CONSENSUS` remain the Release 0.4/0.5 deterministic
placeholders (Release 0.6 spec Part U: no real Verification Agent or
Consensus Engine yet).

This class has two surfaces:

1. **The original surface (Release 0.1), unchanged.** `agents` and
   `run_pitch()` are exactly as they were. `run_pitch()` still raises
   `NotImplementedError`.
2. **The Session Director surface**, below: `start_session()`,
   `submit_founder_response()`, `end_session()`, and the read-only
   `phase` / `pitch` / `conversation` / `awaiting_founder_response` /
   `market_brief` properties.

Failure handling follows `docs/agent_contract.md` -> *Error Handling*'s
layering, unchanged from Release 0.5: agents and the research
provider *raise* specific exceptions; this class is the one that
catches them at each call site and substitutes the appropriate
fallback, so no provider or research failure can ever leave a session
permanently stuck.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.market_research_agent import MarketResearchAgent
from agents.moderator_agent import ModeratorAgent
from agents.shark_agent import (
    BALANCED_PERSONA,
    CONSERVATIVE_PERSONA,
    GROWTH_PERSONA,
    SharkAgent,
)
from config.logging_config import get_logger
from config.settings import get_settings
from models.enums import SessionPhase, SpeakerRole
from models.schemas import (
    ConversationMessage,
    DealStatus,
    MarketRealityBrief,
    NegotiationSession,
    Offer,
    Pitch,
)
from orchestrator import events
from orchestrator.event_bus import EventBus
from orchestrator.exceptions import InvalidTurnError
from orchestrator.negotiation_controller import NegotiationController
from orchestrator.turn_controller import TurnController
from providers.anthropic_provider import AnthropicProvider
from providers.anthropic_research_provider import AnthropicResearchProvider
from providers.base_provider import BaseProvider
from providers.base_research_provider import BaseResearchProvider
from providers.exceptions import ProviderError, ResearchProviderError
from utils.ids import new_id
from utils.pii import anonymize_pii

logger = get_logger(__name__)


class SharkTankOrchestrator:
    """Coordinates the panel of shark agents for a single Shark Tank session."""

    def __init__(
        self,
        agents: list[BaseAgent] | None = None,
        provider: BaseProvider | None = None,
        research_provider: BaseResearchProvider | None = None,
    ) -> None:
        # --- Original surface (Release 0.1); unchanged behavior. ---
        self.agents = agents or []

        # --- Session Director surface. ---
        self.session_id: str = new_id("session_")
        self.event_bus = EventBus()
        # `provider`/`research_provider` are injectable (tests pass a
        # fake/mock through these constructor params rather than
        # monkeypatching); production code goes through
        # `_build_default_provider()`/`_build_default_research_provider()`,
        # the only places that read API credentials.
        llm_provider = provider if provider is not None else _build_default_provider()
        self._moderator = ModeratorAgent(llm_provider)
        research = (
            research_provider
            if research_provider is not None
            else _build_default_research_provider(llm_provider)
        )
        self._research_agent = MarketResearchAgent(llm_provider, research)
        self._sharks: list[SharkAgent] = [
            SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, llm_provider),
            SharkAgent(SpeakerRole.GROWTH_VC, GROWTH_PERSONA, llm_provider),
            SharkAgent(SpeakerRole.BALANCED_VC, BALANCED_PERSONA, llm_provider),
        ]
        self._turns = TurnController()
        self._negotiation: NegotiationController | None = None
        self._phase: SessionPhase = SessionPhase.IDLE
        self._pitch: Pitch | None = None
        self._market_brief: MarketRealityBrief | None = None
        self._final_offers: dict[SpeakerRole, Offer] = {}
        self._conversation: list[ConversationMessage] = []
        self._next_turn_index = 0

    def run_pitch(self, pitch: Pitch) -> NegotiationSession:
        """Run a full pitch session across all configured shark agents.

        Placeholder. Full multi-round negotiation across an arbitrary
        agent list is not what `submit_founder_response()`'s
        Negotiation phase implements -- see module docstring.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Session Director surface
    # ------------------------------------------------------------------

    @property
    def phase(self) -> SessionPhase:
        """The session's current `SessionPhase`."""
        return self._phase

    @property
    def pitch(self) -> Pitch | None:
        """The `Pitch` this session is evaluating, or `None` before
        `start_session()` has been called. Its `description` has
        already had PII redacted (`utils.pii.anonymize_pii()`) by the
        time anything else in this class sees it."""
        return self._pitch

    @property
    def market_brief(self) -> MarketRealityBrief | None:
        """The session's `MarketRealityBrief`, or `None` before
        `MARKET_RESEARCH` has run."""
        return self._market_brief

    @property
    def conversation(self) -> list[ConversationMessage]:
        """The full conversation history so far, oldest first."""
        return list(self._conversation)

    @property
    def awaiting_founder_response(self) -> bool:
        """Whether the founder is currently expected to respond.

        `True` during `QUESTION_ROUND` when it's genuinely the
        founder's turn, or during `NEGOTIATION` when a counter-offer
        is awaited for the current Shark -- `False` at every other
        phase, including while Sharks/the Moderator are "speaking" or
        while research is running.
        """
        if self._phase == SessionPhase.QUESTION_ROUND:
            return self._turns.awaiting_founder_response
        if self._phase == SessionPhase.NEGOTIATION:
            return self._negotiation is not None and self._negotiation.awaiting_founder_counter
        return False

    def start_session(self, pitch: Pitch) -> None:
        """Begin a new session for `pitch`.

        Drives the session from `IDLE` through `PROPOSAL_UPLOADED`,
        `VALIDATION`, and `MARKET_RESEARCH` into `QUESTION_ROUND`,
        stopping once the first Shark has asked its question and the
        founder's response is awaited. Raises `InvalidTurnError` if
        called on a session that has already started.

        `pitch.description` is PII-redacted (`utils.pii.anonymize_pii()`)
        immediately, before anything else in this class -- including
        Moderator validation -- ever sees it (Release 0.6 spec Part E).
        """
        if self._phase != SessionPhase.IDLE:
            raise InvalidTurnError(
                f"start_session() called while phase is {self._phase!r}, expected IDLE"
            )

        truncated_description = _cap_description_length(pitch.description)
        sanitized_description = anonymize_pii(truncated_description)
        self._pitch = pitch.model_copy(update={"description": sanitized_description})
        self.event_bus.publish(events.SessionStarted(session_id=self.session_id))
        self.event_bus.publish(
            events.PiiSanitized(
                session_id=self.session_id,
                redactions_applied=sanitized_description != pitch.description,
            )
        )

        self._phase = SessionPhase.PROPOSAL_UPLOADED
        self._say(SpeakerRole.MODERATOR, self._moderator.welcome_message())
        self.event_bus.publish(
            events.ProposalUploaded(
                session_id=self.session_id,
                proposal_type="Text",
                content_reference=self._pitch.description[:200],
            )
        )

        self._run_validation()

    def submit_founder_response(self, response_text: str) -> None:
        """Record the founder's response and advance the session.

        Dispatches on the current phase: during `QUESTION_ROUND` this
        advances the fixed Shark/Founder turn sequence
        (`orchestrator/turn_controller.py`); during `NEGOTIATION` it
        treats `response_text` as a counter-offer to the current Shark
        (`orchestrator/negotiation_controller.py`). Raises
        `InvalidTurnError` if it is not currently the founder's turn in
        either sense -- callers (`ui/response.py`) are expected to gate
        this on `awaiting_founder_response` first.
        """
        if self._phase == SessionPhase.QUESTION_ROUND:
            self._handle_question_round_response(response_text)
        elif self._phase == SessionPhase.NEGOTIATION:
            self._handle_negotiation_counter(response_text)
        else:
            raise InvalidTurnError(
                "submit_founder_response() called when it is not the founder's turn "
                f"(phase={self._phase!r})"
            )

    def end_session(self, reason: str = "reset") -> None:
        """Publish `SessionEnded`, either because the session finished
        naturally (`reason="completed"`) or the founder reset it early
        (`reason="reset"`). Clears no local state itself -- see
        Release 0.4's original docstring for why."""
        self.event_bus.publish(events.SessionEnded(session_id=self.session_id, reason=reason))

    # ------------------------------------------------------------------
    # Internal helpers: conversation
    # ------------------------------------------------------------------

    def _say(
        self, speaker: SpeakerRole, content: str, requires_response: bool = False
    ) -> ConversationMessage:
        """Append a message to the conversation history and return it."""
        message = ConversationMessage(
            id=new_id("msg_"),
            speaker=speaker,
            content=content,
            turn_index=self._next_turn_index,
            requires_response=requires_response,
        )
        self._next_turn_index += 1
        self._conversation.append(message)
        return message

    # ------------------------------------------------------------------
    # Validation & extraction (Release 0.6)
    # ------------------------------------------------------------------

    def _run_validation(self) -> None:
        assert self._pitch is not None
        self._phase = SessionPhase.VALIDATION
        raw_description = self._pitch.description

        try:
            result = self._moderator.validate_and_extract(raw_description)
        except ProviderError as exc:
            logger.warning(
                "Proposal validation failed (%s); using fallback validation",
                type(exc).__name__,
            )
            result = self._moderator.fallback_validate(raw_description)

        if not result.accepted:
            reason = result.reason or "The submitted proposal was empty."
            self.event_bus.publish(
                events.ProposalRejected(session_id=self.session_id, reason=reason)
            )
            self._say(SpeakerRole.MODERATOR, f"This proposal could not be accepted: {reason}")
            # docs/state_machines.md rule 2: a rejected proposal returns to
            # Idle rather than advancing.
            self._phase = SessionPhase.IDLE
            return

        # Release 0.6.1 spec Part E §13: a second, defensive PII pass
        # over whatever the Moderator's LLM call extracted/paraphrased
        # -- the input it saw was already redacted, but a
        # paraphrase or re-extraction is new model output, not a
        # verbatim echo, so it is sanitized again before it becomes
        # part of persistent session state.
        self._pitch = self._pitch.model_copy(
            update={
                "description": anonymize_pii(result.description or raw_description),
                "founder_name": anonymize_pii(result.founder_name),
                "company_name": anonymize_pii(result.company_name),
                "ask_amount": result.ask_amount,
                "equity_offered_pct": result.equity_offered_pct,
                "valuation": result.valuation,
            }
        )
        summary = self._moderator.validation_summary(self._pitch)
        self.event_bus.publish(
            events.ProposalValidated(session_id=self.session_id, summary=summary)
        )
        self.event_bus.publish(
            events.ProposalExtracted(
                session_id=self.session_id,
                founder_name=self._pitch.founder_name,
                company_name=self._pitch.company_name,
                ask_amount=self._pitch.ask_amount,
                equity_offered_pct=self._pitch.equity_offered_pct,
            )
        )
        self._run_market_research()

    # ------------------------------------------------------------------
    # Market Reality Research (Release 0.6)
    # ------------------------------------------------------------------

    def _run_market_research(self) -> None:
        assert self._pitch is not None
        self._phase = SessionPhase.MARKET_RESEARCH
        self._say(SpeakerRole.MODERATOR, self._moderator.market_research_announcement())
        self.event_bus.publish(events.MarketResearchStarted(session_id=self.session_id))

        try:
            brief = self._research_agent.research(self._pitch)
        except (ProviderError, ResearchProviderError) as exc:
            logger.warning(
                "Market research failed (%s); using fallback brief", type(exc).__name__
            )
            brief = self._research_agent.fallback_brief(self._pitch, reason=type(exc).__name__)
            self.event_bus.publish(
                events.MarketResearchFailed(session_id=self.session_id, reason=type(exc).__name__)
            )

        self._market_brief = brief
        self.event_bus.publish(
            events.MarketResearchCompleted(
                session_id=self.session_id, summary=_summarize_brief(brief)
            )
        )
        self._begin_question_round()

    # ------------------------------------------------------------------
    # Question Round
    # ------------------------------------------------------------------

    def _begin_question_round(self) -> None:
        self._phase = SessionPhase.QUESTION_ROUND
        self._say(SpeakerRole.MODERATOR, self._moderator.question_round_announcement())
        self._turns.reset()
        first_speaker = self._turns.advance()
        assert first_speaker is not None  # the sequence always starts with a Shark
        self._prompt_shark_turn(first_speaker)

    def _handle_question_round_response(self, response_text: str) -> None:
        if not self._turns.awaiting_founder_response:
            raise InvalidTurnError(
                "submit_founder_response() called when it is not the founder's turn"
            )

        # Release 0.6.1 spec Part E §13: founder interaction is
        # sanitized before it is stored or reaches any Shark prompt,
        # not just the original proposal.
        response_text = anonymize_pii(response_text)
        self._say(SpeakerRole.FOUNDER, response_text)
        self.event_bus.publish(
            events.ResponseReceived(session_id=self.session_id, response_text=response_text)
        )

        next_speaker = self._turns.advance()
        if next_speaker is None:
            self._run_deliberation_pipeline()
        else:
            self._prompt_shark_turn(next_speaker)

    def _prompt_shark_turn(self, speaker: SpeakerRole) -> None:
        """Have `speaker` (a Shark) form a preliminary evaluation (Release
        0.6 spec Part B stage 4, "Shark Analysis") and then ask its
        question informed by it (stage 5), before advancing the turn
        controller to the following FOUNDER slot."""
        shark = self._shark_for_role(speaker)
        context = {"conversation": self._conversation, "market_brief": self._market_brief}

        try:
            preliminary = shark.evaluate_pitch(self._pitch, context)  # type: ignore[arg-type]
        except ProviderError as exc:
            logger.warning(
                "Shark %s preliminary evaluation failed (%s); using fallback offer",
                speaker.value,
                type(exc).__name__,
            )
            preliminary = shark.fallback_offer(self._pitch, reason=type(exc).__name__)  # type: ignore[arg-type]

        try:
            question = shark.ask_question(
                self._pitch,  # type: ignore[arg-type]
                self._conversation,
                market_brief=self._market_brief,
                own_evaluation=preliminary,
            )
        except ProviderError as exc:
            logger.warning(
                "Shark %s question generation failed (%s); using fallback question",
                speaker.value,
                type(exc).__name__,
            )
            question = shark.fallback_question(self._pitch)  # type: ignore[arg-type]

        self._say(speaker, question, requires_response=True)
        self.event_bus.publish(
            events.QuestionAsked(session_id=self.session_id, speaker=speaker, question=question)
        )
        self._turns.advance()  # lands on the following FOUNDER slot

    def _shark_for_role(self, role: SpeakerRole) -> SharkAgent:
        for shark in self._sharks:
            if shark.role == role:
                return shark
        raise InvalidTurnError(f"No SharkAgent configured for role {role!r}")

    # ------------------------------------------------------------------
    # Internal Deliberation -> Verification -> Consensus -> Offers
    # ------------------------------------------------------------------

    def _run_deliberation_pipeline(self) -> None:
        """Carry the session from Internal Deliberation through the
        real Investment Decision (initial offers), then into
        Negotiation or straight to completion if nobody made an offer.

        Each Shark's *final* evaluation here (as opposed to the
        preliminary one in `_prompt_shark_turn()`) is now informed by
        the founder's actual Question Round answers -- this final
        evaluation is what becomes that Shark's real `Offer`.
        Verification and Consensus remain the Release 0.4/0.5
        deterministic placeholders (Release 0.6 spec Part U).
        """
        self._phase = SessionPhase.INTERNAL_DELIBERATION
        self._say(SpeakerRole.MODERATOR, self._moderator.deliberation_announcement())
        self.event_bus.publish(events.DebateStarted(session_id=self.session_id))

        final_offers = self._evaluate_all_sharks()
        self._deliberate_all_sharks(final_offers)
        self._final_offers = final_offers

        self.event_bus.publish(
            events.DebateFinished(
                session_id=self.session_id, summary=_summarize_offers(final_offers)
            )
        )

        self._phase = SessionPhase.VERIFICATION
        self.event_bus.publish(events.VerificationStarted(session_id=self.session_id))
        # Placeholder: verification always deterministically passes; no
        # Verification Agent exists yet (Release 0.7 scope).

        self._phase = SessionPhase.CONSENSUS
        self.event_bus.publish(events.ConsensusStarted(session_id=self.session_id))
        self.event_bus.publish(
            events.ConsensusReached(
                session_id=self.session_id, outcome_summary=_summarize_offers(final_offers)
            )
        )

        self._phase = SessionPhase.INVESTMENT_DECISION
        self._announce_offers(final_offers)
        self.event_bus.publish(
            events.InvestmentDecisionMade(
                session_id=self.session_id,
                deal_status=DealStatus.PENDING,
                conditions=(
                    "Each Shark's offer above is real and independent; a formal "
                    "cross-Shark Consensus Engine is not implemented in this "
                    "release (Release 0.7 scope)."
                ),
            )
        )

        self._begin_negotiation_or_complete(final_offers)

    def _evaluate_all_sharks(self) -> dict[SpeakerRole, Offer]:
        """Have every Shark independently form its final evaluation,
        now informed by the founder's actual Question Round answers and
        the Market Reality Brief. A Shark whose provider call fails
        gets `SharkAgent.fallback_offer()` instead of stalling the
        whole session."""
        offers: dict[SpeakerRole, Offer] = {}
        context = {"conversation": self._conversation, "market_brief": self._market_brief}
        for shark in self._sharks:
            try:
                offer = shark.evaluate_pitch(self._pitch, context)  # type: ignore[arg-type]
            except ProviderError as exc:
                logger.warning(
                    "Shark %s evaluation failed (%s); using fallback offer",
                    shark.role.value,
                    type(exc).__name__,
                )
                offer = shark.fallback_offer(self._pitch, reason=type(exc).__name__)  # type: ignore[arg-type]
            offers[shark.role] = offer
        return offers

    def _deliberate_all_sharks(self, offers: dict[SpeakerRole, Offer]) -> None:
        """Have every Shark deliver its own concise deliberation line,
        in the fixed Conservative -> Growth -> Balanced order."""
        for shark in self._sharks:
            offer = offers[shark.role]
            try:
                line = shark.deliberate(
                    self._pitch, offer, self._conversation, market_brief=self._market_brief  # type: ignore[arg-type]
                )
            except ProviderError as exc:
                logger.warning(
                    "Shark %s deliberation failed (%s); using fallback line",
                    shark.role.value,
                    type(exc).__name__,
                )
                line = shark.fallback_deliberation(offer)
            self._say(shark.role, line)

    def _announce_offers(self, offers: dict[SpeakerRole, Offer]) -> None:
        """Have each Shark announce its real, final offer (or pass) in
        the conversation -- the founder must see these before
        Negotiation begins."""
        for shark in self._sharks:
            offer = offers[shark.role]
            self._say(shark.role, _offer_announcement_text(offer))
            self.event_bus.publish(
                events.SharkOfferMade(
                    session_id=self.session_id,
                    speaker=shark.role,
                    interested=offer.interested,
                    amount=offer.amount,
                    equity_pct=offer.equity_pct,
                    evaluation_available=offer.evaluation_available,
                )
            )

    # ------------------------------------------------------------------
    # Negotiation (Release 0.6)
    # ------------------------------------------------------------------

    def _begin_negotiation_or_complete(self, offers: dict[SpeakerRole, Offer]) -> None:
        interested_roles = {role for role, offer in offers.items() if offer.interested}
        # Preserve the fixed committee order (Conservative, Growth, Balanced).
        ordered = [shark.role for shark in self._sharks if shark.role in interested_roles]

        if not ordered:
            self._say(
                SpeakerRole.MODERATOR,
                "No Sharks made an offer this time, so there's nothing to negotiate.",
            )
            self._complete_session()
            return

        self._negotiation = NegotiationController(ordered)
        self._negotiation.start()
        self._phase = SessionPhase.NEGOTIATION
        self._say(SpeakerRole.MODERATOR, self._moderator.negotiation_announcement())
        self.event_bus.publish(events.NegotiationStarted(session_id=self.session_id))

    def _handle_negotiation_counter(self, counter_text: str) -> None:
        if self._negotiation is None or not self._negotiation.awaiting_founder_counter:
            raise InvalidTurnError(
                "submit_founder_response() called during NEGOTIATION with no Shark awaiting a counter"
            )

        shark_role = self._negotiation.current_shark
        assert shark_role is not None
        shark = self._shark_for_role(shark_role)
        offer = self._final_offers[shark_role]

        # Release 0.6.1 spec Part E §13: a negotiation counter is
        # founder interaction too -- sanitize it the same way as a
        # Question Round response before it is stored or sent to the
        # Shark.
        counter_text = anonymize_pii(counter_text)
        self._say(SpeakerRole.FOUNDER, counter_text)
        self.event_bus.publish(
            events.FounderCounterOffered(
                session_id=self.session_id, speaker=shark_role, counter_text=counter_text
            )
        )

        try:
            response = shark.negotiate(self._pitch, offer, counter_text, self._conversation)  # type: ignore[arg-type]
        except ProviderError as exc:
            logger.warning(
                "Shark %s negotiation response failed (%s); using fallback response",
                shark_role.value,
                type(exc).__name__,
            )
            response = shark.fallback_negotiation_response(
                self._pitch, reason=type(exc).__name__  # type: ignore[arg-type]
            )

        self._say(shark_role, _negotiation_response_text(response))
        self.event_bus.publish(
            events.SharkNegotiationResponded(
                session_id=self.session_id, speaker=shark_role, decision=response.decision
            )
        )

        next_shark = self._negotiation.advance()
        if next_shark is None:
            self._complete_session()

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def _complete_session(self) -> None:
        self._say(SpeakerRole.MODERATOR, self._moderator.closing_message())
        self._phase = SessionPhase.SESSION_COMPLETE
        self.end_session(reason="completed")


#: A generous but finite cap on how much proposal text one session
#: will ever send to a provider. Release 0.6 spec Part W: "oversized
#: inputs" is an explicit security-review item -- this bounds worst-
#: case prompt size/cost/risk from a maliciously or accidentally huge
#: submission (e.g. a many-page PDF) without meaningfully constraining
#: any realistic pitch, which is normally a few paragraphs.
_MAX_DESCRIPTION_CHARS = 20_000


def _cap_description_length(description: str) -> str:
    if len(description) <= _MAX_DESCRIPTION_CHARS:
        return description
    return description[:_MAX_DESCRIPTION_CHARS] + "\n\n[Content truncated: proposal exceeded the maximum accepted length.]"


def _build_default_provider() -> BaseProvider:
    """Construct the production `AnthropicProvider` from configuration.

    The only place in this module that reads LLM API credentials
    (`config.settings.Settings.anthropic_api_key`) -- everything else
    talks to `provider` only through the generic `BaseProvider`
    interface. If no key is configured, the resulting provider simply
    has `is_configured == False`; every agent that uses it raises a
    specific `ProviderNotConfiguredError` the first time it tries,
    which this class's call sites already catch and fall back from --
    so the app keeps working with zero configuration, exactly as it
    always has.
    """
    settings = get_settings()
    return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.llm_model)


def _build_default_research_provider(llm_provider: BaseProvider) -> BaseResearchProvider:
    """Construct the production `AnthropicResearchProvider`, reusing the
    same `llm_provider` `_build_default_provider()` built (or the
    injected one, in tests) -- no separate search-vendor credential
    exists or is needed (Release 0.6 spec Part S)."""
    return AnthropicResearchProvider(llm_provider)


def _summarize_offers(offers: dict[SpeakerRole, Offer]) -> str:
    """A factual, one-line tally of how many Sharks were interested --
    not a consensus decision. Used for event payloads only; never
    shown to the founder in chat. Real aggregation logic is Release
    0.7's Consensus Engine, not this.

    Counts only genuinely-evaluated offers as interested/not; Sharks
    whose evaluation was technically unavailable (Release 0.6.1) are
    called out separately rather than folded into "not interested,"
    per the same evaluation-available-vs-genuine-decision distinction
    `_offer_announcement_text()` applies to the founder-facing text.
    """
    unavailable = sum(1 for offer in offers.values() if not offer.evaluation_available)
    evaluated = [offer for offer in offers.values() if offer.evaluation_available]
    interested = sum(1 for offer in evaluated if offer.interested)
    summary = f"{interested} of {len(evaluated)} evaluated Sharks expressed interest during deliberation."
    if unavailable:
        summary += f" {unavailable} Shark(s) could not be evaluated due to a technical issue."
    return summary


def _summarize_brief(brief: MarketRealityBrief) -> str:
    """A short, factual one-line summary of a `MarketRealityBrief`, for
    the `MarketResearchCompleted` event payload only -- the full brief
    is available via `SharkTankOrchestrator.market_brief`, and the
    conversation itself only ever shows the Moderator's fixed
    announcement, never a dumped report (Release 0.6 spec Part O)."""
    if brief.is_fallback:
        return "Market research unavailable; proceeding without external evidence."
    return (
        f"Industry: {brief.industry or 'unknown'}; "
        f"valuation confidence: {brief.valuation.confidence}; "
        f"{len(brief.sources)} source(s) retained."
    )


def _offer_announcement_text(offer: Offer) -> str:
    """Render a Shark's real `Offer` as its own chat-message announcement.

    Checks `evaluation_available` before `interested` (Release 0.6.1
    spec Part Q §15): a Shark that never completed a real evaluation
    must never be announced as having passed/declined -- that would
    present a technical failure as an investment decision.
    """
    if not offer.evaluation_available:
        return (
            "This Shark's evaluation could not be completed due to a technical "
            f"issue; no investment decision was made. {offer.rationale}"
        )
    if not offer.interested:
        return f"I'm going to pass on this one. {offer.rationale}"
    text = f"I'd like to offer ${offer.amount:,.0f} for {offer.equity_pct:.1f}% equity."
    if offer.conditions:
        text += f" Condition: {offer.conditions}."
    return f"{text} {offer.rationale}"


def _negotiation_response_text(response) -> str:  # type: ignore[no-untyped-def]
    """Render a Shark's `NegotiationResponse` as its own chat-message
    announcement.

    `"unavailable"` (Release 0.6.1) is checked separately from
    `"rejected"`: a `negotiate()` failure is a technical failure, not
    the Shark genuinely walking away, and must be worded as such (spec
    Part Q §15).
    """
    if response.decision == "accepted":
        return f"Deal. I accept those terms. {response.rationale}"
    if response.decision == "unavailable":
        return f"{response.rationale}"
    if response.decision == "rejected":
        return f"I'm going to walk away from this one. {response.rationale}"
    amount = f"${response.amount:,.0f}" if response.amount is not None else "an adjusted amount"
    equity = f"{response.equity_pct:.1f}%" if response.equity_pct is not None else "adjusted equity"
    text = f"Let's meet in the middle: {amount} for {equity}."
    if response.conditions:
        text += f" Condition: {response.conditions}."
    return f"{text} {response.rationale}"
