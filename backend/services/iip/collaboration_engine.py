"""
Collaboration Intelligence Engine — network analytics for the institution.
"""
from datetime import datetime, timezone


async def get_collaboration_overview(institution: str, db) -> dict:
    users = await db.users.find({"institution": institution}, {"_id": 1, "department": 1}).to_list(length=2000)
    uids = [str(u["_id"]) for u in users]

    all_collabs = await db.collaborations.find(
        {"user_id": {"$in": uids}},
        {"user_id": 1, "type": 1, "partner_institution": 1, "status": 1, "created_at": 1},
    ).to_list(length=5000)

    total = len(all_collabs)
    internal = sum(1 for c in all_collabs if c.get("partner_institution") == institution or c.get("type") == "internal")
    international = sum(1 for c in all_collabs if c.get("type") in ("international", "cross_border", "global"))
    active = sum(1 for c in all_collabs if c.get("status") in ("active", "ongoing", "approved"))

    # Partner institutions
    partner_map: dict = {}
    for c in all_collabs:
        p = c.get("partner_institution", "")
        if p and p != institution:
            partner_map[p] = partner_map.get(p, 0) + 1
    top_partners = sorted(partner_map.items(), key=lambda x: -x[1])[:10]

    # Type distribution
    type_map: dict = {}
    for c in all_collabs:
        t = c.get("type", "other")
        type_map[t] = type_map.get(t, 0) + 1

    # Network density (collabs / possible connections)
    n = len(uids)
    max_connections = n * (n - 1) / 2 if n > 1 else 1
    density = round(total / max_connections, 4) if max_connections > 0 else 0

    return {
        "institution": institution,
        "total": total,
        "active": active,
        "internal": internal,
        "international": international,
        "international_pct": round(international / total * 100, 1) if total else 0,
        "network_density": density,
        "avg_per_researcher": round(total / len(uids), 2) if uids else 0,
        "top_partner_institutions": [{"institution": p, "count": c} for p, c in top_partners],
        "type_distribution": type_map,
    }


async def get_collaboration_network(institution: str, db) -> dict:
    """Simplified network data: nodes (faculty) and edges (collaborations)."""
    users = await db.users.find(
        {"institution": institution},
        {"_id": 1, "full_name": 1, "name": 1, "department": 1},
    ).to_list(length=100)  # limit for network viz performance

    uids = [str(u["_id"]) for u in users]
    nodes = [{"id": str(u["_id"]), "name": u.get("full_name") or u.get("name", ""), "dept": u.get("department", "")} for u in users]

    collabs = await db.collaborations.find(
        {"user_id": {"$in": uids}, "partner_user_id": {"$exists": True}},
        {"user_id": 1, "partner_user_id": 1, "type": 1},
    ).to_list(length=500)

    edges = []
    seen = set()
    for c in collabs:
        src = c.get("user_id", "")
        tgt = c.get("partner_user_id", "")
        if src and tgt and src in uids and tgt in uids:
            key = tuple(sorted([src, tgt]))
            if key not in seen:
                seen.add(key)
                edges.append({"source": src, "target": tgt, "type": c.get("type", "")})

    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}
