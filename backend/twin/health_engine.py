"""
Research Health engine.

Generates observable health indicators from platform activity.
ALL indicators:
  - Show exact methodology
  - Labeled as "platform activity indicator"
  - Never fabricated
  - Never presented as measures of research quality
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("twin.health")

_POLICY_NOTE = (
    "These are platform activity indicators only. "
    "They reflect your activity within Synaptiq and do not measure research quality or academic standing."
)


def _level(value: int, thresholds: tuple[int, int]) -> str:
    """Map a count to low/moderate/good using caller-supplied thresholds."""
    low, good = thresholds
    if value >= good:
        return "good"
    if value >= low:
        return "moderate"
    return "low"


async def compute_health(db, user_id: str, user: dict) -> dict:
    """
    Compute all research health indicators.
    Each indicator: value, level, methodology, evidence, source.
    """
    now = datetime.now(timezone.utc)
    indicators = []

    # ── 1. Active projects ──────────────────────────────────────────────────
    active_projects = await db.projects.count_documents({"user_id": user_id, "status": "active"})
    indicators.append({
        "id":          "active_projects",
        "label":       "Active Projects",
        "value":       active_projects,
        "unit":        "projects",
        "level":       _level(active_projects, (1, 3)),
        "description": f"{active_projects} active project(s) currently in Synaptiq",
        "methodology": "Count of projects with status='active' in Synaptiq projects DB",
        "source":      "Synaptiq projects DB",
    })

    # ── 2. Publication pipeline ──────────────────────────────────────────────
    in_progress_ms = await db.manuscripts.count_documents({
        "user_id": user_id,
        "status": {"$in": ["draft", "in_progress", "review"]},
    })
    indicators.append({
        "id":          "publication_pipeline",
        "label":       "Publication Pipeline",
        "value":       in_progress_ms,
        "unit":        "manuscripts",
        "level":       _level(in_progress_ms, (1, 2)),
        "description": f"{in_progress_ms} manuscript(s) currently in draft/review stage",
        "methodology": "Count of manuscripts with status in [draft, in_progress, review]",
        "source":      "Synaptiq manuscripts DB",
    })

    # ── 3. Funding activity ──────────────────────────────────────────────────
    grant_count = await db.grants.count_documents({"user_id": user_id})
    indicators.append({
        "id":          "funding_activity",
        "label":       "Funding Activity",
        "value":       grant_count,
        "unit":        "applications",
        "level":       _level(grant_count, (1, 3)),
        "description": f"{grant_count} grant application(s) recorded",
        "methodology": "Count of grant records in Synaptiq grants DB",
        "source":      "Synaptiq grants DB",
    })

    # ── 4. Collaboration diversity ──────────────────────────────────────────
    collab_count = await db.collaborations.count_documents({
        "$or": [{"requester_id": user_id}, {"recipient_id": user_id}],
        "status": "accepted",
    })
    indicators.append({
        "id":          "collaboration_diversity",
        "label":       "Collaboration Activity",
        "value":       collab_count,
        "unit":        "collaborations",
        "level":       _level(collab_count, (1, 4)),
        "description": f"{collab_count} accepted collaboration(s) on platform",
        "methodology": "Count of accepted collaborations in Synaptiq collaborations DB",
        "source":      "Synaptiq collaborations DB",
    })

    # ── 5. Profile completeness ──────────────────────────────────────────────
    profile_fields = [
        "name", "bio", "institution", "orcid", "research_interests",
        "academic_position", "country", "profile_picture",
    ]
    filled = sum(1 for f in profile_fields if user.get(f))
    pct = round((filled / len(profile_fields)) * 100)
    indicators.append({
        "id":          "profile_completeness",
        "label":       "Profile Completeness",
        "value":       pct,
        "unit":        "%",
        "level":       "good" if pct >= 80 else "moderate" if pct >= 50 else "low",
        "description": f"{filled}/{len(profile_fields)} profile fields completed ({pct}%)",
        "methodology": f"Checked {len(profile_fields)} profile fields: {', '.join(profile_fields)}",
        "source":      "Synaptiq user profile",
        "missing_fields": [f for f in profile_fields if not user.get(f)],
    })

    # ── 6. Knowledge graph coverage ─────────────────────────────────────────
    try:
        lkg_node_id = f"researcher:platform:{user_id}"
        lkg_edge_count = await db.lkg_edges.count_documents({
            "$or": [{"from_id": lkg_node_id}, {"to_id": lkg_node_id}]
        })
        indicators.append({
            "id":          "knowledge_coverage",
            "label":       "Knowledge Graph Coverage",
            "value":       lkg_edge_count,
            "unit":        "graph edges",
            "level":       _level(lkg_edge_count, (3, 15)),
            "description": f"{lkg_edge_count} edge(s) in the Living Knowledge Graph connecting this researcher",
            "methodology": "Count of edges in lkg_edges where from_id or to_id = researcher node",
            "source":      "Synaptiq Living Knowledge Graph",
        })
    except Exception:
        pass

    # ── 7. Research continuity (recent activity) ───────────────────────────
    cutoff = now - timedelta(days=90)
    recent_ms  = await db.manuscripts.count_documents({"user_id": user_id, "updated_at": {"$gte": cutoff}})
    recent_proj = await db.projects.count_documents({"user_id": user_id, "updated_at": {"$gte": cutoff}})
    recent_activity = recent_ms + recent_proj
    indicators.append({
        "id":          "research_continuity",
        "label":       "Recent Activity (90 days)",
        "value":       recent_activity,
        "unit":        "items updated",
        "level":       _level(recent_activity, (1, 3)),
        "description": f"{recent_ms} manuscript(s) and {recent_proj} project(s) updated in the last 90 days",
        "methodology": "Count of manuscripts and projects with updated_at >= 90 days ago",
        "source":      "Synaptiq manuscripts and projects DBs",
    })

    # ── 8. ORCID connection ────────────────────────────────────────────────
    has_orcid = bool(user.get("orcid"))
    indicators.append({
        "id":          "external_identity",
        "label":       "External Identity (ORCID)",
        "value":       1 if has_orcid else 0,
        "unit":        "connections",
        "level":       "good" if has_orcid else "low",
        "description": "ORCID connected" if has_orcid else "ORCID not connected — connect ORCID to import verified publication history",
        "methodology": "Checks presence of orcid field in user profile",
        "source":      "Synaptiq user profile",
    })

    # ── Overall score (simple average of indicator levels) ──────────────────
    level_score = {"good": 2, "moderate": 1, "low": 0}
    total_score = sum(level_score.get(ind.get("level", "low"), 0) for ind in indicators)
    max_score   = len(indicators) * 2
    overall_pct = round((total_score / max_score) * 100) if max_score > 0 else 0
    overall_level = "good" if overall_pct >= 67 else "moderate" if overall_pct >= 34 else "low"

    return {
        "indicators":    indicators,
        "overall":       {
            "level":   overall_level,
            "score":   f"{total_score}/{max_score}",
            "label":   "Platform Activity Score",
        },
        "computed_at":   now.isoformat(),
        "policy_note":   _POLICY_NOTE,
        "methodology":   "Each indicator is a direct count or completion check from Synaptiq platform data. No external benchmarks used.",
        "source":        "Synaptiq platform data only",
    }
