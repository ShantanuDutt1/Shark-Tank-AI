# Folder Structure

This document describes the project's folders **exactly as they exist
today**. No folder listed here is proposed or planned — every one of
them is already present in the repository. Where a folder currently
holds only interfaces or placeholders rather than working logic, that
is stated explicitly rather than implied.

For what each folder's contents mean *architecturally*, see
[`architecture.md`](architecture.md). This document is about
ownership and boundaries, not behavior.

---

## Project Root

**Contents:** `app.py`, `pyproject.toml`, `requirements.txt`,
`docker-compose.yml`, `README.md`, `.env.example`, `.gitignore`,
`.dockerignore`.

- **Purpose:** Entry point and project-wide configuration.
- **Responsibility:** `app.py` wires together settings, logging, and
  `ui/layout.py` — it must never contain UI, agent, or business logic
  itself. `pyproject.toml` and `requirements.txt` declare
  dependencies; they must stay in sync with each other.
- **Ownership:** Whoever changes the dependency set or the entry-point
  wiring. Not owned by any single feature area.
- **Future expansion:** None expected. If the entry point ever needs
  to grow beyond a thin wiring layer, that logic belongs in a package,
  not in `app.py`.

## `agents/`

**Contents (current as of Release 0.9):** `base_agent.py` (`BaseAgent`
interface), `shark_agent.py` (`SharkAgent` — real
`ask_question()`/`evaluate_pitch()`/`deliberate()`/`negotiate()`),
`moderator_agent.py` (`ModeratorAgent` — real
`validate_and_extract()` plus deterministic narration; does not
subclass `BaseAgent`), `market_research_agent.py`
(`MarketResearchAgent`, Release 0.6), `research_planner.py`
(`build_research_plan()`, Release 0.6.1), `verification_agent.py`
(`VerificationAgent`, Release 0.7 — also does not subclass
`BaseAgent`, for the same reason as `ModeratorAgent`/
`MarketResearchAgent`), `financial_analyst.py` (`FinancialAnalyst`,
Release 0.8 — extracts financial facts and computes deterministic
financial analysis; also does not subclass `BaseAgent`, same reason),
`founder_feedback_agent.py` (`FounderFeedbackAgent`, Release 0.9 —
synthesizes the full simulation into a `FounderFeedbackReport`; also
does not subclass `BaseAgent`, same reason), `prompt_formatting.py`
(Release 0.7 — shared prompt-rendering helpers extracted from
`shark_agent.py`, reused by `verification_agent.py`,
`financial_analyst.py`, `founder_feedback_agent.py`, and
`orchestrator/consensus_engine.py`), `prompt_safety.py` (Release 0.6).

- **Purpose:** Houses every agent that participates in a session.
- **Responsibility:** Every class here must implement the contract
  defined in [`agent_contract.md`](agent_contract.md), with the
  documented exception of `ModeratorAgent`/`MarketResearchAgent`/
  `VerificationAgent`/`FinancialAnalyst`/`FounderFeedbackAgent` (none
  evaluates a pitch and produces an `Offer`). Agents may depend on
  `models/`, `providers/`, `utils/`, and `prompts/`; they must not
  depend on `ui/`.
- **Ownership:** Backend/agent-logic work.
- **Future expansion:** `docs/state_machines.md` § Rule 3's
  Verification-failure retry path remains unimplemented; see
  `docs/architecture.md` -> Future Extension Points.

## `config/`

**Contents:** `settings.py` (pydantic-settings `Settings` model,
`get_settings()`), `logging_config.py` (stdlib `dictConfig` setup,
`setup_logging()`, `get_logger()`).

- **Purpose:** The single source of truth for application
  configuration and logging setup.
- **Responsibility:** Every other package reads configuration through
  `config.settings.get_settings()` — never through `os.environ`
  directly. Every module that logs uses
  `config.logging_config.get_logger(__name__)`. `Settings` fields must
  all have safe defaults so the app starts with zero configuration.
