"""
Specific exception types for orchestration failures.

`docs/agent_contract.md` -> *Error Handling* and
`docs/coding_standards.md` -> *Error Handling* both require raising a
specific exception type for unrecoverable failures, never a bare
`Exception`. These are that specific-type hierarchy for the Session
Director (`orchestrator/orchestrator.py`).
"""

from __future__ import annotations


class SessionDirectorError(Exception):
    """Base class for every Session Director error."""


class InvalidTurnError(SessionDirectorError):
    """Raised when an action is attempted that doesn't match whose turn it
    is -- e.g. `start_session()` called on a session already in
    progress, or `submit_founder_response()` called when the founder is
    not the current speaker.

    This is an unrecoverable *programming* error, not a transient
    provider failure (`docs/agent_contract.md` -> *Error Handling*
    distinguishes the two) -- the caller has violated the state
    machine's rules, and retrying with the same call won't help.
    """
