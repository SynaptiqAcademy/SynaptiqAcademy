"""Seed demo data: researchers, collaborations, grants, conferences."""
import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from auth_utils import hash_password
from plans_catalogue import PLANS
from seed_phase2 import seed_phase2

DEMO_USERS = [
    {
        "email": "elena.varga@synaptiq.academy", "password": "demo123",
        "full_name": "Elena Vargas", "institution": "ETH Zürich", "department": "Computer Science",
        "country": "Switzerland", "academic_role": "Associate Professor",
        "user_type": "university_faculty", "primary_domain": "both",
        "biography": "Computational linguistics and ethical AI. PI of the SymGraph lab. ERC Starting Grant recipient.",
        "orcid": "0000-0002-1825-0097", "google_scholar": "abc123", "website": "https://elena.example.com",
        "research_areas": ["Artificial Intelligence", "Cybersecurity"],
        "skills": ["Python", "R", "Systematic Literature Review", "Qualitative Research"],
        "can_contribute": ["Methodology", "Statistics", "Writing"],
        "looking_for": ["Co-authors", "Statisticians"],
        "availability": "Available", "h_index": 18,
        "avatar_url": "https://images.unsplash.com/photo-1580894732444-8ecded7900cd?w=400&h=400&fit=crop",
        "collaboration_score": 87, "publication_score": 72, "expertise_score": 81, "community_score": 64,
    },
    {
        "email": "marcus.okafor@synaptiq.academy", "password": "demo123",
        "full_name": "Marcus Okafor", "institution": "University of Cape Town", "department": "Public Health",
        "country": "South Africa", "academic_role": "Senior Lecturer",
        "user_type": "university_faculty", "primary_domain": "both",
        "biography": "Health systems and policy in sub-Saharan Africa. Mixed-methods scholar.",
        "orcid": "0000-0003-1234-5678",
        "research_areas": ["Healthcare", "Public Health"],
        "skills": ["SPSS", "R", "PLS-SEM", "Systematic Literature Review"],
        "can_contribute": ["Data Analysis", "Methodology"],
        "looking_for": ["Co-authors", "Statisticians", "AI Researchers"],
        "availability": "Available", "h_index": 12,
        "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop",
        "collaboration_score": 76, "publication_score": 61, "expertise_score": 70, "community_score": 58,
    },
    {
        "email": "aiko.tanaka@synaptiq.academy", "password": "demo123",
        "full_name": "Aiko Tanaka", "institution": "University of Tokyo", "department": "Economics",
        "country": "Japan", "academic_role": "Professor",
        "user_type": "university_faculty", "primary_domain": "both",
        "biography": "Behavioural economics and decision science. Editor at JEBO.",
        "research_areas": ["Economics", "Management"],
        "skills": ["SEM", "Regression Analysis", "R", "Python"],
        "can_contribute": ["Statistics", "Methodology", "Writing"],
        "looking_for": ["Co-authors"],
        "availability": "Limited Availability", "h_index": 24,
        "avatar_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&h=400&fit=crop",
        "collaboration_score": 92, "publication_score": 88, "expertise_score": 90, "community_score": 71,
    },
    {
        "email": "rafael.santos@synaptiq.academy", "password": "demo123",
        "full_name": "Rafael Santos", "institution": "Universidade de São Paulo", "department": "Engineering",
        "country": "Brazil", "academic_role": "Assistant Professor",
        "user_type": "university_faculty", "primary_domain": "both",
        "biography": "Renewable energy systems, optimization, and policy. Horizon Europe alumnus.",
        "research_areas": ["Engineering", "Public Health"],
        "skills": ["Python", "Regression Analysis", "PLS-SEM"],
        "can_contribute": ["Data Analysis", "Grant Writing"],
        "looking_for": ["Economists", "Engineers"],
        "availability": "Available", "h_index": 9,
        "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
        "collaboration_score": 68, "publication_score": 52, "expertise_score": 64, "community_score": 49,
    },
    {
        "email": "priya.iyer@synaptiq.academy", "password": "demo123",
        "full_name": "Priya Iyer", "institution": "IIT Bombay", "department": "Psychology",
        "country": "India", "academic_role": "Lecturer",
        "user_type": "university_faculty", "primary_domain": "both",
        "biography": "Educational psychology and learning analytics. RCT specialist.",
        "research_areas": ["Education", "Psychology"],
        "skills": ["SPSS", "Qualitative Research", "SEM"],
        "can_contribute": ["Methodology", "Literature Review"],
        "looking_for": ["Co-authors", "Statisticians"],
        "availability": "Available", "h_index": 7,
        "avatar_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop",
        "collaboration_score": 71, "publication_score": 44, "expertise_score": 66, "community_score": 60,
    },
    {
        "email": "lukas.schmidt@synaptiq.academy", "password": "demo123",
        "full_name": "Lukas Schmidt", "institution": "Heidelberg University", "department": "Cybersecurity",
        "country": "Germany", "academic_role": "PhD Candidate",
        "user_type": "phd_candidate", "primary_domain": "research",
        "biography": "PhD on adversarial ML for medical imaging. Co-author on three top-tier venues.",
        "research_areas": ["Cybersecurity", "Artificial Intelligence", "Healthcare"],
        "skills": ["Python", "Regression Analysis"],
        "can_contribute": ["Data Analysis", "Writing"],
        "looking_for": ["Co-authors", "Healthcare Experts"],
        "availability": "Available", "h_index": 4,
        "avatar_url": "https://images.unsplash.com/photo-1633332755192-727a05c4013d?w=400&h=400&fit=crop",
        "collaboration_score": 58, "publication_score": 32, "expertise_score": 54, "community_score": 41,
    },
]


