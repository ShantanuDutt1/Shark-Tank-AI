"""
Base agent abstraction for Shark Tank AI.

Every "shark" agent (and any supporting agent, such as a pitch-analysis
or valuation agent) will implement this interface. No functionality is
implemented yet.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from models.schemas import Offer, Pitch, SharkPersona
from providers.base_provider import BaseProvider


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        persona: Optional[SharkPersona] = None,
        provider: Optional[BaseProvider] = None,
    ) -> None:
        self.persona = persona
        self.provider = provider

    @abstractmethod
    def evaluate_pitch(self, pitch: Pitch, context: Optional[Dict[str, Any]] = None) -> Offer:
        """Evaluate a pitch and produce an offer (or a rejection)."""
        raise NotImplementedError
