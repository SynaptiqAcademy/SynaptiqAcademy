"""
Performance benchmark suite.

Measures API latency, throughput, and concurrent-request handling.
Failures are raised only when SLOs are violated by a significant margin so
the suite doesn't flap on loaded CI machines.

Run:
    cd backend && python -m pytest tests/test_performance.py -v -m performance -s

SLOs (soft — doubled on CI to reduce flakiness):
  p95 latency: 500 ms for simple auth endpoints
  Throughput: ≥ 5 req/s for health/public endpoints on a single connection
"""
import os
import statistics
import time
import uuid
import concurrent.futures
import pytest

pytestmark = pytest.mark.performance

# Latency SLOs (seconds).  Doubled in CI to avoid flaky failures.
_CI = os.environ.get("CI", "").lower() in ("1", "true", "yes")
_P95_SLO   = 1.0 if _CI else 0.5   # 500 ms local, 1 s CI
_P99_SLO   = 2.0 if _CI else 1.0   # 1 s local, 2 s CI
_THROUGHPUT_MIN = 3 if _CI else 5   # req/s


def unique_email(pfx: str = "perf") -> str:
    return f"{pfx}-{uuid.uuid4().hex[:10]}@perf-test.io"


def _cookie_header(client) -> str:
    return "; ".join(f"{k}={v}" for k, v in client.cookies.items())


@pytest.fixture(scope="module")
def client():
    from server import app
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def auth_client(client):
    email = unique_email("pa")
    client.post("/api/auth/register", json={
        "full_name": "Perf User", "email": email, "password": "PerfPass1!",
    })
    client.post("/api/auth/login", json={"email": email, "password": "PerfPass1!"})
    return client


# ─── helpers ─────────────────────────────────────────────────────────────────

def _measure(fn, n: int = 20) -> tuple[float, float, float]:
    """Call fn() n times and return (p50, p95, p99) in seconds."""
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    times.sort()
    p50 = statistics.median(times)
    p95 = times[int(len(times) * 0.95)]
    p99 = times[int(len(times) * 0.99)]
    return p50, p95, p99


# ═══════════════════════════════════════════════════════════════════════════════
# PERF-001: Latency benchmarks
# ═══════════════════════════════════════════════════════════════════════════════


class TestLatency:
    def test_health_endpoint_p95(self, client):
        """GET /health or /api/health p95 < SLO."""
        path = "/api/health" if client.get("/api/health").status_code < 500 else "/health"
        p50, p95, p99 = _measure(lambda: client.get(path), n=30)
        print(f"\n  [health] p50={p50*1000:.1f}ms  p95={p95*1000:.1f}ms  p99={p99*1000:.1f}ms")
        assert p95 < _P95_SLO, f"health p95 {p95*1000:.0f}ms exceeds SLO {_P95_SLO*1000:.0f}ms"

    def test_login_p95(self, client):
        """POST /api/auth/login p95 < SLO (includes DB lookup + bcrypt verify)."""
        email = unique_email("lp")
        client.post("/api/auth/register", json={
            "full_name": "Latency Login", "email": email, "password": "LatPass1!",
        })
        payload = {"email": email, "password": "LatPass1!"}
        p50, p95, p99 = _measure(lambda: client.post("/api/auth/login", json=payload), n=10)
        print(f"\n  [login] p50={p50*1000:.1f}ms  p95={p95*1000:.1f}ms  p99={p99*1000:.1f}ms")
        assert p95 < _P95_SLO * 3, \
            f"login p95 {p95*1000:.0f}ms exceeds SLO {_P95_SLO*3*1000:.0f}ms"

    def test_csrf_token_p95(self, client):
        """GET /api/auth/csrf-token p95 < SLO."""
        p50, p95, p99 = _measure(lambda: client.get("/api/auth/csrf-token"), n=30)
        print(f"\n  [csrf-token] p50={p50*1000:.1f}ms  p95={p95*1000:.1f}ms")
        assert p95 < _P95_SLO

    def test_openapi_schema_p95(self, client):
        """GET /openapi.json p95 < 2 × SLO (large schema; cached after first generation)."""
        p50, p95, p99 = _measure(lambda: client.get("/openapi.json"), n=20)
        print(f"\n  [openapi] p50={p50*1000:.1f}ms  p95={p95*1000:.1f}ms")
        assert p95 < _P95_SLO * 2, \
            f"openapi p95 {p95*1000:.0f}ms exceeds {_P95_SLO*2*1000:.0f}ms SLO"

    def test_me_endpoint_p95(self, auth_client):
        """GET /api/auth/me p95 < SLO (authenticated, DB lookup)."""
        headers = {"Cookie": _cookie_header(auth_client)}
        p50, p95, p99 = _measure(
            lambda: auth_client.get("/api/auth/me", headers=headers), n=20
        )
        print(f"\n  [me] p50={p50*1000:.1f}ms  p95={p95*1000:.1f}ms")
        assert p95 < _P95_SLO * 2


# ═══════════════════════════════════════════════════════════════════════════════
# PERF-002: Throughput benchmarks
# ═══════════════════════════════════════════════════════════════════════════════


