"""Admin Data Governance — GDPR compliance endpoints.

H3: User data export (Right to Portability — GDPR Article 20)
    GET /api/user/export-data               — self-service export
    GET /api/admin/users/{uid}/export-data  — admin-triggered export

Additional:
    POST /api/admin/users/{uid}/anonymize   — GDPR erasure via anonymization
    POST /api/admin/users/{uid}/purge       — hard delete of user data (irreversible)
"""
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from auth_utils import get_current_user, serialize_user
from db import get_db
from services.admin_audit import log_event, request_meta
from services.permissions import require_super_admin
from services.token_service import revoke_all_user_tokens
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(tags=["admin-data-governance"])

# ---------------------------------------------------------------------------
# Integrity repair
# ---------------------------------------------------------------------------

async def _run_integrity_repair(db, dry_run: bool) -> dict:
    """Scan for and optionally repair referential integrity violations.

    Checks:
      1. workspace.members — remove UIDs whose user doc no longer exists
      2. workspace.project_ids — remove project IDs whose project doc no longer exists
      3. project.members — remove UIDs whose user doc no longer exists
      4. manuscript.authors — remove UIDs whose user doc no longer exists
      5. users.connections — remove UIDs whose user doc no longer exists
      6. workspace_invitations with non-existent workspace or user
      7. notifications with non-existent user
      8. orphan tasks (project_id → no project)
      9. orphan milestones (project_id → no project)
    """
    report: dict = {"dry_run": dry_run, "findings": [], "fixed": 0}

    def _note(kind: str, entity_id: str, detail: str):
        report["findings"].append({"kind": kind, "entity_id": entity_id, "detail": detail})

    # 1. workspace.members — orphan user IDs
    async for ws in db.workspaces.find({}, {"_id": 1, "members": 1, "member_roles": 1, "owner_id": 1}):
        ws_id = str(ws["_id"])
        members = ws.get("members") or []
        if not members:
            continue
        member_oids = []
        for m in members:
            try:
                member_oids.append(ObjectId(m))
            except Exception:
                pass
        existing_ids = {str(u["_id"]) async for u in db.users.find({"_id": {"$in": member_oids}}, {"_id": 1})}
        orphan_members = [m for m in members if m not in existing_ids]
        if orphan_members:
            _note("orphan_ws_member", ws_id, f"non-existent user IDs: {orphan_members}")
            if not dry_run:
                pull_ops = {"$pull": {"members": {"$in": orphan_members}}}
                unset_ops = {"$unset": {f"member_roles.{uid}": "" for uid in orphan_members}}
                await db.workspaces.update_one({"_id": ws["_id"]}, pull_ops)
                await db.workspaces.update_one({"_id": ws["_id"]}, unset_ops)
                report["fixed"] += len(orphan_members)

    # 2. workspace.project_ids — orphan project IDs
    async for ws in db.workspaces.find({}, {"_id": 1, "project_ids": 1}):
        ws_id = str(ws["_id"])
        proj_ids = ws.get("project_ids") or []
        if not proj_ids:
            continue
        valid_oids = []
        for p in proj_ids:
            try:
                valid_oids.append(ObjectId(p))
            except Exception:
                pass
        existing_proj_ids = {str(p["_id"]) async for p in db.projects.find({"_id": {"$in": valid_oids}}, {"_id": 1})}
        orphan_proj_ids = [p for p in proj_ids if p not in existing_proj_ids]
        if orphan_proj_ids:
            _note("orphan_ws_project_id", ws_id, f"non-existent project IDs: {orphan_proj_ids}")
            if not dry_run:
                await db.workspaces.update_one(
                    {"_id": ws["_id"]},
                    {"$pull": {"project_ids": {"$in": orphan_proj_ids}}},
                )
                report["fixed"] += len(orphan_proj_ids)

    # 3. project.members — orphan user IDs
    async for proj in db.projects.find({}, {"_id": 1, "members": 1}):
        proj_id = str(proj["_id"])
        members = proj.get("members") or []
        if not members:
            continue
        member_oids = []
        for m in members:
            try:
                member_oids.append(ObjectId(m))
            except Exception:
                pass
        existing_ids = {str(u["_id"]) async for u in db.users.find({"_id": {"$in": member_oids}}, {"_id": 1})}
        orphan_members = [m for m in members if m not in existing_ids]
        if orphan_members:
            _note("orphan_project_member", proj_id, f"non-existent user IDs: {orphan_members}")
            if not dry_run:
                await db.projects.update_one(
                    {"_id": proj["_id"]},
                    {"$pull": {"members": {"$in": orphan_members}}},
                )
                report["fixed"] += len(orphan_members)

    # 4. manuscript.authors — orphan user IDs
    async for ms in db.manuscripts.find({}, {"_id": 1, "authors": 1}):
        ms_id = str(ms["_id"])
        authors = ms.get("authors") or []
        if not authors:
            continue
        author_oids = []
        for a in authors:
            try:
                author_oids.append(ObjectId(a))
            except Exception:
                pass
        existing_ids = {str(u["_id"]) async for u in db.users.find({"_id": {"$in": author_oids}}, {"_id": 1})}
        orphan_authors = [a for a in authors if a not in existing_ids]
        if orphan_authors:
            _note("orphan_manuscript_author", ms_id, f"non-existent user IDs: {orphan_authors}")
            if not dry_run:
                await db.manuscripts.update_one(
                    {"_id": ms["_id"]},
                    {"$pull": {"authors": {"$in": orphan_authors}}},
                )
                report["fixed"] += len(orphan_authors)

    # 5. users.connections — asymmetric or non-existent connections
    async for u in db.users.find({"connections": {"$exists": True, "$ne": []}}, {"_id": 1, "connections": 1}):
        uid = str(u["_id"])
        connections = u.get("connections") or []
        conn_oids = []
        for c in connections:
            try:
                conn_oids.append(ObjectId(c))
            except Exception:
                pass
        existing_ids = {str(p["_id"]) async for p in db.users.find({"_id": {"$in": conn_oids}}, {"_id": 1})}
        orphan_conns = [c for c in connections if c not in existing_ids]
        if orphan_conns:
            _note("orphan_connection", uid, f"connections to non-existent users: {orphan_conns}")
            if not dry_run:
                await db.users.update_one(
                    {"_id": u["_id"]},
                    {"$pull": {"connections": {"$in": orphan_conns}}},
                )
                report["fixed"] += len(orphan_conns)

    # 6. workspace_invitations with non-existent workspace
    async for inv in db.workspace_invitations.find({}, {"_id": 1, "workspace_id": 1}):
        inv_id = str(inv["_id"])
        ws_id = inv.get("workspace_id")
        if not ws_id:
            continue
        try:
            ws = await db.workspaces.find_one({"_id": ObjectId(ws_id)}, {"_id": 1})
        except Exception:
            ws = None
        if not ws:
            _note("orphan_ws_invitation", inv_id, f"workspace {ws_id} does not exist")
            if not dry_run:
                await db.workspace_invitations.delete_one({"_id": inv["_id"]})
                report["fixed"] += 1

    # 7. orphan notifications (user_id → no user)
    async for notif in db.notifications.find({}, {"_id": 1, "user_id": 1}):
        uid = notif.get("user_id")
        if not uid:
            continue
        try:
            exists = await db.users.find_one({"_id": ObjectId(uid)}, {"_id": 1})
        except Exception:
            exists = None
        if not exists:
            _note("orphan_notification", str(notif["_id"]), f"user {uid} does not exist")
            if not dry_run:
                await db.notifications.delete_one({"_id": notif["_id"]})
                report["fixed"] += 1

    # 8. orphan tasks (project_id → no project)
    async for task in db.tasks.find({}, {"_id": 1, "project_id": 1}):
        pid = task.get("project_id")
        if not pid:
            continue
        try:
            exists = await db.projects.find_one({"_id": ObjectId(pid)}, {"_id": 1})
        except Exception:
            exists = None
        if not exists:
            _note("orphan_task", str(task["_id"]), f"project {pid} does not exist")
            if not dry_run:
                await db.tasks.delete_one({"_id": task["_id"]})
                report["fixed"] += 1

    # 9. orphan milestones (project_id → no project)
    async for ms in db.milestones.find({}, {"_id": 1, "project_id": 1}):
        pid = ms.get("project_id")
        if not pid:
            continue
        try:
            exists = await db.projects.find_one({"_id": ObjectId(pid)}, {"_id": 1})
        except Exception:
            exists = None
        if not exists:
            _note("orphan_milestone", str(ms["_id"]), f"project {pid} does not exist")
            if not dry_run:
                await db.milestones.delete_one({"_id": ms["_id"]})
                report["fixed"] += 1

    report["total_findings"] = len(report["findings"])
    return report


