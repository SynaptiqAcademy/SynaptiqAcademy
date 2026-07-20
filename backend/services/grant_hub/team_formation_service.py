"""Grant Collaboration Hub — Team Formation Service.

Manages positions, invitations, and team assembly for collaboration workspaces.

Collections:
  grant_positions        — open roles within a collaboration
  grant_team_invitations — invitation records
  grant_team_members     — team membership records
  grant_collaborations   — for member_count increment
  users                  — for enriching team member info
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from bson import ObjectId


def _ser(d: dict) -> dict:
    if not d:
        return {}
    out = dict(d)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    for k, v in out.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


# ── positions ─────────────────────────────────────────────────────────────────

async def create_position(collab_id: str, user_id: str, data: dict, db) -> dict:
    """Create an open position within a collaboration."""
    now = _now()
    doc = {
        "collaboration_id": collab_id,
        "role_title": data.get("role_title", ""),
        "description": data.get("description", ""),
        "required_expertise": data.get("required_expertise", []),
        "required_publications": int(data.get("required_publications", 0)),
        "required_experience_years": int(data.get("required_experience_years", 0)),
        "availability_required": data.get("availability_required", ""),
        "contribution": data.get("contribution", ""),
        "status": "open",
        "filled_by_user_id": None,
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db["grant_positions"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _ser(doc)


async def list_positions(collab_id: str, db, status: str = None) -> list:
    """List positions for a collaboration, optionally filtered by status."""
    query: dict = {"collaboration_id": collab_id}
    if status:
        query["status"] = status

    docs = await db["grant_positions"].find(query).sort("created_at", 1).to_list(200)
    return [_ser(d) for d in docs]


async def update_position(position_id: str, user_id: str, updates: dict, db) -> dict:
    """Update a position record."""
    try:
        oid = ObjectId(position_id)
    except Exception:
        raise KeyError(f"Invalid position id: {position_id}")

    allowed = {
        "role_title", "description", "required_expertise",
        "required_publications", "required_experience_years",
        "availability_required", "contribution", "status", "filled_by_user_id",
    }
    safe = {k: v for k, v in updates.items() if k in allowed}
    safe["updated_at"] = _now()

    await db["grant_positions"].update_one({"_id": oid}, {"$set": safe})
    doc = await db["grant_positions"].find_one({"_id": oid})
    if not doc:
        raise KeyError(f"Position {position_id} not found")
    return _ser(doc)


# ── invitations ───────────────────────────────────────────────────────────────

async def send_invitation(
    collab_id: str,
    from_user_id: str,
    to_user_id: str,
    role: str,
    message: str,
    position_id: str,
    db,
) -> dict:
    """Send a team invitation. Raises ValueError on duplicates or existing members."""
    # Check for existing pending invitation
    existing = await db["grant_team_invitations"].find_one({
        "collaboration_id": collab_id,
        "to_user_id": to_user_id,
        "status": "pending",
    })
    if existing:
        raise ValueError("A pending invitation already exists for this user in this collaboration")

    # Check if already a team member
    member = await db["grant_team_members"].find_one({
        "collaboration_id": collab_id,
        "user_id": to_user_id,
    })
    if member:
        raise ValueError("User is already a team member of this collaboration")

    now = _now()
    expires = _expires_at()

    doc = {
        "collaboration_id": collab_id,
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "position_id": position_id or None,
        "role": role,
        "message": message,
        "status": "pending",
        "created_at": now,
        "expires_at": expires,
    }
    result = await db["grant_team_invitations"].insert_one(doc)
    doc["_id"] = result.inserted_id

    # If position_id given, mark as pending_fill
    if position_id:
        try:
            await db["grant_positions"].update_one(
                {"_id": ObjectId(position_id)},
                {"$set": {"status": "pending_fill", "updated_at": now}},
            )
        except Exception:
            pass

    return _ser(doc)


async def respond_to_invitation(invitation_id: str, user_id: str, response: str, db) -> dict:
    """Accept or reject a team invitation."""
    if response not in ("accepted", "rejected"):
        raise ValueError("response must be 'accepted' or 'rejected'")

    try:
        oid = ObjectId(invitation_id)
    except Exception:
        raise KeyError(f"Invalid invitation id: {invitation_id}")

    invitation = await db["grant_team_invitations"].find_one({"_id": oid})
    if not invitation:
        raise KeyError(f"Invitation {invitation_id} not found")
    if invitation.get("to_user_id") != user_id:
        raise PermissionError("This invitation is not addressed to you")
    if invitation.get("status") != "pending":
        raise ValueError(f"Invitation is already {invitation.get('status')}")

    # Check expiry
    expires_str = invitation.get("expires_at", "")
    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires_dt:
                await db["grant_team_invitations"].update_one(
                    {"_id": oid},
                    {"$set": {"status": "expired", "updated_at": _now()}},
                )
                raise ValueError("This invitation has expired")
        except ValueError:
            raise
        except Exception:
            pass

    now = _now()
    await db["grant_team_invitations"].update_one(
        {"_id": oid},
        {"$set": {"status": response, "responded_at": now}},
    )

    if response == "accepted":
        collab_id = invitation["collaboration_id"]
        role = invitation.get("role", "member")
        position_id = invitation.get("position_id")

        # Add to team
        existing_member = await db["grant_team_members"].find_one({
            "collaboration_id": collab_id,
            "user_id": user_id,
        })
        if not existing_member:
            await db["grant_team_members"].insert_one({
                "collaboration_id": collab_id,
                "user_id": user_id,
                "role": role,
                "joined_at": now,
            })
            # Increment member_count
            try:
                await db["grant_collaborations"].update_one(
                    {"_id": ObjectId(collab_id)},
                    {"$inc": {"member_count": 1}, "$set": {"updated_at": now}},
                )
            except Exception:
                pass

        # Mark position as filled
        if position_id:
            try:
                await db["grant_positions"].update_one(
                    {"_id": ObjectId(position_id)},
                    {"$set": {"status": "filled", "filled_by_user_id": user_id, "updated_at": now}},
                )
            except Exception:
                pass

    updated = await db["grant_team_invitations"].find_one({"_id": oid})
    return _ser(updated)


# ── team members ──────────────────────────────────────────────────────────────

async def get_team_members(collab_id: str, db) -> list:
    """Return team members joined with user profile data."""
    member_docs = await db["grant_team_members"].find(
        {"collaboration_id": collab_id}
    ).sort("joined_at", 1).to_list(200)

    results = []
    for m in member_docs:
        info = _ser(m)
        uid = m.get("user_id", "")
        if uid:
            try:
                user = await db["users"].find_one(
                    {"_id": ObjectId(uid)},
                    {"first_name": 1, "last_name": 1, "name": 1, "email": 1,
                     "avatar_url": 1, "institution": 1, "institution_id": 1,
                     "career_stage": 1},
                )
                if user:
                    info["user_name"] = (
                        user.get("name")
                        or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                    )
                    info["email"] = user.get("email", "")
                    info["avatar_url"] = user.get("avatar_url", "")
                    info["institution"] = user.get("institution", "")
                    info["institution_id"] = str(user.get("institution_id", ""))
                    info["career_stage"] = user.get("career_stage", "")
            except Exception:
                pass
        results.append(info)

    return results


async def remove_team_member(
    collab_id: str,
    user_id: str,
    target_user_id: str,
    db,
) -> bool:
    """Remove a team member. Only the lead or the member themselves may remove."""
    # Check that requester is lead or is removing themselves
    collab = await db["grant_collaborations"].find_one({"_id": ObjectId(collab_id)})
    if not collab:
        raise KeyError(f"Collaboration {collab_id} not found")

    is_lead = str(collab.get("lead_user_id", "")) == user_id
    is_self = user_id == target_user_id

    if not is_lead and not is_self:
        raise PermissionError("Only the lead or the member themselves may remove a member")

    result = await db["grant_team_members"].delete_one({
        "collaboration_id": collab_id,
        "user_id": target_user_id,
    })

    if result.deleted_count > 0:
        now = _now()
        # Decrement member_count
        try:
            await db["grant_collaborations"].update_one(
                {"_id": ObjectId(collab_id)},
                {"$inc": {"member_count": -1}, "$set": {"updated_at": now}},
            )
        except Exception:
            pass
        return True
    return False
