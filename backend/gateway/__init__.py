"""
Enterprise AI Gateway — public surface.

Import only what callers need:

    from gateway import get_gateway, GatewayRequest, GatewayResponse
    from gateway.prompt_registry import render_prompt
    from gateway.plugin_registry import plugin_registry
    from gateway.ai_memory import get_memory
    from gateway.schemas import GatewayRequest, GatewayResponse, ValidationResult
"""

from .gateway import AIGateway, get_gateway, reset_gateway
from .schemas import GatewayRequest, GatewayResponse, ValidationResult
from .prompt_registry import render_prompt, registry as prompt_registry
from .plugin_registry import plugin_registry
from .ai_memory import get_memory, AIMemory

__all__ = [
    "AIGateway",
    "get_gateway",
    "reset_gateway",
    "GatewayRequest",
    "GatewayResponse",
    "ValidationResult",
    "render_prompt",
    "prompt_registry",
    "plugin_registry",
    "get_memory",
    "AIMemory",
]
