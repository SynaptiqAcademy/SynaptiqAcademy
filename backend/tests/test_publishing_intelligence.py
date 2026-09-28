"""Tests for Phase XII — Academic Publishing Intelligence Platform.

100 tests across 12 test classes covering all service modules.
"""
from __future__ import annotations

import asyncio
import pytest

# ── Fixtures / constants ──────────────────────────────────────────────────────

_ML_TEXT = (
    "This study investigates deep learning methods for natural language processing. "
    "We propose a transformer-based model with attention mechanisms. "
    "The methodology uses a dataset of 50,000 labelled samples. "
    "Results show a 4.5% improvement over baseline (p < 0.01, n = 800). "
    "We applied regression analysis and ANOVA to validate statistical assumptions. "
    "Informed consent was obtained from all participants. "
    "Ethics approval was granted by the institutional review board (IRB-2024-001). "
    "Conflict of interest: none. Data availability: data are available on request. "
    "Author contributions: A.B. — conceptualisation; C.D. — methodology. "
    "Funding: This research was supported by NSF grant #12345. "
    "Keywords: deep learning, NLP, transformer, attention, language model. "
    "References: (Smith, 2021); (Jones, 2022); (Lee, 2023); (Brown, 2020); "
    "(Wang, 2019); (Liu, 2018); (Chen, 2022); (Kim, 2021); (Park, 2023); "
    "(Zhao, 2020); (Yang, 2022); (Wu, 2021); (Nguyen, 2023); (Garcia, 2022). "
    "Abstract: This paper presents a novel NLP approach using transformer architectures. "
    "Introduction: NLP has seen rapid advances. Methods: We used a BERT-based model. "
    "Results: Accuracy improved by 4.5%. Discussion: These findings support prior work. "
    "Conclusion: Our model outperforms state-of-the-art baselines on all benchmarks. "
) * 3   # ~600 words