DEMO_COLLABS = [
    {
        "title": "Looking for a statistician for a healthcare paper",
        "description": "We have a 2,400-patient cardiology dataset and need a statistician comfortable with mixed-effects models and survival analysis. Target journal: JAMA Cardiology.",
        "collab_type": "Journal Article", "research_area": "Healthcare",
        "skills_needed": ["R", "SPSS", "Regression Analysis"],
        "team_size": 3, "duration": "4 months",
        "publication_goal": "Q1 cardiology journal", "funding_status": "Not funded",
        "creator_idx": 1,
    },
    {
        "title": "Seeking AI expert for Horizon Europe proposal",
        "description": "Building a consortium for the next Horizon Europe Health cluster call. Need an AI methods lead with track record in explainable ML for clinical decision support.",
        "collab_type": "Grant Proposal", "research_area": "Artificial Intelligence",
        "skills_needed": ["Python", "Systematic Literature Review"],
        "team_size": 6, "duration": "6 months",
        "publication_goal": "Funded project + 2 publications", "funding_status": "Pending application",
        "creator_idx": 0,
    },
    {
        "title": "Systematic Review: Behavioural Nudges in Public Health",
        "description": "Pre-registered systematic review on nudge interventions in public health since 2015. Looking for two reviewers and a methods checker familiar with PRISMA 2020.",
        "collab_type": "Systematic Review", "research_area": "Public Health",
        "skills_needed": ["Systematic Literature Review", "Qualitative Research"],
        "team_size": 4, "duration": "5 months",
        "publication_goal": "Lancet Public Health", "funding_status": "Internal grant",
        "creator_idx": 2,
    },
    {
        "title": "Meta-analysis on Renewable Energy Policy Effectiveness",
        "description": "Cross-country meta-analysis on feed-in tariffs and adoption rates. Datasets are gathered; need a co-author for the econometric layer.",
        "collab_type": "Meta-analysis", "research_area": "Engineering",
        "skills_needed": ["Regression Analysis", "Python", "PLS-SEM"],
        "team_size": 3, "duration": "3 months",
        "publication_goal": "Energy Policy", "funding_status": "Not funded",
        "creator_idx": 3,
    },
    {
        "title": "Co-author for chapter on Adversarial ML in Healthcare",
        "description": "Invited chapter for a Springer handbook. Need a clinician co-author to ensure the case studies hold up to clinical scrutiny.",
        "collab_type": "Book Chapter", "research_area": "Cybersecurity",
        "skills_needed": ["Qualitative Research"],
        "team_size": 2, "duration": "2 months",
        "publication_goal": "Springer Handbook", "funding_status": "Not funded",
        "creator_idx": 5,
    },
    {
        "title": "RCT on Adaptive Learning Platforms in Indian Universities",
        "description": "Designing a multi-site RCT across three institutions. Need a co-PI with experience in pre-registration and statistical power analysis.",
        "collab_type": "Research Project", "research_area": "Education",
        "skills_needed": ["SPSS", "SEM", "Regression Analysis"],
        "team_size": 5, "duration": "12 months",
        "publication_goal": "British Journal of Educational Psychology", "funding_status": "Funded",
        "creator_idx": 4,
    },
]


