"""/research: claims match the Research Need, matching and Team Builder code."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_landing_commercial_truth import STALE, FABRICATION, UNSAFE, GENERIC, _visible_text

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "frontend" / "src" / "pages" / "ResearchLanding.jsx").read_text()
TEXT = _visible_text("\n".join(l for l in SRC.splitlines() if "rootMargin" not in l))
BACKEND = Path(__file__).resolve().parents[1]

BANNED = [r"\bDr\.", r"\bProf\.", r"100M", r"h-index", r"percentile", r"real[- ]time", r"\d+% (match|fit)",
          r"[Pp]erfect match", r"[Mm]agic", r"[Gg]et (published|funded) faster", r"[Ww]orld-class",
          r"[Bb]est-in-class", r"[Ii]ndustry-leading", r"[Vv]erified [Rr]esearcher", r"automatic"]


@pytest.mark.parametrize("pattern", STALE + FABRICATION + UNSAFE + GENERIC + BANNED)
def test_no_unsupported_or_generic_claims(pattern):
    assert not re.search(pattern, TEXT), pattern


def test_no_pricing_and_free_is_not_collaboration():
    for bad in ("€", "/month", "AI Credits /", " GB", "checkout"):
        assert bad not in TEXT, bad
    assert "Searching, inviting and team building are on Pro" in SRC
    assert not re.search(r"[Cc]ollaborat\w* for free", TEXT)


def test_need_fields_exist_on_model():
    model = (BACKEND / "services" / "research_need" / "models.py").read_text()
    for f in ("concise_problem_statement", "research_domains", "required_expertise", "complementary_expertise",
              "useful_methods", "relevant_professional_roles"):
        assert f in model, f


def test_matching_fields_and_groups_are_real():
    rel = (BACKEND / "services" / "research_need" / "relevance.py").read_text()
    for f in ("research_areas", "research_interests", "research_keywords", "professional_expertise",
              "professional_role", "methods", "software_skills", "missing_expertise"):
        assert f in rel, f
    evidence = (BACKEND / "services" / "research_need" / "evidence.py").read_text()
    for label in ("Directly relevant", "Complementary expertise", "Methods specialist"):
        assert label in SRC
        assert label.lower().replace(" ", "_") in evidence
    assert "Could contribute experience with {v}." in evidence and "Could contribute experience with" in SRC


def test_team_builder_semantics_are_real():
    tb = (BACKEND / "routers" / "team_builder.py").read_text()
    models = (BACKEND / "services" / "team_builder" / "models.py").read_text()
    assert '"essential", "useful", "optional"' in models and "self_covers" in models
    assert "also_relevant_to" in tb and "/invite" in tb and "human-initiated only" in tb
    assert '"status") == "accepted"' in tb and "concise_problem_statement" in tb
    assert "You cover this" in SRC and "Missing expertise" in SRC and "Nobody joins until they accept" in SRC


def test_people_are_specimens_only():
    block = SRC[SRC.index("const PEOPLE"):SRC.index("function Candidate")]
    names = set(re.findall(r'name: "([^"]+)"', block))
    assert names <= {"Researcher A", "Researcher B", "Researcher C"}, names
    assert "Specimens, not real members" in SRC
    assert "api." not in SRC and "fetch(" not in SRC   # no live data on the public page


def test_analytics_never_carries_free_text():
    for call in re.findall(r"track\(([^)]*)\)", SRC):
        assert not re.search(r"query|question|email|name", call), call
