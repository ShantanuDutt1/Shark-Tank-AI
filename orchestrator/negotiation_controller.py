"""
Turn control for the Negotiation phase (Release 0.6).

Deliberately separate from `orchestrator.turn_controller.TurnController`,
which drives the *fixed*, always-three-turn Question Round:
Negotiation's length is variable -- one turn per Shark who actually
made an offer during `INVESTMENT_DECISION` (zero, one, two, or three),
in the existing committee order (Conservative, Growth, Balanced) -- so
it needs its own, simpler sequencing rather than being squeezed into
`TurnController`'s fixed-length assumptions. This is not a duplicate
turn controller for the same concern; it is the concern `TurnController`
was never meant to cover (Release 0.5's own spec section B11 already
established this project's convention of not stretching an existing
controller to cover a genuinely different turn-taking shape).
"""

from __future__ import annotations

from models.enums import SpeakerRole


class NegotiationController:
    """Drives one founder-counter/Shark-response cycle per interested Shark."""

    def __init__(self, interested_sharks: list[SpeakerRole]) -> None:
        self._queue: list[SpeakerRole] = list(interested_sharks)
        self._current: SpeakerRole | None = None

    def start(self) -> SpeakerRole | None:
        """Begin negotiating with the first interested Shark, or `None`
        if no Shark made an offer."""
        self._current = self._queue.pop(0) if self._queue else None
        return self._current

    @property
    def current_shark(self) -> SpeakerRole | None:
        """Which Shark the founder is currently negotiating with, or
        `None` if negotiation hasn't started or has finished."""
        return self._current

    @property
    def awaiting_founder_counter(self) -> bool:
        """Whether the founder is expected to submit a counter-offer
        right now."""
        return self._current is not None

    def advance(self) -> SpeakerRole | None:
        """Move to the next interested Shark, or `None` if negotiation
        is complete."""
        self._current = self._queue.pop(0) if self._queue else None
        return self._current

    @property
    def is_complete(self) -> bool:
        return self._current is None
