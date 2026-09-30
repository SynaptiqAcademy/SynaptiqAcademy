"""Team Blueprint schema — the smallest reusable representation (§4/§29).

Stored as plain dicts in MongoDB (matching this codebase's established
pattern for collaboration_requests.py etc.) — these Pydantic models are the
API request/response boundary, not the storage layer.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

PRIORITIES = {"essential", "useful", "optional"}
CATEGORIES = {
    "core_domain", "complementary_domain", "methods", "technical",
    "policy_context", "professional_practice", "other",
}
# §30 — deliberately the smallest lifecycle that's actually useful: "draft"
# (still editing roles/candidates), "inviting" (at least one invitation
# sent, awaiting responses), "ready" (essential roles all accepted). No
# separate "forming" state — it would only duplicate "inviting" without a
# distinct meaning.
BLUEPRINT_STATUSES = {"draft", "inviting", "ready"}


class SelectedCandidate(BaseModel):
    candidate_id: str
    # Evidence/contribution/explanation are snapshotted at selection time
    # (services/research_need/relevance.py's output is otherwise ephemeral,
    # recomputed per query) so "why invited" stays available later even if
    # the candidate's profile changes or the live retrieval would no longer
    # surface them the same way.
    evidence: list[dict] = Field(default_factory=list)
    contribution: list[str] = Field(default_factory=list)
    explanation: str = ""
    selected_at: str = ""
    collaboration_request_id: str | None = None


class TeamRole(BaseModel):
    role_id: str
    label: str
    category: str = "core_domain"
    description: str = ""
    required_expertise: list[str] = Field(default_factory=list)
    useful_methods: list[str] = Field(default_factory=list)
    useful_tools: list[str] = Field(default_factory=list)
    relevant_disciplines: list[str] = Field(default_factory=list)
    why_needed: str = ""
    priority: str = "useful"
    # §12 — self is represented separately here, never retrieved as an
    # external candidate (self-exclusion in candidate search stays intact).
    self_covers: bool = False
    selected_candidates: list[SelectedCandidate] = Field(default_factory=list)


class TeamBlueprint(BaseModel):
    id: str = ""
    owner_id: str = ""
    research_need: dict = Field(default_factory=dict)
    roles: list[TeamRole] = Field(default_factory=list)
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""
