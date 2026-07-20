"""Phase IV.1 — Reply/Edit/History, /api/ws/user, Notification service tests.

Covers:
- Regression of earlier Phases
- Reply to message (validation: same conv only)
- Edit message (only sender; non-member 403; empty 400; history)
- Edit WS broadcast (message_edited)
- /api/ws/user cookie auth + unread delta on new message + reset on mark-read
- Notifications collection persistence + /api/notifications endpoint
"""
import asyncio
import json
import os
import pytest
import requests
import websockets

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
WS_BASE = BASE_URL.replace("https://", "wss://").replace("http://", "ws://")

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
def direct_conv(elena, marcus):
    s_e, _ = elena
    _, m = marcus
    r = s_e.post(f"{API}/conversations", json={"type": "direct", "other_user_id": m["id"]}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def second_conv(elena, aiko):
    # An unrelated conv that Elena is in (with Aiko) so we have a cross-conv ID
    s_e, _ = elena
    _, a = aiko
    r = s_e.post(f"{API}/conversations", json={"type": "direct", "other_user_id": a["id"]}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


# ============== Regression ==============
class TestRegression:
    def test_login_elena(self, elena):
        _, me = elena
        assert me.get("email") == ELENA["email"]

    def test_conversations_idempotency(self, elena, marcus):
        s_e, _ = elena
        _, m = marcus
        a = s_e.post(f"{API}/conversations", json={"type": "direct", "other_user_id": m["id"]}, timeout=15)
        b = s_e.post(f"{API}/conversations", json={"type": "direct", "other_user_id": m["id"]}, timeout=15)
        assert a.status_code == 200 and b.status_code == 200
        assert a.json()["id"] == b.json()["id"]

    def test_discover_feed(self, elena):
        s, _ = elena
        r = s.get(f"{API}/discover/feed", timeout=15)
        assert r.status_code == 200

    def test_billing_plans(self, elena):
        s, _ = elena
        r = s.get(f"{API}/billing/plans", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ============== Reply ==============
class TestReply:
    def test_reply_snippet_matches_parent(self, elena, direct_conv):
        s, _ = elena
        # Post a parent message
        parent_content = "PARENT-MSG for reply test"
        r1 = s.post(f"{API}/conversations/{direct_conv['id']}/messages",
                    json={"content": parent_content}, timeout=15)
        assert r1.status_code == 200, r1.text
        parent = r1.json()
        # Post a reply
        r2 = s.post(f"{API}/conversations/{direct_conv['id']}/messages",
                    json={"content": "this is a reply", "reply_to_id": parent["id"]}, timeout=15)
        assert r2.status_code == 200, r2.text
        reply = r2.json()
        assert "reply_to" in reply, f"reply_to missing on response: {reply}"
        assert reply["reply_to"]["id"] == parent["id"]
        assert reply["reply_to"]["snippet"] == parent_content

    def test_reply_to_cross_conv_400(self, elena, direct_conv, second_conv):
        s, _ = elena
        # Post message in second_conv
        r = s.post(f"{API}/conversations/{second_conv['id']}/messages",
                   json={"content": "in second"}, timeout=15)
        assert r.status_code == 200
        other_msg_id = r.json()["id"]
        # Try replying in direct_conv with cross msg id → expect 400
        bad = s.post(f"{API}/conversations/{direct_conv['id']}/messages",
                     json={"content": "cross", "reply_to_id": other_msg_id}, timeout=15)
        assert bad.status_code == 400, f"expected 400 got {bad.status_code} {bad.text}"


# ============== Edit ==============
class TestEdit:
    def _post(self, sess, conv_id, content="orig"):
        r = sess.post(f"{API}/conversations/{conv_id}/messages",
                      json={"content": content}, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()

    def test_edit_by_sender(self, elena, direct_conv):
        s, _ = elena
        msg = self._post(s, direct_conv["id"], content="orig content A")
        r = s.patch(f"{API}/conversations/{direct_conv['id']}/messages/{msg['id']}",
                    json={"content": "edited content A"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["content"] == "edited content A"
        assert body.get("edited") is True
        assert body.get("edited_at")

    def test_edit_by_non_sender_403(self, elena, marcus, direct_conv):
        s_e, _ = elena
        s_m, _ = marcus
        msg = self._post(s_e, direct_conv["id"], content="elena's msg for non-sender edit")
        # Marcus is a member but not sender → 403
        r = s_m.patch(f"{API}/conversations/{direct_conv['id']}/messages/{msg['id']}",
                      json={"content": "hijack"}, timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"

    def test_edit_by_non_member_403(self, elena, aiko, direct_conv):
        s_e, _ = elena
        s_a, _ = aiko
        msg = self._post(s_e, direct_conv["id"], content="msg in elena-marcus direct")
        # Aiko is NOT a member of the Elena-Marcus direct conv → 403
        r = s_a.patch(f"{API}/conversations/{direct_conv['id']}/messages/{msg['id']}",
                      json={"content": "intrude"}, timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"

    def test_edit_empty_400(self, elena, direct_conv):
        s, _ = elena
        msg = self._post(s, direct_conv["id"], content="will be cleared")
        r = s.patch(f"{API}/conversations/{direct_conv['id']}/messages/{msg['id']}",
                    json={"content": "   "}, timeout=15)
        assert r.status_code == 400


# ============== Edit history ==============
class TestEditHistory:
    def test_history_preserves_original(self, elena, direct_conv):
        s, _ = elena
        r = s.post(f"{API}/conversations/{direct_conv['id']}/messages",
                   json={"content": "v1 original"}, timeout=15)
        assert r.status_code == 200
        mid = r.json()["id"]
        # Edit twice
        for v in ("v2 first edit", "v3 second edit"):
            r2 = s.patch(f"{API}/conversations/{direct_conv['id']}/messages/{mid}",
                         json={"content": v}, timeout=15)
            assert r2.status_code == 200
        r3 = s.get(f"{API}/conversations/{direct_conv['id']}/messages/{mid}/history", timeout=15)
        assert r3.status_code == 200, r3.text
        body = r3.json()
        assert "history" in body
        hist = body["history"]
        assert isinstance(hist, list) and len(hist) >= 1
        # First entry should be the original content
        assert hist[0]["content"] == "v1 original"
        assert body["current_content"] == "v3 second edit"


# ============== Notifications ==============
class TestNotifications:
    def test_message_creates_in_app_notification(self, elena, marcus, direct_conv):
        s_e, _ = elena
        s_m, m = marcus
        before = s_m.get(f"{API}/notifications", timeout=15)
        assert before.status_code == 200, before.text
        before_count = len(before.json()) if isinstance(before.json(), list) else len(before.json().get("items", []))
        # Send a message from Elena → Marcus (Marcus is non-sender member)
        r = s_e.post(f"{API}/conversations/{direct_conv['id']}/messages",
                     json={"content": "ping for notification"}, timeout=15)
        assert r.status_code == 200
        # Give async dispatch a moment
        import time; time.sleep(0.5)
        after = s_m.get(f"{API}/notifications", timeout=15)
        assert after.status_code == 200
        after_list = after.json() if isinstance(after.json(), list) else after.json().get("items", [])
        assert len(after_list) >= before_count + 1, f"expected new notification: before={before_count} after={len(after_list)}"
        # Latest one should be 'message' type
        latest = after_list[0]
        assert latest.get("type") in ("message", "mention"), f"latest notification type unexpected: {latest}"

    def test_mention_creates_mention_notification(self, elena, marcus, direct_conv):
        s_e, _ = elena
        s_m, _ = marcus
        # Marcus's local-part is 'marcus.okafor'
        r = s_e.post(f"{API}/conversations/{direct_conv['id']}/messages",
                     json={"content": "hey @marcus.okafor check this"}, timeout=15)
        assert r.status_code == 200
        import time; time.sleep(0.5)
        after = s_m.get(f"{API}/notifications", timeout=15)
        lst = after.json() if isinstance(after.json(), list) else after.json().get("items", [])
        # Latest must be a mention
        assert any(n.get("type") == "mention" for n in lst[:5]), f"no mention notification in top5: {lst[:5]}"


# ============== WS user channel ==============
def _cookie_header(sess):
    # requests Session → cookies → cookie header for websockets
    return "; ".join(f"{c.name}={c.value}" for c in sess.cookies)


@pytest.mark.asyncio
async def test_ws_user_missing_cookie_4401():
    url = f"{WS_BASE}/api/ws/user"
    with pytest.raises(Exception) as exc:
        async with websockets.connect(url, open_timeout=8) as ws:
            await ws.recv()
    # Either ConnectionClosed or InvalidStatus; check 4401 if present
    msg = str(exc.value)
    assert "4401" in msg or "401" in msg or "reject" in msg.lower() or "closed" in msg.lower(), msg


@pytest.mark.asyncio
async def test_ws_user_with_cookie_accepts_and_unread_delta(elena, marcus, direct_conv):
    s_e, _ = elena
    s_m, _ = marcus
    cookie = _cookie_header(s_m)
    headers = {"Cookie": cookie}
    url = f"{WS_BASE}/api/ws/user"
    # Use additional_headers or extra_headers depending on websockets version
    try:
        ws = await websockets.connect(url, additional_headers=headers, open_timeout=10)
    except TypeError:
        ws = await websockets.connect(url, extra_headers=headers, open_timeout=10)

    try:
        # Elena posts a message → Marcus's user channel should get unread delta
        await asyncio.sleep(0.3)
        s_e.post(f"{API}/conversations/{direct_conv['id']}/messages",
                 json={"content": "trigger-unread"}, timeout=15)
        # Collect a few events looking for unread
        got = None
        for _ in range(6):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(raw)
                if data.get("type") == "unread" and data.get("conversation_id") == direct_conv["id"]:
                    got = data
                    break
            except asyncio.TimeoutError:
                break
        assert got is not None, "no unread event received on Marcus's user channel"
        assert got.get("delta") == 1
    finally:
        await ws.close()


@pytest.mark.asyncio
async def test_ws_user_mark_read_reset(elena, marcus, direct_conv):
    s_m, _ = marcus
    cookie = _cookie_header(s_m)
    url = f"{WS_BASE}/api/ws/user"
    try:
        ws = await websockets.connect(url, additional_headers={"Cookie": cookie}, open_timeout=10)
    except TypeError:
        ws = await websockets.connect(url, extra_headers={"Cookie": cookie}, open_timeout=10)
    try:
        await asyncio.sleep(0.3)
        # Marcus marks the direct conv as read
        s_m.post(f"{API}/conversations/{direct_conv['id']}/read", timeout=15)
        got = None
        for _ in range(6):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(raw)
                if data.get("type") == "unread" and data.get("conversation_id") == direct_conv["id"] and data.get("reset"):
                    got = data
                    break
            except asyncio.TimeoutError:
                break
        assert got is not None, "no reset unread event received"
    finally:
        await ws.close()


# ============== Edit broadcast WS ==============
@pytest.mark.asyncio
async def test_edit_broadcasts_message_edited(elena, marcus, direct_conv):
    s_e, _ = elena
    s_m, _ = marcus
    # Elena posts a message
    r = s_e.post(f"{API}/conversations/{direct_conv['id']}/messages",
                 json={"content": "to-be-edited"}, timeout=15)
    assert r.status_code == 200
    mid = r.json()["id"]
    cookie = _cookie_header(s_m)
    url = f"{WS_BASE}/api/ws/conversations/{direct_conv['id']}"
    try:
        ws = await websockets.connect(url, additional_headers={"Cookie": cookie}, open_timeout=10)
    except TypeError:
        ws = await websockets.connect(url, extra_headers={"Cookie": cookie}, open_timeout=10)
    try:
        await asyncio.sleep(0.3)
        # Elena edits
        s_e.patch(f"{API}/conversations/{direct_conv['id']}/messages/{mid}",
                  json={"content": "edited-via-ws"}, timeout=15)
        got = None
        for _ in range(8):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(raw)
                if data.get("type") == "message_edited":
                    got = data
                    break
            except asyncio.TimeoutError:
                break
        assert got is not None, "no message_edited WS event received"
        assert got["message"]["id"] == mid
        assert got["message"]["content"] == "edited-via-ws"
        assert got["message"]["edited"] is True
    finally:
        await ws.close()
