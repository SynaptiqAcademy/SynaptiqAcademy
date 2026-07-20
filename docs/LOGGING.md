# Logging

## Format

`backend/services/logging_config.py`'s `configure_logging()` sets up the root logger at
process startup:

- **`APP_ENV=production`:** JSON lines on stdout (`JsonFormatter`). Fields: `ts` (epoch
  ms), `level`, `logger`, `msg`, plus contextual fields when present on the log record —
  `request_id`, `trace_id`, `path`, `method`, `user_id`, `status`. Exception tracebacks
  are included under `exc`.
- **Any other `APP_ENV`:** human-readable plain text
  (`%(asctime)s %(levelname)s %(name)s — %(message)s`) for local development.

This is why every log line you've seen quoted elsewhere in this manual (e.g. in
[BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md) examples) looks like a single JSON
object per line — that's the production format, ready for a log aggregator (Datadog,
Loki, CloudWatch Logs, ELK) to ingest without custom parsing.

## Levels

`LOG_LEVEL` env var (default `INFO`). Noisy third-party libraries
(`pymongo`, `asyncio`, `httpx`, `httpcore`) are forced to `WARNING` regardless of
`LOG_LEVEL`, to keep signal-to-noise reasonable.

## Where logs go

| Deployment | Destination |
|---|---|
| Docker Compose | Container stdout → Docker's `json-file` logging driver (already configured in `docker-compose.prod.yml`: 50MB × 5 files for backend, 20MB × 3 for nginx — old logs are rotated out automatically) |
| systemd (bare metal) | `journalctl -u synaptiq-backend -f` |
| nginx | Its own access/error logs per the `json-file` driver config above |
| Backup/cron scripts | `/var/log/synaptiq/*.log` (rotated weekly, 4-week retention, via `deploy/synaptiq.cron`) |

## Querying logs

- **Docker:** `docker logs synaptiq_backend --tail=200 -f`, or pipe through `jq` for
  structured filtering since prod logs are JSON: `docker logs synaptiq_backend | jq
  'select(.level=="ERROR")'`
- **Built-in query API:** `GET /api/ops/logs` (super-admin) — queries whatever log
  records the observability platform has persisted internally (distinct from raw
  stdout/Docker logs; see [MONITORING.md](MONITORING.md)).
- **journalctl (bare metal):** `journalctl -u synaptiq-backend --since "1 hour ago" -o json`

## What gets logged with structured context

Request-scoped fields (`request_id`, `path`, `method`, `user_id`, `status`) are attached
via `extra={...}` at call sites that care about correlating a log line back to a specific
request — not every log line has all of these; absence just means that particular call
site didn't attach them.

## Sensitive data handling

- Passwords are never logged (hashed before touching any log-adjacent code path).
- OAuth tokens are encrypted before persistence and are not logged in plaintext at the
  call sites reviewed for this manual (verify any new OAuth/token-handling code
  continues this pattern before it ships).
- IP addresses: `IP_HASH_SALT` exists specifically to support GDPR-compliant hashed IP
  storage rather than raw IPs — verify at go-live that the code paths you rely on for
  audit/security logging actually use the hashed form where required for your compliance
  posture (see [SECURITY.md](SECURITY.md)).

## Missing Production Requirements

- No shipped log-aggregator configuration (Datadog agent config, Fluent Bit/Vector
  pipeline, CloudWatch agent) — the JSON format is aggregator-ready, but wiring an actual
  aggregator is an infrastructure step left to the operator.
- No documented log retention policy beyond Docker's rotation (5×50MB backend, 3×20MB
  nginx) and the cron script's 28-day file retention — decide and document a retention
  policy that matches your compliance requirements (see `deploy/ARCHITECTURE.md`'s
  compliance table for GDPR/SOC2/FERPA context) before relying on these defaults.
