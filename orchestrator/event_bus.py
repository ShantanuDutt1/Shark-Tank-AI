"""
Minimal synchronous Event Bus for Shark Tank AI.

`docs/event_catalog.md` defines the full planned message vocabulary as
a specification; this module is the first concrete implementation of
the publish/subscribe mechanism that vocabulary is meant to travel
over (`docs/architecture.md` -> Event Bus, previously "no publish/
subscribe mechanism exists today").

This implementation is deliberately the simplest one that satisfies
the contract:

- Typed events only (`orchestrator.events.Event` subclasses) -- no
  stringly-typed topic names.
- Handlers for a given event type run synchronously, in the order
  they were subscribed, in the same call stack as `publish()`.
- No persistence, no cross-process delivery, no retry policy.

A future release may replace this with an asynchronous, buffered, or
distributed implementation; nothing outside this module should need to
change for that to happen, since callers only ever see `subscribe()`
and `publish()`.

Per `docs/event_catalog.md` -> *Notes for Implementation* #1, this bus
does not enforce "one publisher per event" at runtime -- that is a
design-time convention documented per-event in the catalog and upheld
by `orchestrator/orchestrator.py`'s Session Director, not a mechanism
this class polices.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, DefaultDict, List, Type, TypeVar

from config.logging_config import get_logger
from orchestrator.events import Event

logger = get_logger(__name__)

EventT = TypeVar("EventT", bound=Event)
Handler = Callable[[Event], None]


class EventBus:
    """A synchronous, in-process publish/subscribe bus for typed events."""

    def __init__(self) -> None:
        self._handlers: DefaultDict[Type[Event], List[Handler]] = defaultdict(list)

    def subscribe(self, event_type: Type[EventT], handler: Callable[[EventT], None]) -> None:
        """Register `handler` to be called with every future `event_type` event.

        Multiple handlers for the same event type are supported and run
        in subscription order.
        """
        self._handlers[event_type].append(handler)  # type: ignore[arg-type]

    def publish(self, event: Event) -> None:
        """Publish `event` to every handler subscribed to its exact type.

        Runs synchronously: by the time `publish()` returns, every
        subscribed handler has already run. A handler that needs to be
        resilient to its own failures is responsible for catching its
        own exceptions -- this bus does not swallow handler errors,
        consistent with `docs/coding_standards.md` -> Error Handling
        ("never a bare `except Exception:` that silently swallows an
        error").
        """
        event_type = type(event)
        logger.debug("Publishing %s for session=%s", event_type.__name__, event.session_id)
        for handler in self._handlers.get(event_type, []):
            handler(event)
