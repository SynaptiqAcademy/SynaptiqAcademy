"""Synaptiq AI services — public API surface.

Primary entry points:
  call_llm()   — backward-compatible LLM utility used throughout the codebase
  get_engine() — direct access to the AIEngine for advanced callers
"""
from services.ai.engine.core import get_engine
from services.ai.engine.types import AIRequest, AIResponse, ExecutionLayer
from services.ai.llm import call_llm

__all__ = [
    "call_llm",
    "get_engine",
    "AIRequest",
    "AIResponse",
    "ExecutionLayer",
]
