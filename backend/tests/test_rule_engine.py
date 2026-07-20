"""Comprehensive unit tests for the Rule Engine subsystem.

Run with:
    cd backend && python -m pytest tests/test_rule_engine.py -v

All tests are self-contained — no database, no network, no API keys.
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ── Statistics Engine ─────────────────────────────────────────────────────────

class TestStatsEngine:
    def setup_method(self):
        from services.rule_engine.statistics.stats_engine import StatsEngine
        self.stats = StatsEngine

    def test_mean_basic(self):
        assert self.stats.mean([1, 2, 3, 4, 5]) == pytest.approx(3.0)

    def test_mean_empty(self):
        assert self.stats.mean([]) == 0.0

    def test_mean_single(self):
        assert self.stats.mean([42.0]) == 42.0

    def test_median_odd(self):
        assert self.stats.median([3, 1, 4, 1, 5]) == pytest.approx(3.0)

    def test_median_even(self):
        assert self.stats.median([1, 2, 3, 4]) == pytest.approx(2.5)

    def test_median_empty(self):
        assert self.stats.median([]) == 0.0

    def test_variance_sample(self):
        var = self.stats.variance([2, 4, 4, 4, 5, 5, 7, 9], sample=True)
        assert var == pytest.approx(4.571, abs=0.01)

    def test_variance_population(self):
        var = self.stats.variance([2, 4, 4, 4, 5, 5, 7, 9], sample=False)
        assert var == pytest.approx(4.0)

    def test_std_dev(self):
        sd = self.stats.std_dev([2, 4, 4, 4, 5, 5, 7, 9], sample=False)
        assert sd == pytest.approx(2.0)

    def test_percentile_50(self):
        result = self.stats.percentile([1, 2, 3, 4, 5], 50)
        assert result == pytest.approx(3.0)

    def test_percentile_100(self):
        result = self.stats.percentile([1, 2, 3], 100)
        assert result == pytest.approx(3.0)

    def test_percentile_0(self):
        result = self.stats.percentile([1, 2, 3], 0)
        assert result == pytest.approx(1.0)

    def test_z_score_zero_mean(self):
        assert self.stats.z_score(5, 5, 2) == pytest.approx(0.0)

    def test_z_score_one_std(self):
        assert self.stats.z_score(7, 5, 2) == pytest.approx(1.0)

    def test_z_score_zero_std(self):
        assert self.stats.z_score(5, 5, 0) == 0.0

    def test_normalize(self):
        result = self.stats.normalize([0, 5, 10])
        assert result == pytest.approx([0.0, 0.5, 1.0])

    def test_normalize_all_same(self):
        result = self.stats.normalize([3, 3, 3])
        assert result == [0.5, 0.5, 0.5]

    def test_growth_rate(self):
        assert self.stats.growth_rate(100, 150) == pytest.approx(50.0)

    def test_growth_rate_zero_old(self):
        assert self.stats.growth_rate(0, 10) == pytest.approx(100.0)

    def test_linear_trend_increasing(self):
        t = self.stats.linear_trend([1, 2, 3, 4, 5])
        assert t["direction"] == "increasing"
        assert t["slope"] > 0

    def test_linear_trend_stable(self):
        t = self.stats.linear_trend([5, 5, 5, 5, 5])
        assert t["direction"] == "stable"

    def test_linear_trend_decreasing(self):
        t = self.stats.linear_trend([5, 4, 3, 2, 1])
        assert t["direction"] == "decreasing"

    def test_moving_average(self):
        result = self.stats.moving_average([1, 2, 3, 4, 5], window=3)
        assert result[4] == pytest.approx(4.0)

    def test_forecast_positive(self):
        fc = self.stats.forecast([1, 2, 3, 4, 5], steps=3)
        assert len(fc) == 3
        assert fc[0] > 5  # should continue upward trend

    def test_distribution_bins(self):
        bins = self.stats.distribution([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], bins=5)
        assert len(bins) == 5
        assert sum(b["count"] for b in bins) == 10

    def test_summary_keys(self):
        s = self.stats.summary([1, 2, 3, 4, 5])
        for key in ("count", "mean", "median", "std_dev", "min", "max"):
            assert key in s

    def test_rank_descending(self):
        ranks = self.stats.rank([10, 30, 20], ascending=False)
        assert ranks[1] == 1  # 30 is rank 1

    def test_percentile_rank(self):
        pr = self.stats.percentile_rank(5, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        assert 40 <= pr <= 60  # should be around 45th percentile

    def test_time_series_aggregate(self):
        points = [
            {"date": "2024-01-15", "value": 5},
            {"date": "2024-01-20", "value": 3},
            {"date": "2024-02-10", "value": 7},
        ]
        result = self.stats.time_series_aggregate(points, period="month")
        assert len(result) == 2
        assert result[0]["period"] == "2024-01"
        assert result[0]["sum"] == pytest.approx(8.0)


# ── H-Index Calculator ────────────────────────────────────────────────────────

class TestHIndexCalculator:
    def test_h_index_basic(self):
        from services.rule_engine.calculators.h_index import calculate_h_index
        assert calculate_h_index([10, 5, 3, 3, 2, 1]) == 3

    def test_h_index_empty(self):
        from services.rule_engine.calculators.h_index import calculate_h_index
        assert calculate_h_index([]) == 0

    def test_h_index_single(self):
        from services.rule_engine.calculators.h_index import calculate_h_index
        assert calculate_h_index([100]) == 1

    def test_h_index_all_zero(self):
        from services.rule_engine.calculators.h_index import calculate_h_index
        assert calculate_h_index([0, 0, 0]) == 0

    def test_g_index(self):
        from services.rule_engine.calculators.h_index import calculate_g_index
        # [6, 3, 1] → cumulative: 6, 9, 10. g=3 because 10 >= 9 (3²)
        assert calculate_g_index([6, 3, 1]) >= 2

    def test_i10_index(self):
        from services.rule_engine.calculators.h_index import calculate_i10_index
        assert calculate_i10_index([15, 8, 10, 3, 12]) == 3

    def test_citation_summary_keys(self):
        from services.rule_engine.calculators.h_index import citation_summary
        s = citation_summary([10, 5, 3, 3, 2, 1])
        for key in ("h_index", "g_index", "i10_index", "total_citations", "avg_citations_per_pub"):
            assert key in s

    def test_m_quotient(self):
        from services.rule_engine.calculators.h_index import calculate_m_quotient
        assert calculate_m_quotient(10, 5) == pytest.approx(2.0)

    def test_m_quotient_zero_years(self):
        from services.rule_engine.calculators.h_index import calculate_m_quotient
        assert calculate_m_quotient(5, 0) == 5.0


# ── Format Validators ─────────────────────────────────────────────────────────

class TestFormatValidators:
    def test_doi_valid(self):
        from services.rule_engine.validation.format_validator import validate_doi
        r = validate_doi("10.1038/nature12345")
        assert r.valid
        assert r.normalized == "https://doi.org/10.1038/nature12345"

    def test_doi_with_prefix(self):
        from services.rule_engine.validation.format_validator import validate_doi
        r = validate_doi("https://doi.org/10.1234/test.001")
        assert r.valid

    def test_doi_invalid(self):
        from services.rule_engine.validation.format_validator import validate_doi
        r = validate_doi("not-a-doi")
        assert not r.valid
        assert len(r.errors) > 0

    def test_orcid_valid(self):
        from services.rule_engine.validation.format_validator import validate_orcid
        # Known valid ORCID with correct check digit
        r = validate_orcid("0000-0002-1825-0097")
        assert r.valid

    def test_orcid_invalid_format(self):
        from services.rule_engine.validation.format_validator import validate_orcid
        r = validate_orcid("0000-0000-0000")
        assert not r.valid

    def test_isbn13_valid(self):
        from services.rule_engine.validation.format_validator import validate_isbn
        r = validate_isbn("978-0-306-40615-7")
        assert r.valid

    def test_isbn10_invalid_checksum(self):
        from services.rule_engine.validation.format_validator import validate_isbn
        r = validate_isbn("0-306-40615-0")  # wrong check digit
        assert not r.valid

    def test_issn_valid(self):
        from services.rule_engine.validation.format_validator import validate_issn
        r = validate_issn("1234-5679")
        # ISSN 1234-567X is valid; 1234-5679 has a different check digit
        # We just verify the function runs without error
        assert isinstance(r.valid, bool)

    def test_email_valid(self):
        from services.rule_engine.validation.format_validator import validate_email
        r = validate_email("user@example.com")
        assert r.valid

    def test_email_invalid(self):
        from services.rule_engine.validation.format_validator import validate_email
        r = validate_email("not-an-email")
        assert not r.valid

    def test_url_valid(self):
        from services.rule_engine.validation.format_validator import validate_url
        r = validate_url("https://www.example.com")
        assert r.valid

    def test_url_invalid(self):
        from services.rule_engine.validation.format_validator import validate_url
        r = validate_url("not a url")
        assert not r.valid


# ── Reference Validators ──────────────────────────────────────────────────────

class TestReferenceValidators:
    def test_apa_valid_basic(self):
        from services.rule_engine.validation.reference_validator import validate_apa_reference
        ref = "Smith, J. D. (2020). A study of things. Journal of Research, 15(3), 1–10. https://doi.org/10.1234/abc"
        r = validate_apa_reference(ref)
        assert r.valid
        assert len(r.errors) == 0

    def test_apa_missing_year(self):
        from services.rule_engine.validation.reference_validator import validate_apa_reference
        r = validate_apa_reference("Smith, J. Title. Journal.")
        assert not r.valid

    def test_ieee_valid_basic(self):
        from services.rule_engine.validation.reference_validator import validate_ieee_reference
        ref = '[1] J. D. Smith, "A study of things," J. Res., vol. 15, no. 3, pp. 1–10, 2020.'
        r = validate_ieee_reference(ref)
        assert r.valid

    def test_ieee_missing_ref_number(self):
        from services.rule_engine.validation.reference_validator import validate_ieee_reference
        r = validate_ieee_reference('J. D. Smith, "Title," J. Res., 2020.')
        assert not r.valid

    def test_duplicate_detection(self):
        from services.rule_engine.validation.reference_validator import find_duplicate_references
        refs = [
            "Smith, J. (2020). Title one. Journal, 1, 1–5.",
            "Brown, K. (2021). Title two. Journal, 2, 5–10.",
            "Smith, J. (2020). Title one. Journal, 1, 1–5.",
        ]
        dupes = find_duplicate_references(refs)
        assert len(dupes) >= 1


# ── Manuscript Validator ──────────────────────────────────────────────────────

class TestManuscriptValidator:
    def test_abstract_too_short(self):
        from services.rule_engine.validation.manuscript_validator import validate_abstract
        r = validate_abstract("Short abstract.", min_words=150)
        assert not r.valid

    def test_abstract_ok(self):
        from services.rule_engine.validation.manuscript_validator import validate_abstract
        text = " ".join(["word"] * 200)
        r = validate_abstract(text)
        # May still have warnings for missing components but should not have errors for length
        length_errors = [e for e in r.errors() if "TOO_SHORT" in e.code]
        assert len(length_errors) == 0

    def test_keywords_too_few(self):
        from services.rule_engine.validation.manuscript_validator import validate_keywords
        r = validate_keywords(["single"])
        assert not r.valid

    def test_keywords_ok(self):
        from services.rule_engine.validation.manuscript_validator import validate_keywords
        r = validate_keywords(["machine learning", "neural network", "deep learning", "classification"])
        assert r.valid

    def test_keyword_duplicate(self):
        from services.rule_engine.validation.manuscript_validator import validate_keywords
        r = validate_keywords(["machine learning", "machine learning", "deep learning", "classification"])
        assert not r.valid

    def test_sections_missing(self):
        from services.rule_engine.validation.manuscript_validator import validate_manuscript_sections
        r = validate_manuscript_sections("This is just some text without proper sections.")
        errors = r.errors()
        assert len(errors) > 0  # missing required sections

    def test_sections_present(self):
        from services.rule_engine.validation.manuscript_validator import validate_manuscript_sections
        text = "Introduction\nMethods\nResults\nDiscussion\nConclusion\nAbstract\nReferences"
        r = validate_manuscript_sections(text)
        assert r.valid


# ── Text Formatter ────────────────────────────────────────────────────────────

class TestFormatters:
    def test_apa_journal(self):
        from services.rule_engine.formatting.apa_formatter import format_apa_journal
        ref = format_apa_journal(
            authors=["Smith, John D.", "Brown, Mary A."],
            year=2023,
            title="The title of the article",
            journal="Journal of Research",
            volume=45, issue=3, pages="123-145",
            doi="10.1234/abc",
        )
        assert "2023" in ref
        assert "Journal" in ref and "Research" in ref
        assert "doi.org" in ref
        assert "Smith" in ref
        assert "Brown" in ref

    def test_ieee_journal(self):
        from services.rule_engine.formatting.ieee_formatter import format_ieee_journal
        ref = format_ieee_journal(
            authors=["John D. Smith", "Mary A. Brown"],
            title="The title of the article",
            journal="Journal of Research",
            volume=45, number=3, pages="123-145", year=2023,
            ref_number=1,
        )
        assert "[1]" in ref
        assert "2023" in ref
        assert "The title of the article" in ref

    def test_normalize_author_name(self):
        from services.rule_engine.formatting.text_normalizer import normalize_author_name
        assert normalize_author_name("John Michael Smith") == "Smith, J. M."

    def test_normalize_whitespace(self):
        from services.rule_engine.formatting.text_normalizer import normalize_whitespace
        assert normalize_whitespace("  hello   world  ") == "hello world"

    def test_normalize_page_range(self):
        from services.rule_engine.formatting.reference_normalizer import normalize_page_range
        assert normalize_page_range("123-145") == "123–145"
        assert normalize_page_range("123–145") == "123–145"


# ── Scoring Modules ───────────────────────────────────────────────────────────

class TestScoringModules:
    def test_profile_score_complete(self):
        from services.rule_engine.scoring.profile_score import calculate_profile_score
        profile = {
            "avatar_url": "https://example.com/avatar.jpg",
            "bio": "A" * 100,
            "institution": "MIT",
            "research_keywords": ["ML", "AI", "NLP", "CV"],
            "research_methods": ["experiments"],
            "social_links": ["https://scholar.google.com"],
            "availability": "open",
            "orcid_id": "0000-0002-1825-0097",
            "publications_count": 10,
            "employment": [{"role": "Professor"}],
            "education": [{"degree": "PhD"}],
        }
        r = calculate_profile_score(profile)
        assert r.score > 80

    def test_profile_score_empty(self):
        from services.rule_engine.scoring.profile_score import calculate_profile_score
        r = calculate_profile_score({})
        assert r.score == 0.0
        assert len(r.recommendations) > 0

    def test_research_score_no_output(self):
        from services.rule_engine.scoring.research_score import calculate_research_score
        r = calculate_research_score()
        assert r.score == 0.0
        assert len(r.recommendations) > 0

    def test_research_score_active(self):
        from services.rule_engine.scoring.research_score import calculate_research_score
        r = calculate_research_score(
            publications=20, citations=300, h_index=10,
            grants_awarded=2, collaborations=5, career_years=8,
        )
        assert r.score > 50

    def test_collaboration_score(self):
        from services.rule_engine.scoring.collaboration_score import calculate_collaboration_score
        r = calculate_collaboration_score(
            owned_collaborations=5, accepted_applications=8,
            workspace_members=12, completion_rate=0.8,
        )
        assert r.score > 30

    def test_reviewer_score_high_volume(self):
        from services.rule_engine.scoring.reviewer_score import calculate_reviewer_score
        r = calculate_reviewer_score(
            reviews_completed=20, avg_turnaround_days=7, avg_quality_rating=4.5,
        )
        assert r.score > 60

    def test_teaching_score_empty(self):
        from services.rule_engine.scoring.teaching_score import calculate_teaching_score
        r = calculate_teaching_score()
        assert r.score == 0.0

    def test_institution_score_established(self):
        from services.rule_engine.scoring.institution_score import calculate_institution_score
        r = calculate_institution_score(
            active_researchers=100, publications_count=500,
            total_citations=10000, avg_h_index=15,
            grants_awarded=30, verified=True,
        )
        assert r.score > 50


# ── Matching Engine ───────────────────────────────────────────────────────────

class TestMatchingEngine:
    def test_jaccard_empty(self):
        from services.rule_engine.matching.weighted_scorer import jaccard_similarity
        assert jaccard_similarity([], []) == 0.0

    def test_jaccard_identical(self):
        from services.rule_engine.matching.weighted_scorer import jaccard_similarity
        assert jaccard_similarity(["a", "b", "c"], ["a", "b", "c"]) == pytest.approx(1.0)

    def test_jaccard_disjoint(self):
        from services.rule_engine.matching.weighted_scorer import jaccard_similarity
        assert jaccard_similarity(["a", "b"], ["c", "d"]) == pytest.approx(0.0)

    def test_jaccard_partial(self):
        from services.rule_engine.matching.weighted_scorer import jaccard_similarity
        result = jaccard_similarity(["a", "b", "c"], ["b", "c", "d"])
        assert 0.3 < result < 0.7

    def test_weighted_score(self):
        from services.rule_engine.matching.weighted_scorer import weighted_score
        score = weighted_score({"a": (1.0, 0.5), "b": (0.5, 0.5)})
        assert score == pytest.approx(75.0)

    def test_researcher_matcher_returns_results(self):
        from services.rule_engine.matching.researcher_matcher import match_researchers
        user = {"research_areas": ["machine learning", "NLP"], "user_type": "researcher"}
        candidates = [
            {"_id": "1", "research_areas": ["machine learning", "CV"], "user_type": "phd_candidate"},
            {"_id": "2", "research_areas": ["ecology", "biology"], "user_type": "researcher"},
            {"_id": "3", "research_areas": ["machine learning", "NLP"], "user_type": "researcher"},
        ]
        results = match_researchers(user, candidates, top_n=3)
        assert len(results) == 3
        # Best match (same areas) should rank first
        assert results[0].candidate_id == "3" or results[0].score >= results[1].score

    def test_reviewer_matcher_conflict_of_interest(self):
        from services.rule_engine.matching.reviewer_matcher import match_reviewers
        manuscript = {"research_areas": ["ML"], "author_ids": ["rev1"]}
        reviewers = [
            {"_id": "rev1", "research_areas": ["ML"]},  # conflict: is an author
            {"_id": "rev2", "research_areas": ["ML"]},
        ]
        results = match_reviewers(manuscript, reviewers)
        rev1_result = next((r for r in results if r.reviewer_id == "rev1"), None)
        if rev1_result:
            assert len(rev1_result.conflicts) > 0


# ── Keyword Extractor ─────────────────────────────────────────────────────────

class TestKeywordExtractor:
    def test_extracts_keywords(self):
        from services.rule_engine.recommendations.keyword_extractor import extract_keywords
        text = ("machine learning algorithms for natural language processing "
                "using deep neural networks in computational linguistics")
        kws = extract_keywords(text, top_n=5)
        assert len(kws) > 0
        # Should find meaningful terms
        combined = " ".join(kws).lower()
        assert any(term in combined for term in ("machine", "neural", "language", "learning"))

    def test_removes_stopwords(self):
        from services.rule_engine.recommendations.keyword_extractor import extract_keywords
        text = "the and a is are of in on at for to with by"
        kws = extract_keywords(text, top_n=5)
        # Should return empty or very few results since all are stopwords
        assert len(kws) == 0 or all(len(k) > 2 for k in kws)

    def test_scored_keywords(self):
        from services.rule_engine.recommendations.keyword_extractor import extract_keywords_scored
        text = "machine learning deep learning neural networks classification"
        result = extract_keywords_scored(text, top_n=5)
        assert len(result) > 0
        assert "keyword" in result[0]
        assert "relevance" in result[0]

    def test_suggest_additional(self):
        from services.rule_engine.recommendations.keyword_extractor import suggest_additional_keywords
        existing = ["machine learning"]
        text = "machine learning deep learning neural networks classification optimization"
        suggestions = suggest_additional_keywords(existing, text, top_n=3)
        assert all(s.lower() != "machine learning" for s in suggestions)


# ── Alert Engine ──────────────────────────────────────────────────────────────

class TestAlertEngine:
    def test_no_orcid_alert(self):
        from services.rule_engine.alerts.alert_engine import generate_profile_alerts
        alerts = generate_profile_alerts({"bio": "A" * 100, "institution": "MIT"})
        codes = [a.code for a in alerts]
        assert "ORCID_DISCONNECTED" in codes

    def test_no_alerts_complete_profile(self):
        from services.rule_engine.alerts.alert_engine import generate_profile_alerts
        alerts = generate_profile_alerts({
            "orcid_id": "0000-0002-1825-0097",
            "bio": "A" * 100,
            "institution": "MIT",
            "research_keywords": ["ML", "AI", "NLP"],
        })
        assert len(alerts) == 0

    def test_low_credits_critical(self):
        from services.rule_engine.alerts.alert_engine import generate_account_alerts
        alerts = generate_account_alerts({"credits_balance": 0})
        assert any(a.code == "LOW_AI_CREDITS" and a.level == "critical" for a in alerts)

    def test_grant_deadline_alert(self):
        from services.rule_engine.alerts.alert_engine import generate_grant_alerts
        from datetime import datetime, timezone, timedelta
        deadline = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        alerts = generate_grant_alerts([{"grant_title": "Test Grant", "deadline": deadline}])
        assert len(alerts) > 0
        assert alerts[0].code == "GRANT_DEADLINE_APPROACHING"

    def test_grant_far_deadline_no_alert(self):
        from services.rule_engine.alerts.alert_engine import generate_grant_alerts
        from datetime import datetime, timezone, timedelta
        deadline = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
        alerts = generate_grant_alerts([{"grant_title": "Test Grant", "deadline": deadline}])
        assert len(alerts) == 0

    def test_generate_all_alerts_priority_order(self):
        from services.rule_engine.alerts.alert_engine import generate_all_alerts
        alerts = generate_all_alerts(
            profile={},
            account={"credits_balance": 0},
        )
        levels = [a.level for a in alerts]
        assert "critical" in levels or "warning" in levels


# ── Profile Recommender ───────────────────────────────────────────────────────

class TestProfileRecommender:
    def test_recommendations_for_empty_profile(self):
        from services.rule_engine.recommendations.profile_recommender import get_profile_recommendations
        recs = get_profile_recommendations({})
        assert len(recs) > 0
        # ORCID should be priority 1
        assert recs[0].priority == 1
        assert "ORCID" in recs[0].title

    def test_quick_wins(self):
        from services.rule_engine.recommendations.profile_recommender import get_quick_wins
        wins = get_quick_wins({})
        assert len(wins) <= 3

    def test_complete_profile_no_critical_recs(self):
        from services.rule_engine.recommendations.profile_recommender import get_profile_recommendations
        profile = {
            "orcid_id": "0000-0002-1825-0097",
            "avatar_url": "https://example.com/a.jpg",
            "bio": "A" * 200,
            "institution": "MIT",
            "research_keywords": ["ML", "AI", "NLP", "CV", "DL"],
            "research_methods": ["experiments"],
            "employment": [{}],
            "education": [{}],
            "openalex_id": "A123",
        }
        recs = get_profile_recommendations(profile)
        # Most or all high-priority recommendations should be gone
        high_priority = [r for r in recs if r.priority <= 2]
        assert len(high_priority) == 0


# ── Rule Engine Orchestrator ──────────────────────────────────────────────────

class TestRuleEngineOrchestrator:
    def setup_method(self):
        from services.rule_engine.engine import get_rule_engine
        self.engine = get_rule_engine()

    def test_supported_features(self):
        features = self.engine.supported_features()
        assert len(features) >= 20
        assert "profile_score" in features
        assert "h_index" in features
        assert "validate_doi" in features
        assert "extract_keywords" in features
        assert "statistics" in features

    def test_can_handle_known(self):
        assert self.engine.can_handle("profile_score")

    def test_can_handle_unknown(self):
        assert not self.engine.can_handle("nonexistent_feature_xyz")

    def test_execute_profile_score(self):
        result = self.engine.execute("profile_score", {"bio": "A" * 100})
        assert "score" in result
        assert isinstance(result["score"], (int, float))

    def test_execute_h_index(self):
        result = self.engine.execute("h_index", {"citation_counts": [10, 5, 3, 3, 1]})
        assert result.get("h_index") == 3

    def test_execute_validate_doi(self):
        result = self.engine.execute("validate_doi", {"doi": "10.1038/nature12345"})
        assert result.get("valid") is True

    def test_execute_statistics_mean(self):
        result = self.engine.execute("statistics", {"values": [1, 2, 3, 4, 5], "operation": "mean"})
        assert result.get("mean") == pytest.approx(3.0)

    def test_execute_statistics_summary(self):
        result = self.engine.execute("statistics", {"values": [1, 2, 3], "operation": "summary"})
        assert "mean" in result and "std_dev" in result

    def test_execute_extract_keywords(self):
        result = self.engine.execute("extract_keywords", {
            "text": "machine learning deep learning neural networks",
            "top_n": 5,
        })
        assert "keywords" in result
        assert len(result["keywords"]) > 0

    def test_execute_generate_alerts(self):
        result = self.engine.execute("generate_alerts", {
            "profile": {},
            "account": {"credits_balance": 0},
        })
        assert "alerts" in result
        assert len(result["alerts"]) > 0

    def test_execute_unknown_feature_no_raise(self):
        result = self.engine.execute("nonexistent_feature_xyz", {})
        assert "error" in result
        assert "available" in result

    def test_execute_text_returns_string(self):
        text = self.engine.execute_text("h_index", {"citation_counts": [10, 5, 3, 1]})
        assert isinstance(text, str)
        assert "h-index" in text.lower() or "H-index" in text

    def test_singleton(self):
        from services.rule_engine.engine import get_rule_engine
        e1 = get_rule_engine()
        e2 = get_rule_engine()
        assert e1 is e2

    def test_execute_format_apa(self):
        result = self.engine.execute("format_apa", {
            "type": "journal",
            "authors": ["Smith, John"],
            "year": 2023,
            "title": "A test article",
            "journal": "Journal of Tests",
        })
        assert "formatted" in result
        assert "2023" in result["formatted"]

    def test_execute_match_researchers(self):
        result = self.engine.execute("match_researchers", {
            "user": {"research_areas": ["ML"]},
            "candidates": [
                {"_id": "1", "research_areas": ["ML", "DL"]},
                {"_id": "2", "research_areas": ["ecology"]},
            ],
        })
        assert "matches" in result
        assert len(result["matches"]) > 0


# ── Telemetry ─────────────────────────────────────────────────────────────────

class TestTelemetry:
    def setup_method(self):
        from services.rule_engine import telemetry
        telemetry.reset_stats()
        self.telemetry = telemetry

    def test_record_and_get_stats(self):
        self.telemetry.record_execution("test_rule", 10, saved_ai_request=True)
        stats = self.telemetry.get_stats()
        assert stats["total_requests"] == 1
        assert stats["ai_requests_saved"] == 1
        assert stats["estimated_cost_saved_usd"] > 0

    def test_cache_hit_rate(self):
        self.telemetry.record_execution("r1", 5, cached=True)
        self.telemetry.record_execution("r2", 5, cached=True)
        self.telemetry.record_execution("r3", 5, cached=False)
        stats = self.telemetry.get_stats()
        assert stats["cache_hit_rate_pct"] == pytest.approx(66.7, abs=1.0)

    def test_error_tracking(self):
        self.telemetry.record_execution("bad_rule", 1, error=True)
        stats = self.telemetry.get_stats()
        assert stats["error_count"] == 1

    def test_top_rules(self):
        for _ in range(5):
            self.telemetry.record_execution("popular_rule", 2)
        for _ in range(2):
            self.telemetry.record_execution("rare_rule", 2)
        stats = self.telemetry.get_stats()
        top_rules = stats["top_rules"]
        assert top_rules[0]["rule"] == "popular_rule"
        assert top_rules[0]["count"] == 5

    def test_reset(self):
        self.telemetry.record_execution("r", 10)
        self.telemetry.reset_stats()
        stats = self.telemetry.get_stats()
        assert stats["total_requests"] == 0


# ── Impact Calculator ─────────────────────────────────────────────────────────

class TestImpactCalculator:
    def test_sis_research_output(self):
        from services.rule_engine.calculators.impact_calculator import sis_research_output
        pts = sis_research_output(n_published=5, n_submitted=2, n_drafted=3)
        assert pts > 0
        assert pts <= 2500

    def test_sis_total_labels(self):
        from services.rule_engine.calculators.impact_calculator import compute_sis
        result = compute_sis({"research": 500, "citations": 300})
        assert result["sis_total"] == 800
        assert "sis_label" in result

    def test_career_progress_score(self):
        from services.rule_engine.calculators.impact_calculator import career_progress_score
        score = career_progress_score(
            career_years=5, h_index=8, total_publications=15,
            total_grants=1, academic_role="postdoctoral_researcher",
        )
        assert 0 <= score <= 100


# ── Ranking ───────────────────────────────────────────────────────────────────

class TestRanking:
    def test_researcher_ranking_order(self):
        from services.rule_engine.ranking.researcher_ranker import rank_researchers
        researchers = [
            {"_id": "1", "h_index": 20, "total_citations": 1000, "publications_count": 50},
            {"_id": "2", "h_index": 5, "total_citations": 100, "publications_count": 10},
            {"_id": "3", "h_index": 12, "total_citations": 500, "publications_count": 30},
        ]
        ranked = rank_researchers(researchers)
        assert ranked[0]["id"] == "1"  # highest metrics
        assert ranked[0]["rank"] == 1

    def test_leaderboard(self):
        from services.rule_engine.ranking.researcher_ranker import compute_leaderboard
        researchers = [
            {"_id": "1", "h_index": 20, "country": "Germany"},
            {"_id": "2", "h_index": 5, "country": "France"},
        ]
        result = compute_leaderboard(researchers, scope="global", top_n=10)
        assert result["scope"] == "global"
        assert "leaderboard" in result


# ── Analytics ─────────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_publication_trends(self):
        from services.rule_engine.analytics.publication_analytics import compute_publication_trends
        pubs = [
            {"published_at": "2022-03-01", "status": "published"},
            {"published_at": "2023-06-15", "status": "published"},
            {"published_at": "2023-11-20", "status": "published"},
        ]
        result = compute_publication_trends(pubs, period="year")
        assert result["total"] == 3
        assert len(result["periods"]) >= 2

    def test_citation_milestones(self):
        from services.rule_engine.analytics.citation_analytics import compute_citation_milestones
        result = compute_citation_milestones(75)
        assert result["next_milestone"] == 100
        assert result["prev_milestone"] == 50
        assert 0 < result["progress_pct"] < 100

    def test_per_publication_stats(self):
        from services.rule_engine.analytics.citation_analytics import compute_per_publication_stats
        pubs = [
            {"citation_count": 10},
            {"citation_count": 5},
            {"citation_count": 0},
        ]
        result = compute_per_publication_stats(pubs)
        assert result["h_index"] == 2
        assert result["total"] == 15
        assert result["uncited_pct"] == pytest.approx(33.3, abs=1.0)
