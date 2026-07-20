# Database

Provider setup: [MONGODB_ATLAS_SETUP.md](MONGODB_ATLAS_SETUP.md). This document covers
schema, indexing, and migration conventions.

## Connection management

`backend/db.py`:
- Motor (async) client, connection string from `MONGODB_URI`/`MONGO_URL` (see
  [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for the full alias list).
- Connection pooling via `MONGO_MAX_POOL` (default 200).
- **Circuit breaker:** `is_db_down()` / `mark_db_down()` / `mark_db_up()` — once Mongo is
  detected down, the app stops attempting new connections for `DB_DOWN_COOLDOWN_SECONDS`
  (default 60s) rather than letting every request hang on the driver's own
  `serverSelectionTimeoutMS`. This is why `/api/health` can fail fast instead of taking
  several seconds per probe during an outage.
- No manual restart is required for the app to reconnect once Mongo recovers — the
  circuit breaker's cooldown-then-retry behavior, and the worker platform's own
  supervisor (see [ARCHITECTURE.md](ARCHITECTURE.md)), both self-heal.

## Data access layer

All application code reads/writes MongoDB through `repo/shim.py`'s `DBProxy`, constructed
with a `SecurityContext` (see [SECURITY.md](SECURITY.md)) — never a raw Motor client
directly in route handlers. This gives every query automatic row-level scoping plus a
built-in two-tier cache (in-process L1 + Redis L2, when Redis is available) without each
call site having to opt in individually.

## Core collections

| Collection | Purpose | Notes |
|---|---|---|
| `users` | Accounts, profile, `plan_code`, dual credit balance, OAuth links | Central entity |
| `refresh_tokens` | Refresh-token revocation registry (`jti`, `session_id`, `revoked`) | See [SECURITY.md](SECURITY.md) |
| `subscriptions` | Mirrors Stripe subscription state (`plan_code`, `status`, `stripe_subscription_id`) | Kept in sync with `users.plan_code` by the billing webhook |
| `subscription_history` | Plan-change audit trail | Append-only |
| `billing_events` | Raw Stripe webhook payloads | Unique index on `stripe_event_id` — the idempotency mechanism |
| `billing_history` | User-facing invoice/purchase log | — |
| `billing_disputes` | Stripe dispute records | — |
| `credit_transactions` | The sole authoritative credit ledger (grants, consumption, refunds) | Every balance change has a corresponding row here |
| `credit_purchases` | Credit-pack purchase records | — |
| `conversations` / `messages` | Direct messaging | Backs the WebSocket real-time layer |
| `worker_jobs` | Background job queue | Managed by `backend/worker/` |
| `email_log` | Sent-email records, delivery/open/click tracking | See [EMAIL_SYSTEM.md](EMAIL_SYSTEM.md) |
| `audit_log` | Billing/security audit trail | `services/audit.py` |
| `obs_audit` / `obs_metrics` / `obs_traces` / `obs_cost` / `obs_security` | Observability platform storage | See [MONITORING.md](MONITORING.md) |
| `password_resets` | One-time reset tokens | TTL-indexed — auto-expires |
| `feature_flags` / `platform_settings` | Runtime config, maintenance mode | Admin-managed |
| `platform_incidents` | Status page incident records | Backs `/api/status` |

This is not exhaustive — the platform has ~150 routers across many domains (research
collaboration, grants, teaching, institution analytics, knowledge graph, etc.), each with
its own collection(s). Use `mongosh "$MONGODB_URI/$MONGODB_DB_NAME" --eval
"db.getCollectionNames()"` against a running instance for the full current list.

## Indexes

Created **idempotently at application startup** — not via a separate migration command.
`server.py`'s startup event runs a long sequence of index-creation blocks (one per
feature area — you'll see log lines like `"Phase XI expansion indexes ensured"`,
`"Institution Platform Phase 11 indexes ensured"`, etc.), each wrapped so a failure in one
doesn't block the others. A fresh Atlas cluster self-provisions all required indexes on
first boot; no manual `createIndex` step is needed.

Occasional non-fatal warnings like `IndexKeySpecsConflict` (existing auto-named index
with slightly different options, e.g. missing `sparse: true`) appear in logs on repeated
startups — these are safe to ignore; they mean the index already exists in a compatible
enough form, just not byte-identical to what the code just tried to create.

## Migrations

**There is no dedicated migration framework** (no Alembic-equivalent for MongoDB in this
codebase). Data migrations/backfills are implemented as idempotent blocks directly in
`server.py`'s startup sequence (e.g., "Demo-data isolation migration", "Research OS
migration: back-fill member_roles") — each checks whether its work is already done before
doing it again, logs its own success/warning, and never blocks startup on failure. When
adding a new migration:

1. Write it as an idempotent block (safe to run on every boot).
2. Wrap it in try/except with a clear log message on both success and failure.
3. Add it near the other migration blocks in `server.py`'s startup sequence.
4. Do not assume it runs exactly once — it runs on every process start, including every
   Gunicorn worker reload.

## TTL and retention

| Collection | Retention mechanism |
|---|---|
| `password_resets` | MongoDB TTL index — auto-deleted |
| `billing_events` | 90-day payload retention noted in `deploy/ARCHITECTURE.md`; metadata kept indefinitely (verify current TTL index configuration matches this intent before relying on it) |
| `audit_log` | 90-day TTL referenced in `deploy/RUNBOOK.md` |
| Most other collections | Indefinite — no automated pruning |

`services/cleanup_service.py`'s `run_all()` (invoked every 6 hours via
`deploy/synaptiq.cron`) removes expired password resets, expired MFA tokens, stale
billing payloads, anonymized consent records past their window, deleted API keys,
expired announcements, and old notifications — this is the primary automated retention
mechanism beyond MongoDB's own TTL indexes.

## Backups

See [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md).

## Missing Production Requirements

- No formal schema-versioning/migration-tracking table exists (no record of "which
  migrations have run against this database") — the idempotent-block pattern makes this
  low-risk today, but it will not scale gracefully to a large number of one-time
  backfills. Consider a lightweight `schema_migrations` collection recording
  `{name, applied_at}` if the number of migration blocks keeps growing.
- Verify the actual TTL index configuration on `billing_events` and `audit_log` matches
  the retention periods described in existing docs — this manual reports what other
  project documentation claims, not a freshly re-verified index inspection of every
  collection.
