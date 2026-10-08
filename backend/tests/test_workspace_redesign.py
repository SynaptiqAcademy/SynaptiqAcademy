"""Workspace redesign test suite (Phases 2-10).

Covers, against a real in-process FastAPI app + local MongoDB:
  - Workspace items: CRUD, optimistic concurrency, dependency-cycle rejection (Phase 2)
  - Polymorphic comments: permissions, cross-workspace IDOR, mention cap (Phase 3)
  - Wiki: auto-versioning, restore, duplicate, search (Phase 4)
  - Gantt task fields: date/dependency/parent validation, status_history (Phase 7)
  - Analytics aggregation: pure-function unit tests + a live empty-state check (Phase 8)
  - Live presence WebSocket: auth rejection + snapshot shape (Phase 9)
  - Phase 10 hardening regressions: completed_at no longer settable, mentions/
    depends_on caps enforced at the API boundary

Run:
    cd backend && python -m pytest tests/test_workspace_redesign.py -v
"""
from __future__ import annotations

import time
import uuid

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.conftest import unique_email


# ── auth helpers ───────────────────────────────────────────────────────────────

def _new_authed_client(app, prefix: str) -> tuple[TestClient, str, str]:
    """Fresh TestClient (own cookie jar) + a newly registered, logged-in user.
    EMAIL_VERIFICATION_REQUIRED=0 in conftest.py means register() itself
    issues the session cookie — no separate /login call needed."""
    c = TestClient(app, raise_server_exceptions=False)
    email = unique_email(prefix)
    r = c.post("/api/auth/register", json={
        "full_name": f"{prefix.title()} User", "email": email, "password": "TestPass1!",
    })
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text[:200]}"
    me = c.get("/api/auth/me")
    assert me.status_code == 200, me.text[:200]
    return c, email, me.json()["id"]


def _create_workspace(client: TestClient, name: str) -> dict:
    r = client.post("/api/workspaces", json={"name": name})
    assert r.status_code == 201, r.text[:300]
    return r.json()


def _create_project(client: TestClient, title: str) -> dict:
    r = client.post("/api/projects", json={"title": title})
    assert r.status_code in (200, 201), r.text[:300]
    return r.json()


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def owner(app):
    return _new_authed_client(app, "wsowner")


@pytest.fixture(scope="module")
def outsider(app):
    """A user with no relationship to `owner`'s workspace — used for IDOR checks."""
    return _new_authed_client(app, "wsoutsider")


@pytest.fixture(scope="module")
def workspace(owner):
    client, _, _ = owner
    return _create_workspace(client, f"Redesign Test WS {uuid.uuid4().hex[:8]}")


