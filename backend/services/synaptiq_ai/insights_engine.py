"""Insights Engine — generate proactive insights from real platform data.

All insights are computed purely from DB queries — no LLM calls.
Returns up to 6 most relevant insights per user.
"""
from __future__ import annotations

import ast
import logging
import uuid
from datetime import datetime, timezone

from bson import ObjectId

logger = logging.getLogger("synaptiq.ai.insights_engine")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_research_areas(raw) -> list[str]:
    """Parse research_areas stored as a Python string list or actual list."""
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if x]
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if x]
        except (ValueError, SyntaxError):
            pass
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


async def generate_insights(user_id: str, db) -> list[dict]:
    """
    Generate proactive insights from REAL platform data.
    Does NOT call LLM — all insights computed from data queries.

    Returns list of insights (up to 6).
    """
    insights: list[dict] = []
    generated_at = _now_iso()

    # ── Fetch user profile for research areas ─────────────────────────────────
    user_research_areas: list[str] = []
    try:
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            user_research_areas = _parse_research_areas(user_doc.get("research_areas"))
    except Exception as exc:
        logger.warning("insights_engine: user fetch failed user=%s err=%s", user_id, exc)

    # ── GRANT insight ─────────────────────────────────────────────────────────
    try:
        now_iso = _now_iso()
        grant_query: dict = {"deadline": {"$gt": now_iso}}
        all_grants = await db.grants.find(grant_query).to_list(500)

        eligible_count = 0
        if user_research_areas:
            user_areas_lower = {a.lower() for a in user_research_areas}
            for grant in all_grants:
                grant_areas = _parse_research_areas(grant.get("research_areas"))
                grant_areas_lower = {a.lower() for a in grant_areas}
                if user_areas_lower & grant_areas_lower:
                    eligible_count += 1
        else:
            eligible_count = len(all_grants)

        if eligible_count > 0:
            insights.append({
                "id": str(uuid.uuid4()),
                "type": "grant",
                "message": f"You are eligible for {eligible_count} grant{'s' if eligible_count != 1 else ''} in your research areas",
                "detail": (
                    f"There are {eligible_count} active grants matching your research areas "
                    f"({', '.join(user_research_areas[:3]) or 'your field'}). "
                    "Review them to identify the best funding opportunities for your work."
                ),
                "cta_label": "Explore Grants",
                "cta_path": "/grants",
                "urgency": "high" if eligible_count >= 5 else "medium",
                "generated_at": generated_at,
            })
    except Exception as exc:
        logger.warning("insights_engine: grant insight failed user=%s err=%s", user_id, exc)

    # ── IMPACT insight ────────────────────────────────────────────────────────
    try:
        impact_doc = await db.research_impact.find_one({"user_id": user_id})
        if impact_doc:
            sis_total = impact_doc.get("sis_total") or 0
            sis_percentile = impact_doc.get("sis_percentile")
            h_index = impact_doc.get("h_index") or 0

            if sis_percentile is not None:
                percentile_str = f"in the top {100 - int(sis_percentile)}% of your field"
            else:
                # rough bucket
                if sis_total >= 7000:
                    percentile_str = "in the top 5% of your field"
                elif sis_total >= 5000:
                    percentile_str = "in the top 15% of your field"
                elif sis_total >= 3000:
                    percentile_str = "in the top 30% of your field"
                elif sis_total >= 1000:
                    percentile_str = "in the top 50% of your field"
                else:
                    percentile_str = "building your impact score"

            insights.append({
                "id": str(uuid.uuid4()),
                "type": "impact",
                "message": f"Your Synaptiq Impact Score is {sis_total}/10000 — {percentile_str}",
                "detail": (
                    f"Your current SIS is {sis_total}/10000 with an H-index of {h_index}. "
                    "Increase your score by publishing more, engaging in collaborations, and applying for grants."
                ),
                "cta_label": "View Impact Dashboard",
                "cta_path": "/research-impact",
                "urgency": "low" if sis_total >= 5000 else "medium",
                "generated_at": generated_at,
            })
    except Exception as exc:
        logger.warning("insights_engine: impact insight failed user=%s err=%s", user_id, exc)

    # ── COLLABORATION insight ─────────────────────────────────────────────────
    try:
        # Count researchers with recommendation score > 50 for this user
        rec_scores = await db.recommendation_scores.find(
            {"user_id": user_id, "score": {"$gt": 50}}
        ).to_list(500)
        match_count = len(rec_scores)

        if match_count == 0:
            # Fallback: count researchers in same research areas
            if user_research_areas:
                match_count = await db.users.count_documents({
                    "_id": {"$ne": ObjectId(user_id)},
                    "research_areas": {"$in": user_research_areas},
                })
            else:
                match_count = await db.users.count_documents({"_id": {"$ne": ObjectId(user_id)}})

        if match_count > 0:
            insights.append({
                "id": str(uuid.uuid4()),
                "type": "collaboration",
                "message": f"{match_count} researcher{'s' if match_count != 1 else ''} match your research profile",
                "detail": (
                    f"We found {match_count} researchers whose expertise aligns with yours "
                    f"({', '.join(user_research_areas[:3]) or 'your research area'}). "
                    "Explore potential collaborations to accelerate your work."
                ),
                "cta_label": "Find Collaborators",
                "cta_path": "/discover/researchers",
                "urgency": "medium",
                "generated_at": generated_at,
            })
    except Exception as exc:
        logger.warning("insights_engine: collaboration insight failed user=%s err=%s", user_id, exc)

    # ── REPUTATION insight ────────────────────────────────────────────────────
    try:
        rep_doc = await db.research_reputation.find_one({"user_id": user_id})
        if rep_doc:
            rep_score = rep_doc.get("overall_score") or 0
            rep_level = rep_doc.get("level") or "Newcomer"
            badges = rep_doc.get("badges") or []
            badge_count = len(badges)

            insights.append({
                "id": str(uuid.uuid4()),
                "type": "achievement",
                "message": f"Your reputation score is {rep_score} — earn more badges to advance",
                "detail": (
                    f"You are at level '{rep_level}' with {badge_count} badge{'s' if badge_count != 1 else ''}. "
                    "Publish manuscripts, collaborate with peers, and engage with the community to climb the ranks."
                ),
                "cta_label": "View Reputation",
                "cta_path": "/reputation",
                "urgency": "low",
                "generated_at": generated_at,
            })
    except Exception as exc:
        logger.warning("insights_engine: reputation insight failed user=%s err=%s", user_id, exc)

    # ── MANUSCRIPT / PUBLICATION insight ─────────────────────────────────────
    try:
        draft_count = await db.manuscripts.count_documents({
            "$or": [{"lead_author_id": user_id}, {"authors": user_id}],
            "status": "draft",
        })
        if draft_count > 0:
            insights.append({
                "id": str(uuid.uuid4()),
                "type": "publication",
                "message": f"You have {draft_count} manuscript{'s' if draft_count != 1 else ''} in draft. Submit {'them' if draft_count > 1 else 'it'} to reach more researchers.",
                "detail": (
                    f"You have {draft_count} draft manuscript{'s' if draft_count != 1 else ''}. "
                    "Finalizing and submitting your work increases your visibility, citation potential, and impact score."
                ),
                "cta_label": "Review Manuscripts",
                "cta_path": "/manuscripts",
                "urgency": "medium" if draft_count >= 2 else "low",
                "generated_at": generated_at,
            })
    except Exception as exc:
        logger.warning("insights_engine: manuscript insight failed user=%s err=%s", user_id, exc)

    # ── CITATION / H-INDEX insight ────────────────────────────────────────────
    try:
        impact_doc = await db.research_impact.find_one({"user_id": user_id})
        if impact_doc:
            h_index = impact_doc.get("h_index") or 0
            citation_count = impact_doc.get("citation_count") or 0

            # Also check openalex metrics if available
            openalex_metrics = impact_doc.get("openalex_metrics") or {}
            if openalex_metrics.get("cited_by_count"):
                citation_count = max(citation_count, openalex_metrics["cited_by_count"])

            if citation_count > 0 or h_index > 0:
                # Only generate if we have something meaningful to show
                next_h = h_index + 1
                insights.append({
                    "id": str(uuid.uuid4()),
                    "type": "impact",
                    "message": f"Your H-index is {h_index} with {citation_count} citations",
                    "detail": (
                        f"You currently have an H-index of {h_index} and {citation_count} total citations. "
                        f"To reach H-index {next_h}, you need {next_h} papers each cited at least {next_h} times. "
                        "Increase your citation count by publishing in high-visibility venues and collaborating widely."
                    ),
                    "cta_label": "Analyze Citations",
                    "cta_path": "/research-impact?tab=citations",
                    "urgency": "low",
                    "generated_at": generated_at,
                })
    except Exception as exc:
        logger.warning("insights_engine: citation insight failed user=%s err=%s", user_id, exc)

    # ── Deduplicate "impact" type (keep only the highest urgency one) ─────────
    # If we have both an SIS and H-index insight, keep the more compelling one
    impact_insights = [i for i in insights if i["type"] == "impact"]
    if len(impact_insights) > 1:
        # Keep first (SIS), remove duplicates
        seen_types: set[str] = set()
        deduped: list[dict] = []
        for insight in insights:
            key = insight["type"]
            if key == "impact" and key in seen_types:
                continue
            seen_types.add(key)
            deduped.append(insight)
        insights = deduped

    # Return up to 6 most relevant insights
    # Priority order: grant (high) > collaboration > publication > impact > achievement > citation
    priority_order = {"grant": 0, "collaboration": 1, "publication": 2, "impact": 3, "achievement": 4}
    insights.sort(key=lambda x: (
        priority_order.get(x["type"], 5),
        {"high": 0, "medium": 1, "low": 2}.get(x.get("urgency", "low"), 2),
    ))

    return insights[:6]
