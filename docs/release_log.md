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

## Future Releases

Placeholders for releases not yet started. Each will be filled in with
the same structure as above (Theme, Shipped, Explicitly out of scope)
once it actually ships — this log does not get filled in ahead of
time.

### Release 0.4 — *(not yet started)*

### Release 0.5 — *(not yet started)*

### Release 1.0 — *(not yet started)*
