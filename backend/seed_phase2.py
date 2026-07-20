"""Phase 2 seed data: journals, expanded conferences/funding, workspaces, manuscripts, repository."""
from datetime import datetime, timezone


JOURNALS = [
    {"title": "Nature", "publisher": "Springer Nature", "impact_factor": 64.8, "citescore": 90.2, "sjr": 18.5,
     "quartile": "Q1", "subjects": ["Multidisciplinary"], "scope_keywords": "general science, breakthrough discoveries",
     "apc": "$11,690 (Open Access)", "review_time": "8 weeks median", "acceptance_rate": "8%", "open_access": True,
     "submission_url": "https://www.nature.com/nature/for-authors/submit",
     "description": "The world's most cited scientific journal — primary research across all disciplines."},
    {"title": "Science", "publisher": "AAAS", "impact_factor": 56.9, "citescore": 86.4, "sjr": 16.1,
     "quartile": "Q1", "subjects": ["Multidisciplinary"], "scope_keywords": "all sciences, peer review, original research",
     "apc": "Subscription / hybrid OA", "review_time": "6 weeks median", "acceptance_rate": "7%", "open_access": False,
     "submission_url": "https://www.science.org/content/page/contributing-science-family-journals",
     "description": "Weekly journal of the AAAS publishing original research across the sciences."},
    {"title": "Cell", "publisher": "Elsevier", "impact_factor": 64.5, "citescore": 79.8, "sjr": 19.2,
     "quartile": "Q1", "subjects": ["Biology", "Healthcare"], "scope_keywords": "molecular biology, cell biology",
     "apc": "Hybrid OA", "review_time": "10 weeks median", "acceptance_rate": "11%", "open_access": False,
     "submission_url": "https://www.cell.com/cell/authors",
     "description": "Flagship biology journal — molecular, cellular, and integrative biology."},
    {"title": "The Lancet", "publisher": "Elsevier", "impact_factor": 98.4, "citescore": 105.4, "sjr": 18.0,
     "quartile": "Q1", "subjects": ["Healthcare", "Public Health"], "scope_keywords": "global health, clinical medicine",
     "apc": "Hybrid OA", "review_time": "5 weeks median", "acceptance_rate": "5%", "open_access": False,
     "submission_url": "https://www.thelancet.com/lancet/information-for-authors",
     "description": "Independent general medical journal — clinical research and global health."},
    {"title": "JAMA", "publisher": "AMA", "impact_factor": 56.3, "citescore": 32.1, "sjr": 14.4,
     "quartile": "Q1", "subjects": ["Healthcare", "Public Health"], "scope_keywords": "clinical medicine, RCTs",
     "apc": "Hybrid OA", "review_time": "4 weeks median", "acceptance_rate": "8%", "open_access": False,
     "submission_url": "https://jamanetwork.com/journals/jama/pages/instructions-for-authors",
     "description": "Journal of the American Medical Association — peer-reviewed clinical research."},
    {"title": "Nature Methods", "publisher": "Springer Nature", "impact_factor": 47.9, "citescore": 39.4, "sjr": 11.6,
     "quartile": "Q1", "subjects": ["Artificial Intelligence", "Healthcare"], "scope_keywords": "methods, computational biology",
     "apc": "$11,690 (Open Access)", "review_time": "9 weeks median", "acceptance_rate": "16%", "open_access": True,
     "submission_url": "https://www.nature.com/nmeth/submission-guidelines",
     "description": "Novel methods across the life sciences — including computational and AI methods."},
    {"title": "ACM Computing Surveys", "publisher": "ACM", "impact_factor": 23.8, "citescore": 33.6, "sjr": 6.9,
     "quartile": "Q1", "subjects": ["Artificial Intelligence", "Cybersecurity", "Engineering"],
     "scope_keywords": "surveys, AI, security, software", "apc": "$1,800 (OA optional)",
     "review_time": "12 weeks median", "acceptance_rate": "21%", "open_access": False,
     "submission_url": "https://dl.acm.org/journal/csur/author-guidelines",
     "description": "Comprehensive, tutorial-style surveys of active areas of computer science research."},
    {"title": "Energy Policy", "publisher": "Elsevier", "impact_factor": 7.6, "citescore": 12.4, "sjr": 1.8,
     "quartile": "Q1", "subjects": ["Engineering", "Economics", "Public Health"],
     "scope_keywords": "energy policy, renewables, sustainability", "apc": "$3,900 (OA optional)",
     "review_time": "8 weeks median", "acceptance_rate": "24%", "open_access": False,
     "submission_url": "https://www.elsevier.com/journals/energy-policy/0301-4215/guide-for-authors",
     "description": "Political, economic, planning, environmental and social aspects of energy."},
    {"title": "Journal of Economic Behavior & Organization", "publisher": "Elsevier", "impact_factor": 2.3, "citescore": 4.6, "sjr": 1.2,
     "quartile": "Q1", "subjects": ["Economics", "Management"], "scope_keywords": "behavioural economics, organizations",
     "apc": "$2,790 (OA optional)", "review_time": "10 weeks median", "acceptance_rate": "12%", "open_access": False,
     "submission_url": "https://www.elsevier.com/journals/journal-of-economic-behavior-and-organization/0167-2681/guide-for-authors",
     "description": "Theoretical, experimental and empirical research on the behaviour of economic agents and organisations."},
    {"title": "Computers & Security", "publisher": "Elsevier", "impact_factor": 5.6, "citescore": 11.1, "sjr": 1.5,
     "quartile": "Q1", "subjects": ["Cybersecurity"], "scope_keywords": "cybersecurity, infosec, applied research",
     "apc": "$3,250 (OA optional)", "review_time": "7 weeks median", "acceptance_rate": "19%", "open_access": False,
     "submission_url": "https://www.elsevier.com/journals/computers-and-security/0167-4048/guide-for-authors",
     "description": "Operational research on cybersecurity, threat detection, defence, and privacy."},
    {"title": "British Journal of Educational Psychology", "publisher": "Wiley", "impact_factor": 3.7, "citescore": 7.2, "sjr": 1.4,
     "quartile": "Q1", "subjects": ["Education", "Psychology"], "scope_keywords": "learning, education research, psychology",
     "apc": "$3,070 (OA optional)", "review_time": "9 weeks median", "acceptance_rate": "18%", "open_access": False,
     "submission_url": "https://onlinelibrary.wiley.com/journal/20448279",
     "description": "Original empirical research on educational and developmental psychology."},
    {"title": "PLOS ONE", "publisher": "PLOS", "impact_factor": 3.7, "citescore": 6.0, "sjr": 0.9,
     "quartile": "Q2", "subjects": ["Multidisciplinary"], "scope_keywords": "open access, all sciences",
     "apc": "$1,805 (Open Access)", "review_time": "5 weeks median", "acceptance_rate": "49%", "open_access": True,
     "submission_url": "https://journals.plos.org/plosone/s/submission-guidelines",
     "description": "Inclusive open access journal — methodologically rigorous research from all disciplines."},
]


