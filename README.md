# Shark Tank AI

A turn-based, multi-agent Streamlit application where a founder pitches
a startup to an AI investment committee — a neutral Moderator plus
three Shark investor personas (Conservative, Growth, Balanced) — gets
questioned one Shark at a time, watches the committee deliberate
privately, and receives a session outcome.

> **Status: Release 0.9.5 — Full-System QA, Validation, Simulation
> Conformance & Hardening**, a dedicated QA milestone on top of Release
> 0.9's Agentic Founder Feedback Report, Release 0.8's Advanced
> Investment Analysis + Decision Quality, Release 0.7's Verification
> Agent + Formal Consensus Engine, Release 0.6.1's Hardening/Research
> Integrity/Failure Semantics work, and Release 0.6's Market Reality,
> Proposal Validation, Safety, Structured Extraction, and Negotiation.
> The session flow is: Founder Proposal → Moderator Validation &
> Extraction → Market Reality Research → Shark Analysis → Shark
> Questions → Internal Deliberation → Advanced Financial Analysis →
> Verification → Consensus → Investment Decision → Negotiation →
> **Founder Feedback Report** → Final Outcome. Every stage from
> validation onward uses real, provider-backed reasoning — not
> deterministic templates — with a graceful, clearly-labeled fallback
> at every step if the provider is unconfigured or fails, so the app
> always keeps running; that fallback is never mistakable for a genuine
> investment decision, including Advanced Analysis/Verification/
> Consensus/the Founder Feedback Report itself (see *What Works Today*
> below). Release 0.9.5 verified the whole system end-to-end through
> the real UI with a permanent canonical reference proposal
> (`tests/fixtures/proposals/0_9_5_reference_proposal.md`), fixed a
> real defect where the three canonical final-outcome messages were
> never implemented, and eliminated a long-standing source of
> non-deterministic `tests/test_app_ui.py` failures. See *Current
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
  Question Round → Internal Deliberation → Advanced Financial Analysis →
  Verification → Consensus → Investment Decision → Negotiation →
  Session Complete (generating the Founder Feedback Report as its
  final step), plus a clean reset back to Idle.
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
- **Real Advanced Financial Analysis.** After the Sharks deliberate, a
  Financial Analyst extracts financial facts (revenue, costs, cash,
  customers, SaaS metrics where relevant) with explicit provenance —
  distinguishing what the founder stated from what's derived, inferred,
  estimated, or missing — and computes every calculation
  deterministically in Python: implied valuation, revenue/ARR
  multiples, margins, growth, burn, runway, dilution. It flags
  inconsistencies (e.g. a stated margin that doesn't match revenue and
  cost figures also given), builds downside/base/upside valuation
  scenarios with an identified assumption source for each, and
  identifies structured risk and upside factors — never inventing a
  missing input or presenting a projection as a current fact.
- **Real Verification and Consensus.** A Verification Agent audits
  whether each Shark's final reasoning — and the financial analysis
  itself — is actually supported by the proposal, founder answers, and
  market research — distinguishing supported claims from unsupported
  ones, contradictions, and arithmetic problems, without forcing the
  Sharks to agree with each other. A Consensus Engine then reconciles
  all three Sharks' positions, the financial analysis, and the
  Verification findings into one formal committee recommendation
  (`invest` / `invest with conditions` / `do not invest` /
  `insufficient evidence`), explicitly distinguishing **business
  quality** (how good the company is) from **deal quality** (how
  attractive it is *at the proposed terms*) — an excellent business at
  an excessive valuation can still be a poor deal. Explicitly not a
  majority vote: a single Shark's well-supported concern can outweigh a
  2-1 split. Neither component is a fourth Shark or makes its own
  investment offer; each Shark's own real, independent offer (below) is
  unaffected.
- **Real Negotiation.** The founder gets one counter-offer turn with
  each Shark who made an offer; that Shark independently accepts,
  rejects, or modifies.
- **A real Founder Feedback Report**, generated once at the end of
  every session and offered as a two-page PDF download. Grounded in
  real, cited research into how early-stage investors (YC, Techstars,
  Sequoia, 500 Global, a16z, and others) actually evaluate startups
  (see [docs/investor_evaluation_framework.md](docs/investor_evaluation_framework.md)),
  it critically synthesizes the *entire* simulation — not just the
  Sharks' offers — into strengths, areas that need work, and (reserved
  for genuinely serious problems) critical issues; an investor-readiness
  assessment across market, team, traction, unit economics, and more;
  qualified (never falsely precise) valuation and financial feedback;
  and a prioritized NOW/NEXT/LATER action plan, each item naming the
  problem, why it matters, the action, and what evidence would resolve
  it. It is not a fourth Shark and never issues or implies an
  investment decision — every report carries a fixed disclaimer to that
  effect, generated once per session and rendered entirely in memory
  (no file is ever written to disk).
