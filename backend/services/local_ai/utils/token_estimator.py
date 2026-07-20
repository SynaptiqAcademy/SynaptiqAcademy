"""Token estimation utilities — no tokenizer dependency."""
from __future__ import annotations

# Average chars-per-token per model family (empirically derived)
_CHARS_PER_TOKEN: dict[str, float] = {
    "llama": 3.8,
    "qwen": 3.5,
    "mistral": 3.8,
    "gemma": 3.9,
    "deepseek": 3.6,
    "phi": 4.0,
    "other": 4.0,
}

_DEFAULT_CHARS_PER_TOKEN = 4.0


def estimate_tokens(text: str, model_family: str = "other") -> int:
    """Estimate token count from character count."""
    cpt = _CHARS_PER_TOKEN.get(model_family, _DEFAULT_CHARS_PER_TOKEN)
    return max(1, round(len(text) / cpt))


def estimate_messages_tokens(messages: list[dict], model_family: str = "other") -> int:
    """Estimate tokens across a list of messages, including role overhead."""
    total = 0
    for m in messages:
        content = m.get("content") or ""
        total += estimate_tokens(content, model_family)
        total += 4  # role + formatting overhead per message
    return total


def estimate_request_tokens(
    system: str,
    messages: list[dict],
    model_family: str = "other",
) -> int:
    return (
        estimate_tokens(system, model_family)
        + estimate_messages_tokens(messages, model_family)
        + 2  # request framing
    )


def fits_context_window(
    system: str,
    messages: list[dict],
    max_context_tokens: int,
    reserved_output_tokens: int = 512,
    model_family: str = "other",
) -> bool:
    input_estimate = estimate_request_tokens(system, messages, model_family)
    return (input_estimate + reserved_output_tokens) <= max_context_tokens


def truncation_budget(
    max_context_tokens: int,
    system: str,
    reserved_output_tokens: int = 512,
    model_family: str = "other",
) -> int:
    """How many message tokens remain after accounting for system + output."""
    system_tokens = estimate_tokens(system, model_family)
    return max(0, max_context_tokens - system_tokens - reserved_output_tokens)
