"""
Pluggable provider architecture for external academic data sources.
New providers: subclass BaseProvider, implement verify(), register in PROVIDER_REGISTRY.
"""
import logging
import httpx

log = logging.getLogger(__name__)
_TIMEOUT = 10.0


class BaseProvider:
    name: str = "base"
    label: str = "Base Provider"

    async def is_available(self) -> bool:
        return True

    async def verify(self, entity_type: str, payload: dict) -> dict:
        raise NotImplementedError

    def _ok(self, data: dict, confidence: int, notes: str = "") -> dict:
        return {"provider": self.name, "found": True, "data": data, "confidence": confidence, "notes": notes}

    def _fail(self, notes: str, data: dict | None = None) -> dict:
        return {"provider": self.name, "found": False, "data": data or {}, "confidence": 0, "notes": notes}


# ── ORCID ────────────────────────────────────────────────────────────────────

class OrcidProvider(BaseProvider):
    name = "orcid"
    label = "ORCID"

    async def verify(self, entity_type: str, payload: dict) -> dict:
        orcid = payload.get("orcid", "").strip()
        if not orcid:
            return self._fail("No ORCID provided")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                r = await c.get(
                    f"https://pub.orcid.org/v3.0/{orcid}/record",
                    headers={"Accept": "application/json"},
                )
            if r.status_code != 200:
                return self._fail(f"ORCID API {r.status_code}")
            body = r.json()
            person = body.get("person", {})
            nm = person.get("name") or {}
            given  = (nm.get("given-names")  or {}).get("value", "")
            family = (nm.get("family-name")   or {}).get("value", "")
            works_groups = (body.get("activities-summary", {})
                            .get("works", {}).get("group", []))
            works_count = len(works_groups)
            affil_groups = (body.get("activities-summary", {})
                            .get("employments", {}).get("affiliation-group", []))
            institution = ""
            if affil_groups:
                try:
                    institution = (affil_groups[0]
                                   .get("summaries", [{}])[0]
                                   .get("employment-summary", {})
                                   .get("organization", {}).get("name", ""))
                except (IndexError, KeyError):
                    pass
            return self._ok({
                "orcid": orcid,
                "given_name": given, "family_name": family,
                "full_name": f"{given} {family}".strip(),
                "works_count": works_count, "institution": institution,
            }, min(95, 60 + works_count), "ORCID profile verified")
        except Exception as exc:
            log.warning("ORCID provider: %s", exc)
            return self._fail(str(exc))


# ── Crossref ─────────────────────────────────────────────────────────────────

class CrossrefProvider(BaseProvider):
    name = "crossref"
    label = "Crossref"

    async def verify(self, entity_type: str, payload: dict) -> dict:
        doi = payload.get("doi", "").strip().removeprefix("https://doi.org/").removeprefix("http://dx.doi.org/")
        if not doi:
            return self._fail("No DOI provided")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                r = await c.get(
                    f"https://api.crossref.org/works/{doi}",
                    headers={"User-Agent": "Synaptiq/1.0 (mailto:info@synaptiq.io)"},
                )
            if r.status_code == 404:
                return self._fail("DOI not found in Crossref")
            if r.status_code != 200:
                return self._fail(f"Crossref {r.status_code}")
            work = r.json().get("message", {})
            authors = [
                {"given": a.get("given", ""), "family": a.get("family", ""), "orcid": a.get("ORCID", "")}
                for a in work.get("author", [])
            ]
            pub_date = None
            for field in ("published", "published-print", "published-online", "issued"):
                parts = work.get(field, {}).get("date-parts", [[]])
                if parts and parts[0]:
                    pub_date = "-".join(str(p) for p in parts[0]); break
            return self._ok({
                "doi": doi,
                "title": (work.get("title") or [""])[0],
                "journal": (work.get("container-title") or [""])[0],
                "publisher": work.get("publisher", ""),
                "pub_date": pub_date,
                "type": work.get("type", ""),
                "citations_count": work.get("is-referenced-by-count", 0),
                "authors": authors,
            }, 90, "DOI verified via Crossref")
        except Exception as exc:
            log.warning("Crossref provider: %s", exc)
            return self._fail(str(exc))


