from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from db import get_db, close_db
from rate_limit import limiter
from services.redis_client import init_redis, close_redis
from services.realtime import manager as ws_manager
from middleware import SecurityHeadersMiddleware, CSRFMiddleware, IPBlockMiddleware
from services.logging_config import configure_logging
from services.prod_validator import validate_on_startup
from routers import (
    auth, users, collaborations, projects, notifications, discover,
    ai, analytics,
    journals, conferences, funding, grants, workspaces, manuscripts,
    publication_hub, repository,
    billing, credits, messaging,
    research_os,
    email as email_router,
    discovery_admin,
    matching as matching_router,
    assistant as assistant_router,
    marketplace as marketplace_router,
    expertise as expertise_router,
    reputation as reputation_router,
    institutions as institutions_router,
    orcid as orcid_router,
    files as files_router,
    consent as consent_router,
    admin_health,
    admin_revenue,
    permissions as permissions_router,
    growth as growth_router,
    admin_growth,
    manuscript_review as manuscript_review_router,
    literature_review as literature_review_router,
    research_gap_finder as research_gap_finder_router,
    research_design_advisor as research_design_advisor_router,
    statistical_review as statistical_review_router,
    citation_monitoring as citation_monitoring_router,
    citations as citations_router,
    collaboration_intelligence as collaboration_intelligence_router,
    collaboration_requests as collaboration_requests_router,
    research_impact as research_impact_router,
    departments as departments_router,
    admin_dashboard as admin_dashboard_router,
    admin_users_mgmt as admin_users_mgmt_router,
    admin_security_center as admin_security_center_router,
    admin_email_center as admin_email_center_router,
    admin_data_governance as admin_data_governance_router,
    admin_operations as admin_operations_router,
    admin_content as admin_content_router,
    admin_aos as admin_aos_router,
    admin_expansion as admin_expansion_router,
    admin_account_security as admin_account_security_router,
    admin_mfa as admin_mfa_router,
    mfa as mfa_router,
    admin_hardening as admin_hardening_router,
    email_preferences as email_preferences_router,
    institutional_analytics as institutional_analytics_router,
    google_auth as google_auth_router,
    ai_abstract_generator as ai_abstract_generator_router,
    ai_rewriting as ai_rewriting_router,
    discovery_quota as discovery_quota_router,
    contact as contact_router,
    teaching as teaching_router,
    teaching_analytics as teaching_analytics_router,
    researchers as researchers_router,
    grant_applications as grant_applications_router,
    admin_reputation as admin_reputation_router,
    recommendations as recommendations_router,
    admin_recommendations as admin_recommendations_router,
    impact_dashboard as impact_dashboard_router,
    admin_impact as admin_impact_router,
    synaptiq_ai as synaptiq_ai_router,
    admin_ai_center as admin_ai_center_router,
    institution_hub as institution_hub_router,
    grant_hub as grant_hub_router,
    public_profiles as public_profiles_router,
    reviewer_marketplace as reviewer_marketplace_router,
    institution_analytics_center as institution_analytics_center_router,
    verification as verification_router,
    admin_rule_engine as admin_rule_engine_router,
    admin_local_ai as admin_local_ai_router,
    knowledge as knowledge_router,
    admin_knowledge as admin_knowledge_router,
    admin_smart_router as admin_smart_router_router,
    admin_search as admin_search_router,
    academic_intelligence as academic_intelligence_router,
    literature_intelligence as literature_intelligence_router,
    research_gap_intelligence as research_gap_intelligence_router,
    manuscript_intelligence as manuscript_intelligence_router,
    statistical_intelligence as statistical_intelligence_router,
    academic_copilot as academic_copilot_router,
    publishing_intelligence as publishing_intelligence_router,
    autonomous_agents as autonomous_agents_router,
    collab_intelligence_v2 as collab_intelligence_v2_router,
    institution_intelligence_v2 as institution_intelligence_v2_router,
    career_intelligence as career_intelligence_router,
    knowledge_graph as knowledge_graph_router,
    prediction_intelligence as prediction_intelligence_router,
    self_improvement as self_improvement_router,
    academic_os as academic_os_router,
    trust_center as trust_center_router,
    timeline as timeline_router,
    integrity_engine as integrity_engine_router,
    institution_platform as institution_platform_router,
    sie as sie_router,
    network as network_router,
    acad_market as acad_market_router,
    akg as akg_router,
    proactive as proactive_router,
    meetings as meetings_router,
)
# Multi-agent copilot agents must be imported before the router so each
# agent's module-level REGISTRY.register() call runs at startup.
import agents.literature_agent    # noqa: F401
import agents.gap_agent           # noqa: F401
import agents.study_design_agent  # noqa: F401
import agents.statistics_agent    # noqa: F401
import agents.writing_agent       # noqa: F401
import agents.journal_agent       # noqa: F401
import agents.reviewer_agent      # noqa: F401
import agents.ethics_agent        # noqa: F401
import agents.citation_agent      # noqa: F401
import agents.funding_agent       # noqa: F401
import agents.collaboration_agent # noqa: F401
import agents.teaching_agent      # noqa: F401
import agents.institution_agent   # noqa: F401
import agents.career_agent        # noqa: F401
from routers import copilot as copilot_router
from seed import seed_admin_and_demo, ensure_super_admin_exists
from services.storage_service import init_storage
from repo.shim import make_db_proxy

configure_logging()
logger = logging.getLogger("synaptiq")

# ── Sentry error tracking (no-op when SENTRY_DSN is unset) ──────────────────
_sentry_dsn = os.environ.get("SENTRY_DSN", "").strip()
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        sentry_sdk.init(
            dsn=_sentry_dsn,
            environment=os.environ.get("APP_ENV", "development"),
            traces_sample_rate=0.05,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            send_default_pii=False,
        )
        logger.info("Sentry initialised (env=%s)", os.environ.get("APP_ENV", "development"))
    except ImportError:
        logger.warning("SENTRY_DSN set but sentry-sdk not installed — pip install sentry-sdk")

# AUTH-001: Validate JWT secret entropy at import time (non-blocking in dev)
try:
    from auth_utils import validate_jwt_secret
    _jwt = os.environ.get("JWT_SECRET", "")
    validate_jwt_secret(_jwt)
except RuntimeError as _jwt_err:
    if os.environ.get("APP_ENV", "development").lower() in ("prod", "production"):
        raise
    logger.warning("JWT_SECRET weakness detected (non-blocking in dev): %s", _jwt_err)

app = FastAPI(title="SYNAPTIQ API")

# AUTH-007: CSRF validation middleware (before security headers)
app.add_middleware(CSRFMiddleware)

# H4: IP block enforcement — checked after CSRF but before routing
app.add_middleware(IPBlockMiddleware)

# ----------------- Security headers (CSP, HSTS, etc.) ---------------------------
app.add_middleware(SecurityHeadersMiddleware)

# ----------------- Rate limiting (slowapi) --------------------------------------
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Friendly 429 body — slowapi's default ("Rate limit exceeded: 5 per 1 minute")
    leaks the exact policy and reads like a debug message, not user-facing copy."""
    from fastapi.responses import JSONResponse
    response = JSONResponse(
        {"detail": "Too many attempts. Please wait a moment and try again."},
        status_code=429,
    )
    return app.state.limiter._inject_headers(response, request.state.view_rate_limit)


app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(Exception)
async def _global_500_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions: log with structured context, return safe 500.

    Prevents raw Python stack traces from leaking to clients. Every unhandled
    error is logged through the structured JSON logger with trace context so
    it can be correlated with requests in log aggregators.
    """
    from fastapi.responses import JSONResponse
    import traceback
    trace_id = getattr(request.state, "trace_id", None)
    logger.error(
        "Unhandled exception %s on %s %s — trace=%s",
        type(exc).__name__, request.method, request.url.path, trace_id,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Our team has been notified."},
    )


# AUTH-BUG-002: dedicated handler for MongoDB connectivity failures, registered
# for the specific pymongo exception types so FastAPI prefers it over the bare
# Exception handler above. Applies to every route in the app, not just auth —
# a database outage should always look like a clean, honest 503, never a raw
# 500 or an ambiguous network error. Also arms the circuit breaker (db.py) so
# subsequent requests fail fast instead of each paying the full connection
# timeout. See db.py's DB_DOWN_COOLDOWN_SECONDS / is_db_down() for the other half.
from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect, ConnectionFailure, NetworkTimeout


@app.exception_handler(ServerSelectionTimeoutError)
@app.exception_handler(AutoReconnect)
@app.exception_handler(ConnectionFailure)
@app.exception_handler(NetworkTimeout)
async def _db_unavailable_handler(request: Request, exc: Exception):
    from fastapi.responses import JSONResponse
    from db import mark_db_down, classify_mongo_error
    mark_db_down(exc)
    trace_id = getattr(request.state, "trace_id", None)
    logger.error(
        "Database unavailable on %s %s — trace=%s — %s",
        request.method, request.url.path, trace_id, classify_mongo_error(exc),
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable. Please try again in a moment."},
        headers={"Retry-After": str(int(os.environ.get("DB_DOWN_COOLDOWN_SECONDS", "8")))},
    )

# API monitoring middleware — must be added AFTER rate limiting
try:
    from middleware.api_monitor import APIMonitorMiddleware
    app.add_middleware(APIMonitorMiddleware)
    logger.info("API Monitor middleware registered")
except Exception as _mw_err:
    logger.warning("API Monitor middleware skipped: %s", _mw_err)

# Zero Trust middleware (Phase XXXV.8) — registered before Observability
try:
    from zt.middleware import ZeroTrustMiddleware
    app.add_middleware(ZeroTrustMiddleware)
    logger.info("Zero Trust middleware registered")
except Exception as _zt_mw_err:
    logger.warning("Zero Trust middleware skipped: %s", _zt_mw_err)

# Observability middleware (Phase XXXV.6)
try:
    from obs.middleware import ObservabilityMiddleware
    app.add_middleware(ObservabilityMiddleware)
    logger.info("Observability middleware registered")
