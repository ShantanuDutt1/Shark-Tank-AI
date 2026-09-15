"""
Tests for `agents.moderator_agent.ModeratorAgent`.

Release 0.9.5 QA finding: no test in this repository asserted the
canonical opening/closing wording *exactly*, despite both being
explicitly required, fixed text (Release 0.4 spec section 8 for the
welcome message; Release 0.9.5 spec Part 20 for the three closing
outcome messages) that must never be casually rewritten. This module
closes that gap -- these are "verify structure... except where wording
is explicitly canonical" tests per Release 0.9.5 spec Part 30.
"""

from __future__ import annotations

from agents.moderator_agent import (
    OUTCOME_DEAL_ACCEPTED,
    OUTCOME_NO_DEAL,
    OUTCOME_NO_INTEREST,
    WELCOME_MESSAGE,
    ModeratorAgent,
)


def test_welcome_message_is_exactly_canonical():
    assert WELCOME_MESSAGE == (
        "Welcome, Little Fish. You are in the presence of the Sharks. "
        "Present your proposal. Paste the text or upload a PDF"
    )
    assert ModeratorAgent().welcome_message() == WELCOME_MESSAGE


def test_outcome_messages_are_exactly_canonical():
    assert OUTCOME_NO_INTEREST == "Sorry Little Fish, the Sharks were not impressed"
    assert OUTCOME_NO_DEAL == "Sorry Little Fish, there was nothing for you here today"
    assert OUTCOME_DEAL_ACCEPTED == "Congratulations, Little Fish. You will now swim with the Sharks!"


def test_closing_message_maps_each_outcome_to_its_canonical_line():
    moderator = ModeratorAgent()
    assert moderator.closing_message("no_interest") == OUTCOME_NO_INTEREST
    assert moderator.closing_message("no_deal") == OUTCOME_NO_DEAL
    assert moderator.closing_message("deal_accepted") == OUTCOME_DEAL_ACCEPTED


def test_closing_message_falls_back_to_no_deal_for_an_unrecognized_outcome():
    """Defensive only -- every real call site in `orchestrator.py`
    always passes one of the three closed-set values; this documents
    the fallback without ever expecting it to trigger in practice."""
    assert ModeratorAgent().closing_message("not-a-real-outcome") == OUTCOME_NO_DEAL


def test_the_three_outcome_messages_are_all_distinct():
    assert len({OUTCOME_NO_INTEREST, OUTCOME_NO_DEAL, OUTCOME_DEAL_ACCEPTED}) == 3
