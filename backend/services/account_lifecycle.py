"""Account lifecycle: what happens to each kind of data when a member exports
their data or deletes their account. The single place that knows both.

Deletion matrix (self-service DELETE /api/users/me):

  DELETE     Private to the member: AI conversations, messages and memory,
             knowledge documents and their embeddings, saved searches,
             research goals and plans, notes and meetings they own, team
             blueprints, notifications, connection/collaboration requests and
             invitations, memberships, followers and saved researchers,
             reputation/verification records, sessions and sign-in tokens,
             consent records linked to the account; projects, workspaces and
             manuscripts nobody else has access to, with everything inside
             them; files they uploaded there (including the stored bytes).

  ANONYMISE  The account record itself (name, email, profile, ORCID/Google
             links removed; replaced by "Deleted user") so content shared
             with others keeps working: messages sent to others, comments
             and contributions in shared manuscripts and workspaces, files
             uploaded to shared spaces.

  TRANSFER   Shared projects, workspaces and manuscripts the member owned or
             led pass to another member/author so they stay manageable.

  RETAIN     Billing records (invoices, payments, subscriptions, credit
             purchases and ledger) for tax and accounting law, linked only to
             the anonymised account; security events and audit records until
             their period in retention_policy.py ends. LEGAL REVIEW REQUIRED
             for the billing period.

  PRESERVE   An account under a legal hold (``legal_hold: true``, set by an
             administrator) cannot be self-deleted; the member is told to
             contact us.

Backups are not rewritten; deleted data disappears from them as they are
overwritten on the database provider's backup cycle.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

logger = logging.getLogger("synaptiq.account_lifecycle")

# ── Matrix ────────────────────────────────────────────────────────────────────
# (collection, filter-builder) — private records deleted outright.
_PRIVATE: tuple[tuple[str, Any], ...] = (
    # AI
    ("ai_conversations", lambda u: {"user_id": u}),
    ("ai_requests", lambda u: {"user_id": u}),
    ("ai_memory", lambda u: {"user_id": u}),
    ("ai_actions", lambda u: {"user_id": u}),
    ("ai_task_lists", lambda u: {"user_id": u}),
    ("copilot_conversations", lambda u: {"user_id": u}),
    ("chat_sessions", lambda u: {"user_id": u}),
    ("chat_messages", lambda u: {"user_id": u}),
    ("abstract_generations", lambda u: {"user_id": u}),
    ("literature_reviews", lambda u: {"user_id": u}),
    ("research_gap_reviews", lambda u: {"user_id": u}),
    ("research_design_reviews", lambda u: {"user_id": u}),
    ("statistical_reviews", lambda u: {"user_id": u}),
    ("rewriting_requests", lambda u: {"user_id": u}),
    ("knowledge_documents", lambda u: {"user_id": u}),
    ("knowledge_chunks", lambda u: {"user_id": u}),       # embeddings
    ("credit_reservations", lambda u: {"user_id": u}),
    # Planning, notes, searches
    ("saved_searches", lambda u: {"user_id": u}),
    ("search_queries", lambda u: {"user_id": u}),
    ("discovery_usage", lambda u: {"user_id": u}),
    ("user_research_goals", lambda u: {"user_id": u}),
    ("team_blueprints", lambda u: {"owner_id": u}),
    ("expertise_requests", lambda u: {"$or": [{"owner_id": u}, {"created_by": u}]}),
    ("meetings", lambda u: {"owner_id": u}),
    ("meeting_notes", lambda u: {"owner_id": u}),
    ("timeline_events", lambda u: {"user_id": u}),
    ("timeline_milestones", lambda u: {"user_id": u}),
    ("session_events", lambda u: {"user_id": u}),
    ("collaboration_recommendations", lambda u: {"user_id": u}),
    ("network_recommendations", lambda u: {"user_id": u}),
    ("network_settings", lambda u: {"user_id": u}),
    ("sie_career", lambda u: {"user_id": u}),
    ("sie_roadmaps", lambda u: {"user_id": u}),
    ("sie_missions", lambda u: {"user_id": u}),
    ("sie_memory", lambda u: {"user_id": u}),
    ("sie_goals", lambda u: {"user_id": u}),
    ("sie_automations", lambda u: {"user_id": u}),
    ("sie_commands", lambda u: {"user_id": u}),
    ("sie_daily_agenda", lambda u: {"user_id": u}),
    ("sie_progress_snapshots", lambda u: {"user_id": u}),
    ("sie_weekly_plan", lambda u: {"user_id": u}),
    ("sie_recommendations", lambda u: {"user_id": u}),
    # Profile, reputation, verification
    ("public_profiles", lambda u: {"user_id": u}),
    ("profile_showcases", lambda u: {"user_id": u}),
    ("profile_views", lambda u: {"profile_user_id": u}),
    ("profile_followers", lambda u: {"$or": [{"follower_id": u}, {"following_id": u}]}),
    ("saved_researchers", lambda u: {"$or": [{"user_id": u}, {"saved_user_id": u}]}),
    ("reputation_scores", lambda u: {"user_id": u}),
    ("reputation_badges", lambda u: {"user_id": u}),
    ("reputation_events", lambda u: {"user_id": u}),
    ("research_reputation", lambda u: {"user_id": u}),
    ("research_reputation_events", lambda u: {"user_id": u}),
    ("research_reputation_badges", lambda u: {"user_id": u}),
    ("research_impact", lambda u: {"user_id": u}),
    ("research_impact_history", lambda u: {"user_id": u}),
    ("research_impact_snapshots", lambda u: {"user_id": u}),
    ("verification_profiles", lambda u: {"user_id": u}),
    ("verification_requests", lambda u: {"user_id": u}),
    ("verification_badges", lambda u: {"user_id": u}),
    ("trust_verifications", lambda u: {"user_id": u}),
    ("trust_requests", lambda u: {"user_id": u}),
    ("trust_passports", lambda u: {"user_id": u}),
    ("trust_scores", lambda u: {"user_id": u}),
    ("trust_badges", lambda u: {"user_id": u}),
    ("reviewer_profiles", lambda u: {"user_id": u}),
    ("publications", lambda u: {"owner_id": u}),
    ("repository_items", lambda u: {"owner_id": u}),
    # Requests, invitations, memberships
    ("connection_requests", lambda u: {"$or": [{"sender_id": u}, {"receiver_id": u}]}),
    ("collaboration_requests", lambda u: {"$or": [{"sender_id": u}, {"receiver_id": u}]}),
    ("marketplace_invitations", lambda u: {"$or": [{"from_user_id": u}, {"to_user_id": u}]}),
    ("workspace_invitations", lambda u: {"$or": [{"user_id": u}, {"invited_by": u}]}),
    ("conference_team_invitations", lambda u: {"$or": [{"from_user_id": u}, {"to_user_id": u}]}),
    ("grant_team_invitations", lambda u: {"$or": [{"from_user_id": u}, {"to_user_id": u}]}),
    ("network_mentorship_requests", lambda u: {"$or": [{"mentee_id": u}, {"mentor_user_id": u}]}),
    ("institution_memberships", lambda u: {"user_id": u}),
    ("team_memberships", lambda u: {"user_id": u}),
    ("conversation_members", lambda u: {"user_id": u}),
    ("conference_team_members", lambda u: {"user_id": u}),
    ("grant_team_members", lambda u: {"user_id": u}),
    ("network_group_members", lambda u: {"user_id": u}),
    ("network_community_members", lambda u: {"user_id": u}),
    ("network_event_registrations", lambda u: {"user_id": u}),
    ("network_mentors", lambda u: {"user_id": u}),
    # Notifications, consent, sign-in
    ("notifications", lambda u: {"user_id": u}),
    ("email_preferences", lambda u: {"user_id": u}),
    ("consent_records", lambda u: {"user_id": u}),
    ("refresh_tokens", lambda u: {"user_id": u}),
    ("email_verifications", lambda u: {"user_id": u}),
    ("password_resets", lambda u: {"user_id": u}),
    ("institution_email_verifications", lambda u: {"user_id": u}),
    ("trusted_devices", lambda u: {"user_id": u}),
    ("mfa_configs", lambda u: {"user_id": u}),
    ("mfa_pending", lambda u: {"user_id": u}),
)

# Kept after deletion, linked only to the anonymised account.
RETAINED = (
    "billing_history", "billing_events", "subscriptions", "subscription_history",
    "credit_purchases", "credit_transactions", "credit_usage",
    "security_events", "audit_log",
)

# Children of an owned container that is deleted with it.
_CHILDREN = {
    "projects": (("tasks", "project_id"), ("milestones", "project_id"),
                 ("literature", "project_id"), ("workspace_items", "project_id")),
    "workspaces": (("workspace_items", "workspace_id"), ("workspace_activity", "workspace_id"),
                   ("item_comments", "workspace_id"), ("wiki_page_versions", "workspace_id")),
    "manuscripts": (("manuscript_versions", "manuscript_id"), ("manuscript_comments", "manuscript_id"),
                    ("manuscript_references", "manuscript_id"), ("manuscript_reviews", "manuscript_id"),
                    ("manuscript_contributions", "manuscript_id")),
}
_FILE_KIND = {"projects": "project", "workspaces": "workspace", "manuscripts": "manuscript"}


class DeletionBlocked(Exception):
    """The account can't be deleted yet; ``str(e)`` is shown to the member."""


