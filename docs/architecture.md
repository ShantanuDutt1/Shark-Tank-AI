# Architecture Overview

## Project

**Shark Tank AI** is a Streamlit-based multi-agent application in which
a founder submits a startup pitch and a panel of AI "shark" investor
agents evaluate it, ask questions, and negotiate a deal.

> **Status:** This document describes the intended architecture. The
> current codebase is a production-ready *scaffold*: configuration,
> logging, folder structure, and interfaces are all in place, but no
> agent, orchestration, or provider logic has been implemented yet.

## Layers

- **ui/** — Streamlit page and component rendering. Talks only to
  `config` and (eventually) `orchestrator`. Never calls providers or
  agents directly.
- **orchestrator/** — Coordinates the panel of shark agents for a given
  pitch: fan-out evaluation requests, collect offers, run negotiation
  rounds, and produce a final `NegotiationSession`.
- **agents/** — Individual shark agents (and any support agents, e.g.
  a valuation or pitch-analysis agent). Each agent uses a `providers`
  implementation to talk to an LLM and a `SharkPersona` to stay in
  character.
- **providers/** — Thin, swappable wrappers around LLM APIs (Anthropic,
  OpenAI, etc.), all implementing a common `BaseProvider` interface.
- **memory/** — Pluggable storage for conversation/negotiation state,
  behind a common `BaseMemory` interface. Defaults to an in-memory
  backend so the app runs with zero external dependencies.
- **models/** — Shared pydantic schemas (`Pitch`, `SharkPersona`,
  `Offer`, `NegotiationSession`) used across all layers.
- **prompts/** — Plain-text prompt templates, loaded via
  `prompts/loader.py`, kept separate from Python code.
- **config/** — Centralized `Settings` (pydantic-settings) and
  `logging_config` (stdlib `dictConfig`). Every other layer reads
  configuration from here rather than `os.environ` directly.
- **utils/** — Small, dependency-free helpers (ID generation, currency
  formatting) shared across layers.

## Data Flow (once implemented)

1. Founder submits a pitch via the Streamlit UI (`ui/home.py`).
2. `orchestrator.SharkTankOrchestrator.run_pitch()` receives the
   `Pitch` and dispatches it to each configured `SharkAgent`.
2. Each `SharkAgent` uses its `SharkPersona`, a prompt template from
   `prompts/`, and a `BaseProvider` implementation to produce an
   `Offer`.
4. The orchestrator aggregates offers into a `NegotiationSession` and
   may run further negotiation rounds.
5. Session state is persisted via a `BaseMemory` implementation.
6. Results are rendered back in the Streamlit UI.

## Design Principles

- Every layer depends only on abstractions (`BaseAgent`,
  `BaseProvider`, `BaseMemory`), never on concrete implementations of
  sibling layers, so backends and providers can be swapped freely.
- The application must start successfully with **zero** configuration:
  no `.env` file, no API keys, no external services. Missing
  credentials should degrade gracefully (a visible warning in the UI),
  never crash the app.
