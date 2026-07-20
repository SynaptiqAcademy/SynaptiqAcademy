"""
AI Chat integration test suite.

Tests the complete AI chat flow against the live dev server at localhost:8000:
  conversation creation, message sending, response rendering, persistence,
  health endpoint, agent routing.

Prerequisites: server must be running (`uvicorn server:app --host 0.0.0.0 --port 8000 --reload`)

Run: cd backend && python -m pytest tests/test_ai_chat.py -v
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _session_for(email: str, password: str) -> requests.Session:
    """Return an authenticated requests.Session for the given credentials."""
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed ({r.status_code}): {r.text[:300]}"
    csrf = s.cookies.get("csrf_token", "")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


@pytest.fixture(scope="module")
def owner_session():
    """Session for the platform owner account (always exists)."""
    return _session_for("cristianaa.almasan@gmail.com", "SynaptiqOwner2026!Secure")


@pytest.fixture(scope="module")
def test_session():
    """Session for a freshly registered throw-away test user.

    Skips if the server requires email verification (EMAIL_VERIFICATION_REQUIRED=1)
    because test users can't verify their inbox automatically.
    """
    email = f"ai-test-{uuid.uuid4().hex[:8]}@test.synaptiq"
    password = "Test@1234!AI"
    s = requests.Session()
    reg = s.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "AI Chat Test",
        "email": email,
        "password": password,
        "user_type": "researcher",
    })
    assert reg.status_code == 200, f"Register failed: {reg.text[:300]}"
    login = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if login.status_code != 200:
        if "verify" in login.text.lower():
            pytest.skip("Server requires email verification — skip new-user test")
        assert False, f"Login failed: {login.text[:300]}"
    csrf = s.cookies.get("csrf_token", "")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestAIHealth:
    def test_health_returns_200(self):
        r = requests.get(f"{BASE_URL}/api/ai/health")
        assert r.status_code == 200

    def test_health_has_required_fields(self):
        data = requests.get(f"{BASE_URL}/api/ai/health").json()
        assert "status" in data
        assert "provider" in data
        assert "mode" in data
        assert data["status"] in ("ok", "degraded")
        assert data["mode"] in ("live", "mock")

    def test_health_no_key_is_degraded_or_live(self):
        data = requests.get(f"{BASE_URL}/api/ai/health").json()
        # Either live (key configured) or degraded (mock mode) — both are valid
        assert data["status"] in ("ok", "degraded")
        assert "message" in data


# ── Conversation lifecycle ────────────────────────────────────────────────────

class TestConversationLifecycle:
    def test_create_conversation(self, owner_session):
        r = owner_session.post(f"{BASE_URL}/api/ai-os/conversations",
                               json={"title": "Test Conversation"})
        assert r.status_code == 200
        data = r.json()
        assert data.get("id") or data.get("_id") or data.get("conv_id"), \
            f"No conversation id in response: {data}"

    def test_list_conversations(self, owner_session):
        r = owner_session.get(f"{BASE_URL}/api/ai-os/conversations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_conversation(self, owner_session):
        created = owner_session.post(f"{BASE_URL}/api/ai-os/conversations", json={})
        assert created.status_code == 200
        conv_id = created.json().get("id") or created.json().get("_id")
        if not conv_id:
            pytest.skip("No conversation id in create response")

        r = owner_session.get(f"{BASE_URL}/api/ai-os/conversations/{conv_id}")
        assert r.status_code == 200


# ── Message send and response ─────────────────────────────────────────────────

class TestMessageFlow:
    @pytest.fixture(scope="class")
    def conv_id(self, owner_session):
        r = owner_session.post(f"{BASE_URL}/api/ai-os/conversations",
                               json={"title": "AI Chat Test"})
        assert r.status_code == 200
        data = r.json()
        return data.get("id") or data.get("_id") or data.get("conv_id")

    def test_send_hello_synaptiq(self, owner_session, conv_id):
        """Phase 11 validation: send 'Hello Synaptiq' and get 200 OK."""
        if not conv_id:
            pytest.skip("No conversation id")
        r = owner_session.post(
            f"{BASE_URL}/api/ai-os/conversations/{conv_id}/messages",
            json={"message": "Hello Synaptiq"},
        )
        assert r.status_code == 200, f"Send failed ({r.status_code}): {r.text[:300]}"

    def test_response_is_not_empty(self, owner_session, conv_id):
        if not conv_id:
            pytest.skip("No conversation id")
        r = owner_session.post(
            f"{BASE_URL}/api/ai-os/conversations/{conv_id}/messages",
            json={"message": "What can you help me with?"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "response" in data, f"Missing 'response' key in: {list(data.keys())}"
        assert len(data["response"]) > 0, "Response text is empty"

    def test_response_has_all_expected_fields(self, owner_session, conv_id):
        if not conv_id:
            pytest.skip("No conversation id")
        r = owner_session.post(
            f"{BASE_URL}/api/ai-os/conversations/{conv_id}/messages",
            json={"message": "Tell me about grant writing."},
        )
        assert r.status_code == 200
        data = r.json()
        for field in ("response", "message_id", "agent_type", "suggested_actions", "sources"):
            assert field in data, f"Missing field '{field}' in response keys: {list(data.keys())}"

    def test_conversation_title_auto_set(self, owner_session):
        """First message in a new conversation auto-sets the title."""
        r = owner_session.post(f"{BASE_URL}/api/ai-os/conversations", json={})
        assert r.status_code == 200
        conv_id = r.json().get("id") or r.json().get("_id")
        if not conv_id:
            pytest.skip("No conversation id")

        send = owner_session.post(
            f"{BASE_URL}/api/ai-os/conversations/{conv_id}/messages",
            json={"message": "Hello Synaptiq — auto title test"},
        )
        assert send.status_code == 200
        data = send.json()
        assert data.get("conversation_title"), \
            "conversation_title should be non-empty after first message"

    def test_agent_type_routing(self, owner_session, conv_id):
        if not conv_id:
            pytest.skip("No conversation id")
        r = owner_session.post(
            f"{BASE_URL}/api/ai-os/conversations/{conv_id}/messages",
            json={"message": "Help me write a grant proposal for NSF.", "agent_type": "grant"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("agent_type") == "grant", \
            f"Expected agent_type='grant', got '{data.get('agent_type')}'"

    def test_new_user_can_also_chat(self, test_session):
        """Non-owner regular users can also create conversations and send messages."""
        r = test_session.post(f"{BASE_URL}/api/ai-os/conversations",
                              json={"title": "New User Chat"})
        assert r.status_code == 200
        conv_id = r.json().get("id") or r.json().get("_id")
        if not conv_id:
            pytest.skip("No conversation id")

        send = test_session.post(
            f"{BASE_URL}/api/ai-os/conversations/{conv_id}/messages",
            json={"message": "Hello Synaptiq"},
        )
        assert send.status_code == 200
        assert send.json().get("response"), "Regular user got empty response"


# ── Persistence ───────────────────────────────────────────────────────────────

class TestPersistence:
    def test_messages_persist_after_send(self, owner_session):
        """Messages are retrievable from the conversation after sending."""
        r = owner_session.post(f"{BASE_URL}/api/ai-os/conversations",
                               json={"title": "Persistence Test"})
        assert r.status_code == 200
        conv_id = r.json().get("id") or r.json().get("_id")
        if not conv_id:
            pytest.skip("No conversation id")

        owner_session.post(
            f"{BASE_URL}/api/ai-os/conversations/{conv_id}/messages",
            json={"message": "Persist this message."},
        )

        fetch = owner_session.get(f"{BASE_URL}/api/ai-os/conversations/{conv_id}")
        assert fetch.status_code == 200
        data = fetch.json()
        messages = data.get("messages", [])
        assert len(messages) >= 2, \
            f"Expected at least 2 messages (user+assistant), got {len(messages)}"

        roles = {m.get("role") for m in messages}
        assert "user" in roles, "No user message persisted"
        assert "assistant" in roles, "No assistant message persisted"

    def test_conversation_appears_in_list(self, owner_session):
        """Created conversations appear in the list endpoint."""
        r = owner_session.post(f"{BASE_URL}/api/ai-os/conversations",
                               json={"title": "List Test Conv"})
        assert r.status_code == 200
        conv_id = r.json().get("id") or r.json().get("_id")

        listing = owner_session.get(f"{BASE_URL}/api/ai-os/conversations")
        assert listing.status_code == 200
        ids = [c.get("id") or c.get("_id") for c in listing.json()]
        assert conv_id in ids, f"New conversation {conv_id} not in list"
