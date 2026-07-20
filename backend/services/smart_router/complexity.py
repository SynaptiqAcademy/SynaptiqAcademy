"""ComplexityAnalyzer — classifies every AI request into 5 complexity levels.

Inputs evaluated:
  1. Feature base complexity (from FeatureProfile)
  2. Total input context tokens
  3. Conversational depth (message count)
  4. Keyword signals in the user message
  5. Presence of uploaded document context (RAG tokens in system prompt)
"""
from __future__ import annotations

import re

from services.smart_router.profiles import FeatureProfile, get_profile
from services.smart_router.types import ComplexityLevel

# Keywords that signal reasoning-intensive requests — each bumps complexity by 1
_REASONING_KEYWORDS = frozenset({
    "analyze", "analyse", "synthesize", "synthesise", "compare", "contrast",
    "evaluate", "critically", "hypothesis", "methodology", "systematic",
    "meta-analysis", "meta analysis", "theoretical framework", "literature gap",
    "research design", "statistical significance", "correlation", "causation",
    "interpret", "discuss the implications", "research contribution",
})

# Keywords that signal simple / deterministic tasks — each reduces complexity by 1
_SIMPLE_KEYWORDS = frozenset({
    "fix spelling", "correct grammar", "translate", "summarize", "bullet point",
    "list the", "convert to", "reformat", "simplify", "shorter",
})

_WORD_RE = re.compile(r"\b\w+\b")


def _count_tokens(text: str) -> int:
    """Fast token estimation without tokenizer dependency."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))
    except Exception:
        return max(1, len(text) // 4)


def _keyword_delta(user_text: str) -> int:
    """Returns +1 if reasoning keywords found, -1 if simple keywords, 0 otherwise."""
    lower = user_text.lower()
    has_reasoning = any(kw in lower for kw in _REASONING_KEYWORDS)
    has_simple = any(kw in lower for kw in _SIMPLE_KEYWORDS)
    if has_reasoning and not has_simple:
        return 1
    if has_simple and not has_reasoning:
        return -1
    return 0


class ComplexityAnalyzer:
    """Stateless complexity classifier."""

    def __init__(
        self,
        large_context_tokens: int = 2000,
        very_large_context_tokens: int = 6000,
        deep_message_threshold: int = 5,
    ) -> None:
        self._large_ctx = large_context_tokens
        self._very_large_ctx = very_large_context_tokens
        self._deep_msg = deep_message_threshold

    def analyze(
        self,
        feature: str,
        messages: list[dict],
        system_prompt: str = "",
    ) -> ComplexityLevel:
        """Return the classified complexity level for this request."""
        profile = get_profile(feature)
        base = profile.base_complexity.value

        # Factor 1: system prompt token count (includes RAG context)
        system_tokens = _count_tokens(system_prompt) if system_prompt else 0

        # Factor 2: all messages token count
        msg_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        msg_tokens = _count_tokens(msg_text)

        total_tokens = system_tokens + msg_tokens

        ctx_delta = 0
        if total_tokens > self._very_large_ctx:
            ctx_delta = 2
        elif total_tokens > self._large_ctx:
            ctx_delta = 1

        # Factor 3: conversational depth
        depth_delta = 1 if len(messages) > self._deep_msg else 0

        # Factor 4: keyword signals in latest user message
        latest_user = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        kw_delta = _keyword_delta(latest_user)

        raw = base + ctx_delta + depth_delta + kw_delta
        clamped = max(ComplexityLevel.VERY_LOW.value, min(ComplexityLevel.CRITICAL.value, raw))
        return ComplexityLevel(clamped)

    def explain(
        self,
        feature: str,
        messages: list[dict],
        system_prompt: str = "",
    ) -> dict:
        """Return a breakdown of the complexity decision — for admin/debug."""
        profile = get_profile(feature)
        base = profile.base_complexity.value

        system_tokens = _count_tokens(system_prompt) if system_prompt else 0
        msg_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        msg_tokens = _count_tokens(msg_text)
        total_tokens = system_tokens + msg_tokens

        ctx_delta = 0
        if total_tokens > self._very_large_ctx:
            ctx_delta = 2
        elif total_tokens > self._large_ctx:
            ctx_delta = 1

        depth_delta = 1 if len(messages) > self._deep_msg else 0

        latest_user = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        kw_delta = _keyword_delta(latest_user)

        raw = base + ctx_delta + depth_delta + kw_delta
        clamped = max(1, min(5, raw))
        return {
            "feature": feature,
            "base_complexity": ComplexityLevel(base).name,
            "total_tokens": total_tokens,
            "context_delta": ctx_delta,
            "depth_delta": depth_delta,
            "keyword_delta": kw_delta,
            "raw_score": raw,
            "final_complexity": ComplexityLevel(clamped).name,
        }
