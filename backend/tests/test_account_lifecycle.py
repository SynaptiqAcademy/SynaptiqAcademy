"""Legal & Trust Phase 2: account deletion matrix, export scope and retention.

Runs against a throwaway database on the local MongoDB (skipped if none),
never against production data.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

motor = pytest.importorskip("motor.motor_asyncio")

import retention_policy as RP
from services import account_lifecycle as AL

MONGO = os.environ.get("LIFECYCLE_TEST_MONGO", "mongodb://localhost:27017")


_LOOP = asyncio.new_event_loop()   # motor clients are bound to one loop


def _run(coro):
    return _LOOP.run_until_complete(coro)


async def _db():
    client = motor.AsyncIOMotorClient(MONGO, serverSelectionTimeoutMS=800)
    await client.admin.command("ping")
    return client, client[f"synaptiq_lifecycle_{uuid.uuid4().hex[:10]}"]


@pytest.fixture
def world(monkeypatch):
    try:
        client, db = _run(_db())
    except Exception:
        pytest.skip("local MongoDB not available")

    async def _noop(uid):
        return None
    import services.token_service as TS
    monkeypatch.setattr(TS, "revoke_all_user_tokens", _noop)
    deleted_paths = []
    import services.storage_service as S
    monkeypatch.setattr(S, "delete_object", lambda p: deleted_paths.append(p) or True)

    async def _seed():
        me, other = ObjectId(), ObjectId()
        uid, oid = str(me), str(other)
        await db.users.insert_many([
            {"_id": me, "email": "me@example.org", "full_name": "Me Person", "password_hash": "x",
             "biography": "bio", "orcid": {"orcid_id": "0000"}, "connections": [oid],
             "terms_version": "2026-10-06", "stripe_customer_id": "cus_test", "role": "user"},
            {"_id": other, "email": "o@example.org", "full_name": "Other", "connections": [uid], "role": "user"},
        ])
        priv_ws = (await db.workspaces.insert_one({"owner_id": uid, "members": [uid], "name": "private"})).inserted_id
        shared_ws = (await db.workspaces.insert_one({"owner_id": uid, "members": [uid, oid], "name": "shared"})).inserted_id
        await db.workspace_items.insert_many([
            {"workspace_id": str(priv_ws), "creator_id": uid, "title": "private note"},
            {"workspace_id": str(shared_ws), "creator_id": uid, "title": "shared note"},
        ])
        await db.files.insert_many([
            {"entity_kind": "workspace", "entity_id": str(priv_ws), "owner_id": uid, "storage_path": "p/private.pdf"},
            {"entity_kind": "workspace", "entity_id": str(shared_ws), "owner_id": uid, "storage_path": "p/shared.pdf"},
        ])
        priv_ms = (await db.manuscripts.insert_one({"lead_author_id": uid, "authors": [uid], "title": "solo"})).inserted_id
        shared_ms = (await db.manuscripts.insert_one({"lead_author_id": uid, "authors": [uid, oid], "title": "co"})).inserted_id
        conv = (await db.ai_conversations.insert_one({"user_id": uid, "title": "chat"})).inserted_id
        await db.ai_messages.insert_one({"conv_id": str(conv), "content": "secret research idea"})
        await db.knowledge_chunks.insert_one({"user_id": uid, "embedding": [0.1, 0.2]})
        await db.messages.insert_one({"sender_id": uid, "body": "hello"})
        await db.connection_requests.insert_one({"sender_id": oid, "receiver_id": uid})
        await db.consent_records.insert_one({"user_id": uid, "choice": "analytics"})
        await db.billing_history.insert_one({"user_id": uid, "amount": 10})
        await db.refresh_tokens.insert_one({"user_id": uid, "jti": "j", "token_hash": "h"})
        await db.email_log.insert_one({"to": "me@example.org", "subject": "Welcome"})
        return dict(uid=uid, oid=oid, priv_ws=priv_ws, shared_ws=shared_ws, priv_ms=priv_ms,
                    shared_ms=shared_ms, conv=conv)

    ids = _run(_seed())
    yield db, ids, deleted_paths
    _run(client.drop_database(db.name))
    client.close()


def test_export_is_complete_and_has_no_secrets(world):
    db, ids, _ = world
    data = _run(AL.build_export(db, ids["uid"]))
    for section in ("profile", "terms_acceptance", "connections", "workspaces", "manuscripts",
                    "ai_conversations", "ai_messages", "messages_sent", "connection_requests",
                    "consent_records", "billing_history", "files_uploaded"):
        assert section in data, section
    assert data["terms_acceptance"]["terms_version"] == "2026-10-06"
    assert data["ai_messages"][0]["content"] == "secret research idea"
    text = repr(data)
    for leaked in ("password_hash", "storage_path", "token_hash", "'jti'", "embedding"):
        assert leaked not in text, leaked


def test_delete_matrix(world):
    db, ids, deleted_paths = world
    uid, oid = ids["uid"], ids["oid"]
    _run(AL.delete_account(db, {"id": uid, "role": "user", "email": "me@example.org"}))

    async def check():
        me = await db.users.find_one({"_id": ObjectId(uid)})
        # ANONYMISE: nothing identifying remains on the account record
        assert me["full_name"] == "Deleted user" and me["deleted"] is True and me["status"] == "deleted"
        assert me["email"].endswith("@deleted.synaptiq.invalid")
        for gone in ("password_hash", "biography", "orcid"):
            assert gone not in me, gone
        assert me["stripe_customer_id"] == "cus_test"  # RETAIN: billing reconciliation
        # DELETE: private content
        assert await db.workspaces.count_documents({"_id": ids["priv_ws"]}) == 0
        assert await db.workspace_items.count_documents({"title": "private note"}) == 0
        assert await db.manuscripts.count_documents({"_id": ids["priv_ms"]}) == 0
        assert await db.ai_conversations.count_documents({"user_id": uid}) == 0
        assert await db.ai_messages.count_documents({}) == 0
        assert await db.knowledge_chunks.count_documents({"user_id": uid}) == 0
        assert await db.connection_requests.count_documents({}) == 0
        assert await db.consent_records.count_documents({"user_id": uid}) == 0
        assert await db.refresh_tokens.count_documents({"user_id": uid}) == 0
        assert await db.email_log.count_documents({"to": "me@example.org"}) == 0
        assert await db.files.count_documents({"storage_path": "p/private.pdf"}) == 0
        assert "p/private.pdf" in deleted_paths and "p/shared.pdf" not in deleted_paths
        # TRANSFER: shared spaces stay and pass to the other member
        ws = await db.workspaces.find_one({"_id": ids["shared_ws"]})
        assert ws["owner_id"] == oid and uid not in ws["members"]
        ms = await db.manuscripts.find_one({"_id": ids["shared_ms"]})
        assert ms["lead_author_id"] == oid
        assert await db.workspace_items.count_documents({"title": "shared note"}) == 1
        assert await db.messages.count_documents({"sender_id": uid}) == 1
        other = await db.users.find_one({"_id": ObjectId(oid)})
        assert uid not in other["connections"]
        # RETAIN: billing
        assert await db.billing_history.count_documents({"user_id": uid}) == 1
    _run(check())


def test_legal_hold_blocks_deletion(world):
    db, ids, _ = world
    _run(db.users.update_one({"_id": ObjectId(ids["uid"])}, {"$set": {"legal_hold": True}}))
    with pytest.raises(AL.DeletionBlocked):
        _run(AL.delete_account(db, {"id": ids["uid"], "role": "user"}))


def test_sole_institution_admin_must_hand_over(world):
    db, ids, _ = world
    _run(db.institution_memberships.insert_many([
        {"institution_id": "i1", "user_id": ids["uid"], "role": "owner", "status": "approved"},
        {"institution_id": "i1", "user_id": ids["oid"], "role": "member", "status": "approved"},
    ]))
    with pytest.raises(AL.DeletionBlocked):
        _run(AL.preflight(db, {"id": ids["uid"], "role": "user"}))


# ── Retention policy ─────────────────────────────────────────────────────────

def test_retention_periods_match_published_policy():
    assert RP.BY_KEY["security_events"].effective_days == 365   # "1 year" in the Privacy Policy
    assert RP.BY_KEY["audit_admin"].effective_days == 90
    for key in ("contact_inquiries", "audit_billing", "billing", "consent_account"):
        assert RP.BY_KEY[key].legal_review, key


def test_undecided_periods_stay_off_until_configured(monkeypatch):
    assert RP.BY_KEY["contact_inquiries"].effective_days is None
    assert "contact_inquiries" not in [r.key for r in RP.purge_rules()]
    monkeypatch.setenv("RETENTION_CONTACT_INQUIRIES_DAYS", "365")
    assert "contact_inquiries" in [r.key for r in RP.purge_rules()]


def test_writers_use_the_policy():
    import services.admin_audit as A
    import services.security_event_service as SE
    assert A._SECURITY_EVENT_TTL_DAYS == SE._TTL_DAYS == 365
    assert A._AUDIT_LOG_TTL_DAYS == 90


def test_retention_purge_deletes_only_expired(world, monkeypatch):
    db, _, _ = world
    import services.cleanup_service as C
    monkeypatch.setattr(C, "get_db", lambda: db)
    monkeypatch.setattr(C, "DBProxy", lambda d, ctx: d)
    old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    new = datetime.now(timezone.utc).isoformat()

    async def go():
        await db.email_log.insert_many([{"to": "a", "created_at": old}, {"to": "b", "created_at": new}])
        await db.audit_log.insert_many([
            {"_source": "shim", "_ts": old}, {"_source": "shim", "_ts": new},
            {"action": "billing", "entity_kind": "sub", "created_at": old},
            {"action": "user.self_delete", "extra": {"original_email": "x@y.z"}},
        ])
        await C.enforce_retention_schedule()
        await C.minimise_deletion_audit_records()
        assert await db.email_log.count_documents({"to": {"$in": ["a", "b"]}}) == 1
        assert await db.audit_log.count_documents({"_source": "shim"}) == 1
        assert await db.audit_log.count_documents({"action": "billing"}) == 1  # LEGAL REVIEW: kept
        assert await db.audit_log.count_documents({"extra.original_email": {"$exists": True}}) == 0
    _run(go())


def test_self_delete_endpoint_requires_reauth():
    src = open("routers/users.py", encoding="utf-8").read()
    i = src.index("async def delete_my_account")
    body = src[i:i + 2500]
    assert "verify_password" in body and "reauth_required" in body and '"DELETE"' in body
    assert "original_email" not in src


# ── Emails don't carry research content ──────────────────────────────────────

def test_notification_emails_do_not_reveal_research_topics():
    import itertools
    from services.email.templates.review_request import review_request_email
    from services.email.templates.collaboration_invitation import collaboration_invitation_email
    from services.email.templates.workspace_invitation import workspace_invitation_email
    outs = [
        review_request_email(recipient_name="A", manuscript_title="TOPIC-1", requester_name="<script>x</script>",
                             section="TOPIC-2", note="TOPIC-3", review_url="https://synaptiq.academy/r"),
        collaboration_invitation_email(recipient_name="A", collaboration_title="TOPIC-4", inviter_name="B",
                                       kind="application", action_url="https://synaptiq.academy/c", message="TOPIC-5"),
        collaboration_invitation_email(recipient_name="A", collaboration_title="TOPIC-6", inviter_name="B",
                                       kind="decision", action_url="https://synaptiq.academy/c", message="TOPIC-7"),
        workspace_invitation_email(recipient_name="A", workspace_name="TOPIC-8", role="editor",
                                   inviter_name="B", accept_url="https://synaptiq.academy/w"),
    ]
    for part in itertools.chain(*outs):
        assert "TOPIC-" not in part
    assert "<script>" not in outs[0][1]
    src = open("services/email_service.py", encoding="utf-8").read()
    assert 'subject=f"[SYNAPTIQ] {event.title}"' not in src
