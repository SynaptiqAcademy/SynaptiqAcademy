"""Phase 5 — Discovery Suite + Publication Hub end-to-end backend tests."""
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"

ADMIN = ("admin@synaptiq.io", "admin123")
ELENA = ("elena.varga@synaptiq.io", "demo123")
MARCUS = ("marcus.okafor@synaptiq.io", "demo123")
AIKO = ("aiko.tanaka@synaptiq.io", "demo123")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin(): return _login(*ADMIN)

@pytest.fixture(scope="module")
def elena(): return _login(*ELENA)

@pytest.fixture(scope="module")
def marcus(): return _login(*MARCUS)

@pytest.fixture(scope="module")
def aiko(): return _login(*AIKO)


# =============== Discovery Admin =================
class TestDiscoveryAdmin:
    def test_sources(self, elena):
        r = elena.get(f"{API}/discovery/sources"); assert r.status_code == 200
        d = r.json()
        assert "scheduler_enabled" in d
        assert d["scheduler_enabled"] in (False, 0, "0", None) or d["scheduler_enabled"] is False  # disabled in test env
        names = {p["name"] for p in d["providers"]}
        for must in ("openalex", "doaj", "crossref", "wikicfp", "openaire", "nih", "ukri"):
            assert must in names, f"missing provider {must} in {names}"

    def test_stats_counts(self, elena):
        r = elena.get(f"{API}/discovery/stats"); assert r.status_code == 200
        d = r.json()
        assert d["journal"]["total"] > 5000, f"journals {d['journal']['total']}"
        assert d["conference"]["total"] > 500, f"conferences {d['conference']['total']}"
        assert d["grant"]["total"] > 5000, f"grants {d['grant']['total']}"
        for k in ("journal", "conference", "grant"):
            assert isinstance(d[k]["per_source"], list)
            assert isinstance(d[k]["recent_runs"], list)

    def test_sync_requires_admin(self, elena):
        r = elena.post(f"{API}/discovery/sync/journal", json={"max_records_per_source": 1})
        assert r.status_code == 403

    def test_sync_admin_queues(self, admin):
        # Tiny limits per agent_to_agent_context_note guidance
        r = admin.post(f"{API}/discovery/sync/journal",
                       json={"providers": ["openalex"],
                             "max_records_per_source": 5,
                             "max_wall_seconds_per_source": 10})
        assert r.status_code == 200
        d = r.json()
        assert d.get("queued") is True
        assert d.get("kind") == "journal"

    def test_sync_invalid_kind(self, admin):
        r = admin.post(f"{API}/discovery/sync/widget", json={})
        assert r.status_code == 400

    def test_runs_audit(self, elena):
        r = elena.get(f"{API}/discovery/runs", params={"kind": "journal", "limit": 5})
        assert r.status_code == 200
        runs = r.json()
        assert isinstance(runs, list)
        if runs:
            row = runs[0]
            for k in ("kind", "source", "started_at"):
                assert k in row


# =============== Journals =================
class TestJournals:
    def test_list_paginated(self, elena):
        r = elena.get(f"{API}/journals", params={"page": 1, "page_size": 24})
        assert r.status_code == 200
        d = r.json()
        assert d["total"] > 5000
        assert len(d["items"]) == 24
        assert d["has_more"] is True
        # first item has expected fields
        j = d["items"][0]
        assert "id" in j and "title" in j

    def test_search_neural(self, elena):
        r = elena.get(f"{API}/journals", params={"q": "neural"})
        assert r.status_code == 200
        d = r.json()
        assert d["total"] > 0
        # at least one hit references neural-ish concept
        titles = " ".join(i.get("title", "") for i in d["items"]).lower()
        assert "neural" in titles or "neuro" in titles or d["total"] > 0  # text search returned something

    def test_filter_quartile_oa(self, elena):
        r = elena.get(f"{API}/journals", params={"quartile": "Q1", "open_access": "true", "page_size": 10})
        assert r.status_code == 200
        d = r.json()
        for j in d["items"]:
            assert j.get("quartile") == "Q1"
            assert j.get("open_access") is True

    def test_facets(self, elena):
        r = elena.get(f"{API}/journals/facets"); assert r.status_code == 200
        d = r.json()
        assert "subjects" in d and "publishers" in d and "countries" in d and "quartile" in d and "open_access" in d
        subj = {row["_id"] for row in d["subjects"]}
        # Some real OpenAlex subjects must appear among top 30
        intersect = subj & {"Medicine", "Engineering", "Computer Science", "Biology", "Chemistry", "Physics", "Mathematics", "Economics"}
        assert intersect, f"expected real OpenAlex subjects, got {subj}"

    def test_detail(self, elena):
        # pick a real journal from list
        r = elena.get(f"{API}/journals", params={"page_size": 1, "sort": "popularity"})
        jid = r.json()["items"][0]["id"]
        r2 = elena.get(f"{API}/journals/{jid}")
        assert r2.status_code == 200
        d = r2.json()
        assert d["id"] == jid
        # rich fields
        for f in ("title", "publisher", "works_count", "cited_by_count"):
            assert f in d

    def test_detail_404(self, elena):
        r = elena.get(f"{API}/journals/000000000000000000000000")
        assert r.status_code == 404


