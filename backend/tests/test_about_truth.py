"""/about: why Synaptiq exists, without invented scale, history, people,
endorsements or promises. Present-tense claims are bound to shipped code."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_landing_commercial_truth import STALE, FABRICATION, UNSAFE, GENERIC, _visible_text

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "frontend" / "src" / "pages" / "About.jsx").read_text()
TEXT = _visible_text(SRC)
BACKEND = Path(__file__).resolve().parents[1]

BANNED = [r"\d+\+? (countries|researchers|institutions|universities|users|tools)", r"150\+", r"12\+",
          r"20\d\d Q\d", r"[Ff]ounded", r"[Oo]ur (global )?team", r"[Ii]nvestor", r"[Aa]ward", r"[Ff]eatured in",
          r"[Tt]rusted by", r"[Pp]artner", r"[Tt]estimonial", r"Ltd|Inc\.|SRL|GmbH", r"[Hh]eadquarter|[Oo]ffices? in",
          r"[Cc]areers|[Ww]e're hiring", r"[Pp]ress kit", r"[Rr]evolution", r"[Dd]emocratiz", r"[Ee]mpower",
          r"[Ss]eamless", r"[Aa]ll-in-one", r"[Ww]orld's", r"[Aa]utonomous", r"[Uu]nderstands", r"[Yy]our data is",
          r"[Ee]ncrypt", r"GDPR", r"[Nn]ever (sell|train)", r"[Mm]arketplace", r"[Tt]rust score", r"[Vv]erified researcher",
          r"We believe", r"€", r"Pro Advanced", r"AI Credits? (a|per) month"]


@pytest.mark.parametrize("pattern", STALE + FABRICATION + UNSAFE + GENERIC + BANNED)
def test_no_invented_scale_people_history_or_promises(pattern):
    assert not re.search(pattern, TEXT), pattern


def test_present_tense_claims_match_the_code():
    tb = (BACKEND / "routers" / "team_builder.py").read_text()
    assert '"status") == "accepted"' in tb                         # those who accept join the project
    assert "project_id" in (BACKEND / "routers" / "manuscripts.py").read_text()   # manuscripts linked to projects
    rel = (BACKEND / "services" / "research_need" / "relevance.py").read_text()
    assert "evidence" in rel                                        # suggestions show their evidence
    de = (BACKEND / "services" / "network" / "discovery_engine.py").read_text()
    assert "show_in_discovery" in de                                # you choose whether you appear in discovery
    inst = (BACKEND / "routers" / "institutions.py").read_text()
    assert '"$unset": {"institution_id": ""}' in inst               # leaving ends institutional access only


def test_direction_is_labelled_as_direction():
    assert "Not all of this exists yet." in SRC and "building toward" in SRC


def test_respects_signup_state_and_tracks_nothing_personal():
    assert "registrationOpen === false" in SRC
    for call in re.findall(r"track\(([^)]*)\)", SRC):
        assert "," not in call, call       # event names only
