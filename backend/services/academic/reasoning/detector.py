"""AcademicWeaknessDetector — pure-Python heuristic weakness analysis.

All checks run in O(n) over the text with no external calls.
Results are used to enrich the system prompt and direct LLM reasoning.
"""
from __future__ import annotations

import re
from typing import Generator

from services.academic.models import (
    AcademicDomain, AcademicWeakness, MethodologyType, ResearchDesign,
    WeaknessSeverity, WeaknessType,
)
from services.academic.ontology import (
    DESIGN_KEYWORDS, DOMAIN_KEYWORDS, METHODOLOGY_KEYWORDS, SECTION_KEYWORDS,
)

# ── Precompiled regex patterns ─────────────────────────────────────────────────

_RE_CITATION_APA = re.compile(r'\([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*,?\s+\d{4}\)')
_RE_CITATION_NUM = re.compile(r'\[\d+\]|\[[\d,\s–-]+\]')
_RE_CITATION_ET_AL = re.compile(r'et al\.')
_RE_HYPOTHESIS = re.compile(
    r'\b(h[1-9]\d*|h0|null hypothesis|alternative hypothesis|we hypothesize|'
    r'research question|rq\d*|objective\s?\d|aim of|this study (aims?|seeks?|intends?))\b',
    re.IGNORECASE,
)
_RE_NOVELTY = re.compile(
    r'\b(novel|first|new approach|contribution|gap|we propose|introduce|present a|'
    r'state.of.the.art|outperform|improvement over|advance|pioneer)\b',
    re.IGNORECASE,
)
_RE_LIMITATION = re.compile(
    r'\b(limitation|not generaliz|cannot be generalized|future (work|research|studies?)|'
    r'further research|future directions?|scope of this)\b',
    re.IGNORECASE,
)
_RE_ETHICS = re.compile(
    r'\b(ethics|ethical approval|IRB|institutional review|Helsinki|informed consent|'
    r'anonymized?|participants were informed|GDPR|data protection)\b',
    re.IGNORECASE,
)
_RE_COI = re.compile(
    r'\b(conflict of interest|competing interests?|declaration|authors? declare|'
    r'no conflict|funding disclosure)\b',
    re.IGNORECASE,
)
_RE_DATA_AVAIL = re.compile(
    r'\b(data availability|code availability|available (at|on|from)|GitHub|GitLab|Zenodo|'
    r'upon reasonable request|open access data|dataset released)\b',
    re.IGNORECASE,
)
_RE_SAMPLE_SIZE = re.compile(
    r'\b(n\s?=\s?\d+|sample\s+size\s+of\s+\d+|\d+\s+participants?|\d+\s+subjects?|'
    r'\d+\s+respondents?)\b',
    re.IGNORECASE,
)
_RE_P_VALUE = re.compile(r'\bp\s*[<>=≤≥]\s*0?\.\d+|\bp-value', re.IGNORECASE)
_RE_EFFECT_SIZE = re.compile(
    r"\bCohen[''s]*\s+[df]|odds ratio|hazard ratio|risk ratio|r\s*=\s*0?\.\d+|"
    r"η[²2]|partial η|effect size",
    re.IGNORECASE,
)
_RE_CI = re.compile(r'\b(CI|confidence interval|\d+%\s+CI|95%\s+CI)\b', re.IGNORECASE)
_RE_POWER = re.compile(
    r'\b(power analysis|statistical power|β\s*=|1-β|type II|sample size calculation)\b',
    re.IGNORECASE,
)
_RE_SMALL_N = re.compile(r'\bn\s?=\s?([1-9]\d?)\b')   # captures n=1..99

# ── Main detector class ────────────────────────────────────────────────────────

