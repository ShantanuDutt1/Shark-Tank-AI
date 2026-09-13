"""
Core data models for Shark Tank AI.

These pydantic models describe the shapes of the domain objects the
application will eventually operate on (a pitch, a shark persona, an
offer, and the negotiation session that ties them together). No
business logic lives here -- only data structure definitions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from models.enums import SessionPhase, SpeakerRole


def _utc_now() -> datetime:
    """Timezone-aware "now", in UTC.

    Used as the `default_factory` for every timestamp in this module
    that records *when something happened* (as opposed to
    `ConversationMessage.created_at`, which is display-only local
    time -- see that model's docstring). Replaces the deprecated
    `datetime.utcnow()`, which returns a naive datetime.
    """
    return datetime.now(UTC)


class DealStatus(str, Enum):
    """Possible outcomes of a negotiation."""

    PENDING = "pending"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COUNTERED = "countered"


class Pitch(BaseModel):
    """A founder's pitch submitted to the panel of sharks.

    `founder_name`, `company_name`, `ask_amount`, and
    `equity_offered_pct` are optional with defaults as of Release 0.4:
    the current proposal intake (`ui/proposal.py`) only collects raw,
    unstructured pitch content (typed text, or an uploaded file's
    name) -- it does not parse or transcribe it. Structured extraction
    of these fields into real values is explicit proposal-validation
    work, planned for a future release
    (`docs/architecture.md` -> Moderator Agent -> `proposal_validation`
    skill), not Release 0.4 (see Release 0.4 spec section 8, "Do not
    add sophisticated proposal validation in 0.4").
    """

    id: str
    founder_name: str = "Founder"
    company_name: str = "The Company"
    description: str
    ask_amount: float | None = None
    equity_offered_pct: float | None = None
    valuation: float | None = None
    created_at: datetime = Field(default_factory=_utc_now)


class SharkPersona(BaseModel):
    """Configuration describing a single AI 'shark' agent's persona.

    `priorities` and `core_attitude` were added in Release 0.5
    (`docs/agent_personas.md` §5-7, "Priorities" and the persona's
    named core attitude, e.g. the Conservative Shark's "Why will this
    fail?"). They are structured domain data describing *who* a
    persona is, not prompt text -- the actual system prompt lives in
    `prompts/shark_persona_system.txt` and is filled in from these
    fields by `agents/shark_agent.py`, per `docs/coding_standards.md`
    ("do not hard-code large prompts inside Python classes").
    """

    id: str
    name: str
    investment_style: str
    personality_traits: list[str] = Field(default_factory=list)
    risk_tolerance: float = 0.5  # 0.0 (cautious) - 1.0 (aggressive)
    priorities: list[str] = Field(default_factory=list)
    core_attitude: str = ""


class Offer(BaseModel):
    """A single Shark's investment evaluation of a pitch.

    Extended in Release 0.5 (`docs/release_backlog.md` -> Release 0.5,
    "Real `SharkAgent.evaluate_pitch()`") to carry a real, structured
    evaluation rather than just a final negotiated number:
    `interested`, `rationale`, and `confidence` are new;
    `amount`/`equity_pct` became optional because a Shark can decline
    to invest, in which case neither is meaningful.

    `confidence` is the Shark's own self-reported confidence in this
    evaluation (0.0-1.0), not a measured probability of anything --
    Release 0.5 has no calibration or verification of it. A
    `confidence` of exactly `0.0` is reserved for the deterministic
    fallback path (`SharkAgent.fallback_offer()`) used when the
    provider is unavailable or fails -- see that method's docstring.

    `status` remains `DealStatus.PENDING` for every `Offer` Release 0.5
    produces; real negotiation (multiple rounds, counter-offers,
    acceptance) is Release 0.6 scope, not this one.
    """

    shark_id: str
    pitch_id: str
    interested: bool
    amount: float | None = None
    equity_pct: float | None = None
    conditions: str | None = None
    rationale: str
    confidence: float = 0.5
    status: DealStatus = DealStatus.PENDING
    created_at: datetime = Field(default_factory=_utc_now)


class NegotiationSession(BaseModel):
    """Represents a full negotiation session for a single pitch."""

    id: str
    pitch: Pitch
    offers: list[Offer] = Field(default_factory=list)
    final_status: DealStatus = DealStatus.PENDING
    started_at: datetime = Field(default_factory=_utc_now)
    ended_at: datetime | None = None


class ConversationMessage(BaseModel):
    """A single turn in a session's conversation history.

    Introduced in Release 0.4 to replace the ad-hoc
    `{"speaker": ..., "timestamp": ..., "message": ...}` dict
    `ui/conversation.py` used before this release, per
    `docs/coding_standards.md` -> *Typing* ("prefer concrete types from
    `models/` over `dict`/`Any` wherever a pydantic model already
    exists for that shape") and this release's own spec section 10
    ("Do not use unstructured dictionaries when the architecture calls
    for typed models").

    `created_at` uses local, timezone-naive time (`datetime.now`), not
    UTC like the other timestamps in this file (`_utc_now()`), because
    it exists purely for the conversation panel's timestamp display
    (`ui/conversation.py`), not for cross-system record-keeping.
    """

    id: str
    speaker: SpeakerRole
    content: str
    turn_index: int
    created_at: datetime = Field(default_factory=datetime.now)
    requires_response: bool = False


class TurnState(BaseModel):
    """A read-only, typed snapshot of whose turn it currently is.

    `orchestrator/turn_controller.py`'s `TurnController` owns the
    actual sequencing logic; this model is a projection of its state
    for anything that wants to inspect it without depending on the
    `orchestrator` package directly (tests, future Developer Mode
    diagnostics -- see `docs/architecture.md` -> *Progressive
    Disclosure*).
    """

    phase: SessionPhase
    current_speaker: SpeakerRole | None = None
    awaiting_founder_response: bool = False


# ---------------------------------------------------------------------
# Release 0.6: Market Reality Research
# ---------------------------------------------------------------------


class ResearchSource(BaseModel):
    """Provenance for a single piece of external evidence.

    `docs/architecture.md` -> Market Reality Research and this
    release's spec Part C §7 both require every material research
    claim to retain provenance -- this model is that record. Never
    constructed with a fabricated `url`; `reliability` defaults to the
    most conservative value on purpose.
    """

    title: str
    url: str
    source_type: str = ""
    published_date: str | None = None
    retrieved_at: datetime = Field(default_factory=_utc_now)
    relevant_fact: str = ""
    reliability: str = "unverified"  # "high" | "medium" | "low" | "unverified"


class ClaimAssessment(BaseModel):
    """A single founder claim, compared against external evidence.

    Distinguishes what the founder said from what was found
    externally, per spec Part C §4 -- `assessment` should read as an
    analyst's characterization (e.g. "Partially supported", "Aggressive
    assumption"), never as a flat true/false verdict, since the
    underlying evidence itself may be incomplete or contested.
    """

    claim: str
    external_evidence: str
    assessment: str


class ValuationEstimate(BaseModel):
    """A market-informed valuation range, or an explicit admission that
    none is defensible.

    `confidence == "insufficient_evidence"` is the required outcome
    (spec Part C §10) when the available evidence doesn't support a
    range -- `low`/`high` must stay `None` in that case rather than
    being filled with an invented number. This is enforced by
    `agents/market_research_agent.py`, not by validation on this model
    itself (a plain data container, like `Offer`).
    """

    methodology: str = ""
    low: float | None = None
    high: float | None = None
    assumptions: str = ""
    confidence: str = "insufficient_evidence"  # "high" | "medium" | "low" | "insufficient_evidence"


class MarketRealityBrief(BaseModel):
    """Structured output of the Market Reality Research stage
    (`agents/market_research_agent.py`), attached to a session between
    `VALIDATION` and `QUESTION_ROUND` (`docs/state_machines.md`).

    Deliberately bounded to the fields spec Part C §15 asks for, not
    an exhaustive schema -- `docs/coding_standards.md`'s "no sprawling
    schema" principle applies here as much as it did to `Offer` in
    Release 0.5. `is_fallback=True` marks a brief produced by
    `MarketResearchAgent.fallback_brief()` (no provider, a failed
    request, or an unparseable response) rather than real research;
    every field on a fallback brief stays empty/insufficient rather
    than fabricated.
    """

    pitch_id: str
    industry: str = ""
    business_model: str = ""
    market_summary: str = ""
    market_size_estimate: str = ""
    market_growth: str = ""
    competitors: list[str] = Field(default_factory=list)
    financial_benchmarks: str = ""
    relevant_transactions: str = ""
    valuation: ValuationEstimate = Field(default_factory=ValuationEstimate)
    founder_implied_valuation: float | None = None
    valuation_comparison: str = ""
    validated_claims: list[ClaimAssessment] = Field(default_factory=list)
    unsupported_claims: list[ClaimAssessment] = Field(default_factory=list)
    material_discrepancies: list[str] = Field(default_factory=list)
    research_limitations: str = ""
    sources: list[ResearchSource] = Field(default_factory=list)
    is_fallback: bool = False
    created_at: datetime = Field(default_factory=_utc_now)


class ProposalValidationResult(BaseModel):
    """Structured output of the Moderator's validate-and-extract step
    (`agents/moderator_agent.py::ModeratorAgent.validate_and_extract()`),
    per Release 0.6 spec Part D.

    A valid early-stage business does not need revenue, customers,
    profitability, or complete financials -- `missing_information` is
    informational only, never itself a reason `accepted` is `False`.
    """

    accepted: bool
    reason: str = ""
    founder_name: str = "Founder"
    company_name: str = "The Company"
    description: str = ""
    ask_amount: float | None = None
    equity_offered_pct: float | None = None
    valuation: float | None = None
    missing_information: list[str] = Field(default_factory=list)


class NegotiationResponse(BaseModel):
    """A single Shark's response to one founder counter-offer, during
    the `NEGOTIATION` phase (spec Part J). Exactly one per Shark whose
    initial `Offer.interested` was `True` -- Sharks who declined during
    `INVESTMENT_DECISION` are never negotiated with.
    """

    shark_id: str
    pitch_id: str
    decision: str  # "accepted" | "rejected" | "modified"
    amount: float | None = None
    equity_pct: float | None = None
    conditions: str | None = None
    rationale: str
    created_at: datetime = Field(default_factory=_utc_now)
