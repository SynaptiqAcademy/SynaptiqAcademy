"""AI matching engine — thin wrapper over the canonical person-matching engine
(services/collab_intelligence/matching_engine.py) for network-specific role
fanout (co_author/mentor/reviewer/etc). Scoring itself is delegated to the
canonical 9-dimension engine so every part of the platform that ranks people
against each other uses the same signal."""
from datetime import datetime, timezone

from services.collab_intelligence.researcher_profiler import build_researcher_profile
from services.collab_intelligence.matching_engine import match_researchers


def _now():
    return datetime.now(timezone.utc).isoformat()


def _tokenise(text: str) -> set:
    if not text:
        return set()
    return {w.lower().strip(".,;:()[]") for w in str(text).split() if len(w) > 2}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _field_tokens(doc: dict, fields: list) -> set:
    tokens = set()
    for f in fields:
        v = doc.get(f, "")
        if isinstance(v, list):
            tokens |= _tokenise(" ".join(str(x) for x in v))
        else:
            tokens |= _tokenise(str(v))
    return tokens


_INTEREST_FIELDS = ["research_interests", "expertise", "department", "methodologies"]
_CAREER_FIELDS   = ["career_stage"]


async def compute_similarity(user: dict, candidate: dict) -> float:
    """Return 0-1 similarity between two user profiles, via the canonical engine."""
    pa = build_researcher_profile(user)
    pb = build_researcher_profile(candidate)
    return match_researchers(pa, pb).overall_score


def _explain(user: dict, candidate: dict, role: str) -> str:
    user_tokens = _field_tokens(user, _INTEREST_FIELDS)
    cand_tokens = _field_tokens(candidate, _INTEREST_FIELDS)
    shared = user_tokens & cand_tokens
    top = sorted(shared)[:5]
    if top:
        kw = ", ".join(top)
        return f"Shared expertise in {kw}. Recommended as {role}."
    return f"Strong profile alignment. Recommended as {role}."


# ── Role-specific match generators ──────────────────────────────────────────

_ROLES = [
    ("co_author",           "co-author",          lambda u, c: True),
    ("grant_partner",       "grant partner",       lambda u, c: True),
    ("research_collab",     "research collaborator", lambda u, c: True),
    ("reviewer",            "peer reviewer",       lambda u, c: c.get("career_stage") in ("senior", "professor", "mid_career")),
    ("mentor",              "mentor",              lambda u, c: _stage_higher(c, u)),
    ("doctoral_supervisor", "doctoral supervisor", lambda u, c: c.get("career_stage") in ("professor", "senior")),
    ("teaching_collab",     "teaching collaborator", lambda u, c: True),
]


def _stage_higher(a: dict, b: dict) -> bool:
    order = ["student", "postdoc", "early_career", "mid_career", "senior", "professor"]
    ai = order.index(a.get("career_stage", "")) if a.get("career_stage") in order else -1
    bi = order.index(b.get("career_stage", "")) if b.get("career_stage") in order else -1
    return ai > bi


async def get_matches_for_user(user_id: str, db, limit: int = 30) -> list:
    from bson import ObjectId
    try:
        uid = ObjectId(user_id)
    except Exception:
        return []

    user = await db["users"].find_one({"_id": uid})
    if not user:
        return []

    # Projection covers every field services.collab_intelligence.researcher_profiler
    # reads to build a ResearcherProfile, plus the fields this module's own
    # role-fanout/display logic needs (career_stage, country, trust_score, ...).
    candidates_cursor = db["users"].find(
        {"_id": {"$ne": uid}},
        {"name": 1, "full_name": 1, "first_name": 1, "last_name": 1, "email": 1,
         "institution": 1, "university": 1, "department": 1, "faculty": 1,
         "research_interests": 1, "research_areas": 1, "domains": 1, "expertise": 1,
         "keywords": 1, "research_keywords": 1, "research_methods": 1, "methods": 1,
         "statistical_expertise": 1, "statistics": 1,
         "programming_skills": 1, "software_skills": 1,
         "languages": 1, "language": 1,
         "career_stage": 1, "position": 1, "academic_position": 1, "user_type": 1,
         "h_index": 1, "publication_count": 1, "citation_count": 1,
         "peer_review_count": 1, "grant_success_rate": 1,
         "collaboration_count": 1, "active_collaborations": 1, "collaborators": 1,
         "international_collab_ratio": 1, "international_collaborations": 1,
         "availability": 1, "availability_score": 1, "response_rate": 1,
         "country": 1, "verification_level": 1, "trust_score": 1}
    ).limit(200)
    candidates = await candidates_cursor.to_list(200)

    scored = []
    for c in candidates:
        score = await compute_similarity(user, c)
        if score > 0.05:
            applicable_roles = [r for r in _ROLES if r[2](user, c)]
            for role_key, role_label, _ in applicable_roles:
                scored.append({
                    "candidate_id": str(c["_id"]),
                    "name": c.get("name", ""),
                    "institution": c.get("institution", ""),
                    "country": c.get("country", ""),
                    "career_stage": c.get("career_stage", ""),
                    "research_interests": c.get("research_interests", ""),
                    "trust_score": c.get("trust_score", 0),
                    "role": role_key,
                    "role_label": role_label,
                    "score": round(score, 3),
                    "explanation": _explain(user, c, role_label),
                    "matched_at": _now(),
                })

    scored.sort(key=lambda x: x["score"], reverse=True)
    seen = set()
    unique = []
    for m in scored:
        key = (m["candidate_id"], m["role"])
        if key not in seen:
            seen.add(key)
            unique.append(m)
        if len(unique) >= limit:
            break
    return unique


async def get_institution_matches(user_id: str, db, limit: int = 10) -> list:
    from bson import ObjectId
    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)},
                                          {"research_interests": 1, "expertise": 1, "country": 1})
    except Exception:
        return []
    if not user:
        return []

    user_tokens = _field_tokens(user, _INTEREST_FIELDS)
    cursor = db["institutions"].find({}).limit(100)
    insts = await cursor.to_list(100)

    scored = []
    for inst in insts:
        inst_tokens = _tokenise(str(inst.get("research_focus", "")))
        sim = _jaccard(user_tokens, inst_tokens)
        scored.append({
            "institution_id": str(inst["_id"]),
            "name": inst.get("name", ""),
            "country": inst.get("country", ""),
            "type": inst.get("type", ""),
            "research_focus": inst.get("research_focus", ""),
            "score": round(sim, 3),
            "explanation": f"Research focus aligns with your expertise in {', '.join(sorted(user_tokens & inst_tokens)[:3]) or 'your field'}.",
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
