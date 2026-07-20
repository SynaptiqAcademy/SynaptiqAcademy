# Environment Variables

Every variable below was found by grepping `os.environ.get(...)` / `os.environ[...]`
across `backend/` and `process.env.*` across `frontend/src/` — nothing here is guessed.
No real secret values are shown anywhere in this document.

Backend variables are loaded from `backend/.env` (see `backend/.env.example` if present,
otherwise use the tables below as the template). Frontend variables are baked into the
static build at build time (CRA convention: only `REACT_APP_*` variables are exposed to
browser code).

## Core — required in every environment

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `JWT_SECRET` | HMAC signing secret for access/refresh tokens (HS256) | **Required** | `auth_utils.py` | high-entropy random string, ≥32 chars |
| `MONGODB_URI` (deprecated backward-compatible alias: `MONGO_URL`, checked in that order by `db.py`) | MongoDB Atlas SRV connection string | **Required** | `db.py` | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `MONGODB_DB_NAME` (or legacy `DB_NAME`) | Target database name | **Required** | `db.py` | `synaptiq` |
| `ENCRYPTION_KEY` | 256-bit base64 key for field-level encryption (ORCID tokens, etc.) | **Required** | `services/encryption_service.py` | 44-char base64 string (`openssl rand -base64 32`) |
| `SUPER_ADMIN_EMAILS` | Comma-separated list of emails granted `super_admin` on login | **Required** | `auth_utils.py`, seed scripts | `admin@synaptiq.academy` |
| `CORS_ORIGINS` | Comma-separated allowlist of origins permitted to call the API | **Required** | `server.py` | `https://synaptiq.academy,https://www.synaptiq.academy` |
| `APP_ENV` | Environment flag — gates prod-only behavior (JSON logs, secure cookies default, prod validator) | **Required** (defaults to `development` if unset) | `server.py`, `logging_config.py` | `production` |

## Auth & sessions

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `COOKIE_SECURE` | Force `Secure` flag on auth cookies | Recommended in prod (`1`) | `auth_utils.py` | `1` |
| `COOKIE_SAMESITE` | `SameSite` cookie attribute | Optional (default `lax`) | `auth_utils.py` | `lax` |
| `EMAIL_VERIFICATION_REQUIRED` | Block login/session issuance until email is verified | Optional (default `0`) | `routers/auth.py`, `routers/google_auth.py`, `routers/orcid.py` | `1` |
| `EMAIL_VERIFICATION_TTL_HOURS` | Verification link lifetime | Optional | `services/email/tokens.py` | `24` |
| `EXPOSE_RESET_TOKEN` | **Dev/CI only** — echoes password-reset tokens in the API response instead of only emailing them | Must be unset/`0` in production | `routers/auth.py` | `0` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Seed credentials for the initial admin account (see `seed.py`) | Required for first boot only | `seed.py` | — |
| `SUPER_ADMIN_PASSWORD` | Seed password for the super-admin bootstrap account | Required for first boot only | `seed.py` | — |
| `ZT_MASTER_KEY` | Zero Trust package master key (device trust / risk engine signing) | Recommended in prod | `zt/` | high-entropy random string |
| `IP_HASH_SALT` | Salt used to hash IPs for GDPR-compliant storage | Recommended in prod | `zt/`, audit logging | high-entropy random string |
| `RISK_BLOCK_THRESHOLD` / `RISK_VERIFY_THRESHOLD` | Zero Trust risk-score thresholds | Optional (has defaults) | `zt/` | numeric |
| `RATE_LIMIT_AUTH` | Override default per-IP rate limit for auth endpoints | Optional | `rate_limit.py` | `10/minute` |

*(Resolved: an admin config-status panel in `routers/admin_aos.py` previously checked a
non-existent `JWT_SECRET_KEY` variable instead of the real `JWT_SECRET` — always showing
"not configured" regardless of actual setup. Fixed to read `JWT_SECRET`; `JWT_SECRET_KEY`
is not a real variable and does not appear anywhere in the codebase anymore.)*

## Database (MongoDB)

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `MONGO_MAX_POOL` | Max connection pool size | Optional (default `200`) | `db.py` | `200` |
| `MONGO_SERVER_SELECTION_TIMEOUT_MS` | Server selection timeout | Optional | `db.py` | `5000` |
| `DB_DOWN_COOLDOWN_SECONDS` | Circuit-breaker cooldown before retrying a down Mongo | Optional (default `60`) | `db.py` | `60` |

