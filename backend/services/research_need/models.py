"""The Research Need — one reusable structured representation of a research
question/problem, produced either by AI interpretation or the deterministic
fallback (interpreter.py), and consumed by the relevance layer (relevance.py).

No field is required except original_query. This is intentionally the ONLY
Research Need shape in the codebase — Phase 8E/8F's Team Builder is expected
to reuse this same object (required_expertise -> required roles -> candidate
shortlist -> collaboration request -> team), not define its own.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchNeed(BaseModel):
    original_query: str
    concise_problem_statement: str = ""

    research_domains: list[str] = Field(default_factory=list)
    disciplines: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    research_keywords: list[str] = Field(default_factory=list)

    # Core vs complementary is the interdisciplinary-intelligence split (§7):
    # required_expertise = people working directly in the same area;
    # complementary_expertise = people whose expertise fills a different part
    # of the same problem (e.g. a policy specialist for a technical project).
    required_expertise: list[str] = Field(default_factory=list)
    complementary_expertise: list[str] = Field(default_factory=list)

    professional_expertise: list[str] = Field(default_factory=list)
    useful_methods: list[str] = Field(default_factory=list)
    useful_software_or_tools: list[str] = Field(default_factory=list)
    relevant_professional_roles: list[str] = Field(default_factory=list)

    # Geographic context and expertise are kept as separate fields on purpose
    # (§2) — geographic_context is never derived from a person's name/
    # language/institution, only from what the query itself says.
    geographic_context: str = ""
    languages: list[str] = Field(default_factory=list)

    collaboration_types: list[str] = Field(default_factory=list)
    interdisciplinary_connections: list[str] = Field(default_factory=list)
    constraints: str = ""

    # "ai" | "fallback" — which path produced this interpretation.
    interpretation_source: str = "fallback"

    def all_terms(self) -> list[str]:
        """Every term worth matching against a profile, deduplicated,
        case-insensitive-safe order preserved. Used by both the relevance
        layer's retrieval query and its missing-expertise check."""
        seen: dict[str, str] = {}
        for bucket in (
            self.research_keywords, self.topics, self.required_expertise,
            self.complementary_expertise, self.professional_expertise,
            self.useful_methods, self.useful_software_or_tools,
            self.relevant_professional_roles, self.research_domains,
            self.disciplines,
        ):
            for term in bucket:
                t = (term or "").strip()
                if t and t.lower() not in seen:
                    seen[t.lower()] = t
        return list(seen.values())
