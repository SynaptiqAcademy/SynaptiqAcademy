"""Phase 6 — AI matching + deadline intelligence tests.
Each AI matcher is called EXACTLY ONCE (35 credits total) to preserve Elena's balance.
"""
import os, time, pytest, requests
from pathlib import Path

def _read_env_url():
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return os.environ["REACT_APP_BACKEND_URL"]
    env = Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("REACT_APP_BACKEND_URL not found")

BASE = _read_env_url().rstrip("/")
MANUSCRIPT_ID = "6a2d843b404f238d2070afc2"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def elena():
    return _login("elena.varga@synaptiq.io", "demo123")


@pytest.fixture(scope="module")
def marcus():
    return _login("marcus.okafor@synaptiq.io", "demo123")


@pytest.fixture(scope="module")
def admin():
    return _login("admin@synaptiq.io", "admin123")


# -------- credit helpers --------
def _balance(sess):
    r = sess.get(f"{BASE}/api/auth/me", timeout=15)
    assert r.status_code == 200
    me = r.json()
    return me.get("credits_balance") or (me.get("credits") or {}).get("balance")


# ============================== DEADLINES ==============================
class TestDeadlines:
    def test_deadlines_mine_shape(self, elena):
        r = elena.get(f"{BASE}/api/deadlines/mine", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "counts" in d and "total" in d
        for k in ("missed", "critical", "due_soon", "upcoming"):
            assert k in d["counts"]
        # urgency sorting: missed first then critical etc
        order = {"missed": 0, "critical": 1, "due_soon": 2, "upcoming": 3}
        prev = -1
        for it in d["items"]:
            cur = order[it["urgency"]]
            assert cur >= prev, f"bad sort: {it['urgency']} after rank {prev}"
            prev = cur

    def test_deadlines_workspace_dashboard_embed(self, elena):
        # Find Elena's workspace; dashboard must include upcoming_deadlines
        r = elena.get(f"{BASE}/api/workspaces", timeout=15)
        assert r.status_code == 200
        wss = r.json()
        if not wss:
            pytest.skip("no workspaces")
        wid = wss[0].get("id") or wss[0].get("_id")
        r2 = elena.get(f"{BASE}/api/workspaces/{wid}/dashboard", timeout=20)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert "upcoming_deadlines" in body, f"missing upcoming_deadlines: keys={list(body.keys())}"
        assert isinstance(body["upcoming_deadlines"], list)


# ============================== MATCHING (LIVE LLM) ==============================
class TestAIMatching:
    """Each test calls real LLM — runs once. Order: journal→conference→grant→reviewer."""

    def test_01_journal(self, elena):
        before = _balance(elena)
        r = elena.post(f"{BASE}/api/matching/journal",
                       json={"manuscript_id": MANUSCRIPT_ID, "top_n": 6}, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["credits_consumed"] == 10
        assert "request_id" in d and "manuscript_id" in d
        assert isinstance(d["recommendations"], list) and len(d["recommendations"]) > 0
        first = d["recommendations"][0]
        for k in ("journal", "score", "rationale", "concerns"):
            assert k in first, f"missing {k}: {first}"
        assert 0 <= first["score"] <= 100
        for k in ("id", "title"):
            assert k in first["journal"]
        if before is not None:
            after = _balance(elena)
            assert after == before - 10, f"credits not decremented: {before}->{after}"

    def test_02_conference(self, elena):
        r = elena.post(f"{BASE}/api/matching/conference",
                       json={"manuscript_id": MANUSCRIPT_ID, "top_n": 6}, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["credits_consumed"] == 5
        assert len(d["recommendations"]) > 0
        c0 = d["recommendations"][0]
        assert "conference" in c0 and "score" in c0
        assert "id" in c0["conference"] and "name" in c0["conference"]

    def test_03_grant(self, elena):
        r = elena.post(f"{BASE}/api/matching/grant",
                       json={"manuscript_id": MANUSCRIPT_ID, "top_n": 6}, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["credits_consumed"] == 10
        assert len(d["recommendations"]) > 0
        g0 = d["recommendations"][0]
        assert "grant" in g0 and "score" in g0
        assert g0.get("eligibility_match") in ("high", "medium", "low")

    def test_04_reviewer(self, elena):
        r = elena.post(f"{BASE}/api/matching/reviewer",
                       json={"manuscript_id": MANUSCRIPT_ID, "top_n": 6}, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["credits_consumed"] == 10
        assert len(d["recommendations"]) > 0
        rv = d["recommendations"][0]
        assert "reviewer" in rv and "expertise_areas" in rv
        assert rv["collaboration_risk"] in ("low", "high")
        # Must NOT include manuscript authors
        # Get manuscript authors and assert no reviewer ID overlaps
        m = elena.get(f"{BASE}/api/manuscripts/{MANUSCRIPT_ID}", timeout=15)
        if m.status_code == 200:
            authors = set(m.json().get("authors") or [])
            rev_ids = {r0["reviewer"]["id"] for r0 in d["recommendations"]}
            assert not (authors & rev_ids), "reviewer set includes manuscript authors"

    def test_05_forbidden_non_author(self, admin):
        # Admin is not an author of Elena's manuscript -> 403 (or 404)
        r = admin.post(f"{BASE}/api/matching/journal",
                       json={"manuscript_id": MANUSCRIPT_ID, "top_n": 3}, timeout=30)
        assert r.status_code in (403, 404), f"expected 403/404 got {r.status_code}: {r.text[:200]}"


# ============================== HISTORY + ANALYTICS ==============================
class TestHistoryAnalytics:
    def test_history_journal(self, elena):
        r = elena.get(f"{BASE}/api/matching/history?kind=journal_matching&limit=10", timeout=20)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        if rows:
            assert rows[0]["kind"] == "journal_matching"
            assert "credits_consumed" in rows[0]
            # _id must be stringified (no ObjectId leakage)
            assert isinstance(rows[0].get("_id"), str)

    def test_history_all(self, elena):
        r = elena.get(f"{BASE}/api/matching/history?limit=30", timeout=20)
        assert r.status_code == 200
        rows = r.json()
        kinds = {x["kind"] for x in rows}
        # After 4 matchers we expect at least one of each
        for k in ("journal_matching", "conference_matching", "grant_matching", "reviewer_matching"):
            assert k in kinds, f"expected {k} in history; got {kinds}"

    def test_analytics_user_scope(self, elena):
        r = elena.get(f"{BASE}/api/matching/analytics", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["scope"] == "user"
        data = body["data"]
        assert "by_kind" in data and isinstance(data["by_kind"], list)
        assert "recent" in data

    def test_analytics_admin_global(self, admin):
        r = admin.get(f"{BASE}/api/matching/analytics", timeout=20)
        assert r.status_code == 200
        assert r.json()["scope"] == "global"
