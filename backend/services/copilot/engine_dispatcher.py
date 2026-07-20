"""Academic Copilot — Engine Dispatcher (Phase XI).

Calls each intelligence engine's rule-based components in quick-scan mode
(no full LLM pass, no separate credit charge). The copilot LLM advisor then
synthesises the results. Full-depth analysis can be triggered via the
dedicated engine endpoints.
"""
from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger("synaptiq.copilot.dispatcher")


# ── Quick-scan helpers per engine ─────────────────────────────────────────────

async def _scan_manuscript(content: str, context: dict) -> dict:
    """Run rule-based manuscript components on supplied content."""
    try:
        from services.manuscript.doc_parser import parse_text
        from services.manuscript.section_detector import detect_sections
        from services.manuscript.scientific_reviewer import review_scientific
        from services.manuscript.writing_reviewer import review_writing
        from services.manuscript.statistical_reviewer import review_statistical

        doc = parse_text(content)
        sections = detect_sections(content)
        sci_dim, sci_issues, _ = review_scientific(doc, sections, "", "")
        write_dim, write_issues, _ = review_writing(doc, sections)
        stat_dim, stat_issues, _ = review_statistical(doc)

        critical = [i for i in sci_issues + write_issues + stat_issues if i.severity.value == "critical"]
        major    = [i for i in sci_issues + write_issues + stat_issues if i.severity.value == "major"]

        return {
            "engine": "manuscript",
            "word_count": doc.word_count,
            "section_count": len(sections),
            "critical_issue_count": len(critical),
            "major_issue_count": len(major),
            "scientific_score": sci_dim.score,
            "writing_score": write_dim.score,
            "statistical_score": stat_dim.score,
            "top_issues": [
                {"severity": i.severity.value, "title": i.title}
                for i in (critical + major)[:5]
            ],
            "sections_detected": [s.section_type for s in sections[:6]],
        }
    except Exception as exc:
        logger.warning("manuscript scan failed: %s", exc)
        return {"engine": "manuscript", "error": str(exc)}


async def _scan_statistical(content: str, context: dict) -> dict:
    """Run rule-based statistical components on supplied content."""
    try:
        from services.statistical.data_parser import parse_text
        from services.statistical.design_analyzer import analyze_design
        from services.statistical.sampling_reviewer import review_sampling
        from services.statistical.result_interpreter import interpret_results

        parsed = parse_text(content)
        design = analyze_design(content, parsed)
        sampling, samp_issues = review_sampling(content, design)
        results_interp, res_issues = interpret_results(content)

        return {
            "engine": "statistical",
            "study_type": design.study_type.value if design.study_type else None,
            "primary_method": design.primary_method.value if design.primary_method else None,
            "sample_size": design.sample_size,
            "methods_detected": [m.value for m in design.detected_methods[:5]],
            "sampling_adequate": sampling.is_adequate,
            "sampling_score": sampling.score,
            "has_p_values": results_interp.has_p_values,
            "has_effect_sizes": results_interp.has_effect_sizes,
            "has_confidence_intervals": results_interp.has_confidence_intervals,
            "issue_count": len(samp_issues) + len(res_issues),
            "top_issues": [
                {"severity": i.severity.value, "title": i.title}
                for i in (samp_issues + res_issues)[:5]
            ],
        }
    except Exception as exc:
        logger.warning("statistical scan failed: %s", exc)
        return {"engine": "statistical", "error": str(exc)}


async def _scan_literature(content: str, context: dict) -> dict:
    """Run a keyword-level literature intelligence scan."""
    try:
        from services.literature.quick_scan import quick_scan_content  # type: ignore[import]
        return await quick_scan_content(content, context)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("literature quick_scan failed: %s", exc)

    # Fallback: parse the content for basic lit signals
    import re
    text = content.lower()
    ref_count = len(re.findall(r"\([\w\s]+,?\s*\d{4}\)", content))
    recent = len(re.findall(r"\b(2020|2021|2022|2023|2024|2025|2026)\b", text))
    years_found = re.findall(r"\b(19[89]\d|20[012]\d)\b", content)
    year_range = (
        f"{min(years_found)}–{max(years_found)}"
        if len(years_found) >= 2 else "N/A"
    )
    return {
        "engine": "literature",
        "reference_count": ref_count,
        "recent_citation_count": recent,
        "year_range": year_range,
        "recency_ratio": round(recent / max(ref_count, 1), 2),
        "needs_more_refs": ref_count < 20,
    }


async def _scan_gap(content: str, context: dict) -> dict:
    """Run rule-based research gap signals on supplied content."""
    import re
    text = content.lower()

    gap_signals = [
        "research gap", "gap in the literature", "no study has",
        "few studies", "limited research", "underexplored", "understudied",
        "future research", "unexplored", "lack of research",
    ]
    detected = [s for s in gap_signals if s in text]
    novelty_signals = ["novel", "original", "new framework", "new approach", "first study"]
    novelty = [s for s in novelty_signals if s in text]

    return {
        "engine": "gap",
        "gap_signals_detected": detected,
        "novelty_signals_detected": novelty,
        "gap_signal_count": len(detected),
        "novelty_claim_count": len(novelty),
        "has_explicit_gap": len(detected) >= 2,
        "recommendation": (
            "The manuscript clearly articulates research gaps."
            if len(detected) >= 2
            else "Consider explicitly stating the research gap in the introduction."
        ),
    }


# ── Main dispatcher ───────────────────────────────────────────────────────────

_SCANNERS: dict[str, any] = {
    "manuscript":  _scan_manuscript,
    "literature":  _scan_literature,
    "gap":         _scan_gap,
    "statistical": _scan_statistical,
}


async def dispatch_engines(
    engines: list[str],
    content: str,
    context: dict,
) -> dict[str, dict]:
    """Run all requested engine quick-scans, in parallel where possible.

    Returns mapping engine_name → result dict.
    """
    if not engines or not content.strip():
        return {}

    tasks = {eng: _SCANNERS[eng](content, context) for eng in engines if eng in _SCANNERS}
    if not tasks:
        return {}

    t0 = time.perf_counter()
    results_list = await asyncio.gather(*tasks.values(), return_exceptions=True)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    engine_results: dict[str, dict] = {}
    for engine, result in zip(tasks.keys(), results_list):
        if isinstance(result, Exception):
            engine_results[engine] = {"engine": engine, "error": str(result)}
        else:
            engine_results[engine] = result

    logger.debug(
        "dispatched engines=%s elapsed=%.0fms",
        list(engine_results.keys()), elapsed_ms,
    )
    return engine_results