CONFERENCES_EXTRA = [
    {"name": "ACL 2026", "date": "2026-08-04", "location": "Vienna, Austria", "rank": "A*",
     "deadline": "2026-02-15", "research_areas": ["Artificial Intelligence"],
     "topics": ["NLP", "Computational Linguistics", "Machine Translation", "Dialogue Systems"],
     "organizer": "Association for Computational Linguistics",
     "important_dates": {"Paper submission": "2026-02-15", "Notification": "2026-05-10",
                          "Camera-ready": "2026-06-12", "Conference": "2026-08-04 → 2026-08-09"},
     "submission_url": "https://2026.aclweb.org/", "description": "Premier conference on computational linguistics and NLP."},
    {"name": "CHI 2026", "date": "2026-04-26", "location": "Yokohama, Japan", "rank": "A*",
     "deadline": "2025-09-12", "research_areas": ["Psychology", "Engineering"],
     "topics": ["Human-Computer Interaction", "UX", "Accessibility", "Design"],
     "organizer": "ACM SIGCHI",
     "important_dates": {"Paper submission": "2025-09-12", "Notification": "2025-12-15", "Conference": "2026-04-26 → 2026-05-01"},
     "submission_url": "https://chi2026.acm.org/", "description": "ACM CHI Conference on Human Factors in Computing Systems."},
    {"name": "SIGIR 2026", "date": "2026-07-13", "location": "Singapore", "rank": "A*",
     "deadline": "2026-01-30", "research_areas": ["Artificial Intelligence"],
     "topics": ["Information Retrieval", "Search", "Recommender Systems"],
     "organizer": "ACM SIGIR",
     "important_dates": {"Paper submission": "2026-01-30", "Notification": "2026-04-15", "Conference": "2026-07-13 → 2026-07-17"},
     "submission_url": "https://sigir.org/sigir2026/", "description": "Premier venue for IR and recommender systems."},
    {"name": "ICIS 2026", "date": "2026-12-13", "location": "Dublin, Ireland", "rank": "A*",
     "deadline": "2026-05-01", "research_areas": ["Management"],
     "topics": ["Information Systems", "Digital Transformation", "Tech in Organizations"],
     "organizer": "AIS",
     "important_dates": {"Paper submission": "2026-05-01", "Notification": "2026-08-15", "Conference": "2026-12-13 → 2026-12-16"},
     "submission_url": "https://icis2026.aisnet.org/", "description": "International Conference on Information Systems."},
    {"name": "Society for Research on Educational Effectiveness", "date": "2026-09-22", "location": "Washington DC, USA", "rank": "B",
     "deadline": "2026-04-30", "research_areas": ["Education", "Psychology"],
     "topics": ["Causal inference in education", "RCTs", "Learning analytics"],
     "organizer": "SREE",
     "important_dates": {"Paper submission": "2026-04-30", "Notification": "2026-07-01", "Conference": "2026-09-22 → 2026-09-24"},
     "submission_url": "https://www.sree.org/", "description": "Methodological rigour in education research."},
]


