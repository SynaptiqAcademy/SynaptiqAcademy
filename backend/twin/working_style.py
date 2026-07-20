"""
Working style model.

Learns academic preferences from observed platform behaviour.
All observations are labeled as observations — never as definitive conclusions.
Examples: "Publishes manuscripts with quantitative methods", "Works on multiple projects simultaneously".
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .models import TwinEvidence, WorkingStyleObservation

logger = logging.getLogger("twin.working_style")


async def analyze_working_style(db, user_id: str) -> dict:
    """
    Analyze platform activity to observe working patterns.
    Returns dict with `observations` (list) and `last_analyzed` (datetime).
    """
    observations: list[dict] = []
    now = datetime.now(timezone.utc)

    # ── 1. Manuscript completion rhythm ───────────────────────────────────────
    ms_list = await db.manuscripts.find(
        {"user_id": user_id},
        {"status": 1, "created_at": 1, "updated_at": 1, "abstract": 1, "keywords": 1}
    ).sort("created_at", 1).to_list(100)

    total_ms = len(ms_list)
    completed_ms = [m for m in ms_list if m.get("status") in ("published", "submitted", "accepted")]

    if total_ms >= 2:
        observations.append({
            "pattern":        f"Has {total_ms} manuscript(s) in Synaptiq ({len(completed_ms)} completed/submitted)",
            "observed_count": total_ms,
            "confidence":     "high" if total_ms >= 5 else "medium" if total_ms >= 2 else "low",
            "evidence":       [{"source": "Synaptiq manuscripts DB", "detail": f"{total_ms} manuscript records"}],
            "first_observed": ms_list[0]["created_at"].isoformat() if ms_list[0].get("created_at") else None,
            "last_observed":  ms_list[-1].get("updated_at", ms_list[-1].get("created_at", now)).isoformat() if ms_list else None,
        })

    # ── 2. Research method preferences ────────────────────────────────────────
    method_counts: Counter = Counter()
    for ms in ms_list:
        text = " ".join([
            str(ms.get("abstract") or ""),
            " ".join(ms.get("keywords") or []),
        ]).lower()
        if "regression" in text or "statistical" in text:
            method_counts["quantitative/statistical"] += 1
        if "qualitative" in text or "interview" in text or "ethnograph" in text:
            method_counts["qualitative"] += 1
        if "review" in text or "meta-analysis" in text or "systematic" in text:
            method_counts["literature review/synthesis"] += 1
        if "machine learning" in text or "neural" in text or "deep learning" in text:
            method_counts["computational/ML"] += 1
        if "survey" in text or "questionnaire" in text:
            method_counts["survey-based"] += 1

    for method, count in method_counts.most_common(3):
        if count >= 2:
            observations.append({
                "pattern":        f"Frequently uses {method} methods in manuscripts",
                "observed_count": count,
                "confidence":     "high" if count >= 4 else "medium" if count >= 2 else "low",
                "evidence":       [{"source": "Synaptiq manuscripts DB", "detail": f"Observed in {count} manuscript(s)"}],
                "first_observed": None,
                "last_observed":  None,
            })

    # ── 3. Collaboration patterns ──────────────────────────────────────────────
    collab_count = await db.collaborations.count_documents(
        {"$or": [{"requester_id": user_id}, {"recipient_id": user_id}], "status": "accepted"}
    )
    if collab_count > 0:
        observations.append({
            "pattern":        f"Active collaborator — {collab_count} accepted collaboration(s) on platform",
            "observed_count": collab_count,
            "confidence":     "high" if collab_count >= 5 else "medium" if collab_count >= 2 else "low",
            "evidence":       [{"source": "Synaptiq collaborations DB", "detail": f"{collab_count} accepted collaborations"}],
            "first_observed": None,
            "last_observed":  None,
        })

    # ── 4. Project concurrency (working on multiple projects at once) ──────────
    active_projects = await db.projects.count_documents({"user_id": user_id, "status": "active"})
    if active_projects > 1:
        observations.append({
            "pattern":        f"Works on {active_projects} concurrent active project(s)",
            "observed_count": active_projects,
            "confidence":     "medium",
            "evidence":       [{"source": "Synaptiq projects DB", "detail": f"{active_projects} active projects"}],
            "first_observed": None,
            "last_observed":  now.isoformat(),
        })

    # ── 5. Teaching activity ───────────────────────────────────────────────────
    try:
        lesson_count = await db.lessons.count_documents({"instructor_id": user_id})
        if lesson_count > 0:
            observations.append({
                "pattern":        f"Engages in teaching — {lesson_count} lesson(s) recorded",
                "observed_count": lesson_count,
                "confidence":     "medium" if lesson_count >= 2 else "low",
                "evidence":       [{"source": "Synaptiq teaching DB", "detail": f"{lesson_count} lessons"}],
                "first_observed": None,
                "last_observed":  now.isoformat(),
            })
    except Exception:
        pass

    # ── 6. Grant activity ──────────────────────────────────────────────────────
    grant_count = await db.grants.count_documents({"user_id": user_id})
    if grant_count > 0:
        observations.append({
            "pattern":        f"Engages with research funding — {grant_count} grant record(s) on platform",
            "observed_count": grant_count,
            "confidence":     "medium" if grant_count >= 2 else "low",
            "evidence":       [{"source": "Synaptiq grants DB", "detail": f"{grant_count} grants"}],
            "first_observed": None,
            "last_observed":  now.isoformat(),
        })

    return {
        "observations":  observations,
        "last_analyzed": now.isoformat(),
        "methodology":   "Derived from observed platform activity only. These are observations, not assessments of researcher quality.",
        "source":        "Synaptiq platform data",
    }