## Redis (optional — every consumer degrades gracefully to `None`)

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `REDIS_URL` | Redis connection URL | Optional but strongly recommended in prod | `services/redis_client.py` | `redis://:password@host:6379/0` |
| `REDIS_PASSWORD` | Redis AUTH password (also substituted into `docker-compose.prod.yml`) | Required if `REDIS_URL` is set with auth | `docker-compose.prod.yml` | — |
| `REDIS_MAX_CONNECTIONS` | Connection pool size | Optional (default `20`) | `redis_client.py` | `20` |
| `REDIS_SOCKET_TIMEOUT` | Socket/connect timeout (seconds) | Optional (default `3`) | `redis_client.py` | `3` |
| `REDIS_RETRY_COOLDOWN_SECONDS` | Cold-start reconnect cooldown | Optional (default `15`) | `redis_client.py` | `15` |

## Object storage (AWS S3)

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `AWS_ACCESS_KEY_ID` | IAM key with `s3:GetObject`/`s3:PutObject` | Required for uploads/downloads | `services/storage_service.py` | — |
| `AWS_SECRET_ACCESS_KEY` | Corresponding IAM secret | Required for uploads/downloads | `services/storage_service.py` | — |
| `AWS_REGION` | Bucket region | Optional (default `us-east-1`) | `services/storage_service.py` | `eu-west-1` |
| `S3_BUCKET_NAME` | Target bucket for user uploads | Required for uploads/downloads | `services/storage_service.py` | `synaptiq-prod-uploads` |
| `S3_ENDPOINT_URL` | S3-compatible endpoint override (MinIO, etc.) | Optional | `services/storage_service.py` | `https://s3.eu-west-1.amazonaws.com` |
| `S3_BACKUP_BUCKET` | Destination bucket for `mongodump` backups | Required for automated backups | `deploy/backup.sh` | `synaptiq-prod-backups` |
| `BACKUP_ENCRYPTION_PASSPHRASE` | Passphrase used to `openssl enc` backup archives before upload | Required for automated backups | `deploy/backup.sh` | high-entropy passphrase |

## Email (Resend)

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `RESEND_API_KEY` | Resend API key | Required for real email delivery | `services/email/` | `re_...` |
| `RESEND_WEBHOOK_SECRET` | Svix HMAC secret for the Resend delivery webhook | Required if using delivery/open/click tracking | `routers/email.py` | `whsec_...` |
| `EMAIL_PROVIDER` | Provider selector | Optional (default `resend`) | `services/email_service.py` | `resend` |
| `EMAIL_FROM` | Default From address | Required | `services/email/` | `Synaptiq <noreply@synaptiq.academy>` |
| `EMAIL_DRY_RUN` | Log emails instead of sending — **dev/CI only** | Must be unset/`0` in production | `services/email_service.py` | `0` |
| `DISABLE_EMAIL_STUB` | Disables the mock/stub email path | Optional | `services/email_service.py` | `1` |

