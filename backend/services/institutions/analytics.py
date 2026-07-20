"""Institution analytics — aggregate REAL platform data: publications,
citations, grants, reputation, collaboration, marketplace activity.

All aggregations bind by `institution_id` (set via migration / membership flow).
Funding data merges both grant_links (ORCID-imported) and grant_applications
(platform-native lifecycle from Phase 10) for a complete picture.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

# Simple exchange rates for budget_to_usd conversion (platform grant applications)
_TO_USD: dict[str, float] = {
    "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CHF": 1.11,
    "JPY": 0.0068, "CAD": 0.73, "AUD": 0.65, "SEK": 0.095,
}

def _budget_to_usd(amount: float, currency: str) -> float:
    rate = _TO_USD.get((currency or "USD").upper().strip(), 1.0)
    return float(amount or 0) * rate

# Map grant_application statuses → canonical grant_links-style statuses
_APP_STATUS_MAP: dict[str, str] = {
    "draft": "in_preparation", "in_preparation": "in_preparation",
    "internal_review": "in_preparation", "ready_for_submission": "in_preparation",
    "submitted": "submitted", "eligible": "submitted", "under_evaluation": "submitted",
    "funded": "awarded",
    "rejected": "rejected",
    "closed": "closed", "withdrawn": "closed",
}


async def _platform_grants_for_users(user_ids: list[str]) -> list[dict]:
    """Return grant_applications rows for users as PI."""
    if not user_ids:
        return []
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    return await db.grant_applications.find(
        {"pi_id": {"$in": user_ids}},
        {"pi_id": 1, "status": 1, "requested_budget": 1, "currency": 1,
         "created_at": 1, "updated_at": 1},
    ).to_list(5000)


async def _scoped_user_ids(institution_id: str, *, unit_id: Optional[str] = None) -> list[str]:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    qf: dict = {"institution_id": institution_id, "status": "approved"}
    if unit_id: qf["unit_ids"] = unit_id
    rows = await db.institution_memberships.find(qf, {"user_id": 1}).to_list(5000)
    return [r["user_id"] for r in rows]


async def institution_overview(institution_id: str) -> dict:
    """Top-level overview KPIs for an institution page."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_ids = await _scoped_user_ids(institution_id)
    if not user_ids: return _empty_overview()

    (
        pub_total, pub_in_progress,
        gl_total_agg, gl_awarded_agg,
        app_rows,
        ws_count, project_count,
        rep_rows, u_rows,
    ) = await asyncio.gather(
        db.manuscripts.count_documents({"author_ids": {"$in": user_ids}, "status": "published"}),
        db.manuscripts.count_documents({"author_ids": {"$in": user_ids}, "status": {"$ne": "published"}}),
        db.grant_links.aggregate([
            {"$match": {"user_id": {"$in": user_ids}}},
            {"$group": {"_id": "$status", "n": {"$sum": 1}, "usd": {"$sum": "$amount_usd"}}},
        ]).to_list(20),
        db.grant_links.aggregate([
            {"$match": {"user_id": {"$in": user_ids}, "status": "awarded"}},
            {"$group": {"_id": None, "usd": {"$sum": "$amount_usd"}, "n": {"$sum": 1}}},
        ]).to_list(1),
        db.grant_applications.find(
            {"pi_id": {"$in": user_ids}},
            {"status": 1, "requested_budget": 1, "currency": 1},
        ).to_list(5000),
        db.workspaces.count_documents({"member_ids": {"$in": user_ids}}),
        db.projects.count_documents({"member_ids": {"$in": user_ids}}),
        db.reputation_scores.find({"user_id": {"$in": user_ids}}).to_list(len(user_ids)),
        db.users.find(
            {"_id": {"$in": [ObjectId(u) for u in user_ids]}},
            {"openalex_metrics": 1, "publications_count": 1, "h_index": 1},
        ).to_list(len(user_ids)),
    )

    # grant_links totals
    gl_awarded = (gl_awarded_agg[0] if gl_awarded_agg else {}) or {}
    gl_total   = sum(r.get("n", 0) for r in gl_total_agg)
    gl_award_n = int(gl_awarded.get("n") or 0)
    gl_award_usd = int(gl_awarded.get("usd") or 0)

    # grant_applications totals (platform-native)
    app_total  = len(app_rows)
    app_award_n   = sum(1 for a in app_rows if a.get("status") == "funded")
    app_award_usd = int(sum(_budget_to_usd(a.get("requested_budget") or 0, a.get("currency") or "USD")
                            for a in app_rows if a.get("status") == "funded"))

    funding_usd = gl_award_usd + app_award_usd
    overalls = [r.get("overall") or 0 for r in rep_rows]
    avg_rep = round(sum(overalls) / len(overalls), 1) if overalls else 0.0
    cite_total = sum(int((u.get("openalex_metrics") or {}).get("citations") or 0) for u in u_rows)
    h_total    = sum(int((u.get("openalex_metrics") or {}).get("h_index") or u.get("h_index") or 0) for u in u_rows)
    return {
        "researchers": len(user_ids),
        "publications": {"total": pub_total, "in_progress": pub_in_progress},
        "grants": {
            "total":       gl_total + app_total,
            "awarded":     gl_award_n + app_award_n,
            "awarded_usd": funding_usd,
        },
        "workspaces": ws_count, "projects": project_count,
        "reputation": {"average": avg_rep, "sample_size": len(rep_rows)},
        "citations_total": cite_total,
        "h_index_total": h_total,
    }


