# Shark Tank AI

A turn-based, multi-agent Streamlit application where a founder pitches
a startup to an AI investment committee — a neutral Moderator plus
three Shark investor personas (Conservative, Growth, Balanced) — gets
questioned one Shark at a time, watches the committee deliberate
privately, and receives a session outcome.

> **Status: Release 0.6.1 — Hardening, Research Integrity & Failure
> Semantics**, on top of Release 0.6's Market Reality, Proposal
> Validation, Safety, Structured Extraction, and Negotiation. The
> session flow is unchanged: Founder Proposal → Moderator Validation &
> Extraction → Market Reality Research → Shark Analysis → Shark
> Questions → Internal Deliberation → Initial Offers → Negotiation →
> Final Outcome. Every stage from validation onward uses real,
> provider-backed reasoning — not deterministic templates — with a
> graceful, clearly-labeled fallback at every step if the provider is
> unconfigured or fails, so the app always keeps running; as of
> Release 0.6.1, that fallback is also never mistakable for a genuine
> investment decision (see *What Works Today* below). See *Current
> Limitations* below and [docs/release_log.md](docs/release_log.md)
> for exactly what shipped in each release.

## What Works Today

- **A real chat session**, grounded in external evidence. Enter a
  proposal, click Start, and the Moderator validates and extracts
  structured details from it, the committee researches the market
  before questioning you, each Shark asks a question informed by that
  research and its own persona, and your responses appear in the
  transcript — rendered with Streamlit's native `st.chat_message` /
  `st.chat_input`, not a static mockup.
- **A full session lifecycle**, driven entirely by the backend, not
  the UI: Idle → Proposal Upload → Validation → Market Research →
  Question Round → Internal Deliberation → Verification → Consensus →
  Investment Decision → Negotiation → Session Complete, plus a clean
  reset back to Idle.
- **Real Moderator validation & extraction.** An LLM call decides
  whether a submission is a legitimate business proposal (missing
  revenue/customers/financials is never itself a rejection reason) and
  extracts founder name, company name, ask amount, equity, and implied
  valuation where stated.
