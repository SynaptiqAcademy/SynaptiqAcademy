"""Monetization v2 data migration — report first, reversible changes only.

The deploy itself rewrites no user documents (entitlements are computed from
plan_code at request time). This script:

  --dry-run (default)  report what the new model affects; changes nothing
  --apply              set Free users' leftover subscription credits to 0,
                       backing the old value up in `legacy_v1_credits_balance`
  --revert             restore credits_balance from that backup

Purchased credits, projects, workspaces, files and subscriptions are never
modified. Usage:  python scripts/migrate_monetization_v2.py [--apply|--revert]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

FREE = {"$or": [{"plan_code": "free"}, {"plan_code": {"$exists": False}}, {"plan_code": None}]}


async def report(db) -> None:
    async for row in db.users.aggregate([{"$group": {"_id": {"plan": "$plan_code", "status": "$subscription_status"},
                                                     "users": {"$sum": 1}}}]):
        print("  users", row["_id"], row["users"])
    free_ids = [str(u["_id"]) async for u in db.users.find(FREE, {"_id": 1})]
    print("  free users with subscription credits > 0:",
          await db.users.count_documents({**FREE, "credits_balance": {"$gt": 0}}))
    print("  free users holding purchased credits (kept, usable after upgrade):",
          await db.users.count_documents({**FREE, "credits_pack_balance": {"$gt": 0}}))
    print("  projects owned by free users (become read-only):",
          await db.projects.count_documents({"owner_id": {"$in": free_ids}}))
    print("  workspaces owned by free users (become read-only):",
          await db.workspaces.count_documents({"owner_id": {"$in": free_ids}}))
    pro_ids = [str(u["_id"]) async for u in db.users.find({"plan_code": "researcher"}, {"_id": 1})]
    over = 0
    for uid in pro_ids:
        if await db.workspaces.count_documents({"owner_id": uid}) > 10:
            over += 1
    print("  Pro users above 10 workspaces (extra ones locked read-only):", over)
    print("  open collaboration requests to free users (need Pro to respond):",
          await db.collaboration_requests.count_documents({"receiver_id": {"$in": free_ids}, "status": "pending"}))


async def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true")
    g.add_argument("--revert", action="store_true")
    a = ap.parse_args()
    client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    db = client[os.environ.get("MONGODB_DB_NAME") or os.environ["DB_NAME"]]
    print("Report:")
    await report(db)
    if a.apply:
        r = await db.users.update_many(
            {**FREE, "credits_balance": {"$gt": 0}, "legacy_v1_credits_balance": {"$exists": False}},
            [{"$set": {"legacy_v1_credits_balance": "$credits_balance", "credits_balance": 0,
                       "credits_monthly_allowance": 0}}],
        )
        print(f"Applied: {r.modified_count} free users' subscription credits set to 0 (backed up).")
    elif a.revert:
        r = await db.users.update_many(
            {"legacy_v1_credits_balance": {"$exists": True}},
            [{"$set": {"credits_balance": "$legacy_v1_credits_balance"}},
             {"$unset": "legacy_v1_credits_balance"}],
        )
        print(f"Reverted: {r.modified_count} users restored.")
    else:
        print("Dry run — nothing changed.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
