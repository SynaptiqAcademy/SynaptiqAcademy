"""
Personalized recommendation engine powered by the Digital Research Twin.

Uses twin profile, working style, and activity to generate targeted recommendations.
Evidence policy: all recs trace to verified twin data. No fabricated stats.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("twin.recommendations")


def _conf(evidence: list) -> tuple[str, str]:
    total = sum(e.get("count", 1) for e in evidence if e.get("verified", True))
    if total >= 3:
        return "high", f"Based on {total} verified data points"
    if total >= 2:
        return "medium", "Based on 2 verified data points"
    if total >= 1:
        return "low", "Based on 1 verified data point"
    return "not_applicable", "Insufficient data"


async def generate_recommendations(db, user_id: str, twin: dict) -> list[dict]:
    """
    Generate ranked recommendations from twin intelligence.
    Each rec: type, title, why, evidence[], confidence, confidence_basis, data_quality.
    """
    recs = []
    now  = datetime.now(timezone.utc)
    profile = twin.get("profile", {})

    # ── 1. Journal recommendations from research domains ────────────────────
    domains = profile.get("research_domains", [])
    if domains:
        top_domain = domains[0].get("domain", "")
        # Look for journals in LKG with matching topics
        try:
            topic_id = f"topic:keyword:{top_domain.replace(' ', '_')}"
            journal_edges = await db.lkg_edges.find(
                {"to_id": topic_id, "type": {"$in": ["BELONGS_TO_TOPIC", "PUBLISHED_IN"]}},
                {"from_id": 1}
            ).limit(5).to_list(5)
            j_ids = [e["from_id"] for e in journal_edges if e["from_id"].startswith("journal:")]
            if j_ids:
                j_nodes = await db.lkg_nodes.find({"node_id": {"$in": j_ids}}, {"label": 1, "_id": 0}).to_list(3)
                for jn in j_nodes[:2]:
                    ev = [{"source": "Synaptiq LKG", "detail": f"Journal connected to your top research domain: {top_domain}", "count": 1, "verified": True}]
                    conf, basis = _conf(ev)
                    recs.append({
                        "type":             "journal",
                        "title":            f"Consider: {jn.get('label', 'Unknown journal')}",
                        "why":              f"This journal is connected to your primary research domain '{top_domain}' in the Living Knowledge Graph.",
                        "evidence":         ev,
                        "confidence":       conf,
                        "confidence_basis": basis,
                        "data_quality":     "partial",
                    })
        except Exception:
            pass

    # ── 2. Stale manuscripts ────────────────────────────────────────────────
    cutoff_90 = now - timedelta(days=90)
    stale_ms  = await db.manuscripts.find_one({
        "user_id": user_id,
        "status":  {"$in": ["draft", "in_progress"]},
        "updated_at": {"$lt": cutoff_90},
    }, {"title": 1, "updated_at": 1})
    if stale_ms:
        days_stale = (now - stale_ms["updated_at"].replace(tzinfo=timezone.utc)).days if stale_ms.get("updated_at") else "?"
        ev = [{"source": "Synaptiq manuscripts DB", "detail": f"Manuscript last edited {days_stale} days ago", "count": 1, "verified": True}]
        conf, basis = _conf(ev)
        recs.append({
            "type":             "writing",
            "title":            f"Resume manuscript: {(stale_ms.get('title') or 'Untitled')[:60]}",
            "why":              f"This manuscript has not been edited for {days_stale} days. Platform database shows it is in draft/in-progress status.",
            "evidence":         ev,
            "confidence":       conf,
            "confidence_basis": basis,
            "data_quality":     "sufficient",
        })

    # ── 3. Collaboration opportunities from working style ──────────────────
    working_style = twin.get("working_style", {})
    collab_obs = next((o for o in working_style.get("observations", []) if "collaborat" in o.get("pattern", "").lower()), None)
    if not collab_obs:
        # User hasn't collaborated much — suggest exploring
        collab_count = twin.get("activity_summary", {}).get("collaborations_count", 0)
        if collab_count == 0:
            ev = [{"source": "Synaptiq collaborations DB", "detail": "No accepted collaborations found", "count": 1, "verified": True}]
            conf, basis = _conf(ev)
            recs.append({
                "type":             "collaboration",
                "title":            "Explore research collaboration opportunities",
                "why":              "Your Twin shows no accepted collaborations on Synaptiq. The Collaboration Discovery section may connect you with researchers in your domain.",
                "evidence":         ev,
                "confidence":       conf,
                "confidence_basis": basis,
                "data_quality":     "sufficient",
            })

    # ── 4. Grant opportunities with upcoming deadlines ───────────────────────
    in_7_days = now + timedelta(days=7)
    upcoming_grant = await db.grants.find_one({
        "user_id": user_id,
        "deadline": {"$gte": now, "$lte": in_7_days},
    }, {"title": 1, "deadline": 1})
    if upcoming_grant:
        ev = [{"source": "Synaptiq grants DB", "detail": f"Grant deadline within 7 days", "count": 1, "verified": True}]
        conf, basis = _conf(ev)
        recs.append({
            "type":             "funding",
            "title":            f"Urgent: grant deadline approaching — {(upcoming_grant.get('title') or 'Untitled')[:60]}",
            "why":              "Platform database shows a grant with a deadline within the next 7 days.",
            "evidence":         ev,
            "confidence":       conf,
            "confidence_basis": basis,
            "data_quality":     "sufficient",
            "urgent":           True,
        })

    # ── 5. Career-based suggestions ──────────────────────────────────────────
    career_stage = profile.get("career_stage", "unknown")
    if career_stage == "phd":
        recs.append({
            "type":             "career",
            "title":            "Set a PhD milestone goal",
            "why":              "Your profile indicates PhD student career stage. Setting milestone goals helps track progress.",
            "evidence":         [{"source": "User profile", "detail": "Career stage: PhD student", "count": 1, "verified": True}],
            "confidence":       "low",
            "confidence_basis": "Based on 1 verified data point (profile field)",
            "data_quality":     "partial",
        })
    elif career_stage == "assistant_professor":
        recs.append({
            "type":             "career",
            "title":            "Track promotion-relevant activity",
            "why":              "Your profile indicates assistant professor stage. Tracking publications, grants, and service can support promotion documentation.",
            "evidence":         [{"source": "User profile", "detail": "Career stage: Assistant Professor", "count": 1, "verified": True}],
            "confidence":       "low",
            "confidence_basis": "Based on 1 verified data point (profile field)",
            "data_quality":     "partial",
        })

    # ── 6. ORCID connection ──────────────────────────────────────────────────
    orcid_pubs = twin.get("activity_summary", {}).get("orcid_publications", 0)
    if orcid_pubs == 0 and not twin.get("activity_summary", {}).get("orcid_publications"):
        recs.append({
            "type":             "identity",
            "title":            "Connect your ORCID account",
            "why":              "No ORCID publications found in your Twin. Connecting ORCID imports your verified publication history and improves all Twin recommendations.",
            "evidence":         [{"source": "ORCID check", "detail": "No ORCID-linked publications in twin", "count": 1, "verified": True}],
            "confidence":       "medium",
            "confidence_basis": "Based on absence of verified ORCID data",
            "data_quality":     "partial",
        })

    # Sort: urgent first, then by recommendation type priority
    priority = {"funding": 0, "writing": 1, "journal": 2, "collaboration": 3, "identity": 4, "career": 5}
    recs.sort(key=lambda r: (0 if r.get("urgent") else 1, priority.get(r.get("type", "other"), 9)))

    return recs[:8]


async def get_ai_context(db, user_id: str, twin: dict) -> dict:
    """
    Returns a compact Twin context dict for AI agents to use as context.
    Agents read this — they never write back to it.
    """
    profile = twin.get("profile", {})
    ws      = twin.get("working_style", {})

    return {
        "user_id":        user_id,
        "career_stage":   profile.get("career_stage", "unknown"),
        "research_domains": [d["domain"] for d in profile.get("research_domains", [])[:5]],
        "methodologies":  [m["method"] for m in profile.get("methodological_expertise", [])[:3]],
        "working_patterns": [o["pattern"] for o in ws.get("observations", [])[:3]],
        "activity": {
            "manuscripts":    twin.get("activity_summary", {}).get("manuscripts_count", 0),
            "collaborations": twin.get("activity_summary", {}).get("collaborations_count", 0),
            "orcid_pubs":     twin.get("activity_summary", {}).get("orcid_publications", 0),
        },
        "personalization_enabled": twin.get("privacy", {}).get("personalization_enabled", True),
        "source":         "Digital Research Twin — verified platform data only",
    }
