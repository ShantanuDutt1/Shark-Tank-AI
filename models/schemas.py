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

    `evaluation_available` (Release 0.6.1) is `False` only for
    `SharkAgent.fallback_offer()` -- a provider failure that prevented
    evaluation, never a genuine investment decision.
    `interested=False` alone is ambiguous between "declined" and
    "couldn't be evaluated"; any caller that renders or aggregates
    offers must check `evaluation_available` first, so a technical
    failure is never presented to the founder as a rejection.
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
    evaluation_available: bool = True


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

    `reliability` (Release 0.6.1: now actually varies, via
    `agents.market_research_agent._classify_source_reliability()`'s
    domain heuristic, instead of being hardcoded) reflects the
    *source's* documented quality tier (government/regulatory > public
    filings/financial databases > academic/industry research >
    financial publications > other), per Release 0.6 spec Part C §8.
    `retrieval_method` is a separate, orthogonal fact: this codebase
    never independently re-fetches or verifies a URL -- every source
    is exactly as the model reported it -- so `retrieval_method`
    exists to make that limitation explicit in the data itself rather
    than only in documentation.
    """

    title: str
    url: str
    source_type: str = ""
    published_date: str | None = None
    retrieved_at: datetime = Field(default_factory=_utc_now)
    relevant_fact: str = ""
    reliability: str = "unverified"  # "high" | "medium" | "low" | "unverified"
    retrieval_method: str = "model_reported"  # the only value this codebase produces today


#: Bounded set of claim-validation outcomes (Release 0.6.1, spec Part
#: C §9). Deliberately not a hard pydantic enum -- `ClaimAssessment`
#: parsing is lenient like the rest of this codebase's JSON parsing
#: (`agents/market_research_agent.py` clamps an unrecognized value to
#: `"insufficient_evidence"` rather than raising).
CLAIM_STATUSES: tuple[str, ...] = (
    "supported",
    "partially_supported",
    "unsupported",
    "contradicted",
    "insufficient_evidence",
    "not_externally_verifiable",
)


class ClaimAssessment(BaseModel):
    """A single founder claim, compared against external evidence.

    Distinguishes what the founder said from what was found
    externally, per spec Part C §4 -- `assessment` should read as an
    analyst's characterization (e.g. "Partially supported", "Aggressive
    assumption"), never as a flat true/false verdict, since the
    underlying evidence itself may be incomplete or contested.

    `status` (Release 0.6.1) is the bounded counterpart to the free-text
    `assessment`: one of `CLAIM_STATUSES`. It exists specifically so
    "no evidence was found" (`insufficient_evidence`), "evidence
    conflicts with the claim" (`contradicted`), and "evidence supports
    only part of the claim" (`partially_supported`) are distinguishable
    without parsing prose -- spec Part C §9's explicit requirement that
    absence of evidence must never be treated as proof a claim is
    false.
    """

    claim: str
    external_evidence: str
    assessment: str
    status: str = "insufficient_evidence"


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

    Release 0.6.1 additions, all optional/defaulted so nothing about
    the Release 0.6 shape changed: `research_objectives` names the
    category labels the research plan (`agents/research_planner.py`)
    attempted this session -- empty on a fully-fallback brief, since no
    plan was ever executed. `failed_objectives` names categories whose
    evidence-gathering call itself errored, distinct from a category
    that ran successfully but found nothing -- spec Part C §16:
    research failure must never be represented as negative evidence. A
    non-empty `failed_objectives` alongside `is_fallback=False` means
    this brief is *partial*, not failed; the categories not listed
    still contributed real evidence. `has_conflicting_evidence` /
    `conflicting_evidence_notes` record when retrieved sources
    materially disagreed (spec Part C §19) -- when `True`, synthesis
    must not have silently picked one source as fact.
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
    research_objectives: list[str] = Field(default_factory=list)
    failed_objectives: list[str] = Field(default_factory=list)
    has_conflicting_evidence: bool = False
    conflicting_evidence_notes: str = ""


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

    `decision == "unavailable"` (Release 0.6.1) is reserved for
    `SharkAgent.fallback_negotiation_response()`: the Shark's
    `negotiate()` call failed, so no real negotiation decision was
    made. This is deliberately distinct from `"rejected"` (a genuine
    negotiated outcome) -- a technical failure must never be rendered
    to the founder as the Shark walking away from the deal.
    """

    shark_id: str
    pitch_id: str
    decision: str  # "accepted" | "rejected" | "modified" | "unavailable"
    amount: float | None = None
    equity_pct: float | None = None
    conditions: str | None = None
    rationale: str
    created_at: datetime = Field(default_factory=_utc_now)


