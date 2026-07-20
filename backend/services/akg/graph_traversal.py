"""Graph traversal — BFS, shortest path, neighborhood, common neighbors."""
from __future__ import annotations
import asyncio
from .graph_adapter import get_adapter


async def get_neighborhood(entity_id: str, depth: int,
                            rel_types: list[str] | None, db) -> dict:
    """BFS up to `depth` hops. Returns subgraph suitable for visualization."""
    return await get_adapter().get_neighbors(entity_id, min(depth, 3), rel_types, db)


async def find_shortest_path(from_id: str, to_id: str, db,
                              max_depth: int = 4) -> dict:
    """BFS shortest path between two entities."""
    adapter = get_adapter()

    if from_id == to_id:
        entity = await adapter.get_entity(from_id, db)
        return {"path": [entity] if entity else [], "length": 0, "found": True}

    visited: set[str] = {from_id}
    queue: list[tuple[str, list[str]]] = [(from_id, [from_id])]

    for depth in range(max_depth):
        if not queue:
            break
        next_queue: list[tuple[str, list[str]]] = []
        for current_id, path in queue:
            rels = await adapter.get_relationships(current_id, "both", None, db)
            for r in rels:
                neighbor = r.get("to_id") if r.get("from_id") == current_id else r.get("from_id")
                if not neighbor or neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == to_id:
                    entity_ids = list(new_path)
                    entities = {}
                    for eid in entity_ids:
                        e = await adapter.get_entity(eid, db)
                        if e:
                            entities[eid] = e
                    return {
                        "path": [entities.get(eid, {"entity_id": eid}) for eid in new_path],
                        "length": len(new_path) - 1,
                        "found": True,
                    }
                visited.add(neighbor)
                next_queue.append((neighbor, new_path))
        queue = next_queue

    return {"path": [], "length": -1, "found": False, "message": "No path found within depth limit"}


async def get_common_neighbors(entity_id_a: str, entity_id_b: str, db) -> dict:
    """Find entities connected to both A and B (Jaccard-style overlap)."""
    adapter = get_adapter()

    rels_a, rels_b = await asyncio.gather(
        adapter.get_relationships(entity_id_a, "both", None, db),
        adapter.get_relationships(entity_id_b, "both", None, db),
    )

    def neighbor_ids(eid: str, rels: list) -> set[str]:
        ids = set()
        for r in rels:
            n = r.get("to_id") if r.get("from_id") == eid else r.get("from_id")
            if n and n != eid:
                ids.add(n)
        return ids

    neighbors_a = neighbor_ids(entity_id_a, rels_a) - {entity_id_b}
    neighbors_b = neighbor_ids(entity_id_b, rels_b) - {entity_id_a}
    common = neighbors_a & neighbors_b

    entities = []
    for eid in list(common)[:20]:
        e = await adapter.get_entity(eid, db)
        if e:
            entities.append(e)

    jaccard = len(common) / len(neighbors_a | neighbors_b) if (neighbors_a | neighbors_b) else 0.0

    return {
        "common_neighbors": entities,
        "count": len(common),
        "jaccard_similarity": round(jaccard, 4),
        "neighbors_a_count": len(neighbors_a),
        "neighbors_b_count": len(neighbors_b),
    }


async def explore_from(entity_id: str, db, depth: int = 2,
                        rel_types: list[str] | None = None) -> dict:
    """Full subgraph exploration suitable for the graph explorer UI."""
    subgraph = await get_neighborhood(entity_id, depth, rel_types, db)
    seed_entity = await get_adapter().get_entity(entity_id, db)
    subgraph["seed_entity"] = seed_entity
    return subgraph
