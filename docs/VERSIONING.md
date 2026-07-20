# API Versioning

## Current version

`v1` (`API_VERSION_CURRENT` / `API_VERSION_LATEST` in `backend/api/versioning.py`).
`API_VERSIONS = ("v1",)` today — the tuple is designed to grow (`"v1", "v2"`) as new
versions land.

## How versioning actually works

`V1CompatMiddleware` (ASGI-level, in `backend/api/versioning.py`) transparently rewrites
`/api/v1/<rest>` → `/api/<rest>` **before** routing — so `/api/v1/billing/plans` and
`/api/billing/plans` hit the exact same handler. This means:

- There is currently **one implementation, two accepted paths.** `v1` is not (yet) a
  separately-maintained codepath — it's a compatibility alias over today's `/api/*` routes.
- Every response routed through the `/api/v1/...` path gains two headers:
  `X-Api-Version: v1` and `X-Api-Latest: v1` — clients can use these to detect drift once
  a `v2` exists.
- When a real `v2` is introduced, the same middleware pattern extends
  (`API_VERSIONS = ("v1", "v2")`), and `v1`-specific behavior differences (if any) would
  need their own routing branch — that mechanism does not exist yet because there has
  been no need for one.

## Deprecation registry

`api/versioning.py` defines a `DeprecatedEndpoint` dataclass (`path`, `method`,
`deprecated_in`, `removal_version`, `sunset_date`, `replacement`, `migration_guide`,
`reason`) — a structured way to record "this endpoint is going away" so tooling (and the
Admin Control Center) can surface sunset information to API consumers ahead of removal.

## Backward-compatibility policy

Per `deploy/ARCHITECTURE.md`: breaking changes require a major version bump and a 90-day
deprecation notice. In practice today, given the compatibility-alias implementation
above, this means:

1. Non-breaking changes (new optional fields, new endpoints) ship directly to the
   existing `v1`/unversioned surface.
2. A genuinely breaking change (removed field, changed semantics, removed endpoint)
   should be introduced behind a real `v2` once that mechanism is built out, with the old
   behavior registered in the deprecation registry and left running for the 90-day window.

## For API consumers

- Prefer calling through `/api/v1/...` explicitly (rather than bare `/api/...`) so you
  automatically benefit from the `X-Api-Version`/`X-Api-Latest` headers and any future
  version-specific behavior without needing to change your integration.
- Check `X-Api-Latest` in responses to detect when a newer version becomes available.

## Missing Production Requirements

- No `v2` implementation exists yet — the versioning *mechanism* is real and working, but
  has not yet been exercised by an actual version bump. Treat the "90-day deprecation"
  policy as a stated intent to honor, not a battle-tested process.
- No published, standalone API changelog was found (distinct from the repository's
  general `CHANGELOG.md`) — consider a dedicated API changelog once external consumers
  depend on this surface.
