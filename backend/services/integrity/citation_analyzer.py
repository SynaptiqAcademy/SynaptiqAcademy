import asyncio
from datetime import datetime, timezone
from services.integrity.providers import PROVIDER_REGISTRY


async def analyze_citations(user_id: str, db) -> dict:
    pubs = await db.publications.find({"user_id": user_id}).to_list(length=50)
    if not pubs:
        return {
            "total_citations": 0, "average_per_pub": 0.0,
            "self_citation_ratio": 0.0, "score": 50,
            "checks": [], "issues": [], "velocity": "stable",
        }

    doi_pubs = [p for p in pubs if p.get("doi")][:10]
    all_author_orcids: set[str] = set()
    user = None
    try:
        from bson import ObjectId
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = await db.users.find_one({"_id": user_id})
    if user and user.get("orcid"):
        all_author_orcids.add(user["orcid"].strip())

    pub_results = []
    total_citations = 0
    self_citations = 0

    async def _check_pub(pub: dict) -> dict:
        doi = pub.get("doi", "").strip()
        xr, ss = await asyncio.gather(
            PROVIDER_REGISTRY["crossref"].verify("publication", {"doi": doi}),
            PROVIDER_REGISTRY["semantic_scholar"].verify("publication", {"doi": doi}),
        )
        xr_count = xr["data"].get("citations_count", 0) if xr["found"] else None
        ss_count = ss["data"].get("citation_count", 0) if ss["found"] else None

        if xr_count is not None and ss_count is not None:
            citation_count = (xr_count + ss_count) // 2
        elif xr_count is not None:
            citation_count = xr_count
        elif ss_count is not None:
            citation_count = ss_count
        else:
            citation_count = 0

        # Self-citation detection: look for citing works where author orcid matches
        self_cite_count = 0
        if xr["found"]:
            xr_authors = xr["data"].get("authors", [])
            for a in xr_authors:
                a_orcid = (a.get("orcid") or "").replace("https://orcid.org/", "").strip()
                if a_orcid and a_orcid in all_author_orcids:
                    self_cite_count += 1

        return {
            "doi": doi,
            "title": pub.get("title", "Unknown"),
            "citation_count": citation_count,
            "crossref_count": xr_count,
            "semantic_scholar_count": ss_count,
            "self_cite_indicators": self_cite_count,
        }

    if doi_pubs:
        pub_results = list(await asyncio.gather(*[_check_pub(p) for p in doi_pubs]))

    for pr in pub_results:
        total_citations += pr["citation_count"]
        self_citations += pr.get("self_cite_indicators", 0)

    avg = total_citations / len(pub_results) if pub_results else 0.0
    self_ratio = self_citations / max(total_citations, 1) if total_citations > 0 else 0.0

    # Citation velocity: compare earliest vs latest pubs by year
    velocity = "stable"
    years = []
    for p in pubs:
        yr = p.get("year") or p.get("publication_year")
        if yr:
            try:
                years.append(int(yr))
            except (ValueError, TypeError):
                pass
    if years:
        year_range = max(years) - min(years)
        if year_range > 0 and total_citations > 0:
            recent_pubs = [p for p in pubs if (p.get("year") or 0) >= max(years) - 2]
            recent_count = len(recent_pubs)
            rate = total_citations / year_range
            if rate > 5 and recent_count > len(pubs) * 0.4:
                velocity = "accelerating"
            elif rate < 1 and len(pubs) > 5:
                velocity = "declining"

    checks: list[dict] = []
    issues: list[str] = []

    checks.append({
        "check": "citation_data_available",
        "passed": len(pub_results) > 0,
        "confidence": 80 if pub_results else 0,
        "data": {"verified_pubs": len(pub_results), "total_pubs": len(pubs)},
    })

    if self_ratio > 0.3:
        issues.append(f"High self-citation indicator ratio ({self_ratio:.0%})")
        checks.append({"check": "self_citation_ratio", "passed": False, "confidence": 60,
                       "data": {"ratio": round(self_ratio, 3)},
                       "issue": f"Self-citation ratio {self_ratio:.0%} is elevated"})
    else:
        checks.append({"check": "self_citation_ratio", "passed": True, "confidence": 70,
                       "data": {"ratio": round(self_ratio, 3)}})

    # Score
    if len(pub_results) == 0:
        score = 40
    else:
        base = min(80, 40 + int(avg * 5))
        if self_ratio > 0.3:
            base -= 20
        if velocity == "accelerating":
            base += 10
        score = max(0, min(100, base))

    return {
        "total_citations": total_citations,
        "average_per_pub": round(avg, 2),
        "self_citation_ratio": round(self_ratio, 3),
        "velocity": velocity,
        "pub_results": pub_results,
        "score": score, "checks": checks, "issues": issues,
    }
