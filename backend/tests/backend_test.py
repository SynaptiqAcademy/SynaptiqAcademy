"""SYNAPTIQ Backend API Tests - covers auth, users, collabs, projects, messages, AI, analytics, etc.

Run with:
  pytest /app/backend/tests/backend_test.py -v --tb=short \
    --junitxml=/app/test_reports/pytest/pytest_results.xml
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to /app/frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

API = f"{BASE_URL}/api"

ELENA = ("elena.varga@synaptiq.io", "demo123")
MARCUS = ("marcus.okafor@synaptiq.io", "demo123")
AIKO = ("aiko.tanaka@synaptiq.io", "demo123")


# ----------------- Helpers / Fixtures -----------------

def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(s, email, password):
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def elena_session():
    s = _session()
    _login(s, *ELENA)
    return s


@pytest.fixture(scope="module")
def marcus_session():
    s = _session()
    _login(s, *MARCUS)
    return s


@pytest.fixture(scope="module")
def aiko_session():
    s = _session()
    _login(s, *AIKO)
    return s


# ----------------- Health -----------------

def test_health_root():
    r = requests.get(f"{API}/", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("service") == "SYNAPTIQ"


# ----------------- Auth -----------------

class TestAuth:
    def test_register_then_me(self):
        s = _session()
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "full_name": "TEST User"},
                   timeout=15)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        # API returns flat user object
        assert data.get("email") == email
        names = [c.name for c in s.cookies]
        assert "access_token" in names, f"no access_token cookie. cookies={names}"
        rme = s.get(f"{API}/auth/me", timeout=10)
        assert rme.status_code == 200
        me = rme.json()
        assert me["email"] == email

    def test_login_elena_and_me(self):
        s = _session()
        data = _login(s, *ELENA)
        # flat user object
        assert data.get("email") == ELENA[0]
        rme = s.get(f"{API}/auth/me", timeout=10)
        assert rme.status_code == 200
        assert rme.json()["email"] == ELENA[0]

    def test_login_wrong_password(self):
        s = _session()
        r = s.post(f"{API}/auth/login",
                   json={"email": ELENA[0], "password": "wrongpass"}, timeout=10)
        assert r.status_code == 401
        body = r.json()
        assert "detail" in body

    def test_logout_clears_cookie(self):
        s = _session()
        _login(s, *ELENA)
        rlog = s.post(f"{API}/auth/logout", timeout=10)
        assert rlog.status_code == 200
        # After logout, /me should be 401
        rme = s.get(f"{API}/auth/me", timeout=10)
        assert rme.status_code == 401, f"expected 401 after logout, got {rme.status_code}"


# ----------------- Users -----------------

class TestUsers:
    def test_patch_me(self, elena_session):
        new_bio = f"Updated bio {uuid.uuid4().hex[:6]}"
        payload = {
            "biography": new_bio,
            "research_areas": ["Cybersecurity", "AI"],
            "skills": ["Python", "PyTorch"],
        }
        r = elena_session.patch(f"{API}/users/me", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("biography") == new_bio
        # Persist check
        rme = elena_session.get(f"{API}/auth/me", timeout=10)
        assert rme.status_code == 200
        me = rme.json()
        assert me.get("biography") == new_bio
        assert "Cybersecurity" in me.get("research_areas", [])

    def test_search_by_q_cape(self, elena_session):
        r = elena_session.get(f"{API}/users", params={"q": "Cape"}, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        names = [u.get("full_name", "") for u in data]
        assert any("Marcus" in n or "Okafor" in n for n in names), f"Marcus not in result: {names}"

    def test_search_by_research_area_healthcare(self, elena_session):
        r = elena_session.get(f"{API}/users", params={"research_area": "Healthcare"}, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1, "No researcher found for Healthcare area"

    def test_get_user_by_id_and_404(self, elena_session):
        r = elena_session.get(f"{API}/users", params={"q": "Marcus"}, timeout=10)
        marcus = next((u for u in r.json() if "Okafor" in u.get("full_name", "")), None)
        assert marcus is not None
        uid = marcus["id"]
        rg = elena_session.get(f"{API}/users/{uid}", timeout=10)
        assert rg.status_code == 200
        assert rg.json()["id"] == uid
        # invalid id
        rb = elena_session.get(f"{API}/users/{'a' * 24}", timeout=10)
        assert rb.status_code == 404


# ----------------- Collaborations -----------------

class TestCollaborations:
    def test_list_open_collabs(self, elena_session):
        r = elena_session.get(f"{API}/collaborations", timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        # seed has 6 open collabs
        assert len(items) >= 6, f"expected >=6 seeded collabs, got {len(items)}"
        for it in items:
            assert "creator" in it and it["creator"].get("full_name")

    def test_filter_by_collab_type_journal(self, elena_session):
        r = elena_session.get(f"{API}/collaborations",
                              params={"collab_type": "Journal Article"}, timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert all(it.get("collab_type") == "Journal Article" for it in items)

    def test_create_collab_creates_project(self, elena_session):
        payload = {
            "title": f"TEST_Collab_{uuid.uuid4().hex[:6]}",
            "description": "Test description",
            "collab_type": "Journal Article",
            "research_area": "AI",
            "skills_needed": ["Python"],
            "team_size": 3,
            "duration": "3 months",
        }
        r = elena_session.post(f"{API}/collaborations", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data
        assert data.get("project_id"), "project_id should be returned after auto-create"
        # save for next tests
        pytest.created_collab_id = data["id"]
        pytest.created_project_id = data["project_id"]

    def test_apply_to_own_collab_400(self, elena_session):
        cid = pytest.created_collab_id
        r = elena_session.post(f"{API}/collaborations/{cid}/apply",
                               json={"message": "self"}, timeout=10)
        assert r.status_code == 400

    def test_apply_to_others_collab_flow(self, elena_session, marcus_session):
        cid = pytest.created_collab_id
        # marcus applies
        r1 = marcus_session.post(f"{API}/collaborations/{cid}/apply",
                                 json={"message": "I'd love to join"}, timeout=10)
        assert r1.status_code == 200, r1.text
        # second time should fail
        r2 = marcus_session.post(f"{API}/collaborations/{cid}/apply",
                                 json={"message": "again"}, timeout=10)
        assert r2.status_code == 400
        # creator lists applications
        rapps = elena_session.get(f"{API}/collaborations/{cid}/applications", timeout=10)
        assert rapps.status_code == 200
        apps = rapps.json()
        assert len(apps) >= 1
        app = apps[0]
        assert app["status"] == "pending"
        app_id = app["id"]
        applicant_id = app["applicant"]["id"]
        # accept
        rdec = elena_session.post(f"{API}/collaborations/applications/{app_id}/decide",
                                  json={"decision": "accepted"}, timeout=10)
        assert rdec.status_code == 200
        # verify status updated
        rapps2 = elena_session.get(f"{API}/collaborations/{cid}/applications", timeout=10)
        assert rapps2.status_code == 200
        new_status = next((a["status"] for a in rapps2.json() if a["id"] == app_id), None)
        assert new_status == "accepted"
        # verify applicant added to project members
        proj = elena_session.get(f"{API}/projects/{pytest.created_project_id}", timeout=10)
        assert proj.status_code == 200
        members = proj.json().get("members", [])
        assert applicant_id in members


# ----------------- Projects -----------------

class TestProjects:
    def test_list_projects(self, elena_session):
        r = elena_session.get(f"{API}/projects", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        # We created one above
        ids = [p.get("id") for p in r.json()]
        assert pytest.created_project_id in ids

    def test_get_project_detail_with_members_info(self, elena_session):
        pid = pytest.created_project_id
        r = elena_session.get(f"{API}/projects/{pid}", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == pid
        assert "members_info" in data
        assert isinstance(data["members_info"], list)

    def test_patch_project_fields(self, elena_session):
        pid = pytest.created_project_id
        payload = {
            "problem_statement": "Modeling adversarial drift",
            "objectives": ["o1", "o2"],
            "methodology": "Mixed methods",
        }
        r = elena_session.patch(f"{API}/projects/{pid}", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        rg = elena_session.get(f"{API}/projects/{pid}", timeout=10)
        body = rg.json()
        assert body.get("problem_statement") == "Modeling adversarial drift"
        assert body.get("methodology") == "Mixed methods"
        assert "o1" in body.get("objectives", [])

    def test_tasks_crud(self, elena_session):
        pid = pytest.created_project_id
        rc = elena_session.post(f"{API}/projects/{pid}/tasks",
                                json={"title": "TEST task"}, timeout=10)
        assert rc.status_code in (200, 201), rc.text
        task = rc.json()
        tid = task.get("id") or task.get("_id")
        assert tid
        rl = elena_session.get(f"{API}/projects/{pid}/tasks", timeout=10)
        assert rl.status_code == 200
        assert any((t.get("id") or t.get("_id")) == tid for t in rl.json())
        ru = elena_session.patch(f"{API}/projects/tasks/{tid}",
                                 json={"status": "done"}, timeout=10)
        assert ru.status_code == 200

    def test_literature_crud(self, elena_session):
        pid = pytest.created_project_id
        rc = elena_session.post(
            f"{API}/projects/{pid}/literature",
            json={"title": "TEST paper", "authors": "A", "year": 2024, "source_type": "Paper"},
            timeout=10)
        assert rc.status_code in (200, 201), rc.text
        rl = elena_session.get(f"{API}/projects/{pid}/literature", timeout=10)
        assert rl.status_code == 200
        titles = [x.get("title") for x in rl.json()]
        assert "TEST paper" in titles


# ----------------- Messages & Notifications -----------------

class TestMessages:
    def test_send_message_and_thread(self, elena_session, aiko_session):
        # Find aiko's id
        ru = elena_session.get(f"{API}/users", params={"q": "Aiko"}, timeout=10)
        aiko = next((u for u in ru.json() if "Aiko" in u.get("full_name", "")), None)
        assert aiko is not None
        aiko_id = aiko["id"]
        msg = f"TEST hello {uuid.uuid4().hex[:6]}"
        rs = elena_session.post(f"{API}/messages",
                                json={"recipient_id": aiko_id, "content": msg}, timeout=10)
        assert rs.status_code in (200, 201), rs.text
        # Thread retrieval - returns {messages: [...], other_user: {...}}
        rt = elena_session.get(f"{API}/messages/with/{aiko_id}", timeout=10)
        assert rt.status_code == 200
        thread_body = rt.json()
        assert "messages" in thread_body
        contents = [m.get("content") for m in thread_body["messages"]]
        assert msg in contents
        # Conversations list
        rc = elena_session.get(f"{API}/messages/conversations", timeout=10)
        assert rc.status_code == 200
        # Aiko should have a notification for this message
        rn = aiko_session.get(f"{API}/notifications", timeout=10)
        assert rn.status_code == 200


class TestNotifications:
    def test_mark_read(self, elena_session):
        rn = elena_session.get(f"{API}/notifications", timeout=10)
        assert rn.status_code == 200
        items = rn.json()
        if items:
            nid = items[0].get("id") or items[0].get("_id")
            r = elena_session.post(f"{API}/notifications/{nid}/read", timeout=10)
            assert r.status_code in (200, 204)


# ----------------- Discover & Analytics & AI -----------------

class TestDiscoverAnalytics:
    def test_discover_feed(self, elena_session):
        r = elena_session.get(f"{API}/discover/feed", timeout=15)
        assert r.status_code == 200
        data = r.json()
        for key in ("collaborations", "researchers", "trending_topics", "grants", "conferences"):
            assert key in data, f"missing key: {key}"

    def test_analytics_me(self, elena_session):
        r = elena_session.get(f"{API}/analytics/me", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict) and len(data) > 0


class TestAI:
    def test_recommend_collaborators(self, elena_session):
        r = elena_session.post(f"{API}/ai/recommend-collaborators", json={}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        recs = data if isinstance(data, list) else data.get("recommendations") or data.get("items") or []
        assert len(recs) >= 3, f"expected >=3 recs, got {len(recs)}: {data}"
        # each should have a reason field
        for rec in recs[:3]:
            assert "reason" in rec, f"missing reason in {rec}"