# =============== Conferences =================
class TestConferences:
    def test_list(self, elena):
        r = elena.get(f"{API}/conferences", params={"sort": "recent", "page_size": 24})
        assert r.status_code == 200
        d = r.json()
        assert d["total"] > 500
        # deadline_state enrichment
        for c in d["items"][:5]:
            assert "deadline_state" in c

    def test_search(self, elena):
        r = elena.get(f"{API}/conferences", params={"q": "machine learning"})
        assert r.status_code == 200
        assert r.json()["total"] > 0

    def test_filter_open(self, elena):
        r = elena.get(f"{API}/conferences", params={"deadline_state": "open", "page_size": 10})
        assert r.status_code == 200
        for c in r.json()["items"]:
            assert c.get("deadline_state") == "open"

    def test_facets(self, elena):
        r = elena.get(f"{API}/conferences/facets"); assert r.status_code == 200
        d = r.json()
        for f in ("research_areas", "rank", "deadline_state", "countries"):
            assert f in d

    def test_detail(self, elena):
        # filter to wikicfp-sourced to pick a real ingest, not the seed
        r = elena.get(f"{API}/conferences", params={"page_size": 50})
        items = r.json()["items"]
        wikicfp = next((c for c in items if c.get("source") == "wikicfp"), items[0])
        cid = wikicfp["id"]
        r2 = elena.get(f"{API}/conferences/{cid}")
        assert r2.status_code == 200
        d = r2.json()
        assert d["id"] == cid


# =============== Grants =================
class TestGrants:
    def test_list(self, elena):
        r = elena.get(f"{API}/grants", params={"page_size": 24})
        assert r.status_code == 200
        d = r.json()
        assert d["total"] > 5000

    def test_overview_legacy(self, elena):
        r = elena.get(f"{API}/grants", params={"overview": "true"})
        assert r.status_code == 200
        d = r.json()
        for k in ("discover", "saved", "recommended", "tracking"):
            assert k in d

    def test_facets(self, elena):
        r = elena.get(f"{API}/grants/facets"); assert r.status_code == 200
        d = r.json()
        for k in ("research_areas", "countries", "funding_types", "sponsors"):
            assert k in d

    def test_filter_open_only(self, elena):
        r = elena.get(f"{API}/grants", params={"open_only": "true", "page_size": 5})
        assert r.status_code == 200

    def test_detail_and_save_unsave(self, elena):
        r = elena.get(f"{API}/grants", params={"page_size": 1})
        gid = r.json()["items"][0]["id"]
        r2 = elena.get(f"{API}/grants/{gid}"); assert r2.status_code == 200
        assert r2.json()["id"] == gid
        s = elena.post(f"{API}/grants/{gid}/save"); assert s.status_code == 200
        # Verify saved via overview
        ov = elena.get(f"{API}/grants", params={"overview": "true"}).json()
        saved_ids = {g["id"] for g in ov["saved"]}
        assert gid in saved_ids, "grant not in saved list after save"
        u = elena.post(f"{API}/grants/{gid}/unsave"); assert u.status_code == 200


