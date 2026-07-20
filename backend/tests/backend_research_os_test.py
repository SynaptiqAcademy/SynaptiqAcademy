"""Phase Research OS — Workspace dashboards/invitations/roles + Manuscript
versions/comments/contributions/authors/dashboard tests.

Run:
  pytest /app/backend/tests/backend_research_os_test.py -v --tb=short
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ELENA = {"email": "elena.varga@synaptiq.io", "password": "demo123"}
MARCUS = {"email": "marcus.okafor@synaptiq.io", "password": "demo123"}
AIKO = {"email": "aiko.tanaka@synaptiq.io", "password": "demo123"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    me = s.get(f"{API}/auth/me", timeout=10)
    assert me.status_code == 200
    return s, me.json()


@pytest.fixture(scope="module")
def elena():
    return _login(ELENA)


@pytest.fixture(scope="module")
def marcus():
    return _login(MARCUS)


@pytest.fixture(scope="module")
def aiko():
    return _login(AIKO)


@pytest.fixture(scope="module")
def workspace(elena):
    s_e, _ = elena
    payload = {
        "name": f"TEST_RO_Lab_{int(time.time())}",
        "description": "Research OS phase test workspace",
        "research_domain": "AI/Cybersecurity",
    }
    r = s_e.post(f"{API}/workspaces", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    return r.json()


# ============== Static lookups ==============
class TestStaticLookups:
    def test_workspace_roles(self, elena):
        s, _ = elena
        r = s.get(f"{API}/research-os/workspace-roles", timeout=10)
        assert r.status_code == 200
        roles = r.json()
        assert isinstance(roles, list)
        for role in ["Owner", "Principal Investigator", "Co-Investigator", "Researcher", "Reviewer", "Observer"]:
            assert role in roles

    def test_task_statuses(self, elena):
        s, _ = elena
        r = s.get(f"{API}/research-os/task-statuses", timeout=10)
        assert r.status_code == 200
        ts = r.json()
        for x in ["backlog", "planned", "in_progress", "review", "completed"]:
            assert x in ts

    def test_manuscript_statuses(self, elena):
        s, _ = elena
        r = s.get(f"{API}/research-os/manuscript-statuses", timeout=10)
        assert r.status_code == 200
        ms = r.json()
        for x in ["draft", "internal_review", "ready_for_submission", "submitted", "accepted", "published"]:
            assert x in ms


# ============== Workspace creation + Owner auto-assign ==============
class TestWorkspaceCreate:
    def test_create_assigns_owner_role(self, elena, workspace):
        s_e, me = elena
        # Hit dashboard to confirm your_role == Owner
        r = s_e.get(f"{API}/workspaces/{workspace['id']}/dashboard", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["your_role"] == "Owner"
        assert body["workspace"]["owner_id"] == me["id"]
        # member_roles map should have owner→Owner
        mr = body["workspace"].get("member_roles", {})
        assert mr.get(me["id"]) == "Owner", f"expected member_roles[owner]=Owner, got: {mr}"


# ============== Dashboard shape + 403 ==============
class TestWorkspaceDashboard:
    def test_dashboard_shape(self, elena, workspace):
        s, _ = elena
        r = s.get(f"{API}/workspaces/{workspace['id']}/dashboard", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ["workspace", "your_role", "counts", "research_health", "projects",
                  "manuscripts", "upcoming_milestones", "recent_activity"]:
            assert k in body, f"missing {k}"
        for ck in ["members", "active_projects", "active_manuscripts",
                   "tasks_completed", "tasks_total", "milestones_completed", "milestones_total"]:
            assert ck in body["counts"], f"missing counts.{ck}"
        assert 0 <= body["research_health"] <= 100

    def test_non_member_dashboard_403(self, aiko, workspace):
        s_a, _ = aiko
        r = s_a.get(f"{API}/workspaces/{workspace['id']}/dashboard", timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"


# ============== Invitations ==============
class TestInvitations:
    def test_invite_and_accept(self, elena, marcus, workspace):
        s_e, _ = elena
        s_m, me_m = marcus
        # Invite Marcus
        r = s_e.post(f"{API}/workspaces/{workspace['id']}/invitations",
                     json={"user_id": me_m["id"], "role": "Co-Investigator"}, timeout=15)
        assert r.status_code == 200, r.text
        inv = r.json()
        assert inv["status"] == "pending"
        # Marcus lists own invitations
        my = s_m.get(f"{API}/workspaces/invitations/mine", timeout=15)
        assert my.status_code == 200
        invs = my.json()
        match = [i for i in invs if i["id"] == inv["id"]]
        assert match, "invitation not in /mine"
        # Marcus accepts
        ra = s_m.post(f"{API}/workspaces/invitations/{inv['id']}/respond",
                      json={"decision": "accept"}, timeout=15)
        assert ra.status_code == 200, ra.text
        assert ra.json()["status"] == "accepted"
        # Verify Marcus is now a member with role Co-Investigator
        dash = s_m.get(f"{API}/workspaces/{workspace['id']}/dashboard", timeout=15)
        assert dash.status_code == 200, dash.text
        assert dash.json()["your_role"] == "Co-Investigator"

    def test_invite_non_admin_403(self, marcus, aiko, workspace):
        s_m, _ = marcus
        _, me_a = aiko
        # Marcus is Co-Investigator (after previous test) — cannot invite
        r = s_m.post(f"{API}/workspaces/{workspace['id']}/invitations",
                     json={"user_id": me_a["id"], "role": "Researcher"}, timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"

    def test_invite_decline(self, elena, aiko, workspace):
        s_e, _ = elena
        s_a, me_a = aiko
        r = s_e.post(f"{API}/workspaces/{workspace['id']}/invitations",
                     json={"user_id": me_a["id"], "role": "Researcher"}, timeout=15)
        assert r.status_code == 200, r.text
        iid = r.json()["id"]
        rd = s_a.post(f"{API}/workspaces/invitations/{iid}/respond",
                      json={"decision": "decline"}, timeout=15)
        assert rd.status_code == 200
        assert rd.json()["status"] == "declined"
        # Aiko should NOT be a member
        dash = s_a.get(f"{API}/workspaces/{workspace['id']}/dashboard", timeout=15)
        assert dash.status_code == 403


# ============== Role management ==============
class TestRoleManagement:
    def test_promote_marcus_to_pi(self, elena, marcus, workspace):
        s_e, _ = elena
        _, me_m = marcus
        r = s_e.patch(f"{API}/workspaces/{workspace['id']}/members/{me_m['id']}/role",
                      json={"role": "Principal Investigator"}, timeout=15)
        assert r.status_code == 200, r.text
        # verify
        dash = s_e.get(f"{API}/workspaces/{workspace['id']}/dashboard", timeout=15)
        assert dash.json()["workspace"]["member_roles"][me_m["id"]] == "Principal Investigator"

    def test_cannot_promote_to_owner(self, elena, marcus, workspace):
        s_e, _ = elena
        _, me_m = marcus
        r = s_e.patch(f"{API}/workspaces/{workspace['id']}/members/{me_m['id']}/role",
                      json={"role": "Owner"}, timeout=15)
        assert r.status_code == 400

    def test_non_admin_cannot_change_role(self, elena, marcus, aiko, workspace):
        # First invite & accept Aiko as Researcher
        s_e, _ = elena
        s_a, me_a = aiko
        r = s_e.post(f"{API}/workspaces/{workspace['id']}/invitations",
                     json={"user_id": me_a["id"], "role": "Researcher"}, timeout=15)
        if r.status_code == 200:
            inv = r.json()
            # only accept if pending
            if inv["status"] == "pending":
                s_a.post(f"{API}/workspaces/invitations/{inv['id']}/respond",
                         json={"decision": "accept"}, timeout=15)
        # Aiko (Researcher) tries to change Marcus's role → 403
        _, me_m = marcus
        rbad = s_a.patch(f"{API}/workspaces/{workspace['id']}/members/{me_m['id']}/role",
                         json={"role": "Reviewer"}, timeout=15)
        assert rbad.status_code == 403, f"expected 403 got {rbad.status_code}"

    def test_cannot_remove_owner(self, elena, workspace):
        s_e, me_e = elena
        # Marcus is PI so could call this; but test via Elena trying to remove herself (owner)
        r = s_e.delete(f"{API}/workspaces/{workspace['id']}/members/{me_e['id']}", timeout=15)
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text}"


# ============== Manuscript: versions, comments, contributions, authors ==============
@pytest.fixture(scope="module")
def manuscript(elena, workspace):
    s_e, me_e = elena
    payload = {
        "title": f"TEST_RO_Paper_{int(time.time())}",
        "workspace_id": workspace["id"],
        "abstract": "Initial abstract",
    }
    r = s_e.post(f"{API}/manuscripts", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    m = r.json()
    # sanity — author should be Elena
    return m


class TestManuscriptVersions:
    def test_snapshot_and_list(self, elena, manuscript):
        s_e, _ = elena
        r1 = s_e.post(f"{API}/manuscripts/{manuscript['id']}/versions",
                      json={"summary": "v1 baseline"}, timeout=15)
        assert r1.status_code == 200, r1.text
        v1 = r1.json()
        assert v1["version"] >= 1
        r2 = s_e.post(f"{API}/manuscripts/{manuscript['id']}/versions",
                      json={"summary": "v2 progress"}, timeout=15)
        assert r2.status_code == 200, r2.text
        v2 = r2.json()
        assert v2["version"] == v1["version"] + 1
        # List
        rl = s_e.get(f"{API}/manuscripts/{manuscript['id']}/versions", timeout=15)
        assert rl.status_code == 200
        lst = rl.json()
        assert len(lst) >= 2
        # Descending order
        versions = [d["version"] for d in lst]
        assert versions == sorted(versions, reverse=True)

    def test_restore_creates_auto_and_restore_snapshots(self, elena, manuscript):
        s_e, _ = elena
        # Take a baseline snapshot
        r_v = s_e.post(f"{API}/manuscripts/{manuscript['id']}/versions",
                       json={"summary": "before restore"}, timeout=15)
        target_v = r_v.json()["version"]
        # Now restore to v1 of this manuscript (lowest)
        rl = s_e.get(f"{API}/manuscripts/{manuscript['id']}/versions", timeout=15)
        versions = sorted([d["version"] for d in rl.json()])
        v1 = versions[0]
        r = s_e.post(f"{API}/manuscripts/{manuscript['id']}/versions/{v1}/restore", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        # current_version should be target_v + 2 (auto-snapshot + restored)
        assert body["current_version"] == target_v + 2

    def test_non_member_versions_403(self, aiko, manuscript):
        s_a, _ = aiko
        r = s_a.get(f"{API}/manuscripts/{manuscript['id']}/versions", timeout=15)
        assert r.status_code == 403


class TestManuscriptComments:
    def test_add_list_resolve(self, elena, manuscript):
        s_e, _ = elena
        r = s_e.post(f"{API}/manuscripts/{manuscript['id']}/comments",
                     json={"section": "abstract", "body": "Tighten this paragraph"}, timeout=15)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["section"] == "abstract"
        assert c["resolved"] is False
        # List filtered by section
        rl = s_e.get(f"{API}/manuscripts/{manuscript['id']}/comments",
                     params={"section": "abstract"}, timeout=15)
        assert rl.status_code == 200
        assert any(x["id"] == c["id"] for x in rl.json())
        # Resolve
        rr = s_e.post(f"{API}/manuscripts/comments/{c['id']}/resolve", timeout=15)
        assert rr.status_code == 200
        # Verify resolved
        rl2 = s_e.get(f"{API}/manuscripts/{manuscript['id']}/comments", timeout=15)
        found = [x for x in rl2.json() if x["id"] == c["id"]]
        assert found and found[0]["resolved"] is True


class TestManuscriptContributions:
    def test_upsert_and_aggregate(self, elena, manuscript):
        s_e, _ = elena
        # Two edits in same section
        for delta in (50, 30):
            r = s_e.post(f"{API}/manuscripts/{manuscript['id']}/contributions",
                         json={"section": "introduction", "char_delta": delta}, timeout=15)
            assert r.status_code == 200
        # List
        rl = s_e.get(f"{API}/manuscripts/{manuscript['id']}/contributions", timeout=15)
        assert rl.status_code == 200
        items = rl.json()
        intro = [x for x in items if x["section"] == "introduction"]
        assert intro, "no introduction contribution"
        assert intro[0]["chars_changed"] >= 80
        assert intro[0]["edits"] >= 2
        assert intro[0]["first_edit"]
        assert intro[0]["last_edit"]


class TestManuscriptAuthors:
    def test_reorder_and_set_corresponding(self, elena, marcus, manuscript):
        s_e, me_e = elena
        _, me_m = marcus
        # First add marcus as author via meta? Authors list is set on create; assume Elena is in authors
        # Add marcus by directly patching with order containing both (this also tests authors mutation)
        order = [me_m["id"], me_e["id"]]  # marcus first
        r = s_e.patch(f"{API}/manuscripts/{manuscript['id']}/authors",
                      json={"order": order, "corresponding_author_id": me_e["id"]}, timeout=15)
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["authors"] == order
        assert m.get("corresponding_author_id") == me_e["id"]

    def test_corresponding_must_be_in_order(self, elena, aiko, manuscript):
        s_e, _ = elena
        _, me_a = aiko
        # try setting corresponding to user not in order — should silently NOT set it
        order_resp = s_e.get(f"{API}/manuscripts/{manuscript['id']}", timeout=15)
        current_authors = order_resp.json()["authors"]
        r = s_e.patch(f"{API}/manuscripts/{manuscript['id']}/authors",
                      json={"order": current_authors, "corresponding_author_id": me_a["id"]},
                      timeout=15)
        assert r.status_code == 200
        # corresponding_author_id should NOT be aiko's id
        assert r.json().get("corresponding_author_id") != me_a["id"]


class TestManuscriptMetaAndDashboard:
    def test_meta_update_keywords(self, elena, manuscript):
        s_e, _ = elena
        r = s_e.patch(f"{API}/manuscripts/{manuscript['id']}/meta",
                      json={"keywords": ["AI", "research-os", "test"]}, timeout=15)
        assert r.status_code == 200, r.text
        assert "test" in r.json().get("keywords", [])

    def test_dashboard_shape(self, elena, manuscript):
        s_e, _ = elena
        r = s_e.get(f"{API}/manuscripts/{manuscript['id']}/dashboard", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ["progress_pct", "ready_for_submission", "versions_count", "comments_open",
                  "comments_total", "review_requests_pending", "contributions", "pipeline_hooks"]:
            assert k in body, f"missing {k}"
        assert 0 <= body["progress_pct"] <= 100
        assert isinstance(body["ready_for_submission"], bool)
        assert isinstance(body["pipeline_hooks"], dict)
