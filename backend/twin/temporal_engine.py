"""
Temporal evolution engine.

Computes timelines for: manuscripts, projects, collaborations, grants, teaching.
All data is from verified platform records.
Used to visualize how the researcher's career has developed over time.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger("twin.temporal")


async def build_timeline(db, user_id: str) -> dict:
    """
    Build a unified chronological timeline of platform events.
    Each event: type, title, date, category.
    Grouped by year for chart display.
    """
    now    = datetime.now(timezone.utc)
    events = []

    # Manuscripts
    async for ms in db.manuscripts.find({"user_id": user_id}, {"title": 1, "status": 1, "created_at": 1, "updated_at": 1}):
        dt = ms.get("created_at")
        if dt:
            events.append({
                "type":     "manuscript_created",
                "category": "publishing",
                "title":    (ms.get("title") or "Manuscript")[:80],
                "status":   ms.get("status"),
                "date":     dt.isoformat(),
                "year":     dt.year,
            })

    # Projects
    async for proj in db.projects.find({"user_id": user_id}, {"title": 1, "status": 1, "created_at": 1}):
        dt = proj.get("created_at")
        if dt:
            events.append({
                "type":     "project_created",
                "category": "research",
                "title":    (proj.get("title") or "Project")[:80],
                "status":   proj.get("status"),
                "date":     dt.isoformat(),
                "year":     dt.year,
            })

    # Collaborations
    async for collab in db.collaborations.find(
        {"$or": [{"requester_id": user_id}, {"recipient_id": user_id}], "status": "accepted"},
        {"created_at": 1}
    ):
        dt = collab.get("created_at")
        if dt:
            events.append({
                "type":     "collaboration_accepted",
                "category": "collaboration",
                "title":    "Collaboration accepted",
                "date":     dt.isoformat(),
                "year":     dt.year,
            })

    # Grants
    async for grant in db.grants.find({"user_id": user_id}, {"title": 1, "status": 1, "created_at": 1}):
        dt = grant.get("created_at")
        if dt:
            events.append({
                "type":     "grant_submitted",
                "category": "funding",
                "title":    (grant.get("title") or "Grant")[:80],
                "status":   grant.get("status"),
                "date":     dt.isoformat(),
                "year":     dt.year,
            })

    # Teaching
    try:
        async for lesson in db.lessons.find({"instructor_id": user_id}, {"title": 1, "created_at": 1}):
            dt = lesson.get("created_at")
            if dt:
                events.append({
                    "type":     "lesson_added",
                    "category": "teaching",
                    "title":    (lesson.get("title") or "Lesson")[:80],
                    "date":     dt.isoformat(),
                    "year":     dt.year,
                })
    except Exception:
        pass

    # Sort chronologically
    events.sort(key=lambda e: e["date"])

    # Group by year
    by_year: dict[int, list] = defaultdict(list)
    for ev in events:
        by_year[ev["year"]].append(ev)

    timeline = [
        {
            "year":        year,
            "events":      evs,
            "event_count": len(evs),
            "categories":  list({e["category"] for e in evs}),
        }
        for year, evs in sorted(by_year.items())
    ]

    # Category totals
    cat_counts: dict[str, int] = defaultdict(int)
    for ev in events:
        cat_counts[ev["category"]] += 1

    return {
        "timeline":       timeline,
        "total_events":   len(events),
        "earliest_event": events[0]["date"] if events else None,
        "latest_event":   events[-1]["date"] if events else None,
        "category_totals": dict(cat_counts),
        "source":         "Synaptiq platform data — verified activity records",
        "policy_note":    "Timeline shows verified platform activity only. Events not recorded on Synaptiq are not shown.",
    }


async def get_domain_evolution(db, user_id: str) -> list[dict]:
    """
    Show how research domains appeared and evolved over time.
    Based on manuscript keyword and project tag creation dates.
    """
    domain_years: dict[str, set[int]] = defaultdict(set)

    async for ms in db.manuscripts.find({"user_id": user_id}, {"keywords": 1, "created_at": 1}):
        year = ms["created_at"].year if ms.get("created_at") else None
        if year:
            for kw in (ms.get("keywords") or []):
                domain_years[str(kw).lower()].add(year)

    async for proj in db.projects.find({"user_id": user_id}, {"tags": 1, "created_at": 1}):
        year = proj["created_at"].year if proj.get("created_at") else None
        if year:
            for tag in (proj.get("tags") or []):
                domain_years[str(tag).lower()].add(year)

    return [
        {
            "domain":      domain,
            "years_active": sorted(years),
            "first_year":  min(years),
            "last_year":   max(years),
            "span_years":  max(years) - min(years) + 1,
        }
        for domain, years in sorted(domain_years.items(), key=lambda x: min(x[1]))
        if years
    ][:20]
