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


class SessionPhase(str, Enum):
    """The twelve stages of a Shark Tank AI session, in chronological
    order. `MARKET_RESEARCH` and `NEGOTIATION` were added in Release
    0.6; `ADVANCED_ANALYSIS` was added in Release 0.8 -- deterministic
    financial analysis runs after Internal Deliberation (the Sharks'
    final offers must exist first) and before Verification (so
    Verification can audit it, per Release 0.8 spec Part 20 -- see
    `docs/architecture.md` -> Advanced Financial Analysis for why this
    ordering, not the spec's own suggested "after Verification"
    placement, is what the actual data dependency requires)
    (`docs/state_machines.md`)."""

    IDLE = "idle"
    PROPOSAL_UPLOADED = "proposal_uploaded"
    VALIDATION = "validation"
    MARKET_RESEARCH = "market_research"
    QUESTION_ROUND = "question_round"
    INTERNAL_DELIBERATION = "internal_deliberation"
    ADVANCED_ANALYSIS = "advanced_analysis"
    VERIFICATION = "verification"
    CONSENSUS = "consensus"
    INVESTMENT_DECISION = "investment_decision"
    NEGOTIATION = "negotiation"
    SESSION_COMPLETE = "session_complete"


# Canonical left-to-right ordering used to render the progress stepper.
PHASE_ORDER: list[SessionPhase] = [
    SessionPhase.IDLE,
    SessionPhase.PROPOSAL_UPLOADED,
    SessionPhase.VALIDATION,
    SessionPhase.MARKET_RESEARCH,
    SessionPhase.QUESTION_ROUND,
    SessionPhase.INTERNAL_DELIBERATION,
    SessionPhase.ADVANCED_ANALYSIS,
    SessionPhase.VERIFICATION,
    SessionPhase.CONSENSUS,
    SessionPhase.INVESTMENT_DECISION,
    SessionPhase.NEGOTIATION,
    SessionPhase.SESSION_COMPLETE,
]

# Human-readable labels shown in the header stepper.
PHASE_LABELS: dict[SessionPhase, str] = {
    SessionPhase.IDLE: "Idle",
    SessionPhase.PROPOSAL_UPLOADED: "Proposal Uploaded",
    SessionPhase.VALIDATION: "Validation",
    SessionPhase.MARKET_RESEARCH: "Market Research",
    SessionPhase.QUESTION_ROUND: "Question Round",
    SessionPhase.INTERNAL_DELIBERATION: "Internal Deliberation",
    SessionPhase.ADVANCED_ANALYSIS: "Financial Analysis",
    SessionPhase.VERIFICATION: "Verification",
    SessionPhase.CONSENSUS: "Consensus",
    SessionPhase.INVESTMENT_DECISION: "Investment Decision",
    SessionPhase.NEGOTIATION: "Negotiation",
    SessionPhase.SESSION_COMPLETE: "Session Complete",
}

# Descriptive copy shown on the "Session Stage" card in the main panel.
# Purely display text — no logic decides when these are shown; the UI
# simply looks up the current phase.
PHASE_STAGE_MESSAGES: dict[SessionPhase, str] = {
    SessionPhase.IDLE: "Waiting for proposal.",
    SessionPhase.PROPOSAL_UPLOADED: "Proposal received. Ready to start the session.",
    SessionPhase.VALIDATION: "Validating the proposal.",
    SessionPhase.MARKET_RESEARCH: "Researching current market conditions and comparable businesses.",
    SessionPhase.QUESTION_ROUND: "The investment committee is questioning the founder.",
    SessionPhase.INTERNAL_DELIBERATION: "The committee is deliberating internally.",
    SessionPhase.ADVANCED_ANALYSIS: "Analyzing financial data and valuation.",
    SessionPhase.VERIFICATION: "Verifying the committee's deliberation.",
    SessionPhase.CONSENSUS: "The committee is reaching consensus.",
    SessionPhase.INVESTMENT_DECISION: "Delivering initial offers.",
    SessionPhase.NEGOTIATION: "Negotiating with interested Sharks.",
    SessionPhase.SESSION_COMPLETE: "Session complete.",
}


class LLMProvider(str, Enum):
    """Supported LLM backends, selectable from the sidebar.

    `ANTHROPIC` is the only provider with a real `BaseProvider`
    implementation (`providers/anthropic_provider.py`, Release 0.5).
    `GEMINI` and `OLLAMA` remain here because their sidebar
    configuration fields already existed before any provider was
    implemented (Release 0.3.x) and removing them wasn't necessary to
    ship Release 0.5 -- but `ui/sidebar.py` must not, and does not,
    imply that selecting either of them actually does anything yet.
    """

    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class SpeakerRole(str, Enum):
    """Every participant that can appear in the conversation history.

    As of Release 0.3.7, the investment committee is three Shark Agents
    distinguished by investment *philosophy* (Conservative, Growth,
    Balanced) rather than five distinguished by domain specialty. See
    `docs/agent_personas.md` for the philosophy each role represents.
    """

    MODERATOR = "moderator"
    CONSERVATIVE_VC = "conservative_vc"
    GROWTH_VC = "growth_vc"
    BALANCED_VC = "balanced_vc"
    FOUNDER = "founder"


# Human-readable labels shown next to each message in the conversation panel.
SPEAKER_LABELS: dict[SpeakerRole, str] = {
    SpeakerRole.MODERATOR: "Moderator",
    SpeakerRole.CONSERVATIVE_VC: "Conservative VC",
    SpeakerRole.GROWTH_VC: "Growth VC",
    SpeakerRole.BALANCED_VC: "Balanced VC",
    SpeakerRole.FOUNDER: "Founder (User)",
}
