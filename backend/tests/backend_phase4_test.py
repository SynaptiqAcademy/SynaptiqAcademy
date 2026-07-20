"""Phase IV — SYNAPTIQ Messaging tests. Conversations, messages, attachments, security, WS."""
import io
import os
import json
import asyncio
import pytest
import requests
import websockets

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


# ============== Regression Phase I/II/III ==============
class TestRegression:
    def test_discover_feed(self, elena):
        s, _ = elena
        r = s.get(f"{API}/discover/feed", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))

    def test_journals(self, elena):
        s, _ = elena
        r = s.get(f"{API}/journals", timeout=15)
        assert r.status_code == 200

    def test_billing_plans(self, elena):
        s, _ = elena
        r = s.get(f"{API}/billing/plans", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 3

    def test_credits_balance(self, elena):
        s, _ = elena
        r = s.get(f"{API}/credits/balance", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "balance" in data or "credits" in data or "remaining" in data


# ============== Conversations ==============
class TestDirectConversations:
    def test_create_direct_idempotent(self, elena, marcus):
        s_e, e = elena
        _, m = marcus
        r1 = s_e.post(f"{API}/conversations", json={"type": "direct", "other_user_id": m["id"]}, timeout=15)
        assert r1.status_code == 200, r1.text
        c1 = r1.json()
        assert "id" in c1
        # Idempotent
        r2 = s_e.post(f"{API}/conversations", json={"type": "direct", "other_user_id": m["id"]}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["id"] == c1["id"], "direct conv should be idempotent"
        pytest.elena_marcus_conv_id = c1["id"]

    def test_cannot_message_yourself(self, elena):
        s_e, e = elena
        r = s_e.post(f"{API}/conversations", json={"type": "direct", "other_user_id": e["id"]}, timeout=15)
        assert r.status_code == 400

    def test_direct_third_party_different(self, marcus, aiko):
        s_m, m = marcus
        _, a = aiko
        r = s_m.post(f"{API}/conversations", json={"type": "direct", "other_user_id": a["id"]}, timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] != getattr(pytest, "elena_marcus_conv_id", None)


class TestContextConversations:
    def test_collab_context(self, elena):
        s, e = elena
        # find a collaboration where elena is creator/member
        cr = s.get(f"{API}/collaborations", timeout=15)
        assert cr.status_code == 200
        collabs = cr.json()
        collabs_list = collabs if isinstance(collabs, list) else collabs.get("items", [])
        target = None
        for c in collabs_list:
            cid = c.get("id") or c.get("_id")
            members = c.get("members") or []
            if cid and (c.get("creator_id") == e["id"] or c.get("created_by") == e["id"] or e["id"] in members):
                target = cid
                break
        if not target and collabs_list:
            target = collabs_list[0].get("id") or collabs_list[0].get("_id")
        if not target:
            pytest.skip("No collaboration available")
        r1 = s.post(f"{API}/conversations", json={"type": "collaboration", "context_id": target}, timeout=15)
        assert r1.status_code == 200, r1.text
        c1 = r1.json()
        # idempotent
        r2 = s.post(f"{API}/conversations", json={"type": "collaboration", "context_id": target}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["id"] == c1["id"]
        pytest.collab_conv_id = c1["id"]

    def test_invalid_context(self, elena):
        s, _ = elena
        r = s.post(f"{API}/conversations", json={"type": "project", "context_id": "invalidhex"}, timeout=15)
        assert r.status_code in (400, 404)


class TestListAndFilter:
    def test_list_conversations(self, elena):
        s, _ = elena
        r = s.get(f"{API}/conversations", timeout=15)
        assert r.status_code == 200
        items = r.json()
        ids = [i["id"] for i in items]
        assert pytest.elena_marcus_conv_id in ids
        if hasattr(pytest, "collab_conv_id"):
            assert pytest.collab_conv_id in ids

    def test_filter_by_type(self, elena):
        s, _ = elena
        r = s.get(f"{API}/conversations?type=direct", timeout=15)
        assert r.status_code == 200
        for item in r.json():
            assert item["type"] == "direct"

    def test_search_q(self, elena):
        s, _ = elena
        r = s.get(f"{API}/conversations?q=Marcus", timeout=15)
        assert r.status_code == 200
        items = r.json()
        ids = [i["id"] for i in items]
        assert pytest.elena_marcus_conv_id in ids


# ============== Messages ==============
class TestMessages:
    def test_post_message_with_mention(self, elena):
        s, _ = elena
        cid = pytest.elena_marcus_conv_id
        r = s.post(f"{API}/conversations/{cid}/messages", json={"content": "Hello @marcus"}, timeout=15)
        assert r.status_code == 200, r.text
        msg = r.json()
        assert msg["content"] == "Hello @marcus"
        assert "sender" in msg
        assert isinstance(msg.get("attachments"), list)
        assert isinstance(msg.get("shared_resources"), list)
        assert isinstance(msg.get("mentions"), list)
        # last preview check
        clist = s.get(f"{API}/conversations", timeout=15).json()
        conv = next((c for c in clist if c["id"] == cid), None)
        assert conv and "Hello" in (conv.get("last_message_preview") or "")
        pytest.first_msg_id = msg["id"]

    def test_list_messages_ordering(self, elena):
        s, _ = elena
        cid = pytest.elena_marcus_conv_id
        # Add another
        s.post(f"{API}/conversations/{cid}/messages", json={"content": "second"}, timeout=15)
        r = s.get(f"{API}/conversations/{cid}/messages", timeout=15)
        assert r.status_code == 200
        msgs = r.json()
        assert len(msgs) >= 2
        for i in range(1, len(msgs)):
            assert msgs[i - 1]["created_at"] <= msgs[i]["created_at"]

    def test_non_member_forbidden(self, aiko):
        s, _ = aiko
        cid = pytest.elena_marcus_conv_id
        r1 = s.get(f"{API}/conversations/{cid}/messages", timeout=15)
        assert r1.status_code == 403
        r2 = s.post(f"{API}/conversations/{cid}/messages", json={"content": "hi"}, timeout=15)
        assert r2.status_code == 403


class TestReadReceipts:
    def test_mark_read_drops_unread(self, marcus, elena):
        s_m, _ = marcus
        cid = pytest.elena_marcus_conv_id
        # Marcus marks read
        r = s_m.post(f"{API}/conversations/{cid}/read", timeout=15)
        assert r.status_code == 200
        # Marcus list should show unread=0 for this conv
        items = s_m.get(f"{API}/conversations", timeout=15).json()
        conv = next((c for c in items if c["id"] == cid), None)
        assert conv and conv.get("unread", 0) == 0
        # Total unread tally
        t = s_m.get(f"{API}/conversations/unread/count", timeout=15)
        assert t.status_code == 200
        assert "unread" in t.json()


class TestMentionNotification:
    def test_mention_notif_for_marcus(self, marcus):
        s, _ = marcus
        r = s.get(f"{API}/notifications", timeout=15)
        assert r.status_code == 200
        notifs = r.json()
        items = notifs if isinstance(notifs, list) else notifs.get("items", [])
        has_mention = any(n.get("type") == "mention" for n in items)
        assert has_mention, "Marcus should have a mention notification"


# ============== Attachments ==============
class TestAttachments:
    def _make_pdf_bytes(self):
        return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"

    def _make_png_bytes(self):
        # minimal 1x1 PNG
        import base64
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )

    def test_upload_pdf(self, elena):
        s, _ = elena
        files = {"file": ("hello.pdf", self._make_pdf_bytes(), "application/pdf")}
        r = s.post(f"{API}/uploads", files=files, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["kind"] == "file"
        assert data["content_type"] == "application/pdf"
        assert "id" in data
        pytest.pdf_attachment_id = data["id"]

    def test_upload_png(self, elena):
        s, _ = elena
        files = {"file": ("dot.png", self._make_png_bytes(), "image/png")}
        r = s.post(f"{API}/uploads", files=files, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["kind"] == "image"

    def test_upload_unsupported(self, elena):
        s, _ = elena
        files = {"file": ("a.txt", b"hello world", "text/plain")}
        r = s.post(f"{API}/uploads", files=files, timeout=30)
        assert r.status_code == 415

    def test_attach_to_message_and_security(self, elena, marcus, aiko):
        s_e, _ = elena
        s_m, _ = marcus
        s_a, _ = aiko
        cid = pytest.elena_marcus_conv_id
        att_id = pytest.pdf_attachment_id
        # Post message with attachment
        r = s_e.post(f"{API}/conversations/{cid}/messages",
                     json={"content": "see attached", "attachment_ids": [att_id]}, timeout=30)
        assert r.status_code == 200, r.text
        msg = r.json()
        assert len(msg["attachments"]) == 1
        assert msg["attachments"][0]["id"] == att_id
        # Verify in listing
        msgs = s_e.get(f"{API}/conversations/{cid}/messages", timeout=15).json()
        assert any(att_id in [a["id"] for a in m.get("attachments", [])] for m in msgs)
        # Marcus (member) can download
        rd = s_m.get(f"{API}/uploads/{att_id}", timeout=30)
        assert rd.status_code == 200
        assert rd.headers.get("content-type", "").startswith("application/pdf")
        # Aiko (non-member) cannot
        rfb = s_a.get(f"{API}/uploads/{att_id}", timeout=30)
        assert rfb.status_code == 403


class TestSharedResources:
    def test_share_journal(self, elena):
        s, _ = elena
        cid = pytest.elena_marcus_conv_id
        # Find a journal
        jr = s.get(f"{API}/journals", timeout=15)
        items = jr.json()
        items = items if isinstance(items, list) else items.get("items", [])
        if not items:
            pytest.skip("No journals available")
        jid = items[0].get("id") or items[0].get("_id")
        r = s.post(f"{API}/conversations/{cid}/messages", json={
            "content": "check this",
            "shared_resources": [
                {"type": "journal", "id": jid, "title": "Nature", "subtitle": "Springer Nature"},
                {"type": "video", "id": "x", "title": "junk"},  # invalid filtered
            ],
        }, timeout=15)
        assert r.status_code == 200
        msg = r.json()
        assert len(msg["shared_resources"]) == 1
        assert msg["shared_resources"][0]["type"] == "journal"


# ============== WebSocket ==============
class TestWebSocket:
    @pytest.mark.asyncio
    async def test_ws_member_receives_message(self, elena, marcus):
        s_e, _ = elena
        s_m, _ = marcus
        cid = pytest.elena_marcus_conv_id
        ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + f"/api/ws/conversations/{cid}"
        # cookie header from elena's session
        token = s_e.cookies.get("access_token")
        assert token, "no access_token cookie"
        headers = {"Cookie": f"access_token={token}"}
        try:
            async with websockets.connect(ws_url, additional_headers=headers, open_timeout=10) as ws:
                # Marcus posts msg
                await asyncio.sleep(0.3)
                s_m.post(f"{API}/conversations/{cid}/messages", json={"content": "ws ping"}, timeout=15)
                # Await an event
                got = None
                for _ in range(8):
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        ev = json.loads(raw)
                        if ev.get("type") == "message":
                            got = ev
                            break
                    except asyncio.TimeoutError:
                        break
                assert got is not None, "did not receive WS message broadcast"
        except TypeError:
            # Fallback for older websockets that use extra_headers
            async with websockets.connect(ws_url, extra_headers=headers, open_timeout=10) as ws:
                await asyncio.sleep(0.3)
                s_m.post(f"{API}/conversations/{cid}/messages", json={"content": "ws ping2"}, timeout=15)
                got = None
                for _ in range(8):
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        ev = json.loads(raw)
                        if ev.get("type") == "message":
                            got = ev
                            break
                    except asyncio.TimeoutError:
                        break
                assert got is not None

    @pytest.mark.asyncio
    async def test_ws_non_member_4403(self, aiko):
        s_a, _ = aiko
        cid = pytest.elena_marcus_conv_id
        ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + f"/api/ws/conversations/{cid}"
        token = s_a.cookies.get("access_token")
        headers = {"Cookie": f"access_token={token}"}
        from websockets.exceptions import InvalidStatus, ConnectionClosed
        try:
            try:
                async with websockets.connect(ws_url, additional_headers=headers, open_timeout=10) as ws:
                    try:
                        await asyncio.wait_for(ws.recv(), timeout=3.0)
                    except Exception:
                        pass
            except TypeError:
                async with websockets.connect(ws_url, extra_headers=headers, open_timeout=10) as ws:
                    try:
                        await asyncio.wait_for(ws.recv(), timeout=3.0)
                    except Exception:
                        pass
        except ConnectionClosed as e:
            assert e.code == 4403
            return
        except Exception:
            return  # any failure on connect indicates rejection
        # if we got here, server didn't reject — fail
        pytest.fail("Expected non-member ws connect to be rejected")

    @pytest.mark.asyncio
    async def test_ws_no_cookie_4401(self):
        cid = getattr(pytest, "elena_marcus_conv_id", None)
        if not cid:
            pytest.skip("No conv id")
        ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + f"/api/ws/conversations/{cid}"
        from websockets.exceptions import ConnectionClosed
        try:
            async with websockets.connect(ws_url, open_timeout=10) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=3.0)
                except Exception:
                    pass
        except ConnectionClosed as e:
            assert e.code == 4401
            return
        except Exception:
            return
        pytest.fail("Expected no-cookie ws connect to be rejected")
