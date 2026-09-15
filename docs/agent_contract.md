# Agent Contract

**Status: Partially implemented today.** `agents/base_agent.py`
defines `BaseAgent`, and `agents/shark_agent.py`'s `SharkAgent` is a
real implementation as of Release 0.5 (see *Error Handling* below for
where its failure-handling deliberately reinterprets this document's
original wording); `agents/market_research_agent.py`'s
`MarketResearchAgent` (Release 0.6), `agents/verification_agent.py`'s
`VerificationAgent` (Release 0.7), `agents/financial_analyst.py`'s
`FinancialAnalyst` (Release 0.8), and `agents/founder_feedback_agent.py`'s
`FounderFeedbackAgent` (Release 0.9) all follow the same real/fallback
pattern without being a `BaseAgent` subclass either, for the same
reason `ModeratorAgent` isn't — none of the five evaluates a pitch and
produces an `Offer`; they produce a `MarketRealityBrief`,
`VerificationResult`, `FinancialAnalysisResult`, `FounderFeedbackReport`,
and (for `ModeratorAgent`) narration/validation respectively.
`orchestrator/consensus_engine.py`'s `ConsensusEngine` (Release 0.7)
is not an agent at all in this document's sense — it has no investment
philosophy, never evaluates a pitch, and only reconciles
already-produced structured output, so it deliberately lives in
`orchestrator/`, not `agents/` (see `docs/architecture.md` -> Consensus
Engine). Everything else in this document — Skills, Tool Access,
Memory Access, and Message Publishing/Subscription — is still planned
and must be added when a future release builds it out. This document
is the contract every current and future agent (Shark Agents,
Moderator, Market Research, Verification, Financial Analyst, Founder
Feedback) must satisfy.

## Responsibilities

An agent is responsible for exactly one bounded task within a
session: evaluating a proposal, asking a question, verifying a
deliberation, and so on. An agent must not:

- Decide when it runs — that is the Session Director's responsibility
  (see `architecture.md`).
- Talk to the frontend directly — an agent communicates only through
  its outputs and, once implemented, published events.
- Hold session-wide state — an agent receives what it needs as input
  and returns a result; persistent state belongs in `memory/`.

## Lifecycle

Every agent's execution follows the Agent Orchestration State Machine
defined in [`state_machines.md`](state_machines.md):

```
Waiting -> Task Assigned -> Running -> ... -> Completed | Failed
```

**Implemented today:** `BaseAgent.__init__(persona, provider)` accepts
an optional `SharkPersona` and an optional `BaseProvider`. The
abstract method `evaluate_pitch(pitch, context)` corresponds to the
`Task Assigned -> Running -> Completed | Failed` portion of the
lifecycle for a Shark Agent specifically.

**Planned:** an explicit lifecycle state should be tracked per agent
task instance (not just implied by whether a method call has
returned), so the Session Director can observe an agent as `Running`
or `Waiting for User` rather than only finding out via a blocking
function return.

## Inputs

Every agent method that performs work must accept:

- The domain object it is acting on (e.g., a `Pitch` for
  `evaluate_pitch`). Domain objects come from `models/schemas.py` —
  an agent must never accept or return an ad-hoc dict where a
  pydantic model already exists for that shape.
- An optional `context: dict` for anything that doesn't yet warrant
  its own typed model (already present in `BaseAgent.evaluate_pitch`'s
  signature). As context needs stabilize, promote frequently-used
  context keys into a proper model in `models/schemas.py` rather than
  leaving them as untyped dict entries indefinitely.

## Outputs

Every agent method must return a typed domain object — never a raw
string, dict, or provider response object. `SharkAgent.evaluate_pitch`
returns an `Offer` (`models/schemas.py`). As of Release 0.7,
`VerificationAgent.verify()` returns `models.schemas.VerificationResult`
and `ConsensusEngine.reconcile()` returns `models.schemas.ConsensusResult`
— both added to `models/schemas.py` alongside the existing domain
models, following this same rule. As of Release 0.9,
`FounderFeedbackAgent.generate()` returns
`models.schemas.FounderFeedbackReport`, following the same rule —
never an `Offer` or a recommendation of any kind, since it makes no
investment decision.

## Error Handling

**Implemented as of Release 0.5, with one deliberate reinterpretation
of this section's original wording — see the note below.**

- Recoverable failures (a malformed provider response, a transient
  provider timeout) must never be allowed to raise an uncaught
  exception into the Session Director unhandled. **As implemented**,
  `SharkAgent.ask_question()`/`evaluate_pitch()`/`deliberate()`
  themselves *raise* a specific `providers.exceptions.ProviderError`
  on any such failure, rather than catching it internally as this
  section originally specified — `orchestrator/orchestrator.py`'s
  Session Director is the layer that actually catches it, at each
  call site, and substitutes that Shark's own `fallback_question()` /
  `fallback_offer()` / `fallback_deliberation()`. This still satisfies
  the underlying requirement (no uncaught exception ever reaches the
  founder or crashes the session), but puts the *decision* of how to
  degrade at the orchestration layer instead of inside the agent —
  chosen because the Session Director is what already owns "what
  happens next," and because it makes each Shark's fallback behavior
  visible and testable independently of when it's invoked (see
  `agents/shark_agent.py`'s module docstring).
