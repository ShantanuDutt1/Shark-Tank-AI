"""
Tests for `orchestrator.turn_controller.TurnController`.
"""

from __future__ import annotations

from models.enums import SpeakerRole
from orchestrator.turn_controller import TurnController


def test_initial_state_has_no_current_speaker():
    turns = TurnController()
    assert turns.current_speaker is None
    assert not turns.awaiting_founder_response
    assert not turns.is_complete


def test_full_sequence_alternates_sharks_and_founder():
    turns = TurnController()
    expected = [
        SpeakerRole.CONSERVATIVE_VC,
        SpeakerRole.FOUNDER,
        SpeakerRole.GROWTH_VC,
        SpeakerRole.FOUNDER,
        SpeakerRole.BALANCED_VC,
        SpeakerRole.FOUNDER,
    ]
    actual = [turns.advance() for _ in expected]
    assert actual == expected


def test_awaiting_founder_response_tracks_current_speaker():
    turns = TurnController()
    turns.advance()  # Conservative VC
    assert not turns.awaiting_founder_response
    turns.advance()  # Founder
    assert turns.awaiting_founder_response


def test_is_complete_only_after_last_founder_turn():
    turns = TurnController()
    for _ in range(5):
        turns.advance()
        assert not turns.is_complete
    turns.advance()  # final Founder turn
    assert turns.is_complete


def test_advance_past_the_end_returns_none_and_stays_complete():
    turns = TurnController()
    for _ in range(6):
        turns.advance()
    assert turns.advance() is None
    assert turns.is_complete


def test_reset_returns_to_initial_state():
    turns = TurnController()
    turns.advance()
    turns.advance()
    turns.reset()
    assert turns.current_speaker is None
    assert not turns.is_complete