- **A technical failure is never presented as a decision.** If a
  Shark's evaluation or negotiation response fails for a provider
  reason, the founder sees an honest "evaluation was unavailable" /
  "could not process your counter-offer" message — never a fabricated
  pass, decline, or walk-away.
- **The session's real final outcome is always one of three exact,
  fixed lines** (Release 0.9.5), chosen from what actually happened in
  Negotiation — never a generic "thanks for pitching," and never
  inferred from the committee's advisory Consensus recommendation
  alone: *"Sorry Little Fish, the Sharks were not impressed"* (no
  Shark interested), *"Sorry Little Fish, there was nothing for you
  here today"* (at least one Shark was interested but no deal closed),
  or *"Congratulations, Little Fish. You will now swim with the
  Sharks!"* (a deal was accepted or modified into agreement).
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

- **Financial analysis doesn't feed back into each Shark's own
  reasoning.** Each Shark still forms its question, evaluation, and
  deliberation using only the Market Reality Brief, exactly as before
  Release 0.8 — the Financial Analyst's extracted facts and
  calculations reach the founder-facing decision only through
  Verification (which audits them) and Consensus (which reconciles
  them), not through any individual Shark's own prompt.
- **Scenario valuations are a single figure per scenario, not a true
  range.** Downside/base/upside each compute one point estimate
  (revenue × multiple); the UI rounds it for display to avoid false
  precision, but a genuinely ranged per-scenario valuation is future
  work.
- **No sector-specific calculation frameworks.** The same general set
  of financial calculations runs regardless of business model; a
  business-model label steers what the extraction step prioritizes,
  but there's no distinct SaaS-vs-restaurant-vs-marketplace
  calculation path.
- **No bounded retry when Verification flags a serious problem.** A
  critical Verification finding does not currently send the committee
  back for another deliberation round (`docs/state_machines.md` §
  Rule 3's documented, still-unimplemented path) — it flows forward
  into the Consensus Engine's reconciliation instead, where it can
  still drive the recommendation toward `do_not_invest`/
  `insufficient_evidence`.
- **No distinct "unanimous rejection" outcome.** If all three Sharks
  independently conclude a pitch is impossible or fraudulent, that
  looks the same as an ordinary `do_not_invest` recommendation today —
  `docs/agent_personas.md` §12.2's more severe, no-negotiation
  short-circuit path remains unimplemented.
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
- **The Founder Feedback Report is a single pass, not interactive.**
  It is generated exactly once per session, from a single LLM call — a
  founder cannot ask it follow-up questions, request revisions, or
  regenerate it with different emphasis. It is also not persisted
  anywhere: closing the browser tab or resetting the session discards
  it, exactly like every other in-session artifact (see *No
  persistence* above).

See [docs/release_backlog.md](docs/release_backlog.md) for the full
roadmap.

## Project Structure

```
shark-tank-ai/
├── agents/          # ModeratorAgent, SharkAgent, MarketResearchAgent, VerificationAgent, FinancialAnalyst, FounderFeedbackAgent, prompt_safety
├── orchestrator/     # SharkTankOrchestrator (Session Director), EventBus, TurnController, NegotiationController, ConsensusEngine
├── providers/        # BaseProvider + AnthropicProvider; BaseResearchProvider + AnthropicResearchProvider
├── memory/           # Pluggable session/negotiation memory backends (placeholder)
├── models/           # Shared pydantic data models (Pitch, Offer, MarketRealityBrief, ConversationMessage, ...)
├── prompts/          # Prompt templates (plain text) + loader
├── ui/               # Streamlit UI components (chat, proposal intake, controls, session state)
├── config/           # Settings (pydantic-settings) + logging config
├── utils/            # Small shared helpers (IDs, PII redaction, PDF extraction/rendering, formatting, deterministic financial calculations)
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
- [docs/investor_evaluation_framework.md](docs/investor_evaluation_framework.md)
  — real, cited research into how early-stage investors evaluate
  startups, underlying the Founder Feedback Report's prompt.

## Roadmap

See [docs/release_backlog.md](docs/release_backlog.md) for the full,
maintained roadmap. Immediately next (Release 0.9.5+):

- [ ] Implement the `Verification → Internal Deliberation` bounded retry path for a critical Verification finding (`docs/state_machines.md` § Rule 3)
- [ ] Implement full multi-round negotiation (`SharkTankOrchestrator.run_pitch()`)
- [ ] Reconcile `docs/agent_personas.md` §12.2's Unanimous Rejection path with the Consensus Engine's normal `do_not_invest` outcome
