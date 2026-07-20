"""
Standalone migration: populate users.user_type from users.academic_role.

Run once against the target database:
    python -m scripts.migrate_user_types [--dry-run] [--apply]

Additive-only — never modifies academic_role, never drops documents.
Safe to re-run: users who already have user_type set are skipped unless
--overwrite is passed.

Exit codes:
    0  success
    1  unexpected error
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Allow running from the backend/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from models import ACADEMIC_ROLE_MIGRATION_MAP


async def migrate(dry_run: bool = True, overwrite: bool = False) -> None:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI environment variable is not set")

    client = AsyncIOMotorClient(uri)
    db = client.get_default_database()

    query: dict = {}
    if not overwrite:
        query["user_type"] = {"$exists": False}

    cursor = db.users.find(query, {"_id": 1, "email": 1, "academic_role": 1, "user_type": 1})

    mapped = 0
    unmapped = 0
    skipped = 0
    errors = 0

    async for user in cursor:
        uid = user["_id"]
        raw_role = (user.get("academic_role") or "").strip().lower()
        target_type = ACADEMIC_ROLE_MIGRATION_MAP.get(raw_role)

        if not overwrite and user.get("user_type"):
            skipped += 1
            continue

        if target_type:
            mapped += 1
            print(f"  MAPPED  {user.get('email')}  '{raw_role}' → {target_type}")
        else:
            unmapped += 1
            print(f"  UNMAPPED {user.get('email')}  '{raw_role}' → null (user must self-select)")

        if not dry_run:
            try:
                await db.users.update_one(
                    {"_id": uid},
                    {"$set": {"user_type": target_type, "primary_domain": user.get("primary_domain")}},
                )
            except Exception as exc:
                errors += 1
                print(f"  ERROR   {user.get('email')}  {exc}", file=sys.stderr)

    client.close()

    print()
    print("=" * 60)
    print(f"  Mode     : {'DRY RUN (no writes)' if dry_run else 'APPLIED'}")
    print(f"  Mapped   : {mapped}")
    print(f"  Unmapped : {unmapped}  (user_type will be null; users prompted to complete profile)")
    print(f"  Skipped  : {skipped}  (already had user_type)")
    print(f"  Errors   : {errors}")
    print("=" * 60)

    if unmapped > 0:
        print()
        print("Note: unmapped users will see a profile-completion prompt in the UI.")
        print("They can select their user_type from their Profile → Edit page.")

    if errors:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate academic_role → user_type")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Print what would be changed, make no writes")
    mode.add_argument("--apply",   action="store_true", help="Perform the migration")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-run on users who already have user_type set")
    args = parser.parse_args()

    asyncio.run(migrate(dry_run=args.dry_run, overwrite=args.overwrite))


if __name__ == "__main__":
    main()
