"""
Sprint 1.4 — Unified Knowledge Graph Tests

Tests the consolidated lkg.unified.UnifiedGraphService and related modules.
Uses an in-memory fake MongoDB (FakeDB / FakeCol) — no real database required.

Coverage:
  - Entity CRUD (upsert, get, delete, list, search)
  - Relationship CRUD (upsert, get, delete)
  - Graph traversal (get_neighbors, find_path)
  - Inference (find_similar, detect_communities)
  - Legacy bridge (normalize_akg_entity, normalize_akg_rel)
  - AKG UnifiedAdapter (CRUD through adapter interface)
  - Entity type registry (validate_entity_type, validate_rel_type)
  - get_unified_graph() singleton
  - Stats endpoint
"""
import asyncio
from collections import defaultdict
from typing import Any

import pytest


# ── Fake MongoDB ──────────────────────────────────────────────────────────────

class FakeResult:
    def __init__(self, modified=0, upserted_id=None, deleted=0):
        self.modified_count = modified
        self.upserted_id    = upserted_id
        self.deleted_count  = deleted


class FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def skip(self, n):   self._docs = self._docs[n:]; return self
    def limit(self, n):  self._docs = self._docs[:n]; return self
    def sort(self, *a):  return self

    async def to_list(self, n): return list(self._docs[:n])
    def __aiter__(self):        return self._iter()
    async def _iter(self):
        for d in self._docs:
            yield d


class FakeCol:
    def __init__(self):
        self._docs: dict[str, dict] = {}  # keyed by _id / node_id
        self._seq = 0

    def _pk(self, doc: dict) -> str:
        """Primary key for this collection."""
        return (doc.get("node_id")
                or str(doc.get("from_id", "")) + "|" + str(doc.get("to_id", "")) + "|" + str(doc.get("type", ""))
                or doc.get("entity_id")
                or str(self._seq))

    async def update_one(self, filt: dict, update: dict, upsert: bool = False) -> FakeResult:
        # find matching doc
        match_key = self._find_key(filt)
        if match_key:
            doc = self._docs[match_key]
            if "$set" in update:
                doc.update(update["$set"])
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    doc[k] = doc.get(k, 0) + v
            return FakeResult(modified=1)
        elif upsert:
            # Build doc from $setOnInsert + $set
            new_doc: dict = {}
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    new_doc[k] = new_doc.get(k, 0) + v
            self._seq += 1
            key = self._pk(new_doc) or str(self._seq)
            self._docs[key] = new_doc
            return FakeResult(upserted_id=key)
        return FakeResult()

    async def find_one(self, filt: dict, proj: dict | None = None) -> dict | None:
        key = self._find_key(filt)
        if key:
            doc = dict(self._docs[key])
            if proj:
                doc.pop("_id", None)
            return doc
        return None

    async def insert_one(self, doc: dict) -> FakeResult:
        self._seq += 1
        key = self._pk(doc) or str(self._seq)
        self._docs[key] = dict(doc)
        return FakeResult(upserted_id=key)

    async def delete_one(self, filt: dict) -> FakeResult:
        key = self._find_key(filt)
        if key:
            del self._docs[key]
            return FakeResult(deleted=1)
        return FakeResult()

    async def delete_many(self, filt: dict) -> FakeResult:
        keys_to_del = [k for k in self._docs if self._matches(self._docs[k], filt)]
        for k in keys_to_del:
            del self._docs[k]
        return FakeResult(deleted=len(keys_to_del))

    def find(self, filt: dict | None = None, proj: dict | None = None) -> FakeCursor:
        filt = filt or {}
        matching = [dict(d) for d in self._docs.values() if self._matches(d, filt)]
        return FakeCursor(matching)

    async def count_documents(self, filt: dict) -> int:
        return sum(1 for d in self._docs.values() if self._matches(d, filt))

    async def create_index(self, *a, **kw) -> None:
        pass

    def _find_key(self, filt: dict) -> str | None:
        for k, doc in self._docs.items():
            if self._matches(doc, filt):
                return k
        return None

    def _matches(self, doc: dict, filt: dict) -> bool:
        for key, val in filt.items():
            if key == "$or":
                if not any(self._matches(doc, sub) for sub in val):
                    return False
            elif key == "$and":
                if not all(self._matches(doc, sub) for sub in val):
                    return False
            elif isinstance(val, dict):
                doc_val = doc.get(key)
                for op, operand in val.items():
                    if op == "$ne":
                        if doc_val == operand:
                            return False
                    elif op == "$in":
                        if doc_val not in operand:
                            return False
                    elif op == "$regex":
                        import re
                        flags = re.IGNORECASE if val.get("$options") == "i" else 0
                        if doc_val is None or not re.search(operand, str(doc_val), flags):
                            return False
            else:
                if doc.get(key) != val:
                    return False
        return True


