# Shark Tank AI

An AI multi-agent Streamlit application where founders pitch their
startup idea to a panel of AI "shark" investor agents that evaluate,
question, and negotiate a deal.

> **Status:** Production-ready project scaffold. Configuration,
> logging, folder structure, interfaces, and the Streamlit UI shell are
> all in place and fully functional. Agent, orchestration, and provider
> **business logic** have not been implemented yet — every domain class
> currently raises `NotImplementedError` where real behavior will go.
> The application starts and runs successfully as-is.

## Features (scaffold)

- ✅ Streamlit UI shell (sidebar + home page) that renders with zero configuration
- ✅ Centralized, environment-driven configuration (`pydantic-settings`)
- ✅ Centralized logging (console + optional rotating file handler)
- ✅ Clean layered architecture with abstract interfaces for agents, providers, and memory
- ✅ Pydantic data models for pitches, sharks, offers, and negotiation sessions
- ✅ Test suite covering configuration, logging, and structural smoke tests
- ✅ Docker + Docker Compose setup
- ⬜ Agent evaluation logic (not yet implemented)
- ⬜ Orchestrator negotiation logic (not yet implemented)
- ⬜ LLM provider integrations (not yet implemented)

## Project Structure

```
shark-tank-ai/
├── agents/          # Shark agent implementations (BaseAgent, SharkAgent)
├── orchestrator/     # Coordinates the panel of agents for a pitch
├── providers/        # LLM provider integrations (Anthropic, etc.)
├── memory/           # Pluggable session/negotiation memory backends
├── models/           # Shared pydantic data models
├── prompts/          # Prompt templates (plain text) + loader
├── ui/               # Streamlit UI components (sidebar, home page)
├── config/           # Settings (pydantic-settings) + logging config
├── utils/            # Small shared helpers (IDs, formatting)
├── tests/            # Test suite
├── docs/             # Architecture and getting-started docs
├── docker/           # Dockerfile + .dockerignore
├── app.py            # Streamlit entry point
├── pyproject.toml
├── requirements.txt
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## Requirements

- Python 3.12

## Quick Start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

The app is designed to **start successfully with no configuration at
all** — no `.env` file and no API keys required. Missing LLM
credentials simply surface as a warning in the sidebar rather than
crashing the app.

## Running with Docker

```bash
docker compose up --build
```

Then open `http://localhost:8501`.

- The project directory is bind-mounted into the container, so code
  changes on your host are picked up live (Streamlit's file watcher is
  enabled) — no rebuild needed for most changes, only when
  `requirements.txt` changes.
- `.env` is loaded automatically if present, but it's optional — the
  container starts successfully even without one. To use one:
  `cp .env.example .env` before running `docker compose up`.
- Stop the app with `Ctrl+C`, or `docker compose down` to also remove
  the container.

## Running Tests

```bash
pytest
```

## Configuration

All settings are defined in `config/settings.py` and can be overridden
via environment variables or a `.env` file — see `.env.example` for
the full list (app name/env, server host/port, log level, LLM
provider/model, API keys, memory backend, feature flags).

Logging is configured once, centrally, in `config/logging_config.py`
and initialized at startup by `app.py`. It writes structured logs to
the console by default, with an optional rotating file handler
(`LOG_TO_FILE=true`).

## Documentation

See [docs/architecture.md](docs/architecture.md) for the system's
architecture (the single source of truth as of Release 0.3.5) and
[docs/getting_started.md](docs/getting_started.md) for a setup
walkthrough. Additional engineering documentation:

- [docs/folder_structure.md](docs/folder_structure.md) — purpose,
  responsibility, and ownership of every project folder.
- [docs/state_machines.md](docs/state_machines.md) — the User Session
  and Agent Orchestration state machines.
- [docs/event_catalog.md](docs/event_catalog.md) — every planned Event
  Bus message.
- [docs/agent_contract.md](docs/agent_contract.md) — the common
  interface every agent must implement.
- [docs/coding_standards.md](docs/coding_standards.md) — engineering
  standards for this codebase.
- [docs/release_log.md](docs/release_log.md) — what shipped in each
  release.

## Roadmap

- [ ] Implement `providers/anthropic_provider.py` against the real Anthropic SDK
- [ ] Implement `agents/shark_agent.py` pitch evaluation logic
- [ ] Implement `orchestrator/orchestrator.py` multi-agent negotiation flow
- [ ] Implement a persistent `memory` backend (SQLite / Redis)
- [ ] Flesh out `ui/home.py` to submit real pitches and display results
- [ ] Expand test coverage to agent/orchestrator behavior once implemented
