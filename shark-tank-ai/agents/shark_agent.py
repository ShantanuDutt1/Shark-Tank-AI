"""
Placeholder concrete shark agent.

Will eventually use a `BaseProvider` and a `SharkPersona` to generate
realistic, in-character negotiation behavior. No functionality is
implemented yet.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent
from models.schemas import Offer, Pitch


class SharkAgent(BaseAgent):
    """Placeholder shark agent. Not yet implemented."""

    def evaluate_pitch(self, pitch: Pitch, context: Optional[Dict[str, Any]] = None) -> Offer:
        raise NotImplementedError