except Exception as _obs_mw_err:
    logger.warning("Observability middleware skipped: %s", _obs_mw_err)

# ----------------- CORS (explicit allowlist; no wildcards in prod) --------------
# AUTH-BUG-001: this MUST be the last middleware added (= outermost layer, right
# under Starlette's own ServerErrorMiddleware). Starlette/FastAPI wrap middleware
# in reverse registration order, so whatever is added last runs first on the way
# in and last on the way out. If CORSMiddleware sits *inside* APIMonitor/ZeroTrust/
# Observability (as it previously did — added 3rd of 7), any exception raised by
# — or simply passing through — those outer layers produces a response that never
# reaches CORSMiddleware's header-injection logic. The browser then sees a
# cross-origin response with no Access-Control-Allow-Origin header and reports it
# to JS as a generic network error, indistinguishable from a real connectivity
# failure. Reproduced live: a login request that failed with a real 500 (Mongo
# server-selection timeout) came back with a valid JSON error body but zero CORS
# headers — which is exactly what surfaces to users as "Network connection
# failed" even though the server responded correctly. Adding CORS last guarantees
# every response that leaves the app, error or not, passes through it.
_cors_raw = os.environ.get("CORS_ORIGINS", "").strip()
if _cors_raw == "*" or not _cors_raw:
    # Fail-safe: refuse to combine credentials with wildcard. Empty list means
    # browser cross-origin requests will be blocked — backend still works locally.
    _origins = []
    logger.warning("CORS_ORIGINS is wildcard or empty — refusing wildcard + credentials. "
                   "Set CORS_ORIGINS to an explicit comma-separated allowlist.")
else:
    _origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
    logger.info("CORS allowlist: %s", _origins)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(collaborations.router)
app.include_router(projects.router)
app.include_router(notifications.router)
app.include_router(discover.router)
app.include_router(ai.router)
app.include_router(analytics.router)
app.include_router(journals.router)
app.include_router(conferences.router)
app.include_router(funding.router)
app.include_router(grants.router)
app.include_router(grant_applications_router.router)
app.include_router(workspaces.router)
app.include_router(meetings_router.router)
app.include_router(manuscripts.router)
app.include_router(publication_hub.router)
app.include_router(repository.router)
app.include_router(billing.router)
app.include_router(credits.router)
app.include_router(messaging.router)
app.include_router(research_os.router)
app.include_router(email_router.router)
app.include_router(discovery_admin.router)
app.include_router(matching_router.router)
app.include_router(assistant_router.router)
app.include_router(marketplace_router.router)
app.include_router(expertise_router.router)
app.include_router(reputation_router.router)
app.include_router(institutions_router.router)
app.include_router(orcid_router.router)
app.include_router(files_router.router)
app.include_router(consent_router.router)
app.include_router(admin_health.router)
app.include_router(admin_revenue.router)
app.include_router(permissions_router.router)
app.include_router(growth_router.router)
app.include_router(admin_growth.router)
app.include_router(manuscript_review_router.router)
app.include_router(literature_review_router.router)
app.include_router(research_gap_finder_router.router)
app.include_router(research_design_advisor_router.router)
app.include_router(statistical_review_router.router)
app.include_router(citation_monitoring_router.router)
app.include_router(citations_router.router)
app.include_router(collaboration_intelligence_router.router)
app.include_router(collaboration_requests_router.router)
app.include_router(research_impact_router.router)
app.include_router(departments_router.router)
app.include_router(admin_dashboard_router.router)
app.include_router(admin_users_mgmt_router.router)
app.include_router(admin_security_center_router.router)
app.include_router(admin_email_center_router.router)
app.include_router(admin_data_governance_router.router)
app.include_router(admin_operations_router.router)
app.include_router(admin_content_router.router)
app.include_router(admin_aos_router.router)
app.include_router(admin_expansion_router.router)
app.include_router(admin_account_security_router.router)
app.include_router(admin_mfa_router.router)
app.include_router(mfa_router.router)
app.include_router(admin_hardening_router.router)
app.include_router(email_preferences_router.router)
app.include_router(institutional_analytics_router.router)
app.include_router(google_auth_router.router)
app.include_router(ai_abstract_generator_router.router)
app.include_router(ai_rewriting_router.router)
app.include_router(discovery_quota_router.router)
app.include_router(contact_router.router)
app.include_router(teaching_router.router)
app.include_router(teaching_analytics_router.router)
app.include_router(researchers_router.router)
app.include_router(admin_reputation_router.router)
app.include_router(recommendations_router.router)
app.include_router(admin_recommendations_router.router)
app.include_router(impact_dashboard_router.router)
app.include_router(admin_impact_router.router)
app.include_router(synaptiq_ai_router.router)
app.include_router(admin_ai_center_router.router)
app.include_router(institution_hub_router.router)
app.include_router(grant_hub_router.router)
app.include_router(public_profiles_router.router)
app.include_router(reviewer_marketplace_router.router)
app.include_router(institution_analytics_center_router.router)
app.include_router(verification_router.router)
app.include_router(admin_rule_engine_router.router)
app.include_router(admin_local_ai_router.router)
app.include_router(knowledge_router.router)
app.include_router(admin_knowledge_router.router)
app.include_router(admin_smart_router_router.router)
app.include_router(admin_search_router.router)
app.include_router(academic_intelligence_router.router)
app.include_router(academic_intelligence_router.admin_router)
app.include_router(literature_intelligence_router.router)
app.include_router(literature_intelligence_router.admin_router)
app.include_router(research_gap_intelligence_router.router)
app.include_router(research_gap_intelligence_router.admin_router)
app.include_router(manuscript_intelligence_router.router)
app.include_router(manuscript_intelligence_router.admin_router)
app.include_router(statistical_intelligence_router.router)
app.include_router(statistical_intelligence_router.admin_router)
app.include_router(academic_copilot_router.router)
app.include_router(academic_copilot_router.admin_router)
app.include_router(publishing_intelligence_router.router)
app.include_router(publishing_intelligence_router.admin_router)
app.include_router(autonomous_agents_router.router)
app.include_router(autonomous_agents_router.admin_router)
app.include_router(collab_intelligence_v2_router.router)
app.include_router(collab_intelligence_v2_router.admin_router)
app.include_router(institution_intelligence_v2_router.router)
app.include_router(institution_intelligence_v2_router.admin_router)
app.include_router(career_intelligence_router.router)
app.include_router(career_intelligence_router.admin_router)
app.include_router(knowledge_graph_router.router)
app.include_router(knowledge_graph_router.admin_router)
app.include_router(prediction_intelligence_router.router)
app.include_router(prediction_intelligence_router.admin_router)
app.include_router(self_improvement_router.router)
app.include_router(self_improvement_router.admin_router)
app.include_router(academic_os_router.router)
app.include_router(academic_os_router.admin_router)
app.include_router(trust_center_router.router)
app.include_router(timeline_router.router)
app.include_router(integrity_engine_router.router)
app.include_router(integrity_engine_router.admin_router)
app.include_router(institution_platform_router.router)
app.include_router(institution_platform_router.admin_router)
app.include_router(sie_router.router)
app.include_router(network_router.router)
app.include_router(acad_market_router.router)
app.include_router(acad_market_router.admin_router)
app.include_router(akg_router.router)
app.include_router(akg_router.admin_router)
app.include_router(proactive_router.router)
app.include_router(copilot_router.router)

from routers import lkg as lkg_router
app.include_router(lkg_router.router)

from routers import twin as twin_router
app.include_router(twin_router.router)

from routers import ara as ara_router
app.include_router(ara_router.router)

# Phase 7 — Public platform status endpoint
from routers.platform_status import router as platform_status_router
app.include_router(platform_status_router)

# Phase XXXV.4 — Enterprise Event Bus admin API
from events.router import router as events_router
app.include_router(events_router)

# Phase XXXV.5 — Enterprise Worker Platform admin API
from worker.router import router as worker_router
app.include_router(worker_router)

from obs.router import router as obs_router
app.include_router(obs_router)

# Phase XXXV.7 — Enterprise API Platform
from api.router import router as api_platform_router
app.include_router(api_platform_router)

# Phase XXXV.8 — Zero Trust Security Platform
from zt.router import router as zt_router
app.include_router(zt_router)


@app.get("/api/")
async def root():
    return {"service": "SYNAPTIQ", "status": "running"}


@app.get("/api/health/live")
async def liveness():
    """Kubernetes/Docker liveness probe — server is alive and not deadlocked.

    Returns 200 as long as the process is running and the event loop is responsive.
    Does NOT check external dependencies (MongoDB, Redis) — that is readiness's job.
    """
    return {"status": "alive"}


@app.get("/api/health/ready")
async def readiness():
    """Kubernetes/Docker readiness probe — server is ready to handle traffic.

    Returns 200 only when MongoDB is reachable (required for all API operations).
    Redis unavailability results in degraded=True but still ready (graceful fallback).
    Returns 503 when not ready so load balancers route traffic away.
    """
    import time
    from fastapi.responses import JSONResponse
    from services.redis_client import get_redis

    checks: dict = {}
    ready = True

    try:
        db = get_db()
        await db.command("ping")
        checks["mongodb"] = "ok"
    except Exception as exc:
        checks["mongodb"] = f"error: {str(exc)[:80]}"
        ready = False

    try:
        redis = await get_redis()
        checks["redis"] = "ok" if redis else "unavailable"
    except Exception:
        checks["redis"] = "unavailable"

    result = {
        "ready": ready,
        "degraded": checks.get("redis") != "ok",
        "checks": checks,
        "timestamp": time.time(),
    }
    return result if ready else JSONResponse(content=result, status_code=503)


