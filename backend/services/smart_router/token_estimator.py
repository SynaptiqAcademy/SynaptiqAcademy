"""Token estimator — estimates input/output tokens and cost before execution."""
from __future__ import annotations

from services.smart_router.config import OUTPUT_TOKEN_ESTIMATES, PROVIDER_COSTS, SmartRouterConfig
from services.smart_router.profiles import get_profile
from services.smart_router.types import TokenEstimate


def _count_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))
    except Exception:
        return max(1, len(text) // 4)


class TokenEstimator:
    """Estimates cost before execution so the Budget Manager can approve/reject."""

    def __init__(self, config: SmartRouterConfig) -> None:
        self._config = config

    def estimate(
        self,
        feature: str,
        messages: list[dict],
        system_prompt: str,
        selected_provider: str,
        selected_model: str | None = None,
    ) -> TokenEstimate:
        # Count input tokens
        sys_tokens = _count_tokens(system_prompt) if system_prompt else 0
        msg_tokens = sum(
            _count_tokens(str(m.get("content", ""))) + 4  # 4 overhead per message
            for m in messages
        )
        input_tokens = sys_tokens + msg_tokens + 3  # message wrapping overhead

        # Estimate output tokens from profile
        profile = get_profile(feature)
        output_tokens = OUTPUT_TOKEN_ESTIMATES.get(feature, profile.expected_output_tokens)

        # Select cost model
        cost_key = selected_model or selected_provider
        cost_cfg = PROVIDER_COSTS.get(cost_key) or PROVIDER_COSTS.get(selected_provider)
        if cost_cfg is None:
            cost_cfg = PROVIDER_COSTS.get("anthropic")

        estimated_cost = cost_cfg.estimate(input_tokens, output_tokens) if cost_cfg else 0.0

        return TokenEstimate(
            input_tokens=input_tokens,
            context_tokens=sys_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=round(estimated_cost, 6),
            provider=selected_provider,
            model=selected_model or "",
        )

    def estimate_from_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        provider: str,
        model: str | None = None,
    ) -> float:
        """Quick cost calculation from token counts."""
        cost_key = model or provider
        cost_cfg = PROVIDER_COSTS.get(cost_key) or PROVIDER_COSTS.get(provider)
        if cost_cfg is None:
            return 0.0
        return cost_cfg.estimate(input_tokens, output_tokens)

    @staticmethod
    def count_message_tokens(messages: list[dict]) -> int:
        return sum(
            _count_tokens(str(m.get("content", ""))) + 4
            for m in messages
        ) + 3