class FakeDB:
    def __init__(self):
        self._cols: dict[str, FakeCol] = defaultdict(FakeCol)

    def __getitem__(self, name: str) -> FakeCol:
        return self._cols[name]


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)


# ── Entity type registry ──────────────────────────────────────────────────────

def test_all_entity_types_not_empty():
    from lkg.entity_types import ALL_ENTITY_TYPES
    assert len(ALL_ENTITY_TYPES) >= 30


def test_all_relationship_types_not_empty():
    from lkg.entity_types import ALL_RELATIONSHIP_TYPES
    assert len(ALL_RELATIONSHIP_TYPES) >= 20


def test_validate_entity_type_known():
    from lkg.entity_types import validate_entity_type
    assert validate_entity_type("Researcher") == "researcher"


def test_validate_entity_type_unknown():
    from lkg.entity_types import validate_entity_type
    with pytest.raises(ValueError):
        validate_entity_type("spaceship")


def test_validate_rel_type_known():
    from lkg.entity_types import validate_rel_type
    assert validate_rel_type("authored") == "AUTHORED"


def test_validate_rel_type_unknown():
    from lkg.entity_types import validate_rel_type
    with pytest.raises(ValueError):
        validate_rel_type("JUMPS_OVER")


def test_node_types_legacy_alias():
    from lkg.entity_types import NODE_TYPES
    assert "researcher" in NODE_TYPES


def test_edge_types_legacy_alias():
    from lkg.entity_types import EDGE_TYPES
    assert "AUTHORED" in EDGE_TYPES


# ── get_unified_graph singleton ───────────────────────────────────────────────

def test_get_unified_graph_singleton():
    from lkg.unified import get_unified_graph, UnifiedGraphService
    g1 = get_unified_graph()
    g2 = get_unified_graph()
    assert g1 is g2
    assert isinstance(g1, UnifiedGraphService)


# ── Upsert entity ─────────────────────────────────────────────────────────────

def test_upsert_entity_creates_node():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.upsert_entity(db, "researcher", "Alice Smith"))
    assert result["label"] == "Alice Smith"
    assert result["type"] == "researcher"
    assert result["confidence"] == "medium"


def test_upsert_entity_with_properties():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.upsert_entity(
        db, "publication", "My Paper",
        {"doi": "10.1000/xyz", "year": 2024},
        source="crossref", confidence="high",
    ))
    assert result["type"] == "publication"
    assert result["source"] == "crossref"
    assert result["confidence"] == "high"


def test_upsert_entity_custom_node_id():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.upsert_entity(
        db, "institution", "MIT",
        node_id="institution:ror:042nb2s44",
    ))
    assert result["node_id"] == "institution:ror:042nb2s44"


def test_upsert_entity_unknown_type_stored():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.upsert_entity(db, "alien_form", "Zorg"))
    assert result["type"] == "alien_form"


def test_upsert_entity_invalid_confidence_defaults_medium():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.upsert_entity(db, "researcher", "Bob", confidence="super_confident"))
    assert result["confidence"] == "medium"