def _empty_overview() -> dict:
    return {"researchers": 0,
            "publications": {"total": 0, "in_progress": 0},
            "grants": {"total": 0, "awarded": 0, "awarded_usd": 0},
            "workspaces": 0, "projects": 0,
            "reputation": {"average": 0.0, "sample_size": 0},
            "citations_total": 0, "h_index_total": 0}


async def publications_breakdown(institution_id: str) -> dict:
    """Publications by year + by unit."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_ids = await _scoped_user_ids(institution_id)
    if not user_ids: return {"by_year": [], "by_unit": []}

    # By year (extracts year from created_at or published_at)
    by_year_pipe = [
        {"$match": {"author_ids": {"$in": user_ids}, "status": "published"}},
        {"$project": {"year": {"$substr": [{"$ifNull": ["$published_at", "$created_at"]}, 0, 4]}}},
        {"$group": {"_id": "$year", "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    by_year = await db.manuscripts.aggregate(by_year_pipe).to_list(50)
    by_year = [{"year": r["_id"], "n": r["n"]} for r in by_year if r.get("_id")]

    # By unit
    mem_rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved", "user_id": {"$in": user_ids}},
        {"user_id": 1, "unit_ids": 1}
    ).to_list(len(user_ids))
    unit_to_users: dict[str, set] = {}
    for m in mem_rows:
        for uid in (m.get("unit_ids") or []):
            unit_to_users.setdefault(uid, set()).add(m["user_id"])
    unit_names = {}
    if unit_to_users:
        u_docs = await db.units.find(
            {"_id": {"$in": [ObjectId(u) for u in unit_to_users.keys()]}},
            {"name": 1, "type": 1}).to_list(len(unit_to_users))
        unit_names = {str(u["_id"]): {"name": u.get("name"), "type": u.get("type")} for u in u_docs}
    by_unit = []
    for unit_id, uids in unit_to_users.items():
        if not unit_names.get(unit_id): continue
        n = await db.manuscripts.count_documents({"author_ids": {"$in": list(uids)}, "status": "published"})
        by_unit.append({"unit_id": unit_id, "name": unit_names[unit_id]["name"],
                         "type": unit_names[unit_id]["type"], "n": n})
    by_unit.sort(key=lambda x: x["n"], reverse=True)
    return {"by_year": by_year, "by_unit": by_unit[:20]}


async def collaboration_breakdown(institution_id: str) -> dict:
    """Internal vs external collaborations + network sample."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_ids = await _scoped_user_ids(institution_id)
    if not user_ids: return {"internal": 0, "external": 0, "network": []}
    uid_set = set(user_ids)
    # Co-authored manuscripts
    manus = await db.manuscripts.find(
        {"author_ids": {"$in": user_ids}}, {"author_ids": 1, "title": 1, "status": 1}
    ).to_list(1000)
    internal = external = 0
    edge_counts: dict[tuple, int] = {}
    for m in manus:
        authors = m.get("author_ids") or []
        in_inst = [a for a in authors if a in uid_set]
        out_inst = [a for a in authors if a not in uid_set]
        if len(in_inst) > 1: internal += 1
        if in_inst and out_inst: external += 1
        # Build edges between institution members on a manuscript
        for i in range(len(in_inst)):
            for j in range(i + 1, len(in_inst)):
                a, b = sorted([in_inst[i], in_inst[j]])
                edge_counts[(a, b)] = edge_counts.get((a, b), 0) + 1
    # Resolve user names for top edges
    top_edges = sorted(edge_counts.items(), key=lambda x: x[1], reverse=True)[:50]
    edge_user_ids = list({u for pair, _ in top_edges for u in pair})
    u_docs = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in edge_user_ids]}},
        {"full_name": 1}).to_list(len(edge_user_ids)) if edge_user_ids else []
    name_by_id = {str(u["_id"]): u.get("full_name") for u in u_docs}
    network = [{
        "source": a, "source_name": name_by_id.get(a),
        "target": b, "target_name": name_by_id.get(b), "weight": w,
    } for (a, b), w in top_edges]
    return {"internal": internal, "external": external, "network": network}


