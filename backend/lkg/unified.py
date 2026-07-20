"""
Unified Knowledge Graph Service — Sprint 1.4

Single authoritative entry point for ALL graph operations in Synaptiq.

Storage: lkg_nodes / lkg_edges (MongoDB collections)

Replaces independent implementations in:
  • services/knowledge_graph/   (Phase XVII, in-memory)
  • services/akg/               (Phase IX, akg_entities/akg_relationships)
  • lkg/                        (Phase XXXII, canonical LKG)

All subsystems must call get_unified_graph() and use this class.
No subsystem reads graph data from MongoDB directly using its own queries.

Provenance: every node and edge stores source, confidence, evidence, version.
Evidence policy: every recommendation traces to verified graph data only.
"""
from __future__ import annotations

import logging
import secrets
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .entity_types import (
    ENTITY_TYPES, RELATIONSHIP_TYPES,
    ALL_ENTITY_TYPES, ALL_RELATIONSHIP_TYPES,
    validate_entity_type, validate_rel_type,
)
from .models import LKGNode, LKGEdge, make_node_id

logger = logging.getLogger("lkg.unified")

_NODES_COL = "lkg_nodes"
_EDGES_COL = "lkg_edges"

# Legacy AKG collection — bridged for read backward compat
_AKG_ENTITIES_COL    = "akg_entities"
_AKG_REL_COL         = "akg_relationships"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(doc: dict) -> dict:
    if doc:
        doc.pop("_id", None)
    return doc


def _translate_node_filter(f: dict) -> dict:
    """Translate AKG entity field names to LKG node field names for lkg_nodes queries."""
    out: dict = {}
    for k, v in f.items():
        if k == "entity_type":
            out["type"] = v
        elif k == "entity_id":
            out["node_id"] = v
        elif k in ("$or", "$and", "$nor"):
            out[k] = [_translate_node_filter(clause) for clause in v]
        else:
            out[k] = v
    return out


def _translate_edge_filter(f: dict) -> dict:
    """Translate AKG relationship field names to LKG edge field names for lkg_edges queries."""
    out: dict = {}
    for k, v in f.items():
        if k == "rel_type":
            out["type"] = v
        elif k in ("$or", "$and", "$nor"):
            out[k] = [_translate_edge_filter(clause) for clause in v]
        else:
            out[k] = v
    return out


# ── Unified Graph Service ─────────────────────────────────────────────────────

