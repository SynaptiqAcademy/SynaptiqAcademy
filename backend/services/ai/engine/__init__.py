"""AI Engine package — exports the public API."""
from services.ai.engine.config import AIEngineConfig, ProviderConfig, load_config, reload_config
from services.ai.engine.core import AIEngine, get_engine, reset_engine
from services.ai.engine.registry import FeatureMeta, get_all_feature_ids, get_feature_meta, list_features
from services.ai.engine.router import HybridExecutionRouter
from services.ai.engine.types import (
    AIRequest,
    AIResponse,
    AISystemHealth,
    ExecutionLayer,
    ProviderHealth,
    ProviderName,
)

__all__ = [
    "AIEngine",
    "get_engine",
    "reset_engine",
    "AIRequest",
    "AIResponse",
    "AISystemHealth",
    "ExecutionLayer",
    "ProviderHealth",
    "ProviderName",
    "FeatureMeta",
    "get_feature_meta",
    "list_features",
    "get_all_feature_ids",
    "AIEngineConfig",
    "ProviderConfig",
    "load_config",
    "reload_config",
    "HybridExecutionRouter",
]
