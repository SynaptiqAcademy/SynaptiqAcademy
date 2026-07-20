"""Visualization builder — Phase IX.

Produces 8 JSON-serializable visualizations from a manuscript review result:
  1. quality_radar           — 8-dimension radar chart
  2. section_heatmap         — per-section quality heatmap
  3. publication_readiness   — readiness gauge (donut / score band)
  4. issue_severity_breakdown — stacked bar of critical/major/minor/suggestion
  5. revision_timeline        — Gantt-like timeline from roadmap
  6. completeness_checklist  — binary checklist of detected sections
  7. writing_metrics_chart   — writing quality bar chart
  8. journal_match_scatter   — scatter of journal matches (scope vs acceptance)
"""
from __future__ import annotations

from .models import (
    ReviewDimensions, SectionScore, PublicationReadiness,
    ReviewIssue, WritingMetrics, JournalMatch, SectionType,
)


def build_quality_radar(dims: ReviewDimensions) -> dict:
    """8-axis radar chart of review dimensions."""
    axes = [
        ("Scientific Rigor", dims.scientific_rigor.score),
        ("Originality", dims.originality.score),
        ("Methodology", dims.methodological_soundness.score),
        ("Clarity", dims.clarity.score),
        ("Literature", dims.literature_coverage.score),
        ("Contribution", dims.contribution.score),
        ("Statistics", dims.statistical_validity.score),
        ("Ethics", dims.ethical_compliance.score),
    ]
    return {
        "type": "quality_radar",
        "axes": [{"label": label, "score": round(score, 1)} for label, score in axes],
        "scale_max": 100,
        "overall": round(dims.weighted_score(), 1),
    }


def build_section_heatmap(section_scores: list[SectionScore]) -> dict:
    """Grid heatmap: each cell = section + score + grade."""
    cells = [
        {
            "section": s.label,
            "score": round(s.score, 1),
            "grade": s.grade,
            "detected": s.detected,
            "word_count": s.word_count,
        }
        for s in section_scores
    ]
    # Colour bands: red (<50), amber (50–69), green (70–89), dark-green (90+)
    for cell in cells:
        if not cell["detected"]:
            cell["colour"] = "missing"
        elif cell["score"] >= 90:
            cell["colour"] = "excellent"
        elif cell["score"] >= 70:
            cell["colour"] = "good"
        elif cell["score"] >= 50:
            cell["colour"] = "needs_improvement"
        else:
            cell["colour"] = "poor"
    return {
        "type": "section_heatmap",
        "cells": cells,
    }


def build_publication_readiness_gauge(pr: PublicationReadiness) -> dict:
    """Circular gauge showing publication readiness bands."""
    score = pr.overall_score
    if score >= 85:
        band = "ready"
        label = "Ready to Submit"
    elif score >= 70:
        band = "minor_revisions"
        label = "Minor Revisions Required"
    elif score >= 55:
        band = "major_revisions"
        label = "Major Revisions Required"
    elif score >= 40:
        band = "substantial_rework"
        label = "Substantial Rework Needed"
    else:
        band = "not_ready"
        label = "Not Ready for Submission"

    return {
        "type": "publication_readiness_gauge",
        "score": round(score, 1),
        "band": band,
        "label": label,
        "probabilities": {
            "acceptance": round(pr.acceptance_probability * 100, 1),
            "minor_revision": round(pr.minor_revision_probability * 100, 1),
            "major_revision": round(pr.major_revision_probability * 100, 1),
            "desk_rejection": round(pr.desk_rejection_risk * 100, 1),
        },
        "target_tier": pr.target_tier,
        "reviewer_difficulty": pr.reviewer_difficulty,
    }