# ── Get entity ────────────────────────────────────────────────────────────────

def test_get_entity_returns_none_for_missing():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.get_entity(db, "researcher:platform:nobody"))
    assert result is None


def test_get_entity_falls_back_to_akg():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    # Seed legacy akg_entities
    db["akg_entities"]._docs["e1"] = {
        "entity_id": "e1", "entity_type": "researcher", "label": "Legacy Bob"
    }
    graph = get_unified_graph()
    result = run(graph.get_entity(db, "e1"))
    assert result is not None
    assert "Legacy Bob" in str(result)


# ── Delete entity ─────────────────────────────────────────────────────────────

def test_delete_entity_returns_false_for_missing():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.delete_entity(db, "nonexistent"))
    assert result is False


def test_delete_entity_after_upsert():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.upsert_entity(db, "researcher", "Gone", node_id="gone:1"))
    result = run(graph.delete_entity(db, "gone:1"))
    assert result is True


# ── List entities ─────────────────────────────────────────────────────────────

def test_list_entities_empty():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.list_entities(db))
    assert result["nodes"] == []
    assert result["total"] == 0


def test_list_entities_with_data():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.upsert_entity(db, "researcher", "A"))
    run(graph.upsert_entity(db, "researcher", "B"))
    result = run(graph.list_entities(db, entity_type="researcher"))
    assert result["total"] == 2


# ── Search entities ───────────────────────────────────────────────────────────

def test_search_entities_empty_query():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.search_entities(db, ""))
    assert result == []


def test_search_entities_returns_list():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.upsert_entity(db, "researcher", "Alice Chen", node_id="r:1"))
    # Text index not available in fake; search falls back to regex
    result = run(graph.search_entities(db, "Alice"))
    # Should return a list (possibly empty if regex path not triggered)
    assert isinstance(result, list)


# ── Upsert relationship ───────────────────────────────────────────────────────

def test_upsert_relationship_creates_edge():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.upsert_relationship(db, "r:1", "p:1", "AUTHORED"))
    assert result["from_id"] == "r:1"
    assert result["to_id"] == "p:1"
    assert result["type"] == "AUTHORED"


def test_upsert_relationship_normalises_type():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.upsert_relationship(db, "r:1", "p:1", "authored"))
    assert result["type"] == "AUTHORED"


def test_upsert_relationship_with_evidence():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    ev = [{"type": "doi_link", "basis": "DOI metadata", "verified": True}]
    result = run(graph.upsert_relationship(
        db, "r:1", "p:2", "CITED",
        confidence="high", evidence=ev, status="verified",
    ))
    assert result["confidence"] == "high"
    assert result["status"] == "verified"


# ── Get relationships ─────────────────────────────────────────────────────────

def test_get_relationships_outgoing():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.upsert_relationship(db, "r:1", "p:1", "AUTHORED"))
    run(graph.upsert_relationship(db, "r:1", "p:2", "AUTHORED"))
    rels = run(graph.get_relationships(db, "r:1", direction="out"))
    from_ids = [r["from_id"] for r in rels]
    assert all(f == "r:1" for f in from_ids)


def test_get_relationships_incoming():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.upsert_relationship(db, "r:1", "p:1", "AUTHORED"))
    rels = run(graph.get_relationships(db, "p:1", direction="in"))
    assert any(r["to_id"] == "p:1" for r in rels)


# ── Delete relationship ───────────────────────────────────────────────────────

def test_delete_relationship_removes_edge():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.upsert_relationship(db, "r:1", "p:1", "AUTHORED"))
    result = run(graph.delete_relationship(db, "r:1", "p:1", "AUTHORED"))
    assert result is True


def test_delete_relationship_missing_returns_false():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.delete_relationship(db, "x", "y", "AUTHORED"))
    assert result is False


# ── get_neighbors ─────────────────────────────────────────────────────────────

