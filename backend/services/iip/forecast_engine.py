"""
Forecast Engine — linear trend extrapolation for institutional KPIs.
No external ML dependencies; uses statistical trend from historical data.
"""
from datetime import datetime, timezone


def _linear_trend(data_points: list[tuple[int, float]]) -> tuple[float, float]:
    """Returns (slope, intercept) of least-squares line through (x, y) points."""
    n = len(data_points)
    if n < 2:
        return (0.0, data_points[0][1] if data_points else 0.0)
    xs = [p[0] for p in data_points]
    ys = [p[1] for p in data_points]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0
    intercept = y_mean - slope * x_mean
    return (slope, intercept)


def _project(slope: float, intercept: float, year: int) -> float:
    return max(0.0, slope * year + intercept)


async def get_publication_forecast(institution: str, db, horizon_years: int = 3) -> dict:
    users = await db.users.find({"institution": institution}, {"_id": 1}).to_list(length=2000)
    uids = [str(u["_id"]) for u in users]
    yr = datetime.now().year

    historical = []
    for y in range(yr - 5, yr):
        count = await db.publications.count_documents({"user_id": {"$in": uids}, "year": y})
        historical.append({"year": y, "count": count})

    points = [(h["year"], h["count"]) for h in historical if h["count"] > 0]
    slope, intercept = _linear_trend(points) if points else (0, 0)

    forecasts = []
    for delta in range(1, horizon_years + 1):
        target_yr = yr + delta
        projected = round(_project(slope, intercept, target_yr))
        confidence = max(40, 90 - delta * 15)
        forecasts.append({
            "year": target_yr, "projected": projected,
            "confidence_pct": confidence,
            "trend": "growth" if slope > 0 else ("stable" if abs(slope) < 0.5 else "decline"),
        })

    return {
        "metric": "publications",
        "historical": historical,
        "forecasts": forecasts,
        "trend_slope": round(slope, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_grant_forecast(institution: str, db, horizon_years: int = 3) -> dict:
    users = await db.users.find({"institution": institution}, {"_id": 1}).to_list(length=2000)
    uids = [str(u["_id"]) for u in users]
    yr = datetime.now().year

    historical = []
    for y in range(yr - 5, yr):
        count = await db.grant_applications.count_documents({"user_id": {"$in": uids}, "year": y})
        approved = await db.grant_applications.count_documents({
            "user_id": {"$in": uids}, "year": y,
            "status": {"$in": ["approved", "funded", "active"]},
        })
        historical.append({"year": y, "submitted": count, "approved": approved})

    points = [(h["year"], h["approved"]) for h in historical if h["year"]]
    slope, intercept = _linear_trend(points) if len(points) >= 2 else (0, points[0][1] if points else 0)

    forecasts = []
    for delta in range(1, horizon_years + 1):
        target_yr = yr + delta
        projected = round(_project(slope, intercept, target_yr))
        forecasts.append({
            "year": target_yr, "projected_approved": projected,
            "confidence_pct": max(40, 85 - delta * 15),
            "trend": "growth" if slope > 0 else ("stable" if abs(slope) < 0.3 else "decline"),
        })

    return {
        "metric": "grants",
        "historical": historical,
        "forecasts": forecasts,
        "trend_slope": round(slope, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_faculty_growth_forecast(institution: str, db, horizon_years: int = 3) -> dict:
    yr = datetime.now().year
    current_count = await db.users.count_documents({"institution": institution})

    historical_snapshots = await db.iip_health_snapshots.find(
        {"institution": institution},
        {"date": 1, "faculty_count": 1, "_id": 0},
    ).sort("date", 1).to_list(length=100)

    points = []
    for s in historical_snapshots:
        try:
            y = int(s["date"][:4])
            points.append((y, s["faculty_count"]))
        except Exception:
            pass

    if len(points) < 2:
        points = [(yr - 1, current_count), (yr, current_count)]

    slope, intercept = _linear_trend(points)
    forecasts = []
    for delta in range(1, horizon_years + 1):
        target_yr = yr + delta
        projected = round(_project(slope, intercept, target_yr))
        forecasts.append({
            "year": target_yr, "projected_faculty": projected,
            "change": projected - current_count,
            "confidence_pct": max(40, 80 - delta * 15),
        })

    return {
        "metric": "faculty_growth",
        "current_faculty": current_count,
        "forecasts": forecasts,
        "trend_slope": round(slope, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_citation_forecast(institution: str, db, horizon_years: int = 3) -> dict:
    users = await db.users.find({"institution": institution}, {"_id": 1}).to_list(length=2000)
    uids = [str(u["_id"]) for u in users]
    yr = datetime.now().year

    # Derive from existing publications' citation counts
    pubs = await db.publications.find(
        {"user_id": {"$in": uids}, "citations": {"$exists": True}},
        {"year": 1, "citations": 1},
    ).to_list(length=5000)

    by_year: dict[int, int] = {}
    for p in pubs:
        y = p.get("year")
        if y:
            by_year[y] = by_year.get(y, 0) + int(p.get("citations") or 0)

    historical = [{"year": y, "citations": c} for y, c in sorted(by_year.items()) if y <= yr]
    points = [(h["year"], h["citations"]) for h in historical]
    slope, intercept = _linear_trend(points) if len(points) >= 2 else (0, 0)

    forecasts = []
    for delta in range(1, horizon_years + 1):
        target_yr = yr + delta
        projected = round(_project(slope, intercept, target_yr))
        forecasts.append({
            "year": target_yr, "projected_citations": projected,
            "confidence_pct": max(35, 75 - delta * 15),
        })

    return {
        "metric": "citations",
        "historical": historical[-6:],
        "forecasts": forecasts,
        "trend_slope": round(slope, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