@router.post("/api/admin/integrity/repair")
async def integrity_repair(
    request: Request,
    body: dict = None,
    admin: dict = Depends(require_super_admin),
):
    """Scan all collections for referential integrity violations.

    Pass body {"dry_run": false} to auto-fix. Default is dry_run=true (scan only).
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    dry_run = (body or {}).get("dry_run", True)
    report = await _run_integrity_repair(db, dry_run=dry_run)
    await log_event(
        "admin.integrity.repair",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id="platform", ip=request_meta(request)["ip"],
        extra={"dry_run": dry_run, "findings": report["total_findings"], "fixed": report["fixed"]},
    )
    return report

_EXPORT_LIMIT = 1000  # max records per collection in export


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_oid(uid: str) -> ObjectId:
    try:
        return ObjectId(uid)
    except (InvalidId, Exception):
        raise HTTPException(status_code=400, detail="Invalid user ID")


def _strip_oids(docs: list) -> list:
    out = []
    for d in docs:
        d = dict(d)
        d["id"] = str(d.pop("_id", ""))
        out.append(d)
    return out


async def _collect_user_data(db, uid: str) -> dict:
    """Aggregate all data belonging to a user across collections."""
    async def _q(collection, filt: dict) -> list:
        return _strip_oids(
            await getattr(db, collection).find(filt).sort("created_at", -1).limit(_EXPORT_LIMIT).to_list(_EXPORT_LIMIT)
        )

    user_doc = await db.users.find_one({"_id": ObjectId(uid)})
    if not user_doc:
        return {}

    safe_user = serialize_user(user_doc)
    # Remove sensitive fields from export
    safe_user.pop("password_hash", None)

    (
        projects, workspaces, manuscripts, publications, collaborations,
        messages, credit_txns, billing_hist, audit_events,
    ) = await asyncio.gather(
        _q("projects", {"owner_id": uid}),
        _q("workspaces", {"owner_id": uid}),
        _q("manuscripts", {"lead_author_id": uid}),
        _q("publications", {"owner_id": uid}),
        _q("collaborations", {"$or": [{"owner_id": uid}, {"member_ids": uid}]}),
        _q("messages", {"sender_id": uid}),
        _q("credit_transactions", {"user_id": uid}),
        _q("billing_history", {"user_id": uid}),
        _q("audit_log", {"actor_id": uid}),
    )

    return {
        "export_generated_at": _now_iso(),
        "user_id": uid,
        "profile": safe_user,
        "projects": projects,
        "workspaces": workspaces,
        "manuscripts": manuscripts,
        "publications": publications,
        "collaborations": collaborations,
        "messages": messages,
        "credit_transactions": credit_txns,
        "billing_history": billing_hist,
        "audit_log_events": audit_events,
    }


# ---------------------------------------------------------------------------
# Self-service export
# ---------------------------------------------------------------------------

@router.get("/api/user/export-data")
async def export_my_data(user: dict = Depends(get_current_user)):
    """GDPR Article 20 — Right to Data Portability. Returns all user data as JSON."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    data = await _collect_user_data(db, user["id"])
    payload = json.dumps(data, indent=2, default=str).encode()
    filename = f"synaptiq-data-{user['id']}.json"
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Admin-triggered export
# ---------------------------------------------------------------------------

