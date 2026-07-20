"""AI provider package — exports all provider classes and the registry builder."""
from __future__ import annotations

from services.ai.providers.base import AIProvider
from services.ai.providers.mock_provider import MockProvider

__all__ = [
    "AIProvider",
    "MockProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "LocalProvider",
    "build_provider_registry",
]


def build_provider_registry(
    config: "AIEngineConfig",  # type: ignore[name-defined]
) -> dict[str, AIProvider]:
    """Instantiate and return every provider that is configured and importable.

    MockProvider is always registered and acts as the unconditional last-resort
    fallback regardless of API key availability.
    """
    from services.ai.engine.config import AIEngineConfig  # noqa: F401

    registry: dict[str, AIProvider] = {
        "mock": MockProvider(config.providers.get("mock")),
    }

    anthropic_cfg = config.providers.get("anthropic")
    if anthropic_cfg and anthropic_cfg.enabled:
        try:
            import anthropic  # noqa: F401
            from services.ai.providers.anthropic_provider import AnthropicProvider
            registry["anthropic"] = AnthropicProvider(anthropic_cfg)
        except ImportError:
            import logging
            logging.getLogger("synaptiq.ai.providers").warning(
                "anthropic package not installed — AnthropicProvider unavailable"
            )

    openai_cfg = config.providers.get("openai")
    if openai_cfg and openai_cfg.enabled:
        try:
            import openai  # noqa: F401
            from services.ai.providers.openai_provider import OpenAIProvider
            registry["openai"] = OpenAIProvider(openai_cfg)
        except ImportError:
            import logging
            logging.getLogger("synaptiq.ai.providers").warning(
                "openai package not installed — OpenAIProvider unavailable"
            )

    local_cfg = config.providers.get("local")
    if local_cfg and local_cfg.enabled:
        from services.ai.providers.local_provider import LocalProvider
        registry["local"] = LocalProvider(local_cfg)

    return registry


try:
    from services.ai.providers.anthropic_provider import AnthropicProvider
except ImportError:
    pass  # optional dependency

try:
    from services.ai.providers.openai_provider import OpenAIProvider
except ImportError:
    pass  # optional dependency

try:
    from services.ai.providers.local_provider import LocalProvider
except ImportError:
    pass  # optional dependency
