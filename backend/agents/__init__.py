"""Multi-Agent Research Copilot — Phase XXXI.

Import the orchestrator and registry here so server.py only needs:
    from agents import orchestrator, REGISTRY
"""
from .base_agent import AgentTask, AgentOutput, AgentEvidence, BaseAgent
from .memory import SharedMemory
from .registry import REGISTRY
from . import orchestrator as orchestrator

__all__ = [
    "AgentTask", "AgentOutput", "AgentEvidence", "BaseAgent",
    "SharedMemory", "REGISTRY", "orchestrator",
]
