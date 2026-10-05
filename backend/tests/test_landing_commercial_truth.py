"""Landing page: commercial truth, claim safety and public-preview behaviour.

Guards against stale plan values, invented proof, unsafe claims and generic
marketing language returning to the public homepage.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from plans_catalogue import get_plan, PLAN_QUOTAS, STORAGE_LIMITS_BYTES

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
LANDING_DIR = FRONTEND / "src" / "components" / "landing"
LANDING_FILES = [FRONTEND / "src" / "pages" / "Landing.jsx", *LANDING_DIR.glob("*.js*")]
ALL_LANDING = "\n".join(p.read_text() for p in LANDING_FILES)
FOOTER = (FRONTEND / "src" / "components" / "layout" / "MarketingLayout.jsx").read_text()
INDEX_HTML = (FRONTEND / "public" / "index.html").read_text()
GB = 1024 ** 3


def _visible_text(src: str) -> str:
    """Drop comment lines so documentation can quote what's banned."""
    return "\n".join(l for l in src.splitlines()
                     if not l.strip().startswith(("//", "*", "/*", "{/*")))


class TestNoPricingOnLanding:
    """Plans, prices, credits and storage live on /pricing only."""

    def test_no_prices_credits_or_plan_cards(self):
        text = _visible_text(ALL_LANDING)
        for bad in ("€", "AI Credits /", "credits_per_month", "PLAN_PREVIEW", "Choose Pro", "Pro Advanced",
                    "Contact Sales", " GB", "Early Access", "<Plans", "LandingFAQ", "lp-plan"):
            assert bad not in text, bad

    def test_conversion_moment_is_start_free_and_pricing(self):
        s = (LANDING_DIR / "Sections.jsx").read_text()
        assert "You already have the question." in s
        assert 'to="/register"' in s and "Start Free" in s
        assert 'to="/pricing"' in s and "Explore Pricing" in s
        assert "checkout" not in _visible_text(ALL_LANDING)

    def test_old_closing_and_faq_are_gone(self):
        assert "Every project starts as a question." not in ALL_LANDING
        assert "lp-close" not in ALL_LANDING
        assert not (LANDING_DIR / "content.js").exists()
        assert not (LANDING_DIR / "AfterMatch.jsx").exists()


STALE = [r"\b300 (AI )?[Cc]redits", r"\b1,?000 (AI )?[Cc]redits", r"\b50 (AI )?[Cc]redits", r"\b25 (AI )?[Cc]redits",
         r"\b100 ?GB\b", r"\b500 ?GB\b", r"€299", r"\b2,?000 (AI )?[Cc]redits", r"\b250 (AI )?[Cc]redits"]
FABRICATION = [r"Trusted by", r"\b\d{2,}\+? (countries|universities|researchers|institutions)\b",
               r"\b\d+%", r"[Tt]estimonial", r"\b[Rr]atings?\b", r"Most Popular", r"Best Value", r"Recommended",
               r"#1", r"Platform coverage", r"Only today", r"[Ll]imited time", r"[Ll]ast chance", r"places left"]
UNSAFE = [r"SOC ?2", r"ISO ?27001", r"HIPAA", r"end-to-end", r"[Mm]ilitary-grade", r"[Ee]nterprise-grade",
          r"GDPR[- ](certified|compliant)", r"\b(we|Synaptiq) guarantees\b", r"guaranteed (publication|funding|acceptance)",
          r"verified (expert|professional)s?\b"]
GENERIC = [r"[Rr]evolutioni[sz]e", r"[Ss]upercharge", r"[Uu]nlock your", r"[Tt]ransform your research",
           r"[Gg]ame-changing", r"[Cc]utting-edge", r"\b[Pp]owerful\b", r"\b[Ss]eamless", r"[Nn]ext-generation",
           r"[Ff]uture of research", r"[Aa]ll-in-one", r"[Ss]uperpower", r"[Ss]marter research",
           r"[Ee]mpower", r"[Ll]everag", r"[Hh]arness the power", r"Whether you're", r"\bImagine\b",
           r"AI-powered"]


