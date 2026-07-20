# Deployment

This is the canonical deploy path (Docker Compose + nginx, self-hosted on a VM/VPS),
matching the assets already in `/deploy`. `VERCEL_SETUP.md` and `RAILWAY_SETUP.md` document
an alternative managed-platform path if you choose not to self-host.

## GitHub repository

- Repository contains `backend/` (FastAPI), `frontend/` (CRA React), `deploy/` (infra),
  `.github/workflows/ci.yml` (CI), `docs/` (this manual).
- CI (`.github/workflows/ci.yml`) currently triggers on pushes/PRs touching `backend/**`
  to branches `main`, `develop`, `release/**`. There is no equivalent CI job for
  `frontend/**` changes — see [CI_CD.md](CI_CD.md) "Missing Production Requirements".

## Branch strategy

| Branch | Purpose |
|---|---|
| `main` | Production. CI certification gate (`certification` job) runs only here. Protect this branch — require CI green + review before merge. |
| `develop` | Integration branch for the next release. CI runs lint/unit/security/regression/integration here too. |
| `release/*` | Cut from `develop` when preparing a release; only bugfixes land here. CI also runs on `release/**` pushes. Merge into `main` and tag on release day (see [RELEASE_PROCESS.md](RELEASE_PROCESS.md)). |

## Clone and install

```bash
git clone <repo-url> sinaptiq-main-2
cd sinaptiq-main-2

# Backend
cd backend
python3.11 -m venv .venv        # or use the repo-root .venv convention already in use
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # see note in ENVIRONMENT_VARIABLES.md — create this file if absent
nano .env                       # fill in every REQUIRED variable

# Frontend
cd ../frontend
npm ci
```

## Frontend build & deploy

```bash
cd frontend
# REACT_APP_BACKEND_URL must be set in the environment (or an .env.production file)
# before building — it is compiled into the static bundle.
REACT_APP_BACKEND_URL=https://api.synaptiq.academy npm run build
# Output: frontend/build/  (static files)
```