def _others(doc: dict, uid: str, *fields: str) -> list[str]:
    seen: list[str] = []
    for f in fields:
        for m in doc.get(f) or []:
            m = str(m)
            if m != uid and m not in seen:
                seen.append(m)
    return seen


async def preflight(db, user: dict) -> None:
    """Raise DeletionBlocked when deletion would leave something unmanageable
    or is not allowed."""
    if user.get("role") == "super_admin" or user.get("is_super_admin"):
        raise DeletionBlocked("Administrator accounts can't be deleted here.")
    full = await db.users.find_one({"_id": ObjectId(user["id"])}, {"legal_hold": 1}) or {}
    if full.get("legal_hold"):
        raise DeletionBlocked("This account can't be deleted right now. Please contact us.")
    uid = user["id"]
    async for m in db.institution_memberships.find(
            {"user_id": uid, "status": "approved", "role": {"$in": ["owner", "admin"]}}, {"institution_id": 1}):
        iid = m.get("institution_id")
        other_admins = await db.institution_memberships.count_documents({
            "institution_id": iid, "status": "approved",
            "role": {"$in": ["owner", "admin"]}, "user_id": {"$ne": uid}})
        other_members = await db.institution_memberships.count_documents({
            "institution_id": iid, "status": "approved", "user_id": {"$ne": uid}})
        if other_members and not other_admins:
            raise DeletionBlocked(
                "You're the only administrator of an institution that has other members. "
                "Make someone else an administrator first, then delete your account.")