class AcademicWeaknessDetector:
    """Stateless heuristic weakness detector."""

    def detect(
        self,
        text: str,
        feature: str = "",
        domain: AcademicDomain = AcademicDomain.UNKNOWN,
        methodology: MethodologyType = MethodologyType.UNKNOWN,
    ) -> list[AcademicWeakness]:
        weaknesses: list[AcademicWeakness] = []
        lower = text.lower()

        # ── Hypothesis checks ────────────────────────────────────────────────
        if feature in _HYPOTHESIS_FEATURES:
            if not _RE_HYPOTHESIS.search(text):
                weaknesses.append(AcademicWeakness(
                    type=WeaknessType.MISSING_HYPOTHESIS,
                    severity=WeaknessSeverity.HIGH,
                    description="No hypothesis, research question, or explicit study objective detected.",
                    suggestion="State the research question or hypothesis explicitly in the introduction.",
                    confidence=0.75,
                    location="introduction",
                ))

        # ── Novelty checks ───────────────────────────────────────────────────
        if feature in _NOVELTY_FEATURES:
            if not _RE_NOVELTY.search(text):
                weaknesses.append(AcademicWeakness(
                    type=WeaknessType.WEAK_NOVELTY,
                    severity=WeaknessSeverity.HIGH,
                    description="No explicit novelty claim or contribution statement detected.",
                    suggestion="Add a clear contribution paragraph stating what is new vs. existing work.",
                    confidence=0.70,
                    location="introduction",
                ))

        # ── Citation checks ──────────────────────────────────────────────────
        citation_count = self.count_citations(text)
        if feature in _CITATION_REQUIRED_FEATURES and citation_count < 3:
            weaknesses.append(AcademicWeakness(
                type=WeaknessType.MISSING_CITATIONS,
                severity=WeaknessSeverity.HIGH if citation_count == 0 else WeaknessSeverity.MEDIUM,
                description=f"Very few citations detected ({citation_count}). Academic work requires adequate referencing.",
                suggestion="Add references to support all claims, especially in the literature review and discussion.",
                confidence=0.85,
                location="references",
            ))

        # ── Limitation checks ────────────────────────────────────────────────
        if feature in _LIMITATION_REQUIRED_FEATURES:
            if not _RE_LIMITATION.search(text):
                weaknesses.append(AcademicWeakness(
                    type=WeaknessType.MISSING_LIMITATIONS,
                    severity=WeaknessSeverity.MEDIUM,
                    description="No limitations section or future work discussion detected.",
                    suggestion="Add a limitations paragraph discussing boundary conditions and generalizability.",
                    confidence=0.75,
                    location="discussion",
                ))

        # ── Statistical checks ───────────────────────────────────────────────
        if methodology in (MethodologyType.QUANTITATIVE, MethodologyType.EXPERIMENTAL):
            weaknesses.extend(self._check_statistics(text))

        # ── Methodology checks ───────────────────────────────────────────────
        if feature in _METHODOLOGY_FEATURES:
            weaknesses.extend(self._check_methodology(text, lower))

        # ── Ethics checks ────────────────────────────────────────────────────
        if domain in (AcademicDomain.MEDICINE_HEALTH, AcademicDomain.SOCIAL_SCIENCES,
                      AcademicDomain.PSYCHOLOGY, AcademicDomain.EDUCATION):
            if not _RE_ETHICS.search(text) and feature in _ETHICS_SENSITIVE_FEATURES:
                weaknesses.append(AcademicWeakness(
                    type=WeaknessType.MISSING_ETHICS_APPROVAL,
                    severity=WeaknessSeverity.HIGH,
                    description="No ethics approval or participant consent statement detected.",
                    suggestion="Include IRB/ethics committee approval number and informed consent procedure.",
                    confidence=0.72,
                    location="methods",
                ))

        # ── Conflict of Interest ────────────────────────────────────────────
        if not _RE_COI.search(text) and feature in _FULL_MANUSCRIPT_FEATURES:
            weaknesses.append(AcademicWeakness(
                type=WeaknessType.MISSING_CONFLICT_OF_INTEREST,
                severity=WeaknessSeverity.LOW,
                description="No conflict of interest declaration found.",
                suggestion="Add a conflict of interest statement (even if 'none declared').",
                confidence=0.80,
                location="declarations",
            ))

        # ── Data availability ───────────────────────────────────────────────
        if domain == AcademicDomain.COMPUTER_SCIENCE and not _RE_DATA_AVAIL.search(text):
            if feature in _CODE_SHARING_EXPECTED_FEATURES:
                weaknesses.append(AcademicWeakness(
                    type=WeaknessType.MISSING_DATA_AVAILABILITY,
                    severity=WeaknessSeverity.MEDIUM,
                    description="No data/code availability statement detected.",
                    suggestion="Add a data availability statement with a repository link (GitHub, Zenodo).",
                    confidence=0.68,
                    location="declarations",
                ))

        # ── Sample size warning ──────────────────────────────────────────────
        small_n_match = _RE_SMALL_N.search(text)
        if small_n_match:
            n = int(small_n_match.group(1))
            if n < 30 and methodology != MethodologyType.QUALITATIVE:
                weaknesses.append(AcademicWeakness(
                    type=WeaknessType.SMALL_SAMPLE_SIZE,
                    severity=WeaknessSeverity.HIGH if n < 10 else WeaknessSeverity.MEDIUM,
                    description=f"Sample size appears small (n={n}) for quantitative analysis.",
                    suggestion="Justify sample size with power analysis or acknowledge this as a limitation.",
                    confidence=0.78,
                    location="methods",
                ))

        return weaknesses

    def _check_statistics(self, text: str) -> Generator[AcademicWeakness, None, None]:
        has_stats = bool(_RE_P_VALUE.search(text))
        if not has_stats:
            return

        if not _RE_EFFECT_SIZE.search(text):
            yield AcademicWeakness(
                type=WeaknessType.MISSING_EFFECT_SIZE,
                severity=WeaknessSeverity.MEDIUM,
                description="Statistical results present but no effect size reported.",
                suggestion="Report effect sizes (Cohen's d, r, odds ratio) alongside p-values for practical significance.",
                confidence=0.78,
                location="results",
            )

        if not _RE_CI.search(text):
            yield AcademicWeakness(
                type=WeaknessType.MISSING_CONFIDENCE_INTERVAL,
                severity=WeaknessSeverity.MEDIUM,
                description="No confidence intervals reported with statistical results.",
                suggestion="Report 95% confidence intervals alongside all main statistical estimates.",
                confidence=0.78,
                location="results",
            )

        if not _RE_POWER.search(text):
            yield AcademicWeakness(
                type=WeaknessType.MISSING_POWER_ANALYSIS,
                severity=WeaknessSeverity.LOW,
                description="No power analysis or sample size justification found.",
                suggestion="Include an a priori power analysis justifying the sample size.",
                confidence=0.65,
                location="methods",
            )

    def _check_methodology(self, text: str, lower: str) -> Generator[AcademicWeakness, None, None]:
        has_methodology = any(kw in lower for kw in SECTION_KEYWORDS.get("methodology", []))
        if not has_methodology:
            yield AcademicWeakness(
                type=WeaknessType.WEAK_METHODOLOGY,
                severity=WeaknessSeverity.HIGH,
                description="No clear methodology section detected.",
                suggestion="Add an explicit methodology section describing research design, data collection, and analysis.",
                confidence=0.70,
                location="methodology",
            )

    def detect_domain(self, text: str) -> tuple[AcademicDomain, float]:
        """Return (domain, confidence_score) based on keyword frequency."""
        scores: dict[str, int] = {}
        text_lower = text.lower()
        for domain_key, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[domain_key] = score
        if not scores:
            return AcademicDomain.UNKNOWN, 0.0
        best = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = min(0.95, scores[best] / max(total, 1) + 0.3)
        return AcademicDomain(best), round(confidence, 2)

    def detect_methodology(self, text: str) -> tuple[MethodologyType, ResearchDesign]:
        """Classify methodology type and research design."""
        text_lower = text.lower()
        meth_scores: dict[str, int] = {}
        for mtype, keywords in METHODOLOGY_KEYWORDS.items():
            meth_scores[mtype] = sum(1 for kw in keywords if kw.lower() in text_lower)

        best_meth = max(meth_scores, key=lambda k: meth_scores[k]) if meth_scores else "unknown"
        methodology = MethodologyType(best_meth) if meth_scores.get(best_meth, 0) > 0 else MethodologyType.UNKNOWN

        design = ResearchDesign.UNKNOWN
        for design_key, keywords in DESIGN_KEYWORDS.items():
            if any(kw.lower() in text_lower for kw in keywords):
                design = ResearchDesign(design_key)
                break

        return methodology, design

    def detect_sections(self, text: str) -> list[str]:
        """Return list of detected structural sections."""
        lower = text.lower()
        return [
            section
            for section, keywords in SECTION_KEYWORDS.items()
            if any(kw.lower() in lower for kw in keywords)
        ]

    def count_citations(self, text: str) -> int:
        apa_matches = len(_RE_CITATION_APA.findall(text))
        num_matches = len(_RE_CITATION_NUM.findall(text))
        et_al_matches = len(_RE_CITATION_ET_AL.findall(text))
        return max(apa_matches, num_matches, et_al_matches)

    def build_structure_flags(self, text: str) -> dict[str, bool]:
        """Build a dict of structural flags for AcademicContext."""
        sections = self.detect_sections(text)
        return {
            "has_abstract": "abstract" in sections,
            "has_hypothesis": bool(_RE_HYPOTHESIS.search(text)),
            "has_methodology": "methodology" in sections,
            "has_results": "results" in sections,
            "has_limitations": "limitations" in sections,
            "has_future_work": "future_work" in sections,
            "has_ethics": bool(_RE_ETHICS.search(text)),
            "has_conflicts_of_interest": bool(_RE_COI.search(text)),
        }


# ── Feature sets for conditional checks ───────────────────────────────────────

_HYPOTHESIS_FEATURES = {
    "manuscript_review", "research_gap_finder", "research_design_advisor",
    "statistical_review", "grant_gap_detection",
}
_NOVELTY_FEATURES = {
    "manuscript_review", "research_gap_finder", "abstract_generator",
}
_CITATION_REQUIRED_FEATURES = {
    "manuscript_review", "literature_review", "research_gap_finder",
    "statistical_review", "abstract_generator",
}
_LIMITATION_REQUIRED_FEATURES = {
    "manuscript_review", "literature_review", "research_gap_finder",
}
_METHODOLOGY_FEATURES = {
    "manuscript_review", "research_design_advisor", "statistical_review",
}
_ETHICS_SENSITIVE_FEATURES = {
    "manuscript_review", "research_design_advisor", "statistical_review",
}
_FULL_MANUSCRIPT_FEATURES = {
    "manuscript_review",
}
_CODE_SHARING_EXPECTED_FEATURES = {
    "manuscript_review", "research_gap_finder",
}
