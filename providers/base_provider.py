"""
LLM provider abstraction for Shark Tank AI.

Defines the interface that all LLM provider integrations (Anthropic,
OpenAI, local models, etc.) will implement, so agents can remain
provider-agnostic.

No functionality is implemented yet -- this module only establishes
the contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Generate a text completion for the given conversation messages."""
        raise NotImplementedError

    @property
    def is_configured(self) -> bool:
        """Whether this provider has the credentials it needs to run."""
        return bool(self.api_key)