# ── OpenAlex ─────────────────────────────────────────────────────────────────

class OpenAlexProvider(BaseProvider):
    name = "openalex"
    label = "OpenAlex"

    async def verify(self, entity_type: str, payload: dict) -> dict:
        doi = payload.get("doi", "").strip()
        if doi:
            return await self._by_doi(doi)
        author_id = payload.get("openalex_id", "").strip()
        if author_id:
            return await self._by_author(author_id)
        return self._fail("No doi or openalex_id provided")

    async def _by_doi(self, doi: str) -> dict:
        doi_clean = doi.removeprefix("https://doi.org/").removeprefix("http://dx.doi.org/")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                r = await c.get(
                    "https://api.openalex.org/works",
                    params={"filter": f"doi:{doi_clean}",
                            "select": "id,title,authorships,publication_date,is_retracted,cited_by_count,primary_location"},
                    headers={"User-Agent": "Synaptiq/1.0"},
                )
            if r.status_code != 200:
                return self._fail(f"OpenAlex {r.status_code}")
            results = r.json().get("results", [])
            if not results:
                return self._fail("DOI not in OpenAlex")
            work = results[0]
            retracted = work.get("is_retracted", False)
            authors = [
                {"name": a.get("author", {}).get("display_name", ""),
                 "id":   a.get("author", {}).get("id", "")}
                for a in work.get("authorships", [])
            ]
            return self._ok({
                "doi": doi_clean, "title": work.get("title", ""),
                "publication_date": work.get("publication_date"),
                "is_retracted": retracted,
                "cited_by_count": work.get("cited_by_count", 0),
                "authorships": authors,
                "source": ((work.get("primary_location") or {})
                           .get("source") or {}).get("display_name", ""),
            }, 85, "OpenAlex verified" + (" — RETRACTED" if retracted else ""))
        except Exception as exc:
            return self._fail(str(exc))

    async def _by_author(self, author_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                r = await c.get(
                    f"https://api.openalex.org/authors/{author_id}",
                    headers={"User-Agent": "Synaptiq/1.0"},
                )
            if r.status_code != 200:
                return self._fail(f"OpenAlex author {r.status_code}")
            data = r.json()
            return self._ok({
                "id": author_id,
                "name": data.get("display_name", ""),
                "works_count": data.get("works_count", 0),
                "cited_by_count": data.get("cited_by_count", 0),
                "affiliations": [a.get("institution", {}).get("display_name", "")
                                 for a in data.get("affiliations", [])],
            }, 80, "OpenAlex author found")
        except Exception as exc:
            return self._fail(str(exc))


# ── ROR ──────────────────────────────────────────────────────────────────────

class RorProvider(BaseProvider):
    name = "ror"
    label = "ROR (Research Organization Registry)"

    async def verify(self, entity_type: str, payload: dict) -> dict:
        institution = payload.get("institution", "").strip()
        if not institution:
            return self._fail("No institution name provided")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                r = await c.get(
                    "https://api.ror.org/organizations",
                    params={"query": institution},
                    headers={"Accept": "application/json"},
                )
            if r.status_code != 200:
                return self._fail(f"ROR {r.status_code}")
            items = r.json().get("items", [])
            if not items:
                return self._fail("Institution not in ROR")
            top = items[0]
            match_score = top.get("score", 0)
            confidence = min(90, int(match_score * 18))
            return self._ok({
                "ror_id": top.get("id", ""),
                "name": top.get("name", ""),
                "types": top.get("types", []),
                "country": (top.get("country") or {}).get("country_name", ""),
                "match_score": match_score,
            }, confidence, f"ROR match score {match_score:.1f}/5")
        except Exception as exc:
            log.warning("ROR provider: %s", exc)
            return self._fail(str(exc))


# ── DOI Resolver ─────────────────────────────────────────────────────────────

class DoiProvider(BaseProvider):
    name = "doi"
    label = "DOI Resolver"

    async def verify(self, entity_type: str, payload: dict) -> dict:
        doi = payload.get("doi", "").strip().removeprefix("https://doi.org/").removeprefix("http://dx.doi.org/")
        if not doi:
            return self._fail("No DOI provided")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as c:
                r = await c.head(f"https://doi.org/{doi}")
            if r.status_code < 400:
                return self._ok({
                    "doi": doi,
                    "resolved_url": str(r.url),
                    "status_code": r.status_code,
                }, 80, "DOI resolves successfully")
            return self._fail(f"DOI resolution failed: {r.status_code}")
        except Exception as exc:
            return self._fail(str(exc))


# ── DataCite ─────────────────────────────────────────────────────────────────

class DataCiteProvider(BaseProvider):
    name = "datacite"
    label = "DataCite"

    async def verify(self, entity_type: str, payload: dict) -> dict:
        doi = payload.get("doi", "").strip().removeprefix("https://doi.org/").removeprefix("http://dx.doi.org/")
        if not doi:
            return self._fail("No DOI provided")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                r = await c.get(
                    f"https://api.datacite.org/dois/{doi}",
                    headers={"Accept": "application/vnd.api+json"},
                )
            if r.status_code == 404:
                return self._fail("DOI not in DataCite")
            if r.status_code != 200:
                return self._fail(f"DataCite {r.status_code}")
            attrs = r.json().get("data", {}).get("attributes", {})
            return self._ok({
                "doi": doi,
                "title": ((attrs.get("titles") or [{}])[0]).get("title", ""),
                "resource_type": (attrs.get("types") or {}).get("resourceTypeGeneral", ""),
                "publisher": attrs.get("publisher", ""),
                "pub_year": attrs.get("publicationYear"),
                "creators": [c.get("name", "") for c in attrs.get("creators", [])],
            }, 85, "Found in DataCite")
        except Exception as exc:
            return self._fail(str(exc))


# ── Semantic Scholar ──────────────────────────────────────────────────────────

class SemanticScholarProvider(BaseProvider):
    name = "semantic_scholar"
    label = "Semantic Scholar"

    async def verify(self, entity_type: str, payload: dict) -> dict:
        doi = payload.get("doi", "").strip().removeprefix("https://doi.org/").removeprefix("http://dx.doi.org/")
        if not doi:
            return self._fail("No DOI provided")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                r = await c.get(
                    f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                    params={"fields": "title,authors,year,citationCount,isOpenAccess,publicationTypes"},
                )
            if r.status_code == 404:
                return self._fail("Paper not in Semantic Scholar")
            if r.status_code != 200:
                return self._fail(f"Semantic Scholar {r.status_code}")
            data = r.json()
            return self._ok({
                "title": data.get("title", ""),
                "year": data.get("year"),
                "citation_count": data.get("citationCount", 0),
                "is_open_access": data.get("isOpenAccess", False),
                "authors": [a.get("name", "") for a in data.get("authors", [])],
                "types": data.get("publicationTypes", []),
            }, 78, "Found in Semantic Scholar")
        except Exception as exc:
            return self._fail(str(exc))


# ── Registry ─────────────────────────────────────────────────────────────────

PROVIDER_REGISTRY: dict[str, BaseProvider] = {
    "orcid":            OrcidProvider(),
    "crossref":         CrossrefProvider(),
    "openalex":         OpenAlexProvider(),
    "ror":              RorProvider(),
    "doi":              DoiProvider(),
    "datacite":         DataCiteProvider(),
    "semantic_scholar": SemanticScholarProvider(),
}


async def get_all_provider_status() -> list[dict]:
    status = []
    for key, prov in PROVIDER_REGISTRY.items():
        try:
            avail = await prov.is_available()
        except Exception:
            avail = False
        status.append({"name": key, "label": prov.label, "available": avail})
    return status


def get_provider(name: str) -> BaseProvider | None:
    return PROVIDER_REGISTRY.get(name)