# ---------------------------------------------------------------------
# Release 0.6.1: Research planning
# ---------------------------------------------------------------------


class ResearchObjective(BaseModel):
    """One targeted evidence-gathering goal within a `ResearchPlan`.

    Deliberately thin, matching `RawSearchResult`'s spirit: a
    `category` label (e.g. `"market_size_growth"`, used to report
    which categories succeeded/failed on `MarketRealityBrief`) and the
    literal search `query` to run for it. Not persisted onto the
    session's `MarketRealityBrief` itself -- only the category labels
    are (`research_objectives`/`failed_objectives`), so the brief
    doesn't need to grow a nested plan object of its own.
    """

    category: str
    query: str


class ResearchPlan(BaseModel):
    """A small, pre-search plan for what to research, produced by
    `agents/research_planner.py::build_research_plan()` before any web
    search happens (Release 0.6.1 spec Parts A/4-5).

    `business_model` is one of a small, fixed set of categories (see
    `agents.research_planner.BUSINESS_MODEL_CATEGORIES`) -- a
    deterministic keyword heuristic, not an LLM classification, so
    this step never needs a provider call and stays fully testable
    offline. `is_uncertain=True` means the heuristic could not
    confidently classify the pitch; `objectives` is then the small,
    conservative generic plan (spec Part A §4: "use a conservative
    generic research plan rather than inventing classification"),
    never an invented specific one.
    """

    business_model: str
    is_uncertain: bool
    objectives: list[ResearchObjective] = Field(default_factory=list)


# ---------------------------------------------------------------------
# Release 0.7: Verification & Consensus
# ---------------------------------------------------------------------

#: Bounded severity levels for a single `VerificationFinding` -- how
#: much a given finding should weigh in the Consensus Engine's
#: reconciliation, independent of how confident the Verification Agent
#: is in the finding itself (`VerificationFinding.confidence`).
VERIFICATION_SEVERITIES: tuple[str, ...] = ("low", "medium", "high", "critical")


class VerificationFinding(BaseModel):
    """One specific audited claim or piece of reasoning, produced by
    the Verification Agent (`agents/verification_agent.py`).

    `assessment` reuses `CLAIM_STATUSES` (Release 0.6.1) rather than a
    second, near-duplicate status vocabulary -- the same supported/
    partially_supported/unsupported/contradicted/insufficient_evidence/
    not_externally_verifiable distinction applies whether the claim
    came from a web source (0.6.1) or from a Shark's own reasoning
    (0.7). Absence of evidence must never be represented as
    `contradicted` -- see `CLAIM_STATUSES`'s own docstring.
    """

    subject: str
    claim: str
    assessment: str = "insufficient_evidence"  # one of CLAIM_STATUSES
    evidence: str = ""
    severity: str = "low"  # one of VERIFICATION_SEVERITIES
    confidence: float = 0.5


