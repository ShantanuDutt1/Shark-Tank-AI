# Reference Proposal Manifest — FleetPulse (Release 0.9.5)

Machine-readable-ish summary of what
[`0_9_5_reference_proposal.md`](0_9_5_reference_proposal.md)
intentionally contains, for QA/regression use. This describes the
proposal's *content characteristics* only — it deliberately does not
encode an expected Shark decision, Consensus recommendation, or
verification verdict. The fixture tests whether the system's
conclusions are properly supported by evidence, not whether the system
reaches a predetermined outcome.

```text
contains_company_and_product = true
contains_problem_statement = true
contains_target_customer = true
contains_business_model = true
contains_market_size_claim = true          # "$40 billion" — unsourced, challengeable
contains_competition = true                 # FleetIQ, $120M funded incumbent
contains_differentiation = true
contains_traction = true                    # 4 paying customers, 260 trucks, renewals
contains_customer_evidence = true           # anecdotal, explicitly not rigorously measured
contains_financial_history = true           # ARR, COGS, opex, burn
contains_projections = true                 # $1.2M ARR in 12 months
contains_costs = true
contains_funding_request = true             # $750,000
contains_valuation = true                   # ~$9.375M post-money implied
contains_equity_offered = true              # 8%
contains_use_of_funds = true
contains_team_and_founder_experience = true
contains_risks = true
contains_growth_strategy = true
contains_timing_rationale = true

contains_challengeable_claim = true         # unsourced $40B TAM
contains_financial_inconsistency = true     # stated 75% gross margin vs. (420k-180k)/420k = ~57.1% from the founder's own other figures
contains_customer_concentration_weakness = true  # one customer = 55% of ARR
contains_competitive_weakness = true        # well-funded incumbent could out-compete on price/speed
contains_missing_information = true         # no churn rate, no CAC, vague CTO background
contains_aggressive_valuation_signal = true # ~22x current ARR implied multiple, unresolved by the text itself

encodes_expected_shark_decision = false
encodes_expected_consensus_recommendation = false
encodes_expected_verification_verdict = false
```
