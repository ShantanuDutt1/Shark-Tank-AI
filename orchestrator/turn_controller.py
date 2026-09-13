"""
Turn control for the Question Round of a Shark Tank AI session.

This is the "generic enough that the exact Shark implementations can
become more intelligent later" turn-sequencing mechanism the Release
0.4 specification calls for. It knows nothing about *what* a Shark
says -- only whose turn it is next. Content generation belongs to
`agents/shark_agent.py` and `agents/moderator_agent.py`; sequencing
belongs here; deciding *when* to invoke either belongs to the Session
Director (`orchestrator/orchestrator.py`).

The Moderator's own turns (the session-opening welcome, the Question
Round announcement, the deliberation announcement, the closing
message) are handled directly by the Session Director outside this
sequence -- this controller only tracks the fixed Shark/Founder
alternation described in the Release 0.4 spec:

    Shark 1 -> Founder -> Shark 2 -> Founder -> Shark 3 -> Founder

with the Session Director speaking as Moderator immediately before the
first Shark's turn and immediately after the sequence completes.
"""

from __future__ import annotations

from typing import List, Optional

from models.enums import SpeakerRole

#: The fixed speaking order for a single Question Round, per Release
#: 0.4 spec section 6. Order matches `docs/agent_personas.md` sections
#: 5-7 (Conservative, then Growth, then Balanced).
QUESTION_ROUND_SEQUENCE: List[SpeakerRole] = [
    SpeakerRole.CONSERVATIVE_VC,
    SpeakerRole.FOUNDER,
    SpeakerRole.GROWTH_VC,
    SpeakerRole.FOUNDER,
    SpeakerRole.BALANCED_VC,
    SpeakerRole.FOUNDER,
]


class TurnController:
    """Drives the fixed Shark/Founder speaking order for one Question Round.

    One instance is scoped to a single session (owned by the Session
    Director) and reset at the start of each Question Round via
    `reset()`.
    """

    def __init__(self) -> None:
        self._sequence = QUESTION_ROUND_SEQUENCE
        self._index = -1  # -1: nothing has spoken yet this round

    def reset(self) -> None:
        """Return to "nothing has spoken yet", ready for a new Question Round."""
        self._index = -1

    @property
    def current_speaker(self) -> Optional[SpeakerRole]:
        """Who is currently expected to speak, or `None` before `advance()`
        has been called at least once, or after the sequence is exhausted."""
        if 0 <= self._index < len(self._sequence):
            return self._sequence[self._index]
        return None

    @property
    def awaiting_founder_response(self) -> bool:
        """Whether the founder is the current speaker."""
        return self.current_speaker == SpeakerRole.FOUNDER

    @property
    def is_complete(self) -> bool:
        """Whether the fixed sequence has been fully exhausted."""
        return self._index >= len(self._sequence) - 1

    def advance(self) -> Optional[SpeakerRole]:
        """Move to the next speaker in the fixed sequence.

        Returns the new current speaker, or `None` if the sequence was
        already exhausted -- the Session Director should treat `None`
        as "Question Round is complete; begin Internal Deliberation."
        """
        if self.is_complete:
            return None
        self._index += 1
        return self._sequence[self._index]
