"""
Job Handler Registry — maps job_type strings to async handler callables.

Every handler signature:
    async def handler(job: Job, context: HandlerContext) -> HandlerResult

Context provides:
  - checkpoint: CheckpointEngine  (save/load mid-execution state)
  - db:         MongoDB database
  - publish:    publish a domain event to the event bus

Handlers must:
  - Be idempotent (safe to re-run from last checkpoint)
  - Lazy-import service modules (avoids circular imports)
  - Propagate only transient exceptions (permanent errors raise ValueError/TypeError)
  - Report cost/tokens via HandlerResult when available

Future job types: register with @handler_registry.register("new.job_type").
Zero infrastructure changes required.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from .models import Job

logger = logging.getLogger(__name__)

Handler = Callable[["Job", "HandlerContext"], Awaitable["HandlerResult"]]


@dataclass
class HandlerContext:
    db:         Any
    checkpoint: Any    # CheckpointEngine
    publish:    Any    # async (event: DomainEvent) -> None


@dataclass
class HandlerResult:
    success:    bool         = True
    cost_usd:   float        = 0.0
    tokens:     int          = 0
    provider:   str | None   = None
    model:      str | None   = None
    output:     dict         = field(default_factory=dict)
    error:      str | None   = None


class HandlerRegistry:
    """Maps job_type → async handler function."""

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, job_type: str) -> Callable[[Handler], Handler]:
        def decorator(fn: Handler) -> Handler:
            self._handlers[job_type] = fn
            logger.debug("Handler registered: %s → %s", job_type, fn.__name__)
            return fn
        return decorator

    def get(self, job_type: str) -> Handler | None:
        return self._handlers.get(job_type)

    def registered_types(self) -> list[str]:
        return list(self._handlers.keys())


_registry = HandlerRegistry()


def get_handler_registry() -> HandlerRegistry:
    return _registry


# ── Handler Implementations ───────────────────────────────────────────────────


@_registry.register("ai.execution")
async def handle_ai_execution(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Route AI generation request through the existing AI engine."""
    try:
        from services.ai.engine.core import AIEngine
        engine = AIEngine()
        payload = job.payload
        result  = await engine.generate(
            prompt=payload.get("prompt", ""),
            user_id=job.user_id or "",
            db=ctx.db,
            **{k: v for k, v in payload.items() if k not in ("prompt",)},
        )
        return HandlerResult(
            cost_usd=result.get("cost_usd", 0.0),
            tokens=result.get("tokens_used", 0),
            provider=result.get("provider"),
            model=result.get("model"),
            output=result,
        )
    except ImportError:
        logger.debug("ai.execution: AIEngine not available")
        return HandlerResult()


