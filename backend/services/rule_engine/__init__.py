"""Synaptiq Rule Engine — deterministic, zero-LLM computation layer.

All operations execute in pure Python in milliseconds with no API calls.
"""
from .engine import RuleEngine, get_rule_engine
from . import telemetry

__all__ = ["RuleEngine", "get_rule_engine", "telemetry"]
