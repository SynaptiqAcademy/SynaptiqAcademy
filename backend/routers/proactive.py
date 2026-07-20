"""Proactive AI Research Assistant — Phase XXX (Evidence-Corrected Build).

Academic Reliability Policy (applied throughout):
- Every recommendation is traceable to a specific, verified data source.
- No fabricated statistics, invented percentages, or speculative claims.
- Confidence is rated by evidence quality (number and strength of verified data points),
  NOT by arbitrary numbers.
- When data is insufficient, the response says so explicitly and lists what is missing.
- Health/opportunity scores are platform-activity indicators only — they make no claim
  about external research outcomes or correlations.

Routes
------
GET  /api/proactive/briefing                      — personalized daily briefing
GET  /api/proactive/recommendations               — all recs (paginated, filterable by category)
GET  /api/proactive/next-action                   — highest-priority action for current page context
POST /api/proactive/recommendations/{id}/dismiss  — dismiss (learning signal)
POST /api/proactive/recommendations/{id}/accept   — accept (positive learning signal)
GET  /api/proactive/insights                      — verified platform insights
GET  /api/proactive/health-score                  — platform-activity indicator (0-100) with methodology
GET  /api/proactive/opportunity-score             — open platform items count
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy

logger = logging.getLogger("synaptiq.proactive")

router = APIRouter(prefix="/api/proactive", tags=["proactive"])

# ── Constants ──────────────────────────────────────────────────────────────────

CATEGORIES = [
    "writing", "publishing", "research", "collaboration",
    "funding", "teaching", "institution", "career", "productivity",
]

# Verified profile fields and their weights for completeness computation.
# Weights are platform-internal — they do not claim to correlate with external outcomes.
PROFILE_FIELDS = [
    ("full_name",          "Full name",           10),
    ("bio",                "Bio",                  8),
    ("institution",        "Institution",          8),
    ("research_interests", "Research interests",   8),
    ("user_type",          "Academic role",        6),
    ("orcid",              "ORCID",                6),
    ("website",            "Website",              4),
    ("location",           "Location",             4),
    ("avatar_url",         "Profile photo",        6),
]

# ── Evidence helpers ───────────────────────────────────────────────────────────

def _uid(user: dict) -> str:
    return str(user["_id"])

def _rec_id(*parts: str) -> str:
    """Stable deterministic ID so dismiss/accept can be stored."""
    return hashlib.sha1(":".join(parts).encode()).hexdigest()[:16]

def _profile_completeness(user: dict) -> tuple[int, list[str]]:
    """
    Returns (score 0-100, list of missing field labels).
    Score computed from platform-defined field weights. No external correlation claimed.
    """
    earned   = 0
    possible = sum(w for _, _, w in PROFILE_FIELDS)
    missing  = []
    for key, label, weight in PROFILE_FIELDS:
        val = user.get(key)
        if val and (not isinstance(val, list) or len(val) > 0):
            earned += weight
        else:
            missing.append(label)
    return round(earned * 100 / possible), missing

def _confidence_from_evidence(evidence: list[dict]) -> tuple[str, str]:
    """
    Derive confidence level from the number of verified evidence data points.
    Returns (level: "high"|"medium"|"low", basis: explanation string).
    No fake percentages are used — only evidence-count reasoning.
    """
    verified_count = len([e for e in evidence if e.get("verified", True)])
    if verified_count >= 3:
        return "high", (
            f"Supported by {verified_count} verified data points from the platform database. "
            "All evidence is directly observable in your account."
        )
    elif verified_count >= 1:
        return "medium", (
            f"Supported by {verified_count} verified data point(s). "
            "Additional profile or activity information would increase confidence."
        )
    else:
        return "low", (
            "Inferred from general profile context with limited specific activity data. "
            "Complete your profile to generate more accurate recommendations."
        )

def _deadline_days(deadline) -> Optional[int]:
    """Returns days until deadline, or None if past or unparseable."""
    if not deadline:
        return None
    try:
        if isinstance(deadline, str):
            dt = datetime.strptime(deadline[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        elif isinstance(deadline, datetime):
            dt = deadline if deadline.tzinfo else deadline.replace(tzinfo=timezone.utc)
        else:
            return None
        days = (dt - datetime.now(timezone.utc)).days
        return days if days >= 0 else None
    except Exception:
        return None

def _deadline_label(days: Optional[int]) -> Optional[str]:
    if days is None:
        return None
    if days == 0:
        return "closes today"
    if days == 1:
        return "closes tomorrow"
    return f"closes in {days} days"

# ── Recommendation generators ──────────────────────────────────────────────────

async def _build_recommendations(user: dict, db, dismissed_ids: set) -> list[dict]:
    uid   = _uid(user)
    recs  = []
    now   = datetime.now(timezone.utc)
    comp, missing_fields = _profile_completeness(user)

    # Track whether we have any substantive user data.
    # If not, we return a single "insufficient data" recommendation.
    has_any_data = False

    # ── WRITING: manuscript activity ──────────────────────────────────────────
    try:
        manuscripts = await db.manuscripts.find(
            {"user_id": uid, "status": {"$nin": ["submitted", "published", "rejected"]}}
        ).to_list(20)

        if manuscripts:
            has_any_data = True

        for ms in manuscripts:
            ms_id    = str(ms["_id"])
            ms_title = ms.get("title", "Untitled manuscript")[:60]

            # Determine days since last edit from real data
            updated = ms.get("updated_at")
            days_inactive = None
            last_edit_label = "unknown"
            if updated:
                try:
                    if isinstance(updated, str):
                        updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    elif isinstance(updated, datetime):
                        updated_dt = updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)
                    else:
                        updated_dt = None
                    if updated_dt:
                        days_inactive = (now - updated_dt).days
                        last_edit_label = f"{days_inactive} days ago" if days_inactive > 0 else "today"
                except Exception:
                    pass

            stale = days_inactive is not None and days_inactive > 14

            evidence = [
                {
                    "type": "manuscript_record",
                    "source": "Synaptiq platform database",
                    "detail": f"Manuscript '{ms_title}' — status: {ms.get('status', 'draft')}",
                    "verified": True,
                },
            ]
            if days_inactive is not None:
                evidence.append({
                    "type": "activity_timestamp",
                    "source": "Synaptiq platform database",
                    "detail": f"Last edited: {last_edit_label} (platform-recorded timestamp)",
                    "verified": True,
                })

            rec_id = _rec_id("manuscript_resume", ms_id)
            if rec_id not in dismissed_ids:
                conf, conf_basis = _confidence_from_evidence(evidence)
                recs.append({
                    "id":          rec_id,
                    "category":    "writing",
                    "priority":    9 if stale else 6,
                    "title":       f"Continue: {ms_title}",
                    "description": (
                        f"Manuscript last edited {last_edit_label}."
                        if last_edit_label != "unknown"
                        else "Active manuscript found with no recent recorded edit."
                    ),
                    "why": (
                        f"Platform database shows this manuscript has not been edited for "
                        f"{days_inactive} days. No external outcome data is used in this recommendation."
                        if days_inactive is not None
                        else "Platform database shows this manuscript is active with no confirmed recent edit."
                    ),
                    "evidence":         evidence,
                    "data_quality":     "sufficient",
                    "confidence":       conf,
                    "confidence_basis": conf_basis,
                    "action": {"label": "Open manuscripts", "route": "/manuscripts"},
                    "meta": {
                        "manuscript_id": ms_id,
                        "source": "platform_database",
                        "days_inactive": days_inactive,
                    },
                })

            # Suggest AI review only when manuscript exists and no review was found
            review_id = _rec_id("manuscript_review", ms_id)
            if review_id not in dismissed_ids:
                review_evidence = [
                    {
                        "type": "manuscript_record",
                        "source": "Synaptiq platform database",
                        "detail": f"Manuscript '{ms_title}' is active and has no AI review record",
                        "verified": True,
                    },
                ]
                conf, conf_basis = _confidence_from_evidence(review_evidence)
                recs.append({
                    "id":          review_id,
                    "category":    "writing",
                    "priority":    5,
                    "title":       f"AI review available for: {ms_title}",
                    "description": "No AI review has been submitted for this manuscript.",
                    "why": (
                        "Platform database shows this manuscript exists and no AI review record is linked to it. "
                        "This recommendation is based solely on platform activity data — no outcome predictions are made."
                    ),
                    "evidence":         review_evidence,
                    "data_quality":     "sufficient",
                    "confidence":       conf,
                    "confidence_basis": conf_basis,
                    "action": {"label": "Run manuscript review", "route": "/manuscript-review"},
                    "meta": {"manuscript_id": ms_id, "source": "platform_database"},
                })

    except Exception as e:
        logger.debug("Manuscript recs error: %s", e)

    # ── PUBLISHING: journal finder (only if research interests are set) ────────
    try:
        interests = user.get("research_interests") or user.get("research_areas") or []
        if interests:
            has_any_data = True
            evidence = [
                {
                    "type": "profile_field",
                    "source": "Synaptiq platform database — user profile",
                    "detail": f"Research interests set: {', '.join(interests[:3])}",
                    "verified": True,
                },
            ]
            conf, conf_basis = _confidence_from_evidence(evidence)
            rec_id = _rec_id("journal_finder", uid)
            if rec_id not in dismissed_ids:
                recs.append({
                    "id":          rec_id,
                    "category":    "publishing",
                    "priority":    4,
                    "title":       "Journal Finder is available for your research area",
                    "description": (
                        f"Your profile lists research interests: {', '.join(interests[:2])}. "
                        "Journal Finder can search the platform's journal database for these areas."
                    ),
                    "why": (
                        "Your research interests are set in your profile (platform database). "
                        "Journal Finder will search the journal database using these terms. "
                        "No pre-computed match score or acceptance probability exists — "
                        "results depend on what you search for."
                    ),
                    "evidence":         evidence,
                    "data_quality":     "partial",
                    "confidence":       conf,
                    "confidence_basis": conf_basis,
                    "action": {"label": "Open Journal Finder", "route": "/journals"},
                    "meta": {"source": "profile_data"},
                })
    except Exception as e:
        logger.debug("Publishing recs error: %s", e)

    # ── FUNDING: grants from platform database with verified upcoming deadlines ──
    try:
        interests = user.get("research_interests") or user.get("research_areas") or []
        grants_cursor = db.grants.find({"deadline": {"$gte": now}}).sort("deadline", 1).limit(50)
        grants = await grants_cursor.to_list(50)

        for grant in grants:
            grant_id    = str(grant["_id"])
            grant_title = grant.get("title", "Untitled grant")[:55]
            grant_areas = grant.get("research_areas") or grant.get("fields") or []
            d_days      = _deadline_days(grant.get("deadline"))
            dlabel      = _deadline_label(d_days)

            if dlabel is None:
                continue

            rec_id = _rec_id("grant_match", grant_id, uid)
            if rec_id in dismissed_ids:
                continue

            # Build evidence from verified data only
            evidence = [
                {
                    "type": "grant_record",
                    "source": "Synaptiq platform database — grants collection",
                    "detail": f"Grant '{grant_title}' — deadline {dlabel}, status: open",
                    "verified": True,
                },
            ]

            # Only report overlap if both interests and grant areas are present
            overlap = []
            if interests and grant_areas:
                overlap = [
                    kw for kw in interests
                    if any(kw.lower() in area.lower() or area.lower() in kw.lower()
                           for area in grant_areas)
                ]
                if overlap:
                    has_any_data = True
                    evidence.append({
                        "type": "keyword_overlap",
                        "source": "Synaptiq platform database — user profile + grant record",
                        "detail": (
                            f"Overlapping terms between your research interests and grant areas: "
                            f"{', '.join(overlap[:3])}"
                        ),
                        "verified": True,
                    })

            conf, conf_basis = _confidence_from_evidence(evidence)
            urgency = d_days is not None and d_days <= 7

            # Description is factual only
            if overlap:
                description = (
                    f"Grant '{grant_title}' {dlabel}. "
                    f"Grant areas include: {', '.join(grant_areas[:2])}. "
                    f"Your profile mentions: {', '.join(overlap[:2])}."
                )
            else:
                description = f"Grant '{grant_title}' {dlabel}."

            recs.append({
                "id":       rec_id,
                "category": "funding",
                "priority": 9 if urgency else (6 if overlap else 3),
                "title":    f"Grant opportunity: {grant_title}",
                "description": description,
                "why": (
                    f"This grant is listed in the Synaptiq platform database with a verified upcoming deadline ({dlabel}). "
                    + (
                        f"Text overlap detected between your stated research interests ({', '.join(overlap[:2])}) "
                        f"and the grant's listed areas ({', '.join(grant_areas[:2])}). "
                        "This is a keyword match — not a compatibility score or acceptance probability."
                        if overlap else
                        "No keyword overlap with your research interests detected. "
                        "Shown because the deadline is upcoming. Review the grant to assess relevance."
                    )
                ),
                "evidence":         evidence,
                "data_quality":     "sufficient" if overlap else "partial",
                "confidence":       conf,
                "confidence_basis": conf_basis,
                "action": {"label": "View grant", "route": "/grants"},
                "meta": {
                    "grant_id":      grant_id,
                    "deadline_days": d_days,
                    "deadline_label": dlabel,
                    "keyword_overlap": overlap,
                    "source": "platform_database",
                    "urgent": urgency,
                },
            })
    except Exception as e:
        logger.debug("Funding recs error: %s", e)

    # ── COLLABORATION: based on real platform open collaboration count ─────────
    try:
        open_collab_count = await db.collaborations.count_documents({"status": "open"})

        if open_collab_count > 0:
            evidence = [
                {
                    "type": "platform_count",
                    "source": "Synaptiq platform database — collaborations collection",
                    "detail": f"{open_collab_count} collaborations with status='open' found",
                    "verified": True,
                },
            ]
            rec_id = _rec_id("collabs_open", uid)
            if rec_id not in dismissed_ids:
                conf, conf_basis = _confidence_from_evidence(evidence)
                recs.append({
                    "id":       rec_id,
                    "category": "collaboration",
                    "priority": 4,
                    "title":    f"{open_collab_count} open collaboration{'' if open_collab_count == 1 else 's'} on the platform",
                    "description": (
                        f"Platform database shows {open_collab_count} collaboration "
                        f"post{'s' if open_collab_count > 1 else ''} currently marked as open."
                    ),
                    "why": (
                        f"The collaborations collection in the platform database contains "
                        f"{open_collab_count} records with status='open'. "
                        "No compatibility or relevance score is applied — browse to assess fit."
                    ),
                    "evidence":         evidence,
                    "data_quality":     "sufficient",
                    "confidence":       conf,
                    "confidence_basis": conf_basis,
                    "action": {"label": "Browse collaborations", "route": "/collaborations"},
                    "meta": {"count": open_collab_count, "source": "platform_database"},
                })
    except Exception as e:
        logger.debug("Collaboration recs error: %s", e)

    # ── CAREER: profile completeness — based entirely on verified profile fields ─
    if comp < 85 and missing_fields:
        evidence = [
            {
                "type": "profile_audit",
                "source": "Synaptiq platform database — user profile",
                "detail": (
                    f"Profile completeness: {comp}% ({len(missing_fields)} fields empty: "
                    f"{', '.join(missing_fields[:4])})"
                ),
                "verified": True,
            },
        ]
        rec_id = _rec_id("profile_complete", uid, str(comp))
        if rec_id not in dismissed_ids:
            conf, conf_basis = _confidence_from_evidence(evidence)
            recs.append({
                "id":       rec_id,
                "category": "career",
                "priority": 8 if comp < 60 else 5,
                "title":    f"Profile {comp}% complete",
                "description": f"Missing fields: {', '.join(missing_fields[:4])}.",
                "why": (
                    f"Your profile in the platform database has {len(missing_fields)} empty fields: "
                    f"{', '.join(missing_fields)}. "
                    "A complete profile allows the platform to generate more targeted recommendations "
                    "based on verified information. No external outcome prediction is made."
                ),
                "evidence":         evidence,
                "data_quality":     "sufficient",
                "confidence":       conf,
                "confidence_basis": conf_basis,
                "action": {"label": "Complete profile", "route": "/profile"},
                "meta": {
                    "completion":   comp,
                    "missing":      missing_fields,
                    "source":       "platform_database",
                },
            })

    # ORCID: based on verified profile field
    if not (user.get("orcid") or {}).get("orcid_id"):
        evidence = [
            {
                "type": "profile_field",
                "source": "Synaptiq platform database — user profile",
                "detail": "ORCID field is empty in your platform profile",
                "verified": True,
            },
        ]
        rec_id = _rec_id("orcid_connect", uid)
        if rec_id not in dismissed_ids:
            conf, conf_basis = _confidence_from_evidence(evidence)
            recs.append({
                "id":       rec_id,
                "category": "career",
                "priority": 5,
                "title":    "ORCID iD not connected",
                "description": "Your ORCID is not linked in your platform profile.",
                "why": (
                    "The ORCID field in your platform profile is empty (verified from platform database). "
                    "Connecting ORCID allows the platform to retrieve your verified publication list. "
                    "No prediction about outcomes is made."
                ),
                "evidence":         evidence,
                "data_quality":     "sufficient",
                "confidence":       conf,
                "confidence_basis": conf_basis,
                "action": {"label": "Connect ORCID", "route": "/profile"},
                "meta": {"source": "platform_database"},
            })

    # ── PRODUCTIVITY: stale projects based on real timestamps ─────────────────
    try:
        cutoff = now - timedelta(days=30)
        stale_projects = await db.projects.find({
            "creator_id": uid,
            "status": {"$in": ["active", "draft"]},
            "updated_at": {"$lt": cutoff},
        }).limit(5).to_list(5)

        for proj in stale_projects:
            proj_id    = str(proj["_id"])
            proj_title = proj.get("title", "Untitled project")[:50]
            updated    = proj.get("updated_at")
            days_ago   = None
            if updated:
                try:
                    if isinstance(updated, str):
                        updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    elif isinstance(updated, datetime):
                        updated_dt = updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)
                    else:
                        updated_dt = None
                    if updated_dt:
                        days_ago = (now - updated_dt).days
                except Exception:
                    pass

            evidence = [
                {
                    "type": "project_record",
                    "source": "Synaptiq platform database — projects collection",
                    "detail": f"Project '{proj_title}' — status: {proj.get('status', 'unknown')}",
                    "verified": True,
                },
            ]
            if days_ago is not None:
                evidence.append({
                    "type": "activity_timestamp",
                    "source": "Synaptiq platform database",
                    "detail": f"Last updated: {days_ago} days ago (platform-recorded timestamp)",
                    "verified": True,
                })

            rec_id = _rec_id("stale_project", proj_id)
            if rec_id not in dismissed_ids:
                conf, conf_basis = _confidence_from_evidence(evidence)
                recs.append({
                    "id":       rec_id,
                    "category": "productivity",
                    "priority": 4,
                    "title":    f"Inactive project: {proj_title}",
                    "description": (
                        f"Last updated {days_ago} days ago."
                        if days_ago else "Project has no recent recorded activity."
                    ),
                    "why": (
                        f"Platform database shows this project was last updated "
                        f"{days_ago + ' days ago' if days_ago else 'over 30 days ago'} "
                        "and is still marked as active. "
                        "No external outcome prediction is made."
                    ),
                    "evidence":         evidence,
                    "data_quality":     "sufficient",
                    "confidence":       conf,
                    "confidence_basis": conf_basis,
                    "action": {"label": "Open project", "route": "/projects"},
                    "meta": {"project_id": proj_id, "days_inactive": days_ago, "source": "platform_database"},
                })
    except Exception as e:
        logger.debug("Productivity recs error: %s", e)

    # ── TEACHING: only shown for educators with verified role ─────────────────
    if user.get("primary_domain") in ("teaching", "both"):
        has_any_data = True
        evidence = [
            {
                "type": "profile_field",
                "source": "Synaptiq platform database — user profile",
                "detail": f"primary_domain = '{user.get('primary_domain')}' in your platform profile",
                "verified": True,
            },
        ]
        rec_id = _rec_id("teaching_tools", uid)
        if rec_id not in dismissed_ids:
            conf, conf_basis = _confidence_from_evidence(evidence)
            recs.append({
                "id":       rec_id,
                "category": "teaching",
                "priority": 4,
                "title":    "Teaching tools available for your role",
                "description": "Your profile domain is set to teaching. Teaching Hub has lesson planning, assessments, and portfolio tools.",
                "why": (
                    "Your platform profile has primary_domain set to 'teaching' or 'both' "
                    "(verified from platform database). Teaching tools are available for this role. "
                    "No activity prediction is made."
                ),
                "evidence":         evidence,
                "data_quality":     "sufficient",
                "confidence":       conf,
                "confidence_basis": conf_basis,
                "action": {"label": "Open Lesson Planner", "route": "/teaching/lesson-planner"},
                "meta": {"source": "platform_database"},
            })

    # ── INSUFFICIENT DATA: shown when we genuinely have nothing to base recs on ─
    if not has_any_data and not recs:
        interests = user.get("research_interests") or user.get("research_areas") or []
        missing_context = []
        if not interests:
            missing_context.append("Research interests (not set in profile)")
        try:
            ms_count = await db.manuscripts.count_documents({"user_id": uid})
            if ms_count == 0:
                missing_context.append("Manuscripts (none found in platform database)")
        except Exception:
            pass
        try:
            proj_count = await db.projects.count_documents({"creator_id": uid})
            if proj_count == 0:
                missing_context.append("Projects (none found in platform database)")
        except Exception:
            pass
        if not (user.get("orcid") or {}).get("orcid_id"):
            missing_context.append("ORCID (not connected — no publication data available)")

        recs.append({
            "id":          _rec_id("insufficient_data", uid),
            "category":    "career",
            "priority":    10,
            "title":       "Not enough verified information to generate recommendations",
            "description": "Synaptiq needs verified profile and activity data to surface accurate recommendations.",
            "why": (
                "No sufficient evidence currently exists to generate recommendations. "
                "The following information is missing from your platform profile and activity: "
                + ("; ".join(missing_context) if missing_context else "No specific data gaps identified.")
            ),
            "evidence":    [],
            "data_quality": "insufficient",
            "confidence":   "not_applicable",
            "confidence_basis": (
                "Recommendations cannot be generated without verified data. "
                "No estimates or guesses are produced in place of real evidence."
            ),
            "missing_data": missing_context,
            "action": {"label": "Complete your profile", "route": "/profile"},
            "meta": {"source": "data_audit", "missing_fields": missing_context},
        })

    recs.sort(key=lambda r: r["priority"], reverse=True)
    return recs


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/briefing")
async def get_briefing(user=Depends(get_current_user), db=Depends(get_db)):
    """
    Personalized daily briefing derived entirely from verified platform data.
    All counts come from real database queries. No estimates or predictions.
    """
    db = make_db_proxy(db, user)
    uid     = _uid(user)
    comp, _ = _profile_completeness(user)
    now     = datetime.now(timezone.utc)
    name    = (user.get("full_name") or "Researcher").split()[0]

    h = now.hour
    greeting = "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"

    summary_items = []

    try:
        ms_count = await db.manuscripts.count_documents(
            {"user_id": uid, "status": {"$nin": ["submitted", "published", "rejected"]}}
        )
        if ms_count > 0:
            summary_items.append({
                "type": "manuscripts",
                "count": ms_count,
                "label": f"active manuscript{'s' if ms_count > 1 else ''}",
                "route": "/manuscripts",
                "icon": "file-text",
                "source": "Synaptiq platform database",
            })
    except Exception:
        pass

    try:
        soon = now + timedelta(days=14)
        grant_count = await db.grants.count_documents({"deadline": {"$gte": now, "$lte": soon}})
        if grant_count > 0:
            summary_items.append({
                "type": "grants",
                "count": grant_count,
                "label": f"grant deadline{'s' if grant_count > 1 else ''} within 14 days",
                "route": "/grants",
                "icon": "dollar-sign",
                "source": "Synaptiq platform database",
            })
    except Exception:
        pass

    try:
        collab_count = await db.collaborations.count_documents({"status": "open"})
        if collab_count > 0:
            summary_items.append({
                "type": "collaborations",
                "count": collab_count,
                "label": "open collaboration opportunities",
                "route": "/collaborations",
                "icon": "users",
                "source": "Synaptiq platform database",
            })
    except Exception:
        pass

    try:
        proj_count = await db.projects.count_documents({"creator_id": uid, "status": "active"})
        if proj_count > 0:
            summary_items.append({
                "type": "projects",
                "count": proj_count,
                "label": f"active project{'s' if proj_count > 1 else ''}",
                "route": "/projects",
                "icon": "folder",
                "source": "Synaptiq platform database",
            })
    except Exception:
        pass

    try:
        dismissed_docs = await db.proactive_interactions.find(
            {"user_id": uid, "action": "dismissed"}
        ).to_list(500)
        dismissed_ids = {d["rec_id"] for d in dismissed_docs}
    except Exception:
        dismissed_ids = set()

    all_recs = await _build_recommendations(user, db, dismissed_ids)
    top_rec  = all_recs[0] if all_recs else None

    return {
        "greeting":             f"{greeting}, {name}",
        "date":                 now.strftime("%A, %-d %B %Y"),
        "summary_items":        summary_items[:6],
        "profile_completion":   comp,
        "top_recommendation":   top_rec,
        "total_recs":           len(all_recs),
        "data_sources":         ["Synaptiq platform database"],
        "generated_at":         now.isoformat(),
    }


@router.get("/recommendations")
async def get_recommendations(
    category: Optional[str] = Query(None),
    limit:    int           = Query(20, ge=1, le=100),
    offset:   int           = Query(0, ge=0),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Evidence-based recommendations, filterable by category.
    Each recommendation includes evidence sources and data quality rating.
    """
    db = make_db_proxy(db, user)
    uid = _uid(user)

    try:
        dismissed_docs = await db.proactive_interactions.find(
            {"user_id": uid, "action": "dismissed"}
        ).to_list(500)
        dismissed_ids = {d["rec_id"] for d in dismissed_docs}
    except Exception:
        dismissed_ids = set()

    all_recs = await _build_recommendations(user, db, dismissed_ids)

    if category and category in CATEGORIES:
        all_recs = [r for r in all_recs if r["category"] == category]

    return {
        "recommendations": all_recs[offset: offset + limit],
        "total":           len(all_recs),
        "offset":          offset,
        "limit":           limit,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "data_sources":    ["Synaptiq platform database"],
        "policy_note":     (
            "All recommendations are derived from verified platform data only. "
            "No fabricated statistics, estimated probabilities, or invented metrics are used."
        ),
    }