def build_issue_severity_breakdown(
    critical: list[ReviewIssue],
    major: list[ReviewIssue],
    minor: list[ReviewIssue],
    suggestions: list[ReviewIssue],
) -> dict:
    """Stacked bar showing issue counts by severity and section."""
    # Section breakdown
    section_counts: dict[str, dict[str, int]] = {}
    for issue_list, label in [
        (critical, "critical"), (major, "major"),
        (minor, "minor"), (suggestions, "suggestion"),
    ]:
        for issue in issue_list:
            sec = issue.section or "General"
            if sec not in section_counts:
                section_counts[sec] = {"critical": 0, "major": 0, "minor": 0, "suggestion": 0}
            section_counts[sec][label] += 1

    bars = [
        {"section": sec, **counts}
        for sec, counts in sorted(section_counts.items(), key=lambda x: -(
            x[1]["critical"] * 4 + x[1]["major"] * 2 + x[1]["minor"] + x[1]["suggestion"] * 0.5
        ))
    ]

    return {
        "type": "issue_severity_breakdown",
        "summary": {
            "critical": len(critical),
            "major": len(major),
            "minor": len(minor),
            "suggestion": len(suggestions),
            "total": len(critical) + len(major) + len(minor) + len(suggestions),
        },
        "by_section": bars[:12],
    }


def build_revision_timeline(roadmap: list[dict]) -> dict:
    """Gantt-like timeline from roadmap phases."""
    phases = []
    cumulative_days = 0
    effort_to_days = {
        "1-2 days": (1, 2), "2–4 days": (2, 4), "1–5 days": (1, 5),
        "3–7 days": (3, 7), "1–2 weeks": (7, 14), "2–4 weeks": (14, 28),
        "1–3 months": (30, 90), "1–3 weeks": (7, 21),
        "2–5 days": (2, 5), ">3 months": (90, 120),
    }
    for p in roadmap:
        effort = p.get("estimated_effort", "1 week")
        low, high = effort_to_days.get(effort, (3, 7))
        phases.append({
            "phase": p.get("phase", 1),
            "title": p.get("title", ""),
            "priority": p.get("priority", "medium"),
            "start_day": cumulative_days,
            "end_day": cumulative_days + high,
            "duration_days": f"{low}–{high}",
            "section_focus": p.get("section_focus", []),
            "action_count": len(p.get("actions", [])),
        })
        cumulative_days += high

    return {
        "type": "revision_timeline",
        "phases": phases,
        "total_estimated_days": cumulative_days,
        "total_phases": len(phases),
    }


def build_completeness_checklist(
    detected_types: list[str],
    section_scores: list[SectionScore],
) -> dict:
    """Binary checklist of expected manuscript sections."""
    critical_sections = [
        SectionType.ABSTRACT, SectionType.INTRODUCTION, SectionType.METHODOLOGY,
        SectionType.RESULTS, SectionType.DISCUSSION, SectionType.CONCLUSIONS,
        SectionType.REFERENCES,
    ]
    recommended_sections = [
        SectionType.KEYWORDS, SectionType.LITERATURE_REVIEW, SectionType.OBJECTIVES,
        SectionType.HYPOTHESES, SectionType.LIMITATIONS, SectionType.FUTURE_WORK,
        SectionType.ETHICS, SectionType.ACKNOWLEDGEMENTS, SectionType.DATA_AVAILABILITY,
    ]
    optional_sections = [
        SectionType.THEORETICAL_FRAMEWORK, SectionType.RESEARCH_DESIGN,
        SectionType.PARTICIPANTS, SectionType.INSTRUMENTS, SectionType.DATA_ANALYSIS,
        SectionType.CONFLICT_OF_INTEREST, SectionType.FUNDING, SectionType.APPENDIX,
    ]

    detected_set = set(detected_types)
    score_map = {s.section_type.value: s.score for s in section_scores}

    def _items(sec_list: list[SectionType]) -> list[dict]:
        return [
            {
                "section": s.value,
                "label": s.value.replace("_", " ").title(),
                "detected": s.value in detected_set,
                "score": score_map.get(s.value),
            }
            for s in sec_list
        ]

    critical_items = _items(critical_sections)
    recommended_items = _items(recommended_sections)
    optional_items = _items(optional_sections)

    critical_count = sum(1 for i in critical_items if i["detected"])
    rec_count = sum(1 for i in recommended_items if i["detected"])
    completeness = (critical_count / len(critical_sections)) * 0.60 + \
                   (rec_count / len(recommended_sections)) * 0.40

    return {
        "type": "completeness_checklist",
        "completeness_score": round(completeness * 100, 1),
        "critical_sections": critical_items,
        "recommended_sections": recommended_items,
        "optional_sections": optional_items,
        "critical_complete": f"{critical_count}/{len(critical_sections)}",
        "recommended_complete": f"{rec_count}/{len(recommended_sections)}",
    }