DEMO_GRANTS = [
    {"title": "Horizon Europe - Health Cluster Call 2026", "amount": "€8M", "deadline": "2026-04-15",
     "agency": "European Commission", "research_areas": ["Healthcare", "Artificial Intelligence"]},
    {"title": "ERC Starting Grant", "amount": "€1.5M", "deadline": "2026-03-30",
     "agency": "European Research Council", "research_areas": ["Artificial Intelligence", "Engineering"]},
    {"title": "NIH R01 Behavioural Health", "amount": "$2.4M", "deadline": "2026-05-10",
     "agency": "National Institutes of Health", "research_areas": ["Public Health", "Psychology"]},
    {"title": "Wellcome Discovery Award", "amount": "£3M", "deadline": "2026-06-01",
     "agency": "Wellcome Trust", "research_areas": ["Healthcare"]},
    {"title": "Erasmus+ Cooperation Partnerships", "amount": "€400K", "deadline": "2026-03-05",
     "agency": "European Commission", "research_areas": ["Education"]},
]


DEMO_CONFERENCES = [
    {"name": "NeurIPS 2026", "date": "2026-12-08", "location": "Vancouver, Canada", "rank": "A*",
     "deadline": "2026-05-20", "research_areas": ["Artificial Intelligence"]},
    {"name": "Academy of Management Meeting", "date": "2026-08-10", "location": "Chicago, USA", "rank": "A",
     "deadline": "2026-01-15", "research_areas": ["Management", "Economics"]},
    {"name": "ICML 2026", "date": "2026-07-15", "location": "Vienna, Austria", "rank": "A*",
     "deadline": "2026-02-01", "research_areas": ["Artificial Intelligence"]},
    {"name": "European Health Psychology Conference", "date": "2026-09-02", "location": "Berlin, Germany",
     "rank": "B", "deadline": "2026-03-15", "research_areas": ["Psychology", "Public Health"]},
    {"name": "IEEE S&P 2026", "date": "2026-05-18", "location": "San Francisco, USA", "rank": "A*",
     "deadline": "2026-01-08", "research_areas": ["Cybersecurity"]},
]


_IS_PROD = os.environ.get("APP_ENV", "development").lower() in ("prod", "production")
_DEFAULT_ADMIN_PASSWORD = "admin123"
_DEFAULT_SA_PASSWORD = "SuperAdmin123"


def _check_default_creds_in_prod(env_key: str, value: str, default: str, label: str):
    """AUTH-010: Refuse to seed with default/weak credentials in production."""
    if _IS_PROD and value == default:
        raise RuntimeError(
            f"[AUTH-010] {label} is using the default value '{default}'. "
            f"Set the {env_key} environment variable to a strong credential before deploying to production."
        )


