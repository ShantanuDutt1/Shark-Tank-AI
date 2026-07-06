"""
Shared enumerations for Shark Tank AI.

These enums are the single source of truth for the session lifecycle
(`SessionPhase`), the configurable LLM backend (`LLMProvider`), and the
investment committee roles (`SpeakerRole`). They live in `models/`
rather than `ui/` because future milestones (agents, orchestrator,
memory) will reference the exact same values — the UI is just the
first consumer.

No agent logic, LLM calls, or transition logic lives here — only the
vocabulary those future systems and the current UI will share.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List


class SessionPhase(str, Enum):
    """The nine stages of a Shark Tank AI session, in chronological order."""

    IDLE = "idle"
    PROPOSAL_UPLOADED = "proposal_uploaded"
    VALIDATION = "validation"
    QUESTION_ROUND = "question_round"
    INTERNAL_DELIBERATION = "internal_deliberation"
    VERIFICATION = "verification"
    CONSENSUS = "consensus"
    INVESTMENT_DECISION = "investment_decision"
    SESSION_COMPLETE = "session_complete"


# Canonical left-to-right ordering used to render the progress stepper.
PHASE_ORDER: List[SessionPhase] = [
    SessionPhase.IDLE,
    SessionPhase.PROPOSAL_UPLOADED,
    SessionPhase.VALIDATION,
    SessionPhase.QUESTION_ROUND,
    SessionPhase.INTERNAL_DELIBERATION,
    SessionPhase.VERIFICATION,
    SessionPhase.CONSENSUS,
    SessionPhase.INVESTMENT_DECISION,
    SessionPhase.SESSION_COMPLETE,
]

# Human-readable labels shown in the header stepper.
PHASE_LABELS: Dict[SessionPhase, str] = {
    SessionPhase.IDLE: "Idle",
    SessionPhase.PROPOSAL_UPLOADED: "Proposal Uploaded",
    SessionPhase.VALIDATION: "Validation",
    SessionPhase.QUESTION_ROUND: "Question Round",
    SessionPhase.INTERNAL_DELIBERATION: "Internal Deliberation",
    SessionPhase.VERIFICATION: "Verification",
    SessionPhase.CONSENSUS: "Consensus",
    SessionPhase.INVESTMENT_DECISION: "Investment Decision",
    SessionPhase.SESSION_COMPLETE: "Session Complete",
}

# Descriptive copy shown on the "Session Stage" card in the main panel.
# Purely display text — no logic decides when these are shown; the UI
# simply looks up the current phase.
PHASE_STAGE_MESSAGES: Dict[SessionPhase, str] = {
    SessionPhase.IDLE: "Waiting for proposal.",
    SessionPhase.PROPOSAL_UPLOADED: "Proposal received. Ready to start the session.",
    SessionPhase.VALIDATION: "Validating the proposal.",
    SessionPhase.QUESTION_ROUND: "The investment committee is questioning the founder.",
    SessionPhase.INTERNAL_DELIBERATION: "The committee is deliberating internally.",
    SessionPhase.VERIFICATION: "Verifying the committee's deliberation.",
    SessionPhase.CONSENSUS: "The committee is reaching consensus.",
    SessionPhase.INVESTMENT_DECISION: "Delivering the investment decision.",
    SessionPhase.SESSION_COMPLETE: "Session complete.",
}


class LLMProvider(str, Enum):
    """Supported LLM backends, selectable from the sidebar."""

    GEMINI = "gemini"
    OLLAMA = "ollama"


class SpeakerRole(str, Enum):
    """Every participant that can appear in the conversation history."""

    MODERATOR = "moderator"
    GROWTH_INVESTOR = "growth_investor"
    FINANCIAL_INVESTOR = "financial_investor"
    TECHNICAL_INVESTOR = "technical_investor"
    MARKETING_INVESTOR = "marketing_investor"
    RISK_INVESTOR = "risk_investor"
    FOUNDER = "founder"


# Human-readable labels shown next to each message in the conversation panel.
SPEAKER_LABELS: Dict[SpeakerRole, str] = {
    SpeakerRole.MODERATOR: "Moderator",
    SpeakerRole.GROWTH_INVESTOR: "Growth Investor",
    SpeakerRole.FINANCIAL_INVESTOR: "Financial Investor",
    SpeakerRole.TECHNICAL_INVESTOR: "Technical Investor",
    SpeakerRole.MARKETING_INVESTOR: "Marketing Investor",
    SpeakerRole.RISK_INVESTOR: "Risk Investor",
    SpeakerRole.FOUNDER: "Founder (User)",
}
