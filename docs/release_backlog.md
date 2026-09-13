# Release Backlog

This tracks planned-but-unbuilt work, grouped by the release most
likely to ship it. It is a planning aid, not a commitment — scope can
move between releases. Completed work is not re-listed here once it
ships; see `release_log.md` for the historical record of what actually
shipped in each release.

---

## Release 0.7 — Verification & Consensus

- A `VerificationAgent` class (implementing `agent_contract.md`'s
  common interface) plugged into the `VERIFICATION` phase, replacing
  the always-pass placeholder.
- A real Consensus Engine aggregating the three Sharks' individual
  `Offer`s (real as of Release 0.5/0.6) into a genuine, single final
  decision, replacing the fixed `DealStatus.PENDING` placeholder still
  published by `InvestmentDecisionMade`. `orchestrator.orchestrator
  .SharkTankOrchestrator._summarize_offers()`'s factual interest tally
  is a legitimate, minimal starting point but is explicitly not real
  aggregation logic (Release 0.5 spec section B17, reaffirmed in
  Release 0.6 spec Part U).
- Full multi-round negotiation: counter-to-a-counter, more than one
  round per Shark, and a real `NegotiationSession` outcome via
  `SharkTankOrchestrator.run_pitch()` (Release 0.6 shipped exactly one
  counter-offer turn per interested Shark — see Release 0.6 spec Part
  J and Part U).

## Unscheduled

- Dynamic Industry Adaptation as a distinct mechanism
  (`docs/agent_personas.md` §9 and its new §5.1) — an explicit
  industry-detection/taxonomy step and an `industry_context` output
  field, as opposed to Release 0.5's approach of just letting the
  model reason from the pitch text directly.
- Reconciling `agents/shark_agent.py`'s actual evaluation JSON schema
  (`interested`/`amount`/`equity_pct`/`conditions`/`rationale`/
  `confidence`) with `docs/agent_personas.md` §5-§7's fuller
  aspirational schema (`deal_status`, `industry_context`).
- `docs/agent_personas.md` §11's specific confidence-threshold
  formulas and equity/risk formulas — Release 0.5's `confidence` is
  the model's own self-reported number, unvalidated against any
  specific formula.
- `docs/agent_personas.md` §12.2 Unanimous Rejection and the rest of
  §13's negotiation mechanics.
- `GeminiProvider` / `OllamaProvider` implementations (`ui/sidebar.py`
  already reconciled as of Release 0.5 to not claim these work; the
  providers themselves still don't exist).
- SQLite-backed `BaseMemory` implementation
  (`memory/in_memory_store.py` is still `NotImplementedError` on every
  method).
- MCP integration for external tool/data access
  (`docs/architecture.md` -> MCP).
- Google ADK integration (`docs/architecture.md` -> Google ADK).
- Agent Skills system (`docs/agent_contract.md` -> Skills).
- The Agent Orchestration State Machine (`docs/state_machines.md` §2) —
  governing a single agent task's `Waiting` → `Completed`/`Failed`
  lifecycle, distinct from the User Session State Machine the Session
  Director already drives end-to-end as of Release 0.4.
- Generalizing `agents.base_agent.BaseAgent` so a facilitator like
  `ModeratorAgent` can subclass it, per `docs/release_log.md` ->
  Release 0.4's recorded deviation.
- Bounded retry logic for transient provider failures (Release 0.5
  deliberately shipped only an immediate fallback, no retry, per its
  own spec section B4).
- True asynchronous/background execution of provider-backed phases, if
  synchronous latency ever becomes a real problem (Release 0.5
  deliberately kept everything synchronous, per its own spec section
  B24; Release 0.6 kept this unchanged, per its own spec Part R24 —
  the same reasoning now also covers Market Research and Negotiation).
- PII coverage beyond the three identifier types
  `utils/pii.py::anonymize_pii()` currently redacts (email, phone,
  street address) — e.g. names, SSNs, financial account numbers.
- Independent verification of retrieved-source URLs from Market
  Reality Research (`providers/anthropic_research_provider.py`
  currently trusts the model's self-report — see
  `docs/architecture.md` -> Market Reality Research's documented
  limitation).
- A dedicated search-vendor `BaseResearchProvider` implementation
  (e.g. a real search API), replacing/supplementing
  `AnthropicResearchProvider`'s LLM-mediated search.
- A formal security audit / penetration test of the prompt-injection
  and PII defenses shipped in Release 0.6 — those are documented,
  best-effort mitigations, not a verified guarantee.
- Analytics/telemetry platform.

