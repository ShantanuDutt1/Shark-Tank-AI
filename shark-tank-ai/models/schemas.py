"""
Core data models for Shark Tank AI.

These pydantic models describe the shapes of the domain objects the
application will eventually operate on (a pitch, a shark persona, an
offer, and the negotiation session that ties them together). No
business logic lives here -- only data structure definitions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DealStatus(str, Enum):
    """Possible outcomes of a negotiation."""

    PENDING = "pending"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COUNTERED = "countered"


class Pitch(BaseModel):
    """A founder's pitch submitted to the panel of sharks."""

    id: str
    founder_name: str
    company_name: str
    description: str
    ask_amount: float
    equity_offered_pct: float
    valuation: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SharkPersona(BaseModel):
    """Configuration describing a single AI 'shark' agent's persona."""

    id: str
    name: str
    investment_style: str
    personality_traits: List[str] = Field(default_factory=list)
    risk_tolerance: float = 0.5  # 0.0 (cautious) - 1.0 (aggressive)


class Offer(BaseModel):
    """An offer made by a shark in response to a pitch."""

    shark_id: str
    pitch_id: str
    amount: float
    equity_pct: float
    conditions: Optional[str] = None
    status: DealStatus = DealStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NegotiationSession(BaseModel):
    """Represents a full negotiation session for a single pitch."""

    id: str
    pitch: Pitch
    offers: List[Offer] = Field(default_factory=list)
    final_status: DealStatus = DealStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