- **Ownership:** Whoever introduces a new configurable value or
  changes logging behavior.
- **Future expansion:** New settings fields as new backend pieces
  (Gemini/Ollama providers, SQLite memory, Event Bus) are implemented.
  No new files are anticipated in this folder beyond the existing two.

## `docker/`

**Contents:** `Dockerfile`.

- **Purpose:** Container build definition for the Streamlit
  application.
- **Responsibility:** Must stay in sync with `requirements.txt` (the
  layer that installs dependencies) and with the port/command expected
  by `docker-compose.yml` at the project root.
- **Ownership:** Whoever changes how the app is built or run in a
  container.
- **Future expansion:** None anticipated. `.dockerignore` lives at the
  project root (not inside this folder), because it must match the
  build context, which is the project root.

## `docs/`

**Contents:** `architecture.md`, `folder_structure.md`,
`state_machines.md`, `event_catalog.md`, `agent_contract.md`,
`agent_personas.md`, `coding_standards.md`, `release_log.md`,
`release_backlog.md`, `getting_started.md`,
`investor_evaluation_framework.md` (Release 0.9 — real, cited research
underlying the Founder Feedback Report's prompt; see
`architecture.md` → *Founder Feedback Report*).

- **Purpose:** All project documentation.
- **Responsibility:** `architecture.md` is the single source of truth
  for system design; every other document here must stay consistent
  with it. Documentation changes that alter architecture require the
  same scrutiny as a code change — see `release_log.md` for when the
  architecture was locked.
- **Ownership:** Whoever is proposing or recording an architectural or
  process decision.
- **Future expansion:** Additional focused documents (e.g., a
  deployment runbook) may be added here as needed; this document
  should be updated to describe them when they are.

## `memory/`

**Contents:** `base_memory.py` (interface), `in_memory_store.py`
(placeholder implementation).

- **Purpose:** Pluggable persistence for conversation and negotiation
  state.
- **Responsibility:** Every backend must implement `BaseMemory`
  (`save`, `load`, `history`, `clear`). The active backend is selected
  via `Settings.memory_backend`, never hardcoded by a caller.
  Current state: both `save`, `load`, `history`, and `clear` on
  `InMemoryStore` raise `NotImplementedError`.
- **Ownership:** Backend/persistence work.
- **Future expansion:** A SQLite-backed implementation, selected when
  `memory_backend` is set to `"sqlite"`, using `Settings.database_url`.

## `models/`

**Contents (current as of Release 0.9):** `schemas.py` (pydantic
domain models: `Pitch`, `SharkPersona`, `Offer`, `NegotiationSession`,
`DealStatus`, `ConversationMessage`, `TurnState`, `MarketRealityBrief`
and friends (Release 0.6), `VerificationResult`/`ConsensusResult` and
friends (Release 0.7), `FinancialAnalysisResult` and friends (Release
0.8 — `FinancialFact`, `ConsistencyFinding`, `RiskFactor`,
`UpsideFactor`, `ScenarioValuation`), `FounderFeedbackReport` and
friends (Release 0.9 — `InvestorReadinessDimension`, `ActionItem`,
`ReportEvidenceRef`)), `enums.py` (`SessionPhase` (twelve phases,
unchanged since Release 0.8 — the Founder Feedback Report deliberately
did not add a thirteenth; see `architecture.md` → *Founder Feedback
Report*), `LLMProvider`, `SpeakerRole`, and their label/ordering
dictionaries).

- **Purpose:** Shared data shapes and vocabulary used by every other
  package — the UI, agents, orchestrator, and memory all reference the
  same definitions rather than each defining their own.
- **Responsibility:** No business logic belongs here — only data
  structure and pure lookup tables (like `PHASE_LABELS`). Anything
  that reads or writes these models lives elsewhere.
- **Ownership:** Shared; changes here affect every other package, so
  they should be made deliberately and reviewed against
  `architecture.md` and `state_machines.md` for consistency.
