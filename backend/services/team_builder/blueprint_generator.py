"""Research Need -> proposed Team Blueprint roles (§2, §34, §35).

Same interpretation pattern as services/research_need/interpreter.py: one
AI call attempts a structured role breakdown; any failure (unavailable,
malformed, disabled, timeout) falls back to a deterministic derivation from
the Research Need's own fields. AI never sees or invents candidates — role
generation and candidate retrieval are fully separate steps, so "AI must
never invent people" is enforced structurally, not just by instruction.
"""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import HTTPException

from services.ai.llm import call_llm
from services.research_need.models import ResearchNeed
from .models import TeamRole, PRIORITIES as PRIORITIES_SET, CATEGORIES as CATEGORIES_SET

log = logging.getLogger("synaptiq.team_builder")

CREDIT_ACTION = "team_blueprint_generate"
_MAX_ROLES = 8

_SYSTEM_PROMPT = """\
You are a research-team-composition assistant. You read one structured \
research need and propose the EXPERTISE ROLES an interdisciplinary team \
might need to address it — not people, not job titles, just the kind of \
expertise required. You are domain-general: medicine, engineering, \
economics, education, AI, law, climate, sociology, business, public \
administration, political science, the humanities, or any interdisciplinary \
combination — never assume any specific domain unless the need itself is \
about it.

A team ROLE is NOT a job title. "Quantitative Methods" is a valid role even \
though the person filling it might be an Associate Professor, a Data \
Scientist, or a PhD Candidate.

You must NOT:
- name or invent any specific person
- claim a role is filled by anyone
- output a team-quality score or percentage
- add a role just to appear interdisciplinary — every role must trace to \
something in the research need

Respond with ONLY a single JSON object, no prose, no markdown fences:

{
  "roles": [
    {
      "label": "short role name, e.g. Health Policy",
      "category": "core_domain | complementary_domain | methods | technical | policy_context | professional_practice | other",
      "description": "one sentence describing the role",
      "required_expertise": ["..."],
      "useful_methods": ["..."],
      "useful_tools": ["..."],
      "relevant_disciplines": ["..."],
      "why_needed": "one sentence explaining why THIS research need benefits from this role",
      "priority": "essential | useful | optional"
    }
  ]
}

Propose at most 8 roles. Omit fields you have no basis for rather than \
guessing.
"""


def _new_role_id() -> str:
    return uuid.uuid4().hex[:12]


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


def _deterministic_roles(need: ResearchNeed) -> list[TeamRole]:
    """§35 — must remain fully functional with no AI at all. One role per
    named expertise bucket the Research Need already has; no invented
    disciplines, no arbitrary padding to "look interdisciplinary" (§5)."""
    roles: list[TeamRole] = []

    for term in need.required_expertise[:4]:
        roles.append(TeamRole(
            role_id=_new_role_id(), label=term, category="core_domain",
            required_expertise=[term], priority="essential",
            why_needed=f"Your research question directly concerns {term}.",
        ))

    for term in (need.complementary_expertise + need.interdisciplinary_connections)[:3]:
        if any(r.label == term for r in roles):
            continue
        roles.append(TeamRole(
            role_id=_new_role_id(), label=term, category="complementary_domain",
            required_expertise=[term], priority="useful",
            why_needed=f"{term} may fill a different part of this research problem.",
        ))

    if need.useful_methods:
        roles.append(TeamRole(
            role_id=_new_role_id(), label="Methods", category="methods",
            useful_methods=need.useful_methods, priority="useful",
            why_needed="Your research need identifies specific methods that benefit from dedicated expertise.",
        ))

    for term in need.relevant_professional_roles[:2]:
        roles.append(TeamRole(
            role_id=_new_role_id(), label=term, category="professional_practice",
            relevant_disciplines=[term], priority="optional",
            why_needed=f"{term} expertise may bring a practical, non-academic perspective.",
        ))

    return roles[:_MAX_ROLES]


async def generate_blueprint_roles(
    need: ResearchNeed, *, use_ai: bool = True, user_id: str | None = None, db=None,
) -> tuple[list[TeamRole], dict]:
    """Returns (roles, meta) where meta = {"source": "ai"|"fallback", "reason": str|None}.
    Never raises for an AI failure — always returns a usable role list."""
    if not use_ai:
        return _deterministic_roles(need), {"source": "fallback", "reason": "ai_not_requested"}

    try:
        user_msg = json.dumps({
            "concise_problem_statement": need.concise_problem_statement or need.original_query,
            "research_domains": need.research_domains,
            "disciplines": need.disciplines,
            "required_expertise": need.required_expertise,
            "complementary_expertise": need.complementary_expertise,
            "useful_methods": need.useful_methods,
            "relevant_professional_roles": need.relevant_professional_roles,
            "interdisciplinary_connections": need.interdisciplinary_connections,
        })
        raw = await call_llm(
            system=_SYSTEM_PROMPT, user_msg=user_msg,
            feature="team_builder.blueprint", user_id=user_id, db=db, max_tokens=1500,
        )
        parsed = json.loads(_strip_fences(raw))
        roles = []
        for r in (parsed.get("roles") or [])[:_MAX_ROLES]:
            label = (r.get("label") or "").strip()
            if not label:
                continue
            priority = r.get("priority") if r.get("priority") in PRIORITIES_SET else "useful"
            category = r.get("category") if r.get("category") in CATEGORIES_SET else "other"
            roles.append(TeamRole(
                role_id=_new_role_id(), label=label, category=category,
                description=r.get("description") or "",
                required_expertise=r.get("required_expertise") or [],
                useful_methods=r.get("useful_methods") or [],
                useful_tools=r.get("useful_tools") or [],
                relevant_disciplines=r.get("relevant_disciplines") or [],
                why_needed=r.get("why_needed") or "",
                priority=priority,
            ))
        if not roles:
            return _deterministic_roles(need), {"source": "fallback", "reason": "empty_ai_output"}
        return roles, {"source": "ai", "reason": None}
    except HTTPException as exc:
        log.warning("Team blueprint AI generation unavailable (%s) — falling back", exc.detail)
        return _deterministic_roles(need), {"source": "fallback", "reason": "ai_unavailable"}
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        log.warning("Team blueprint AI generation returned malformed output (%s) — falling back", exc)
        return _deterministic_roles(need), {"source": "fallback", "reason": "malformed_ai_output"}
    except Exception as exc:  # noqa: BLE001 — must never 500 the request (§35)
        log.error("Team blueprint AI generation failed unexpectedly (%s) — falling back", exc)
        return _deterministic_roles(need), {"source": "fallback", "reason": "unexpected_error"}