@app.get("/api/health")
async def health():
    """Public health check used by uptime monitors (UptimeRobot, BetterStack, etc.)."""
    import shutil
    import time
    from fastapi.responses import JSONResponse
    from services.redis_client import get_redis
    from db import is_db_down, mark_db_down, mark_db_up, db_down_reason

    result = {
        "service": "SYNAPTIQ",
        "status": "ok",
        "timestamp": time.time(),
        "checks": {},
    }
    overall_ok = True

    # MongoDB Atlas connectivity. If the circuit breaker already knows Mongo is
    # down, don't even attempt the round-trip — a monitoring probe should never
    # itself queue behind a slow outage. Otherwise rely on the driver's own
    # serverSelectionTimeoutMS (db.py — now 4s, not asyncio.wait_for: wrapping a
    # Motor call in wait_for only stops *this* coroutine from waiting, it does
    # not cancel the underlying executor-thread work, which keeps running for
    # the full driver timeout regardless and can exhaust the thread pool under
    # repeated attempts — reproduced locally during this investigation).
    if is_db_down():
        result["checks"]["mongodb"] = "error"
        result["checks"]["mongodb_detail"] = db_down_reason()
        overall_ok = False
    else:
        try:
            db = get_db()
            await db.command("ping")
            result["checks"]["mongodb"] = "ok"
            mark_db_up()
        except Exception as e:
            result["checks"]["mongodb"] = "error"
            mark_db_down(e)
            logger.error("Health check — MongoDB unreachable: %s", e)
            overall_ok = False

    # Redis (optional — platform degrades gracefully without it)
    try:
        redis = await get_redis()
        if redis:
            await redis.ping()
            result["checks"]["redis"] = "ok"
        else:
            result["checks"]["redis"] = "unavailable"
    except Exception as e:
        result["checks"]["redis"] = "error"
        logger.warning("Health check — Redis error: %s", e)

    # Disk space (warn at >80%, fail at >95%)
    try:
        usage = shutil.disk_usage("/")
        pct = usage.used / usage.total * 100
        result["checks"]["disk_pct"] = round(pct, 1)
        if pct > 95:
            result["checks"]["disk"] = "critical"
            overall_ok = False
        elif pct > 80:
            result["checks"]["disk"] = "warning"
        else:
            result["checks"]["disk"] = "ok"
    except Exception:
        result["checks"]["disk"] = "unknown"

    if not overall_ok:
        result["status"] = "degraded"
        return JSONResponse(content=result, status_code=503)

    return result