async def funding_breakdown(institution_id: str) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_ids = await _scoped_user_ids(institution_id)
    if not user_ids: return {"total_usd": 0, "by_status": [], "by_unit": []}

    gl_agg, app_rows, mem_rows = await asyncio.gather(
        db.grant_links.aggregate([
            {"$match": {"user_id": {"$in": user_ids}}},
            {"$group": {"_id": "$status", "n": {"$sum": 1}, "usd": {"$sum": "$amount_usd"}}},
        ]).to_list(20),
        _platform_grants_for_users(user_ids),
        db.institution_memberships.find(
            {"institution_id": institution_id, "status": "approved"},
            {"user_id": 1, "unit_ids": 1}
        ).to_list(len(user_ids)),
    )

    # Merge grant_links + grant_applications by_status
    merged: dict[str, dict] = {}
    for r in gl_agg:
        s = r.get("_id") or "unknown"
        merged[s] = {"status": s, "n": r.get("n", 0), "usd": int(r.get("usd") or 0)}
    for a in app_rows:
        s = _APP_STATUS_MAP.get(a.get("status") or "draft", "in_preparation")
        usd = _budget_to_usd(a.get("requested_budget") or 0, a.get("currency") or "USD")
        if s not in merged:
            merged[s] = {"status": s, "n": 0, "usd": 0}
        merged[s]["n"] += 1
        merged[s]["usd"] += int(usd)
    by_status = sorted(merged.values(), key=lambda x: x["usd"], reverse=True)
    total = sum(r["usd"] for r in by_status if r["status"] == "awarded")

    # By unit — merge both sources
    unit_to_users: dict[str, set] = {}
    for m in mem_rows:
        for uid in (m.get("unit_ids") or []):
            unit_to_users.setdefault(uid, set()).add(m["user_id"])
    unit_docs = await db.units.find(
        {"_id": {"$in": [ObjectId(u) for u in unit_to_users.keys()]}},
        {"name": 1, "type": 1}
    ).to_list(50) if unit_to_users else []
    unit_names = {str(u["_id"]): u for u in unit_docs}

    # Build per-unit PI → app mapping for grant_applications
    app_by_pi: dict[str, list] = {}
    for a in app_rows:
        app_by_pi.setdefault(a.get("pi_id", ""), []).append(a)

    by_unit = []
    for unit_id, uids in unit_to_users.items():
        if not unit_names.get(unit_id):
            continue
        info = unit_names[unit_id]
        uid_list = list(uids)
        gl_agg2 = await db.grant_links.aggregate([
            {"$match": {"user_id": {"$in": uid_list}, "status": "awarded"}},
            {"$group": {"_id": None, "usd": {"$sum": "$amount_usd"}, "n": {"$sum": 1}}},
        ]).to_list(1)
        gl_usd = int((gl_agg2[0].get("usd") if gl_agg2 else 0) or 0)
        gl_n   = int((gl_agg2[0].get("n") if gl_agg2 else 0) or 0)
        app_usd = sum(
            int(_budget_to_usd(a.get("requested_budget") or 0, a.get("currency") or "USD"))
            for uid in uid_list
            for a in app_by_pi.get(uid, [])
            if a.get("status") == "funded"
        )
        app_n = sum(
            sum(1 for a in app_by_pi.get(uid, []) if a.get("status") == "funded")
            for uid in uid_list
        )
        if gl_usd + app_usd == 0 and gl_n + app_n == 0:
            continue
        by_unit.append({
            "unit_id": unit_id, "name": info.get("name"), "type": info.get("type"),
            "awarded_usd": gl_usd + app_usd, "n": gl_n + app_n,
        })
    by_unit.sort(key=lambda x: x["awarded_usd"], reverse=True)
    return {"total_usd": total, "by_status": by_status, "by_unit": by_unit[:20]}


