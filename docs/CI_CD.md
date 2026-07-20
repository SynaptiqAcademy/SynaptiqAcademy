# CI/CD

Pipeline: `.github/workflows/ci.yml`, GitHub Actions.

## Triggers

- **Push** to `main`, `develop`, or `release/**` — but only when files under `backend/**`
  or the workflow file itself change.
- **Pull request** targeting `main` or `develop` — same path filter.

**There is currently no CI job triggered by `frontend/**` changes** — see "Missing
Production Requirements."

## Jobs (in dependency order)

| Job | What it does | Blocking? |
|---|---|---|
| **Lint** | `ruff check` (errors/warnings/flake8-bugbear/complexity, line-length ignored) and `pyflakes` (unused-import noise filtered out) | Soft — `ruff` runs with `\|\| true`, so lint failures don't fail the build today |
| **Unit Tests** | `pytest tests/ -m "not integration and not performance and not slow"` against a real `mongo:7` service container, with coverage (`--cov-fail-under=60`) | **Yes** — coverage gate fails the job below 60% |
| **Security Tests** | `pytest tests/test_auth_security.py tests/test_zero_trust.py` | Yes |
| **Regression Tests** | `pytest tests/test_regression.py` | Yes |
| **Integration Tests** | `pytest tests/test_integration.py` | Yes |
| **Performance Smoke** | `pytest tests/test_performance.py` — **only runs on `main`** (too slow for every PR) | Yes, but only gates `main` |
| **Coverage Report** | Summarizes coverage from the Unit Tests artifact | Informational |
| **Build Validation** | Imports `server.py` in a clean env, asserts the app has >50 registered routes, then runs the production validator (`services/prod_validator.py`) non-blocking | Import/route-count check is blocking; prod validator output is informational only |
| **Release Certification** | **Only runs on `main`**, requires `[unit, security, regression, integration, build]` to have passed — prints a certification banner | Gate for `main` |

## CI-only environment

The workflow sets these directly in `ci.yml`'s `env:` block (not read from any secret —
safe placeholder values, since CI runs against a throwaway `mongo:7` container, not
Atlas): `MONGODB_URI`/`MONGO_URL` → `mongodb://localhost:27017/`, `MONGODB_DB_NAME`/
`DB_NAME` → `synaptiq_ci`, `APP_ENV=test`, `REDIS_URL=""` (Redis intentionally absent —
proves graceful degradation), `EMAIL_VERIFICATION_REQUIRED=0`, `EXPOSE_RESET_TOKEN=1`
(CI-only convenience — **never set this in production**), a CI-only `JWT_SECRET` and
`ENCRYPTION_KEY` (clearly named/scoped, not usable outside CI), `CORS_ORIGINS=http://localhost:3000`.

## Running the suite locally

```bash
cd backend
export APP_ENV=test REDIS_URL="" MONGODB_URI="mongodb://localhost:27017/" MONGODB_DB_NAME=synaptiq_ci \
       JWT_SECRET="local-dev-only-secret" ENCRYPTION_KEY="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
docker run -d -p 27017:27017 mongo:7
python -m pytest tests/ -m "not integration and not performance and not slow" -q
```

## What CI does not do

- No frontend build/lint/test job.
- No deploy step — CI certifies the code; deployment is manual (or you can add a deploy
  job — see [DEPLOYMENT.md](DEPLOYMENT.md) and [RELEASE_PROCESS.md](RELEASE_PROCESS.md)
  for the manual procedure this pipeline currently expects you to run yourself).
- No container image build/push to a registry.
- No dependency vulnerability scanning.

## Missing Production Requirements

- **No frontend CI** — add a job that runs `npm ci && npm run build` (and ideally
  `npm test`) on `frontend/**` changes, so a broken frontend build is caught before merge
  rather than at deploy time.
- **No automated deploy job** — `main` being "certified" doesn't automatically ship it;
  someone must manually run the [DEPLOYMENT.md](DEPLOYMENT.md) steps. Consider adding a
  deploy job gated on the `certification` job succeeding, at least for a staging
  environment.
- **No container image publishing** — `deploy/Dockerfile` is only built locally/on the
  deploy host today; consider building and pushing to a registry (GHCR, ECR) in CI so the
  exact tested artifact is what gets deployed, rather than rebuilding from source on the
  production host.
- Lint failures are currently non-blocking (`ruff check ... || true`) — decide whether to
  make this blocking as the codebase matures.
