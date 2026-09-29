"""P1 Phase 8D — Explainable Expert Matching & Research Collaboration
Intelligence.

Covers what's new on top of Phase 8C: the structured Evidence model
(type/candidate_value/need_value/relationship), deterministic contribution
sentences, relevance labels, primary-group placement with no duplicate
cards, the coverage map, batched publication-title evidence (with and
without a match), context (geographic/language) evidence, the new real
backend user controls (country/language/available_for_collaboration/
include_methods/prioritize), security re-audit of the publication path, and
confirmation that editing the Research Need recomputes everything (no
stale-explanation caching exists to invalidate).
"""
from __future__ import annotations

import os

import pytest
from bson import ObjectId

from services.research_need.models import ResearchNeed
from services.research_need.relevance import find_relevant_people
from services.research_need import evidence as ev


def _oid() -> str:
    return str(ObjectId())


class _RawDB:
    def __init__(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self._client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
        self.db = self._client[os.environ["MONGODB_DB_NAME"]]

    def close(self):
        self._client.close()


async def _insert_user(db, full_name: str, **extra) -> str:
    doc = {
        "full_name": full_name,
        "email": f"{full_name.lower().replace(' ', '')}-{_oid()[:8]}@synaptiq-test.io",
        "is_demo": False,
        "profile_visibility": "public",
        **extra,
    }
    res = await db.users.insert_one(doc)
    return str(res.inserted_id)


def _find(result, uid):
    for group in (result["similar"], result["complementary"], result["methods_specialists"], result["context_specialists"]):
        for p in group:
            if p["id"] == uid:
                return p
    return None


class TestEvidenceModel:
    def test_labels_for_direct(self):
        assert ev.labels_for([{"type": "research_area", "candidate_value": "X", "need_value": "X", "relationship": "direct"}]) == ["directly_relevant"]

    def test_labels_for_multiple_types(self):
        e = [
            {"type": "research_area", "candidate_value": "A", "need_value": "A", "relationship": "direct"},
            {"type": "professional_expertise", "candidate_value": "B", "need_value": "B", "relationship": "complementary"},
            {"type": "method", "candidate_value": "C", "need_value": "C", "relationship": "direct"},
        ]
        labels = ev.labels_for(e)
        assert set(labels) == {"directly_relevant", "complementary_expertise", "methods_specialist"}

    def test_primary_group_default_priority(self):
        assert ev.primary_group(["methods_specialist", "directly_relevant"]) == "directly_relevant"

    def test_primary_group_respects_prioritize_override(self):
        assert ev.primary_group(["methods_specialist", "directly_relevant"], prioritize="methods_specialist") == "methods_specialist"

    def test_contributions_are_conservative_no_leadership_claims(self):
        lines = ev.contributions_for([{"type": "research_area", "candidate_value": "Public Health", "need_value": "x", "relationship": "direct"}])
        assert lines
        blob = " ".join(lines).lower()
        for forbidden in ("should lead", "ideal co-author", "best person", "will improve"):
            assert forbidden not in blob

    def test_explanation_no_evidence_says_limited_information(self):
        assert ev.explanation_for([]) == "Limited profile information available to explain this match."

    def test_explanation_never_contains_a_percentage(self):
        e = [{"type": "research_area", "candidate_value": "AI", "need_value": "AI", "relationship": "direct"}]
        text = ev.explanation_for(e)
        assert "%" not in text


class TestDirectComplementaryMethodsContext:
    @pytest.mark.asyncio
    async def test_direct_expertise_grouping(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"D8Direct {suffix}", research_areas=[f"Quality Management {suffix}"])
            need = ResearchNeed(original_query="x", required_expertise=[f"Quality Management {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            person = _find(result, uid)
            assert person is not None
            assert "directly_relevant" in person["relevance_labels"]
            assert person in result["similar"]
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Direct"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_complementary_expertise_grouping_generalizes_non_medical(self):
        """Domain-general check: economics, not healthcare."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"D8Econ {suffix}", professional_expertise=[f"Trade Economics {suffix}"])
            need = ResearchNeed(
                original_query="x",
                required_expertise=["Something Unrelated"],
                complementary_expertise=[f"Trade Economics {suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            person = _find(result, uid)
            assert person in result["complementary"]
            assert "complementary_expertise" in person["relevance_labels"]
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Econ"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_methods_specialist_grouping(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"D8Method {suffix}", methods=[f"Lean Six Sigma {suffix}"])
            need = ResearchNeed(original_query="x", useful_methods=[f"Lean Six Sigma {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            person = _find(result, uid)
            assert person in result["methods_specialists"]
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Method"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_context_specialist_geographic(self):
        # Retrieval only runs against profile fields (see relevance.py's
        # module docstring on this scope limit), so the candidate also needs
        # a real matching research_area to enter the pool; prioritize= is
        # used to force context_specialist as the primary placement so both
        # the context-evidence match AND the prioritize control are proven
        # in one test.
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(
                raw.db, f"D8Context {suffix}",
                country=f"Kenya{suffix}", research_areas=[f"Retrievable {suffix}"],
            )
            need = ResearchNeed(
                original_query="x", required_expertise=[f"Retrievable {suffix}"],
                geographic_context=f"Kenya{suffix}",
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None, prioritize="context_specialist")
            person = _find(result, uid)
            assert person is not None
            assert "context_specialist" in person["relevance_labels"]
            assert person in result["context_specialists"]
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Context"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_context_specialist_language(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(
                raw.db, f"D8Lang {suffix}",
                languages=[f"Swahili{suffix}"], research_areas=[f"Retrievable {suffix}"],
            )
            need = ResearchNeed(
                original_query="x", required_expertise=[f"Retrievable {suffix}"],
                languages=[f"Swahili{suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None, prioritize="context_specialist")
            person = _find(result, uid)
            assert person is not None
            assert "context_specialist" in person["relevance_labels"]
            assert person in result["context_specialists"]
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Lang"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_candidate_in_multiple_categories_gets_one_primary_no_duplicate(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(
                raw.db, f"D8Multi {suffix}",
                research_areas=[f"AI {suffix}"], methods=[f"Deep Learning {suffix}"],
            )
            need = ResearchNeed(original_query="x", required_expertise=[f"AI {suffix}"], useful_methods=[f"Deep Learning {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            appearances = sum(
                1 for group in (result["similar"], result["complementary"], result["methods_specialists"], result["context_specialists"])
                for p in group if p["id"] == uid
            )
            assert appearances == 1  # no duplicate card
            person = _find(result, uid)
            assert set(person["relevance_labels"]) >= {"directly_relevant", "methods_specialist"}
            assert person in result["similar"]  # directly_relevant wins default priority
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Multi"}})
            raw.close()


class TestPublicationEvidence:
    @pytest.mark.asyncio
    async def test_publication_title_overlap_is_evidence(self):
        # Publication evidence enriches a candidate already retrieved via a
        # real profile field (see relevance.py's documented scope limit) —
        # so this candidate also needs a matching research_area.
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"D8Pub {suffix}", research_areas=[f"Retrievable {suffix}"])
            await raw.db.publications.insert_one({
                "title": f"Quality Improvement Research {suffix}", "owner_id": uid,
                "journal": "J", "year": 2020,
            })
            need = ResearchNeed(
                original_query="x",
                required_expertise=[f"Retrievable {suffix}", f"Quality Improvement Research {suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            person = _find(result, uid)
            assert person is not None
            assert any(e["type"] == "publication" for e in person["evidence"])
        finally:
            await raw.db.publications.delete_many({"title": {"$regex": "Quality Improvement Research"}})
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Pub"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_publication_via_publication_authors_link_also_counts(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"D8PubLink {suffix}", research_areas=[f"Retrievable {suffix}"])
            other_owner = _oid()
            pub = await raw.db.publications.insert_one({
                "title": f"Health Diplomacy Frameworks {suffix}", "owner_id": other_owner, "year": 2021,
            })
            await raw.db.publication_authors.insert_one({
                "publication_id": str(pub.inserted_id), "synaptiq_user_id": uid, "role": "co_author", "source": "manual",
            })
            need = ResearchNeed(
                original_query="x",
                required_expertise=[f"Retrievable {suffix}", f"Health Diplomacy Frameworks {suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            person = _find(result, uid)
            assert person is not None
            assert any(e["type"] == "publication" for e in person["evidence"])
        finally:
            await raw.db.publication_authors.delete_many({"synaptiq_user_id": uid} if False else {})
            await raw.db.publications.delete_many({"title": {"$regex": "Health Diplomacy Frameworks"}})
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8PubLink"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_no_publication_evidence_when_no_overlap(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"D8NoPub {suffix}", research_areas=[f"Field {suffix}"])
            await raw.db.publications.insert_one({"title": "Totally Unrelated Topic", "owner_id": uid, "year": 2020})
            need = ResearchNeed(original_query="x", required_expertise=[f"Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            person = _find(result, uid)
            assert person is not None
            assert not any(e["type"] == "publication" for e in person["evidence"])
        finally:
            await raw.db.publications.delete_many({"owner_id": uid} if False else {"title": "Totally Unrelated Topic"})
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8NoPub"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_publication_evidence_exposes_only_title_no_other_fields(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"D8PubPriv {suffix}", research_areas=[f"Retrievable {suffix}"])
            await raw.db.publications.insert_one({
                "title": f"Sensitive Research {suffix}", "owner_id": uid, "year": 2020,
                "doi": "10.9999/should-not-appear", "journal": "SecretJournal",
            })
            need = ResearchNeed(
                original_query="x",
                required_expertise=[f"Retrievable {suffix}", f"Sensitive Research {suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            person = _find(result, uid)
            assert person is not None
            assert any(e["type"] == "publication" for e in person["evidence"])  # evidence really was produced
            blob = str(result)
            assert "10.9999/should-not-appear" not in blob
            assert "SecretJournal" not in blob
        finally:
            await raw.db.publications.delete_many({"title": {"$regex": "Sensitive Research"}})
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8PubPriv"}})
            raw.close()


class TestCoverageMap:
    @pytest.mark.asyncio
    async def test_coverage_map_marks_covered_and_uncovered(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            await _insert_user(raw.db, f"D8Cov {suffix}", research_areas=[f"Covered {suffix}"])
            need = ResearchNeed(
                original_query="x",
                required_expertise=[f"Covered {suffix}"],
                complementary_expertise=[f"Uncovered {suffix}"],
            )
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            cov = {c["term"]: c["covered"] for c in result["coverage_map"]}
            assert cov[f"Covered {suffix}"] is True
            assert cov[f"Uncovered {suffix}"] is False
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Cov"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_coverage_map_not_a_quality_score_just_booleans(self):
        raw = _RawDB()
        try:
            need = ResearchNeed(original_query="x", required_expertise=["Anything"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            for c in result["coverage_map"]:
                assert isinstance(c["covered"], bool)
                assert "score" not in c
        finally:
            raw.close()


class TestUserControls:
    @pytest.mark.asyncio
    async def test_country_filter_is_real_not_decorative(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid_match = await _insert_user(raw.db, f"D8CtrlA {suffix}", research_areas=[f"Field {suffix}"], country=f"Wakanda{suffix}")
            uid_other = await _insert_user(raw.db, f"D8CtrlB {suffix}", research_areas=[f"Field {suffix}"], country="Elsewhere")
            need = ResearchNeed(original_query="x", required_expertise=[f"Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None, country=f"Wakanda{suffix}")
            ids = {p["id"] for g in (result["similar"], result["complementary"], result["methods_specialists"], result["context_specialists"]) for p in g}
            assert uid_match in ids
            assert uid_other not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Ctrl"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_include_methods_false_drops_methods_only_matches(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid = await _insert_user(raw.db, f"D8NoMethod {suffix}", methods=[f"Technique {suffix}"])
            need = ResearchNeed(original_query="x", useful_methods=[f"Technique {suffix}"])
            with_methods = await find_relevant_people(raw.db, need, viewer_id=None, include_methods=True)
            without_methods = await find_relevant_people(raw.db, need, viewer_id=None, include_methods=False)
            assert _find(with_methods, uid) is not None
            assert _find(without_methods, uid) is None
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8NoMethod"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_available_for_collaboration_filter_real(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid_avail = await _insert_user(raw.db, f"D8Avail {suffix}", research_areas=[f"Field {suffix}"], available_for_collaboration=True)
            uid_not = await _insert_user(raw.db, f"D8NotAvail {suffix}", research_areas=[f"Field {suffix}"], available_for_collaboration=False)
            need = ResearchNeed(original_query="x", required_expertise=[f"Field {suffix}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None, available_for_collaboration=True)
            ids = {p["id"] for g in (result["similar"], result["complementary"], result["methods_specialists"], result["context_specialists"]) for p in g}
            assert uid_avail in ids
            assert uid_not not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Avail|^D8NotAvail"}})
            raw.close()


class TestRecomputeOnEdit:
    @pytest.mark.asyncio
    async def test_editing_need_changes_results_no_stale_cache(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            uid_a = await _insert_user(raw.db, f"D8EditA {suffix}", research_areas=[f"Topic A {suffix}"])
            uid_b = await _insert_user(raw.db, f"D8EditB {suffix}", research_areas=[f"Topic B {suffix}"])
            need1 = ResearchNeed(original_query="x", required_expertise=[f"Topic A {suffix}"])
            r1 = await find_relevant_people(raw.db, need1, viewer_id=None)
            need2 = ResearchNeed(original_query="x", required_expertise=[f"Topic B {suffix}"])
            r2 = await find_relevant_people(raw.db, need2, viewer_id=None)
            assert _find(r1, uid_a) is not None and _find(r1, uid_b) is None
            assert _find(r2, uid_b) is not None and _find(r2, uid_a) is None
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^D8Edit"}})
            raw.close()


class TestSparseAndZero:
    @pytest.mark.asyncio
    async def test_sparse_profile_limited_information_not_invented(self):
        raw = _RawDB()
        try:
            need = ResearchNeed(original_query="x", required_expertise=[f"NothingMatches{_oid()}"])
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            assert result["similar"] == result["complementary"] == result["methods_specialists"] == result["context_specialists"] == []
        finally:
            raw.close()

    @pytest.mark.asyncio
    async def test_zero_candidate_network_returns_clean_empty_shape(self):
        raw = _RawDB()
        try:
            need = ResearchNeed(original_query="x")
            result = await find_relevant_people(raw.db, need, viewer_id=None)
            assert set(result.keys()) >= {"similar", "complementary", "methods_specialists", "context_specialists", "coverage_map", "missing_expertise", "pool_total"}
        finally:
            raw.close()
