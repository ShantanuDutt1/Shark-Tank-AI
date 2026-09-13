"""
Tests for `agents.shark_agent.SharkAgent`'s Release 0.5 behavior: real
provider-backed questions, structured evaluation, and deliberation,
plus each method's deterministic fallback. Uses `tests.fakes.FakeProvider`
exclusively -- no network access, no API key (Release 0.5 spec B27).
"""

from __future__ import annotations

import json

import pytest

from agents.shark_agent import (
    BALANCED_PERSONA,
    CONSERVATIVE_PERSONA,
    GROWTH_PERSONA,
    SharkAgent,
)
from models.enums import SpeakerRole
from models.schemas import Offer, Pitch
from providers.exceptions import ProviderNotConfiguredError, ProviderResponseError
from tests.fakes import FakeProvider, unconfigured_provider

VALID_OFFER_JSON = json.dumps(
    {
        "interested": True,
        "amount": 250000,
        "equity_pct": 8.5,
        "conditions": "Board observer seat",
        "rationale": "Strong existing customer base and clear revenue.",
        "confidence": 0.8,
    }
)

DECLINE_OFFER_JSON = json.dumps(
    {
        "interested": False,
        "amount": None,
        "equity_pct": None,
        "conditions": None,
        "rationale": "Not enough evidence of retention.",
        "confidence": 0.6,
    }
)


def make_pitch(**overrides) -> Pitch:
    defaults = dict(
        id="pitch-1",
        company_name="Widget Co",
        founder_name="Ada",
        description="We sell smart widgets to hardware stores.",
    )
    defaults.update(overrides)
    return Pitch(**defaults)


ALL_PERSONAS = [
    (SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA),
    (SpeakerRole.GROWTH_VC, GROWTH_PERSONA),
    (SpeakerRole.BALANCED_VC, BALANCED_PERSONA),
]


# ---------------------------------------------------------------------
# Each of the three personas
# ---------------------------------------------------------------------


@pytest.mark.parametrize("role,persona", ALL_PERSONAS)
def test_each_persona_produces_a_question_via_the_provider(role, persona):
    provider = FakeProvider(fixed_response="What is your monthly churn rate?")
    shark = SharkAgent(role, persona, provider)

    question = shark.ask_question(make_pitch(), [])

    assert question == "What is your monthly churn rate?"
    assert provider.call_count == 1


@pytest.mark.parametrize("role,persona", ALL_PERSONAS)
def test_each_persona_s_system_prompt_mentions_its_own_name_and_attitude(role, persona):
    provider = FakeProvider(fixed_response="A question.")
    shark = SharkAgent(role, persona, provider)

    shark.ask_question(make_pitch(), [])

    system_prompt = provider.last_system_message()
    assert persona.name in system_prompt
    assert persona.core_attitude in system_prompt
    for priority in persona.priorities:
        assert priority in system_prompt


def test_different_personas_get_different_system_prompts():
    provider_a = FakeProvider(fixed_response="q")
    provider_b = FakeProvider(fixed_response="q")
    conservative = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider_a)
    growth = SharkAgent(SpeakerRole.GROWTH_VC, GROWTH_PERSONA, provider_b)

    conservative.ask_question(make_pitch(), [])
    growth.ask_question(make_pitch(), [])

    assert provider_a.last_system_message() != provider_b.last_system_message()


# ---------------------------------------------------------------------
# Persona-specific prompt construction
# ---------------------------------------------------------------------


def test_pitch_details_appear_in_the_question_prompt():
    provider = FakeProvider(fixed_response="q")
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    shark.ask_question(make_pitch(company_name="Widget Co", description="We sell widgets."), [])

    user_prompt = provider.last_user_message()
    assert "Widget Co" in user_prompt
    assert "We sell widgets." in user_prompt


def test_conversation_history_appears_in_the_prompt():
    from models.schemas import ConversationMessage

    provider = FakeProvider(fixed_response="q")
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)
    conversation = [
        ConversationMessage(
            id="m1", speaker=SpeakerRole.FOUNDER, content="We have 40 paying customers.", turn_index=0
        )
    ]

    shark.ask_question(make_pitch(), conversation)

    assert "We have 40 paying customers." in provider.last_user_message()


def test_empty_conversation_still_produces_a_usable_prompt():
    provider = FakeProvider(fixed_response="q")
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    question = shark.ask_question(make_pitch(), [])

    assert question == "q"
    assert "No questions have been asked yet" in provider.last_user_message()


# ---------------------------------------------------------------------
# Questions are not hard-coded templates
# ---------------------------------------------------------------------