@app.on_event("startup")
async def startup():
    # Production-mode env validation — REFUSES startup when required vars missing.
    validate_on_startup()

    # Redis: connect pool (non-fatal — degrades gracefully if unavailable)
    await init_redis()

    # WebSocket pub/sub listener (depends on Redis — starts regardless, degrades gracefully)
    await ws_manager.start()

    db = get_db()

    # AUTH-BUG-006: this handler runs dozens of sequential Mongo operations
    # (seed, index creation, backfills, migrations). Each one is individually
    # try/except-guarded and safe to skip (they're idempotent — re-run cleanly
    # on the next successful startup), but when Mongo/Atlas is unreachable each
    # one still pays its own server-selection timeout before its own
    # except-block gives up. That serialized cost — reproduced locally at
    # several minutes — blocks `Application startup complete`, and Uvicorn does
    # not accept ANY HTTP traffic (including /api/health) until lifespan
    # startup finishes. One Mongo hiccup at boot therefore looks like the
    # entire API being down, not just the database. Probe once and skip
    # straight to serving traffic if the database isn't there — migrations
    # simply run on the next restart once Mongo recovers. Relies on db.py's
    # own serverSelectionTimeoutMS (now 4s) rather than asyncio.wait_for: the
    # latter only stops this coroutine from waiting, it does not cancel the
    # underlying executor-thread work, which keeps running for the full
    # driver timeout regardless — see AUTH-BUG-007 in db.py.
    from db import mark_db_down, mark_db_up, classify_mongo_error
    try:
        await db.command("ping")
        mark_db_up()
    except Exception as ping_exc:
        mark_db_down(ping_exc)
        logger.error(
            "Startup: MongoDB unreachable — skipping seed/migrations for this run "
            "(idempotent, will run on next successful startup). %s",
            classify_mongo_error(ping_exc),
        )
        return

    try:
        # Drop legacy direct-message collection if present (old schema, no conversations)
        if "messages" in await db.list_collection_names():
            sample = await db.messages.find_one({})
            if sample and ("recipient_id" in sample or "sender_id" in sample) and "attachment_ids" not in sample:
                await db.messages.drop()
                logger.info("Dropped legacy messages collection (old schema)")
        # Phase XII: verify protected super-admin FIRST, before anything else
        sa_status = await ensure_super_admin_exists(db)
        logger.info("Super-admin check: action=%s rogue_stripped=%d",
                    sa_status["action"], sa_status["rogue_stripped"])

        await seed_admin_and_demo(db)
        logger.info("Seed complete")

        # ── Demo-data isolation migration (idempotent) ────────────────────────
        # Tag all records created by known demo accounts with is_demo:True so
        # they are excluded from every production-facing API query.
        _DEMO_EMAILS = [
            "elena.varga@synaptiq.academy",
            "marcus.okafor@synaptiq.academy",
            "aiko.tanaka@synaptiq.academy",
            "rafael.santos@synaptiq.academy",
            "priya.iyer@synaptiq.academy",
            "lukas.schmidt@synaptiq.academy",
        ]
        demo_user_cursor = db.users.find(
            {"email": {"$in": _DEMO_EMAILS}, "is_demo": {"$ne": True}},
            {"_id": 1},
        )
        demo_ids_to_tag = [str(u["_id"]) async for u in demo_user_cursor]
        if demo_ids_to_tag:
            await db.users.update_many(
                {"email": {"$in": _DEMO_EMAILS}}, {"$set": {"is_demo": True}}
            )
            await db.collaborations.update_many(
                {"creator_id": {"$in": demo_ids_to_tag}, "is_demo": {"$ne": True}},
                {"$set": {"is_demo": True}},
            )
            await db.projects.update_many(
                {"owner_id": {"$in": demo_ids_to_tag}, "is_demo": {"$ne": True}},
                {"$set": {"is_demo": True}},
            )
            logger.info(
                "Demo isolation: tagged %d demo user(s) and their collaborations/projects",
                len(demo_ids_to_tag),
            )

        # ── Core uniqueness indexes — run BEFORE any data inserts ─────────
        try:
            await db.users.create_index([("email", 1)], unique=True)
            logger.info("users.email unique index ensured")
        except Exception as ei:
            logger.warning("users.email index warning: %s", ei)

        # ── AUTH security indexes ──────────────────────────────────────────
        try:
            # AUTH-005: Refresh token registry
            await db.refresh_tokens.create_index([("jti", 1)], unique=True)
            await db.refresh_tokens.create_index([("user_id", 1)])
            await db.refresh_tokens.create_index([("expires_at", 1)], expireAfterSeconds=0)
            # AUTH-006: Account lockout
            await db.users.create_index([("locked_until", 1)], sparse=True)
            # AUTH-009: UUID JTI for email verifications + password resets
            await db.email_verifications.create_index([("jti", 1)], sparse=True)
            await db.password_resets.create_index([("jti", 1)], sparse=True)
            # TTL: auto-delete expired verification tokens and reset tokens
            await db.email_verifications.create_index([("expires_at", 1)], expireAfterSeconds=0)
            await db.password_resets.create_index([("expires_at", 1)], expireAfterSeconds=0)
            # AUTH-011: Audit log TTL (90 days) + security events TTL (180 days)
            await db.audit_log.create_index([("expires_at", 1)], expireAfterSeconds=0)
            await db.security_events.create_index([("expires_at", 1)], expireAfterSeconds=0)
            await db.audit_log.create_index([("action", 1), ("created_at", -1)])
            await db.audit_log.create_index([("actor_id", 1), ("created_at", -1)])
            await db.security_events.create_index([("event_type", 1), ("created_at", -1)])
            await db.security_events.create_index([("ip", 1), ("created_at", -1)])
            logger.info("Security indexes created")
        except Exception as sec_e:
            logger.warning("Security index creation warning: %s", sec_e)

        # ── AUTH-002: Backfill email_verified for existing users ───────────
        try:
            result = await db.users.update_many(
                {"email_verified": {"$exists": False}},
                {"$set": {"email_verified": True,
                          "email_verified_at": "2024-01-01T00:00:00+00:00"}},
            )
            if result.modified_count:
                logger.info("Backfilled email_verified=True for %d existing users", result.modified_count)
        except Exception as ev_e:
            logger.warning("email_verified backfill warning: %s", ev_e)

        # ── H1: Backfill email_marketing_consent for existing users ─────────
        # Existing users are treated as consented (they signed up).
        # New signups get True by default. Users can opt out via unsubscribe.
        try:
            result = await db.users.update_many(
                {"email_marketing_consent": {"$exists": False}},
                {"$set": {"email_marketing_consent": True}},
            )
            if result.modified_count:
                logger.info("Backfilled email_marketing_consent=True for %d users", result.modified_count)
        except Exception as mc_e:
            logger.warning("email_marketing_consent backfill warning: %s", mc_e)

        # ── AUTH-006: Backfill lockout fields for existing users ──────────
        try:
            await db.users.update_many(
                {"failed_login_count": {"$exists": False}},
                {"$set": {"failed_login_count": 0, "locked_until": None,
                          "last_failed_login": None, "last_successful_login": None}},
            )
        except Exception as lo_e:
            logger.warning("Lockout fields backfill warning: %s", lo_e)

        # --- Research OS migration: back-fill member_roles ---
        try:
            async for ws in db.workspaces.find({"member_roles": {"$exists": False}}):
                roles = {}
                owner_id = ws.get("owner_id")
                if owner_id: roles[owner_id] = "Owner"
                for m in ws.get("members", []):
                    if m != owner_id: roles[m] = "Researcher"
                await db.workspaces.update_one({"_id": ws["_id"]},
                    {"$set": {"member_roles": roles, "status": ws.get("status","active"),
                              "research_domain": ws.get("research_domain","")}})
            await db.workspace_invitations.create_index([("workspace_id", 1), ("user_id", 1), ("status", 1)])
            await db.manuscript_versions.create_index([("manuscript_id", 1), ("version", -1)])
            await db.manuscript_versions.create_index([("manuscript_id", 1), ("created_at", -1)])
            await db.manuscript_comments.create_index([("manuscript_id", 1), ("section", 1)])
            await db.manuscript_comments.create_index([("manuscript_id", 1), ("resolved", 1)])
            await db.manuscript_contributions.create_index([("manuscript_id", 1), ("user_id", 1), ("section", 1)], unique=True)
            await db.manuscript_contributions.create_index([("manuscript_id", 1), ("edits", -1)])
            await db.review_requests.create_index([("manuscript_id", 1), ("reviewer_id", 1)])
            await db.review_requests.create_index([("reviewer_id", 1), ("status", 1)])
            await db.review_requests.create_index([("manuscript_id", 1), ("status", 1)])
            await db.manuscript_references.create_index([("manuscript_id", 1), ("doi", 1)])
            await db.manuscript_references.create_index([("manuscript_id", 1), ("created_at", 1)])
            await db.manuscripts.create_index([("authors", 1), ("status", 1)])
            await db.manuscripts.create_index([("authors", 1), ("manuscript_type", 1)])
            await db.manuscripts.create_index([("workspace_id", 1), ("updated_at", -1)])
            await db.manuscripts.create_index([("project_id", 1), ("updated_at", -1)])
            await db.manuscripts.create_index([("lead_author_id", 1), ("created_at", -1)])
            await db.manuscripts.create_index([("doi", 1)], sparse=True)
            # Grant application collections
            await db.grant_applications.create_index([("pi_id", 1), ("status", 1)])
            await db.grant_applications.create_index([("pi_id", 1), ("grant_id", 1)])
            await db.grant_applications.create_index([("grant_id", 1), ("status", 1)])
            await db.grant_applications.create_index([("pi_id", 1), ("updated_at", -1)])
            await db.grant_team_members.create_index([("application_id", 1), ("user_id", 1)], unique=True)
            await db.grant_team_members.create_index([("user_id", 1), ("status", 1)])
            await db.grant_budget_items.create_index([("application_id", 1), ("category", 1)])
            await db.grant_deliverables.create_index([("application_id", 1), ("due_date", 1)])
            await db.grant_deliverables.create_index([("application_id", 1), ("status", 1)])
            await db.grant_proposal_versions.create_index([("application_id", 1), ("version", -1)])
            # Enhanced grants discovery indexes
            await db.grants.create_index([("research_areas", 1), ("deadline", 1)])
            await db.grants.create_index([("sponsor", 1), ("deadline", 1)])
            await db.grants.create_index([("country", 1), ("deadline", 1)])
            await db.grants.create_index([("funding_type", 1), ("deadline", 1)])
            await db.grants.create_index([("funding_amount.amount", -1)])
            await db.grants.create_index([("source", 1)])
            logger.info("Research OS migration complete")
        except Exception as mig_e:
            logger.warning("Research OS migration warning: %s", mig_e)

        # ── Knowledge Chunks + Timeline indexes (Phase 5 perf audit) ─────────
        try:
            await db.knowledge_chunks.create_index([("document_id", 1)])
            await db.knowledge_chunks.create_index([("user_id", 1), ("visibility", 1)])
            await db.knowledge_documents.create_index([("user_id", 1), ("status", 1)])
            await db.knowledge_documents.create_index([("workspace_id", 1)])
            await db.timeline_events.create_index([("user_id", 1), ("category", 1), ("created_at", -1)])
            await db.timeline_events.create_index([("user_id", 1), ("created_at", -1)])
            logger.info("Knowledge and timeline indexes ensured")
        except Exception as ki:
            logger.warning("Knowledge/timeline index warning: %s", ki)

        # ── Phase 7: Billing idempotency + commercial readiness indexes ───────
        try:
            # Unique index on stripe_event_id prevents double-processing webhook events
            await db.billing_events.create_index(
                [("stripe_event_id", 1)],
                unique=True,
                sparse=True,   # sparse so documents without stripe_event_id are excluded
                name="billing_events_idempotency",
            )
            await db.billing_events.create_index([("received_at", -1)])
            # Billing disputes for charge.dispute.created events
            await db.billing_disputes.create_index([("stripe_dispute_id", 1)], unique=True, sparse=True)
            await db.billing_disputes.create_index([("resolved", 1), ("created_at", -1)])
            # Platform incidents for /api/status endpoint
            await db.platform_incidents.create_index([("status", 1), ("created_at", -1)])
            await db.platform_incidents.create_index([("created_at", -1)])
            # Password reset tokens (TTL index — auto-deleted after 1800s / 30 min)
            await db.password_resets.create_index("expires_at", expireAfterSeconds=0, sparse=True)
            logger.info("Phase 7 commercial readiness indexes ensured")
        except Exception as p7_idx:
            logger.warning("Phase 7 index warning: %s", p7_idx)

        # ── Phase XX: Research Reputation & Trust System indexes ─────────────
        try:
            await db.research_reputation.create_index([("user_id", 1)], unique=True)
            await db.research_reputation.create_index([("overall_score", -1)])
            await db.research_reputation.create_index([("rank_global", 1)], sparse=True)
            await db.research_reputation.create_index([("rank_country", 1)], sparse=True)
            await db.research_reputation.create_index([("rank_institution", 1)], sparse=True)
            await db.research_reputation_events.create_index(
                [("user_id", 1), ("event_type", 1), ("source_entity_id", 1)], unique=True
            )
            await db.research_reputation_events.create_index([("user_id", 1), ("created_at", -1)])
            await db.research_reputation_events.create_index([("event_type", 1), ("created_at", -1)])
            await db.research_reputation_events.create_index([("created_at", -1)])
            await db.research_reputation_badges.create_index([("user_id", 1)], unique=True)
            await db.research_rankings.create_index([("computed_at", -1)])
            logger.info("Phase XX reputation indexes created")
        except Exception as rep_idx_e:
            logger.warning("Phase XX reputation index warning: %s", rep_idx_e)
        # ── Phase XXI: Recommendation Engine indexes ──────────────────────────
        try:
            await db.recommendation_profiles.create_index([("user_id", 1)], unique=True)
            await db.recommendation_profiles.create_index([("research_areas", 1)])
            await db.recommendation_profiles.create_index([("institution", 1)])
            await db.recommendation_profiles.create_index([("country", 1)])
            await db.recommendation_profiles.create_index([("academic_role", 1)])
            await db.recommendation_profiles.create_index([("updated_at", -1)])
            await db.recommendation_scores.create_index([("user_id", 1), ("category", 1)], unique=True)
            await db.recommendation_scores.create_index([("computed_at", -1)])
            await db.recommendation_interactions.create_index([("user_id", 1), ("recommendation_type", 1), ("target_id", 1)], unique=True)
            await db.recommendation_interactions.create_index([("user_id", 1), ("created_at", -1)])
            await db.recommendation_interactions.create_index([("recommendation_type", 1), ("action", 1)])
            await db.recommendation_interactions.create_index([("created_at", -1)])
            logger.info("Phase XXI recommendation engine indexes created")
        except Exception as rec_idx_e:
            logger.warning("Phase XXI recommendation index warning: %s", rec_idx_e)
        # ── Phase XXII: Research Impact Dashboard indexes ──────────────────────
        try:
            await db.research_impact.create_index([("user_id", 1)], unique=True)
            await db.research_impact.create_index([("sis_total", -1)])
            await db.research_impact.create_index([("h_index", -1)])
            await db.research_impact.create_index([("updated_at", -1)])
            await db.research_impact_history.create_index([("user_id", 1), ("computed_at", -1)])
            await db.research_impact_history.create_index([("computed_at", -1)])
            await db.research_impact_snapshots.create_index([("user_id", 1), ("created_at", -1)])
            logger.info("Phase XXII research impact indexes created")
        except Exception as impact_idx_e:
            logger.warning("Phase XXII impact index warning: %s", impact_idx_e)
        # ── Phase XXIII: Synaptiq AI OS indexes ───────────────────────────────
        try:
            await db.ai_conversations.create_index([("user_id", 1), ("updated_at", -1)])
            await db.ai_conversations.create_index([("user_id", 1), ("pinned", -1)])
            await db.ai_conversations.create_index([("user_id", 1), ("archived", 1)])
            await db.ai_messages.create_index([("conv_id", 1), ("created_at", 1)])
            await db.ai_messages.create_index([("user_id", 1), ("created_at", -1)])
            await db.ai_messages.create_index([("agent_type", 1)])
            await db.ai_memory.create_index([("user_id", 1), ("is_active", 1)])
            await db.ai_memory.create_index([("user_id", 1), ("memory_type", 1)])
            await db.ai_actions.create_index([("user_id", 1), ("created_at", -1)])
            await db.ai_actions.create_index([("action_type", 1), ("created_at", -1)])
            await db.ai_context_cache.create_index([("user_id", 1)], unique=True)
            await db.ai_context_cache.create_index([("computed_at", -1)])
            await db.ai_usage_analytics.create_index(
                [("user_id", 1), ("date", 1), ("agent_type", 1)], unique=True
            )
            await db.ai_usage_analytics.create_index([("date", -1)])
            logger.info("Phase XXIII AI OS indexes created")
        except Exception as ai_idx_e:
            logger.warning("Phase XXIII AI OS index warning: %s", ai_idx_e)
        try:
            await db.institution_impact.create_index([("institution_id", 1)], unique=True)
            await db.institution_impact.create_index([("iis_total", -1)])
            await db.institution_impact.create_index([("computed_at", -1)])
            await db.institution_verifications.create_index([("institution_id", 1)], unique=True)
            await db.institution_verifications_requests.create_index([("institution_id", 1), ("status", 1)])
            await db.institution_verifications_requests.create_index([("created_at", -1)])
            await db.institution_invites.create_index([("institution_id", 1), ("email", 1)], unique=True, sparse=True)
            await db.institution_invites.create_index([("institution_id", 1), ("status", 1)])
            logger.info("Phase XXIV Institution Hub indexes created")
        except Exception as hub_idx_e:
            logger.warning("Phase XXIV Institution Hub index warning: %s", hub_idx_e)
        try:
            await db.grant_collaborations.create_index([("lead_user_id", 1), ("status", 1)])
            await db.grant_collaborations.create_index([("status", 1), ("visibility", 1)])
            await db.grant_collaborations.create_index([("research_areas", 1)])
            await db.grant_collaborations.create_index([("deadline", 1)])
            await db.grant_collaborations.create_index([("created_at", -1)])
            await db.grant_consortia.create_index([("collaboration_id", 1)], unique=True)
            await db.grant_positions.create_index([("collaboration_id", 1), ("status", 1)])
            await db.grant_partner_matches.create_index([("collaboration_id", 1), ("score", -1)])
            await db.grant_partner_matches.create_index([("collaboration_id", 1), ("user_id", 1)], unique=True, sparse=True)
            await db.grant_team_invitations.create_index([("collaboration_id", 1), ("status", 1)])
            await db.grant_team_invitations.create_index([("to_user_id", 1), ("status", 1)])
            await db.grant_team_invitations.create_index([("expires_at", 1)])
            await db.grant_team_requirements.create_index([("collaboration_id", 1)], unique=True)
            await db.grant_work_packages.create_index([("collaboration_id", 1), ("status", 1)])
            await db.grant_collab_proposal_sections.create_index([("collaboration_id", 1), ("created_at", 1)])
            logger.info("Phase XXV Grant Collaboration Hub indexes created")
        except Exception as ghub_idx_e:
            logger.warning("Phase XXV Grant Hub index warning: %s", ghub_idx_e)
        try:
            await db.public_profiles.create_index([("user_id", 1)], unique=True)
            await db.public_profiles.create_index([("slug", 1)], unique=True)
            await db.public_profiles.create_index([("view_count", -1)])
            await db.profile_views.create_index([("profile_user_id", 1), ("viewed_at", -1)])
            await db.profile_views.create_index([("viewed_at", -1)])
            await db.profile_followers.create_index([("follower_id", 1), ("following_id", 1)], unique=True)
            await db.profile_followers.create_index([("following_id", 1)])
            await db.profile_followers.create_index([("follower_id", 1)])
            await db.profile_showcases.create_index([("user_id", 1), ("order", 1)])
            logger.info("Phase XXVI Public Profiles indexes created")
        except Exception as pp_idx_e:
            logger.warning("Phase XXVI Public Profiles index warning: %s", pp_idx_e)
        try:
            await db.reviewer_profiles.create_index([("user_id", 1)], unique=True)
            await db.reviewer_profiles.create_index([("reviewer_score", -1)])
            await db.reviewer_profiles.create_index([("research_areas", 1)])
            await db.reviewer_profiles.create_index([("country", 1)])
            await db.reviewer_profiles.create_index([("availability_status", 1)])
            await db.review_requests.create_index([("requester_user_id", 1)])
            await db.review_requests.create_index([("status", 1)])
            await db.review_requests.create_index([("review_type", 1)])
            await db.review_requests.create_index([("created_at", -1)])
            await db.review_assignments.create_index([("request_id", 1)])
            await db.review_assignments.create_index([("reviewer_user_id", 1)])
            await db.review_assignments.create_index([("request_id", 1), ("reviewer_user_id", 1)], unique=True)
            await db.review_reports.create_index([("request_id", 1)])
            await db.review_reports.create_index([("assignment_id", 1)], unique=True)
            await db.review_reports.create_index([("reviewer_user_id", 1)])
            await db.review_ratings.create_index([("reviewer_user_id", 1)])
            await db.review_ratings.create_index([("request_id", 1), ("rater_user_id", 1)], unique=True)
            await db.review_conflicts.create_index([("request_id", 1)])
            await db.review_conflicts.create_index([("request_id", 1), ("reviewer_user_id", 1)])
            await db.reviewer_certifications.create_index([("user_id", 1)])
            await db.reviewer_certifications.create_index([("user_id", 1), ("cert_type", 1)], unique=True)
            logger.info("Phase XXVII Reviewer Marketplace indexes created")
        except Exception as rmp_idx_e:
            logger.warning("Phase XXVII Reviewer Marketplace index warning: %s", rmp_idx_e)
        try:
            await db.institution_kpis.create_index([("institution_id", 1)], unique=True)
            await db.institution_kpis.create_index([("computed_at", -1)])
            await db.institution_analytics_history.create_index([("institution_id", 1), ("snapshot_date", -1)])
            await db.institution_analytics_history.create_index([("snapshot_date", -1)])
            await db.institution_forecasts.create_index([("institution_id", 1)])
            await db.institution_forecasts.create_index([("institution_id", 1), ("generated_at", -1)])
            await db.institution_reports.create_index([("institution_id", 1)])
            await db.institution_reports.create_index([("institution_id", 1), ("created_at", -1)])
            await db.institution_reports.create_index([("created_by", 1)])
            logger.info("Phase XXVIII Institution Analytics indexes created")
        except Exception as iac_idx_e:
            logger.warning("Phase XXVIII Institution Analytics index warning: %s", iac_idx_e)
        try:
            await db.verification_profiles.create_index([("user_id", 1)], unique=True)
            await db.verification_profiles.create_index([("verification_level", -1)])
            await db.verification_profiles.create_index([("verification_score", -1)])
            await db.verification_requests.create_index([("user_id", 1)])
            await db.verification_requests.create_index([("status", 1)])
            await db.verification_requests.create_index([("created_at", -1)])
            await db.verification_evidence.create_index([("user_id", 1)])
            await db.verification_evidence.create_index([("status", 1)])
            await db.verification_evidence.create_index([("created_at", -1)])
            await db.verification_audits.create_index([("user_id", 1)])
            await db.verification_audits.create_index([("created_at", -1)])
            await db.verification_badges.create_index([("user_id", 1)])
            await db.verification_badges.create_index([("user_id", 1), ("badge_type", 1)], unique=True)
            await db.verification_history.create_index([("user_id", 1)])
            await db.verification_history.create_index([("user_id", 1), ("created_at", -1)])
            logger.info("Phase XXIX Verification indexes created")
        except Exception as ver_idx_e:
            logger.warning("Phase XXIX Verification index warning: %s", ver_idx_e)
        try:
            init_storage()
            logger.info("Object storage initialized")
        except Exception as se:
            logger.warning("Object storage init deferred: %s", se)
        from services.notifications_service import register_default_providers
        register_default_providers()
        try:
            from services.email_service import register as register_email
            register_email()
        except Exception as ee:
            logger.warning("Email provider registration deferred: %s", ee)
        logger.info("Notification providers registered")
        # Discovery suite: ensure indexes + optionally start scheduler.
        try:
            from services.discovery import ensure_indexes as _ensure_disc, start_scheduler as _start_disc
            await _ensure_disc()
            await _start_disc()
        except Exception as de:
            logger.warning("Discovery init deferred: %s", de)
        # ORCID and citation weekly syncs are now managed by the Enterprise Scheduler
        # (Phase XXXV.5). Schedules are registered via start_worker_platform() at startup.
        logger.info("ORCID/citation weekly syncs managed by Enterprise Scheduler")
        # Marketplace + Reputation indexes
        try:
            await db.expertise_requests.create_index([("status", 1), ("created_at", -1)])
            await db.expertise_requests.create_index([("owner_id", 1)])
            await db.expertise_requests.create_index([("kind", 1)])
            await db.expertise_requests.create_index([("research_areas", 1)])
            await db.marketplace_invitations.create_index([("to_user_id", 1), ("status", 1)])
            await db.marketplace_invitations.create_index([("from_user_id", 1)])
            await db.marketplace_invitations.create_index([("entity_id", 1), ("kind", 1)])
            await db.marketplace_invitations.create_index([("created_at", -1)])
            await db.marketplace_invitations.create_index(
                [("from_user_id", 1), ("to_user_id", 1), ("kind", 1), ("entity_id", 1), ("status", 1)])
            # Team memberships — collaboration acceptance tracking
            await db.team_memberships.create_index([("user_id", 1), ("entity_type", 1)])
            await db.team_memberships.create_index([("entity_id", 1), ("entity_type", 1)])
            await db.team_memberships.create_index([("inviter_id", 1)])
            await db.team_memberships.create_index([("invitation_id", 1)])
            # Collaboration requests — expiry and status queries
            await db.collaboration_requests.create_index([("expires_at", 1), ("status", 1)])
            await db.collaboration_requests.create_index([("status", 1), ("created_at", -1)])
            await db.reputation_scores.create_index([("user_id", 1)], unique=True)
            # Institutional Layer
            await db.institutions.create_index([("name", 1)])
            await db.institutions.create_index([("country", 1), ("type", 1)])
            await db.institutions.create_index([("email_domains", 1)])
            await db.units.create_index([("institution_id", 1), ("parent_id", 1)])
            await db.units.create_index([("institution_id", 1), ("type", 1)])
            await db.institution_memberships.create_index(
                [("institution_id", 1), ("user_id", 1)], unique=True)
            await db.institution_memberships.create_index([("user_id", 1)])
            await db.institution_memberships.create_index([("institution_id", 1), ("status", 1)])
            await db.institution_audit.create_index([("institution_id", 1), ("created_at", -1)])
            # Publications (ORCID-sourced canonical store)
            await db.publications.create_index([("owner_id", 1), ("year", -1)])
            await db.publications.create_index([("doi", 1)], sparse=True)
            await db.publications.create_index([("orcid_put_code", 1)], sparse=True)
            await db.publications.create_index([("title_norm", 1)])
            # Research File Layer
            await db.files.create_index([("entity_kind", 1), ("entity_id", 1), ("is_latest", -1)])
            await db.files.create_index([("owner_id", 1), ("created_at", -1)])
            await db.files.create_index([("root_id", 1), ("version", -1)])
            await db.files.create_index([("sha256", 1)])
            await db.file_activity.create_index([("file_id", 1), ("created_at", -1)])
            # Email verification + consent
            await db.email_verifications.create_index([("user_id", 1), ("used", 1)])
            await db.email_verifications.create_index([("token_jti", 1)])
            await db.consent_records.create_index([("user_id", 1), ("created_at", -1)])
            await db.consent_records.create_index([("consent_id", 1), ("created_at", -1)])
            # AI Manuscript Reviews
            await db.manuscript_reviews.create_index([("user_id", 1), ("created_at", -1)])
            await db.manuscript_reviews.create_index([("manuscript_id", 1)], sparse=True)
            # AI Literature Reviews
            await db.literature_reviews.create_index([("user_id", 1), ("created_at", -1)])
            await db.literature_reviews.create_index([("user_id", 1), ("topic", 1)])
            # AI Research Gap Finder
            await db.research_gap_reviews.create_index([("user_id", 1), ("created_at", -1)])
            await db.research_gap_reviews.create_index([("user_id", 1), ("topic", 1)])
            # AI Research Design Advisor
            await db.research_design_reviews.create_index([("user_id", 1), ("created_at", -1)])
            await db.research_design_reviews.create_index([("user_id", 1), ("topic", 1)])
            # AI Statistical Review
            await db.statistical_reviews.create_index([("user_id", 1), ("created_at", -1)])
            await db.statistical_reviews.create_index([("user_id", 1), ("topic", 1)])
            # Citation Monitoring — compound indexes on publications for dashboard queries
            await db.publications.create_index([("owner_id", 1), ("citations", -1)])
            await db.publications.create_index([("owner_id", 1), ("openalex_enriched_at", -1)])
            await db.publications.create_index([("openalex_id", 1)], sparse=True)
            await db.publications.create_index(
                [("owner_id", 1), ("topics", 1)], sparse=True)
            await db.publications.create_index(
                [("owner_id", 1), ("concepts", 1)], sparse=True)
            # Citation Tracker — dedicated snapshot / alert collections
            await db.publication_citations.create_index([("user_id", 1), ("pub_id", 1), ("created_at", -1)])
            await db.publication_citations.create_index([("user_id", 1), ("snapshot_month", 1)])
            # Unique compound index on citation_sources prevents duplicate citing-work records
            await db.citation_sources.create_index(
                [("user_id", 1), ("pub_id", 1), ("citing_doi", 1)],
                unique=True, sparse=True)
            await db.citation_sources.create_index([("user_id", 1), ("pub_id", 1)])
            await db.citation_sources.create_index([("user_id", 1), ("detected_at", -1)])
            await db.citation_alerts.create_index([("user_id", 1), ("read", 1), ("created_at", -1)])
            await db.citation_alerts.create_index([("user_id", 1), ("pub_id", 1), ("alert_type", 1)])
            # Collaboration Intelligence
            await db.collaboration_recommendations.create_index([("user_id", 1), ("created_at", -1)])
            await db.collaboration_scores.create_index([("requester_id", 1), ("candidate_id", 1)])
            await db.collaboration_scores.create_index([("requester_id", 1), ("created_at", -1)])
            # Collaboration Requests
            await db.collaboration_requests.create_index([("sender_id", 1), ("created_at", -1)])
            await db.collaboration_requests.create_index([("receiver_id", 1), ("status", 1)])
            await db.collaboration_requests.create_index([("sender_id", 1), ("receiver_id", 1), ("status", 1)])
            # Research Impact Dashboard
            await db.user_research_goals.create_index([("user_id", 1)], unique=True)
            # Department Management
            await db.department_projects.create_index(
                [("department_id", 1), ("project_id", 1)], unique=True)
            await db.department_projects.create_index([("department_id", 1), ("linked_at", -1)])
            await db.department_projects.create_index([("institution_id", 1)])
            await db.department_metrics.create_index([("department_id", 1)], unique=True)
            await db.department_metrics.create_index([("institution_id", 1)])
            # Collaboration Activity
            await db.collaboration_activity.create_index([("user_id", 1), ("created_at", -1)])
            await db.collaboration_activity.create_index([("action", 1), ("created_at", -1)])
            # Connection Requests
            await db.connection_requests.create_index(
                [("sender_id", 1), ("receiver_id", 1), ("status", 1)])
            await db.connection_requests.create_index([("receiver_id", 1), ("status", 1)])
            await db.connection_requests.create_index([("sender_id", 1), ("created_at", -1)])
            # Workspace Invitations — expiry index (ISO string compare via sort)
            await db.workspace_invitations.create_index([("expires_at", 1)])
            # Billing v2 — credit ledger, packs, history
            await db.credit_transactions.create_index([("user_id", 1), ("created_at", -1)])
            await db.credit_transactions.create_index([("kind", 1), ("bucket", 1)])
            await db.credit_purchases.create_index([("user_id", 1), ("created_at", -1)])
            await db.credit_purchases.create_index([("stripe_checkout_session_id", 1)], sparse=True)
            await db.billing_history.create_index([("user_id", 1), ("created_at", -1)])
            await db.subscription_history.create_index([("user_id", 1), ("created_at", -1)])
            await db.subscriptions.create_index([("stripe_subscription_id", 1)], sparse=True)
            await db.subscriptions.create_index([("user_id", 1), ("status", 1)])
            # Admin platform indexes
            await db.audit_log.create_index([("created_at", -1)])
            await db.audit_log.create_index([("action", 1), ("created_at", -1)])
            await db.audit_log.create_index([("actor_id", 1), ("created_at", -1)])
            await db.audit_log.create_index([("target_id", 1), ("created_at", -1)])
            await db.security_events.create_index([("event_type", 1), ("created_at", -1)])
            await db.security_events.create_index([("ip", 1), ("created_at", -1)])
            await db.blocked_ips.create_index([("ip", 1)], unique=True)
            await db.email_templates.create_index([("name", 1)], unique=True)
            await db.email_campaigns.create_index([("status", 1), ("created_at", -1)])
            await db.email_log.create_index([("created_at", -1)])
            await db.email_log.create_index([("to", 1), ("created_at", -1)])
            await db.email_log.create_index([("kind", 1), ("created_at", -1)])
            await db.email_log.create_index([("status", 1), ("created_at", -1)])
            await db.users.create_index([("status", 1)])
            # Admin operations indexes
            await db.feature_flags.create_index([("name", 1)], unique=True)
            await db.platform_settings.create_index([("key", 1)], unique=True)
            await db.announcements.create_index([("created_at", -1)])
            await db.email_preferences.create_index([("user_id", 1)], unique=True, sparse=True)
            # Engagement precomputed scores
            await db.users.create_index([("engagement_score", -1)])
            await db.users.create_index([("engagement_tier", 1)])
            # GDPR consent
            await db.users.create_index([("email_marketing_consent", 1)])
            # AI Abstract Generator
            await db.abstract_generations.create_index([("user_id", 1), ("created_at", -1)])
            # AI Rewriting
            await db.rewriting_requests.create_index([("user_id", 1), ("created_at", -1)])
            # Teaching Hub collections
            await db.teaching_lessons.create_index([("owner_id", 1), ("created_at", -1)])
            await db.teaching_lessons.create_index([("owner_id", 1), ("status", 1)])
            await db.teaching_assessments.create_index([("owner_id", 1), ("created_at", -1)])
            await db.teaching_assessments.create_index([("owner_id", 1), ("assessment_type", 1)])
            await db.teaching_portfolio_items.create_index([("owner_id", 1), ("featured", -1), ("date", -1)])
            await db.teaching_workspaces.create_index([("owner_id", 1), ("updated_at", -1)])
            await db.teaching_workspaces.create_index([("member_ids", 1)])
            await db.teaching_chat_messages.create_index([("workspace_id", 1), ("owner_id", 1), ("created_at", 1)])
            # ── Teaching Analytics (Phase 9) — analytics-heavy collection indexes ──
            await db.teaching_workspace_activity.create_index([("actor_id", 1), ("created_at", -1)])
            await db.teaching_workspace_activity.create_index([("workspace_id", 1), ("kind", 1), ("created_at", -1)])
            await db.teaching_workspace_comments.create_index([("author_id", 1), ("created_at", -1)])
            await db.teaching_workspace_comments.create_index([("workspace_id", 1), ("created_at", -1)])
            await db.teaching_workspace_invitations.create_index([("inviter_id", 1), ("status", 1), ("created_at", -1)])
            await db.teaching_workspace_invitations.create_index([("invitee_id", 1), ("status", 1)])
            await db.teaching_lesson_versions.create_index([("author_id", 1), ("created_at", -1)])
            await db.teaching_assessment_versions.create_index([("author_id", 1), ("created_at", -1)])
            await db.teaching_chat_messages.create_index([("owner_id", 1), ("role", 1), ("created_at", -1)])
            await db.reputation_scores.create_index([("user_id", 1)], unique=True, sparse=True)
            await db.reputation_badges.create_index([("user_id", 1)], unique=True, sparse=True)
            # Free-plan discovery quota tracking
            await db.discovery_usage.create_index(
                [("user_id", 1), ("kind", 1), ("month", 1)], unique=True)
            # ── Scalability indexes — 100k+ user / 1M+ message scale ────────────
            # Submissions — compound stage+updated_at for pipeline queries
            await db.submissions.create_index([("manuscript_id", 1), ("stage", 1)])
            await db.submissions.create_index([("author_id", 1), ("stage", 1)])
            await db.submissions.create_index([("author_id", 1), ("updated_at", -1)])
            # Messages — cursor-pagination compound index (avoid full collection scans at 1M+ msgs)
            await db.messages.create_index([("conversation_id", 1), ("created_at", -1)])
            await db.messages.create_index([("conversation_id", 1), ("deleted", 1), ("created_at", -1)])
            await db.messages.create_index([("sender_id", 1), ("created_at", -1)])
            # Task assignee lookup
            await db.tasks.create_index([("assignee_id", 1), ("status", 1)], sparse=True)
            # Message attachments — owner lookup for upload/download auth
            await db.message_attachments.create_index([("owner_id", 1), ("created_at", -1)])
            await db.message_attachments.create_index([("is_deleted", 1), ("created_at", -1)])
            # Manuscript contributions — section analytics
            await db.manuscript_contributions.create_index([("manuscript_id", 1), ("chars_changed", -1)])
            # Collaboration scores — faster candidate lookups
            await db.collaboration_scores.create_index([("candidate_id", 1), ("requester_id", 1)])
            # Connection requests — fast inbox + status lookup
            await db.connection_requests.create_index([("receiver_id", 1), ("created_at", -1)])
            logger.info("Scalability indexes ensured")
            # ── Performance-critical missing indexes (DB-CERT Phase 2) ─────────
            # Conversations / messaging — hot lookup on every message auth check
            await db.conversation_members.create_index(
                [("conversation_id", 1), ("user_id", 1)], unique=True)
            await db.conversation_members.create_index([("user_id", 1), ("updated_at", -1)])
            await db.conversations.create_index([("updated_at", -1)])
            await db.conversations.create_index([("last_message_at", -1)])
            await db.conversations.create_index([("context_key", 1)], unique=True, sparse=True)
            await db.message_reactions.create_index([("message_id", 1)])
            await db.message_reactions.create_index(
                [("message_id", 1), ("user_id", 1), ("emoji", 1)], unique=True)
            await db.message_reads.create_index(
                [("conversation_id", 1), ("user_id", 1)], unique=True, sparse=True)
            # Workspace activity feed
            await db.workspace_activity.create_index([("workspace_id", 1), ("created_at", -1)])
            await db.workspace_activity.create_index([("workspace_id", 1), ("kind", 1), ("created_at", -1)])
            await db.workspace_activity.create_index([("actor_id", 1), ("created_at", -1)])
            # Workspace invitations
            await db.workspace_invitations.create_index([("user_id", 1), ("status", 1), ("created_at", -1)])
            await db.workspace_invitations.create_index([("workspace_id", 1), ("status", 1)])
            await db.workspace_invitations.create_index([("invited_by", 1)])
            # Workspace search and list queries
            await db.workspaces.create_index([("owner_id", 1), ("updated_at", -1)])
            await db.workspaces.create_index([("workspace_type", 1), ("updated_at", -1)])
            await db.workspaces.create_index([("status", 1), ("workspace_type", 1)])
            await db.workspaces.create_index([("institution", 1)])
            # Workspace tasks
            await db.workspace_tasks.create_index([("workspace_id", 1), ("status", 1)])
            await db.workspace_tasks.create_index([("workspace_id", 1), ("assignee_id", 1)])
            await db.workspace_tasks.create_index([("workspace_id", 1), ("created_at", -1)])
            # Members array lookups — critical for list_workspaces / list_projects
            await db.workspaces.create_index([("members", 1)])
            await db.projects.create_index([("members", 1)])
            await db.projects.create_index([("members", 1), ("visibility", 1)])
            # Manuscripts by workspace and sort
            await db.manuscripts.create_index([("workspace_id", 1), ("updated_at", -1)])
            await db.manuscripts.create_index([("updated_at", -1)])
            # credit_usage is deprecated (no longer written to) — index kept for historical queries
            await db.credit_usage.create_index([("user_id", 1), ("created_at", -1)])
            # Review requests by reviewer for my_reviews endpoint
            await db.review_requests.create_index([("reviewer_id", 1), ("status", 1)])
            # Notifications compound for read-filtered dashboard queries
            await db.notifications.create_index([("user_id", 1), ("read", 1), ("created_at", -1)])
            # Tasks compound for kanban + filtering
            await db.tasks.create_index([("project_id", 1), ("status", 1)])
            await db.tasks.create_index([("project_id", 1), ("created_at", -1)])
            # Milestones sort
            await db.milestones.create_index([("project_id", 1), ("due_date", 1)])
            # ORCID uniqueness — prevents two accounts sharing the same verified ORCID
            await db.users.create_index([("orcid.orcid_id", 1)], sparse=True)
            # Discovery / search indexes
            await db.users.create_index([("research_areas", 1)])
            await db.users.create_index([("research_keywords", 1)])
            await db.users.create_index([("methods", 1)])
            await db.users.create_index([("software_skills", 1)])
            await db.users.create_index([("country", 1), ("research_areas", 1)])
            await db.users.create_index([("institution", 1)])
            await db.users.create_index([("user_type", 1), ("research_areas", 1)])
            await db.users.create_index([("h_index", -1)])
            await db.users.create_index([("publications_count", -1)])
            await db.users.create_index([("available_for_collaboration", 1)])
            await db.users.create_index([("available_for_reviewing", 1)])
            await db.users.create_index([("available_for_consulting", 1)])
            await db.users.create_index([("available_for_supervision", 1)])
            await db.users.create_index([("profile_visibility", 1)])
            await db.users.create_index([("openalex_author_id", 1)], sparse=True)
            await db.users.create_index([("last_updated", -1)])
            # Text index for full-text search
            await db.users.create_index([
                ("full_name", "text"), ("institution", "text"),
                ("department", "text"), ("biography", "text"),
                ("research_areas", "text"), ("research_keywords", "text"),
                ("methods", "text"), ("software_skills", "text"),
                ("skills", "text"),
            ], name="users_fulltext", default_language="english")
            # Saved researchers
            await db.saved_researchers.create_index([("user_id", 1), ("saved_user_id", 1)], unique=True)
            await db.saved_researchers.create_index([("user_id", 1), ("created_at", -1)])
            await db.saved_researchers.create_index([("saved_user_id", 1)])
            # Profile views
            await db.profile_views.create_index([("viewed_id", 1), ("created_at", -1)])
            await db.profile_views.create_index([("viewer_id", 1), ("created_at", -1)])
            await db.profile_views.create_index([("viewed_id", 1), ("viewer_id", 1)])
            # Workspace invitations — partial unique index prevents concurrent duplicate pending
            await db.workspace_invitations.create_index(
                [("workspace_id", 1), ("user_id", 1)],
                unique=True,
                partialFilterExpression={"status": "pending"},
                name="unique_pending_ws_invitation",
            )
            # Connection requests — partial unique index prevents concurrent duplicate pending
            await db.connection_requests.create_index(
                [("sender_id", 1), ("receiver_id", 1)],
                unique=True,
                partialFilterExpression={"status": "pending"},
                name="unique_pending_connection_request",
            )
            # Subscriptions for active-subscription lookups
            await db.subscriptions.create_index([("user_id", 1), ("current_period_end", -1)])
            # User research goals (impact dashboard)
            await db.user_research_goals.create_index([("user_id", 1)], unique=True)
            # Discover feed — grants and conferences sorted by recency (L-2 fix)
            await db.grants.create_index([("created_at", -1)])
            await db.grants.create_index([("deadline", 1)], sparse=True)
            await db.conferences.create_index([("created_at", -1)])
            await db.conferences.create_index([("start_date", 1)], sparse=True)
            # Email campaigns — status lookup for bulk send progress polling
            await db.email_campaigns.create_index([("status", 1), ("created_at", -1)])
            await db.email_campaigns.create_index([("sent_by", 1), ("created_at", -1)])
            logger.info("Marketplace indexes ensured")
        except Exception as me:
            logger.warning("Marketplace index init deferred: %s", me)

        # ── Institution Platform Phase 11 indexes ────────────────────────────
        try:
            # Invite store for users not yet registered
            await db.institution_invites.create_index(
                [("institution_id", 1), ("email", 1)], unique=True)
            await db.institution_invites.create_index([("email", 1)])
            await db.institution_invites.create_index([("status", 1)])
            # Faster doctoral queries: filter by academic_role
            await db.users.create_index([("academic_role", 1), ("institution_id", 1)])
            # Research-office pipeline queries
            await db.grant_applications.create_index([("pi_id", 1), ("status", 1)])
            await db.grant_applications.create_index([("pi_id", 1), ("updated_at", -1)])
            # Funding trend merge (grant_applications by year)
            await db.grant_applications.create_index([("updated_at", 1), ("status", 1)])
            # Department metrics cache
            await db.department_metrics.create_index(
                [("department_id", 1)], unique=True)
            await db.department_metrics.create_index([("computed_at", 1)])
            logger.info("Institution Platform Phase 11 indexes ensured")
        except Exception as ie:
            logger.warning("Institution Phase 11 index init deferred: %s", ie)

        # ── Research Analytics indexes ────────────────────────────────────────
        try:
            await db.publications.create_index([("user_id", 1), ("year", -1)])
            await db.publications.create_index([("user_id", 1), ("citations", -1)])
            await db.openalex_metrics.create_index([("user_id", 1)], unique=True)
            await db.grant_links.create_index([("user_id", 1), ("status", 1)])
            await db.grant_links.create_index([("user_id", 1), ("year_start", -1)])
            await db.manuscripts.create_index([("authors", 1)])
            await db.submissions.create_index([("manuscript_id", 1), ("stage", 1)])
            await db.submissions.create_index([("manuscript_id", 1), ("submitted_at", -1)])
            logger.info("Research Analytics indexes ensured")
        except Exception as ra:
            logger.warning("Research Analytics index init deferred: %s", ra)

        # ── Phase XI expansion indexes ────────────────────────────────────────
        try:
            await db.api_stats.create_index([("endpoint", 1), ("method", 1), ("date", 1)], unique=True)
            await db.api_stats.create_index([("date", -1)])
            await db.api_error_log.create_index([("created_at", -1)])
            await db.background_jobs.create_index([("kind", 1), ("status", 1)])
            await db.background_jobs.create_index([("created_at", -1)])
            await db.background_jobs.create_index([("status", 1), ("scheduled_at", 1)])
            await db.search_queries.create_index([("module", 1), ("created_at", -1)])
            await db.search_queries.create_index([("query", 1)])
            await db.search_queries.create_index([("created_at", -1)])
            await db.support_tickets.create_index([("status", 1), ("priority", 1)])
            await db.support_tickets.create_index([("created_at", -1)])
            await db.support_tickets.create_index([("assigned_to", 1)])
            await db.release_history.create_index([("released_at", -1)])
            await db.release_history.create_index([("version", 1)], unique=True, sparse=True)
            await db.executive_briefings.create_index([("kind", 1), ("created_at", -1)])
            await db.uploads.create_index([("user_id", 1)])
            await db.uploads.create_index([("size_bytes", -1)])
            await db.uploads.create_index([("created_at", -1)])
            logger.info("Phase XI expansion indexes ensured")
        except Exception as xi_e:
            logger.warning("Phase XI index init deferred: %s", xi_e)

        # ── AOS indexes ───────────────────────────────────────────────────────
        try:
            await db.error_logs.create_index([("severity", 1), ("resolved", 1)])
            await db.error_logs.create_index([("first_seen", -1)])
            await db.error_logs.create_index([("last_seen", -1)])
            await db.error_logs.create_index([("category", 1), ("severity", 1)])
            await db.platform_audit_reports.create_index([("_id", 1)])
            await db.platform_banners.create_index([("active", 1)])
            await db.promotion_campaigns.create_index([("active", 1), ("created_at", -1)])
            await db.subscription_history.create_index([("user_id", 1), ("created_at", -1)])
            await db.subscription_history.create_index([("from_plan", 1), ("to_plan", 1), ("created_at", -1)])
            await db.billing_history.create_index([("kind", 1), ("status", 1), ("created_at", -1)])
            logger.info("AOS indexes ensured")
        except Exception as aos_e:
            logger.warning("AOS index init deferred: %s", aos_e)

        # ── Phase XII security hardening indexes ──────────────────────────────
        try:
            # MFA configs
            await db.mfa_configs.create_index("user_id", unique=True)
            # Trusted devices
            await db.trusted_devices.create_index([("user_id", 1), ("fingerprint", 1)], unique=True)
            await db.trusted_devices.create_index([("user_id", 1), ("revoked", 1)])
            # Security events (enhanced)
            await db.security_events.create_index([("severity", 1), ("resolved", 1), ("created_at", -1)])
            await db.security_events.create_index([("event_type", 1), ("created_at", -1)])
            await db.security_events.create_index([("actor_email", 1), ("created_at", -1)])
            # IP allowlist
            await db.ip_allowlist.create_index([("ip", 1), ("active", 1)])
            # Break-glass events
            await db.break_glass_events.create_index("token_hash", unique=True, sparse=True)
            await db.break_glass_events.create_index("created_at")
            # Refresh tokens — add ip/device_info for session center
            await db.refresh_tokens.create_index([("user_id", 1), ("revoked", 1), ("issued_at", -1)])
            logger.info("Phase XII security indexes ensured")
        except Exception as p12_e:
            logger.warning("Phase XII index init deferred: %s", p12_e)

    except Exception as e:
        logger.exception("Seed failed: %s", e)


