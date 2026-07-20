import time
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from auth_utils import get_current_user
from db import get_db
from models import AIAssistRequest
from services.credits_service import consume_credits, refund_credits
from services.permissions import require_feature
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/health")
async def ai_health(deep: bool = False):
    """AI subsystem health check — reports provider and configuration status.

    Query params:
      deep=true  — makes live API calls to confirm authentication and measure
                   real latency (subject to a 5-minute cooldown per process).
    """
    import os
    from services.ai.engine.core import get_engine

    system_health = await get_engine().health(deep=deep)
    health_dict = system_health.to_dict()

    provider = os.environ.get("AI_MATCHING_PROVIDER", "anthropic")
    anthropic_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    openai_key = bool(os.environ.get("OPENAI_API_KEY"))

    try:
        import anthropic as _anthropic  # noqa: F401
        anthropic_pkg = True
    except ImportError:
        anthropic_pkg = False

    configured = (provider == "anthropic" and anthropic_key and anthropic_pkg) or (
        provider == "openai" and openai_key
    )

    return {
        **health_dict,
        "provider": provider,
        "anthropic_package_installed": anthropic_pkg,
        "anthropic_key_set": anthropic_key,
        "openai_key_set": openai_key,
        "mode": "live" if configured else "mock",
        "message": (
            "AI is fully operational."
            if configured
            else f"No API key configured for provider '{provider}'. "
            "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env. "
            "Mock responses are active."
        ),
    }

# ─── Compatibility matrix ────────────────────────────────────────────────────
# Defines which user_type pairs are considered compatible for collaboration.
# Symmetric but defined per source type for clarity.

_COMPATIBLE_TYPES: dict[str, list[str]] = {
    "undergraduate_student":   ["researcher", "phd_candidate", "masters_student",
                                "university_faculty", "postdoctoral_researcher"],
    "masters_student":         ["researcher", "phd_candidate", "postdoctoral_researcher",
                                "university_faculty", "masters_student"],
    "phd_candidate":           ["researcher", "postdoctoral_researcher", "university_faculty",
                                "phd_candidate", "masters_student"],
    "postdoctoral_researcher": ["researcher", "university_faculty", "phd_candidate",
                                "industry_professional", "postdoctoral_researcher"],
    "researcher":              ["researcher", "phd_candidate", "postdoctoral_researcher",
                                "university_faculty", "industry_professional"],
    "educator":                ["educator", "university_faculty", "trainer",
                                "researcher", "phd_candidate"],
    "university_faculty":      ["researcher", "phd_candidate", "postdoctoral_researcher",
                                "educator", "university_faculty", "industry_professional"],
    "trainer":                 ["trainer", "educator", "industry_professional",
                                "university_faculty"],
    "industry_professional":   ["researcher", "postdoctoral_researcher", "university_faculty",
                                "trainer", "industry_professional"],
}

# For users without a type, treat as researcher (backward compat)
_DEFAULT_COMPATIBLE = _COMPATIBLE_TYPES["researcher"]


