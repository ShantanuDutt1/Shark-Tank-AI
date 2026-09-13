"""
Tests for `orchestrator.event_bus.EventBus`.
"""

from __future__ import annotations

from orchestrator import events
from orchestrator.event_bus import EventBus


def test_publish_calls_subscribed_handler():
    bus = EventBus()
    received = []
    bus.subscribe(events.SessionStarted, lambda e: received.append(e))

    event = events.SessionStarted(session_id="s1")
    bus.publish(event)

    assert received == [event]


def test_handlers_run_in_subscription_order():
    bus = EventBus()
    order = []
    bus.subscribe(events.SessionStarted, lambda e: order.append("first"))
    bus.subscribe(events.SessionStarted, lambda e: order.append("second"))

    bus.publish(events.SessionStarted(session_id="s1"))

    assert order == ["first", "second"]


def test_multiple_handlers_all_receive_the_event():
    bus = EventBus()
    counts = {"a": 0, "b": 0}
    bus.subscribe(events.DebateStarted, lambda e: counts.__setitem__("a", counts["a"] + 1))
    bus.subscribe(events.DebateStarted, lambda e: counts.__setitem__("b", counts["b"] + 1))

    bus.publish(events.DebateStarted(session_id="s1"))

    assert counts == {"a": 1, "b": 1}


def test_unsubscribed_event_type_has_no_handlers_called():
    bus = EventBus()
    received = []
    bus.subscribe(events.SessionStarted, lambda e: received.append(e))

    # No handler subscribed to QuestionAsked -- publishing it must not
    # raise or invoke the SessionStarted handler.
    bus.publish(events.QuestionAsked(session_id="s1", speaker=None, question="q"))  # type: ignore[arg-type]

    assert received == []


def test_event_type_isolation():
    """A handler for one event type never fires for a different type."""
    bus = EventBus()
    session_started_calls = []
    debate_started_calls = []
    bus.subscribe(events.SessionStarted, lambda e: session_started_calls.append(e))
    bus.subscribe(events.DebateStarted, lambda e: debate_started_calls.append(e))

    bus.publish(events.DebateStarted(session_id="s1"))

    assert session_started_calls == []
    assert len(debate_started_calls) == 1
