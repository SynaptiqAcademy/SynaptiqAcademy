"""
SIE Career Engine — long-term academic career planning.
Tracks position, promotion requirements, readiness indicators, and career roadmap.
"""
from datetime import datetime, timezone
from typing import Optional

_POSITIONS = [
    "phd_student", "postdoc", "research_associate",
    "assistant_professor", "associate_professor", "full_professor",
    "research_scientist", "senior_researcher", "principal_investigator",
    "professor_emeritus", "industry_researcher", "other",
]

_PROMOTION_REQUIREMENTS = {
    "phd_student": {
        "next_position": "postdoc",
        "requirements": [
            {"key": "thesis", "label": "Complete PhD thesis", "weight": 0.5},
            {"key": "publications", "label": "1+ peer-reviewed publications", "threshold": 1, "weight": 0.3},
            {"key": "conference", "label": "Present at 2+ conferences", "threshold": 2, "weight": 0.2},
        ],
    },
    "postdoc": {
        "next_position": "assistant_professor",
        "requirements": [
            {"key": "publications", "label": "5+ peer-reviewed publications (2+ Q1)", "threshold": 5, "weight": 0.4},
            {"key": "grants", "label": "1+ competitive grant", "threshold": 1, "weight": 0.3},
            {"key": "teaching", "label": "Teaching experience", "weight": 0.15},
            {"key": "collabs", "label": "International collaborations", "weight": 0.15},
        ],
    },
    "assistant_professor": {
        "next_position": "associate_professor",
        "requirements": [
            {"key": "publications", "label": "15+ publications (5+ Q1)", "threshold": 15, "weight": 0.35},
            {"key": "grants", "label": "3+ grants as PI", "threshold": 3, "weight": 0.25},
            {"key": "teaching", "label": "Positive teaching evaluations", "weight": 0.2},
            {"key": "service", "label": "Editorial/review service", "weight": 0.1},
            {"key": "h_index", "label": "h-index ≥ 8", "threshold": 8, "weight": 0.1},
        ],
    },
    "associate_professor": {
        "next_position": "full_professor",
        "requirements": [
            {"key": "publications", "label": "30+ publications (10+ Q1)", "threshold": 30, "weight": 0.3},
            {"key": "grants", "label": "Sustained grant funding", "threshold": 5, "weight": 0.25},
            {"key": "phd_supervised", "label": "3+ PhD students supervised", "threshold": 3, "weight": 0.2},
            {"key": "h_index", "label": "h-index ≥ 15", "threshold": 15, "weight": 0.15},
            {"key": "international", "label": "International recognition", "weight": 0.1},
        ],
    },
    "other": {
        "next_position": "assistant_professor",
        "requirements": [
            {"key": "publications", "label": "Build publication record", "weight": 0.5},
            {"key": "grants", "label": "Secure funding", "weight": 0.3},
            {"key": "network", "label": "Build professional network", "weight": 0.2},
        ],
    },
}


def _ser(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id", ""))
    for k, v in doc.items():
        if hasattr(v, "isoformat"):
            doc[k] = v.isoformat()
    return doc


async def get_career_profile(user_id: str, db) -> dict:
    doc = await db.sie_career.find_one({"user_id": user_id})
    if not doc:
        profile = {
            "user_id": user_id,
            "current_position": "other",
            "institution": "",
            "department": "",
            "years_in_position": 0,
            "target_position": "assistant_professor",
            "target_timeline_years": 3,
            "skills": [],
            "certifications": [],
            "training": [],
            "phd_students_supervised": 0,
            "teaching_courses": 0,
            "editorial_roles": [],
            "notes": "",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await db.sie_career.insert_one(profile)
        profile.pop("_id", None)
        return profile
    doc.pop("_id", None)
    return doc


async def update_career_profile(user_id: str, updates: dict, db) -> dict:
    allowed = {
        "current_position", "institution", "department", "years_in_position",
        "target_position", "target_timeline_years", "skills", "certifications",
        "training", "phd_students_supervised", "teaching_courses", "editorial_roles", "notes",
    }
    safe = {k: v for k, v in updates.items() if k in allowed}
    safe["updated_at"] = datetime.now(timezone.utc)
    await db.sie_career.update_one({"user_id": user_id}, {"$set": safe}, upsert=True)
    return await get_career_profile(user_id, db)


async def get_promotion_readiness(user_id: str, db) -> dict:
    profile = await get_career_profile(user_id, db)
    position = profile.get("current_position", "other")
    reqs_def = _PROMOTION_REQUIREMENTS.get(position, _PROMOTION_REQUIREMENTS["other"])

    pubs = await db.publications.count_documents({"user_id": user_id})
    grants = await db.grant_applications.count_documents({"user_id": user_id, "status": "approved"})
    collabs = await db.collaborations.count_documents({"user_id": user_id})

    live_data = {
        "publications": pubs,
        "grants": grants,
        "collabs": collabs,
        "phd_supervised": profile.get("phd_students_supervised", 0),
        "h_index": 0,
    }

    requirements = []
    total_score = 0.0
    for req in reqs_def["requirements"]:
        key = req["key"]
        threshold = req.get("threshold", 0)
        weight = req["weight"]
        current = live_data.get(key, 0)
        if threshold > 0:
            met = current >= threshold
            pct = min(100, round((current / threshold) * 100)) if threshold > 0 else 0
        else:
            met = False
            pct = 0
        contribution = weight * pct
        total_score += contribution
        requirements.append({
            "key": key,
            "label": req["label"],
            "weight": weight,
            "threshold": threshold,
            "current": current,
            "met": met,
            "pct": pct,
        })

    return {
        "current_position": position,
        "next_position": reqs_def["next_position"],
        "readiness_score": round(total_score),
        "requirements": requirements,
        "live_data": live_data,
        "ready_for_promotion": total_score >= 75,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_career_roadmap(user_id: str, db) -> dict:
    profile = await get_career_profile(user_id, db)
    position = profile.get("current_position", "other")
    target = profile.get("target_position", "full_professor")
    timeline_years = profile.get("target_timeline_years", 5)

    positions_ordered = [
        "phd_student", "postdoc", "research_associate", "assistant_professor",
        "associate_professor", "full_professor",
    ]

    try:
        start_idx = positions_ordered.index(position) if position in positions_ordered else 0
        end_idx = positions_ordered.index(target) if target in positions_ordered else len(positions_ordered) - 1
    except ValueError:
        start_idx, end_idx = 0, 3

    path = positions_ordered[start_idx:end_idx + 1]
    steps_per_position = max(1, timeline_years // max(1, len(path) - 1)) if len(path) > 1 else timeline_years

    milestones = []
    for i, pos in enumerate(path):
        reqs_def = _PROMOTION_REQUIREMENTS.get(pos, _PROMOTION_REQUIREMENTS["other"])
        milestones.append({
            "position": pos,
            "label": pos.replace("_", " ").title(),
            "estimated_years": i * steps_per_position,
            "next_position": reqs_def.get("next_position"),
            "key_requirements": [r["label"] for r in reqs_def.get("requirements", [])[:3]],
        })

    return {
        "current_position": position,
        "target_position": target,
        "timeline_years": timeline_years,
        "path": milestones,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
