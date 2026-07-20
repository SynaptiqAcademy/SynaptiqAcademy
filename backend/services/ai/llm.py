"""Backward-compatible LLM utility — routes through the Enterprise AI Gateway.

All existing callers use:
    from services.ai.llm import call_llm
    text = await call_llm(system=..., user_msg=..., max_tokens=...)

The signature is preserved exactly. Every call now transparently flows through
the full gateway pipeline: context building, policy enforcement, prompt registry,
AIEngine routing (RAG, academic enrichment, provider fallback), evidence
validation, cost tracking, observability, and AI memory.

No caller changes are required. Callers may optionally supply `user_id`,
`mission_id`, and `db` to enable cost attribution and memory persistence.
"""
from __future__ import annotations


async def call_llm(
    *,
    system: str = "",
    user_msg: str = "",
    provider: str | None = None,
    model: str | None = None,
    messages: list[dict] | None = None,
    max_tokens: int = 2048,
    feature: str | None = None,
    user_id: str | None = None,
    mission_id: str | None = None,
    db=None,
    prompt_id: str | None = None,
    variables: dict | None = None,
) -> str:
    """Single- or multi-turn LLM call; returns the assistant text.

    Preserved public interface:
      system    — system prompt text (omit when using prompt_id)
      user_msg  — single-turn user message (ignored when `messages` is provided)
      provider  — force a specific provider (optional)
      model     — force a specific model (optional)
      messages  — list of {role, content} dicts for multi-turn; takes priority
      max_tokens — max output tokens
      feature   — feature_id for routing, cost attribution, and logging.
                  Defaults to prompt_id if provided, else 'general'.

    Optional params:
      user_id    — for conversation memory and cost attribution
      mission_id — for ARA mission cost tracking ($inc used_credits)
      db         — MongoDB database handle; needed for cost and observability
      prompt_id  — versioned prompt from the PromptRegistry; if provided,
                   the gateway renders system+user from the registry entry
      variables  — substitution variables for prompt_id templates
    """
    from gateway.gateway import get_gateway
    from gateway.schemas import GatewayRequest

    request = GatewayRequest(
        system=system,
        user_message=user_msg or "",
        messages=messages,
        feature=feature or prompt_id or "general",
        provider=provider,
        model=model,
        max_tokens=max_tokens,
        user_id=user_id,
        mission_id=mission_id,
        prompt_id=prompt_id,
        variables=variables or {},
    )
    response = await get_gateway().execute(request, db=db)
    return response.response
