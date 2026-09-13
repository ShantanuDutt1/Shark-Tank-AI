"""
Typed Event Bus messages for Shark Tank AI.

Every dataclass below corresponds 1:1 to an entry in
`docs/event_catalog.md`, using the same name, publisher, and payload
fields documented there. `session_id` and `emitted_at` are the two
universal fields every event carries (per that document's
*Conventions* section); every other field matches a catalog entry's
*Payload* row exactly.

This module defines the message *shapes* only. Publishing and
subscribing happens through `orchestrator.event_bus.EventBus`. Nothing
here decides when an event fires -- that is the Session Director's
responsibility (`orchestrator/orchestrator.py`), per
`docs/event_catalog.md` -> *Notes for Implementation* #2.

All event dataclasses are keyword-only (`kw_only=True`) so that
required and optional fields can be declared in the order that best
matches the documentation table, without Python's "non-default
argument follows default argument" dataclass-inheritance restriction
forcing an awkward field order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from models.enums import SpeakerRole
from models.schemas import DealStatus


def _utc_now() -> datetime:
    """Timezone-aware "now", in UTC. Replaces the deprecated
    `datetime.utcnow()`, which returns a naive datetime."""
    return datetime.now(UTC)


@dataclass(frozen=True, kw_only=True)
class Event:
    """Base class for every Event Bus message. Never published directly."""

    session_id: str
    emitted_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, kw_only=True)
class ProposalUploaded(Event):
    """Publisher: Frontend, via the Session Director's intake step."""

    proposal_type: str
    content_reference: str


@dataclass(frozen=True, kw_only=True)
class ProposalValidated(Event):
    """Publisher: Session Director (after Validation phase)."""

    summary: str


@dataclass(frozen=True, kw_only=True)
class ProposalRejected(Event):
    """Publisher: Session Director (after Validation phase)."""

    reason: str


@dataclass(frozen=True, kw_only=True)
class SessionStarted(Event):
    """Publisher: Frontend (Start Session), relayed by the Session Director."""


@dataclass(frozen=True, kw_only=True)
class QuestionAsked(Event):
    """Publisher: Moderator Agent."""

    speaker: SpeakerRole
    question: str


@dataclass(frozen=True, kw_only=True)
class ResponseReceived(Event):
    """Publisher: Frontend (founder response), relayed by the Session Director."""

    response_text: str


@dataclass(frozen=True, kw_only=True)
class InterruptRequested(Event):
    """Publisher: Frontend. Not exposed anywhere in the Release 0.4 UI."""

    reason: str = ""


@dataclass(frozen=True, kw_only=True)
class InterruptApproved(Event):
    """Publisher: Session Director."""

    granted: bool
    reason: str | None = None


@dataclass(frozen=True, kw_only=True)
class DebateStarted(Event):
    """Publisher: Session Director. Fires when Internal Deliberation begins."""


@dataclass(frozen=True, kw_only=True)
class DebateFinished(Event):
    """Publisher: Session Director."""

    summary: str


@dataclass(frozen=True, kw_only=True)
class VerificationStarted(Event):
    """Publisher: Session Director."""


@dataclass(frozen=True, kw_only=True)
class VerificationFailed(Event):
    """Publisher: Verification Agent. Not fired in Release 0.4 (no
    Verification Agent intelligence exists yet -- verification always
    deterministically passes; see orchestrator/orchestrator.py)."""

    reason: str
    retry_count: int


@dataclass(frozen=True, kw_only=True)
class ConsensusStarted(Event):
    """Publisher: Session Director."""


@dataclass(frozen=True, kw_only=True)
class ConsensusReached(Event):
    """Publisher: Consensus Engine (Release 0.4: a deterministic placeholder
    inside the Session Director; no real aggregation logic exists yet)."""

    outcome_summary: str