def test_question_reflects_the_actual_provider_response_not_a_template():
    provider = FakeProvider(fixed_response="What's your burn rate given the new hires?")
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    question = shark.ask_question(make_pitch(), [])

    assert question == "What's your burn rate given the new hires?"
    assert "why will" not in question.lower()  # not the Release 0.4 fixed template


def test_each_shark_can_produce_a_distinct_question_for_the_same_pitch():
    conservative = SharkAgent(
        SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, FakeProvider(fixed_response="Q about risk.")
    )
    growth = SharkAgent(
        SpeakerRole.GROWTH_VC, GROWTH_PERSONA, FakeProvider(fixed_response="Q about scale.")
    )

    pitch = make_pitch()
    q1 = conservative.ask_question(pitch, [])
    q2 = growth.ask_question(pitch, [])

    assert q1 != q2


# ---------------------------------------------------------------------
# Structured evaluation / offer conversion
# ---------------------------------------------------------------------


def test_evaluate_pitch_returns_a_structured_offer():
    provider = FakeProvider(fixed_response=VALID_OFFER_JSON)
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    offer = shark.evaluate_pitch(make_pitch(), {"conversation": []})

    assert isinstance(offer, Offer)
    assert offer.interested is True
    assert offer.amount == 250000
    assert offer.equity_pct == 8.5
    assert offer.conditions == "Board observer seat"
    assert offer.confidence == 0.8
    assert offer.shark_id == "conservative_vc"
    assert offer.pitch_id == "pitch-1"


def test_evaluate_pitch_handles_markdown_fenced_json():
    fenced = f"```json\n{VALID_OFFER_JSON}\n```"
    provider = FakeProvider(fixed_response=fenced)
    shark = SharkAgent(SpeakerRole.GROWTH_VC, GROWTH_PERSONA, provider)

    offer = shark.evaluate_pitch(make_pitch(), {})

    assert offer.interested is True
    assert offer.amount == 250000


def test_decline_offer_nulls_out_amount_and_equity_even_if_provider_sent_some():
    payload = json.loads(DECLINE_OFFER_JSON)
    payload["amount"] = 999  # a misbehaving provider sending numbers anyway
    payload["equity_pct"] = 10
    provider = FakeProvider(fixed_response=json.dumps(payload))
    shark = SharkAgent(SpeakerRole.BALANCED_VC, BALANCED_PERSONA, provider)

    offer = shark.evaluate_pitch(make_pitch(), {})

    assert offer.interested is False
    assert offer.amount is None
    assert offer.equity_pct is None


def test_malformed_json_raises_provider_response_error():
    provider = FakeProvider(fixed_response="I think this looks promising!")
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    with pytest.raises(ProviderResponseError):
        shark.evaluate_pitch(make_pitch(), {})


def test_json_missing_required_field_raises_provider_response_error():
    incomplete = json.dumps({"amount": 100})  # no "interested", no "rationale"
    provider = FakeProvider(fixed_response=incomplete)
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    with pytest.raises(ProviderResponseError):
        shark.evaluate_pitch(make_pitch(), {})


def test_equity_pct_over_100_is_rejected():
    payload = json.loads(VALID_OFFER_JSON)
    payload["equity_pct"] = 150
    provider = FakeProvider(fixed_response=json.dumps(payload))
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    with pytest.raises(ProviderResponseError):
        shark.evaluate_pitch(make_pitch(), {})


def test_negative_equity_pct_is_rejected():
    payload = json.loads(VALID_OFFER_JSON)
    payload["equity_pct"] = -5
    provider = FakeProvider(fixed_response=json.dumps(payload))
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    with pytest.raises(ProviderResponseError):
        shark.evaluate_pitch(make_pitch(), {})


def test_negative_amount_is_rejected():
    payload = json.loads(VALID_OFFER_JSON)
    payload["amount"] = -100000
    provider = FakeProvider(fixed_response=json.dumps(payload))
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    with pytest.raises(ProviderResponseError):
        shark.evaluate_pitch(make_pitch(), {})


def test_evaluation_confidence_is_never_exactly_zero_for_a_real_response():
    payload = json.loads(VALID_OFFER_JSON)
    payload["confidence"] = 0.0  # a provider that (mis)reports zero confidence
    provider = FakeProvider(fixed_response=json.dumps(payload))
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    offer = shark.evaluate_pitch(make_pitch(), {})

    # 0.0 is reserved for fallback_offer() -- a *real* evaluation's
    # confidence is floored just above it so the two are distinguishable.
    assert offer.confidence > 0.0


# ---------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------


def test_unconfigured_provider_raises_on_ask_question():
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, unconfigured_provider())
    with pytest.raises(ProviderNotConfiguredError):
        shark.ask_question(make_pitch(), [])