# Extra funding/grants opportunities (additional to the 5 already seeded)
FUNDING_EXTRA = [
    {"title": "Marie Skłodowska-Curie Postdoctoral Fellowship", "amount": "€200K", "deadline": "2026-09-15",
     "agency": "European Commission", "research_areas": ["Artificial Intelligence", "Healthcare", "Public Health", "Engineering"],
     "description": "Two-year mobility fellowship for postdoctoral researchers in any discipline.",
     "eligibility": "PhD obtained within 8 years prior to deadline; mobility rule (12-of-36 months) applies.",
     "funding_type": "Fellowship", "duration": "12-24 months"},
    {"title": "NSF CAREER Award", "amount": "$500K", "deadline": "2026-07-25",
     "agency": "National Science Foundation", "research_areas": ["Artificial Intelligence", "Engineering", "Cybersecurity"],
     "description": "Foundation's most prestigious award for early-career faculty.",
     "eligibility": "US-based tenure-track faculty, untenured, US citizenship not required.",
     "funding_type": "Grant", "duration": "5 years"},
    {"title": "Volkswagen Foundation - Mixed Methods in Humanities", "amount": "€800K", "deadline": "2026-04-20",
     "agency": "Volkswagen Foundation", "research_areas": ["Psychology", "Education", "Economics"],
     "description": "Supports innovative methodological approaches in the humanities and social sciences.",
     "eligibility": "Researchers based in Germany or affiliated with German institutions.",
     "funding_type": "Grant", "duration": "3 years"},
    {"title": "Templeton World Charity Foundation - Global Innovations", "amount": "$1.2M", "deadline": "2026-08-10",
     "agency": "Templeton World Charity", "research_areas": ["Public Health", "Psychology", "Education"],
     "description": "Cross-disciplinary projects on human flourishing and global well-being.",
     "eligibility": "Open globally; institutional affiliation required.",
     "funding_type": "Grant", "duration": "2-3 years"},
    {"title": "Wellcome Leap - Bold Bets in Health", "amount": "$10M", "deadline": "2026-06-30",
     "agency": "Wellcome Leap", "research_areas": ["Healthcare"],
     "description": "Programme-style funding for radical advances in human health.",
     "eligibility": "Consortia welcome; demonstrated track record in translational research.",
     "funding_type": "Programme", "duration": "3-5 years"},
    {"title": "Fulbright Scholar Program", "amount": "$45K", "deadline": "2026-09-15",
     "agency": "US Department of State", "research_areas": ["Education", "Economics", "Public Health", "Psychology"],
     "description": "International exchange programme for US scholars to teach/research abroad.",
     "eligibility": "US citizens with PhD or significant professional experience.",
     "funding_type": "Fellowship", "duration": "3-12 months"},
    {"title": "Royal Society University Research Fellowship", "amount": "£1.2M", "deadline": "2026-09-08",
     "agency": "Royal Society", "research_areas": ["Artificial Intelligence", "Engineering", "Healthcare"],
     "description": "Long-term independent research fellowship for outstanding early-career scientists in the UK.",
     "eligibility": "PhD obtained 3-8 years ago; based in UK or willing to relocate.",
     "funding_type": "Fellowship", "duration": "8 years"},
]


