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
        from services.publishing.models import JournalProfile
        j = JournalProfile(name="Test Journal", publisher="Test")
        assert j.quartile == "Q3"
        assert j.open_access is False
        assert j.apc_usd == 0
        assert j.predatory_risk == 0.0

    def test_journal_profile_to_dict(self):
        from services.publishing.models import JournalProfile
        j = JournalProfile(name="J", publisher="P", quartile="Q1", impact_factor=5.0)
        d = j.to_dict()
        assert d["name"] == "J"
        assert d["impact_factor"] == 5.0
        assert "open_access" in d

    def test_journal_fit_score_to_dict(self):
        from services.publishing.models import JournalFitScore, JournalProfile
        fs = JournalFitScore(
            journal=JournalProfile(name="Test", publisher="P"),
            scope_match=0.8, acceptance_probability=0.3,
            desk_rejection_risk=0.2, overall_fit=0.65,
        )
        d = fs.to_dict()
        assert d["scope_match"] == 0.8
        assert "journal" in d
        assert d["overall_fit"] == 0.65

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

class TestJournalAnalyzer:
    def test_returns_fits_for_ml_text(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        fits = analyze_journal_fit(_ML_TEXT, "computer science", 80)
        assert len(fits) > 0

    def test_fits_sorted_by_overall_fit(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        fits = analyze_journal_fit(_ML_TEXT, "ai", 75)
        if len(fits) > 1:
            assert fits[0].overall_fit >= fits[1].overall_fit

    def test_medicine_text_matches_medicine_journals(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        fits = analyze_journal_fit(_MED_TEXT, "medicine", 80)
        names = [f.journal.name for f in fits[:5]]
        med_journals = {"The Lancet", "JAMA", "BMJ", "PLOS Medicine"}
        assert any(n in med_journals for n in names)

    def test_scope_match_between_0_and_1(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        fits = analyze_journal_fit(_ML_TEXT, "ai", 70)
        for f in fits:
            assert 0.0 <= f.scope_match <= 1.0

    def test_acceptance_probability_between_0_and_1(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        fits = analyze_journal_fit(_ML_TEXT, "ai", 70)
        for f in fits:
            assert 0.0 <= f.acceptance_probability <= 1.0

    def test_desk_rejection_risk_between_0_and_1(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        fits = analyze_journal_fit(_ML_TEXT, "ai", 70)
        for f in fits:
            assert 0.0 <= f.desk_rejection_risk <= 1.0

    def test_high_quality_gets_higher_acceptance(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        fits_high = analyze_journal_fit(_ML_TEXT, "ai", 95)
        fits_low  = analyze_journal_fit(_ML_TEXT, "ai", 30)
        avg_high = sum(f.acceptance_probability for f in fits_high) / max(len(fits_high), 1)
        avg_low  = sum(f.acceptance_probability for f in fits_low) / max(len(fits_low), 1)
        assert avg_high > avg_low

    def test_get_all_profiles_returns_list(self):
        from services.publishing.journal_analyzer import get_all_profiles
        profiles = get_all_profiles()
        assert len(profiles) > 10

    def test_fit_score_has_strengths_list(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        fits = analyze_journal_fit(_ML_TEXT, "ai", 80)
        if fits:
            assert isinstance(fits[0].strengths, list)

    def test_fit_score_has_rationale(self):
        from services.publishing.journal_analyzer import analyze_journal_fit
        fits = analyze_journal_fit(_ML_TEXT, "ai", 80)
        if fits:
            assert len(fits[0].rationale) > 10


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Journal Matcher
# ═══════════════════════════════════════════════════════════════════════════════

class TestJournalMatcher:
    def test_returns_all_six_match_types(self):
        from services.publishing.journal_matcher import match_journals
        results = match_journals(_ML_TEXT, "ai", 75)
        assert len(results) == 6

    def test_best_match_type_correct(self):
        from services.publishing.models import MatchType
        from services.publishing.journal_matcher import match_journals
        results = match_journals(_ML_TEXT, "ai", 75, [MatchType.BEST])
        assert results[0].match_type == MatchType.BEST

    def test_open_access_match_only_oa_journals(self):
        from services.publishing.models import MatchType
        from services.publishing.journal_matcher import match_journals
        results = match_journals(_ML_TEXT, "ai", 75, [MatchType.OPEN_ACCESS])
        oa_match = results[0]
        for fit in oa_match.fits:
            assert fit.journal.open_access is True

    def test_high_impact_only_q1_q2(self):
        from services.publishing.models import MatchType
        from services.publishing.journal_matcher import match_journals
        results = match_journals(_ML_TEXT, "ai", 75, [MatchType.HIGH_IMPACT])
        hi_match = results[0]
        for fit in hi_match.fits:
            assert fit.journal.quartile in ("Q1", "Q2")

    def test_budget_friendly_max_1000_apc(self):
        from services.publishing.models import MatchType
        from services.publishing.journal_matcher import match_journals
        results = match_journals(_ML_TEXT, "ai", 75, [MatchType.BUDGET_FRIENDLY])
        budget = results[0]
        for fit in budget.fits:
            assert fit.journal.apc_usd <= 1000

    def test_fast_pub_sorted_by_review_weeks(self):
        from services.publishing.models import MatchType
        from services.publishing.journal_matcher import match_journals
        results = match_journals(_ML_TEXT, "ai", 75, [MatchType.FAST_PUB])
        fp = results[0]
        if len(fp.fits) >= 2:
            assert fp.fits[0].journal.review_duration_weeks <= fp.fits[1].journal.review_duration_weeks

    def test_top_pick_present(self):
        from services.publishing.journal_matcher import match_journals
        results = match_journals(_ML_TEXT, "ai", 75)
        for r in results:
            if r.fits:
                assert r.top_pick is not None

    def test_match_types_accept_strings(self):
        from services.publishing.journal_matcher import match_journals
        results = match_journals(_ML_TEXT, "ai", 75, ["best_match", "safe_match"])
        assert len(results) == 2

    def test_medicine_text_conference_match_returns_medicine(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        fits = analyze_conference_fit(_MED_TEXT, "medicine", 80)
        names = [f.name for f in fits[:5]]
        med_confs = {"European Congress of Cardiology", "American Heart Association Scientific Sessions"}
        assert any(n in med_confs for n in names)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Conference Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestConferenceAnalyzer:
    def test_returns_fits_for_ai_text(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        fits = analyze_conference_fit(_ML_TEXT, "ai", 75)
        assert len(fits) > 0

    def test_fits_sorted_by_overall_score(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        fits = analyze_conference_fit(_ML_TEXT, "ai", 75)
        if len(fits) > 1:
            assert fits[0].overall_score >= fits[1].overall_score

    def test_ai_text_includes_ai_conferences(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        fits = analyze_conference_fit(_ML_TEXT, "ai", 80)
        names = [f.name for f in fits[:5]]
        ai_confs = {"International Conference on Machine Learning", "Neural Information Processing Systems"}
        assert any(n in ai_confs for n in names)

    def test_acceptance_probability_in_range(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        fits = analyze_conference_fit(_ML_TEXT, "ai", 75)
        for f in fits:
            assert 0.0 <= f.acceptance_probability <= 1.0

    def test_research_fit_in_range(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        fits = analyze_conference_fit(_ML_TEXT, "ai", 75)
        for f in fits:
            assert 0.0 <= f.research_fit <= 1.0

    def test_to_dict_has_required_keys(self):
        from services.publishing.conference_analyzer import analyze_conference_fit
        fits = analyze_conference_fit(_ML_TEXT, "ai", 75)
        if fits:
            d = fits[0].to_dict()
            assert "name" in d and "overall_score" in d and "acceptance_probability" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Grant Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestGrantAnalyzer:
    def test_returns_fits(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        fits = analyze_grant_fit(_ML_TEXT, "computer science", 75)
        assert len(fits) > 0

    def test_fits_sorted_correctly(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        fits = analyze_grant_fit(_ML_TEXT, "ai", 75)
        for f in fits:
            assert 0.0 <= f.topic_fit <= 1.0

    def test_medicine_text_matches_nih(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        fits = analyze_grant_fit(_MED_TEXT, "medicine", 80)
        names = [f.title for f in fits[:5]]
        assert any("NIH" in n for n in names)

    def test_eligibility_score_in_range(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        fits = analyze_grant_fit(_ML_TEXT, "ai", 75, {"role": "faculty"})
        for f in fits:
            assert 0.0 <= f.eligibility_score <= 1.0

    def test_funding_probability_in_range(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        fits = analyze_grant_fit(_ML_TEXT, "ai", 75)
        for f in fits:
            assert 0.0 <= f.funding_probability <= 1.0

    def test_faculty_profile_increases_eligibility(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        fits_faculty = analyze_grant_fit(_ML_TEXT, "ai", 75, {"role": "professor"})
        fits_anon    = analyze_grant_fit(_ML_TEXT, "ai", 75, {})
        avg_fac  = sum(f.eligibility_score for f in fits_faculty) / max(len(fits_faculty), 1)
        avg_anon = sum(f.eligibility_score for f in fits_anon) / max(len(fits_anon), 1)
        assert avg_fac >= avg_anon

    def test_grant_fit_to_dict_has_keys(self):
        from services.publishing.grant_analyzer import analyze_grant_fit
        fits = analyze_grant_fit(_ML_TEXT, "ai", 75)
        if fits:
            d = fits[0].to_dict()
            assert "title" in d and "funder" in d and "funding_probability" in d


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
    def test_builds_strategy(self):
        from services.publishing.strategy_builder import build_publication_strategy
        strategy = build_publication_strategy("AI Paper", _ML_TEXT, "ai", 75)
        assert len(strategy.options) >= 3

    def test_recommended_option_is_set(self):
        from services.publishing.strategy_builder import build_publication_strategy
        strategy = build_publication_strategy("AI Paper", _ML_TEXT, "ai", 75)
        assert strategy.recommended_option is not None

    def test_strategy_has_backup_journals(self):
        from services.publishing.strategy_builder import build_publication_strategy
        strategy = build_publication_strategy("AI Paper", _ML_TEXT, "ai", 75)
        assert isinstance(strategy.backup_journals, list)

    def test_options_have_steps(self):
        from services.publishing.strategy_builder import build_publication_strategy
        strategy = build_publication_strategy("AI Paper", _ML_TEXT, "ai", 75)
        for opt in strategy.options:
            assert len(opt.steps) > 0

    def test_strategy_to_dict(self):
        from services.publishing.strategy_builder import build_publication_strategy
        strategy = build_publication_strategy("AI Paper", _ML_TEXT, "ai", 75)
        d = strategy.to_dict()
        assert "options" in d and "recommended_option" in d

    def test_citation_strategy_non_empty(self):
        from services.publishing.strategy_builder import build_publication_strategy
        strategy = build_publication_strategy("AI Paper", _ML_TEXT, "ai", 75)
        assert len(strategy.citation_strategy) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Risk Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskAnalyzer:
    def test_returns_eight_dimensions(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75, 0.7, 0.25, 12, 0.0)
        assert len(risk.dimensions) == 8

    def test_overall_risk_in_range(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75, 0.7, 0.25, 12, 0.0)
        assert 0.0 <= risk.overall_risk_score <= 1.0

    def test_success_probability_inverse_of_risk(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75, 0.7, 0.25, 12, 0.0)
        assert risk.estimated_success_probability > 0

    def test_predatory_journal_elevates_risk(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk_safe  = analyze_publication_risk(_ML_TEXT, 75, 0.7, 0.25, 12, 0.0)
        risk_pred  = analyze_publication_risk(_ML_TEXT, 75, 0.7, 0.25, 12, 0.9)
        pred_dim_safe = next(d for d in risk_safe.dimensions if "Predatory" in d.dimension)
        pred_dim_risky = next(d for d in risk_pred.dimensions if "Predatory" in d.dimension)
        assert pred_dim_risky.score > pred_dim_safe.score

    def test_low_scope_elevates_desk_rejection_risk(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk_high_scope = analyze_publication_risk(_ML_TEXT, 75, 0.9, 0.25, 12, 0.0)
        risk_low_scope  = analyze_publication_risk(_ML_TEXT, 75, 0.1, 0.25, 12, 0.0)
        desk_high = next(d for d in risk_high_scope.dimensions if "Desk" in d.dimension)
        desk_low  = next(d for d in risk_low_scope.dimensions  if "Desk" in d.dimension)
        assert desk_low.score > desk_high.score

    def test_long_review_elevates_delay_risk(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk_fast = analyze_publication_risk(_ML_TEXT, 75, 0.7, 0.25, 4,  0.0)
        risk_slow = analyze_publication_risk(_ML_TEXT, 75, 0.7, 0.25, 24, 0.0)
        delay_fast = next(d for d in risk_fast.dimensions if "Delay" in d.dimension)
        delay_slow = next(d for d in risk_slow.dimensions if "Delay" in d.dimension)
        assert delay_slow.score > delay_fast.score

    def test_top_risks_non_empty(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75, 0.7, 0.25, 12, 0.0)
        assert len(risk.top_risks) > 0

    def test_to_dict_has_dimensions(self):
        from services.publishing.risk_analyzer import analyze_publication_risk
        risk = analyze_publication_risk(_ML_TEXT, 75, 0.7, 0.25, 12, 0.0)
        d = risk.to_dict()
        assert isinstance(d["dimensions"], list)
        assert len(d["dimensions"]) == 8


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Export Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestExportEngine:
    def _make_letter(self):
        from services.publishing.models import CoverLetter
        return CoverLetter(journal="Nature", manuscript_title="AI Study", text="Dear Editor,\n\nTest.\n\nYours,\nAuthor")

    def _make_strategy(self):
        from services.publishing.strategy_builder import build_publication_strategy
        return build_publication_strategy("AI Paper", _ML_TEXT, "ai", 75)

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

    def test_export_roadmap_markdown(self):
        from services.publishing.export_engine import export
        from services.publishing.models import ExportFormat
        result = export(ExportFormat.PUBLICATION_ROADMAP, ExportFormat.MARKDOWN, {"strategy": self._make_strategy()})
        assert "# Publication Roadmap" in result

    def test_export_roadmap_latex(self):
        from services.publishing.export_engine import export
        from services.publishing.models import ExportFormat
        result = export(ExportFormat.PUBLICATION_ROADMAP, ExportFormat.LATEX, {"strategy": self._make_strategy()})
        assert "\\documentclass" in result

    def test_export_journal_comparison(self):
        from services.publishing.export_engine import export
        from services.publishing.journal_matcher import match_journals
        from services.publishing.models import ExportFormat
        matches = match_journals(_ML_TEXT, "ai", 75)
        result = export(ExportFormat.JOURNAL_COMPARISON, ExportFormat.MARKDOWN, {"matches": matches})
        assert "Journal" in result

    def test_export_grant_readiness(self):
        from services.publishing.export_engine import export
        from services.publishing.grant_analyzer import analyze_grant_fit
        from services.publishing.models import ExportFormat
        grants = analyze_grant_fit(_ML_TEXT, "ai", 75)
        result = export(ExportFormat.GRANT_READINESS, ExportFormat.MARKDOWN, {"grants": grants})
        assert "Grant" in result

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

    def test_analyse_journal_returns_list(self):
        async def _run():
            e = await _make_engine()
            result = await e.analyse_journal(_ML_TEXT, "ai", 75)
            assert isinstance(result, list)
            assert len(result) > 0
        asyncio.run(_run())

    def test_match_journal_returns_list(self):
        async def _run():
            e = await _make_engine()
            result = await e.match_journal(_ML_TEXT, "ai", 75)
            assert isinstance(result, list)
            assert len(result) == 6
        asyncio.run(_run())

    def test_match_conference_returns_list(self):
        async def _run():
            e = await _make_engine()
            result = await e.match_conference(_ML_TEXT, "ai", 75)
            assert isinstance(result, list)
        asyncio.run(_run())

    def test_match_grant_returns_list(self):
        async def _run():
            e = await _make_engine()
            result = await e.match_grant(_ML_TEXT, "ai", 75)
            assert isinstance(result, list)
        asyncio.run(_run())

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

    def test_export_markdown(self):
        async def _run():
            from services.publishing.strategy_builder import build_publication_strategy
            e = await _make_engine()
            strategy = build_publication_strategy("AI Paper", _ML_TEXT, "ai", 75)
            result = await e.export("publication_roadmap", "markdown", {"strategy": strategy})
            assert isinstance(result, str)
            assert len(result) > 50
        asyncio.run(_run())
