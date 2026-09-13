"""
Tests for `agents.research_planner` (Release 0.6.1).

Pure, offline tests -- no provider, no network access -- since
`build_research_plan()` is a deterministic keyword heuristic, not an
LLM call (spec Part A section 26).
"""

from __future__ import annotations

from agents.research_planner import build_research_plan, classify_business_model
from models.schemas import Pitch


def make_pitch(description: str) -> Pitch:
    return Pitch(id="test-pitch", company_name="Acme", description=description)


def test_saas_pitch_produces_saas_objectives():
    pitch = make_pitch(
        "We sell a SaaS subscription software product with strong recurring revenue and ARR growth."
    )
    plan = build_research_plan(pitch)

    assert plan.business_model == "saas"
    assert plan.is_uncertain is False
    categories = [o.category for o in plan.objectives]
    assert "arr_revenue_multiples" in categories
    assert "margin_and_churn" in categories


def test_consumer_pitch_produces_consumer_objectives():
    pitch = make_pitch("A direct-to-consumer CPG retail brand selling snacks online.")
    plan = build_research_plan(pitch)

    assert plan.business_model == "consumer"
    categories = [o.category for o in plan.objectives]
    assert "retail_economics" in categories
    assert "comparable_brands" in categories


def test_marketplace_pitch_produces_marketplace_objectives():
    pitch = make_pitch("A two-sided marketplace connecting buyers and sellers, taking a take rate on GMV.")
    plan = build_research_plan(pitch)

    assert plan.business_model == "marketplace"
    categories = [o.category for o in plan.objectives]
    assert "gmv_and_take_rate" in categories
    assert "network_effects" in categories


def test_restaurant_pitch_produces_restaurant_objectives():
    pitch = make_pitch("A quick-service restaurant chain with a rotating menu for diners.")
    plan = build_research_plan(pitch)

    assert plan.business_model == "restaurant"
    categories = [o.category for o in plan.objectives]
    assert "labor_and_occupancy_costs" in categories
    assert "margin_benchmarks" in categories


def test_cleantech_pitch_produces_cleantech_objectives():
    pitch = make_pitch("A cleantech startup deploying solar battery storage to reduce emissions.")
    plan = build_research_plan(pitch)

    assert plan.business_model == "cleantech"
    categories = [o.category for o in plan.objectives]
    assert "deployment_economics" in categories
    assert "regulatory_context" in categories


def test_professional_services_pitch_produces_relevant_objectives():
    pitch = make_pitch("A consulting agency billing clients by the billable hour for advisory work.")
    plan = build_research_plan(pitch)

    assert plan.business_model == "professional_services"
    categories = [o.category for o in plan.objectives]
    assert "utilization_benchmarks" in categories
    assert "revenue_ebitda_multiples" in categories


def test_ambiguous_pitch_produces_conservative_generic_plan():
    """Spec Part A section 4: when the business model can't be
    confidently classified, the plan must be the small, conservative
    generic set -- never an invented specific classification."""
    pitch = make_pitch("We help people do things better and faster than before.")
    plan = build_research_plan(pitch)

    assert plan.business_model == "generic"
    assert plan.is_uncertain is True
    assert len(plan.objectives) == 3


def test_classify_business_model_returns_uncertain_for_generic_text():
    business_model, is_uncertain = classify_business_model("A general business idea.")
    assert business_model == "generic"
    assert is_uncertain is True


def test_every_specific_plan_has_between_3_and_8_objectives():
    """Spec Part A section 5: 3-8 targeted research objectives."""
    descriptions = [
        "A SaaS subscription software company with recurring revenue.",
        "A direct-to-consumer retail brand.",
        "A marketplace connecting buyers and sellers with a take rate.",
        "A restaurant with a menu for diners.",
        "A cleantech company deploying solar panels.",
        "A consulting agency billing by the billable hour.",
        "We help people do things better.",
    ]
    for description in descriptions:
        plan = build_research_plan(make_pitch(description))
        assert 3 <= len(plan.objectives) <= 8


def test_objectives_are_not_blindly_identical_across_categories():
    """Spec Part A section 5: not every proposal should get every
    category -- different business models must produce different
    objective sets."""
    saas_plan = build_research_plan(make_pitch("A SaaS subscription product with recurring revenue."))
    restaurant_plan = build_research_plan(make_pitch("A restaurant with a menu for diners."))

    saas_categories = {o.category for o in saas_plan.objectives}
    restaurant_categories = {o.category for o in restaurant_plan.objectives}
    assert saas_categories != restaurant_categories
