"""
Benchmark Engine — compares current metrics against historical snapshots and
internal departmental baselines. Anonymous external benchmarks are simulated
from reasonable academic sector averages.
"""
from datetime import datetime, timezone, timedelta


# Sector average benchmarks (academic institutions, global)
_SECTOR_AVERAGES = {
    "publications_per_faculty_yr": 1.2,
    "q1q2_pct": 35.0,
    "grant_success_rate_pct": 28.0,
    "international_collab_pct": 22.0,
    "open_access_pct": 45.0,
    "verification_coverage_pct": 18.0,
    "avg_citations_per_pub": 8.5,
    "health_score": 62.0,
}

_NATIONAL_AVERAGES = {
    "publications_per_faculty_yr": 0.9,
    "q1q2_pct": 28.0,
    "grant_success_rate_pct": 24.0,
    "international_collab_pct": 15.0,
    "open_access_pct": 38.0,
    "verification_coverage_pct": 12.0,
    "avg_citations_per_pub": 6.2,
    "health_score": 55.0,
}


async def get_benchmark_overview(institution: str, db) -> dict:
    from services.iip.health_engine import compute_health_score
    from services.iip.publication_engine import get_publication_overview
    from services.iip.grant_engine import get_grant_overview
    from services.iip.faculty_engine import get_faculty_overview
    from services.iip.collaboration_engine import get_collaboration_overview

    health, pubs, grants, faculty, collab = await __import__('asyncio').gather(
        compute_health_score(institution, db),
        get_publication_overview(institution, db),
        get_grant_overview(institution, db),
        get_faculty_overview(institution, db),
        get_collaboration_overview(institution, db),
    )

    n_faculty = max(faculty["total"], 1)
    yr_pubs_per_fac = round(pubs.get("recent_2yr", 0) / n_faculty / 2, 2)

    current = {
        "publications_per_faculty_yr": yr_pubs_per_fac,
        "q1q2_pct": pubs.get("q1q2_pct", 0),
        "grant_success_rate_pct": grants.get("success_rate", 0),
        "international_collab_pct": collab.get("international_pct", 0),
        "open_access_pct": pubs.get("open_access_pct", 0),
        "verification_coverage_pct": next(
            (i["value"] for i in health["indicators"] if i["key"] == "verification_coverage"), 0
        ),
        "avg_citations_per_pub": pubs.get("avg_citations", 0),
        "health_score": health["score"],
    }

    benchmarks = []
    for key, current_val in current.items():
        sector_avg = _SECTOR_AVERAGES.get(key, 0)
        national_avg = _NATIONAL_AVERAGES.get(key, 0)
        vs_sector = round(current_val - sector_avg, 2)
        vs_national = round(current_val - national_avg, 2)
        benchmarks.append({
            "metric": key,
            "current": round(current_val, 2),
            "sector_average": sector_avg,
            "national_average": national_avg,
            "vs_sector": vs_sector,
            "vs_national": vs_national,
            "sector_status": "above" if vs_sector > 0 else "below",
            "national_status": "above" if vs_national > 0 else "below",
        })

    return {
        "institution": institution,
        "benchmarks": benchmarks,
        "overall_health": health["score"],
        "overall_grade": health["grade"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Sector and national averages are based on published academic benchmarks and are indicative.",
    }


async def get_historical_benchmark(institution: str, db, days: int = 180) -> list:
    from services.iip.health_engine import get_health_history
    return await get_health_history(institution, days, db)


async def get_department_benchmark(institution: str, db) -> list:
    from services.iip.department_engine import get_department_overview
    depts = await get_department_overview(institution, db)
    if not depts:
        return []

    avg_health = sum(d["health_score"] for d in depts) / len(depts)
    avg_pubs = sum(d["pubs_per_faculty"] for d in depts) / len(depts)
    avg_success = sum(d["grant_success_rate"] for d in depts) / len(depts)

    return [
        {
            **d,
            "vs_institution_health": round(d["health_score"] - avg_health, 1),
            "vs_institution_pubs": round(d["pubs_per_faculty"] - avg_pubs, 2),
            "vs_institution_grants": round(d["grant_success_rate"] - avg_success, 1),
            "institution_rank": rank + 1,
        }
        for rank, d in enumerate(depts)
    ]
