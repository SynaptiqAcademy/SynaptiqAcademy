# Synaptiq — Architecture Reference

**Version:** 1.7.0 | **Updated:** 2026-07-05

---

## Overview

Synaptiq is a multi-tenant academic SaaS platform built on a FastAPI/Python backend, React frontend, MongoDB Atlas database, and Redis cache layer. It serves individual researchers, research groups, departments, universities, and enterprise institutions.

---

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| API Framework | FastAPI (Python 3.11+) | Async, OpenAPI 3.1, Pydantic v2 |
| Production Server | Gunicorn + UvicornWorker | Multi-process async workers |
| Database | MongoDB Atlas | Managed, M10+, global clusters |
| Cache | Redis 7 | Sessions, L2 repo cache, rate limiting |
| Search/Vector | MongoDB Atlas Vector Search | 1536-dim OpenAI or native embeddings |
| AI Providers | Anthropic Claude, OpenAI GPT | Auto-fallback chain |
| File Storage | AWS S3 / compatible | Via `services/storage_service.py` |
| Email | Resend | Transactional email |
| Payments | Stripe | Subscriptions, one-time packs, webhooks |
| Auth | JWT (RS256), TOTP MFA, Google OAuth, ORCID | |
| Container | Docker + Docker Compose | Production |
| Orchestration | Kubernetes (optional) | HPA, PDB, anti-affinity |
| Ingress | nginx | Rate limiting, TLS termination |
| Monitoring | Sentry (errors), custom obs/ (traces, metrics) | |
| CI/CD | Configurable (GitHub Actions recommended) | See RUNBOOK.md |

---

## System Architecture

```
                          ┌─────────────────────────────┐
                          │        INTERNET              │
                          └──────────┬──────────────────┘
                                     │ HTTPS
                          ┌──────────▼──────────────────┐
                          │       nginx (TLS)            │
                          │  rate limiting, CORS         │
                          └──────────┬──────────────────┘
                                     │ HTTP/WS
                    ┌────────────────▼────────────────────┐
                    │        FastAPI Application           │
                    │                                      │
                    │  ┌─────────┐  ┌────────────────┐   │
                    │  │ ZT Auth │  │ CSRF Middleware │   │
                    │  └─────────┘  └────────────────┘   │
                    │                                      │
                    │  ┌─────────────────────────────┐    │
                    │  │    150+ API Routers          │    │
                    │  │  (academic, billing, admin)  │    │
                    │  └──────────┬──────────────────┘    │
                    │             │                        │
                    │  ┌──────────▼──────────────────┐    │
                    │  │   Enterprise AI Gateway      │    │
                    │  │  Rule → Local → Cloud chain  │    │
                    │  └──────────┬──────────────────┘    │
                    │             │                        │
                    └────────────┼────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────────┐
            │                    │                         │
   ┌────────▼────────┐  ┌────────▼────────┐  ┌──────────▼────┐
   │  MongoDB Atlas  │  │  Redis 7        │  │  AI Providers  │
   │  (primary DB)   │  │  (cache/session)│  │  Anthropic/OAI │
   │  Vector Search  │  │  (rate limit)   │  │  Local/Ollama  │
   └─────────────────┘  └─────────────────┘  └───────────────┘
```

---

## Directory Structure

