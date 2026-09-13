"""
Research planning for Market Reality Research (Release 0.6.1).

Produces a small, typed `models.schemas.ResearchPlan` *before* any web
search happens, per spec Parts A/4-5: research should not start from
one broad, undifferentiated query -- it should start from an explicit
plan naming which categories of evidence actually matter for this
pitch's business model, then bound the number of targeted searches
that follow.

Deliberately a plain keyword heuristic, not an LLM call: classification
this coarse (SaaS vs. marketplace vs. restaurant vs. ...) does not need
a provider round-trip, and keeping it a pure function makes it fully
unit-testable offline with no API key (Release 0.6.1 spec Part A §26).
This is explicitly NOT an attempt at a general industry taxonomy --
spec Part A §4: "do not hard-code an enormous industry taxonomy... use
a small, extensible set of business-model categories." When the
heuristic can't confidently classify a pitch, `is_uncertain=True` and
a conservative generic plan is used rather than inventing a
classification.
"""

from __future__ import annotations

import re

from models.schemas import Pitch, ResearchObjective, ResearchPlan

#: Category -> ordered (category_label, query_template) objectives,
#: drawn directly from spec Part A's own worked examples. Query
#: templates are filled in with the company name and a short pitch
#: excerpt at plan-build time. Bounded to spec Part A §5's "3-8
#: targeted research objectives" -- every list here has 5 or 6 entries,
#: except the conservative generic fallback (3).
_OBJECTIVE_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "saas": [
        ("market_size_growth", "{company}: SaaS market size and growth rate for {topic}"),
        (
            "arr_revenue_multiples",
            "typical ARR and revenue multiples for early-stage SaaS companies in {topic}",
        ),
        (
            "growth_benchmarks",
            "typical revenue growth rate benchmarks for early-stage SaaS companies",
        ),
        (
            "margin_and_churn",
            "typical gross margin and churn benchmarks for SaaS companies in {topic}",
        ),
        ("comparable_companies", "public and private comparable SaaS companies in {topic}"),
        (
            "funding_transactions",
            "recent funding rounds or acquisitions of SaaS companies in {topic}",
        ),
    ],
    "consumer": [
        (
            "category_size_growth",
            "{company}: consumer product category size and growth for {topic}",
        ),
        ("gross_margin", "typical gross margin for consumer products in {topic}"),
        (
            "retail_economics",
            "typical retail/DTC unit economics for consumer products in {topic}",
        ),
        ("comparable_brands", "comparable consumer brands in {topic}"),
        (
            "funding_transactions",
            "recent funding rounds or acquisitions of consumer brands in {topic}",
        ),
    ],
    "marketplace": [
        (
            "gmv_and_take_rate",
            "{company}: typical GMV and take rate benchmarks for marketplaces in {topic}",
        ),
        ("revenue_growth", "typical revenue growth benchmarks for marketplace companies"),
        ("network_effects", "network effects and market structure for marketplaces in {topic}"),
        ("comparable_companies", "comparable marketplace companies in {topic}"),
        (
            "funding_transactions",
            "recent funding rounds or acquisitions of marketplace companies in {topic}",
        ),
    ],
    "restaurant": [
        (
            "unit_economics",
            "{company}: typical revenue and unit economics for restaurants in {topic}",
        ),
        (
            "margin_benchmarks",
            "typical gross margin and operating margin benchmarks for restaurants",
        ),
        (
            "labor_and_occupancy_costs",
            "typical labor cost and occupancy cost benchmarks for restaurants",
        ),
        ("comparable_businesses", "comparable restaurant businesses or chains in {topic}"),
        (
            "transaction_evidence",
            "recent acquisitions or funding of restaurant businesses in {topic}",
        ),
    ],
    "cleantech": [
        ("market_size_growth", "{company}: cleantech market size and growth for {topic}"),
        (
            "deployment_economics",
            "typical deployment economics and capex intensity for {topic}",
        ),
        ("technology_economics", "technology cost curve and unit economics for {topic}"),
        ("regulatory_context", "regulatory and market context for cleantech in {topic}"),
        ("comparable_companies", "comparable cleantech companies in {topic}"),
        (
            "funding_transactions",
            "recent funding rounds or acquisitions of cleantech companies in {topic}",
        ),
    ],
    "professional_services": [
        (
            "revenue_ebitda_multiples",
            "typical revenue and EBITDA multiples for professional services firms in {topic}",
        ),
        (
            "utilization_benchmarks",
            "typical utilization rate benchmarks for professional services firms",
        ),
        (
            "recurring_revenue",
            "typical recurring revenue share for professional services firms in {topic}",
        ),
        ("comparable_businesses", "comparable professional services businesses in {topic}"),
        (
            "transaction_evidence",
            "recent acquisitions of professional services businesses in {topic}",
        ),
    ],
}