async def _delete_files(db, flt: dict) -> int:
    from services import storage_service as S
    n = 0
    async for f in db.files.find(flt, {"storage_path": 1}):
        if f.get("storage_path"):
            await asyncio.to_thread(S.delete_object, f["storage_path"])
        n += 1
    if n:
        await db.files.delete_many(flt)
    return n


async def _containers(db, uid: str, summary: dict) -> None:
    """Owned projects/workspaces/manuscripts: delete private ones with their
    contents; hand shared ones to another member and leave them in place."""
    specs = (
        ("projects", {"owner_id": uid}, "owner_id", ("members",)),
        ("workspaces", {"owner_id": uid}, "owner_id", ("members",)),
        ("manuscripts", {"lead_author_id": uid}, "lead_author_id", ("authors",)),
    )
    for coll, flt, owner_field, member_fields in specs:
        deleted, transferred = [], 0
        async for d in getattr(db, coll).find(flt):
            others = _others(d, uid, *member_fields)
            if others:
                await getattr(db, coll).update_one({"_id": d["_id"]}, {"$set": {
                    owner_field: others[0],
                    "ownership_transferred_at": datetime.now(timezone.utc).isoformat(),
                    "ownership_transferred_reason": "previous owner deleted their account",
                }})
                transferred += 1
            elif d.get("visibility") == "public":
                # Published for everyone: keep it, credited to "Deleted user".
                transferred += 1
            else:
                deleted.append(d["_id"])
        if deleted:
            ids = [str(i) for i in deleted]
            for child, key in _CHILDREN[coll]:
                await getattr(db, child).delete_many({key: {"$in": ids}})
            summary["files"] += await _delete_files(db, {"entity_kind": _FILE_KIND[coll], "entity_id": {"$in": ids}})
            await getattr(db, coll).delete_many({"_id": {"$in": deleted}})
        summary[f"{coll}_deleted"] = len(deleted)
        summary[f"{coll}_kept_for_others"] = transferred

    # Remove the member from things other people own.
    await asyncio.gather(
        db.workspaces.update_many({"members": uid}, {"$pull": {"members": uid}, "$unset": {f"member_roles.{uid}": ""}}),
        db.projects.update_many({"members": uid}, {"$pull": {"members": uid}}),
        db.users.update_many({"connections": uid}, {"$pull": {"connections": uid}}),
        db.workspace_items.update_many({"assignee_ids": uid}, {"$pull": {"assignee_ids": uid}}),
        db.teaching_workspaces.update_many({"member_ids": uid}, {"$pull": {"member_ids": uid}, "$unset": {f"member_roles.{uid}": ""}}),
    )
    # Manuscripts keep the author id so authorship history stays intact; the
    # id now resolves to "Deleted user".


