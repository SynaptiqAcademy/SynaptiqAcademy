import asyncio
from bson import ObjectId
from services.integrity.providers import PROVIDER_REGISTRY


_KNOWN_FUNDERS = {
    "nsf", "nih", "erc", "horizon", "wellcome", "gates", "nwo", "dfg",
    "ahrc", "esrc", "epsrc", "bbsrc", "mrc", "arc", "nserc", "sshrc",
    "national science foundation", "national institutes of health",
    "european research council", "wellcome trust", "bill & melinda gates",
    "bill and melinda gates",
}


def _funder_known(funder: str) -> bool:
    fl = funder.lower()
    return any(k in fl for k in _KNOWN_FUNDERS)


async def analyze_grants(user_id: str, db) -> dict:
    grants = await db.grant_applications.find({"user_id": user_id}).to_list(length=50)
    if not grants:
        return {
            "total": 0, "complete": 0, "partial": 0, "score": 50,
            "checks": [], "issues": [], "funder_recognized": 0,
        }

    checks: list[dict] = []
    issues: list[str] = []
    complete_count = 0
    partial_count = 0
    funder_recognized = 0
    grant_results = []

    _REQUIRED_FIELDS = ["title", "funder", "amount", "status", "start_date"]

    # Try to get user institution for cross-check
    user_institution = ""
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user_institution = (user.get("institution") or "").strip()
    except Exception:
        pass

    for g in grants[:20]:
        g_id = str(g.get("_id", ""))
        title = g.get("title", "Untitled")
        funder = (g.get("funder") or g.get("funding_body") or "").strip()
        amount = g.get("amount") or g.get("budget") or 0
        status = g.get("status", "unknown")
        institution = (g.get("institution") or g.get("host_institution") or "").strip()

        g_issues: list[str] = []
        filled = [f for f in _REQUIRED_FIELDS if g.get(f)]
        completeness = len(filled) / len(_REQUIRED_FIELDS)

        if completeness >= 0.8:
            complete_count += 1
        elif completeness >= 0.4:
            partial_count += 1

        # Funder recognition
        funder_ok = _funder_known(funder) if funder else False
        if funder_ok:
            funder_recognized += 1
        elif funder:
            g_issues.append(f"Funder '{funder}' not in recognized list")

        # Institution consistency
        inst_ok = True
        if institution and user_institution:
            from services.integrity.identity_analyzer import _fuzzy_match
            inst_sim = _fuzzy_match(institution, user_institution)
            inst_ok = inst_sim >= 0.3
            if not inst_ok:
                g_issues.append("Grant institution may not match profile institution")

        # Amount sanity
        try:
            amount_num = float(amount) if amount else 0
        except (ValueError, TypeError):
            amount_num = 0
        if amount_num < 0:
            g_issues.append("Negative grant amount recorded")

        grant_results.append({
            "grant_id": g_id, "title": title, "funder": funder,
            "amount": amount, "status": status,
            "completeness": round(completeness, 2),
            "funder_recognized": funder_ok, "issues": g_issues,
        })
        issues.extend(g_issues)

    # Dedup issues
    issues = list(dict.fromkeys(issues))

    # Overall checks
    total = len(grants)
    checks.append({
        "check": "grant_completeness",
        "passed": complete_count / max(total, 1) >= 0.6,
        "confidence": 75,
        "data": {"complete": complete_count, "partial": partial_count, "total": total},
        "issue": "" if complete_count / max(total, 1) >= 0.6 else "Many grants have incomplete metadata",
    })
    checks.append({
        "check": "funder_recognition",
        "passed": funder_recognized / max(total, 1) >= 0.5,
        "confidence": 65,
        "data": {"recognized": funder_recognized, "total": total},
        "issue": "" if funder_recognized / max(total, 1) >= 0.5 else "Many funders not in recognized registry",
    })

    # Score
    completeness_ratio = complete_count / max(total, 1)
    funder_ratio = funder_recognized / max(total, 1)
    score = int((completeness_ratio * 50) + (funder_ratio * 30) + 20)
    score = max(0, min(100, score))

    return {
        "total": total,
        "complete": complete_count,
        "partial": partial_count,
        "funder_recognized": funder_recognized,
        "score": score, "checks": checks,
        "issues": [c.get("issue") for c in checks if not c.get("passed") and c.get("issue")] + issues,
        "grant_results": grant_results,
    }
