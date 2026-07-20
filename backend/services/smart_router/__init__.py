"""Smart Execution Router — three-layer AI routing, budget management, and observability."""
from services.smart_router.engine import SmartExecutionRouter, get_smart_router, get_smart_router_async
from services.smart_router.types import ComplexityLevel, RouterSignal, RoutingDecision

__all__ = [
    "SmartExecutionRouter",
    "get_smart_router",
    "get_smart_router_async",
    "ComplexityLevel",
    "RouterSignal",
    "RoutingDecision",
]