async def delete_account(db, user: dict, *, actor: str = "self") -> dict:
    """Run the deletion matrix for ``user``. Returns a summary of counts."""
    uid = user["id"]
    await preflight(db, user)
    summary: dict[str, int] = {"files": 0}

    from services.token_service import revoke_all_user_tokens
    try:
        await revoke_all_user_tokens(uid)
    except Exception as exc:
        logger.warning("token revocation during deletion failed: %s", exc)

    # AI conversation messages hang off the conversation id.
    conv_ids = [str(d["_id"]) async for d in db.ai_conversations.find({"user_id": uid}, {"_id": 1})]
    if conv_ids:
        await db.ai_messages.delete_many({"conv_id": {"$in": conv_ids}})

    await _containers(db, uid, summary)
    # Files the member uploaded to spaces that stay (shared) are kept for the
    # people who still work there; files in deleted spaces went above.
    results = await asyncio.gather(*[
        getattr(db, coll).delete_many(build(uid)) for coll, build in _PRIVATE
    ], return_exceptions=True)
    for (coll, _), r in zip(_PRIVATE, results):
        if isinstance(r, Exception):
            logger.warning("deletion of %s failed: %s", coll, type(r).__name__)
        elif r.deleted_count:
            summary[coll] = r.deleted_count

    # Email delivery log entries addressed to this member.
    if user.get("email"):
        await db.email_log.delete_many({"to": user["email"]})

    # Anonymise the account record. Billing ids stay so retained financial
    # records still reconcile; nothing identifies the person.
    anon_email = f"deleted-{hashlib.sha256(uid.encode()).hexdigest()[:12]}@deleted.synaptiq.invalid"
    now = datetime.now(timezone.utc).isoformat()
    keep = {"_id", "plan_code", "stripe_customer_id", "stripe_subscription_id",
            "terms_version", "terms_accepted_at", "privacy_version_acknowledged", "created_at"}
    full = await db.users.find_one({"_id": ObjectId(uid)}) or {}
    unset = {k: "" for k in full if k not in keep}
    await db.users.update_one({"_id": ObjectId(uid)}, {"$unset": unset} if unset else {"$set": {}})
    await db.users.update_one({"_id": ObjectId(uid)}, {"$set": {
        "email": anon_email, "full_name": "Deleted user", "first_name": "Deleted", "last_name": "user",
        "role": "user", "status": "deleted", "deleted": True, "anonymized": True,
        "anonymized_at": now, "anonymized_by": actor, "deleted_at": now,
        "connections": [], "discoverable": False, "profile_visibility": "private",
        "onboarded": True, "credits_balance": 0,
    }})
    return summary