def _get_compatible_types(user_type: str | None) -> list[str]:
    return _COMPATIBLE_TYPES.get(user_type or "", _DEFAULT_COMPATIBLE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _call_llm(system: str, user_msg: str, session_id: str, *, feature: str = "general.analysis") -> str:
    from services.ai.llm import call_llm
    try:
        return await call_llm(system=system, user_msg=user_msg, feature=feature)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM error: {str(e)[:200]}")


@router.post("/recommend-collaborators", dependencies=[Depends(require_feature("ai_assistant"))])
async def recommend_collaborators(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    charged = await consume_credits(user["id"], "ai_collaborator_matching")
    credits_used = charged.get("consumed", 5) if isinstance(charged, dict) else 5

    user_type       = user.get("user_type")
    primary_domain  = user.get("primary_domain")
    user_areas      = user.get("research_areas") or []
    user_teaching   = user.get("teaching_areas") or []
    user_expertise  = user.get("professional_expertise") or []
    compatible_types = _get_compatible_types(user_type)

    base_query = {"_id": {"$ne": ObjectId(user["id"])}, "role": {"$ne": "admin"}, "is_demo": {"$ne": True}}

    # ── Stage 1: compatibility + domain overlap ─────────────────────────────
    stage1_query = {**base_query, "user_type": {"$in": compatible_types}}

    # Narrow by domain if the user has a focused primary_domain
    if primary_domain == "research" and user_areas:
        stage1_query["research_areas"] = {"$in": user_areas}
    elif primary_domain == "teaching" and user_teaching:
        stage1_query["teaching_areas"] = {"$in": user_teaching}
    elif primary_domain == "both":
        # For hybrid users prefer others who also cover both or match on either domain
        area_overlap = {"research_areas": {"$in": user_areas}} if user_areas else {}
        teaching_overlap = {"teaching_areas": {"$in": user_teaching}} if user_teaching else {}
        if area_overlap or teaching_overlap:
            conditions = [c for c in [area_overlap, teaching_overlap] if c]
            stage1_query["$or"] = conditions if len(conditions) > 1 else conditions

    candidates = await db.users.find(stage1_query).limit(15).to_list(15)

    # ── Stage 2: fall back if < 5 found ─────────────────────────────────────
    if len(candidates) < 5:
        existing = {str(c["_id"]) for c in candidates}
        # Relax to compatible types only (drop domain filter)
        backup = await db.users.find({**base_query, "user_type": {"$in": compatible_types}}).limit(20).to_list(20)
        for c in backup:
            if str(c["_id"]) not in existing:
                candidates.append(c)
                if len(candidates) >= 15:
                    break

    # ── Stage 3: if still < 5, open pool ────────────────────────────────────
    if len(candidates) < 5:
        existing = {str(c["_id"]) for c in candidates}
        fallback = await db.users.find(base_query).limit(20).to_list(20)
        for c in fallback:
            if str(c["_id"]) not in existing:
                candidates.append(c)
                if len(candidates) >= 15:
                    break

    if not candidates:
        return {"recommendations": []}

    # ── Fetch OpenAlex metrics for current user and candidates ───────────────
    all_ids = [ObjectId(user["id"])] + [c["_id"] for c in candidates]
    metrics_docs = await db.users.find(
        {"_id": {"$in": all_ids}},
        {"openalex_metrics": 1, "h_index": 1, "publications_count": 1, "research_keywords": 1},
    ).to_list(len(all_ids))
    metrics_by_id = {str(d["_id"]): d for d in metrics_docs}

    def _openalex_line(u: dict) -> str:
        uid = str(u.get("_id", u.get("id", "")))
        m = metrics_by_id.get(uid, {})
        oam = m.get("openalex_metrics") or {}
        parts = []
        h = int(oam.get("h_index") or m.get("h_index") or 0)
        pubs = int(oam.get("works_count") or m.get("publications_count") or 0)
        cits = int(oam.get("citations") or 0)
        kws = m.get("research_keywords") or []
        if h: parts.append(f"  h-index: {h}")
        if pubs: parts.append(f"  Publications: {pubs}")
        if cits: parts.append(f"  Citations: {cits:,}")
        if kws: parts.append(f"  Keywords: {', '.join(kws[:8])}")
        return "\n".join(parts)

    # ── Build LLM prompt ─────────────────────────────────────────────────────
    def _profile_line(u: dict) -> str:
        parts = [
            f"  Name: {u.get('full_name', '')}",
            f"  Institution: {u.get('institution', '')}",
        ]
        if u.get("user_type"):
            parts.append(f"  Type: {u['user_type'].replace('_', ' ')}")
        if u.get("primary_domain"):
            parts.append(f"  Domain: {u['primary_domain']}")
        if u.get("research_areas"):
            parts.append(f"  Research areas: {', '.join(u['research_areas'])}")
        if u.get("teaching_areas"):
            parts.append(f"  Teaching areas: {', '.join(u['teaching_areas'])}")
        if u.get("professional_expertise"):
            parts.append(f"  Professional expertise: {', '.join(u['professional_expertise'])}")
        if u.get("skills"):
            parts.append(f"  Skills: {', '.join(u.get('skills', []))}")
        openalex_extra = _openalex_line(u)
        if openalex_extra:
            parts.append(openalex_extra)
        return "\n".join(parts)

    my_type_label = (user_type or "researcher").replace("_", " ")
    my_domain = primary_domain or "research"
    my_meta = metrics_by_id.get(user["id"], {})
    my_oam = my_meta.get("openalex_metrics") or {}
    my_h = int(my_oam.get("h_index") or my_meta.get("h_index") or 0)
    my_pubs = int(my_oam.get("works_count") or my_meta.get("publications_count") or 0)
    my_kws = my_meta.get("research_keywords") or []

    profile_blurb = (
        f"I am a {my_type_label} focused on {my_domain}.\n"
        f"Institution: {user.get('institution', '')}.\n"
        + (f"Research areas: {', '.join(user_areas)}.\n" if user_areas else "")
        + (f"Teaching areas: {', '.join(user_teaching)}.\n" if user_teaching else "")
        + (f"Professional expertise: {', '.join(user_expertise)}.\n" if user_expertise else "")
        + (f"Skills: {', '.join(user.get('skills', []))}.\n" if user.get("skills") else "")
        + (f"Research keywords: {', '.join(my_kws[:8])}.\n" if my_kws else "")
        + (f"h-index: {my_h}. Publications: {my_pubs}.\n" if my_h or my_pubs else "")
        + (f"Looking for: {', '.join(user.get('looking_for', []))}." if user.get("looking_for") else "")
    )

    candidate_blurbs = "\n\n".join([
        f"- ID={str(c['_id'])}\n{_profile_line(c)}"
        for c in candidates
    ])

    system = (
        "You are an academic and professional network matchmaker. "
        "Given a user's profile and a list of candidate collaborators, "
        "rank the top 5 most relevant for meaningful collaboration and explain why in ONE sentence each. "
        "Consider: domain compatibility, role complementarity, shared research/teaching areas, expertise overlap. "
        "Reply STRICTLY in this format, one per line:\n"
        "ID|reason"
    )
    prompt = f"My profile:\n{profile_blurb}\n\nCandidates:\n{candidate_blurbs}\n\nReturn top 5."

    started = time.monotonic()
    llm_success = True
    try:
        text = await _call_llm(system, prompt, session_id=f"recco-{user['id']}", feature="collaboration.researcher_matching")
    except HTTPException:
        await refund_credits(user["id"], "ai_collaborator_matching", reason="LLM error")
        llm_success = False
        credits_used = 0
        text = ""
    duration_ms = int((time.monotonic() - started) * 1000)

    # ── Parse LLM response ───────────────────────────────────────────────────
    recs = []
    cand_map = {str(c["_id"]): c for c in candidates}
    if text:
        for line in text.splitlines():
            line = line.strip().lstrip("-").strip()
            if "|" not in line:
                continue
            parts = line.split("|", 1)
            cid = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else ""
            if cid in cand_map:
                c = cand_map[cid]
                recs.append({
                    "id":                   str(c["_id"]),
                    "full_name":            c.get("full_name", ""),
                    "institution":          c.get("institution", ""),
                    "academic_role":        c.get("academic_role", ""),
                    "user_type":            c.get("user_type"),
                    "primary_domain":       c.get("primary_domain"),
                    "avatar_url":           c.get("avatar_url", ""),
                    "research_areas":       c.get("research_areas", []),
                    "teaching_areas":       c.get("teaching_areas", []),
                    "professional_expertise": c.get("professional_expertise", []),
                    "reason":               reason,
                })
            if len(recs) >= 5:
                break

    # ── Fallback heuristic ───────────────────────────────────────────────────
    if not recs:
        for c in candidates[:5]:
            overlap_r = set(c.get("research_areas", [])) & set(user_areas)
            overlap_t = set(c.get("teaching_areas", [])) & set(user_teaching)
            overlap_e = set(c.get("professional_expertise", [])) & set(user_expertise)
            if overlap_r:
                reason = f"Shared research focus in {', '.join(overlap_r)}"
            elif overlap_t:
                reason = f"Shared teaching areas in {', '.join(overlap_t)}"
            elif overlap_e:
                reason = f"Complementary expertise in {', '.join(overlap_e)}"
            else:
                reason = "Compatible role and complementary expertise"
            recs.append({
                "id":                   str(c["_id"]),
                "full_name":            c.get("full_name", ""),
                "institution":          c.get("institution", ""),
                "academic_role":        c.get("academic_role", ""),
                "user_type":            c.get("user_type"),
                "primary_domain":       c.get("primary_domain"),
                "avatar_url":           c.get("avatar_url", ""),
                "research_areas":       c.get("research_areas", []),
                "teaching_areas":       c.get("teaching_areas", []),
                "professional_expertise": c.get("professional_expertise", []),
                "reason":               reason,
            })

    try:
        await db.ai_requests.insert_one({
            "user_id":     user["id"],
            "feature":     "ai_collaborator_matching",
            "credits":     credits_used,
            "duration_ms": duration_ms,
            "success":     llm_success,
            "ref_id":      None,
            "created_at":  _now(),
        })
    except Exception:
        pass

    return {"recommendations": recs}


@router.post("/assist", dependencies=[Depends(require_feature("ai_methodology_builder"))])
async def research_assist(payload: AIAssistRequest, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    charged = await consume_credits(user["id"], "ai_methodology_builder")
    credits_used = charged.get("consumed", 10) if isinstance(charged, dict) else 10

    system = ("You are a senior academic research assistant. Help the researcher with rigorous, "
              "concise, citation-aware suggestions. Be specific and structured. Keep the response "
              "under 350 words. Use plain text — no markdown headers.")
    user_text = payload.prompt
    if payload.context:
        user_text = f"Context:\n{payload.context}\n\nQuestion:\n{payload.prompt}"

    started = time.monotonic()
    try:
        text = await _call_llm(system, user_text, session_id=f"assist-{user['id']}", feature="general.assistant")
        duration_ms = int((time.monotonic() - started) * 1000)
        try:
            await db.ai_requests.insert_one({
                "user_id":     user["id"],
                "feature":     "ai_methodology_builder",
                "credits":     credits_used,
                "duration_ms": duration_ms,
                "success":     True,
                "ref_id":      None,
                "created_at":  _now(),
            })
        except Exception:
            pass
        return {"response": text}
    except HTTPException as e:
        await refund_credits(user["id"], "ai_methodology_builder", reason=str(e.detail)[:200])
        raise
