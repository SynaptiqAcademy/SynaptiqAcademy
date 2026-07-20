import asyncio
from bson import ObjectId
from services.integrity.providers import PROVIDER_REGISTRY


def _fuzzy_match(a: str, b: str) -> float:
    """Token-overlap similarity 0.0–1.0."""
    a_t = set(a.lower().split())
    b_t = set(b.lower().split())
    if not a_t or not b_t:
        return 0.0
    return len(a_t & b_t) / max(len(a_t), len(b_t))


_ACADEMIC_TLDS = (".edu", ".ac.uk", ".edu.au", ".ac.", ".uni.", ".university.", ".college.")


async def analyze_identity(user_id: str, db) -> dict:
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = await db.users.find_one({"_id": user_id})

    if not user:
        return {"score": 0, "checks": [], "issues": ["User record not found"], "confidence": 0}

    u = user or {}
    checks: list[dict] = []
    score = 0

    # 1. ORCID presence and validity
    orcid = (u.get("orcid") or "").strip()
    if orcid:
        res = await PROVIDER_REGISTRY["orcid"].verify("researcher", {"orcid": orcid})
        if res["found"]:
            orcid_name = res["data"].get("full_name", "")
            profile_name = u.get("full_name") or u.get("name") or ""
            name_sim = _fuzzy_match(orcid_name, profile_name)
            checks.append({"check": "orcid_valid", "passed": True, "confidence": 90, "data": res["data"]})
            checks.append({
                "check": "name_matches_orcid",
                "passed": name_sim >= 0.6,
                "confidence": int(name_sim * 100),
                "data": {"orcid_name": orcid_name, "profile_name": profile_name, "similarity": round(name_sim, 2)},
                "issue": "" if name_sim >= 0.6 else "Name differs from ORCID record",
            })
            score += 30 if name_sim >= 0.6 else 15
        else:
            checks.append({"check": "orcid_valid", "passed": False, "confidence": 0, "data": {}, "issue": f"ORCID not found: {orcid}"})
    else:
        checks.append({"check": "orcid_present", "passed": False, "confidence": 0, "data": {}, "issue": "No ORCID in profile"})

    # 2. Institution via ROR
    institution = (u.get("institution") or "").strip()
    ror_data: dict = {}
    if institution:
        ror_res = await PROVIDER_REGISTRY["ror"].verify("researcher", {"institution": institution})
        ror_data = ror_res.get("data", {})
        checks.append({
            "check": "institution_in_ror", "passed": ror_res["found"],
            "confidence": ror_res["confidence"], "data": ror_data,
            "issue": "" if ror_res["found"] else "Institution not found in ROR",
        })
        if ror_res["found"]:
            score += 20
    else:
        checks.append({"check": "institution_present", "passed": False, "confidence": 0, "data": {}, "issue": "No institution in profile"})

    # 3. Email domain academic check
    email = u.get("email", "")
    domain = email.split("@")[1].lower() if "@" in email else ""
    if domain:
        is_academic = any(tld in f".{domain}" for tld in _ACADEMIC_TLDS)
        checks.append({
            "check": "academic_email_domain",
            "passed": is_academic,
            "confidence": 70 if is_academic else 30,
            "data": {"domain": domain, "is_academic": is_academic},
            "issue": "" if is_academic else "Non-academic email domain",
        })
        if is_academic:
            score += 15

        # 3b. Email domain ↔ institution consistency (simple heuristic)
        if domain and institution and ror_data.get("name"):
            ror_name_lower = ror_data["name"].lower()
            domain_parts = domain.replace(".edu", "").replace(".ac.uk", "").split(".")
            domain_hint = domain_parts[-2] if len(domain_parts) >= 2 else domain_parts[0]
            consistent = domain_hint in ror_name_lower or any(w in ror_name_lower for w in domain_parts if len(w) > 3)
            checks.append({
                "check": "email_institution_consistent",
                "passed": consistent,
                "confidence": 75 if consistent else 40,
                "data": {"domain": domain, "ror_institution": ror_data["name"]},
                "issue": "" if consistent else "Email domain may not match institution",
            })
            if consistent:
                score += 10

    # 4. Profile completeness
    req = ["full_name", "institution", "department", "academic_position", "research_interests"]
    filled = [f for f in req if u.get(f)]
    completeness = len(filled) / len(req)
    checks.append({
        "check": "profile_completeness",
        "passed": completeness >= 0.6,
        "confidence": int(completeness * 100),
        "data": {"filled": filled, "missing": [f for f in req if not u.get(f)], "ratio": round(completeness, 2)},
        "issue": "" if completeness >= 0.6 else f"Profile incomplete ({len(filled)}/{len(req)} fields)",
    })
    score += int(completeness * 20)

    # 5. ORCID institution cross-check
    if orcid and institution and ror_data and PROVIDER_REGISTRY["orcid"]:
        orcid_res_data = next((c["data"] for c in checks if c["check"] == "orcid_valid" and c.get("passed")), {})
        orcid_inst = orcid_res_data.get("institution", "")
        if orcid_inst and institution:
            inst_sim = _fuzzy_match(orcid_inst, institution)
            checks.append({
                "check": "institution_matches_orcid",
                "passed": inst_sim >= 0.4,
                "confidence": int(inst_sim * 100),
                "data": {"orcid_institution": orcid_inst, "profile_institution": institution},
                "issue": "" if inst_sim >= 0.4 else "Institution differs from ORCID affiliation",
            })
            if inst_sim >= 0.4:
                score += 5

    issues = [c["issue"] for c in checks if not c.get("passed") and c.get("issue")]
    final_score = min(100, score)
    return {"score": final_score, "checks": checks, "issues": issues, "confidence": final_score}
