"""Phase 9A Part 2 — public landing-page "What are you researching?" preview.

Covers the safety invariants this endpoint exists to guarantee: no AI call
(zero cost, zero abuse-via-cost surface), no database access, no real
person/institution ever appears in a response, always returns something
useful (never an empty/error state for a query that matches nothing), input
is length-bounded, and the public route is rate-limited by IP.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.public_demo.research_preview import preview_research_themes, _MAX_QUERY_LEN
from routers.public_demo import PreviewRequest


class TestDeterministicTaxonomy:
    def test_health_query_matches_expected_domains(self):
        result = preview_research_themes(
            "How can hospitals reduce patient waiting times without increasing staff workload?"
        )
        assert "Health Services Research" in result["themes"]
        assert "Quality Management" in result["complementary_disciplines"]
        assert "Operations Research" in result["complementary_disciplines"]
        assert result["matched_taxonomy"] is True

    def test_interdisciplinary_query_surfaces_both_domains(self):
        result = preview_research_themes(
            "Using machine learning to detect early signs of crop disease in smallholder farms"
        )
        assert "Machine Learning" in result["themes"]
        assert "Agricultural Science" in result["themes"]

    def test_no_taxonomy_match_falls_back_to_query_keywords_not_empty(self):
        result = preview_research_themes("asdkjaslkdjaslkdj random gibberish text nothing meaningful")
        assert result["matched_taxonomy"] is False
        assert len(result["themes"]) > 0  # never an empty response
        assert result["complementary_disciplines"] == []

    def test_empty_query_still_returns_a_shape_without_raising(self):
        result = preview_research_themes("")
        assert isinstance(result, dict)
        assert result["themes"] == []
        assert result["keywords"] == []

    def test_never_returns_a_person_name_or_institution_field(self):
        """Structural guarantee, not just a spot-check: the response shape
        itself has no field that could ever carry a person/institution."""
        result = preview_research_themes("cybersecurity policy for hospitals")
        allowed_keys = {"themes", "complementary_disciplines", "methods", "keywords", "matched_taxonomy"}
        assert set(result.keys()) == allowed_keys

    def test_long_query_is_truncated_not_rejected(self):
        long_query = "climate policy " * 100  # far over _MAX_QUERY_LEN
        result = preview_research_themes(long_query)
        assert isinstance(result, dict)  # truncated internally, never raises


class TestNoNetworkOrDbDependency:
    def test_module_has_no_db_or_llm_imports(self):
        """The whole point of this module is that it CANNOT become an AI-cost
        or real-people surface — enforce that structurally by checking what
        it actually imports, not just by convention. (Checks real bindings,
        not raw source text, since the module's own docstring explains this
        guarantee in prose and would otherwise trip a naive string search.)"""
        import ast
        import inspect
        import services.public_demo.research_preview as mod

        tree = ast.parse(inspect.getsource(mod))
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_names.add(node.module or "")
                imported_names.update(a.name for a in node.names)

        forbidden = {"call_llm", "get_db", "discovery_engine", "find_relevant_people", "services.ai.llm"}
        assert not (imported_names & forbidden), imported_names & forbidden


class TestRequestValidation:
    def test_empty_query_rejected(self):
        with pytest.raises(Exception):
            PreviewRequest(query="")

    def test_whitespace_only_query_rejected(self):
        with pytest.raises(Exception):
            PreviewRequest(query="   ")

    def test_over_length_query_rejected(self):
        with pytest.raises(Exception):
            PreviewRequest(query="x" * (_MAX_QUERY_LEN + 1))

    def test_reasonable_query_accepted(self):
        req = PreviewRequest(query="What are the effects of remote work on team collaboration?")
        assert req.query


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_kicks_in_after_threshold(self, monkeypatch):
        import rate_limit
        monkeypatch.setattr(rate_limit.limiter, "enabled", True)
        monkeypatch.setattr(rate_limit, "PUBLIC_DEMO_RATE", "3/minute")
        monkeypatch.setattr(rate_limit, "_public_demo_rate_item", None)

        ip = "203.0.113.42"  # TEST-NET-3, safe to use as a fake IP in a test
        for _ in range(3):
            rate_limit.check_public_demo_rate_limit(ip)
        with pytest.raises(HTTPException) as exc:
            rate_limit.check_public_demo_rate_limit(ip)
        assert exc.value.status_code == 429

    @pytest.mark.asyncio
    async def test_different_ips_have_independent_limits(self, monkeypatch):
        import rate_limit
        monkeypatch.setattr(rate_limit.limiter, "enabled", True)
        monkeypatch.setattr(rate_limit, "PUBLIC_DEMO_RATE", "1/minute")
        monkeypatch.setattr(rate_limit, "_public_demo_rate_item", None)

        rate_limit.check_public_demo_rate_limit("203.0.113.10")
        rate_limit.check_public_demo_rate_limit("203.0.113.11")  # must not raise — different IP
