# Monitoring

## Health & readiness endpoints (built-in — no external tool required to check these)

| Endpoint | Purpose | Notes |
|---|---|---|
| `GET /api/health` | Public health check for uptime monitors | Checks MongoDB (fails fast via circuit breaker if already known down) and Redis (reports `unavailable`, not an error, if unset/down). Returns `503` if MongoDB is down. |
| `GET /api/health/live` | Liveness probe (Kubernetes/Docker) | Returns `200` if the process/event loop is responsive — does not check dependencies. Use this for container restart decisions. |
| `GET /api/health/ready` | Readiness probe (Kubernetes/Docker) | Returns `200` only when MongoDB is reachable; `503` otherwise. Use this to gate load-balancer traffic. |
| `GET /api/status` | Public, machine-readable platform status (incidents, component status) | Backs the in-app "Platform Status" admin page; also usable as an external status-page data source |
| `GET /api/ops/health`, `/api/ops/health/{component}` | Detailed per-component health (super-admin) | `backend/obs/router.py` |

## What to monitor externally

| Signal | How | Alert condition |
|---|---|---|
| Uptime | UptimeRobot / BetterStack (or similar) polling `https://api.synaptiq.academy/api/health` every 1–5 min | HTTP status ≠ 200 for 2 consecutive checks, or JSON `status` ≠ `"ok"` |
| Frontend availability | Same tool, polling `https://synaptiq.academy/` | HTTP status ≠ 200 |
| Errors | Sentry (`SENTRY_DSN`) | New error type, or error rate spike (>10/min recommended starting threshold) |
| Disk space | `deploy/synaptiq.cron` hourly check + `/api/health`'s own `disk_pct` field | >80% warning, >95% critical (thresholds referenced in `deploy/INCIDENT_RESPONSE.md`) |
| Backup success/failure | `ALERT_WEBHOOK_URL` (Slack/Discord-compatible), fired by `deploy/backup.sh` | Any failure |
| Backup integrity | `ALERT_WEBHOOK_URL`, fired by `deploy/check_backup_integrity.sh` (weekly) | Checksum mismatch |
| DR readiness | `ALERT_WEBHOOK_URL`, fired by `deploy/dr_validate.sh` (weekly) | Any validation failure |
| MongoDB Atlas | Atlas's own built-in alerting (connections, disk, replication lag, slow queries) | Configure directly in Atlas UI — not automated by this codebase |
| AI spend | `obs_cost` collection / `GET /api/ops/cost`, `/api/ops/cost/breakdown` | Approaching `AI_DAILY_BUDGET_USD`/`AI_MONTHLY_BUDGET_USD` |

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

- No pre-built Grafana/Datadog dashboard definitions exist in the repo — the data is
  collected (`obs_metrics`, `obs_traces`, etc.) but visualization is left to the operator.
- No alerting is wired directly from `obs/alerting.py`'s alert records to an external
  paging tool (PagerDuty, Opsgenie) — only the cron-based `ALERT_WEBHOOK_URL` (Slack/
  Discord) path exists today. For true on-call paging, integrate one.
- `/api/health` does not check S3 or AI provider connectivity (see
  [AWS_S3_SETUP.md](AWS_S3_SETUP.md) and [OPENAI_ANTHROPIC_SETUP.md](OPENAI_ANTHROPIC_SETUP.md)
  "Missing Production Requirements").