async def ensure_super_admin_exists(db) -> dict:
    """Lightweight startup check — ONLY verifies/heals the protected super-admin account.

    Does NOT touch demo data, other users, or unrelated collections.
    Called on every server startup before routes are served.

    Returns a status dict describing what was done.
    """
    PROTECTED_EMAIL = "admin@synaptiq.academy"
    now_iso = datetime.now(timezone.utc).isoformat()
    sa_password = os.environ.get("SUPER_ADMIN_PASSWORD", _DEFAULT_SA_PASSWORD)

    doc = await db.users.find_one({"email": PROTECTED_EMAIL})
    action = "none"

    if not doc:
        # First boot: create the account
        _check_default_creds_in_prod("SUPER_ADMIN_PASSWORD", sa_password, _DEFAULT_SA_PASSWORD, "SUPER_ADMIN_PASSWORD")
        await db.users.insert_one({
            "email": PROTECTED_EMAIL,
            "password_hash": hash_password(sa_password),
            "full_name": "SYNAPTIQ Super Admin",
            "role": "super_admin",
            "institution": "SYNAPTIQ HQ",
            "department": "Operations",
            "country": "Global",
            "academic_role": "Super Administrator",
            "biography": "Sole platform super administrator.",
            "research_areas": [], "skills": [], "can_contribute": [], "looking_for": [],
            "availability": "Available", "h_index": 0, "avatar_url": "",
            "collaboration_score": 100, "publication_score": 0,
            "expertise_score": 100, "community_score": 100,
            "connections": [], "onboarded": True,
            "email_verified": True, "email_verified_at": now_iso,
            "plan_code": "institution",
            "subscription_status": "active",
            "credits_balance": 1_000_000,
            "credits_pack_balance": 0,
            "credits_monthly_allowance": 1_000_000,
            "credits_reset_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "failed_login_count": 0, "locked_until": None,
            "protected": True,
            "mfa_enabled": False,
            "created_at": now_iso,
        })
        action = "created"
    else:
        # Heal any tampering
        upd: dict = {}
        if doc.get("role") != "super_admin":     upd["role"] = "super_admin"
        if doc.get("plan_code") != "institution": upd["plan_code"] = "institution"
        if not doc.get("email_verified"):         upd["email_verified"] = True
        if not doc.get("protected"):              upd["protected"] = True
        if doc.get("status") in ("suspended", "banned"):
            upd["status"] = None
        if upd:
            await db.users.update_one(
                {"_id": doc["_id"]},
                {"$set": {**upd, "updated_at": now_iso},
                 "$unset": {"suspended_at": "", "ban_reason": ""}},
            )
            action = "healed"

    # Strip super_admin from any account that is NOT in the authorised SUPER_ADMIN_EMAILS list.
    # Accounts in that list are allowed to keep role=super_admin in the DB.
    _sa_whitelist = {
        e.strip().lower()
        for e in os.environ.get("SUPER_ADMIN_EMAILS", PROTECTED_EMAIL).split(",")
        if e.strip()
    } | {PROTECTED_EMAIL.lower()}
    stripped = await db.users.update_many(
        {"role": "super_admin", "email": {"$nin": list(_sa_whitelist)}},
        {"$set": {"role": "user"}},
    )

    return {
        "action": action,
        "protected_email": PROTECTED_EMAIL,
        "rogue_stripped": stripped.modified_count,
    }