def build_writing_metrics_chart(metrics: WritingMetrics) -> dict:
    """Bar chart of writing quality indicators."""

    def _classify(value: float, thresholds: list[tuple[float, str]]) -> str:
        for threshold, label in thresholds:
            if value <= threshold:
                return label
        return thresholds[-1][1]

    bars = [
        {
            "metric": "Avg Sentence Length",
            "value": metrics.avg_sentence_length,
            "unit": "words",
            "status": _classify(metrics.avg_sentence_length, [
                (18, "excellent"), (22, "good"), (30, "needs_improvement"), (1000, "poor")
            ]),
            "target": "18–22 words",
        },
        {
            "metric": "Passive Voice",
            "value": round(metrics.passive_voice_ratio * 100, 1),
            "unit": "%",
            "status": _classify(metrics.passive_voice_ratio, [
                (0.15, "excellent"), (0.25, "good"), (0.40, "needs_improvement"), (1.0, "poor")
            ]),
            "target": "<20%",
        },
        {
            "metric": "Academic Vocabulary",
            "value": round(metrics.academic_word_ratio * 100, 1),
            "unit": "%",
            "status": _classify(1 - metrics.academic_word_ratio, [
                (0.92, "excellent"), (0.95, "good"), (0.97, "needs_improvement"), (1.0, "poor")
            ]),
            "target": ">8%",
        },
        {
            "metric": "Transition Density",
            "value": round(metrics.transition_density, 2),
            "unit": "per 5 sentences",
            "status": _classify(3.0 - metrics.transition_density, [
                (1.0, "excellent"), (2.0, "good"), (2.5, "needs_improvement"), (3.0, "poor")
            ]),
            "target": ">1.5",
        },
        {
            "metric": "Readability (Flesch)",
            "value": metrics.readability_score,
            "unit": "score",
            "status": _classify(abs(metrics.readability_score - 47), [
                (10, "excellent"), (20, "good"), (30, "needs_improvement"), (100, "poor")
            ]),
            "target": "30–65 (academic)",
        },
        {
            "metric": "Long Sentences",
            "value": round(metrics.long_sentence_ratio * 100, 1),
            "unit": "%",
            "status": _classify(metrics.long_sentence_ratio, [
                (0.10, "excellent"), (0.20, "good"), (0.35, "needs_improvement"), (1.0, "poor")
            ]),
            "target": "<20%",
        },
    ]

    return {
        "type": "writing_metrics_chart",
        "word_count": metrics.word_count,
        "sentence_count": metrics.sentence_count,
        "paragraph_count": metrics.paragraph_count,
        "bars": bars,
    }


def build_journal_match_scatter(journal_matches: list[JournalMatch]) -> dict:
    """Scatter plot: x=scope_match, y=acceptance_probability, label=journal name."""
    points = [
        {
            "name": j.name,
            "publisher": j.publisher,
            "quartile": j.quartile,
            "x": round(j.scope_match, 3),
            "y": round(j.acceptance_probability, 3),
            "impact_factor": j.impact_factor,
            "open_access": j.open_access,
        }
        for j in journal_matches
    ]
    return {
        "type": "journal_match_scatter",
        "x_label": "Scope Match (0–1)",
        "y_label": "Estimated Acceptance Probability (0–1)",
        "points": points,
    }


def build_all_visualizations(
    dims: ReviewDimensions,
    section_scores: list[SectionScore],
    pr: PublicationReadiness,
    critical: list[ReviewIssue],
    major: list[ReviewIssue],
    minor: list[ReviewIssue],
    suggestions: list[ReviewIssue],
    roadmap: list[dict],
    detected_types: list[str],
    writing_metrics: WritingMetrics,
    journal_matches: list[JournalMatch],
) -> dict:
    return {
        "quality_radar": build_quality_radar(dims),
        "section_heatmap": build_section_heatmap(section_scores),
        "publication_readiness_gauge": build_publication_readiness_gauge(pr),
        "issue_severity_breakdown": build_issue_severity_breakdown(critical, major, minor, suggestions),
        "revision_timeline": build_revision_timeline(roadmap),
        "completeness_checklist": build_completeness_checklist(detected_types, section_scores),
        "writing_metrics_chart": build_writing_metrics_chart(writing_metrics),
        "journal_match_scatter": build_journal_match_scatter(journal_matches),
    }
