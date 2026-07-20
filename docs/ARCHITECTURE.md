# Architecture

> A deeper, script-oriented version of this document already exists at
> [`/deploy/ARCHITECTURE.md`](../deploy/ARCHITECTURE.md). This document is the
> canonical reference for new engineers; the two are kept consistent.

## Stack

| Layer | Technology | Notes |
|---|---|---|
| API framework | FastAPI (Python 3.11+) | Async, Pydantic v2, OpenAPI 3.1 at `/docs` |
| Production server | Gunicorn + `uvicorn.workers.UvicornWorker` | Multi-process; `WORKERS` env var |
| Database | MongoDB Atlas | Motor (async) driver, connection pooling |
| Cache / sessions / rate limiting | Redis 7 | Optional — every consumer degrades gracefully to `None` |
| AI providers | Anthropic Claude (primary), OpenAI GPT (fallback) | Routed through an internal Rule → Local → Cloud engine chain |
| Object storage | AWS S3 (or S3-compatible via `S3_ENDPOINT_URL`) | `backend/services/storage_service.py` |
| Transactional email | Resend | `backend/services/email/` |
| Payments | Stripe | Checkout, subscriptions, webhooks |
| Auth | JWT (HS256), bcrypt, TOTP MFA, Google OAuth, ORCID OAuth | Access + refresh cookie pair |
| Frontend | React 18, Create React App via `craco` | SPA, client-side routing |
| Reverse proxy | nginx | TLS termination, rate limiting, static asset caching |
| Container runtime | Docker + Docker Compose | See [DEPLOYMENT.md](DEPLOYMENT.md) |
| Orchestration (optional) | Kubernetes | Manifests in `/deploy/k8s/` |
| Error tracking | Sentry (`SENTRY_DSN`) | Optional but strongly recommended |
| CI | GitHub Actions | `.github/workflows/ci.yml` |

## Request flow

```
Browser
  │  HTTPS
  ▼
nginx  (TLS termination, rate-limit zones, static file serving for the SPA)
  │  HTTP  (proxy_pass to backend:8000)
  ▼
FastAPI app (backend/server.py)
  │
  ├─ CORS (explicit origin allowlist — added LAST in the middleware stack so it
  │        still runs on error responses; see backend/server.py comments)
  ├─ Zero Trust middleware (zt/) — identity/device/risk checks
  ├─ CSRF double-submit cookie check (middleware/__init__.py) — all mutating verbs
  ├─ API Monitor middleware — per-request stats (skipped while Mongo is down)
  ├─ Rate limiting (slowapi, Redis-backed with in-memory fallback)
  │
  ▼
150+ routers (backend/routers/*.py), grouped by domain
  │
  ▼
Services layer (backend/services/*.py) — business logic, credit consumption,
billing, email, AI orchestration
  │
  ├──────────────┬───────────────┬────────────────┐
  ▼              ▼               ▼                ▼
MongoDB Atlas   Redis         AI providers      S3 / Stripe / Resend / ORCID
(via repo/      (optional)    (Anthropic →      (external HTTP APIs)
 DBProxy)                      OpenAI fallback)
```

## Directory layout

```
sinaptiq-main-2/
├── backend/
│   ├── server.py              # FastAPI app: middleware stack, startup/shutdown, router mounting
│   ├── auth_utils.py           # JWT issuance/verification, bcrypt, cookie helpers
│   ├── db.py                   # Motor client, circuit breaker (is_db_down/mark_db_down/mark_db_up)
│   ├── rate_limit.py           # slowapi limiter, Redis→memory fallback
│   ├── plans_catalogue.py      # Single source of truth: plans, credit costs, feature matrix
│   ├── routers/                # ~150 route modules, one per domain (auth, billing, ai, admin_*, ...)
│   ├── services/                # Business logic (credits, billing_history, storage, email/, orcid/, ...)
│   ├── middleware/              # CSRF, security headers, IP blocking
│   ├── worker/                  # Enterprise background job platform (queue, scheduler, DLQ, supervisor)
│   ├── repo/                    # Data access layer: DBProxy, SecurityContext, row-level security, audit
│   ├── obs/                     # Observability: tracing, metrics, cost, security events, audit, alerting
│   ├── zt/                      # Zero Trust: identity, authz, policy, encryption, compliance
│   ├── events/                  # Typed internal event bus + outbox pattern
│   ├── gateway/                 # Enterprise AI Gateway (policy/budget/audit wrapper around AI calls)
│   ├── ara/                     # Autonomous Research Agents + durable mission engine
│   ├── api/                     # Enterprise API platform: versioning, API keys, webhooks, SDK generation
│   └── tests/                   # pytest suite (unit, integration, security, regression, performance)
├── frontend/
│   └── src/                     # React app: pages/, components/, contexts/, lib/api.js (axios client)
├── deploy/
│   ├── Dockerfile, docker-compose.prod.yml, nginx.conf
│   ├── k8s/                     # Kubernetes manifests (Deployment, HPA, PDB, Ingress, Namespace)
│   ├── backup.sh, check_backup_integrity.sh, dr_validate.sh
│   ├── synaptiq.cron, synaptiq-backend.service
│   └── ARCHITECTURE.md, RUNBOOK.md, INCIDENT_RESPONSE.md
├── .github/workflows/ci.yml
└── docs/                        # This manual
```