def repository_seed_for(owner_id: str, names: list):
    items = []
    types = ["Document", "Dataset", "Template", "Literature"]
    for i, name in enumerate(names):
        items.append({
            "title": name,
            "type": types[i % len(types)],
            "description": f"Sample {types[i % len(types)].lower()} for reference and reuse.",
            "url": "",
            "tags": ["sample", "reusable"],
            "owner_id": owner_id,
            "owner_name": "",
            "project_id": "",
            "workspace_id": "",
            "visibility": "private",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return items


async def seed_phase2(db):
    # Journals
    if await db.journals.count_documents({}) == 0:
        await db.journals.insert_many(JOURNALS)

    # Conferences extra (only if existing count is low)
    existing_conf = await db.conferences.count_documents({})
    if existing_conf < 10:
        # Backfill topics/organizer fields on existing
        async for c in db.conferences.find({"topics": {"$exists": False}}):
            await db.conferences.update_one(
                {"_id": c["_id"]},
                {"$set": {
                    "topics": c.get("research_areas", []),
                    "organizer": c.get("organizer", "Society / Association"),
                    "important_dates": {"Paper submission": c.get("deadline", ""), "Conference": c.get("date", "")},
                    "submission_url": c.get("submission_url", ""),
                    "description": c.get("description", "Annual scholarly conference in the field."),
                }},
            )
        await db.conferences.insert_many(CONFERENCES_EXTRA)

    # Extra funding (in grants collection)
    if await db.grants.count_documents({}) < 10:
        # Add eligibility/duration/funding_type to existing entries first
        async for g in db.grants.find({"eligibility": {"$exists": False}}):
            await db.grants.update_one(
                {"_id": g["_id"]},
                {"$set": {
                    "eligibility": "Open to qualified researchers; consult agency call text for full criteria.",
                    "funding_type": "Grant",
                    "duration": "2-3 years",
                    "description": "Funding call. Refer to the agency website for full programme details.",
                }},
            )
        await db.grants.insert_many(FUNDING_EXTRA)

    # Demo workspaces (one per first 2 demo users)
    if await db.workspaces.count_documents({}) == 0:
        demo_users = await db.users.find({"role": "user"}).limit(3).to_list(3)
        for u in demo_users:
            uid = str(u["_id"])
            ws_doc = {
                "name": f"{u.get('institution', 'Lab')} — {u.get('full_name', '').split()[0]} Group",
                "description": "Shared workspace for the group's collaborative research.",
                "owner_id": uid,
                "members": [uid],
                "project_ids": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            res = await db.workspaces.insert_one(ws_doc)
            await db.workspace_activity.insert_one({
                "workspace_id": str(res.inserted_id),
                "actor_id": uid,
                "actor_name": u.get("full_name", ""),
                "message": "Workspace created.",
                "kind": "system",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    # Demo manuscripts (one per first 2 demo users)
    if await db.manuscripts.count_documents({}) == 0:
        demo_users = await db.users.find({"role": "user"}).limit(3).to_list(3)
        statuses = ["draft", "under_review", "revision_requested"]
        for i, u in enumerate(demo_users):
            uid = str(u["_id"])
            ms = {
                "title": f"Working paper · {u.get('full_name', 'Author').split()[0]} et al.",
                "manuscript_type": "Journal Article",
                "project_id": "",
                "authors": [uid],
                "lead_author_id": uid,
                "status": statuses[i % len(statuses)],
                "target_journal_id": "",
                "sections": {
                    "title": f"Working paper · {u.get('full_name', 'Author').split()[0]} et al.",
                    "abstract": "Draft abstract — outline of contribution, methods, results, and implications.",
                    "introduction": "", "literature_review": "",
                    "methodology": "", "results": "", "discussion": "",
                    "conclusion": "", "references": "",
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.manuscripts.insert_one(ms)

    # Repository sample items
    if await db.repository_items.count_documents({}) == 0:
        demo_users = await db.users.find({"role": "user"}).limit(2).to_list(2)
        sample_names = [
            "PRISMA 2020 systematic review template",
            "Pilot study dataset — Q1 2026",
            "IRB consent form (English/Spanish)",
            "Smith & Lee (2024) — annotated bibliography",
        ]
        for u in demo_users:
            items = repository_seed_for(str(u["_id"]), sample_names)
            for it in items:
                it["owner_name"] = u.get("full_name", "")
            await db.repository_items.insert_many(items)

    # Indexes
    await db.journals.create_index([("title", 1)])
    await db.workspaces.create_index("owner_id")
    await db.manuscripts.create_index("authors")
    await db.repository_items.create_index("owner_id")
