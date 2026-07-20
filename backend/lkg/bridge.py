"""
Legacy AKG Bridge — Sprint 1.4

Read-only backward compatibility layer for data still living in
akg_entities / akg_relationships (Phase IX legacy collections).

All new writes go to lkg_nodes / lkg_edges via unified.py.
This module provides:
  1. normalize_akg_entity()   — converts an akg_entities doc → LKG node format
  2. normalize_akg_rel()      — converts an akg_relationships doc → LKG edge format
  3. migrate_akg_to_lkg()     — one-shot bulk migration (idempotent, skip-if-exists)
  4. AKGBridgeReader          — thin wrapper to search both stores and merge results

The bridge never writes to akg_entities; writes always go through unified.py.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("lkg.bridge")

_AKG_ENTITIES_COL    = "akg_entities"
_AKG_REL_COL         = "akg_relationships"
_LKG_NODES_COL       = "lkg_nodes"
_LKG_EDGES_COL       = "lkg_edges"


# ── Format normalizers ────────────────────────────────────────────────────────

def normalize_akg_entity(doc: dict) -> dict:
    """
    Convert an akg_entities document to the canonical lkg_nodes format.

    akg_entities schema:
      entity_id   → node_id
      entity_type → type
      label       → label
      properties  → merged into root
      source      → source (default "akg_legacy")
    """
    d = {k: v for k, v in doc.items() if k != "_id"}
    return {
        "node_id":      d.get("entity_id") or d.get("id", ""),
        "type":         d.get("entity_type") or d.get("type", "unknown"),
        "label":        d.get("label", ""),
        "source":       d.get("source", "akg_legacy"),
        "confidence":   d.get("confidence", "medium"),
        "evidence":     d.get("evidence", []),
        "last_updated": d.get("updated_at") or d.get("last_updated") or datetime.now(timezone.utc).isoformat(),
        "version":      d.get("version", 1),
        "_bridge_source": "akg_entities",
        **{k: v for k, v in (d.get("properties") or {}).items()},
    }


def normalize_akg_rel(doc: dict) -> dict:
    """
    Convert an akg_relationships document to the canonical lkg_edges format.

    akg_relationships schema:
      from_id   → from_id
      to_id     → to_id
      rel_type  → type
    """
    d = {k: v for k, v in doc.items() if k != "_id"}
    return {
        "from_id":    d.get("from_id", ""),
        "to_id":      d.get("to_id", ""),
        "type":       (d.get("rel_type") or d.get("type", "RELATED_TO")).upper(),
        "source":     d.get("source", "akg_legacy"),
        "confidence": d.get("confidence", "medium"),
        "evidence":   d.get("evidence", []),
        "status":     d.get("status", "observed"),
        "updated_at": d.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        "_bridge_source": "akg_relationships",
    }


# ── Bulk migration utility ────────────────────────────────────────────────────

async def migrate_akg_to_lkg(db, batch_size: int = 500) -> dict:
    """
    One-shot idempotent migration: copy akg_entities → lkg_nodes
    and akg_relationships → lkg_edges.

    Already-migrated documents are skipped (upsert by node_id / (from_id, to_id, type)).
    Safe to run multiple times.

    Returns migration summary.
    """
    nodes_written = 0
    nodes_skipped = 0
    edges_written = 0
    edges_skipped = 0
    errors = 0

    now = datetime.now(timezone.utc).isoformat()

    # ── Entities ──────────────────────────────────────────────────────────────
    cursor = db[_AKG_ENTITIES_COL].find({})
    batch: list[dict] = []

    async for raw in cursor:
        doc = normalize_akg_entity(raw)
        if not doc.get("node_id"):
            errors += 1
            continue
        batch.append(doc)
        if len(batch) >= batch_size:
            written, skipped, errs = await _flush_nodes(db, batch, now)
            nodes_written += written
            nodes_skipped += skipped
            errors += errs
            batch = []

    if batch:
        written, skipped, errs = await _flush_nodes(db, batch, now)
        nodes_written += written
        nodes_skipped += skipped
        errors += errs

    # ── Relationships ─────────────────────────────────────────────────────────
    cursor = db[_AKG_REL_COL].find({})
    batch = []

    async for raw in cursor:
        doc = normalize_akg_rel(raw)
        if not (doc.get("from_id") and doc.get("to_id")):
            errors += 1
            continue
        batch.append(doc)
        if len(batch) >= batch_size:
            written, skipped, errs = await _flush_edges(db, batch, now)
            edges_written += written
            edges_skipped += skipped
            errors += errs
            batch = []

    if batch:
        written, skipped, errs = await _flush_edges(db, batch, now)
        edges_written += written
        edges_skipped += skipped
        errors += errs

    logger.info(
        "AKG→LKG migration: %d nodes written, %d skipped, %d edges written, %d skipped, %d errors",
        nodes_written, nodes_skipped, edges_written, edges_skipped, errors,
    )
    return {
        "nodes_written":  nodes_written,
        "nodes_skipped":  nodes_skipped,
        "edges_written":  edges_written,
        "edges_skipped":  edges_skipped,
        "errors":         errors,
        "migrated_at":    now,
    }


async def _flush_nodes(db, batch: list[dict], now: str) -> tuple[int, int, int]:
    written = skipped = errors = 0
    for doc in batch:
        try:
            result = await db[_LKG_NODES_COL].update_one(
                {"node_id": doc["node_id"]},
                {
                    "$setOnInsert": {**doc, "created_at": now},
                },
                upsert=True,
            )
            if result.upserted_id:
                written += 1
            else:
                skipped += 1
        except Exception as exc:
            logger.debug("Node migration error %s: %s", doc.get("node_id"), exc)
            errors += 1
    return written, skipped, errors


async def _flush_edges(db, batch: list[dict], now: str) -> tuple[int, int, int]:
    written = skipped = errors = 0
    for doc in batch:
        try:
            result = await db[_LKG_EDGES_COL].update_one(
                {
                    "from_id": doc["from_id"],
                    "to_id":   doc["to_id"],
                    "type":    doc["type"],
                },
                {"$setOnInsert": {**doc, "created_at": now}},
                upsert=True,
            )
            if result.upserted_id:
                written += 1
            else:
                skipped += 1
        except Exception as exc:
            logger.debug("Edge migration error (%s→%s): %s", doc.get("from_id"), doc.get("to_id"), exc)
            errors += 1
    return written, skipped, errors


# ── AKGBridgeReader ───────────────────────────────────────────────────────────

class AKGBridgeReader:
    """
    Thin read wrapper used by the akg/ routers for backward compat.

    Routes reads through unified.py while the legacy akg_entities collection
    still exists. Once migration is complete and akg_entities is empty,
    this becomes a thin pass-through.
    """

    async def get_entity(self, db, entity_id: str) -> dict | None:
        from .unified import get_unified_graph
        return await get_unified_graph().get_entity(db, entity_id)

    async def search_entities(
        self, db, query: str, entity_type: str | None = None, limit: int = 20
    ) -> list[dict]:
        from .unified import get_unified_graph
        return await get_unified_graph().search_entities(db, query, entity_type, limit)

    async def get_relationships(
        self, db, entity_id: str, direction: str = "both",
        rel_types: list[str] | None = None, limit: int = 100,
    ) -> list[dict]:
        from .unified import get_unified_graph
        return await get_unified_graph().get_relationships(db, entity_id, direction, rel_types, limit)

    async def get_neighbors(
        self, db, entity_id: str, depth: int = 2,
        rel_types: list[str] | None = None,
    ) -> dict:
        from .unified import get_unified_graph
        return await get_unified_graph().get_neighbors(db, entity_id, depth, rel_types)


_bridge_reader: AKGBridgeReader | None = None


def get_bridge_reader() -> AKGBridgeReader:
    global _bridge_reader
    if _bridge_reader is None:
        _bridge_reader = AKGBridgeReader()
    return _bridge_reader
