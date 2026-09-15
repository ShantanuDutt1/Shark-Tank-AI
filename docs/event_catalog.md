# Event Catalog

**Status: A minimal synchronous implementation of the Event Bus
mechanism shipped in Release 0.4** (`orchestrator/event_bus.py`,
`orchestrator/events.py`), covering every message defined below as a
typed dataclass and published by the Session Director
(`orchestrator/orchestrator.py`) at the points documented per-event.
This document remains the source of truth for the vocabulary —
`orchestrator/events.py` is a direct transcription of it, not an
independent design.

Every event name is written in the past tense (something that
*happened*), except for two explicit request/approval pairs
(`InterruptRequested` / `InterruptApproved`) which represent a request
still awaiting a decision.

## Conventions

- **Publisher** — the single component responsible for emitting this
  event. Only one publisher per event.
- **Subscribers** — every component expected to react to this event.
  A component not listed here should not react to it; if it needs to,
  this catalog must be updated first.
- **Payload** — the fields carried by the event. All payloads include
  an implicit `session_id: str` and `emitted_at: datetime` in addition
  to the fields listed; those two are omitted from each table below
  for brevity since they're universal.
- **Description** — what the event means and when it fires.

---

### `ProposalUploaded`

| | |
|---|---|
| **Publisher** | Frontend (`ui/proposal.py`, via the future Event Bus bridge) |
| **Subscribers** | Session Director |
| **Payload** | `proposal_type: str` (`"Text"` \| `"PDF"`), `content_reference: str` (raw text or filename) |
| **Description** | Fires when the founder has provided proposal content and it has been detected as present (today, this maps to `st.session_state.proposal_uploaded` becoming `True`). Does not imply the proposal has been validated. |

### `ProposalValidated`

| | |
|---|---|
| **Publisher** | Session Director (after Validation phase) |
| **Subscribers** | Moderator Agent, Frontend |
| **Payload** | `summary: str` |
| **Description** | Fires when the Validation phase determines the proposal is well-formed and answerable. Triggers the transition to Question Round. |

### `ProposalRejected`

| | |
|---|---|
| **Publisher** | Session Director (after Validation phase) |
| **Subscribers** | Moderator Agent, Frontend |
| **Payload** | `reason: str` |
| **Description** | Fires when the Validation phase determines the proposal cannot proceed (e.g., missing essential information). Triggers a return to Idle rather than advancing. |

### `SessionStarted`

| | |
|---|---|
| **Publisher** | Frontend (`ui/controls.py`, via the future Event Bus bridge) |
| **Subscribers** | Session Director |
| **Payload** | *(none beyond the universal fields)* |
| **Description** | Fires when the founder clicks "Start Session" with a proposal already present. Today this is implemented as a direct `st.session_state` mutation in `ui/controls.py`; the Event Bus bridge will replace that mutation with publishing this event instead. |

### `QuestionAsked`

| | |
|---|---|
| **Publisher** | Moderator Agent |
| **Subscribers** | Frontend, Memory |
| **Payload** | `speaker: str` (a `SpeakerRole` value), `question: str` |
| **Description** | Fires each time a committee member (relayed through the Moderator) asks the founder a question during Question Round. The frontend appends it to the conversation history. |

### `ResponseReceived`

| | |
|---|---|
| **Publisher** | Frontend (`ui/response.py`, via the future Event Bus bridge) |
| **Subscribers** | Session Director, Moderator Agent, Memory |
| **Payload** | `response_text: str` |
| **Description** | Fires when the founder submits a response via the single response control. Today, submission appends directly to `st.session_state.conversation_history` (`ui/response.py`); the Event Bus bridge will replace that append with publishing this event, with the frontend subscribing to its own downstream effect (or the append happening as a reaction to this event, depending on how the bridge is implemented). |

### `InterruptRequested`