async def _citation_weekly_sync_job():
    """Background task: refresh OpenAlex citations weekly for all users with publications.

    Runs on a 7-day interval. Staggers user syncs with a 0.5s delay to stay
    within OpenAlex polite-pool rate limits. Skips users synced in the last 6 days
    so a manual sync earlier in the week doesn't block the weekly refresh.
    """
    import asyncio
    from datetime import datetime, timedelta, timezone
    from services.citations.sync_service import sync_user_citations

    ONE_WEEK = 7 * 24 * 3600

    while True:
        await asyncio.sleep(ONE_WEEK)
        try:
            db_ref = make_db_proxy(get_db(), system=True)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
            # Find users who have at least one publication not enriched recently
            stale_owners = await db_ref.publications.distinct(
                "owner_id",
                {
                    "$or": [
                        {"openalex_enriched_at": {"$exists": False}},
                        {"openalex_enriched_at": {"$lt": cutoff}},
                    ]
                },
            )
            count = errors = 0
            for uid in stale_owners:
                try:
                    await sync_user_citations(db_ref, uid, pub_limit=200, inter_pub_delay=0.2)
                    count += 1
                    await asyncio.sleep(0.5)
                except Exception as sync_err:
                    logger.warning("Weekly citation sync: user %s failed: %s", uid, sync_err)
                    errors += 1
            logger.info("Weekly citation sync complete: synced=%d errors=%d", count, errors)
        except Exception as job_err:
            logger.error("Weekly citation sync job error: %s", job_err)