_MED_TEXT = (
    "This randomised controlled trial investigates treatment outcomes in clinical medicine. "
    "We enrolled 240 patients with cardiovascular disease. "
    "Primary endpoint: 30-day mortality rate (p = 0.003). "
    "Ethics approval: IRB-MED-2024. Conflict of interest: none declared. "
    "Funding: NIH grant R01-HL-123456. Data availability: available on request. "
    "Abstract: A randomised controlled trial in cardiovascular medicine. "
    "Introduction: Cardiovascular disease is the leading cause of death. "
    "Methods: RCT with 240 patients randomised 1:1. Results: 30-day mortality reduced. "
    "Discussion: Our findings align with prior meta-analyses. "
    "Conclusion: Treatment X significantly reduces cardiovascular mortality. "
    "Author contributions: defined per CRediT taxonomy. "
    "(Jones, 2020); (Smith, 2021); (Brown, 2019); (Davis, 2022); (Wilson, 2023); "
    "(Taylor, 2021); (Anderson, 2020); (Thomas, 2022); (Jackson, 2019); "
    "(White, 2023); (Harris, 2021); (Martin, 2020). "
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_journal_profile_defaults(self):
        # Phase 0: no field defaults to a fabricated non-zero value — an
        # unpopulated JournalProfile must read as "no data", not "average".
        from services.publishing.models import JournalProfile
        j = JournalProfile(name="Test Journal", publisher="Test")
        assert j.quartile is None
        assert j.open_access is False
        assert j.apc_usd is None
        assert j.acceptance_rate is None
        assert not hasattr(j, "impact_factor")  # removed — no free source publishes JIF
        assert not hasattr(j, "predatory_risk")  # removed — no real basis existed

    def test_journal_profile_to_dict_carries_provenance(self):
        from services.publishing.models import JournalProfile
        j = JournalProfile(name="J", publisher="P", quartile="Q1", source="openalex", last_verified_at="2026-01-01T00:00:00Z")
        d = j.to_dict()
        assert d["name"] == "J"
        assert d["source"] == "openalex"
        assert d["last_verified_at"] == "2026-01-01T00:00:00Z"
        assert "open_access" in d

    def test_journal_fit_score_to_dict(self):
        from services.publishing.models import JournalFitScore, JournalProfile
        fs = JournalFitScore(
            journal=JournalProfile(name="Test", publisher="P"),
            scope_match=0.8, overall_fit=0.65,
        )
        d = fs.to_dict()
        assert d["scope_match"] == 0.8
        assert "journal" in d
        assert d["overall_fit"] == 0.65
        assert "acceptance_probability" not in d  # Phase 0: no invented figure
        assert "desk_rejection_risk" not in d

    def test_smart_journal_match_to_dict(self):
        from services.publishing.models import MatchType, SmartJournalMatch
        m = SmartJournalMatch(match_type=MatchType.BEST, label="Best Overall")
        d = m.to_dict()
        assert d["match_type"] == "best_match"
        assert d["label"] == "Best Overall"

    def test_conference_fit_to_dict(self):
        from services.publishing.models import ConferenceFit
        c = ConferenceFit(name="ICML", acronym="ICML", ranking="A*")
        d = c.to_dict()
        assert d["name"] == "ICML"
        assert d["ranking"] == "A*"

    def test_grant_fit_to_dict(self):
        from services.publishing.models import GrantFit
        g = GrantFit(title="ERC Grant", funder="ERC", amount_usd=1_500_000)
        d = g.to_dict()
        assert d["title"] == "ERC Grant"
        assert d["amount_usd"] == 1_500_000

    def test_readiness_check_to_dict(self):
        from services.publishing.models import ReadinessCheck
        c = ReadinessCheck("Abstract", "formatting", True, "minor", "OK", "")
        d = c.to_dict()
        assert d["passed"] is True
        assert d["criterion"] == "Abstract"

    def test_submission_readiness_to_dict(self):
        from services.publishing.models import ReadinessLevel, SubmissionReadiness
        r = SubmissionReadiness(
            level=ReadinessLevel.READY,
            overall_score=88.0,
            grade="A",
            passed_checks=14,
            total_checks=15,
        )
        d = r.to_dict()
        assert d["level"] == "ready"
        assert d["grade"] == "A"

    def test_cover_letter_to_dict(self):
        from services.publishing.models import CoverLetter
        cl = CoverLetter(journal="Nature", manuscript_title="AI Study", text="Dear Editor...")
        d = cl.to_dict()
        assert d["journal"] == "Nature"
        assert d["text"] == "Dear Editor..."

    def test_reviewer_response_to_dict(self):
        from services.publishing.models import RevisionType, ReviewerResponse
        r = ReviewerResponse(
            revision_type=RevisionType.MAJOR,
            manuscript_title="Test Paper",
            journal="PLOS ONE",
        )
        d = r.to_dict()
        assert d["revision_type"] == "major_revision"
        assert d["manuscript_title"] == "Test Paper"

    def test_publication_strategy_to_dict(self):
        from services.publishing.models import PublicationStrategy
        s = PublicationStrategy(manuscript_title="My Paper")
        d = s.to_dict()
        assert d["manuscript_title"] == "My Paper"
        assert isinstance(d["options"], list)

    def test_risk_dimension_to_dict(self):
        from services.publishing.models import RiskDimension, RiskLevel
        d = RiskDimension("Desk Rejection", RiskLevel.HIGH, 0.65)
        dd = d.to_dict()
        assert dd["level"] == "high"
        assert dd["score"] == 0.65

    def test_publication_risk_to_dict(self):
        from services.publishing.models import PublicationRisk, RiskLevel
        r = PublicationRisk(
            overall_risk_score=0.45,
            overall_risk_level=RiskLevel.MODERATE,
        )
        d = r.to_dict()
        assert d["overall_risk_level"] == "moderate"

    def test_publication_dashboard_to_dict(self):
        from services.publishing.models import PublicationDashboard
        db = PublicationDashboard(user_id="u1", total_manuscripts=5, published_count=2)
        d = db.to_dict()
        assert d["user_id"] == "u1"
        assert d["total_manuscripts"] == 5

    def test_score_to_grade_thresholds(self):
        from services.publishing.models import _score_to_grade
        assert _score_to_grade(95) == "A+"
        assert _score_to_grade(88) == "A"
        assert _score_to_grade(83) == "A-"
        assert _score_to_grade(73) == "B"
        assert _score_to_grade(58) == "C"
        assert _score_to_grade(30) == "F"

    def test_match_type_values(self):
        from services.publishing.models import MatchType
        assert MatchType.BEST.value == "best_match"
        assert MatchType.SAFE.value == "safe_match"
        assert MatchType.HIGH_IMPACT.value == "high_impact_match"
        assert MatchType.FAST_PUB.value == "fast_publication_match"
        assert MatchType.OPEN_ACCESS.value == "open_access_match"
        assert MatchType.BUDGET_FRIENDLY.value == "budget_friendly_match"

    def test_revision_type_values(self):
        from services.publishing.models import RevisionType
        assert RevisionType.MAJOR.value == "major_revision"
        assert RevisionType.MINOR.value == "minor_revision"
        assert RevisionType.REJECT_RESUBMIT.value == "reject_and_resubmit"

    def test_readiness_level_values(self):
        from services.publishing.models import ReadinessLevel
        assert ReadinessLevel.READY.value == "ready"
        assert ReadinessLevel.NOT_READY.value == "not_ready"

    def test_export_format_values(self):
        from services.publishing.models import ExportFormat
        assert ExportFormat.COVER_LETTER.value == "cover_letter"
        assert ExportFormat.JOURNAL_COMPARISON.value == "journal_comparison"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Journal Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

import datetime as _dt

from db import get_db
from repo.security_context import SecurityContext
from repo.shim import DBProxy


def _test_db():
    return DBProxy(get_db(), SecurityContext.system())


_FUTURE = (_dt.date.today() + _dt.timedelta(days=180)).isoformat()
_PAST = (_dt.date.today() - _dt.timedelta(days=30)).isoformat()

_REAL_JOURNALS = [
    {"title": "Nature Machine Intelligence", "publisher": "Springer Nature", "quartile": "Q1",
     "quartile_source": "openalex_estimate", "h_index": 120, "works_count": 900, "cited_by_count": 40000,
     "open_access": False, "apc_usd": 9500, "subjects": ["Artificial Intelligence", "Machine Learning"],
     "research_areas": ["computer science"], "scope_keywords": ["deep learning", "neural network"],
     "source": "openalex", "last_seen_source_at": "2026-01-01T00:00:00Z"},
    {"title": "PLOS ONE", "publisher": "PLOS", "quartile": "Q2", "quartile_source": "openalex_estimate",
     "h_index": 300, "works_count": 5000, "cited_by_count": 20000, "open_access": True, "apc_usd": 1895,
     "subjects": ["Multidisciplinary"], "research_areas": ["science"], "scope_keywords": ["open science"],
     "source": "openalex", "last_seen_source_at": "2026-01-01T00:00:00Z"},
]
# A record with no real signals at all — must never be dropped into the
# result set with an invented acceptance rate or impact factor.
_SPARSE_JOURNAL = {
    "title": "Journal Of Minimal Data", "publisher": "", "subjects": ["Artificial Intelligence"],
    "source": "openalex", "last_seen_source_at": "2026-01-01T00:00:00Z",
}
_SEED_JOURNAL = {
    "title": "Fabricated Impact Journal", "publisher": "Test", "quartile": "Q1",
    "impact_factor": 999.9, "acceptance_rate": 5, "subjects": ["Artificial Intelligence"],
    "is_seed": True, "source": "seed",
}

_REAL_CONFERENCES = [
    {"name": "International Conference on Machine Learning", "acronym": "ICML", "organizer": "PMLR",
     "rank": "A*", "research_areas": ["Artificial Intelligence"], "topics": ["machine learning", "deep learning"],
     "submission_deadline": _FUTURE, "location": "International", "source": "wikicfp"},
    {"name": "Expired AI Symposium", "acronym": "EAS", "research_areas": ["Artificial Intelligence"],
     "topics": ["machine learning"], "submission_deadline": _PAST, "source": "wikicfp"},
]
_SEED_CONFERENCE = {
    "name": "Fabricated AI Summit", "acronym": "FAS", "rank": "A*", "research_areas": ["Artificial Intelligence"],
    "topics": ["machine learning"], "submission_deadline": _FUTURE, "is_seed": True, "source": "seed",
}

_REAL_GRANTS = [
    {"title": "NIH R01 Machine Learning in Medicine", "sponsor": "NIH", "research_areas": ["Artificial Intelligence", "medicine"],
     "keywords": ["machine learning", "clinical"], "deadline": _FUTURE,
     "funding_amount": {"currency": "USD", "amount": 500000}, "eligibility": "US institutions per NIH announcement.",
     "source": "nih", "url": "https://reporter.nih.gov/example"},
    {"title": "Expired AI Grant", "sponsor": "NSF", "research_areas": ["Artificial Intelligence"],
     "keywords": ["machine learning"], "deadline": _PAST, "source": "nih"},
]
_SEED_GRANT = {
    "title": "Fabricated Mega Grant", "sponsor": "Test Foundation", "research_areas": ["Artificial Intelligence"],
    "keywords": ["machine learning"], "deadline": _FUTURE, "funding_amount": {"currency": "USD", "amount": 99000000},
    "is_seed": True, "source": "seed",
}


async def _seeded_db(journals=None, conferences=None, grants=None):
    """Insert fixture records into the real test-DB collections and return a
    DBProxy plus the inserted ids for cleanup."""
    db = _test_db()
    ids = {"journals": [], "conferences": [], "grants": []}
    if journals:
        res = await db.journals.insert_many(journals)
        ids["journals"] = list(res.inserted_ids)
    if conferences:
        res = await db.conferences.insert_many(conferences)
        ids["conferences"] = list(res.inserted_ids)
    if grants:
        res = await db.grants.insert_many(grants)
        ids["grants"] = list(res.inserted_ids)
    return db, ids


async def _cleanup(db, ids):
    if ids["journals"]:
        await db.journals.delete_many({"_id": {"$in": ids["journals"]}})
    if ids["conferences"]:
        await db.conferences.delete_many({"_id": {"$in": ids["conferences"]}})
    if ids["grants"]:
        await db.grants.delete_many({"_id": {"$in": ids["grants"]}})


class TestJournalAnalyzer:
    """Phase 0: real-DB-backed, no invented acceptance/desk-rejection figures."""

    async def test_returns_fits_from_real_records_only(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        db, ids = await _seeded_db(journals=_REAL_JOURNALS + [_SEED_JOURNAL])
        try:
            fits = await analyze_journal_fit(_ML_TEXT, "artificial intelligence", 80, db=db)
            names = {f.journal.name for f in fits}
            assert "Nature Machine Intelligence" in names
            # The fabricated seed record must never appear in results.
            assert "Fabricated Impact Journal" not in names
        finally:
            await _cleanup(db, ids)

    async def test_no_journal_carries_an_impact_factor_field(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            fits = await analyze_journal_fit(_ML_TEXT, "artificial intelligence", 80, db=db)
            for f in fits:
                d = f.journal.to_dict()
                assert "impact_factor" not in d  # no legitimate free source publishes JIF

        finally:
            await _cleanup(db, ids)

    async def test_sparse_journal_reports_data_unavailable_not_a_fabricated_default(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        db, ids = await _seeded_db(journals=[_SPARSE_JOURNAL])
        try:
            fits = await analyze_journal_fit(_ML_TEXT, "artificial intelligence", 80, db=db)
            assert len(fits) == 1
            f = fits[0]
            assert f.journal.acceptance_rate is None
            assert any("not available" in n.lower() or "no " in n.lower() for n in f.notes)
        finally:
            await _cleanup(db, ids)

    async def test_scope_match_between_0_and_1(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            fits = await analyze_journal_fit(_ML_TEXT, "artificial intelligence", 70, db=db)
            for f in fits:
                assert 0.0 <= f.scope_match <= 1.0
        finally:
            await _cleanup(db, ids)

    async def test_fits_sorted_by_overall_fit(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            fits = await analyze_journal_fit(_ML_TEXT, "artificial intelligence", 75, db=db)
            if len(fits) > 1:
                assert fits[0].overall_fit >= fits[1].overall_fit
        finally:
            await _cleanup(db, ids)

    async def test_get_all_profiles_excludes_seed(self):
        from services.publishing.journal_analyzer import get_all_profiles
        db, ids = await _seeded_db(journals=_REAL_JOURNALS + [_SEED_JOURNAL])
        try:
            profiles = await get_all_profiles(db=db)
            names = {p.name for p in profiles}
            assert "Fabricated Impact Journal" not in names
        finally:
            await _cleanup(db, ids)

    async def test_fit_score_has_rationale(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            fits = await analyze_journal_fit(_ML_TEXT, "artificial intelligence", 80, db=db)
            if fits:
                assert len(fits[0].rationale) > 10
        finally:
            await _cleanup(db, ids)


class TestJournalMatcher:
    async def test_returns_all_six_match_types(self):
        from services.publishing.journal_matcher import match_journals
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            results = await match_journals(_ML_TEXT, "artificial intelligence", 75, db=db)
            assert len(results) == 6
        finally:
            await _cleanup(db, ids)

    async def test_open_access_match_only_oa_journals(self):
        from services.publishing.models import MatchType
        from services.publishing.journal_matcher import match_journals
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            results = await match_journals(_ML_TEXT, "artificial intelligence", 75, [MatchType.OPEN_ACCESS], db=db)
            for fit in results[0].fits:
                assert fit.journal.open_access is True
        finally:
            await _cleanup(db, ids)

    async def test_safe_match_only_journals_with_published_acceptance_rate(self):
        from services.publishing.models import MatchType
        from services.publishing.journal_matcher import match_journals
        db, ids = await _seeded_db(journals=_REAL_JOURNALS + [_SPARSE_JOURNAL])
        try:
            results = await match_journals(_ML_TEXT, "artificial intelligence", 75, [MatchType.SAFE], db=db)
            for fit in results[0].fits:
                assert fit.journal.acceptance_rate is not None
        finally:
            await _cleanup(db, ids)

    async def test_fast_pub_returns_empty_no_source_has_review_time_data(self):
        from services.publishing.models import MatchType
        from services.publishing.journal_matcher import match_journals
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            results = await match_journals(_ML_TEXT, "artificial intelligence", 75, [MatchType.FAST_PUB], db=db)
            assert results[0].fits == []
        finally:
            await _cleanup(db, ids)

    async def test_budget_friendly_max_1000_apc(self):
        from services.publishing.models import MatchType
        from services.publishing.journal_matcher import match_journals
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            results = await match_journals(_ML_TEXT, "artificial intelligence", 75, [MatchType.BUDGET_FRIENDLY], db=db)
            for fit in results[0].fits:
                assert fit.journal.apc_usd is not None and fit.journal.apc_usd <= 1000
        finally:
            await _cleanup(db, ids)

    async def test_match_types_accept_strings(self):
        from services.publishing.journal_matcher import match_journals
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            results = await match_journals(_ML_TEXT, "artificial intelligence", 75, ["best_match", "safe_match"], db=db)
            assert len(results) == 2
        finally:
            await _cleanup(db, ids)


class TestConferenceAnalyzer:
    """Phase 0: real-DB-backed, expired deadlines excluded, seed excluded."""

    async def test_returns_real_conferences_only(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        db, ids = await _seeded_db(conferences=_REAL_CONFERENCES + [_SEED_CONFERENCE])
        try:
            fits = await analyze_conference_fit(_ML_TEXT, "artificial intelligence", 80, db=db)
            names = {f.name for f in fits}
            assert "International Conference on Machine Learning" in names
            assert "Fabricated AI Summit" not in names  # seed — never shown
        finally:
            await _cleanup(db, ids)

    async def test_expired_deadline_excluded(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        db, ids = await _seeded_db(conferences=_REAL_CONFERENCES)
        try:
            fits = await analyze_conference_fit(_ML_TEXT, "artificial intelligence", 80, db=db)
            names = {f.name for f in fits}
            assert "Expired AI Symposium" not in names
        finally:
            await _cleanup(db, ids)

    async def test_no_acceptance_rate_or_networking_value_fields(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        db, ids = await _seeded_db(conferences=_REAL_CONFERENCES)
        try:
            fits = await analyze_conference_fit(_ML_TEXT, "artificial intelligence", 75, db=db)
            for f in fits:
                d = f.to_dict()
                assert "acceptance_rate" not in d
                assert "networking_value" not in d
                assert "registration_fee_usd" not in d
        finally:
            await _cleanup(db, ids)

    async def test_research_fit_in_range(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        db, ids = await _seeded_db(conferences=_REAL_CONFERENCES)
        try:
            fits = await analyze_conference_fit(_ML_TEXT, "artificial intelligence", 75, db=db)
            for f in fits:
                assert 0.0 <= f.research_fit <= 1.0
        finally:
            await _cleanup(db, ids)


class TestGrantAnalyzer:
    """Phase 0: real-DB-backed, no invented funding-probability/eligibility score."""

    async def test_returns_real_grants_only(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        db, ids = await _seeded_db(grants=_REAL_GRANTS + [_SEED_GRANT])
        try:
            fits = await analyze_grant_fit(_ML_TEXT, "artificial intelligence", 75, db=db)
            titles = {f.title for f in fits}
            assert "NIH R01 Machine Learning in Medicine" in titles
            assert "Fabricated Mega Grant" not in titles
        finally:
            await _cleanup(db, ids)

    async def test_expired_deadline_excluded(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        db, ids = await _seeded_db(grants=_REAL_GRANTS)
        try:
            fits = await analyze_grant_fit(_ML_TEXT, "artificial intelligence", 75, db=db)
            titles = {f.title for f in fits}
            assert "Expired AI Grant" not in titles
        finally:
            await _cleanup(db, ids)

    async def test_topic_fit_in_range(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        db, ids = await _seeded_db(grants=_REAL_GRANTS)
        try:
            fits = await analyze_grant_fit(_ML_TEXT, "artificial intelligence", 75, db=db)
            for f in fits:
                assert 0.0 <= f.topic_fit <= 1.0
        finally:
            await _cleanup(db, ids)

    async def test_no_funding_probability_or_competitiveness_fields(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        db, ids = await _seeded_db(grants=_REAL_GRANTS)
        try:
            fits = await analyze_grant_fit(_ML_TEXT, "artificial intelligence", 75, db=db)
            for f in fits:
                d = f.to_dict()
                assert "funding_probability" not in d
                assert "competitiveness" not in d
                assert "eligibility_score" not in d
        finally:
            await _cleanup(db, ids)

    async def test_grant_fit_to_dict_has_keys(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        db, ids = await _seeded_db(grants=_REAL_GRANTS)
        try:
            fits = await analyze_grant_fit(_ML_TEXT, "artificial intelligence", 75, db=db)
            if fits:
                d = fits[0].to_dict()
                assert "title" in d and "funder" in d and "topic_fit" in d
        finally:
            await _cleanup(db, ids)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Submission Checker
# ═══════════════════════════════════════════════════════════════════════════════

class TestSubmissionChecker:
    def test_ready_manuscript_passes_most_checks(self):
        from services.publishing.submission_checker import check_submission_readiness
        result = check_submission_readiness(_ML_TEXT, {"word_count": 4000, "abstract_word_count": 180})
        assert result.passed_checks >= 10

    def test_total_checks_always_15(self):
        from services.publishing.submission_checker import check_submission_readiness
        result = check_submission_readiness(_ML_TEXT)
        assert result.total_checks == 15

    def test_no_abstract_triggers_major_issue(self):
        from services.publishing.submission_checker import check_submission_readiness
        bare_text = "We study machine learning. Methods: SVM. Results: 85% accuracy. Discussion: good."
        result = check_submission_readiness(bare_text)
        assert any("abstract" in c.criterion.lower() and not c.passed for c in result.checks)

    def test_missing_ethics_is_critical_blocker(self):
        from services.publishing.submission_checker import check_submission_readiness
        text_with_participants = (
            "We recruited 100 participants. Methods: surveys. Results: significant effects. "
            "Introduction: psychology study. Discussion: implications. Conclusion: done. "
            "References: (A, 2020); (B, 2021); (C, 2022). Keywords: psychology. "
        )
        result = check_submission_readiness(text_with_participants)
        ethics_check = next((c for c in result.checks if "ethics" in c.criterion.lower()), None)
        if ethics_check and not ethics_check.passed:
            assert ethics_check.severity == "critical"

    def test_full_manuscript_level_ready_or_minor(self):
        from services.publishing.models import ReadinessLevel
        from services.publishing.submission_checker import check_submission_readiness
        result = check_submission_readiness(_ML_TEXT, {"word_count": 5000, "abstract_word_count": 200})
        assert result.level in (ReadinessLevel.READY, ReadinessLevel.MINOR_ISSUES)

    def test_overall_score_in_range(self):
        from services.publishing.submission_checker import check_submission_readiness
        result = check_submission_readiness(_ML_TEXT)
        assert 0 <= result.overall_score <= 100

    def test_grade_assigned(self):
        from services.publishing.submission_checker import check_submission_readiness
        result = check_submission_readiness(_ML_TEXT)
        assert result.grade in ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F")

    def test_checklist_length_equals_total_checks(self):
        from services.publishing.submission_checker import check_submission_readiness
        result = check_submission_readiness(_ML_TEXT)
        assert len(result.submission_checklist) == result.total_checks

    def test_estimated_revision_days_is_nonnegative(self):
        from services.publishing.submission_checker import check_submission_readiness
        result = check_submission_readiness(_ML_TEXT)
        assert result.estimated_revision_days >= 0

    def test_word_count_check_triggers_on_short_text(self):
        from services.publishing.submission_checker import check_submission_readiness
        short_text = "A study of X. Methods: SVM. Results: ok. " * 20
        result = check_submission_readiness(short_text, {"word_count": 150, "journal_min_words": 3000})
        wc_check = next((c for c in result.checks if "word" in c.criterion.lower()), None)
        if wc_check:
            assert not wc_check.passed


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Cover Letter Generator
# ═══════════════════════════════════════════════════════════════════════════════

class TestCoverLetterGenerator:
    def test_generates_cover_letter(self):
        from services.publishing.cover_letter_generator import generate_cover_letter
        letter = asyncio.run(
            generate_cover_letter("Deep Learning for NLP", "Nature Machine Intelligence")
        )
        assert len(letter.text) > 100

    def test_cover_letter_contains_journal(self):
        from services.publishing.cover_letter_generator import generate_cover_letter
        letter = asyncio.run(
            generate_cover_letter("AI Study", "PLOS ONE")
        )
        assert "PLOS ONE" in letter.text

    def test_cover_letter_word_count(self):
        from services.publishing.cover_letter_generator import generate_cover_letter
        letter = asyncio.run(
            generate_cover_letter("AI Study", "IEEE TNN")
        )
        assert letter.word_count > 50

    def test_cover_letter_has_sections(self):
        from services.publishing.cover_letter_generator import generate_cover_letter
        letter = asyncio.run(
            generate_cover_letter("Test", "Test Journal")
        )
        assert len(letter.sections) > 0

    def test_cover_letter_has_letter_id(self):
        from services.publishing.cover_letter_generator import generate_cover_letter
        letter = asyncio.run(
            generate_cover_letter("Test", "Journal")
        )
        assert letter.letter_id is not None

    def test_cover_letter_custom_metadata(self):
        from services.publishing.cover_letter_generator import generate_cover_letter
        letter = asyncio.run(
            generate_cover_letter(
                "AI Study", "Nature",
                {"corresponding_author": "Dr. Jane Smith", "editor_title": "Editor-in-Chief"}
            )
        )
        assert "Dr. Jane Smith" in letter.text

    def test_cover_letter_to_dict(self):
        from services.publishing.cover_letter_generator import generate_cover_letter
        letter = asyncio.run(
            generate_cover_letter("AI Study", "Nature")
        )
        d = letter.to_dict()
        assert "text" in d and "journal" in d and "word_count" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Reviewer Response Generator
# ═══════════════════════════════════════════════════════════════════════════════

class TestReviewerResponseGenerator:
    _COMMENTS = [
        {"reviewer_id": "Reviewer 1", "comment": "The sample size seems too small for the conclusions drawn."},
        {"reviewer_id": "Reviewer 1", "comment": "The literature review is missing key papers from 2022–2023."},
        {"reviewer_id": "Reviewer 2", "comment": "The methodology section lacks detail on the statistical analysis."},
        {"reviewer_id": "Reviewer 2", "comment": "Figure 3 is unclear and difficult to interpret."},
    ]

    def test_generates_response(self):
        from services.publishing.reviewer_response_generator import generate_reviewer_response
        from services.publishing.models import RevisionType
        resp = generate_reviewer_response(
            RevisionType.MAJOR, "AI Study", "PLOS ONE", self._COMMENTS
        )
        assert len(resp.full_text) > 200

    def test_comment_count_matches_input(self):
        from services.publishing.reviewer_response_generator import generate_reviewer_response
        from services.publishing.models import RevisionType
        resp = generate_reviewer_response(
            RevisionType.MAJOR, "AI Study", "PLOS ONE", self._COMMENTS
        )
        assert len(resp.comments) == len(self._COMMENTS)

    def test_cover_letter_in_response(self):
        from services.publishing.reviewer_response_generator import generate_reviewer_response
        from services.publishing.models import RevisionType
        resp = generate_reviewer_response(
            RevisionType.MINOR, "AI Study", "Nature", self._COMMENTS[:2]
        )
        assert len(resp.cover_letter) > 50

    def test_response_has_general_intro(self):
        from services.publishing.reviewer_response_generator import generate_reviewer_response
        from services.publishing.models import RevisionType
        resp = generate_reviewer_response(
            RevisionType.MAJOR, "Test", "Journal", self._COMMENTS[:1]
        )
        assert len(resp.general_response) > 20

    def test_reject_resubmit_type(self):
        from services.publishing.reviewer_response_generator import generate_reviewer_response
        from services.publishing.models import RevisionType
        resp = generate_reviewer_response(
            RevisionType.REJECT_RESUBMIT, "Test Paper", "Lancet", self._COMMENTS[:2]
        )
        assert resp.revision_type == RevisionType.REJECT_RESUBMIT

    def test_to_dict_has_comments(self):
        from services.publishing.reviewer_response_generator import generate_reviewer_response
        from services.publishing.models import RevisionType
        resp = generate_reviewer_response(
            RevisionType.MAJOR, "Test", "Journal", self._COMMENTS[:2]
        )
        d = resp.to_dict()
        assert isinstance(d["comments"], list)
        assert d["revision_type"] == "major_revision"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Strategy Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestStrategyBuilder:
    async def test_builds_strategy(self):
        from services.publishing.strategy_builder import build_publication_strategy
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            strategy = await build_publication_strategy("AI Paper", _ML_TEXT, "artificial intelligence", 75, db=db)
            assert len(strategy.options) >= 3
        finally:
            await _cleanup(db, ids)

    async def test_recommended_option_is_set(self):
        from services.publishing.strategy_builder import build_publication_strategy
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            strategy = await build_publication_strategy("AI Paper", _ML_TEXT, "artificial intelligence", 75, db=db)
            assert strategy.recommended_option is not None
        finally:
            await _cleanup(db, ids)

    async def test_no_option_claims_an_unsupported_success_probability(self):
        # Phase 0: strategic options no longer assert a fabricated numeric
        # outcome probability — see AUDIT_PHASE0.md.
        from services.publishing.strategy_builder import build_publication_strategy
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            strategy = await build_publication_strategy("AI Paper", _ML_TEXT, "artificial intelligence", 75, db=db)
            for opt in strategy.options:
                assert opt.success_probability is None
        finally:
            await _cleanup(db, ids)

    async def test_options_have_steps(self):
        from services.publishing.strategy_builder import build_publication_strategy
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            strategy = await build_publication_strategy("AI Paper", _ML_TEXT, "artificial intelligence", 75, db=db)
            for opt in strategy.options:
                assert len(opt.steps) > 0
        finally:
            await _cleanup(db, ids)

    async def test_strategy_to_dict(self):
        from services.publishing.strategy_builder import build_publication_strategy
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            strategy = await build_publication_strategy("AI Paper", _ML_TEXT, "artificial intelligence", 75, db=db)
            d = strategy.to_dict()
            assert "options" in d and "recommended_option" in d
        finally:
            await _cleanup(db, ids)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Risk Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskAnalyzer:
    """Phase 0: 5 manuscript-content dimensions only — desk-rejection, delay,
    and predatory-journal dimensions were removed because they depended on
    fabricated per-journal figures (acceptance rate, review weeks, predatory
    score) with hardcoded defaults. See AUDIT_PHASE0.md."""

    def test_returns_five_dimensions(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75)
        assert len(risk.dimensions) == 5
        names = {d.dimension for d in risk.dimensions}
        assert "Desk Rejection" not in names
        assert "Publication Delay" not in names
        assert "Predatory Journal Risk" not in names

    def test_overall_risk_in_range(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75)
        assert 0.0 <= risk.overall_risk_score <= 1.0

    def test_no_fabricated_success_probability(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75)
        assert risk.estimated_success_probability is None

    def test_top_risks_non_empty(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75)
        assert len(risk.top_risks) > 0

    def test_to_dict_has_dimensions(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75)
        d = risk.to_dict()
        assert isinstance(d["dimensions"], list)
        assert len(d["dimensions"]) == 5
        assert d["estimated_success_probability"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Export Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestExportEngine:
    def _make_letter(self):
        from services.publishing.models import CoverLetter
        return CoverLetter(journal="Nature", manuscript_title="AI Study", text="Dear Editor,\n\nTest.\n\nYours,\nAuthor")

    async def _make_strategy(self, db):
        from services.publishing.strategy_builder import build_publication_strategy
        return await build_publication_strategy("AI Paper", _ML_TEXT, "artificial intelligence", 75, db=db)

    def test_export_cover_letter_markdown(self):
        from services.publishing.export_engine import export
        from services.publishing.models import ExportFormat
        result = export(ExportFormat.COVER_LETTER, ExportFormat.MARKDOWN, {"cover_letter": self._make_letter()})
        assert "Dear Editor" in result

    def test_export_cover_letter_latex(self):
        from services.publishing.export_engine import export
        from services.publishing.models import ExportFormat
        result = export(ExportFormat.COVER_LETTER, ExportFormat.LATEX, {"cover_letter": self._make_letter()})
        assert "\\documentclass" in result

    async def test_export_roadmap_markdown(self):
        from services.publishing.export_engine import export
        from services.publishing.models import ExportFormat
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            strategy = await self._make_strategy(db)
            result = export(ExportFormat.PUBLICATION_ROADMAP, ExportFormat.MARKDOWN, {"strategy": strategy})
            assert "# Publication Roadmap" in result
        finally:
            await _cleanup(db, ids)

    async def test_export_roadmap_latex(self):
        from services.publishing.export_engine import export
        from services.publishing.models import ExportFormat
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            strategy = await self._make_strategy(db)
            result = export(ExportFormat.PUBLICATION_ROADMAP, ExportFormat.LATEX, {"strategy": strategy})
            assert "\\documentclass" in result
        finally:
            await _cleanup(db, ids)

    async def test_export_journal_comparison(self):
        from services.publishing.export_engine import export
        from services.publishing.journal_matcher import match_journals
        from services.publishing.models import ExportFormat
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            matches = await match_journals(_ML_TEXT, "artificial intelligence", 75, db=db)
            result = export(ExportFormat.JOURNAL_COMPARISON, ExportFormat.MARKDOWN, {"matches": matches})
            assert "Journal" in result
        finally:
            await _cleanup(db, ids)

    async def test_export_grant_readiness(self):
        from services.publishing.export_engine import export
        from services.publishing.grant_analyzer import analyze_grant_fit
        from services.publishing.models import ExportFormat
        db, ids = await _seeded_db(grants=_REAL_GRANTS)
        try:
            grants = await analyze_grant_fit(_ML_TEXT, "artificial intelligence", 75, db=db)
            result = export(ExportFormat.GRANT_READINESS, ExportFormat.MARKDOWN, {"grants": grants})
            assert "Grant" in result
        finally:
            await _cleanup(db, ids)

    def test_export_submission_package(self):
        from services.publishing.export_engine import export
        from services.publishing.models import ExportFormat
        from services.publishing.submission_checker import check_submission_readiness
        readiness = check_submission_readiness(_ML_TEXT)
        result = export(ExportFormat.SUBMISSION_PACKAGE, ExportFormat.MARKDOWN,
                        {"readiness": readiness, "cover_letter": self._make_letter()})
        assert "Submission Package" in result

    def test_export_no_payload_returns_message(self):
        from services.publishing.export_engine import export
        from services.publishing.models import ExportFormat
        result = export(ExportFormat.COVER_LETTER, ExportFormat.MARKDOWN, {})
        assert "No cover letter" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def _fresh(self):
        from services.publishing.telemetry import PublishingTelemetry
        PublishingTelemetry._instance = None
        from services.publishing.telemetry import get_telemetry
        return get_telemetry()

    def test_singleton(self):
        t1 = self._fresh()
        from services.publishing.telemetry import get_telemetry
        t2 = get_telemetry()
        assert t1 is t2

    def test_journal_analysis_increments(self):
        t = self._fresh()
        t.record_journal_analysis()
        assert t.snapshot()["journal_analyses"] == 1

    def test_journal_match_increments(self):
        t = self._fresh()
        t.record_journal_match()
        assert t.snapshot()["journal_matches"] == 1

    def test_cover_letter_increments(self):
        t = self._fresh()
        t.record_cover_letter()
        assert t.snapshot()["cover_letters"] == 1

    def test_error_increments(self):
        t = self._fresh()
        t.record_error()
        assert t.snapshot()["errors"] == 1

    def test_latency_tracking(self):
        t = self._fresh()
        t.record_latency(0.1)
        t.record_latency(0.5)
        s = t.snapshot()
        assert s["sample_count"] == 2
        assert s["latency_avg_s"] > 0

    def test_reset_clears_all(self):
        t = self._fresh()
        t.record_journal_analysis()
        t.record_error()
        t.reset()
        s = t.snapshot()
        assert s["journal_analyses"] == 0
        assert s["errors"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Engine integration
# ═══════════════════════════════════════════════════════════════════════════════

async def _make_engine():
    from services.publishing.engine import reset_publishing_engine, get_publishing_engine
    reset_publishing_engine()
    return await get_publishing_engine()


class TestPublishingEngine:
    def test_singleton(self):
        async def _run():
            from services.publishing.engine import reset_publishing_engine, get_publishing_engine
            reset_publishing_engine()
            e1 = await get_publishing_engine()
            e2 = await get_publishing_engine()
            assert e1 is e2
        asyncio.run(_run())

    async def test_analyse_journal_returns_list(self):
        # engine methods use the process-default DB connection (db=None
        # inside journal_analyzer.py), which is the same live test DB
        # _seeded_db() writes to — so seeding here is visible to the engine.
        e = await _make_engine()
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            result = await e.analyse_journal(_ML_TEXT, "artificial intelligence", 75)
            assert isinstance(result, list)
            assert len(result) > 0
            assert "impact_factor" not in result[0]["journal"]
        finally:
            await _cleanup(db, ids)

    async def test_match_journal_returns_six_strategies(self):
        e = await _make_engine()
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            result = await e.match_journal(_ML_TEXT, "artificial intelligence", 75)
            assert isinstance(result, list)
            assert len(result) == 6
        finally:
            await _cleanup(db, ids)

    async def test_match_conference_returns_list(self):
        e = await _make_engine()
        db, ids = await _seeded_db(conferences=_REAL_CONFERENCES)
        try:
            result = await e.match_conference(_ML_TEXT, "artificial intelligence", 75)
            assert isinstance(result, list)
        finally:
            await _cleanup(db, ids)

    async def test_match_grant_returns_list(self):
        e = await _make_engine()
        db, ids = await _seeded_db(grants=_REAL_GRANTS)
        try:
            result = await e.match_grant(_ML_TEXT, "artificial intelligence", 75)
            assert isinstance(result, list)
        finally:
            await _cleanup(db, ids)

    def test_check_readiness_returns_dict(self):
        async def _run():
            e = await _make_engine()
            result = await e.check_readiness(_ML_TEXT)
            assert isinstance(result, dict)
            assert "level" in result
        asyncio.run(_run())

    def test_generate_cover_letter_returns_dict(self):
        async def _run():
            e = await _make_engine()
            result = await e.generate_cover_letter("AI Study", "PLOS ONE")
            assert isinstance(result, dict)
            assert "text" in result
        asyncio.run(_run())

    def test_generate_reviewer_response_returns_dict(self):
        async def _run():
            e = await _make_engine()
            result = await e.generate_reviewer_response(
                "major_revision", "AI Study", "Nature",
                [{"reviewer_id": "R1", "comment": "Sample size is too small."}]
            )
            assert isinstance(result, dict)
            assert "full_text" in result
        asyncio.run(_run())

    def test_build_strategy_returns_dict(self):
        async def _run():
            e = await _make_engine()
            result = await e.build_strategy("AI Paper", _ML_TEXT, "ai", 75)
            assert isinstance(result, dict)
            assert "options" in result
        asyncio.run(_run())

    def test_analyse_risk_returns_dict(self):
        async def _run():
            e = await _make_engine()
            result = await e.analyse_risk(_ML_TEXT, 75)
            assert isinstance(result, dict)
            assert "dimensions" in result
        asyncio.run(_run())

    async def test_export_markdown(self):
        from services.publishing.strategy_builder import build_publication_strategy
        e = await _make_engine()
        db, ids = await _seeded_db(journals=_REAL_JOURNALS)
        try:
            strategy = await build_publication_strategy("AI Paper", _ML_TEXT, "artificial intelligence", 75, db=db)
            result = await e.export("publication_roadmap", "markdown", {"strategy": strategy})
            assert isinstance(result, str)
            assert len(result) > 50
        finally:
            await _cleanup(db, ids)