#: The conservative fallback used whenever the pitch's business model
#: cannot be confidently classified -- spec Part A §4: "use a
#: conservative generic research plan rather than inventing
#: classification." Deliberately smaller than every specific list
#: above.
_GENERIC_OBJECTIVES: list[tuple[str, str]] = [
    ("market_size_growth", "{company}: market size and growth for {topic}"),
    (
        "financial_benchmarks",
        "typical financial benchmarks (margins, multiples) for businesses in {topic}",
    ),
    ("comparable_companies", "comparable companies or transactions in {topic}"),
]

#: Ordered so the first matching category wins -- deliberately coarse
#: substring/keyword matching, not an ML classifier (spec Part A §4:
#: "a small, extensible set," not a taxonomy). A pitch matching more
#: than one category's keywords (e.g. "a SaaS marketplace") takes
#: whichever is checked first below; this is a heuristic, not a
#: guarantee, and `is_uncertain` exists precisely so a low-confidence
#: classification degrades safely rather than committing hard to one.
_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (
        "marketplace",
        ("marketplace", "buyers and sellers", "gmv", "gross merchandise", "take rate", "two-sided"),
    ),
    (
        "restaurant",
        ("restaurant", "menu", "diners", "eatery", "food truck", "quick-service", "cafe"),
    ),
    (
        "cleantech",
        ("solar", "cleantech", "clean energy", "carbon", "battery", "emissions", "renewable"),
    ),
    (
        "professional_services",
        ("consulting", "agency", "billable hour", "professional services", "advisory firm"),
    ),
    (
        "saas",
        ("saas", "subscription software", "recurring revenue", "arr", "mrr", "software as a service"),
    ),
    (
        "consumer",
        ("consumer product", "dtc", "direct-to-consumer", "retail brand", "e-commerce brand", "cpg"),
    ),
]


def classify_business_model(description: str) -> tuple[str, bool]:
    """Best-effort `(business_model, is_uncertain)` classification of
    `description` via keyword matching.

    Returns a category from `_OBJECTIVE_TEMPLATES` when a keyword
    match is found (`is_uncertain=False`), or `("generic", True)` when
    nothing matches -- an explicit, honest admission of uncertainty
    rather than a guessed classification (spec Part A §4).
    """
    text = description.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return category, False
    return "generic", True


def build_research_plan(pitch: Pitch) -> ResearchPlan:
    """Produce a `ResearchPlan` for `pitch` -- the first step of Market
    Reality Research (Release 0.6.1 spec Parts A/4-5), before any web
    search happens. Pure and deterministic: no provider call, no
    network access.
    """
    business_model, is_uncertain = classify_business_model(pitch.description)
    templates = _GENERIC_OBJECTIVES if is_uncertain else _OBJECTIVE_TEMPLATES[business_model]

    topic = _topic_phrase(pitch)
    objectives = [
        ResearchObjective(
            category=category,
            query=template.format(company=pitch.company_name, topic=topic),
        )
        for category, template in templates
    ]
    return ResearchPlan(
        business_model=business_model, is_uncertain=is_uncertain, objectives=objectives
    )


def _topic_phrase(pitch: Pitch) -> str:
    """A short phrase describing what the pitch is about, for filling
    `{topic}` in an objective's query template. Bounded to keep every
    search query a reasonable length."""
    description = re.sub(r"\s+", " ", pitch.description).strip()
    return description[:150] if description else pitch.company_name