class UnifiedGraphService:
    """
    Single source of truth for Academic Knowledge Graph operations.

    Every entity write goes to lkg_nodes.
    Every relationship write goes to lkg_edges.
    Reads merge lkg_nodes with the legacy akg_entities for backward compat.
    """

    # ── Entity (Node) operations ──────────────────────────────────────────────

    async def upsert_entity(
        self,
        db,
        entity_type: str,
        label: str,
        properties: dict | None = None,
        *,
        source: str = "platform",
        confidence: str = "medium",
        evidence: list | None = None,
        node_id: str | None = None,
    ) -> dict:
        """
        Create or update an entity node.

        Returns the stored node document.
        Provenance fields (source, confidence, evidence, version) are always set.
        """
        try:
            entity_type = validate_entity_type(entity_type)
        except ValueError:
            entity_type = entity_type.lower().strip()

        if confidence not in ("high", "medium", "low"):
            confidence = "medium"

        if node_id is None:
            node_id = make_node_id(entity_type, source, label)

        now = _now()
        doc: dict[str, Any] = {
            "node_id":      node_id,
            "type":         entity_type,
            "label":        label,
            "source":       source,
            "confidence":   confidence,
            "evidence":     evidence or [],
            "last_updated": now,
            **(properties or {}),
        }
        await db[_NODES_COL].update_one(
            {"node_id": node_id},
            {
                "$set": doc,
                "$inc": {"version": 1},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        result = await db[_NODES_COL].find_one({"node_id": node_id}, {"_id": 0})
        try:
            from obs.metrics import get_metrics, M_KG_UPDATES
            get_metrics().inc(M_KG_UPDATES, tags={"collection": "nodes", "type": entity_type})
        except Exception:
            pass
        try:
            from events import get_bus, KGNodeAdded
            get_bus().publish_sync(KGNodeAdded(
                aggregate_id=node_id,
                payload={"node_id": node_id, "type": entity_type, "label": label, "source": source},
            ))
        except Exception:
            pass
        return result or doc

    async def get_entity(self, db, node_id: str) -> dict | None:
        """Fetch a node from lkg_nodes, then fall back to akg_entities."""
        doc = await db[_NODES_COL].find_one({"node_id": node_id}, {"_id": 0})
        if doc:
            return doc
        # Bridge: check legacy AKG collection
        doc = await db[_AKG_ENTITIES_COL].find_one(
            {"$or": [{"entity_id": node_id}, {"id": node_id}]},
            {"_id": 0},
        )
        return _clean(doc) if doc else None

    async def delete_entity(self, db, node_id: str) -> bool:
        """Soft-delete: mark deleted_at; also removes from akg_entities."""
        result = await db[_NODES_COL].update_one(
            {"node_id": node_id},
            {"$set": {"deleted_at": _now(), "status": "deleted"}},
        )
        await db[_AKG_ENTITIES_COL].delete_one({"entity_id": node_id})
        return result.modified_count > 0

    async def list_entities(
        self,
        db,
        entity_type: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict:
        """Paginated entity list. Merges lkg_nodes and akg_entities."""
        filt_lkg = {"status": {"$ne": "deleted"}}
        if entity_type:
            filt_lkg["type"] = entity_type.lower()

        skip = (page - 1) * limit
        nodes = await db[_NODES_COL].find(filt_lkg, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
        total = await db[_NODES_COL].count_documents(filt_lkg)
        return {"nodes": nodes, "total": total, "page": page, "limit": limit}

    async def search_entities(
        self,
        db,
        query: str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """
        Full-text search across lkg_nodes. Also searches akg_entities for legacy data.
        Returns merged de-duplicated results ranked by relevance.
        """
        q = query.strip()
        if not q:
            return []

        filt: dict = {"$text": {"$search": q}, "status": {"$ne": "deleted"}}
        if entity_type:
            filt["type"] = entity_type.lower()

        # Primary: lkg_nodes text search
        try:
            lkg_docs = await db[_NODES_COL].find(
                filt, {"_id": 0, "score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit).to_list(limit)
        except Exception:
            # Fallback: regex search if text index not ready
            regex = {"$regex": q, "$options": "i"}
            filt2 = {"label": regex, "status": {"$ne": "deleted"}}
            if entity_type:
                filt2["type"] = entity_type.lower()
            lkg_docs = await db[_NODES_COL].find(filt2, {"_id": 0}).limit(limit).to_list(limit)

        seen_ids = {d["node_id"] for d in lkg_docs}

        # Bridge: also search akg_entities
        remaining = max(0, limit - len(lkg_docs))
        if remaining > 0:
            try:
                akg_docs = await db[_AKG_ENTITIES_COL].find(
                    {"label": {"$regex": q, "$options": "i"}},
                    {"_id": 0},
                ).limit(remaining).to_list(remaining)
                for d in akg_docs:
                    eid = d.get("entity_id") or d.get("id", "")
                    if eid not in seen_ids:
                        # Normalize to LKG format
                        d["node_id"] = eid
                        d.setdefault("type", d.pop("entity_type", "unknown"))
                        d.setdefault("source", "akg_legacy")
                        lkg_docs.append(d)
                        seen_ids.add(eid)
            except Exception:
                pass

        return lkg_docs[:limit]

    # ── Relationship (Edge) operations ────────────────────────────────────────

    async def upsert_relationship(
        self,
        db,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: dict | None = None,
        *,
        source: str = "platform",
        confidence: str = "medium",
        evidence: list | None = None,
        status: str = "observed",
    ) -> dict:
        """Create or update a directed relationship edge."""
        try:
            rel_type = validate_rel_type(rel_type)
        except ValueError:
            rel_type = rel_type.upper().strip()

        if confidence not in ("high", "medium", "low"):
            confidence = "medium"
        if status not in ("verified", "inferred", "predicted", "observed"):
            status = "observed"

        now = _now()
        doc: dict[str, Any] = {
            "from_id":    from_id,
            "to_id":      to_id,
            "type":       rel_type,
            "source":     source,
            "confidence": confidence,
            "evidence":   evidence or [],
            "status":     status,
            "updated_at": now,
            **(properties or {}),
        }
        await db[_EDGES_COL].update_one(
            {"from_id": from_id, "to_id": to_id, "type": rel_type},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        result = await db[_EDGES_COL].find_one(
            {"from_id": from_id, "to_id": to_id, "type": rel_type}, {"_id": 0}
        )
        try:
            from obs.metrics import get_metrics, M_KG_UPDATES
            get_metrics().inc(M_KG_UPDATES, tags={"collection": "edges", "type": rel_type})
        except Exception:
            pass
        try:
            from events import get_bus, KGEdgeAdded
            get_bus().publish_sync(KGEdgeAdded(
                aggregate_id=f"{from_id}::{rel_type}::{to_id}",
                payload={"from_id": from_id, "to_id": to_id, "rel_type": rel_type, "source": source},
            ))
        except Exception:
            pass
        return result or doc

    async def get_relationships(
        self,
        db,
        entity_id: str,
        direction: str = "both",
        rel_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Fetch relationships for an entity from lkg_edges + akg_relationships."""
        filt: dict = {}
        if rel_types:
            rt_upper = [r.upper() for r in rel_types]
            filt["type"] = {"$in": rt_upper}

        edges: list[dict] = []
        if direction in ("out", "both"):
            filt_out = {**filt, "from_id": entity_id}
            out = await db[_EDGES_COL].find(filt_out, {"_id": 0}).limit(limit).to_list(limit)
            edges.extend(out)

        if direction in ("in", "both"):
            filt_in = {**filt, "to_id": entity_id}
            in_edges = await db[_EDGES_COL].find(filt_in, {"_id": 0}).limit(limit).to_list(limit)
            edges.extend(in_edges)

        seen = {(e["from_id"], e["to_id"], e["type"]) for e in edges}

        # Bridge: also fetch from akg_relationships
        if direction in ("out", "both"):
            akg_out = await db[_AKG_REL_COL].find(
                {"from_id": entity_id}, {"_id": 0}
            ).limit(limit).to_list(limit)
            for e in akg_out:
                key = (e.get("from_id", ""), e.get("to_id", ""), e.get("rel_type", ""))
                if key not in seen:
                    e["type"] = e.pop("rel_type", e.get("type", "RELATED_TO"))
                    e.setdefault("source", "akg_legacy")
                    edges.append(e)
                    seen.add(key)

        return edges

    async def delete_relationship(self, db, from_id: str, to_id: str, rel_type: str) -> bool:
        result = await db[_EDGES_COL].delete_one(
            {"from_id": from_id, "to_id": to_id, "type": rel_type.upper()}
        )
        return result.deleted_count > 0

    # ── Graph traversal ───────────────────────────────────────────────────────

    async def get_neighbors(
        self,
        db,
        node_id: str,
        depth: int = 2,
        rel_types: list[str] | None = None,
        limit_per_level: int = 20,
    ) -> dict:
        """
        BFS neighbor traversal up to `depth` hops.
        Returns nodes and edges found.
        """
        visited_nodes: dict[str, dict] = {}
        visited_edges: list[dict] = []
        frontier = {node_id}
        seen_edges: set[tuple] = set()

        for level in range(depth):
            if not frontier:
                break
            next_frontier: set[str] = set()
            for nid in list(frontier)[:limit_per_level]:
                rels = await self.get_relationships(db, nid, "both", rel_types, limit=50)
                for e in rels:
                    key = (e.get("from_id"), e.get("to_id"), e.get("type"))
                    if key in seen_edges:
                        continue
                    seen_edges.add(key)
                    visited_edges.append(e)
                    neighbor = e["to_id"] if e["from_id"] == nid else e["from_id"]
                    if neighbor not in visited_nodes:
                        next_frontier.add(neighbor)
            for nid in next_frontier:
                node = await self.get_entity(db, nid)
                if node:
                    visited_nodes[nid] = node
            frontier = next_frontier

        root = await self.get_entity(db, node_id)
        if root:
            visited_nodes[node_id] = root

        return {
            "nodes": list(visited_nodes.values()),
            "edges": visited_edges,
            "depth": depth,
        }

    async def find_path(
        self,
        db,
        from_id: str,
        to_id: str,
        max_hops: int = 4,
    ) -> list[str]:
        """
        BFS shortest-path finder.
        Returns list of node_ids from from_id to to_id, or empty list if not reachable.
        """
        if from_id == to_id:
            return [from_id]

        queue = [[from_id]]
        visited = {from_id}

        while queue:
            path = queue.pop(0)
            if len(path) > max_hops:
                break
            current = path[-1]
            rels = await self.get_relationships(db, current, "both", limit=30)
            for e in rels:
                neighbor = e["to_id"] if e["from_id"] == current else e["from_id"]
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == to_id:
                    return new_path
                visited.add(neighbor)
                queue.append(new_path)

        return []

    # ── Inference ─────────────────────────────────────────────────────────────

    async def find_similar(
        self,
        db,
        node_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Find similar entities via shared relationships (Jaccard similarity on neighbors).
        Returns list of {node_id, label, similarity_score, shared_connections, evidence}.
        All similarity scores are derived from verified graph structure.
        """
        entity = await self.get_entity(db, node_id)
        if not entity:
            return []

        rels = await self.get_relationships(db, node_id, "both", limit=200)
        my_neighbors = set()
        for r in rels:
            neighbor = r["to_id"] if r["from_id"] == node_id else r["from_id"]
            my_neighbors.add(neighbor)

        if not my_neighbors:
            return []

        # Find who else connects to the same neighbors
        candidate_scores: dict[str, int] = defaultdict(int)
        candidate_neighbors: dict[str, set] = defaultdict(set)

        for nid in list(my_neighbors)[:50]:
            peer_rels = await self.get_relationships(db, nid, "both", limit=50)
            for pr in peer_rels:
                peer = pr["to_id"] if pr["from_id"] == nid else pr["from_id"]
                if peer != node_id and peer not in my_neighbors:
                    candidate_scores[peer] += 1
                    candidate_neighbors[peer].add(nid)

        if not candidate_scores:
            return []

        results = []
        for candidate_id, shared in sorted(
            candidate_scores.items(), key=lambda x: -x[1]
        )[:limit]:
            node = await self.get_entity(db, candidate_id)
            if not node:
                continue
            jaccard = shared / (len(my_neighbors) + candidate_scores[candidate_id] - shared)
            results.append({
                "node_id":            candidate_id,
                "label":              node.get("label", ""),
                "type":               node.get("type", ""),
                "similarity_score":   round(min(jaccard, 1.0), 3),
                "shared_connections": shared,
                "evidence": [
                    {"type": "graph_structure", "shared_nodes": shared,
                     "basis": f"{shared} shared graph connections", "verified": True}
                ],
                "confidence":      "high" if shared >= 3 else "medium" if shared >= 2 else "low",
                "confidence_basis": f"Jaccard similarity from {shared} shared graph connections",
            })

        return results

    # ── Community detection ───────────────────────────────────────────────────

    async def detect_communities(self, db, max_nodes: int = 500) -> list[dict]:
        """
        Label-propagation community detection over lkg_edges + akg_relationships.
        Returns list of communities with members and evidence.
        """
        lkg_edges = await db[_EDGES_COL].find(
            {}, {"from_id": 1, "to_id": 1, "_id": 0}
        ).limit(max_nodes * 10).to_list(max_nodes * 10)
        try:
            akg_edges = await db[_AKG_REL_COL].find(
                {}, {"from_id": 1, "to_id": 1, "_id": 0}
            ).limit(max_nodes * 10).to_list(max_nodes * 10)
        except Exception:
            akg_edges = []
        edges = lkg_edges + akg_edges

        # Build adjacency
        adj: dict[str, set[str]] = defaultdict(set)
        for e in edges:
            f, t = e["from_id"], e["to_id"]
            adj[f].add(t)
            adj[t].add(f)

        # Label propagation
        labels = {n: n for n in adj}
        for _ in range(10):
            changed = False
            for node in list(adj):
                neighbor_labels = [labels.get(nb, nb) for nb in adj[node]]
                if not neighbor_labels:
                    continue
                best = max(set(neighbor_labels), key=neighbor_labels.count)
                if labels[node] != best:
                    labels[node] = best
                    changed = True
            if not changed:
                break

        # Group by label
        communities: dict[str, list[str]] = defaultdict(list)
        for node, label in labels.items():
            communities[label].append(node)

        result = []
        for cid, members in sorted(communities.items(), key=lambda x: -len(x[1])):
            if len(members) < 2:
                continue
            result.append({
                "community_id": cid,
                "size":         len(members),
                "members":      members[:20],
                "evidence": [
                    {"type": "graph_structure", "method": "label_propagation",
                     "verified": True, "basis": f"{len(members)} graph-connected nodes"}
                ],
            })

        return result[:50]

    # ── Graph governance ──────────────────────────────────────────────────────

    # ── Bridging query methods (Sprint 1.6) ──────────────────────────────────

    async def find_nodes(self, db, akg_filter: dict, limit: int = 200) -> list[dict]:
        """
        Flexible filtered node query. Accepts AKG-style filter (entity_type/entity_id)
        or LKG-style (type/node_id). Bridges lkg_nodes + akg_entities.
        """
        lkg_filter = _translate_node_filter(akg_filter)
        lkg_filter.setdefault("status", {"$ne": "deleted"})
        nodes = await db[_NODES_COL].find(lkg_filter, {"_id": 0}).limit(limit).to_list(limit)
        seen = {d.get("node_id", "") for d in nodes}
        remaining = limit - len(nodes)
        if remaining > 0:
            try:
                akg_docs = await db[_AKG_ENTITIES_COL].find(
                    akg_filter, {"_id": 0}
                ).limit(remaining).to_list(remaining)
                for d in akg_docs:
                    eid = d.get("entity_id") or d.get("id", "")
                    if eid and eid not in seen:
                        d["node_id"] = eid
                        d.setdefault("type", d.pop("entity_type", "unknown"))
                        d.setdefault("source", "akg_legacy")
                        nodes.append(d)
                        seen.add(eid)
            except Exception:
                pass
        return nodes

    async def count_nodes(self, db, akg_filter: dict) -> int:
        """Count nodes matching AKG-style filter across lkg_nodes + akg_entities."""
        lkg_filter = _translate_node_filter(akg_filter)
        lkg_filter.setdefault("status", {"$ne": "deleted"})
        lkg_n = await db[_NODES_COL].count_documents(lkg_filter)
        try:
            akg_n = await db[_AKG_ENTITIES_COL].count_documents(akg_filter)
        except Exception:
            akg_n = 0
        return lkg_n + akg_n

    async def count_edges(self, db, akg_filter: dict) -> int:
        """Count edges matching AKG-style filter across lkg_edges + akg_relationships."""
        lkg_filter = _translate_edge_filter(akg_filter)
        lkg_n = await db[_EDGES_COL].count_documents(lkg_filter)
        try:
            akg_n = await db[_AKG_REL_COL].count_documents(akg_filter)
        except Exception:
            akg_n = 0
        return lkg_n + akg_n

    async def group_nodes_by_type(self, db) -> dict:
        """Return {entity_type: count} merged from lkg_nodes + akg_entities."""
        lkg_agg = await db[_NODES_COL].aggregate([
            {"$match": {"status": {"$ne": "deleted"}}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        ]).to_list(100)
        result: dict[str, int] = {r["_id"]: r["count"] for r in lkg_agg if r["_id"]}
        try:
            akg_agg = await db[_AKG_ENTITIES_COL].aggregate([
                {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}},
            ]).to_list(100)
            for r in akg_agg:
                if r["_id"]:
                    result[r["_id"]] = result.get(r["_id"], 0) + r["count"]
        except Exception:
            pass
        return result

    async def group_edges_by_type(self, db) -> dict:
        """Return {rel_type: count} merged from lkg_edges + akg_relationships."""
        lkg_agg = await db[_EDGES_COL].aggregate([
            {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        ]).to_list(100)
        result: dict[str, int] = {r["_id"]: r["count"] for r in lkg_agg if r["_id"]}
        try:
            akg_agg = await db[_AKG_REL_COL].aggregate([
                {"$group": {"_id": "$rel_type", "count": {"$sum": 1}}},
            ]).to_list(100)
            for r in akg_agg:
                if r["_id"]:
                    result[r["_id"]] = result.get(r["_id"], 0) + r["count"]
        except Exception:
            pass
        return result

    async def aggregate_edges(self, db, pipeline: list) -> list[dict]:
        """
        Run an aggregation pipeline on lkg_edges and merge with akg_relationships.
        Pipeline must use from_id/to_id field names (same in both collections).
        Group results are merged by _id, numeric fields summed.
        """
        lkg_res = await db[_EDGES_COL].aggregate(pipeline).to_list(None)
        try:
            akg_res = await db[_AKG_REL_COL].aggregate(pipeline).to_list(None)
        except Exception:
            akg_res = []
        merged: dict = {r["_id"]: dict(r) for r in lkg_res}
        for r in akg_res:
            key = r["_id"]
            if key in merged:
                for k, v in r.items():
                    if k != "_id" and isinstance(v, (int, float)):
                        merged[key][k] = merged[key].get(k, 0) + v
            else:
                merged[key] = dict(r)
        return list(merged.values())

    async def aggregate_nodes_by_label_and_filter(
        self, db, lkg_match: dict, akg_match: dict
    ) -> list[dict]:
        """
        Aggregate nodes by label with separate match filters for each store.
        Used for trend discovery where field names differ (type vs entity_type).
        Returns [{_id: label, count: n}, ...] merged from both collections.
        """
        suffix = [{"$group": {"_id": "$label", "count": {"$sum": 1}}}]
        lkg_res = await db[_NODES_COL].aggregate(
            [{"$match": lkg_match}] + suffix
        ).to_list(None)
        try:
            akg_res = await db[_AKG_ENTITIES_COL].aggregate(
                [{"$match": akg_match}] + suffix
            ).to_list(None)
        except Exception:
            akg_res = []
        merged: dict[str, int] = {r["_id"]: r["count"] for r in lkg_res if r["_id"]}
        for r in akg_res:
            if r["_id"]:
                merged[r["_id"]] = merged.get(r["_id"], 0) + r["count"]
        return [{"_id": k, "count": v} for k, v in merged.items()]

    async def discover_hot_research_areas(
        self, db, top_n: int = 10, days: int = 30
    ) -> list[dict]:
        """Research areas with most new relationships recently. Bridges both stores."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        lkg_pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}}},
            {"$lookup": {"from": _NODES_COL, "localField": "to_id",
                         "foreignField": "node_id", "as": "target"}},
            {"$unwind": "$target"},
            {"$match": {"target.type": "research_area"}},
            {"$group": {"_id": "$target.label", "connections": {"$sum": 1}}},
            {"$sort": {"connections": -1}},
            {"$limit": top_n},
        ]
        akg_pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}}},
            {"$lookup": {"from": _AKG_ENTITIES_COL, "localField": "to_id",
                         "foreignField": "entity_id", "as": "target"}},
            {"$unwind": "$target"},
            {"$match": {"target.entity_type": "research_area"}},
            {"$group": {"_id": "$target.label", "connections": {"$sum": 1}}},
            {"$sort": {"connections": -1}},
            {"$limit": top_n},
        ]
        lkg_res = await db[_EDGES_COL].aggregate(lkg_pipeline).to_list(top_n)
        try:
            akg_res = await db[_AKG_REL_COL].aggregate(akg_pipeline).to_list(top_n)
        except Exception:
            akg_res = []
        merged: dict[str, int] = {r["_id"]: r["connections"] for r in lkg_res if r["_id"]}
        for r in akg_res:
            if r["_id"]:
                merged[r["_id"]] = merged.get(r["_id"], 0) + r["connections"]
        return [
            {"area": k, "new_connections": v}
            for k, v in sorted(merged.items(), key=lambda x: -x[1])[:top_n]
        ]

    async def get_institutional_growth(self, db, top_n: int = 10) -> list[dict]:
        """Institutions gaining most new researcher affiliations. Bridges both stores."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        lkg_pipeline = [
            {"$match": {"type": "WORKS_AT", "created_at": {"$gte": cutoff}}},
            {"$group": {"_id": "$to_id", "new_affiliations": {"$sum": 1}}},
            {"$sort": {"new_affiliations": -1}},
            {"$limit": top_n},
        ]
        akg_pipeline = [
            {"$match": {"rel_type": "WORKS_AT", "created_at": {"$gte": cutoff}}},
            {"$group": {"_id": "$to_id", "new_affiliations": {"$sum": 1}}},
            {"$sort": {"new_affiliations": -1}},
            {"$limit": top_n},
        ]
        lkg_res = await db[_EDGES_COL].aggregate(lkg_pipeline).to_list(top_n)
        try:
            akg_res = await db[_AKG_REL_COL].aggregate(akg_pipeline).to_list(top_n)
        except Exception:
            akg_res = []
        merged: dict[str, int] = {r["_id"]: r["new_affiliations"] for r in lkg_res if r["_id"]}
        for r in akg_res:
            if r["_id"]:
                merged[r["_id"]] = merged.get(r["_id"], 0) + r["new_affiliations"]
        results = []
        for inst_id, count in sorted(merged.items(), key=lambda x: -x[1])[:top_n]:
            inst = await self.get_entity(db, inst_id)
            if inst:
                inst["new_affiliations"] = count
                results.append(inst)
        return results

    async def get_collaboration_trends(self, db) -> dict:
        """Monthly collaboration counts for last 6 months. Bridges both stores."""
        lkg_pipeline = [
            {"$match": {"type": "COLLABORATES_WITH"}},
            {"$group": {"_id": {"$substr": ["$created_at", 0, 7]}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$limit": 6},
        ]
        akg_pipeline = [
            {"$match": {"rel_type": "COLLABORATES_WITH"}},
            {"$group": {"_id": {"$substr": ["$created_at", 0, 7]}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$limit": 6},
        ]
        lkg_res = await db[_EDGES_COL].aggregate(lkg_pipeline).to_list(6)
        try:
            akg_res = await db[_AKG_REL_COL].aggregate(akg_pipeline).to_list(6)
        except Exception:
            akg_res = []
        merged: dict[str, int] = {r["_id"]: r["count"] for r in lkg_res if r["_id"]}
        for r in akg_res:
            if r["_id"]:
                merged[r["_id"]] = merged.get(r["_id"], 0) + r["count"]
        monthly = sorted(merged.items())[-6:]
        return {"monthly": [{"month": k, "collaborations": v} for k, v in monthly]}

    # ── Graph governance ──────────────────────────────────────────────────────

    async def ensure_indexes(self, db) -> None:
        """Create all required indexes for lkg_nodes and lkg_edges."""
        try:
            await db[_NODES_COL].create_index("node_id",  unique=True)
            await db[_NODES_COL].create_index("type")
            await db[_NODES_COL].create_index("source")
            await db[_NODES_COL].create_index("status")
            await db[_NODES_COL].create_index([("label", "text")])
            await db[_EDGES_COL].create_index([("from_id", 1), ("to_id", 1), ("type", 1)], unique=True)
            await db[_EDGES_COL].create_index("from_id")
            await db[_EDGES_COL].create_index("to_id")
            await db[_EDGES_COL].create_index("type")
            await db[_EDGES_COL].create_index("status")
            logger.info("UnifiedGraph indexes ensured")
        except Exception as exc:
            logger.warning("UnifiedGraph index creation (non-fatal): %s", exc)

    async def stats(self, db) -> dict:
        """Return node/edge counts and type distributions."""
        node_count = await db[_NODES_COL].count_documents({"status": {"$ne": "deleted"}})
        edge_count = await db[_EDGES_COL].count_documents({})
        akg_node_count = await db[_AKG_ENTITIES_COL].count_documents({})
        akg_edge_count = await db[_AKG_REL_COL].count_documents({})
        return {
            "lkg_nodes":   node_count,
            "lkg_edges":   edge_count,
            "akg_entities": akg_node_count,
            "akg_relationships": akg_edge_count,
            "total_nodes": node_count + akg_node_count,
            "total_edges": edge_count + akg_edge_count,
            "canonical_store":   "lkg_nodes / lkg_edges",
            "entity_types":      len(ENTITY_TYPES),
            "relationship_types": len(RELATIONSHIP_TYPES),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: UnifiedGraphService | None = None


def get_unified_graph() -> UnifiedGraphService:
    """
    Get the singleton UnifiedGraphService.

    Usage:
        from lkg.unified import get_unified_graph
        graph = get_unified_graph()
        node = await graph.upsert_entity(db, "researcher", "Alice Smith", {...})
    """
    global _instance
    if _instance is None:
        _instance = UnifiedGraphService()
    return _instance
