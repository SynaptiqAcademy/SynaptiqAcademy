"""AI-powered 19-field structured extraction for a single paper.

Results are cached in MongoDB `lit_paper_analyses` so repeated analysis of
the same paper_id costs zero credits and zero latency.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from services.literature.analysis.evidence_quality import score_paper
from services.literature.models import Paper, PaperAnalysis

log = logging.getLogger("synaptiq.literature.analyzer")

_MAX_TEXT_CHARS = 6000   # trim to avoid max-token errors

_SYSTEM = """\
You are a senior academic research analyst with expertise across scientific disciplines.
Your role is to perform precise, structured extraction of academic content from research papers.

RULES:
1. Extract ONLY information explicitly present in the provided text.
2. If a field is not discussed, use an empty string or empty list — never invent.
3. Be concise but complete: each extracted element should be a single sentence or short phrase.
4. For statistical_methods, list only methods explicitly named (e.g. "logistic regression", "ANOVA").
5. For variables, list only those explicitly identified as independent/dependent/control.
6. Return ONLY valid JSON — no markdown fences, no commentary.
"""

_PROMPT = """\
Analyse the following academic paper text and extract structured information.

PAPER TEXT (may be abstract or full text):
---
{text}
---

Return a JSON object with EXACTLY this schema:
{{
  "research_question": "<the primary research question or problem statement — 1-2 sentences>",
  "objectives": ["<objective 1>", "<objective 2>"],
  "hypothesis": "<the stated or implied hypothesis — empty if none>",
  "methodology": "<methodology summary — quantitative/qualitative/mixed/computational/experimental>",
  "research_design": "<specific design — RCT/cohort/survey/case study/systematic review/etc.>",
  "variables": {{
    "independent": ["<variable>"],
    "dependent": ["<variable>"],
    "control": ["<variable>"]
  }},
  "sample": "<sample description: size, population, selection method>",
  "data_collection": "<how data was collected — instruments, sources, period>",
  "statistical_methods": ["<method 1>", "<method 2>"],
  "results": "<key findings summary — 2-3 sentences>",
  "limitations": ["<limitation 1>", "<limitation 2>"],
  "novelty": "<what is new or original about this work>",
  "contribution": "<main scientific contribution to the field>",
  "future_work": "<suggested directions for future research>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "citation_context": "<how this paper relates to or cites the broader literature>",
  "domain": "<primary research domain — e.g. machine learning, oncology, education>",
  "extracted_keywords": ["<keyword 1>", "<keyword 2>", "<keyword 3>"]
}}
"""


async def analyze_paper(
    paper: Paper,
    db: Any = None,
    force: bool = False,
) -> PaperAnalysis:
    """Extract 19-field academic structure from a paper, with MongoDB caching."""
    # Check cache
    if db is not None and not force:
        cached = await _load_cached(db, paper.paper_id)
        if cached:
            return cached

    text = paper.analysis_text[:_MAX_TEXT_CHARS]
    if not text.strip():
        return _empty_analysis(paper)

    fields = await _call_ai(text)
    quality = score_paper(paper)

    confidence = _estimate_confidence(text, fields)

    analysis = PaperAnalysis(
        paper_id=paper.paper_id,
        session_id=paper.session_id,
        research_question=fields.get("research_question", ""),
        objectives=_list(fields.get("objectives")),
        hypothesis=fields.get("hypothesis", ""),
        methodology=fields.get("methodology", ""),
        research_design=fields.get("research_design", ""),
        variables=fields.get("variables", {"independent": [], "dependent": [], "control": []}),
        sample=fields.get("sample", ""),
        data_collection=fields.get("data_collection", ""),
        statistical_methods=_list(fields.get("statistical_methods")),
        results=fields.get("results", ""),
        limitations=_list(fields.get("limitations")),
        novelty=fields.get("novelty", ""),
        contribution=fields.get("contribution", ""),
        future_work=fields.get("future_work", ""),
        strengths=_list(fields.get("strengths")),
        weaknesses=_list(fields.get("weaknesses")),
        citation_context=fields.get("citation_context", ""),
        domain=fields.get("domain", ""),
        extracted_keywords=_list(fields.get("extracted_keywords")),
        evidence_quality=quality,
        analysis_confidence=confidence,
        analysis_method="ai",
    )

    # Persist to cache
    if db is not None:
        await _save_cached(db, analysis)

    return analysis


async def analyze_batch(
    papers: list[Paper],
    db: Any = None,
    max_concurrent: int = 5,
) -> list[PaperAnalysis]:
    """Analyse multiple papers with bounded concurrency."""
    sem = asyncio.Semaphore(max_concurrent)

    async def _bounded(p: Paper) -> PaperAnalysis:
        async with sem:
            return await analyze_paper(p, db)

    return list(await asyncio.gather(*[_bounded(p) for p in papers]))


# ── AI call ───────────────────────────────────────────────────────────────────

async def _call_ai(text: str) -> dict:
    try:
        from services.ai.llm import call_llm
        raw = await call_llm(
            system=_SYSTEM,
            user_msg=_PROMPT.format(text=text),
            feature="literature_review.paper_analysis",
            max_tokens=2000,
        )
        return _parse_json(raw)
    except Exception as exc:
        log.warning("Paper AI analysis failed: %s", exc)
        return {}


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    # Strip markdown fences
    if text.startswith("```"):
        parts = text.split("```", 2)
        inner = parts[1] if len(parts) >= 2 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip().split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


# ── MongoDB cache ─────────────────────────────────────────────────────────────

async def _load_cached(db: Any, paper_id: str) -> PaperAnalysis | None:
    try:
        doc = await db["lit_paper_analyses"].find_one({"paper_id": paper_id})
        if not doc:
            return None
        quality_data = doc.pop("evidence_quality", {})
        from services.literature.models import EvidenceQuality, EvidenceGrade
        eq = EvidenceQuality(
            methodological_quality=quality_data.get("methodological_quality", 0.0),
            scientific_rigor=quality_data.get("scientific_rigor", 0.0),
            citation_impact=quality_data.get("citation_impact", 0.0),
            novelty_score=quality_data.get("novelty_score", 0.0),
            reproducibility_score=quality_data.get("reproducibility_score", 0.0),
            publication_credibility=quality_data.get("publication_credibility", 0.0),
            overall_score=quality_data.get("overall_score", 0.0),
            grade=EvidenceGrade(quality_data.get("grade", "C")),
            study_design=quality_data.get("study_design", ""),
            quality_notes=quality_data.get("quality_notes", []),
        )
        doc.pop("_id", None)
        return PaperAnalysis(**{k: v for k, v in doc.items()
                                if k in PaperAnalysis.__dataclass_fields__},
                             evidence_quality=eq)
    except Exception:
        return None


async def _save_cached(db: Any, analysis: PaperAnalysis) -> None:
    try:
        doc = analysis.to_dict()
        await db["lit_paper_analyses"].update_one(
            {"paper_id": analysis.paper_id},
            {"$set": doc},
            upsert=True,
        )
    except Exception:
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _list(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(v).strip() for v in val if v]
    if isinstance(val, str) and val:
        return [val]
    return []


def _estimate_confidence(text: str, fields: dict) -> float:
    filled = sum(1 for v in fields.values()
                 if v and (isinstance(v, str) and v) or
                 (isinstance(v, list) and v) or
                 (isinstance(v, dict) and any(v.values())))
    base = min(0.95, filled / 19)
    if len(text) > 1000:
        base = min(0.95, base + 0.10)
    return round(base, 3)


def _empty_analysis(paper: Paper) -> PaperAnalysis:
    return PaperAnalysis(
        paper_id=paper.paper_id,
        session_id=paper.session_id,
        evidence_quality=score_paper(paper),
        analysis_confidence=0.0,
        analysis_method="rule",
    )
