# Redis Setup

Redis is **optional** in this codebase — every consumer (`services/redis_client.py`,
`rate_limit.py`, `services/realtime.py`, worker locking/queuing) checks for `None` and
degrades gracefully (in-memory rate limiting, local-only WebSocket delivery, no
distributed locking). Production should still run Redis for correctness at scale
(distributed rate limiting, cross-replica WebSocket fan-out, session revocation).

## 1. Provisioning

**Docker Compose (default, matches `deploy/docker-compose.prod.yml`):**
Already configured — `redis:7-alpine` with:
- `--requirepass "${REDIS_PASSWORD}"` (password required)
- AOF persistence (`--appendonly yes`, fsync every second) plus RDB snapshots
  (`save 900 1 / 300 10 / 60 1000`)
- `--maxmemory 256mb --maxmemory-policy allkeys-lru` (cache eviction, not a durable store)

Nothing to configure beyond setting `REDIS_PASSWORD` in `backend/.env` before first
`docker compose up`.

**Managed Redis (alternative):** any Redis 7-compatible provider (Upstash, Redis Cloud,
Railway's Redis plugin, ElastiCache) works — just set `REDIS_URL` to the provided
connection string, in the form `redis://:password@host:port/0` or `rediss://...` for TLS.

## 2. Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `REDIS_URL` | Full connection URL | — (unset = Redis disabled, graceful degradation) |
| `REDIS_PASSWORD` | AUTH password (Docker Compose substitutes this into the Redis container's own start command and healthcheck) | — |
| `REDIS_MAX_CONNECTIONS` | Pool size | `20` |
| `REDIS_SOCKET_TIMEOUT` | Connect/socket timeout (s) | `3` |
| `REDIS_RETRY_COOLDOWN_SECONDS` | Cold-start reconnect cooldown — how often `get_redis()` retries connecting from a fully-down state | `15` |

## 3. Docker-hostname auto-fallback

`services/redis_client.py` has a convenience behavior: if `REDIS_URL` points at a
Docker-only hostname (e.g. `synaptiq_redis`) that can't be resolved (because you're
running the backend outside Docker, e.g. locally), it automatically substitutes
`localhost` with the same port/credentials. This exists purely for local development
ergonomics and requires no configuration.

## 4. What uses Redis

| Consumer | Purpose | Behavior if Redis is down |
|---|---|---|
| `rate_limit.py` | Distributed rate-limit counters (slowapi) | Falls back to in-memory limiter — works, but per-process (not shared across Gunicorn workers) |
| `services/realtime.py` | WebSocket Pub/Sub fan-out across replicas | Falls back to local-only delivery (single replica) |
| Session/JWT revocation | JTI-based refresh token revocation | Degrades — see [SECURITY.md](SECURITY.md) for the exact impact |
| `worker/` job locking | Distributed locks for scheduled jobs (prevents double-execution across replicas) | Single-replica deployments are unaffected either way |

## 5. Auto-recovery

Both the cold-start path (Redis never reachable at boot) and the mid-session drop path
(Redis was live, then died) reconnect automatically — no manual restart required. See
`services/redis_client.py`'s `get_redis()`. This was verified end-to-end in a recovery
simulation (see project history) and is a certified production blocker fix, not a
theoretical claim.

## 6. Verification

```bash
docker exec synaptiq_redis redis-cli -a "$REDIS_PASSWORD" ping
# Expect: PONG

curl https://api.synaptiq.academy/api/health
# "checks":{"redis":"ok"}  — or "unavailable" if intentionally not configured
```

## Missing Production Requirements

- Single Redis node in the default Docker Compose setup — no Sentinel/cluster HA. Add
  Redis Sentinel or a managed HA Redis for multi-replica production deployments where
  Redis downtime should not degrade rate limiting/real-time fan-out.
