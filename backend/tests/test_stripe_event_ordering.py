"""Stripe webhooks: duplicate, delayed and out-of-order delivery.

Stripe does not guarantee event order and retries failed deliveries for days,
so the handler must never let an older event overwrite newer state.
Uses the signed-request helpers and database fixtures of test_monetization.
"""
from __future__ import annotations

import asyncio

from bson import ObjectId

from tests.test_monetization import (  # noqa: F401 (fixtures)
    mdb, webhook_env, _signed_request, _evt, _sub, _mk_user, _bal,
)


def _at(event: dict, created: int) -> dict:
    return {**event, "created": created}


async def _user(mdb, uid):
    return await mdb.users.find_one({"_id": ObjectId(uid)})


class TestOrdering:
    async def test_late_update_after_cancellation_does_not_restore_plan(self, mdb, webhook_env):
        billing = webhook_env
        uid = await _mk_user(mdb, plan="free", sub=0, pack=0)
        sub_id = "sub_test_" + str(ObjectId())
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.created", _sub(uid, sub_id, "price_pro", 1000)), 100)))
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.deleted", _sub(uid, sub_id, "price_pro", 1000, "canceled")), 300)))
        assert (await _user(mdb, uid))["plan_code"] == "free"
        # A retried "updated (active)" from before the cancellation arrives late.
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.updated", _sub(uid, sub_id, "price_adv", 1000)), 200)))
        assert (await _user(mdb, uid))["plan_code"] == "free"
        # Even with a newer timestamp, a canceled subscription is never revived.
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.updated", _sub(uid, sub_id, "price_adv", 1000)), 400)))
        assert (await _user(mdb, uid))["plan_code"] == "free"

    async def test_older_update_does_not_overwrite_newer_plan(self, mdb, webhook_env):
        billing = webhook_env
        uid = await _mk_user(mdb, plan="free", sub=0, pack=0)
        sub_id = "sub_test_" + str(ObjectId())
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.created", _sub(uid, sub_id, "price_adv", 1000)), 100)))
        # Downgrade to Pro at t=300 arrives first, the earlier upgrade (t=200) arrives after it.
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.updated", _sub(uid, sub_id, "price_pro", 1000)), 300)))
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.updated", _sub(uid, sub_id, "price_adv", 1000)), 200)))
        assert (await _user(mdb, uid))["plan_code"] == "researcher"
        local = await mdb.subscriptions.find_one({"stripe_subscription_id": sub_id})
        assert local["plan_code"] == "researcher" and local["last_subscription_event_created"] == 300

    async def test_late_payment_failure_does_not_mark_paid_account_past_due(self, mdb, webhook_env):
        billing = webhook_env
        uid = await _mk_user(mdb, plan="free", sub=0, pack=0)
        sub_id = "sub_test_" + str(ObjectId())
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.created", _sub(uid, sub_id, "price_pro", 1000)), 100)))
        paid = {"id": "in_ok", "subscription": sub_id, "billing_reason": "subscription_cycle", "amount_paid": 999,
                "lines": {"data": [{"type": "subscription", "price": {"id": "price_pro"},
                                    "period": {"start": 2_593_000, "end": 5_185_000}}]}}
        await billing.stripe_webhook(_signed_request(_at(_evt("invoice.paid", paid), 500)))
        failed = {"id": "in_old", "subscription": sub_id, "amount_due": 999}
        await billing.stripe_webhook(_signed_request(_at(_evt("invoice.payment_failed", failed), 400)))
        u = await _user(mdb, uid)
        assert u.get("subscription_status") != "past_due"
        local = await mdb.subscriptions.find_one({"stripe_subscription_id": sub_id})
        assert local["status"] != "past_due"

    async def test_invoice_after_cancellation_grants_nothing(self, mdb, webhook_env):
        billing = webhook_env
        uid = await _mk_user(mdb, plan="free", sub=0, pack=7)
        sub_id = "sub_test_" + str(ObjectId())
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.created", _sub(uid, sub_id, "price_pro", 1000)), 100)))
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.deleted", _sub(uid, sub_id, "price_pro", 1000, "canceled")), 300)))
        assert await _bal(mdb, uid) == (0, 7)
        late = {"id": "in_late", "subscription": sub_id, "billing_reason": "subscription_cycle", "amount_paid": 999,
                "lines": {"data": [{"type": "subscription", "price": {"id": "price_pro"},
                                    "period": {"start": 2_593_000, "end": 5_185_000}}]}}
        await billing.stripe_webhook(_signed_request(_at(_evt("invoice.paid", late), 400)))
        assert await _bal(mdb, uid) == (0, 7)
        assert (await _user(mdb, uid))["plan_code"] == "free"

    async def test_concurrent_deliveries_of_the_same_event_apply_once(self, mdb, webhook_env):
        billing = webhook_env
        uid = await _mk_user(mdb, plan="free", sub=0, pack=0)
        sub_id = "sub_test_" + str(ObjectId())
        evt = _at(_evt("customer.subscription.created", _sub(uid, sub_id, "price_pro", 1000)), 100)
        results = await asyncio.gather(*[billing.stripe_webhook(_signed_request(evt)) for _ in range(5)],
                                       return_exceptions=True)
        assert sum(1 for r in results if isinstance(r, dict) and r.get("reason") == "duplicate") == 4
        assert (await _user(mdb, uid))["credits_balance"] == 200

    async def test_state_is_taken_from_stripe_when_refetch_is_on(self, mdb, webhook_env, monkeypatch):
        """A delayed 'active' snapshot is replaced by Stripe's current state."""
        billing = webhook_env
        monkeypatch.setenv("STRIPE_REFETCH_SUBSCRIPTIONS", "1")
        uid = await _mk_user(mdb, plan="free", sub=0, pack=0)
        sub_id = "sub_test_" + str(ObjectId())
        current = _sub(uid, sub_id, "price_pro", 1000, status="canceled")
        monkeypatch.setattr(billing.stripe_service, "retrieve_subscription", lambda sid: current)
        await billing.stripe_webhook(_signed_request(_at(_evt("customer.subscription.updated", _sub(uid, sub_id, "price_adv", 1000)), 100)))
        assert (await _user(mdb, uid))["plan_code"] == "free"
