# Investor Evaluation Framework (Release 0.9 research)

**Status:** Research artifact backing `agents/founder_feedback_agent.py`'s
investor-readiness dimensions and prompt. This document is **framework
evidence** -- what reputable accelerators and venture investors say
they look for in general -- and must never be conflated with
**simulation evidence** -- what a specific founder's proposal actually
demonstrated. `agents/founder_feedback_agent.py` keeps these two
sources logically separate (see `docs/architecture.md` -> Founder
Feedback Report): the eleven dimensions below shape *what the report
asks about*, never a specific finding about any one company.

This document does not claim to be exhaustive or definitive. It
reflects a focused, time-boxed web research pass across a handful of
reputable, named sources (Y Combinator, Techstars, Sequoia Capital,
500 Global, a16z, and a small number of specialist venture-finance
publications), not a systematic literature review.

---

## Method

Targeted web searches were run against named, reputable sources rather
than generic "startup pitch checklist" content, per Release 0.9 spec
Part 4. Search queries and the sources actually consulted are listed
under each dimension below. Where a claim could not be traced to one
of these sources, it is not included here.

## The eleven dimensions

Drawn directly from Release 0.9 spec Part 4's own list, cross-checked
against the sources below rather than accepted at face value.

### 1. Team / founder-market fit