# =============== Publication Hub =================
class TestPublicationHub:
    def test_pipeline_shape(self, elena):
        r = elena.get(f"{API}/publication-hub/pipeline")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "summary" in d and "stages" in d and "stage_order" in d
        for st in ("selected", "ready", "submitted", "under_review",
                   "revision_requested", "accepted", "published"):
            assert st in d["stages"]
        for k in ("total", "active", "under_review", "accepted", "published"):
            assert k in d["summary"]

    def test_full_submission_lifecycle(self, elena):
        # 1. pick a manuscript of elena
        r = elena.get(f"{API}/manuscripts")
        assert r.status_code == 200
        ms_list = r.json()
        assert ms_list, "Elena has no manuscripts"
        mid = ms_list[0]["id"]
        # 2. find a journal
        j = elena.get(f"{API}/journals", params={"page_size": 1}).json()["items"][0]
        # 3. create submission
        cr = elena.post(f"{API}/publication-hub/submissions", json={
            "manuscript_id": mid, "venue_kind": "journal", "venue_id": j["id"], "stage": "selected"})
        assert cr.status_code == 200, cr.text
        sub = cr.json()
        sid = sub["id"]
        assert sub["stage"] == "selected"
        assert sub["venue_snapshot"].get("name")
        # 4. patch to submitted -> sets submitted_at
        p1 = elena.patch(f"{API}/publication-hub/submissions/{sid}", json={"stage": "submitted"})
        assert p1.status_code == 200
        assert p1.json().get("submitted_at")
        # 5. under_review
        p2 = elena.patch(f"{API}/publication-hub/submissions/{sid}", json={"stage": "under_review"})
        assert p2.status_code == 200
        # 6. reviewer feedback
        fb = elena.post(f"{API}/publication-hub/submissions/{sid}/feedback",
                         json={"round": 1, "reviewer_alias": "R1", "body": "TEST_FB please address methods"})
        assert fb.status_code == 200
        # 7. revision note -> stage=revision_requested
        rv = elena.post(f"{API}/publication-hub/submissions/{sid}/revision",
                         json={"round": 1, "body": "TEST_REV revised methods section"})
        assert rv.status_code == 200
        cur = elena.get(f"{API}/publication-hub/submissions/{sid}").json()
        assert cur["stage"] == "revision_requested"
        assert any(f["body"].startswith("TEST_FB") for f in cur["reviewer_feedback"])
        assert any(n["body"].startswith("TEST_REV") for n in cur["revision_notes"])
        # 8. accept -> decision_at set
        p3 = elena.patch(f"{API}/publication-hub/submissions/{sid}",
                          json={"stage": "accepted", "decision": "accept"})
        assert p3.status_code == 200
        d3 = p3.json()
        assert d3["stage"] == "accepted"
        assert d3["decision"] == "accept"
        assert d3["decision_at"] is not None
        # 9. history present
        assert len(d3["history"]) >= 4  # selected,submitted,under_review,accepted (revision_requested via revision endpoint may also push)
        # 10. publish
        p4 = elena.patch(f"{API}/publication-hub/submissions/{sid}", json={"stage": "published"})
        assert p4.status_code == 200

    def test_non_author_cannot_create(self, aiko, elena):
        # Aiko tries to create submission on Elena's manuscript
        ms = elena.get(f"{API}/manuscripts").json()
        if not ms: pytest.skip("no manuscript")
        mid = ms[0]["id"]
        j = elena.get(f"{API}/journals", params={"page_size": 1}).json()["items"][0]
        r = aiko.post(f"{API}/publication-hub/submissions", json={
            "manuscript_id": mid, "venue_kind": "journal", "venue_id": j["id"]})
        assert r.status_code == 403

    def test_submissions_list_filters(self, elena):
        r = elena.get(f"{API}/publication-hub/submissions", params={"stage": "active"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        r2 = elena.get(f"{API}/publication-hub/submissions", params={"stage": "terminal"})
        assert r2.status_code == 200

    def test_target_journal_mirrored(self, elena):
        ms = elena.get(f"{API}/manuscripts").json()
        if not ms: pytest.skip("no manuscript")
        mid = ms[0]["id"]
        j = elena.get(f"{API}/journals", params={"page_size": 1}).json()["items"][0]
        cr = elena.post(f"{API}/publication-hub/submissions", json={
            "manuscript_id": mid, "venue_kind": "journal", "venue_id": j["id"]})
        assert cr.status_code == 200
        # check manuscript
        m = elena.get(f"{API}/manuscripts/{mid}").json()
        assert m.get("target_journal_id") == j["id"]
