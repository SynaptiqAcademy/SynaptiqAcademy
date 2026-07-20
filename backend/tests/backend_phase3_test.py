"""
Phase III backend tests: auth password flows, onboarding enforcement, marketing,
billing/plans/subscription, credits, Stripe-ready endpoints.
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read from frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ELENA_EMAIL = "elena.varga@synaptiq.io"
ELENA_PASS = "demo123"
ADMIN_EMAIL = "admin@synaptiq.io"
ADMIN_PASS = "admin123"


# ============== Fixtures ==============
@pytest.fixture(scope="session")
def elena_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ELENA_EMAIL, "password": ELENA_PASS})
    assert r.status_code == 200, f"Elena login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture()
def fresh_user():
    """Register a brand new user. Returns (session, email, password, user)."""
    s = requests.Session()
    email = f"phase3_{uuid.uuid4().hex[:8]}@example.com"
    password = "freshpass123"
    r = s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "password": password, "full_name": "Fresh User"})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return {"session": s, "email": email, "password": password, "user": r.json()}


# ============== Phase I/II regression ==============
class TestRegression:
    def test_elena_login(self, elena_session):
        r = elena_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ELENA_EMAIL
        assert r.json().get("onboarded") is True, "Elena should be onboarded after seed backfill"

    def test_discover_feed(self, elena_session):
        r = elena_session.get(f"{BASE_URL}/api/discover/feed")
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))

    def test_manuscripts_list(self, elena_session):
        r = elena_session.get(f"{BASE_URL}/api/manuscripts")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1, "Expected at least one seeded manuscript"


# ============== Auth: Register ==============
class TestRegister:
    def test_register_creates_free_user(self, fresh_user):
        user = fresh_user["user"]
        assert user["email"] == fresh_user["email"]
        assert user.get("onboarded") is False
        assert user.get("plan_code") == "free"
        assert user.get("credits_balance") == 100

    def test_me_returns_same_user(self, fresh_user):
        r = fresh_user["session"].get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == fresh_user["email"]
        assert r.json().get("onboarded") is False


# ============== Auth: Forgot / Reset / Change ==============
class TestPasswordFlows:
    def test_forgot_password_existing(self):
        r = requests.post(f"{BASE_URL}/api/auth/forgot-password",
                          json={"email": ELENA_EMAIL})
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert data.get("debug_reset_token"), "EXPOSE_RESET_TOKEN=1 should surface token"

    def test_forgot_password_unknown_no_enum(self):
        r = requests.post(f"{BASE_URL}/api/auth/forgot-password",
                          json={"email": f"nope_{uuid.uuid4().hex[:6]}@x.com"})
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_reset_password_full_cycle(self, fresh_user):
        email = fresh_user["email"]
        old_pw = fresh_user["password"]
        new_pw = "newpass456"
        # forgot
        r = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        token = r.json()["debug_reset_token"]
        # reset
        r = requests.post(f"{BASE_URL}/api/auth/reset-password",
                          json={"token": token, "new_password": new_pw})
        assert r.status_code == 200, r.text
        # old password fails
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": email, "password": old_pw})
        assert r.status_code == 401
        # new password works
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": email, "password": new_pw})
        assert r.status_code == 200

    def test_change_password_wrong_current(self, fresh_user):
        r = fresh_user["session"].post(f"{BASE_URL}/api/auth/change-password",
                                       json={"current_password": "wrong", "new_password": "abc1234"})
        assert r.status_code == 400

    def test_change_password_correct(self, fresh_user):
        r = fresh_user["session"].post(f"{BASE_URL}/api/auth/change-password",
                                       json={"current_password": fresh_user["password"],
                                             "new_password": "changed789"})
        assert r.status_code == 200
        # login with new
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": fresh_user["email"], "password": "changed789"})
        assert r.status_code == 200


# ============== Onboarding enforcement ==============
class TestOnboarding:
    def test_complete_onboarding(self, fresh_user):
        s = fresh_user["session"]
        payload = {
            "first_name": "Fresh",
            "last_name": "User",
            "country": "Switzerland",
            "user_type": "phd_candidate",
            "primary_domain": "research",
            "academic_role": "PhD Candidate",
            "institution": "ETH Zurich",
            "department": "Computer Science",
            "research_areas": ["AI"],
            "research_interests": ["LLMs"],
            "research_keywords": ["transformers"],
        }
        r = s.post(f"{BASE_URL}/api/users/me/onboarding", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("onboarded") is True
        assert body.get("full_name") == "Fresh User"

        # Verify persistence
        r2 = s.get(f"{BASE_URL}/api/auth/me")
        assert r2.json().get("onboarded") is True


# ============== Marketing pages ==============
class TestMarketingPages:
    @pytest.mark.parametrize("path", [
        "/pricing", "/platform", "/contact",
        "/terms", "/privacy", "/gdpr", "/cookies", "/security",
    ])
    def test_marketing_page_200(self, path):
        r = requests.get(f"{BASE_URL}{path}", allow_redirects=True)
        assert r.status_code == 200, f"{path} returned {r.status_code}"


# ============== Billing: plans / subscription / Stripe ==============
class TestBilling:
    def test_plans(self):
        r = requests.get(f"{BASE_URL}/api/billing/plans")
        assert r.status_code == 200
        plans = r.json()
        assert len(plans) == 3
        by_code = {p["code"]: p for p in plans}
        assert set(by_code.keys()) == {"free", "researcher", "institution"}
        assert by_code["free"]["credits_per_month"] == 100
        assert by_code["researcher"]["credits_per_month"] == 2000
        assert by_code["institution"]["credits_per_month"] == 50000
        assert by_code["free"]["price_eur_monthly"] == 0
        assert by_code["researcher"]["price_eur_monthly"] == 19
        assert by_code["researcher"]["price_eur_annual"] == 15
        assert by_code["institution"]["price_eur_monthly"] == 199
        assert by_code["institution"]["price_eur_annual"] == 159

    def test_subscription_elena(self, elena_session):
        r = elena_session.get(f"{BASE_URL}/api/billing/subscription")
        assert r.status_code == 200
        body = r.json()
        assert body["plan"]["code"] == "free"
        assert body["credits"]["balance"] >= 0
        assert body["stripe_configured"] is False

    def test_checkout_session_returns_503_structured(self, elena_session):
        r = elena_session.post(f"{BASE_URL}/api/billing/checkout-session",
                               json={"plan_code": "researcher", "billing_period": "monthly"})
        assert r.status_code == 503
        body = r.json()
        # FastAPI HTTPException wraps detail under 'detail'
        detail = body.get("detail")
        assert detail is not None
        assert "Stripe is not yet configured" in str(detail)

    def test_portal_session_503(self, elena_session):
        r = elena_session.post(f"{BASE_URL}/api/billing/portal-session", json={})
        assert r.status_code == 503

    def test_webhook_persists(self, elena_session):
        evt_type = f"test.event.{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{BASE_URL}/api/billing/webhook",
                          json={"type": evt_type, "data": {"id": "evt_test"}})
        assert r.status_code == 200
        assert r.json().get("received") is True


# ============== Credits ==============
class TestCredits:
    def test_balance(self, elena_session):
        r = elena_session.get(f"{BASE_URL}/api/credits/balance")
        assert r.status_code == 200
        data = r.json()
        assert "plan_code" in data
        assert "balance" in data
        assert "monthly_allowance" in data
        assert "reset_at" in data
        assert "costs" in data
        assert data["costs"]["ai_collaborator_matching"] == 10

    def test_consume_via_collaborator_matching(self, fresh_user):
        """Use fresh_user (not Elena) so we can also exhaust later."""
        s = fresh_user["session"]
        # Complete onboarding first (some endpoints may require it)
        s.post(f"{BASE_URL}/api/users/me/onboarding", json={
            "first_name": "Fresh", "last_name": "User",
            "country": "CH", "user_type": "phd_candidate", "primary_domain": "research",
            "academic_role": "PhD", "institution": "ETH", "department": "CS",
            "research_areas": ["AI"], "research_interests": ["LLMs"],
            "research_keywords": ["transformers"],
        })
        b0 = s.get(f"{BASE_URL}/api/credits/balance").json()["balance"]
        r = s.post(f"{BASE_URL}/api/ai/recommend-collaborators", json={})
        # 200 expected if LLM works; either way credits should consume on success
        if r.status_code != 200:
            pytest.skip(f"AI endpoint returned {r.status_code}: {r.text[:200]}")
        b1 = s.get(f"{BASE_URL}/api/credits/balance").json()["balance"]
        assert b1 == b0 - 10, f"balance went {b0} -> {b1}"
        # usage entry recorded
        usage = s.get(f"{BASE_URL}/api/credits/usage").json()
        assert any(u["action"] == "ai_collaborator_matching" and u["amount"] == 10 for u in usage)

    def test_insufficient_credits_exhaust(self, fresh_user):
        s = fresh_user["session"]
        # Complete onboarding
        s.post(f"{BASE_URL}/api/users/me/onboarding", json={
            "first_name": "Fresh", "last_name": "User",
            "country": "CH", "user_type": "phd_candidate", "primary_domain": "research",
            "academic_role": "PhD", "institution": "ETH", "department": "CS",
            "research_areas": ["AI"], "research_interests": ["LLMs"],
            "research_keywords": ["transformers"],
        })
        # Fresh user has 100 credits => 10 calls @ 10 credits drains it
        last_status = None
        last_body = None
        for i in range(12):
            r = s.post(f"{BASE_URL}/api/ai/recommend-collaborators", json={})
            last_status = r.status_code
            last_body = r.text
            if r.status_code == 402:
                break
            time.sleep(0.2)
        assert last_status == 402, f"Expected 402 after exhausting credits, got {last_status}: {last_body[:200]}"
        body = {}
        try:
            body = r.json()
        except Exception:
            pass
        detail = body.get("detail")
        assert "Insufficient research credits" in str(detail)