- **Y Combinator**: cites founding-team strength as one of the biggest
  factors partners weigh -- "YC's most-cited preference is for teams of
  two or three technical co-founders who have worked together before
  and have a reason to be attacking this specific problem," optimizing
  for founder "relentlessness" and a "clear, fast-rising trajectory."
  ([Chapter 1: What YC Looks For In Startups](https://www.tiagosada.com/notes/yc-handbook-chapter-one))
- **Techstars**: explicitly ranks priorities as "team, team, team,
  market, product, traction, in that order," looking for strong
  founder-market fit and (usually) a technical co-founder.
  ([Accelerometry: How investors at Techstars pick winners](https://sylviabouloutas.medium.com/accelerometry-2d2c552d8703))
- **500 Global**: emphasizes "entrepreneurs with deep industry
  knowledge, proven execution ability, and a clear vision."
  ([How 500 Startups picks investments](https://500.co/content/how-500-startups-picks-investments))

### 2. Problem and target customer

- **Sequoia's 10-slide template** opens with a concise articulation of
  the problem before any solution content -- the template's whole
  design is built around "can I understand this in 3 minutes?"
  ([Sequoia Capital Pitch Deck Template](https://www.slidegenius.com/cm-faq-question/what-is-the-recommended-pitch-template-provided-by-sequoia-capital-for-presentations))
- Due-diligence guides list "is there evidence that customers want
  this product and will use it?" among the first questions investors
  ask. ([How VCs Evaluate Startups](https://blog.thinklions.com/how-vcs-evaluate-startups))

### 3. Solution / value proposition

- Sequoia's template treats "solution" as its own slide, directly
  following "problem" -- evaluated on whether it's a specific,
  credible mechanism, not a restatement of ambition.
  ([Sequoia Pitch Deck Template](https://slidebean.com/templates/sequoia-pitch-deck-template))

### 4. Market opportunity

- YC "favors startups that target large, addressable markets... a
  startup that can tap into a billion-dollar industry is much more
  appealing than one aiming for a niche market," though YC also notes
  the *initial* market can be small if there's a credible path to
  grow it. ([What is Y Combinator?](https://medium.com/@markeeters/what-is-y-combinator-1de598e83cd4))
- a16z's Marc Andreessen has been characterized as treating market as
  "the most important factor in a startup's success or failure."
  ([How the Top 12 VC Firms Evaluate Startups](https://eqvista.com/how-top-vc-firms-evaluate-startups/))

### 5. Traction / validation

- YC: "a working product with ten paying users and a 20 percent
  week-over-week growth rate is a stronger application than a 40-page
  deck describing a category you intend to invent."
  ([Y Combinator: A Comprehensive Analysis](https://bytebridge.medium.com/y-combinator-a-comprehensive-analysis-of-the-worlds-leading-startup-accelerator-5c927b8af7ae))
- Stage-specific benchmarks (see *Stage-awareness* below): pre-seed
  investors look for problem validation (customer interviews, LOIs);
  seed investors look for early product-market-fit signals
  (commonly cited: $5K-$20K+ MRR, 10-20%+ MoM growth sustained over
  several months, a flattening retention curve); Series A investors
  increasingly expect roughly $3M ARR with 2-3x YoY growth.
  ([Traction Benchmarks by Funding Stage](https://www.stackmatix.com/blog/traction-benchmarks-by-funding-stage))

### 6. Business model / economics

- Sequoia's template includes a dedicated "business model" slide
  alongside financials -- evaluated for whether the revenue mechanism
  is actually credible for the stated market, not just "big number."
  ([Sequoia Pitch Deck - Pitch Deck Examples](https://www.basetemplates.com/pitch-decks/sequoia))

### 7. Competition / differentiation / moat

- a16z's own writing frames long-term defensibility as coming from
  "packaging differentiated technology, understanding the domain...
  and dominating the go-to-market race" rather than any single
  static moat. ([The Empty Promise of Data Moats](https://a16z.com/the-empty-promise-of-data-moats/))
- Founder guidance distilled from VC sources: acknowledge all real
  competitors openly, articulate a specific advantage, and show how
  it translates into defensible growth rather than a generic claim of
  uniqueness. ([How VCs Evaluate Your Competition](https://www.allied.vc/guides/how-startup-investors-evaluate-your-competition))
- Techstars explicitly looks for "a strong tech moat and robust IP."
  ([Techstars evaluation criteria](https://fastercapital.com/topics/how-does-the-selection-process-at-techstars-work-what-factors-are-considered.html))

### 8. Go-to-market

- Covered as part of Techstars' explicit "market, product, traction"
  ordering and Sequoia's business-model slide -- a credible,
  specific acquisition mechanism (not "we will use social media") is
  what's actually assessed.

### 9. Financials / capital efficiency

- Lightspeed Ventures is cited as prioritizing "clear product
  differentiation and capital efficiency" alongside growth.
  ([How the Top 12 VC Firms Evaluate Startups](https://eqvista.com/how-top-vc-firms-evaluate-startups/))
- Due-diligence practice reviews financials, customer data, and
  market assumptions together, not financials in isolation.
  ([How VCs Evaluate Startups](https://blog.thinklions.com/how-vcs-evaluate-startups))

### 10. Why now / timing

- YC: "timing matters more than novelty" -- the same idea can fail and
  later succeed once "AI models had finally become good enough and
  cheap enough for the market to catch up" (Lyrebird in 2017 vs.
  ElevenLabs in 2022, cited as an explicit example).
  ([Timing is the single biggest reason](https://theventurecrew.substack.com/p/timing-is-the-single-biggest-reason))
  A credible "why now" names a specific change in technology,
  regulation, cost structure, or customer behavior -- not just
  founder enthusiasm.

### 11. Ask / valuation / use of funds

- For pre-revenue companies, cited qualitative methods include the
  Berkus Method and Scorecard Valuation (team, market potential, early
  product development); for revenue-stage companies, comparable/
  multiple-based approaches are more common.
  ([Venture Capital Valuation: A Guide to Valuing Startups](https://growthequityinterviewguide.com/venture-capital/venture-capital-term-sheets/venture-capital-valuation))
- Investors reportedly prefer use-of-funds framed around specific
  milestones and KPIs the raise will achieve, not a cost breakdown.
  ([The Key Questions VCs Ask](https://capbase.com/the-key-questions-to-expect-from-venture-capitals-when-you-pitch-them-your-startup/))

## Stage-awareness (Release 0.9 spec Part 9)

Cited traction/evidence expectations by stage (used to calibrate the
report's tone, never to penalize a company for lacking metrics its
actual stage wouldn't yet produce):

| Stage | What's actually expected (per sources above) |
|---|---|
| Pre-seed | Problem validation: customer interviews, LOIs (a cited rule of thumb: "10-20 strong LOIs are more valuable than a 1,000-person email list" for B2B) -- not revenue. |
| Seed | Early product-market-fit signal: commonly cited ranges of $5K-$20K+ MRR, 10-20%+ MoM growth sustained over several months, and a flattening (not decaying) retention curve. |
| Series A | Repeatable, scalable traction: a commonly cited ~$3M ARR benchmark (reported as roughly triple the ~$1M benchmark common in 2018-2020), 2-3x YoY growth, and a proven acquisition channel. |

Source: [Traction Benchmarks by Funding Stage](https://www.stackmatix.com/blog/traction-benchmarks-by-funding-stage),
[CRV: Seed Stage vs Pre-Seed Funding](https://www.crv.com/content/seed-stage-vs-pre-seed-funding).

## Explicit non-goals of this framework

- **Not a rigid checklist.** `agents/founder_feedback_agent.py`'s
  prompt explicitly instructs the model to weight these dimensions by
  the pitch's actual stage, business model, and available evidence --
  a pre-revenue company is never penalized for lacking Series A-grade
  metrics (spec Part 9).
- **Not business-model-agnostic.** §10 of the Release 0.9 spec (SaaS/
  marketplace/consumer/restaurant/professional-services/cleantech-
  hardware/biotech) further adapts which financial and commercial
  facts matter within each dimension -- reusing
  `agents.research_planner.classify_business_model()`'s existing
  category set (Release 0.6.1) rather than a new taxonomy.
- **Not investment advice and not a prediction.** This framework
  describes what named investors say they look for in general; it is
  never used to imply that satisfying it predicts real investor
  interest in a specific company. See the report's own disclaimer.
