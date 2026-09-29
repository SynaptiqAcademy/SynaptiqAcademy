"""Interprets a free-text research question/problem into a structured
ResearchNeed — via AI when requested and available, with a deterministic
fallback that never lets the feature collapse into an error (§4).

No user/profile data is ever included in the interpretation prompt, so the
AI has nothing to invent a person from at this stage — the "must not
fabricate a person/credential" constraint (§3) is enforced structurally,
not just by instruction.
"""
from __future__ import annotations

import json
import logging
import re

from fastapi import HTTPException

from services.ai.llm import call_llm
from .models import ResearchNeed

log = logging.getLogger("synaptiq.research_need")

CREDIT_ACTION = "research_need_interpret"

_SYSTEM_PROMPT = """\
You are a research-taxonomy assistant. You read one free-text research \
question or problem and extract a structured description of the EXPERTISE \
it likely requires. You are domain-general: the query may be about \
medicine, engineering, economics, education, AI, law, climate, sociology, \
business, public administration, political science, the humanities, or any \
interdisciplinary combination — never assume healthcare or any other \
specific domain unless the query itself is about it.

You must NOT:
- invent or name any specific person, researcher, or institution
- claim any credential, publication, or verification status exists
- output a match percentage or score
- infer a person's language, location, or profession from anything other \
than what the query explicitly states

Distinguish two kinds of expertise:
- required_expertise: people working directly in the same research area as \
the query
- complementary_expertise: people whose expertise would fill a DIFFERENT \
part of the same problem (e.g. a technical project may also need a policy, \
ethics, or economics angle) — identify real interdisciplinary connections, \
not just synonyms of the same field

Respond with ONLY a single JSON object, no prose, no markdown fences, \
matching exactly this shape (omit or empty-array any field you have no \
evidence for — do not guess to fill every field):

{
  "concise_problem_statement": "one or two sentences restating the problem",
  "research_domains": ["..."],
  "disciplines": ["..."],
  "topics": ["..."],
  "research_keywords": ["..."],
  "required_expertise": ["..."],
  "complementary_expertise": ["..."],
  "professional_expertise": ["..."],
  "useful_methods": ["..."],
  "useful_software_or_tools": ["..."],
  "relevant_professional_roles": ["..."],
  "geographic_context": "",
  "languages": [],
  "collaboration_types": ["..."],
  "interdisciplinary_connections": ["..."],
  "constraints": ""
}
"""

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "for", "to", "in", "on",
    "with", "how", "can", "could", "would", "should", "is", "are", "be",
    "while", "protecting", "supporting", "improve", "improving", "this",
    "that", "these", "those", "it", "its", "we", "our", "i", "my",
}


def _deterministic_interpret(query: str) -> ResearchNeed:
    """No AI needed, no AI available, or AI failed: normalize the raw query
    into keywords using the taxonomy the platform already has (free-text
    tags — there is no fixed controlled vocabulary to match against), so
    canonical discovery still has something real to search on (§4)."""
    words = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", query)
    seen: dict[str, str] = {}
    for w in words:
        lw = w.lower()
        if lw in _STOPWORDS or lw in seen:
            continue
        seen[lw] = w
    keywords = list(seen.values())[:12]
    return ResearchNeed(
        original_query=query,
        concise_problem_statement=query.strip()[:280],
        research_keywords=keywords,
        topics=keywords[:6],
        interpretation_source="fallback",
    )


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```", 2)
        inner = parts[1] if len(parts) >= 2 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
        if "```" in text:
            text = text.split("```")[0].strip()
    return text


async def interpret_research_need(
    query: str,
    *,
    use_ai: bool = True,
    user_id: str | None = None,
    db=None,
) -> tuple[ResearchNeed, dict]:
    """Returns (need, meta). meta = {"source": "ai"|"fallback", "reason": str|None}.

    Never raises for an AI failure — always returns a usable ResearchNeed,
    falling back deterministically (§4). The caller decides whether to
    charge credits, based on meta["source"].
    """
    query = (query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Describe what you're researching first.")

    if not use_ai:
        return _deterministic_interpret(query), {"source": "fallback", "reason": "ai_not_requested"}

    try:
        raw = await call_llm(
            system=_SYSTEM_PROMPT,
            user_msg=query,
            feature="research_need.interpret",
            user_id=user_id,
            db=db,
            max_tokens=1200,
        )
        text = _strip_fences(raw)
        parsed = json.loads(text)
        need = ResearchNeed(
            original_query=query,
            concise_problem_statement=parsed.get("concise_problem_statement") or query.strip()[:280],
            research_domains=parsed.get("research_domains") or [],
            disciplines=parsed.get("disciplines") or [],
            topics=parsed.get("topics") or [],
            research_keywords=parsed.get("research_keywords") or [],
            required_expertise=parsed.get("required_expertise") or [],
            complementary_expertise=parsed.get("complementary_expertise") or [],
            professional_expertise=parsed.get("professional_expertise") or [],
            useful_methods=parsed.get("useful_methods") or [],
            useful_software_or_tools=parsed.get("useful_software_or_tools") or [],
            relevant_professional_roles=parsed.get("relevant_professional_roles") or [],
            geographic_context=parsed.get("geographic_context") or "",
            languages=parsed.get("languages") or [],
            collaboration_types=parsed.get("collaboration_types") or [],
            interdisciplinary_connections=parsed.get("interdisciplinary_connections") or [],
            constraints=parsed.get("constraints") or "",
            interpretation_source="ai",
        )
        return need, {"source": "ai", "reason": None}
    except HTTPException as exc:
        log.warning("Research need AI interpretation unavailable (%s) — falling back", exc.detail)
        return _deterministic_interpret(query), {"source": "fallback", "reason": "ai_unavailable"}
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        log.warning("Research need AI interpretation returned malformed output (%s) — falling back", exc)
        return _deterministic_interpret(query), {"source": "fallback", "reason": "malformed_ai_output"}
    except Exception as exc:  # noqa: BLE001 — this must never 500 the request (§4)
        log.error("Research need AI interpretation failed unexpectedly (%s) — falling back", exc)
        return _deterministic_interpret(query), {"source": "fallback", "reason": "unexpected_error"}