The production nginx config (`deploy/nginx.conf`) expects the build output at
`../frontend/build` relative to `deploy/`, mounted read-only into the `nginx` container
(see `docker-compose.prod.yml`'s `nginx` service volumes). Copy the fresh build there
before starting/restarting the `nginx` container.

## Backend deployment (Docker Compose — recommended)

```bash
# 1. Fill backend/.env with every required variable (see ENVIRONMENT_VARIABLES.md)

# 2. Obtain SSL certificates (see DOMAIN_CONFIGURATION.md)
apt install certbot
certbot certonly --standalone \
  -d synaptiq.academy -d www.synaptiq.academy -d api.synaptiq.academy

# 3. Build the frontend (see above), so nginx has something to serve

# 4. Export REDIS_PASSWORD for docker-compose variable substitution
export REDIS_PASSWORD="$(grep '^REDIS_PASSWORD=' backend/.env | cut -d= -f2)"

# 5. Start all services
docker compose -f deploy/docker-compose.prod.yml up -d

# 6. Verify
curl https://api.synaptiq.academy/api/health
```

This starts three containers: `synaptiq_backend` (Gunicorn + Uvicorn workers, built from
`deploy/Dockerfile`), `synaptiq_redis` (Redis 7 with AOF persistence), and
`synaptiq_nginx` (TLS termination + static file serving + reverse proxy).

### Backend deployment (bare metal / systemd — alternative)

If not using Docker, `deploy/synaptiq-backend.service` is a ready-to-use systemd unit:

```bash
sudo cp deploy/synaptiq-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now synaptiq-backend
journalctl -u synaptiq-backend -f
```

It runs `gunicorn server:app -k uvicorn.workers.UvicornWorker --workers 4` bound to
`127.0.0.1:8000`, expecting nginx (installed separately) to reverse-proxy to it — same
`nginx.conf` applies, just point `proxy_pass` at `127.0.0.1:8000` instead of the Docker
service name `synaptiq_backend`.

## Build & start commands (reference)

| Component | Build command | Start command |
|---|---|---|
| Frontend | `npm run build` (runs `craco build`) | Static files served by nginx — no server process |
| Backend (Docker) | `docker build -t synaptiq-backend -f deploy/Dockerfile .` | `gunicorn server:app -k uvicorn.workers.UvicornWorker --workers ${WORKERS} --bind ${HOST}:${PORT} --timeout 120` (baked into the Dockerfile `CMD`) |
| Backend (bare metal) | `pip install -r requirements.txt` | Same gunicorn command, via systemd unit |

## Production environment

- `APP_ENV=production` — forces JSON structured logs and gates prod-only validation
  (`docker-compose.prod.yml` sets this explicitly regardless of what `.env` says).
- `COOKIE_SECURE=1` — also force-set in `docker-compose.prod.yml`.
- Full variable list: [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md).

## HTTPS

TLS is terminated at nginx using Let's Encrypt certificates via `certbot`. See
[DOMAIN_CONFIGURATION.md](DOMAIN_CONFIGURATION.md) for the full certificate + renewal
setup. Renewal is automated twice daily via `deploy/synaptiq.cron`
(`certbot renew --quiet --deploy-hook "nginx -s reload"`).

## Custom domains

Production domains, as hard-coded in `deploy/nginx.conf` and referenced throughout the
codebase (OAuth redirect URIs, email links, CORS allowlist):

- `synaptiq.academy`, `www.synaptiq.academy` — frontend (React SPA)
- `api.synaptiq.academy` — backend API

Changing domains requires updating: `nginx.conf` `server_name` directives, `CORS_ORIGINS`,
`FRONTEND_BASE_URL`/`BACKEND_BASE_URL`, Google OAuth `GOOGLE_REDIRECT_URI` (+ console
config), ORCID `ORCID_REDIRECT_URI` (+ developer tools config), and the Stripe webhook
endpoint URL in the Stripe dashboard.

## Reverse proxy

nginx (`deploy/nginx.conf`) does:
- HTTP → HTTPS redirect for all three hostnames
- TLS termination (TLS 1.2/1.3 only, modern cipher list, HSTS, OCSP stapling)
- Rate-limit zones: `api_general` (60 req/min/IP), `api_auth` (10 req/min/IP, burst 5) on
  `/api/(auth|register|login|password-reset)`
- WebSocket upgrade handling for `/api/ws/` with a 3600s read timeout
- Static asset caching (1 year, immutable) for hashed CRA build assets
- SPA fallback (`try_files ... /index.html`) for all other frontend routes
- Security headers: HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy`, `Permissions-Policy`

## Production verification

After any deploy:

```bash
# 1. Health check
curl https://api.synaptiq.academy/api/health
# Expect: {"service":"SYNAPTIQ","status":"ok","checks":{"mongodb":"ok",...}}

# 2. Liveness/readiness (used by container orchestrators)
curl https://api.synaptiq.academy/api/health/live
curl https://api.synaptiq.academy/api/health/ready

# 3. Public status page
curl https://api.synaptiq.academy/api/status

# 4. Frontend loads
curl -I https://synaptiq.academy   # expect 200

# 5. Full manual smoke test — see PRODUCTION_CHECKLIST.md
```

## Rollback procedure

**Docker Compose:**
```bash
# Roll back to the previous image tag (tag every release — see RELEASE_PROCESS.md)
docker compose -f deploy/docker-compose.prod.yml stop backend
docker tag synaptiq-backend:<previous-tag> synaptiq-backend:latest
docker compose -f deploy/docker-compose.prod.yml up -d --no-deps backend
curl https://api.synaptiq.academy/api/health
```

**Git-based rollback (if not using tagged images):**
```bash
git checkout <previous-good-commit-or-tag>
docker compose -f deploy/docker-compose.prod.yml build backend
docker compose -f deploy/docker-compose.prod.yml up -d --no-deps backend
```

Database schema changes in this codebase are additive (no destructive migrations found)
— rolling back application code does not require a corresponding database rollback in
the common case. If a specific release did run a destructive data migration, that
release's notes must document its own rollback steps (see [RELEASE_PROCESS.md](RELEASE_PROCESS.md)).

## Disaster recovery

Full procedures: [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md) and
`/deploy/INCIDENT_RESPONSE.md`. Summary:

- **RPO:** 24 hours (daily `mongodump` → S3 via `deploy/backup.sh`). Reducible to <1
  hour by upgrading to MongoDB Atlas M10+ continuous backup (point-in-time restore).
- **RTO:** ~4 hours (manual restore + verify + restart) with `mongodump` backups, ~30
  minutes with Atlas continuous backup.
- Full-host loss: provision a new host, install Docker, copy `.env` and SSL certs, run
  `deploy/backup.sh restore`, update DNS A records (see `deploy/RUNBOOK.md` → "Service
  migration").

## Missing Production Requirements

- No blue/green or canary deployment mechanism — `docker compose up -d --no-deps backend`
  is a hard cutover (brief connection drop while the new container passes its health
  check before nginx's `depends_on` gate opens).
- No automated smoke test suite runs post-deploy — verification today is the manual
  curl checklist above. Consider adding a post-deploy smoke test job to CI.
- No documented staging environment — `develop`/`release/*` branches exist in the
  branch strategy but no staging infrastructure/URL was found in the codebase.
