"""Regression tests for the Academic Research Record (Phase 1 consolidation).

Uses a private Motor client (see test_phase1_safety_fixes.py's _RawDB
pattern) rather than the cached global db.py client, and mocks the
Crossref/OpenAlex HTTP calls so these tests never hit the real network.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId

from services.research_record.doi_normalize import normalize_doi, is_valid_doi
from services.research_record.dedup import find_by_doi, find_candidate_by_title, NON_DOI_AUTO_MERGE_THRESHOLD
from services.research_record.authors import (
    link_user_to_publication, is_user_linked, get_publication_ids_for_user,
    resolve_author_identities, link_confidently_resolved_authors,
)
from services.research_record.manuscript_link import publish_manuscript_to_research_record
from services.research_record.migration import ensure_publications_backward_compat


def _oid() -> str:
    return str(ObjectId())


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


# ── DOI normalization ────────────────────────────────────────────────────

class TestDoiNormalization:
    def test_bare_doi(self):
        assert normalize_doi("10.1038/nature12345") == "10.1038/nature12345"

    def test_https_prefix_stripped(self):
        assert normalize_doi("https://doi.org/10.1038/Nature12345") == "10.1038/nature12345"

    def test_http_prefix_stripped(self):
        assert normalize_doi("http://dx.doi.org/10.1038/nature12345") == "10.1038/nature12345"

    def test_doi_colon_prefix_stripped(self):
        assert normalize_doi("doi:10.1038/nature12345") == "10.1038/nature12345"

    def test_whitespace_stripped(self):
        assert normalize_doi("  10.1038/nature12345  ") == "10.1038/nature12345"

    def test_invalid_doi_returns_none(self):
        assert normalize_doi("not-a-doi") is None
        assert normalize_doi("") is None
        assert normalize_doi("10.abc/xyz") is None

    def test_is_valid_doi(self):
        assert is_valid_doi("10.1038/nature12345") is True
        assert is_valid_doi("garbage") is False


# ── DOI lookup / merge (mocked providers, no network) ───────────────────────

class TestDoiLookupMerge:
    @pytest.mark.asyncio
    async def test_merges_crossref_and_openalex(self):
        from services.research_record.doi_lookup import lookup_doi

        crossref_ok = {
            "found": True,
            "data": {
                "doi": "10.1038/nature12345", "title": "A Real Paper",
                "journal": "Nature", "publisher": "Springer Nature",
                "pub_date": "2021-03-15", "type": "journal-article",
                "citations_count": 10,
                "authors": [{"given": "Ada", "family": "Lovelace", "orcid": "0000-0001-2345-6789"}],
            },
        }
        openalex_ok = {
            "found": True,
            "data": {
                "doi": "10.1038/nature12345", "title": "A Real Paper",
                "publication_date": "2021-03-15", "is_retracted": False,
                "cited_by_count": 12, "authorships": [{"name": "Ada Lovelace", "id": "A123"}],
                "source": "Nature",
            },
        }
        with patch("services.research_record.doi_lookup.CrossrefProvider") as MockCR, \
             patch("services.research_record.doi_lookup.OpenAlexProvider") as MockOA:
            MockCR.return_value.verify = AsyncMock(return_value=crossref_ok)
            MockOA.return_value.verify = AsyncMock(return_value=openalex_ok)
            result = await lookup_doi("10.1038/NATURE12345")

        assert result["doi"] == "10.1038/nature12345"
        assert result["found"] is True
        assert result["title"] == "A Real Paper"
        assert result["publisher"] == "Springer Nature"  # only Crossref has this
        assert result["year"] == 2021
        assert result["citations_count"] == 12  # max of the two sources
        assert set(result["sources_used"]) == {"crossref", "openalex"}
        assert result["authors"][0]["orcid_id"] == "0000-0001-2345-6789"

    @pytest.mark.asyncio
    async def test_not_found_never_fabricates(self):
        from services.research_record.doi_lookup import lookup_doi
        with patch("services.research_record.doi_lookup.CrossrefProvider") as MockCR, \
             patch("services.research_record.doi_lookup.OpenAlexProvider") as MockOA:
            MockCR.return_value.verify = AsyncMock(return_value={"found": False, "data": {}})
            MockOA.return_value.verify = AsyncMock(return_value={"found": False, "data": {}})
            result = await lookup_doi("10.9999/nonexistent")
        assert result["found"] is False
        assert result["title"] == ""
        assert result["sources_used"] == []

    @pytest.mark.asyncio
    async def test_invalid_doi_raises(self):
        from services.research_record.doi_lookup import lookup_doi
        with pytest.raises(ValueError):
            await lookup_doi("not-a-doi")


# ── DOI-based dedup / global identity ───────────────────────────────────────

class TestDoiDedup:
    @pytest.mark.asyncio
    async def test_find_by_doi_is_global_not_owner_scoped(self):
        raw = _RawDB()
        try:
            doi = f"10.1234/{_oid()[:12]}"
            owner_a = _oid()
            await raw.db.publications.insert_one({"owner_id": owner_a, "doi": doi, "title": "X"})
            # A DIFFERENT user's lookup by the same DOI must find the SAME doc —
            # this is the CRITICAL rule: publication identity is global, not
            # scoped to whoever happens to own/have-imported it.
            found = await find_by_doi(raw.db, doi)
            assert found is not None
            assert found["owner_id"] == owner_a
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_find_by_doi_none_when_absent(self):
        raw = _RawDB()
        try:
            found = await find_by_doi(raw.db, f"10.0000/{_oid()}")
            assert found is None
        finally:
            raw.close()


# ── Non-DOI confidence-based matching ───────────────────────────────────────

class TestNonDoiDedup:
    @pytest.mark.asyncio
    async def test_title_only_match_is_below_auto_merge_threshold(self):
        raw = _RawDB()
        try:
            title = f"Ambiguous Title {_oid()[:8]}"
            await raw.db.publications.insert_one({
                "title": title, "title_norm": title.lower(), "year": 2019,
                "authors": [{"display_name": "Someone Else"}],
            })
            result = await find_candidate_by_title(raw.db, title, authors=[], year=None)
            assert result is not None
            # Title match alone, no year/author corroboration — must NOT
            # clear the auto-merge bar (Step 8: no silent title-only merge).
            assert result["confidence"] < NON_DOI_AUTO_MERGE_THRESHOLD
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_title_plus_year_plus_author_overlap_raises_confidence(self):
        raw = _RawDB()
        try:
            title = f"Well Corroborated Title {_oid()[:8]}"
            await raw.db.publications.insert_one({
                "title": title, "title_norm": title.lower(), "year": 2022,
                "authors": [{"display_name": "Jane Researcher"}],
            })
            weak = await find_candidate_by_title(raw.db, title, authors=[], year=None)
            strong = await find_candidate_by_title(
                raw.db, title, authors=[{"display_name": "Jane Researcher"}], year=2022)
            assert strong["confidence"] > weak["confidence"]
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_no_candidate_returns_none(self):
        raw = _RawDB()
        try:
            result = await find_candidate_by_title(raw.db, f"Nonexistent {_oid()}")
            assert result is None
        finally:
            raw.close()


# ── Authorship relationship (multi-user, one publication) ──────────────────

class TestAuthorshipRelationship:
    @pytest.mark.asyncio
    async def test_multiple_synaptiq_users_share_one_publication(self):
        raw = _RawDB()
        try:
            pub_id = _oid()
            user_a, user_b = _oid(), _oid()
            await link_user_to_publication(raw.db, pub_id, user_a, role="author", source="manual")
            await link_user_to_publication(raw.db, pub_id, user_b, role="author", source="manual")

            assert await is_user_linked(raw.db, pub_id, user_a)
            assert await is_user_linked(raw.db, pub_id, user_b)
            # No duplicate publication was created for the second user —
            # both reference the SAME pub_id.
            assert pub_id in await get_publication_ids_for_user(raw.db, user_a)
            assert pub_id in await get_publication_ids_for_user(raw.db, user_b)
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_linking_twice_is_idempotent(self):
        raw = _RawDB()
        try:
            pub_id, uid = _oid(), _oid()
            await link_user_to_publication(raw.db, pub_id, uid, role="author", source="manual")
            await link_user_to_publication(raw.db, pub_id, uid, role="owner", source="orcid")
            count = await raw.db.publication_authors.count_documents(
                {"publication_id": pub_id, "synaptiq_user_id": uid})
            assert count == 1
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_external_author_with_no_orcid_stays_external(self):
        raw = _RawDB()
        try:
            resolved = await resolve_author_identities(
                raw.db, [{"display_name": "Some External Author", "orcid_id": None}])
            assert resolved[0]["is_external"] is True
            assert resolved[0]["synaptiq_user_id"] is None
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_confident_orcid_match_links_author(self):
        raw = _RawDB()
        try:
            orcid_id = f"0000-0001-{_oid()[:4]}-{_oid()[:4]}"
            await raw.db.users.delete_many({"orcid.orcid_id": orcid_id})
            matched_uid = (await raw.db.users.insert_one(
                {"full_name": "Real User", "orcid": {"orcid_id": orcid_id},
                 "email": f"realuser-{_oid()}@synaptiq-test.io"})).inserted_id
            resolved = await resolve_author_identities(
                raw.db, [{"display_name": "Real User", "orcid_id": orcid_id}])
            assert resolved[0]["is_external"] is False
            assert resolved[0]["synaptiq_user_id"] == str(matched_uid)
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_no_fuzzy_name_matching_without_orcid(self):
        raw = _RawDB()
        try:
            # A Synaptiq user exists with this exact name, but the author
            # entry carries no ORCID id — must NOT be auto-linked by name.
            await raw.db.users.insert_one({
                "full_name": "Ambiguous Name Match",
                "email": f"ambiguous-{_oid()}@synaptiq-test.io",
            })
            resolved = await resolve_author_identities(
                raw.db, [{"display_name": "Ambiguous Name Match", "orcid_id": None}])
            assert resolved[0]["is_external"] is True
            assert resolved[0]["synaptiq_user_id"] is None
        finally:
            raw.close()


# ── Manuscript -> Research Record explicit publish action ──────────────────

class TestManuscriptPublish:
    @pytest.mark.asyncio
    async def test_manuscript_untouched_until_explicit_publish(self):
        raw = _RawDB()
        try:
            m_id = (await raw.db.manuscripts.insert_one({
                "title": "Draft Paper", "status": "published",  # status alone must NOT trigger promotion
                "manuscript_type": "Journal Article", "authors": [_oid()],
                "lead_author_id": _oid(),
            })).inserted_id
            assert await raw.db.publications.count_documents({"synaptiq_work_ref.id": str(m_id)}) == 0
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_explicit_publish_creates_research_record(self):
        raw = _RawDB()
        try:
            lead = _oid()
            m_id = (await raw.db.manuscripts.insert_one({
                "title": f"Explicit Publish Paper {_oid()[:8]}", "status": "published",
                "manuscript_type": "Journal Article", "authors": [lead],
                "lead_author_id": lead,
            })).inserted_id

            result = await publish_manuscript_to_research_record(raw.db, str(m_id))
            assert result["created"] is True

            pub = await raw.db.publications.find_one({"_id": ObjectId(result["publication_id"])})
            assert pub["origin"] == "synaptiq"
            assert pub["verification_status"] == "synaptiq_published"
            assert pub["synaptiq_work_ref"] == {"collection": "manuscripts", "id": str(m_id)}
            assert await is_user_linked(raw.db, result["publication_id"], lead)

            updated_manuscript = await raw.db.manuscripts.find_one({"_id": m_id})
            assert updated_manuscript["research_record_id"] == result["publication_id"]
            assert updated_manuscript["orcid_publication_id"] == result["publication_id"]  # legacy field kept in sync
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_later_doi_discovery_converges_not_duplicates(self):
        """Simulates Step 11: a manuscript is explicitly published, then a
        DOI is later associated (e.g. an ORCID/Crossref sync discovers it) —
        must enrich the SAME record, not create a second one."""
        raw = _RawDB()
        try:
            lead = _oid()
            m_id = (await raw.db.manuscripts.insert_one({
                "title": f"Convergence Paper {_oid()[:8]}", "status": "published",
                "manuscript_type": "Journal Article", "authors": [lead],
                "lead_author_id": lead,
            })).inserted_id

            first = await publish_manuscript_to_research_record(raw.db, str(m_id))
            doi = f"10.5555/{_oid()[:10]}"
            second = await publish_manuscript_to_research_record(raw.db, str(m_id), doi=doi)

            assert second["publication_id"] == first["publication_id"]
            assert second["created"] is False
            total = await raw.db.publications.count_documents(
                {"synaptiq_work_ref.id": str(m_id)})
            assert total == 1
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_publish_never_flips_origin_of_pre_existing_external_record(self):
        """If a publications doc for this DOI already exists as an external
        (e.g. ORCID-imported) record before the manuscript is published,
        linking onto it must not silently relabel it — Step 11."""
        raw = _RawDB()
        try:
            doi = f"10.7777/{_oid()[:10]}"
            await raw.db.publications.insert_one({
                "doi": doi, "title": "Pre-existing external record",
                "origin": "external", "source": "orcid",
            })
            lead = _oid()
            m_id = (await raw.db.manuscripts.insert_one({
                "title": "Later Synaptiq Manuscript", "status": "published",
                "manuscript_type": "Journal Article", "authors": [lead],
                "lead_author_id": lead,
            })).inserted_id

            result = await publish_manuscript_to_research_record(raw.db, str(m_id), doi=doi)
            pub = await raw.db.publications.find_one({"_id": ObjectId(result["publication_id"])})
            assert pub["origin"] == "external"  # untouched, not flipped to "synaptiq"
            assert pub["synaptiq_work_ref"] == {"collection": "manuscripts", "id": str(m_id)}
        finally:
            raw.close()


# ── Backward-compatible migration ───────────────────────────────────────────

class TestBackwardCompatMigration:
    @pytest.mark.asyncio
    async def test_backfills_user_id_author_ids_and_origin(self):
        raw = _RawDB()
        try:
            owner = _oid()
            doc_id = (await raw.db.publications.insert_one(
                {"owner_id": owner, "title": "Legacy Row"})).inserted_id

            await ensure_publications_backward_compat(raw.db)

            doc = await raw.db.publications.find_one({"_id": doc_id})
            assert doc["user_id"] == owner
            assert doc["author_ids"] == [owner]
            assert doc["origin"] == "external"
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_migration_is_idempotent(self):
        raw = _RawDB()
        try:
            owner = _oid()
            doc_id = (await raw.db.publications.insert_one(
                {"owner_id": owner, "title": "Idempotency Check"})).inserted_id

            r1 = await ensure_publications_backward_compat(raw.db)
            r2 = await ensure_publications_backward_compat(raw.db)
            # Second run should not re-modify the same, already-backfilled doc.
            doc = await raw.db.publications.find_one({"_id": doc_id})
            assert doc["user_id"] == owner
            assert r2["user_id_backfilled"] <= r1["user_id_backfilled"]
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_does_not_touch_existing_source_field(self):
        raw = _RawDB()
        try:
            doc_id = (await raw.db.publications.insert_one(
                {"owner_id": _oid(), "title": "OpenAlex row", "source": "openalex"})).inserted_id
            await ensure_publications_backward_compat(raw.db)
            doc = await raw.db.publications.find_one({"_id": doc_id})
            assert doc["source"] == "openalex"  # untouched
        finally:
            raw.close()