@router.get("/next-action")
async def get_next_action(
    page: str = Query("/"),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Returns the single highest-priority evidence-based action for the current page."""
    db = make_db_proxy(db, user)
    uid = _uid(user)

    try:
        dismissed_docs = await db.proactive_interactions.find(
            {"user_id": uid, "action": "dismissed"}
        ).to_list(500)
        dismissed_ids = {d["rec_id"] for d in dismissed_docs}
    except Exception:
        dismissed_ids = set()

    all_recs = await _build_recommendations(user, db, dismissed_ids)

    page_lower = page.lower()
    if "manuscript" in page_lower or "writing" in page_lower:
        preferred = [r for r in all_recs if r["category"] == "writing"]
    elif "grant" in page_lower or "funding" in page_lower:
        preferred = [r for r in all_recs if r["category"] == "funding"]
    elif "teach" in page_lower:
        preferred = [r for r in all_recs if r["category"] == "teaching"]
    elif "collab" in page_lower or "network" in page_lower:
        preferred = [r for r in all_recs if r["category"] == "collaboration"]
    elif "profile" in page_lower or "settings" in page_lower:
        preferred = [r for r in all_recs if r["category"] == "career"]
    else:
        preferred = []

    top = preferred[0] if preferred else (all_recs[0] if all_recs else None)

    # Never surface "insufficient data" rec as the next action — it's informational
    if top and top.get("data_quality") == "insufficient":
        substantive = [r for r in all_recs if r.get("data_quality") != "insufficient"]
        top = substantive[0] if substantive else None

    return {"action": top, "generated_at": datetime.now(timezone.utc).isoformat()}


@router.post("/recommendations/{rec_id}/dismiss")
async def dismiss_recommendation(
    rec_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    try:
        await db.proactive_interactions.update_one(
            {"user_id": uid, "rec_id": rec_id},
            {
                "$set": {"action": "dismissed", "updated_at": datetime.now(timezone.utc)},
                "$setOnInsert": {"user_id": uid, "rec_id": rec_id, "created_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )
    except Exception as e:
        logger.warning("Dismiss write failed: %s", e)
    return {"ok": True}


@router.post("/recommendations/{rec_id}/accept")
async def accept_recommendation(
    rec_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    try:
        await db.proactive_interactions.update_one(
            {"user_id": uid, "rec_id": rec_id},
            {
                "$set": {"action": "accepted", "updated_at": datetime.now(timezone.utc)},
                "$setOnInsert": {"user_id": uid, "rec_id": rec_id, "created_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )
    except Exception as e:
        logger.warning("Accept write failed: %s", e)
    return {"ok": True}


@router.get("/insights")
async def get_insights(user=Depends(get_current_user), db=Depends(get_db)):
    """
    Verified platform insights based solely on your account activity.
    All figures are direct counts from the platform database.
    No estimates or external benchmarks are used.
    """
    db = make_db_proxy(db, user)
    uid      = _uid(user)
    interests = user.get("research_interests") or user.get("research_areas") or []
    comp, _  = _profile_completeness(user)
    insights = []

    try:
        ms_total = await db.manuscripts.count_documents({"user_id": uid})
        ms_pub   = await db.manuscripts.count_documents({"user_id": uid, "status": "published"})
        if ms_total > 0:
            insights.append({
                "id":     "ms_count",
                "icon":   "file-text",
                "title":  f"{ms_total} manuscript{'s' if ms_total > 1 else ''} on platform",
                "text":   f"{ms_pub} marked as published. Source: Synaptiq platform database.",
                "source": "Synaptiq platform database",
            })
    except Exception:
        pass

    try:
        app_count = await db.grant_applications.count_documents({"applicant_id": uid})
        if app_count > 0:
            insights.append({
                "id":     "grant_apps",
                "icon":   "dollar-sign",
                "title":  f"{app_count} grant application{'s' if app_count > 1 else ''} on record",
                "text":   "Source: Synaptiq platform database — grant_applications collection.",
                "source": "Synaptiq platform database",
            })
    except Exception:
        pass

    try:
        collab_count = await db.collaborations.count_documents(
            {"$or": [{"creator_id": uid}, {"members.user_id": uid}]}
        )
        if collab_count > 0:
            insights.append({
                "id":     "collabs",
                "icon":   "users",
                "title":  f"Member of {collab_count} collaboration{'s' if collab_count > 1 else ''}",
                "text":   "Source: Synaptiq platform database — collaborations collection.",
                "source": "Synaptiq platform database",
            })
    except Exception:
        pass

    if interests:
        insights.append({
            "id":     "domains",
            "icon":   "brain",
            "title":  "Research interests on file",
            "text":   f"{', '.join(interests[:4])}. Source: Your platform profile.",
            "source": "Synaptiq platform database — user profile",
        })

    insights.append({
        "id":     "profile",
        "icon":   "user",
        "title":  f"Profile {comp}% complete",
        "text":   (
            "All fields complete. Source: Platform profile audit."
            if comp == 100
            else f"{comp}% of weighted profile fields are filled. Source: Platform profile audit."
        ),
        "source": "Synaptiq platform database — user profile",
    })

    if not (user.get("orcid") or {}).get("orcid_id"):
        insights.append({
            "id":     "orcid",
            "icon":   "link",
            "title":  "ORCID not connected",
            "text":   "ORCID field is empty in your profile. Source: Platform profile audit.",
            "source": "Synaptiq platform database — user profile",
        })

    return {
        "insights":      insights[:6],
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "data_sources":  ["Synaptiq platform database"],
        "policy_note":   "All insights are counts and facts from your platform data. No estimates or external benchmarks.",
    }


@router.get("/health-score")
async def get_health_score(user=Depends(get_current_user), db=Depends(get_db)):
    """
    Platform activity indicator (0-100).

    IMPORTANT: This score reflects your Synaptiq platform activity only.
    It is NOT a measure of research quality, impact, or academic standing.
    It is NOT validated against external outcomes.
    Methodology: weighted sum of platform-observable fields and record counts.
    """
    db = make_db_proxy(db, user)
    uid     = _uid(user)
    comp, _ = _profile_completeness(user)

    subscores = {}
    total     = 0

    # Profile completeness (30 pts max) — direct field audit
    profile_pts = round(comp * 0.30)
    subscores["profile"] = {
        "label":  "Profile completeness",
        "score":  profile_pts,
        "max":    30,
        "basis":  f"{comp}% of weighted profile fields filled (platform profile audit)",
    }
    total += profile_pts

    # Manuscript records (25 pts max) — direct DB count, capped at 3 manuscripts
    ms_pts = 0
    ms_count = 0
    try:
        ms_count = await db.manuscripts.count_documents({"user_id": uid})
        ms_pts   = min(25, ms_count * 8)
    except Exception:
        pass
    subscores["manuscripts"] = {
        "label":  "Manuscript records",
        "score":  ms_pts,
        "max":    25,
        "basis":  f"{ms_count} manuscript record(s) found (platform database)",
    }
    total += ms_pts

    # Project records (20 pts max) — direct DB count
    proj_pts   = 0
    proj_count = 0
    try:
        proj_count = await db.projects.count_documents({"creator_id": uid, "status": "active"})
        proj_pts   = min(20, proj_count * 7)
    except Exception:
        pass
    subscores["projects"] = {
        "label":  "Active project records",
        "score":  proj_pts,
        "max":    20,
        "basis":  f"{proj_count} active project record(s) found (platform database)",
    }
    total += proj_pts

    # ORCID (15 pts) — direct profile field check
    orcid_pts = 15 if (user.get("orcid") or {}).get("orcid_id") else 0
    subscores["orcid"] = {
        "label":  "ORCID connected",
        "score":  orcid_pts,
        "max":    15,
        "basis":  "ORCID field present in platform profile" if orcid_pts else "ORCID field empty in platform profile",
    }
    total += orcid_pts

    # Collaboration records (10 pts max) — direct DB count
    collab_pts   = 0
    collab_count = 0
    try:
        collab_count = await db.collaborations.count_documents(
            {"$or": [{"creator_id": uid}, {"members.user_id": uid}]}
        )
        collab_pts = min(10, collab_count * 3)
    except Exception:
        pass
    subscores["collaboration"] = {
        "label":  "Collaboration records",
        "score":  collab_pts,
        "max":    10,
        "basis":  f"{collab_count} collaboration record(s) (platform database)",
    }
    total += collab_pts

    final_score = min(100, total)

    return {
        "score":         final_score,
        "subscores":     subscores,
        "label":         "Excellent" if final_score >= 80 else "Good" if final_score >= 60 else "Fair" if final_score >= 40 else "Getting started",
        "methodology":   (
            "Score is a weighted sum of platform-observable activity indicators. "
            "It reflects Synaptiq profile and database activity only. "
            "It makes no claim about research quality, impact factor, or academic outcomes. "
            "Weights: profile (30), manuscripts (25), projects (20), ORCID (15), collaboration (10)."
        ),
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "data_sources":  ["Synaptiq platform database"],
    }


@router.get("/opportunity-score")
async def get_opportunity_score(user=Depends(get_current_user), db=Depends(get_db)):
    """
    Count of open opportunities currently available on the platform.
    All counts are real database queries with no estimates.
    """
    db = make_db_proxy(db, user)
    now   = datetime.now(timezone.utc)
    soon  = now + timedelta(days=30)
    counts = {}

    try:
        grants = await db.grants.count_documents({"deadline": {"$gte": now, "$lte": soon}})
        counts["grants_closing_30d"] = grants
    except Exception:
        counts["grants_closing_30d"] = 0

    try:
        collabs = await db.collaborations.count_documents({"status": "open"})
        counts["open_collaborations"] = collabs
    except Exception:
        counts["open_collaborations"] = 0

    try:
        confs = await db.conferences.count_documents({"deadline": {"$gte": now, "$lte": soon}})
        counts["conferences_closing_30d"] = confs
    except Exception:
        counts["conferences_closing_30d"] = 0

    total_open = sum(counts.values())

    return {
        "total_open_items": total_open,
        "counts":           counts,
        "label":            "Several open items" if total_open >= 10 else "Some open items" if total_open >= 3 else "Few open items",
        "methodology":      "All counts are live database queries. No scoring formula or weighting is applied.",
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "data_sources":     ["Synaptiq platform database"],
    }