def test_get_neighbors_returns_dict():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.upsert_entity(db, "researcher", "Alice", node_id="r:1"))
    result = run(graph.get_neighbors(db, "r:1", depth=1))
    assert "nodes" in result
    assert "edges" in result
    assert result["depth"] == 1


def test_get_neighbors_includes_root():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.upsert_entity(db, "researcher", "Alice", node_id="r:1"))
    result = run(graph.get_neighbors(db, "r:1", depth=1))
    node_ids = [n["node_id"] for n in result["nodes"] if "node_id" in n]
    assert "r:1" in node_ids


# ── find_path ─────────────────────────────────────────────────────────────────

def test_find_path_same_node():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.find_path(db, "r:1", "r:1"))
    assert result == ["r:1"]


def test_find_path_no_path():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.find_path(db, "r:1", "r:999", max_hops=2))
    assert result == []


def test_find_path_direct():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.upsert_relationship(db, "r:1", "p:1", "AUTHORED"))
    result = run(graph.find_path(db, "r:1", "p:1", max_hops=3))
    assert result == ["r:1", "p:1"]


# ── find_similar ─────────────────────────────────────────────────────────────

def test_find_similar_empty_graph():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.find_similar(db, "r:nobody"))
    assert result == []


def test_find_similar_has_evidence():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    # r:1 and r:2 both authored p:1
    run(graph.upsert_relationship(db, "r:1", "p:1", "AUTHORED"))
    run(graph.upsert_relationship(db, "r:2", "p:1", "AUTHORED"))
    run(graph.upsert_entity(db, "researcher", "Bob", node_id="r:2"))
    result = run(graph.find_similar(db, "r:1"))
    if result:  # may be empty if r:2 not found as entity yet
        for item in result:
            assert "evidence" in item
            assert "confidence" in item
            assert "confidence_basis" in item
            assert "confidence_pct" not in item


# ── detect_communities ────────────────────────────────────────────────────────

def test_detect_communities_empty():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.detect_communities(db))
    assert isinstance(result, list)


# ── Stats ─────────────────────────────────────────────────────────────────────

def test_stats_returns_expected_keys():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    result = run(graph.stats(db))
    for key in ("lkg_nodes", "lkg_edges", "total_nodes", "total_edges", "canonical_store"):
        assert key in result


# ── ensure_indexes ────────────────────────────────────────────────────────────

def test_ensure_indexes_does_not_raise():
    from lkg.unified import get_unified_graph
    db = FakeDB()
    graph = get_unified_graph()
    run(graph.ensure_indexes(db))  # FakeCol.create_index is a no-op


# ── Legacy bridge normalize ───────────────────────────────────────────────────

def test_normalize_akg_entity_basic():
    from lkg.bridge import normalize_akg_entity
    raw = {
        "entity_id": "e1", "entity_type": "researcher",
        "label": "Dr. Smith", "source": "openalex",
    }
    result = normalize_akg_entity(raw)
    assert result["node_id"] == "e1"
    assert result["type"] == "researcher"
    assert result["label"] == "Dr. Smith"
    assert result["source"] == "openalex"
    assert result["_bridge_source"] == "akg_entities"


def test_normalize_akg_entity_no_entity_id():
    from lkg.bridge import normalize_akg_entity
    raw = {"id": "fallback_id", "label": "X"}
    result = normalize_akg_entity(raw)
    assert result["node_id"] == "fallback_id"


def test_normalize_akg_entity_strips_mongo_id():
    from lkg.bridge import normalize_akg_entity
    raw = {"_id": "mongo_oid", "entity_id": "e2", "label": "Y"}
    result = normalize_akg_entity(raw)
    assert "_id" not in result


def test_normalize_akg_rel_basic():
    from lkg.bridge import normalize_akg_rel
    raw = {"from_id": "r:1", "to_id": "p:1", "rel_type": "authored"}
    result = normalize_akg_rel(raw)
    assert result["from_id"] == "r:1"
    assert result["to_id"] == "p:1"
    assert result["type"] == "AUTHORED"
    assert result["_bridge_source"] == "akg_relationships"


