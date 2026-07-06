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

**Contents:** `base_agent.py` (interface), `shark_agent.py`
(placeholder implementation).

- **Purpose:** Houses every agent that participates in a session —
  currently the Shark Agent; in the future, the Moderator,
  Verification Agent, and any other agent described in
  `architecture.md`.
- **Responsibility:** Every class here must implement the contract
  defined in [`agent_contract.md`](agent_contract.md). Agents may
  depend on `models/`, `providers/`, and `prompts/`; they must not
  depend on `ui/`.
  Current state: `BaseAgent.evaluate_pitch()` and
  `SharkAgent.evaluate_pitch()` both raise `NotImplementedError`.
- **Ownership:** Backend/agent-logic work.
- **Future expansion:** A `ModeratorAgent` class and a
  `VerificationAgent` class are both expected here, each following the
  same contract as `SharkAgent`.

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
`coding_standards.md`, `release_log.md`, `getting_started.md`.

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

**Contents:** `schemas.py` (pydantic domain models: `Pitch`,
`SharkPersona`, `Offer`, `NegotiationSession`, `DealStatus`),
`enums.py` (`SessionPhase`, `LLMProvider`, `SpeakerRole`, and their
label/ordering dictionaries).

- **Purpose:** Shared data shapes and vocabulary used by every other
  package — the UI, agents, orchestrator, and memory all reference the
  same definitions rather than each defining their own.
- **Responsibility:** No business logic belongs here — only data
  structure and pure lookup tables (like `PHASE_LABELS`). Anything
  that reads or writes these models lives elsewhere.
- **Ownership:** Shared; changes here affect every other package, so
  they should be made deliberately and reviewed against
  `architecture.md` and `state_machines.md` for consistency.
- **Future expansion:** New domain models as new backend concepts
  (Verification results, Consensus outcomes) are implemented. New
  enum values must never be added without updating
  `state_machines.md` and `event_catalog.md` to match.

## `orchestrator/`

**Contents:** `orchestrator.py` (`SharkTankOrchestrator`, placeholder
implementation).

- **Purpose:** Coordinates multiple agents for a single session — the
  seed of the future Session Director and Consensus Engine described
  in `architecture.md`.
- **Responsibility:** Depends on `agents/`, `models/`, and (in the
  future) `memory/`; must never depend on `ui/`. Owns the *sequencing*
  of agent calls, not the agents' individual behavior.
  Current state: `run_pitch()` raises `NotImplementedError`.
- **Ownership:** Backend/orchestration work.
- **Future expansion:** This is the most likely home for the Session
  Director and Consensus Engine responsibilities described in
  `architecture.md`, and for driving the Agent Orchestration State
  Machine defined in `state_machines.md`.

## `prompts/`

**Contents:** `loader.py` (`load_prompt(name)`),
`shark_persona_system.txt`, `pitch_analysis.txt`,
`negotiation_round.txt`.

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
`test_logging_config.py`, `test_smoke.py`.

- **Purpose:** Automated verification of configuration, logging, and
  structural integrity (every package imports cleanly).
- **Responsibility:** Tests must not depend on real network access,
  real API keys, or a running Streamlit server. `conftest.py`'s
  autouse fixture clears the settings cache between tests so each test
  gets a fresh `Settings` instance.
- **Ownership:** Shared; every package that adds behavior should add
  corresponding tests here (or in a same-named submodule if this
  folder grows subpackages).
- **Future expansion:** Test coverage for agents, orchestrator, and
  providers once their `NotImplementedError` placeholders are replaced
  with real logic.

## `ui/`

**Contents:** `layout.py` (page composition), `session_state.py`
(session state model), `styles.py` (shared CSS), `header.py`,
`sidebar.py`, `proposal.py`, `conversation.py`, `response.py`,
`controls.py`.

- **Purpose:** Every Streamlit-facing component. This is the only
  package allowed to `import streamlit`.
- **Responsibility:** All state lives in `st.session_state`, defined
  once in `session_state.py` — no other module in this folder invents
  its own state key. `layout.py` is the only place components are
  composed together; individual components do not import each other
  directly. See [`coding_standards.md`](coding_standards.md) →
  *Session State*.
- **Ownership:** Frontend work.
- **Future expansion:** New components as new phases of the User
  Session State Machine gain dedicated UI (e.g., a Verification
  detail view, a Consensus rationale panel) — always added as their
  own module and wired in through `layout.py`, following the existing
  pattern.

## `utils/`

**Contents:** `ids.py` (`new_id()`), `formatting.py`
(`format_currency()`, `format_percentage()`).

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
