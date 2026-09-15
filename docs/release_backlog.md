# Release Backlog

This tracks planned-but-unbuilt work, grouped by the release most
likely to ship it. It is a planning aid, not a commitment — scope can
move between releases. Completed work is not re-listed here once it
ships; see `release_log.md` for the historical record of what actually
shipped in each release.

---

## Release 0.9.5+ — Verification/Consensus Refinement & Multi-Round Negotiation

Release 0.7 shipped a real `VerificationAgent` and `ConsensusEngine`;
Release 0.8 shipped real, deterministic Advanced Financial Analysis;
Release 0.9 shipped the Founder Feedback Report (see `docs/release_log.md`
for all three). What those releases deliberately left unbuilt, as a
documented scope boundary rather than an oversight (this section's own
name was originally "Release 0.9" before Release 0.9 was actually
scoped as the Founder Feedback Report — renamed rather than
re-numbered, since none of this was reprioritized, just correctly
relabeled):

- The `Verification -> Internal Deliberation` bounded retry path
  (`docs/state_machines.md` § Rule 3): a critical/severe Verification
  finding does not currently re-route the session for another
  deliberation round; it flows forward into the Consensus Engine's
  reconciliation instead. Adding the retry loop needs a retry counter
  and new Session Director control flow — a real architectural
  addition, not a small one, per Release 0.7's own spec Part 3
  ("do not... replace the Session Director").
- Full multi-round negotiation: counter-to-a-counter, more than one
  round per Shark, and a real `NegotiationSession` outcome via
  `SharkTankOrchestrator.run_pitch()` (Release 0.6/0.7/0.8 all shipped
  exactly one counter-offer turn per interested Shark — see Release
  0.6 spec Part J, Release 0.7 spec Part 21, Release 0.8 spec Part 4).
- Reconciling `docs/agent_personas.md` §12.2's "Unanimous Rejection"
  short-circuit path (all three Sharks independently conclude a
  pitch is impossible/fraudulent/economically nonviable, ending the
  session with no negotiation) with the Consensus Engine's normal
  `do_not_invest` outcome — a `do_not_invest` recommendation today
  looks the same as an ordinary decline.

## Unscheduled — Release 0.8 additions

Deliberately left unbuilt by Release 0.8's own scope boundary (spec
Part 4/38: no unjustified new LLM calls, no platform expansion):

- **Feeding Advanced Financial Analysis back into each Shark's own
  prompt.** Release 0.8 spec Part 19's "common analytical foundation
  the Sharks continue interpreting differently" is served today by the
  Consensus Engine reconciling the analysis alongside each Shark's
  already-independently-formed position (from Market Reality Research
  alone), not by re-running or extending `SharkAgent.evaluate_pitch()`
  with the financial analysis as additional input — doing so would
  mean re-running Shark evaluation after Question Round completes but
  before deliberation, a real pipeline reshape, and risked exactly the
  "sacrifice three-Shark independence" regression spec Part 35
  explicitly warns against. If a future release wants each Shark's own
  reasoning (not just Consensus's) to visibly reference the financial
  analysis, this is the extension point.
- **A dedicated sector-specific financial framework per business
  model** (spec Part 10's SaaS/marketplace/consumer/restaurant/
  professional-services/cleantech/hardware sections as distinct
  calculation paths, rather than one general extraction+calculation
  pipeline guided by a business-model label in the prompt). Release
  0.8 computes the same general set of calculations
  (`utils/financial_calculations.py`) regardless of business model and
  relies on the LLM extraction step to prioritize the metrics that
  actually matter for the classified model — a deliberate
  simplification, not an oversight (mirrors Release 0.6.1's
  research-planner precedent of a small heuristic over a large
  taxonomy).
- **"Hardware" and "biotech/deep tech" as distinct business-model
  categories** for financial analysis guidance. Release 0.8 reuses
  `agents.research_planner.classify_business_model()`'s existing six
  categories (`saas`/`consumer`/`marketplace`/`restaurant`/
  `cleantech`/`professional_services`) plus `generic` rather than
  extending that Release 0.6.1 classifier — a pitch matching neither
  keyword set falls into the conservative `generic` bucket, per that
  module's own established behavior for ambiguous business models.
- **More than a two-point (low=high) scenario valuation.** Downside/
  upside scenarios currently compute one point estimate (revenue ×
  multiple) rather than a true range per scenario; the UI rounds this
  for display (`_format_currency_range()`) to avoid false precision,
  but a future release could compute a genuine range per scenario if a
  defensible method for doing so (without inventing a spread) is
  identified.

## Unscheduled — Release 0.9 additions

Deliberately left unbuilt by Release 0.9's own scope boundary (spec
Parts 36-37: no 0.9.5-scope autonomous QA, no 1.x-scope platform
work):

- **No 0.9.5-scope autonomous QA/regression tooling.** A simulated
  founder regression suite, automated agent-impersonation QA, or any
  system that generates and runs its own test pitches against the
  live app remains unbuilt — Release 0.9 only added conventional,
  human-authored tests (`tests/test_founder_feedback_agent.py`,
  `tests/test_report_rendering.py`, and additions to
  `tests/test_session_director.py`/`tests/test_app_ui.py`).
- **No interactivity for the Founder Feedback Report.** It is
  generated exactly once per session from a single LLM call; there is
  no follow-up-question, regenerate, or "ask the report a question"
  capability, and none is planned as an extension of `FounderFeedbackAgent`
  itself — see README.md → *What's a Placeholder Today*.
  `FounderFeedbackAgent.generate()`'s single-call, single-report shape
  is deliberate, not a stepping stone left half-built.
- **No persistence of the report.** Like every other session artifact,
  the report (and its rendered PDF) exists only for the lifetime of
  the Python process's `SharkTankOrchestrator` instance; a founder
  cannot retrieve a past session's report after a reset or restart. A
  persistent store is the same unscheduled `memory/` work already
  listed below (SQLite-backed `BaseMemory`), not a new gap.
- **No sector-specific investor-readiness rubric.** The investor-readiness
  dimensions and action-plan guidance in `prompts/founder_feedback.txt`
  /`docs/investor_evaluation_framework.md` are business-model-aware
  (steered by the same `classify_business_model()` categories Release
  0.6.1/0.8 already established) but not a fully distinct rubric per
  business model — mirrors Release 0.8's identical, deliberate
  simplification for financial analysis (see *Unscheduled — Release
  0.8 additions* below).
- **Blockchain, Google ADK, MCP, persistent memory, multi-round
  negotiation, and additional Shark personas** were all explicitly out
  of scope for Release 0.9, as they are for every release to date —
  restated here only because Release 0.9's own specification named
  them explicitly as things not to build; see the relevant
  already-listed *Unscheduled* items below for each.

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
  and PII defenses shipped in Release 0.6 (still unaddressed after
  Release 0.6.1's redaction-coverage widening) — those are documented,
  best-effort mitigations, not a verified guarantee.
- Analytics/telemetry platform.
- An LLM-based (rather than keyword-heuristic) research-planning
  classifier. Release 0.6.1's `agents/research_planner.py` deliberately
  uses a small, deterministic keyword heuristic instead — no provider
  call, no network dependency, fully offline-testable — per its own
  spec Part A's "do not hard-code an enormous industry taxonomy... use
  a small, extensible set of business-model categories." Revisiting
  this with a real classifier is future scope, not a gap being hidden.
- PII coverage for founder-authored content beyond the three identifier
  types (unchanged from Release 0.6's item above); Release 0.6.1 widened
  *where* redaction is applied (Moderator-extracted fields, Question
  Round answers, negotiation counters), not *what* it detects.

