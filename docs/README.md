# Synaptiq — Operations Manual

This `/docs` folder is the production operations manual for Synaptiq. It is written so a
senior engineer who has never touched this codebase can deploy, operate, secure, and
recover the platform without asking anyone a question.

**Scope note:** `/deploy` (repo root) already contains working operational assets —
`Dockerfile`, `docker-compose.prod.yml`, `nginx.conf`, `k8s/`, `backup.sh`,
`check_backup_integrity.sh`, `dr_validate.sh`, `synaptiq.cron`, `synaptiq-backend.service`,
plus three existing docs (`ARCHITECTURE.md`, `RUNBOOK.md`, `INCIDENT_RESPONSE.md`). This
`/docs` folder does not duplicate those scripts — it explains what they do, when to use
them, and everything else (env vars, third-party setup, security model, release process)
that wasn't previously documented in one place. Where `/deploy`'s existing docs already
cover a topic well, this manual cross-references them rather than restating verbatim.

## What Synaptiq is

A FastAPI (Python 3.11+) backend + React 18 (CRA/craco) frontend academic SaaS platform:
research collaboration, AI-assisted academic tooling, grants/funding discovery, billing,
messaging, and an institution-facing admin suite. MongoDB Atlas is the system of record;
Redis is an optional, gracefully-degradable cache/session/rate-limit layer.

## Reading order for a new engineer

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** — system shape, data model, request flow.
2. **[ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)** — every config knob, required vs optional.
3. **[DEPLOYMENT.md](DEPLOYMENT.md)** — how to actually stand the thing up.
4. **[PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)** and **[GO_LIVE_CHECKLIST.md](GO_LIVE_CHECKLIST.md)** — what must be true before real users touch it.
5. Everything else, as needed — indexed below.

## Document index

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, stack, data flow, directory layout |
| [DEPLOYMENT.md](DEPLOYMENT.md) | End-to-end deploy: clone → build → run → verify → rollback |
| [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) | Pre-launch verification checklist by subsystem |
| [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) | Every env var: purpose, required/optional, where used |
| [DOMAIN_CONFIGURATION.md](DOMAIN_CONFIGURATION.md) | `synaptiq.academy` / `api.synaptiq.academy` setup |
| [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md) | Exact DNS records to create |
| [VERCEL_SETUP.md](VERCEL_SETUP.md) | Optional: deploying the frontend to Vercel |
| [RAILWAY_SETUP.md](RAILWAY_SETUP.md) | Optional: deploying the backend to Railway |
| [MONGODB_ATLAS_SETUP.md](MONGODB_ATLAS_SETUP.md) | Atlas cluster, network access, users, indexes |
| [REDIS_SETUP.md](REDIS_SETUP.md) | Redis provisioning and configuration |
| [AWS_S3_SETUP.md](AWS_S3_SETUP.md) | Object storage bucket + IAM setup |
| [RESEND_SETUP.md](RESEND_SETUP.md) | Transactional email provider setup |
| [ORCID_SETUP.md](ORCID_SETUP.md) | ORCID OAuth application setup |
| [OPENAI_ANTHROPIC_SETUP.md](OPENAI_ANTHROPIC_SETUP.md) | AI provider keys and fallback chain |
| [STRIPE_SETUP.md](STRIPE_SETUP.md) | Stripe products, prices, webhook setup |
| [SECURITY.md](SECURITY.md) | Auth, CSRF, rate limiting, secrets, headers, CORS |
| [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md) | Backup schedule, restore procedure, DR |
| [MONITORING.md](MONITORING.md) | What to monitor and how, for every subsystem |
| [LOGGING.md](LOGGING.md) | Log format, levels, where logs go, how to query them |
| [EMAIL_SYSTEM.md](EMAIL_SYSTEM.md) | Transactional email architecture |
| [DATABASE.md](DATABASE.md) | Collections, indexes, migrations, connection management |
| [API.md](API.md) | API conventions, auth, error format, key endpoints |
| [VERSIONING.md](VERSIONING.md) | API versioning and backward-compatibility policy |
| [CI_CD.md](CI_CD.md) | GitHub Actions pipeline |
| [RELEASE_PROCESS.md](RELEASE_PROCESS.md) | Branching, release cutting, hotfixes |
| [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md) | Severity levels, on-call steps, escalation |
| [BETA_LAUNCH.md](BETA_LAUNCH.md) | Beta-specific rollout plan and gates |
| [GO_LIVE_CHECKLIST.md](GO_LIVE_CHECKLIST.md) | Final sign-off checklist before opening to real users |

## Conventions used throughout this manual

- Every environment variable is named exactly as it appears in code — verified by grep
  against `backend/` and `frontend/src/`, not guessed.
- No real secret values are ever shown — only variable names, purposes, and example
  *formats* (e.g. `sk_live_...`, never a real key).
- Where the codebase does not yet implement something a production SaaS normally needs,
  it is called out explicitly under a **Missing Production Requirements** heading in the
  relevant document, not silently invented.
- Commands assume the repository root is `sinaptiq-main-2/` and are safe to copy-paste.
