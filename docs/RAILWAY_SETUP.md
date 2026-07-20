# Railway Setup (Backend — Optional Alternative)

**This is not the platform's current production deployment path.** The verified,
existing production path is Docker Compose on a self-managed VM (see
[DEPLOYMENT.md](DEPLOYMENT.md), `/deploy/Dockerfile`, `/deploy/docker-compose.prod.yml`).
This document exists because it was requested as an alternative for teams who prefer a
managed container platform instead of operating Docker/nginx/certbot themselves. Nothing
here is currently configured in the repository — there is no `railway.json`/`railway.toml`.

## Why you might use this

- You want managed deploys, logs, and scaling for the backend without running your own
  Docker host.
- Railway can build directly from `deploy/Dockerfile`, so the same production image
  definition is reused — no separate Railway-specific Dockerfile is needed.

## Setup steps

1. **Create a Railway project**, add a service from this GitHub repo.
2. **Build:** Railway auto-detects Dockerfiles. Point it explicitly at
   `deploy/Dockerfile` with build context set to the **repository root** (the Dockerfile
   does `COPY backend/ /app/`, which requires the repo root as context, not `backend/`).
   In Railway's service settings: **Root Directory** = `/` (repo root), **Dockerfile
   Path** = `deploy/Dockerfile`.
3. **Start command:** already baked into the Dockerfile's `CMD` — no override needed:
   ```
   gunicorn server:app -k uvicorn.workers.UvicornWorker --workers ${WORKERS} --bind ${HOST}:${PORT} --timeout 120 --max-requests 1000 --max-requests-jitter 100 --access-logfile - --error-logfile -
   ```
   Railway injects its own `PORT` — set the container's `PORT` env var to Railway's
   provided value (Railway sets `PORT` automatically for most templates; if the
   Dockerfile's `ENV PORT=8000` conflicts, override it in Railway's service variables to
   match what Railway expects, or configure Railway to route to port 8000 explicitly).
4. **Environment variables:** set every variable from
   [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) required for your feature set, at
   minimum: `JWT_SECRET`, `MONGODB_URI`, `MONGODB_DB_NAME`, `ENCRYPTION_KEY`,
   `SUPER_ADMIN_EMAILS`, `CORS_ORIGINS`, `APP_ENV=production`, `COOKIE_SECURE=1`.
5. **Redis:** add the Railway Redis plugin (or point `REDIS_URL` at an external Redis —
   e.g. Upstash) — Railway's Redis plugin gives you a connection URL to paste directly
   into `REDIS_URL`. Everything in this codebase degrades gracefully if Redis is absent,
   but production should have it.
6. **MongoDB:** this app expects MongoDB **Atlas** specifically (`db.py` builds an Atlas
   SRV connection) — do not use Railway's MongoDB plugin as the primary store unless you
   verify SRV-string compatibility; Atlas is the documented and tested path (see
   [MONGODB_ATLAS_SETUP.md](MONGODB_ATLAS_SETUP.md)). If using Atlas, add Railway's
   egress IP ranges to Atlas Network Access (Railway uses dynamic egress IPs on some
   plans — check Railway's current networking docs for a static-IP add-on if Atlas IP
   allowlisting is required).
7. **Custom domain:** Railway service → Settings → Networking → Custom Domain → add
   `api.synaptiq.academy`. Railway will show you a `CNAME` target to create — this
   replaces the `A` record in [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md) for the `api`
   subdomain specifically (Railway terminates TLS for you; you do not need the nginx
   `api.synaptiq.academy` server block from `deploy/nginx.conf` in this scenario).
8. **Health check:** configure Railway's health check path to `/api/health` (this
   endpoint already exists and returns `200` with `{"status":"ok",...}` when Mongo is
   reachable).
9. **Background workers / WebSockets:** this backend runs its worker platform and
   WebSocket connections **in the same process** as the API (see
   `worker/__init__.py`'s supervisor, started from `server.py`'s startup event) — a
   single Railway service covers all of it. Do not split workers into a separate Railway
   service unless you first refactor `start_worker_platform_supervisor()` out of the main
   app process, which this codebase does not currently support.

## What this does not replace

Frontend hosting, Stripe, Resend, S3, and OAuth provider configuration are unaffected by
this choice — configure them per their own setup documents regardless of where the
backend runs.

## Missing Production Requirements

- No `railway.json`/`railway.toml` exists in the repo — if you adopt this path, commit
  one (Railway supports config-as-code) so the build/deploy configuration is
  version-controlled rather than only set in the Railway dashboard.
- Railway's dynamic egress IPs may require a static-IP add-on for MongoDB Atlas IP
  allowlisting — verify current Railway networking behavior before relying on Atlas
  Network Access restrictions in this configuration.
