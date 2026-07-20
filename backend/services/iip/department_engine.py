"""
Department Intelligence Engine — aggregates per-department analytics.
"""
import asyncio
from datetime import datetime, timezone


async def get_department_overview(institution: str, db) -> list:
    users = await db.users.find({"institution": institution}, {"_id": 1, "department": 1}).to_list(length=2000)
    dept_map: dict[str, list] = {}
    for u in users:
        d = u.get("department") or "Unknown"
        dept_map.setdefault(d, []).append(str(u["_id"]))

    yr = datetime.now().year

    async def _analyze(dept_name: str, uids: list) -> dict:
        n = max(len(uids), 1)
        pubs, grants, courses, collabs = await asyncio.gather(
            db.publications.count_documents({"user_id": {"$in": uids}}),
            db.grant_applications.count_documents({"user_id": {"$in": uids}}),
            db.courses.count_documents({"user_id": {"$in": uids}}),
            db.collaborations.count_documents({"user_id": {"$in": uids}}),
        )
        recent_pubs = await db.publications.count_documents({
            "user_id": {"$in": uids}, "year": {"$gte": yr - 2},
        })
        approved_grants = await db.grant_applications.count_documents({
            "user_id": {"$in": uids},
            "status": {"$in": ["approved", "funded", "active"]},
        })
        grant_rate = approved_grants / grants if grants > 0 else 0

        # Health score proxy
        pub_rate = recent_pubs / n
        health = min(100, int(pub_rate * 20 + grant_rate * 40 + min(collabs / n, 1) * 20 + 20))

        return {
            "department": dept_name,
            "faculty_count": len(uids),
            "publications_total": pubs,
            "publications_recent": recent_pubs,
            "grants_total": grants,
            "grants_approved": approved_grants,
            "grant_success_rate": round(grant_rate * 100, 1),
            "courses": courses,
            "collaborations": collabs,
            "pubs_per_faculty": round(recent_pubs / n, 2),
            "health_score": health,
            "health_grade": ("A" if health >= 80 else "B" if health >= 65 else "C" if health >= 50 else "D"),
        }

    results = await asyncio.gather(*[_analyze(d, u) for d, u in dept_map.items()])
    return sorted(results, key=lambda x: x["health_score"], reverse=True)


async def get_department_detail(institution: str, department: str, db) -> dict:
    users = await db.users.find(
        {"institution": institution, "department": department},
        {"_id": 1, "full_name": 1, "name": 1, "academic_position": 1, "orcid": 1},
    ).to_list(length=500)
    uids = [str(u["_id"]) for u in users]
    yr = datetime.now().year

    pubs_by_year = {}
    all_pubs = await db.publications.find(
        {"user_id": {"$in": uids}, "year": {"$exists": True}},
        {"year": 1, "quartile": 1},
    ).to_list(length=2000)
    for p in all_pubs:
        y = str(p.get("year", ""))
        if y:
            pubs_by_year[y] = pubs_by_year.get(y, 0) + 1

    grant_types: dict = {}
    all_grants = await db.grant_applications.find(
        {"user_id": {"$in": uids}},
        {"funder": 1, "status": 1, "amount": 1},
    ).to_list(length=500)
    total_funding = sum(float(g.get("amount") or 0) for g in all_grants if g.get("status") in ("approved", "funded", "active"))
    for g in all_grants:
        f = g.get("funder", "Unknown")
        grant_types[f] = grant_types.get(f, 0) + 1

    q1q2 = sum(1 for p in all_pubs if p.get("quartile") in ["Q1", "Q2", 1, 2])
    pub_quality = round(q1q2 / len(all_pubs) * 100, 1) if all_pubs else 0

    return {
        "department": department,
        "institution": institution,
        "faculty": [{"user_id": str(u["_id"]), "name": u.get("full_name") or u.get("name"), "position": u.get("academic_position")} for u in users],
        "faculty_count": len(users),
        "publications_by_year": pubs_by_year,
        "publication_quality_pct": pub_quality,
        "total_publications": len(all_pubs),
        "total_funding_approved": round(total_funding, 2),
        "grant_funder_distribution": dict(sorted(grant_types.items(), key=lambda x: -x[1])[:10]),
        "collaborations": await db.collaborations.count_documents({"user_id": {"$in": uids}}),
    }
