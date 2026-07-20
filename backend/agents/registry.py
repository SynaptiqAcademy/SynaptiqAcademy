"""Agent registry — singleton that maps agent_name → BaseAgent instance.

All specialized agents call `REGISTRY.register(agent_instance)` at import time.
The orchestrator looks up agents by name.
"""
from __future__ import annotations

from typing import Optional
from .base_agent import BaseAgent


class _AgentRegistry:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def all(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def names(self) -> list[str]:
        return list(self._agents.keys())

    def info(self) -> list[dict]:
        return [
            {
                "name":         a.name,
                "description":  a.description,
                "mission":      a.mission,
                "capabilities": a.capabilities,
            }
            for a in self._agents.values()
        ]


REGISTRY = _AgentRegistry()