@pytest.fixture(scope="module")
def project(owner):
    client, _, _ = owner
    return _create_project(client, f"Redesign Test Project {uuid.uuid4().hex[:8]}")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2 — Workspace Items
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestWorkspaceItems:
    def test_create_and_list_wiki_page(self, owner, workspace):
        client, _, _ = owner
        r = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "wiki_page", "title": "Onboarding Notes",
        })
        assert r.status_code == 200, r.text[:300]
        item = r.json()
        assert item["item_type"] == "wiki_page"
        assert item["version"] == 1

        r = client.get(f"/api/workspaces/{workspace['id']}/items", params={"item_type": "wiki_page"})
        assert r.status_code == 200
        ids = [i["id"] for i in r.json()]
        assert item["id"] in ids

    def test_update_rejects_stale_expected_version(self, owner, workspace):
        client, _, _ = owner
        item = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "wiki_page", "title": "Concurrency Test",
        }).json()

        ok = client.patch(f"/api/items/{item['id']}", json={"title": "Renamed", "expected_version": item["version"]})
        assert ok.status_code == 200, ok.text[:300]

        stale = client.patch(f"/api/items/{item['id']}", json={"title": "Stale Write", "expected_version": item["version"]})
        assert stale.status_code == 409, stale.text[:300]

    def test_circular_dependency_rejected(self, owner, workspace):
        client, _, _ = owner
        a = client.post(f"/api/workspaces/{workspace['id']}/items", json={"item_type": "note", "title": "A"}).json()
        b = client.post(f"/api/workspaces/{workspace['id']}/items", json={"item_type": "note", "title": "B"}).json()

        r = client.patch(f"/api/items/{a['id']}", json={"dependency_ids": [b["id"]]})
        assert r.status_code == 200, r.text[:300]

        cycle = client.patch(f"/api/items/{b['id']}", json={"dependency_ids": [a["id"]]})
        assert cycle.status_code == 400, "B depending on A (which depends on B) must be rejected as a cycle"

    def test_soft_delete_and_admin_restore(self, owner, workspace):
        client, _, _ = owner
        item = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "note", "title": "Deletable",
        }).json()

        d = client.delete(f"/api/items/{item['id']}")
        assert d.status_code == 204

        gone = client.get(f"/api/items/{item['id']}")
        assert gone.status_code == 404

        restored = client.post(f"/api/items/{item['id']}/restore")
        assert restored.status_code == 200, restored.text[:300]

        back = client.get(f"/api/items/{item['id']}")
        assert back.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Comments
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestComments:
    def test_create_and_reply(self, owner, workspace):
        client, _, uid = owner
        item = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "note", "title": "Commentable",
        }).json()

        c1 = client.post("/api/comments", json={
            "target_type": "workspace_item", "target_id": item["id"], "content": "First comment",
        })
        assert c1.status_code == 201, c1.text[:300]
        comment = c1.json()
        assert comment["author_id"] == uid

        reply = client.post("/api/comments", json={
            "target_type": "workspace_item", "target_id": item["id"],
            "content": "A reply", "parent_comment_id": comment["id"],
        })
        assert reply.status_code == 201, reply.text[:300]

        listing = client.get("/api/comments", params={"target_type": "workspace_item", "target_id": item["id"]})
        assert listing.status_code == 200
        assert listing.json()["total"] == 2

    def test_only_author_can_edit_content(self, owner, workspace, outsider):
        client, _, _ = owner
        other_client, _, _ = outsider
        item = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "note", "title": "Edit Perms",
        }).json()
        comment = client.post("/api/comments", json={
            "target_type": "workspace_item", "target_id": item["id"], "content": "Mine",
        }).json()

        # outsider isn't even a workspace member, so this should fail at the
        # authorization layer (403) before content-authorship is checked.
        forbidden = other_client.patch(f"/api/comments/{comment['id']}", json={"content": "Hijacked"})
        assert forbidden.status_code == 403

    def test_resolve_requires_author_or_admin(self, owner, workspace):
        client, _, _ = owner
        item = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "note", "title": "Resolve Perms",
        }).json()
        comment = client.post("/api/comments", json={
            "target_type": "workspace_item", "target_id": item["id"], "content": "Needs resolving",
        }).json()
        # owner is both author and workspace Owner (admin) here — resolving must succeed.
        r = client.patch(f"/api/comments/{comment['id']}", json={"resolved": True})
        assert r.status_code == 200
        assert r.json()["resolved"] is True

    def test_cross_workspace_idor_blocked(self, owner, workspace, outsider):
        """A user with no membership in `workspace` must not be able to read
        or write comments on an item that lives inside it."""
        client, _, _ = owner
        other_client, _, _ = outsider
        item = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "note", "title": "IDOR Target",
        }).json()

        r_list = other_client.get("/api/comments", params={"target_type": "workspace_item", "target_id": item["id"]})
        assert r_list.status_code == 403

        r_create = other_client.post("/api/comments", json={
            "target_type": "workspace_item", "target_id": item["id"], "content": "Should not land",
        })
        assert r_create.status_code == 403

    def test_mentions_cap_enforced(self, owner, workspace):
        client, _, _ = owner
        item = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "note", "title": "Mentions Cap",
        }).json()
        r = client.post("/api/comments", json={
            "target_type": "workspace_item", "target_id": item["id"], "content": "Spam?",
            "mentions": [str(ObjectId()) for _ in range(51)],
        })
        assert r.status_code == 422, "mentions list over the 50-item cap must be rejected"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4 — Wiki
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestWiki:
    def test_content_update_creates_version_and_restore_works(self, owner, workspace):
        client, _, _ = owner
        page = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "wiki_page", "title": "Versioned Page",
            "content": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "v1"}]}]},
        }).json()

        client.patch(f"/api/items/{page['id']}", json={
            "content": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "v2"}]}]},
        })

        versions = client.get(f"/api/wiki/pages/{page['id']}/versions")
        assert versions.status_code == 200
        vlist = versions.json()
        assert len(vlist) >= 1, "editing content must snapshot the pre-edit version"

        restored = client.post(f"/api/wiki/pages/{page['id']}/versions/{vlist[0]['id']}/restore")
        assert restored.status_code == 200, restored.text[:300]

    def test_duplicate_and_search(self, owner, workspace):
        client, _, _ = owner
        unique_title = f"Findable Page {uuid.uuid4().hex[:6]}"
        page = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "wiki_page", "title": unique_title,
        }).json()

        dup = client.post(f"/api/wiki/pages/{page['id']}/duplicate")
        assert dup.status_code == 200
        assert dup.json()["title"] == f"{unique_title} (copy)"

        found = client.get(f"/api/workspaces/{workspace['id']}/wiki/search", params={"q": unique_title})
        assert found.status_code == 200
        titles = [r["title"] for r in found.json()]
        assert unique_title in titles
        assert f"{unique_title} (copy)" in titles


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7 — Gantt task fields
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestGanttTasks:
    def test_start_after_end_rejected(self, owner, project):
        client, _, _ = owner
        r = client.post(f"/api/projects/{project['id']}/tasks", json={
            "title": "Bad dates", "start_date": "2026-02-01", "end_date": "2026-01-01",
        })
        assert r.status_code == 400

    def test_progress_out_of_range_rejected(self, owner, project):
        client, _, _ = owner
        r = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "Bad progress", "progress": 150})
        assert r.status_code == 422

    def test_status_history_seeded_on_create_and_appended_on_transition(self, owner, project):
        client, _, _ = owner
        task = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "Trackable"}).json()
        assert task.get("status_history"), "creation must seed status_history with the initial status"
        assert task["status_history"][0]["status"] == task["status"]

        updated = client.patch(f"/api/projects/tasks/{task['id']}", json={"status": "in_progress"}).json()
        statuses = [h["status"] for h in updated["status_history"]]
        assert statuses[-1] == "in_progress"
        assert len(updated["status_history"]) >= 2

    def test_unknown_dependency_rejected(self, owner, project):
        client, _, _ = owner
        task = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "Needs real deps"}).json()
        r = client.patch(f"/api/projects/tasks/{task['id']}", json={"depends_on": [str(ObjectId())]})
        assert r.status_code == 400

    def test_circular_task_dependency_rejected(self, owner, project):
        client, _, _ = owner
        a = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "Task A"}).json()
        b = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "Task B"}).json()

        ok = client.patch(f"/api/projects/tasks/{a['id']}", json={"depends_on": [b["id"]]})
        assert ok.status_code == 200, ok.text[:300]

        cycle = client.patch(f"/api/projects/tasks/{b['id']}", json={"depends_on": [a["id"]]})
        assert cycle.status_code == 400

    def test_self_parent_rejected(self, owner, project):
        client, _, _ = owner
        task = client.post(f"/api/projects/{project['id']}/tasks", json={"title": "Self parent"}).json()
        r = client.patch(f"/api/projects/tasks/{task['id']}", json={"parent_task_id": task["id"]})
        assert r.status_code == 400

    def test_depends_on_cap_enforced(self, owner, project):
        client, _, _ = owner
        r = client.post(f"/api/projects/{project['id']}/tasks", json={
            "title": "Too many deps", "depends_on": [str(ObjectId()) for _ in range(201)],
        })
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8 — Analytics
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsMetrics:
    """Pure-function unit tests against a minimal fake DB — no network, no
    real Mongo — isolating the metrics math itself from the HTTP/auth layer."""

    @pytest.mark.unit
    def test_empty_project_ids_returns_honest_zero_state(self):
        import asyncio
        from services.workspace_metrics import compute_task_metrics

        result = asyncio.get_event_loop().run_until_complete(compute_task_metrics(db=None, project_ids=[], days=30))
        assert result["tasks_total"] == 0
        assert result["cycle_time_days"]["sample_size"] == 0
        assert result["lead_time_days"]["sample_size"] == 0
        assert result["completion_rate_overall"] is None

    @pytest.mark.unit
    def test_cycle_lead_time_and_blocked_computed_correctly(self):
        import asyncio
        from datetime import datetime, timedelta, timezone
        from services.workspace_metrics import compute_task_metrics

        class _Cursor:
            def __init__(self, docs): self.docs = docs
            def sort(self, *a, **k): return self
            async def to_list(self, n): return self.docs[:n]

        class _Coll:
            def __init__(self, docs): self.docs = docs
            def find(self, query=None, proj=None):
                query = query or {}
                out = []
                for d in self.docs:
                    ok = True
                    for k, v in query.items():
                        if isinstance(v, dict) and "$in" in v:
                            if d.get(k) not in v["$in"]:
                                ok = False
                        elif d.get(k) != v:
                            ok = False
                    if ok:
                        out.append(d)
                return _Cursor(out)

        class _DB:
            def __init__(self, tasks, users):
                self.tasks = _Coll(tasks)
                self.users = _Coll(users)

        now = datetime.now(timezone.utc)

        def iso(dt): return dt.isoformat()

        done = {
            "_id": "t1", "project_id": "p1", "status": "completed",
            "created_at": iso(now - timedelta(days=10)), "due_date": None,
            "assignee_id": None, "depends_on": [],
            "status_history": [
                {"status": "backlog", "at": iso(now - timedelta(days=10))},
                {"status": "in_progress", "at": iso(now - timedelta(days=8))},
                {"status": "completed", "at": iso(now - timedelta(days=2))},
            ],
        }
        blocker = {
            "_id": "t2", "project_id": "p1", "status": "in_progress",
            "created_at": iso(now - timedelta(days=5)), "due_date": None,
            "assignee_id": None, "depends_on": [],
            "status_history": [{"status": "in_progress", "at": iso(now - timedelta(days=5))}],
        }
        blocked = {
            "_id": "t3", "project_id": "p1", "status": "backlog",
            "created_at": iso(now - timedelta(days=1)), "due_date": None,
            "assignee_id": None, "depends_on": ["t2"],
            "status_history": [{"status": "backlog", "at": iso(now - timedelta(days=1))}],
        }
        db = _DB([done, blocker, blocked], [])

        result = asyncio.get_event_loop().run_until_complete(compute_task_metrics(db, ["p1"], 14))
        assert result["tasks_total"] == 3
        assert result["tasks_completed_total"] == 1
        assert result["blocked_count"] == 1  # t3 depends on t2, which isn't completed
        assert result["wip_count"] == 1       # t2 is in_progress
        assert result["cycle_time_days"]["sample_size"] == 1
        assert result["cycle_time_days"]["avg"] == 6.0   # in_progress day-8 -> completed day-2
        assert result["lead_time_days"]["avg"] == 8.0    # created day-10 -> completed day-2


