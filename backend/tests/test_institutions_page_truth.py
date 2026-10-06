"""/for-institutions: claims bound to the institution model, no pricing or
checkout, no fabricated proof, Contact Sales posts to the real endpoint."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_landing_commercial_truth import STALE, FABRICATION, UNSAFE, GENERIC, _visible_text

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
SRC = (ROOT / "frontend" / "src" / "pages" / "InstitutionsLanding.jsx").read_text()
TEXT = _visible_text(SRC)

BANNED = [r"€", r"checkout", r"[Bb]uy ", r"[Tt]rial", r"[Ss]tart Institutional", r"Choose Institution",
          r"SOC ?2", r"ISO ?27001", r"HIPAA", r"GDPR", r"[Ee]nterprise-grade", r"[Tt]rusted by",
          r"Harvard|Oxford|\bMIT\b|Stanford|Cambridge|Karolinska|Charit|\bETH\b|CNRS",
          r"real[- ]time", r"[Mm]onitor", r"[Tt]rack (your )?(researchers|faculty)", r"productivity",
          r"\bROI\b", r"360", r"single pane", r"[Tt]alent", r"[Hh]uman capital", r"[Ee]mpower",
          r"[Uu]nlock", r"24 hours", r"per seat", r"seats?\b", r"AI Credits", r"\b\d+%"]


@pytest.mark.parametrize("pattern", STALE + FABRICATION + UNSAFE + GENERIC + BANNED)
def test_no_unsupported_claims(pattern):
    assert not re.search(pattern, TEXT), pattern


def test_contact_sales_is_the_only_commercial_action():
    assert 'api.post("/contact"' in SRC and 'topic: "institution"' in SRC
    assert "Contact Sales" in SRC and "Pricing is custom" in SRC
    assert 'to="/pricing"' not in SRC
    contact = (BACKEND / "routers" / "contact.py").read_text()
    assert '"institution"' in contact and "organization" in contact


def test_membership_claims_match_the_model():
    inst = (BACKEND / "routers" / "institutions.py").read_text()
    for via in ('"email_domain"', '"admin_approval"', '"admin_invite"'):
        assert via in inst, via
    assert "institutional email domain, an invitation the person accepts, or an admin's review of evidence" in SRC
    perms = (BACKEND / "services" / "permissions.py").read_text()
    assert '"status": "approved"' in perms
    assert "A name typed into a profile or an ORCID affiliation is not membership" in SRC


def test_department_roles_use_product_labels():
    dept = (BACKEND / "routers" / "departments.py").read_text()
    assert '"Department Admin"' in dept and '"Research Coordinator"' in dept
    assert "Department admin" in SRC and "Research coordinator" in SRC


def test_people_and_institutions_are_illustrative():
    assert "Illustrative institution" in SRC
    names = set(re.findall(r"Researcher \d\d", SRC)) | set(re.findall(r'\["(\d\d)"', SRC))
    assert names and not re.search(r"\b(Dr|Prof)\.", SRC)


def test_analytics_never_carries_form_content():
    for call in re.findall(r"track\(([^)]*)\)", SRC):
        assert not re.search(r"\bf\.|email|message|organization|name\b", call), call
