"""
Smoke tests verifying the full project structure imports correctly and
that the app can be constructed without errors, even though no agent
logic has been implemented yet.
"""

from __future__ import annotations

import importlib


def test_package_imports():
    """Every top-level package should import without error."""
    packages = [
        "agents",
        "orchestrator",
        "providers",
        "memory",
        "models",
        "prompts",
        "ui",
        "config",
        "utils",
    ]
    for package_name in packages:
        module = importlib.import_module(package_name)
        assert module is not None


def test_models_schemas_import():
    from models.schemas import DealStatus, NegotiationSession, Offer, Pitch, SharkPersona

    assert Pitch is not None
    assert SharkPersona is not None
    assert Offer is not None
    assert NegotiationSession is not None
    assert DealStatus.PENDING == "pending"


def test_orchestrator_constructs_without_agents():
    from orchestrator.orchestrator import SharkTankOrchestrator

    orchestrator = SharkTankOrchestrator()
    assert orchestrator.agents == []


def test_prompt_loader_reads_placeholder_file():
    from prompts.loader import load_prompt

    content = load_prompt("shark_persona_system")
    assert "PLACEHOLDER" in content