@router.get("/api/admin/users/{uid}/export-data")
async def admin_export_user_data(uid: str, request: Request, admin: dict = Depends(require_super_admin)):
    """Admin: export all data for a specific user (for support/compliance)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    data = await _collect_user_data(db, uid)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    await log_event(
        "admin.gdpr.export",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, ip=request_meta(request)["ip"],
    )
    payload = json.dumps(data, indent=2, default=str).encode()
    filename = f"synaptiq-export-{uid}.json"
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Anonymize (GDPR Article 17 — Right to Erasure, soft form)
# ---------------------------------------------------------------------------

@router.post("/api/admin/users/{uid}/anonymize")
async def anonymize_user(uid: str, request: Request, admin: dict = Depends(require_super_admin)):
    """Replace all identifying information with anonymized placeholders.
    The account remains in the DB to preserve referential integrity but is
    stripped of all PII. This satisfies GDPR Article 17 in most cases.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if zt_is_super_admin(user):
        raise HTTPException(status_code=400, detail="Cannot anonymize a super admin account")

    import hashlib
    uid_hash = hashlib.sha256(uid.encode()).hexdigest()[:8]
    anon_email = f"deleted-{uid_hash}@deleted.synaptiq.invalid"

    await revoke_all_user_tokens(uid)
    await db.users.update_one(
        {"_id": oid},
        {"$set": {
            "email": anon_email,
            "full_name": "Deleted User",
            "first_name": "Deleted",
            "last_name": "User",
            "biography": "",
            "institution": "",
            "department": "",
            "country": "",
            "avatar_url": "",
            "orcid": None,
            "google_id": None,
            "google_email": None,
            "research_areas": [],
            "research_interests": [],
            "research_keywords": [],
            "skills": [],
            "status": "banned",
            "deleted": True,
            "anonymized": True,
            "anonymized_at": _now_iso(),
            "anonymized_by": admin.get("email"),
            "email_marketing_consent": False,
        }},
    )
    await log_event(
        "admin.gdpr.anonymize",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, ip=request_meta(request)["ip"],
        extra={"original_email": user.get("email")},
    )
    return {"ok": True, "anonymized": True, "new_email": anon_email}


