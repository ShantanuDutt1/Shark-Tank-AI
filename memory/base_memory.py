"""
Memory abstraction for Shark Tank AI.

Defines the interface that all memory backends (in-memory, SQLite,
Redis, vector store, etc.) will implement so agents and the
orchestrator can persist and recall conversation / negotiation state.

No functionality is implemented yet -- this module only establishes
the contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseMemory(ABC):
    """Abstract base class for all memory backends."""

    @abstractmethod
    def save(self, session_id: str, key: str, value: Any) -> None:
        """Persist a value under a given session and key."""
        raise NotImplementedError

    @abstractmethod
    def load(self, session_id: str, key: str) -> Optional[Any]:
        """Retrieve a previously saved value, or None if absent."""
        raise NotImplementedError

    @abstractmethod
    def history(self, session_id: str) -> List[Dict[str, Any]]:
        """Return the full recorded history for a session."""
        raise NotImplementedError

    @abstractmethod
    def clear(self, session_id: str) -> None:
        """Remove all stored data for a session."""
        raise NotImplementedError
