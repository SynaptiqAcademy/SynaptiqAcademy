"""Academic Publishing Intelligence — Publishing dashboard builder (Phase XII)."""
from __future__ import annotations

from datetime import datetime, timezone

from .models import PublicationDashboard


async def build_publishing_dashboard(
    user_id: str,
    db=None,
) -> PublicationDashboard:
    """Aggregate publishing intelligence dashboard from database."""
    dashboard = PublicationDashboard(user_id=user_id)

    manuscripts = []
    if db is not None:
        try:
            cursor = db["manuscripts"].find(
                {"user_id": user_id},
                {"title": 1, "status": 1, "word_count": 1, "target_journal": 1,
                 "created_at": 1, "submission_date": 1},
            )
            manuscripts = await cursor.to_list(length=50)
        except Exception:
            pass

    dashboard.total_manuscripts = len(manuscripts)
    status_counts: dict[str, int] = {}
    for ms in manuscripts:
        s = str(ms.get("status", "draft")).lower()
        status_counts[s] = status_counts.get(s, 0) + 1

    dashboard.published_count         = status_counts.get("published", 0)
    dashboard.under_review_count      = status_counts.get("under_review", 0)
    dashboard.revision_required_count = status_counts.get("revision_required", 0)
    dashboard.draft_count             = status_counts.get("draft", 0)

    # Build manuscript list
    dashboard.manuscripts = [
        {
            "id": str(ms.get("_id", "")),
            "title": ms.get("title", "Untitled"),
            "status": ms.get("status", "draft"),
            "word_count": ms.get("word_count", 0),
            "target_journal": ms.get("target_journal", "Not set"),
        }
        for ms in manuscripts[:10]
    ]

    # Readiness summary (rule-based heuristic)
    dashboard.readiness_summary = [
        {
            "title": ms.get("title", "Untitled"),
            "estimated_readiness": (
                "Ready" if ms.get("word_count", 0) >= 3000 and ms.get("target_journal")
                else "Review needed"
            ),
        }
        for ms in manuscripts[:5]
    ]

    # Timeline projections
    now = datetime.now(timezone.utc)
    dashboard.impact_projections = [
        {"year": now.year + 1, "projected_citations": dashboard.published_count * 3},
        {"year": now.year + 2, "projected_citations": dashboard.published_count * 8},
        {"year": now.year + 3, "projected_citations": dashboard.published_count * 15},
    ]

    # Recommended actions
    actions: list[dict] = []
    if dashboard.revision_required_count > 0:
        actions.append({
            "priority": "high",
            "action": f"Respond to reviewer comments ({dashboard.revision_required_count} revision(s) pending)",
            "category": "revision",
        })
    if dashboard.draft_count > 2:
        actions.append({
            "priority": "medium",
            "action": f"You have {dashboard.draft_count} draft manuscripts — consider moving one to submission",
            "category": "submission",
        })
    if dashboard.total_manuscripts == 0:
        actions.append({
            "priority": "high",
            "action": "Start your first manuscript — use the Writing Coach to get started",
            "category": "onboarding",
        })

    dashboard.top_recommended_actions = actions[:5]
    return dashboard