class VerificationResult(BaseModel):
    """Structured output of the Verification Agent
    (`agents/verification_agent.py::VerificationAgent.verify()`),
    attached to a session during `SessionPhase.VERIFICATION`
    (`docs/state_machines.md`), per Release 0.7 spec Part 10.

    The Verification Agent audits whether the Sharks' reasoning is
    adequately supported by the proposal, founder answers, and Market
    Reality Brief -- it does NOT make an investment decision and never
    produces an `Offer`. `verification_status="unavailable"` (rather
    than an uncaught exception reaching the Session Director) marks a
    technical failure -- `VerificationAgent.fallback_result()` -- a
    genuine failure to complete verification, distinct from a
    completed verification that simply found problems (those problems
    are `unsupported_claims`/`contradictions`, not a failure; spec
    Part 24).
    """

    verification_status: str = "completed"  # "completed" | "unavailable"
    overall_confidence: float = 0.0
    verified_findings: list[VerificationFinding] = Field(default_factory=list)
    unsupported_claims: list[VerificationFinding] = Field(default_factory=list)
    contradictions: list[VerificationFinding] = Field(default_factory=list)
    financial_issues: list[VerificationFinding] = Field(default_factory=list)
    valuation_issues: list[VerificationFinding] = Field(default_factory=list)
    research_limitations: str = ""
    shark_specific_findings: dict[str, list[VerificationFinding]] = Field(default_factory=dict)
    material_risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    sources_or_evidence_references: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)


#: Bounded set of the Consensus Engine's formal recommendations
#: (Release 0.7 spec Part 13). `"unavailable"` (not in the spec's own
#: enumerated list, added per spec Part 14/24's explicit requirement
#: that "Consensus unavailable" be distinct from every genuine
#: recommendation, including `insufficient_evidence`) marks a
#: technical failure of the Consensus Engine itself -- the engine
#: never ran to completion -- as opposed to `insufficient_evidence`,
#: which means it *did* run and concluded the evidence doesn't support
#: a confident recommendation either way. Mirrors the same distinction
#: `NegotiationResponse.decision`'s `"unavailable"` value established
#: in Release 0.6.1.
CONSENSUS_RECOMMENDATIONS: tuple[str, ...] = (
    "invest",
    "invest_with_conditions",
    "do_not_invest",
    "insufficient_evidence",
    "unavailable",
)


class NumericRange(BaseModel):
    """A small, generic low/high/confidence range.

    Reused for both `ConsensusResult.recommended_investment_range`
    (dollars) and `recommended_equity_range` (percentage points) --
    Release 0.7 spec Part 13 asks for three separate ranges, but the
    valuation range reuses the existing `ValuationEstimate` (Release
    0.6) instead of a fourth near-identical type, since that model
    already carries the extra methodology/assumptions fields a
    valuation range needs (`docs/coding_standards.md` -> *Modularity*:
    reuse an existing model rather than inventing a parallel one).
    `low`/`high` stay `None`, with `confidence =
    "insufficient_evidence"`, exactly like `ValuationEstimate`, when
    the underlying evidence doesn't support a range -- never a
    fabricated number.
    """

    low: float | None = None
    high: float | None = None
    confidence: str = "insufficient_evidence"  # "high" | "medium" | "low" | "insufficient_evidence"


