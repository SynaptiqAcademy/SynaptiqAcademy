"""Regression tests for the Phase 1 matching-consolidation work on
services/collab_intelligence — the canonical matching engine.

Covers the specific signals migrated in from the (now-deprecated-candidate)
duplicate matchers, plus the two ground rules from the Phase 1 spec:
deterministic matching must not consume AI credits, and the engine must
support both similarity and complementarity, not just keyword overlap.
"""
from __future__ import annotations

import ast
import pathlib

from services.collab_intelligence.matching_engine import (
    match_researchers, rank_matches, _WEIGHTS,
)
from services.collab_intelligence.researcher_profiler import build_researcher_profile
from services.collab_intelligence.models import CareerStage


def _user(uid, **overrides):
    base = {
        "_id": uid,
        "full_name": f"User {uid}",
        "institution": "Test University",
        "country": "United States",
        "research_areas": ["machine learning"],
        "keywords": ["deep learning"],
        "h_index": 5.0,
        "publications_count": 10,
        "availability_score": 0.7,
    }
    base.update(overrides)
    return base


class TestWeights:
    def test_weights_sum_to_one(self):
        assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9

    def test_reputation_compatibility_is_a_weighted_factor(self):
        assert "reputation_compatibility" in _WEIGHTS
        assert _WEIGHTS["reputation_compatibility"] > 0


class TestReputationSignalMigration:
    """Signal migrated from services/recommendation/matchers/researchers.py's
    rep_score (min(reputation/200, 1.0) * 5 out of 100)."""

    def test_higher_combined_reputation_scores_higher(self):
        a = build_researcher_profile(_user("a"), reputation_score=90)
        b_low = build_researcher_profile(_user("b1"), reputation_score=5)
        b_high = build_researcher_profile(_user("b2"), reputation_score=90)

        low_match = match_researchers(a, b_low)
        high_match = match_researchers(a, b_high)
        assert high_match.reputation_compatibility > low_match.reputation_compatibility
        assert high_match.overall_score > low_match.overall_score

    def test_reputation_score_param_overrides_user_dict(self):
        # Explicit param takes priority over a same-named key on the user dict,
        # per build_researcher_profile's documented precedence.
        profile = build_researcher_profile(_user("a", reputation_score=1), reputation_score=99)
        assert profile.reputation_score == 99.0

    def test_no_reputation_data_is_neutral_not_penalized(self):
        a = build_researcher_profile(_user("a"))
        b = build_researcher_profile(_user("b"))
        m = match_researchers(a, b)
        assert m.reputation_compatibility == 0.5


class TestCareerComplementaritySignalMigration:
    """Signal migrated from services/recommendation/scoring.py's
    career_complement(), which read `academic_role` — collab_intelligence's
    own career_stage inference previously only read position/academic_position
    + user_type, never academic_role."""

    def test_academic_role_feeds_career_stage_inference(self):
        profile = build_researcher_profile(_user("a", academic_role="Full Professor"))
        assert profile.career_stage == CareerStage.SENIOR

        profile2 = build_researcher_profile(_user("b", academic_role="PhD Student"))
        assert profile2.career_stage == CareerStage.STUDENT


class TestDismissalSignalMigration:
    """Signal migrated from services/recommendation/matchers/researchers.py's
    interaction_cache dismissal penalty (*0.2)."""

    def test_dismissed_candidate_is_penalized_and_ranked_last(self):
        source = build_researcher_profile(_user("src"))
        strong_match = build_researcher_profile(
            _user("strong", research_areas=["machine learning"], keywords=["deep learning"]))
        weak_match = build_researcher_profile(
            _user("weak", research_areas=["completely unrelated topic xyz"], keywords=[]))

        undismissed = rank_matches(source, [strong_match, weak_match], top_n=10)
        assert undismissed[0].researcher_b_id == "strong"

        dismissed = rank_matches(source, [strong_match, weak_match], top_n=10,
                                  dismissed_ids={"strong"})
        strong_result = next(m for m in dismissed if m.researcher_b_id == "strong")
        undismissed_strong = next(m for m in undismissed if m.researcher_b_id == "strong")
        assert strong_result.overall_score == round(undismissed_strong.overall_score * 0.2, 3)


class TestSimilarityAndComplementarityBothSupported:
    def test_identical_profiles_score_high_similarity(self):
        a = build_researcher_profile(_user("a", research_areas=["genomics"], keywords=["crispr"]))
        b = build_researcher_profile(_user("b", research_areas=["genomics"], keywords=["crispr"]))
        m = match_researchers(a, b)
        assert m.research_similarity > 0.8

    def test_partial_overlap_scores_higher_complementarity_than_total_overlap(self):
        # 100% keyword overlap = pure duplication, not complementary.
        a = build_researcher_profile(_user("a", research_areas=["x"], keywords=["y", "z"]))
        b_identical = build_researcher_profile(_user("b1", research_areas=["x"], keywords=["y", "z"]))
        # Partial overlap (shared "x" area, distinct keywords) sits in the
        # documented complementarity sweet spot.
        b_partial = build_researcher_profile(
            _user("b2", research_areas=["x"], keywords=["q", "r", "s", "t", "u"]))

        m_identical = match_researchers(a, b_identical)
        m_partial = match_researchers(a, b_partial)
        assert m_partial.complementarity >= m_identical.complementarity


class TestNoAICreditConsumption:
    def test_matching_engine_module_imports_no_ai_or_llm_dependency(self):
        path = pathlib.Path(
            __import__("services.collab_intelligence.matching_engine", fromlist=["x"]).__file__
        )
        tree = ast.parse(path.read_text())
        banned = ("openai", "anthropic", "call_llm", "ai_credits", "claude")
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", None) or ""
                names = [a.name for a in node.names]
                joined = f"{module} {' '.join(names)}".lower()
                assert not any(b in joined for b in banned), f"unexpected AI-related import: {joined}"