| | |
|---|---|
| **Publisher** | Frontend |
| **Subscribers** | Session Director |
| **Payload** | `reason: str` (optional, may be empty) |
| **Description** | Fires when the founder requests to interrupt an in-progress phase (for example, to add a clarification during Internal Deliberation, where they are otherwise absent). Not yet exposed anywhere in the current UI. |

### `InterruptApproved`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Moderator Agent |
| **Payload** | `granted: bool`, `reason: str` (present when `granted` is `False`) |
| **Description** | Fires in response to `InterruptRequested`, indicating whether the interruption is allowed at this point in the session. |

### `DebateStarted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Shark Agents, Moderator Agent, Frontend |
| **Payload** | *(none beyond the universal fields)* |
| **Description** | Fires when Internal Deliberation begins — the committee discusses without the founder present. Triggers each Shark Agent's Agent Orchestration State Machine into the `Debating` state. |

### `DebateFinished`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `summary: str` |
| **Description** | Fires when Internal Deliberation concludes and the session is ready to move to Advanced Financial Analysis (Release 0.8) / Verification. |

### `AdvancedAnalysisStarted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend |
| **Payload** | *(none beyond the universal fields)* |
| **Description** | Added in Release 0.8. Fires when Advanced Financial Analysis begins, after Internal Deliberation and before Verification. |

### `AdvancedAnalysisCompleted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `summary: str` (a short factual one-liner — business model, fact/finding/risk/upside counts; never the full `FinancialAnalysisResult`) |
| **Description** | Added in Release 0.8. Fires once `agents.financial_analyst.FinancialAnalyst.analyze()` produces a real `FinancialAnalysisResult` (`analysis_status="completed"`). Triggers the transition to Verification. |

### `AdvancedAnalysisFailed`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `reason: str` (the failing exception's type name) |
| **Description** | Added in Release 0.8. Fires instead of `AdvancedAnalysisCompleted` when the financial analysis could not be completed (unconfigured provider, request failure, unparseable response) — the session still proceeds to Verification with `FinancialAnalyst.fallback_result()` (`analysis_status="unavailable"`), never a silently-skipped step. |

### `VerificationStarted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Verification Agent, Frontend |
| **Payload** | *(none beyond the universal fields)* |
| **Description** | Fires when the Verification Agent begins auditing the Sharks' final evaluations for evidentiary support. |

### `VerificationCompleted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `summary: str` (a short factual one-liner — overall confidence, issue count; never the full `VerificationResult`) |
| **Description** | Added in Release 0.7. Fires once `agents.verification_agent.VerificationAgent.verify()` produces a real `VerificationResult` (`verification_status="completed"`). Triggers the transition to Consensus. |

### `VerificationFailed`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `reason: str` (the failing exception's type name), `retry_count: int` (always `0` as of Release 0.7 — the bounce-back-to-Internal-Deliberation retry path in `state_machines.md` remains unimplemented; see that document's Rule 3) |
| **Description** | Fires instead of `VerificationCompleted` when verification could not be completed (unconfigured provider, request failure, unparseable response) — the session still proceeds to Consensus with `VerificationAgent.fallback_result()` (`verification_status="unavailable"`), never a silently-passing placeholder. |

### `ConsensusStarted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Consensus Engine, Frontend |
| **Payload** | *(none beyond the universal fields)* |
| **Description** | Fires once Verification completes (or fails) and the Consensus Engine begins reconciling the Shark Agents' individual positions and the Verification findings. |

### `ConsensusReached`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `outcome_summary: str` (a short factual one-liner — recommendation and confidence; never the full `ConsensusResult`) |
| **Description** | Fires once `orchestrator.consensus_engine.ConsensusEngine.reconcile()` produces a real `ConsensusResult` (Release 0.7). Triggers the transition to Investment Decision. |

### `ConsensusFailed`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `reason: str` (the failing exception's type name) |
| **Description** | Added in Release 0.7. Fires instead of `ConsensusReached` when consensus could not be reached (unconfigured provider, request failure, unparseable response) — `ConsensusResult.recommendation="unavailable"` in this case, never silently treated as `"do_not_invest"` or `"insufficient_evidence"` (both genuine conclusions a *completed* Consensus run can reach). |

