"""AI matching engine — rule-based keyword similarity for collaborator recommendations."""
import asyncio
from datetime import datetime, timezone


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
    """Return 0-1 similarity between two user profiles."""
    user_tokens = _field_tokens(user, _INTEREST_FIELDS)
    cand_tokens = _field_tokens(candidate, _INTEREST_FIELDS)
    semantic = _jaccard(user_tokens, cand_tokens)

    # Boost for same institution country (international collab is valuable too — mild boost only)
    country_bonus = 0.05 if user.get("country") == candidate.get("country") else 0.0
    # Boost for compatible career stages (peers or mentor-mentee)
    stage_bonus = 0.0
    stage_map = {"student": 0, "postdoc": 1, "early_career": 2, "mid_career": 3, "senior": 4, "professor": 5}
    us = stage_map.get(user.get("career_stage", ""), -1)
    cs = stage_map.get(candidate.get("career_stage", ""), -1)
    if us >= 0 and cs >= 0:
        diff = abs(us - cs)
        stage_bonus = 0.1 if diff <= 1 else (0.08 if diff == 2 else 0.0)

    return min(1.0, semantic + country_bonus + stage_bonus)


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

    candidates_cursor = db["users"].find(
        {"_id": {"$ne": uid}},
        {"name": 1, "email": 1, "institution": 1, "department": 1,
         "research_interests": 1, "expertise": 1, "career_stage": 1,
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
