"""Academic Publishing Intelligence — Main engine + async singleton (Phase XII)."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from .conference_analyzer import analyze_conference_fit
from .cover_letter_generator import generate_cover_letter
from .dashboard_builder import build_publishing_dashboard
from .export_engine import export as run_export
from .grant_analyzer import analyze_grant_fit
from .journal_analyzer import analyze_journal_fit
from .journal_matcher import match_journals
from .models import (
    ExportFormat, MatchType, PublicationDashboard, PublicationRisk,
    PublicationStrategy, RevisionType, SmartJournalMatch,
    SubmissionReadiness,
)
from .reviewer_response_generator import generate_reviewer_response
from .risk_analyzer import analyze_publication_risk
from .strategy_builder import build_publication_strategy
from .submission_checker import check_submission_readiness
from .telemetry import get_telemetry


class PublishingEngine:
    """Central orchestrator for all publishing intelligence operations."""

    def __init__(self, call_llm=None) -> None:
        self._call_llm = call_llm

    # ── Journal operations ────────────────────────────────────────────────────

    async def analyse_journal(
        self,
        text: str,
        discipline: str,
        manuscript_quality: float,
    ) -> list[dict]:
        t0 = time.monotonic()
        try:
            fits = analyze_journal_fit(text, discipline, manuscript_quality)
            get_telemetry().record_journal_analysis()
            return [f.to_dict() for f in fits[:10]]
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    async def match_journal(
        self,
        text: str,
        discipline: str,
        manuscript_quality: float,
        match_types: list[str] | None = None,
    ) -> list[dict]:
        t0 = time.monotonic()
        try:
            mts = [MatchType(m) for m in match_types] if match_types else None
            matches = match_journals(text, discipline, manuscript_quality, mts)
            get_telemetry().record_journal_match()
            return [m.to_dict() for m in matches]
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    # ── Conference ────────────────────────────────────────────────────────────

    async def match_conference(
        self,
        text: str,
        discipline: str,
        manuscript_quality: float,
    ) -> list[dict]:
        t0 = time.monotonic()
        try:
            fits = analyze_conference_fit(text, discipline, manuscript_quality)
            get_telemetry().record_conference_match()
            return [f.to_dict() for f in fits[:8]]
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    # ── Grant ─────────────────────────────────────────────────────────────────

    async def match_grant(
        self,
        text: str,
        discipline: str,
        manuscript_quality: float,
        user_profile: dict | None = None,
    ) -> list[dict]:
        t0 = time.monotonic()
        try:
            fits = analyze_grant_fit(text, discipline, manuscript_quality, user_profile)
            get_telemetry().record_grant_match()
            return [f.to_dict() for f in fits[:10]]
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    # ── Submission readiness ──────────────────────────────────────────────────

    async def check_readiness(
        self,
        text: str,
        metadata: dict | None = None,
    ) -> dict:
        t0 = time.monotonic()
        try:
            result = check_submission_readiness(text, metadata)
            get_telemetry().record_readiness_check()
            return result.to_dict()
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    # ── Cover letter ──────────────────────────────────────────────────────────

    async def generate_cover_letter(
        self,
        manuscript_title: str,
        journal: str,
        metadata: dict | None = None,
    ) -> dict:
        t0 = time.monotonic()
        try:
            letter = await generate_cover_letter(
                manuscript_title, journal, metadata, self._call_llm
            )
            get_telemetry().record_cover_letter()
            return letter.to_dict()
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    # ── Reviewer response ─────────────────────────────────────────────────────

    async def generate_reviewer_response(
        self,
        revision_type: str,
        manuscript_title: str,
        journal: str,
        reviewer_comments: list[dict],
        metadata: dict | None = None,
    ) -> dict:
        t0 = time.monotonic()
        try:
            rt = RevisionType(revision_type)
            response = generate_reviewer_response(
                rt, manuscript_title, journal, reviewer_comments, metadata
            )
            get_telemetry().record_reviewer_response()
            return response.to_dict()
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    # ── Strategy ──────────────────────────────────────────────────────────────

    async def build_strategy(
        self,
        manuscript_title: str,
        text: str,
        discipline: str,
        manuscript_quality: float,
    ) -> dict:
        t0 = time.monotonic()
        try:
            strategy = build_publication_strategy(
                manuscript_title, text, discipline, manuscript_quality
            )
            get_telemetry().record_strategy()
            return strategy.to_dict()
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    # ── Risk ─────────────────────────────────────────────────────────────────

    async def analyse_risk(
        self,
        text: str,
        manuscript_quality: float,
        scope_match: float = 0.5,
        journal_acceptance_rate: float = 0.25,
        journal_review_weeks: int = 12,
        journal_predatory_risk: float = 0.0,
        metadata: dict | None = None,
    ) -> dict:
        t0 = time.monotonic()
        try:
            risk = analyze_publication_risk(
                text, manuscript_quality, scope_match,
                journal_acceptance_rate, journal_review_weeks,
                journal_predatory_risk, metadata,
            )
            get_telemetry().record_risk_analysis()
            return risk.to_dict()
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    # ── Dashboard ─────────────────────────────────────────────────────────────

    async def get_dashboard(
        self,
        user_id: str,
        db=None,
    ) -> dict:
        t0 = time.monotonic()
        try:
            dashboard = await build_publishing_dashboard(user_id, db)
            get_telemetry().record_dashboard_view()
            return dashboard.to_dict()
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)

    # ── Export ────────────────────────────────────────────────────────────────

    async def export(
        self,
        export_type: str,
        fmt: str,
        payload: dict,
    ) -> str:
        t0 = time.monotonic()
        try:
            result = run_export(ExportFormat(export_type), ExportFormat(fmt), payload)
            get_telemetry().record_export()
            return result
        except Exception:
            get_telemetry().record_error()
            raise
        finally:
            get_telemetry().record_latency(time.monotonic() - t0)


# ── Async singleton ───────────────────────────────────────────────────────────

_engine_lock = asyncio.Lock()
_engine_instance: PublishingEngine | None = None


async def get_publishing_engine(call_llm=None) -> PublishingEngine:
    global _engine_instance
    if _engine_instance is None:
        async with _engine_lock:
            if _engine_instance is None:
                _engine_instance = PublishingEngine(call_llm)
    return _engine_instance


def reset_publishing_engine() -> None:
    global _engine_instance
    _engine_instance = None
