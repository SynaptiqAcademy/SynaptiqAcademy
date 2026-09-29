"""P1 Phase 8D — the reusable Evidence representation, plus the deterministic
label/contribution/explanation generation built from it.

Evidence shape (a plain dict, not a class, so it serializes straight into
the API response with no extra step):

    {"type": str, "candidate_value": str, "need_value": str, "relationship": "direct"|"complementary"}

Every entry here is produced by matching a real profile/research-record
value against a real Research Need term — never "an LLM said this person
probably has this expertise." relevance.py is the only caller that builds
these; this module only turns a finished evidence list into labels,
contribution sentences, and an explanation — no retrieval, no matching.
"""
from __future__ import annotations

_DIRECT = {"research_area", "research_keyword", "topic", "method", "software_tool", "publication"}
_METHOD = {"method", "software_tool"}
_COMPLEMENTARY = {"professional_expertise", "professional_role", "interdisciplinary"}
_CONTEXT = {"geographic_context", "language"}

LABELS = ("directly_relevant", "complementary_expertise", "methods_specialist", "context_specialist")

# Priority order for a candidate's PRIMARY placement when they qualify for
# more than one label (§12: one primary placement, secondary relevance
# stays visible in their evidence — never a duplicate card). Callers may
# override via `prioritize` (§22 user control) to swap the first two.
_DEFAULT_PRIORITY = ("directly_relevant", "complementary_expertise", "methods_specialist", "context_specialist")


def labels_for(evidence: list[dict]) -> list[str]:
    types = {e["type"] for e in evidence}
    labels = []
    if types & (_DIRECT - _METHOD):
        labels.append("directly_relevant")
    if types & _COMPLEMENTARY:
        labels.append("complementary_expertise")
    if types & _METHOD:
        labels.append("methods_specialist")
    if types & _CONTEXT:
        labels.append("context_specialist")
    return labels


def primary_group(labels: list[str], prioritize: str | None = None) -> str | None:
    if not labels:
        return None
    order = list(_DEFAULT_PRIORITY)
    if prioritize in order:
        order.remove(prioritize)
        order.insert(0, prioritize)
    for candidate in order:
        if candidate in labels:
            return candidate
    return labels[0]


_CONTRIBUTION_TEMPLATES = {
    "research_area": "Could contribute expertise in {v}.",
    "research_keyword": "Could contribute expertise in {v}.",
    "topic": "Could contribute expertise in {v}.",
    "method": "Could contribute experience with {v}.",
    "software_tool": "Could contribute experience with {v}.",
    "professional_expertise": "Could contribute a {v} perspective.",
    "professional_role": "Could contribute a {v} perspective.",
    "interdisciplinary": "Could contribute a {v} perspective.",
    "publication": "Could contribute research experience from published work related to {v}.",
    "geographic_context": "Could contribute context relevant to {v}.",
    "language": "Could contribute {v} language capability.",
}


def contributions_for(evidence: list[dict], limit: int = 3) -> list[str]:
    """Conservative, evidence-grounded — never a leadership/quality claim
    (§7): no "should lead", "ideal co-author", "best person"."""
    out: list[str] = []
    seen: set[str] = set()
    for e in evidence:
        tmpl = _CONTRIBUTION_TEMPLATES.get(e["type"])
        if not tmpl:
            continue
        line = tmpl.format(v=e["candidate_value"])
        if line not in seen:
            seen.add(line)
            out.append(line)
        if len(out) >= limit:
            break
    return out


def explanation_for(evidence: list[dict]) -> str:
    if not evidence:
        return "Limited profile information available to explain this match."
    direct = [e for e in evidence if e["type"] in (_DIRECT - _METHOD)]
    methods = [e for e in evidence if e["type"] in _METHOD]
    comp = [e for e in evidence if e["type"] in _COMPLEMENTARY]
    pubs = [e for e in evidence if e["type"] == "publication"]
    ctx = [e for e in evidence if e["type"] in _CONTEXT]

    parts = []
    direct_nonpub = [e for e in direct if e["type"] != "publication"]
    if direct_nonpub:
        vals = ", ".join(sorted({e["candidate_value"] for e in direct_nonpub})[:3])
        parts.append(f"profile lists {vals}")
    if methods:
        vals = ", ".join(sorted({e["candidate_value"] for e in methods})[:2])
        parts.append(f"uses {vals}")
    if comp:
        vals = ", ".join(sorted({e["candidate_value"] for e in comp})[:2])
        parts.append(f"brings complementary {vals} expertise")
    if pubs:
        parts.append("has published research related to this topic")
    if ctx:
        vals = ", ".join(sorted({e["candidate_value"] for e in ctx})[:2])
        parts.append(f"matches context: {vals}")

    if not parts:
        return "Limited profile information available to explain this match."
    return "Relevant because their " + "; ".join(parts) + "."
