from datetime import datetime, timezone, timedelta


async def generate_insights(user_id: str, db) -> list[dict]:
    now = datetime.now(timezone.utc)
    d30 = now - timedelta(days=30)
    d60 = now - timedelta(days=60)
    d90 = now - timedelta(days=90)

    async def _count(since: datetime, category: str | None = None) -> int:
        filt: dict = {"user_id": user_id, "occurred_at": {"$gte": since}}
        if category:
            filt["category"] = category
        return await db.timeline_events.count_documents(filt)

    # Gather metrics
    recent_total  = await _count(d30)
    prior_total   = await _count(d60) - recent_total
    recent_collab = await _count(d30, "collaboration")
    recent_teach  = await _count(d30, "teaching")
    recent_grant  = await _count(d90, "grant")
    recent_ai     = await _count(d30, "ai")
    recent_review = await _count(d30, "review")
    recent_verify = await _count(d30, "verification")
    total_review  = await db.timeline_events.count_documents({"user_id": user_id, "category": "review"})
    total_events  = await db.timeline_events.count_documents({"user_id": user_id})

    from services.timeline.analytics_service import get_analytics
    analytics = await get_analytics(user_id, db, period_months=6)

    insights: list[dict] = []

    # Productivity trend
    if prior_total > 0:
        trend = round(((recent_total - prior_total) / prior_total) * 100)
        if trend >= 20:
            insights.append({
                "key": "productivity_up",
                "type": "positive",
                "title": "Research Productivity Increasing",
                "body": f"Your academic activity increased by {trend}% compared to the previous period.",
                "action": "Keep the momentum — consider submitting a new grant or preprint.",
            })
        elif trend <= -25 and prior_total >= 3:
            insights.append({
                "key": "productivity_down",
                "type": "warning",
                "title": "Research Activity Decreased",
                "body": f"Academic activity dropped by {abs(trend)}% over the last 30 days.",
                "action": "Reconnect with collaborators or revisit pending projects.",
            })

    # Collaboration growth
    if recent_collab >= 2:
        insights.append({
            "key": "collab_growth",
            "type": "positive",
            "title": "Collaboration Network Growing",
            "body": f"You added {recent_collab} collaboration events in the past 30 days.",
            "action": "Consider submitting a joint grant with your new collaborators.",
        })

    # Teaching inactivity
    if recent_teach == 0 and total_events > 5:
        insights.append({
            "key": "teaching_inactive",
            "type": "info",
            "title": "No Recent Teaching Activity",
            "body": "No teaching events recorded in the past 30 days.",
            "action": "Log a course creation or lesson to maintain your teaching profile.",
        })

    # Grant gap
    if recent_grant == 0 and total_events > 5:
        insights.append({
            "key": "grant_gap",
            "type": "info",
            "title": "No Active Grant Activity",
            "body": "No grant events recorded in the past 90 days.",
            "action": "Explore open calls in your research area via the Grant Hub.",
        })

    # AI power user
    if recent_ai >= 5:
        insights.append({
            "key": "ai_power_user",
            "type": "positive",
            "title": "High AI Usage",
            "body": f"You used Synaptiq AI tools {recent_ai} times this month.",
            "action": "Try the AI Collaboration Recommendation engine for new research partners.",
        })

    # Review activity
    if recent_review >= 1 and total_review >= 5:
        insights.append({
            "key": "review_active",
            "type": "positive",
            "title": "Active Peer Reviewer",
            "body": f"You have completed {total_review} peer reviews in total.",
            "action": "Accept pending reviewer invitations to reach the next milestone.",
        })

    # Verification nudge
    if recent_verify == 0 and total_events > 3:
        insights.append({
            "key": "verify_nudge",
            "type": "info",
            "title": "Boost Your Trust Score",
            "body": "No verification events recently. More verifications raise your Trust Score.",
            "action": "Visit the Trust & Verification Center to verify your identity and publications.",
        })

    # Peak month
    monthly = analytics.get("monthly_breakdown", [])
    if monthly:
        best = max(monthly, key=lambda m: m["total"])
        if best["total"] >= 3:
            insights.append({
                "key": "peak_month",
                "type": "positive",
                "title": "Most Active Month Identified",
                "body": f"{best['label']} was your most productive month with {best['total']} events.",
                "action": "Replicate this by scheduling dedicated research blocks each week.",
            })

    return insights[:6]