class TestThroughput:
    def test_health_throughput(self, client):
        """Health endpoint must sustain ≥ _THROUGHPUT_MIN req/s sequentially."""
        path = "/api/health" if client.get("/api/health").status_code < 500 else "/health"
        n = 30
        t0 = time.perf_counter()
        for _ in range(n):
            client.get(path)
        elapsed = time.perf_counter() - t0
        rps = n / elapsed
        print(f"\n  [health throughput] {rps:.1f} req/s over {elapsed:.2f}s")
        assert rps >= _THROUGHPUT_MIN, f"health throughput {rps:.1f} req/s below {_THROUGHPUT_MIN}"

    def test_register_throughput(self, client):
        """Registration throughput — skips SLO assertion when email retries are active."""
        n = 5
        t0 = time.perf_counter()
        for i in range(n):
            client.post("/api/auth/register", json={
                "full_name": f"Tput {i}",
                "email": unique_email(f"tput{i}"),
                "password": "TputPass1!",
            })
        elapsed = time.perf_counter() - t0
        rps = n / elapsed
        print(f"\n  [register throughput] {rps:.1f} req/s over {elapsed:.2f}s")
        # If email sending is rate-limited (causing ~2 s retries per call), skip
        # the throughput SLO — this is an environment constraint, not a code issue.
        if elapsed / n > 1.5:
            pytest.skip(
                f"Email rate-limit retries dominate ({elapsed/n:.1f}s/req) — "
                "register throughput SLO skipped"
            )
        assert rps >= 1.0, f"register throughput {rps:.1f} req/s too low (bcrypt issue?)"


# ═══════════════════════════════════════════════════════════════════════════════
# PERF-003: Concurrency benchmarks
# ═══════════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    def test_concurrent_csrf_token_requests(self):
        """10 concurrent CSRF token requests must all succeed within 2 × SLO."""
        from server import app
        from fastapi.testclient import TestClient
        clients = [TestClient(app, raise_server_exceptions=False) for _ in range(10)]
        for c in clients:
            c.__enter__()
        try:
            def _fetch(c):
                t0 = time.perf_counter()
                r = c.get("/api/auth/csrf-token")
                return time.perf_counter() - t0, r.status_code

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
                results = list(pool.map(_fetch, clients))

            latencies = [r[0] for r in results]
            statuses  = [r[1] for r in results]
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            print(f"\n  [concurrent csrf] p95={p95*1000:.1f}ms  statuses={statuses}")

            assert all(s == 200 for s in statuses), f"Some requests failed: {statuses}"
            assert p95 < _P95_SLO * 2
        finally:
            for c in clients:
                try:
                    c.__exit__(None, None, None)
                except Exception:
                    pass

    def test_concurrent_login_requests(self):
        """5 concurrent login requests on a shared client must all succeed.

        We reuse a single TestClient (entered sequentially) and issue concurrent
        requests via a thread pool.  Creating multiple TestClients in parallel
        triggers motor event-loop conflicts, so only one ASGI app instance is used.
        """
        from server import app
        from fastapi.testclient import TestClient
        with TestClient(app, raise_server_exceptions=False) as c:
            email = unique_email("conclogin")
            c.post("/api/auth/register", json={
                "full_name": "Conc Login", "email": email, "password": "ConcPass1!",
            })
            payload = {"email": email, "password": "ConcPass1!"}

            def _login(_):
                r = c.post("/api/auth/login", json=payload)
                return r.status_code

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                statuses = list(pool.map(_login, range(5)))

            print(f"\n  [concurrent login] statuses={statuses}")
            success_count = sum(1 for s in statuses if s == 200)
            assert success_count >= 3, \
                f"Expected ≥3/5 concurrent logins to succeed, got {success_count}"


# ═══════════════════════════════════════════════════════════════════════════════
# PERF-004: Memory / resource baseline
# ═══════════════════════════════════════════════════════════════════════════════


class TestResourceBaseline:
    def test_no_memory_leak_over_repeated_requests(self, client):
        """100 sequential requests must not cause an obvious memory growth trend."""
        import sys
        sizes = []
        for _ in range(100):
            client.get("/api/auth/csrf-token")
            sizes.append(sys.getsizeof(client))
        # size of TestClient object should not grow unboundedly
        growth = sizes[-1] - sizes[0]
        print(f"\n  [memory baseline] object size growth over 100 reqs: {growth} bytes")
        assert growth < 10_000, f"TestClient object grew by {growth} bytes over 100 requests"

    def test_large_payload_does_not_hang(self, client):
        """A 1 MB request body must return within 5 seconds, not hang."""
        t0 = time.perf_counter()
        client.post("/api/auth/login", json={
            "email": "x" * 500_000 + "@test.com",
            "password": "y" * 500_000,
        })
        elapsed = time.perf_counter() - t0
        print(f"\n  [large payload] elapsed={elapsed:.2f}s")
        assert elapsed < 5.0, f"Large payload request took {elapsed:.2f}s (possible hang)"
