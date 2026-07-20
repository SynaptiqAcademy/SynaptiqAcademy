"""Hybrid Execution Router.

Decides which execution layer (Rule / Local / Cloud) should handle a given
AIRequest based on feature metadata and current engine configuration.
No network calls are made here — routing is pure logic over config + feature flags.

Decision priority:
  1. Explicit request.provider override → respect it directly.
  2. Feature.preferred_layer == RULE and rule layer enabled → RULE.
  3. Feature.preferred_layer != CLOUD and local layer enabled and
     feature does not require reasoning → LOCAL.
  4. Default → CLOUD.
"""
from __future__ import annotations

import logging

from services.ai.engine.config import AIEngineConfig
from services.ai.engine.registry import FeatureMeta, get_feature_meta
from services.ai.engine.types import AIRequest, ExecutionLayer

logger = logging.getLogger("synaptiq.ai.engine.router")


class HybridExecutionRouter:
    """Stateless router — safe to call concurrently."""

    def route(self, request: AIRequest, config: AIEngineConfig) -> ExecutionLayer:
        """Return the most appropriate layer for this request."""
        meta = get_feature_meta(request.feature)

        if request.provider == "local":
            return ExecutionLayer.LOCAL

        if request.provider == "mock":
            return ExecutionLayer.CLOUD  # mock is a cloud provider in our registry

        if request.provider and request.provider not in ("local", "mock"):
            return ExecutionLayer.CLOUD

        if meta.preferred_layer == ExecutionLayer.RULE and config.enable_rule_layer:
            logger.debug("router: feature=%s → RULE", request.feature)
            return ExecutionLayer.RULE

        if (
            config.enable_local_layer
            and not meta.requires_reasoning
            and meta.preferred_layer in (ExecutionLayer.LOCAL, ExecutionLayer.CLOUD)
        ):
            logger.debug("router: feature=%s → LOCAL (local enabled, no reasoning required)", request.feature)
            return ExecutionLayer.LOCAL

        logger.debug("router: feature=%s → CLOUD", request.feature)
        return ExecutionLayer.CLOUD

    def route_fallback(
        self,
        failed_layer: ExecutionLayer,
        request: AIRequest,
        config: AIEngineConfig,
    ) -> ExecutionLayer | None:
        """Return the next layer to try after failed_layer failed, or None."""
        meta = get_feature_meta(request.feature)

        for candidate in meta.fallback_layers:
            if candidate == failed_layer:
                continue
            if candidate == ExecutionLayer.LOCAL and not config.enable_local_layer:
                continue
            if candidate == ExecutionLayer.RULE and not config.enable_rule_layer:
                continue
            logger.debug(
                "router: fallback feature=%s failed_layer=%s → %s",
                request.feature, failed_layer.value, candidate.value,
            )
            return candidate

        return None
