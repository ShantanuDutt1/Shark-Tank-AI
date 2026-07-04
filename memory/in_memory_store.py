"""
Placeholder in-memory implementation of `BaseMemory`.

This is the default memory backend so the application can run without
any external dependency (database, Redis, etc.) configured. It does
not yet implement any storage logic beyond the minimal structure
needed to satisfy the `BaseMemory` interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from memory.base_memory import BaseMemory


class InMemoryStore(BaseMemory):
    """Placeholder in-memory store. Not yet implemented."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def save(self, session_id: str, key: str, value: Any) -> None:
        raise NotImplementedError

    def load(self, session_id: str, key: str) -> Optional[Any]:
        raise NotImplementedError

    def history(self, session_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def clear(self, session_id: str) -> None:
        raise NotImplementedError