## AI providers

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `ANTHROPIC_API_KEY` | Primary AI provider key | Required for AI features | `services/ai/` | `sk-ant-...` |
| `OPENAI_API_KEY` | Fallback AI provider key | Recommended | `services/ai/` | `sk-...` |
| `AI_MATCHING_PROVIDER` | Which provider to prefer for matching features | Optional (default `anthropic`) | `services/ai/` | `anthropic` |
| `AI_MATCHING_MODEL` / `AI_OPENAI_MODEL` | Model name override | Optional | `services/ai/` | `claude-sonnet-4-6`, `gpt-4o` |
| `AI_ANTHROPIC_TIMEOUT` / `AI_OPENAI_TIMEOUT` | Per-provider request timeout (seconds) | Optional | `services/ai/` | `30` |
| `AI_ANTHROPIC_RETRIES` / `AI_OPENAI_RETRIES` | Retry count | Optional | `services/ai/` | `2` |
| `AI_DAILY_BUDGET_USD` / `AI_HOURLY_BUDGET_USD` / `AI_MONTHLY_BUDGET_USD` | Spend caps enforced by the AI Gateway | Optional | `gateway/`, `obs/cost.py` | `50` |
| `AI_CACHE_ENABLED` / `AI_CACHE_TTL_SECONDS` | Response caching | Optional | `services/ai/` | `1` / `3600` |
| `AI_RULE_LAYER_ENABLED` | Enable the deterministic rule-engine layer before any LLM call | Optional (default `1`) | `services/ai/` | `1` |
| `SMART_ROUTER_PREFERRED_PROVIDER` | Override for the smart execution router | Optional | `services/ai/` | `anthropic` |
| `AI_LOCAL_ENABLED` | Enable the local/self-hosted model **layer inside the main AI Gateway chain** (`services/ai/layers/local_ai.py`) — see the important distinction below | Optional (default `0`) | `services/ai/engine/config.py`, `services/ai/layers/local_ai.py` | `0` |
| `AI_LOCAL_URL` / `AI_LOCAL_MODEL` / `AI_LOCAL_TIMEOUT` | Endpoint/model/timeout for the Gateway-chain local layer above — only relevant if `AI_LOCAL_ENABLED=1` | Optional (defaults: `http://localhost:11434`, `llama3.2`, `120`s) | `services/ai/engine/config.py` | `http://localhost:11434` |
| `LOCAL_AI_*` (12 vars: `DEFAULT_PROVIDER`, `OLLAMA_URL`, `VLLM_URL`, `LM_STUDIO_URL`, `OPENAI_COMPAT_URL`, `OPENAI_COMPAT_KEY`, `PREFERRED_MODEL`, `TIMEOUT`, `MAX_RETRIES`, `RETRY_DELAY`, `MAX_PARALLEL`, `MAX_CONTEXT`, `MAX_OUTPUT`, `TEMPERATURE`, `STREAMING`, `AUTO_DISCOVER`, `DISCOVERY_TIMEOUT`, `HEALTH_INTERVAL`, `CACHE_MAX_SIZE`, `CACHE_TTL`) | **A completely separate, independent local-model engine** (`services/local_ai/`) with its own multi-provider registry, caching, and health monitoring — exposed only via its own admin router (`/api/admin/local-ai/*`), **not** gated by `AI_LOCAL_ENABLED` and not part of the main AI Gateway fallback chain | Optional | `services/local_ai/config.py`, `routers/admin_local_ai.py` | — |
| `KNOWLEDGE_*` (17 vars: `ENABLED`, `RAG_ENABLED`, `VECTOR_BACKEND`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `CHUNK_STRATEGY`, `CHUNK_MIN_TOKENS`, `CHUNK_MAX_TOKENS`, `CHUNK_OVERLAP`, `TOP_K`, `MIN_SCORE`, `SEM_WEIGHT`, `KW_WEIGHT`, `CTX_MAX_CHUNKS`, `CTX_MAX_TOKENS`, `AUTO_INDEX`) | RAG/knowledge-base retrieval tuning | Optional (all have defaults) | `services/knowledge/` | — |

Both providers below now follow identical conventions: `{PROVIDER}_CLIENT_ID` /
`{PROVIDER}_CLIENT_SECRET` / `{PROVIDER}_REDIRECT_URI`, plus an optional
`{PROVIDER}_STATE_SECRET` (falls back to `JWT_SECRET` if unset) for OAuth CSRF-state
signing. This was made consistent in the 2026-07-19 configuration pass — Google
previously derived its state secret from `JWT_SECRET` with no override option and no
dedicated variable name.

## OAuth — Google

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID | Required for Google login | `services/google_oauth.py` | `....apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret | Required for Google login | `services/google_oauth.py` | — |
| `GOOGLE_REDIRECT_URI` | Must exactly match the URI registered in Google Cloud Console. Falls back to `BACKEND_BASE_URL + /api/google/callback` if unset. | Required for Google login | `services/google_oauth.py` | `https://api.synaptiq.academy/api/google/callback` |
| `GOOGLE_STATE_SECRET` | Signs the OAuth `state` parameter. Optional — falls back to `JWT_SECRET` if unset. | Optional | `services/google_oauth.py` | high-entropy random string |

