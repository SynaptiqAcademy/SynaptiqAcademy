"""Deterministic platform dashboard metrics aggregation."""
from __future__ import annotations

from typing import Any

from ..statistics.stats_engine import StatsEngine
from ..utils.date_utils import days_ago


def compute_platform_overview(users: list[dict]) -> dict[str, Any]:
    """Aggregate platform-level summary statistics from user list."""
    total = len(users)
    if not total:
        return {"total_users": 0}

    type_dist: dict[str, int] = {}
    countries: set[str] = set()
    institutions: set[str] = set()
    orcid_count = 0
    pub_counts: list[float] = []

    for u in users:
        t = u.get("user_type") or "unknown"
        type_dist[t] = type_dist.get(t, 0) + 1
        if u.get("country"):
            countries.add(u["country"])
        if u.get("institution"):
            institutions.add(u["institution"])
        if u.get("orcid_id"):
            orcid_count += 1
        pub_counts.append(float(u.get("publications_count") or 0))

    return {
        "total_users": total,
        "orcid_verified_pct": round(orcid_count / total * 100, 1),
        "unique_countries": len(countries),
        "unique_institutions": len(institutions),
        "user_type_distribution": type_dist,
        "avg_publications": round(StatsEngine.mean(pub_counts), 1),
        "median_publications": round(StatsEngine.median(pub_counts), 1),
    }


def compute_activity_metrics(
    activity_events: list[dict],
    window_days: int = 30,
) -> dict[str, Any]:
    """Compute activity metrics from event stream.

    events: list of {type, user_id, created_at} dicts.
    """
    cutoff = days_ago(window_days)
    recent = [
        e for e in activity_events
        if _parse_ts(e.get("created_at")) >= cutoff
    ]

    type_counts: dict[str, int] = {}
    user_activity: dict[str, int] = {}
    for e in recent:
        t = e.get("type") or "unknown"
        type_counts[t] = type_counts.get(t, 0) + 1
        uid = str(e.get("user_id") or "")
        if uid:
            user_activity[uid] = user_activity.get(uid, 0) + 1

    activity_values = list(user_activity.values())

    return {
        "window_days": window_days,
        "total_events": len(recent),
        "active_users": len(user_activity),
        "events_per_day": round(len(recent) / window_days, 1),
        "events_per_active_user": round(
            StatsEngine.mean(activity_values), 1
        ) if activity_values else 0.0,
        "event_type_breakdown": type_counts,
        "top_users": sorted(user_activity.items(), key=lambda x: -x[1])[:10],
    }


def compute_content_health(
    manuscripts: list[dict],
    projects: list[dict],
    collaborations: list[dict],
) -> dict[str, Any]:
    """Status breakdown of content items."""
    def _breakdown(items: list[dict]) -> dict[str, int]:
        d: dict[str, int] = {}
        for item in items:
            s = item.get("status") or "unknown"
            d[s] = d.get(s, 0) + 1
        return d

    ms_statuses = _breakdown(manuscripts)
    return {
        "manuscripts": {
            "total": len(manuscripts),
            "by_status": ms_statuses,
            "published_pct": round(
                ms_statuses.get("published", 0) / max(len(manuscripts), 1) * 100, 1
            ),
        },
        "projects": {
            "total": len(projects),
            "by_status": _breakdown(projects),
        },
        "collaborations": {
            "total": len(collaborations),
            "by_status": _breakdown(collaborations),
        },
    }


def compute_growth_rate(
    time_series: list[dict],
    value_key: str = "value",
    period: str = "month",
) -> dict[str, Any]:
    """Compute period-over-period growth rate from time series."""
    aggregated = StatsEngine.time_series_aggregate(time_series, period=period,
                                                   value_key=value_key)
    counts = [a["sum"] for a in aggregated]
    trend = StatsEngine.linear_trend(counts) if len(counts) >= 3 else None
    mom = [
        {"period": aggregated[i]["period"],
         "value": aggregated[i]["sum"],
         "growth_pct": StatsEngine.growth_rate(aggregated[i - 1]["sum"], aggregated[i]["sum"])}
        for i in range(1, len(aggregated))
    ] if len(aggregated) > 1 else []

    return {
        "periods": aggregated,
        "period_over_period": mom,
        "trend": trend,
        "forecast_next_3": StatsEngine.forecast(counts, steps=3) if len(counts) >= 3 else [],
    }


def _parse_ts(value: Any):
    from ..utils.date_utils import parse_date, utcnow
    dt = parse_date(str(value) if value else None)
    return dt or utcnow()
