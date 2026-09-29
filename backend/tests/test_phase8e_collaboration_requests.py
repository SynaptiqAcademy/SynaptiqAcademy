"""P1 Phase 8E — Structured Research Collaboration Requests.

Covers the NEW behavior added on top of the already-extensive, pre-existing
routers/collaboration_requests.py: mandatory reciprocal blocking, demo-
account rejection, context-scoped duplicate protection (so the same two
people can legitimately have separate simultaneous requests for different
projects/topics), the new collaboration_purpose field, per-user rate
limiting, and regression coverage proving the pre-existing self-invitation
guard, sender/recipient authorization, safe serialization, and zero-credit
behavior all remain intact.
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId
from fastapi import HTTPException

import rate_limit
from routers.collaboration_requests import (
    send_request, list_my_requests, get_request, update_request_status,
    SendRequestBody, UpdateStatusBody, _is_blocked_either_way,
)


def _oid() -> str:
    return str(ObjectId())


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


async def _insert_user(db, full_name: str, **extra) -> str:
    doc = {
        "full_name": full_name,
        "email": f"{full_name.lower().replace(' ', '')}-{_oid()[:8]}@synaptiq-test.io",
        "is_demo": False,
        "profile_visibility": "public",
        **extra,
    }
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


def _user(uid: str, name: str = "Test") -> dict:
    return {"id": uid, "full_name": name, "email": f"{name}@synaptiq-test.io"}


class TestBlockingEnforcement:
    @pytest.mark.asyncio
    async def test_is_blocked_either_way_detects_a_blocks_b(self):
        raw = _RawDB()
        try:
            a, b = _oid(), _oid()
            await raw.db.network_settings.insert_one({"user_id": a, "blocked_users": [b]})
            assert await _is_blocked_either_way(raw.db, a, b) is True
            assert await _is_blocked_either_way(raw.db, b, a) is True
        finally:
            await raw.db.network_settings.delete_many({"user_id": a})
            raw.close()

    @pytest.mark.asyncio
    async def test_send_request_blocked_when_recipient_blocked_sender(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"Sender {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"Receiver {_oid()[:8]}")
            await raw.db.network_settings.insert_one({"user_id": receiver_id, "blocked_users": [sender_id]})

            with pytest.raises(HTTPException) as exc:
                await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            assert exc.value.status_code == 404  # never discloses that a block occurred
        finally:
            await raw.db.network_settings.delete_many({"user_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^Sender|^Receiver"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_send_request_blocked_when_sender_blocked_receiver(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"Sender2 {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"Receiver2 {_oid()[:8]}")
            await raw.db.network_settings.insert_one({"user_id": sender_id, "blocked_users": [receiver_id]})

            with pytest.raises(HTTPException) as exc:
                await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            assert exc.value.status_code == 404
        finally:
            await raw.db.network_settings.delete_many({"user_id": sender_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^Sender2|^Receiver2"}})
            raw.close()


class TestDemoAccountRejection:
    @pytest.mark.asyncio
    async def test_cannot_send_request_to_demo_account(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"RealSender {_oid()[:8]}")
            demo_id = await _insert_user(raw.db, f"DemoFixture {_oid()[:8]}", is_demo=True)

            with pytest.raises(HTTPException) as exc:
                await send_request(SendRequestBody(receiver_id=demo_id), user=_user(sender_id))
            assert exc.value.status_code == 404
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^RealSender|^DemoFixture"}})
            raw.close()


class TestContextScopedDuplicateProtection:
    @pytest.mark.asyncio
    async def test_duplicate_blocked_same_project(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"DupSenderA {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"DupReceiverA {_oid()[:8]}")
            proj = await raw.db.projects.insert_one({"title": "Project X", "owner_id": sender_id})
            proj_id = str(proj.inserted_id)

            await send_request(SendRequestBody(receiver_id=receiver_id, project_id=proj_id), user=_user(sender_id))
            with pytest.raises(HTTPException) as exc:
                await send_request(SendRequestBody(receiver_id=receiver_id, project_id=proj_id), user=_user(sender_id))
            assert exc.value.status_code == 409
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.projects.delete_many({"title": "Project X"})
            await raw.db.users.delete_many({"full_name": {"$regex": "^DupSenderA|^DupReceiverA"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_separate_requests_allowed_for_different_projects(self, monkeypatch):
        """§15's explicit example: Project X and Paper Y are legitimately
        distinct, simultaneous pending requests to the same person."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"DupSenderB {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"DupReceiverB {_oid()[:8]}")
            proj_x = await raw.db.projects.insert_one({"title": "Project X2", "owner_id": sender_id})
            proj_y = await raw.db.projects.insert_one({"title": "Paper Y2", "owner_id": sender_id})

            r1 = await send_request(SendRequestBody(receiver_id=receiver_id, project_id=str(proj_x.inserted_id)), user=_user(sender_id))
            r2 = await send_request(SendRequestBody(receiver_id=receiver_id, project_id=str(proj_y.inserted_id)), user=_user(sender_id))
            assert r1["id"] != r2["id"]
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.projects.delete_many({"title": {"$regex": "^Project X2|^Paper Y2"}})
            await raw.db.users.delete_many({"full_name": {"$regex": "^DupSenderB|^DupReceiverB"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_duplicate_blocked_same_research_need_topic(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"DupSenderC {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"DupReceiverC {_oid()[:8]}")
            ctx = {"research_need_topic": "AI in hospital quality management"}

            await send_request(SendRequestBody(receiver_id=receiver_id, context=ctx), user=_user(sender_id))
            with pytest.raises(HTTPException) as exc:
                await send_request(SendRequestBody(receiver_id=receiver_id, context=ctx), user=_user(sender_id))
            assert exc.value.status_code == 409
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^DupSenderC|^DupReceiverC"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_separate_requests_allowed_for_different_research_need_topics(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"DupSenderD {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"DupReceiverD {_oid()[:8]}")

            r1 = await send_request(SendRequestBody(receiver_id=receiver_id, context={"research_need_topic": "Topic A"}), user=_user(sender_id))
            r2 = await send_request(SendRequestBody(receiver_id=receiver_id, context={"research_need_topic": "Topic B"}), user=_user(sender_id))
            assert r1["id"] != r2["id"]
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^DupSenderD|^DupReceiverD"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_duplicate_blocked_for_plain_contextless_requests(self, monkeypatch):
        """Original blanket behaviour preserved when neither project nor
        research-need topic is given."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"DupSenderE {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"DupReceiverE {_oid()[:8]}")

            await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            with pytest.raises(HTTPException) as exc:
                await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            assert exc.value.status_code == 409
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^DupSenderE|^DupReceiverE"}})
            raw.close()


class TestCollaborationPurpose:
    @pytest.mark.asyncio
    async def test_valid_purpose_stored(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"PurposeSender {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"PurposeReceiver {_oid()[:8]}")
            out = await send_request(
                SendRequestBody(receiver_id=receiver_id, collaboration_purpose="co_author_paper"),
                user=_user(sender_id),
            )
            assert out["collaboration_purpose"] == "co_author_paper"
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^PurposeSender|^PurposeReceiver"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_invalid_purpose_rejected(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"BadPurposeSender {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"BadPurposeReceiver {_oid()[:8]}")
            with pytest.raises(HTTPException) as exc:
                await send_request(
                    SendRequestBody(receiver_id=receiver_id, collaboration_purpose="not_a_real_purpose"),
                    user=_user(sender_id),
                )
            assert exc.value.status_code == 400
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^BadPurposeSender|^BadPurposeReceiver"}})
            raw.close()


class TestRateLimiting:
    def test_write_rate_limit_fires_after_threshold(self, monkeypatch):
        monkeypatch.setattr(rate_limit.limiter, "enabled", True)
        monkeypatch.setattr(rate_limit, "WRITE_RATE", "2/minute")
        monkeypatch.setattr(rate_limit, "_write_rate_item", None)
        uid = _oid()
        rate_limit.check_write_rate_limit(uid, bucket="test_bucket")
        rate_limit.check_write_rate_limit(uid, bucket="test_bucket")
        with pytest.raises(HTTPException) as exc:
            rate_limit.check_write_rate_limit(uid, bucket="test_bucket")
        assert exc.value.status_code == 429

    def test_rate_limit_disabled_in_test_env_by_default(self):
        # Confirms the default test-suite posture (limiter.enabled is False
        # under APP_ENV=test) so this new check never makes unrelated tests
        # in this file flaky.
        assert rate_limit.limiter.enabled is False


class TestRegressionSelfInvitationAndAuthorization:
    @pytest.mark.asyncio
    async def test_self_invitation_still_forbidden(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            uid = await _insert_user(raw.db, f"SelfInvite {_oid()[:8]}")
            with pytest.raises(HTTPException) as exc:
                await send_request(SendRequestBody(receiver_id=uid), user=_user(uid))
            assert exc.value.status_code == 400
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^SelfInvite"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_unrelated_user_cannot_read_a_request(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"ReadSender {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"ReadReceiver {_oid()[:8]}")
            stranger_id = await _insert_user(raw.db, f"ReadStranger {_oid()[:8]}")
            req = await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            with pytest.raises(HTTPException) as exc:
                await get_request(req["id"], user=_user(stranger_id))
            assert exc.value.status_code == 403
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^ReadSender|^ReadReceiver|^ReadStranger"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_sender_cannot_accept_own_outgoing_request(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"AcceptSender {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"AcceptReceiver {_oid()[:8]}")
            req = await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            with pytest.raises(HTTPException) as exc:
                await update_request_status(req["id"], UpdateStatusBody(status="accepted"), user=_user(sender_id))
            assert exc.value.status_code == 403
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^AcceptSender|^AcceptReceiver"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_only_sender_can_cancel(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"CancelSender {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"CancelReceiver {_oid()[:8]}")
            req = await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            with pytest.raises(HTTPException) as exc:
                await update_request_status(req["id"], UpdateStatusBody(status="cancelled"), user=_user(receiver_id))
            assert exc.value.status_code == 403
            out = await update_request_status(req["id"], UpdateStatusBody(status="cancelled"), user=_user(sender_id))
            assert out["status"] == "cancelled"
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^CancelSender|^CancelReceiver"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_accept_creates_dm_conversation_reusing_existing_messaging(self, monkeypatch):
        """Regression: 'Discuss' reuses the existing conversations system —
        confirms Phase 8E doesn't need (and mustn't build) a new one."""
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"DiscussSender {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"DiscussReceiver {_oid()[:8]}")
            req = await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            await update_request_status(req["id"], UpdateStatusBody(status="accepted"), user=_user(receiver_id))
            sorted_ids = sorted([sender_id, receiver_id])
            conv = await raw.db.conversations.find_one({"context_key": f"direct:{sorted_ids[0]}:{sorted_ids[1]}"})
            assert conv is not None
        finally:
            await raw.db.conversations.delete_many({"created_by": {"$in": [sender_id, receiver_id]}})
            await raw.db.conversation_members.delete_many({"user_id": {"$in": [sender_id, receiver_id]}})
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^DiscussSender|^DiscussReceiver"}})
            raw.close()


class TestSafeSerializationAndZeroCredit:
    @pytest.mark.asyncio
    async def test_list_requests_never_exposes_email_or_orcid_tokens(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(
                raw.db, f"SafeSender {_oid()[:8]}",
                orcid={"orcid_id": "0000-0001-2222-3333", "access_token": "SHOULD_NOT_LEAK"},
            )
            receiver_id = await _insert_user(raw.db, f"SafeReceiver {_oid()[:8]}")
            await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            out = await list_my_requests(kind="received", status=None, user=_user(receiver_id))
            blob = str(out)
            assert "SHOULD_NOT_LEAK" not in blob
            assert "@synaptiq-test.io" not in blob
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^SafeSender|^SafeReceiver"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_send_accept_decline_never_touch_credit_transactions(self, monkeypatch):
        raw = _RawDB()
        try:
            monkeypatch.setattr("routers.collaboration_requests.get_db", lambda: raw.db)
            sender_id = await _insert_user(raw.db, f"CreditSender {_oid()[:8]}")
            receiver_id = await _insert_user(raw.db, f"CreditReceiver {_oid()[:8]}")
            before = await raw.db.credit_transactions.count_documents({})

            req = await send_request(SendRequestBody(receiver_id=receiver_id), user=_user(sender_id))
            await update_request_status(req["id"], UpdateStatusBody(status="viewed"), user=_user(receiver_id))
            await update_request_status(req["id"], UpdateStatusBody(status="declined"), user=_user(receiver_id))

            after = await raw.db.credit_transactions.count_documents({})
            assert after == before
        finally:
            await raw.db.collaboration_requests.delete_many({"receiver_id": receiver_id})
            await raw.db.users.delete_many({"full_name": {"$regex": "^CreditSender|^CreditReceiver"}})
            raw.close()
