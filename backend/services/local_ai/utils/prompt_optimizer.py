"""Prompt optimization — compress, deduplicate, and trim prompts before local inference."""
from __future__ import annotations

import re

from services.local_ai.utils.token_estimator import (
    estimate_tokens,
    truncation_budget,
)


def compress_system_prompt(system: str) -> str:
    """Remove redundant whitespace, repeated blank lines, and trailing spaces."""
    text = re.sub(r"\r\n?", "\n", system)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    # Deduplicate adjacent identical lines
    deduped: list[str] = []
    for line in lines:
        if deduped and line == deduped[-1]:
            continue
        deduped.append(line)
    return "\n".join(deduped).strip()


def deduplicate_instructions(system: str) -> str:
    """Remove duplicate sentences/instructions from system prompt."""
    sentences = re.split(r"(?<=[.!?])\s+", system)
    seen: set[str] = set()
    unique: list[str] = []
    for s in sentences:
        key = re.sub(r"\s+", " ", s.strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return " ".join(unique)


def trim_messages_to_budget(
    messages: list[dict],
    budget_tokens: int,
    model_family: str = "other",
    preserve_last_n: int = 2,
) -> list[dict]:
    """Trim oldest messages (excluding last `preserve_last_n`) to fit budget."""
    if not messages:
        return messages

    total = sum(estimate_tokens(m.get("content", ""), model_family) + 4 for m in messages)
    if total <= budget_tokens:
        return messages

    # Keep the most recent messages; trim from the front
    protected = messages[-preserve_last_n:] if preserve_last_n else []
    trimmable = messages[:-preserve_last_n] if preserve_last_n else messages

    while trimmable and total > budget_tokens:
        removed = trimmable.pop(0)
        total -= estimate_tokens(removed.get("content", ""), model_family) + 4

    return trimmable + protected


def optimize_prompt(
    system: str,
    messages: list[dict],
    max_context_tokens: int,
    reserved_output_tokens: int = 512,
    model_family: str = "other",
) -> tuple[str, list[dict]]:
    """Full optimization pipeline: compress → deduplicate → trim.

    Returns (optimized_system, trimmed_messages).
    """
    opt_system = compress_system_prompt(system)
    opt_system = deduplicate_instructions(opt_system)

    budget = truncation_budget(
        max_context_tokens, opt_system, reserved_output_tokens, model_family
    )
    opt_messages = trim_messages_to_budget(messages, budget, model_family)

    return opt_system, opt_messages


def build_academic_system_prompt(task: str, language: str = "English") -> str:
    """Reusable system prompt for academic writing tasks."""
    return (
        f"You are an expert academic writing assistant. "
        f"Respond in {language}. Be concise, precise, and scholarly. "
        f"Task: {task}"
    )
