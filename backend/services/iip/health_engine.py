"""
Institution Health Score — 15 weighted indicators (weights sum exactly to 1.0).
All data derived from existing Synaptiq collections; no new data entry required.
"""
import asyncio
from datetime import datetime, timezone, timedelta
_INDICATORS = [
    ("research_productivity",    0.12, "Research Productivity",      "Publications per researcher per year"),
    ("publication_quality",      0.10, "Publication Quality",        "Share of Q1/Q2 publications"),
    ("grant_success",            0.10, "Grant Success Rate",         "Approved grants vs submitted"),
    ("faculty_engagement",       0.08, "Faculty Engagement",         "% actively producing research"),
    ("teaching_activity",        0.08, "Teaching Activity",          "Active courses per faculty"),
    ("research_integrity",       0.08, "Research Integrity",         "Average integrity score across faculty"),
    ("verification_coverage",    0.07, "Verification Coverage",      "% of researchers verified"),
    ("international_reach",      0.07, "International Reach",        "% international collaborations"),
    ("ai_adoption",              0.05, "AI Adoption",                "% faculty engaging with AI tools"),
    ("citation_impact",          0.08, "Citation Impact",            "Normalised citation performance"),
    ("supervision_activity",     0.05, "Supervision Activity",       "Active supervision per faculty"),
    ("collaboration_density",    0.06, "Collaboration Density",      "Avg collaborations per researcher"),
    ("profile_completeness",     0.03, "Profile Completeness",       "% complete researcher profiles"),
    ("institutional_reputation", 0.02, "Institutional Reputation",   "Average trust/reputation score"),
    ("funding_diversity",        0.01, "Funding Diversity",          "Variety of active funding sources"),
]
_WEIGHT_SUM = sum(w for _, w, *_ in _INDICATORS)
assert abs(_WEIGHT_SUM - 1.0) < 0.001, f"Weights sum to {_WEIGHT_SUM}, not 1.0"


def _grade(s: float) -> str:
    if s >= 90: return "A+"
    if s >= 80: return "A"
    if s >= 70: return "B"
    if s >= 60: return "C"
    if s >= 50: return "D"
    return "F"


def _c(v: float) -> float:
    return max(0.0, min(100.0, float(v)))


async def _research_productivity(uids: list, n: int, db) -> float:
    yr = datetime.now().year
    count = await db.publications.count_documents({"user_id": {"$in": uids}, "year": {"$gte": yr - 2}})
    return _c(count / n * 20)  # 5 pubs/person/2yr → 100


async def _publication_quality(uids: list, db) -> float:
    total = await db.publications.count_documents({"user_id": {"$in": uids}})
    if not total:
        return 50.0
    q12 = await db.publications.count_documents({
        "user_id": {"$in": uids}, "quartile": {"$in": ["Q1", "Q2", 1, 2]},
    })
    return _c(q12 / total * 100)


async def _grant_success(uids: list, db) -> float:
    total = await db.grant_applications.count_documents({"user_id": {"$in": uids}})
    if not total:
        return 50.0
    approved = await db.grant_applications.count_documents({
        "user_id": {"$in": uids},
        "status": {"$in": ["approved", "funded", "granted", "active"]},
    })
    return _c(approved / total * 100)


async def _faculty_engagement(uids: list, n: int, db) -> float:
    yr = datetime.now().year
    active = await db.publications.distinct("user_id", {"user_id": {"$in": uids}, "year": {"$gte": yr - 1}})
    return _c(len(active) / n * 100)


async def _teaching_activity(uids: list, n: int, db) -> float:
    count = await db.courses.count_documents({
        "user_id": {"$in": uids},
        "status": {"$in": ["active", "published", "completed"]},
    })
    return _c(count / n * 25)  # 4 courses/person → 100


async def _research_integrity_avg(uids: list, db) -> float:
    docs = await db.integrity_reports.find(
        {"user_id": {"$in": uids}, "status": "complete"},
        {"integrity_score": 1},
    ).to_list(length=1000)
    if not docs:
        return 50.0
    return _c(sum(d.get("integrity_score", 0) for d in docs) / len(docs))


async def _verification_coverage(uids: list, n: int, db) -> float:
    ver = await db.trust_profiles.count_documents({"user_id": {"$in": uids}, "verification_level": {"$gte": 1}})
    return _c(ver / n * 100)


async def _international_reach(uids: list, db) -> float:
    total = await db.collaborations.count_documents({"user_id": {"$in": uids}})
    if not total:
        return 30.0
    intl = await db.collaborations.count_documents({
        "user_id": {"$in": uids},
        "type": {"$in": ["international", "cross_border", "global"]},
    })
    return _c(intl / total * 100) if intl else 20.0


