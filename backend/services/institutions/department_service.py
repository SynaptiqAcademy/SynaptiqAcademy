"""Department-level analytics and aggregation service.

Departments are units with type="department" stored in the existing `units`
collection. All aggregations scope data to the subset of institution members
who have the department's unit_id in their `unit_ids` array.

New collections used:
  department_projects : {department_id, project_id, institution_id,
                         linked_by, linked_at}
  department_metrics  : cached metrics doc per department, TTL=3600s
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

PAID_INSTITUTION_PLANS = {"institution", "institution_pro", "institution_enterprise"}
METRICS_TTL_SECONDS = 3600


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────── institution plan gate ────────────────────────────

async def assert_institution_plan(institution_id: str) -> dict:
    """Raise 402 if the institution does not have a paid institution plan.
    Returns the institution doc on success."""
    from fastapi import HTTPException
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    inst = await db.institutions.find_one({"_id": ObjectId(institution_id)},
                                           {"name": 1, "plan_code": 1})
    if not inst:
        raise HTTPException(404, "Institution not found")
    if inst.get("plan_code") not in PAID_INSTITUTION_PLANS:
        raise HTTPException(
            402,
            detail={
                "code": "institution_plan_required",
                "message": "Department Management requires an Institution plan. Contact your institution admin.",
                "upgrade_url": "/pricing",
            },
        )
    inst["id"] = str(inst.pop("_id"))
    return inst


async def assert_dept_membership(institution_id: str, user_id: str) -> dict:
    """Raise 403 if user is not an approved member of the institution.
    Returns membership doc on success."""
    from fastapi import HTTPException
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    m = await db.institution_memberships.find_one(
        {"institution_id": institution_id, "user_id": user_id, "status": "approved"})
    if not m:
        raise HTTPException(403, "You must be an approved member of this institution")
    return m


async def assert_dept_admin(institution_id: str, department_id: str, user_id: str) -> None:
    """Raise 403 if user is not a department admin, institution admin, or platform admin."""
    from fastapi import HTTPException
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    # Platform admin bypass
    u = await db.users.find_one({"_id": ObjectId(user_id)}, {"role": 1})
    if (u or {}).get("role") == "admin":
        return
    # Institution admin bypass
    m = await db.institution_memberships.find_one(
        {"institution_id": institution_id, "user_id": user_id, "status": "approved"})
    if not m:
        raise HTTPException(403, "Not a member of this institution")
    if m.get("role") in {"owner", "admin"}:
        return
    # Department-level admin: unit_admin for this unit OR head_id
    dept = await db.units.find_one({"_id": ObjectId(department_id)}, {"admin_ids": 1, "head_id": 1})
    if not dept:
        raise HTTPException(404, "Department not found")
    if user_id in (dept.get("admin_ids") or []) or dept.get("head_id") == user_id:
        return
    raise HTTPException(403, "Department admin role required")


# ─────────────────────────── member helpers ───────────────────────────────────

async def get_dept_user_ids(institution_id: str, department_id: str) -> list[str]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved",
         "unit_ids": department_id},
        {"user_id": 1},
    ).to_list(2000)
    return [r["user_id"] for r in rows]


async def get_dept_members_enriched(institution_id: str, department_id: str) -> list[dict]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved",
         "unit_ids": department_id},
    ).to_list(500)
    if not rows:
        return []
    uids = [r["user_id"] for r in rows]
    udocs = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in uids]}},
        {"full_name": 1, "email": 1, "academic_role": 1, "avatar_url": 1,
         "research_areas": 1, "h_index": 1, "openalex_metrics": 1},
    ).to_list(len(uids))
    umap: dict[str, dict] = {}
    for u in udocs:
        uid_str = str(u.pop("_id"))
        oam = u.pop("openalex_metrics", None) or {}
        u["h_index"] = int(oam.get("h_index") or u.get("h_index") or 0)
        u["citations"] = int(oam.get("citations") or 0)
        umap[uid_str] = {**u, "id": uid_str}
    out = []
    for r in rows:
        r["id"] = str(r.pop("_id"))
        r["user"] = umap.get(r["user_id"])
        out.append(r)
    return out


# ─────────────────────────── projects helpers ─────────────────────────────────

async def get_dept_projects(department_id: str) -> list[dict]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    links = await db.department_projects.find(
        {"department_id": department_id}).sort("linked_at", -1).to_list(200)
    if not links:
        return []
    pids = [ObjectId(lk["project_id"]) for lk in links
            if len(lk.get("project_id", "")) == 24]
    proj_docs = await db.projects.find(
        {"_id": {"$in": pids}},
        {"title": 1, "description": 1, "visibility": 1, "keywords": 1,
         "members": 1, "owner_id": 1, "created_at": 1},
    ).to_list(200) if pids else []
    proj_map = {str(p["_id"]): p for p in proj_docs}
    out = []
    for lk in links:
        p = proj_map.get(lk["project_id"])
        if not p:
            continue
        members = p.get("members") or []
        out.append({
            "link_id":     lk["id"] if "id" in lk else str(lk.get("_id", "")),
            "project_id":  lk["project_id"],
            "title":       p.get("title") or "Untitled",
            "description": (p.get("description") or "")[:200],
            "visibility":  p.get("visibility") or "private",
            "keywords":    (p.get("keywords") or [])[:3],
            "team_size":   len(set([p.get("owner_id"), *members])) if p.get("owner_id") else len(members),
            "linked_at":   lk.get("linked_at"),
            "linked_by":   lk.get("linked_by"),
        })
    return out


# ─────────────────────────── metrics computation ──────────────────────────────

async def compute_dept_metrics(department_id: str, institution_id: str,
                                user_ids: list[str]) -> dict:
    """Compute all department metrics from real collections.

    Aggregates publications (ORCID), manuscripts (platform), citations,
    reputation scores, grants, and projects for the given user subset.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now()

    if not user_ids:
        return _empty_metrics()

    # Run all queries in parallel
    import asyncio
    (
        pub_agg,
        ms_total,
        ms_in_progress,
        rep_rows,
        grant_agg,
        grant_awarded,
        proj_count,
        collab_accepted,
        dept_proj_count,
    ) = await asyncio.gather(
        # Publications (ORCID-sourced, with citation data)
        db.publications.aggregate([
            {"$match": {"owner_id": {"$in": user_ids}}},
            {"$group": {
                "_id": None,
                "count":   {"$sum": 1},
                "cits":    {"$sum": {"$ifNull": ["$citations", 0]}},
                "h_sum":   {"$sum": {"$ifNull": ["$h_index_contribution", 0]}},
            }},
        ]).to_list(1),
        # Manuscripts (platform-written)
        db.manuscripts.count_documents(
            {"author_ids": {"$in": user_ids}, "status": "published"}),
        db.manuscripts.count_documents(
            {"author_ids": {"$in": user_ids}, "status": {"$ne": "published"}}),
        # Reputation scores
        db.reputation_scores.find({"user_id": {"$in": user_ids}}).to_list(500),
        # Grants
        db.grant_links.aggregate([
            {"$match": {"user_id": {"$in": user_ids}}},
            {"$group": {"_id": "$status", "n": {"$sum": 1}, "usd": {"$sum": "$amount_usd"}}},
        ]).to_list(20),
        # Awarded grant count
        db.grant_links.count_documents(
            {"user_id": {"$in": user_ids}, "status": "awarded"}),
        # Platform projects
        db.projects.count_documents(
            {"$or": [{"owner_id": {"$in": user_ids}}, {"members": {"$in": user_ids}}]}),
        # Accepted collaborations
        db.collaboration_requests.count_documents({
            "$or": [{"sender_id": {"$in": user_ids}}, {"receiver_id": {"$in": user_ids}}],
            "status": "accepted",
        }),
        # Department-linked projects
        db.department_projects.count_documents({"department_id": department_id}),
    )

    # Publications
    pub_stats = pub_agg[0] if pub_agg else {}
    pub_count    = int(pub_stats.get("count") or 0)
    total_cits   = int(pub_stats.get("cits") or 0)

    # Reputation
    rep_overalls = [r.get("overall") or 0 for r in rep_rows]
    avg_rep = round(sum(rep_overalls) / len(rep_overalls), 1) if rep_overalls else 0.0

    # h-index (per-user max, aggregate)
    h_values = []
    for r in rep_rows:
        pass  # reputation_scores doesn't have h_index — fetch from users
    u_rows = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in user_ids]}},
        {"h_index": 1, "openalex_metrics": 1},
    ).to_list(500)
    for u in u_rows:
        oam = u.get("openalex_metrics") or {}
        h = int(oam.get("h_index") or u.get("h_index") or 0)
        h_values.append(h)
    avg_h = round(sum(h_values) / len(h_values), 1) if h_values else 0.0
    max_h = max(h_values, default=0)

    # Grants / funding
    funding_usd = sum(int(r.get("usd") or 0) for r in grant_agg if r.get("_id") == "awarded")
    grant_total = sum(r.get("n", 0) for r in grant_agg)

    # Research areas (union of member research_areas)
    area_members = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in user_ids[:50]]}},
        {"research_areas": 1},
    ).to_list(50)
    area_counter: dict[str, int] = {}
    for u in area_members:
        for a in (u.get("research_areas") or []):
            area_counter[a] = area_counter.get(a, 0) + 1
    top_areas = sorted(area_counter.items(), key=lambda x: x[1], reverse=True)[:8]
    research_areas = [a for a, _ in top_areas]

    return {
        "members":           len(user_ids),
        "publications":      pub_count,
        "manuscripts":       ms_total,
        "manuscripts_wip":   ms_in_progress,
        "total_citations":   total_cits,
        "avg_citations":     round(total_cits / max(1, pub_count), 1),
        "avg_h_index":       avg_h,
        "max_h_index":       max_h,
        "avg_reputation":    avg_rep,
        "grants_total":      grant_total,
        "grants_awarded":    grant_awarded,
        "funding_usd":       funding_usd,
        "projects":          proj_count,
        "dept_projects":     dept_proj_count,
        "collaborations":    collab_accepted,
        "research_areas":    research_areas,
        "computed_at":       now,
    }


