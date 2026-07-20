"""Academic Copilot — Dashboard Builder (Phase XI).

Assembles a personalised CopilotDashboard from all platform collections
for the authenticated user.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId

from .models import CopilotDashboard, DashboardWidget, Urgency

logger = logging.getLogger("synaptiq.copilot.dashboard")


def _safe_oid(val) -> bool:
    try:
        ObjectId(str(val))
        return True
    except Exception:
        return False


def _days_until(date_str: str | None) -> int | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(str(date_str)[:19], fmt).replace(tzinfo=timezone.utc)
            return (dt - datetime.now(timezone.utc)).days
        except ValueError:
            continue
    return None


async def build_dashboard(user_id: str, db) -> CopilotDashboard:
    dash = CopilotDashboard(user_id=user_id)
    widgets: list[DashboardWidget] = []

    try:
        uid_oid = ObjectId(user_id)
    except Exception:
        return dash

    # ── Active projects ────────────────────────────────────────────────────────
    try:
        projects = await db.projects.find(
            {"members": user_id, "status": {"$in": ["active", "in_progress", "planning"]}}
        ).sort("updated_at", -1).limit(5).to_list(5)
        dash.active_projects = [
            {
                "id": str(p["_id"]),
                "title": p.get("title", "Untitled"),
                "status": p.get("status"),
                "updated_at": str(p.get("updated_at", "")),
                "progress_pct": p.get("progress_pct", 0),
            }
            for p in projects
        ]
        if projects:
            widgets.append(DashboardWidget(
                widget_type="active_projects",
                title=f"Active Projects ({len(projects)})",
                data={"projects": dash.active_projects},
                priority=90,
            ))
    except Exception as exc:
        logger.debug("projects query failed: %s", exc)

    # ── Manuscripts & publication readiness ───────────────────────────────────
    try:
        manuscripts = await db.manuscripts.find(
            {"user_id": user_id, "status": {"$in": ["draft", "in_progress", "under_review", "revision_required"]}}
        ).sort("updated_at", -1).limit(8).to_list(8)
        readiness_items = []
        for ms in manuscripts:
            score = ms.get("publication_readiness_score") or ms.get("quality_score") or 0
            readiness_items.append({
                "id": str(ms["_id"]),
                "title": ms.get("title", "Untitled"),
                "status": ms.get("status"),
                "readiness_score": score,
                "word_count": ms.get("word_count", 0),
            })
        dash.publication_readiness = readiness_items
        if readiness_items:
            widgets.append(DashboardWidget(
                widget_type="publication_readiness",
                title=f"Manuscripts ({len(readiness_items)})",
                data={"manuscripts": readiness_items},
                priority=85,
                urgency=Urgency.MEDIUM,
            ))
    except Exception as exc:
        logger.debug("manuscripts query failed: %s", exc)

    # ── Upcoming deadlines ─────────────────────────────────────────────────────
    try:
        grant_apps = await db.grant_applications.find(
            {"user_id": user_id, "status": {"$in": ["draft", "in_progress"]}}
        ).limit(10).to_list(10)
        for g in grant_apps:
            deadline = g.get("deadline") or g.get("application_deadline")
            days = _days_until(deadline)
            if days is not None and 0 <= days <= 90:
                urgency = Urgency.CRITICAL if days <= 7 else (
                    Urgency.HIGH if days <= 21 else Urgency.MEDIUM
                )
                dash.upcoming_deadlines.append({
                    "type": "grant",
                    "title": g.get("grant_title") or g.get("title", "Grant"),
                    "deadline": str(deadline),
                    "days_remaining": days,
                    "urgency": urgency.value,
                })
    except Exception as exc:
        logger.debug("grant_applications query failed: %s", exc)

    try:
        milestones = await db.milestones.find(
            {"workspace_id": {"$exists": True}, "completed": False}
        ).limit(20).to_list(20)
        for m in milestones:
            days = _days_until(m.get("target_date"))
            if days is not None and 0 <= days <= 30:
                dash.upcoming_deadlines.append({
                    "type": "milestone",
                    "title": m.get("title", "Milestone"),
                    "deadline": str(m.get("target_date", "")),
                    "days_remaining": days,
                    "urgency": (Urgency.HIGH if days <= 7 else Urgency.MEDIUM).value,
                })
    except Exception as exc:
        logger.debug("milestones query failed: %s", exc)

    dash.upcoming_deadlines.sort(key=lambda d: d["days_remaining"])

    if dash.upcoming_deadlines:
        widgets.append(DashboardWidget(
            widget_type="upcoming_deadlines",
            title=f"Upcoming Deadlines ({len(dash.upcoming_deadlines)})",
            data={"deadlines": dash.upcoming_deadlines[:5]},
            priority=95,
            urgency=Urgency.HIGH,
        ))

    # ── Grant opportunities ────────────────────────────────────────────────────
    try:
        user_doc = await db.users.find_one({"_id": uid_oid}, {"research_areas": 1})
        research_areas = user_doc.get("research_areas") or [] if user_doc else []
        grant_count = await db.grants.count_documents({})
        dash.grant_opportunities = grant_count
        if grant_count > 0:
            widgets.append(DashboardWidget(
                widget_type="grant_opportunities",
                title=f"Grant Opportunities ({grant_count})",
                data={"count": grant_count, "research_areas": research_areas[:3]},
                priority=60,
                urgency=Urgency.LOW,
            ))
    except Exception as exc:
        logger.debug("grants query failed: %s", exc)

    # ── Conference opportunities ───────────────────────────────────────────────
    try:
        conf_count = await db.conferences.count_documents({})
        dash.conference_opportunities = conf_count
        if conf_count > 0:
            widgets.append(DashboardWidget(
                widget_type="conference_opportunities",
                title=f"Conferences ({conf_count})",
                data={"count": conf_count},
                priority=55,
                urgency=Urgency.LOW,
            ))
    except Exception as exc:
        logger.debug("conferences query failed: %s", exc)

    # ── Research goals from memory ─────────────────────────────────────────────
    try:
        memory_docs = await db.ai_memory.find(
            {"user_id": user_id, "is_active": True,
             "memory_type": {"$in": ["research_goal", "publication_goal", "career_goal"]}}
        ).limit(5).to_list(5)
        dash.research_goals = [m.get("content", "") for m in memory_docs if m.get("content")]
        if dash.research_goals:
            widgets.append(DashboardWidget(
                widget_type="research_goals",
                title="Research Goals",
                data={"goals": dash.research_goals},
                priority=70,
            ))
    except Exception as exc:
        logger.debug("ai_memory query failed: %s", exc)

    # ── Recommended actions (rule-based) ──────────────────────────────────────
    actions: list[dict] = []

    if not dash.research_goals:
        actions.append({
            "action_type": "set_research_goal",
            "label": "Set your research goal",
            "description": "Tell the Copilot your main research goal for personalised guidance.",
            "priority": 1,
        })
    if not dash.publication_readiness:
        actions.append({
            "action_type": "create_manuscript",
            "label": "Start a manuscript",
            "description": "Create your first manuscript and get AI-powered feedback.",
            "priority": 2,
        })
    if not dash.active_projects:
        actions.append({
            "action_type": "create_project",
            "label": "Start a research project",
            "description": "Organise your research with projects, milestones, and collaboration tools.",
            "priority": 3,
        })
    if dash.grant_opportunities > 0 and len(actions) < 4:
        actions.append({
            "action_type": "explore_grants",
            "label": "Explore grant opportunities",
            "description": f"Browse {dash.grant_opportunities} grants matched to your research areas.",
            "priority": 4,
        })

    dash.recommended_actions = actions[:4]

    # ── AI insights (rule-based, no LLM needed) ───────────────────────────────
    insights: list[str] = []
    if dash.active_projects and not dash.publication_readiness:
        insights.append("You have active research projects but no active manuscripts. Consider starting to write up your findings.")
    if len(dash.upcoming_deadlines) >= 2:
        d = dash.upcoming_deadlines[0]
        insights.append(f"Your most urgent deadline is '{d['title']}' in {d['days_remaining']} days.")
    if dash.publication_readiness:
        rev = [m for m in dash.publication_readiness if m.get("status") == "revision_required"]
        if rev:
            insights.append(f"You have {len(rev)} manuscript(s) awaiting revision. Addressing these promptly improves acceptance chances.")

    dash.ai_insights = insights[:4]

    # Sort widgets by priority descending
    widgets.sort(key=lambda w: -w.priority)
    dash.widgets = widgets

    return dash
