"""Rule-based evidence quality scoring — no LLM required."""
from __future__ import annotations

import math
import re

from services.literature.models import EvidenceGrade, EvidenceQuality, Paper

# Study design hierarchy (higher = better methodological quality)
_DESIGN_SCORES: dict[str, float] = {
    "systematic review": 1.00,
    "meta-analysis": 1.00,
    "randomised controlled trial": 0.95,
    "randomized controlled trial": 0.95,
    "rct": 0.95,
    "cohort study": 0.80,
    "longitudinal study": 0.78,
    "prospective study": 0.75,
    "retrospective study": 0.65,
    "cross-sectional": 0.60,
    "cross-sectional study": 0.60,
    "case-control": 0.60,
    "survey": 0.55,
    "qualitative study": 0.60,
    "grounded theory": 0.62,
    "ethnography": 0.60,
    "mixed methods": 0.70,
    "case study": 0.40,
    "literature review": 0.65,
    "scoping review": 0.70,
    "narrative review": 0.60,
    "benchmark": 0.75,
    "simulation": 0.65,
    "experiment": 0.80,
}

# Keywords indicating rigour elements
_RE_HYPOTHESIS = re.compile(r"\bhypothes[ie]s\b|\baim\b|\bobjective\b|\bresearch question\b", re.I)
_RE_STATISTICS = re.compile(r"\bp\s*[<=>]\s*0\.\d+|confidence interval|effect size|Cohen|OR\b|RR\b|hazard ratio|regression|ANOVA|chi.?square", re.I)
_RE_LIMITATIONS = re.compile(r"\blimitation|weakness|constraint|shortcoming\b", re.I)
_RE_DATA_AVAIL = re.compile(r"data availab|github\.com|zenodo|figshare|osf\.io|dryad|data sharing|replication", re.I)
_RE_ETHICS = re.compile(r"ethical approval|IRB|ethics committee|informed consent|IACUC", re.I)


def score_paper(paper: Paper) -> EvidenceQuality:
    """Compute multi-dimensional evidence quality for a paper."""
    text = (paper.analysis_text or "").lower()
    title_lower = paper.title.lower()
    notes: list[str] = []

    # 1. Methodological quality (study design detection)
    meth_score, study_design = _methodological_quality(text, title_lower, notes)

    # 2. Scientific rigour (hypothesis + stats + limitations)
    rigor_score = _scientific_rigour(text, notes)

    # 3. Citation impact (log-normalised, saturates at ~1000 citations)
    cit_score = _citation_impact(paper.citation_count)

    # 4. Novelty proxy (how distinctive are its keywords vs. generic)
    novelty_score = _novelty_proxy(paper, notes)

    # 5. Reproducibility (data + ethics statement)
    repr_score = _reproducibility(text, notes)

    # 6. Publication credibility
    cred_score = _publication_credibility(paper, notes)

    # Weighted overall
    overall = (
        meth_score * 0.30
        + rigor_score * 0.25
        + cit_score * 0.15
        + novelty_score * 0.10
        + repr_score * 0.10
        + cred_score * 0.10
    )
    overall = round(min(1.0, max(0.0, overall)), 3)
    grade = _grade(overall)

    return EvidenceQuality(
        methodological_quality=round(meth_score, 3),
        scientific_rigor=round(rigor_score, 3),
        citation_impact=round(cit_score, 3),
        novelty_score=round(novelty_score, 3),
        reproducibility_score=round(repr_score, 3),
        publication_credibility=round(cred_score, 3),
        overall_score=overall,
        grade=grade,
        study_design=study_design,
        quality_notes=notes[:5],
    )


def score_corpus(papers: list[Paper]) -> list[EvidenceQuality]:
    scores = [score_paper(p) for p in papers]
    # Adjust novelty relative to corpus average keyword overlap
    _adjust_novelty(papers, scores)
    return scores