# ── Export ────────────────────────────────────────────────────────────────────
_SECRET_KEYS = {
    "password_hash", "storage_path", "access_token", "refresh_token", "id_token",
    "secret", "totp_secret", "mfa_secret", "backup_codes", "recovery_codes",
    "api_key", "key_hash", "token", "token_hash", "jti", "csrf_token", "ip_hash",
    "debug_verification_token", "debug_reset_token", "embedding", "vector",
}
_EXPORT_LIMIT = 2000


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            kl = str(k).lower()
            if kl in _SECRET_KEYS or kl.endswith("_secret") or kl.endswith("_token") or kl.endswith("_hash"):
                continue
            out["id" if k == "_id" else k] = _scrub(v)
        return out
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


async def _q(db, coll: str, flt: dict, projection: dict | None = None) -> list:
    docs = await getattr(db, coll).find(flt, projection).limit(_EXPORT_LIMIT).to_list(_EXPORT_LIMIT)
    return _scrub(docs)


async def build_export(db, uid: str) -> dict:
    """Everything Synaptiq holds about the member, structured, without
    passwords, tokens, secrets, internal storage paths or embeddings."""
    from auth_utils import serialize_user
    user = await db.users.find_one({"_id": ObjectId(uid)})
    if not user:
        return {}
    conv = await _q(db, "ai_conversations", {"user_id": uid})
    conv_ids = [c["id"] for c in conv]
    sections = {
        "projects": ("projects", {"$or": [{"owner_id": uid}, {"members": uid}]}),
        "workspaces": ("workspaces", {"$or": [{"owner_id": uid}, {"members": uid}]}),
        "manuscripts": ("manuscripts", {"$or": [{"lead_author_id": uid}, {"authors": uid}]}),
        "publications": ("publications", {"owner_id": uid}),
        "files_uploaded": ("files", {"owner_id": uid}),
        "messages_sent": ("messages", {"sender_id": uid}),
        "ai_requests": ("ai_requests", {"user_id": uid}),
        "copilot_conversations": ("copilot_conversations", {"user_id": uid}),
        "knowledge_documents": ("knowledge_documents", {"user_id": uid}),
        "saved_searches": ("saved_searches", {"user_id": uid}),
        "research_goals": ("user_research_goals", {"user_id": uid}),
        "team_blueprints": ("team_blueprints", {"owner_id": uid}),
        "meetings": ("meetings", {"owner_id": uid}),
        "meeting_notes": ("meeting_notes", {"owner_id": uid}),
        "connection_requests": ("connection_requests", {"$or": [{"sender_id": uid}, {"receiver_id": uid}]}),
        "collaboration_requests": ("collaboration_requests", {"$or": [{"sender_id": uid}, {"receiver_id": uid}]}),
        "institution_memberships": ("institution_memberships", {"user_id": uid}),
        "notifications": ("notifications", {"user_id": uid}),
        "consent_records": ("consent_records", {"user_id": uid}),
        "subscriptions": ("subscriptions", {"user_id": uid}),
        "billing_history": ("billing_history", {"user_id": uid}),
        "credit_transactions": ("credit_transactions", {"user_id": uid}),
    }
    results = await asyncio.gather(*[_q(db, c, f) for c, f in sections.values()], return_exceptions=True)
    out: dict[str, Any] = {
        "format": "synaptiq-account-export",
        "format_version": 2,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user_id": uid,
        "profile": _scrub(serialize_user(dict(user))),
        "terms_acceptance": {
            "terms_version": user.get("terms_version"),
            "terms_accepted_at": _scrub(user.get("terms_accepted_at")),
            "privacy_version_acknowledged": user.get("privacy_version_acknowledged"),
        },
        "connections": [str(c) for c in user.get("connections") or []],
        "ai_conversations": conv,
        "ai_messages": await _q(db, "ai_messages", {"conv_id": {"$in": conv_ids}}) if conv_ids else [],
    }
    for name, r in zip(sections, results):
        out[name] = [] if isinstance(r, Exception) else r
    out["limits"] = f"Each section includes up to {_EXPORT_LIMIT} records."
    return out
