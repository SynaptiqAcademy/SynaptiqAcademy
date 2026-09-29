"""Regression tests for the P1 Phase 6 (Matching Consolidation) fixes.

Covers: services/recommendation/matchers/researchers.py now delegates to
the canonical services/collab_intelligence/matching_engine.py instead of
computing its own independent formula; the legacy /match-score/{id}
endpoint is removed; discover/sections remains a separate, unaffected
discovery scorer; the canonical engine still reads no reputation/trust
collection directly; deterministic matching still consumes zero AI credits.

No matching weights, Research Record, Verification, reputation/trust
architecture, grant/institution/reviewer matching, or Connect/Follow/
Collaboration Request mechanisms were touched.
"""
from __future__ import annotations

import ast
import inspect
import os

import pytest
from bson import ObjectId

from services.collab_intelligence.matching_engine import match_researchers as canonical_match
from services.collab_intelligence.researcher_profiler import build_researcher_profile
from services.recommendation.matchers.researchers import match_researchers as delegate_match


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


class TestRecommendationMatcherDelegatesToCanonical:
    @pytest.mark.asyncio
    async def test_score_matches_canonical_engine_for_identical_inputs(self):
        """The recommendation matcher's returned score for a candidate must
        equal what the canonical engine itself computes for the same two
        profiles — proving it's not running an independent formula."""
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            source_id = await _insert_user(
                raw.db, f"Delegate Source {suffix}",
                research_areas=["genomics"], research_keywords=["crispr"], methods=["cohort study"])
            cand_id = await _insert_user(
                raw.db, f"Delegate Candidate {suffix}",
                research_areas=["genomics"], research_keywords=["gene editing"], methods=["cohort study"])

            results = await delegate_match(source_id, raw.db, limit=20)
            result = next((r for r in results if r["user_id"] == cand_id), None)
            assert result is not None

            # Recompute independently via the canonical engine directly.
            source_doc = await raw.db.users.find_one({"_id": ObjectId(source_id)})
            cand_doc = await raw.db.users.find_one({"_id": ObjectId(cand_id)})
            source_doc["_id"] = source_id
            cand_doc["_id"] = cand_id
            source_profile = build_researcher_profile(source_doc, reputation_score=0)
            cand_profile = build_researcher_profile(cand_doc, reputation_score=0)
            canonical = canonical_match(source_profile, cand_profile)

            assert result["score"] == round(canonical.overall_score * 100, 1)
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Delegate"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_no_independent_formula_source_check(self):
        """Static check: the rewritten module must not contain its own
        jaccard/scoring re-implementation — it should import and call the
        canonical engine's rank_matches, not recompute sub-scores itself."""
        tree = ast.parse(inspect.getsource(
            __import__("services.recommendation.matchers.researchers", fromlist=["x"])))
        # No local jaccard/career_complement helper functions defined in this module anymore.
        func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        assert "jaccard" not in func_names
        assert "career_complement" not in func_names
        # Must import rank_matches from the canonical engine.
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        imported_names = {a.name for n in imports for a in n.names}
        assert "rank_matches" in imported_names

    @pytest.mark.asyncio
    async def test_reputation_still_isolated_from_canonical_engine_itself(self):
        """The canonical engine module itself must still import nothing
        reputation/trust-related — reputation only enters via the optional
        parameter this file passes in, never a direct collection read
        inside matching_engine.py or researcher_profiler.py."""
        for modname in (
            "services.collab_intelligence.matching_engine",
            "services.collab_intelligence.researcher_profiler",
        ):
            src = inspect.getsource(__import__(modname, fromlist=["x"]))
            lowered = src.lower()
            for banned in ("reputation_scores", "research_reputation", "verification_profiles",
                           "research_impact", "trust_passports", "trust_scores"):
                assert banned not in lowered, f"{modname} unexpectedly references {banned}"

    @pytest.mark.asyncio
    async def test_excludes_already_connected_and_self(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            source_id = await _insert_user(raw.db, f"Exclusion Source {suffix}")
            connected_id = await _insert_user(raw.db, f"Exclusion Connected {suffix}")
            await raw.db.collaborations.insert_one({"members": [source_id, connected_id]})

            results = await delegate_match(source_id, raw.db, limit=20)
            ids = {r["user_id"] for r in results}
            assert source_id not in ids
            assert connected_id not in ids
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Exclusion"}})
            await raw.db.collaborations.delete_many({"members": source_id})
            raw.close()

    @pytest.mark.asyncio
    async def test_dismissal_still_applies_via_canonical_rank_matches(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            source_id = await _insert_user(
                raw.db, f"Dismiss Source {suffix}", research_areas=["genomics"])
            cand_id = await _insert_user(
                raw.db, f"Dismiss Candidate {suffix}", research_areas=["genomics"])

            undismissed = await delegate_match(source_id, raw.db, limit=20)
            u = next(r for r in undismissed if r["user_id"] == cand_id)

            dismissed = await delegate_match(
                source_id, raw.db, limit=20, interaction_cache={cand_id: "dismissed"})
            d = next(r for r in dismissed if r["user_id"] == cand_id)

            assert d["score"] == round(u["score"] * 0.2, 1)
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Dismiss"}})
            raw.close()

    @pytest.mark.asyncio
    async def test_response_shape_unchanged(self):
        raw = _RawDB()
        try:
            suffix = _oid()[:8]
            source_id = await _insert_user(raw.db, f"Shape Source {suffix}")
            await _insert_user(raw.db, f"Shape Candidate {suffix}", research_areas=["x"])

            results = await delegate_match(source_id, raw.db, limit=20)
            assert results
            row = results[0]
            for key in ("user_id", "full_name", "institution", "country", "academic_role",
                        "avatar_url", "orcid", "research_areas", "reputation_score",
                        "publication_count", "score", "explanation", "match_label"):
                assert key in row
            assert row["match_label"].endswith("% Match")
        finally:
            await raw.db.users.delete_many({"full_name": {"$regex": "^Shape"}})
            raw.close()


class TestLegacyMatchScoreRemoved:
    def test_route_no_longer_registered(self):
        from server import app
        paths = [r.path for r in app.routes if "match-score" in getattr(r, "path", "")]
        assert paths == []

    def test_get_match_score_function_removed(self):
        import routers.researchers as researchers_router
        assert not hasattr(researchers_router, "get_match_score")


class TestDiscoverySectionsUnaffected:
    def test_discover_sections_score_function_still_independent(self):
        """discover/sections keeps its own lightweight scorer — it must NOT
        have been converted to call the canonical engine (that would make
        the per-section score comparable to true compatibility, which this
        phase explicitly forbids)."""
        import routers.researchers as researchers_router
        src = inspect.getsource(researchers_router)
        # The discover_sections function's local _score() must still exist
        # and must not import or call the canonical engine (a code comment
        # merely explaining the separation, as this file has, is fine —
        # what's actually forbidden is importing/calling it).
        assert "def discover_sections" in src
        assert "from services.collab_intelligence" not in src
        assert "import services.collab_intelligence" not in src
        assert "rank_matches(" not in src
        assert "build_researcher_profile(" not in src


class TestNoAICreditsForDeterministicMatching:
    def test_recommendation_matcher_module_has_no_credit_or_llm_calls(self):
        tree = ast.parse(inspect.getsource(
            __import__("services.recommendation.matchers.researchers", fromlist=["x"])))
        src_lower = inspect.getsource(
            __import__("services.recommendation.matchers.researchers", fromlist=["x"])).lower()
        for banned in ("consume_credits", "charge_credits", "deduct_credit",
                       "call_llm", "anthropic", "openai"):
            assert banned not in src_lower

    def test_canonical_engine_module_has_no_credit_or_llm_calls(self):
        src_lower = inspect.getsource(
            __import__("services.collab_intelligence.matching_engine", fromlist=["x"])).lower()
        for banned in ("consume_credits", "charge_credits", "deduct_credit",
                       "call_llm", "anthropic", "openai"):
            assert banned not in src_lower
