"""Grant Collaboration Hub — Analytics Service.

Aggregates real data from grant hub collections for dashboards.

Collections:
  grant_collaborations         — workspace docs
  grant_team_invitations       — invitation records
  grant_team_members           — membership records
  grant_consortia              — consortium info
  grant_positions              — open roles
  grant_work_packages          — work packages
  grant_collab_proposal_sections — proposal sections
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from bson import ObjectId


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── user-level analytics ──────────────────────────────────────────────────────

async def get_hub_analytics(user_id: str, db) -> dict:
    """Return personal hub analytics for a specific user."""
    # Fetch base data in parallel
    (
        my_collab_docs,
        my_invitations_as_invitee,
        my_accepted_invitations,
    ) = await asyncio.gather(
        db["grant_collaborations"].find(
            {"lead_user_id": user_id},
            {"status": 1},
        ).to_list(500),
        db["grant_team_invitations"].find(
            {"to_user_id": user_id},
            {"status": 1},
        ).to_list(500),
        db["grant_team_invitations"].find(
            {"to_user_id": user_id, "status": "accepted"},
            {"collaboration_id": 1},
        ).to_list(500),
    )

    # Also get collabs where user is a member (not just lead)
    member_collab_ids = await db["grant_team_members"].find(
        {"user_id": user_id},
        {"collaboration_id": 1},
    ).to_list(500)
    member_collab_id_set = {m["collaboration_id"] for m in member_collab_ids}

    # Get member collabs (not already counted as lead)
    lead_collab_ids = {str(d["_id"]) for d in my_collab_docs}
    additional_collab_ids = member_collab_id_set - lead_collab_ids

    additional_collabs: list = []
    if additional_collab_ids:
        oids = []
        for cid in additional_collab_ids:
            try:
                oids.append(ObjectId(cid))
            except Exception:
                pass
        if oids:
            additional_collabs = await db["grant_collaborations"].find(
                {"_id": {"$in": oids}},
                {"status": 1},
            ).to_list(500)

    all_my_collabs = list(my_collab_docs) + additional_collabs

    # Count collaborations by status
    collab_by_status: dict = {}
    for c in all_my_collabs:
        st = c.get("status", "unknown")
        collab_by_status[st] = collab_by_status.get(st, 0) + 1

    # Count invitations by status
    invitations_by_status: dict = {}
    for inv in my_invitations_as_invitee:
        st = inv.get("status", "unknown")
        invitations_by_status[st] = invitations_by_status.get(st, 0) + 1

    # Count positions filled (accepted invitations = accepted into teams)
    positions_filled = len(my_accepted_invitations)

    # Active consortium count (where user is lead of the collab)
    lead_collab_list = list(lead_collab_ids)
    active_consortia_count = 0
    if lead_collab_list:
        active_consortia_count = await db["grant_consortia"].count_documents(
            {"collaboration_id": {"$in": lead_collab_list}}
        )

    return {
        "user_id": user_id,
        "my_collaborations": {
            "total": len(all_my_collabs),
            "by_status": collab_by_status,
        },
        "my_invitations": {
            "total": len(my_invitations_as_invitee),
            "by_status": invitations_by_status,
        },
        "positions_filled": positions_filled,
        "active_consortia": active_consortia_count,
        "computed_at": _now(),
    }


# ── collaboration-level analytics ─────────────────────────────────────────────

async def get_collaboration_analytics(collab_id: str, db) -> dict:
    """Return detailed analytics for a specific collaboration."""
    try:
        collab_oid = ObjectId(collab_id)
    except Exception:
        return {"collaboration_id": collab_id, "error": "Invalid id"}

    (
        collab,
        total_positions,
        filled_positions,
        total_sections,
        approved_sections,
        invitation_docs,
        wp_docs,
        consortium,
    ) = await asyncio.gather(
        db["grant_collaborations"].find_one({"_id": collab_oid}),
        db["grant_positions"].count_documents({"collaboration_id": collab_id}),
        db["grant_positions"].count_documents({"collaboration_id": collab_id, "status": "filled"}),
        db["grant_collab_proposal_sections"].count_documents({"collaboration_id": collab_id}),
        db["grant_collab_proposal_sections"].count_documents(
            {"collaboration_id": collab_id, "status": "approved"}
        ),
        db["grant_team_invitations"].find(
            {"collaboration_id": collab_id},
            {"status": 1, "created_at": 1, "to_user_id": 1},
        ).to_list(500),
        db["grant_work_packages"].find(
            {"collaboration_id": collab_id},
            {"created_at": 1, "status": 1},
        ).to_list(200),
        db["grant_consortia"].find_one({"collaboration_id": collab_id}),
    )

    # Position fill rate
    fill_rate = round(filled_positions / max(total_positions, 1) * 100, 1)

    # Proposal completion
    proposal_completion = round(approved_sections / max(total_sections, 1) * 100, 1)

    # Partner diversity
    partner_countries: list = []
    institution_types: list = []
    partners = (consortium or {}).get("partner_institutions", [])
    active_partners = [p for p in partners if p.get("status") != "removed"]
    for p in active_partners:
        for c in (p.get("countries") or []):
            if c and c not in partner_countries:
                partner_countries.append(c)

    # Fetch institution types
    inst_ids = [p.get("institution_id") for p in active_partners if p.get("institution_id")]
    if inst_ids:
        inst_oids = []
        for iid in inst_ids:
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
                itype = inst.get("type", "")
                if itype and itype not in institution_types:
                    institution_types.append(itype)

    # Timeline events (invitation created_at + wp created_at)
    timeline: list = []
    for inv in invitation_docs:
        timeline.append({
            "event": "invitation_sent",
            "date": inv.get("created_at", ""),
            "status": inv.get("status", ""),
        })
    for wp in wp_docs:
        timeline.append({
            "event": "work_package_created",
            "date": wp.get("created_at", ""),
            "status": wp.get("status", ""),
        })
    timeline.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Invitation acceptance rate
    inv_sent = len(invitation_docs)
    inv_accepted = sum(1 for i in invitation_docs if i.get("status") == "accepted")
    inv_acceptance_rate = round(inv_accepted / max(inv_sent, 1) * 100, 1)

    return {
        "collaboration_id": collab_id,
        "position_fill_rate": fill_rate,
        "positions": {"total": total_positions, "filled": filled_positions},
        "proposal_completion": proposal_completion,
        "proposal_sections": {"total": total_sections, "approved": approved_sections},
        "partner_diversity": {
            "countries": partner_countries,
            "institution_types": institution_types,
            "partner_count": len(active_partners),
        },
        "invitations": {
            "total": inv_sent,
            "accepted": inv_accepted,
            "acceptance_rate": inv_acceptance_rate,
        },
        "timeline": timeline[:50],
        "computed_at": _now(),
    }


# ── platform-wide analytics ───────────────────────────────────────────────────

async def get_platform_grant_analytics(db) -> dict:
    """Return platform-wide grant collaboration analytics."""
    (
        collab_status_agg,
        total_invitations,
        accepted_invitations,
        research_area_agg,
        funding_source_agg,
    ) = await asyncio.gather(
        db["grant_collaborations"].aggregate([
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]).to_list(20),
        db["grant_team_invitations"].count_documents({}),
        db["grant_team_invitations"].count_documents({"status": "accepted"}),
        db["grant_collaborations"].aggregate([
            {"$unwind": "$research_areas"},
            {"$group": {"_id": "$research_areas", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]).to_list(10),
        db["grant_collaborations"].aggregate([
            {"$match": {"funding_source": {"$ne": "", "$exists": True}}},
            {"$group": {"_id": "$funding_source", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]).to_list(10),
    )

    # Collabs by status
    collab_by_status: dict = {}
    total_collabs = 0
    for item in collab_status_agg:
        st = item.get("_id") or "unknown"
        cnt = item.get("count", 0)
        collab_by_status[st] = cnt
        total_collabs += cnt

    # Most active research areas
    active_research_areas = [
        {"area": item["_id"], "count": item["count"]}
        for item in research_area_agg
        if item.get("_id")
    ]

    # Top funding sources
    top_funding_sources = [
        {"funding_source": item["_id"], "count": item["count"]}
        for item in funding_source_agg
        if item.get("_id")
    ]

    # Acceptance rate
    invitation_acceptance_rate = round(
        accepted_invitations / max(total_invitations, 1) * 100, 1
    )

    return {
        "total_collaborations": total_collabs,
        "collaborations_by_status": collab_by_status,
        "total_invitations_sent": total_invitations,
        "total_invitations_accepted": accepted_invitations,
        "invitation_acceptance_rate": invitation_acceptance_rate,
        "most_active_research_areas": active_research_areas,
        "top_funding_sources": top_funding_sources,
        "computed_at": _now(),
    }
