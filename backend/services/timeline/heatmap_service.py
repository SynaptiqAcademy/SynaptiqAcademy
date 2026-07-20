from datetime import datetime, timezone, timedelta
from collections import defaultdict


async def get_heatmap(
    user_id: str,
    db,
    days: int = 365,
    category: str | None = None,
) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    filt: dict = {"user_id": user_id, "occurred_at": {"$gte": start, "$lte": end}}
    if category:
        filt["category"] = category

    daily: dict = defaultdict(list)
    cursor = db.timeline_events.find(
        filt,
        {"occurred_at": 1, "event_type": 1, "title": 1, "category": 1, "color": 1, "is_milestone": 1},
    )
    async for doc in cursor:
        day_key = doc["occurred_at"].strftime("%Y-%m-%d")
        daily[day_key].append({
            "event_type": doc.get("event_type", ""),
            "title": doc.get("title", ""),
            "category": doc.get("category", ""),
            "color": doc.get("color", "#0369A1"),
            "is_milestone": doc.get("is_milestone", False),
        })

    # Build day-by-day grid
    cells = []
    current = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while current <= end:
        day_str = current.strftime("%Y-%m-%d")
        events = daily.get(day_str, [])
        count = len(events)
        # 5-level intensity: 0 = none, 1 = 1, 2 = 2–3, 3 = 4–6, 4 = 7+
        intensity = 0 if count == 0 else (1 if count == 1 else (2 if count <= 3 else (3 if count <= 6 else 4)))
        has_milestone = any(e["is_milestone"] for e in events)
        cells.append({
            "date": day_str,
            "count": count,
            "intensity": intensity,
            "has_milestone": has_milestone,
            "events": events[:5],
        })
        current += timedelta(days=1)

    # Weekly totals
    weeks: dict = defaultdict(int)
    for c in cells:
        week = datetime.strptime(c["date"], "%Y-%m-%d").strftime("%Y-W%V")
        weeks[week] += c["count"]

    # Monthly totals
    months: dict = defaultdict(int)
    for c in cells:
        months[c["date"][:7]] += c["count"]

    total = sum(c["count"] for c in cells)
    active_days = sum(1 for c in cells if c["count"] > 0)
    max_day = max((c["count"] for c in cells), default=0)

    # Streak (consecutive active days ending today)
    streak = 0
    for c in reversed(cells):
        if c["count"] > 0:
            streak += 1
        else:
            break

    return {
        "cells": cells,
        "total_events": total,
        "active_days": active_days,
        "max_day_count": max_day,
        "current_streak": streak,
        "weeks": dict(sorted(weeks.items())),
        "months": dict(sorted(months.items())),
        "period_days": days,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
    }