@pytest.mark.integration
class TestAnalyticsLiveEndpoint:
    def test_analytics_endpoint_honest_empty_state_for_new_workspace(self, owner):
        client, _, _ = owner
        empty_ws = _create_workspace(client, f"Empty Analytics WS {uuid.uuid4().hex[:8]}")
        r = client.get(f"/api/workspaces/{empty_ws['id']}/analytics")
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["tasks"]["tasks_total"] == 0
        assert data["tasks"]["cycle_time_days"]["sample_size"] == 0
        assert data["tasks"]["completion_rate_overall"] is None
        assert data["comments_by_day"] == []
        assert data["wiki_edits_by_day"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 9 — Presence WebSocket
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestPresence:
    def test_unauthenticated_connection_is_rejected(self, app, workspace):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/api/ws/workspace/{workspace['id']}/presence"):
                pass

    def test_member_connects_and_sees_self_in_snapshot(self, owner, workspace):
        client, _, uid = owner
        with client.websocket_connect(f"/api/ws/workspace/{workspace['id']}/presence") as ws:
            snapshot = ws.receive_json()
            assert snapshot["type"] == "presence_snapshot"
            user_ids = [u["user_id"] for u in snapshot["users"]]
            assert uid in user_ids

            ws.send_json({"view": "gantt", "typing": False})
            updated = ws.receive_json()
            me = next(u for u in updated["users"] if u["user_id"] == uid)
            assert me["view"] == "gantt"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 10 — Security hardening regressions
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.security
@pytest.mark.integration
class TestSecurityHardening:
    def test_completed_at_is_not_client_settable(self, owner, workspace):
        """WorkspaceItemUpdate no longer has a completed_at field — an extra
        key in the request body must be silently ignored by pydantic, never
        applied to the document."""
        client, _, _ = owner
        item = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "note", "title": "No forged timestamps",
        }).json()
        assert item.get("completed_at") is None

        r = client.patch(f"/api/items/{item['id']}", json={
            "title": "still no forged timestamp", "completed_at": "2020-01-01T00:00:00+00:00",
        })
        assert r.status_code == 200
        assert r.json().get("completed_at") is None

    def test_comment_workspace_id_field_removed(self, owner, workspace):
        client, _, _ = owner
        item = client.post(f"/api/workspaces/{workspace['id']}/items", json={
            "item_type": "note", "title": "Dead field check",
        }).json()
        r = client.post("/api/comments", json={
            "target_type": "workspace_item", "target_id": item["id"], "content": "hi",
            "workspace_id": "some-other-workspace-id",  # must be ignored, not trusted
        })
        assert r.status_code == 201
        # workspace_id on the stored comment must be the REAL one resolved
        # server-side from the item, never the client-supplied value.
        assert r.json()["workspace_id"] == workspace["id"]