def corpus_quality_summary(scores: list[EvidenceQuality]) -> dict:
    if not scores:
        return {"avg_score": 0.0, "grade_distribution": {}}
    avg = sum(s.overall_score for s in scores) / len(scores)
    grade_dist: dict[str, int] = {}
    for s in scores:
        grade_dist[s.grade.value] = grade_dist.get(s.grade.value, 0) + 1
    return {
        "avg_score": round(avg, 3),
        "grade_distribution": grade_dist,
        "top_papers_count": sum(1 for s in scores if s.overall_score >= 0.75),
        "low_quality_count": sum(1 for s in scores if s.overall_score < 0.40),
    }


# ── Private helpers ────────────────────────────────────────────────────────────

def _methodological_quality(text: str, title_lower: str, notes: list) -> tuple[float, str]:
    for design, score in _DESIGN_SCORES.items():
        if design in text[:3000] or design in title_lower:
            notes.append(f"Study design detected: {design}")
            return score, design
    # Default if no recognisable design
    notes.append("Study design not clearly identified")
    return 0.50, "unspecified"


def _scientific_rigour(text: str, notes: list) -> float:
    score = 0.0
    if _RE_HYPOTHESIS.search(text):
        score += 0.35
    else:
        notes.append("No hypothesis or clear objective identified")
    if _RE_STATISTICS.search(text):
        score += 0.40
    else:
        notes.append("No statistical reporting detected")
    if _RE_LIMITATIONS.search(text):
        score += 0.25
    else:
        notes.append("No limitations section found")
    return score


def _citation_impact(count: int) -> float:
    if count <= 0:
        return 0.0
    return min(1.0, math.log(count + 1) / math.log(1001))


def _novelty_proxy(paper: Paper, notes: list) -> float:
    keyword_count = len(paper.keywords)
    if keyword_count == 0:
        return 0.5   # neutral when no keywords
    score = min(1.0, keyword_count / 8)
    return round(score, 3)


def _reproducibility(text: str, notes: list) -> float:
    score = 0.0
    if _RE_DATA_AVAIL.search(text):
        score += 0.60
    if _RE_ETHICS.search(text):
        score += 0.40
    if score == 0:
        notes.append("No reproducibility indicators found")
    return score


def _publication_credibility(paper: Paper, notes: list) -> float:
    if not paper.journal:
        notes.append("Journal not identified")
        return 0.5
    # Preprints are lower credibility by default
    if paper.arxiv_id and not paper.doi:
        return 0.50
    # Known high-tier indicators (simple keyword check)
    title = paper.journal.lower()
    if any(t in title for t in ["nature", "science", "cell", "lancet", "nejm", "jama", "bmj"]):
        return 1.0
    if any(t in title for t in ["plos", "frontiers", "ieee", "acm", "springer"]):
        return 0.80
    # Peer-reviewed default
    return 0.70


def _grade(score: float) -> EvidenceGrade:
    if score >= 0.80:
        return EvidenceGrade.A
    if score >= 0.65:
        return EvidenceGrade.B
    if score >= 0.50:
        return EvidenceGrade.C
    if score >= 0.35:
        return EvidenceGrade.D
    return EvidenceGrade.F


def _adjust_novelty(papers: list[Paper], scores: list[EvidenceQuality]) -> None:
    """Post-adjustment: papers with unique keywords get a small novelty boost."""
    all_kw: dict[str, int] = {}
    for p in papers:
        for kw in p.keywords:
            all_kw[kw.lower()] = all_kw.get(kw.lower(), 0) + 1

    for paper, score in zip(papers, scores):
        unique = sum(1 for kw in paper.keywords if all_kw.get(kw.lower(), 0) == 1)
        if unique > 2 and score.novelty_score < 1.0:
            boost = min(0.15, unique * 0.03)
            score.novelty_score = round(min(1.0, score.novelty_score + boost), 3)
            # Recompute overall
            score.overall_score = round(min(1.0, score.overall_score + boost * 0.10), 3)
