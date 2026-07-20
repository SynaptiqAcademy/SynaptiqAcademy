"""
Publication Intelligence Engine — analytics on the institution's publication output.
"""
from datetime import datetime, timezone


async def get_publication_overview(institution: str, db) -> dict:
    users = await db.users.find({"institution": institution}, {"_id": 1}).to_list(length=2000)
    uids = [str(u["_id"]) for u in users]
    yr = datetime.now().year

    all_pubs = await db.publications.find(
        {"user_id": {"$in": uids}},
        {"year": 1, "quartile": 1, "journal": 1, "doi": 1, "citations": 1, "status": 1, "open_access": 1},
    ).to_list(length=5000)

    total = len(all_pubs)
    recent = sum(1 for p in all_pubs if (p.get("year") or 0) >= yr - 2)
    q1q2 = sum(1 for p in all_pubs if p.get("quartile") in ["Q1", "Q2", 1, 2])
    open_access = sum(1 for p in all_pubs if p.get("open_access"))
    total_citations = sum(int(p.get("citations") or 0) for p in all_pubs)

    # Publications by year
    by_year: dict = {}
    for p in all_pubs:
        y = str(p.get("year", ""))
        if y:
            by_year[y] = by_year.get(y, 0) + 1

    # Quartile distribution
    quartile_dist: dict = {}
    for p in all_pubs:
        q = str(p.get("quartile") or "Unknown")
        quartile_dist[q] = quartile_dist.get(q, 0) + 1

    # Top journals
    journal_map: dict = {}
    for p in all_pubs:
        j = p.get("journal", "Unknown")
        if j:
            journal_map[j] = journal_map.get(j, 0) + 1
    top_journals = sorted(journal_map.items(), key=lambda x: -x[1])[:10]

    # Citation distribution
    high_cited = sum(1 for p in all_pubs if int(p.get("citations") or 0) >= 10)
    uncited = sum(1 for p in all_pubs if int(p.get("citations") or 0) == 0)

    # Growth rate
    last_yr = by_year.get(str(yr - 1), 0)
    prev_yr = by_year.get(str(yr - 2), 0)
    growth = round((last_yr - prev_yr) / max(prev_yr, 1) * 100, 1) if prev_yr else 0

    return {
        "institution": institution,
        "total": total,
        "recent_2yr": recent,
        "q1q2_count": q1q2,
        "q1q2_pct": round(q1q2 / total * 100, 1) if total else 0,
        "open_access_count": open_access,
        "open_access_pct": round(open_access / total * 100, 1) if total else 0,
        "total_citations": total_citations,
        "avg_citations": round(total_citations / total, 2) if total else 0,
        "high_cited_count": high_cited,
        "uncited_count": uncited,
        "growth_rate_pct": growth,
        "by_year": dict(sorted(by_year.items())),
        "quartile_distribution": quartile_dist,
        "top_journals": [{"journal": j, "count": c} for j, c in top_journals],
    }


async def get_publication_trends(institution: str, db, years: int = 5) -> list:
    users = await db.users.find({"institution": institution}, {"_id": 1}).to_list(length=2000)
    uids = [str(u["_id"]) for u in users]
    yr = datetime.now().year
    trends = []
    for y in range(yr - years, yr + 1):
        total = await db.publications.count_documents({"user_id": {"$in": uids}, "year": y})
        q12 = await db.publications.count_documents({
            "user_id": {"$in": uids}, "year": y,
            "quartile": {"$in": ["Q1", "Q2", 1, 2]},
        })
        trends.append({
            "year": y, "total": total, "q1q2": q12,
            "q1q2_pct": round(q12 / total * 100, 1) if total else 0,
        })
    return trends
