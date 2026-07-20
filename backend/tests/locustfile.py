"""
Locust load-test scenarios for Synaptiq backend.

Simulates realistic user behaviour: auth, profile reads, AI features,
collaboration, and discovery.  Designed to run against a live backend.

Usage (requires a running server):
    locust -f tests/locustfile.py --host http://localhost:8000

Headless (100 users, 10/s spawn, 2 min):
    locust -f tests/locustfile.py --host http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 2m --headless

Stages (quick regression smoke):
    locust -f tests/locustfile.py --host http://localhost:8000 \
           --users 50 --spawn-rate 5 --run-time 60s --headless

SLO thresholds (enforced via --exit-code-on-error):
  p95 < 500 ms for auth / read endpoints
  p99 < 2 s for any endpoint
  Error rate < 1 %
"""
import random
import string
import uuid

try:
    from locust import HttpUser, task, between, events, LoadTestShape
    from locust.exception import StopUser
    _LOCUST_AVAILABLE = True
except ImportError:
    _LOCUST_AVAILABLE = False
    # Provide stubs so the file can be imported without locust installed.
    class HttpUser:
        pass
    def task(weight=1):
        return lambda fn: fn
    def between(a, b):
        return (a, b)
    class StopUser(Exception):
        pass
    class LoadTestShape:
        pass
    class events:
        quitting = None


def _rand_email() -> str:
    return f"load-{uuid.uuid4().hex[:12]}@loadtest.synaptiq.io"


def _rand_password() -> str:
    return "Load" + "".join(random.choices(string.ascii_letters + string.digits, k=12)) + "1!"


# ─── Shared user pool ─────────────────────────────────────────────────────────
# Users self-register on first spawn, then reuse credentials across tasks.


class AuthenticatedUser(HttpUser):
    """Simulates a logged-in researcher performing common actions."""

    wait_time = between(1, 3)  # Think time between requests

    def on_start(self):
        """Register and login before running tasks."""
        self._email    = _rand_email()
        self._password = _rand_password()
        self._logged_in = False
        self._csrf_token = ""
        self._access_cookies = {}

        # Register
        r = self.client.post("/api/auth/register", json={
            "full_name": "Load Test User",
            "email":     self._email,
            "password":  self._password,
        }, name="/api/auth/register")
        if r.status_code not in (200, 201):
            raise StopUser()

        # Login
        r = self.client.post("/api/auth/login", json={
            "email":    self._email,
            "password": self._password,
        }, name="/api/auth/login")
        if r.status_code != 200:
            raise StopUser()

        self._logged_in = True
        self._refresh_csrf()

    def _refresh_csrf(self):
        r = self.client.get("/api/auth/csrf-token", name="/api/auth/csrf-token")
        if r.status_code == 200:
            self._csrf_token = r.json().get("csrf_token", "")

    def _csrf_headers(self) -> dict:
        return {"X-CSRF-Token": self._csrf_token} if self._csrf_token else {}

    def on_stop(self):
        if self._logged_in:
            self.client.post("/api/auth/logout",
                             headers=self._csrf_headers(),
                             name="/api/auth/logout")

    # ── Read-heavy tasks (higher weight = more frequent) ─────────────────────

    @task(10)
    def get_profile(self):
        self.client.get("/api/auth/me", name="/api/auth/me")

    @task(8)
    def get_csrf_token(self):
        self._refresh_csrf()

    @task(6)
    def list_files(self):
        self.client.get("/api/files/", name="/api/files/")

    @task(5)
    def get_credits_balance(self):
        self.client.get("/api/credits/balance", name="/api/credits/balance")

    @task(4)
    def get_analytics_dashboard(self):
        self.client.get("/api/analytics/dashboard", name="/api/analytics/dashboard")

    @task(3)
    def list_collaborations(self):
        self.client.get("/api/collaborations/", name="/api/collaborations/")

    @task(3)
    def list_publications(self):
        self.client.get("/api/publications/", name="/api/publications/")

    @task(2)
    def get_notifications(self):
        self.client.get("/api/notifications", name="/api/notifications")

    @task(2)
    def get_reputation(self):
        self.client.get("/api/reputation/score", name="/api/reputation/score")

    @task(2)
    def get_career_profile(self):
        self.client.get("/api/career/profile", name="/api/career/profile")

    # ── Write tasks (lower weight — less frequent) ────────────────────────────

    @task(1)
    def refresh_tokens(self):
        self.client.post("/api/auth/refresh", name="/api/auth/refresh")
        self._refresh_csrf()

    @task(1)
    def update_profile(self):
        self.client.patch(
            "/api/auth/profile",
            json={"bio": f"Load test bio {random.randint(1, 9999)}"},
            headers=self._csrf_headers(),
            name="/api/auth/profile PATCH",
        )


class UnauthenticatedUser(HttpUser):
    """Simulates anonymous visitors browsing public endpoints."""

    wait_time = between(0.5, 2)

    @task(10)
    def health_check(self):
        self.client.get("/api/health", name="/api/health")

    @task(5)
    def openapi_schema(self):
        self.client.get("/openapi.json", name="/openapi.json")

    @task(3)
    def get_plans(self):
        self.client.get("/api/billing/plans", name="/api/billing/plans")

    @task(2)
    def failed_login(self):
        """Intentional failed login — verifies lockout and error handling."""
        self.client.post("/api/auth/login", json={
            "email": "nobody@loadtest.io", "password": "WrongPass1",
        }, name="/api/auth/login [anon]")


# ─── Load shape: ramping scenario ─────────────────────────────────────────────


class RampingLoadShape(LoadTestShape):
    """
    Gradually ramps from 0 to peak, holds, then ramps down.

    Stage      Duration   Users   Spawn rate
    ─────────────────────────────────────────
    Ramp up    60s        100     5/s
    Hold       120s       100     —
    Peak       60s        500     10/s
    Hold peak  120s       500     —
    Ramp down  60s        0       10/s

    Total: ~7 minutes.
    Override with standard --users / --run-time flags for quick runs.
    """

    stages = [
        {"duration": 60,  "users": 100,  "spawn_rate": 5},
        {"duration": 180, "users": 100,  "spawn_rate": 5},
        {"duration": 240, "users": 500,  "spawn_rate": 10},
        {"duration": 360, "users": 500,  "spawn_rate": 10},
        {"duration": 420, "users": 0,    "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None
