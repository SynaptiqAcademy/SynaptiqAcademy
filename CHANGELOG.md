# Synaptiq — Changelog

All notable changes to the Synaptiq platform are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.7.0] — 2026-07-05 · Phase 7: Commercial Readiness

### Added
- **Billing webhook idempotency** — unique index on `stripe_event_id` in `billing_events`; duplicate webhook deliveries from Stripe are safely ignored (prevents double credit grants)
- **Webhook handlers** — `customer.subscription.trial_will_end` (in-app notification 3 days before trial ends), `charge.refunded` (refund recorded in billing history), `charge.dispute.created` (dispute logged to `billing_disputes` for admin review), `invoice.payment_action_required` (3DS/SCA notification)
- **Enterprise plan tier** — unlimited users, unlimited credits, site license, SSO, custom AI, on-premise option, SLA-backed support; contact-sales flow
- **Platform status endpoint** — `GET /api/status` (public, machine-readable), `GET /api/status/history` (incident log), admin incident CRUD at `POST/PATCH /api/status/incidents`
- **Operational cleanup service** — `services/cleanup_service.py`: cleans expired password resets, MFA tokens, stale billing payloads (>90 days), anonymous consent records (>2 years), deleted API keys (>90 days), expired announcements, read notifications (>90 days)
- **Startup cleanup** — cleanup service runs once at application startup (non-fatal)
- **Stripe Tax** — opt-in `automatic_tax` and `tax_id_collection` via `STRIPE_TAX_ENABLED=1` env var
- **Stripe idempotency keys** — deterministic SHA-256 idempotency keys on all checkout sessions (enabled by default; disable with `STRIPE_IDEMPOTENCY=0`)
- **MongoDB startup indexes** — `billing_events.stripe_event_id` (unique sparse), `billing_disputes`, `platform_incidents`, `password_resets` TTL index (30 min)
- **FEATURE_MATRIX expanded** — SSO/SAML, Custom AI, On-premise, SLA uptime columns added; Enterprise column added
- **Cron automation** — cleanup every 6h, platform health check every 5min with webhook alert, daily health log
- **GDPR Article 17 self-service deletion** — `DELETE /api/users/me` (added Phase 6; carried forward)
- `CHANGELOG.md`, `deploy/ARCHITECTURE.md`, `deploy/INCIDENT_RESPONSE.md` documentation added

### Changed
- `plans_catalogue.py`: `PLAN_RANK`, `PLAN_QUOTAS`, `STORAGE_LIMITS_BYTES` extended with `enterprise` tier
- `services/stripe_service.py`: refactored checkout functions to support Tax and idempotency without breaking existing API shape
- `routers/billing.py`: `VALID_PAID_PLANS` includes `enterprise`; feature matrix columns include `enterprise`

### Fixed
- Webhook double-processing: Stripe retries no longer trigger duplicate credit grants or plan changes

---

## [1.6.0] — 2026-07-05 · Phase 6: Final Enterprise Hardening

### Security
- **ReDoS** — `re.escape()` on all user-supplied MongoDB `$regex` patterns (`institutions.py`, `journals.py`)
- **Global 500 handler** — unhandled exceptions return `{"detail": "internal error"}` instead of leaking stack traces
- **Rate limit on password reset** — `POST /auth/reset-password` now rate-limited (matching login rate)
- **IP hash salt isolated** — `IP_HASH_SALT` env var decoupled from `JWT_SECRET` rotation
- **AI jailbreak severity** — fictional-framing patterns elevated from `LOW` → `MEDIUM` (score 10 → 30)
- **GDPR Article 17** — `DELETE /api/users/me` self-service account erasure

### Reliability
- **429 retry** — rate-limit errors removed from `_NO_RETRY_STATUS_CODES`; now retried with exponential backoff
- **Redis SCAN** — `KEYS` replaced with `scan_iter()` in cache invalidation (non-blocking)
- **Context truncation** — `CloudAILayer._truncate_messages()` trims at 720k chars (~180k tokens)
- **Log level configurable** — `LOG_LEVEL` env var; JSON formatter in production
- **Disk space check** — `/api/health` monitors disk (warn >80%, critical >95%)
- **Missing indexes** — `knowledge_chunks`, `knowledge_documents`, `timeline_events` at startup

### Tests
- **2865 passed / 0 failed / 97 skipped** (baseline maintained from Phase 5)

---

## [1.5.0] — 2026-07-05 · Phase 5: Horizontal Scalability

### Added
- **Redis-backed session memory** — `agents/memory.py` L1 in-process + L2 Redis
- **Atlas Vector Search** — default vector backend (`KNOWLEDGE_VECTOR_BACKEND=mongodb`)
- **Distributed scheduler dedup** — MongoDB atomic lock per time-bucket prevents duplicate APScheduler fires
- **Redis L2 cache** — wired into all 93 bounded-context repositories via `get_cache_with_redis()`
- **Configurable pool size** — `MONGO_MAX_POOL` env var (default 200)
- **Kubernetes manifests** — `deploy/k8s/`: 3 replicas, HPA (3–20), PDB, ingress, anti-affinity
- **SCALABILITY_CERTIFICATION.md** — 11-section capacity estimate document

