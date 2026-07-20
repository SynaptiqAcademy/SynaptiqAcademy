"""Grant Collaboration Hub — Funding Readiness Engine.

Computes a 0-100 readiness score across 9 dimensions.

Collections:
  grant_collaborations             — collab metadata
  grant_positions                  — for team completeness
  grant_consortia                  — for consortium readiness
  grant_work_packages              — for work package coverage
  grant_collab_proposal_sections   — for proposal progress
  grant_team_members               — for member count
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from bson import ObjectId

from services.grant_hub.consortium_service import validate_consortium_eligibility


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _label(score: float) -> str:
    if score <= 25:
        return "Just Starting"
    elif score <= 50:
        return "Building"
    elif score <= 70:
        return "Making Progress"
    elif score <= 85:
        return "Nearly Ready"
    else:
        return "Submission Ready"


async def compute_readiness(collab_id: str, db) -> dict:
    """Compute funding readiness score (0-100) across 9 dimensions."""
    try:
        collab_oid = ObjectId(collab_id)
    except Exception:
        return _empty_result(collab_id)

    # Load all needed data in parallel
    (
        collab,
        total_positions,
        open_positions,
        member_count,
        total_wps,
        active_wps,
        total_sections,
        approved_sections,
        consortium,
    ) = await asyncio.gather(
        db["grant_collaborations"].find_one({"_id": collab_oid}),
        db["grant_positions"].count_documents({"collaboration_id": collab_id}),
        db["grant_positions"].count_documents({"collaboration_id": collab_id, "status": "open"}),
        db["grant_team_members"].count_documents({"collaboration_id": collab_id}),
        db["grant_work_packages"].count_documents({"collaboration_id": collab_id}),
        db["grant_work_packages"].count_documents(
            {"collaboration_id": collab_id, "status": {"$ne": "not_started"}}
        ),
        db["grant_collab_proposal_sections"].count_documents({"collaboration_id": collab_id}),
        db["grant_collab_proposal_sections"].count_documents(
            {"collaboration_id": collab_id, "status": "approved"}
        ),
        db["grant_consortia"].find_one({"collaboration_id": collab_id}),
    )

    if not collab:
        return _empty_result(collab_id)

    filled_positions = total_positions - open_positions
    dimensions: dict = {}
    improvement_actions: list[str] = []

    # ── 1. Team completeness (0-20) ───────────────────────────────────────────
    if total_positions > 0:
        team_completeness = round(filled_positions / total_positions * 20, 2)
    else:
        team_completeness = 10.0  # No positions defined — partial credit
    dimensions["team_completeness"] = {"score": team_completeness, "max": 20}
    if team_completeness < 20:
        if total_positions == 0:
            improvement_actions.append("Define required positions for the collaboration")
        else:
            improvement_actions.append(
                f"Fill {open_positions} open position(s) to improve team completeness"
            )

    # ── 2. Consortium readiness (0-15) ────────────────────────────────────────
    consortium_score = 0.0
    has_lead_institution = bool(consortium and consortium.get("lead_institution_id"))
    partners = (consortium or {}).get("partner_institutions", [])
    active_partners = [p for p in partners if p.get("status") != "removed"]
    has_partners = len(active_partners) >= 1

    if has_lead_institution:
        consortium_score += 5.0
    if has_partners:
        consortium_score += 5.0

    # Check eligibility validity (async)
    try:
        eligibility = await validate_consortium_eligibility(collab_id, db)
        if eligibility.get("is_eligible"):
            consortium_score += 5.0
        elif not eligibility.get("issues"):
            consortium_score += 5.0
    except Exception:
        pass

    dimensions["consortium_readiness"] = {"score": consortium_score, "max": 15}
    if consortium_score < 15:
        if not has_lead_institution:
            improvement_actions.append("Set a lead institution for the consortium")
        if not has_partners:
            improvement_actions.append("Add at least one partner institution")

    # ── 3. Expertise coverage (0-15) ─────────────────────────────────────────
    if total_positions > 0:
        expertise_coverage = round(filled_positions / total_positions * 15, 2)
    else:
        expertise_coverage = 0.0
    dimensions["expertise_coverage"] = {"score": expertise_coverage, "max": 15}
    if expertise_coverage < 15 and total_positions > 0:
        improvement_actions.append(
            f"Fill expertise gaps: {open_positions} role(s) still open"
        )

    # ── 4. Proposal progress (0-15) ──────────────────────────────────────────
    if total_sections > 0:
        proposal_progress = round(approved_sections / total_sections * 15, 2)
    else:
        proposal_progress = 0.0
    dimensions["proposal_progress"] = {"score": proposal_progress, "max": 15}
    if proposal_progress < 15:
        if total_sections == 0:
            improvement_actions.append("Start writing collaborative proposal sections")
        else:
            improvement_actions.append(
                f"Get proposal sections approved: {total_sections - approved_sections} pending"
            )

    # ── 5. Work package coverage (0-10) ──────────────────────────────────────
    if total_wps > 0:
        wp_coverage = round(active_wps / total_wps * 10, 2)
    else:
        wp_coverage = 0.0
    dimensions["work_package_coverage"] = {"score": wp_coverage, "max": 10}
    if wp_coverage < 10:
        if total_wps == 0:
            improvement_actions.append("Create work packages to structure the project")
        else:
            improvement_actions.append(
                f"Start work on {total_wps - active_wps} work package(s) still not started"
            )

    # ── 6. Institutional coverage (0-10) ─────────────────────────────────────
    # Count unique countries across active partners
    partner_countries: set = set()
    for p in active_partners:
        for c in (p.get("countries") or []):
            if c:
                partner_countries.add(c)
    # Also count lead institution's country
    if consortium and consortium.get("lead_institution_id"):
        try:
            lead_inst = await db["institutions"].find_one(
                {"_id": ObjectId(consortium["lead_institution_id"])},
                {"country": 1},
            )
            if lead_inst and lead_inst.get("country"):
                partner_countries.add(lead_inst["country"])
        except Exception:
            pass

    if len(partner_countries) >= 2:
        institutional_coverage = 10.0
    elif len(partner_countries) == 1:
        institutional_coverage = 5.0
    else:
        institutional_coverage = 0.0
    dimensions["institutional_coverage"] = {"score": institutional_coverage, "max": 10}
    if institutional_coverage < 10:
        improvement_actions.append(
            "Add partners from at least 2 different countries for multi-national coverage"
        )

    # ── 7. Budget defined (0-5) ──────────────────────────────────────────────
    budget_total = float(collab.get("budget_total", 0))
    budget_defined = 5.0 if budget_total > 0 else 0.0
    dimensions["budget_defined"] = {"score": budget_defined, "max": 5}
    if budget_defined < 5:
        improvement_actions.append("Define the collaboration's total budget")

    # ── 8. Deadline buffer (0-5) ─────────────────────────────────────────────
    deadline_str = collab.get("deadline", "")
    deadline_score = 0.0
    if deadline_str:
        try:
            # Normalize ISO string to date comparison
            deadline_clean = deadline_str.replace("Z", "+00:00")
            # Try parsing as full ISO datetime, fall back to date-only
            try:
                deadline_dt = datetime.fromisoformat(deadline_clean)
                # Ensure timezone-aware
                if deadline_dt.tzinfo is None:
                    deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                # Date only (YYYY-MM-DD)
                from datetime import date
                d = date.fromisoformat(deadline_str[:10])
                deadline_dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)

            now_dt = datetime.now(timezone.utc)
            days_left = (deadline_dt - now_dt).days

            if days_left > 14:
                deadline_score = 5.0
            elif days_left >= 7:
                deadline_score = 3.0
            elif days_left >= 0:
                deadline_score = 1.0
            else:
                deadline_score = 0.0
        except Exception:
            deadline_score = 0.0
    dimensions["deadline_buffer"] = {"score": deadline_score, "max": 5}
    if deadline_score == 0.0 and deadline_str:
        improvement_actions.append("Deadline has passed or is critically close — review submission timeline")
    elif deadline_score < 5.0:
        improvement_actions.append("Deadline is approaching — accelerate preparation")

    # ── 9. Member count (0-5) ────────────────────────────────────────────────
    if member_count >= 3:
        member_score = 5.0
    elif member_count == 2:
        member_score = 3.0
    elif member_count == 1:
        member_score = 1.0
    else:
        member_score = 0.0
    dimensions["member_count"] = {"score": member_score, "max": 5}
    if member_score < 5:
        improvement_actions.append(
            f"Recruit more team members (currently {member_count}; aim for 3+)"
        )

    # ── Total ────────────────────────────────────────────────────────────────
    total_score = round(sum(d["score"] for d in dimensions.values()), 2)
    total_score = min(100.0, total_score)

    return {
        "collaboration_id": collab_id,
        "total_score": total_score,
        "label": _label(total_score),
        "dimensions": dimensions,
        "improvement_actions": improvement_actions,
        "computed_at": _now(),
    }


def _empty_result(collab_id: str) -> dict:
    return {
        "collaboration_id": collab_id,
        "total_score": 0.0,
        "label": "Just Starting",
        "dimensions": {},
        "improvement_actions": ["Collaboration not found"],
        "computed_at": _now(),
    }
