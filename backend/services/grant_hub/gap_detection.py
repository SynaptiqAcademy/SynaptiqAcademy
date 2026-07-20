"""Grant Collaboration Hub — Expertise Gap Detection.

AI-assisted + rule-based analysis of expertise gaps within a collaboration.

Collections:
  grant_collaborations             — collab metadata
  grant_team_members               — team roster
  grant_positions                  — open positions / requirements
  grant_consortia                  — partner institutions
  grant_work_packages              — work package task coverage
  grant_team_requirements          — cache collection (2hr TTL)
  institutions                     — for institution type lookup
  users                            — for career_stage
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


# ── main entry points ─────────────────────────────────────────────────────────

async def get_gap_analysis(collab_id: str, db) -> dict:
    """Return cached gap analysis (2hr TTL). Recomputes if stale."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    cutoff_str = cutoff.isoformat()

    cached = await db["grant_team_requirements"].find_one({
        "collaboration_id": collab_id,
        "computed_at": {"$gte": cutoff_str},
    })
    if cached:
        cached.pop("_id", None)
        return cached

    return await analyze_expertise_gaps(collab_id, db)


async def analyze_expertise_gaps(collab_id: str, db) -> dict:
    """Run full gap analysis (rule-based + AI) and cache the result."""
    try:
        collab_oid = ObjectId(collab_id)
    except Exception:
        return _empty_result(collab_id)

    # Parallel data load
    collab, member_docs, position_docs, consortium, wp_docs = await asyncio.gather(
        db["grant_collaborations"].find_one({"_id": collab_oid}),
        db["grant_team_members"].find({"collaboration_id": collab_id}).to_list(200),
        db["grant_positions"].find({"collaboration_id": collab_id}).to_list(100),
        db["grant_consortia"].find_one({"collaboration_id": collab_id}),
        db["grant_work_packages"].find({"collaboration_id": collab_id}).to_list(100),
    )

    if not collab:
        return _empty_result(collab_id)

    # ── Rule-based analysis ────────────────────────────────────────────────────

    # 1. Missing expertise: open positions → extract required expertise
    open_positions = [p for p in position_docs if p.get("status") == "open"]
    missing_expertise: list[str] = []
    for pos in open_positions:
        for exp in _safe_list(pos.get("required_expertise", [])):
            if exp and exp not in missing_expertise:
                missing_expertise.append(exp)

    # 2. Missing institution types
    expected_types = {"university", "hospital", "ngo", "industry", "government_agency"}
    present_types: set = set()

    partner_institutions = consortium.get("partner_institutions", []) if consortium else []
    all_inst_ids = []
    lead_inst_id = (consortium or {}).get("lead_institution_id", "")
    if lead_inst_id:
        all_inst_ids.append(lead_inst_id)
    for p in partner_institutions:
        if p.get("institution_id") and p.get("status") != "removed":
            all_inst_ids.append(p["institution_id"])

    if all_inst_ids:
        inst_oids = []
        for iid in all_inst_ids:
            try:
                inst_oids.append(ObjectId(iid))
            except Exception:
                pass
        if inst_oids:
            inst_docs = await db["institutions"].find(
                {"_id": {"$in": inst_oids}},
                {"type": 1},
            ).to_list(50)
            for inst in inst_docs:
                itype = (inst.get("type") or "").lower().strip()
                if itype:
                    present_types.add(itype)

    missing_institution_types = list(expected_types - present_types)

    # 3. Missing countries
    countries_required = _safe_list(collab.get("countries_required", []))
    actual_countries: set = set()
    for p in partner_institutions:
        if p.get("status") != "removed":
            for c in _safe_list(p.get("countries", [])):
                if c:
                    actual_countries.add(c)
    missing_countries = [c for c in countries_required if c not in actual_countries]

    # 4. Missing seniority mix
    user_ids = [m.get("user_id") for m in member_docs if m.get("user_id")]
    career_stages: list[str] = []
    if user_ids:
        user_oids = []
        for uid in user_ids:
            try:
                user_oids.append(ObjectId(uid))
            except Exception:
                pass
        if user_oids:
            user_docs = await db["users"].find(
                {"_id": {"$in": user_oids}},
                {"career_stage": 1},
            ).to_list(200)
            career_stages = [
                (u.get("career_stage") or "").lower()
                for u in user_docs
                if u.get("career_stage")
            ]

    seniority_map = {
        "senior": {"senior", "professor", "principal"},
        "mid": {"mid", "associate", "researcher"},
        "junior": {"junior", "phd", "postdoc", "early"},
    }

    present_levels: set = set()
    for stage in career_stages:
        for level, keywords in seniority_map.items():
            if any(kw in stage for kw in keywords):
                present_levels.add(level)

    missing_seniority: list[str] = []
    for level in ["senior", "mid", "junior"]:
        if level not in present_levels:
            missing_seniority.append(level)

    # 5. Missing deliverable owners
    missing_deliverable_owners: list[str] = []
    for wp in wp_docs:
        if not wp.get("lead_user_id"):
            missing_deliverable_owners.append(f"Work package '{wp.get('title', wp.get('_id', ''))}' has no lead")
        for task in wp.get("tasks", []):
            if not task.get("assignee_user_id"):
                missing_deliverable_owners.append(
                    f"Task '{task.get('title', task.get('task_id', ''))}' has no assignee"
                )

    # ── AI analysis ────────────────────────────────────────────────────────────
    ai_recommendations = ""
    try:
        from services.ai.llm import call_llm

        prompt_user = (
            f"Collaboration: {collab.get('title', 'Untitled')}\n"
            f"Research areas: {', '.join(_safe_list(collab.get('research_areas', [])))}\n"
            f"Team size: {len(member_docs)}\n"
            f"Open positions: {len(open_positions)}\n"
            f"Partner institution count: {len(partner_institutions)}\n"
            f"Missing expertise areas: {', '.join(missing_expertise) if missing_expertise else 'none identified'}\n\n"
            "Identify: (1) missing methodologies not covered by the team, "
            "(2) missing review capacity, (3) 3-5 specific recommendations "
            "to strengthen this collaboration. Be concise and actionable."
        )

        ai_recommendations = await call_llm(
            system=(
                "You are an expert grant collaboration advisor. "
                "Analyze the collaboration profile and provide structured gap analysis. "
                "Respond in plain text with clearly numbered points."
            ),
            user_msg=prompt_user,
            feature="grant_hub.gap_detection",
            max_tokens=800,
        )
    except Exception:
        ai_recommendations = ""

    # Build recommendations list from rule-based findings
    recommendations: list[str] = []
    if missing_expertise:
        recommendations.append(
            f"Fill open positions requiring: {', '.join(missing_expertise[:5])}"
        )
    if missing_institution_types:
        recommendations.append(
            f"Add partner institutions of type: {', '.join(missing_institution_types)}"
        )
    if missing_countries:
        recommendations.append(
            f"Recruit partners from required countries: {', '.join(missing_countries[:5])}"
        )
    if missing_seniority:
        recommendations.append(
            f"Recruit {'/'.join(missing_seniority)}-level team members for seniority balance"
        )
    if missing_deliverable_owners:
        recommendations.append(
            f"Assign owners to {len(missing_deliverable_owners)} unassigned tasks/work packages"
        )

    now = _now()
    result = {
        "collaboration_id": collab_id,
        "missing_expertise": missing_expertise,
        "missing_institution_types": missing_institution_types,
        "missing_countries": missing_countries,
        "missing_seniority": missing_seniority,
        "missing_deliverable_owners": missing_deliverable_owners,
        "ai_recommendations": ai_recommendations,
        "recommendations": recommendations,
        "computed_at": now,
    }

    # Cache result
    await db["grant_team_requirements"].update_one(
        {"collaboration_id": collab_id},
        {"$set": result},
        upsert=True,
    )

    return result


def _empty_result(collab_id: str) -> dict:
    return {
        "collaboration_id": collab_id,
        "missing_expertise": [],
        "missing_institution_types": [],
        "missing_countries": [],
        "missing_seniority": [],
        "missing_deliverable_owners": [],
        "ai_recommendations": "",
        "recommendations": [],
        "computed_at": _now(),
    }