async def _ai_adoption(uids: list, n: int, db) -> float:
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    try:
        active = await db.ai_usage_logs.distinct("user_id", {
            "user_id": {"$in": uids}, "created_at": {"$gte": cutoff},
        })
        return _c(len(active) / n * 100)
    except Exception:
        return 30.0  # baseline if collection absent


async def _citation_impact(uids: list, db) -> float:
    pubs = await db.publications.find(
        {"user_id": {"$in": uids}, "citations": {"$exists": True, "$gt": 0}},
        {"citations": 1},
    ).to_list(length=500)
    if not pubs:
        return 40.0
    avg = sum(p.get("citations", 0) for p in pubs) / len(pubs)
    return _c(avg * 5)  # 20 avg citations → 100


async def _supervision_activity(uids: list, n: int, db) -> float:
    count = await db.collaborations.count_documents({
        "user_id": {"$in": uids},
        "type": {"$in": ["mentoring", "supervision", "co_supervision"]},
    })
    return _c(count / n * 33) if count else 40.0  # 3/person → 99


async def _collaboration_density(uids: list, n: int, db) -> float:
    total = await db.collaborations.count_documents({"user_id": {"$in": uids}})
    return _c(total / n * 20)  # 5 collabs/person → 100


async def _profile_completeness(users: list) -> float:
    required = ["full_name", "institution", "department", "academic_position", "research_interests", "orcid"]
    if not users:
        return 50.0
    scores = [sum(1 for f in required if u.get(f)) / len(required) for u in users]
    return _c(sum(scores) / len(scores) * 100)


async def _institutional_reputation(uids: list, db) -> float:
    docs = await db.trust_profiles.find(
        {"user_id": {"$in": uids}, "trust_score": {"$exists": True}},
        {"trust_score": 1},
    ).to_list(length=1000)
    if not docs:
        return 50.0
    avg = sum(d.get("trust_score", 0) for d in docs) / len(docs)
    return _c(avg / 10)  # trust_score 0-1000 → 0-100


async def _funding_diversity(uids: list, db) -> float:
    funders = await db.grant_applications.distinct("funder", {
        "user_id": {"$in": uids},
        "status": {"$in": ["approved", "funded", "active"]},
        "funder": {"$exists": True, "$ne": ""},
    })
    return _c(len(funders) * 10)  # 10 funders → 100


async def compute_health_score(institution: str, db) -> dict:
    users = await db.users.find({"institution": institution}).to_list(length=2000)
    uids = [str(u["_id"]) for u in users]
    n = max(len(users), 1)

    if not users:
        return {
            "score": 0.0, "grade": "F", "institution": institution,
            "faculty_count": 0, "indicators": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    results = await asyncio.gather(
        _research_productivity(uids, n, db),
        _publication_quality(uids, db),
        _grant_success(uids, db),
        _faculty_engagement(uids, n, db),
        _teaching_activity(uids, n, db),
        _research_integrity_avg(uids, db),
        _verification_coverage(uids, n, db),
        _international_reach(uids, db),
        _ai_adoption(uids, n, db),
        _citation_impact(uids, db),
        _supervision_activity(uids, n, db),
        _collaboration_density(uids, n, db),
        _profile_completeness(users),
        _institutional_reputation(uids, db),
        _funding_diversity(uids, db),
    )

    indicators, weighted_sum = [], 0.0
    for (key, weight, label, description), value in zip(_INDICATORS, results):
        indicators.append({
            "key": key, "label": label, "description": description,
            "value": round(value, 1), "weight": weight,
            "contribution": round(weight * value, 2),
            "status": "good" if value >= 70 else ("warning" if value >= 50 else "critical"),
        })
        weighted_sum += weight * value

    overall = round(min(100.0, max(0.0, weighted_sum)), 1)
    today = datetime.now(timezone.utc)

    await db.iip_health_snapshots.update_one(
        {"institution": institution, "date": today.strftime("%Y-%m-%d")},
        {"$set": {
            "institution": institution, "score": overall, "grade": _grade(overall),
            "faculty_count": len(users), "indicators": indicators,
            "date": today.strftime("%Y-%m-%d"),
            "created_at": today.isoformat(),
        }},
        upsert=True,
    )

    return {
        "score": overall, "grade": _grade(overall),
        "institution": institution, "faculty_count": len(users),
        "indicators": indicators,
        "generated_at": today.isoformat(),
    }


async def get_health_history(institution: str, days: int, db) -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    docs = await db.iip_health_snapshots.find(
        {"institution": institution, "date": {"$gte": cutoff}},
        {"date": 1, "score": 1, "grade": 1, "faculty_count": 1, "_id": 0},
    ).sort("date", 1).to_list(length=365)
    return docs
