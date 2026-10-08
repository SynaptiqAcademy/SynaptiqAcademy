"""Conference Submission Teams — form a co-author team around a conference
submission, backed by a shared Workspace ("Conference Paper" type).

Endpoints:
  POST   /api/conference-teams                    — create a team for a conference
  GET    /api/conference-teams/mine                — teams I lead or belong to
  GET    /api/conference-teams/invitations/my      — invitations sent to me
  GET    /api/conference-teams/{team_id}           — team detail + members
  POST   /api/conference-teams/{team_id}/invite    — invite a co-author
  POST   /api/conference-teams/invitations/{inv_id}/respond — accept/reject
  DELETE /api/conference-teams/{team_id}/members/{uid} — remove a member
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy

router = APIRouter(prefix="/api/conference-teams", tags=["conference-teams"])


class CreateTeamBody(BaseModel):
    conference_id: str
    title: Optional[str] = None
    description: str = ""


class SendInvitationBody(BaseModel):
    to_user_id: str
    role: str = "co_author"
    message: str = ""


class InvitationResponseBody(BaseModel):
    response: str  # "accepted" or "rejected"


@router.post("", status_code=201)
async def create_team(
    body: CreateTeamBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Start a submission team for a conference (creates a shared workspace)."""
    db = make_db_proxy(db, user)
    from services.conference_hub.team_service import create_team as _create_team
    try:
        return await _create_team(user["id"], user.get("full_name", ""), body.dict(), db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/mine")
async def my_teams(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Teams the current user leads or belongs to."""
    db = make_db_proxy(db, user)
    from services.conference_hub.team_service import list_teams_for_user
    teams = await list_teams_for_user(user["id"], db)
    return {"teams": teams, "total": len(teams)}


@router.get("/invitations/my")
async def my_invitations(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Invitations sent to the current user."""
    db = make_db_proxy(db, user)
    from services.conference_hub.team_service import list_my_invitations
    invitations = await list_my_invitations(user["id"], db)
    return {"invitations": invitations, "total": len(invitations)}


@router.get("/{team_id}")
async def get_team_detail(
    team_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Team detail + members (members-only)."""
    db = make_db_proxy(db, user)
    from services.conference_hub.team_service import get_team, list_team_members
    try:
        team = await get_team(team_id, db)
    except KeyError:
        raise HTTPException(status_code=404, detail="Team not found")
    members = await list_team_members(team_id, db)
    is_member = any(m.get("user_id") == user["id"] for m in members)
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return {**team, "members": members}


@router.post("/{team_id}/invite")
async def send_invitation(
    team_id: str,
    body: SendInvitationBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Invite a co-author to this submission team (lead-only)."""
    db = make_db_proxy(db, user)
    from services.conference_hub.team_service import get_team, send_invitation as _send_invitation
    try:
        team = await get_team(team_id, db)
    except KeyError:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.get("lead_user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the team lead can invite members")
    try:
        return await _send_invitation(team_id, user["id"], body.to_user_id, body.role, body.message, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invitations/{inv_id}/respond")
async def respond_invitation(
    inv_id: str,
    body: InvitationResponseBody,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Accept or reject a conference team invitation."""
    db = make_db_proxy(db, user)
    from services.conference_hub.team_service import respond_to_invitation
    try:
        return await respond_to_invitation(inv_id, user["id"], body.response, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{team_id}/members/{uid}")
async def remove_member(
    team_id: str,
    uid: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Remove a team member (lead or self-removal)."""
    db = make_db_proxy(db, user)
    from services.conference_hub.team_service import remove_team_member
    try:
        removed = await remove_team_member(team_id, user["id"], uid, db)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"removed": True}
