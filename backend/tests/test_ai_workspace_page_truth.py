"""/ai-workspace: page claims bound to the AI code, plus the AI safety fixes
made alongside it (no fabricated references, untrusted-content boundary,
discovery eligibility for AI people-lookups, no raw provider errors)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from plans_catalogue import CREDIT_COSTS, FEATURE_MIN_PLAN
from services.ai.pricing import guards_for
from tests.test_landing_commercial_truth import STALE, FABRICATION, UNSAFE, GENERIC, _visible_text

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
SRC = (ROOT / "frontend" / "src" / "pages" / "AIWorkspaceLanding.jsx").read_text()
TEXT = _visible_text(SRC)

BANNED = [r"Try AI Free", r"[Hh]allucination-free", r"100% accurate", r"[Ss]cientifically validated", r"\b10x\b",
          r"[Aa]utonomous", r"[Pp]ublish faster", r"[Gg]et funded faster", r"[Uu]ndetectable", r"[Bb]eat AI",
          r"[Pp]lagiarism", r"[Ww]orld's most", r"[Mm]agic", r"\bPerfect\b", r"[Gg]uarantee", r"never leaves",
          r"never used to train", r"[Pp]riority (AI )?processing", r"Advanced Manuscript Intelligence",
          r"PubMed|Scopus|Web of Science|100M", r"knows your", r"understands your", r"--\s*AI Credits"]


@pytest.mark.parametrize("pattern", STALE + FABRICATION + UNSAFE + GENERIC + BANNED)
def test_no_unsupported_or_generic_claims(pattern):
    assert not re.search(pattern, TEXT), pattern


def test_no_prices_and_free_has_no_ai():
    for bad in ("€", "/month", "checkout"):
        assert bad not in TEXT, bad
    assert "The Free plan has no AI Credits" in SRC


@pytest.mark.parametrize("label,action", [
    ("Rewrite a passage", "ai_rewriting"), ("Copilot message", "ai_chat_message"),
    ("Journal fit", "ai_journal_matching"), ("Statistical review", "ai_statistical_review"),
    ("Literature review", "ai_literature_review"), ("Full manuscript review", "ai_manuscript_review"),
    ("Research Assistant run", "DEEP_RESEARCH"),
])
def test_cost_strip_reads_the_catalogue_keys_routers_charge(label, action):
    # Costs come from /billing/credit-usage-catalogue at runtime; the page only names the key.
    assert action in CREDIT_COSTS
    assert f'["{label}", "{action}"]' in SRC
    assert "loadCreditCatalogue" in SRC and 'api.get("/billing/plans")' in SRC


def test_routers_charge_the_keys_the_page_names():
    for router, action in (("literature_review", "ai_literature_review"), ("statistical_review", "ai_statistical_review"),
                           ("manuscript_review", "ai_manuscript_review"), ("assistant", "ai_chat_message")):
        assert f'"{action}"' in (BACKEND / "routers" / f"{router}.py").read_text(), router
    assert '"DEEP_RESEARCH"' in (BACKEND / "routers" / "copilot.py").read_text()


@pytest.mark.parametrize("name,feature", [
    ("Literature review", "ai_literature_review"), ("Research gap finder", "ai_research_gap_finder"),
    ("Study design advisor", "ai_research_design_advisor"), ("Statistical review", "ai_statistical_review"),
    ("Journal, conference and grant fit", "ai_journal_matching"),
])
def test_task_plan_labels_match_enforcement(name, feature):
    plan = "Pro Advanced" if FEATURE_MIN_PLAN[feature] == "pro_researcher" else "Pro"
    assert re.search(rf'\["{re.escape(name)}", "[^"]+", "{plan}", "{feature}"\]', SRC), name


def test_context_sizes_match_guards():
    for tier, words in (("PRO", "45,000"), ("PRO_ADVANCED", "112,000")):
        approx = round(guards_for(tier)["max_input_tokens"] * 0.75, -3)   # cost_guard's words-per-token
        assert abs(approx - int(words.replace(",", ""))) <= 1000, (tier, approx)
        assert f"up to about {words} words" in SRC


def test_literature_tools_are_described_as_model_knowledge():
    assert "doesn't search databases" in SRC
    lr = (BACKEND / "routers" / "literature_review.py").read_text()
    assert "openalex" not in lr.lower() and "crossref" not in lr.lower()


def test_manuscript_context_fields_are_real():
    a = (BACKEND / "routers" / "assistant.py").read_text()
    for f in ('"abstract"', '"keywords"', '"status"', '"filled_sections"', '"objectives"', '"methodology"',
              '"skills_needed"', '"milestones"'):
        assert f in a, f


# ── AI safety fixes ──────────────────────────────────────────────────────────
def test_assistant_never_asks_for_invented_references():
    from routers.assistant import CAPABILITY_DIRECTIVES
    assert "plausible" not in CAPABILITY_DIRECTIVES["citation_generation"].lower()
    assert "Never create" in CAPABILITY_DIRECTIVES["citation_generation"]
    assert "likely venues" not in CAPABILITY_DIRECTIVES["literature_synthesis"]


def test_assistant_marks_user_material_as_data():
    a = (BACKEND / "routers" / "assistant.py").read_text()
    assert "never as instructions" in a and "<context>" in a and "<manuscript_sections>" in a
    assert 'f"LLM error' not in a


def test_copilot_stream_does_not_echo_exceptions():
    c = (BACKEND / "routers" / "copilot.py").read_text()
    assert "str(exc)[:200]" not in c


def test_ai_people_lookups_use_discovery_eligibility():
    agent = (BACKEND / "agents" / "collaboration_agent.py").read_text()
    assert "discovery.search_people" in agent and "db.users.find" not in agent
    m = (BACKEND / "services" / "ai" / "matching.py").read_text()
    block = m[m.index("Pull a broad pool"):m.index(".limit(120)")]
    for rule in ('"profile_visibility": {"$ne": "private"}', '"is_demo": {"$ne": True}',
                 "REAL_CUSTOMER_FILTER", "_discovery_exclusions"):
        assert rule in block, rule


def test_analytics_never_carries_free_text():
    for call in re.findall(r"track\(([^)]*)\)", SRC):
        assert not re.search(r"\b(query|question|prompt|text|email|name)\b", call), call
