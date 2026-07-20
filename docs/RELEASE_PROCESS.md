# Release Process

## Versioning scheme

[Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`), tracked in
`/CHANGELOG.md` at the repo root, which follows the
[Keep a Changelog](https://keepachangelog.com/) format. Current version at time of
writing: **1.7.0**. This is distinct from [VERSIONING.md](VERSIONING.md)'s API version
(`v1`) — the app/release version and the API contract version change independently.

## Branch strategy (recap — full detail in [DEPLOYMENT.md](DEPLOYMENT.md))

- `main` — production, protected, CI certification gate required.
- `develop` — integration branch for the next release.
- `release/*` — cut from `develop` to stabilize a release; only bugfixes land here.

## Cutting a release

1. From `develop`, create `release/x.y.z`.
2. Only bugfixes and release-prep changes (changelog entry, version bump) land on this
   branch — no new features.
3. CI runs the full suite on every push to `release/**` (same jobs as `main`/`develop` —
   see [CI_CD.md](CI_CD.md)), except the performance-smoke and certification jobs, which
   are gated to `main` only.
4. Update `/CHANGELOG.md`: add a new `## [x.y.z] — YYYY-MM-DD · <theme>` section, following
   the existing `Added`/`Changed`/`Fixed`/`Security` sub-heading convention already used
   throughout the file.
5. When stable: merge `release/x.y.z` → `main` (triggers the `certification` CI job) and
   also merge back into `develop` (so bugfixes found during stabilization aren't lost).
6. Tag the release: `git tag -a v1.8.0 -m "Release 1.8.0" && git push origin v1.8.0`.
7. Deploy `main` per [DEPLOYMENT.md](DEPLOYMENT.md). Tag your Docker image with the same
   version (`docker build -t synaptiq-backend:1.8.0 ...`) so rollback (see DEPLOYMENT.md's
   "Rollback procedure") has a concrete previous tag to fall back to.

## Hotfixes

For a production-breaking bug that can't wait for the normal release cycle:

1. Branch `hotfix/x.y.z+1` directly from `main` (not `develop`).
2. Fix, test locally, push — CI runs the same gates as any `main`-adjacent push would
   (verify the branch name pattern is covered by `ci.yml`'s triggers; if not, open the PR
   against `main` directly so the PR-triggered jobs still run).
3. Merge to `main`, tag, deploy immediately per [DEPLOYMENT.md](DEPLOYMENT.md).
4. Merge the same fix into `develop` (and any active `release/*` branch) so it isn't lost
   in the next regular release.
5. Add a `## [x.y.z+1] — YYYY-MM-DD · Hotfix: <brief description>` entry to
   `CHANGELOG.md` immediately — don't defer changelog updates for hotfixes.

## Pre-release checklist

Before merging any `release/*` branch to `main`:

- [ ] CI is green on the release branch (lint/unit/security/regression/integration/build)
- [ ] `CHANGELOG.md` updated
- [ ] [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) re-verified for any subsystem the
      release touched
- [ ] Any new environment variables documented in
      [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) and set in production `.env`
      *before* deploying the new code (never deploy code that depends on a variable that
      isn't set yet)
- [ ] Any new/changed MongoDB migration block (see [DATABASE.md](DATABASE.md)) has been
      tested against a copy of production-shaped data, not just a fresh empty database
- [ ] Rollback plan confirmed (previous Docker tag exists, or previous commit/tag noted)

## Missing Production Requirements

- No automated release-branch-cutting tooling (e.g. `release-please`, a GitHub Action
  that bumps version/changelog automatically) — this is entirely manual today.
- No documented process for what happens if a migration block (see
  [DATABASE.md](DATABASE.md)) needs to be rolled back alongside a code rollback — since
  migrations are idempotent-forward-only blocks, a destructive migration bundled into a
  release that then needs rolling back requires a manually-written reverse migration;
  there is no tooling support for this today.