class ConsensusResult(BaseModel):
    """Structured output of the Consensus Engine
    (`orchestrator/consensus_engine.py::ConsensusEngine.reconcile()`),
    attached to a session during `SessionPhase.CONSENSUS`, per Release
    0.7 spec Parts 11-13.

    Reconciles the three Sharks' independent evaluations, deliberation,
    and the Verification Agent's findings into one formal
    recommendation -- explicitly NOT a majority vote (spec Part 12): a
    single Shark's well-supported concern or high-upside read can
    outweigh the other two. `recommendation="unavailable"` marks a
    technical failure (`ConsensusEngine.fallback_result()`);
    `recommendation="insufficient_evidence"` is a genuine conclusion
    the engine reached after actually running -- the two must never be
    confused (spec Part 14).
    """

    recommendation: str = "insufficient_evidence"  # one of CONSENSUS_RECOMMENDATIONS
    confidence: float = 0.0
    investment_thesis: str = ""
    key_strengths: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    material_disagreements: list[str] = Field(default_factory=list)
    verification_summary: str = ""
    valuation_assessment: str = ""
    recommended_valuation_range: ValuationEstimate = Field(default_factory=ValuationEstimate)
    recommended_investment_range: NumericRange = Field(default_factory=NumericRange)
    recommended_equity_range: NumericRange = Field(default_factory=NumericRange)
    conditions: list[str] = Field(default_factory=list)
    decision_rationale: str = ""
    evidence_limitations: str = ""
    created_at: datetime = Field(default_factory=_utc_now)

    # --- Release 0.8: business quality vs. deal quality ---
    business_quality: str = "insufficient_evidence"
    """How good the underlying business appears, independent of the
    proposed terms -- one of `QUALITY_RATINGS`. Deliberately separate
    from `deal_quality`: a strong business can still be a poor
    investment at an excessive valuation (spec Part 15)."""
    deal_quality: str = "insufficient_evidence"
    """How attractive an investment this is *at the proposed terms* --
    one of `QUALITY_RATINGS`. This, not `business_quality` alone, is
    what `recommendation` should ultimately track."""
    financial_health: str = "insufficient_evidence"
    """One of `QUALITY_RATINGS`, summarizing `FinancialAnalysisResult`
    (Release 0.8) -- margins, burn/runway, revenue quality -- at the
    level the founder-facing summary needs, not every underlying
    figure."""
    growth_profile: str = ""
    """Short free-text qualitative summary of growth potential -- not
    a bounded enum, since a defensible growth read has too many
    legitimate framings to force into a fixed vocabulary the way a
    quality rating can be."""
    risk_profile: str = ""
    """Short free-text qualitative summary of the dominant risk
    picture, synthesizing `FinancialAnalysisResult.risk_factors`."""
    scenario_summary: str = ""
    """Short free-text summary of the downside/base/upside valuation
    scenarios (`FinancialAnalysisResult.scenarios`) and what mainly
    drives the spread between them."""


# ---------------------------------------------------------------------
# Release 0.8: Advanced Financial / Commercial Analysis
# ---------------------------------------------------------------------

#: Bounded provenance categories for a single extracted financial data
#: point (Release 0.8 spec Part 6). `"missing"` is a first-class,
#: expected value -- a `FinancialFact` with `value=None,
#: provenance="missing"` is the correct, honest representation of data
#: the founder never provided, not an omitted list entry.
FINANCIAL_FACT_PROVENANCE: tuple[str, ...] = (
    "founder_stated",
    "externally_reported",
    "derived",
    "analyst_inference",
    "estimated",
    "missing",
)


class FinancialFact(BaseModel):
    """A single structured financial data point with explicit
    provenance (Release 0.8 spec Parts 5-6).

    `metric` is a short, stable identifier (e.g. `"current_revenue"`,
    `"projected_revenue_next_year"`, `"arr"`, `"gross_margin_pct"`,
    `"monthly_burn"`) rather than a dedicated model field per metric --
    this codebase's established convention for an open-ended,
    extensible set of categories (mirroring `ResearchObjective.category`,
    Release 0.6.1) rather than a sprawling fixed schema
    (`docs/coding_standards.md` -> *no sprawling schema*). Critically,
    `metric` naming keeps a founder's *projection* (e.g.
    `"projected_revenue_next_year"`) structurally distinct from
    *current* fact (`"current_revenue"`) -- spec Part 6's central
    requirement that a projection never silently becomes a historical
    fact.
    """

    metric: str
    value: float | None = None
    provenance: str = "missing"  # one of FINANCIAL_FACT_PROVENANCE
    note: str = ""


#: Bounded consistency assessments (Release 0.8 spec Part 8). Never a
#: verdict like "fraudulent" -- see that section's own instruction.
CONSISTENCY_ASSESSMENTS: tuple[str, ...] = (
    "consistent",
    "potentially_inconsistent",
    "materially_inconsistent",
    "insufficient_information",
)