class TestClaimSafety:
    @pytest.mark.parametrize("pattern", STALE)
    def test_no_stale_commercial_values(self, pattern):
        assert not re.search(pattern, _visible_text(ALL_LANDING)), pattern

    @pytest.mark.parametrize("pattern", FABRICATION)
    def test_no_fabricated_proof_or_pressure(self, pattern):
        assert not re.search(pattern, _visible_text(ALL_LANDING)), pattern

    @pytest.mark.parametrize("pattern", UNSAFE)
    def test_no_unsupported_security_or_outcome_claims(self, pattern):
        text = _visible_text(ALL_LANDING)
        hits = [m.group(0) for m in re.finditer(pattern, text)]
        # Questions/negations ("Does Synaptiq guarantee…? No.") are allowed.
        assert not hits, hits

    @pytest.mark.parametrize("pattern", GENERIC)
    def test_no_generic_ai_marketing_language(self, pattern):
        assert not re.search(pattern, _visible_text(ALL_LANDING)), pattern

    def test_footer_has_no_certification_badges(self):
        for bad in ("SOC 2", "ISO 27001", "Compliance badges", "Customer Stories"):
            assert bad not in FOOTER, bad

    def test_static_html_has_no_fake_ratings(self):
        assert "AggregateRating" not in INDEX_HTML and '"Review"' not in INDEX_HTML
        assert "Research starts with a question." in INDEX_HTML   # crawler-visible content

    def test_verification_language_is_precise(self):
        p = (LANDING_DIR / "Passport.jsx").read_text()
        assert "doesn't verify" in p and "degrees, licences or professional competence" in p
        assert "Self-declared" in p and "Connected" in p and "Verified" in p
        assert "not a real person" in p

    def test_preview_never_promises_free_discovery(self):
        q = (LANDING_DIR / "ResearchQuestion.jsx").read_text()
        assert "On Pro, this becomes a search for the people" in q
        assert "no people shown" in q

    def test_hero_h1_and_ctas(self):
        h = (LANDING_DIR / "Hero.jsx").read_text()
        assert ">Research starts with a question.</h1>" in h
        assert ">\n              Start Free\n" in h and "See how it works" in h
        assert "Request" not in h   # no demo request in the individual hero


class TestPublicPreviewStructure:
    def test_example_question_reading(self):
        from services.public_demo.research_preview import preview_research_themes
        s = preview_research_themes(
            "How can public hospitals reduce patient waiting times without increasing staff workload?")["structure"]
        assert s == {"kind": "aim", "objective": "reduce patient waiting times", "subject": "public hospitals",
                     "constraints": ["without increasing staff workload"]}

    def test_hero_figure_matches_engine(self):
        # Fig. 1 claims the constraint brings in operations research / workforce expertise.
        from services.public_demo.research_preview import preview_research_themes
        r = preview_research_themes(
            "How can public hospitals reduce patient waiting times without increasing staff workload?")
        assert "Operations Research" in r["complementary_disciplines"]
        assert "Management Studies" in r["themes"]

    def test_inquiry_and_empty(self):
        from services.public_demo.research_preview import preview_research_themes
        assert preview_research_themes("What drives vaccine hesitancy in rural areas?")["structure"]["kind"] == "inquiry"
        assert preview_research_themes("soil carbon")["structure"]["objective"] == ""

    def test_never_returns_people_fields(self):
        from services.public_demo.research_preview import preview_research_themes
        r = preview_research_themes("Who are the best oncologists at Harvard working on CAR-T?")
        assert set(r) == {"themes", "complementary_disciplines", "methods", "keywords", "structure", "matched_taxonomy"}

    def test_rate_limit_key_ignores_spoofed_forwarded_for(self):
        from starlette.requests import Request
        from routers.public_demo import _client_ip
        req = Request({"type": "http", "headers": [(b"x-forwarded-for", b"1.2.3.4, 10.0.0.9")], "client": ("10.0.0.1", 1)})
        assert _client_ip(req) == "10.0.0.9"
        req = Request({"type": "http", "headers": [(b"x-real-ip", b"203.0.113.7"), (b"x-forwarded-for", b"9.9.9.9")]})
        assert _client_ip(req) == "203.0.113.7"

    async def test_registration_status_endpoint(self, monkeypatch):
        from routers import auth
        async def _closed(db):
            return False
        monkeypatch.setattr(auth, "is_registration_open", _closed)
        monkeypatch.setattr(auth, "get_db", lambda: object())
        assert await auth.registration_status() == {"open": False}
