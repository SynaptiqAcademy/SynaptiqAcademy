"""Authenticated app design system: one brand navy, one button system, light
page headers, one credit indicator, honest empty/error/upgrade states.
Reads the frontend sources (docs/product/app-design-system.md)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
DS = SRC / "components" / "ds"


def _read(p):
    return (SRC / p).read_text()


def test_one_brand_colour_in_tokens():
    tokens = _read("lib/tokens.js")
    assert 'export const NAVY         = "#0F2847";' in tokens
    assert 'export const ACCENT       = "#0F2847";' in tokens          # no second brand colour
    assert 'export const VIOLET       = "#2f5486";' in tokens          # AI surfaces are navy-family
    assert 'export const INFO           = "#2f5486";' in tokens
    assert "Newsreader" in tokens.split("FONT_SERIF")[1][:80]
    css = _read("index.css")
    assert "--sq-crimson-600: #b42318;" in css                         # danger is semantic red
    assert "--sq-bg:          #FBFAF7;" in css
    assert "--sq-radius-btn:    4px;" in css


def test_button_system():
    b = (DS / "Button.jsx").read_text()
    assert '"border border-navy-700 bg-navy-700 text-white hover:bg-navy-800' in b
    for alias in ("ghost:     SECONDARY", "outline:   SECONDARY", "hero:      SECONDARY"):
        assert alias in b, alias
    offenders = []
    for f in list((SRC / "pages").rglob("*.jsx")) + list((SRC / "components").rglob("*.jsx")):
        for m in re.finditer(r"<Button\b[^>]*?style=\{\{[^}]*\bbackground(?:Color)?:\s*(ACCENT|EMERALD|\"#[0-9a-fA-F]{6}\"|step\.color)", f.read_text()):
            offenders.append(f"{f.relative_to(SRC)}: {m.group(1)}")
    assert not offenders, offenders


def test_page_header_is_light_and_honest():
    pl = (DS / "PageLayout.jsx").read_text()
    assert "linear-gradient" not in pl
    assert "pl-hero-title" in pl and "Newsreader" in pl
    assert "function cleanStats" in pl and "undefined|NaN" in pl


def test_no_burgundy_or_decorative_violet_outside_charts():
    hits = []
    for f in list((SRC / "pages").rglob("*.jsx")) + list((SRC / "components").rglob("*.jsx")):
        rel = str(f.relative_to(SRC))
        if any(x in rel for x in ("landing/", "auth/", "consent/", "ds/Chart.jsx")):
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if re.search(r"#(8A1538|7C3AED|8B5CF6|0891B2|EC4899)\b", line, re.I) and not re.search(r"\[i ?%|PALETTE|COLORS", line):
                hits.append(f"{rel}:{i}")
    assert not hits, hits[:20]


def test_one_global_credit_indicator():
    top = (DS / "TopNav.jsx").read_text()
    assert "/credits/balance" not in top and " cr\n" not in top
    side = (DS / "Sidebar.jsx").read_text()
    assert "The one global credit indicator" in side and "/credits/balance" in side
    home = (SRC / "pages" / "Home")
    assert not (home / "FooterSummary.jsx").exists()
    assert "balance" not in (home / "WelcomeHeader.jsx").read_text()


def test_empty_states_and_metrics_degrade():
    es = (DS / "EmptyState.jsx").read_text()
    assert "dashed ${" not in es and "TEXT_DISABLED" not in es
    sc = (DS / "StatCard.jsx").read_text()
    assert "valued.every((c) => isEmptyValue(c.props.value))) return null" in sc


def test_upgrade_state_names_the_current_plan():
    gate = _read("components/billing/RouteEntitlementGate.jsx")
    assert "Your Pro plan includes" in gate and "Your Free plan includes" in gate
    assert "Pro Advanced adds" in gate


def test_home_ai_input_shows_cost_and_respects_plan():
    ai = _read("pages/Home/AICommandCenter.jsx")
    assert "ai_os_message" in ai and "lockedFor(\"/ai\")" in ai
    assistant = _read("pages/AIAssistant.jsx")
    assert "initialPrompt" in assistant and "never sent automatically" in assistant


def test_research_and_experts_paths_are_explicit():
    rx = _read("pages/ResearchExperts.jsx")
    assert "Describe a research need" in rx and "Search members" in rx
    assert "Member search is free and never uses AI credits." in rx
    panel = _read("components/research/ResearchNeedPanel.jsx")
    assert "Find expertise with AI" in panel and "Basic term matching · free" in panel


def test_raw_api_errors_never_reach_the_ui():
    pat = re.compile(r"\b\w+\??\.response\??\.data\??\.detail\s*\|\|\s*[\"'`]")
    hits = [str(f.relative_to(SRC)) for f in list((SRC / "pages").rglob("*.jsx")) + list((SRC / "components").rglob("*.jsx"))
            if pat.search(f.read_text())]
    assert not hits, hits


def test_no_match_percentages_for_people():
    # The public site promises "No match percentages": people are ranked, the
    # card shows the evidence (shared topics, complementary skills), never a number.
    rx = _read("pages/ResearchExperts.jsx")
    assert "Research compatibility ·" not in rx and "Why they may fit" in rx
    assert "MatchBadge" not in _read("pages/Network.jsx")
    assert "ScoreRing" not in _read("pages/CollaborationIntelligence.jsx")
    assert "CompatBar" not in _read("pages/GrantOpportunityWorkspace.jsx")
    assert "match_score" not in _read("pages/Researchers.jsx")
    card = _read("components/ds/EntityCards.jsx").split("export function ResearcherCard")[1].split("export function")[0]
    assert "match_score" not in card
    assert "const score" not in _read("components/marketplace/MatchCard.jsx")
    recs = _read("pages/Recommendations.jsx")
    for card in ("function ResearcherCard", "function MentorCard", "function ReviewerCard"):
        body = recs.split(card)[1].split("\nfunction ")[0]
        assert "ScoreBadge" not in body, card


def test_ai_credit_prices_come_from_the_server_catalogue():
    assistant = _read("pages/AIAssistant.jsx")
    assert "WF_CREDITS" not in assistant and "~12 cr" not in assistant
    assert "loadCreditCatalogue" in assistant and "ai_os_message" in assistant
    market = _read("pages/Marketplace.jsx")
    assert "RERANK_COST" not in market and "ai_marketplace_rerank" in market
    assert "loadCreditCatalogue" in _read("pages/Today.jsx")
    pat = re.compile(r"~\d+\s*cr\b|\b\d+\s*credits?\s*per\b")
    hits = [str(f.relative_to(SRC)) for f in (SRC / "pages").rglob("*.jsx") if pat.search(f.read_text())]
    assert not hits, hits


def test_page_title_classes_are_global():
    css = _read("index.css")
    assert ".pl-hero-title {" in css and ".pl-eyebrow {" in css
    assert ".pl-hero-title {" not in (DS / "PageLayout.jsx").read_text()
    for page in ("pages/PaymentSuccess.jsx", "pages/PaymentCancelled.jsx", "components/auth/RequireInstitution.jsx"):
        assert 'className="pl-hero-title"' in _read(page), page
