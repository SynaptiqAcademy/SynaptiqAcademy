"""Living Academic Knowledge Graph — Phase XXXII + Sprint 1.4 consolidation.

Sprint 1.4: Single source of truth for ALL graph operations.
  - lkg.unified.get_unified_graph()  — canonical write/read service
  - lkg.bridge.get_bridge_reader()   — backward-compat read from akg_entities
  - lkg.bridge.migrate_akg_to_lkg() — one-shot idempotent migration

Original Phase XXXII modules remain unchanged; they work through the unified service.
Backward compatibility: all /api/akg/* routes remain unchanged.
New routes: /api/lkg/*
New collections: lkg_nodes, lkg_edges, lkg_jobs
"""
from . import graph_store, models, reasoning, analytics, timeline, search, insights, discovery
from .entity_types import (
    ENTITY_TYPES, RELATIONSHIP_TYPES,
    ALL_ENTITY_TYPES, ALL_RELATIONSHIP_TYPES,
    NODE_TYPES, EDGE_TYPES,
    validate_entity_type, validate_rel_type,
)
from .unified import UnifiedGraphService, get_unified_graph
from .bridge import AKGBridgeReader, get_bridge_reader, migrate_akg_to_lkg

__all__ = [
    # Phase XXXII original modules
    "graph_store", "models", "reasoning", "analytics",
    "timeline", "search", "insights", "discovery",
    # Sprint 1.4 unified API
    "UnifiedGraphService", "get_unified_graph",
    "AKGBridgeReader", "get_bridge_reader", "migrate_akg_to_lkg",
    # Type registry
    "ENTITY_TYPES", "RELATIONSHIP_TYPES",
    "ALL_ENTITY_TYPES", "ALL_RELATIONSHIP_TYPES",
    "NODE_TYPES", "EDGE_TYPES",
    "validate_entity_type", "validate_rel_type",
]
