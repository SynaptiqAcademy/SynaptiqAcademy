from datetime import datetime, timezone, timedelta
from collections import defaultdict


_CATS = ["research", "teaching", "grant", "collaboration", "review", "verification", "recognition", "community", "ai"]


async def get_analytics(user_id: str, db, period_months: int = 12) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30 * period_months)

    cursor = db.timeline_events.find(
        {"user_id": user_id, "occurred_at": {"$gte": start}},
        {"occurred_at": 1, "category": 1, "event_type": 1, "is_milestone": 1},
    )

    monthly_raw: dict = defaultdict(lambda: defaultdict(int))
    category_total: dict = defaultdict(int)
    event_type_total: dict = defaultdict(int)

    async for doc in cursor:
        month_key = doc["occurred_at"].strftime("%Y-%m")
        cat = doc.get("category", "research")
        monthly_raw[month_key][cat] += 1
        monthly_raw[month_key]["total"] += 1
        category_total[cat] += 1
        event_type_total[doc.get("event_type", "")] += 1

    # Build complete month list (no gaps)
    monthly_breakdown = []
    cur = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while cur <= end:
        key = cur.strftime("%Y-%m")
        entry = {
            "month": key,
            "label": cur.strftime("%b %Y"),
            "total": monthly_raw[key].get("total", 0),
        }
        for cat in _CATS:
            entry[cat] = monthly_raw[key].get(cat, 0)
        monthly_breakdown.append(entry)
        # advance one month
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    # Top 10 event types
    top_types = sorted(event_type_total.items(), key=lambda x: x[1], reverse=True)[:10]

    # Trend: recent 3 months vs prior 3 months
    def _range_count(months_back_start: int, months_back_end: int) -> int:
        s = (end - timedelta(days=30 * months_back_start)).strftime("%Y-%m")
        e = (end - timedelta(days=30 * months_back_end)).strftime("%Y-%m")
        return sum(m["total"] for m in monthly_breakdown if s <= m["month"] <= e)

    recent_3 = _range_count(3, 0)
    prior_3 = _range_count(6, 3)
    trend_pct = round(((recent_3 - prior_3) / max(prior_3, 1)) * 100)

    # Peak month
    peak = max(monthly_breakdown, key=lambda m: m["total"], default=None)

    return {
        "monthly_breakdown": monthly_breakdown,
        "category_totals": dict(category_total),
        "top_event_types": [{"type": t, "count": c} for t, c in top_types],
        "trend_pct": trend_pct,
        "recent_3_months": recent_3,
        "prior_3_months": prior_3,
        "peak_month": peak,
        "period_months": period_months,
    }