- **Future expansion:** New enum values must never be added without
  updating `state_machines.md` and `event_catalog.md` to match.

## `orchestrator/`

**Contents (current as of Release 0.9):** `orchestrator.py`
(`SharkTankOrchestrator` — the Session Director; `run_pitch()` still a
placeholder, `start_session()` / `submit_founder_response()` /
`end_session()` implemented; as of Release 0.9, `_complete_session()`
also generates the session's `FounderFeedbackReport` as its first
step, exposed via the new `founder_report` property), `event_bus.py`
(`EventBus`, minimal
synchronous pub/sub), `events.py` (a typed dataclass per
`event_catalog.md` message), `turn_controller.py` (`TurnController`,
the fixed Shark/Founder speaking-order sequencer),
`negotiation_controller.py` (`NegotiationController`, Release 0.6),
`consensus_engine.py` (`ConsensusEngine`, Release 0.7, extended in
Release 0.8 with business/deal-quality reconciliation — real
reconciliation of Shark positions, financial analysis, and
Verification findings; not an `agents/` class, since it has no
investment philosophy and never evaluates a pitch itself, see
`agent_contract.md`), `exceptions.py` (`SessionDirectorError`,
`InvalidTurnError`).

- **Purpose:** Coordinates multiple agents for a single session — the
  Session Director described in `architecture.md`.
- **Responsibility:** Depends on `agents/`, `models/`, `utils/`, and
  (in the future) `memory/`; must never depend on `ui/`. Owns the
  *sequencing* of agent calls and phase transitions, not the agents'
  individual behavior.
  Current state: `run_pitch()` raises `NotImplementedError`; the
  Session Director surface (`start_session()`,
  `submit_founder_response()`, `end_session()`, and the `phase()` /
  `conversation()` / `market_brief()` / `financial_analysis()` /
  `verification_result()` / `consensus_result()` /
  `awaiting_founder_response()` properties) is implemented.
- **Ownership:** Backend/orchestration work.
- **Future expansion:** `docs/state_machines.md` § Rule 3's
  Verification-failure retry path (bounded bounce-back to Internal
  Deliberation) remains unimplemented; driving the Agent Orchestration
  State Machine defined in `state_machines.md` also remains planned.

## `prompts/`

**Contents (current as of Release 0.9):** `loader.py`
(`load_prompt(name)`), `shark_persona_system.txt`,
`pitch_analysis.txt`, `adaptive_question.txt`, `deliberation.txt`,
`negotiation.txt`, `proposal_validation.txt`,
`market_research_search.txt`, `market_research_synthesis.txt`,
`verification.txt` (Release 0.7), `consensus.txt` (Release 0.7),
`financial_analysis.txt` (Release 0.8), `founder_feedback.txt`
(Release 0.9).

- **Purpose:** Keeps prompt text out of Python source, so prompts can
  be edited, reviewed, and versioned independently of code.
- **Responsibility:** Every prompt is a plain-text `.txt` file loaded
  by name through `prompts.loader.load_prompt()` — no module should
  read a prompt file directly or embed prompt text as a Python string
  literal. See [`coding_standards.md`](coding_standards.md) → *Prompt
  Management*.
- **Ownership:** Whoever is tuning agent behavior/persona.
- **Future expansion:** Additional templates for the Moderator,
  Verification Agent, and Consensus Engine as they're implemented.

## `providers/`

**Contents:** `base_provider.py` (interface), `anthropic_provider.py`
(placeholder implementation).

- **Purpose:** Thin, swappable wrappers around LLM APIs, isolating
  every other package from provider-specific SDK details.
- **Responsibility:** Every provider implements `BaseProvider`
  (`generate()`, `is_configured`). Agents depend on `BaseProvider`,
  never on a concrete provider class directly.
  Current state: `AnthropicProvider.generate()` raises
  `NotImplementedError`.
- **Ownership:** Backend/integration work.
- **Future expansion:** `GeminiProvider` and `OllamaProvider` classes
  are expected here to close the known gap recorded in
  `architecture.md` (the sidebar already offers both as options).
  This is also the most likely home for MCP tool access and
  ADK-managed execution, per `architecture.md`.