def test_no_provider_at_all_raises_on_ask_question():
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, None)
    with pytest.raises(ProviderNotConfiguredError):
        shark.ask_question(make_pitch(), [])


def test_unconfigured_provider_raises_on_evaluate_pitch():
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, unconfigured_provider())
    with pytest.raises(ProviderNotConfiguredError):
        shark.evaluate_pitch(make_pitch(), {})


def test_fallback_question_is_deterministic_and_does_not_call_provider():
    provider = FakeProvider(fixed_response="should not be used")
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    question = shark.fallback_question(make_pitch(company_name="Acme"))

    assert "Acme" in question
    assert provider.call_count == 0


def test_fallback_offer_is_honest_not_interested_with_zero_confidence():
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, None)

    offer = shark.fallback_offer(make_pitch(), reason="test_reason")

    assert offer.interested is False
    assert offer.amount is None
    assert offer.equity_pct is None
    assert offer.confidence == 0.0
    assert "test_reason" in offer.rationale


def test_fallback_offer_never_fabricates_investment_interest():
    """Release 0.5 spec B4: 'do not silently convert provider failures
    into fake investment decisions.'"""
    shark = SharkAgent(SpeakerRole.GROWTH_VC, GROWTH_PERSONA, None)
    offer = shark.fallback_offer(make_pitch(), reason="any_failure")
    assert offer.interested is False


# ---------------------------------------------------------------------
# Deliberation
# ---------------------------------------------------------------------


def _sample_offer(interested: bool = True) -> Offer:
    return Offer(
        shark_id="conservative_vc",
        pitch_id="pitch-1",
        interested=interested,
        amount=100000 if interested else None,
        equity_pct=5.0 if interested else None,
        rationale="Solid fundamentals.",
        confidence=0.7,
    )


def test_deliberate_returns_provider_text():
    provider = FakeProvider(fixed_response="I'm impressed by the retention numbers here.")
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)

    line = shark.deliberate(make_pitch(), _sample_offer(), [])

    assert line == "I'm impressed by the retention numbers here."


def test_deliberate_truncates_to_at_most_two_sentences():
    long_text = (
        "First point about the market. Second point about the team. "
        "Third point that should be dropped. Fourth point also dropped."
    )
    provider = FakeProvider(fixed_response=long_text)
    shark = SharkAgent(SpeakerRole.GROWTH_VC, GROWTH_PERSONA, provider)

    line = shark.deliberate(make_pitch(), _sample_offer(), [])

    assert "First point about the market." in line
    assert "Second point about the team." in line
    assert "Third point" not in line
    assert "Fourth point" not in line


def test_deliberate_raises_on_provider_failure():
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, unconfigured_provider())
    with pytest.raises(ProviderNotConfiguredError):
        shark.deliberate(make_pitch(), _sample_offer(), [])


def test_fallback_deliberation_is_deterministic_and_reflects_offer_stance():
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, None)

    interested_line = shark.fallback_deliberation(_sample_offer(interested=True))
    declined_line = shark.fallback_deliberation(_sample_offer(interested=False))

    assert "want in" in interested_line.lower()
    assert "pass" in declined_line.lower()


def test_fallback_deliberation_for_zero_confidence_does_not_claim_a_stance():
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, None)
    failed_offer = shark.fallback_offer(make_pitch(), reason="provider_down")

    line = shark.fallback_deliberation(failed_offer)

    assert "want in" not in line.lower()
    assert "pass on" not in line.lower()


def test_own_evaluation_is_included_in_the_deliberation_prompt():
    provider = FakeProvider(fixed_response="A reaction.")
    shark = SharkAgent(SpeakerRole.CONSERVATIVE_VC, CONSERVATIVE_PERSONA, provider)
    offer = _sample_offer(interested=True)

    shark.deliberate(make_pitch(), offer, [])

    assert "Solid fundamentals." in provider.last_user_message()


def test_sharks_can_disagree_given_different_provider_responses():
    """Not a claim that the LLM will disagree -- just that nothing in
    this class prevents two Sharks' deliberation lines from differing
    when their provider responses differ (Release 0.5 spec B16)."""
    conservative = SharkAgent(
        SpeakerRole.CONSERVATIVE_VC,
        CONSERVATIVE_PERSONA,
        FakeProvider(fixed_response="I don't see enough evidence this survives a bad year."),
    )
    growth = SharkAgent(
        SpeakerRole.GROWTH_VC,
        GROWTH_PERSONA,
        FakeProvider(fixed_response="If the market converts, this could scale extremely fast."),
    )

    offer = _sample_offer()
    line_a = conservative.deliberate(make_pitch(), offer, [])
    line_b = growth.deliberate(make_pitch(), offer, [])

    assert line_a != line_b
