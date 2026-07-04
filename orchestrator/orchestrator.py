"""
Placeholder orchestrator for Shark Tank AI.

The orchestrator will eventually coordinate the panel of shark agents:
routing a pitch to each shark, collecting their offers, running any
negotiation rounds, and returning a final `NegotiationSession`.

No functionality is implemented yet.
"""

from __future__ import annotations

from typing import List, Optional

from agents.base_agent import BaseAgent
from models.schemas import NegotiationSession, Pitch


class SharkTankOrchestrator:
    """Placeholder orchestrator. Not yet implemented."""

    def __init__(self, agents: Optional[List[BaseAgent]] = None) -> None:
        self.agents = agents or []

    def run_pitch(self, pitch: Pitch) -> NegotiationSession:
        """Run a full pitch session across all configured shark agents."""
        raise NotImplementedError