class ConsistencyFinding(BaseModel):
    """One financial sanity-check result (Release 0.8 spec Part 8) --
    e.g. a stated gross margin that doesn't match revenue/COGS, or a
    runway claim inconsistent with stated cash/burn. Produced by both
    deterministic Python checks (`agents.financial_analyst
    ._run_sanity_checks()`) and the synthesis LLM's own qualitative
    reading (e.g. a founder projection quietly treated as a historical
    fact elsewhere in the same proposal) -- both populate this same
    model so callers don't need to know which produced a given
    finding.
    """

    subject: str
    assessment: str = "insufficient_information"  # one of CONSISTENCY_ASSESSMENTS
    explanation: str = ""


class RiskFactor(BaseModel):
    """One structured investment risk (Release 0.8 spec Part 17).
    `category` is intentionally free text guided by, but not hard-
    validated against, the spec's own suggested list (market /
    product_technology / financial / execution / competitive /
    regulatory / customer / capital_intensity / valuation) -- "not
    every business requires every category," and a fixed enum would
    force a category onto a risk that doesn't cleanly fit one.
    `severity` reuses `VERIFICATION_SEVERITIES` (Release 0.7) rather
    than a second severity vocabulary.
    """

    category: str
    description: str
    severity: str = "low"  # one of VERIFICATION_SEVERITIES
    evidence: str = ""
    confidence: float = 0.5
    mitigable: bool = True
    material: bool = True


#: Bounded basis categories for a single upside factor (Release 0.8
#: spec Part 18) -- keeps speculative upside explicitly distinct from
#: actual evidence, mirroring `CLAIM_STATUSES`'s founder-stated/
#: externally-reported/derived/inference distinctions from Release
#: 0.6.1.
UPSIDE_BASIS: tuple[str, ...] = ("evidence", "inference", "hypothesis")


class UpsideFactor(BaseModel):
    """One structured upside factor (Release 0.8 spec Part 18) --
    market expansion, margin expansion, defensibility, network
    effects, recurring revenue, strategic/exit value, and similar.
    `category` is free text for the same reason as `RiskFactor
    .category`. `basis` is bounded (`UPSIDE_BASIS`) specifically so
    speculative upside can never be silently presented as established
    fact."""

    category: str
    description: str
    basis: str = "hypothesis"  # one of UPSIDE_BASIS
    evidence: str = ""
    confidence: float = 0.5


#: Bounded scenario labels (Release 0.8 spec Part 12) -- analytical
#: scenarios, explicitly not forecasts (see that section).
SCENARIO_LABELS: tuple[str, ...] = ("downside", "base", "upside")

#: Bounded sources for a scenario's underlying assumption (Release 0.8
#: spec Part 12: "assumption source must be identified... must either
#: come from founder-provided projections, market evidence, or
#: explicit analyst assumptions"). `"insufficient_evidence"` is the
#: honest alternative to inventing an assumption when none of the
#: other three sources actually apply.
ASSUMPTION_SOURCES: tuple[str, ...] = (
    "founder_provided",
    "market_evidence",
    "analyst_assumption",
    "insufficient_evidence",
)


class ScenarioValuation(BaseModel):
    """One downside/base/upside valuation scenario (Release 0.8 spec
    Parts 12-13). Reuses the existing `ValuationEstimate` (Release
    0.6) for the scenario's own range/methodology/confidence rather
    than a fourth valuation-shaped model. `assumption_basis` makes
    explicit where the scenario's growth/margin assumptions actually
    came from -- never left implicit."""

    scenario: str  # one of SCENARIO_LABELS
    valuation: ValuationEstimate = Field(default_factory=ValuationEstimate)
    assumption_basis: str = "insufficient_evidence"  # one of ASSUMPTION_SOURCES
    assumptions: str = ""


#: Bounded qualitative ratings shared by `ConsensusResult.business_quality`
#: / `deal_quality` / `financial_health` (Release 0.8) -- deliberately
#: coarse (never a numeric score dressed up as precision; spec Part 33:
#: "No Fake Precision").
QUALITY_RATINGS: tuple[str, ...] = ("strong", "moderate", "weak", "insufficient_evidence")