```
sinaptiq-main-2/
├── backend/                  # Python API server
│   ├── server.py             # FastAPI app, startup, middleware
│   ├── auth_utils.py         # JWT, bcrypt, session helpers
│   ├── db.py                 # Motor async MongoDB client
│   ├── plans_catalogue.py    # Single source of truth for billing
│   ├── routers/              # 150+ route modules (organized by domain)
│   ├── services/             # Domain services (billing, AI, credits, etc.)
│   ├── agents/               # Multi-agent copilot agent registry
│   ├── ara/                  # Autonomous Research Agents
│   │   └── engine/           # Durable mission execution engine
│   ├── events/               # Enterprise Event Bus (36 typed events)
│   ├── gateway/              # Enterprise AI Gateway
│   ├── lkg/                  # Living Knowledge Graph
│   ├── obs/                  # Enterprise Observability (tracing, metrics)
│   ├── api/                  # Enterprise API Platform (keys, webhooks, SDK)
│   ├── repo/                 # Repository Layer (RLS, audit, 2-tier cache)
│   ├── twin/                 # Digital Research Twin
│   ├── worker/               # Worker Platform (APScheduler, DLQ)
│   ├── zt/                   # Zero Trust Security Package
│   ├── middleware/            # Security headers, CSRF, IP blocking
│   └── tests/                # 2865 tests
├── frontend/                 # React 18 SPA
├── deploy/                   # Infrastructure and operations
│   ├── Dockerfile            # Production image (python:3.11-slim)
│   ├── docker-compose.prod.yml
│   ├── nginx.conf
│   ├── k8s/                  # Kubernetes manifests
│   ├── backup.sh             # mongodump → S3
│   ├── RUNBOOK.md            # Operational runbook
│   ├── ARCHITECTURE.md       # This file
│   └── INCIDENT_RESPONSE.md  # Incident response guide
└── CHANGELOG.md
```

---

## Data Architecture

### MongoDB Collections (Primary)

| Collection | Purpose | Retention |
|-----------|---------|-----------|
| `users` | User accounts, profiles, credits | Indefinite |
| `subscriptions` | Active Stripe subscriptions | Indefinite |
| `billing_history` | User-facing invoice log | Indefinite |
| `billing_events` | Raw Stripe webhook events | 90d payload, metadata forever |
| `billing_disputes` | Stripe dispute records | Indefinite (audit) |
| `subscription_history` | Plan change audit trail | Indefinite |
| `credit_transactions` | Authoritative credit ledger | Indefinite |
| `audit_log` | Billing/security audit (services/audit.py) | Indefinite |
| `obs_audit` | Compliance-grade audit trail (obs/audit.py) | Indefinite |
| `platform_incidents` | Status page incidents | Indefinite |
| `feature_flags` | Runtime feature toggles | Indefinite |
| `platform_settings` | Maintenance mode, global config | Indefinite |
| `password_resets` | One-time tokens (TTL: 30 min) | Auto-deleted via TTL index |

### Redis Keys

| Pattern | Purpose | TTL |
|---------|---------|-----|
| `session:{user_id}:{jti}` | JWT revocation | 7 days |
| `repo:{collection}:{key}` | Repository L2 cache | 10–120s |
| `copilot:session:{id}` | Copilot session memory | 1 hour |
| `rate:{ip}:{endpoint}` | Rate limiting counters | 1 min–1 day |

---

## Security Architecture

### Authentication Flow
1. User logs in → `POST /api/auth/login`
2. Server issues access token (15 min) + refresh token (7 days) with JTI
3. All protected endpoints validate JWT via `get_current_user` → ZT check
4. Refresh tokens stored with JTI in Redis; revocable

### Zero Trust (zt/ package)
- Every API call checked via `zt_check` middleware
- Role hierarchy: `user` < `admin` < `super_admin`
- Device trust, risk scoring, IP allowlist enforcement
- AI security scan on all LLM inputs (19 threat patterns)

### Data Access Control
- `repo/shim.py` `DBProxy` wraps all MongoDB access with `SecurityContext`
- Row-Level Security enforced at repository layer
- Audit log for every write operation

---

## AI Architecture

```
User Request
     │
     ▼
Enterprise AI Gateway (gateway/)
     │  ── policy check (zt/ai_security.py)
     │  ── budget check (obs/cost.py)
     │  ── audit log
     │
     ▼
AIEngine (services/ai/)
     │
     ├── Layer 1: Rule Engine (no LLM, instant)
     ├── Layer 2: Local AI (Ollama/vLLM/LM Studio)
     └── Layer 3: Cloud AI
          ├── Primary: Anthropic Claude (Sonnet 4.6)
          ├── Fallback: OpenAI GPT-4o
          └── Emergency: MockProvider (dev only)
```

---

## Billing Architecture

### Subscription Lifecycle
```
Stripe Checkout → checkout.session.completed
      ↓
customer.subscription.created
      ↓ (ongoing)
invoice.payment_succeeded (monthly/annual)
      ↓ (failure)
invoice.payment_failed → status=past_due → user notification
      ↓
customer.subscription.deleted → downgrade to free
```