- Unrecoverable failures (missing required configuration, a
  programming error) raise a specific exception type, never a bare
  `Exception` — implemented via `providers.exceptions
  .ProviderNotConfiguredError` and Python's own built-in exceptions for
  genuine programming errors.
- Every agent failure is observable: `orchestrator/orchestrator.py`
  logs a warning via `config.logging_config.get_logger(__name__)` for
  every caught `ProviderError`/`ResearchProviderError`, naming the
  Shark/component and the exception type (never the failed message
  content or any credentials). As of Release 0.6, some failures are
  also published as typed events for observability
  (`MarketResearchFailed` — see `event_catalog.md`), but there is
  still no generic "agent task failed" event covering every failure
  mode uniformly; that remains planned.

## Confidence Scores

**Implemented for `Offer` as of Release 0.5; still planned for other
agents.** `Offer.confidence: float` (0.0-1.0, `models/schemas.py`) is
now a real field: `SharkAgent.evaluate_pitch()` sets it from the
model's own self-reported confidence (floored just above 0.0 so a real
evaluation is never confused with `fallback_offer()`'s reserved
`confidence=0.0`, which means "no real evaluation happened," not "very
low confidence"). It is not calibrated or verified against anything —
`docs/agent_personas.md` §11's specific confidence-threshold formulas
remain unimplemented (see that document's §5.1). As of Release 0.7,
`VerificationResult.overall_confidence` and `ConsensusResult.confidence`
(`models/schemas.py`) carry the same kind of field, populated the same
way -- the model's own self-reported number, with no calibration or
verification against it either, consistent with `Offer.confidence`'s
existing behavior.

## Skills

**Planned. No skill system exists today.** A skill is a named,
bounded capability with a defined input shape, output shape, and
failure mode — distinct from an unstructured call to
`BaseProvider.generate()`. For example, `valuation_estimation` or
`risk_flagging` would be skills, not raw prompts.

When implemented:

- An agent declares the skills it uses (e.g., as a class attribute or
  constructor argument), rather than a skill being implicitly
  whatever the current prompt happens to ask for.
- A skill's prompt template lives in `prompts/`, loaded via
  `prompts.loader.load_prompt()`, exactly like any other prompt — a
  skill is a structured wrapper around a prompt plus its
  input/output validation, not a new prompt-storage mechanism.
- A skill must be independently testable without needing a full agent
  or session to exercise it.

## Tool Access

**Planned. No tool-calling mechanism exists today.** Once MCP is
integrated (`architecture.md` -> *MCP*), tool access must be requested
by an agent as a named capability (e.g., "I need market data lookup"),
resolved by the provider/runtime layer, not hardcoded per agent as a
specific MCP server address. An agent's declared tool needs should be
inspectable independently of running it, the same way its skills are.

## Memory Access

**Planned. Interfaces exist; no agent uses them yet.** When
implemented, an agent that needs to read or write persistent state
must do so exclusively through a `BaseMemory` instance
(`memory/base_memory.py`) passed to it — never by importing a
concrete backend (e.g., `InMemoryStore`) directly, and never by
holding its own separate copy of state. This mirrors how agents must
depend on `BaseProvider`, not a concrete provider class
(`architecture.md` -> *LLM Provider Layer*).

## Message Publishing

**Planned. No Event Bus exists today.** Once the Event Bus is
implemented (`event_catalog.md`), every agent's publisher
responsibilities are exactly the entries in that catalog where the
agent is listed as **Publisher** — for example, the Moderator Agent
publishes `QuestionAsked`; the Verification Agent publishes
`VerificationFailed`. An agent must never publish an event it is not
listed as the publisher for in `event_catalog.md`; if a new event is
needed, the catalog is updated first.

## Message Subscription

**Planned. No Event Bus exists today.** Symmetrically, an agent
subscribes only to the events `event_catalog.md` lists it as a
**Subscriber** for. An agent reacting to an event it isn't listed
against is a signal that either the agent's design or the catalog is
out of date — resolve the mismatch by updating whichever one is wrong,
not by quietly wiring up an unlisted subscription.

---

## Summary Checklist for a New Agent

When implementing any new agent (Verification Agent, Moderator Agent,
or beyond), it must:

1. Subclass `BaseAgent` (or its future equivalent) from `agents/`.
2. Accept typed domain objects as input; return a typed domain object
   as output — add new models to `models/schemas.py` as needed.
3. Track its lifecycle per the Agent Orchestration State Machine in
   `state_machines.md`.
4. Handle recoverable errors internally; raise specific exception
   types for unrecoverable ones.
5. Attach a `confidence` score to any judgment-based output.
6. Declare its skills explicitly, backed by `prompts/` templates.
7. Request tool access by capability, not by hardcoded provider.
8. Access persistent state only through an injected `BaseMemory`.
9. Publish and subscribe only to events it is listed against in
   `event_catalog.md`.