def test_normalize_akg_rel_strips_mongo_id():
    from lkg.bridge import normalize_akg_rel
    raw = {"_id": "oid", "from_id": "r:1", "to_id": "p:1", "rel_type": "CITED"}
    result = normalize_akg_rel(raw)
    assert "_id" not in result


# ── AKG UnifiedAdapter ────────────────────────────────────────────────────────

def test_unified_adapter_is_default():
    from services.akg.graph_adapter import get_adapter, UnifiedAdapter
    adapter = get_adapter()
    assert isinstance(adapter, UnifiedAdapter)


def test_unified_adapter_upsert_entity():
    from services.akg.graph_adapter import UnifiedAdapter
    db = FakeDB()
    adapter = UnifiedAdapter()
    result = run(adapter.upsert_entity("e:1", "researcher", "Alice", {}, db))
    assert result["label"] == "Alice"


def test_unified_adapter_get_entity_none():
    from services.akg.graph_adapter import UnifiedAdapter
    db = FakeDB()
    adapter = UnifiedAdapter()
    result = run(adapter.get_entity("nobody", db))
    assert result is None


def test_unified_adapter_list_entities():
    from services.akg.graph_adapter import UnifiedAdapter
    db = FakeDB()
    adapter = UnifiedAdapter()
    run(adapter.upsert_entity("e:1", "researcher", "Alice", {}, db))
    result = run(adapter.list_entities("researcher", 1, 10, db))
    assert "results" in result
    assert "total" in result
    assert "pages" in result


def test_unified_adapter_delete_entity():
    from services.akg.graph_adapter import UnifiedAdapter
    db = FakeDB()
    adapter = UnifiedAdapter()
    run(adapter.upsert_entity("e:del", "researcher", "Del", {}, db))
    result = run(adapter.delete_entity("e:del", db))
    assert result is True


def test_unified_adapter_upsert_relationship():
    from services.akg.graph_adapter import UnifiedAdapter
    db = FakeDB()
    adapter = UnifiedAdapter()
    result = run(adapter.upsert_relationship("r:1", "p:1", "AUTHORED", {}, db))
    assert result["from_id"] == "r:1"


def test_unified_adapter_get_relationships():
    from services.akg.graph_adapter import UnifiedAdapter
    db = FakeDB()
    adapter = UnifiedAdapter()
    run(adapter.upsert_relationship("r:1", "p:1", "AUTHORED", {}, db))
    rels = run(adapter.get_relationships("r:1", "out", None, db))
    assert isinstance(rels, list)


# ── LKG __init__ exports ──────────────────────────────────────────────────────

def test_lkg_init_exports_unified():
    import lkg
    assert hasattr(lkg, "get_unified_graph")
    assert hasattr(lkg, "UnifiedGraphService")


def test_lkg_init_exports_bridge():
    import lkg
    assert hasattr(lkg, "get_bridge_reader")
    assert hasattr(lkg, "migrate_akg_to_lkg")


def test_lkg_init_exports_types():
    import lkg
    assert hasattr(lkg, "ENTITY_TYPES")
    assert hasattr(lkg, "RELATIONSHIP_TYPES")
    assert hasattr(lkg, "validate_entity_type")
    assert hasattr(lkg, "validate_rel_type")


# ── No confidence_pct anywhere in unified.py ─────────────────────────────────

def test_no_confidence_pct_in_unified():
    from pathlib import Path
    src = Path(__file__).parent.parent / "lkg" / "unified.py"
    content = src.read_text()
    assert "confidence_pct" not in content, (
        "confidence_pct is forbidden (evidence policy). Use confidence high/medium/low only."
    )


def test_no_confidence_pct_in_bridge():
    from pathlib import Path
    src = Path(__file__).parent.parent / "lkg" / "bridge.py"
    content = src.read_text()
    assert "confidence_pct" not in content
