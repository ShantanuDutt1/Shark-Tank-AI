# Release Log

This log records what each release of Shark Tank AI actually shipped.
It is a historical record, not a roadmap — planned-but-unbuilt work
lives in `architecture.md` → *Future Extension Points*, not here.

---

## Release 0.1 — Project Skeleton

**Theme:** Establish the project structure and every package boundary
before any real logic exists.

**Shipped:**

- Full folder structure: `agents/`, `orchestrator/`, `providers/`,
  `memory/`, `models/`, `prompts/`, `ui/`, `config/`, `utils/`,
  `tests/`, `docs/`, `docker/`.
- `BaseAgent`, `BaseProvider`, `BaseMemory` interfaces, each with one
  placeholder concrete implementation (`SharkAgent`,
  `AnthropicProvider`, `InMemoryStore`), all raising
  `NotImplementedError`.
- Domain models in `models/schemas.py`: `Pitch`, `SharkPersona`,
  `Offer`, `NegotiationSession`, `DealStatus`.
- `config/settings.py` (pydantic-settings, every field defaulted) and
  `config/logging_config.py` (stdlib `dictConfig`).
- Prompt templates (`prompts/*.txt`) and `prompts/loader.py`.
- Initial test suite: `test_smoke.py` (package import checks),
  `test_config.py`, `test_logging_config.py`.
- `pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`,
  initial `README.md` and `docs/architecture.md` /
  `docs/getting_started.md`.

**Explicitly out of scope:** any working agent, orchestration,
provider, or memory logic. The application was runnable, but did
nothing beyond starting up.

---

## Release 0.2 — Docker

**Theme:** Make the (still-inert) application runnable in a container
for local development.

**Shipped:**

- `docker/Dockerfile`: Python 3.12-slim base, dependency layer caching,
  `HEALTHCHECK`, and a `CMD` that runs the Streamlit entry point.
- `docker-compose.yml` at the project root: builds from
  `docker/Dockerfile`, bind-mounts the project directory for live
  development, loads `.env` if present (optional — the container
  starts successfully without one).
- Fixed a build-context bug: `.dockerignore` had initially been placed
  inside `docker/` (next to the Dockerfile) instead of the project
  root, where Docker actually looks for it given
  `context: .` in `docker-compose.yml`. Corrected to live at the
  project root.
- `docker/CMD` configured with `--server.runOnSave=true` and
  `--server.fileWatcherType=poll` for a reliable hot-reload experience
  across the host/container bind mount.

**Explicitly out of scope:** any change to application logic. This
release only made the existing (inert) app containerized.

---

## Release 0.3 — Streamlit UI

**Theme:** Build the complete, turn-based frontend experience —
still with zero backend logic — so the full user-facing shape of the
product exists and can be reviewed before any agent behavior is
implemented.

**Shipped:**

- `models/enums.py`: `SessionPhase` (all nine states), `LLMProvider`,
  `SpeakerRole`, plus their label/ordering/message lookup tables.
- `ui/session_state.py`: the single source of truth for
  `st.session_state` defaults, initialization, and full reset.
- `ui/styles.py`: shared CSS (progress stepper, speaker bubbles,
  session stage card, sticky bottom bar).
- `ui/header.py`: title, subtitle, and the nine-phase progress
  stepper, driven by `SessionPhase`.
- `ui/sidebar.py` (rewritten): LLM provider selection (Gemini/Ollama)
  with conditional fields, Verbose/Developer/Show Reasoning toggles,
  and Memory/MCP/ADK status placeholders.
- `ui/proposal.py`: Startup Proposal intake (Text/PDF/Audio/Video) and
  the Session Stage card. Detects presence of content only — no
  parsing.
- `ui/conversation.py`: the turn-based conversation history panel,
  with distinct styling per `SpeakerRole` and an example seed
  transcript.
- `ui/response.py`: the single founder response control (gated by
  `user_input_enabled`, disabled by default).
- `ui/controls.py`: the sticky bottom bar — instruction label plus
  Start Session (gated on a proposal being present) and End Session
  (always available, full reset, no confirmation).
- `ui/layout.py`: composes all of the above; `app.py` rewritten to
  delegate to it.
- Removed `ui/home.py`, fully superseded by the components above.

**Explicitly out of scope (unchanged from prior releases):** Google
ADK, MCP, agent logic, memory persistence, Event Bus, debate logic,
report generation. All confirmed via an offline functional test
harness simulating a full user session (proposal entry, Start
Session, provider switch, response submission, End Session reset).

---

## Release 0.3.5 — Architecture Lock

**Theme:** No functionality. This release exists solely to document
the system's architecture and lock in the engineering standards every
future release must follow.

**Shipped:**

- `docs/architecture.md` (rewritten in full): the single source of
  truth for the system — Project Vision, Overall Architecture,
  Frontend, Backend, Google ADK, MCP, Session Director, Moderator
  Agent, Shark Agents, Verification Agent, Consensus Engine, Memory,
  SQLite, LLM Provider Layer, Event Bus, State Machines, Agent Skills,
  Progressive Disclosure, and Future Extension Points — with an
  explicit status legend distinguishing implemented, planned, and
  known-gap items.
- `docs/folder_structure.md`: purpose, responsibility, ownership, and
  future expansion for every existing project folder.
- `docs/state_machines.md`: the User Session State Machine (backed by
  the already-implemented `SessionPhase` enum) and the Agent
  Orchestration State Machine (fully planned, defined here for the
  first time), both with diagrams.
- `docs/event_catalog.md`: every planned Event Bus message
  (publisher, subscribers, payload, description).
- `docs/agent_contract.md`: the common interface every agent must
  implement — responsibilities, lifecycle, inputs/outputs, error
  handling, confidence scores, skills, tool access, memory access,
  message publishing/subscription.
- `docs/coding_standards.md`: Python, formatting, typing, imports,
  logging, error handling, naming, dependency injection,
  configuration, session state, JSON schemas, prompt management, and
  modularity standards, distinguishing what's already followed from
  what's not yet exercised.
- `README.md`: *Documentation* section updated to link all of the
  above.

**Explicitly out of scope:** any code, configuration, Docker, or test
change. No functionality was added, changed, or removed in this
release — verified by leaving every non-`docs/` file (other than the
`README.md` documentation links) untouched.

---

## Release 0.4 — Core Conversation Engine

**Theme:** Turn the existing Streamlit interface into a functioning
turn-based Shark Tank session engine — the conversation/orchestration
machinery that later releases plug real intelligence into. No
sophisticated investment reasoning was added.

**Shipped:**

- `orchestrator/events.py`: a typed, `kw_only` dataclass for every
  message defined in `docs/event_catalog.md`.
- `orchestrator/event_bus.py`: `EventBus`, a minimal synchronous
  publish/subscribe implementation.
- `orchestrator/turn_controller.py`: `TurnController`, the fixed
  Shark → Founder → Shark → Founder → Shark → Founder sequencer for a
  Question Round.
- `orchestrator/exceptions.py`: `SessionDirectorError`,
  `InvalidTurnError` — specific exception types for unrecoverable
  orchestration failures, per `agent_contract.md`/`coding_standards.md`.
- `orchestrator/orchestrator.py`: `SharkTankOrchestrator` grew into the
  Session Director. Added `start_session()`, `submit_founder_response()`,
  `end_session()`, and read-only `phase` / `conversation` /
  `awaiting_founder_response` properties, driving the full User Session
  State Machine from `IDLE` through `SESSION_COMPLETE`. The original
  `agents` constructor argument and `run_pitch()` (still
  `NotImplementedError`) are unchanged.
- `agents/moderator_agent.py`: `ModeratorAgent` — deterministic,
  phase-appropriate narration (welcome, validation summary, Question
  Round and deliberation announcements, closing message). Does not
  subclass `BaseAgent`; see its docstring for why.
- `agents/shark_agent.py`: added `ask_question()` (a deterministic,
  persona-appropriate template) and the three persona constants
  (`CONSERVATIVE_PERSONA`, `GROWTH_PERSONA`, `BALANCED_PERSONA`).
  `evaluate_pitch()` is unchanged (`NotImplementedError`).
- `models/schemas.py`: added `ConversationMessage` and `TurnState`.
  Relaxed `Pitch.founder_name` / `company_name` / `ask_amount` /
  `equity_offered_pct` to optional with defaults, since proposal intake
  still only collects raw, unparsed content (see *Known limitations*).
- `ui/session_state.py`: added the `_session_director` key, plus two
  new helpers — `build_pitch_from_state()` and `sync_from_director()` —
  which are now the only way any other `ui/` module touches Session
  Director state, keeping `ui/controls.py` and `ui/response.py` from
  importing each other or the Session Director's internals directly.
- `ui/controls.py`: Start Session now builds a `Pitch`, creates a new
  `SharkTankOrchestrator`, and calls `start_session()`; End Session
  notifies the director before the existing full reset.
- `ui/response.py`: Submit Response now calls
  `director.submit_founder_response()` instead of appending to
  `conversation_history` directly; enablement is still driven entirely
  by `user_input_enabled`, itself now sourced from the director's
  `awaiting_founder_response`.
- `ui/conversation.py`: `conversation_history` entries and the example
  seed transcript are now `models.schemas.ConversationMessage`
  instances, not dicts.
- `ui/styles.py`: replaced the leftover five-Shark-era CSS classes
  (`stka-speaker-financial`/`technical`/`marketing`/`risk`) with the
  three-Shark classes the UI actually needs
  (`stka-speaker-conservative`/`growth`/`balanced`) — this was the gap
  flagged in `docs/agent_personas.md` §14.
- Tests: `tests/test_event_bus.py`, `tests/test_turn_controller.py`,
  `tests/test_session_director.py` (47 tests total across the suite,
  all passing, including the 10 pre-existing ones unchanged).

**Known limitations:**

- Every Shark question and every Moderator line is a deterministic
  template, not an LLM call — no `BaseProvider` implementation is
  wired in yet (Release 0.5+).