async def reputation_top(institution_id: str, limit: int = 10) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_ids = await _scoped_user_ids(institution_id)
    if not user_ids: return {"top_researchers": [], "top_units": [], "average": 0.0}
    rows = await db.reputation_scores.find({"user_id": {"$in": user_ids}}).to_list(len(user_ids))
    rows.sort(key=lambda r: r.get("overall") or 0, reverse=True)
    user_id_to_name = {}
    u_docs = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in user_ids]}},
        {"full_name": 1, "academic_role": 1, "avatar_url": 1}
    ).to_list(len(user_ids))
    for u in u_docs:
        uid = str(u["_id"])
        user_id_to_name[uid] = {"full_name": u.get("full_name"), "academic_role": u.get("academic_role"),
                                 "avatar_url": u.get("avatar_url"), "id": uid}
    top_researchers = []
    for r in rows[:limit]:
        u = user_id_to_name.get(r["user_id"])
        if not u: continue
        top_researchers.append({"user": u, "overall": r.get("overall"),
                                 "publication": (r.get("publication") or {}).get("score"),
                                 "reviewer": (r.get("reviewer") or {}).get("score"),
                                 "funding": (r.get("funding") or {}).get("score")})
    # Per unit averages
    mem_rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved"},
        {"user_id": 1, "unit_ids": 1}).to_list(len(user_ids))
    unit_to_users: dict[str, list] = {}
    for m in mem_rows:
        for uid in (m.get("unit_ids") or []):
            unit_to_users.setdefault(uid, []).append(m["user_id"])
    unit_docs = await db.units.find(
        {"_id": {"$in": [ObjectId(u) for u in unit_to_users.keys()]}}, {"name": 1, "type": 1}
    ).to_list(50) if unit_to_users else []
    unit_meta = {str(u["_id"]): u for u in unit_docs}
    rep_by_user = {r["user_id"]: r.get("overall") or 0 for r in rows}
    top_units = []
    for unit_id, uids in unit_to_users.items():
        info = unit_meta.get(unit_id)
        if not info: continue
        scores = [rep_by_user.get(u, 0) for u in uids if u in rep_by_user]
        if not scores: continue
        top_units.append({"unit_id": unit_id, "name": info.get("name"), "type": info.get("type"),
                            "average": round(sum(scores) / len(scores), 1), "n": len(scores)})
    top_units.sort(key=lambda x: x["average"], reverse=True)
    overalls = [r.get("overall") or 0 for r in rows]
    avg = round(sum(overalls) / len(overalls), 1) if overalls else 0.0
    return {"top_researchers": top_researchers, "top_units": top_units[:10], "average": avg}


async def marketplace_activity(institution_id: str) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_ids = await _scoped_user_ids(institution_id)
    if not user_ids: return {"expertise_open": 0, "expertise_filled": 0, "invitations_sent": 0,
                             "invitations_accepted": 0, "match_success_rate": 0.0}
    exp_open   = await db.expertise_requests.count_documents({"owner_id": {"$in": user_ids}, "status": "open"})
    exp_filled = await db.expertise_requests.count_documents({"owner_id": {"$in": user_ids}, "status": "filled"})
    inv_sent   = await db.marketplace_invitations.count_documents({"from_user_id": {"$in": user_ids}})
    inv_acc    = await db.marketplace_invitations.count_documents({"from_user_id": {"$in": user_ids}, "status": "accepted"})
    return {"expertise_open": exp_open, "expertise_filled": exp_filled,
            "invitations_sent": inv_sent, "invitations_accepted": inv_acc,
            "match_success_rate": round((inv_acc / inv_sent) if inv_sent else 0.0, 2)}


async def research_health(institution_id: str) -> dict:
    """Single composite "Research Health Score" for leadership dashboards.

    Blends recent activity, publication output, funding momentum, and avg
    reputation. 0..100.
    """
    overview = await institution_overview(institution_id)
    funding = await funding_breakdown(institution_id)
    rep = overview["reputation"]["average"] or 0
    pubs = overview["publications"]["total"]
    awarded = overview["grants"]["awarded"]
    funding_usd = funding["total_usd"]
    # Saturate each component to 0..100
    import math
    f = min(100, 100 * (1 - math.exp(-pubs / 50)))
    g = min(100, 100 * (1 - math.exp(-awarded / 10)))
    fu = min(100, 100 * (1 - math.exp(-(funding_usd or 0) / 1_000_000)))
    # Weighted blend
    score = round(0.35 * pubs_sat(pubs) + 0.25 * g + 0.15 * fu + 0.25 * rep, 1)
    return {
        "score": score,
        "publications_component": round(pubs_sat(pubs), 1),
        "grants_component": round(g, 1),
        "funding_usd_component": round(fu, 1),
        "reputation_component": round(rep, 1),
    }


def pubs_sat(n: int) -> float:
    import math
    return min(100.0, 100.0 * (1.0 - math.exp(-n / 40.0)))
