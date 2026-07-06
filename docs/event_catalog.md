# Event Catalog

**Status: Fully planned. No Event Bus implementation exists in the
codebase today.** This document defines the complete message
vocabulary that any future Event Bus implementation must satisfy. It
exists so that when the Event Bus is built, every publisher and
subscriber it needs to support is already agreed upon — the
implementation should conform to this catalog, not invent its own
event names or shapes.

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
| **Payload** | `proposal_type: str` (`"Text"` \| `"PDF"` \| `"Audio"` \| `"Video"`), `content_reference: str` (raw text or filename) |
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
| **Description** | Fires when Internal Deliberation concludes and the session is ready to move to Verification. |

### `VerificationStarted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Verification Agent, Frontend |
| **Payload** | *(none beyond the universal fields)* |
| **Description** | Fires when the Verification Agent begins checking the deliberation's outputs for consistency. |

### `VerificationFailed`

| | |
|---|---|
| **Publisher** | Verification Agent |
| **Subscribers** | Session Director, Frontend |
| **Payload** | `reason: str`, `retry_count: int` |
| **Description** | Fires when verification finds an inconsistency. Per `state_machines.md`, this returns the session to Internal Deliberation rather than failing the session, up to a bounded retry count. |

### `ConsensusStarted`

| | |
|---|---|
| **Publisher** | Session Director |
| **Subscribers** | Consensus Engine, Frontend |
| **Payload** | *(none beyond the universal fields)* |
| **Description** | Fires once verification passes and the Consensus Engine begins aggregating the Shark Agents' individual positions. |

### `ConsensusReached`

| | |
|---|---|
| **Publisher** | Consensus Engine |
| **Subscribers** | Session Director, Frontend |
| **Payload** | `outcome_summary: str` |
| **Description** | Fires when the Consensus Engine has produced a single aggregated outcome from all Shark Agents' positions. Triggers the transition to Investment Decision. |

### `InvestmentDecisionMade`

| | |
|---|---|
| **Publisher** | Consensus Engine |
| **Subscribers** | Frontend, Memory |
| **Payload** | `deal_status: str` (a `DealStatus` value), `amount: float` (present when an offer was made), `equity_pct: float` (present when an offer was made), `conditions: str` (optional) |
| **Description** | Fires exactly once per session — the final decision delivered to the founder. Corresponds to `models.schemas.Offer` and `DealStatus`. Triggers the transition to Session Complete. |

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