@dataclass(frozen=True, kw_only=True)
class InvestmentDecisionMade(Event):
    """Publisher: Consensus Engine (Release 0.4: deterministic placeholder).

    Fires exactly once per session. In Release 0.4, `deal_status` is
    always `DealStatus.PENDING` with `amount`/`equity_pct` unset --
    real investment intelligence is Release 0.5+ (see
    `docs/architecture.md` -> Consensus Engine).
    """

    deal_status: DealStatus
    amount: float | None = None
    equity_pct: float | None = None
    conditions: str | None = None


@dataclass(frozen=True, kw_only=True)
class SessionEnded(Event):
    """Publisher: Frontend, relayed by the Session Director. Fires both on
    natural completion and on an explicit End Session reset."""

    reason: str  # "completed" | "reset"


@dataclass(frozen=True, kw_only=True)
class PiiSanitized(Event):
    """Publisher: Session Director. Fires once, immediately after
    `start_session()` redacts PII from the raw proposal
    (`utils.pii.anonymize_pii()`), before validation begins. Added in
    Release 0.6 (spec Part E / Part M)."""

    redactions_applied: bool


@dataclass(frozen=True, kw_only=True)
class ProposalExtracted(Event):
    """Publisher: Session Director (via `ModeratorAgent
    .validate_and_extract()`). Fires once per accepted proposal,
    immediately after `ProposalValidated`. Added in Release 0.6 (spec
    Part D / Part M)."""

    founder_name: str
    company_name: str
    ask_amount: float | None = None
    equity_offered_pct: float | None = None


@dataclass(frozen=True, kw_only=True)
class MarketResearchStarted(Event):
    """Publisher: Session Director. Added in Release 0.6."""


@dataclass(frozen=True, kw_only=True)
class MarketResearchCompleted(Event):
    """Publisher: Session Director. Added in Release 0.6."""

    summary: str


@dataclass(frozen=True, kw_only=True)
class MarketResearchFailed(Event):
    """Publisher: Session Director. Fires instead of
    `MarketResearchCompleted` when research could not be completed
    (unconfigured provider, request failure, or an unparseable
    response) -- the session still proceeds with
    `MarketResearchAgent.fallback_brief()`. Added in Release 0.6."""

    reason: str


@dataclass(frozen=True, kw_only=True)
class SharkOfferMade(Event):
    """Publisher: Session Director. Fires once per Shark during
    `INVESTMENT_DECISION`, after each Shark's real offer has been
    announced in the conversation. Added in Release 0.6 (spec Part I /
    Part M).

    `evaluation_available` (Release 0.6.1) is `False` when this Shark's
    evaluation failed technically -- `interested` is always `False` in
    that case too (see `models.schemas.Offer`), but a subscriber must
    check `evaluation_available` first to avoid treating a technical
    failure as a genuine decline.
    """

    speaker: SpeakerRole
    interested: bool
    amount: float | None = None
    equity_pct: float | None = None
    evaluation_available: bool = True


@dataclass(frozen=True, kw_only=True)
class NegotiationStarted(Event):
    """Publisher: Session Director. Fires once, when at least one Shark
    made an offer and `NEGOTIATION` begins. Added in Release 0.6 (spec
    Part J / Part M)."""


@dataclass(frozen=True, kw_only=True)
class FounderCounterOffered(Event):
    """Publisher: Frontend, relayed by the Session Director. Fires once
    per founder counter-offer, naming which Shark it targets. Added in
    Release 0.6."""

    speaker: SpeakerRole
    counter_text: str


@dataclass(frozen=True, kw_only=True)
class SharkNegotiationResponded(Event):
    """Publisher: Session Director. Fires once per Shark negotiation
    response (`"accepted"` / `"rejected"` / `"modified"` / (Release
    0.6.1) `"unavailable"` -- a technical failure prevented a real
    negotiation decision; see
    `agents.shark_agent.SharkAgent.fallback_negotiation_response()`).
    Added in Release 0.6."""

    speaker: SpeakerRole
    decision: str


@dataclass(frozen=True, kw_only=True)
class MemorySaved(Event):
    """Publisher: Memory. Not fired in Release 0.4 (no `BaseMemory`
    implementation exists yet; see memory/in_memory_store.py)."""

    key: str