### `InvestmentDecisionMade`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `deal_status: str` (a `DealStatus` value, derived from `ConsensusResult.recommendation` as of Release 0.7 — see `orchestrator/orchestrator.py::_deal_status_from_recommendation()`), `amount`/`equity_pct` (unused — see `SharkOfferMade` below), `conditions: str` (the Consensus Engine's stated conditions, its decision rationale, or an honest note that consensus was unavailable) |
| **Description** | Fires exactly once per session, when the `INVESTMENT_DECISION` phase begins. Each Shark's own real, independent offer is still announced individually (see `SharkOfferMade`) — this event's payload now reflects the real, formal committee recommendation (Release 0.7's Consensus Engine) rather than a fixed placeholder (Release 0.4-0.6.1). Triggers the transition to Negotiation (or Session Complete, if no Shark made an offer). |

### `FounderReportStarted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | *(none beyond the universal `session_id`/`emitted_at`)* |
| **Description** | Added in Release 0.9. Fires once, as the first step of `SharkTankOrchestrator._complete_session()` — after Negotiation concludes (or immediately, if no Shark made an offer) and before the session's closing message and `SESSION_COMPLETE`. Deliberately not tied to its own `SessionPhase`: report generation is a finalization step, not a stage the founder actively waits through turn-by-turn — see `docs/architecture.md` → *Founder Feedback Report* and `docs/state_machines.md` § Rule 6. |

### `FounderReportCompleted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `summary: str` (a short, factual one-line summary of the real `FounderFeedbackReport` — counts of strengths/needs-work/critical issues/action items — never the full structured report or any internal reasoning) |
| **Description** | Added in Release 0.9. Fires once `agents.founder_feedback_agent.FounderFeedbackAgent.generate()` produces a real `FounderFeedbackReport` (`report_status="completed"`). The full report is available via `SharkTankOrchestrator.founder_report`, not this event's payload. |

### `FounderReportFailed`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `reason: str` (the failing exception's type name) |
| **Description** | Added in Release 0.9. Fires instead of `FounderReportCompleted` when the report could not be generated (unconfigured provider, request failure, unparseable response) — the session still completes normally with `FounderFeedbackAgent.fallback_result()` (`report_status="unavailable"`), never a silently fabricated report and never confused with a genuine simulation outcome like a Shark rejection. |

### `PiiSanitized`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend (diagnostic only) |
| **Payload** | `redactions_applied: bool` |
| **Description** | Added in Release 0.6. Fires once, immediately after `SessionStarted`, right after `utils.pii.anonymize_pii()` has redacted the raw proposal — before Validation or anything else sees it. |

### `ProposalExtracted`

| | |
|---|---|
| **Publisher** | Session Director (via `ModeratorAgent.validate_and_extract()`) |
| **Subscribers** | Frontend, Memory |
| **Payload** | `founder_name: str`, `company_name: str`, `ask_amount: float` (optional), `equity_offered_pct: float` (optional) |
| **Description** | Added in Release 0.6. Fires once per accepted proposal, immediately after `ProposalValidated`, once the Moderator's real LLM call (or its deterministic fallback) has extracted whatever structured fields are present. |

### `MarketResearchStarted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend |
| **Payload** | *(none beyond the universal fields)* |
| **Description** | Added in Release 0.6. Fires when the `MARKET_RESEARCH` phase begins, right after an accepted proposal. |

### `MarketResearchCompleted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `summary: str` (a short factual one-liner — industry, valuation confidence, source count; never the full brief) |
| **Description** | Added in Release 0.6. Fires once Market Reality Research has produced a `MarketRealityBrief` (real or, on failure, `MarketResearchAgent.fallback_brief()` — see `MarketResearchFailed` below). Triggers the transition to Question Round. |

### `MarketResearchFailed`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend (diagnostic only) |
| **Payload** | `reason: str` (the failing exception's type name) |
| **Description** | Added in Release 0.6. Fires instead of blocking the session when research could not be completed (unconfigured provider, request failure, unparseable response) — `MarketResearchCompleted` still fires immediately after, with the fallback brief's summary. |

### `SharkOfferMade`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `speaker: SpeakerRole`, `interested: bool`, `amount: float` (optional), `equity_pct: float` (optional), `evaluation_available: bool` (Release 0.6.1, default `True`) |
| **Description** | Added in Release 0.6. Fires once per Shark during `INVESTMENT_DECISION`, immediately after that Shark's real offer (or decline) has been announced in the conversation. `evaluation_available=False` (Release 0.6.1) means this Shark's evaluation failed technically (a provider failure) -- `interested` is `False` in that case too, but a subscriber must check `evaluation_available` first: a technical failure must never be treated as a genuine decline (see `docs/architecture.md` -> Security / Failure Semantics). |

### `NegotiationStarted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend |
| **Payload** | *(none beyond the universal fields)* |
| **Description** | Added in Release 0.6. Fires once, when at least one Shark made an offer and the `NEGOTIATION` phase begins. Never fires if every Shark declined (the session goes straight to Session Complete instead). |

### `FounderCounterOffered`

| | |
|---|---|
| **Publisher** | Frontend, relayed by the Session Director |
| **Subscribers** | Session Director, Memory |
| **Payload** | `speaker: SpeakerRole` (which Shark this counter targets), `counter_text: str` |
| **Description** | Added in Release 0.6. Fires once per founder counter-offer submitted during Negotiation. |

### `SharkNegotiationResponded`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Frontend, Memory |
| **Payload** | `speaker: SpeakerRole`, `decision: str` (`"accepted"` \| `"rejected"` \| `"modified"` \| `"unavailable"` (Release 0.6.1)) |
| **Description** | Added in Release 0.6. Fires once per Shark's response to a founder counter-offer. When every interested Shark has responded once, the session transitions to Session Complete. `decision="unavailable"` (Release 0.6.1) means the Shark's `negotiate()` call failed technically -- distinct from a genuine `"rejected"` outcome; see `agents.shark_agent.SharkAgent.fallback_negotiation_response()`. |

### `SessionEnded`

| | |
|---|---|
| **Publisher** | Frontend (`ui/controls.py`, via the future Event Bus bridge) |
| **Subscribers** | Session Director, Memory |
| **Payload** | `reason: str` (`"completed"` \| `"reset"`) |
| **Description** | Fires both when a session concludes naturally (after `InvestmentDecisionMade`) and when the founder clicks "End Session" to reset early. Today, "End Session" is implemented as a direct call to `reset_session_state()` in `ui/controls.py`; the Event Bus bridge will replace that direct reset with publishing this event and reacting to it. |

### `MemorySaved`

| | |
|---|---|
| **Publisher** | Memory (whichever `BaseMemory` implementation is active) |
| **Subscribers** | Frontend (for diagnostic/Developer Mode display only) |
| **Payload** | `key: str` |
| **Description** | Fires after any successful write to the active memory backend. Intended primarily for Developer Mode diagnostics (see `architecture.md` → *Progressive Disclosure*), not for driving session logic. |

---

## Notes for Implementation

1. **One publisher per event, always.** If a future change would
   require two components to publish the same event name, that is a
   sign the event needs to be split into two distinct events instead.
2. **The Session Director is the only component permitted to advance
   `SessionPhase`.** Every event above that implies a phase
   transition does so by the Session Director reacting to it and
   updating state — no other subscriber should mutate
   `current_phase` directly, matching the rule stated in
   `state_machines.md`.
3. **Frontend subscription today is simulated by direct
   `st.session_state` access.** Every event above whose publisher or
   subscriber says "Frontend, via the future Event Bus bridge" has a
   concrete, already-implemented equivalent in `ui/` today (noted in
   each entry). Implementing the Event Bus means replacing those
   direct calls with publish/subscribe, not adding new frontend
   behavior.
