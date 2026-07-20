"""Academic Knowledge Graph — Core in-memory graph store (Phase XVII).

Thread-safe adjacency-list graph supporting millions of nodes via dict-based storage.
Supports incremental updates and indexed lookups by node type and relationship type.
"""
from __future__ import annotations

import threading
import uuid

from .models import Edge, Node, NodeType, RelType


class AcademicKnowledgeGraph:
    """
    Thread-safe in-memory Academic Knowledge Graph.

    Adjacency lists give O(1) neighbor lookup.
    Type/relation indexes give O(1) filtered queries.
    """

    def __init__(self) -> None:
        self._nodes:  dict[str, Node]       = {}
        self._edges:  dict[str, Edge]       = {}
        # node_id → list[edge_id] (outgoing)
        self._out:    dict[str, list[str]]  = {}
        # node_id → list[edge_id] (incoming)
        self._in:     dict[str, list[str]]  = {}
        # NodeType.value → set[node_id]
        self._type_idx: dict[str, set[str]] = {}
        # RelType.value → list[edge_id]
        self._rel_idx:  dict[str, list[str]]= {}
        # (node_type.value, label.lower()) → node_id  (deduplication)
        self._label_idx: dict[tuple, str]   = {}
        self._lock = threading.Lock()

    # ── Node operations ───────────────────────────────────────────────────────

    def add_node(
        self,
        node_id:    str,
        node_type:  NodeType | str,
        label:      str,
        properties: dict | None = None,
        weight:     float = 1.0,
    ) -> Node:
        nt = NodeType(node_type) if isinstance(node_type, str) else node_type
        with self._lock:
            if node_id in self._nodes:
                # Update properties only
                existing = self._nodes[node_id]
                if properties:
                    existing.properties.update(properties)
                return existing
            node = Node(node_id=node_id, node_type=nt, label=label,
                        properties=properties or {}, weight=weight)
            self._nodes[node_id] = node
            self._out[node_id] = []
            self._in[node_id]  = []
            self._type_idx.setdefault(nt.value, set()).add(node_id)
            self._label_idx[(nt.value, label.lower())] = node_id
            return node

    def get_or_create_node(
        self,
        node_type:  NodeType | str,
        label:      str,
        properties: dict | None = None,
        weight:     float = 1.0,
    ) -> Node:
        """Return existing node matching (type, label) or create a new one."""
        nt = NodeType(node_type) if isinstance(node_type, str) else node_type
        key = (nt.value, label.lower())
        with self._lock:
            if key in self._label_idx:
                nid = self._label_idx[key]
                if properties:
                    self._nodes[nid].properties.update(properties)
                return self._nodes[nid]
        # Create outside the lock-check to avoid re-entry, then re-lock in add_node
        nid = f"{nt.value}_{uuid.uuid4().hex[:12]}"
        return self.add_node(nid, nt, label, properties, weight)

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def find_node(self, node_type: NodeType | str, label: str) -> Node | None:
        nt = NodeType(node_type) if isinstance(node_type, str) else node_type
        nid = self._label_idx.get((nt.value, label.lower()))
        return self._nodes.get(nid) if nid else None

    def nodes_by_type(self, node_type: NodeType | str) -> list[Node]:
        nt = NodeType(node_type) if isinstance(node_type, str) else node_type
        ids = self._type_idx.get(nt.value, set())
        return [self._nodes[nid] for nid in ids if nid in self._nodes]

    def remove_node(self, node_id: str) -> bool:
        with self._lock:
            if node_id not in self._nodes:
                return False
            node = self._nodes.pop(node_id)
            # Remove from type index
            self._type_idx.get(node.node_type.value, set()).discard(node_id)
            self._label_idx.pop((node.node_type.value, node.label.lower()), None)
            # Remove all connected edges
            for eid in list(self._out.get(node_id, [])):
                self._remove_edge_unsafe(eid)
            for eid in list(self._in.get(node_id, [])):
                self._remove_edge_unsafe(eid)
            self._out.pop(node_id, None)
            self._in.pop(node_id, None)
            return True

    # ── Edge operations ───────────────────────────────────────────────────────

    def add_edge(
        self,
        source_id:  str,
        target_id:  str,
        rel_type:   RelType | str,
        weight:     float = 1.0,
        properties: dict | None = None,
    ) -> Edge | None:
        """Add a directed edge. Returns None if either node is missing."""
        rt = RelType(rel_type) if isinstance(rel_type, str) else rel_type
        with self._lock:
            if source_id not in self._nodes or target_id not in self._nodes:
                return None
            # Dedup: only one edge per (source, target, rel_type)
            for eid in self._out.get(source_id, []):
                e = self._edges[eid]
                if e.target == target_id and e.rel_type == rt:
                    if properties:
                        e.properties.update(properties)
                    return e
            eid = f"e_{uuid.uuid4().hex[:16]}"
            edge = Edge(edge_id=eid, source=source_id, target=target_id,
                        rel_type=rt, weight=weight, properties=properties or {})
            self._edges[eid] = edge
            self._out.setdefault(source_id, []).append(eid)
            self._in.setdefault(target_id, []).append(eid)
            self._rel_idx.setdefault(rt.value, []).append(eid)
            return edge

    def get_edge(self, edge_id: str) -> Edge | None:
        return self._edges.get(edge_id)

    def edges_by_rel(self, rel_type: RelType | str) -> list[Edge]:
        rt = RelType(rel_type) if isinstance(rel_type, str) else rel_type
        eids = self._rel_idx.get(rt.value, [])
        return [self._edges[eid] for eid in eids if eid in self._edges]

    def _remove_edge_unsafe(self, edge_id: str) -> None:
        """Remove edge without acquiring lock (must be called within lock)."""
        edge = self._edges.pop(edge_id, None)
        if edge:
            for lst in [self._out.get(edge.source, []),
                        self._in.get(edge.target, [])]:
                try:
                    lst.remove(edge_id)
                except ValueError:
                    pass
            rel_list = self._rel_idx.get(edge.rel_type.value, [])
            try:
                rel_list.remove(edge_id)
            except ValueError:
                pass

    # ── Traversal ─────────────────────────────────────────────────────────────

    def neighbors(
        self,
        node_id:  str,
        rel_type: str | None = None,
        direction: str = "out",   # "out" | "in" | "both"
    ) -> list[str]:
        """Return neighboring node IDs."""
        result: list[str] = []
        if direction in ("out", "both"):
            for eid in self._out.get(node_id, []):
                e = self._edges.get(eid)
                if e and (rel_type is None or e.rel_type.value == rel_type):
                    result.append(e.target)
        if direction in ("in", "both"):
            for eid in self._in.get(node_id, []):
                e = self._edges.get(eid)
                if e and (rel_type is None or e.rel_type.value == rel_type):
                    result.append(e.source)
        return result

    def degree(self, node_id: str) -> int:
        return len(self._out.get(node_id, [])) + len(self._in.get(node_id, []))

    def out_degree(self, node_id: str) -> int:
        return len(self._out.get(node_id, []))

    def in_degree(self, node_id: str) -> int:
        return len(self._in.get(node_id, []))

    # ── Stats ─────────────────────────────────────────────────────────────────

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def all_node_ids(self) -> list[str]:
        return list(self._nodes.keys())

    def all_nodes(self) -> list[Node]:
        return list(self._nodes.values())

    def all_edges(self) -> list[Edge]:
        return list(self._edges.values())

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._out.clear()
            self._in.clear()
            self._type_idx.clear()
            self._rel_idx.clear()
            self._label_idx.clear()


def create_graph() -> AcademicKnowledgeGraph:
    """Factory for a fresh graph instance."""
    return AcademicKnowledgeGraph()
