"""Regression tests for startup() error-boundary independence.

AUDIT_PHASE0.md incident: seed_admin_and_demo() raising [AUTH-010] because
SUPER_ADMIN_PASSWORD wasn't configured in production silently cancelled
every startup task sequenced after it — including discovery-index creation
and the discovery scheduler — because they all lived inside one shared
try/except. These tests exercise the real startup() function and assert
that later, independent tasks still run when an earlier one fails.
"""
from __future__ import annotations

import pytest

import server
import services.discovery as discovery_pkg


async def _run_startup_and_capture(monkeypatch, *, seed_admin_side_effect=None):
    """Call the real server.startup() with seed_admin_and_demo and the
    discovery scheduler mocked out, and report what actually ran."""
    calls: dict[str, bool] = {"ensure_indexes": False, "start_scheduler": False, "seed_admin_and_demo": False}

    async def fake_seed_admin_and_demo(db):
        calls["seed_admin_and_demo"] = True
        if seed_admin_side_effect is not None:
            raise seed_admin_side_effect

    async def fake_ensure_indexes():
        calls["ensure_indexes"] = True

    async def fake_start_scheduler():
        calls["start_scheduler"] = True
        return None

    # server.py imports seed_admin_and_demo by name at module load time —
    # patch that binding directly.
    monkeypatch.setattr(server, "seed_admin_and_demo", fake_seed_admin_and_demo)
    # server.py does a LOCAL `from services.discovery import ensure_indexes,
    # start_scheduler` inside startup() — patch the source module's
    # attributes so that local import resolves to the fakes.
    monkeypatch.setattr(discovery_pkg, "ensure_indexes", fake_ensure_indexes)
    monkeypatch.setattr(discovery_pkg, "start_scheduler", fake_start_scheduler)
    # Content seeding also touches real collections extensively — not the
    # concern of this test, keep it inert and fast.
    monkeypatch.setattr(server, "seed_content_and_tag_legacy", lambda db: _noop())

    await server.startup()
    return calls


async def _noop():
    return None


class TestStartupIndependence:
    async def test_scheduler_starts_despite_seed_admin_auth010_failure(self, monkeypatch):
        """Core regression: AUTH-010 in seed_admin_and_demo() must not
        prevent the discovery scheduler from being attempted."""
        calls = await _run_startup_and_capture(
            monkeypatch,
            seed_admin_side_effect=RuntimeError(
                "[AUTH-010] SUPER_ADMIN_PASSWORD is using the default value 'SuperAdmin123'. "
                "Set the SUPER_ADMIN_PASSWORD environment variable to a strong credential "
                "before deploying to production."
            ),
        )
        assert calls["seed_admin_and_demo"] is True   # it was attempted
        assert calls["ensure_indexes"] is True         # ...and still reached
        assert calls["start_scheduler"] is True        # ...and the scheduler still started

    async def test_scheduler_starts_despite_generic_seed_admin_exception(self, monkeypatch):
        """Same independence guarantee for a non-AUTH-010 failure — any
        exception in one startup task must not cascade to the others."""
        calls = await _run_startup_and_capture(
            monkeypatch,
            seed_admin_side_effect=Exception("simulated unrelated failure"),
        )
        assert calls["seed_admin_and_demo"] is True
        assert calls["ensure_indexes"] is True
        assert calls["start_scheduler"] is True

    async def test_scheduler_starts_on_clean_boot(self, monkeypatch):
        """Baseline — no failure injected, scheduler still starts (guards
        against the test doubles masking a real wiring break)."""
        calls = await _run_startup_and_capture(monkeypatch)
        assert calls["seed_admin_and_demo"] is True
        assert calls["ensure_indexes"] is True
        assert calls["start_scheduler"] is True
