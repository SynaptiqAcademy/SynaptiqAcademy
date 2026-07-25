"""Real workspace analytics aggregation (Workspace redesign Phase 8).

Every number here is computed from stored documents — no invented or
hardcoded metrics. Where a real limitation exists (see the module docstring
notes below each function), it is reflected honestly in the output rather
than papered over.

Task lifecycle timestamps come from `status_history`, a list of
`{"status": str, "at": iso_str}` entries appended by routers/projects.py on
every status change (and seeded with the creation status on insert). Tasks
that existed before this field was introduced only have their *current*
status known — for those, cycle/lead time are excluded from the sample
(never estimated), and burndown/cumulative-flow treat their current status
as having applied since creation, which is disclosed via `metric_definitions`
rather than silently assumed.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

TASK_STATUSES = ["backlog", "planned", "in_progress", "review", "completed"]

METRIC_DEFINITIONS = {
    "completion_rate_overall": "tasks_completed_total / tasks_total, across all tasks regardless of period.",
    "cycle_time_days": "Days between a task's first entry into 'in_progress' and its first entry into 'completed', per status_history. Only tasks with both transitions recorded are included (see sample_size).",
    "lead_time_days": "Days between task creation (created_at) and first entry into 'completed'. Only tasks with a recorded completion are included.",
    "overdue_count": "Open (non-completed) tasks whose due_date is before today.",
    "blocked_count": "Open tasks with at least one entry in depends_on whose referenced task is not completed.",
    "wip_count": "Tasks currently in 'in_progress' or 'review' — a snapshot, not a historical average.",
    "completed_trend": "Count of tasks completed per calendar week (Monday-start) within the period, using status_history's completed timestamp.",
    "burndown": "Per day in the period: count of tasks that exist (created_at <= day) and are not yet completed as of that day, reconstructed from status_history. Tasks with no history use their current status for their entire lifetime — a disclosed approximation for pre-Phase-8 tasks.",
    "cumulative_flow": "Per day in the period: count of tasks in each status as of that day, same reconstruction/approximation rule as burndown.",
}


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def _median(vals: list[float]) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _stats(vals: list[float]) -> dict:
    return {
        "avg": round(sum(vals) / len(vals), 2) if vals else None,
        "median": round(_median(vals), 2) if vals else None,
        "sample_size": len(vals),
    }


def _empty_task_metrics(days: int) -> dict:
    return {
        "period_days": days,
        "tasks_total": 0, "tasks_completed_total": 0, "completion_rate_overall": None,
        "created_in_period": 0, "completed_in_period": 0,
        "overdue_count": 0, "blocked_count": 0, "wip_count": 0,
        "workload_by_status": [], "workload_by_assignee": [],
        "cycle_time_days": _stats([]), "lead_time_days": _stats([]),
        "completed_trend": [], "burndown": [], "cumulative_flow": [],
        "metric_definitions": METRIC_DEFINITIONS,
    }


async def compute_task_metrics(db, project_ids: list[str], days: int) -> dict:
    if not project_ids:
        return _empty_task_metrics(days)

    tasks = await db.tasks.find({"project_id": {"$in": project_ids}}).to_list(5000)
    if not tasks:
        return _empty_task_metrics(days)

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)
    today_iso = now.date().isoformat()
    task_by_id = {str(t["_id"]): t for t in tasks}

    total = len(tasks)
    completed_total = sum(1 for t in tasks if t.get("status") == "completed")
    created_in_period = 0
    completed_in_period = 0
    overdue_count = 0
    blocked_count = 0
    wip_count = 0
    workload_status: dict = {}
    workload_assignee: dict = {}
    cycle_times: list = []
    lead_times: list = []
    completed_dates: list = []

    for t in tasks:
        tid = str(t["_id"])
        status = t.get("status", "backlog")
        created_at = _parse_iso(t.get("created_at"))
        if created_at and created_at >= period_start:
            created_in_period += 1

        workload_status[status] = workload_status.get(status, 0) + 1
        if status != "completed":
            if status in ("in_progress", "review"):
                wip_count += 1
            due = t.get("due_date")
            if due and due < today_iso:
                overdue_count += 1
            deps = t.get("depends_on") or []
            if deps and any((task_by_id.get(d) or {}).get("status") != "completed" for d in deps):
                blocked_count += 1
            aid = t.get("assignee_id")
            if aid:
                workload_assignee[aid] = workload_assignee.get(aid, 0) + 1

        history = t.get("status_history") or []
        completed_at = None
        in_progress_at = None
        for h in history:
            hat = _parse_iso(h.get("at"))
            if not hat:
                continue
            if h.get("status") == "completed" and (completed_at is None or hat < completed_at):
                completed_at = hat
            if h.get("status") == "in_progress" and (in_progress_at is None or hat < in_progress_at):
                in_progress_at = hat
        if completed_at:
            if completed_at >= period_start:
                completed_in_period += 1
                completed_dates.append(completed_at.date())
            if created_at:
                lead_times.append((completed_at - created_at).total_seconds() / 86400)
            if in_progress_at:
                cycle_times.append((completed_at - in_progress_at).total_seconds() / 86400)

    # enrich assignee workload with names
    assignee_ids = list(workload_assignee.keys())
    names = {}
    if assignee_ids:
        from bson import ObjectId
        oids = []
        for a in assignee_ids:
            try:
                oids.append(ObjectId(a))
            except Exception:
                pass
        if oids:
            users = await db.users.find({"_id": {"$in": oids}}, {"full_name": 1}).to_list(200)
            names = {str(u["_id"]): u.get("full_name", "") for u in users}

    weekly = defaultdict(int)
    for d in completed_dates:
        week_start = (d - timedelta(days=d.weekday())).isoformat()
        weekly[week_start] += 1
    completed_trend = [{"period_start": k, "count": v} for k, v in sorted(weekly.items())]

    # Burndown + cumulative flow: reconstruct per-day status from history,
    # falling back to current status for tasks with no recorded history.
    day_list = [(now - timedelta(days=i)).date() for i in range(days - 1, -1, -1)]
    burndown = []
    cumulative_flow = []
    for day in day_list:
        day_end = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)
        status_counts = {s: 0 for s in TASK_STATUSES}
        open_count = 0
        for t in tasks:
            created_at = _parse_iso(t.get("created_at"))
            if not created_at or created_at > day_end:
                continue
            history = t.get("status_history") or [{"status": t.get("status", "backlog"), "at": t.get("created_at")}]
            current = None
            for h in sorted(history, key=lambda h: h.get("at") or ""):
                hat = _parse_iso(h.get("at"))
                if hat and hat <= day_end:
                    current = h.get("status")
            current = current or t.get("status", "backlog")
            status_counts[current] = status_counts.get(current, 0) + 1
            if current != "completed":
                open_count += 1
        burndown.append({"date": day.isoformat(), "open_count": open_count})
        cumulative_flow.append({"date": day.isoformat(), **status_counts})

    return {
        "period_days": days,
        "tasks_total": total,
        "tasks_completed_total": completed_total,
        "completion_rate_overall": round(completed_total / total, 3) if total else None,
        "created_in_period": created_in_period,
        "completed_in_period": completed_in_period,
        "overdue_count": overdue_count,
        "blocked_count": blocked_count,
        "wip_count": wip_count,
        "workload_by_status": [{"status": s, "count": c} for s, c in workload_status.items()],
        "workload_by_assignee": [
            {"assignee_id": a, "name": names.get(a, ""), "open_count": c} for a, c in workload_assignee.items()
        ],
        "cycle_time_days": _stats(cycle_times),
        "lead_time_days": _stats(lead_times),
        "completed_trend": completed_trend,
        "burndown": burndown,
        "cumulative_flow": cumulative_flow,
        "metric_definitions": METRIC_DEFINITIONS,
    }


async def compute_content_activity(db, workspace_id: str, project_ids: list[str], days: int) -> dict:
    """Comment + wiki-edit activity by day, for the workspace's items/tasks."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    task_ids = []
    if project_ids:
        task_docs = await db.tasks.find({"project_id": {"$in": project_ids}}, {"_id": 1}).to_list(5000)
        task_ids = [str(d["_id"]) for d in task_docs]

    page_docs = await db.workspace_items.find(
        {"workspace_id": workspace_id, "item_type": "wiki_page"}, {"_id": 1}
    ).to_list(2000)
    page_ids = [str(d["_id"]) for d in page_docs]

    comments_by_day = []
    if page_ids or task_ids:
        or_clauses = [{"target_type": "workspace", "target_id": workspace_id}]
        if page_ids:
            or_clauses.append({"target_type": "workspace_item", "target_id": {"$in": page_ids}})
        if task_ids:
            or_clauses.append({"target_type": "task", "target_id": {"$in": task_ids}})
        pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}, "$or": or_clauses}},
            {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        comments_by_day = await db.item_comments.aggregate(pipeline).to_list(400)

    wiki_by_day = []
    if page_ids:
        pipeline = [
            {"$match": {"page_id": {"$in": page_ids}, "created_at": {"$gte": cutoff}}},
            {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        wiki_by_day = await db.wiki_page_versions.aggregate(pipeline).to_list(400)

    return {
        "comments_by_day": [{"date": a["_id"], "count": a["count"]} for a in comments_by_day],
        "wiki_edits_by_day": [{"date": a["_id"], "count": a["count"]} for a in wiki_by_day],
    }