## OAuth — ORCID

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `ORCID_CLIENT_ID` | ORCID API client ID | Required for ORCID login/linking | `services/orcid/oauth.py` | — |
| `ORCID_CLIENT_SECRET` | ORCID API client secret | Required for ORCID login/linking | `services/orcid/oauth.py` | — |
| `ORCID_REDIRECT_URI` | Must exactly match the URI registered in the ORCID Developer Tools. Falls back to `BACKEND_BASE_URL + /api/orcid/callback` if unset. | Required for ORCID login/linking | `services/orcid/oauth.py` | `https://api.synaptiq.academy/api/orcid/callback` |
| `ORCID_BASE_URL` | `https://orcid.org` (production) or `https://sandbox.orcid.org` (sandbox) | Required | `services/orcid/oauth.py` | `https://orcid.org` |
| `ORCID_API_BASE_URL` | ORCID public API base | Required | `services/orcid/sync.py` | `https://pub.orcid.org/v3.0` |
| `ORCID_STATE_SECRET` | Signs the OAuth `state` parameter. Optional — falls back to `JWT_SECRET`, then to a hardcoded literal string, if unset. Set explicitly to keep this secret's blast radius separate from `JWT_SECRET`. | Optional | `services/orcid/oauth.py` | high-entropy random string |
| `OPENALEX_MAILTO` | Contact email sent to OpenAlex's polite pool (publication enrichment) | Optional but recommended | `services/orcid/sync.py` | `contact@synaptiq.academy` |

## Payments (Stripe)

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `STRIPE_SECRET_KEY` | Stripe secret API key | Required for any billing feature | `services/stripe_service.py` | `sk_live_...` / `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | Signing secret for webhook HMAC verification | Required — webhook is a no-op without it | `routers/billing.py` | `whsec_...` |
| `STRIPE_TAX_ENABLED` | Enable Stripe Tax (automatic tax + tax ID collection) | Optional (default `0`) | `services/stripe_service.py` | `1` |
| `STRIPE_IDEMPOTENCY` | Attach idempotency keys to checkout session creation | Optional (default `1`, recommended on) | `services/stripe_service.py` | `1` |

See [STRIPE_SETUP.md](STRIPE_SETUP.md) — Stripe Price IDs are **not** environment
variables; they are stored per-plan in `backend/plans_catalogue.py` and are currently
empty strings (not yet configured — see that document's "Missing Production
Requirements" section).

## URLs

**Resolved (2026-07-19 configuration consistency pass):** an earlier audit of this
codebase found that `services/google_oauth.py` read `APP_BASE_URL` for its frontend
redirect base instead of the real `FRONTEND_BASE_URL` variable that
`services/orcid/oauth.py` correctly used, and that `APP_BASE_URL` was inconsistently
treated as "the frontend origin" in some call sites. This has been fixed in code:
`FRONTEND_BASE_URL` and `BACKEND_BASE_URL` are now the two canonical names, read
identically by both OAuth providers and by the email system. `APP_BASE_URL` still works
— it is kept as an explicit, documented backward-compatible alias for
`FRONTEND_BASE_URL` — but should not be used in new deployments.

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `FRONTEND_BASE_URL` | **Canonical.** Frontend origin, used to build every user-facing link: OAuth post-login redirect targets (both Google and ORCID), email verification/reset links, unsubscribe redirect. | Required | `services/google_oauth.py`, `services/orcid/oauth.py`, `services/email_service.py`, `routers/email_preferences.py`, `routers/email.py` | `https://synaptiq.academy` |
| `APP_BASE_URL` | **Deprecated backward-compatible alias for `FRONTEND_BASE_URL`.** Every call site above falls back to this name if `FRONTEND_BASE_URL` is unset, so existing deployments that only set `APP_BASE_URL` keep working unchanged. Do not use on new deployments — set `FRONTEND_BASE_URL` instead. | Not required if `FRONTEND_BASE_URL` is set | same as `FRONTEND_BASE_URL` (fallback only) | `https://synaptiq.academy` |
| `BACKEND_BASE_URL` | **Canonical.** Backend/API origin, used to construct this app's own OAuth callback URLs when `GOOGLE_REDIRECT_URI`/`ORCID_REDIRECT_URI` themselves are unset, and by the admin unsubscribe-link builder. | Recommended | `services/google_oauth.py`, `services/orcid/oauth.py`, `routers/admin_email_center.py` | `https://api.synaptiq.academy` |
| `BASE_URL` | **Test-only** — read exclusively by files under `backend/tests/` as the target host for test-runner HTTP calls (default `http://localhost:8001`). Not read by any production application code path; unrelated to `FRONTEND_BASE_URL`/`BACKEND_BASE_URL` despite the similar name. | Not applicable to production | `tests/test_*.py` (multiple files) | `http://localhost:8001` |
| `PUBLIC_BASE_URL` | **Test-only** — read by exactly one test file (`tests/test_files_smoke_iter15.py`) as its target host default. Not read by any production application code path. | Not applicable to production | `tests/test_files_smoke_iter15.py` | `http://localhost:8001` |
| `TEST_BASE_URL` | Base URL used by `deploy/dr_validate.sh` | Optional | `deploy/dr_validate.sh` | `http://localhost:8000` |