async def seed_admin_and_demo(db):
    # ── Protected Super Administrator ────────────────────────────────────────
    # admin@synaptiq.academy is the sole permanent super administrator.
    # This account is always created/upgraded on startup and can never be
    # demoted, suspended, or deleted via the API.
    super_admin_email = "admin@synaptiq.academy"
    super_admin_password = os.environ.get("SUPER_ADMIN_PASSWORD", _DEFAULT_SA_PASSWORD)
    _check_default_creds_in_prod("SUPER_ADMIN_PASSWORD", super_admin_password, _DEFAULT_SA_PASSWORD, "SUPER_ADMIN_PASSWORD")
    sa_existing = await db.users.find_one({"email": super_admin_email})
    now_iso = datetime.now(timezone.utc).isoformat()
    if not sa_existing:
        await db.users.insert_one({
            "email": super_admin_email,
            "password_hash": hash_password(super_admin_password),
            "full_name": "SYNAPTIQ Super Admin",
            "role": "super_admin",
            "institution": "SYNAPTIQ HQ",
            "department": "Operations",
            "country": "Global",
            "academic_role": "Super Administrator",
            "biography": "Sole platform super administrator with unrestricted access.",
            "research_areas": [], "skills": [], "can_contribute": [], "looking_for": [],
            "availability": "Available", "h_index": 0, "avatar_url": "",
            "collaboration_score": 100, "publication_score": 0,
            "expertise_score": 100, "community_score": 100,
            "connections": [], "onboarded": True,
            "email_verified": True, "email_verified_at": now_iso,
            "plan_code": "institution",
            "subscription_status": "active",
            "credits_balance": 1000000,
            "credits_pack_balance": 0,
            "credits_monthly_allowance": 1000000,
            "credits_reset_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "failed_login_count": 0, "locked_until": None,
            "protected": True,
            "created_at": now_iso,
        })
    else:
        # Ensure the existing account has correct role and attributes regardless of
        # what it was created with previously.
        upd: dict = {}
        if sa_existing.get("role") != "super_admin":
            upd["role"] = "super_admin"
        if sa_existing.get("plan_code") != "institution":
            upd["plan_code"] = "institution"
        if not sa_existing.get("email_verified"):
            upd["email_verified"] = True
        if not sa_existing.get("protected"):
            upd["protected"] = True
        if sa_existing.get("status") in ("suspended", "banned"):
            upd["status"] = None          # lift any suspension/ban
        if upd:
            await db.users.update_one({"_id": sa_existing["_id"]}, {"$set": upd, "$unset": {"suspended_at": "", "ban_reason": ""}})

    # ── Strip super_admin from accounts not in the authorised whitelist ───────
    # Any account with role=super_admin that is NOT listed in SUPER_ADMIN_EMAILS
    # (or the hard-coded protected email) is demoted to "user".
    _seed_sa_whitelist = {
        e.strip().lower()
        for e in os.environ.get("SUPER_ADMIN_EMAILS", super_admin_email).split(",")
        if e.strip()
    } | {super_admin_email.lower()}
    await db.users.update_many(
        {"role": "super_admin", "email": {"$nin": list(_seed_sa_whitelist)}},
        {"$set": {"role": "user"}},
    )

    # Demo users and sample collaborations — never created in production.
    # All demo records carry is_demo: True so they can be filtered from API responses.
    if not _IS_PROD:
        created_user_ids = []
        for u in DEMO_USERS:
            existing = await db.users.find_one({"email": u["email"]})
            if existing:
                created_user_ids.append(str(existing["_id"]))
                # Ensure legacy records are tagged
                if not existing.get("is_demo"):
                    await db.users.update_one({"_id": existing["_id"]}, {"$set": {"is_demo": True}})
                continue
            doc = {
                "email": u["email"],
                "password_hash": hash_password(u["password"]),
                "full_name": u["full_name"],
                "role": "user",
                "is_demo": True,
                "institution": u["institution"],
                "department": u["department"],
                "country": u["country"],
                "academic_role": u["academic_role"],
                "user_type": u.get("user_type"),
                "primary_domain": u.get("primary_domain"),
                "biography": u["biography"],
                "orcid": u.get("orcid", ""),
                "google_scholar": u.get("google_scholar", ""),
                "researchgate": "",
                "scopus_id": "",
                "website": u.get("website", ""),
                "research_areas": u["research_areas"],
                "skills": u["skills"],
                "can_contribute": u["can_contribute"],
                "looking_for": u["looking_for"],
                "availability": u["availability"],
                "avatar_url": u["avatar_url"],
                "h_index": u["h_index"],
                "collaboration_score": u["collaboration_score"],
                "publication_score": u["publication_score"],
                "expertise_score": u["expertise_score"],
                "community_score": u["community_score"],
                "connections": [],
                "onboarded": True,
                "email_verified": True, "email_verified_at": datetime.now(timezone.utc).isoformat(),
                "failed_login_count": 0, "locked_until": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            res = await db.users.insert_one(doc)
            created_user_ids.append(str(res.inserted_id))

        # Sample collaborations — seed only if none exist yet (real records excluded via is_demo filter)
        if await db.collaborations.count_documents({"is_demo": {"$ne": True}}) == 0 \
                and await db.collaborations.count_documents({"is_demo": True}) == 0:
            for c in DEMO_COLLABS:
                creator_id = created_user_ids[c["creator_idx"]]
                collab_doc = {
                    "title": c["title"],
                    "description": c["description"],
                    "collab_type": c["collab_type"],
                    "research_area": c["research_area"],
                    "skills_needed": c["skills_needed"],
                    "team_size": c["team_size"],
                    "duration": c["duration"],
                    "publication_goal": c["publication_goal"],
                    "funding_status": c["funding_status"],
                    "creator_id": creator_id,
                    "status": "open",
                    "is_demo": True,
                    "members": [creator_id],
                    "applications_count": 0,
                    "created_at": (datetime.now(timezone.utc) - timedelta(days=c["creator_idx"] * 2)).isoformat(),
                }
                res = await db.collaborations.insert_one(collab_doc)
                # Auto-create project
                proj = {
                    "title": c["title"],
                    "description": c["description"],
                    "visibility": "team",
                    "owner_id": creator_id,
                    "is_demo": True,
                    "members": [creator_id],
                    "collaboration_id": str(res.inserted_id),
                    "problem_statement": "",
                    "research_gap": "",
                    "objectives": [], "research_questions": [], "hypotheses": [],
                    "expected_contributions": "",
                    "methodology": "", "data_sources": "", "sampling": "",
                    "analysis_methods": "", "ethics": "",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                p_res = await db.projects.insert_one(proj)
                await db.collaborations.update_one(
                    {"_id": res.inserted_id},
                    {"$set": {"project_id": str(p_res.inserted_id)}}
                )

    if await db.grants.count_documents({}) == 0:
        await db.grants.insert_many(DEMO_GRANTS)
    if await db.conferences.count_documents({}) == 0:
        await db.conferences.insert_many(DEMO_CONFERENCES)

    # Backfill user_type/primary_domain for users who registered before these fields existed
    from models import ACADEMIC_ROLE_MIGRATION_MAP
    async for u in db.users.find({"user_type": {"$exists": False}}):
        raw_role = (u.get("academic_role") or "").strip().lower()
        mapped_type = ACADEMIC_ROLE_MIGRATION_MAP.get(raw_role)
        await db.users.update_one(
            {"_id": u["_id"]},
            {"$set": {"user_type": mapped_type, "primary_domain": None}},
        )

    # Backfill missing fields on existing users for Phase III (SaaS)
    async for u in db.users.find({"plan_code": {"$exists": False}}):
        await db.users.update_one(
            {"_id": u["_id"]},
            {"$set": {
                "plan_code": "free",
                "credits_balance": 50,
                "credits_monthly_allowance": 50,
                "credits_pack_balance": 0,
                "credits_reset_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "first_name": (u.get("full_name", "").split() + [""])[0],
                "last_name": " ".join(u.get("full_name", "").split()[1:]),
                "research_interests": u.get("research_interests", u.get("research_areas", [])),
                "research_keywords": u.get("research_keywords", []),
                "linkedin": u.get("linkedin", ""),
                "publications_count": u.get("publications_count", 0),
                "conferences_count": u.get("conferences_count", 0),
                "onboarded": u.get("onboarded", True),
            }},
        )

    # Ensure pack_balance exists for all users (one-time backfill)
    await db.users.update_many({"credits_pack_balance": {"$exists": False}},
                               {"$set": {"credits_pack_balance": 0}})

    # Plans catalogue — overwrite to reflect latest catalogue
    for p in PLANS:
        await db.plans.update_one({"code": p["code"]}, {"$set": p}, upsert=True)
    # Drop any stale plan codes that no longer exist in the catalogue
    current_codes = [p["code"] for p in PLANS]
    await db.plans.delete_many({"code": {"$nin": current_codes}})

    # Credit packs — seed/upsert
    from plans_catalogue import CREDIT_PACKS
    for pk in CREDIT_PACKS:
        await db.credit_packs.update_one({"code": pk["code"]}, {"$set": pk}, upsert=True)

    # Indexes
    await db.users.create_index("email", unique=True)
    await db.collaborations.create_index("creator_id")
    await db.projects.create_index("owner_id")
    await db.tasks.create_index("project_id")
    await db.messages.create_index("conversation_id")
    await db.notifications.create_index("user_id")

    # Phase 2 seed (journals, expanded conferences/funding, workspaces, manuscripts, repository)
    await seed_phase2(db)