async def _orcid_weekly_sync_job():
    """Background task: auto-sync ORCID profiles that are stale (> 7 days without sync).

    Runs on a recurring 7-day interval. Skips gracefully when ORCID is not configured
    or when the server is under high load. Each user is synced with a 2-second delay to
    stay within ORCID API rate limits.
    """
    import asyncio
    from datetime import datetime, timedelta, timezone
    from services.orcid.sync import sync_user
    from services.orcid.oauth import is_configured

    ONE_WEEK = 7 * 24 * 3600

    while True:
        await asyncio.sleep(ONE_WEEK)
        if not is_configured():
            logger.info("ORCID weekly sync: ORCID not configured, skipping")
            continue
        try:
            db_ref = make_db_proxy(get_db(), system=True)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            stale_cursor = db_ref.users.find(
                {
                    "orcid.orcid_id": {"$exists": True, "$ne": None},
                    "$or": [
                        {"orcid.last_sync_at": {"$exists": False}},
                        {"orcid.last_sync_at": {"$lt": cutoff}},
                    ],
                },
                {"_id": 1},
            )
            count = errors = 0
            async for u in stale_cursor:
                uid = str(u["_id"])
                try:
                    await sync_user(uid, trigger="scheduled")
                    count += 1
                    await asyncio.sleep(2)
                except Exception as sync_err:
                    logger.warning("ORCID weekly sync: user %s failed: %s", uid, sync_err)
                    errors += 1
            logger.info("ORCID weekly sync complete: synced=%d errors=%d", count, errors)
        except Exception as job_err:
            logger.error("ORCID weekly sync job error: %s", job_err)


