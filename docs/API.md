# API

## Conventions

- **Base path:** all routes are mounted under `/api/` (e.g. `/api/auth/login`,
  `/api/billing/plans`). ~150 routers, one per domain, registered in `server.py`.
- **Auth:** JWT via HttpOnly cookies (`access_token`, `refresh_token`) — not a bearer
  token in the `Authorization` header for browser clients. See [SECURITY.md](SECURITY.md).
  Server-to-server/API-key auth (for the Enterprise API Platform, `backend/api/`) is a
  separate mechanism — see `api/keys.py`.
- **CSRF:** every mutating request (`POST`/`PUT`/`PATCH`/`DELETE`) from a browser client
  must include `X-CSRF-Token` matching the `csrf_token` cookie. See [SECURITY.md](SECURITY.md).
- **Errors:** unhandled exceptions never leak a raw traceback — the global exception
  handler (`server.py`) returns `{"detail": "An internal error occurred. Our team has
  been notified."}` with `500`, and logs the real exception server-side with a
  correlatable `trace_id`. Expected errors (validation, auth, not-found, rate limit) use
  FastAPI's standard `{"detail": ...}` shape with the appropriate status code.
  MongoDB connectivity failures specifically get their own handler
  (`ServerSelectionTimeoutError`/`AutoReconnect`/`ConnectionFailure`/`NetworkTimeout`) that
  always returns a clean `503` rather than a generic `500` — see [DATABASE.md](DATABASE.md).
- **Rate limiting:** `429` with `Retry-After` semantics on excess requests — see
  [SECURITY.md](SECURITY.md).

## Interactive docs

FastAPI's auto-generated interactive docs are available at the app's default paths
(`/docs` — Swagger UI, `/redoc` — ReDoc), reflecting the live OpenAPI 3.1 schema. No
override was found disabling these in production — verify whether you want them
publicly reachable before go-live (see "Missing Production Requirements").

## Key endpoint groups

| Domain | Prefix | Notes |
|---|---|---|
| Auth | `/api/auth/*` | register, login, logout, refresh, password reset, email verification |
| OAuth | `/api/google/*`, `/api/orcid/*` | see their setup docs |
| Billing | `/api/billing/*` | plans, checkout, portal, subscription, webhook |
| Credits | `/api/credits/*` | balance, usage catalogue |
| Messaging | `/api/conversations/*`, `/api/ws/*` | REST + WebSocket |
| Admin | `/api/admin_*` (many sub-domains) | super-admin/admin gated |
| Observability | `/api/ops/*` | super-admin gated, see [MONITORING.md](MONITORING.md) |
| Platform status | `/api/status/*` | public read; admin-only writes (incident management) |
| Health | `/api/health`, `/api/health/live`, `/api/health/ready` | public, unauthenticated |

This is not an exhaustive endpoint list — use the live OpenAPI schema (`/docs` or
`GET /openapi.json`) against a running instance for the complete, current surface.

## Enterprise API Platform (`backend/api/`)

A separate, more formal layer exists for third-party/programmatic API consumers
(distinct from the browser SPA's own cookie-authenticated calls):

- **API keys** (`api/keys.py`) — issued/scoped/revocable, for server-to-server auth.
- **Versioning middleware** (`api/versioning.py`) — see [VERSIONING.md](VERSIONING.md).
- **Webhooks** (`api/webhooks.py`) — outbound webhook delivery for platform events (not
  to be confused with *inbound* webhooks like Stripe's or Resend's, which are handled by
  their respective routers).
- **SDK generation** (`api/sdk_gen.py`) — generates client SDKs from the OpenAPI schema.
- **Pagination** (`api/pagination.py`) — standard cursor/offset pagination contract used
  across list endpoints in this layer.

## Missing Production Requirements

- Confirm whether `/docs`/`/redoc`/`/openapi.json` should be publicly reachable in
  production — if not, disable them (`FastAPI(docs_url=None, redoc_url=None,
  openapi_url=None)`) or gate them behind admin auth; no such restriction was found today.
- No published, versioned "public API reference" document for third-party integrators
  was found beyond the auto-generated OpenAPI schema — if you intend to support external
  API consumers, consider a curated reference beyond raw Swagger output.
