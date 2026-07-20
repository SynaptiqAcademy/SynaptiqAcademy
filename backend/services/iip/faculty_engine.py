"""
Faculty Intelligence Engine — per-researcher analytics aggregated from existing collections.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from bson import ObjectId


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, float(v)))


async def _pub_counts(uid: str, db) -> dict:
    yr = datetime.now().year
    total = await db.publications.count_documents({"user_id": uid})
    recent = await db.publications.count_documents({"user_id": uid, "year": {"$gte": yr - 2}})
    return {"total": total, "recent_2yr": recent}


async def get_faculty_overview(institution: str, db) -> dict:
    users = await db.users.find({"institution": institution}).to_list(length=2000)
    yr = datetime.now().year
    uids = [str(u["_id"]) for u in users]

    if not users:
        return {"total": 0, "active": 0, "departments": [], "positions": {}, "institution": institution}

    # Active = published in last 2 years
    active_ids = set(await db.publications.distinct("user_id", {
        "user_id": {"$in": uids}, "year": {"$gte": yr - 2},
    }))

    # Department breakdown
    dept_map: dict = {}
    position_map: dict = {}
    for u in users:
        d = u.get("department") or "Unknown"
        dept_map[d] = dept_map.get(d, 0) + 1
        p = u.get("academic_position") or "Unknown"
        position_map[p] = position_map.get(p, 0) + 1

    departments = [{"name": k, "count": v} for k, v in sorted(dept_map.items(), key=lambda x: -x[1])]

    return {
        "institution": institution,
        "total": len(users),
        "active": len(active_ids),
        "inactive": len(users) - len(active_ids),
        "engagement_rate": round(len(active_ids) / len(users) * 100, 1),
        "departments": departments[:10],
        "positions": position_map,
    }


async def get_faculty_list(institution: str, db, limit: int = 50, skip: int = 0) -> dict:
    users = await db.users.find({"institution": institution}).skip(skip).limit(limit).to_list(length=limit)
    total = await db.users.count_documents({"institution": institution})
    yr = datetime.now().year

    async def _enrich(u: dict) -> dict:
        uid = str(u["_id"])
        pub_total = await db.publications.count_documents({"user_id": uid})
        pub_recent = await db.publications.count_documents({"user_id": uid, "year": {"$gte": yr - 2}})
        grants = await db.grant_applications.count_documents({"user_id": uid})
        courses = await db.courses.count_documents({"user_id": uid})
        collabs = await db.collaborations.count_documents({"user_id": uid})
        trust = await db.trust_profiles.find_one({"user_id": uid}, {"verification_level": 1, "trust_score": 1})

        # Productivity score: composite
        prod = _clamp((pub_recent * 20) + (grants * 5) + (courses * 5) + (collabs * 5))

        return {
            "user_id": uid,
            "name": u.get("full_name") or u.get("name", ""),
            "email": u.get("email", ""),
            "department": u.get("department", ""),
            "position": u.get("academic_position", ""),
            "orcid": u.get("orcid", ""),
            "publications_total": pub_total,
            "publications_recent": pub_recent,
            "grants": grants,
            "courses": courses,
            "collaborations": collabs,
            "verification_level": (trust or {}).get("verification_level", 0),
            "trust_score": (trust or {}).get("trust_score", 0),
            "productivity_score": round(prod, 1),
            "status": "active" if pub_recent > 0 else "inactive",
        }

    enriched = await asyncio.gather(*[_enrich(u) for u in users])
    return {"total": total, "skip": skip, "limit": limit, "faculty": list(enriched)}


async def get_top_performers(institution: str, db, limit: int = 10) -> list:
    result = await get_faculty_list(institution, db, limit=100)
    sorted_fac = sorted(result["faculty"], key=lambda x: x["productivity_score"], reverse=True)
    return sorted_fac[:limit]


async def get_at_risk_researchers(institution: str, db) -> list:
    """Researchers with zero publications in last 3 years."""
    users = await db.users.find({"institution": institution}).to_list(length=2000)
    yr = datetime.now().year
    at_risk = []
    for u in users:
        uid = str(u["_id"])
        recent = await db.publications.count_documents({"user_id": uid, "year": {"$gte": yr - 3}})
        if recent == 0:
            grants = await db.grant_applications.count_documents({"user_id": uid})
            at_risk.append({
                "user_id": uid,
                "name": u.get("full_name") or u.get("name", ""),
                "department": u.get("department", ""),
                "position": u.get("academic_position", ""),
                "last_publication": None,
                "grants_ever": grants,
                "risk_level": "high" if grants == 0 else "medium",
                "recommendation": "Consider outreach to understand barriers and offer support.",
            })
    return sorted(at_risk, key=lambda x: x["risk_level"])


async def get_promotion_candidates(institution: str, db) -> list:
    """Faculty with strong recent metrics — candidates for promotion review."""
    result = await get_faculty_list(institution, db, limit=200)
    candidates = [
        f for f in result["faculty"]
        if f["publications_recent"] >= 3 and f["grants"] >= 1 and f["productivity_score"] >= 70
    ]
    return sorted(candidates, key=lambda x: x["productivity_score"], reverse=True)[:20]