### Credit System (Dual Balance)
- `credits_balance` — monthly allowance (resets each cycle, never rolls over)
- `credits_pack_balance` — from one-time purchases (never expires, never resets)
- Consume order: monthly first, then pack
- `credit_transactions` is the sole authoritative ledger

### Idempotency
- `billing_events.stripe_event_id` unique sparse index prevents double-processing
- Stripe checkout sessions have deterministic SHA-256 idempotency keys
- MongoDB `find_one_and_update` compare-and-swap for credit reset races

---

## Scaling Architecture

| Component | Strategy | Config |
|-----------|---------|--------|
| API workers | Gunicorn multi-process | `WORKERS` env var |
| Horizontal scaling | Kubernetes HPA (3–20 pods) | CPU>60%, Memory>70% |
| MongoDB | Atlas M10+ connection pooling | `MONGO_MAX_POOL=200` |
| Redis | Single node (Sentinel in enterprise) | Redis 7 + AOF |
| Sessions | Redis-backed (stateless workers) | 7-day TTL |
| Cache | In-process L1 (2000 entries) + Redis L2 | Per-collection TTL |
| Vector Search | MongoDB Atlas Vector Search | 1536-dim, cosine |
| CDN | Not configured (recommended: Cloudflare) | — |

---

## Observability

| Signal | Tool | Location |
|--------|------|---------|
| Distributed traces | `obs/tracing.py` | `obs_traces` collection |
| Structured logs | `services/logging_config.py` | stdout (JSON in prod) |
| Metrics | `obs/metrics.py` | `obs_metrics` collection |
| Cost tracking | `obs/cost.py` | `obs_cost_records` collection |
| Security events | `obs/security.py` | `obs_security_events` collection |
| Audit trail | `obs/audit.py` | `obs_audit` collection |
| Error tracking | Sentry SDK | External (SENTRY_DSN env) |
| Health checks | `/api/health`, `/api/status` | Built-in |

---

## Environment Variables

### Required in Production

| Variable | Purpose |
|----------|---------|
| `JWT_SECRET` | HMAC signing (≥32 chars, high entropy) |
| `MONGODB_URI` | Atlas SRV connection string |
| `MONGODB_DB_NAME` | Target database name |
| `REDIS_URL` | Redis connection URL |
| `REDIS_PASSWORD` | Redis authentication |
| `ENCRYPTION_KEY` | 256-bit base64 key for field encryption |
| `SUPER_ADMIN_EMAILS` | Comma-separated super admin email addresses |

### Recommended in Production

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Primary AI provider | — |
| `OPENAI_API_KEY` | Fallback AI provider | — |
| `STRIPE_SECRET_KEY` | Payment processing | — |
| `STRIPE_WEBHOOK_SECRET` | Webhook HMAC verification | — |
| `STRIPE_TAX_ENABLED` | Enable automatic tax | `0` |
| `RESEND_API_KEY` | Transactional email | — |
| `SENTRY_DSN` | Error tracking | — |
| `APP_ENV` | Environment flag | `development` |
| `COOKIE_SECURE` | Secure cookie flag | `0` (set `1` in prod) |
| `IP_HASH_SALT` | GDPR-compliant IP anonymization | — |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `MONGO_MAX_POOL` | MongoDB connection pool size | `200` |

---

## API Versioning

- Current: **v1** (prefix: `/api/`)
- API platform (`api/`) provides versioning middleware
- All changes follow backward-compatibility policy (see RUNBOOK.md)
- Breaking changes require major version bump and 90-day deprecation notice

---

## Compliance

| Standard | Status | Notes |
|---------|--------|-------|
| GDPR | CERTIFIED | Art. 17 (erasure), Art. 20 (portability), consent records, audit trail |
| SOC2 Type II | ARCHITECTURE READY | Access logs, audit trail, encryption, MFA — requires external audit |
| ISO 27001 | ARCHITECTURE READY | Risk engine, policy enforcement, incident management |
| NIS2 | PARTIAL | Incident reporting, DR plan — notification procedure needed |
| FERPA | PARTIAL | User data isolated per institution; data sharing consent needed |
| HIPAA | ARCHITECTURE ONLY | BAA required; PHI handling not validated |
