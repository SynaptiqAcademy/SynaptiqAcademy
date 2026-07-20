"""Phase P1 (Kanban) + P2 (Manuscript Review Workflow) + P3 (Resend DRY-RUN email
infrastructure) backend tests.

Run:
  pytest /app/backend/tests/backend_phase_kanban_review_email_test.py -v --tb=short \
      --junitxml=/app/test_reports/pytest/pytest_phase_kre.xml
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ELENA = {"email": "elena.varga@synaptiq.io", "password": "demo123"}
MARCUS = {"email": "marcus.okafor@synaptiq.io", "password": "demo123"}
RAFAEL = {"email": "rafael.santos@synaptiq.io", "password": "demo123"}
AIKO = {"email": "aiko.tanaka@synaptiq.io", "password": "demo123"}
ADMIN = {"email": "admin@synaptiq.io", "password": "admin123"}

# Pre-seeded by main agent (per agent_to_agent_context_note)
SEED_WS_ID = "6a2d8426404f238d2070afbf"   # RO Test Lab
SEED_PROJECT_ID = "6a2d8a4201b9ebfbe33c3e88"
SEED_MS_ID = "6a2d843b404f238d2070afc2"   # RO Test Paper


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login failed for {creds['email']}: {r.status_code} {r.text}")
    me = s.get(f"{API}/auth/me", timeout=10)
    assert me.status_code == 200
    return s, me.json()


@pytest.fixture(scope="module")
def elena(): return _login(ELENA)


@pytest.fixture(scope="module")
def marcus(): return _login(MARCUS)


@pytest.fixture(scope="module")
def rafael(): return _login(RAFAEL)


@pytest.fixture(scope="module")
def aiko(): return _login(AIKO)


@pytest.fixture(scope="module")
def admin(): return _login(ADMIN)


# ========================= P1 — Workspace Kanban =========================
class TestWorkspaceTasksKanban:
    def test_returns_projects_and_tasks_shape(self, elena):
        s, _ = elena
        r = s.get(f"{API}/workspaces/{SEED_WS_ID}/tasks", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "projects" in data and "tasks" in data
        assert isinstance(data["projects"], list) and isinstance(data["tasks"], list)
        # Seed has 1 project + 5 sample tasks
        assert len(data["projects"]) >= 1
        # Validate task shape
        for t in data["tasks"]:
            assert "id" in t and "title" in t and "status" in t
            # Either project enriched or null
            assert "project" in t and "assignee" in t
            assert t["status"] != "todo", "Legacy 'todo' should normalize to 'backlog'"

    def test_workspace_tasks_forbidden_for_non_member(self, aiko):
        s, _ = aiko
        r = s.get(f"{API}/workspaces/{SEED_WS_ID}/tasks", timeout=15)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    def test_task_create_then_appears_in_workspace_aggregation(self, elena):
        s, _ = elena
        title = f"TEST_KAN_TASK_{int(time.time())}"
        cr = s.post(
            f"{API}/projects/{SEED_PROJECT_ID}/tasks",
            json={"title": title, "status": "backlog", "priority": "medium"},
            timeout=15,
        )
        assert cr.status_code in (200, 201), cr.text
        created = cr.json()
        assert created.get("title") == title
        tid = created.get("id") or created.get("_id")
        assert tid

        # Verify it shows up in workspace aggregation
        agg = s.get(f"{API}/workspaces/{SEED_WS_ID}/tasks", timeout=15)
        assert agg.status_code == 200
        titles = [t["title"] for t in agg.json()["tasks"]]
        assert title in titles

        # Update status via PATCH
        up = s.patch(
            f"{API}/projects/tasks/{tid}",
            json={"status": "in_progress"},
            timeout=15,
        )
        assert up.status_code in (200, 204), up.text
        agg2 = s.get(f"{API}/workspaces/{SEED_WS_ID}/tasks", timeout=15)
        found = [t for t in agg2.json()["tasks"] if t["title"] == title]
        assert found and found[0]["status"] == "in_progress"


# ========================= P2 — Review Workflow =========================
class TestReviewWorkflow:
    def test_review_verdicts_catalog(self, elena):
        s, _ = elena
        r = s.get(f"{API}/research-os/review-verdicts", timeout=10)
        assert r.status_code == 200
        v = r.json()
        assert set(v) == {"accepted", "minor_revision", "major_revision", "rejected"}
        assert len(v) == 4

    def test_full_review_lifecycle_request_accept_verdict(self, elena, rafael):
        """Elena requests, Rafael accepts then submits a minor_revision verdict.
        Should cascade manuscript status → revision_requested.
        """
        s_e, _ = elena
        s_r, rafael_user = rafael
        reviewer_id = rafael_user["id"]

        # 1) Elena creates a review request for Rafael
        cr = s_e.post(
            f"{API}/manuscripts/{SEED_MS_ID}/review-requests",
            json={
                "reviewer_id": reviewer_id,
                "section": "methodology",
                "note": "Please review sampling justification."
            },
            timeout=15,
        )
        assert cr.status_code in (200, 201), cr.text
        created = cr.json()
        rid = created.get("id") or created.get("_id")
        assert rid
        assert created.get("status") == "pending"

        # 2) Verify it shows in manuscript review-requests list w/ enrichment
        listr = s_e.get(f"{API}/manuscripts/{SEED_MS_ID}/review-requests", timeout=10)
        assert listr.status_code == 200
        items = listr.json()
        item = next((x for x in items if x.get("id") == rid), None)
        assert item is not None
        assert item.get("reviewer") and item["reviewer"].get("full_name")
        assert item.get("requester") and item["requester"].get("full_name")

        # 3) Verify it shows in Rafael's /review-requests/mine queue
        mine = s_r.get(f"{API}/review-requests/mine?status=pending", timeout=10)
        assert mine.status_code == 200
        my = [x for x in mine.json() if x.get("id") == rid]
        assert my, "Pending request not in reviewer's queue"
        assert my[0].get("manuscript") and my[0]["manuscript"].get("title")
        assert my[0].get("requester") and my[0]["requester"].get("full_name")

        # 4) Cannot submit verdict before accepting → 400
        bad = s_r.post(f"{API}/review-requests/{rid}/verdict",
                       json={"verdict": "minor_revision", "comment": "n/a"}, timeout=10)
        assert bad.status_code == 400

        # 5) Non-reviewer cannot respond → 403 (Elena tries to respond on Rafael's behalf)
        forb = s_e.post(f"{API}/review-requests/{rid}/respond",
                        json={"decision": "accept"}, timeout=10)
        assert forb.status_code == 403

        # 6) Rafael accepts
        acc = s_r.post(f"{API}/review-requests/{rid}/respond",
                       json={"decision": "accept"}, timeout=10)
        assert acc.status_code == 200
        assert acc.json().get("status") == "accepted"

        # 7) Cannot re-respond (already accepted)
        rr = s_r.post(f"{API}/review-requests/{rid}/respond",
                      json={"decision": "decline"}, timeout=10)
        assert rr.status_code == 400

        # 8) Rafael submits minor_revision verdict
        vr = s_r.post(f"{API}/review-requests/{rid}/verdict",
                      json={"verdict": "minor_revision", "comment": "Solid; small tweaks."},
                      timeout=15)
        assert vr.status_code == 200, vr.text
        vrj = vr.json()
        assert vrj.get("verdict") == "minor_revision"
        assert vrj.get("manuscript_status") == "revision_requested"

        # 9) Manuscript status cascaded
        m = s_e.get(f"{API}/manuscripts/{SEED_MS_ID}", timeout=10)
        assert m.status_code == 200
        assert m.json().get("status") == "revision_requested"

        # 10) Review-history includes completed entry with reviewer enrichment
        hist = s_e.get(f"{API}/manuscripts/{SEED_MS_ID}/review-history", timeout=10)
        assert hist.status_code == 200
        hit = [x for x in hist.json() if x.get("id") == rid]
        assert hit and hit[0].get("reviewer", {}).get("full_name")

    def test_review_decline_path(self, elena, rafael):
        s_e, _ = elena
        s_r, rafael_user = rafael
        cr = s_e.post(
            f"{API}/manuscripts/{SEED_MS_ID}/review-requests",
            json={"reviewer_id": rafael_user["id"], "section": "results", "note": "decline test"},
            timeout=15,
        )
        assert cr.status_code in (200, 201), cr.text
        rid = cr.json().get("id")
        dec = s_r.post(f"{API}/review-requests/{rid}/respond",
                       json={"decision": "decline"}, timeout=10)
        assert dec.status_code == 200
        assert dec.json().get("status") == "declined"
        # Cannot submit verdict on a declined request
        bad = s_r.post(f"{API}/review-requests/{rid}/verdict",
                       json={"verdict": "accepted"}, timeout=10)
        assert bad.status_code == 400

    def test_status_filter_on_mine(self, rafael):
        s, _ = rafael
        for st in ("pending", "accepted", "completed", "declined"):
            r = s.get(f"{API}/review-requests/mine?status={st}", timeout=10)
            assert r.status_code == 200
            assert all(x.get("status") == st for x in r.json())


# ========================= P3 — Email DRY-RUN infrastructure =========================
class TestEmailInfrastructure:
    def test_resend_sdk_import_works(self):
        try:
            import resend  # noqa
            assert hasattr(resend, "Emails")
        except Exception as e:
            pytest.fail(f"resend SDK not importable: {e}")

    def test_email_service_import_works(self):
        import importlib
        mod = importlib.import_module("services.email_service")
        assert hasattr(mod, "is_live")
        assert hasattr(mod, "send_email")
        assert hasattr(mod, "send_password_reset")
        assert hasattr(mod, "send_workspace_invitation")
        assert hasattr(mod, "send_review_request")
        assert hasattr(mod, "send_collaboration_invitation")
        assert hasattr(mod, "ResendProvider")

    def test_email_config_endpoint_reports_dry_run(self, elena):
        s, _ = elena
        r = s.get(f"{API}/email/config", timeout=10)
        assert r.status_code == 200, r.text
        cfg = r.json()
        # In DRY-RUN env (EMAIL_DRY_RUN=1, blank keys) → live=False, configured=False
        assert cfg["live"] is False
        assert cfg["dry_run"] is True
        assert cfg["configured"] is False
        missing = cfg.get("missing", [])
        assert "RESEND_API_KEY" in missing
        assert "EMAIL_FROM" in missing
        assert "FRONTEND_BASE_URL" in missing
        # Templates catalog
        assert set(cfg["templates"]) == {
            "password_reset", "workspace_invitation", "review_request",
            "collaboration_invitation_application", "collaboration_invitation_decision",
        }

    @pytest.mark.parametrize("tpl", [
        "password_reset", "workspace_invitation", "review_request",
        "collaboration_invitation_application", "collaboration_invitation_decision",
    ])
    def test_email_preview_renders_html(self, elena, tpl):
        s, _ = elena
        r = s.get(f"{API}/email/preview/{tpl}", timeout=10)
        assert r.status_code == 200, r.text
        assert "text/html" in r.headers.get("content-type", "").lower()
        body = r.text
        assert "<html" in body.lower() or "<!doctype" in body.lower() or "<body" in body.lower(), (
            f"preview/{tpl} did not render HTML"
        )
        assert len(body) > 200

    def test_email_preview_unknown_template_404(self, elena):
        s, _ = elena
        r = s.get(f"{API}/email/preview/bogus", timeout=10)
        assert r.status_code == 404

    def test_email_test_requires_admin(self, elena):
        s, _ = elena
        r = s.post(f"{API}/email/test?template=password_reset", timeout=10)
        assert r.status_code == 403, f"Expected 403 for non-admin, got {r.status_code}"

    def test_email_test_admin_dry_run_ok(self, admin):
        s, _ = admin
        r = s.post(f"{API}/email/test?template=password_reset", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # In env w/ EMAIL_DRY_RUN=1 + blank keys → mode is "unconfigured" (no key) per service logic
        assert data.get("ok") is True
        assert data.get("mode") in ("unconfigured", "dry_run")
        assert data.get("id") is None

    def test_email_test_admin_unknown_template(self, admin):
        s, _ = admin
        r = s.post(f"{API}/email/test?template=bogus", timeout=10)
        assert r.status_code == 404

    def test_forgot_password_logs_email_dry_run(self, elena):
        # Public endpoint — no auth needed for forgot-password
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": ELENA["email"]}, timeout=15)
        # Endpoint should always return 200 (avoid email enumeration)
        assert r.status_code in (200, 202), f"forgot-password returned {r.status_code}: {r.text}"