class FinancialAnalysisResult(BaseModel):
    """Structured output of the Advanced Financial/Commercial Analysis
    step (`agents/financial_analyst.py::FinancialAnalyst.analyze()`),
    attached to a session during `SessionPhase.ADVANCED_ANALYSIS`
    (Release 0.8) -- between Internal Deliberation and Verification
    (see `docs/architecture.md` -> Advanced Financial Analysis for why
    this ordering, not the spec's own suggested Verification-then-
    Analysis order, is what data dependencies actually require:
    Verification needs the financial analysis to exist so it can audit
    it, per spec Part 20).

    Every numeric field below (`implied_post_money_valuation` through
    `ltv_to_cac`) is computed deterministically in Python
    (`utils/financial_calculations.py`) from `financial_facts`, never
    trusted from the synthesis LLM's own arithmetic -- `None` whenever
    the required inputs are missing, exactly like `MarketRealityBrief
    .founder_implied_valuation` already established in Release 0.6.1.
    `is_fallback`/`analysis_status="unavailable"` marks a result
    produced by `FinancialAnalyst.fallback_result()` (unconfigured
    provider, failed request, or unparseable response) -- every field
    on a fallback result stays empty rather than invented, matching
    every other real agent's fallback convention in this codebase.
    """

    analysis_status: str = "completed"  # "completed" | "unavailable"
    business_model: str = ""
    financial_facts: list[FinancialFact] = Field(default_factory=list)
    consistency_findings: list[ConsistencyFinding] = Field(default_factory=list)
    implied_post_money_valuation: float | None = None
    implied_pre_money_valuation: float | None = None
    revenue_multiple: float | None = None
    arr_multiple: float | None = None
    gross_margin_pct: float | None = None
    operating_margin_pct: float | None = None
    revenue_growth_pct: float | None = None
    monthly_burn: float | None = None
    runway_months: float | None = None
    dilution_pct: float | None = None
    ltv_to_cac: float | None = None
    scenarios: list[ScenarioValuation] = Field(default_factory=list)
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    upside_factors: list[UpsideFactor] = Field(default_factory=list)
    business_quality_summary: str = ""
    financial_health_summary: str = ""
    research_limitations: str = ""
    created_at: datetime = Field(default_factory=_utc_now)


# ---------------------------------------------------------------------
# Release 0.9: Founder Feedback Report
# ---------------------------------------------------------------------

#: Apparent company maturity (Release 0.9 spec Part 9) -- used to
#: calibrate what evidence the report should expect, never to penalize
#: a company for lacking metrics its actual stage wouldn't produce yet.
#: `"unclear"` is the honest alternative to guessing a stage the
#: available information doesn't actually support.
COMPANY_STAGES: tuple[str, ...] = (
    "idea",
    "pre_validation",
    "early_validation",
    "early_revenue",
    "growth",
    "later_stage",
    "unclear",
)

#: Bounded qualitative ratings for a single investor-readiness
#: dimension (Release 0.9 spec Part 8) -- deliberately a different,
#: five-value vocabulary from `QUALITY_RATINGS` (Release 0.8), per that
#: spec section's own explicit wording ("Strong / Developing / Weak /
#: Unclear / Insufficient evidence"), not a duplicate: `developing` and
#: `unclear` have no equivalent in `QUALITY_RATINGS`.
INVESTOR_READINESS_ASSESSMENTS: tuple[str, ...] = (
    "strong",
    "developing",
    "weak",
    "unclear",
    "insufficient_evidence",
)

#: Bounded action-plan priority buckets (Release 0.9 spec Part 15).
ACTION_PRIORITIES: tuple[str, ...] = ("now", "next", "later")

#: The exact disclaimer text required by Release 0.9 spec Part 18.
#: Always set literally in Python (`FounderFeedbackAgent`), never
#: generated or paraphrased by the LLM -- a founder-controlled or
#: model-generated substitute could otherwise drop or soften it.
FOUNDER_REPORT_DISCLAIMER: str = (
    "Disclaimer: This report provides AI-generated feedback and suggestions "
    "based on the information and evidence available during the simulation. "
    "It is not a prediction of investor interest or investment outcome. You "
    "decide when your proposal is ready to pitch."
)