# ---------------------------------------------------------------------------
# Hard purge (GDPR — complete erasure)
# ---------------------------------------------------------------------------

class PurgeConfirm(dict):
    pass


async def _purge_user_owned_data(db, uid: str) -> None:
    """Delete every piece of data this user owns, across every collection
    that stores a reference to them — everything except the users document
    itself (callers delete that separately, since single-user purge and
    bulk platform-reset batch it differently).

    Shared by purge_user() (single-account GDPR erasure) and the platform
    reset tool (routers/admin_platform_reset.py) so there is exactly one
    place that has to know about every user-owned collection.
    """
    await revoke_all_user_tokens(uid)

    # Collect a couple of id sets we need for two-level cascades (delete a
    # child collection keyed by a parent id, where the parent is itself
    # keyed by user_id) before the parent docs are deleted below.
    ai_conv_ids = [
        str(d["_id"]) async for d in db.ai_conversations.find({"user_id": uid}, {"_id": 1})
    ]

    # Delete across all collections — full cascade
    await asyncio.gather(
        # Owned entities
        db.projects.delete_many({"owner_id": uid}),
        db.workspaces.delete_many({"owner_id": uid}),
        db.manuscripts.delete_many({"lead_author_id": uid}),
        db.publications.delete_many({"owner_id": uid}),
        db.repository_items.delete_many({"owner_id": uid}),
        # Financial records
        db.credit_transactions.delete_many({"user_id": uid}),
        db.credit_purchases.delete_many({"user_id": uid}),
        db.credit_usage.delete_many({"user_id": uid}),
        db.billing_history.delete_many({"user_id": uid}),
        db.subscriptions.delete_many({"user_id": uid}),
        db.subscription_history.delete_many({"user_id": uid}),
        # Auth records
        db.refresh_tokens.delete_many({"user_id": uid}),
        db.email_verifications.delete_many({"user_id": uid}),
        db.password_resets.delete_many({"user_id": uid}),
        db.trusted_devices.delete_many({"user_id": uid}),
        db.mfa_configs.delete_many({"user_id": uid}),
        # Notifications & consent
        db.notifications.delete_many({"user_id": uid}),
        db.consent_records.delete_many({"user_id": uid}),
        db.email_preferences.delete_many({"user_id": uid}),
        # Social / collaboration records
        db.workspace_invitations.delete_many(
            {"$or": [{"user_id": uid}, {"invited_by": uid}]}),
        db.connection_requests.delete_many(
            {"$or": [{"sender_id": uid}, {"receiver_id": uid}]}),
        db.collaboration_requests.delete_many(
            {"$or": [{"sender_id": uid}, {"receiver_id": uid}]}),
        db.marketplace_invitations.delete_many(
            {"$or": [{"from_user_id": uid}, {"to_user_id": uid}]}),
        # review_requests holds two different schemas in the same collection:
        # research_os.py's manuscript reviews (reviewer_id/requested_by) and
        # reviewer_marketplace.py's marketplace requests (requester_user_id).
        db.review_requests.delete_many(
            {"$or": [{"reviewer_id": uid}, {"requested_by": uid}, {"requester_user_id": uid}]}),
        db.review_assignments.delete_many({"reviewer_user_id": uid}),
        db.reviewer_profiles.delete_many({"user_id": uid}),
        # Manuscript contributions / comments / versions by this user
        db.manuscript_contributions.delete_many({"user_id": uid}),
        db.manuscript_comments.delete_many({"author_id": uid}),
        db.manuscript_versions.delete_many({"author_id": uid}),
        db.manuscript_reviews.delete_many({"user_id": uid}),
        # Files owned by user
        db.files.delete_many({"owner_id": uid}),
        db.file_activity.delete_many({"actor_id": uid}),
        # AI records
        db.ai_requests.delete_many({"user_id": uid}),
        db.abstract_generations.delete_many({"user_id": uid}),
        db.literature_reviews.delete_many({"user_id": uid}),
        db.research_gap_reviews.delete_many({"user_id": uid}),
        db.research_design_reviews.delete_many({"user_id": uid}),
        db.statistical_reviews.delete_many({"user_id": uid}),
        db.rewriting_requests.delete_many({"user_id": uid}),
        db.ai_conversations.delete_many({"user_id": uid}),
        db.copilot_conversations.delete_many({"user_id": uid}),
        db.knowledge_documents.delete_many({"user_id": uid}),
        db.knowledge_chunks.delete_many({"user_id": uid}),
        # Direct messaging
        db.messages.delete_many({"sender_id": uid}),
        db.conversations.delete_many({"created_by": uid}),
        db.conversation_members.delete_many({"user_id": uid}),
        # Activity trails
        db.workspace_activity.delete_many({"actor_id": uid}),
        db.collaboration_activity.delete_many({"user_id": uid}),
        # Chat
        db.chat_sessions.delete_many({"user_id": uid}),
        db.saved_searches.delete_many({"user_id": uid}),
        db.discovery_usage.delete_many({"user_id": uid}),
        db.user_research_goals.delete_many({"user_id": uid}),
        # Referrals
        db.referrals.delete_many({"referrer_id": uid}),
        db.referrals.delete_many({"referee_id": uid}),
        # Workspace items (Notion-style docs/tasks)
        db.workspace_items.delete_many({"creator_id": uid}),
        db.item_comments.delete_many({"user_id": uid}),
        # Profile / reputation / trust / verification
        db.saved_researchers.delete_many({"$or": [{"user_id": uid}, {"saved_user_id": uid}]}),
        db.profile_followers.delete_many({"$or": [{"follower_id": uid}, {"following_id": uid}]}),
        db.public_profiles.delete_many({"user_id": uid}),
        db.reputation_scores.delete_many({"user_id": uid}),
        db.reputation_badges.delete_many({"user_id": uid}),
        db.reputation_events.delete_many({"user_id": uid}),
        db.research_reputation.delete_many({"user_id": uid}),
        db.research_reputation_events.delete_many({"user_id": uid}),
        db.research_reputation_badges.delete_many({"user_id": uid}),
        db.research_impact.delete_many({"user_id": uid}),
        db.verification_profiles.delete_many({"user_id": uid}),
        db.verification_requests.delete_many({"user_id": uid}),
        db.verification_badges.delete_many({"user_id": uid}),
        db.trust_verifications.delete_many({"user_id": uid}),
        db.trust_requests.delete_many({"user_id": uid}),
        db.trust_audit.delete_many({"user_id": uid}),
        db.trust_passports.delete_many({"user_id": uid}),
        # SIE (self-improvement engine)
        db.sie_career.delete_many({"user_id": uid}),
        db.sie_roadmaps.delete_many({"user_id": uid}),
        db.sie_missions.delete_many({"user_id": uid}),
        db.sie_memory.delete_many({"user_id": uid}),
        db.sie_goals.delete_many({"user_id": uid}),
        db.sie_automations.delete_many({"user_id": uid}),
        db.sie_commands.delete_many({"user_id": uid}),
        db.sie_daily_agenda.delete_many({"user_id": uid}),
        db.sie_progress_snapshots.delete_many({"user_id": uid}),
        db.sie_weekly_plan.delete_many({"user_id": uid}),
        db.sie_recommendations.delete_many({"user_id": uid}),
        # Network hub
        db.network_settings.delete_many({"user_id": uid}),
        db.network_group_members.delete_many({"user_id": uid}),
        db.network_community_members.delete_many({"user_id": uid}),
        db.network_collaborations.delete_many({"owner_id": uid}),
        db.network_event_registrations.delete_many({"user_id": uid}),
        db.network_mentors.delete_many({"user_id": uid}),
        db.network_mentorship_requests.delete_many(
            {"$or": [{"mentee_id": uid}, {"mentor_user_id": uid}]}),
        db.network_recommendations.delete_many({"user_id": uid}),
        # Academic Marketplace
        db.mkt_providers.delete_many({"user_id": uid}),
        db.mkt_orders.delete_many({"$or": [{"buyer_user_id": uid}, {"provider_user_id": uid}]}),
        db.mkt_wallet.delete_many({"user_id": uid}),
        db.mkt_ratings.delete_many({"provider_user_id": uid}),
        # Teaching OS
        db.teaching_lessons.delete_many({"owner_id": uid}),
        db.teaching_assessments.delete_many({"owner_id": uid}),
        db.teaching_workspaces.delete_many({"owner_id": uid}),
        # Conference team-forming
        db.conference_submission_teams.delete_many({"lead_user_id": uid}),
        db.conference_team_members.delete_many({"user_id": uid}),
        # Grant Hub team formation
        db.grant_team_members.delete_many({"user_id": uid}),
        db.grant_team_invitations.delete_many({"user_id": uid}),
        db.grant_collaborations.delete_many({"user_id": uid}),
    )
    # Child rows keyed by a parent id collected above
    if ai_conv_ids:
        await db.ai_messages.delete_many({"conv_id": {"$in": ai_conv_ids}})

    # Remove user from others' membership arrays (non-owned entities)
    await asyncio.gather(
        db.workspaces.update_many(
            {"members": uid},
            {"$pull": {"members": uid}, "$unset": {f"member_roles.{uid}": ""}},
        ),
        db.projects.update_many(
            {"members": uid},
            {"$pull": {"members": uid}},
        ),
        db.manuscripts.update_many(
            {"authors": uid},
            {"$pull": {"authors": uid}},
        ),
        db.users.update_many(
            {"connections": uid},
            {"$pull": {"connections": uid}},
        ),
        db.workspace_items.update_many(
            {"assignee_ids": uid},
            {"$pull": {"assignee_ids": uid}},
        ),
        db.teaching_workspaces.update_many(
            {"member_ids": uid},
            {"$pull": {"member_ids": uid}, "$unset": {f"member_roles.{uid}": ""}},
        ),
    )


@router.delete("/api/admin/users/{uid}/purge")
async def purge_user(uid: str, request: Request, body: dict, admin: dict = Depends(require_super_admin)):
    """Permanently delete all user data across all collections.
    Requires body: {"confirm": "PURGE_CONFIRMED"} to prevent accidental use.
    This is irreversible.
    """
    if (body or {}).get("confirm") != "PURGE_CONFIRMED":
        raise HTTPException(
            status_code=400,
            detail="Set body confirm='PURGE_CONFIRMED' to execute purge. This is irreversible.",
        )

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if zt_is_super_admin(user):
        raise HTTPException(status_code=400, detail="Cannot purge a super admin account")

    original_email = user.get("email", "")
    await _purge_user_owned_data(db, uid)
    await db.users.delete_one({"_id": oid})

    await log_event(
        "admin.gdpr.purge",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, ip=request_meta(request)["ip"],
        extra={"original_email": original_email},
    )
    return {"ok": True, "purged": True, "user_id": uid}