@app.on_event("startup")
async def start_ara_engine():
    """Start the durable ARA Mission Execution Engine (Phase XXXV.2)."""
    import asyncio
    from db import is_db_down
    if is_db_down():
        logger.warning("ARA engine startup skipped — database unavailable")
        return
    db = get_db()
    try:
        from ara.engine import start_engine
        asyncio.create_task(start_engine(db))
    except Exception as exc:
        logger.warning("ARA engine startup error (non-fatal): %s", exc)


@app.on_event("startup")
async def start_enterprise_event_bus():
    """Start the Enterprise Event Bus (Phase XXXV.4)."""
    import asyncio
    from db import is_db_down
    if is_db_down():
        logger.warning("Event bus startup skipped — database unavailable")
        return
    db = get_db()
    try:
        from events import start_event_bus
        asyncio.create_task(start_event_bus(db))
    except Exception as exc:
        logger.warning("Event bus startup error (non-fatal): %s", exc)


@app.on_event("startup")
async def start_enterprise_worker_platform():
    """Start the Enterprise Worker Platform's auto-recovery supervisor
    (Phase XXXV.5 + RC production blocker fix).

    The supervisor (not a one-shot attempt) runs for the whole process
    lifetime: it starts the platform the moment Mongo is reachable — whether
    that's immediately, or minutes later after a startup-time outage clears —
    and restarts it if it ever stops unexpectedly. No manual restart is ever
    required to recover this subsystem after a Mongo/Redis reconnect.
    """
    try:
        from worker import start_worker_platform_supervisor
        start_worker_platform_supervisor()
    except Exception as exc:
        logger.warning("Worker platform supervisor failed to start (non-fatal): %s", exc)


