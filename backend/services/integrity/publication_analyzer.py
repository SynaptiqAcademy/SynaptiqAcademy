import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from services.integrity.providers import PROVIDER_REGISTRY


async def _verify_one_pub(pub: dict) -> dict:
    """Run Crossref + OpenAlex + DOI resolver in parallel for a single publication."""
    doi = (pub.get("doi") or "").strip()
    pub_id = str(pub.get("_id", ""))
    title = pub.get("title", "Unknown")

    if not doi:
        return {
            "pub_id": pub_id, "title": title, "doi": None,
            "status": "no_doi", "confidence": 30,
            "issues": ["No DOI — metadata cannot be externally verified"],
            "providers": {},
        }

    crossref, openalex, doi_res = await asyncio.gather(
        PROVIDER_REGISTRY["crossref"].verify("publication", {"doi": doi}),
        PROVIDER_REGISTRY["openalex"].verify("publication", {"doi": doi}),
        PROVIDER_REGISTRY["doi"].verify("publication", {"doi": doi}),
    )

    providers = {
        "crossref": crossref,
        "openalex": openalex,
        "doi_resolver": doi_res,
    }

    issues: list[str] = []
    confidence = 0
    verified_by = []

    if crossref["found"]:
        verified_by.append("crossref")
        confidence = max(confidence, crossref["confidence"])
        # Author name consistency check (basic)
        crossref_title = crossref["data"].get("title", "").lower()
        local_title = title.lower()
        if crossref_title and local_title:
            title_words_local = set(local_title.split())
            title_words_xr = set(crossref_title.split())
            overlap = len(title_words_local & title_words_xr)
            total = len(title_words_local | title_words_xr)
            if total > 0 and overlap / total < 0.4:
                issues.append("Title diverges from Crossref record")
    else:
        issues.append("DOI not found in Crossref")

    if openalex["found"]:
        verified_by.append("openalex")
        confidence = max(confidence, openalex["confidence"])
        if openalex["data"].get("is_retracted"):
            issues.append("RETRACTED — flagged in OpenAlex")
            confidence = min(confidence, 10)
    else:
        if crossref["found"]:
            pass  # Crossref is authoritative for DOIs; OpenAlex absence is minor
        else:
            issues.append("DOI not found in OpenAlex")

    if doi_res["found"]:
        verified_by.append("doi_resolver")

    if not doi_res["found"] and not crossref["found"]:
        issues.append("DOI does not resolve — may be invalid")
        confidence = max(0, confidence - 30)

    status = "verified" if len(verified_by) >= 2 else ("partial" if verified_by else "failed")
    return {
        "pub_id": pub_id, "title": title, "doi": doi,
        "status": status, "confidence": confidence,
        "verified_by": verified_by, "issues": issues,
        "providers": {k: {"found": v["found"], "confidence": v["confidence"], "notes": v["notes"]}
                      for k, v in providers.items()},
        "crossref_data": crossref.get("data"),
        "openalex_data": openalex.get("data"),
    }


async def analyze_publications(user_id: str, db) -> dict:
    pubs = await db.publications.find({"user_id": user_id}).to_list(length=50)
    if not pubs:
        return {
            "total": 0, "verified": 0, "partial": 0, "failed": 0, "no_doi": 0,
            "score": 50, "checks": [], "issues": [],
            "retracted_count": 0, "duplicate_dois": [],
        }

    # Check for duplicate DOIs within user's records
    doi_counts: dict = {}
    for p in pubs:
        doi = (p.get("doi") or "").strip()
        if doi:
            doi_counts[doi] = doi_counts.get(doi, 0) + 1
    duplicate_dois = [doi for doi, cnt in doi_counts.items() if cnt > 1]

    # Verify up to 10 pubs with DOIs (to keep latency reasonable)
    doi_pubs = [p for p in pubs if p.get("doi")][:10]
    no_doi_pubs = [p for p in pubs if not p.get("doi")]

    checks = await asyncio.gather(*[_verify_one_pub(p) for p in doi_pubs])
    checks = list(checks)

    # Add no-doi entries without external verification
    for p in no_doi_pubs[:5]:
        checks.append({
            "pub_id": str(p.get("_id", "")),
            "title": p.get("title", "Unknown"),
            "doi": None, "status": "no_doi", "confidence": 30,
            "issues": ["No DOI — cannot externally verify"], "providers": {},
        })

    verified_count  = sum(1 for c in checks if c["status"] == "verified")
    partial_count   = sum(1 for c in checks if c["status"] == "partial")
    failed_count    = sum(1 for c in checks if c["status"] == "failed")
    no_doi_count    = sum(1 for c in checks if c["status"] == "no_doi")
    retracted_count = sum(
        1 for c in checks
        if any("RETRACTED" in i for i in c.get("issues", []))
    )

    # Score: base on verification ratio
    verifiable = verified_count + partial_count + failed_count
    if verifiable > 0:
        verify_ratio = (verified_count + partial_count * 0.5) / verifiable
    else:
        verify_ratio = 0.5
    base_score = int(verify_ratio * 80)
    if retracted_count > 0:
        base_score = max(0, base_score - retracted_count * 20)
    if duplicate_dois:
        base_score = max(0, base_score - len(duplicate_dois) * 15)
    score = min(100, base_score + (10 if not no_doi_pubs else 0))

    all_issues = list({i for c in checks for i in c.get("issues", [])})
    if duplicate_dois:
        all_issues.append(f"Duplicate DOIs found: {', '.join(duplicate_dois[:3])}")

    return {
        "total": len(pubs),
        "verified": verified_count, "partial": partial_count,
        "failed": failed_count, "no_doi": no_doi_count,
        "score": score, "checks": checks, "issues": all_issues,
        "retracted_count": retracted_count, "duplicate_dois": duplicate_dois,
    }
