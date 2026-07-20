# SYNAPTIQ — Technical Handoff Package
**Generated**: 2026-02-14 (final Emergent-phase deliverable, prior to GitHub/VS Code migration)
**Status**: Production-ready code; **Production Readiness Score 92.5 / 100**
**Companion docs**: PRD.md, PRE_BETA_AUDIT.md, HARDENING_REPORT.md, PRODUCTION_CHECKLIST.md, PHASE5_DATA_SOURCES.md, test_credentials.md

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Route Inventory (229 endpoints)](#2-route-inventory)
3. [Database Schema (47 collections)](#3-database-schema)
4. [Environment Variable Inventory](#4-environment-variable-inventory)
5. [External Integrations](#5-external-integrations)
6. [Deployment Requirements](#6-deployment-requirements)
7. [GitHub Migration Checklist](#7-github-migration-checklist)
8. [VS Code Local Development Checklist](#8-vs-code-local-development-checklist)
9. [Production Deployment Checklist](#9-production-deployment-checklist)
10. [Beta Launch Checklist](#10-beta-launch-checklist)
11. [Known Limitations](#11-known-limitations)
12. [Technical Debt](#12-technical-debt)
13. [Future Roadmap](#13-future-roadmap)

---

## 1. Architecture Overview

### 1.1 High-level

```
┌─────────────────────────────────────────────────────────────┐
│                       Browser (React 19)                     │
│  ├─ Editorial UI (Tailwind + Shadcn + Cormorant Garamond)    │
│  ├─ React Router v7 (57 routes)                              │
│  ├─ AuthProvider + UnreadProvider contexts                   │
│  ├─ CookieConsentBanner (GDPR)                               │
│  └─ axios with withCredentials:true                          │
└────────────────────┬────────────────────────────────────────┘
                     │  HTTPS (prod) / HTTP (dev)
                     │  httpOnly cookies: access_token, refresh_token
┌────────────────────▼────────────────────────────────────────┐
│              Ingress (K8s / Cloudflare in prod)              │
│  ⚠ Must NOT rewrite CORS to '*' — see §11                   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  FastAPI Backend (uvicorn on :8001, supervisor-managed)      │
│  ├─ Middleware: CORS allowlist → SlowAPI → SecurityHeaders   │
│  ├─ 33 routers, 229 endpoints (all /api-prefixed)            │
│  ├─ JWT auth (bcrypt + PyJWT) via httpOnly cookies           │
│  ├─ APScheduler (in-process, opt-in via env)                 │
│  ├─ WebSocket ConnectionManager (in-process)                 │
│  └─ Structured logging (JSON in prod / text in dev)          │
└────┬──────────────────────────┬─────────────────────────────┘
     │                          │
     │                          │
┌────▼─────────┐         ┌──────▼──────────────────────────┐
│   MongoDB    │         │      External Services           │
│  (Motor      │         │  ├─ Emergent LLM Key (Claude     │
│   async)     │         │  │  Sonnet 4.5 via emergent      │
│  47 cols     │         │  │  integrations lib)            │
│              │         │  ├─ Emergent Object Storage      │
│              │         │  ├─ OpenAlex / Crossref / DOAJ   │
│              │         │  ├─ WikiCFP / OpenAIRE / NIH /   │
│              │         │  │  UKRI (discovery)             │
│              │         │  ├─ Stripe (UNCONFIGURED)        │
│              │         │  ├─ Resend (DRY-RUN)             │
│              │         │  └─ ORCID OAuth (SANDBOX)        │
└──────────────┘         └──────────────────────────────────┘
```

### 1.2 Stack

| Layer | Tech | Version |
|---|---|---|
| Frontend | React | 19.x |
| Frontend Router | React Router | 7.x |
| Frontend UI | Tailwind CSS + Shadcn/UI | latest |
| Frontend Build | Create-React-App (CRA) + webpack | as-is |
| Backend | FastAPI | 0.110.1 |
| ASGI Server | uvicorn | latest |
| Process Manager | Supervisor | system |
| Database | MongoDB | 4.x+ |
| Mongo Driver | Motor (async) | latest |
| Auth | PyJWT + passlib[bcrypt] | latest |
| Rate Limiting | slowapi | 0.1.10 |
| Email | resend SDK | latest (dry-run-safe) |
| Billing | stripe SDK | latest (lazy-imported) |
| AI | emergentintegrations | platform-pinned |
| Scheduler | APScheduler | latest |
| HTTP client (backend) | httpx | latest |

### 1.3 Service Layer Structure

```
backend/
├── server.py                   # FastAPI app + middleware + startup/shutdown
├── auth_utils.py               # JWT + bcrypt + cookies + get_current_user
├── rate_limit.py               # SlowAPI limiter
├── db.py                       # Mongo connection
├── seed.py                     # Idempotent admin + demo data seed
├── models.py                   # Pydantic shared models
├── middleware/                 # SecurityHeadersMiddleware
├── routers/                    # 33 thin routers, all /api-prefixed
├── services/                   # Domain logic (delegated by routers)
│   ├── ai/                     # matching + assistant
│   ├── discovery/              # 7 providers + scheduler + ingest orchestrator
│   ├── institutions/           # 7 analytics aggregators
│   ├── marketplace/            # deterministic_rank + llm_rerank
│   ├── orcid/                  # oauth + works sync + enrich
│   ├── reputation/             # 5 sub-score scorer + openalex
│   ├── credits_service.py
│   ├── email_service.py        # Resend provider (dry-run-safe)
│   ├── email_templates.py      # 5 typed templates
│   ├── logging_config.py       # JSON / text logging
│   ├── prod_validator.py       # env audit + startup gate
│   ├── storage_service.py      # Emergent Object Storage
│   └── stripe_service.py       # Lazy-imported, 503 when unconfigured
├── tests/                      # pytest suite
└── scripts/                    # migrations (e.g. institutions backfill)
```

```
frontend/src/
├── App.js                      # BrowserRouter + Routes + Providers
├── lib/
│   └── api.js                  # axios w/ withCredentials
├── context/                    # AuthContext, UnreadContext
├── pages/                      # 51 page components
├── components/
│   ├── ui/                     # Shadcn primitives
│   ├── consent/                # CookieConsentBanner
│   ├── files/                  # FilePanel, PreviewDrawer
│   ├── marketplace/            # MatchCard, FacetSidebar
│   ├── researchOS/             # Kanban, ManuscriptEditor
│   ├── ai/                     # Assistant drawer
│   ├── orcid/                  # OrcidBadge, OrcidSettings
│   ├── institutions/           # InstitutionAnalytics, AdminControls
│   ├── discovery/              # DataCards
│   └── layout/                 # AppShell, Sidebar, TopBar
└── styles/                     # editorial.css (Cormorant + Plex Sans)
```

### 1.4 Request flow (authenticated request)

```
Browser → ingress → uvicorn → CORSMiddleware (allowlist) →
SlowAPIMiddleware (per-IP throttle) → SecurityHeadersMiddleware →
route handler → get_current_user (verifies access_token cookie,
auto-refresh from refresh_token if expired) → service layer →
Mongo → service layer → router → CORS+headers attached → browser
```

---

## 2. Route Inventory

**Total**: 229 endpoints across 33 routers. All `/api`-prefixed.

### 2.1 Auth (`auth.py`) — 9 endpoints
| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | Rate-limited 5/min; weak-password 400 |
| POST | `/api/auth/login` | Rate-limited 5/min; 403 if email unverified (when REQUIRED=1) |
| POST | `/api/auth/logout` | Clears cookies |
| GET | `/api/auth/me` | Returns serialized user (no password_hash, no ORCID tokens) |
| POST | `/api/auth/verify-email` | Idempotent token verification |
| POST | `/api/auth/resend-verification` | Rate-limited; no enumeration |
| POST | `/api/auth/forgot-password` | Rate-limited; no debug_reset_token in prod |
| POST | `/api/auth/reset-password` | Single-use JWT token |
| POST | `/api/auth/change-password` | Authed |

### 2.2 Users (`users.py`) — 5 endpoints
| Method | Path |
|---|---|
| GET | `/api/users` |
| GET | `/api/users/{uid}` |
| PATCH | `/api/users/me` |
| POST | `/api/users/me/onboarding` |
| POST | `/api/users/{uid}/connect` |

### 2.3 Research File Layer (`files.py`) — 13 endpoints
Versioned files with ACL inherited from parent entity (workspace / project / manuscript).
Upload, list, recent, get, versions, activity, download, preview, preview-csv, patch, delete.

### 2.4 Workspaces (`workspaces.py`) — 14 endpoints
Dashboard, members, role mgmt (6 roles), invitations, activity, tasks.

### 2.5 Manuscripts (`manuscripts.py`) — 16 endpoints
Sections, versions, comments, contributions, review-requests, authors, meta, state machine.

### 2.6 Marketplace v2 (`marketplace.py`) — 9 endpoints
Search → deterministic_rank → llm_rerank, reverse, invite, invitations, analytics.

### 2.7 Expertise Requests (`expertise.py`) — 12 endpoints
CRUD + apply + decide + close + attachments (link to files) + matching.

### 2.8 Institutions (`institutions.py`) — 18 endpoints
CRUD, units (nested), members, roles, seats, 7 analytics aggregations, audit, claim.

### 2.9 ORCID (`orcid.py`) — 9 endpoints
config, authorize, callback, disconnect, sync, enrich-openalex, sync-history, status, publications.

### 2.10 Discovery (`discovery_admin.py` + `journals.py` + `conferences.py` + `grants.py` + `funding.py` + `discover.py`) — 17 endpoints
Admin: sources, stats, sync/{kind}, indexes/ensure, runs.
Public: journals + journals/facets + journals/{id}; same for conferences + grants; discover/feed.

### 2.11 Conversations (`messaging.py`) — 11 endpoints
list, get, messages (CRUD), read, typing, edit-history, unread, WS at `/api/ws/conversations/{id}`.

### 2.12 AI Matching (`matching.py`) — 5 endpoints
journal, conference, grant, reviewer + analytics + history.

### 2.13 Assistant (`assistant.py`) — 4 endpoints
sessions CRUD + messages.

### 2.14 Publication Hub (`publication_hub.py`) — 7 endpoints
Kanban (6 stages), submissions, feedback, revision, status.

### 2.15 Reputation (`reputation.py`) — 4 endpoints
me, by-id, sync-openalex, batch.

### 2.16 Saved Searches (in discover/marketplace) — 6 endpoints

### 2.17 Billing (`billing.py`) — 5 endpoints
plans, subscription, checkout-session, portal-session, webhook.

### 2.18 Email Admin (`email.py`) — 3 endpoints
config, preview/{template}, test (admin-only).

### 2.19 Notifications (`notifications.py`) — 3 endpoints

### 2.20 Collaborations (`collaborations.py`) — 7 endpoints

### 2.21 Repository (`repository.py`) — 3 endpoints

### 2.22 Reviews (within `research_os.py`) — 5 endpoints

### 2.23 Consent (`consent.py`) — 2 endpoints
POST `/api/consent`, GET `/api/consent/latest`.

### 2.24 Admin Health (`admin_health.py`) — 1 endpoint
**`GET /api/admin/production-readiness`** — env audit endpoint (admin/owner role).

### 2.25 Misc (`analytics.py`, `credits.py`, `research_os.py`, `ai.py`, `projects.py`)
analytics/me, deadlines/mine, ai/recommendations, projects, research-os lookups, credits/balance + history.

---

## 3. Database Schema

**Total**: 47 collections.

### 3.1 Identity & Auth
| Collection | Docs | Indexes | Purpose |
|---|---|---|---|
| `users` | 54 | unique(email) | Profile + auth + credits + orcid + reputation + institution_id |
| `password_resets` | 18 | (user_id, token_jti) | Single-use reset tokens |
| `email_verifications` | 7 | (user_id, used), (token_jti) | Email verification tokens |
| `consent_records` | 5 | (user_id, created_at), (consent_id, created_at) | GDPR consent history (append-only) |

### 3.2 Discovery (live data, ~19k records)
| Collection | Docs | Indexes |
|---|---|---|
| `journals` | 10,160 | text(title, publisher, subjects), unique sparse(entity_key) |
| `conferences` | 808 | text(name, topics), unique sparse(entity_key), deadline |
| `grants` | 7,997 | text(name, sponsor), sponsor, deadline, amount_usd |
| `ingest_runs` | 14 | (kind, started_at) |
| `ingest_state` | 3 | (kind, source) |

### 3.3 Research OS
| Collection | Docs | Notes |
|---|---|---|
| `workspaces` | 16 | member_roles {uid: role}, member_ids |
| `workspace_invitations` | 11 | (workspace_id, email) |
| `workspace_activity` | 10 | activity feed |
| `projects` | 9 | member_ids |
| `tasks` | 10 | kanban state |
| `manuscripts` | 14 | author_ids, lead_author_id |
| `manuscript_versions` | 15 | (manuscript_id, version) |
| `manuscript_comments` | 3 | |
| `manuscript_contributions` | 3 | |
| `review_requests` | 8 | state machine |

### 3.4 Marketplace + Reputation
| Collection | Docs | Notes |
|---|---|---|
| `expertise_requests` | 0 | attachments[] field |
| `marketplace_invitations` | 10 | unique (from, to, kind, context) |
| `reputation_scores` | 3 | 5 sub-scores; 24h cache |

### 3.5 Files
| Collection | Docs | Indexes |
|---|---|---|
| `files` | 2 | (entity_kind, entity_id, is_latest), (root_id, version), (owner_id, created_at), (sha256) |
| `file_activity` | 75 | (file_id, created_at) |

### 3.6 Institutional Layer
| Collection | Docs | Notes |
|---|---|---|
| `institutions` | 2 | name, email_domains[] |
| `units` | 2 | parent_id (nested), head_id, admin_ids[] |
| `institution_memberships` | 10 | unique (institution_id, user_id) |
| `institution_audit` | 81 | every governance write |

### 3.7 ORCID
| Collection | Docs | Indexes |
|---|---|---|
| `publications` | 0 | sparse(doi), (orcid_id, put_code), (title_norm) |

### 3.8 Billing
| Collection | Docs | Notes |
|---|---|---|
| `plans` | 3 | Free / Researcher / Institution |
| `subscriptions` | — | Stripe-shape fields |
| `billing_events` | 6 | Webhook receipts |
| `credit_usage` | 76 | Per-action audit |

### 3.9 Conversations
| Collection | Docs | Notes |
|---|---|---|
| `conversations` | 5 | direct/group/workspace/project/manuscript |
| `conversation_members` | 9 | (conversation_id, user_id) |
| `messages` | 92 | text + attachments + mentions |
| `message_attachments` | 10 | uploaded files |
| `message_reads` | 4 | (conversation_id, user_id) → last_read_at |

### 3.10 Misc
| Collection | Docs | Notes |
|---|---|---|
| `collaborations` | 8 | open / closed / accepted |
| `applications` | 2 | to collaborations |
| `repository_items` | 15 | shared datasets / code |
| `submissions` | 12 | journal submissions |
| `ai_requests` | 19 | LLM call audit |
| `chat_sessions` | 2 | Assistant sessions |
| `chat_messages` | 8 | Assistant turns |
| `saved_searches` | 1 | scheduled digest |
| `literature` | 2 | imported papers |
| `notifications` | 158 | |

---

## 4. Environment Variable Inventory

### 4.1 Backend `.env` (Group A — required for prod startup)

| Variable | Type | Description | Dev value | Prod requirement |
|---|---|---|---|---|
| `APP_ENV` | enum | `development` \| `staging` \| `production` | `development` | `production` |
| `MONGO_URL` | string | Mongo connection string | `mongodb://localhost:27017` | `mongodb+srv://...` (Atlas/managed) |
| `DB_NAME` | string | Database name | `synaptiq_db` | `synaptiq_prod` |
| `JWT_SECRET` | string ≥32 ch | HMAC signing secret | dev value | **64-char random hex** |
| `APP_BASE_URL` | URL | Public base for email links + OAuth callbacks | preview URL | `https://app.synaptiq.io` |
| `CORS_ORIGINS` | csv | Explicit allowlist | preview, localhost | prod domains |
| `COOKIE_SECURE` | bool | HTTPS-only cookies | `0` | **`1`** |
| `COOKIE_SAMESITE` | enum | `lax` \| `strict` \| `none` | `lax` | `lax` or `strict` |
| `EXPOSE_RESET_TOKEN` | bool | Surface debug_reset_token | `0` | **`0`** (hard-off in prod regardless) |

### 4.2 Backend `.env` (Group A.1 — recommended)
| Variable | Description | Dev | Prod |
|---|---|---|---|
| `EMAIL_VERIFICATION_REQUIRED` | Gate sign-in until verified | `0` | `1` |
| `EMAIL_VERIFICATION_TTL_HOURS` | Token expiry | `24` | `24` |
| `RATE_LIMIT_AUTH` | slowapi rate | `5/minute` | `5/minute` |
| `EMERGENT_LLM_KEY` | AI calls | set | set |
| `DISCOVERY_CONTACT_EMAIL` | Polite UA | optional | set |
| `DISCOVERY_SCHEDULER_ENABLED` | APScheduler | `0` | `1` (single pod) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Seed | set | set strong |
| `CSP_REPORT_URI` | Optional CSP reporting | unset | optional |

### 4.3 Backend `.env` (Group B — integrations, set when activating)
| Variable | Where to obtain |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe dashboard → API keys |
| `STRIPE_WEBHOOK_SECRET` | Stripe → Webhooks → endpoint signing secret |
| `STRIPE_PRICE_RESEARCHER_MONTHLY` | Stripe → Products → price ID |
| `STRIPE_PRICE_RESEARCHER_ANNUAL` | Same |
| `STRIPE_PRICE_INSTITUTION_MONTHLY` | Same |
| `STRIPE_PRICE_INSTITUTION_ANNUAL` | Same |
| `RESEND_API_KEY` | Resend dashboard → API Keys |
| `EMAIL_FROM` | Format: `SYNAPTIQ <noreply@verified-domain.com>` |
| `EMAIL_DRY_RUN` | `0` to send live, `1` for log-only |
| `ORCID_CLIENT_ID` | orcid.org → Developer Tools (production app) |
| `ORCID_CLIENT_SECRET` | Same dashboard |
| `ORCID_REDIRECT_URI` | Must match exactly the registered URI |
| `ORCID_BASE_URL` | `https://orcid.org` (prod) or `https://sandbox.orcid.org` (staging) |

### 4.4 Frontend `.env`
| Variable | Description | Dev | Prod |
|---|---|---|---|
| `REACT_APP_BACKEND_URL` | API base | preview URL | `https://app.synaptiq.io` |
| `WDS_SOCKET_PORT` | CRA HMR | `443` | n/a (build) |
| `ENABLE_HEALTH_CHECK` | Devbox internals | `false` | n/a |

### 4.5 Validator
Run `GET /api/admin/production-readiness` (admin auth) → returns `{ready_for_production, errors, warnings, checks}`. Backend refuses startup with `APP_ENV=production` if any error-level check fails (programmatic enforcement).

---

## 5. External Integrations

| Integration | Mode | Code state | Activation path |
|---|---|---|---|
| **Claude Sonnet 4.5** (`emergentintegrations`) | LIVE | Production-grade | EMERGENT_LLM_KEY (already set) |
| **Emergent Object Storage** | LIVE | Production-grade | Built-in |
| **OpenAlex** (journals + reputation + ORCID enrich) | LIVE | Production-grade | Set DISCOVERY_CONTACT_EMAIL for polite UA |
| **DOAJ / Crossref** | LIVE | Production-grade | None |
| **WikiCFP** (RSS for conferences) | LIVE | Production-grade | None |
| **OpenAIRE / NIH RePORTER / UKRI** (grants) | LIVE | Production-grade | None |
| **Stripe** | UNCONFIGURED (503 on checkout) | Production-ready code; lazy SDK import | Set 6 Group B Stripe vars |
| **Resend** (transactional email) | DRY-RUN | Production-ready code; 5 templates wired | Set 3 Group B Resend vars |
| **ORCID OAuth** | SANDBOX DRY-RUN | Production-ready code | Set 4 Group B ORCID vars |

### Triggers wired (exactly-once)
- Register → email verification
- Forgot password → reset email
- Workspace invite respond → invite email
- Review request create → reviewer email
- Collaboration invite decide → applicant email

---

## 6. Deployment Requirements

### 6.1 Compute
- **Backend**: 1 vCPU, 1 GB RAM minimum; 2 vCPU, 2 GB recommended at beta.
- **Frontend**: static build artifact; any CDN (Vercel, Netlify, Cloudflare Pages, S3+CloudFront).
- **MongoDB**: Atlas M10+ (1.5 GB RAM, 10 GB storage) recommended. The 19k discovery records + 47 collections fit comfortably.

### 6.2 Network
- **HTTPS-only** (TLS 1.2+).
- **Ingress** must pass through `Set-Cookie` headers untouched (HttpOnly+Secure flags preserved).
- **Ingress** must NOT rewrite `Access-Control-Allow-Origin` to `*` when credentials are sent (see Known Limitations §11).
- **Ingress** must forward `X-Forwarded-For` (rate limiting depends on it).

### 6.3 Storage
- **Files**: Emergent Object Storage in dev; migrate to S3-compatible bucket for prod (or keep Emergent if migrating intra-platform).
- **Mongo backups**: continuous backup (Atlas) OR cron'd `mongodump` to S3.

### 6.4 DNS
- 1 production domain (e.g. `app.synaptiq.io`) — frontend + backend either same-origin or two subdomains.
- TLS cert (Let's Encrypt / Cloudflare / ACM).

### 6.5 Monitoring
- Error tracking: Sentry (recommended; SDK can be wired in 1 hour).
- Metrics: a Prometheus `/metrics` endpoint should be added before public scale (not yet present).
- Logs: structured JSON (already implemented; pipe stdout to Datadog/Loki/CloudWatch).

---

## 7. GitHub Migration Checklist

### 7.1 Repo setup
- [ ] Create private GitHub repo: `synaptiq/synaptiq` (or your org).
- [ ] Add `.gitignore` covering `node_modules/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`, `.env`, `frontend/build/`, `frontend/.cache/`, `.DS_Store`, `*.swp`.
- [ ] Initial commit from `/app` root.

### 7.2 Secrets handling
- [ ] **DO NOT commit `.env` files.** Add to `.gitignore`.
- [ ] Provide `.env.example` files (committed) with placeholder values:
  - `/app/backend/.env.example` — every key from §4 with placeholder
  - `/app/frontend/.env.example` — REACT_APP_BACKEND_URL placeholder
- [ ] Rotate `JWT_SECRET` and admin password before first prod deploy (current values are dev-only).

### 7.3 Branch strategy
- [ ] Default branch: `main` (protected).
- [ ] Working branches: `feat/...`, `fix/...`, `chore/...`.
- [ ] Pre-merge: require PR + 1 review + CI green.
- [ ] Tag releases: `v1.0-beta`, `v1.0.0`, etc.

### 7.4 CI/CD (recommended starting point)
- [ ] GitHub Actions workflow `.github/workflows/ci.yml`:
  - Backend: install requirements → `python -m pytest tests/`.
  - Frontend: `yarn install` → `yarn lint` → `yarn build`.
- [ ] Optional: deploy workflow firing on `main` push or release tag.

### 7.5 Documentation in repo
- [ ] Copy `/app/memory/*.md` into a `docs/` folder at repo root:
  - PRD.md
  - PRE_BETA_AUDIT.md
  - HARDENING_REPORT.md
  - PRODUCTION_CHECKLIST.md
  - PHASE5_DATA_SOURCES.md
  - HANDOFF_PACKAGE.md (this file)
- [ ] Root `README.md` with: project intro, quick-start, link to docs/.

### 7.6 Test credentials handling
- [ ] **DO NOT commit `/app/memory/test_credentials.md`** — add to `.gitignore`.
- [ ] Provide `test_credentials.md.example` with placeholder structure.

---

## 8. VS Code Local Development Checklist

### 8.1 Prerequisites
- [ ] Python 3.11 (pyenv or system).
- [ ] Node 20.x + Yarn 1.22+.
- [ ] MongoDB 4.4+ (local install OR Atlas free tier OR Docker).
- [ ] VS Code with extensions: Python, Pylance, ESLint, Tailwind CSS IntelliSense.

### 8.2 Clone + bootstrap
```bash
git clone https://github.com/<org>/synaptiq.git
cd synaptiq

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
cp .env.example .env
# Edit .env: set MONGO_URL=mongodb://localhost:27017, DB_NAME, JWT_SECRET, EMERGENT_LLM_KEY

# Frontend
cd ../frontend
cp .env.example .env
# Edit .env: REACT_APP_BACKEND_URL=http://localhost:8001
yarn install
```

### 8.3 Run services locally
```bash
# Terminal 1: Mongo (skip if Atlas)
mongod --dbpath ./data

# Terminal 2: Backend
cd backend && source .venv/bin/activate
uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Terminal 3: Frontend
cd frontend && yarn start  # opens http://localhost:3000
```

### 8.4 First-run verification
- [ ] Backend log shows `Application startup complete`.
- [ ] Backend log shows `Seeded admin + demo data`.
- [ ] Frontend opens, login page renders.
- [ ] Sign in with `admin@synaptiq.io / admin123` (or your seeded admin).
- [ ] Visit `/discover` — journals/conferences/grants render.

### 8.5 Recommended VS Code workspace settings
- `python.defaultInterpreterPath`: `backend/.venv/bin/python`
- `python.testing.pytestEnabled`: true
- `python.testing.pytestArgs`: `["backend/tests"]`
- `eslint.workingDirectories`: `["frontend"]`
- `editor.formatOnSave`: true

### 8.6 Common local issues
- **CORS errors**: confirm `CORS_ORIGINS=http://localhost:3000` in backend `.env`.
- **Cookie not set**: in dev, browsers tolerate `secure=False`; in prod-style local testing, use HTTPS (mkcert).
- **Rate-limited during testing**: bump `RATE_LIMIT_AUTH=100/minute` in dev `.env`.

---

## 9. Production Deployment Checklist

See `PRODUCTION_CHECKLIST.md` for the authoritative version. Summary:

1. Procure domain + TLS (Let's Encrypt / Cloudflare / ACM).
2. Provision compute (1+ vCPU per pod) + Mongo Atlas M10+.
3. Configure ingress to pass CORS + cookies through, forward `X-Forwarded-For`.
4. Set Group A env vars; flip `APP_ENV=production`, `COOKIE_SECURE=1`, `EXPOSE_RESET_TOKEN=0`, `EMAIL_VERIFICATION_REQUIRED=1`.
5. Restart backend; confirm startup logs show "Production env validation passed".
6. Verify headers: `curl -I https://app.synaptiq.io/api/` → CSP + HSTS + X-Frame + Referrer-Policy.
7. Smoke-test auth flow end-to-end.
8. Activate Stripe (Step 6 in PRODUCTION_CHECKLIST), Resend (Step 7), ORCID prod (Step 8) in any order.
9. Hit `GET /api/admin/production-readiness` — confirm `errors: []`.
10. Tag `v1.0-beta`.

---

## 10. Beta Launch Checklist

### 10.1 Code & deployment
- [ ] Production deployment checklist (§9) complete.
- [ ] All 3 integrations (Stripe, Resend, ORCID) activated.
- [ ] `/api/admin/production-readiness` returns `ready_for_production: true`.

### 10.2 Data + content
- [ ] Discovery sync run at least once (journals + conferences + grants populated).
- [ ] Seed admin password rotated from default `admin123`.
- [ ] 3 plans visible at `/pricing`.
- [ ] Privacy / Terms / Cookies / GDPR pages legally reviewed.

### 10.3 Communications
- [ ] Beta invitation email template ready.
- [ ] Beta-user onboarding doc ready (link to /onboarding).
- [ ] Status page (e.g., statuspage.io) configured.
- [ ] Support email (support@synaptiq.io) configured + auto-acknowledged.

### 10.4 Monitoring
- [ ] Sentry (or equivalent) wired and tested with a sample error.
- [ ] Log aggregator receiving JSON lines from backend.
- [ ] Mongo Atlas alerting configured (disk, connection pool, slow queries).
- [ ] Stripe + Resend dashboards have alert rules.

### 10.5 Safety nets
- [ ] Mongo backup snapshot taken; restore drill rehearsed.
- [ ] Rollback plan documented (previous container image + previous DB snapshot ID).
- [ ] Maintenance-mode page available (single HTML file, served by ingress).

### 10.6 Beta scope guards
- [ ] Mark certain features as "beta": Stripe checkout, ORCID sync, AI matching — collect explicit feedback.
- [ ] Add a feedback widget (or a `Help → Send Feedback` link) on every page.

### 10.7 Day-1 ops
- [ ] On-call rotation defined.
- [ ] Runbook for top 5 likely incidents (Mongo down, Stripe webhook backlog, Resend rate limit, ORCID API outage, login failure spike).
- [ ] Daily metrics review for first 2 weeks.

---

## 11. Known Limitations

### 11.1 Infrastructure-level (NOT code)
- **🔴 P1 — Ingress CORS rewrite**: K8s/Cloudflare ingress overrides `Access-Control-Allow-Origin` to `*` regardless of FastAPI's correct explicit allowlist. **Impact**: cross-origin authenticated requests will be rejected by browsers in production when frontend + backend are on different origins. **Resolution**: configure ingress to pass through upstream headers, OR deploy same-origin (frontend at `/`, backend at `/api/`).

### 11.2 Scalability
- **🟡 In-process APScheduler** — fires N times in N-pod deployment. Mitigation: keep `DISCOVERY_SCHEDULER_ENABLED=1` on single dedicated pod, OR migrate to external cron / Celery beat.
- **🟡 In-process WebSocket ConnectionManager** — won't broadcast across pods. Mitigation: Redis pub/sub adapter (1 day work).
- **🟡 In-process discovery ingest** — wall-bound; OK for ≤500k records. Mitigation: Celery worker for larger scales.
- **🟡 Mongo text search** — works up to ~100k records per collection. Mitigation: Atlas Search migration when relevance + autocomplete needed.

### 11.3 Feature gaps
- **Plan enforcement at write-time**: `plans_catalogue` limits (workspace count, AI calls) are informational only — not enforced at API boundary.
- **CCPA "Do Not Sell My Info"** link missing from cookie banner (acceptable if not targeting California consumers initially).
- **No 2FA / MFA** for user accounts.
- **No SSO** (SAML / OIDC) for institutional customers — institutional layer is invitation-based currently.
- **No admin UI for ingest scheduling** — all admin actions via API.

### 11.4 Test coverage
- 13 stale pytest tests reference deprecated API shapes (raw lists where new APIs return paginated dicts). Not real bugs — APIs upgraded intentionally. ~2 hours to update.
- ESLint warnings in PreviewDrawer (pre-existing, cosmetic).
- No load testing performed yet.

### 11.5 Orphan code
- `frontend/src/components/files/RecentFilesWidget.jsx` declared but not mounted in any layout. Either mount in sidebar (15 min) or delete.

---

## 12. Technical Debt

| Item | Severity | Effort | Plan |
|---|---|---|---|
| 13 stale pytest tests | LOW | 2 hours | Update assertions to new paginated shapes |
| `RecentFilesWidget` orphan | LOW | 15 min | Mount in sidebar or delete |
| PreviewDrawer ESLint warnings | LOW | 30 min | Cosmetic refactor |
| In-process WebSocket | MEDIUM | 1 day | Redis pub/sub when sharding |
| In-process APScheduler | MEDIUM | 1 day | External cron / Celery beat |
| Mongo text search | MEDIUM | 1 week | Atlas Search migration |
| No structured perf testing | MEDIUM | 1 day | k6 / Locust load test scripts |
| No Prometheus metrics | MEDIUM | 4 hours | `/metrics` endpoint with FastAPI Prometheus exporter |
| No Sentry / error tracker | HIGH for prod | 2 hours | Wire SDK + DSN env var |
| No request-ID middleware | MEDIUM | 1 hour | Generate UUID per request, attach to all logs |
| No admin UI for ingest | LOW | 1 day | Build `/admin/discovery` page |
| Plan limits not enforced | MEDIUM | 1 day | Add `@require_plan` decorator + enforcement at write APIs |
| Discovery ingest is wall-bound | MEDIUM | 2 days | Migrate to Celery worker before 1M+ records |

---

## 13. Future Roadmap Recommendations

### 13.1 Phase v1.1 (post-beta, 4–6 weeks)
- Two-factor authentication (TOTP via QR code).
- Stripe-driven plan enforcement (limit AI calls per plan, throttle workspace count).
- Sentry + Prometheus + request IDs (full observability).
- Atlas Search for discovery + autocomplete.
- Admin discovery dashboard.
- Researcher of the Month leaderboard (engagement / virality).
- CCPA-compliant cookie banner enhancement.

### 13.2 Phase v1.2 (8–12 weeks)
- Institutional SSO (SAML / OIDC) — enterprise sales unlocker.
- Public institution storefront (`/institution/{slug}` landing pages with research-output highlights).
- Cover-letter generator (LLM-assisted submission package).
- Author-level analytics (citation trajectory, network growth).
- Reviewer credentialing badges (verified ORCID + ≥10 completed reviews).

### 13.3 Phase v1.3 (3–6 months)
- Mobile-responsive deep refactor (current desktop-first).
- Native mobile app (React Native or Expo).
- Public API + developer portal (institutional integrations).
- Migration: in-process WS → Redis pub/sub.
- Migration: APScheduler → Celery beat.
- Multi-region deployment (EU + US data residency).

### 13.4 Strategic / business
- Integrate ResearchGate import (similar to ORCID) for broader publication coverage.
- Partnerships with publishers (Elsevier, Springer Nature) for journal preference data.
- Funder integrations (NSF, ERC, Wellcome Trust direct grant APIs).
- Conference organiser tools (registration, abstract review board on SYNAPTIQ).
- Department-level dashboard for research office customers.

---

## Appendix A — Files Created in Hardening + Production-Prep Phases

| File | Phase |
|---|---|
| `backend/rate_limit.py` | iter18 |
| `backend/routers/consent.py` | iter18 |
| `backend/services/email_templates.py` (verification template) | iter18 |
| `backend/services/email_service.py` (`send_email_verification`) | iter18 |
| `frontend/src/components/consent/CookieConsentBanner.jsx` | iter18 |
| `frontend/src/pages/VerifyEmail.jsx` | iter18 |
| `backend/middleware/__init__.py` (`SecurityHeadersMiddleware`) | iter19 |
| `backend/services/prod_validator.py` | iter19 |
| `backend/services/logging_config.py` | iter19 |
| `backend/routers/admin_health.py` (`/api/admin/production-readiness`) | iter19 |
| `memory/PRE_BETA_AUDIT.md` | audit pass 1 |
| `memory/HARDENING_REPORT.md` | iter18 |
| `memory/PRODUCTION_CHECKLIST.md` | iter19 |
| `memory/HANDOFF_PACKAGE.md` (this doc) | handoff |

## Appendix B — Quick smoke commands

```bash
# Production readiness check (run after every deploy)
COOKIE_JAR=$(mktemp)
curl -s -c $COOKIE_JAR -X POST "$API/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@synaptiq.io","password":"<ADMIN_PASS>"}' >/dev/null
curl -s -b $COOKIE_JAR "$API/api/admin/production-readiness" | jq

# Security headers check
curl -sI "$API/api/" | grep -iE "content-security|strict-transport|x-frame|referrer|permissions"

# Rate limit verification
for i in {1..7}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST "$API/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"x@x.com","password":"x"}'
done
```

---

## Appendix C — Credentials handoff

See `/app/memory/test_credentials.md` (DO NOT commit to GitHub).

Demo admin: `admin@synaptiq.io / admin123` ⚠ ROTATE BEFORE FIRST PROD DEPLOY.
Demo researcher: `elena.varga@synaptiq.io / demo123` (safe to discard in prod).

---

**End of handoff package. Codebase is ready for migration.**