- **Real, planned Market Reality Research.** A deterministic
  research-planning step first classifies the pitch's business model
  (SaaS, consumer, marketplace, restaurant, cleantech, professional
  services, or a conservative generic plan when uncertain) into 3-8
  targeted evidence categories, then gathers real web search results
  per category (Anthropic's server-side search tool), and synthesizes
  them into an uncertainty-aware brief — market size, competitors,
  financial benchmarks, comparable transactions — that distinguishes
  founder claims from externally-reported evidence, tags each source's
  reliability and each claim's validation status, flags conflicting
  evidence instead of silently picking one source, and never fabricates
  a valuation range (or a founder-implied valuation, now computed
  deterministically) when the evidence doesn't support one. A failed
  research category doesn't discard the rest — partial evidence is
  preserved and the gap disclosed.
- **Real Shark investment intelligence.** Each of the three personas
  (Conservative, Growth, Balanced) independently asks pitch-adaptive
  questions, forms a real structured evaluation, deliberates
  (disagreement included) in at most two sentences each, and makes its
  own real offer or declines — per
  [docs/agent_personas.md](docs/agent_personas.md). All three Sharks
  always evaluate against the identical research evidence.
- **Real Negotiation.** The founder gets one counter-offer turn with
  each Shark who made an offer; that Shark independently accepts,
  rejects, or modifies.
- **A technical failure is never presented as a decision.** If a
  Shark's evaluation or negotiation response fails for a provider
  reason, the founder sees an honest "evaluation was unavailable" /
  "could not process your counter-offer" message — never a fabricated
  pass, decline, or walk-away.
- **PII redaction and prompt-injection defense.** Emails, phone
  numbers, and street addresses are redacted from the proposal before
  anything else sees it, from the Moderator's own extracted fields
  before they enter session state, and from every founder Question
  Round answer and negotiation counter-offer before they're stored or
  reach any Shark prompt; all founder-authored and web-retrieved
  content is architecturally wrapped as untrusted data in every prompt
  (see [docs/architecture.md](docs/architecture.md) → *Security*).
- **Turn-gated founder input.** The chat input is only usable when it
  is genuinely the founder's turn; it locks while the Moderator, a
  Shark, or research is "speaking"/running.
- **Text or PDF proposal input**, with real PDF text extraction
  (Audio/Video were removed — they were never processed by anything
  and only implied support that didn't exist).

## What's a Placeholder Today

- **No formal cross-Shark consensus.** Each Shark's evaluation, offer,
  and negotiation is real and independent, but there is no real
  Consensus Engine combining all three into one final aggregated
  decision — Verification and Consensus remain deterministic
  pass-through phases (Release 0.7 scope).
- **No multi-round negotiation.** Exactly one counter-offer per
  interested Shark; no counter-to-a-counter, and `SharkTankOrchestrator
  .run_pitch()` (a full negotiation across an arbitrary agent list)
  still raises `NotImplementedError`.
- **No persistence.** Ending the Python process loses every session;
  every `BaseMemory` method still raises `NotImplementedError`.
- **Security is best-effort, not comprehensive.** PII redaction is
  regex-based (three identifier types — Release 0.6.1 widened *where*
  it's applied, not *what* it detects); prompt-injection defense is
  architectural wrapping plus a secondary pattern filter, not a
  guarantee an LLM never follows an embedded instruction. See
  [docs/architecture.md](docs/architecture.md) → *Security* for
  documented limitations.
- **Research provenance is heuristic, not independently verified.**
  Source reliability is a domain-hostname heuristic, and retrieved
  URLs are exactly as self-reported by the model — this codebase never
  independently re-fetches or verifies a source. Business-model
  classification for research planning is a small keyword heuristic,
  not a general industry taxonomy or an LLM classifier.

See [docs/release_backlog.md](docs/release_backlog.md) for the full
roadmap.

## Project Structure

```
shark-tank-ai/
├── agents/          # ModeratorAgent, SharkAgent, MarketResearchAgent, prompt_safety
├── orchestrator/     # SharkTankOrchestrator (Session Director), EventBus, TurnController, NegotiationController
├── providers/        # BaseProvider + AnthropicProvider; BaseResearchProvider + AnthropicResearchProvider
├── memory/           # Pluggable session/negotiation memory backends (placeholder)
├── models/           # Shared pydantic data models (Pitch, Offer, MarketRealityBrief, ConversationMessage, ...)
├── prompts/          # Prompt templates (plain text) + loader
├── ui/               # Streamlit UI components (chat, proposal intake, controls, session state)
├── config/           # Settings (pydantic-settings) + logging config
├── utils/            # Small shared helpers (IDs, PII redaction, PDF extraction, formatting)
├── tests/            # Unit tests + Streamlit AppTest integration tests
├── docs/             # Architecture and process documentation
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

The app **starts successfully with no configuration at all** — no
`.env` file and no API keys required. Without `ANTHROPIC_API_KEY` set,
every stage (validation, research, questions, evaluation, deliberation,
offers, negotiation) automatically falls back to a deterministic
placeholder rather than failing, so the full session lifecycle still
works end to end; set `ANTHROPIC_API_KEY` in `.env` for real,
provider-backed reasoning throughout.

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

The suite includes direct unit tests of the Session Director, Event
Bus, Turn/Negotiation Controllers, providers, agents, PII redaction,
prompt-injection helpers, and PDF extraction, plus full-application
integration tests that drive `app.py` itself via Streamlit's `AppTest`
harness (`tests/test_app_ui.py`) — none require a browser, live
network access, or an API key. `tests/fakes.py` provides
`FakeProvider` and `MockResearchProvider`, deterministic offline test
doubles for both provider abstractions.

## Configuration

All settings are defined in `config/settings.py` and can be overridden
via environment variables or a `.env` file — see `.env.example` for
the full list (app name/env, server host/port, log level, LLM
provider/model, API keys, memory backend, feature flags).

**Provider status:** Anthropic is the real, active provider (see
`providers/anthropic_provider.py`); the sidebar's Gemini/Ollama options
are explicitly labeled "not implemented yet" and do nothing. The same
`ANTHROPIC_API_KEY` also powers Market Reality Research, via
Anthropic's server-side web search tool (`providers
/anthropic_research_provider.py`) — no separate search API key is
needed or supported.

Logging is configured once, centrally, in `config/logging_config.py`
and initialized at startup by `app.py`. It writes structured logs to
the console by default, with an optional rotating file handler
(`LOG_TO_FILE=true`).

## Documentation

See [docs/architecture.md](docs/architecture.md) for the system's
architecture (kept current release-over-release; see its own status
markers per section) and [docs/getting_started.md](docs/getting_started.md)
for a setup walkthrough. Additional engineering documentation:

- [docs/folder_structure.md](docs/folder_structure.md) — purpose,
  responsibility, and ownership of every project folder.
- [docs/state_machines.md](docs/state_machines.md) — the User Session
  and Agent Orchestration state machines.
- [docs/event_catalog.md](docs/event_catalog.md) — every Event Bus
  message, implemented and planned.
- [docs/agent_contract.md](docs/agent_contract.md) — the common
  interface every agent must implement.
- [docs/agent_personas.md](docs/agent_personas.md) — the three Shark
  personas' priorities and behavior.
- [docs/coding_standards.md](docs/coding_standards.md) — engineering
  standards for this codebase.
- [docs/release_log.md](docs/release_log.md) — what actually shipped
  in each release, historically.
- [docs/release_backlog.md](docs/release_backlog.md) — planned,
  not-yet-built work by release.

## Roadmap

See [docs/release_backlog.md](docs/release_backlog.md) for the full,
maintained roadmap. Immediately next (Release 0.7):

- [ ] Implement a real `VerificationAgent`, replacing the always-pass placeholder
- [ ] Implement a real Consensus Engine aggregating the three Sharks' independent offers into one final decision
- [ ] Implement full multi-round negotiation (`SharkTankOrchestrator.run_pitch()`)
