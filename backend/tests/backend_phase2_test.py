"""SYNAPTIQ Phase II Backend API Tests.

Covers: Journals, Conferences, Funding, Grants, Workspaces, Manuscripts,
Publication Hub, Repository + permissions and Phase I regression.

Run with:
  pytest /app/backend/tests/backend_phase2_test.py -v --tb=short \
    --junitxml=/app/test_reports/pytest/pytest_phase2.xml
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
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


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(s, email, password):
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def elena():
    s = _session()
    _login(s, *ELENA)
    return s


@pytest.fixture(scope="module")
def marcus():
    s = _session()
    _login(s, *MARCUS)
    return s


@pytest.fixture(scope="module")
def aiko():
    s = _session()
    _login(s, *AIKO)
    return s


# -------- Phase I Regression --------
class TestPhase1Regression:
    def test_login_elena_me(self, elena):
        r = elena.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ELENA[0]

    def test_collaborations_seeded(self, elena):
        r = elena.get(f"{API}/collaborations", timeout=10)
        assert r.status_code == 200
        assert len(r.json()) >= 6

    def test_projects_list(self, elena):
        r = elena.get(f"{API}/projects", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_discover_feed(self, elena):
        r = elena.get(f"{API}/discover/feed", timeout=15)
        assert r.status_code == 200
        data = r.json()
        for key in ("collaborations", "researchers", "grants", "conferences", "trending_topics"):
            assert key in data, f"missing key {key}"


# -------- Journals --------
class TestJournals:
    def test_list_journals(self, elena):
        r = elena.get(f"{API}/journals", timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 10, f"expected ~12 journals, got {len(items)}"

    def test_filter_subject_healthcare(self, elena):
        r = elena.get(f"{API}/journals", params={"subject": "Healthcare"}, timeout=10)
        assert r.status_code == 200
        items = r.json()
        names = [j.get("title", "") or j.get("name", "") for j in items]
        # Lancet/JAMA should be present
        assert any("Lancet" in n or "JAMA" in n for n in names), f"healthcare filter missing Lancet/JAMA. names={names}"

    def test_filter_q1_open_access(self, elena):
        r = elena.get(f"{API}/journals", params={"quartile": "Q1", "open_access": "true"}, timeout=10)
        assert r.status_code == 200
        items = r.json()
        names = [j.get("title", "") or j.get("name", "") for j in items]
        for j in items:
            assert j.get("quartile") == "Q1"
            assert j.get("open_access") in (True, "true", 1)
        # At least one of these should be present
        assert any("Nature" in n or "PLOS" in n for n in names), f"expected Nature/PLOS ONE. names={names}"

    def test_get_journal_detail(self, elena):
        r = elena.get(f"{API}/journals", timeout=10)
        jid = r.json()[0]["id"]
        rd = elena.get(f"{API}/journals/{jid}", timeout=10)
        assert rd.status_code == 200
        assert rd.json()["id"] == jid


# -------- Conferences --------
class TestConferences:
    def test_list_conferences(self, elena):
        r = elena.get(f"{API}/conferences", timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 8, f"expected ~10, got {len(items)}"

    def test_filter_ai(self, elena):
        r = elena.get(f"{API}/conferences", params={"research_area": "Artificial Intelligence"}, timeout=10)
        assert r.status_code == 200
        # Items may or may not be present, just ensure 200 returned a list
        assert isinstance(r.json(), list)

    def test_get_conference_detail(self, elena):
        r = elena.get(f"{API}/conferences", timeout=10)
        cid = r.json()[0]["id"]
        rd = elena.get(f"{API}/conferences/{cid}", timeout=10)
        assert rd.status_code == 200
        data = rd.json()
        # Check topics/organizer/important_dates fields exist (may be empty for legacy)
        assert "topics" in data or "organizer" in data or "important_dates" in data


# -------- Funding --------
class TestFunding:
    def test_list_funding(self, elena):
        r = elena.get(f"{API}/funding", timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 10, f"expected ~12, got {len(items)}"
        first = items[0]
        # Field validation
        for key in ("amount", "deadline", "agency"):
            assert key in first, f"missing {key} in funding item"

    def test_get_funding_detail(self, elena):
        items = elena.get(f"{API}/funding", timeout=10).json()
        fid = items[0]["id"]
        rd = elena.get(f"{API}/funding/{fid}", timeout=10)
        assert rd.status_code == 200
        assert rd.json()["id"] == fid


# -------- Grants --------
class TestGrants:
    def test_grants_overview_shape(self, elena):
        r = elena.get(f"{API}/grants", timeout=10)
        assert r.status_code == 200
        data = r.json()
        for k in ("discover", "saved", "recommended", "tracking"):
            assert k in data, f"missing key {k}"

    def test_save_unsave_grant(self, elena):
        items = elena.get(f"{API}/grants", timeout=10).json().get("discover", [])
        assert items, "no discover grants"
        gid = items[0]["id"]
        # save
        rs = elena.post(f"{API}/grants/{gid}/save", timeout=10)
        assert rs.status_code in (200, 201)
        # verify in saved
        saved = elena.get(f"{API}/grants", timeout=10).json().get("saved", [])
        saved_ids = [g["id"] for g in saved]
        assert gid in saved_ids, f"saved grant not visible. saved_ids={saved_ids}"
        # unsave
        ru = elena.post(f"{API}/grants/{gid}/unsave", timeout=10)
        assert ru.status_code in (200, 201)
        saved2 = elena.get(f"{API}/grants", timeout=10).json().get("saved", [])
        assert gid not in [g["id"] for g in saved2]


# -------- Workspaces --------
class TestWorkspaces:
    def test_list_workspaces(self, elena):
        r = elena.get(f"{API}/workspaces", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_get_activity(self, elena):
        # create
        name = f"TEST_WS_{uuid.uuid4().hex[:6]}"
        rc = elena.post(f"{API}/workspaces",
                        json={"name": name, "description": "TEST workspace"}, timeout=10)
        assert rc.status_code in (200, 201), rc.text
        ws = rc.json()
        assert ws["name"] == name
        wid = ws["id"]
        pytest.created_workspace_id = wid

        # get detail
        rd = elena.get(f"{API}/workspaces/{wid}", timeout=10)
        assert rd.status_code == 200
        detail = rd.json()
        for k in ("members_info", "projects", "activity", "documents"):
            assert k in detail, f"missing {k} in workspace detail"

        # add activity (backend expects 'message' and 'kind')
        ra = elena.post(f"{API}/workspaces/{wid}/activity",
                        json={"kind": "note", "message": "TEST note"}, timeout=10)
        assert ra.status_code in (200, 201)
        # verify activity present
        rd2 = elena.get(f"{API}/workspaces/{wid}", timeout=10).json()
        assert any(a.get("message") == "TEST note" for a in rd2.get("activity", [])), \
            f"note not in activity: {rd2.get('activity')}"

    def test_workspace_permissions(self, elena, marcus):
        wid = pytest.created_workspace_id
        r = marcus.get(f"{API}/workspaces/{wid}", timeout=10)
        assert r.status_code == 403, f"expected 403 for non-member, got {r.status_code}"


# -------- Manuscripts --------
class TestManuscripts:
    def test_list_manuscripts(self, elena):
        r = elena.get(f"{API}/manuscripts", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_and_default_sections(self, elena):
        title = f"TEST_Manuscript_{uuid.uuid4().hex[:6]}"
        rc = elena.post(f"{API}/manuscripts",
                        json={"title": title}, timeout=10)
        assert rc.status_code in (200, 201), rc.text
        m = rc.json()
        assert m["title"] == title
        mid = m["id"]
        pytest.created_manuscript_id = mid

        # Get detail and check sections
        rd = elena.get(f"{API}/manuscripts/{mid}", timeout=10)
        assert rd.status_code == 200
        d = rd.json()
        sections = d.get("sections", {})
        expected = ["title", "abstract", "introduction", "literature_review",
                    "methodology", "results", "discussion", "conclusion", "references"]
        for sec in expected:
            assert sec in sections, f"missing section {sec}. got: {list(sections.keys())}"
        assert "authors_info" in d
        assert "target_journal" in d or "target_journal_id" in d

    def test_update_sections(self, elena):
        mid = pytest.created_manuscript_id
        new_sections = {"introduction": "This is a TEST intro."}
        r = elena.patch(f"{API}/manuscripts/{mid}",
                        json={"sections": new_sections}, timeout=10)
        assert r.status_code == 200, r.text
        # verify
        rd = elena.get(f"{API}/manuscripts/{mid}", timeout=10).json()
        assert rd["sections"].get("introduction") == "This is a TEST intro."

    def test_add_author(self, elena, marcus):
        mid = pytest.created_manuscript_id
        # Find Marcus
        ru = elena.get(f"{API}/users", params={"q": "Marcus"}, timeout=10).json()
        m_user = next((u for u in ru if "Okafor" in u.get("full_name", "")), None)
        assert m_user
        marcus_id = m_user["id"]
        ra = elena.post(f"{API}/manuscripts/{mid}/authors",
                        json={"user_id": marcus_id}, timeout=10)
        assert ra.status_code in (200, 201), ra.text

    def test_manuscript_permissions(self, aiko):
        mid = pytest.created_manuscript_id
        r = aiko.get(f"{API}/manuscripts/{mid}", timeout=10)
        assert r.status_code == 403, f"expected 403, got {r.status_code}"


# -------- Publication Hub --------
class TestPublicationHub:
    def test_pipeline(self, elena):
        r = elena.get(f"{API}/publication-hub/pipeline", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "stages" in data
        assert "stage_order" in data
        # stage_order should have 6 entries
        assert len(data["stage_order"]) == 6, f"expected 6 stages, got {data['stage_order']}"

    def test_change_status(self, elena):
        mid = pytest.created_manuscript_id
        for status in ("under_review", "revision_requested", "draft"):
            r = elena.post(f"{API}/publication-hub/manuscripts/{mid}/status",
                           json={"status": status}, timeout=10)
            assert r.status_code in (200, 201), f"{status}: {r.text}"
        # invalid status
        rbad = elena.post(f"{API}/publication-hub/manuscripts/{mid}/status",
                          json={"status": "nope"}, timeout=10)
        assert rbad.status_code in (400, 422)


# -------- Repository --------
class TestRepository:
    def test_list_repository(self, elena):
        r = elena.get(f"{API}/repository", timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 3, f"expected 4-8 seeded items, got {len(items)}"

    def test_filter_dataset(self, elena):
        r = elena.get(f"{API}/repository", params={"item_type": "Dataset"}, timeout=10)
        assert r.status_code == 200
        for it in r.json():
            assert it.get("type") == "Dataset", f"non-dataset returned: {it}"

    def test_create_document(self, elena):
        title = f"TEST_Doc_{uuid.uuid4().hex[:6]}"
        rc = elena.post(f"{API}/repository",
                        json={"title": title, "type": "Document",
                              "description": "TEST doc",
                              "tags": ["test", "phase2"]}, timeout=10)
        assert rc.status_code in (200, 201), rc.text
        item = rc.json()
        assert item["title"] == title
        assert "test" in item.get("tags", [])
        iid = item["id"]
        # GET single
        rg = elena.get(f"{API}/repository/{iid}", timeout=10)
        assert rg.status_code == 200
        assert rg.json()["id"] == iid
