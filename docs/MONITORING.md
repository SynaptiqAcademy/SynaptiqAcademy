# Monitoring

## Health & readiness endpoints (built-in — no external tool required to check these)

| Endpoint | Purpose | Notes |
|---|---|---|
| `GET /api/health` | Public health check for uptime monitors | Checks MongoDB (fails fast via circuit breaker if already known down) and Redis (reports `unavailable`, not an error, if unset/down). Returns `503` if MongoDB is down. |
| `GET /api/health/live` | Liveness probe (Kubernetes/Docker) | Returns `200` if the process/event loop is responsive — does not check dependencies. Use this for container restart decisions. |
| `GET /api/health/ready` | Readiness probe (Kubernetes/Docker) | Returns `200` only when MongoDB is reachable; `503` otherwise. Use this to gate load-balancer traffic. |
| `GET /api/status` | Public, machine-readable platform status (incidents, component status) | Backs the in-app "Platform Status" admin page; also usable as an external status-page data source |
| `GET /api/ops/health`, `/api/ops/health/{component}` | Detailed per-component health (super-admin) | `backend/obs/router.py` |

## External uptime monitoring (set up in an uptime service)

Production runs on Railway and Vercel; the cron-based checks in `deploy/synaptiq.cron`
target a self-hosted server and **do not run there**. Create these monitors in an external
service (Better Stack, UptimeRobot or similar), alerting by email plus SMS or push to at
least two people:

| Monitor | URL | Interval | Alert when |
|---|---|---|---|
| API health | `https://api.synaptiq.academy/api/health` (until the domain is live: the Railway URL) | 1 min | status ≠ 200, or body lacks `"status":"ok"`, for 2 consecutive checks |
| API readiness | `https://api.synaptiq.academy/api/health/ready` | 1 min | status ≠ 200 for 2 checks (database unreachable) |
| Web app | `https://www.synaptiq.academy/` | 1 min | status ≠ 200, or the page lacks the text `Synaptiq` |
| Apex redirect | `https://synaptiq.academy/` | 5 min | not a 3xx to `www` |
| TLS certificates | both domains | daily | expiry < 14 days |

Railway's deploy health check uses `/api/health/live` (process alive). Consider switching it
to `/api/health/ready` so a release that cannot reach the database is not promoted.

## Alerts sent by the backend

`services/alerts.py` posts to `ALERT_WEBHOOK_URL` (a Slack, Discord or Teams incoming
webhook). Each alert is sent once per throttle window across all workers and replicas, and
never contains secrets or personal data.

| Alert | Trigger | What to do |
|---|---|---|
| `stripe_webhook_failed` | A Stripe event failed to process (Stripe retries it) | Check logs for the event id; Stripe → Developers → Webhooks → resend once fixed |
| `job_failed` | A scheduled job (imports, digests, ORCID/citation sync) failed for its window | Check logs; the job does not re-run in the same window |
| `credits_released` | Abandoned AI reservations were returned to users (requests killed by a restart, timeout or crash) | Expected after deploys; investigate if frequent |
| `ai_background_budget` | Background AI reached its daily or monthly budget and was paused | Review background AI usage or raise `AI_SYSTEM_BUDGET_SHARE` |
| `ai_budget` | Total AI provider spend crossed 50% / 80% / 100% of `AI_MONTHLY_BUDGET_USD` | Review usage; provider-side hard limits are the final backstop |

Also configure:

- **Sentry** (`SENTRY_DSN`): issue alerts for new issues and error spikes, routed to email or chat.
- **Stripe** → Developers → Webhooks → endpoint → email on failing deliveries.
- **Atlas** → Alerts: connections > 80% of limit, disk > 80%, replication lag, CPU sustained > 80%,
  backup failures.
- **AI providers**: monthly spend limits and notification thresholds in the Anthropic and OpenAI consoles.

## Internal observability platform (`backend/obs/`)

Mounted at `/api/ops/*` (super-admin only unless noted):

| Signal | Endpoint | Storage |
|---|---|---|
| Health per component | `GET /api/ops/health`, `/api/ops/health/{component}` | live checks |
| Metrics | `GET /api/ops/metrics`, `/api/ops/metrics/{category}` | `obs_metrics` collection |
| Distributed traces | `GET /api/ops/traces`, `/api/ops/traces/{trace_id}` | `obs_traces` collection |
| Structured logs (queryable) | `GET /api/ops/logs` | see [LOGGING.md](LOGGING.md) |
| Audit trail | `GET /api/ops/audit`, `/api/ops/audit/{record_id}` | `obs_audit` collection |
| Alerts | `GET /api/ops/alerts`, `POST /api/ops/alerts/evaluate`, acknowledge/resolve | — |
| AI cost | `GET /api/ops/cost`, `/api/ops/cost/breakdown`, `/api/ops/cost/recent` | `obs_cost` collection |
| Security events | `GET /api/ops/security`, `/api/ops/security/summary` | `obs_security` collection |
| Performance profiling | `GET /api/ops/profiler`, `/api/ops/profiler/recommendations` | — |

`GET /api/admin/production-readiness` (super-admin) runs the built-in production
validator (`services/prod_validator.py`) — a set of environment/configuration checks the
same tool used by CI's non-blocking "Production validator" step.

## Container-level monitoring (Docker Compose deployment)

```bash
docker ps                                    # container status
docker stats                                 # live CPU/memory per container
docker logs synaptiq_backend --tail=100 -f   # backend logs
docker logs synaptiq_redis --tail=50
docker logs synaptiq_nginx --tail=50
```

Resource limits are already defined in `docker-compose.prod.yml` (backend: 2 CPU / 2GB
limit; Redis: 0.5 CPU / 384MB; nginx: 1 CPU / 256MB) — a container repeatedly hitting its
memory limit will be OOM-killed and restarted (`restart: unless-stopped`); watch `docker
events` or your log aggregator for `OOMKilled` to catch this before users notice
repeated brief outages.

## Recommended dashboards (not built-in — assemble from the above)

- **Golden signals:** request rate, error rate, p50/p95/p99 latency — derive from
  `obs_traces`/`obs_metrics` or from your reverse proxy's access logs (nginx `json-file`
  logging driver is already configured with rotation in `docker-compose.prod.yml`).
- **Business signals:** registrations/day, active subscriptions, credit consumption rate,
  email delivery rate — derive from `credit_transactions`, `subscription_history`,
  `billing_events`, `email_log` collections respectively.

## Missing Production Requirements

- No pre-built dashboards; the data is collected (`obs_metrics`, `obs_traces`) but
  visualisation is left to the operator.
- `/api/health` does not check S3 or AI provider connectivity.
- For on-call paging beyond chat, connect the uptime service and Sentry to a pager.