def _empty_metrics() -> dict:
    return {
        "members": 0, "publications": 0, "manuscripts": 0, "manuscripts_wip": 0,
        "total_citations": 0, "avg_citations": 0.0, "avg_h_index": 0.0,
        "max_h_index": 0, "avg_reputation": 0.0, "grants_total": 0,
        "grants_awarded": 0, "funding_usd": 0, "projects": 0,
        "dept_projects": 0, "collaborations": 0, "research_areas": [],
        "computed_at": _now(),
    }


async def get_cached_metrics(department_id: str, institution_id: str) -> dict:
    """Return cached metrics if fresh, else recompute and cache."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cached = await db.department_metrics.find_one({"department_id": department_id})
    if cached:
        try:
            ts = datetime.fromisoformat(cached.get("computed_at", "").replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - ts).seconds < METRICS_TTL_SECONDS:
                m = cached.get("metrics") or {}
                m["cached"] = True
                return m
        except Exception:
            pass
    user_ids = await get_dept_user_ids(institution_id, department_id)
    metrics  = await compute_dept_metrics(department_id, institution_id, user_ids)
    await db.department_metrics.update_one(
        {"department_id": department_id},
        {"$set": {"department_id": department_id, "institution_id": institution_id,
                  "metrics": metrics, "computed_at": metrics["computed_at"]}},
        upsert=True,
    )
    metrics["cached"] = False
    return metrics


# ─────────────────────────── rankings ────────────────────────────────────────

async def rank_departments(institution_id: str) -> list[dict]:
    """Rank all departments in the institution by a composite score.

    Score = 30% citations + 25% publications + 20% reputation + 15% funding + 10% projects
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    dept_docs = await db.units.find(
        {"institution_id": institution_id, "type": "department"},
        {"name": 1, "head_id": 1, "research_areas": 1},
    ).to_list(100)

    if not dept_docs:
        return []

    results = []
    for d in dept_docs:
        did = str(d["_id"])
        m   = await get_cached_metrics(did, institution_id)
        results.append({
            "department_id": did,
            "name":          d.get("name"),
            "research_areas": d.get("research_areas") or [],
            "metrics":       m,
        })

    if not results:
        return []

    # Normalise each dimension to 0..1 within the set, then weight
    def _norm(vals: list[float]) -> list[float]:
        mx = max(vals) if vals else 1.0
        if mx == 0:
            return [0.0] * len(vals)
        return [v / mx for v in vals]

    cits  = _norm([r["metrics"].get("total_citations", 0) for r in results])
    pubs  = _norm([r["metrics"].get("publications", 0)    for r in results])
    rep   = _norm([r["metrics"].get("avg_reputation", 0)  for r in results])
    fund  = _norm([r["metrics"].get("funding_usd", 0)     for r in results])
    proj  = _norm([r["metrics"].get("projects", 0)        for r in results])

    for i, r in enumerate(results):
        r["score"] = round(
            0.30 * cits[i] + 0.25 * pubs[i] + 0.20 * rep[i] +
            0.15 * fund[i] + 0.10 * proj[i],
            4,
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    for rank, r in enumerate(results, 1):
        r["rank"] = rank

    return results


# ─────────────────────────── collaboration network ────────────────────────────

async def get_dept_collaboration(institution_id: str, department_id: str) -> dict:
    """Internal + external collaboration summary for a department."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_ids = await get_dept_user_ids(institution_id, department_id)
    if not user_ids:
        return {"internal": 0, "external": 0, "network": [], "top_external_depts": []}

    uid_set = set(user_ids)

    # Get all institution member IDs for internal/external split
    all_inst = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved"},
        {"user_id": 1},
    ).to_list(5000)
    inst_uid_set = {r["user_id"] for r in all_inst}

    # Collaboration requests
    reqs = await db.collaboration_requests.find(
        {"$or": [{"sender_id": {"$in": user_ids}}, {"receiver_id": {"$in": user_ids}}],
         "status": "accepted"},
        {"sender_id": 1, "receiver_id": 1},
    ).to_list(2000)

    internal_count = 0
    external_count = 0
    edge_counts: dict[tuple, int] = {}

    for req in reqs:
        s, r_ = req.get("sender_id"), req.get("receiver_id")
        both_in_dept = s in uid_set and r_ in uid_set
        one_in_dept  = (s in uid_set) != (r_ in uid_set)
        if both_in_dept:
            internal_count += 1
        elif one_in_dept:
            external_count += 1
            a, b = sorted([s, r_])
            edge_counts[(a, b)] = edge_counts.get((a, b), 0) + 1

    # Top external collaborators
    top_edges = sorted(edge_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    ext_uids  = list({u for pair, _ in top_edges for u in pair if u not in uid_set})
    ext_docs  = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in ext_uids]}},
        {"full_name": 1, "institution": 1},
    ).to_list(len(ext_uids)) if ext_uids else []
    ext_map = {str(u["_id"]): u for u in ext_docs}

    network = []
    for (a, b), w in top_edges[:15]:
        network.append({
            "source": a, "source_name": ext_map.get(a, {}).get("full_name") or a,
            "target": b, "target_name": ext_map.get(b, {}).get("full_name") or b,
            "weight": w,
            "external": a not in uid_set or b not in uid_set,
        })

    return {
        "internal": internal_count,
        "external": external_count,
        "network":  network,
    }