@app.on_event("startup")
async def start_observability_platform():
    """Start the Enterprise Observability Platform (Phase XXXV.6)."""
    from db import is_db_down
    if is_db_down():
        logger.warning("Observability platform startup skipped — database unavailable")
        return
    db = get_db()
    try:
        from obs import init_observability
        await init_observability(db)
    except Exception as exc:
        logger.warning("Observability platform startup error (non-fatal): %s", exc)


@app.on_event("startup")
async def start_api_platform():
    """Start the Enterprise API Platform (Phase XXXV.7)."""
    from db import is_db_down
    if is_db_down():
        logger.warning("API platform startup skipped — database unavailable")
        return
    db = get_db()
    try:
        from api import init_api_platform
        await init_api_platform(app, db)
    except Exception as exc:
        logger.warning("API platform startup error (non-fatal): %s", exc)


@app.on_event("startup")
async def start_zero_trust_platform():
    """Start the Zero Trust Security Platform (Phase XXXV.8)."""
    from db import is_db_down
    if is_db_down():
        logger.warning("Zero Trust platform startup skipped — database unavailable")
        return
    db = get_db()
    try:
        from zt import init_zero_trust
        await init_zero_trust(app, db)
    except Exception as exc:
        logger.warning("Zero Trust platform startup error (non-fatal): %s", exc)


@app.on_event("startup")
async def run_startup_cleanup():
    """Phase 7: Run cleanup service once at startup (non-fatal)."""
    from db import is_db_down
    if is_db_down():
        logger.warning("Startup cleanup skipped — database unavailable")
        return
    try:
        from services.cleanup_service import run_all
        await run_all()
    except Exception as exc:
        logger.warning("Startup cleanup error (non-fatal): %s", exc)


@app.on_event("shutdown")
async def shutdown():
    try:
        from ara.engine import stop_engine
        await stop_engine()
    except Exception:
        pass
    try:
        from events import stop_event_bus
        await stop_event_bus()
    except Exception:
        pass
    try:
        from worker import stop_worker_platform_supervisor
        await stop_worker_platform_supervisor()
    except Exception:
        pass
    try:
        from obs import stop_observability
        await stop_observability()
    except Exception:
        pass
    try:
        from api import stop_api_platform
        await stop_api_platform()
    except Exception:
        pass
    try:
        from zt import stop_zero_trust
        await stop_zero_trust()
    except Exception:
        pass
    try:
        from services.discovery import stop_scheduler
        from services.discovery.http import close_http
        await stop_scheduler()
        await close_http()
    except Exception:
        pass
    try:
        await ws_manager.stop()
    except Exception:
        pass
    try:
        await close_redis()
    except Exception:
        pass
    close_db()