@_registry.register("mission.step")
async def handle_mission_step(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Execute one step of an autonomous research mission."""
    try:
        from ara.engine.worker import MissionWorker
        worker  = MissionWorker(ctx.db)
        payload = job.payload
        cp      = await ctx.checkpoint.load(job.job_id)
        result  = await worker.execute_step(
            mission_id=payload.get("mission_id", ""),
            step_id=payload.get("step_id", ""),
            checkpoint=cp,
        )
        if result.get("checkpoint"):
            await ctx.checkpoint.save(job.job_id, result["checkpoint"])
        return HandlerResult(output=result)
    except ImportError:
        logger.debug("mission.step: MissionWorker not available")
        return HandlerResult()


@_registry.register("kg.update")
async def handle_kg_update(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Update the Living Knowledge Graph for a publication/entity."""
    try:
        from lkg.ingestion import LKGIngestion
        ingestion = LKGIngestion(ctx.db)
        await ingestion.process(job.payload)
        return HandlerResult()
    except ImportError:
        logger.debug("kg.update: LKGIngestion not available")
        return HandlerResult()


@_registry.register("twin.update")
async def handle_twin_update(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Recompute Digital Research Twin data for a user."""
    try:
        from twin.engine import TwinEngine
        engine = TwinEngine(ctx.db)
        await engine.recompute(
            user_id=job.payload.get("user_id", job.user_id or ""),
            triggers=job.payload.get("triggers", []),
        )
        return HandlerResult()
    except ImportError:
        logger.debug("twin.update: TwinEngine not available")
        return HandlerResult()


@_registry.register("recommendation.generate")
async def handle_recommendation_generate(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Generate recommendations for a user or entity."""
    try:
        from services.recommendations import RecommendationEngine
        engine = RecommendationEngine(ctx.db)
        await engine.generate_all_recommendations(
            entity_id=job.payload.get("entity_id", job.user_id or ""),
            db=ctx.db,
        )
        return HandlerResult()
    except ImportError:
        logger.debug("recommendation.generate: RecommendationEngine not available")
        return HandlerResult()


@_registry.register("grant.discovery")
async def handle_grant_discovery(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Discover new grant opportunities for a researcher."""
    try:
        from services.grant_hub import GrantDiscoveryService
        svc    = GrantDiscoveryService(ctx.db)
        result = await svc.discover_for_user(
            user_id=job.user_id or job.payload.get("user_id", ""),
            filters=job.payload.get("filters", {}),
        )
        return HandlerResult(output=result or {})
    except ImportError:
        logger.debug("grant.discovery: GrantDiscoveryService not available")
        return HandlerResult()


@_registry.register("publication.monitor")
async def handle_publication_monitor(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Monitor tracked publications for updates (citations, status)."""
    try:
        from services.citation_monitoring import CitationMonitorService
        svc = CitationMonitorService(ctx.db)
        await svc.run_monitoring_cycle()
        return HandlerResult()
    except ImportError:
        logger.debug("publication.monitor: CitationMonitorService not available")
        return HandlerResult()


@_registry.register("citation.monitor")
async def handle_citation_monitor(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Check for new citations on monitored papers."""
    try:
        from services.citation_monitoring import CitationMonitorService
        svc = CitationMonitorService(ctx.db)
        await svc.check_citations(doi=job.payload.get("doi", ""))
        return HandlerResult()
    except ImportError:
        logger.debug("citation.monitor: CitationMonitorService not available")
        return HandlerResult()


@_registry.register("orcid.sync")
async def handle_orcid_sync(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Sync ORCID profile for a single user."""
    try:
        from services.orcid import OrcidSyncService
        svc = OrcidSyncService(ctx.db)
        await svc.sync_user(user_id=job.payload.get("user_id", job.user_id or ""))
        return HandlerResult()
    except ImportError:
        logger.debug("orcid.sync: OrcidSyncService not available")
        return HandlerResult()


@_registry.register("orcid.weekly_sync")
async def handle_orcid_weekly_sync(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Weekly batch ORCID sync for all users with connected profiles."""
    try:
        from services.orcid import OrcidSyncService
        svc = OrcidSyncService(ctx.db)
        await svc.sync_all_users()
        return HandlerResult()
    except ImportError:
        logger.debug("orcid.weekly_sync: OrcidSyncService not available")
        return HandlerResult()


@_registry.register("citation.weekly_sync")
async def handle_citation_weekly_sync(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Weekly batch citation sync for all tracked publications."""
    try:
        from services.citation_monitoring import CitationMonitorService
        svc = CitationMonitorService(ctx.db)
        await svc.run_full_sync()
        return HandlerResult()
    except ImportError:
        logger.debug("citation.weekly_sync: CitationMonitorService not available")
        return HandlerResult()


@_registry.register("institution.analytics")
async def handle_institution_analytics(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Refresh institution analytics for a given institution."""
    try:
        from services.institution_analytics import InstitutionAnalyticsService
        svc = InstitutionAnalyticsService(ctx.db)
        await svc.refresh(institution=job.payload.get("institution", ""))
        return HandlerResult()
    except ImportError:
        logger.debug("institution.analytics: InstitutionAnalyticsService not available")
        return HandlerResult()


@_registry.register("teaching.analytics")
async def handle_teaching_analytics(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Refresh teaching analytics for a user or institution."""
    try:
        from services.teaching_analytics import TeachingAnalyticsService
        svc = TeachingAnalyticsService(ctx.db)
        await svc.refresh(user_id=job.user_id or "")
        return HandlerResult()
    except ImportError:
        logger.debug("teaching.analytics: TeachingAnalyticsService not available")
        return HandlerResult()


@_registry.register("marketplace.process")
async def handle_marketplace_process(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Process a marketplace order (escrow, matching, confirmation)."""
    try:
        from services.marketplace import MarketplaceOrderProcessor
        proc = MarketplaceOrderProcessor(ctx.db)
        await proc.process(order_id=job.payload.get("order_id", ""))
        return HandlerResult()
    except ImportError:
        logger.debug("marketplace.process: MarketplaceOrderProcessor not available")
        return HandlerResult()


@_registry.register("notification.deliver")
async def handle_notification_deliver(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Deliver a notification to a user (email, in-app)."""
    try:
        from services.notifications import NotificationDeliveryService
        svc = NotificationDeliveryService(ctx.db)
        await svc.deliver(notification=job.payload)
        return HandlerResult()
    except ImportError:
        logger.debug("notification.deliver: NotificationDeliveryService not available")
        return HandlerResult()


@_registry.register("data.import")
async def handle_data_import(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Import external data (publications, profiles, grants)."""
    try:
        cp     = await ctx.checkpoint.load(job.job_id)
        offset = cp.get("offset", 0)
        from services.data_import import DataImportService
        svc    = DataImportService(ctx.db)
        result = await svc.run(
            source=job.payload.get("source", ""),
            params=job.payload.get("params", {}),
            offset=offset,
        )
        await ctx.checkpoint.save(job.job_id, {"offset": result.get("next_offset", 0)})
        return HandlerResult(output=result)
    except ImportError:
        logger.debug("data.import: DataImportService not available")
        return HandlerResult()


@_registry.register("graph.rebuild")
async def handle_graph_rebuild(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Full Knowledge Graph rebuild (expensive — singleton job type)."""
    try:
        from lkg.rebuild import LKGRebuildService
        svc = LKGRebuildService(ctx.db)
        await svc.rebuild_full()
        return HandlerResult()
    except ImportError:
        logger.debug("graph.rebuild: LKGRebuildService not available")
        return HandlerResult()


@_registry.register("report.generate")
async def handle_report_generate(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Generate a research report (PDF, DOCX, JSON)."""
    try:
        from services.reporting import ReportGenerationService
        svc = ReportGenerationService(ctx.db)
        result = await svc.generate(
            report_type=job.payload.get("report_type", ""),
            params=job.payload.get("params", {}),
            user_id=job.user_id or "",
        )
        return HandlerResult(output=result)
    except ImportError:
        logger.debug("report.generate: ReportGenerationService not available")
        return HandlerResult()


@_registry.register("integrity.analysis")
async def handle_integrity_analysis(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Run academic integrity analysis for a user or document."""
    try:
        from services.integrity.engine import run_integrity_analysis
        await run_integrity_analysis(
            uid=job.payload.get("user_id", job.user_id or ""),
            db=ctx.db,
        )
        return HandlerResult()
    except ImportError:
        logger.debug("integrity.analysis: run_integrity_analysis not available")
        return HandlerResult()


@_registry.register("memory.enrich")
async def handle_memory_enrich(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Enrich SIE memory from platform activity."""
    try:
        from services.sie.memory_engine import enrich_memory_from_platform
        await enrich_memory_from_platform(
            user_id=job.payload.get("user_id", job.user_id or ""),
            db=ctx.db,
        )
        return HandlerResult()
    except ImportError:
        logger.debug("memory.enrich: enrich_memory_from_platform not available")
        return HandlerResult()


@_registry.register("mission.run")
async def handle_mission_run(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Run a full autonomous research mission from approve-plan."""
    try:
        from ara import orchestrator
        user    = job.payload.get("user", {})
        if not user and job.user_id:
            doc = await ctx.db.users.find_one({"_id": __import__("bson").ObjectId(job.user_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                user = doc
        await orchestrator.run_mission(
            ctx.db,
            job.payload.get("mission_id", ""),
            job.payload.get("user_id", job.user_id or ""),
            user,
            job.payload.get("autonomy_level", 1),
        )
        return HandlerResult()
    except ImportError:
        logger.debug("mission.run: ara.orchestrator not available")
        return HandlerResult()


@_registry.register("mission.resume")
async def handle_mission_resume(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Resume mission execution after human approval."""
    try:
        from ara import orchestrator
        user = job.payload.get("user", {})
        if not user and job.user_id:
            doc = await ctx.db.users.find_one({"_id": __import__("bson").ObjectId(job.user_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                user = doc
        await orchestrator.resume_after_approval(
            ctx.db,
            job.payload.get("mission_id", ""),
            job.payload.get("user_id", job.user_id or ""),
            user,
            job.payload.get("autonomy_level", 1),
        )
        return HandlerResult()
    except ImportError:
        logger.debug("mission.resume: ara.orchestrator not available")
        return HandlerResult()


@_registry.register("mission.monitors")
async def handle_mission_monitors(job: Job, ctx: HandlerContext) -> HandlerResult:
    """Run all background research monitors for a user."""
    try:
        from ara import background_agents, mission_store
        user = job.payload.get("user", {})
        if not user and job.user_id:
            doc = await ctx.db.users.find_one({"_id": __import__("bson").ObjectId(job.user_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                user = doc
        user_id = job.payload.get("user_id", job.user_id or "")
        alerts  = await background_agents.run_all_monitors(ctx.db, user_id, user)
        for alert in alerts:
            await mission_store.append_log(
                ctx.db, "background", alert["monitor"], "monitor_alert",
                alert["title"], alert,
            )
        return HandlerResult(output={"alerts": len(alerts)})
    except ImportError:
        logger.debug("mission.monitors: ara not available")
        return HandlerResult()


@_registry.register("email.bulk_campaign")
async def handle_email_bulk_campaign(job: Job, ctx: HandlerContext) -> HandlerResult:
    """
    Send a bulk email campaign. All args are serialized in the payload.

    Registered here; actual _run_bulk_send is imported lazily from
    routers.admin_email_center to avoid circular imports at module level.
    """
    try:
        from routers.admin_email_center import _run_bulk_send  # type: ignore[attr-defined]
        p = job.payload
        await _run_bulk_send(
            campaign_id=p.get("campaign_id", ""),
            query=p.get("query", {}),
            base_subject=p.get("base_subject", ""),
            base_html=p.get("base_html"),
            tmpl=p.get("tmpl"),
            body_variables=p.get("body_variables", {}),
        )
        return HandlerResult()
    except ImportError:
        logger.debug("email.bulk_campaign: _run_bulk_send not available")
        return HandlerResult()


@_registry.register("email.send")
async def handle_email_send(job: Job, ctx: HandlerContext) -> HandlerResult:
    """
    Generic transactional-email dispatch — every trigger site (registration,
    invitations, future billing/security emails) enqueues one of these instead
    of awaiting Resend inline, so a slow or failing send never blocks the
    HTTP response. `payload["kind"]` selects the typed sender in
    services/email_service.py; `payload["args"]` are its kwargs.

    Add a new email kind by adding one entry to KIND_TO_SENDER — no other
    infrastructure change needed.
    """
    from services import email_service as svc

    KIND_TO_SENDER = {
        "welcome": svc.send_welcome_email,
        "verification": svc.send_email_verification,
        "getting_started": svc.send_getting_started_email,
        "password_reset": svc.send_password_reset,
        "workspace_invitation": svc.send_workspace_invitation,
        "review_request": svc.send_review_request,
        "collaboration_invitation": svc.send_collaboration_invitation,
    }
    kind = job.payload.get("kind", "")
    sender = KIND_TO_SENDER.get(kind)
    if not sender:
        logger.error("email.send: unknown kind=%r — dropping job %s", kind, job.job_id)
        return HandlerResult(success=False, error=f"unknown email kind: {kind}")

    args = job.payload.get("args", {})
    result = await sender(**args)
    if not result.get("ok"):
        # Transient (network/provider) failure — let the worker's retry policy
        # re-attempt. A permanent "user not found" is not retried (max_attempts
        # on the job already bounds this either way).
        return HandlerResult(success=False, error=result.get("error") or "send failed",
                             output={"mode": result.get("mode")})
    return HandlerResult(output={"mode": result.get("mode"), "id": result.get("id")})


@_registry.register("email.getting_started_check")
async def handle_getting_started_check(job: Job, ctx: HandlerContext) -> HandlerResult:
    """
    Runs once, 24h after registration (scheduled by routers/auth.py). Sends
    the Getting Started email ONLY if the user is still not "active" — never
    to a user who has already verified, completed their passport, and joined
    a collaboration/workspace. All conditions are re-checked here at run time
    (not at schedule time), against real data, per the platform's no-fabricated-
    stats policy.
    """
    from bson import ObjectId
    from services.profile_completion import compute_profile_completion
    from services import email_service as svc

    user_id = job.payload.get("user_id", "")
    if not user_id:
        return HandlerResult(success=False, error="missing user_id")

    user = await ctx.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        logger.info("email.getting_started_check: user %s no longer exists — skipping", user_id)
        return HandlerResult(output={"skipped": "user_not_found"})

    completion = await compute_profile_completion(ctx.db, user_id)
    pct = completion["percentage"] if completion else 0

    has_collaboration = await ctx.db.collaborations.count_documents(
        {"$or": [{"creator_id": user_id}, {"members": user_id}]}, limit=1
    ) > 0
    has_workspace = await ctx.db.workspaces.count_documents(
        {"$or": [{"owner_id": user_id}, {"members": user_id}]}, limit=1
    ) > 0

    email_verified = bool(user.get("email_verified"))
    orcid = user.get("orcid") or {}
    orcid_connected = bool(orcid.get("orcid_id")) if isinstance(orcid, dict) else bool(orcid)

    is_active = (
        email_verified and pct >= 70 and has_collaboration and has_workspace
    )
    if is_active:
        logger.info("email.getting_started_check: user %s already active — skipping", user_id)
        return HandlerResult(output={"skipped": "already_active", "percentage": pct})

    remaining_tasks = [
        ("Verify Email", email_verified),
        ("Connect ORCID", orcid_connected),
        ("Add Research Interests", bool(user.get("research_areas") or user.get("research_interests"))),
        ("Upload Profile Photo", bool(user.get("avatar_url"))),
        ("Create First Workspace", has_workspace),
    ]

    result = await svc.send_getting_started_email(
        user_id=user_id, completion_pct=pct, remaining_tasks=remaining_tasks,
    )
    if not result.get("ok"):
        return HandlerResult(success=False, error=result.get("error") or "send failed")
    return HandlerResult(output={"mode": result.get("mode"), "percentage": pct})