## `tests/`

**Contents:** `conftest.py`, `test_config.py`,
`test_logging_config.py`, `test_smoke.py`, and, added in Release 0.4,
`test_event_bus.py`, `test_turn_controller.py`,
`test_session_director.py`.

- **Purpose:** Automated verification of configuration, logging,
  structural integrity (every package imports cleanly), and, as of
  Release 0.4, the Session Director's orchestration behavior (session
  lifecycle, turn control, input-locking state, Event Bus ordering).
- **Responsibility:** Tests must not depend on real network access,
  real API keys, or a running Streamlit server. `conftest.py`'s
  autouse fixture clears the settings cache between tests so each test
  gets a fresh `Settings` instance.
- **Ownership:** Shared; every package that adds behavior should add
  corresponding tests here (or in a same-named submodule if this
  folder grows subpackages).
- **Future expansion:** Test coverage for providers and memory once
  their `NotImplementedError` placeholders are replaced with real
  logic, and for `SharkAgent.evaluate_pitch()` once Release 0.5
  implements it.

## `ui/`

**Contents:** `layout.py` (page composition), `session_state.py`
(session state model — as of Release 0.4, also `build_pitch_from_state()`
and `sync_from_director()`, the read/sync helpers every other component
uses instead of talking to the Session Director's state directly),
`styles.py` (shared CSS), `header.py`, `sidebar.py`, `proposal.py`
(as of Release 0.9, also `_render_founder_report_section()` — the
Founder Feedback Report download, gated on
`SessionPhase.SESSION_COMPLETE` and a real `founder_report`),
`conversation.py`, `response.py`, `controls.py`.

- **Purpose:** Every Streamlit-facing component. This is the only
  package allowed to `import streamlit`.
- **Responsibility:** All state lives in `st.session_state`, defined
  once in `session_state.py` — no other module in this folder invents
  its own state key. `layout.py` is the only place components are
  composed together; individual components do not import each other
  directly (as of Release 0.4, `controls.py` and `response.py` import
  `orchestrator.orchestrator.SharkTankOrchestrator` and
  `session_state.py`'s helpers, not one another). See
  [`coding_standards.md`](coding_standards.md) → *Session State*.
- **Ownership:** Frontend work.
- **Future expansion:** New components as new phases of the User
  Session State Machine gain dedicated UI (e.g., a Verification
  detail view, a Consensus rationale panel) — always added as their
  own module and wired in through `layout.py`, following the existing
  pattern.

## `utils/`

**Contents (current as of Release 0.9):** `ids.py` (`new_id()`),
`formatting.py` (`format_currency()`, `format_percentage()`),
`pii.py` (`anonymize_pii()`, Release 0.6.1), `pdf_extraction.py`
(`extract_pdf_text()`, Release 0.6), `financial_calculations.py`
(Release 0.8 — deterministic implied-valuation/multiple/margin/
growth/burn/runway/dilution calculations; used by
`agents/financial_analyst.py`, never by an LLM prompt),
`report_rendering.py` (`render_founder_report_pdf()`, Release 0.9 —
pure PDF rendering of an already-generated `FounderFeedbackReport` via
`reportlab`, entirely in memory; no provider calls, no filesystem
writes).

- **Purpose:** Small, dependency-free helper functions with no
  business logic and no dependency on any other project package.
- **Responsibility:** Anything added here must be a pure function with
  no side effects and no imports from `ui/`, `agents/`, `orchestrator/`,
  `providers/`, or `memory/`. If a helper needs any of those, it
  belongs in that package instead, not here.
- **Ownership:** Shared; low-risk, low-review-overhead additions.
- **Future expansion:** Additional pure formatting/ID helpers as
  needed. This folder should stay small — if it starts accumulating
  logic specific to one domain (e.g., pitch-specific formatting), that
  logic should move to the package that owns that domain.