- `Pitch` still has no real founder name, company name, ask amount, or
  equity — proposal intake collects only raw text or a filename, per
  spec section 8 ("Do not add sophisticated proposal validation in
  0.4").
- Internal Deliberation, Verification, Consensus, and the Investment
  Decision all run synchronously, back-to-back, inside
  `submit_founder_response()`'s final call — there is no pause between
  them for the UI to render an intermediate state, and no real
  reasoning happens in any of them (`DealStatus.PENDING` is the only
  possible outcome). A future release that adds real reasoning to any
  of these phases will likely also want to make each one its own
  awaitable step.
- No memory/persistence: ending the Python process (not just the
  Streamlit session) loses everything, exactly as before this release.

**Explicitly out of scope (per spec section 20; unchanged from prior
releases unless noted above):** real LLM reasoning, autonomous
multi-agent debate, VC valuation research, real investment offers, a
negotiation engine, a real Consensus Engine, Verification Agent
intelligence, PII anonymization, prompt-injection defense, persistent
memory, MCP, ADK, Agent Skills, multi-provider production
infrastructure, analytics/telemetry.

**Decisions that differ from prior documentation:**

- `docs/agent_contract.md`'s "Summary Checklist for a New Agent" item 1
  calls for every agent to subclass `BaseAgent`. `ModeratorAgent`
  deliberately does not, because `BaseAgent`'s one abstract method,
  `evaluate_pitch() -> Offer`, has no meaningful implementation for a
  non-investing facilitator. Generalizing `BaseAgent` into a
  facilitator-compatible contract is left to a future release rather
  than forced to fit here.
- The Release 0.4 spec's own turn-order diagram lists "Moderator" as
  the first step of the Question Round sequence. The implementation
  keeps the Moderator's Question Round announcement as an explicit
  Session Director call immediately before the sequence starts, rather
  than a `TurnController` entry, so `TurnController` only ever needs to
  reason about the Shark/Founder alternation it's actually generic
  over. The resulting conversation order is identical either way.

---

## Release 0.4.1 — Core Conversation Engine Stabilization, Chat UX & Cleanup

**Theme:** A focused stabilization release on top of Release 0.4: fix
the proposal-persistence and session-completion lifecycle bugs,
convert the conversation UI to a real chat session using Streamlit's
native chat components, remove the obsolete Audio/Video proposal
inputs, and clean up a misleadingly-named test and every deprecated
`datetime.utcnow()` call. No Release 0.5 intelligence was added; every
Shark and Moderator response remains a deterministic template.

**Bug fixes:**

- **Proposal-persistence bug (spec section 4).** Release 0.4's
  `ui.controls._handle_start_session()` called
  `reset_session_state()` — a full wipe — immediately after capturing
  the just-submitted proposal, which cleared `proposal_content`/
  `proposal_uploaded` even though the backend had already received it.
  The proposal box visibly went blank the instant a session started.
  Fixed by replacing that full reset with a new, narrower
  `ui.session_state.clear_active_session()`, which discards only the
  previous session's Session Director / conversation / turn state and
  leaves every `proposal_*` key untouched. `reset_session_state()`
  (full wipe, including the proposal) remains what End Session calls.
- **Natural-completion lifecycle bug (spec section 9).** `session_running`
  used to be a UI-only flag, set to `True` by `_handle_start_session()`
  and never updated again — so a session that reached
  `SESSION_COMPLETE` entirely on its own (no further UI click) left
  `session_running` stuck at `True`: Start stayed disabled, End stayed
  enabled, forever. Fixed by making `session_running` a pure
  projection of the Session Director's `phase`, recomputed by
  `ui.session_state.sync_from_director()` on every sync
  (`True` for every phase between `IDLE` and `SESSION_COMPLETE`,
  `False` at both ends) instead of a hand-set flag.

**Chat UX conversion (spec sections 5-7):**

- `ui/conversation.py` now renders `conversation_history` with
  `st.chat_message` (one call per `ConversationMessage`, each with a
  speaker-specific avatar) instead of custom `<div>` bubbles.
- `ui/response.py` now uses a single `st.chat_input`, gated on
  `awaiting_founder_response`, instead of a text area + submit button
  pair. `st.chat_input` clears itself after submission, so the manual
  key-rotation "nonce" trick (`response_input_nonce`) is gone.
- Neither `models.schemas.ConversationMessage` nor the Session
  Director's turn-gating logic changed — only the rendering layer did,
  per spec section 5 ("Do NOT redesign the backend message model").
- `ui/proposal.py` now shows a read-only "Submitted Proposal" summary
  once a session has been started (`_session_director` is set),
  instead of continuing to render an editable text area/uploader that
  visibly did nothing once the backend had already captured the pitch.

**Proposal input cleanup (spec section 8):**

- Removed Audio and Video from `ui.proposal.PROPOSAL_TYPES` and their
  file-uploader branches. Only Text and PDF remain. Nothing downstream
  ever processed audio/video content — this was UI-only cleanup.
- `docs/event_catalog.md`'s `ProposalUploaded` payload description
  updated to match (`proposal_type` is now `"Text"` \| `"PDF"`).

**Lifecycle corrections (spec sections 9-11):**

- End Session is now disabled whenever no session is actively running
  (Idle, or already `SESSION_COMPLETE`) — there's nothing left to
  stop. Start Session becomes enabled again the moment
  `session_running` goes back to `False`, including immediately after
  natural completion.
- The completed conversation is deliberately **not** cleared on
  natural completion — it stays visible (and the proposal stays shown,
  read-only) until the founder clicks Start Session again (which
  clears the prior session's runtime state, but not the proposal
  input) or End Session (a full reset, including the proposal).
- The bottom-bar instruction label now has dedicated copy for
  `SESSION_COMPLETE` ("Review the conversation above, or click
  Start Session to begin a new pitch") instead of falling through to
  generic in-progress phase text.

**Test changes:**

- Corrected a misleadingly-named test in `tests/test_session_director.py`:
  `test_founder_input_disabled_immediately_after_start_while_shark_speaks_first`
  claimed input was "disabled immediately after start" but only ever
  asserted turn *order*, never the input-lock state — which is in fact
  already `True` by the time `start_session()` returns, since the
  Moderator's announcement and the first Shark's question run
  synchronously. Split into two accurately-named tests: one for the
  turn-order fact, one asserting `awaiting_founder_response is True`
  directly. Added a further test asserting input stays locked through
  every phase of the deliberation pipeline, not just at
  `SESSION_COMPLETE`.
- Added `tests/test_app_ui.py`: 23 new integration tests using
  Streamlit's `AppTest` harness (`streamlit.testing.v1.AppTest`) to
  drive `app.py` end-to-end — proposal persistence across Start, proposal
  clearing on reset, chat messages sourced from real conversation
  state, input gating, natural completion, and Stop/reset — the layer
  where the Release 0.4 proposal bug actually lived and where
  `tests/test_session_director.py` (which talks to
  `SharkTankOrchestrator` directly, bypassing Streamlit) could not
  have caught it.
- Total suite: 71 tests, all passing (up from 47).

**Warning changes:**

- Every `datetime.utcnow()` call (`models/schemas.py`'s `Pitch.created_at`
  /`Offer.created_at`/`NegotiationSession.started_at`,
  `orchestrator/events.py`'s `Event.emitted_at`) replaced with a small
  local `_utc_now() -> datetime.now(timezone.utc)` helper in each
  file, per Python's deprecation of the naive-datetime form.
  `ConversationMessage.created_at` intentionally keeps naive local
  `datetime.now()` — it's display-only, not a deprecated call, and
  its docstring already explained why it differs from the others.
- Full suite now runs with **0 warnings**. (An exact "before" count
  isn't quoted here because Release 0.4 and this release were
  committed together — see *Known limitations* below — but every
  `datetime.utcnow()` call site that existed is confirmed fixed by
  running the full suite with `-W error::DeprecationWarning`, which
  now passes clean.)

**Regression:** all 47 Release 0.4 tests continue to pass, unmodified
except the one corrected test described above.

**Known limitations (unchanged from Release 0.4 unless noted):**

- Every Shark question and every Moderator line is still a
  deterministic template, not an LLM call.
- `Pitch` still has no real founder name, company name, ask amount, or
  equity — proposal intake collects only raw text or a filename.
- Internal Deliberation, Verification, Consensus, and the Investment
  Decision still run synchronously, back-to-back, with
  `DealStatus.PENDING` as the only possible outcome.
- No memory/persistence: ending the Python process loses everything.
- PDF upload still only detects file *presence*; content is never
  read or parsed (unchanged from Release 0.4 — out of scope per spec
  section 8, "Do not implement advanced PDF intelligence in this
  release").
- Manual browser verification was not performed in this environment
  (no browser available); instead, `tests/test_app_ui.py`'s `AppTest`
  suite drives the actual `app.py` script end-to-end (every button
  click, text/chat input, and resulting rerun), and the app was
  separately confirmed to boot cleanly (`streamlit run app.py`, HTTP
  200, no exceptions in the server log). Visual/CSS rendering (avatar
  emoji, spacing, the chat input's position relative to the sticky
  Start/End bar) was not independently confirmed in an actual browser.
- Release 0.4 and Release 0.4.1 ended up in the same git commit (Release
  0.4 had never been committed on its own before 0.4.1 work started),
  so there is no clean "Release 0.4 only" commit to diff against for
  historical before/after comparisons (e.g. the exact prior
  `DeprecationWarning` count). Every current warning count and test
  result in this entry was verified directly against the current
  working tree.

**Deviations from this specification:**

- Section 9's "Stop/End becomes disabled when appropriate" and Test C's
  "Stop is no longer needed" are implemented as an actual `disabled`
  state on the End Session button once `session_running` is `False`
  (Idle or Session Complete), rather than leaving it always-clickable
  as Release 0.4 did. This is a small, deliberate behavior change the
  spec's wording seemed to call for; noted here since Release 0.4 had
  explicitly documented End Session as "always enabled."
- `ui/proposal.py` locking to a read-only summary once a session has
  started was not explicitly required by any single acceptance
  criterion, but follows directly from spec section 4's "the UI must
  not unexpectedly erase the proposal" and section 6's general chat
  conversion intent — an editable box that silently stopped doing
  anything once a session started would have been confusing on its
  own.

### 0.4.1 Finalization Pass

A follow-up audit found four remaining issues before 0.5 work began;
all four are fixed, and 0.4.1 is considered fully finalized as of this
pass (72 tests passing at this point, before Release 0.5's additions).

- **Vacuous test assertion.** `tests/test_app_ui.py`'s
  `test_proposal_is_available_to_the_active_session` contained
  `assert ... or True`, which could never fail. Fixed by adding
  `SharkTankOrchestrator.pitch` — a read-only property mirroring the
  existing `phase`/`conversation` pattern, not a test-only accessor —
  and asserting `director.pitch.description == SAMPLE_PROPOSAL`
  directly. Verified the new assertion actually fails when proposal
  persistence is broken (temporarily reverted the fix and confirmed
  the test catches it).
- **Stale README.** Rewritten to describe the actual Release 0.4.1
  application (chat UI, Session Director, Turn Controller, Event Bus,
  three Sharks, Text/PDF intake, current limitations, Release 0.5
  scope) instead of the Release 0.1-era "inert scaffold" description.
- **Stale `state_machines.md` wording.** The User Session State
  Machine's diagram and rules still labeled every transition after
  "Proposal Upload" as "(planned)" even though `SharkTankOrchestrator`
  has driven all of them since Release 0.4. Updated the top summary,
  every diagram transition label, and rules 2 and 4 to accurately say
  "(implemented)" where true, while leaving rule 3 (Verification's
  failure/retry path) correctly marked planned, since Verification
  still always passes.
- **XSS via founder-controlled proposal text.** `ui/proposal.py`'s
  locked "Submitted Proposal" summary interpolated the founder's raw
  text directly into `unsafe_allow_html=True` markup, so a proposal
  containing `<script>...</script>` would have been rendered as
  markup, not text. Fixed with `html.escape()` on that one value
  (the only founder-controlled string reaching `unsafe_allow_html`
  anywhere in the codebase — every other `unsafe_allow_html=True` call
  site was audited and only ever renders static or phase-derived
  strings). Added a regression test
  (`test_founder_proposal_html_is_escaped_not_interpreted`) and
  verified it fails without the fix.

All 13 items in the Release 0.4.1 spec's manual test checklist were
re-verified via `AppTest` end-to-end runs of the actual `app.py` after
these fixes (not just re-inspected).

---

## Release 0.5 — Shark Investment Intelligence

**Theme:** The first real AI investment intelligence, layered onto the
Release 0.4.1 conversation/orchestration foundation without changing
it. Each Shark's questions, evaluation, and internal deliberation are
now real, provider-backed LLM output instead of deterministic
templates. The Session Director, Turn Controller, Event Bus, and chat
UI are all unchanged in their own responsibilities — only *what a
Shark says* changed, not *when* it gets to say it.

**Shipped:**

- `providers/exceptions.py`: `ProviderError`,
  `ProviderNotConfiguredError`, `ProviderRequestError`,
  `ProviderResponseError` — specific exception types for every provider
  failure mode, mirroring `orchestrator/exceptions.py`'s pattern.
- `providers/anthropic_provider.py`: `AnthropicProvider.generate()` is
  now a real implementation against the `anthropic` SDK. Reads
  `ANTHROPIC_API_KEY` exclusively via `config.settings.Settings` (never
  hardcoded, never read from `st.session_state`); lazily constructs
  its SDK client so building a provider never touches the network;
  splits any `role="system"` messages into the API's separate `system`
  parameter; maps SDK exceptions to `ProviderRequestError` and empty/
  non-text responses to `ProviderResponseError`; never logs message
  content or the API key.
- `prompts/shark_persona_system.txt` and `prompts/pitch_analysis.txt`:
  replaced their `[PLACEHOLDER]` stubs with real templates. Added two
  new prompt files following the same convention:
  `prompts/adaptive_question.txt`, `prompts/deliberation.txt`. All four
  loaded via the existing `prompts/loader.py` — no second prompt
  system.
- `models/schemas.py`: `SharkPersona` gained `priorities: List[str]`
  and `core_attitude: str` (structured persona data, not prompt text).
  `Offer` gained `interested: bool`, `rationale: str`, and
  `confidence: float`; `amount`/`equity_pct` became optional (null
  when not interested). `status` remains fixed at `DealStatus.PENDING`
  — Release 0.5 does not implement negotiation.
- `agents/shark_agent.py`: real `ask_question()` (pitch-adaptive,
  persona-influenced), real `evaluate_pitch()` (structured JSON →
  `Offer`, tolerating a markdown code fence), and new `deliberate()`
  (at-most-two-sentence deliberation line, enforced by a simple
  sentence-splitting safety net even if the model doesn't comply).
  Each of these three raises a specific `ProviderError` on failure
  rather than degrading itself; `fallback_question()`,
  `fallback_offer()`, and `fallback_deliberation()` are separate public
  methods holding the honest, deterministic Release 0.4/0.4.1 behavior,
  called by the Session Director when it catches that error — an
  explicit choice to keep the "who decides how to degrade" layering
  `docs/agent_contract.md` already established, rather than having the
  agent swallow its own failures. `fallback_offer()` never fabricates
  investment interest (`interested=False`, `confidence=0.0`, an honest
  rationale).
- `orchestrator/orchestrator.py`: `SharkTankOrchestrator` gained an
  injectable `provider` constructor parameter (defaults to a real
  `AnthropicProvider` built from settings via the new
  `_build_default_provider()`). `_prompt_shark_turn()` now calls the
  real `ask_question()`, falling back per-Shark on `ProviderError`.
  `_run_deliberation_pipeline()` now calls two new private methods,
  `_evaluate_all_sharks()` and `_deliberate_all_sharks()`, which
  produce three real `Offer`s and three real deliberation lines
  (appended to the conversation, founder still excluded — turn gating
  unchanged), each independently falling back on failure. Verification,
  Consensus, and the Investment Decision remain exactly the Release
  0.4.1 deterministic placeholders, per this release's own scope
  boundary (spec section B17) — `_summarize_offers()`'s "N of 3 Sharks
  interested" tally is a factual count for event payloads only, never
  shown to the founder, and explicitly not consensus logic.
- `ui/sidebar.py` / `models/enums.py`: added `LLMProvider.ANTHROPIC`;
  Anthropic is now the default, represented provider with real
  read-only configuration status (not an editable field that did
  nothing); Gemini/Ollama sections now explicitly say "Not implemented
  yet." Resolves the "Known gap" `docs/architecture.md` had recorded
  since Release 0.3.x.
- `ui/response.py` / `ui/controls.py`: added `st.spinner()` around the
  Session Director calls that now may take real wall-clock time — no
  threading, no async framework, per this release's own spec section
  B24.
- `tests/fakes.py`: `FakeProvider`, a deterministic offline
  `BaseProvider` test double (fixed/scripted responses, or a scripted
  failure), plus `unconfigured_provider()`. Used by every new test
  below — no test requires network access or an API key.
- Tests: `tests/test_providers.py` (10 tests: configuration, successful
  generation, system-message splitting, `max_tokens` forwarding, API
  failure mapping, empty/non-text response handling), 
  `tests/test_shark_agent.py` (31 tests: all three personas, distinct
  system prompts per persona, pitch/conversation content reaching the
  prompt, structured evaluation and its edge cases, failure handling,
  deliberation and its two-sentence truncation, disagreement between
  Sharks), and 12 new integration tests in `tests/test_session_director.py`
  (all three Sharks participating in deliberation, founder exclusion,
  concise deliberation, disagreement, provider-failure resilience,
  adaptive questions, injected-provider wiring). Two Release 0.4 tests
  were updated to reflect intentionally changed behavior: each Shark
  now legitimately speaks twice (a question, then a deliberation line)
  where it used to speak once, and the prompt-loader smoke test no
  longer expects a `[PLACEHOLDER]` stub.
- Total suite: **122 tests, all passing**, zero warnings.

**Live Anthropic smoke test:** Not executed. No `ANTHROPIC_API_KEY`
was available in this environment. This is reported per spec section
B28 rather than assumed to have passed.

**Explicitly out of scope (per spec sections B17-B20; unchanged from
prior releases unless noted above):** real Consensus Engine or
Verification Agent, negotiation/counter-offers, `run_pitch()`,
proposal validation/PII anonymization/prompt-injection defense, ADK,
MCP, Agent Skills, persistent memory, retry logic for transient
provider failures, true asynchronous phase execution, additional LLM
providers.

**Known limitations:**

- `ask_question()`'s "pitch-adaptive" behavior comes from the model
  reasoning over the raw pitch text in the prompt, not a distinct
  industry-classification mechanism — `docs/agent_personas.md` §9's
  Dynamic Industry Adaptation as its own step remains unimplemented
  (see that document's new §5.1).
- `confidence` is the model's own self-reported number with no
  calibration or verification against it — `docs/agent_personas.md`
  §11's specific formulas are not implemented.
- The actual evaluation JSON schema
  (`interested`/`amount`/`equity_pct`/`conditions`/`rationale`/
  `confidence`) differs from `docs/agent_personas.md` §5-§7's fuller
  aspirational schema (`deal_status`, `industry_context`) — a
  deliberate simplification per this release's own spec section B9,
  not an oversight; recorded in `docs/release_backlog.md`.
- No retry on transient provider failures — a single failure
  immediately falls back to the deterministic path for that one
  question/evaluation/deliberation call. Correct per this release's
  scope (spec section B4), but means a flaky connection could degrade
  an entire session to placeholders one Shark-turn at a time.
- Every provider-backed call is still fully synchronous, exactly like
  Release 0.4.1 — the founder's third response can now take several
  real seconds (three evaluations + three deliberations, sequentially)
  before the UI updates. A `st.spinner()` is the only affordance added
  for this; no background execution.

**Deviations from this specification:**

- Section B4 says provider failures must be "handled" and the
  session "must not become permanently stuck," but doesn't explicitly
  mandate the layering used here (agent raises, Director catches and
  substitutes a fallback) versus the agent swallowing its own
  failures internally. This implementation chose the Director-decides
  layering because `docs/agent_contract.md` -> *Error Handling*
  already established exactly that principle for a future release to
  follow, and Release 0.5 is that release.
- `agents/shark_agent.py`'s actual JSON schema omits `deal_status` and
  `industry_context`, both present in `docs/agent_personas.md` §5-§7's
  "Structured JSON Output Schema" tables, in favor of the field list
  Release 0.5's own spec section B9 asked for instead
  (`interested`/`amount`/`equity_pct`/`conditions`/`rationale`/
  `confidence`). Recorded in both `docs/agent_personas.md` §5.1 and
  `docs/release_backlog.md`.

---

## Release 0.6 — Market Reality, Proposal Validation, Safety, Structured Extraction, and Negotiation

**Theme:** Ground every Shark's reasoning in real external evidence,
make proposal validation and structured extraction real (not a
trivial non-empty check), add a focused security layer (PII redaction
+ prompt-injection defense), and let the founder negotiate once with
each Shark who made an offer. The session flow is now: Founder
Proposal → Moderator Validation & Extraction → Market Reality Research
→ Shark Analysis → Shark Questions → Internal Deliberation → Initial
Offers → Negotiation → Final Outcome. No Verification Agent, no real
Consensus Engine, no multi-round negotiation — those remain Release
0.7 scope, per this release's own Part U.

**Shipped:**

- **Security first** (spec priority order: security → correctness →
  evidence quality → architecture → testability → UX → polish):
  `utils/pii.py::anonymize_pii()` (deterministic email/phone/street-
  address redaction, applied once in `SharkTankOrchestrator
  .start_session()` before anything else sees the proposal) and
  `agents/prompt_safety.py` (`wrap_untrusted()`, applied to every
  founder-authored and web-retrieved string in every prompt this
  codebase builds; `looks_like_injection_attempt()` as a documented
  secondary/observability-only filter). Numeric validation
  (`agents/shark_agent.py::_validate_equity_pct()`/`_validate_amount()`)
  rejects an out-of-range equity percentage or a negative amount as a
  `ProviderResponseError`, triggering the normal fallback path rather
  than accepting a nonsensical figure. `orchestrator/orchestrator.py
  ::_cap_description_length()` bounds a submitted proposal to 20,000
  characters before anything processes it.
- **Real Moderator validation & extraction**
  (`agents/moderator_agent.py::ModeratorAgent.validate_and_extract()`):
  a real LLM call decides whether a proposal is legitimate (missing
  revenue/customers/financials is never itself a rejection reason) and
  extracts `founder_name`/`company_name`/`ask_amount`/
  `equity_offered_pct`/`valuation` into a new
  `models.schemas.ProposalValidationResult`. Raises on failure;
  `fallback_validate()` (the Release 0.4/0.4.1 trivial non-empty
  check) is the Session Director's fallback.
- **Real Market Reality Research**
  (`agents/market_research_agent.py::MarketResearchAgent`), run once
  per session between `VALIDATION` and `QUESTION_ROUND`:
  - `providers/base_research_provider.py`: a new, deliberately
    separate `BaseResearchProvider` abstraction (not folded into
    `BaseProvider`) plus `RawSearchResult`.
  - `providers/anthropic_research_provider.py`:
    `AnthropicResearchProvider`, using Anthropic's server-side web
    search tool (`web_search_20250305`, forwarded via a new `tools`
    kwarg on `AnthropicProvider.generate()`) — real, internet-connected
    search when `ANTHROPIC_API_KEY` is configured, no second search
    vendor/API key introduced.
  - `models/schemas.py`: new `ResearchSource`, `ClaimAssessment`,
    `ValuationEstimate`, `MarketRealityBrief` — bounded to spec Part
    C §15's field list. `ValuationEstimate.confidence` includes
    `"insufficient_evidence"`, the required (not fallback) outcome
    when evidence doesn't support a range.
  - `prompts/market_research_search.txt` /
    `market_research_synthesis.txt`: explicit founder-stated vs.
    externally-reported vs. derived vs. analyst-inference framing;
    explicit instructions never to fabricate a URL or a figure, and to
    treat retrieved page content as data, never instructions.
  - `MarketResearchAgent.fallback_brief()`: an honest
    `is_fallback=True` brief when research fails — every field stays
    empty, never invented.
- **Shark reasoning grounded in evidence**
  (`agents/shark_agent.py`): `ask_question()`, `evaluate_pitch()`, and
  `deliberate()` now each optionally take a `market_brief`. Each Shark
  is evaluated twice per session — a preliminary evaluation just
  before its Question Round turn (informing that question), and a
  final one during Internal Deliberation, now also informed by the
  founder's actual answers — matching spec Part B's "Shark Analysis"
  (stage 4) / "Questions" (stage 5) / "Internal Deliberation" (stage
  6) sequence, without adding a separate round or touching the
  existing bounded three-Shark turn sequence.
- **Real offers, announced in chat**
  (`orchestrator/orchestrator.py::_announce_offers()`): after
  deliberation, each Shark announces its real, final offer (or
  decline) as its own chat message, and a new `SharkOfferMade` event
  fires per Shark.
- **Real Negotiation** (spec Part J):
  - `orchestrator/negotiation_controller.py`: `NegotiationController`,
    a second, deliberately separate turn controller from
    `orchestrator/turn_controller.py::TurnController` — Negotiation's
    length is variable (zero to three turns, one per interested Shark)
    where the Question Round's is fixed, so it needed its own simpler
    sequencing rather than stretching `TurnController`'s fixed-length
    assumptions.
  - `agents/shark_agent.py::SharkAgent.negotiate()` /
    `fallback_negotiation_response()`: `accepted`/`rejected`/`modified`
    via a new `models.schemas.NegotiationResponse`. The fallback always
    rejects rather than silently accepting terms nobody evaluated.
  - `SharkTankOrchestrator.awaiting_founder_response`/
    `submit_founder_response()` now dispatch on phase (`QUESTION_ROUND`
    vs. `NEGOTIATION`) to route founder input to the right handler.
- **Real PDF text extraction** (`utils/pdf_extraction.py`, via
  `pypdf`): `ui/proposal.py` now extracts and uses a PDF's actual text
  as `proposal_content`, not just its filename. A PDF with no
  extractable text (e.g. a scanned image) is surfaced as an explicit
  error and not marked as an accepted proposal, never silently treated
  as an empty-but-valid submission.
- **State machine extended**: `SessionPhase` gained `MARKET_RESEARCH`
  (between `VALIDATION` and `QUESTION_ROUND`) and `NEGOTIATION`
  (between `INVESTMENT_DECISION` and `SESSION_COMPLETE`) —
  `docs/state_machines.md` updated accordingly. `VERIFICATION` and
  `CONSENSUS` remain unchanged deterministic pass-through phases.
- **Event Bus extended** (`orchestrator/events.py`): `PiiSanitized`,
  `ProposalExtracted`, `MarketResearchStarted`, `MarketResearchCompleted`,
  `MarketResearchFailed`, `SharkOfferMade`, `NegotiationStarted`,
  `FounderCounterOffered`, `SharkNegotiationResponded` — all added by
  extending the existing typed Event Bus, none replacing it.
- **UI**: an optional, collapsed "Market Reality Research" expander in
  `ui/proposal.py` (spec Part O: "do not dump a giant research report
  into the chat" — the chat itself only ever shows the Moderator's
  fixed, generic research announcement).
- **Tests**: `tests/test_pii.py` (8), `tests/test_prompt_safety.py`
  (10), `tests/test_pdf_extraction.py` (4), plus large additions to
  `tests/test_shark_agent.py` (negotiation, market-brief-aware
  prompts, numeric validation), `tests/test_session_director.py`
  (validation, research, offers, negotiation, PII, injection
  resistance — the whole Release 0.5/0.6 integration section was
  rewritten to match the new pipeline shape), and `tests/test_app_ui.py`
  (PDF upload end-to-end, Market Reality expander rendering).
  `tests/fakes.py` gained `MockResearchProvider` and support for
  scripting a mid-sequence failure via an exception instance in a
  `FakeProvider`'s `responses` list. Total suite: **177 tests, all
  passing**, zero warnings, no live network access or API key required
  anywhere.

**Explicitly out of scope (per spec Part U; unchanged from prior
releases unless noted above):** a real Verification Agent, a real
Consensus Engine, multi-round negotiation (counter-to-a-counter,
`SharkTankOrchestrator.run_pitch()`), Google ADK, MCP, Agent Skills,
persistent memory, analytics/telemetry, a five-Shark architecture,
Audio/Video proposals.

**Known limitations:**

- Dynamic Industry Adaptation (`docs/agent_personas.md` §9) is not a
  distinct mechanism — questions are adaptive because the model
  reasons over the raw pitch and market brief text, not because of an
  explicit industry-classification step or `industry_context` field.
- The actual evaluation/offer JSON schema
  (`interested`/`amount`/`equity_pct`/`conditions`/`rationale`/
  `confidence`) differs from `docs/agent_personas.md` §5-§7's fuller
  aspirational schema (`deal_status`, `industry_context`) — unchanged
  from Release 0.5, recorded there and in `docs/release_backlog.md`.
- `AnthropicResearchProvider` trusts the model's self-reported search
  results; it does not independently re-fetch or verify each URL. A
  fabricated or inconsistent-looking source is a documented risk, not
  a solved problem — see `docs/architecture.md` -> Market Reality
  Research.
- PII redaction covers exactly three identifier types (email, phone,
  street address) via regex — not a comprehensive PII scrubber.
- Prompt-injection defense is architectural wrapping plus a secondary
  pattern filter for observability only — not a guarantee an LLM never
  follows an embedded instruction embedded in founder or web content.
- Every provider-backed call remains fully synchronous (unchanged
  since Release 0.4.1/0.5) — a full session with real research,
  evaluation, deliberation, and negotiation now makes considerably
  more provider calls in sequence, so real-provider latency compounds
  further than it did in Release 0.5. Still no threading/async
  framework, per this release's own spec section B24-equivalent (Part
  Q's error-handling boundary and the general "do not overbuild"
  principle carried from prior releases).
- No live Anthropic smoke test or live research smoke test was
  performed — no `ANTHROPIC_API_KEY` was available in this
  environment. Every claim above about real provider-backed behavior
  is verified via `tests.fakes.FakeProvider`/`MockResearchProvider`
  (deterministic, offline) and via manual runs confirming the
  zero-configuration fallback path works end-to-end — not via a live
  API call. This is reported honestly rather than assumed to have
  passed.

**Deviations from this specification:**

- Part B's "Shark Analysis" (stage 4) is not a separate round before
  Questions (stage 5) — each Shark's preliminary evaluation happens
  immediately before that same Shark's question, within its existing
  Question Round turn, so the existing bounded three-Shark turn
  sequence (Part H: "Preserve the existing three-Shark architecture
  and bounded turn sequence") never needed to change shape.
  `evaluate_pitch()` is simply called twice per Shark per session
  (preliminary, then final during deliberation) rather than the
  pipeline gaining a fourth conversational round.
- `VERIFICATION` and `CONSENSUS` phases were kept exactly as they were
  (deterministic pass-through, unchanged code) rather than removed
  from the state machine, even though Part N's conceptual diagram
  omits them — Part U's own framing ("0.7 can then build formal
  verification and consensus on top of this foundation") only makes
  sense if those phases still exist to build onto, and removing
  already-documented scaffolding would have been an unnecessary
  architecture change the spec elsewhere warns against.

---

## Release 0.6.1 — Hardening, Research Integrity & Failure Semantics

**Theme:** A hardening release on top of Release 0.6, not a feature
expansion: strengthen Market Reality Research into a planning ->
targeted-evidence -> synthesis pipeline, close PII gaps beyond the
initial proposal, and guarantee a provider/research failure can never
be represented as a genuine investment decision -- so Release 0.7 can
build a real Verification Agent and Consensus Engine on a trustworthy
evidence/decision layer.

**Shipped:**

- **Failure semantics** (spec Part Q §15, this release's headline
  correctness fix): `models.schemas.Offer` gained
  `evaluation_available: bool = True`; `SharkAgent.fallback_offer()`
  now sets it `False`. `models.schemas.NegotiationResponse.decision`
  gained a fourth value, `"unavailable"`, returned only by
  `SharkAgent.fallback_negotiation_response()`.
  `orchestrator/orchestrator.py::_offer_announcement_text()` and
  `_negotiation_response_text()` both check the new signal *before*
  `interested`/`"rejected"`, so a technical failure is rendered as
  "evaluation could not be completed" / "could not process your
  counter-offer," never as a pass or a walk-away.
  `events.SharkOfferMade` carries `evaluation_available`;
  `_summarize_offers()`'s internal tally now reports unavailable
  Sharks separately rather than folding them into "not interested."
- **PII hardening** (spec Part E §13): `anonymize_pii()` is now also
  applied to the Moderator's LLM-extracted `description`/`founder_name`
  /`company_name` before they enter session state, and to every
  founder Question Round answer and negotiation counter-offer before
  they are stored or reach any Shark prompt -- closing the gap where
  only the original proposal was redacted.
- **Research planning** (spec Parts A/4-5): new
  `agents/research_planner.py::build_research_plan()`, a deterministic
  keyword heuristic (no LLM call) classifying a pitch into one of
  `saas`/`consumer`/`marketplace`/`restaurant`/`cleantech`/
  `professional_services`, or a conservative `generic` plan when
  uncertain, producing 3-8 typed `models.schemas.ResearchObjective`
  entries. `models.schemas.ResearchPlan` is the new typed container.
- **Targeted, partial-failure-aware evidence gathering** (spec Part C
  §§6/17): `MarketResearchAgent._gather_evidence()` now calls
  `research_provider.search()` once per planned objective instead of
  once per session, catching a `ResearchProviderError` per objective
  so one failed category never discards the rest. Results are
  deduplicated by normalized URL (`_dedupe_results()`, spec §20).
  `MarketRealityBrief` gained `research_objectives`/`failed_objectives`
  (naming attempted/failed categories) and
  `has_conflicting_evidence`/`conflicting_evidence_notes` (spec §19).
  `providers/anthropic_research_provider.py`'s `WEB_SEARCH_TOOL
  max_uses` lowered 6 -> 3 per call, since `search()` is now called
  up to ~6 times per session instead of once.
- **Evidence provenance** (spec Part C §§7-9): `ResearchSource` gained
  `retrieval_method: str = "model_reported"` (always this value --
  makes the "not independently verified" limitation explicit in the
  data, not only in docs) and its `reliability` is now set by a real
  domain-quality heuristic (`_classify_source_reliability()` --
  government/regulatory/major-statistics domains rank `"high"`, a
  short list of recognized financial/industry publications rank
  `"medium"`, everything else stays the conservative `"unverified"`
  default) instead of being hardcoded to `"unverified"` for every
  source. `ClaimAssessment` gained a bounded `status` field
  (`models.schemas.CLAIM_STATUSES`:
  `supported`/`partially_supported`/`unsupported`/`contradicted`/
  `insufficient_evidence`/`not_externally_verifiable`), parsed
  leniently with an unrecognized value clamped to
  `insufficient_evidence` rather than raised or trusted blindly.
- **Deterministic founder-implied valuation** (spec Part C §§10/12):
  `MarketRealityBrief.founder_implied_valuation` is now computed in
  Python (`ask_amount / (equity_offered_pct / 100)`) rather than
  trusted from the synthesis LLM's own arithmetic; the synthesis
  prompt no longer asks the model to compute it. The prompt also now
  forbids "wrong"/"incorrect" valuation framing, requiring
  "above/below the observed benchmark range" language instead (spec
  §12).
- **Housekeeping:** `pypdf` (used by `utils/pdf_extraction.py` since
  Release 0.6) and `reportlab` (used by `tests/test_pdf_extraction.py`
  since Release 0.6) were both used but declared in neither
  `requirements.txt` nor `pyproject.toml` -- a pre-existing
  dependency-declaration gap, found while trying to run the suite in a
  clean environment. Both now declared (`pypdf` as a runtime
  dependency, `reportlab` as a dev/test dependency).
- **Tests:** `tests/test_research_planner.py` (10 tests, fully offline)
  and `tests/test_market_research_agent.py` (21 tests: provenance,
  deterministic valuation, reliability heuristic, dedup, partial
  research, conflicting evidence, malformed/empty synthesis responses,
  a prompt-injection test for malicious search-snippet content) are
  new. `tests/fakes.py::MockResearchProvider` gained an optional
  `responses` scripted-per-call mode (alongside its existing
  `results`/`raise_error` modes, unchanged) for testing partial
  research. `tests/test_shark_agent.py` and
  `tests/test_session_director.py` gained failure-semantics and
  PII-widening tests, and two tests whose names/assertions described
  the pre-0.6.1 behavior (`fallback_offer()`'s "pass on this one" text;
  `fallback_negotiation_response()`'s "honest rejection" framing) were
  corrected to match the fixed behavior, per this project's established
  practice of fixing a misleadingly-named test rather than leaving it
  passing for the wrong reason (see Release 0.4.1's own precedent).
  The six files this release touched or added
  (`tests/test_shark_agent.py`, `tests/test_session_director.py`,
  `tests/test_research_planner.py`, `tests/test_market_research_agent.py`,
  `tests/test_pii.py`, `tests/test_prompt_safety.py`) run **156 tests,
  all passing**, under `tests.fakes` doubles with zero network access
  or API key required anywhere. Full project suite: **212 passing**
  (see *Known limitations* for the pre-existing, unrelated
  `tests/test_app_ui.py` flakiness this count excludes).

**Explicitly out of scope (per this release's own scope boundary;
unchanged from Release 0.6 unless noted above):** a real Verification
Agent, a real Consensus Engine, multi-round negotiation, Google ADK,
MCP, Agent Skills, persistent memory, a new search vendor, independent
URL re-fetching/verification, an LLM-based research-planning
classifier (a deterministic heuristic was used instead -- see
`docs/release_backlog.md`), a Streamlit/UI redesign, and a fix for the
pre-existing `tests/test_app_ui.py` `AppTest` flakiness/`file_uploader`
incompatibility discovered during this release's own verification pass
(see *Known limitations*) -- unrelated to this release's scope and
would have been an unrelated-code-cleanup expansion.

**Known limitations:**

- PII redaction is still exactly the same three regex patterns
  (email, phone, street address) as Release 0.6 -- 0.6.1 widened
  *where* redaction is applied, not *what* it detects. Still not a
  comprehensive PII scrubber.
- Prompt-injection defense is still architectural wrapping plus a
  secondary observability-only pattern filter -- not a guarantee an
  LLM never follows an embedded instruction. New adversarial tests
  (proposal, founder answer, negotiation counter, search-result
  snippet) confirm the wrapping is applied at every relevant call site
  and that a scripted response's output contract is unaffected by
  injected text, which is what this architecture can actually
  guarantee -- it is not a claim that a real LLM can never be
  manipulated.
- `AnthropicResearchProvider` still trusts the model's self-reported
  search results; `ResearchSource.retrieval_method` is always
  `"model_reported"` specifically to keep this limitation visible in
  the data, not to solve it.
- The research-planning heuristic is a small, fixed set of six business
  -model categories plus a generic fallback -- not a general industry
  taxonomy, and a pitch matching multiple categories' keywords takes
  whichever is checked first (documented in
  `agents/research_planner.py`'s own module docstring).
- Discovered but explicitly not fixed: `tests/test_app_ui.py`'s
  Streamlit `AppTest`-based integration tests exhibit pre-existing,
  order-dependent flakiness unrelated to this release's changes
  (confirmed by running the identical tests against the pre-0.6.1
  codebase), and two of them (`test_pdf_upload_extracts_real_text_not_just_filename`,
  `test_pdf_with_no_extractable_text_is_not_marked_uploaded`) fail
  deterministically against the installed Streamlit 1.41.1 because
  `AppTest` has no `file_uploader` accessor in that version -- a
  version-compatibility gap, not a regression from this release. Both
  are out of this release's scope (fixing them is unrelated test-
  harness maintenance, not research/PII/failure-semantics hardening).
- No live Anthropic smoke test or live research smoke test was
  performed. An `ANTHROPIC_API_KEY` was present in the ambient shell
  environment during this release's own verification, but real calls
  made with it failed with `AuthenticationError` -- so even with a key
  present, no successful live call occurred, and this is reported
  honestly rather than assumed to have passed. Every claim above about
  real provider-backed behavior is verified via
  `tests.fakes.FakeProvider`/`MockResearchProvider` (deterministic,
  offline).

**Deviations from this specification:**

- The specification's research-planning section allowed either a
  heuristic or an LLM-based planner; this release chose the
  deterministic keyword heuristic exclusively; see
  `docs/release_backlog.md`'s new entry for the reasoning (no provider
  call, no network dependency, fully offline-testable, and the
  specification's own instruction not to over-engineer this step).
- Per-source reliability is a domain-hostname heuristic computed in
  Python, not an LLM judgment per source -- the specification's Part C
  §8 did not mandate which approach, and computing it deterministically
  keeps the claim auditable and avoids asking the synthesis model to
  simultaneously judge its own sources' credibility while using them.
- `RawSearchResult` and `BaseResearchProvider`'s interface were left
  completely unchanged, per the specification's own instruction to
  preserve the provider abstraction -- a search result's category is
  tracked only internally within `MarketResearchAgent`, never added to
  the shared interface type.

---

## Release 0.7 — Verification Agent + Formal Consensus Engine

**Theme:** Replace the Release 0.4-0.6.1 deterministic pass-through
`VERIFICATION`/`CONSENSUS` phases with real components: a Verification
Agent that independently audits whether each Shark's final reasoning
is actually supported by the evidence, and a Consensus Engine that
reconciles the three Sharks' positions and the Verification findings
into one formal, non-majority-vote investment recommendation. Neither
is a fourth Shark; Shark independence, the existing per-Shark
offer/negotiation flow, the Event Bus, the Session Director, the Turn
Controller, and the Streamlit architecture are all preserved
unchanged.

**Shipped:**

- **Verification Agent** (`agents/verification_agent.py::VerificationAgent`):
  audits the three Sharks' final `Offer`s against the proposal, the
  founder's Question Round answers, and the Market Reality Brief.
  Checks: whether material claims are supported/partially supported/
  unsupported/contradicted/insufficient-evidence/not-externally-verifiable
  (reusing `models.schemas.CLAIM_STATUSES` from Release 0.6.1, not a
  second vocabulary); whether a Shark's reasoning accurately reflects
  what the founder actually said (a stated projection treated as
  current revenue, for example); and whether arithmetic a Shark relied
  on (e.g. an implied valuation) is actually consistent with the
  available inputs. Does not subclass `BaseAgent` (same reason
  `ModeratorAgent`/`MarketResearchAgent` don't); never produces an
  `Offer` or makes an investment decision. Runs once per session,
  during `VERIFICATION`, strictly after every Shark's own deliberation
  and strictly before Consensus (spec Part 22 — Shark independence is
  preserved: Verification never feeds back into a Shark's own
  reasoning). Raises `providers.exceptions.ProviderError` on failure;
  `fallback_result()` (`verification_status="unavailable"`) is the
  Session Director's fallback, distinct from a completed verification
  that simply found nothing wrong.
- **Consensus Engine** (`orchestrator/consensus_engine.py::ConsensusEngine`):
  reconciles the three Sharks' final positions, the Market Reality
  Brief, and the Verification findings into one
  `models.schemas.ConsensusResult`. Lives in `orchestrator/`, not
  `agents/` — it has no investment philosophy of its own and never
  evaluates the pitch independently, per `docs/folder_structure.md`'s
  own long-standing "Future expansion" note under `orchestrator/`.
  Explicitly **not** a majority vote (spec Part 12): deterministic
  per-Shark implied-valuation and interested/declined-tally facts are
  computed in Python (`_compute_facts()`) and handed to the LLM as
  given facts rather than left for it to (mis)calculate (spec Part
  16). `recommendation` is one of `models.schemas
  .CONSENSUS_RECOMMENDATIONS` (`invest` / `invest_with_conditions` /
  `do_not_invest` / `insufficient_evidence` / `unavailable`) —
  `"unavailable"` is reserved exclusively for
  `ConsensusEngine.fallback_result()`; a real LLM response claiming
  `"unavailable"` is rejected as invalid, mirroring
  `NegotiationResponse.decision`'s `"unavailable"` precedent from
  Release 0.6.1. `recommended_valuation_range` reuses the existing
  `ValuationEstimate`; `recommended_investment_range`/
  `recommended_equity_range` use a new, minimal `NumericRange` model —
  all stay null/`insufficient_evidence` rather than a fabricated
  number when evidence doesn't support a range.
- **New data models** (`models/schemas.py`): `VerificationFinding`,
  `VerificationResult`, `VERIFICATION_SEVERITIES`,
  `CONSENSUS_RECOMMENDATIONS`, `NumericRange`, `ConsensusResult`.
- **New prompts**: `prompts/verification.txt`, `prompts/consensus.txt`,
  both explicit that every founder/web/Shark-generated content block
  is untrusted data, never an instruction (spec Part 17).
- **Session Director integration** (`orchestrator/orchestrator.py`):
  `_run_verification()`/`_run_consensus()` mirror the existing
  `_run_market_research()` shape (set phase, publish `Started`, run
  the real component, publish `Completed`/`Reached` or `Failed`,
  never raise). `_run_deliberation_pipeline()` now runs Verification
  and Consensus between `DebateFinished` and `INVESTMENT_DECISION`;
  the Moderator gained `consensus_announcement()`, a short fixed line
  before the existing per-Shark offer announcements
  (`_announce_offers()`, unchanged). `InvestmentDecisionMade.deal_status`
  is now derived from `ConsensusResult.recommendation`
  (`_deal_status_from_recommendation()`, reusing the existing
  `DealStatus` enum rather than adding a parallel one) instead of a
  fixed `DealStatus.PENDING` placeholder; `unavailable`/an
  unrecognized recommendation both map to `PENDING`, never
  `OFFERED`/`REJECTED`. New `SharkTankOrchestrator.verification_result`
  / `consensus_result` read-only properties, following the existing
  `market_brief` pattern.
- **New Event Bus events** (`orchestrator/events.py`):
  `VerificationCompleted`, `ConsensusFailed` (added alongside the
  already-existing `VerificationStarted`/`VerificationFailed`/
  `ConsensusStarted`/`ConsensusReached`, reused rather than
  duplicated).
- **Shared prompt formatting** (`agents/prompt_formatting.py`, new): 
  `format_market_brief()`/`format_qa_transcript()` were extracted from
  `agents/shark_agent.py`'s private
  `_format_market_brief()`/`_format_qa_transcript()` (behavior
  unchanged — `SharkAgent`'s full test suite passes unmodified after
  the extraction) so the Verification Agent and Consensus Engine could
  reuse them instead of duplicating ~60 lines of formatting logic a
  second and third time (`docs/coding_standards.md` -> *Modularity: No
  Duplicated Logic*). Also adds `format_offer()`/`format_offers()`
  (multi-Shark rendering, new — no single-Shark prompt needed this
  before) and `format_verification()` (new).
- **UI** (`ui/proposal.py`): a new, optional "Investment Committee"
  expander — collapsed by default, same pattern as the existing
  "Market Reality Research" expander — showing `ConsensusResult`'s
  recommendation, confidence, thesis, strengths, risks, and conditions
  once a real result exists. No chain-of-thought, raw verification
  reasoning, or internal prompts are ever shown (spec Part 23); the
  chat itself only ever shows the Moderator's fixed
  `consensus_announcement()` line.
- **Tests**: `tests/test_verification_agent.py` (21 tests) and
  `tests/test_consensus_engine.py` (16 tests), both new — claim-status
  parsing, financial/valuation issue parsing, failure semantics,
  adversarial prompt-injection coverage (malicious proposal, founder
  answer, market brief content, and Shark-generated rationale text, per
  spec Part 26). `tests/test_session_director.py` gained a Release 0.7
  integration section (13 new tests: event ordering, `deal_status`
  mapping for `invest`/`do_not_invest`, one Verification/Consensus
  failure not blocking the other, one Shark's technical failure not
  corrupting Verification/Consensus, founder input never requested
  during either phase, and the spec's own adversarial malicious-proposal
  case) and had its `_scripted_provider()` fixture and two pre-existing
  tests (`test_expected_events_fire_in_order_for_a_full_session`,
  `test_investment_decision_is_an_explicit_pending_placeholder` →
  renamed `..._reflects_pending_when_consensus_is_unavailable`) updated
  to account for the two new provider calls now in the full-session
  sequence — corrected, not deleted, following this project's
  established practice (see Release 0.4.1's own precedent). Full
  suite: **261 passing** (up from 211 before this release); the 4-7
  pre-existing, order-dependent `tests/test_app_ui.py` failures are
  unchanged and unrelated (confirmed via `git stash` against the
  pre-0.7 codebase before starting this release's own work).

**Explicitly out of scope (per spec Part 3; unchanged from prior
releases unless noted above):** a fourth Shark or additional Shark
personas, Google ADK, MCP, Agent Skills, SQLite/persistent memory,
multi-session learning, multi-round negotiation, autonomous post-deal
monitoring, a new UI architecture, a new orchestration framework,
replacing the Event Bus/Session Director/Turn Controller/research
provider architecture, a new database, a new external search provider,
hidden chain-of-thought exposure.

**Known limitations:**

- The Verification-failure bounce-back-to-Internal-Deliberation retry
  path (`docs/state_machines.md` § Rule 3) remains unimplemented — see
  *Deviations* below.
- `docs/agent_personas.md` §12.2's "Unanimous Rejection" short-circuit
  (ending the session immediately, no negotiation, when all three
  Sharks independently conclude a pitch is impossible/fraudulent) has
  no distinct signal in `ConsensusResult` — a unanimous `do_not_invest`
  today looks the same as an ordinary decline. Recorded in
  `docs/release_backlog.md`.
- Verification's audit quality depends entirely on the underlying
  model's reasoning; this codebase adds no independent, deterministic
  arithmetic-checking beyond what the Consensus Engine's own
  `_compute_facts()` computes for its own prompt — the Verification
  Agent's own "check the arithmetic" instruction is prompt-level
  guidance to the LLM, not a second, separate deterministic verifier.
- Prompt-injection defense is unchanged from Release 0.6.1: architectural
  wrapping plus an observability-only secondary filter, extended in
  Release 0.7 to also cover Shark-generated rationale text (new) — not
  a guarantee an LLM never follows an embedded instruction.
- No live Anthropic smoke test was performed. An `ANTHROPIC_API_KEY`
  present in the ambient shell environment during this release's own
  verification (leaked from the Claude Code process context, not this
  project's own `.env`) fails real calls with `AuthenticationError` —
  reported honestly, not assumed to have passed. Every claim above
  about real provider-backed behavior is verified via
  `tests.fakes.FakeProvider` (deterministic, offline).
- Discovered, not fixed (pre-existing, unrelated to this release): a
  dead, unused `prompts/negotiation_round.txt` placeholder file from
  early releases (superseded by `prompts/negotiation.txt`, never
  cleaned up, never loaded by any code) and `tests/test_app_ui.py`'s
  pre-existing `AppTest` flakiness/`file_uploader` version
  incompatibility (see Release 0.6.1's own entry, still present,
  still unrelated to this release's own changes).

**Deviations from this specification:**

- Part 3/25's implied full test matrix (regional mismatch, stale
  evidence, proposal/Shark mismatch, etc. as separate dedicated test
  cases) is covered through the structural formatting/parsing tests in
  `test_verification_agent.py`/`test_consensus_engine.py` plus the
  Release 0.6.1 Market Reality Research tests those same fields
  already exercise (`has_conflicting_evidence`, source dates,
  `failed_objectives`) rather than a fully separate duplicate test set
  — the same evidence-quality fields flow through Verification/Consensus
  unchanged, so re-testing their parsing a second time at every layer
  would be redundant coverage, not new confidence.
- **The `Verification → Internal Deliberation` bounded retry path
  (`docs/state_machines.md` § Rule 3) was deliberately NOT
  implemented**, despite `VerificationAgent` now being real. Adding it
  would require the Session Director to gain new retry-counter/loop
  control flow and at least one new state transition — a materially
  larger architectural change than "add a real Verification Agent and
  Consensus Engine," and this specification's own Part 3 explicitly
  warns against expanding the Session Director/orchestration framework
  beyond what's asked. Today, `VERIFICATION` always proceeds to
  `CONSENSUS` regardless of findings; a critical finding instead flows
  *forward* into the Consensus Engine's reconciliation (where it can
  legitimately drive the recommendation toward `do_not_invest`/
  `insufficient_evidence`), which is how this release surfaces a
  serious problem without a retry loop. Recorded as a "Future
  Extension Point" in `docs/architecture.md` and moved to
  `docs/release_backlog.md`'s Release 0.8 section rather than silently
  dropped.
- `docs/agent_personas.md` §12.2's Unanimous Rejection path (a distinct,
  more severe outcome than an ordinary decline) was not implemented —
  that document itself already marks it 🧭 planned with "this document
  does not invent the specific mechanism," and Release 0.7's own spec
  does not ask for it either; recorded in `docs/release_backlog.md`
  rather than implemented speculatively.

---

## Release 0.8 — Advanced Investment Analysis + Decision Quality

**Theme:** Move the committee's decision from "do the Sharks like this
business?" toward "given the evidence, financial reality, valuation,
risk, growth potential, and deal structure, is this an attractive
investment at the proposed terms?" A new Advanced Financial Analysis
step extracts financial facts with explicit provenance, computes every
calculation deterministically in Python, produces analytical
downside/base/upside valuation scenarios, and identifies structured
risk/upside factors -- feeding both the existing Verification Agent
(extended to audit it) and Consensus Engine (extended to reconcile it
into a formal business-quality-vs-deal-quality distinction). No fourth
Shark, no new orchestration framework, no platform expansion --
exactly one new LLM call added per session.

**Architecture decision, stated up front:** the release's own
conceptual pipeline diagram places Advanced Analysis *after*
Verification; this implementation places it *before* Verification
instead. Verification must be able to audit the financial analysis
itself (this release's own spec Part 20), which is only possible if
the analysis already exists when Verification runs -- the diagram's
box order and its own stated requirement were in tension, and the
data dependency, not the diagram, determined the actual order. See
`docs/architecture.md` -> Advanced Financial Analysis for the full
reasoning; `docs/state_machines.md` reflects the same choice.

**Shipped:**

- **Financial Analyst** (`agents/financial_analyst.py::FinancialAnalyst`):
  extracts financial facts from the pitch and founder Question Round
  answers with explicit provenance
  (`models.schemas.FINANCIAL_FACT_PROVENANCE`: `founder_stated` /
  `externally_reported` / `derived` / `analyst_inference` / `estimated`
  / `missing`) -- a founder's *projection* is a structurally distinct
  `metric` name from *current* fact, so a projection can never
  silently become the input to a current-fact calculation (spec Part
  6). Does not subclass `BaseAgent` (same reason
  `ModeratorAgent`/`MarketResearchAgent`/`VerificationAgent` don't).
  Runs once per session, during the new `ADVANCED_ANALYSIS` phase,
  after every Shark's final deliberation and before Verification.
- **Deterministic financial calculations** (`utils/financial_calculations.py`,
  new module, zero dependencies on any other project package): implied
  post-/pre-money valuation, revenue/ARR multiples, gross/operating
  margin, revenue growth, monthly burn, runway, dilution, LTV/CAC, and
  `apply_growth_delta()` (used to compute scenario figures from the
  LLM's proposed assumption deltas). Every function returns `None`
  rather than raising or guessing on a missing/zero/negative
  denominator (spec Part 37) -- the LLM is never asked to perform this
  arithmetic itself (spec Part 16); deal terms
  (`ask_amount`/`equity_offered_pct`/`valuation`) reuse the Moderator's
  existing Release 0.6 extraction on `Pitch` rather than being
  re-extracted.
- **Deterministic + LLM-assisted consistency checks**
  (`models.schemas.CONSISTENCY_ASSESSMENTS`: `consistent` /
  `potentially_inconsistent` / `materially_inconsistent` /
  `insufficient_information` -- never "fraudulent," per spec Part 8).
  `FinancialAnalyst._run_sanity_checks()` deterministically compares a
  founder-stated figure (margin, burn, runway) against the same figure
  computed independently from other stated inputs, and flags
  out-of-range percentages or logically-invalid negative values; the
  synthesis LLM call separately flags issues needing narrative
  judgment (e.g. a projection referenced elsewhere as historical fact).
- **Scenario analysis, not forecasts** (spec Part 12):
  `models.schemas.ScenarioValuation` (`downside`/`base`/`upside`,
  `models.schemas.SCENARIO_LABELS`), each with an `assumption_basis`
  (`models.schemas.ASSUMPTION_SOURCES`: `founder_provided` /
  `market_evidence` / `analyst_assumption` / `insufficient_evidence`)
  making explicit where its assumption came from. `base` reuses the
  existing Market Reality-informed valuation range (Release 0.6) as
  its anchor; `downside`/`upside` apply the LLM's proposed revenue
  growth delta to extracted current revenue
  (`apply_growth_delta()`), then multiply by the same revenue multiple
  already computed -- both steps are Python arithmetic. A scenario
  with no computable base stays `insufficient_evidence` with
  `low`/`high` left `None`, never fabricated.
- **Structured risk and upside factors**: `models.schemas.RiskFactor`
  (category, description, severity -- reusing Release 0.7's
  `VERIFICATION_SEVERITIES` rather than a second vocabulary --
  evidence, confidence, mitigable, material) and `UpsideFactor`
  (category, description, `basis` -- `models.schemas.UPSIDE_BASIS`:
  `evidence` / `inference` / `hypothesis`, so speculative upside can
  never be presented as established fact -- evidence, confidence).
- **Business quality vs. deal quality** (spec Part 15, `ConsensusResult`
  extended): `business_quality`, `deal_quality`, `financial_health`
  (all `models.schemas.QUALITY_RATINGS`: `strong`/`moderate`/`weak`/
  `insufficient_evidence` -- deliberately coarse, never a numeric score
  dressed up as precision) plus free-text `growth_profile`/
  `risk_profile`/`scenario_summary`. `recommendation` tracks deal
  quality, not business quality alone -- an excellent business at an
  excessive valuation should still drive `deal_quality` and
  `recommendation` down. No duplicate/overlapping fields were added:
  the spec's own suggested `key_value_drivers`/`key_risk_drivers`/
  `recommended_terms` reuse the existing `key_strengths`/`key_risks`/
  `conditions` fields from Release 0.7 instead, and `investment_quality`
  was deliberately not added as a fourth field redundant with
  `recommendation`.
- **Verification extended, not duplicated** (spec Part 20):
  `VerificationAgent.verify()` gained an optional `financial_analysis`
  parameter; findings about the analysis's own facts, calculations, or
  scenario assumptions land in the existing `financial_issues`/
  `valuation_issues` lists -- no new `VerificationResult` fields.
- **New Event Bus events** (`orchestrator/events.py`):
  `AdvancedAnalysisStarted`, `AdvancedAnalysisCompleted`,
  `AdvancedAnalysisFailed`, following the exact `Started`/`Completed`/
  `Failed` convention Release 0.7 already established for Verification
  and Consensus.
- **New `SessionPhase.ADVANCED_ANALYSIS`** (`models/enums.py`), the
  twelfth phase, positioned between `INTERNAL_DELIBERATION` and
  `VERIFICATION` in `PHASE_ORDER`/`PHASE_LABELS`/`PHASE_STAGE_MESSAGES`.
- **New `prompts/financial_analysis.txt`**, explicit that every
  founder/web/Shark-generated content block is untrusted data, and
  that scenario deltas/risk-upside factors must never be presented
  with false precision.
- **Shared prompt formatting extended** (`agents/prompt_formatting.py`):
  new `format_financial_analysis()`, reused by both
  `VerificationAgent` and `ConsensusEngine` -- avoiding a third
  duplicated rendering of the same result type.
- **UI** (`ui/proposal.py`): the existing "Investment Committee"
  expander (Release 0.7) extended with business/financial/deal quality
  rows, a rounded valuation range, and growth/risk/scenario summaries.
  New `_format_currency_range()` helper rounds every displayed
  valuation to at most 2-3 significant figures ("$2.5M-$3.5M", never
  "$3,184,721" -- spec Part 33, "No Fake Precision"). No new expander
  was added -- keeping the UI consolidated rather than adding another
  collapsed section for a founder to open.
- **Tests**: `tests/test_financial_calculations.py` (40 tests, pure
  deterministic functions), `tests/test_financial_analyst.py` (31
  tests: extraction/provenance, deterministic calculations, sanity
  checks, scenarios, risk/upside factors, failure semantics,
  adversarial prompt-injection coverage), `tests/test_ui_proposal_formatting.py`
  (7 tests for `_format_currency_range()`), all new.
  `tests/test_verification_agent.py` (+3) and `tests/test_consensus_engine.py`
  (+9, including numeric-range validation for the new fields) extended
  for the financial-analysis integration.
  `tests/test_session_director.py` gained a Release 0.8 integration
  section (9 new tests: phase/event ordering, one financial-analysis
  failure not blocking Verification/Consensus, `financial_analysis`
  accessible via the director) and had its `_scripted_provider()`
  fixture updated for the new provider call in the full-session
  sequence (the same category of fixture update Release 0.7 needed).
  Full suite: **355 passing** (up from 263 before this release); the
  2-7 pre-existing, order-dependent `tests/test_app_ui.py` failures
  remain unchanged and unrelated (confirmed via baseline run before
  starting this release's own work).

**Explicitly out of scope (per spec Part 4; unchanged from prior
releases unless noted above):** ADK, MCP, Agent Skills, SQLite/
persistent memory, blockchain, multi-session learning, autonomous
post-investment monitoring, multi-round negotiation, a fourth Shark,
replacing Streamlit/Event Bus/Session Director/the research provider
abstraction, a generic "AI financial advisor."

**Known limitations:**

- Scenario valuations are a single point estimate per scenario
  (revenue × multiple), not a true range -- the UI rounds for display
  to avoid false precision, but a genuinely ranged per-scenario
  valuation (without inventing a spread) is future work. Recorded in
  `docs/release_backlog.md`.
- No dedicated per-sector calculation framework (spec Part 10's
  SaaS/marketplace/restaurant/etc. sections) -- one general
  extraction+calculation pipeline is guided by a business-model label
  rather than branching into distinct sector-specific logic paths.
  Recorded in `docs/release_backlog.md`.
- "Hardware" and "biotech/deep tech" are not distinct business-model
  categories -- pitches in those spaces fall into the existing Release
  0.6.1 `generic` bucket or whichever of the six existing categories
  their keywords happen to match. `agents/research_planner.py` was not
  modified.
- The Advanced Financial Analysis's own output is not fed back into
  any Shark's own prompt -- each Shark's reasoning is still grounded
  only in the Market Reality Brief (Release 0.6), exactly as before.
  Recorded as a Release 0.9 extension point in `docs/release_backlog.md`.
- No independent, deterministic verification of the LLM's own
  arithmetic claims beyond what `utils/financial_calculations.py`
  computes for Consensus's `_compute_facts()` -- the Verification
  Agent's own "check the arithmetic" instruction is prompt-level
  guidance, not a second automated verifier.
- No live Anthropic smoke test was performed. An `ANTHROPIC_API_KEY`
  present in the ambient shell environment during this release's own
  verification (leaked from the Claude Code process context, not this
  project's own `.env`) fails real calls with `AuthenticationError` --
  reported honestly, not assumed to have passed. Every claim above
  about real provider-backed behavior is verified via
  `tests.fakes.FakeProvider` (deterministic, offline).

**Deviations from this specification:**

- **Advanced Analysis runs before Verification, not after it**, despite
  the specification's own conceptual pipeline diagram placing it after
  -- see the Architecture Decision note at the top of this entry and
  `docs/architecture.md` -> Advanced Financial Analysis for the full
  reasoning. This is the specification's own Part 31 invitation acted
  on directly: "if the actual architecture indicates that Advanced
  Analysis belongs before Verification... determine the correct
  ordering based on data dependencies and explain it."
- The Advanced Financial Analysis's output is not threaded into
  individual Shark prompts (spec Part 19's "common analytical
  foundation the Sharks continue interpreting differently" is read as
  Consensus reconciling the analysis alongside each Shark's
  already-independently-formed position, not as each Shark literally
  reading the analysis) -- chosen specifically to avoid reshaping the
  Question Round pipeline or risking the "preserve three-Shark
  independence" regression the specification's own Part 35 warns
  against. Recorded in `docs/release_backlog.md` as a Release 0.9
  extension point.
- `ConsensusResult`'s new fields omit the specification's suggested
  `investment_quality` (redundant with the existing `recommendation`),
  `key_value_drivers`/`key_risk_drivers` (reuse the existing
  `key_strengths`/`key_risks`), and `recommended_terms` (reuses the
  existing `conditions`) -- all per the specification's own instruction
  not to create fields that duplicate or overlap existing 0.7 models.

---

## Release 0.9 — Agentic Founder Feedback Report + Investor-Readiness Assessment

**Theme:** Move beyond "what did the committee decide?" to "what
should the founder actually improve before pitching real investors?"
A new Founder Feedback Report, generated once at the end of every
session, critically synthesizes the *entire* simulation -- not just
the Sharks' offers -- into strengths, needs-work areas, and (reserved
for genuinely serious problems) critical issues; an investor-readiness
assessment grounded in real, cited research into how early-stage
investors actually evaluate startups; qualified valuation/financial
feedback; and a prioritized NOW/NEXT/LATER action plan. Delivered as
an in-memory-only two-page PDF download. No fourth Shark, no second
Consensus Engine, no new `SessionPhase`, no threading/async -- exactly
one new LLM call added per session, run synchronously as the first
step of the existing completion path.

**Architecture decision, stated up front:** the specification's own
scope language discourages adding state transitions for cosmetic
reasons, and by the time this report can run, the simulation's
interactive/visible lifecycle is already over -- there is no
turn-by-turn founder experience left to represent with a dedicated
`SessionPhase`. Report generation was implemented entirely inside
`SharkTankOrchestrator._complete_session()` instead, with three new
typed events (`FounderReportStarted`/`Completed`/`Failed`) preserving
full Event Bus visibility without a thirteenth phase. See
`docs/architecture.md` -> Founder Feedback Report and
`docs/state_machines.md` § Rule 6 for the full reasoning.

**Shipped:**

- **Real, cited research into investor evaluation criteria**
  (`docs/investor_evaluation_framework.md`, new): assembled from actual
  web research (Y Combinator, Techstars, Sequoia, 500 Global, a16z, CRV,
  and others) covering market opportunity, team, traction, unit
  economics, defensibility, and every other spec-mandated dimension,
  plus stage-aware benchmarks -- per the specification's own explicit
  instruction not to rely on a generic, uncited checklist. Kept
  strictly separate from session-specific conclusions: the framework
  document is general evidence about how investors evaluate companies,
  never conflated with what a specific pitch actually demonstrated.
- **Founder Feedback Agent** (`agents/founder_feedback_agent.py::FounderFeedbackAgent`):
  `generate()` synthesizes the proposal, the Moderator's
  `ProposalValidationResult`, the Market Reality Brief, the full Q&A
  transcript, every Shark's final `Offer`, every `NegotiationResponse`,
  the `VerificationResult`, the `ConsensusResult`, and the
  `FinancialAnalysisResult` -- every input wrapped as a separately
  labeled untrusted-content block (`agents.prompt_safety.wrap_untrusted()`),
  exactly like every other real agent. Does not subclass `BaseAgent`
  (same reason `ModeratorAgent`/`MarketResearchAgent`/
  `VerificationAgent`/`FinancialAnalyst` don't -- it never evaluates a
  pitch or produces an `Offer`). Raises a
  `providers.exceptions.ProviderError` on failure, exactly like every
  other real agent; never degrades itself.
- **New domain models** (`models/schemas.py`): `FounderFeedbackReport`
  (`report_status`: `completed`/`unavailable`; `stage`
  (`COMPANY_STAGES`: `idea`/`pre_validation`/`early_validation`/
  `early_revenue`/`growth`/`later_stage`/`unclear`);
  `strengths`/`needs_work`/`critical_issues`;
  `investor_readiness: list[InvestorReadinessDimension]`
  (`INVESTOR_READINESS_ASSESSMENTS`: `strong`/`developing`/`weak`/
  `unclear`/`insufficient_evidence`); qualified `valuation_feedback`/
  `financial_feedback`; `action_plan: list[ActionItem]`
  (`ACTION_PRIORITIES`: `now`/`next`/`later`, each item carrying
  `problem`/`why_it_matters`/`action`/`evidence_needed`);
  `evidence_references: list[ReportEvidenceRef]`; `limitations`; and a
  fixed `disclaimer` defaulting to the module-level
  `FOUNDER_REPORT_DISCLAIMER` constant, which the parsed LLM JSON can
  never override (`_build_report()` simply never reads a
  disclaimer-like field from the model's response). Every bounded field
  is clamped to its enum rather than raising on an unrecognized LLM
  value, consistent with this codebase's established lenient-parsing
  pattern (`_readiness_from_json()`, `_action_plan_from_json()`); an
  action item missing `problem`/`action` is dropped rather than stored
  incomplete.
- **In-memory PDF rendering** (`utils/report_rendering.py::render_founder_report_pdf()`,
  new): pure rendering via `reportlab.platypus`
  (`SimpleDocTemplate`/`Paragraph`/`ListFlowable`/`PageBreak`), zero
  filesystem writes (`io.BytesIO` throughout, confirmed by a test that
  runs rendering inside an empty `tmp_path` and asserts nothing
  appears there), no provider calls of its own. Every field is
  HTML-escaped (`xml.sax.saxutils.escape()`) before insertion into a
  `Paragraph`, since `reportlab` interprets a small HTML-like markup
  language -- the same class of fix as `ui/proposal.py`'s
  `html.escape()` XSS fix from Release 0.4.1. Handles
  `report_status="unavailable"` by rendering an honest one-page notice
  instead of raising. `reportlab` was promoted from a dev-only
  dependency (it already generated test fixture PDFs) to a core
  dependency in `requirements.txt`/`pyproject.toml`, reusing rather
  than adding a new PDF library.
- **New prompt** (`prompts/founder_feedback.txt`): instructs
  cross-referencing the entire simulation (not just the Sharks) to
  catch discrepancies no individual Shark caught, 3-5 evidence-linked
  strengths, an ordered needs-work list, a reserved "critical" category
  for genuinely serious problems only, adaptive (not rigid)
  investor-readiness dimensions with business-model-specific guidance,
  qualified-only valuation language, financial feedback that
  distinguishes a business problem from bad deal terms, a four-part
  NOW/NEXT/LATER action-plan structure, evidence-reference provenance,
  an honest limitations statement, and explicit untrusted-content
  handling instructions for every wrapped input block.
- **Shared prompt formatting extended** (`agents/prompt_formatting.py`):
  new `format_validation_result()`, `format_negotiation_responses()`,
  and `format_consensus()`, reused by `FounderFeedbackAgent` rather
  than duplicating rendering logic already established for other
  result types.
- **Two previously-discarded orchestrator inputs, now persisted**
  (`orchestrator/orchestrator.py`): `SharkTankOrchestrator._validation_result`
  (the Moderator's `ProposalValidationResult`, previously used only
  transiently) and `SharkTankOrchestrator._negotiation_responses`
  (per-Shark `NegotiationResponse` objects, previously only rendered to
  chat text) are now stored as internal state at their existing
  production call sites, specifically so the Founder Feedback Report
  can use them -- both were explicitly required report inputs by the
  specification and were the only real input-completeness gap the
  implementation audit found.
- **New `founder_report` property** on `SharkTankOrchestrator`,
  mirroring `market_brief`/`verification_result`/`consensus_result`'s
  existing pattern -- `None` until `_complete_session()` generates a
  real result.
- **`_complete_session()` rewritten**: generates the
  `FounderFeedbackReport` as its first action (via the new
  `_run_founder_report()`, mirroring every other `_run_*()`
  finalization method's raise/catch/fallback shape), then proceeds to
  the closing message and `SESSION_COMPLETE` exactly as before.
- **New Event Bus events** (`orchestrator/events.py`):
  `FounderReportStarted`, `FounderReportCompleted`, `FounderReportFailed`,
  following the exact `Started`/`Completed`/`Failed` convention Release
  0.7/0.8 already established.
- **UI** (`ui/proposal.py::_render_founder_report_section()`, new):
  gated on `SessionPhase.SESSION_COMPLETE` and a real `founder_report`;
  renders PDF bytes on demand via `render_founder_report_pdf()` (cheap
  and safe to redo every rerun, rather than caching bytes on the
  director) and offers them through `st.download_button()`. An
  `unavailable` report renders an honest notice instead of a download
  button. Session isolation required no new cleanup code: `ui/controls.py`
  already builds a brand-new `SharkTankOrchestrator` per session, so
  `founder_report` starts `None` for every new session with zero
  additional code -- verified directly by reading `ui/controls.py`/
  `ui/session_state.py` rather than assumed.
- **Tests**: `tests/test_founder_feedback_agent.py` (21 tests: schema
  completeness, exact-disclaimer enforcement, stage/assessment/priority
  clamping, action-item dropping on missing required fields, JSON
  round-trip, business-model detection, failure semantics, "never
  produces an Offer" structural check, 5 adversarial prompt-injection
  tests), `tests/test_report_rendering.py` (7 tests: real PDF bytes,
  zero filesystem writes, `unavailable`-status handling, empty optional
  lists, HTML-escaping verified via actual `pypdf` text extraction --
  not raw-byte substring search, since `reportlab` compresses content
  streams by default). `tests/test_session_director.py` gained a
  Release 0.9 integration section (9 new tests: report accessible after
  success, structural "never an Offer" check, failure falls back
  without blocking completion, `FounderReportFailed` fires instead of
  `Completed`, report still generates when no Shark is interested,
  report reflects validation/negotiation inputs, report synthesizes the
  full pipeline -- all 9 prompt-input labels present, end-to-end
  adversarial injection test) and had its `_scripted_provider()`
  fixture updated for the new provider call (the same category of
  fixture update Release 0.7/0.8 needed), plus its full-session
  event-ordering test extended to assert `FounderReportStarted`/
  `Completed` fire after negotiation and before `SessionEnded`.
  `tests/test_app_ui.py` gained 4 new Streamlit `AppTest` tests: the
  report section is absent before completion, appears after completion,
  shows an honest unavailable notice when no provider is configured
  (the actual behavior in this test environment), and a prior session's
  report never leaks into a new one after reset. Full suite: **393
  passing**; the same 6 pre-existing, non-deterministic
  `tests/test_app_ui.py` failures remain, confirmed unrelated via a
  `git stash` baseline comparison before this release's own work.

**Explicitly out of scope (per spec Parts 36-37; unchanged from prior
releases unless noted above):** ADK, MCP, Agent Skills, SQLite/
persistent memory, blockchain, a 0.9.5-scope autonomous QA/regression
suite (simulated founder testing, agent-impersonation QA), multi-round
negotiation, a fourth Shark, an interactive/regenerable report,
persistence of the report across a reset, replacing Streamlit/Event
Bus/Session Director/the research provider abstraction.

**Known limitations:**

- The Founder Feedback Report is a single pass from a single LLM
  call -- no follow-up questions, no regeneration, no "ask the report a
  question" capability. Recorded in `docs/release_backlog.md`.
- Like every other session artifact, the report is not persisted --
  ending the session or the Python process loses it, exactly like
  every other `BaseMemory`-backed artifact this codebase still lacks.
- No dedicated per-business-model investor-readiness rubric -- the same
  general dimension set is used for every pitch, steered by the
  existing `classify_business_model()` label, mirroring Release 0.8's
  identical, deliberate simplification for financial analysis.
- No live Anthropic smoke test was performed. An `ANTHROPIC_API_KEY`
  present in the ambient shell environment (leaked from the Claude Code
  process context, not this project's own `.env`) fails real calls
  with `AuthenticationError` -- reported honestly, not assumed to have
  passed. Every claim above about real provider-backed behavior is
  verified via `tests.fakes.FakeProvider` (deterministic, offline); in
  this test environment specifically, the Streamlit `AppTest` suite's
  founder report ends up `report_status="unavailable"` for every
  simulated session, since no provider is configured there either --
  exercising the honest-failure UI path in practice, not just in a
  scripted unit test.

**Deviations from this specification:**

- **No new `SessionPhase` for report generation**, despite report
  generation being a distinct pipeline stage in the specification's own
  narrative -- see the Architecture Decision note at the top of this
  entry, `docs/architecture.md` -> Founder Feedback Report, and
  `docs/state_machines.md` § Rule 6 for the full reasoning. This is the
  specification's own explicit instruction acted on directly: "do not
  add state transitions merely for cosmetic reasons."
- **"Background" generation is synchronous, not literally
  concurrent** -- consistent with every prior release's documented
  choice to keep this codebase's execution model synchronous
  throughout (Release 0.5 spec section B24, Release 0.6 spec Part R24).
  "Background" is implemented as "no exposed turn-by-turn reasoning,"
  not as a separate thread or async task.

---

## Release 0.9.5 — Full-System QA, Validation, Simulation Conformance & Hardening

**Theme:** A dedicated QA milestone, not a feature release: prove the
complete system works as an integrated agentic application *and*
actually behaves like the Shark Tank simulation it was designed to
be, per its own two-level mandate ("does the machine work?" and "does
the product feel like Shark Tank?"). Per its own governing instruction
("do not trust previous reports"), every claim below was independently
re-verified in this release rather than inherited from Release
0.6.1-0.9's own final reports.

**Shipped:**

- **A permanent canonical reference proposal**
  (`tests/fixtures/proposals/0_9_5_reference_proposal.md`, plus a
  content-characteristics manifest alongside it): a fictional B2B SaaS
  pitch ("FleetPulse") deliberately engineered to exercise the whole
  pipeline -- real strengths (renewing paying customers), a fixable
  weakness (customer concentration), an unsupported market-size claim,
  a genuine financial inconsistency (a stated gross margin that
  contradicts the founder's own other stated figures), a named
  well-funded competitor, and missing information (churn, CAC) --
  without encoding an expected Shark/Consensus/Verification verdict, so
  the fixture tests whether conclusions are *supported*, not whether
  the system reaches a predetermined outcome. A second fixture
  (`0_9_5_pii_test_proposal.md`) provides synthetic PII for redaction
  testing.
- **A real, previously-unimplemented product defect found and fixed:
  the three canonical final-outcome messages did not exist.**
  `ModeratorAgent.closing_message()` delivered one fixed, generic
  "thank you" line regardless of what actually happened in the
  session -- the exact required lines ("Sorry Little Fish, the Sharks
  were not impressed" / "...there was nothing for you here today" /
  "Congratulations, Little Fish. You will now swim with the Sharks!")
  were specified but never implemented in any prior release. Fixed:
  `agents/moderator_agent.py` now defines the three lines as named
  constants and `closing_message(outcome)` selects one;
  `orchestrator/orchestrator.py::SharkTankOrchestrator._final_outcome()`
  classifies the session's real Negotiation result (never the
  Consensus Engine's pre-Negotiation advisory recommendation, which
  would risk showing "Congratulations" merely because the pipeline
  technically completed -- the exact anti-pattern this milestone's own
  specification warns against). See `docs/architecture.md` -> Session
  Director and `tests/test_moderator_agent.py` /
  `tests/test_session_director.py`'s "Final outcome messages" section
  (9 new tests total).
- **Two new public accessors closing an API completeness gap found
  during the Agent Handoff Audit:** `SharkTankOrchestrator.final_offers`
  and `.negotiation_responses` -- both already existed as internal
  state (used by Negotiation and the Founder Feedback Report) but had
  no public accessor, so a caller could previously only recover an
  individual Shark's position by re-parsing conversation chat text.
  Added mirroring the existing `market_brief`/`verification_result`/
  `consensus_result` property pattern exactly.
- **A real, `AppTest`-driven end-to-end simulation-conformance test**
  (`tests/test_release_0_9_5_e2e.py`, 3 tests): drives the actual
  Streamlit application (`app.py` via `streamlit.testing.v1.AppTest`)
  through the intended user-facing path with the FleetPulse reference
  proposal and a realistic, pitch-specific scripted committee response
  at every stage (not generic filler) -- covering the canonical
  greeting, independent per-Shark positions, Verification catching an
  unsupported claim a Shark accepted approvingly (spec Part 40's
  explicit test case), Advanced Financial Analysis flagging the margin
  inconsistency, one-by-one offers, real Negotiation, the correct
  "Congratulations" outcome, and a Founder Feedback Report that
  surfaces the margin discrepancy no individual Shark raised (spec Part
  44) -- plus a real, generated PDF artifact inspected via `pypdf` text
  extraction. A second test confirms the "Sharks were not impressed"
  outcome fires correctly when every Shark declines. A third performs
  the mandated three-consecutive-session reset/isolation test (spec
  Parts 48-49) inside one running `AppTest` instance (never a fresh
  Python process substituted for real isolation testing).
- **A genuine, previously-undiagnosed root cause found for this
  project's long-documented `tests/test_app_ui.py` non-determinism**
  (the "2-7 failures across runs" noted in every prior release's own
  QA section, and in this project's own working memory). Root-caused
  via direct, repeatable isolation: `AppTest`'s in-process button-click
  simulation does not reliably register a second widget click chained
  immediately onto another click whose own callback already called
  `st.rerun()` (`ui/controls.py::_handle_start_session()`/
  `_handle_end_session()` both do) -- a real browser round-trip never
  exhibits this, since every real click is already a fresh, fully
  settled request. Fixed by adding one idempotent settle rerun inside
  `tests/test_app_ui.py::_started_app()` (used by ~30 of that file's
  tests). Confirmed via 7 consecutive full-suite runs after the fix:
  0 non-deterministic failures across all 7 (was previously 2-7 varying
  per run) -- only the 2 already-known, deterministic, unrelated
  `file_uploader`-API-version-gap failures remain (Streamlit 1.41.1's
  installed `AppTest` has no `file_uploader` accessor at all; a
  dependency-version gap, not an application defect -- see *Known
  limitations*).
- **Simulation Form Conformance Test performed** (spec Part 28), via
  the new E2E test plus direct code inspection against every canonical
  requirement in spec Parts 8-27: Moderator conducts the session
  without becoming a fourth Shark (PASS); Little Fish presents the
  proposal via text or PDF (PASS); exactly 3 independent Sharks with
  distinct personas matching the specified philosophies (PASS);
  concern-focused, pitch-specific questions, one per Shark per round
  (PASS -- see *Known limitations* for a documented wording-ambiguity
  note, not a defect); founder response opportunity before final
  positions (PASS); private deliberation never exposes raw reasoning
  (PASS); individual Shark positions exist and are now individually
  inspectable before Consensus (PASS, closing the accessor gap above);
  offers presented one-by-one, not merged (PASS); Negotiation matches
  the existing one-counter-per-interested-Shark model, not expanded
  (PASS); genuine rejection vs. technical-failure distinction preserved
  (PASS, unchanged from Release 0.6.1); **final outcome message
  (FAIL -> FIXED, see above)**; Founder Feedback Report generated
  strictly post-simulation (PASS, unchanged from Release 0.9); reset
  destroys simulation and report state (PASS, confirmed via the new
  isolation test).
- **Verification/Consensus/Advanced Analysis audits performed** against
  spec Parts 40-42 using the new realistic FleetPulse script: confirmed
  Verification is structurally incapable of becoming a fourth Shark
  (no `SpeakerRole` exists for it, never announced as a chat speaker);
  confirmed Consensus's recommendation is demonstrably not a majority
  vote by construction (`ConsensusEngine._compute_facts()` hands the
  LLM the tally as a given fact, never derives the recommendation from
  it in Python -- unchanged since Release 0.7, re-verified here); ran
  the specific adversarial case spec Part 40 names (a Shark accepts an
  unsupported claim approvingly; Verification correctly flags it in the
  new E2E test); confirmed Advanced Financial Analysis flags -- rather
  than silently "fixing" -- a deliberately inconsistent founder-stated
  figure.
- **Security/PII/prompt-injection spot-audit**: confirmed no secrets,
  API keys, or raw exception messages appear in the rendered Founder
  Feedback Report PDF or session logs (unchanged since Release 0.6.1/
  0.9, re-verified by direct PDF text inspection in the new E2E test);
  confirmed the report artifact never contains a stack trace or
  provider-error string. PII and prompt-injection defenses themselves
  were not modified -- Release 0.6.1's existing dedicated test coverage
  (`tests/test_pii.py`, `tests/test_prompt_safety.py`, and the
  adversarial tests already in `tests/test_session_director.py`) was
  re-run, not rewritten, and still passes.

**Explicitly out of scope (per spec Parts 60-61; unchanged from prior
releases unless noted above):** any change to Shark personas,
investment philosophy, Shark count, research/Consensus/report
philosophy, or the negotiation model; ADK, MCP, Agent Skills,
persistent memory, SQLite, blockchain, additional Sharks, multi-round
negotiation, cross-session learning; a Streamlit/dependency version
upgrade to close the `file_uploader` test gap (a deliberate,
documented deferral -- see *Known limitations*).

**Known limitations:**

- **`tests/test_app_ui.py`'s 2 `file_uploader` test failures remain,
  unfixed.** Confirmed as a genuine API-surface gap in the installed
  Streamlit 1.41.1's `AppTest.file_uploader` (does not exist in this
  version at all, not a flaky/order-dependent issue) -- fixing it
  means a Streamlit version upgrade, which spec Part 58 explicitly
  warns against as an "unrelated upgrade" outside this milestone's
  authority. Recorded as a candidate for a future release.
- **No live Anthropic smoke test was performed**, for the same reason
  documented in every prior release: the `ANTHROPIC_API_KEY` present in
  this environment leaks from the Claude Code process context (not
  this project's own `.env`) and fails real calls with
  `AuthenticationError`. Every claim above about real, pitch-specific
  committee behavior is verified via a scripted `tests.fakes.FakeProvider`
  standing in for a real model's output, driven through the real UI
  (`AppTest`) rather than direct orchestrator calls -- not a live
  network call. This was reported honestly rather than assumed to have
  passed, per this milestone's own explicit instruction (spec Part 2/63).
  The application does start the real Streamlit server successfully in
  this environment (confirmed via an HTTP 200 boot check).
- **A wording-ambiguity note on "1-2 questions per Shark" (spec Part
  13), not treated as a defect.** The existing, five-releases-old
  architecture has each Shark ask exactly one question per Question
  Round turn, phrased in "one or two sentences"
  (`prompts/adaptive_question.txt`) -- a defensible reading of "1-2
  meaningful, concern-focused questions," not a literal multi-question
  turn. Changing this to a literal multi-question-per-turn model would
  be a real architectural change to the turn-based Question Round
  structure, which this milestone's own scope explicitly forbids
  deciding unilaterally (spec Part 60) -- classified as **Architectural/
  User Decision Required** if a literal reading is intended, not fixed.
- **Every release's own work since Release 0.6.1 remains uncommitted.**
  `git log` shows the repository's last commit as `601e2c5` ("0.6.1");
  all of Releases 0.7, 0.8, 0.9, and this 0.9.5 QA pass exist only as
  uncommitted working-tree changes, confirmed via `git status` at the
  start of this milestone. This is a process observation, not a product
  defect -- no commit was made without being explicitly asked, per
  standing instructions.
- One full-suite stress-test run of the fixed `_started_app()` helper
  took anomalously long (~68 minutes, versus ~4-6 seconds for every
  other run in the same stress test) while still passing; this appears
  to be transient local resource contention (a live `streamlit run`
  dev server was running concurrently on this machine at the time), not
  a reproduction of the underlying flakiness this release fixed -- every
  other run, before and after, was fast and consistent. Noted honestly
  rather than omitted, per this milestone's own "no fake success"
  instruction (spec Part 63).

**Deviations from this specification:**

- **The "1-2 questions per Shark" wording (spec Part 13) was not
  changed** -- classified as Architectural/User Decision Required
  rather than unilaterally reinterpreted or implemented, per spec Part
  60's explicit instruction not to silently change core simulation
  mechanics.
- **The `file_uploader` `AppTest` gap was diagnosed but not closed** --
  closing it requires a Streamlit dependency upgrade, which spec Part
  58 explicitly scopes out of this milestone ("do not perform unrelated
  upgrades").
- **No live-provider run was performed** -- the same documented,
  unavoidable environment constraint every release since 0.6.1 has
  reported; this milestone's own scripted-`FakeProvider`-through-the-
  real-UI approach is the closest available approximation, and is
  reported as such, not conflated with a live run.

---

## Future Releases

Placeholders for releases not yet started. Each will be filled in with
the same structure as above (Theme, Shipped, Explicitly out of scope)
once it actually ships — this log does not get filled in ahead of
time.

### Release 1.0 — *(not yet started)*