## Data model summary

See [DATABASE.md](DATABASE.md) for the full collection list. The core entities:

- **`users`** — account, profile, `plan_code`, dual credit balance (`credits_balance` /
  `credits_pack_balance`), OAuth links (Google/ORCID), security fields (lockout, MFA).
- **`subscriptions`** — mirrors Stripe subscription state; `plan_code` and `status` are
  kept in sync with `users.plan_code` by the billing webhook handler.
- **`credit_transactions`** — the sole authoritative ledger for credit grants/consumption.
- **`conversations` / `messages`** — direct messaging, backed by WebSocket fan-out.
- **`worker_jobs`** — background job queue (email sends, scheduled syncs, analytics).

## Real-time (WebSockets)

Two WebSocket endpoints, both cookie-authenticated (`access_token` JWT):

- `GET /api/ws/conversations/{conv_id}` — per-conversation channel (typing, presence, message events)
- `GET /api/ws/user` — per-user channel (unread counters, in-app notifications)

`backend/services/realtime.py` implements a `ConnectionManager` that keeps local
`Set[WebSocket]` per conversation/user (so multiple tabs/devices all receive events) and
publishes through Redis Pub/Sub when available, falling back to local-only delivery when
Redis is down. See [MONITORING.md](MONITORING.md) for what to watch here.

## Background jobs

`backend/worker/` is a self-contained job platform: `MongoQueueBackend` (Mongo-persisted
queue), `WorkerPool` (4 concurrent workers across 5 named queues), and `Scheduler`
(APScheduler + Mongo-persisted cron schedules). A supervisor task
(`start_worker_platform_supervisor()`, wired in `server.py`'s startup handler) keeps this
platform alive across MongoDB/Redis reconnects and backend restarts with exponential
backoff — no manual restart is required if Mongo or Redis blip.

## AI request routing

```
Router endpoint
     │
     ▼
Enterprise AI Gateway (backend/gateway/) — policy + budget + audit wrapper
     │
     ▼
AI Engine (backend/services/ai/)
     ├─ Layer 1: Rule Engine        — deterministic, no LLM call, instant
     ├─ Layer 2: Local AI           — Ollama / vLLM / LM Studio (optional, self-hosted)
     └─ Layer 3: Cloud AI
          ├─ Primary:  Anthropic Claude  (ANTHROPIC_API_KEY)
          ├─ Fallback: OpenAI GPT        (OPENAI_API_KEY)
          └─ Emergency: Mock provider    (dev/test only — never in production)
```

## Billing lifecycle

```
Stripe Checkout Session created (subscription_data.metadata carries user_id/plan_code)
        │
        ▼
checkout.session.completed  ──► logs the transition (subscription_history)
        │
        ▼
customer.subscription.created/updated (status=active/trialing)
        │  resolves plan_code via metadata, falling back to a Stripe price-id →
        │  plan_code lookup against plans_catalogue.PLANS
        ▼
users.plan_code, credits_balance, credits_monthly_allowance, subscription_status
        │  all updated together — this is the single source of truth every other
        │  surface (Pricing, Billing, Admin, AI Credits) reads from
        ▼
invoice.payment_failed  ──► subscription_status=past_due, user notified
        │
        ▼
customer.subscription.deleted / non-payment ──► plan_code reverts to "free"
```

Full webhook event coverage and idempotency mechanism: see [STRIPE_SETUP.md](STRIPE_SETUP.md).

## Scaling

| Component | Strategy |
|---|---|
| API | Gunicorn multi-process (`WORKERS` env var); Kubernetes HPA (3–20 pods, CPU>60%/Mem>70%) if using `/deploy/k8s/` |
| MongoDB | Atlas connection pooling (`MONGO_MAX_POOL`, default 200) |
| Redis | Single node by default; add Sentinel/cluster for HA at higher scale |
| Sessions | Stateless workers — session/refresh-token state lives in Mongo/Redis, not in-process |
| Cache | In-process L1 (small, per-process) + Redis L2 (shared) in the repository layer |
| CDN | Not configured — recommended addition (Cloudflare or similar) in front of nginx for static assets |

## Missing Production Requirements

- **No CDN** in front of the frontend/static assets — nginx serves them directly with
  long cache headers, which is functional but not geographically distributed.
- **No managed load balancer / multi-region failover** documented — the Docker Compose
  path is single-host. The Kubernetes manifests in `/deploy/k8s/` support horizontal
  scaling of the backend but assume a single cluster/region.
- **No formal API gateway rate-limit tier per plan** — rate limiting in `nginx.conf` and
  `rate_limit.py` is IP-based, not account/plan-based.
