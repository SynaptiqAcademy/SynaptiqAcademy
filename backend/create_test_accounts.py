"""Create the three canonical test accounts directly in MongoDB Atlas.

Usage:
    cd backend && python create_test_accounts.py

Accounts created:
    researcher@test.synaptiq.academy    / SynaptiqTest2026!   → pro_researcher
    institution@test.synaptiq.academy   / SynaptiqTest2026!   → institution_admin
    platformowner@test.synaptiq.academy / SynaptiqMaster2026! → super_admin (protected)
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from motor.motor_asyncio import AsyncIOMotorClient
from auth_utils import hash_password

MONGODB_URI = (
    os.environ.get("MONGODB_URI", "").strip()
    or os.environ.get("MONGO_URL", "").strip()
)
DB_NAME = (
    os.environ.get("MONGODB_DB_NAME", "").strip()
    or os.environ.get("DB_NAME", "").strip()
    or "synaptiq"
)

if not MONGODB_URI:
    print("ERROR: MONGODB_URI not set in .env")
    sys.exit(1)


def _now():
    return datetime.now(timezone.utc)


ACCOUNTS = [
    {
        "email": "researcher@test.synaptiq.academy",
        "password": "SynaptiqTest2026!",
        "full_name": "Test Researcher",
        "first_name": "Test",
        "last_name": "Researcher",
        "role": "user",
        "plan_code": "pro_researcher",
        "subscription_status": "active",
        "institution": "Test University",
        "department": "Computer Science",
        "country": "United States",
        "academic_role": "Associate Professor",
        "user_type": "university_faculty",
        "primary_domain": "research",
        "biography": "Test researcher account for platform validation. Pro researcher plan with full access.",
        "research_areas": ["Artificial Intelligence", "Cybersecurity"],
        "skills": ["Python", "R", "Machine Learning"],
        "can_contribute": ["Data Analysis", "Methodology", "Writing"],
        "looking_for": ["Co-authors", "Statisticians"],
        "availability": "Available",
        "h_index": 12,
        "publications_count": 18,
        "conferences_count": 5,
        "orcid": "0000-0001-2345-6789",
        "avatar_url": "",
        "collaboration_score": 80,
        "publication_score": 75,
        "expertise_score": 82,
        "community_score": 70,
        "email_verified": True,
        "onboarded": True,
        "profile_completion": 100,
        "credits_balance": 1000,
        "credits_monthly_allowance": 1000,
        "credits_pack_balance": 0,
        "failed_login_count": 0,
        "locked_until": None,
        "mfa_enabled": False,
        "is_test_account": True,
        "protected": False,
    },
    {
        "email": "institution@test.synaptiq.academy",
        "password": "SynaptiqTest2026!",
        "full_name": "Test Institution Admin",
        "first_name": "Test",
        "last_name": "Institution Admin",
        "role": "institution_admin",
        "plan_code": "institution",
        "subscription_status": "active",
        "institution": "Test University",
        "department": "Research Office",
        "country": "United States",
        "academic_role": "Research Director",
        "user_type": "university_faculty",
        "primary_domain": "both",
        "biography": "Test institution admin account for platform validation. Institutional plan.",
        "research_areas": ["Management", "Education"],
        "skills": ["Research Management", "Grant Writing"],
        "can_contribute": ["Grant Writing", "Methodology"],
        "looking_for": ["Co-authors"],
        "availability": "Available",
        "h_index": 5,
        "publications_count": 8,
        "conferences_count": 3,
        "orcid": "",
        "avatar_url": "",
        "collaboration_score": 65,
        "publication_score": 45,
        "expertise_score": 60,
        "community_score": 55,
        "email_verified": True,
        "onboarded": True,
        "profile_completion": 100,
        "credits_balance": 20000,
        "credits_monthly_allowance": 20000,
        "credits_pack_balance": 0,
        "failed_login_count": 0,
        "locked_until": None,
        "mfa_enabled": False,
        "is_test_account": True,
        "protected": False,
    },
    {
        "email": "platformowner@test.synaptiq.academy",
        "password": "SynaptiqMaster2026!",
        "full_name": "Platform Owner",
        "first_name": "Platform",
        "last_name": "Owner",
        "role": "super_admin",
        "plan_code": "institution",
        "subscription_status": "active",
        "institution": "SYNAPTIQ HQ",
        "department": "Operations",
        "country": "Global",
        "academic_role": "Super Administrator",
        "user_type": "university_faculty",
        "primary_domain": "both",
        "biography": "Protected platform owner test account with unrestricted super-admin access.",
        "research_areas": [],
        "skills": [],
        "can_contribute": [],
        "looking_for": [],
        "availability": "Available",
        "h_index": 0,
        "publications_count": 0,
        "conferences_count": 0,
        "orcid": "",
        "avatar_url": "",
        "collaboration_score": 100,
        "publication_score": 0,
        "expertise_score": 100,
        "community_score": 100,
        "email_verified": True,
        "onboarded": True,
        "profile_completion": 100,
        "credits_balance": 1_000_000,
        "credits_monthly_allowance": 1_000_000,
        "credits_pack_balance": 0,
        "failed_login_count": 0,
        "locked_until": None,
        "mfa_enabled": False,
        "is_test_account": True,
        "protected": True,
    },
]


async def main():
    print(f"Connecting to MongoDB: {MONGODB_URI[:50]}...")
    client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]

    # Verify connection
    await client.admin.command("ping")
    print(f"Connected to MongoDB Atlas — database: {DB_NAME}")
    print()

    now_iso = _now().isoformat()
    credits_reset = (_now() + timedelta(days=30)).isoformat()

    for acct in ACCOUNTS:
        email = acct["email"]
        existing = await db.users.find_one({"email": email})

        base_doc = {
            "email": email,
            "password_hash": hash_password(acct["password"]),
            "full_name": acct["full_name"],
            "first_name": acct["first_name"],
            "last_name": acct["last_name"],
            "role": acct["role"],
            "plan_code": acct["plan_code"],
            "subscription_status": acct["subscription_status"],
            "institution": acct["institution"],
            "department": acct["department"],
            "country": acct["country"],
            "academic_role": acct["academic_role"],
            "user_type": acct["user_type"],
            "primary_domain": acct["primary_domain"],
            "biography": acct["biography"],
            "research_areas": acct["research_areas"],
            "research_interests": acct["research_areas"],
            "research_keywords": [],
            "skills": acct["skills"],
            "can_contribute": acct["can_contribute"],
            "looking_for": acct["looking_for"],
            "availability": acct["availability"],
            "h_index": acct["h_index"],
            "publications_count": acct["publications_count"],
            "conferences_count": acct["conferences_count"],
            "orcid": acct["orcid"],
            "google_scholar": "",
            "researchgate": "",
            "scopus_id": "",
            "linkedin": "",
            "website": "",
            "avatar_url": acct["avatar_url"],
            "collaboration_score": acct["collaboration_score"],
            "publication_score": acct["publication_score"],
            "expertise_score": acct["expertise_score"],
            "community_score": acct["community_score"],
            "connections": [],
            "email_verified": True,
            "email_verified_at": now_iso,
            "onboarded": True,
            "profile_completion": acct["profile_completion"],
            "credits_balance": acct["credits_balance"],
            "credits_monthly_allowance": acct["credits_monthly_allowance"],
            "credits_pack_balance": acct["credits_pack_balance"],
            "credits_reset_at": credits_reset,
            "failed_login_count": 0,
            "locked_until": None,
            "last_failed_login": None,
            "last_successful_login": None,
            "mfa_enabled": False,
            "is_test_account": True,
            "protected": acct["protected"],
            "teaching_areas": [],
            "professional_expertise": [],
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        if existing:
            # Update to ensure all fields are correct
            await db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {k: v for k, v in base_doc.items() if k != "created_at"}},
            )
            print(f"[UPDATED] {email}  role={acct['role']}  plan={acct['plan_code']}")
        else:
            res = await db.users.insert_one(base_doc)
            print(f"[CREATED] {email}  role={acct['role']}  plan={acct['plan_code']}  _id={res.inserted_id}")

    print()
    print("Test accounts ready:")
    print("  researcher@test.synaptiq.academy    / SynaptiqTest2026!   → pro_researcher, email_verified, onboarded")
    print("  institution@test.synaptiq.academy   / SynaptiqTest2026!   → institution_admin, institutional plan")
    print("  platformowner@test.synaptiq.academy / SynaptiqMaster2026! → super_admin, protected, unrestricted")
    print()

    # Verify they're in the DB
    print("Verifying accounts in DB:")
    for acct in ACCOUNTS:
        doc = await db.users.find_one({"email": acct["email"]})
        if doc:
            print(f"  ✓ {acct['email']}  role={doc.get('role')}  verified={doc.get('email_verified')}  plan={doc.get('plan_code')}")
        else:
            print(f"  ✗ {acct['email']} — NOT FOUND (insert failed?)")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
