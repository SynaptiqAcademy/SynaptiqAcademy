"""Conference Hub — Team Formation Service.

Forms a co-author/collaborator team around a conference submission, and backs
every team with a shared Workspace ("Conference Paper" type) via
services.workspace_provisioning — the same "match/team -> shared place to
work" pattern already used for collaboration requests (Phase 2) and grant
collaborations (Phase 3).

Mirrors services.grant_hub.team_formation_service's invite/accept shape
(invitee-side accept, not PI-only) but scoped down: no positions/consortium
complexity, a conference submission team just needs a lead + co-authors.

Collections:
  conference_submission_teams — one per team-forming-around-a-submission
  conference_team_members     — team membership records
  conference_team_invitations — invitation records
  conferences                 — for validating conference_id + enrichment
  users                       — for enriching team member info
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId

from services.workspace_provisioning import provision_workspace


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


# ── team ─────────────────────────────────────────────────────────────────────

async def create_team(user_id: str, user_name: str, data: dict, db) -> dict:
    """Create a submission team for a conference and provision its workspace."""
    conference_id = (data.get("conference_id") or "").strip()
    if not conference_id or not ObjectId.is_valid(conference_id):
        raise ValueError("A valid conference_id is required")

    conference = await db["conferences"].find_one({"_id": ObjectId(conference_id)})
    if not conference:
        raise KeyError(f"Conference {conference_id} not found")

    title = data.get("title") or conference.get("name") or conference.get("title") or "Conference Submission"
    now = _now()
    doc = {
        "conference_id": conference_id,
        "lead_user_id": user_id,
        "title": title,
        "description": data.get("description", ""),
        "workspace_id": "",
        "status": "forming",
        "member_count": 1,
        "created_at": now,
        "updated_at": now,
    }
    result = await db["conference_submission_teams"].insert_one(doc)
    team_id = str(result.inserted_id)
    doc["_id"] = result.inserted_id

    await db["conference_team_members"].insert_one({
        "team_id": team_id,
        "user_id": user_id,
        "role": "lead",
        "joined_at": now,
    })

    try:
        ws = await provision_workspace(
            db, owner_id=user_id, owner_name=user_name or "Someone",
            name=title, workspace_type="Conference Paper",
            description=doc["description"],
            activity_message=f"Workspace auto-created for conference submission \"{title}\".",
        )
        await db["conference_submission_teams"].update_one(
            {"_id": result.inserted_id}, {"$set": {"workspace_id": ws["id"]}}
        )
        doc["workspace_id"] = ws["id"]
    except Exception:
        pass  # non-fatal — team still usable without an auto-workspace

    return _ser(doc)


async def get_team(team_id: str, db) -> dict:
    try:
        oid = ObjectId(team_id)
    except Exception:
        raise KeyError(f"Invalid team id: {team_id}")
    doc = await db["conference_submission_teams"].find_one({"_id": oid})
    if not doc:
        raise KeyError(f"Team {team_id} not found")
    return _ser(doc)


async def list_teams_for_user(user_id: str, db) -> list:
    """Teams the user leads or is a member of."""
    member_entries = await db["conference_team_members"].find({"user_id": user_id}).to_list(200)
    team_ids = [ObjectId(m["team_id"]) for m in member_entries if ObjectId.is_valid(m.get("team_id", ""))]
    if not team_ids:
        return []
    docs = await db["conference_submission_teams"].find({"_id": {"$in": team_ids}}).sort("updated_at", -1).to_list(200)
    return [_ser(d) for d in docs]


# ── team members ─────────────────────────────────────────────────────────────

async def list_team_members(team_id: str, db) -> list:
    """Return team members joined with user profile data."""
    member_docs = await db["conference_team_members"].find({"team_id": team_id}).sort("joined_at", 1).to_list(100)

    results = []
    for m in member_docs:
        info = _ser(m)
        uid = m.get("user_id", "")
        if uid and ObjectId.is_valid(uid):
            user = await db["users"].find_one(
                {"_id": ObjectId(uid)},
                {"full_name": 1, "name": 1, "avatar_url": 1, "institution": 1},
            )
            if user:
                info["user_name"] = user.get("full_name") or user.get("name") or ""
                info["avatar_url"] = user.get("avatar_url", "")
                info["institution"] = user.get("institution", "")
        results.append(info)
    return results


async def remove_team_member(team_id: str, user_id: str, target_user_id: str, db) -> bool:
    """Remove a team member. Only the lead or the member themselves may remove."""
    team = await db["conference_submission_teams"].find_one({"_id": ObjectId(team_id)})
    if not team:
        raise KeyError(f"Team {team_id} not found")

    is_lead = str(team.get("lead_user_id", "")) == user_id
    is_self = user_id == target_user_id
    if not is_lead and not is_self:
        raise PermissionError("Only the lead or the member themselves may remove a member")

    result = await db["conference_team_members"].delete_one({"team_id": team_id, "user_id": target_user_id})
    if result.deleted_count > 0:
        now = _now()
        await db["conference_submission_teams"].update_one(
            {"_id": ObjectId(team_id)}, {"$inc": {"member_count": -1}, "$set": {"updated_at": now}},
        )
        ws_id = team.get("workspace_id")
        if ws_id and ObjectId.is_valid(ws_id):
            try:
                await db["workspaces"].update_one(
                    {"_id": ObjectId(ws_id)},
                    {"$pull": {"members": target_user_id}, "$unset": {f"member_roles.{target_user_id}": ""}},
                )
            except Exception:
                pass
        return True
    return False


# ── invitations ──────────────────────────────────────────────────────────────

async def send_invitation(team_id: str, from_user_id: str, to_user_id: str, role: str, message: str, db) -> dict:
    """Send a team invitation. Raises ValueError on duplicates or existing members."""
    existing = await db["conference_team_invitations"].find_one({
        "team_id": team_id, "to_user_id": to_user_id, "status": "pending",
    })
    if existing:
        raise ValueError("A pending invitation already exists for this user in this team")

    member = await db["conference_team_members"].find_one({"team_id": team_id, "user_id": to_user_id})
    if member:
        raise ValueError("User is already a member of this team")

    now = _now()
    doc = {
        "team_id": team_id,
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "role": role or "co_author",
        "message": message,
        "status": "pending",
        "created_at": now,
        "expires_at": _expires_at(),
    }
    result = await db["conference_team_invitations"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _ser(doc)


async def respond_to_invitation(invitation_id: str, user_id: str, response: str, db) -> dict:
    """Accept or reject a team invitation."""
    if response not in ("accepted", "rejected"):
        raise ValueError("response must be 'accepted' or 'rejected'")

    try:
        oid = ObjectId(invitation_id)
    except Exception:
        raise KeyError(f"Invalid invitation id: {invitation_id}")

    invitation = await db["conference_team_invitations"].find_one({"_id": oid})
    if not invitation:
        raise KeyError(f"Invitation {invitation_id} not found")
    if invitation.get("to_user_id") != user_id:
        raise PermissionError("This invitation is not addressed to you")
    if invitation.get("status") != "pending":
        raise ValueError(f"Invitation is already {invitation.get('status')}")

    expires_str = invitation.get("expires_at", "")
    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires_dt:
                await db["conference_team_invitations"].update_one(
                    {"_id": oid}, {"$set": {"status": "expired", "updated_at": _now()}},
                )
                raise ValueError("This invitation has expired")
        except ValueError:
            raise
        except Exception:
            pass

    now = _now()
    await db["conference_team_invitations"].update_one(
        {"_id": oid}, {"$set": {"status": response, "responded_at": now}},
    )

    if response == "accepted":
        team_id = invitation["team_id"]
        role = invitation.get("role", "co_author")

        existing_member = await db["conference_team_members"].find_one({"team_id": team_id, "user_id": user_id})
        if not existing_member:
            await db["conference_team_members"].insert_one({
                "team_id": team_id, "user_id": user_id, "role": role, "joined_at": now,
            })
            try:
                await db["conference_submission_teams"].update_one(
                    {"_id": ObjectId(team_id)},
                    {"$inc": {"member_count": 1}, "$set": {"updated_at": now}},
                )
            except Exception:
                pass

            # Sync into the linked workspace, same as grants (Phase 3) and
            # collaboration requests (Phase 2) — accepting always lands you
            # inside the shared workspace, not just a roster entry.
            try:
                team = await db["conference_submission_teams"].find_one({"_id": ObjectId(team_id)})
                ws_id = (team or {}).get("workspace_id")
                if ws_id and ObjectId.is_valid(ws_id):
                    await db["workspaces"].update_one(
                        {"_id": ObjectId(ws_id)},
                        {"$addToSet": {"members": user_id},
                         "$set": {f"member_roles.{user_id}": "Co-Author"}},
                    )
            except Exception:
                pass

    updated = await db["conference_team_invitations"].find_one({"_id": oid})
    return _ser(updated)


async def list_my_invitations(user_id: str, db) -> list:
    """Received invitations, enriched with team title."""
    docs = await db["conference_team_invitations"].find({"to_user_id": user_id}).sort("created_at", -1).to_list(100)
    results = []
    for inv in docs:
        item = _ser(inv)
        tid = item.get("team_id")
        if tid and ObjectId.is_valid(tid):
            team = await db["conference_submission_teams"].find_one({"_id": ObjectId(tid)}, {"title": 1})
            item["team_title"] = (team or {}).get("title", "")
        results.append(item)
    return results