class InvestorReadinessDimension(BaseModel):
    """One compact investor-readiness assessment (Release 0.9 spec Part
    8), e.g. "Market" -> `assessment="developing"` with a one-sentence
    `rationale`. The eleven dimensions themselves come from
    `docs/investor_evaluation_framework.md`'s research (Y Combinator,
    Techstars, Sequoia, 500 Global, a16z), not from this codebase's own
    judgment -- see that document for sources. Deliberately no numeric
    score (spec Part 33: "No Fake Precision" carried over from Release
    0.8) and no fixed set of exactly eleven -- the prompt is
    instructed to adapt which dimensions are actually discussed to the
    proposal's own stage and business model, not force all eleven onto
    every pitch."""

    dimension: str
    assessment: str = "insufficient_evidence"  # one of INVESTOR_READINESS_ASSESSMENTS
    rationale: str = ""


class ActionItem(BaseModel):
    """One concrete, prioritized recommendation (Release 0.9 spec
    Parts 15-17). Every field maps to that section's own four
    questions ("what is wrong / why does it matter / what should the
    founder do / what evidence would resolve it") rather than a single
    free-text recommendation string, so a generic "improve your
    marketing"-style non-answer has no field to hide in."""

    priority: str = "later"  # one of ACTION_PRIORITIES
    problem: str
    why_it_matters: str
    action: str
    evidence_needed: str = ""


class ReportEvidenceRef(BaseModel):
    """A single provenance pointer from a report finding back to where
    it came from in the simulation (Release 0.9 spec Part 30) --
    e.g. `subject="Market size claim"`,
    `source="market_reality_brief"`, `detail="Research found
    insufficient evidence for the founder's stated $10B figure"`.
    Deliberately not attached to every sentence in the report (spec
    Part 30: "do not needlessly expose URLs throughout the visible
    report") -- only the material findings that most need traceability
    get one."""

    subject: str
    source: str
    detail: str = ""


class FounderFeedbackReport(BaseModel):
    """Structured output of the Founder Feedback Report step
    (`agents/founder_feedback_agent.py::FounderFeedbackAgent.generate()`),
    produced once per session, after Negotiation, as the final step of
    `SharkTankOrchestrator._complete_session()` -- Release 0.9 spec
    Part 19's "background/finalization process, not another visible
    Shark turn." Not a fourth Shark, not a second Consensus Engine, and
    not a generic startup-advice generator: it synthesizes the actual
    evidence the simulation produced (see `docs/architecture.md` ->
    Founder Feedback Report for the full input list and why no new
    `SessionPhase` was added for it).

    `report_status="unavailable"` (via `FounderFeedbackAgent
    .fallback_result()`) marks a technical failure -- distinct from a
    completed report that is simply critical (spec Part 22: report-
    generation failure must never be confused with, or silently
    substituted by, fabricated feedback or a Shark-rejection-shaped
    outcome). `disclaimer` is always `FOUNDER_REPORT_DISCLAIMER`
    verbatim, set in Python, never LLM-generated.
    """

    report_status: str = "completed"  # "completed" | "unavailable"
    session_id: str
    pitch_id: str
    company_name: str = ""
    stage: str = "unclear"  # one of COMPANY_STAGES
    stage_rationale: str = ""
    business_model: str = ""
    executive_summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    needs_work: list[str] = Field(default_factory=list)
    critical_issues: list[str] = Field(default_factory=list)
    investor_readiness: list[InvestorReadinessDimension] = Field(default_factory=list)
    valuation_feedback: str = ""
    financial_feedback: str = ""
    action_plan: list[ActionItem] = Field(default_factory=list)
    evidence_references: list[ReportEvidenceRef] = Field(default_factory=list)
    limitations: str = ""
    disclaimer: str = FOUNDER_REPORT_DISCLAIMER
    generated_at: datetime = Field(default_factory=_utc_now)