### Tests
- **2865 passed / 0 failed / 97 skipped**

---

## [1.4.0] — 2026-07-05 · Phase 4: Production Hardening

### Added
- **Gunicorn** production server with UvicornWorker
- **38-check production validator** (`services/prod_validator.py`) — blocks startup on missing critical env vars
- **Redis AOF persistence** — append-only file, `appendfsync everysec`
- **Liveness + readiness probes** in Kubernetes and Docker Compose
- **Backup hardening** — `backup.sh`, `check_backup_integrity.sh`, `dr_validate.sh`
- **Resource limits** — 500m/1Gi request, 2000m/4Gi limit per pod

### Tests
- **2854 passed / 0 failed** (Phase 4 baseline)

---

## [1.3.0] — 2026-07-03 · Phase XXXV: Enterprise Infrastructure

### Added
- **Repository Layer** — 19-file `repo/` package; RLS, audit, 2-tier cache, 10 bounded-context repos
- **Event Bus** — 14-file `events/` package; outbox, DLQ, circuit breaker, 36 typed events
- **Worker Platform** — 16-file `worker/` package; 4-worker pool, dedup scheduler
- **Observability** — 13-file `obs/` package; distributed tracing, structured logs, metrics, cost, security
- **API Platform** — 10-file `api/` package; versioning, webhooks, SDK gen, API keys
- **Zero Trust Security** — 16-file `zt/` package; identity, authz, policy, AI security, compliance; 113/113 tests
- **Enterprise AI Gateway** — 11-file `gateway/` package; unified pipeline, audit, cost tracking
- **Durable Mission Engine** — `ara/engine/`; crash-safe execution, checkpoint/recovery
- **KG Consolidation** — `lkg/unified.py` as single truth source

### Migration
- 548 MongoDB handlers proxied through `repo/shim.py`
- 93 routers migrated to `zt_check`/`zt_is_admin`/`zt_is_super_admin`
- All events through `EnterpriseEventBus`

---

## [1.2.0] — 2026-07-02 · Phases XXVI–XXXIV: Academic Platform Expansion

### Added
- Phase XXVI: Public Research Profiles (slug system, follow, showcase)
- Phase XXVII: Reviewer Marketplace (7 collections, matching + conflict engine)
- Phase XXVIII: Institution Analytics Center (65KB dashboard, 26 endpoints)
- Phase XXIX: Verification & Trust Center (8 levels, 1000-point trust score)
- Phase XXX: Proactive AI (evidence-compliant, 8 endpoints)
- Phase XXXI: Multi-Agent Copilot (14 agents, 15 workflows, SSE streaming)
- Phase XXXII: Living Knowledge Graph (GraphCanvas force simulation)
- Phase XXXIII: Digital Research Twin (goals/health/simulation, private-by-default)
- Phase XXXIV: Autonomous Research Agents (20 agents, mission state machine)
- Phase XXXV.1: Enterprise AI Gateway

---

## [1.1.0] — 2026-07-01 · Phases XIV–XXV: Intelligence Platform

### Added
- Phases XIV–XXV: Research Collaboration Intelligence, Institution Intelligence,
  Career Intelligence, Academic Knowledge Graph, Prediction & Forecasting,
  Self-Improving Platform, Academic OS, Design System, Adaptive Dashboard,
  Institution Hub, Grant Collaboration Hub
- Trust & Verification Platform (Phase I)
- Research Timeline (Phase III)
- Academic Integrity Engine (Phase IV)
- Institution Intelligence Platform (Phase V)
- Synaptiq Intelligence Engine (Phase VI)
- Academic Collaboration Network (Phase VII)
- Academic Services Marketplace (Phase VIII)
- Academic Knowledge Graph Platform (Phase IX)
- Sidebar V2 (8-section accordion, search, pinned items)
- UX Phase XXVIII (Command Center ⌘K, Breadcrumbs, Workflow Launcher)
- Adaptive OS (useUserMemory, Today.jsx, intent search)
- IA Redesign (17 → 8 sidebar sections)

---

## [1.0.0] — 2026-06-30 · Initial Commercial Release

### Added
- Core authentication (JWT + refresh tokens, TOTP MFA, Google OAuth, ORCID)
- Research platform: projects, workspaces, manuscripts, publications, citations
- AI engines: 9-agent AIEngine, smart router, RAG, local AI, academic intelligence
- Literature Review 2.0, Research Gap 2.0, Manuscript Intelligence, Statistical Intelligence
- Publishing Intelligence, Autonomous Research Agents, Career Intelligence
- Subscription billing (Free / Researcher / Pro Researcher / Institution)
- Credit system (dual-balance: monthly + pack)
- Stripe Checkout + webhook handler + billing portal
- Admin Control Center (24 admin routers)
- GDPR compliance (Article 17 erasure, Article 20 portability)
- Zero Trust security (MFA, device trust, risk engine, IP allowlist)
- Reputation & Trust System (7 levels, 16 badges)
- Grant Lifecycle Hub
- Institutional Platform (IIS scoring, benchmarking, doctoral school)

---

*For full commit history: `git log --oneline`*
*For security advisories: see `deploy/INCIDENT_RESPONSE.md`*
*For deployment: see `deploy/RUNBOOK.md`*