## Observability / operations

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `SENTRY_DSN` | Sentry project DSN for error tracking | Strongly recommended | `server.py` | `https://...@o0.ingest.sentry.io/0` |
| `LOG_LEVEL` | Root logger level | Optional (default `INFO`) | `services/logging_config.py` | `INFO` |
| `ALERT_WEBHOOK_URL` | Slack/Discord-compatible webhook for cron alerts (backup failure, disk space, health) | Recommended | `deploy/synaptiq.cron` | `https://hooks.slack.com/services/...` |
| `CSP_REPORT_URI` | Content-Security-Policy report endpoint | Optional | `middleware/` | `/api/csp-report` |
| `DISCOVERY_SCHEDULER_ENABLED` | Enable the OpenAlex/discovery ingestion scheduler | Optional (default `0`) | `services/discovery/scheduler.py` | `0` |
| `DISCOVERY_CONTACT_EMAIL` | Contact email for discovery-provider polite pools | Optional | `services/discovery/` | `contact@synaptiq.academy` |
| `GEO_TIMEOUT_SECS` | Timeout for IP geolocation lookups (login anomaly detection) | Optional | `zt/` | `2` |
| `APP_NAME` / `APP_VERSION` | Displayed in health checks and logs | Optional | `server.py` | `SYNAPTIQ` / `1.7.0` |
| `CI` | Set automatically by GitHub Actions; gates CI-only behavior | N/A (auto-set) | tests, `services/prod_validator.py` | `true` |

## Frontend (build-time)

| Variable | Description | Required | Used in | Example format |
|---|---|---|---|---|
| `REACT_APP_BACKEND_URL` | Backend origin the SPA calls (axios `baseURL` is derived from this + `/api`) | **Required** | `frontend/src/lib/api.js` | `https://api.synaptiq.academy` |
| `REACT_APP_API_URL` | Legacy/alternate name for the same purpose — verify only one is actually read in your build | Check before relying on it | grep `frontend/src` | — |
| `NODE_ENV` | Standard CRA build-mode flag | Set automatically by `npm run build` | CRA tooling | `production` |

**Important:** these are baked into the JS bundle at build time. Changing
`REACT_APP_BACKEND_URL` requires a rebuild and redeploy of the frontend — it cannot be
changed at runtime via server environment variables.

## Missing Production Requirements

- `backend/.env.example` exists and is a good starting template, but does not include
  every variable in this document (e.g. it omits `KNOWLEDGE_*`, most `LOCAL_AI_*`/`AI_LOCAL_*`
  tuning knobs, `ZT_MASTER_KEY`, `RISK_BLOCK_THRESHOLD`/`RISK_VERIFY_THRESHOLD`, `IP_HASH_SALT`,
  `CSP_REPORT_URI`). Treat this document's tables as the complete reference and
  `.env.example` as a quick-start subset, not the other way around.
- Stripe Price IDs are still empty in `plans_catalogue.py` in this environment — see
  [STRIPE_SETUP.md](STRIPE_SETUP.md). The production validator now checks this directly
  (`STRIPE_PLAN_PRICE_IDS`) instead of the non-functional `STRIPE_PRICE_*` env vars that
  used to be checked (those env vars, and the dead validator checks for them, have been
  removed from the codebase).
- `BASE_URL` and `PUBLIC_BASE_URL` remain test-only variables with no effect on production
  behavior — do not set them expecting them to configure anything in the running app.

**Resolved in the 2026-07-19 configuration consistency pass** (kept here for history —
no further action needed): the `google_oauth.py`/`FRONTEND_BASE_URL` mismatch described in
the "URLs" section above, the dead `JWT_SECRET_KEY` admin-panel check, the dead
`STRIPE_PRICE_*` variables, the undocumented `DATABASE_URL`/`MONGO_URI` Mongo-connection
fallbacks, and Google OAuth's lack of a dedicated, overridable state secret.
