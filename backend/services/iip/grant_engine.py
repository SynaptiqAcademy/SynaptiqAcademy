"""
Grant Intelligence Engine — aggregates grant analytics for the institution.
"""
import asyncio
from datetime import datetime, timezone


async def get_grant_overview(institution: str, db) -> dict:
    users = await db.users.find({"institution": institution}, {"_id": 1, "department": 1}).to_list(length=2000)
    uids = [str(u["_id"]) for u in users]
    uid_to_dept = {str(u["_id"]): (u.get("department") or "Unknown") for u in users}

    all_grants = await db.grant_applications.find(
        {"user_id": {"$in": uids}},
        {"user_id": 1, "funder": 1, "amount": 1, "status": 1, "year": 1, "title": 1},
    ).to_list(length=5000)

    total = len(all_grants)
    approved = [g for g in all_grants if g.get("status") in ("approved", "funded", "active", "granted")]
    submitted = [g for g in all_grants if g.get("status") in ("submitted", "under_review", "pending")]
    rejected = [g for g in all_grants if g.get("status") in ("rejected", "declined")]

    total_funding = sum(float(g.get("amount") or 0) for g in approved)

    # Funder distribution
    funder_map: dict = {}
    for g in all_grants:
        f = g.get("funder", "Unknown")
        if f:
            funder_map[f] = funder_map.get(f, 0) + 1
    top_funders = sorted(funder_map.items(), key=lambda x: -x[1])[:10]

    # By department
    dept_funding: dict = {}
    for g in approved:
        dept = uid_to_dept.get(g.get("user_id", ""), "Unknown")
        dept_funding[dept] = dept_funding.get(dept, 0) + float(g.get("amount") or 0)

    # By year
    by_year: dict = {}
    for g in all_grants:
        y = str(g.get("year", ""))
        if y:
            by_year.setdefault(y, {"total": 0, "approved": 0})
            by_year[y]["total"] += 1
            if g.get("status") in ("approved", "funded", "active", "granted"):
                by_year[y]["approved"] += 1

    return {
        "institution": institution,
        "total": total,
        "approved": len(approved),
        "submitted": len(submitted),
        "rejected": len(rejected),
        "success_rate": round(len(approved) / total * 100, 1) if total else 0,
        "total_funding": round(total_funding, 2),
        "avg_grant_size": round(total_funding / len(approved), 2) if approved else 0,
        "top_funders": [{"funder": f, "count": c} for f, c in top_funders],
        "funding_by_department": [{"department": d, "funding": round(v, 2)} for d, v in sorted(dept_funding.items(), key=lambda x: -x[1])],
        "by_year": {k: v for k, v in sorted(by_year.items())},
    }


async def get_grant_pipeline(institution: str, db) -> list:
    users = await db.users.find({"institution": institution}, {"_id": 1, "full_name": 1, "name": 1}).to_list(length=2000)
    uid_to_name = {str(u["_id"]): (u.get("full_name") or u.get("name", "")) for u in users}
    uids = list(uid_to_name.keys())

    pipeline_grants = await db.grant_applications.find(
        {"user_id": {"$in": uids}, "status": {"$in": ["submitted", "under_review", "pending"]}},
        {"user_id": 1, "title": 1, "funder": 1, "amount": 1, "status": 1},
    ).to_list(length=500)

    return [
        {
            "grant_id": str(g.get("_id", "")),
            "title": g.get("title", "Untitled"),
            "funder": g.get("funder", "Unknown"),
            "amount": g.get("amount", 0),
            "status": g.get("status", "pending"),
            "researcher": uid_to_name.get(g.get("user_id", ""), "Unknown"),
        }
        for g in pipeline_grants
    ]
